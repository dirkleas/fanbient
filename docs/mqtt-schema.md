# fanbient — MQTT Topic Schema

## Broker

- **Software**: Mosquitto
- **Host**: `localhost` (RPi5) for PoC; configurable for network deployments
- **Port**: 1883 (default), 8883 (TLS, future)

## Topic Naming Convention

```
fanbient/{zone}/{component}/{action}
```

- `zone`: Physical location (e.g. `bedroom`, `tiggy_bed`)
- `component`: Device or subsystem
- `action`: Command or status

## Core Topics

### Fan Control
| Topic | Direction | Payload | Description |
|-------|-----------|---------|-------------|
| `fanbient/{zone}/fan/command` | Publish → switch | `ON` / `OFF` | Command fan on/off |
| `fanbient/{zone}/fan/state` | Subscribe ← switch | `ON` / `OFF` | Confirmed fan state |
| `fanbient/{zone}/fan/speed` | Publish → switch | `0`-`100` | PWM speed (future) |

### Audio Detection
| Topic | Direction | Payload | Description |
|-------|-----------|---------|-------------|
| `fanbient/{zone}/audio/panting` | Publish | JSON (see below) | Panting detection event |
| `fanbient/{zone}/audio/level` | Publish | `{"rms": 0.05}` | Audio RMS level (debug) |

#### Panting Detection Payload
```json
{
  "detected": true,
  "confidence": 0.87,
  "tier": "T1",
  "timestamp": "2026-03-03T02:15:30Z"
}
```

### Temperature Sensing
| Topic | Direction | Payload | Description |
|-------|-----------|---------|-------------|
| `fanbient/{zone}/temp/reading` | Publish | JSON (see below) | Temperature reading |
| `fanbient/{zone}/temp/alert` | Publish | JSON | Threshold exceeded |

#### Temperature Reading Payload
```json
{
  "temp_f": 98.8,
  "source": "apple_watch",
  "timestamp": "2026-03-03T02:15:30Z"
}
```

### State Machine
| Topic | Direction | Payload | Description |
|-------|-----------|---------|-------------|
| `fanbient/{zone}/state` | Publish | `idle` / `fan_on` / `cooldown` | Current state |
| `fanbient/{zone}/trigger` | Publish | `panting` / `temperature` / `manual` | Active trigger |

### System
| Topic | Direction | Payload | Description |
|-------|-----------|---------|-------------|
| `fanbient/system/status` | Publish | `online` / `offline` | System heartbeat |
| `fanbient/system/config` | Publish | JSON | Current config snapshot |

## Tasmota Smart Switch Integration

For Sonoff S31 / Shelly with Tasmota firmware:

- Command topic: `cmnd/{device_name}/POWER`
- State topic: `stat/{device_name}/POWER`
- Telemetry: `tele/{device_name}/STATE`

The MQTT client bridges fanbient topics to Tasmota topics:
- `fanbient/{zone}/fan/command` → `cmnd/{device_name}/POWER`
- `stat/{device_name}/POWER` → `fanbient/{zone}/fan/state`

## QoS Levels

| Topic Pattern | QoS | Rationale |
|---------------|-----|-----------|
| `*/command` | 1 | At-least-once for actuation commands |
| `*/state` | 1 | At-least-once for state confirmations |
| `*/audio/*` | 0 | Fire-and-forget for high-frequency data |
| `*/temp/*` | 0 | Fire-and-forget, readings are periodic |
| `system/*` | 1 | Reliable system status |

## Retained Messages

- `fanbient/{zone}/fan/state` — retained, so new subscribers get current state
- `fanbient/{zone}/state` — retained
- `fanbient/system/status` — retained (with LWT for offline detection)

## Last Will & Testament (LWT)

- Topic: `fanbient/system/status`
- Payload: `offline`
- QoS: 1
- Retained: true
