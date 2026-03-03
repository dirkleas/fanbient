"""Configuration models for fanbient."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings


class MQTTConfig(BaseSettings):
    """MQTT broker connection settings."""

    model_config = {"env_prefix": "FANBIENT_MQTT_"}

    host: str = "localhost"
    port: int = 1883
    username: str | None = None
    password: str | None = None
    client_id: str = "fanbient"
    zone: str = "bedroom"
    # Tasmota device name for smart switch bridging
    tasmota_device: str = "tasmota_fan"
    keepalive: int = 60
    reconnect_delay: float = 1.0
    reconnect_max_delay: float = 60.0


class AudioConfig(BaseSettings):
    """Audio capture and classification settings."""

    model_config = {"env_prefix": "FANBIENT_AUDIO_"}

    sample_rate: int = 16000
    channels: int = 1
    chunk_duration: float = 2.5  # seconds per analysis window
    device: int | None = None  # sounddevice device index, None = default

    # T1 classifier thresholds
    panting_confidence_threshold: float = 0.6
    # Spectral features
    n_mfcc: int = 13
    hop_length: int = 512
    n_fft: int = 2048


class FanControlConfig(BaseSettings):
    """Fan state machine and control settings."""

    model_config = {"env_prefix": "FANBIENT_FAN_"}

    cooldown_seconds: float = 300.0  # 5 minutes after last trigger
    # Number of consecutive positive detections before triggering
    detection_confirmations: int = 2
    # Minimum seconds between state change logs
    log_debounce: float = 5.0


class TemperatureConfig(BaseSettings):
    """Temperature sensing settings (Phase 2)."""

    model_config = {"env_prefix": "FANBIENT_TEMP_"}

    enabled: bool = False
    # Deadband thresholds (Fahrenheit)
    on_threshold_f: float = 98.8
    off_threshold_f: float = 98.2
    # HTTP receiver for Sensor Logger
    http_host: str = "0.0.0.0"
    http_port: int = 8080
    # Sensor source: "apple_watch", "thermal_camera", or "both"
    source: str = "apple_watch"


class ThermalCameraConfig(BaseSettings):
    """Thermal imaging camera settings (optional temp sensor)."""

    model_config = {"env_prefix": "FANBIENT_THERMAL_"}

    enabled: bool = False
    # Device index or path for thermal camera
    device: str = "/dev/video0"
    # Region of interest for temperature extraction
    roi_x: int = 0
    roi_y: int = 0
    roi_width: int = 0  # 0 = full frame
    roi_height: int = 0  # 0 = full frame
    # Polling interval in seconds
    poll_interval: float = 10.0
    # Emissivity for skin temperature measurement
    emissivity: float = 0.98


class FanbientConfig(BaseSettings):
    """Top-level fanbient configuration."""

    model_config = {"env_prefix": "FANBIENT_"}

    mqtt: MQTTConfig = Field(default_factory=MQTTConfig)
    audio: AudioConfig = Field(default_factory=AudioConfig)
    fan: FanControlConfig = Field(default_factory=FanControlConfig)
    temperature: TemperatureConfig = Field(default_factory=TemperatureConfig)
    thermal_camera: ThermalCameraConfig = Field(default_factory=ThermalCameraConfig)
    log_level: str = "INFO"
