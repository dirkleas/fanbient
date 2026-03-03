# fanbient — Hardware BOM & Wiring

## PoC Hardware (Phase 1)

### Core Compute
| Component | Model | Est. Cost | Notes |
|-----------|-------|-----------|-------|
| SBC | [Raspberry Pi 5 (4GB+)](https://www.raspberrypi.com/products/raspberry-pi-5/) | $60-80 | Main compute, MQTT broker, audio processing |
| MicroSD | 64GB A2 class | $10 | Boot/storage |
| Power supply | [Official RPi5 27W USB-C](https://www.raspberrypi.com/products/27w-power-supply/) | $12 | |

### Audio Capture
| Component | Model | Est. Cost | Notes |
|-----------|-------|-----------|-------|
| Wireless mic kit | [Hollyland Lark M2 (USB-C)](https://www.hollyland.com/product/lark-m2) | $150-200 | TX clips near Tiggy's bed; USB-C RX plugs directly into RPi5 — UAC class-compliant, 24-bit/48kHz, no audio interface needed |
| _Alt: Wireless mic_ | _[DJI Mic 2](https://store.dji.com/product/dji-mic-2)_ | _$200-300_ | _USB-C RX option also available_ |
| _Alt: USB mic_ | _Budget USB condenser_ | _$15-30_ | _Simpler, wired, shorter range_ |
| Audio tooling | [SoX](https://sox.sourceforge.net/) + [FFmpeg](https://ffmpeg.org/) (system packages) | $0 | `rec` captures from USB audio; `silence` effect gates on configurable amplitude/duration threshold — only emits audio segments with actual sound activity; `sox` resamples/chunks; `ffmpeg` for format conversion; Python subprocess reads serialized segments as numpy arrays for classifier |

### Fan & Actuation
| Component | Model | Est. Cost | Notes |
|-----------|-------|-----------|-------|
| Fan | See [Fan Design Rationale](#fan-design-rationale) | $15-65 | Multiple fan types evaluated below |
| Smart plug | [Sonoff S31 (Tasmota)](https://sonoff.tech/product/smart-plugs/s31/) or [Shelly Plug S](https://www.shelly.com/en-us/products/shop/shelly-plus-plug-s-1) | $12-20 | MQTT-native or flashable |
| Oscillation motor | See [Directional Actuation](#directional-actuation) | $5-15 | Sweep/oscillation for coverage |
| _Alt: PWM control_ | _[M5Stack](https://shop.m5stack.com/) relay/MOSFET + 12V PSU_ | _$15-25_ | _Variable speed_ |

### Positioning — Triad Orbit Armatures
| Component | Model | Est. Cost | Notes |
|-----------|-------|-----------|-------|
| Tripod stand | [Triad Orbit T2 Short](https://www.triad-orbit.com/t2/) or [T3 Tall](https://www.triad-orbit.com/t3/) | $80-130 | Floor stand base for fan or mic |
| Orbital boom | [Triad Orbit O2](https://www.triad-orbit.com/o2/) | $90-110 | Adjustable boom arm for directional positioning |
| Micro orbital | [Triad Orbit IO-VM](https://www.triad-orbit.com/io-vm/) | $30-40 | Compact orbital head for fine-angle adjustment |
| Desk clamp | [Triad Orbit IO-Desk](https://www.triad-orbit.com/io-desk/) | $40-50 | Clamp mount for nightstand or shelf |
| Adapter | [Triad Orbit IO-R Retrofit](https://www.triad-orbit.com/io-r/) | $20-30 | Adapts standard 5/8" threads to Triad Orbit IO system |

All positional components (mic, fan, thermal camera) deploy via [Triad Orbit](https://www.triad-orbit.com/) modular armatures — providing repeatable, vibration-isolated, tool-free adjustment. Mix and match stands, booms, and adapters for each deployment scenario.

### Battery Power
| Component | Model | Est. Cost | Notes |
|-----------|-------|-----------|-------|
| USB-C PD power bank | 65W+ USB-C PD, 20000mAh+ (e.g. [Anker](https://www.anker.com/collections/portable-chargers)) | $30-60 | Powers RPi5 via USB-C PD; ~3-5 hrs runtime at 27W |
| _Alt: USB-C PD power bank_ | _100W USB-C PD, 25000mAh+_ | _$50-80_ | _Longer runtime, can power RPi5 + USB peripherals_ |
| M18 battery adapter | [Milwaukee M18 dock adapter + 12AWG harness](https://www.amazon.com/Milwaukee-Connector-Building-projects-Robotics/dp/B08KNN4T3M) | $12-20 | Snap-on dock mount with fused 12AWG leads; quick battery swap |
| M18 → 12V step-down | [M18 18V-to-12V buck converter](https://www.daierswitches.com/products/milwaukee-m18-power-wheel-battery-adapter) | $10-15 | 20A max output; powers 12V fans, blowers directly |
| M18 → 5V USB-C | M18 USB-C adapter or buck converter to 5V/5A | $10-15 | Powers RPi5 from M18 battery |

[Milwaukee M18 REDLITHIUM](https://www.milwaukeetool.com/products/48-11-1850) batteries provide substantial portable power with tool-free hot-swap convenience. Runtime estimates at 12V fan load (~10-20W):

| M18 Battery | Capacity | Wh | Est. Runtime (12V/15W fan) | Est. Runtime (RPi5 + fan) |
|-------------|----------|-----|---------------------------|--------------------------|
| CP 2.0 Ah | 2.0 Ah | 36 Wh | ~2 hrs | ~1 hr |
| XC 5.0 Ah | 5.0 Ah | 90 Wh | ~5 hrs | ~2.5 hrs |
| HD 6.0 Ah | 6.0 Ah | 108 Wh | ~6 hrs | ~3 hrs |
| HO 8.0 Ah | 8.0 Ah | 144 Wh | ~8 hrs | ~4 hrs |
| FORGE 12.0 Ah | 12.0 Ah | 216 Wh | ~12 hrs | ~6 hrs |

The M18 dock adapter mounts to the Triad Orbit armature base or stand, keeping
the battery accessible for swap-outs. With multiple M18 batteries on hand,
continuous overnight operation is practical — swap a fresh battery without
powering down (use a small capacitor/UPS bridge for uninterrupted RPi5 operation).

USB-C PD power banks are simpler for RPi5-only power (no fan), while M18
batteries excel at powering the full system (RPi5 + 12V fan + peripherals)
from a single source via a wiring harness with buck converters for each
voltage rail.

### Estimated PoC Cost
- **Minimal** (USB mic + smart plug + RPi5 + blower fan): ~$105-145
- **Full wireless** (Lark M2 USB-C + smart plug + RPi5 + blower fan + Triad Orbit armature): ~$355-570
- **Battery-powered** (add M18 adapter + step-down to above): +$25-35

---

## Fan Design Rationale

### CFM Requirements

Appropriate airflow depends on the target, distance, and whether the goal is
gentle cooling or active heat dissipation. These are approximate targets for
a directed fan mounted on an armature 3-6 ft from the sleeping subject:

| Persona | Scenario | Target CFM | Notes |
|---------|----------|------------|-------|
| **Tiggy** (pug, ~15 lb) | Spot cooling from 3-4 ft | 30-60 CFM | Gentle, focused airflow; avoid startling |
| **Leigh** (human, sleeping) | Upper-body cooling from 4-6 ft | 80-150 CFM | Broader coverage, light breeze feel |
| **Both** (shared zone) | Oscillating sweep | 100-200 CFM | Directional actuator distributes airflow |

For context: a comfortable light breeze is ~1-3 mph at the skin (~50-100 CFM
from a directed source at 4 ft). Higher CFM fans can always be PWM-throttled
down, but a fan that's too weak at full speed can't be made stronger.

### Fan Types Compared

The project originated with PC axial fans (Noctua) as the obvious COTS choice.
However, centrifugal blowers and mixed-flow inline fans — the same
design families used in HVAC ducting, commercial carpet dryers, and air movers
— achieve comparable or higher CFM in significantly more compact, lighter
form factors. Their turbine/squirrel-cage impeller design produces higher
static pressure, meaning the airstream stays coherent over longer throw
distances — ideal for directed cooling from an armature.

#### T1: Axial Fans (PC-style)
| Model | CFM | Noise | Size | Power | Est. Cost | Notes |
|-------|-----|-------|------|-------|-----------|-------|
| [Noctua NF-A14 PWM](https://noctua.at/en/nf-a14-pwm) | 82 CFM | 24.6 dBA | 140mm sq × 25mm | 12V, 1.56W | $25 | Gold standard quiet PC fan |
| [Noctua NF-A20 PWM](https://noctua.at/en/nf-a20-pwm) | 86 CFM | 18.1 dBA | 200mm sq × 30mm | 12V, 2.16W | $35 | Larger, quieter, gentle breeze |

Pros: Extremely quiet, PWM-controllable, well-documented, easy to mount.
Cons: Low static pressure — airstream disperses quickly over distance. At
3-4 ft throw, effective delivered CFM drops significantly. Large flat form
factor for the airflow produced.

#### T2: DC Centrifugal Blowers (Radial/Squirrel-Cage)
| Model | CFM | Noise | Size | Power | Est. Cost | Notes |
|-------|-----|-------|------|-------|-----------|-------|
| [Delta BFB1012L](https://www.delta-fan.com/products/BFB1012L-A.html) | 23 CFM | ~35 dBA | 97 × 95 × 33mm | 12V, 4.4W | $15-20 | Quiet, compact radial blower |
| [Delta BFB1012M](https://www.delta-fan.com/products/BFB1012M-A.html) | 27 CFM | ~42 dBA | 97 × 95 × 33mm | 12V, 6.6W | $15-20 | Mid-speed, good Tiggy option |
| [Delta BFB1012VH](https://www.delta-fan.com/products/BFB1012VH-A.html) | 38 CFM | ~52 dBA | 97 × 95 × 33mm | 12V, 18W | $15-25 | High airflow in tiny package |
| [Sanyo Denki 9BMB12P2F01](https://products.sanyodenki.com/en/sanace/dc/blower/) | 37 CFM | — | 97 × 33mm | 12V, 10.8W | $20-30 | San Ace blower, industrial quality |
| [Sanyo Denki 9BMB12P2G01](https://products.sanyodenki.com/en/sanace/dc/blower/) | 47 CFM | — | 97 × 33mm | 12V, 21.6W | $25-35 | Higher CFM San Ace variant |

Pros: **Dramatically smaller** than axial fans at equivalent CFM. High static
pressure produces a focused, coherent airstream that holds together over
distance. 90-degree exhaust angle suits duct or nozzle attachments. 12V DC
runs from same PSU as Noctua. Easily ganged (2-3 units) for higher CFM.
Cons: Noisier per-CFM than Noctua axial at close range. May need a 3D-printed
nozzle/shroud for best directional performance.

#### T3: Mixed-Flow Inline Duct Fans
| Model | CFM | Noise | Size | Power | Est. Cost | Notes |
|-------|-----|-------|------|-------|-----------|-------|
| [AC Infinity RAXIAL S4](https://acinfinity.com/hydroponics-growers/booster-duct-fans/raxial-s4-inline-booster-duct-fan-with-speed-controller-4-inch/) | 106 CFM | 28 dBA | 4" duct | 110V AC | $25-30 | Quiet, speed controller included |
| [AC Infinity CLOUDLINE S4](https://www.amazon.com/dp/B07PLCQPKN) | 205 CFM | 28 dBA | 4" duct | 110V AC | $40-50 | EC motor, 10-speed, excellent for Leigh |
| [iPower 4" Inline](https://www.amazon.com/iPower-Silent-90CFM-Booster-Quiet/dp/B091T8DLB9) | 100 CFM | 30 dBA | 4" duct | 110V AC | $20-25 | Budget option, solid performer |
| [TerraBloom 4" Silent](https://www.amazon.com/Silent-Booster-Efficient-Circulation-Ducting/dp/B075333HWM) | 47 CFM | ~25 dBA | 4" duct | 110V AC | $20-25 | Ultra-quiet, lower CFM |

Pros: Best noise-to-CFM ratio. Mixed-flow impeller combines axial throughput
with centrifugal pressure. Designed for continuous quiet operation. Can attach
a short duct section + nozzle for highly directed throw. 4" form factor is
very compact for 100-200 CFM output.
Cons: AC-powered (uses smart plug, no PWM — on/off via MQTT or multi-speed
controller). Round duct form factor needs adapter for armature mounting.

#### T4: Mini Air Movers (Carpet Dryer Style)
| Model | CFM | Noise | Size | Weight | Est. Cost | Notes |
|-------|-----|-------|------|--------|-----------|-------|
| [XPOWER P-80A](https://xpower.com/shop/xpower-p-80a-mighty-air-mover/) | 600 CFM | ~55 dBA | 11.5 × 9.3 × 12.3" | 7.9 lb | $65 | 3-speed, 4 positions, stackable |
| [BlueDri Mini Storm](https://www.amazon.com/BlueDri-Storm-Mover-Carpet-Blower/dp/B007TC55N4) | ~500 CFM | ~55 dBA | compact | 6 lb | $55 | Lightest option |

Pros: Massive CFM in a compact, self-contained package. Multiple angle
positions built in. Robust — designed for 24/7 commercial use.
Cons: Overkill for this project at full speed. Noisier than other options.
AC-powered, on/off only. Heavier — less suited to armature mounting. Best as
a floor-standing option for extreme heat scenarios.

### Recommended Configurations

| Scenario | Fan Choice | Why |
|----------|-----------|-----|
| **Tiggy PoC** (quiet, close range) | Noctua NF-A14 or Delta BFB1012M | Quiet, 12V, 27-82 CFM, armature-friendly |
| **Leigh** (broader coverage) | AC Infinity CLOUDLINE S4 or RAXIAL S4 | 106-205 CFM at 28 dBA, via smart plug |
| **Both / oscillating** | 2× Delta BFB1012M ganged + oscillation motor | Compact, 54 CFM combined, directional sweep |
| **Maximum cooling** | XPOWER P-80A on floor | 600 CFM, floor-standing, heat emergency |

### Directional Actuation

Standard consumer fans achieve sweep coverage via a geared synchronous
oscillation motor — the same mechanism can be applied to any fan mounted on a
Triad Orbit armature. A small oscillation motor drives a crank arm that
converts continuous rotation into a back-and-forth sweep arc.

| Component | Model | Est. Cost | Notes |
|-----------|-------|-----------|-------|
| Oscillation motor | [AC synchronous gear motor 5-6 RPM](https://www.amazon.com/Mxfans-Electric-Synchronous-5-6RPM-Oscillating/dp/B07GFC6644) | $8-12 | 12V AC, CW/CCW, 4W, 7mm shaft; same type used in pedestal/tower fans |
| Oscillation gearbox | [Fan oscillation gear mechanism](https://www.amazon.com/Gadpiparty-Oscillation-Operation-Replacement-Lightweight/dp/B0F5P4HGZB) | $5-10 | ABS housing, quiet operation, drop-in sweep mechanism |
| _Alt: Servo sweep_ | [ServoCity SPT200 pan-tilt kit](https://www.servocity.com/pan-tilt-kits/) + servo | $30-50 | Programmable pan/tilt, 2 lb payload, RPi-controlled via GPIO PWM |
| _Alt: Micro pan-tilt_ | [Adafruit Mini Pan-Tilt Kit](https://www.adafruit.com/product/1967) | $25 | Micro servos, lightweight loads, I2C/PWM from RPi |

**Oscillation motor** is the simplest and cheapest option — it replicates
exactly how a consumer pedestal fan oscillates, just applied to an
armature-mounted blower. Mount the motor to the Triad Orbit IO head; fan
attaches to the output shaft and sweeps automatically.

**Servo pan-tilt** is programmable — the RPi can control sweep arc, speed,
and dwell angle via GPIO, and can target specific zones (e.g., point at Tiggy
for 30s, sweep to Leigh for 30s). Higher cost and complexity but enables
software-defined directional control via MQTT commands.

---

## Phase 2 Additions

### Temperature Sensing
| Component | Model | Est. Cost | Notes |
|-----------|-------|-----------|-------|
| Apple Watch | [Apple Watch](https://www.apple.com/apple-watch/) (already owned) | $0 | Wrist temp during sleep |
| iOS Sensor Logger | [Sensor Logger](https://apps.apple.com/app/sensor-logger/id1531582925) (free/paid tier) | $0-5 | HTTP push to RPi5 |
| _Alt: Thermal camera_ | _[FLIR Lepton 3.5](https://www.flir.com/products/lepton/) + [PureThermal](https://groupgets.com/manufacturers/getlab/products/purethermal-mini)_ | _$200-300_ | _Contactless, multi-zone capable; mount via Triad Orbit armature_ |
| _Alt: Thermal camera_ | _[AMG8833 Grid-Eye (8x8)](https://www.adafruit.com/product/3538)_ | _$30-50_ | _Low-res but cheap, I2C to RPi; mount via Triad Orbit armature_ |
| _Alt: Thermal camera_ | _[MLX90640 (32x24)](https://www.adafruit.com/product/4469)_ | _$50-80_ | _Mid-res thermal, I2C to RPi; mount via Triad Orbit armature_ |

### Thermal Camera Notes
- Contactless temperature sensing — no wearable required
- Can monitor Tiggy and Leigh simultaneously from a single sensor
- [AMG8833](https://www.adafruit.com/product/3538) or [MLX90640](https://www.adafruit.com/product/4469) are cheapest options and connect via I2C to RPi5
- [FLIR Lepton](https://www.flir.com/products/lepton/) gives higher resolution but requires [PureThermal](https://groupgets.com/manufacturers/getlab/products/purethermal-mini) USB breakout
- Software support via `fanbient run --thermal` flag
- Emissivity calibration needed for accurate skin temperature (default 0.98)
- Mount thermal cameras on [Triad Orbit](https://www.triad-orbit.com/) armatures for stable, adjustable positioning

## Future Extensions
| Component | Model | Est. Cost | Notes |
|-----------|-------|-----------|-------|
| M5Stack | [Core2](https://shop.m5stack.com/products/m5stack-core2-esp32-iot-development-kit) or [AtomS3](https://shop.m5stack.com/products/atoms3) | $20-50 | Local sensor hub, display |
| LED strip | [WS2812B (Adafruit NeoPixel)](https://www.adafruit.com/category/168) | $10 | Ambient lighting |
| Aroma diffuser | USB mini diffuser | $15 | MQTT-switched |
| Ambient speaker | Bluetooth mini speaker | $15-25 | Sleep sounds |

## Wiring — PoC Configuration

```
[Hollyland Lark M2 TX] ~~~2.4GHz~~~ [Lark M2 USB-C RX]
                                            │ USB-C (UAC digital audio)
                                            ▼
                               [RPi5] ─── Ethernet/WiFi ─── [Router]
                                │   │
                      GPIO PWM  │   │ MQTT over WiFi
                          ▼     │   ▼
                  [Oscillation  │  [Smart Plug (Tasmota)]
                   Motor or     │       │ AC mains
                   Servo]       │       ▼
                      │         │  [Fan: Blower / Inline / Noctua]
                      └─────────┘       │
                                mounted on Triad Orbit armature
                                with oscillation sweep
```

## Safety Notes

- Fan and mic mounted on Triad Orbit armatures — positioned safely away from Tiggy's sleeping area
- Smart plug fail-off: fan turns off on power loss or MQTT disconnect
- No exposed 12V wiring near pet; use enclosed PSU + fan shroud
- Monitor initial deployments to ensure fan doesn't cause anxiety
- Triad Orbit's locking joints prevent accidental repositioning
- Oscillation motor/servo should have sweep limits to prevent aiming at unintended areas
