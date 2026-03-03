# fanbient - Project Roadmap Plan

## Context

fanbient is an ambient smart fan system for autonomous cooling during sleep.
Two personas: Tiggy (pug, sound-triggered) and Leigh (wife, temp-triggered).
The project is freshly scaffolded (Python 3.12 + uv) with no implementation yet.

This plan establishes a phased roadmap starting with the Tiggy sound/panting
PoC, followed by Leigh's temperature trigger, then extensions.

## Key Decisions (from seed audit)

| Decision | Choice |
|----------|--------|
| Planning approach | Phased roadmap |
| First PoC target | Tiggy (sound/panting detection) |
| Temp sensor (Leigh) | Apple Watch + Sensor Logger |
| Audio classification | Tiered: simple classifier → homelab LM → cloud frontier LLM |
| Fan actuation | Smart switch via MQTT |

## Open Questions (to resolve in Phase 0)

- MQTT broker location (RPi5? homelab? dedicated?)
- Network topology and failure mode (fail-on vs fail-off)
- Hysteresis/cooldown timing after panting stops
- Wireless mic kit choice (DJI vs Hollyland) and audio capture pipeline
- Smart switch selection (Tasmota/ESPHome flashed vs commercial MQTT-native)
- Physical safety considerations for fan near sleeping dog

---

## Preliminary BOM

### Core Compute & Control
| Component | Example | Est. Cost | Notes |
|-----------|---------|-----------|-------|
| SBC | Raspberry Pi 5 (4GB or 8GB) | $60-80 | Main compute, MQTT broker, audio processing |
| Microcontroller | M5Stack Core2 or AtomS3 | $20-50 | Optional local sensor hub, display, or relay control |
| MicroSD card | 64GB A2 class | $10 | RPi5 boot/storage |
| Power supply (RPi) | Official RPi5 27W USB-C PSU | $12 | |

### Audio Capture
| Component | Example | Est. Cost | Notes |
|-----------|---------|-----------|-------|
| Wireless mic kit | Hollyland Lark M2 or DJI Mic 2 | $150-300 | Clip-on TX near Tiggy's bed, RX to RPi |
| USB audio interface | Budget USB DAC (e.g. Sabrent) | $8-15 | RX 3.5mm → USB for RPi input |
| _Alt: USB mic_ | _Cheap USB condenser_ | _$15-30_ | _Simpler but wired, shorter range_ |

### Fan & Actuation
| Component | Example | Est. Cost | Notes |
|-----------|---------|-----------|-------|
| Fan | Noctua NF-A14 (140mm) or NF-A20 (200mm) | $25-35 | Quiet, PWM-capable, 12V |
| Smart plug (MQTT) | Sonoff S31 (Tasmota flashed) or Shelly Plug S | $12-20 | MQTT-native or flashable; controls fan power |
| _Alt: PWM fan control_ | _M5Stack relay/MOSFET + 12V PSU_ | _$15-25_ | _Variable speed vs on/off; more wiring_ |
| 12V DC PSU | Barrel jack PSU for PC fan | $8-12 | Only if not using smart plug AC fan |

### Networking & MQTT
| Component | Example | Est. Cost | Notes |
|-----------|---------|-----------|-------|
| MQTT broker | Mosquitto (software, on RPi5) | $0 | Runs on RPi5 |
| WiFi | Built-in RPi5 WiFi | $0 | Or Ethernet if near router |

### Temperature Sensing (Phase 2)
| Component | Example | Est. Cost | Notes |
|-----------|---------|-----------|-------|
| Apple Watch | Already owned | $0 | Wrist temp during sleep |
| iOS Sensor Logger | App (free/paid) | $0-5 | Exports sensor data via HTTP/push |

### Optional / Extensions
| Component | Example | Est. Cost | Notes |
|-----------|---------|-----------|-------|
| Articulating arm | Monitor arm or gooseneck clamp | $15-30 | Fan positioning |
| LED strip | WS2812B or similar | $10 | Ambient lighting via MQTT |
| Aroma diffuser | USB mini diffuser | $15 | MQTT-switched |
| Ambient speaker | Bluetooth mini speaker | $15-25 | Sleep sounds |

### Estimated PoC Cost (Phase 1 only)
- **Minimal** (USB mic + smart plug + RPi5 + PC fan): ~$115-155
- **Full wireless** (wireless mic kit + smart plug + RPi5 + PC fan): ~$265-440

---

## Phase 0: Architecture & Decisions

**Goal:** Lock down hardware choices, network topology, and software architecture.

### Deliverables
1. **Architecture diagram** — components, data flow, MQTT topics
2. **Hardware BOM** — finalized component list with purchase links
3. **MQTT topic schema** — naming conventions, payload formats
4. **Software architecture** — module structure, dependency choices
5. **Hysteresis/control logic spec** — thresholds, timings, deadbands

