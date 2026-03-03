# gemini_audit.md — fanbient System Audit

## Executive Summary

`fanbient` is a sophisticated, modular, and well-engineered autonomous fan control system. It leverages modern Python 3.12+ features and a robust set of libraries (`pydantic`, `typer`, `librosa`, `scikit-learn`, `fastapi`) to deliver a specialized IoT solution for sleep cooling. The architecture is highly decoupled, making it extensible and testable. While the core logic is sound, there are opportunities to enhance robustness in edge cases (device disconnections, thread safety) and to optimize for the target RPi5 hardware.

---

## Architectural Review

### The Service Layer Pattern

The `FanbientService` in `fanbient/service.py` acts as a protocol-agnostic orchestrator. This is a strong design choice because it allows the same core logic to be driven by:

- A command-line interface (`cli.py`).
- A REST API (`api.py`).
- Potential future interfaces (MCP, MQTT commands, etc.).

**Consideration:** The service currently manages its own lifecycle and background threads. This makes it easy to use but harder to integrate into a modern `asyncio` stack.

### Decoupled State Machine

The `FanStateMachine` is purely logic-driven and doesn't know about MQTT or audio. It relies on callbacks (`on_fan_change`, `on_state_change`). This makes it highly unit-testable.

---

## Component Deep Dives

### 1. Audio Pipeline (`audio/`)

- **Capture:** `AudioCapture` uses `sounddevice` with a thread-safe `queue.Queue`. It handles overflows by dropping old chunks, which is appropriate for real-time systems.
- **Classification:** `PantingClassifier` implements a tiered approach (heuristic fallback). Feature extraction using `librosa` is comprehensive (MFCCs, spectral centroid, RMS, etc.).

**Suggestion:**

- **Capture Resilience:** If the USB microphone is disconnected, `sounddevice` may throw an exception or stop calling the callback. A monitoring/reconnect loop for the `InputStream` would improve long-term reliability on an RPi5.
- **Feature Extraction Overhead:** `librosa` can be slow on ARM. Consider benchmarking the extraction time for a 2.5s chunk. If it approaches 2.5s, the system will lag. Using `numpy` directly for simpler features (RMS, ZCR) might be an optimization.

### 2. Control Logic (`control/`)

- **State Machine:** Uses a clean `IDLE -> FAN_ON -> COOLDOWN` flow. Multiple triggers are handled by a set (`_active_triggers`).
- **Confirmation Logic:** `detection_confirmations` (default: 2) prevents "fluttering" by requiring consecutive positive detections.

**Observation:**

- The `tick()` method advances the cooldown timer. It is called from the `_audio_loop` in `FanbientService`. If the audio loop stalls or the service is running without audio, `tick()` might not be called regularly.

### 3. Sensors (`sensors/`)

- **Hysteresis:** `TemperatureMonitor` implements a proper deadband (on_threshold/off_threshold), which is critical for preventing rapid fan cycling.
- **Thermal Camera:** The `ThermalCamera` module assumes 16-bit raw values in centikelvin. This is highly specific to FLIR Lepton-like hardware.

**Suggestion:**

- **Sensor Logger Payload:** The `_extract_temperature` function is a bit fragile as it tries to guess the JSON structure. A more rigid schema (using Pydantic) would be safer.

---

## Technical Considerations & Suggestions

### 1. Concurrency: Threading vs. Asyncio

The current implementation is heavily thread-based. While fine for Python 3.12 (especially with the improvements to the GIL), it can lead to subtle race conditions and complex lifecycle management.

- **Suggestion:** For I/O-bound tasks like MQTT and the REST API, `asyncio` would be more idiomatic and potentially more efficient. However, `librosa` and `scikit-learn` are CPU-bound and would still require `run_in_executor` or separate threads.

### 2. Lifecycle Management

The `FanbientService` starts several threads. Stopping it requires calling `.stop()`, which joins threads.

- **Risk:** If a thread hangs (e.g., waiting for a slow sensor or blocked I/O), the whole service might hang on shutdown.
- **Suggestion:** Use `threading.Event` more consistently for stopping loops (already partially implemented) and consider a context manager for the service to ensure cleanup.

### 3. Configuration & Environment

Using `pydantic-settings` is excellent. It allows easy configuration via environment variables (`FANBIENT_*`).

### 4. Safety & Fail-Safes

- **MQTT Broker Down:** The service continues but warns. If the broker is the *only* way to turn the fan on/off, the system is essentially dead.
- **Suggestion:** A "Local Override" or "Safe State" (e.g., turn fan OFF if MQTT is lost for more than X minutes) could be implemented in the state machine.

---

## Alternatives & Rationale

| Alternative | Rationale |
| :--- | :--- |
| **MQTT-Native Automation** | Instead of a Python service, use Node-RED or Home Assistant. *Rationale:* `fanbient` is better for specialized local audio processing (T1/T2) that might be too heavy or complex for standard HA integrations. |
| **Simple Heuristics Only** | Use only RMS/ZCR instead of full spectral analysis. *Rationale:* Full spectral analysis is much more robust against false positives (e.g., white noise, talking) compared to simple energy thresholds. |
| **Edge Impulse / TFLite** | Use a pre-compiled model for panting detection. *Rationale:* Would be significantly faster and more energy-efficient on RPi5, but less flexible than the current scikit-learn approach for user retraining. |

---

## Fitness for Purpose

- **Tiggy (Pug):** The audio-driven approach with cooldown is perfect for a dog's panting patterns. The `detection_confirmations` setting is a key feature here.
- **Leigh (Human):** Apple Watch integration via Sensor Logger is a clever use of existing hardware. The deadband logic ensures comfort without annoying fan cycling.

## Conclusion

`fanbient` is a high-quality codebase that effectively solves a niche problem. By addressing potential hardware-level failures and optimizing the CPU-intensive classification pipeline, it can transition from a robust PoC to a production-grade appliance.
