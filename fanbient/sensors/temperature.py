"""Temperature sensor integrations.

Supports:
1. Apple Watch via iOS Sensor Logger HTTP push
2. Thermal imaging camera (e.g. FLIR Lepton, AMG8833, MLX90640)

Both sources push temperature readings through a callback to the state machine.
"""

from __future__ import annotations

import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from fanbient.config import TemperatureConfig, ThermalCameraConfig

logger = logging.getLogger(__name__)


class TemperatureMonitor:
    """Monitors temperature and calls back when thresholds are crossed.

    Implements deadband (hysteresis): triggers ON when temp >= on_threshold,
    triggers OFF when temp <= off_threshold.
    """

    def __init__(
        self,
        config: TemperatureConfig,
        on_threshold_crossed: Callable[[bool, float], None] | None = None,
    ) -> None:
        self.config = config
        self._on_threshold_crossed = on_threshold_crossed
        self._triggered = False
        self._last_temp: float | None = None

    def update(self, temp_f: float, source: str = "apple_watch") -> bool:
        """Process a new temperature reading. Returns whether fan should be on."""
        self._last_temp = temp_f

        if not self._triggered and temp_f >= self.config.on_threshold_f:
            self._triggered = True
            logger.info(
                "Temperature threshold crossed: %.1f°F >= %.1f°F (source=%s)",
                temp_f, self.config.on_threshold_f, source,
            )
            if self._on_threshold_crossed:
                self._on_threshold_crossed(True, temp_f)
        elif self._triggered and temp_f <= self.config.off_threshold_f:
            self._triggered = False
            logger.info(
                "Temperature below threshold: %.1f°F <= %.1f°F (source=%s)",
                temp_f, self.config.off_threshold_f, source,
            )
            if self._on_threshold_crossed:
                self._on_threshold_crossed(False, temp_f)

        return self._triggered

    @property
    def is_triggered(self) -> bool:
        return self._triggered

    @property
    def last_temp(self) -> float | None:
        return self._last_temp


class SensorLoggerReceiver:
    """HTTP server that receives temperature data from iOS Sensor Logger app.

    Sensor Logger can push JSON data via HTTP POST. This receiver parses
    the body temperature field and feeds it to a TemperatureMonitor.
    """

    def __init__(
        self,
        config: TemperatureConfig,
        monitor: TemperatureMonitor,
    ) -> None:
        self.config = config
        self.monitor = monitor
        self._server: HTTPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Start the HTTP receiver in a background thread."""
        monitor = self.monitor

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length)
                try:
                    data = json.loads(body)
                    temp_f = _extract_temperature(data)
                    if temp_f is not None:
                        monitor.update(temp_f, source="apple_watch")
                    self.send_response(200)
                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    logger.warning("Invalid sensor data: %s", e)
                    self.send_response(400)
                self.end_headers()

            def log_message(self, format: str, *args: object) -> None:
                # Suppress default HTTP logging
                pass

        self._server = HTTPServer(
            (self.config.http_host, self.config.http_port), Handler,
        )
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        logger.info(
            "Sensor Logger receiver started on %s:%d",
            self.config.http_host, self.config.http_port,
        )

    def stop(self) -> None:
        """Stop the HTTP receiver."""
        if self._server:
            self._server.shutdown()
            self._server = None
        logger.info("Sensor Logger receiver stopped")


class ThermalCamera:
    """Thermal imaging camera integration for contactless temperature sensing.

    Supports cameras that expose a video device (e.g. FLIR Lepton on a
    PureThermal breakout, AMG8833 grid-eye, MLX90640). Polls the camera
    at a configurable interval, extracts max temperature from a region of
    interest, and feeds it to a TemperatureMonitor.

    Requires opencv-python for image capture (optional dependency).
    """

    def __init__(
        self,
        config: ThermalCameraConfig,
        monitor: TemperatureMonitor,
    ) -> None:
        self.config = config
        self.monitor = monitor
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        """Start polling the thermal camera in a background thread."""
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        logger.info("Thermal camera started on %s", self.config.device)

    def stop(self) -> None:
        """Stop the polling thread."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5.0)
        logger.info("Thermal camera stopped")

    def _poll_loop(self) -> None:
        try:
            import cv2
        except ImportError:
            logger.error(
                "opencv-python not installed — thermal camera unavailable. "
                "Install with: uv add opencv-python"
            )
            return

        cap = cv2.VideoCapture(self.config.device)
        if not cap.isOpened():
            logger.error("Cannot open thermal camera at %s", self.config.device)
            return

        try:
            while not self._stop_event.is_set():
                ret, frame = cap.read()
                if not ret:
                    logger.warning("Thermal camera read failed")
                    self._stop_event.wait(self.config.poll_interval)
                    continue

                temp_f = self._extract_temp_from_frame(frame)
                if temp_f is not None:
                    self.monitor.update(temp_f, source="thermal_camera")

                self._stop_event.wait(self.config.poll_interval)
        finally:
            cap.release()

    def _extract_temp_from_frame(self, frame) -> float | None:
        """Extract temperature from a thermal camera frame.

        For radiometric cameras (e.g. FLIR Lepton with PureThermal),
        raw pixel values map to temperature. The exact mapping depends
        on the camera/SDK. This provides a basic implementation that
        assumes 16-bit raw values in decikelvin (common for Lepton).

        Override this method for your specific camera.
        """
        import numpy as np

        roi = frame
        if self.config.roi_width > 0 and self.config.roi_height > 0:
            x, y = self.config.roi_x, self.config.roi_y
            w, h = self.config.roi_width, self.config.roi_height
            roi = frame[y : y + h, x : x + w]

        if roi.ndim == 3:
            # Convert to grayscale if color
            roi = roi[:, :, 0].astype(np.float64)

        # Assume 16-bit raw values in centikelvin (common Lepton format)
        # Convert: pixel_value / 100 → Kelvin → Fahrenheit
        max_val = float(np.max(roi))
        if max_val > 1000:  # Likely raw thermal data in centikelvin
            kelvin = max_val / 100.0
            temp_f = (kelvin - 273.15) * 9.0 / 5.0 + 32.0
            return temp_f

        # Fallback: if values are small, assume already in Celsius
        if max_val > 0:
            temp_f = max_val * 9.0 / 5.0 + 32.0
            return temp_f

        return None


def _extract_temperature(data: dict) -> float | None:
    """Extract body temperature (°F) from Sensor Logger JSON payload.

    Sensor Logger can send data in various formats. This handles common ones.
    """
    # Direct temperature field
    if "temperature" in data:
        return float(data["temperature"])

    # Nested under payload
    if "payload" in data:
        payload = data["payload"]
        if isinstance(payload, dict) and "temperature" in payload:
            return float(payload["temperature"])

    # Array of sensor readings
    if "readings" in data:
        for reading in data["readings"]:
            if reading.get("name") == "wristTemperature":
                return float(reading["value"])

    return None
