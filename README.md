# fanbient — ambient smart fan++

Autonomous smart fan system for cooling during sleep. Detects when cooling is
needed via audio analysis or body temperature, then actuates a fan through
MQTT-controlled smart switches — all fully automated with optional manual
override.

## How It Works

Two trigger modes feed a shared fan control state machine:

- **Sound trigger** — wireless mic ([Hollyland Lark M2](https://www.hollyland.com/product/lark-m2) or [DJI Mic 2](https://store.dji.com/product/dji-mic-2)) near the dog's bed captures audio; spectral
  analysis detects panting and turns the fan on automatically
- **Temperature trigger** — [Apple Watch](https://www.apple.com/apple-watch/) body temp (via [Sensor Logger](https://apps.apple.com/app/sensor-logger/id1531582925)) or a
  thermal imaging camera detects elevated temperature and triggers the fan

When the trigger clears, the fan enters a configurable cooldown period before
shutting off. Multiple triggers can be active simultaneously — the fan stays on
until all triggers clear.

## Quick Start

```bash
# install and run directly from github (no clone needed)
uvx --from git+https://github.com/dirkleas/fanbient fanbient run --dry-run

# or clone and run locally
git clone https://github.com/dirkleas/fanbient.git
cd fanbient
uv sync
./fanbient.py run --dry-run
```

## CLI

```
fanbient run      # start the fan controller
fanbient train    # train panting classifier from labeled audio
fanbient status   # show current state via MQTT
fanbient serve    # start the FastAPI REST server
```

Key options for `run`:

| Flag | Description |
|------|-------------|
| `--dry-run` / `-n` | Run without MQTT actuation |
| `--model` / `-m` | Path to trained classifier `.pkl` |
| `--temp` / `-t` | Enable Apple Watch temperature sensing |
| `--thermal` | Enable thermal camera temperature sensing |
| `--cooldown` / `-c` | Seconds fan stays on after trigger clears (default 300) |
| `--zone` / `-z` | MQTT zone name (default `bedroom`) |
| `--mqtt-host` | MQTT broker host (default `localhost`) |

## REST API

Start with `fanbient serve` then hit endpoints:

```
GET  /status           # current service state
POST /start            # start the service
POST /stop             # stop the service
POST /fan              # manual fan on/off  {"on": true}
POST /trigger          # fire a trigger     {"trigger_type": "panting"}
POST /trigger/clear    # clear a trigger
POST /temperature      # push a temp reading {"temp_f": 99.1}
```

## Training the Classifier

Record audio samples into a directory structure:

```
training_data/
  panting/       # .wav files of panting
  not_panting/   # .wav files of ambient/silence/other
```

Then train:

```bash
fanbient train training_data/ --output model.pkl
fanbient run --model model.pkl
```

Without a trained model, a heuristic detector based on spectral features
(RMS energy, tempo, zero-crossing rate) is used as a fallback.

## Architecture

```
fanbient/
  service.py          # core service layer (protocol-agnostic)
  config.py           # pydantic settings (env vars: FANBIENT_*)
  api.py              # FastAPI REST wrapper
  audio/
    capture.py        # SoX/FFmpeg subprocess → chunked numpy arrays
    classifier.py     # T1 panting detection (librosa + sklearn)
  control/
    state_machine.py  # IDLE → FAN_ON → COOLDOWN
  mqtt/
    client.py         # paho-mqtt with Tasmota bridging
  sensors/
    temperature.py    # Sensor Logger HTTP + thermal camera
fanbient.py           # typer CLI entry point (uv shebang)
```

The core service layer in `service.py` is decoupled from any transport —
it can be driven by the CLI, FastAPI, MCP, or MQTT commands.

## Hardware

Minimal PoC (~$115-155): [RPi5](https://www.raspberrypi.com/products/raspberry-pi-5/) + USB mic + smart plug + fan

Supports AC or battery power — [Milwaukee M18](https://www.milwaukeetool.com/products/48-11-1850)
batteries via dock adapter for portable deployment, or USB-C PD power banks.

See [docs/hardware.md](docs/hardware.md) for the full BOM including wireless
mic kits, thermal cameras, battery power options, extension components, and a
[fan design rationale](docs/hardware.md#fan-design-rationale) comparing axial
PC fans, DC centrifugal blowers, inline duct fans, and mini air movers — with
CFM targets for each persona and directional actuation via oscillation motors
or servo pan-tilt.

## Configuration

All settings are configurable via environment variables with `FANBIENT_` prefix
or through the Pydantic config classes. See [docs/architecture.md](docs/architecture.md)
for details.

MQTT topic schema is documented in [docs/mqtt-schema.md](docs/mqtt-schema.md).

## Future Opportunities

- **Tiered classification** — escalate from local spectral analysis (T1) to
  homelab LM (T2) to cloud frontier LLM (T3) for edge cases
- **Temporal scheduling** — time-based rules and sleep schedule awareness
- **Ambient extensions** — aromatherapy, lighting, sleep sounds via MQTT
- **[Triad Orbit](https://www.triad-orbit.com/) armatures** — modular adjustable stands, booms, and adapters for fan/mic/sensor positioning with auto-stow potential
- **Directional actuation** — oscillation motors or servo pan-tilt for automated fan sweep between zones
- **Multi-room support** — zone-based fan control across rooms
- **PWM speed control** — variable fan speed instead of on/off

## Docs

- [Architecture](docs/architecture.md) — system design and data flow
- [Hardware BOM](docs/hardware.md) — components, wiring, thermal camera options
- [MQTT Schema](docs/mqtt-schema.md) — topic naming, payloads, QoS
- [Seed Thoughts](SEEDS.md) — original brainstorming notes
- Gemini Preliminary [Audit](gemini_audit.md) ([plan](gemini_audit_plan.md))
