"""MQTT client wrapper for fanbient."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Callable

import paho.mqtt.client as mqtt

if TYPE_CHECKING:
    from fanbient.config import MQTTConfig

logger = logging.getLogger(__name__)

# Type alias for subscription callbacks
MessageCallback = Callable[[str, Any], None]


class FanbientMQTT:
    """MQTT client with fanbient topic conventions and Tasmota bridging."""

    def __init__(self, config: MQTTConfig) -> None:
        self.config = config
        self._client = mqtt.Client(
            client_id=config.client_id,
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        )
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message
        self._subscriptions: dict[str, list[MessageCallback]] = {}
        self._connected = False

        if config.username:
            self._client.username_pw_set(config.username, config.password)

        # LWT for system status
        self._client.will_set(
            "fanbient/system/status", payload="offline", qos=1, retain=True,
        )

    def _on_connect(
        self, client: mqtt.Client, userdata: Any, flags: Any,
        rc: mqtt.ReasonCode, properties: Any = None,
    ) -> None:
        if rc == 0:
            logger.info("MQTT connected to %s:%d", self.config.host, self.config.port)
            self._connected = True
            # Publish online status
            self._client.publish(
                "fanbient/system/status", "online", qos=1, retain=True,
            )
            # Re-subscribe on reconnect
            for topic in self._subscriptions:
                self._client.subscribe(topic, qos=1)
        else:
            logger.error("MQTT connection failed: %s", rc)

    def _on_disconnect(
        self, client: mqtt.Client, userdata: Any, flags: Any,
        rc: mqtt.ReasonCode, properties: Any = None,
    ) -> None:
        self._connected = False
        if rc != 0:
            logger.warning("MQTT unexpected disconnect (rc=%s), will reconnect", rc)

    def _on_message(
        self, client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage,
    ) -> None:
        topic = msg.topic
        try:
            payload = json.loads(msg.payload.decode())
        except (json.JSONDecodeError, UnicodeDecodeError):
            payload = msg.payload.decode()

        for pattern, callbacks in self._subscriptions.items():
            if mqtt.topic_matches_sub(pattern, topic):
                for cb in callbacks:
                    try:
                        cb(topic, payload)
                    except Exception:
                        logger.exception("Error in MQTT callback for %s", topic)

    def connect(self) -> None:
        """Connect to the MQTT broker."""
        logger.info("Connecting to MQTT broker %s:%d", self.config.host, self.config.port)
        self._client.connect(
            self.config.host, self.config.port, keepalive=self.config.keepalive,
        )
        self._client.loop_start()

    def disconnect(self) -> None:
        """Cleanly disconnect from MQTT broker."""
        self._client.publish(
            "fanbient/system/status", "offline", qos=1, retain=True,
        )
        self._client.loop_stop()
        self._client.disconnect()
        self._connected = False
        logger.info("MQTT disconnected")

    def subscribe(self, topic: str, callback: MessageCallback) -> None:
        """Subscribe to an MQTT topic with a callback."""
        if topic not in self._subscriptions:
            self._subscriptions[topic] = []
            if self._connected:
                self._client.subscribe(topic, qos=1)
        self._subscriptions[topic].append(callback)
        logger.debug("Subscribed to %s", topic)

    def publish(self, topic: str, payload: Any, qos: int = 0, retain: bool = False) -> None:
        """Publish to an MQTT topic. Dicts are JSON-encoded."""
        if isinstance(payload, dict):
            payload = json.dumps(payload)
        self._client.publish(topic, payload, qos=qos, retain=retain)

    # --- Convenience methods for fanbient topics ---

    def _topic(self, *parts: str) -> str:
        """Build a fanbient topic: fanbient/{zone}/..."""
        return f"fanbient/{self.config.zone}/{'/'.join(parts)}"

    def publish_panting(self, detected: bool, confidence: float, tier: str = "T1") -> None:
        """Publish a panting detection event."""
        self.publish(self._topic("audio", "panting"), {
            "detected": detected,
            "confidence": round(confidence, 3),
            "tier": tier,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def publish_state(self, state: str, trigger: str | None = None) -> None:
        """Publish current state machine state."""
        self.publish(self._topic("state"), state, qos=1, retain=True)
        if trigger:
            self.publish(self._topic("trigger"), trigger, qos=1, retain=True)

    def publish_temp(self, temp_f: float, source: str = "apple_watch") -> None:
        """Publish a temperature reading."""
        self.publish(self._topic("temp", "reading"), {
            "temp_f": round(temp_f, 2),
            "source": source,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def command_fan(self, on: bool) -> None:
        """Send fan command (bridges to Tasmota topic)."""
        payload = "ON" if on else "OFF"
        # Publish to fanbient topic
        self.publish(self._topic("fan", "command"), payload, qos=1)
        # Bridge to Tasmota
        tasmota_topic = f"cmnd/{self.config.tasmota_device}/POWER"
        self.publish(tasmota_topic, payload, qos=1)
        logger.info("Fan command: %s", payload)

    def subscribe_fan_state(self, callback: MessageCallback) -> None:
        """Subscribe to fan state updates from Tasmota."""
        tasmota_topic = f"stat/{self.config.tasmota_device}/POWER"
        self.subscribe(tasmota_topic, callback)

    @property
    def is_connected(self) -> bool:
        return self._connected