### Key files to create
- `docs/architecture.md` — system design
- `docs/hardware.md` — BOM and wiring
- `docs/mqtt-schema.md` — topic definitions

---

## Phase 1: Tiggy Sound Trigger PoC

**Goal:** Detect pug panting from audio → actuate fan via MQTT smart switch.

### 1a. Audio Capture Pipeline
- Wireless mic → RPi5 audio input (USB/line-in)
- Continuous audio stream capture (PyAudio or sounddevice)
- Chunked processing (e.g. 2-3 second windows)

### 1b. Panting Detection — Tiered Classification
Three tiers, build bottom-up:

| Tier | Where | Approach | Latency | Notes |
|------|-------|----------|---------|-------|
| T1 (local) | RPi5 | Spectral analysis (librosa) — breath rate, frequency bands | <1s | Always-on, first pass |
| T2 (homelab) | LAN server | Larger audio classifier or small LM | 1-3s | Fallback/confirmation |
| T3 (cloud) | Cloud API | Frontier LLM with audio understanding | 3-10s | High-confidence override, edge cases |

**PoC starts with T1 only.** T2/T3 added incrementally.

T1 approach:
- Panting has distinct spectral signature: rhythmic, 1-3 Hz breath rate, broadband noise bursts
- Use librosa for spectral feature extraction (MFCCs, spectral centroid, RMS energy)
- Simple threshold or lightweight sklearn classifier (SVM/RandomForest)
- Training data: record Tiggy panting vs ambient/silence/other sounds

### 1c. Fan Actuation
- MQTT publish on panting detection → smart switch toggles fan
- Configurable cooldown timer (fan stays on N minutes after last panting detected)
- State tracking: `idle` → `panting_detected` → `fan_on` → `cooldown` → `idle`

### 1d. Monitoring & Logging
- Log all detections, actuations, and state transitions
- Simple dashboard or terminal output for debugging

### Key files to create/modify
- `fanbient/audio/capture.py` — audio stream capture
- `fanbient/audio/classifier.py` — panting detection (T1)
- `fanbient/control/state_machine.py` — fan state management
- `fanbient/mqtt/client.py` — MQTT publish/subscribe
- `fanbient/config.py` — thresholds, timings, MQTT settings
- `fanbient.py` — CLI entry point (uv shebang)
- `tests/` — unit tests for classifier and state machine

### Dependencies to add
- `sounddevice` or `pyaudio` — audio capture
- `librosa` — audio feature extraction
- `numpy` — array ops
- `scikit-learn` — simple classifier
- `paho-mqtt` — MQTT client
- `pydantic` or `dataclasses` — config/models

---

## Phase 2: Leigh Temperature Trigger

**Goal:** Apple Watch body temp → fan actuation via MQTT.

### 2a. Sensor Logger Integration
- iOS Sensor Logger app exports via HTTP/WebSocket/file
- Bridge to MQTT (Python service or Node-RED)
- Parse body temperature readings

### 2b. Temperature Control Logic
- Configurable temp thresholds with deadband (e.g. on at 98.8F, off at 98.2F)
- Same state machine pattern as Phase 1, different trigger
- Merge with Tiggy trigger (either trigger can activate fan)

### Key files
- `fanbient/sensors/temperature.py` — Sensor Logger integration
- `fanbient/control/state_machine.py` — extend with temp trigger

---

## Phase 3: Extensions (Future)

- Temporal scheduling (time-based rules, sleep schedule awareness)
- Aromatherapy, lighting, ambient sound via MQTT
- Articulating armature for positioning
- T2/T3 audio classification tiers
- Auto-positioning and stow-away
- Multi-room support

---

## Verification Plan

### Phase 0
- Review architecture docs for completeness and consistency

### Phase 1
- **Audio capture:** Record test clips, verify chunked processing pipeline
- **Classifier:** Train on Tiggy panting samples, measure precision/recall on held-out set
- **MQTT:** Verify pub/sub with mosquitto_sub/pub CLI tools
- **Integration:** End-to-end test: play panting audio → verify fan switch toggles
- **Cooldown:** Verify fan stays on during cooldown, turns off after timeout

### Phase 2
- **Sensor Logger:** Verify temp data flows from Apple Watch → MQTT
- **Threshold logic:** Unit test deadband behavior
- **Integration:** Simulate temp changes → verify fan actuation

---

## Immediate Next Steps

1. Start Phase 0 — make architecture decisions, draw data flow
2. Order/source hardware if not already available
3. Set up MQTT broker (Mosquitto on RPi5 is simplest start)
4. Record Tiggy panting audio samples for classifier training data
5. Scaffold Phase 1 module structure
