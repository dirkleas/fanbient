# fanbient — System Architecture

## Overview

fanbient is an ambient smart fan system for autonomous cooling during sleep.
It supports two trigger modes:

- **Tiggy (pug)**: Sound-triggered — detects panting via audio classification
- **Leigh (human)**: Temperature-triggered — monitors body temp via Apple Watch

Both triggers feed into a shared fan control state machine that actuates a
fan via MQTT-controlled smart switch.

## System Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        RPi5 (Main Compute)                  │
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │ Audio Capture │───▶│  Panting     │───▶│              │  │
│  │ (sounddevice) │    │  Classifier  │    │              │  │
│  └──────────────┘    │  (T1: local)  │    │    Fan       │  │
│                      └──────────────┘    │    State      │  │
│  ┌──────────────┐                        │    Machine    │  │
│  │ Sensor Logger│───▶ Temp Threshold ───▶│              │  │
│  │ HTTP Receiver │                       │              │  │
│  └──────────────┘                        └──────┬───────┘  │
│                                                 │          │
│  ┌──────────────┐                               │          │
│  │  Mosquitto   │◀──────────────────────────────┘          │
│  │  MQTT Broker │                                          │
│  └──────┬───────┘                                          │
└─────────┼───────────────────────────────────────────────────┘
          │ MQTT
          ▼
   ┌──────────────┐
   │  Smart Switch │ (Sonoff S31 / Shelly Plug S)
   │  (Tasmota)   │
   └──────┬───────┘
          │ AC Power
          ▼
   ┌──────────────┐
   │     Fan      │ (blower / inline / axial — see hardware.md)
   │ on Triad     │ (Triad Orbit armature + oscillation motor)
   │ Orbit mount  │
   └──────────────┘
```

## Data Flow

1. **Audio path**: Hollyland Lark M2 TX (on [Triad Orbit](https://www.triad-orbit.com/) armature) →
   USB-C RX direct to RPi5 (UAC class-compliant, 24-bit/48kHz) →
   [SoX](https://sox.sourceforge.net/) `rec` captures and resamples to 16kHz mono.
   SoX `silence` effect gates on configurable amplitude/duration thresholds —
   only segments exceeding the threshold are serialized (dead air and ambient
   noise below threshold are discarded before Python ever sees them). Emitted
   segments are chunked into 2-3s WAV files or piped as raw audio →
   Python reads chunks as numpy arrays → librosa feature extraction
   (MFCCs, spectral centroid, RMS) → sklearn classifier → panting confidence
   score. [FFmpeg](https://ffmpeg.org/) available for format conversion as needed.

2. **Temperature path**: Apple Watch → iOS Sensor Logger app → HTTP POST to
   RPi5 receiver → parse body temp → compare against thresholds with deadband

3. **Control path**: Either trigger fires → state machine transitions →
   MQTT publish to smart switch topic → fan on/off

4. **Cooldown**: After trigger clears, configurable cooldown timer keeps fan
   running for N minutes before returning to idle

## Software Modules

```
fanbient/
├── __init__.py
├── config.py              # Pydantic settings (thresholds, MQTT, timings)
├── audio/
│   ├── __init__.py
│   ├── capture.py         # SoX/FFmpeg subprocess → chunked numpy arrays
│   └── classifier.py      # T1 spectral panting detection (librosa + sklearn)
├── control/
│   ├── __init__.py
│   └── state_machine.py   # Fan state: idle → detected → fan_on → cooldown
├── mqtt/
│   ├── __init__.py
│   └── client.py          # paho-mqtt wrapper (pub/sub, reconnect)
└── sensors/
    ├── __init__.py
    └── temperature.py     # Sensor Logger HTTP receiver + temp threshold
fanbient.py                # CLI entry point (uv shebang)
tests/                     # Unit tests (classifier, state machine, config)
```

## Classification Tiers (Incremental)

| Tier | Location | Method | Latency | Status |
|------|----------|--------|---------|--------|
| T1 | RPi5 (local) | Spectral features + sklearn | <1s | PoC target |
| T2 | Homelab LAN | Larger audio model / small LM | 1-3s | Future |
| T3 | Cloud API | Frontier LLM audio understanding | 3-10s | Future |

## Fan State Machine

```
         panting_detected              cooldown_expired
              or temp_high                  │
  ┌─────┐ ──────────────▶ ┌────────┐       │       ┌──────────┐
  │ IDLE │                 │ FAN_ON │───────┼──────▶│ COOLDOWN │
  └─────┘ ◀────────────── └────────┘       │       └──────────┘
              cooldown_expired              │            │
                                            └────────────┘
                                          trigger_during_cooldown
                                          resets timer → FAN_ON
```

States:
- **IDLE**: No trigger active, fan off
- **FAN_ON**: Trigger active, fan running
- **COOLDOWN**: Trigger cleared, fan still running for configurable duration

## Network & Failure Modes

- **Broker**: Mosquitto on RPi5 (localhost for PoC, network for multi-device)
- **Fail-safe**: Fan defaults to OFF if MQTT connection lost (fail-off)
- **Reconnect**: MQTT client auto-reconnects with exponential backoff
- **Logging**: All state transitions and detections logged for debugging

## Configuration

All thresholds, timings, and connection details are configurable via:
1. `fanbient/config.py` Pydantic models with sensible defaults
2. Environment variables (FANBIENT_* prefix)
3. Optional YAML/TOML config file override
