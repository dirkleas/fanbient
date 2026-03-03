# fanbient — Hardware BOM & Wiring

## PoC Hardware (Phase 1)

### Core Compute
| Component | Model | Est. Cost | Notes |
|-----------|-------|-----------|-------|
| SBC | Raspberry Pi 5 (4GB+) | $60-80 | Main compute, MQTT broker, audio processing |
| MicroSD | 64GB A2 class | $10 | Boot/storage |
| Power supply | Official RPi5 27W USB-C | $12 | |

### Audio Capture
| Component | Model | Est. Cost | Notes |
|-----------|-------|-----------|-------|
| Wireless mic kit | Hollyland Lark M2 or DJI Mic 2 | $150-300 | TX clips near Tiggy's bed |
| USB audio interface | Sabrent USB DAC | $8-15 | 3.5mm RX → USB for RPi |
| _Alt: USB mic_ | _Budget USB condenser_ | _$15-30_ | _Simpler, wired, shorter range_ |

### Fan & Actuation
| Component | Model | Est. Cost | Notes |
|-----------|-------|-----------|-------|
| Fan | Noctua NF-A14 (140mm) or NF-A20 (200mm) | $25-35 | Quiet, 12V |
| Smart plug | Sonoff S31 (Tasmota) or Shelly Plug S | $12-20 | MQTT-native or flashable |
| _Alt: PWM control_ | _M5Stack relay/MOSFET + 12V PSU_ | _$15-25_ | _Variable speed_ |

### Estimated PoC Cost
- **Minimal** (USB mic + smart plug + RPi5 + PC fan): ~$115-155
- **Full wireless** (wireless mic kit + smart plug + RPi5 + PC fan): ~$265-440

## Phase 2 Additions

### Temperature Sensing
| Component | Model | Est. Cost | Notes |
|-----------|-------|-----------|-------|
| Apple Watch | Already owned | $0 | Wrist temp during sleep |
| iOS Sensor Logger | App (free/paid tier) | $0-5 | HTTP push to RPi5 |
| _Alt: Thermal camera_ | _FLIR Lepton 3.5 + PureThermal_ | _$200-300_ | _Contactless, multi-zone capable_ |
| _Alt: Thermal camera_ | _AMG8833 Grid-Eye (8x8)_ | _$30-50_ | _Low-res but cheap, I2C to RPi_ |
| _Alt: Thermal camera_ | _MLX90640 (32x24)_ | _$50-80_ | _Mid-res thermal, I2C to RPi_ |

### Thermal Camera Notes
- Contactless temperature sensing — no wearable required
- Can monitor Tiggy and Leigh simultaneously from a single sensor
- AMG8833 or MLX90640 are cheapest options and connect via I2C to RPi5
- FLIR Lepton gives higher resolution but requires PureThermal USB breakout
- Software support via `fanbient run --thermal` flag
- Emissivity calibration needed for accurate skin temperature (default 0.98)

## Future Extensions
| Component | Model | Est. Cost | Notes |
|-----------|-------|-----------|-------|
| M5Stack | Core2 or AtomS3 | $20-50 | Local sensor hub, display |
| Articulating arm | Monitor arm / gooseneck | $15-30 | Fan positioning |
| LED strip | WS2812B | $10 | Ambient lighting |
| Aroma diffuser | USB mini diffuser | $15 | MQTT-switched |
| Ambient speaker | Bluetooth mini speaker | $15-25 | Sleep sounds |

## Wiring — PoC Configuration

```
[Hollyland TX] ~~~wireless~~~ [Hollyland RX]
                                    │ 3.5mm audio
                                    ▼
                            [USB Audio Interface]
                                    │ USB
                                    ▼
                               [RPi5] ─── Ethernet/WiFi ─── [Router]
                                    │ MQTT over WiFi
                                    ▼
                            [Smart Plug (Tasmota)]
                                    │ AC mains
                                    ▼
                               [AC Fan] or [12V PSU → Noctua Fan]
```

## Safety Notes

- Fan should be positioned safely away from Tiggy's sleeping area
- Smart plug fail-off: fan turns off on power loss or MQTT disconnect
- No exposed 12V wiring near pet; use enclosed PSU + fan shroud
- Monitor initial deployments to ensure fan doesn't cause anxiety
