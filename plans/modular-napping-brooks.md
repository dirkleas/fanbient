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
| SBC | [Raspberry Pi 5 (4GB or 8GB)](https://www.raspberrypi.com/products/raspberry-pi-5/) | $60-80 | Main compute, MQTT broker, audio processing |
| Microcontroller | [M5Stack Core2](https://shop.m5stack.com/products/m5stack-core2-esp32-iot-development-kit) or [AtomS3](https://shop.m5stack.com/products/atoms3) | $20-50 | Optional local sensor hub, display, or relay control |
| MicroSD card | 64GB A2 class | $10 | RPi5 boot/storage |
| Power supply (RPi) | [Official RPi5 27W USB-C PSU](https://www.raspberrypi.com/products/27w-power-supply/) | $12 | |

### Audio Capture
| Component | Example | Est. Cost | Notes |
|-----------|---------|-----------|-------|
| Wireless mic kit | [Hollyland Lark M2 (USB-C)](https://www.hollyland.com/product/lark-m2) | $150-200 | TX clips near Tiggy's bed; USB-C RX plugs directly into RPi5 (UAC, 24-bit/48kHz — no audio interface needed); mount via [Triad Orbit](https://www.triad-orbit.com/) armature |
| _Alt: Wireless mic_ | _[DJI Mic 2](https://store.dji.com/product/dji-mic-2)_ | _$200-300_ | _USB-C RX option also available_ |
| _Alt: USB mic_ | _Cheap USB condenser_ | _$15-30_ | _Simpler but wired, shorter range_ |

### Fan & Actuation
| Component | Example | Est. Cost | Notes |
|-----------|---------|-----------|-------|
| Fan | Multiple types — see [hardware.md fan rationale](../docs/hardware.md#fan-design-rationale) | $15-65 | Axial, centrifugal blower, inline duct, or air mover; mount via [Triad Orbit](https://www.triad-orbit.com/) armature |
| Smart plug (MQTT) | [Sonoff S31 (Tasmota)](https://sonoff.tech/product/smart-plugs/s31/) or [Shelly Plug S](https://www.shelly.com/en-us/products/shop/shelly-plus-plug-s-1) | $12-20 | MQTT-native or flashable; controls fan power |
| _Alt: PWM fan control_ | _[M5Stack](https://shop.m5stack.com/) relay/MOSFET + 12V PSU_ | _$15-25_ | _Variable speed vs on/off; more wiring_ |
| 12V DC PSU | Barrel jack PSU for PC fan | $8-12 | Only if not using smart plug AC fan |
| _Alt: Battery power_ | _[Milwaukee M18](https://www.milwaukeetool.com/products/48-11-1850) + [dock adapter](https://www.amazon.com/Milwaukee-Connector-Building-projects-Robotics/dp/B08KNN4T3M) + 18V→12V step-down_ | _$25-35_ | _Portable; hot-swap batteries for overnight runtime_ |
| _Alt: USB-C PD bank_ | _65W+ USB-C PD power bank (e.g. [Anker](https://www.anker.com/collections/portable-chargers))_ | _$30-60_ | _RPi5-only portable power; ~3-5 hrs_ |

### Networking & MQTT
| Component | Example | Est. Cost | Notes |
|-----------|---------|-----------|-------|
| MQTT broker | Mosquitto (software, on RPi5) | $0 | Runs on RPi5 |
| WiFi | Built-in RPi5 WiFi | $0 | Or Ethernet if near router |

### Temperature Sensing (Phase 2)
| Component | Example | Est. Cost | Notes |
|-----------|---------|-----------|-------|
| Apple Watch | [Apple Watch](https://www.apple.com/apple-watch/) (already owned) | $0 | Wrist temp during sleep |
| iOS Sensor Logger | [Sensor Logger](https://apps.apple.com/app/sensor-logger/id1531582925) (free/paid) | $0-5 | Exports sensor data via HTTP/push |

### Optional / Extensions
| Component | Example | Est. Cost | Notes |
|-----------|---------|-----------|-------|
| Positioning armature | [Triad Orbit](https://www.triad-orbit.com/) stands, booms, adapters | $80-200 | Modular mounting for fan, mic, sensors |
| Directional actuation | Oscillation motor or servo pan-tilt — see [hardware.md](../docs/hardware.md#directional-actuation) | $5-50 | Automated fan sweep between Tiggy/Leigh zones |
| LED strip | [WS2812B (Adafruit NeoPixel)](https://www.adafruit.com/category/168) | $10 | Ambient lighting via MQTT |
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
- Hollyland Lark M2 TX → USB-C RX plugged directly into RPi5 (UAC class-compliant, no audio interface needed)
- [SoX](https://sox.sourceforge.net/) `rec` captures from USB audio device; `silence` effect gates on
  configurable amplitude/duration threshold — only serializes segments with
  actual sound activity (dead air never reaches Python); resamples 48kHz → 16kHz mono
- [FFmpeg](https://ffmpeg.org/) for format conversion if needed (e.g. training data normalization)
- Python subprocess reads threshold-gated chunks as numpy arrays for classifier
- Chunked processing (e.g. 2-3 second windows of above-threshold audio)

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
- `sox` / `ffmpeg` — system packages for audio capture, resample, format conversion
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
- [Triad Orbit](https://www.triad-orbit.com/) modular armatures for positioning
- Directional actuation — oscillation motors or servo pan-tilt for fan sweep
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
