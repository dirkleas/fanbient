"""Core fanbient service — protocol-agnostic orchestration layer.

This is the central service that can be driven by any interface:
CLI (typer), REST (FastAPI), MCP, MQTT commands, etc.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

from fanbient.audio.capture import AudioCapture
from fanbient.audio.classifier import DetectionResult, PantingClassifier
from fanbient.config import FanbientConfig
from fanbient.control.state_machine import FanState, FanStateMachine, TriggerType
from fanbient.mqtt.client import FanbientMQTT
from fanbient.sensors.temperature import (
    SensorLoggerReceiver,
    TemperatureMonitor,
    ThermalCamera,
)

logger = logging.getLogger(__name__)


@dataclass
class ServiceStatus:
    """Snapshot of current service state."""

    running: bool = False
    fan_state: str = "idle"
    active_triggers: list[str] = field(default_factory=list)
    mqtt_connected: bool = False
    last_detection: DetectionResult | None = None
    last_temp_f: float | None = None
    uptime_seconds: float = 0.0
    timestamp: str = ""

    def to_dict(self) -> dict:
        return {
            "running": self.running,
            "fan_state": self.fan_state,
            "active_triggers": self.active_triggers,
            "mqtt_connected": self.mqtt_connected,
            "last_detection": {
                "detected": self.last_detection.detected,
                "confidence": self.last_detection.confidence,
                "tier": self.last_detection.tier,
            } if self.last_detection else None,
            "last_temp_f": self.last_temp_f,
            "uptime_seconds": round(self.uptime_seconds, 1),
            "timestamp": self.timestamp,
        }


class FanbientService:
    """Core service that wires audio capture, classification, state machine,
    MQTT, and temperature sensing. Protocol-agnostic — call methods from
    any interface (CLI, REST, MCP, etc.).
    """

    def __init__(self, config: FanbientConfig, dry_run: bool = False) -> None:
        self.config = config
        self.dry_run = dry_run
        self._running = False
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._start_time: float | None = None

        # Components (initialized on start)
        self._mqtt: FanbientMQTT | None = None
        self._state_machine: FanStateMachine | None = None
        self._classifier: PantingClassifier | None = None
        self._capture: AudioCapture | None = None
        self._temp_monitor: TemperatureMonitor | None = None
        self._sensor_receiver: SensorLoggerReceiver | None = None
        self._thermal_cam: ThermalCamera | None = None

        # Observable state
        self._last_detection: DetectionResult | None = None
        self._event_callbacks: list[Callable[[str, dict], None]] = []

    def on_event(self, callback: Callable[[str, dict], None]) -> None:
        """Register a callback for service events.

        Events: "fan_change", "state_change", "detection", "temp_reading"
        """
        self._event_callbacks.append(callback)

    def _emit(self, event: str, data: dict) -> None:
        for cb in self._event_callbacks:
            try:
                cb(event, data)
            except Exception:
                logger.exception("Event callback error for %s", event)

    def start(self, model_path: str | None = None, background: bool = True) -> None:
        """Start the fanbient service.

        Args:
            model_path: Path to trained .pkl classifier model. None = heuristic.
            background: If True, run audio loop in background thread.
        """
        if self._running:
            logger.warning("Service already running")
            return

        import time
        self._start_time = time.monotonic()

        # --- MQTT ---
        if not self.dry_run:
            self._mqtt = FanbientMQTT(self.config.mqtt)
            try:
                self._mqtt.connect()
            except Exception as e:
                logger.warning("MQTT connection failed: %s — continuing without MQTT", e)
                self._mqtt = None

        # --- State Machine ---
        self._state_machine = FanStateMachine(
            self.config.fan,
            on_fan_change=self._on_fan_change,
            on_state_change=self._on_state_change,
        )

        # --- Classifier ---
        self._classifier = PantingClassifier(self.config.audio)
        if model_path:
            self._classifier.load(model_path)
            logger.info("Loaded classifier model from %s", model_path)
        else:
            logger.info("Using heuristic panting detector (no trained model)")

        # --- Temperature ---
        if self.config.temperature.enabled or self.config.thermal_camera.enabled:
            self._temp_monitor = TemperatureMonitor(
                self.config.temperature, self._on_temp_threshold,
            )
            if self.config.temperature.enabled:
                self._sensor_receiver = SensorLoggerReceiver(
                    self.config.temperature, self._temp_monitor,
                )
                self._sensor_receiver.start()
            if self.config.thermal_camera.enabled:
                self._thermal_cam = ThermalCamera(
                    self.config.thermal_camera, self._temp_monitor,
                )
                self._thermal_cam.start()

        # --- Audio ---
        self._capture = AudioCapture(self.config.audio)
        self._capture.start()

        self._running = True
        self._stop_event.clear()

        if background:
            self._thread = threading.Thread(target=self._audio_loop, daemon=True)
            self._thread.start()
        else:
            self._audio_loop()

    def stop(self) -> None:
        """Stop the service gracefully."""
        if not self._running:
            return

        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None

        if self._capture:
            self._capture.stop()
        if self._sensor_receiver:
            self._sensor_receiver.stop()
        if self._thermal_cam:
            self._thermal_cam.stop()
        if self._mqtt:
            self._mqtt.disconnect()

        self._running = False
        logger.info("Service stopped")

    def status(self) -> ServiceStatus:
        """Get current service status."""
        import time
        uptime = 0.0
        if self._start_time and self._running:
            uptime = time.monotonic() - self._start_time

        return ServiceStatus(
            running=self._running,
            fan_state=self._state_machine.state.value if self._state_machine else "idle",
            active_triggers=[t.value for t in (self._state_machine.active_triggers if self._state_machine else set())],
            mqtt_connected=self._mqtt.is_connected if self._mqtt else False,
            last_detection=self._last_detection,
            last_temp_f=self._temp_monitor.last_temp if self._temp_monitor else None,
            uptime_seconds=uptime,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def manual_fan_on(self) -> None:
        """Manually turn fan on."""
        if self._state_machine:
            self._state_machine.manual_on()

    def manual_fan_off(self) -> None:
        """Manually turn fan off."""
        if self._state_machine:
            self._state_machine.manual_off()

    def trigger(self, trigger_type: str) -> None:
        """Programmatically fire a trigger."""
        if self._state_machine:
            self._state_machine.trigger(TriggerType(trigger_type))

    def clear_trigger(self, trigger_type: str) -> None:
        """Programmatically clear a trigger."""
        if self._state_machine:
            self._state_machine.clear_trigger(TriggerType(trigger_type))

    def push_temperature(self, temp_f: float, source: str = "external") -> None:
        """Push a temperature reading from an external source."""
        if self._temp_monitor:
            self._temp_monitor.update(temp_f, source)
        if self._mqtt:
            self._mqtt.publish_temp(temp_f, source)

    # --- Internal ---

    def _audio_loop(self) -> None:
        while not self._stop_event.is_set():
            chunk = self._capture.read_chunk(timeout=1.0)
            if chunk is not None and self._classifier:
                result = self._classifier.detect(chunk)
                self._last_detection = result
                if result.detected:
                    self._state_machine.trigger(TriggerType.PANTING)
                    if self._mqtt:
                        self._mqtt.publish_panting(True, result.confidence)
                    self._emit("detection", {
                        "detected": True, "confidence": result.confidence,
                    })
                else:
                    self._state_machine.clear_trigger(TriggerType.PANTING)

            if self._state_machine:
                self._state_machine.tick()

    def _on_fan_change(self, on: bool) -> None:
        logger.info("Fan %s", "ON" if on else "OFF")
        if self._mqtt:
            self._mqtt.command_fan(on)
        self._emit("fan_change", {"on": on})

    def _on_state_change(self, state: FanState, trigger: TriggerType | None) -> None:
        if self._mqtt:
            self._mqtt.publish_state(state.value, trigger.value if trigger else None)
        self._emit("state_change", {
            "state": state.value,
            "trigger": trigger.value if trigger else None,
        })

    def _on_temp_threshold(self, triggered: bool, temp_f: float) -> None:
        if triggered:
            self._state_machine.trigger(TriggerType.TEMPERATURE)
        else:
            self._state_machine.clear_trigger(TriggerType.TEMPERATURE)
        if self._mqtt:
            self._mqtt.publish_temp(temp_f)
        self._emit("temp_reading", {"temp_f": temp_f, "triggered": triggered})
