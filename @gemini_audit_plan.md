# @gemini_audit_plan.md — fanbient Audit Plan

This document outlines the strategy for auditing the `fanbient` repository. The goal is to evaluate the current implementation, identify potential risks, and suggest improvements or alternatives.

## 1. Audit Objectives

*   **Architectural Soundness:** Evaluate the decoupling of components and the central service orchestration.
*   **Implementation Quality:** Assess code style, type safety, and use of modern Python features.
*   **Performance & Efficiency:** Analyze the resource footprint, especially for real-time audio processing on RPi5.
*   **Robustness & Reliability:** Identify edge cases in state transitions, sensor data handling, and network failures.
*   **Extensibility:** Determine how easily new triggers, classification tiers (T2/T3), and actuators can be integrated.
*   **Security:** Review MQTT communication and REST API security.

## 2. Research & Analysis Phases

### Phase 1: Deep Code Review
*   **Core Orchestration (`fanbient/service.py`):** Analyze how components are wired and managed.
*   **State Machine (`fanbient/control/state_machine.py`):** Verify transition logic, multiple trigger handling, and cooldown/hysteresis.
*   **Audio Pipeline (`fanbient/audio/`):**
    *   `capture.py`: Review buffer management and potential for underruns/overruns.
    *   `classifier.py`: Evaluate feature extraction efficiency and heuristic fallback logic.
*   **Sensor Integration (`fanbient/sensors/`):**
    *   `temperature.py`: Check for robust parsing of external JSON and thermal camera frame processing.

### Phase 2: System-Level Evaluation
*   **Concurrency Model:** Evaluate the use of `threading` vs. potential `asyncio` for I/O-bound tasks (MQTT, REST API, Sensor Logger).
*   **Configuration Management:** Review `FanbientConfig` (Pydantic) for completeness and ease of override.
*   **Error Handling:** Identify critical failure points (MQTT broker down, Mic disconnected, Sensor Logger timeout) and recovery strategies.

### Phase 3: Future-Proofing & Extensions
*   **Classification Tiers:** Assess the feasibility of T2/T3 integration into the current `PantingClassifier` interface.
*   **Hardware Integration:** Review the modularity for adding new fans (PWM), sensors, or armatures.

## 3. Deliverables

*   **@gemini_audit.md:** A comprehensive report including:
    *   **Executive Summary:** High-level take on the project's health.
    *   **Architectural Overview:** Discussion of the "Service Layer" pattern.
    *   **Deep Dives:** Detailed analysis of key modules.
    *   **Considerations & Suggestions:** Actionable improvements with rationale.
    *   **Alternatives:** Discussion of `asyncio`, MQTT-native triggers vs. polling, etc.
    *   **Fitness for Purpose:** Evaluation against the Tiggy/Leigh personas.

## 4. Timeline (Internal)

1.  **Initialize Audit:** (Done)
2.  **Phase 1 (Code Review):** Immediate next step.
3.  **Phase 2 (System Eval):** Following code review.
4.  **Phase 3 (Reporting):** Consolidate findings into `@gemini_audit.md`.
