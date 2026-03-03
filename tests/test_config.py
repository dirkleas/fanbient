"""Tests for configuration."""

from fanbient.config import (
    AudioConfig,
    FanbientConfig,
    FanControlConfig,
    MQTTConfig,
    TemperatureConfig,
    ThermalCameraConfig,
)


def test_default_config():
    config = FanbientConfig()
    assert config.mqtt.host == "localhost"
    assert config.mqtt.port == 1883
    assert config.audio.sample_rate == 16000
    assert config.fan.cooldown_seconds == 300.0
    assert config.temperature.enabled is False
    assert config.thermal_camera.enabled is False
    assert config.log_level == "INFO"


def test_mqtt_defaults():
    config = MQTTConfig()
    assert config.client_id == "fanbient"
    assert config.zone == "bedroom"
    assert config.tasmota_device == "tasmota_fan"


def test_audio_defaults():
    config = AudioConfig()
    assert config.channels == 1
    assert config.chunk_duration == 2.5
    assert config.n_mfcc == 13


def test_fan_control_defaults():
    config = FanControlConfig()
    assert config.detection_confirmations == 2
    assert config.cooldown_seconds == 300.0


def test_temperature_defaults():
    config = TemperatureConfig()
    assert config.on_threshold_f == 98.8
    assert config.off_threshold_f == 98.2
    assert config.source == "apple_watch"


def test_thermal_camera_defaults():
    config = ThermalCameraConfig()
    assert config.emissivity == 0.98
    assert config.poll_interval == 10.0
    assert config.device == "/dev/video0"


def test_deadband_valid():
    """On threshold must be higher than off threshold."""
    config = TemperatureConfig()
    assert config.on_threshold_f > config.off_threshold_f
