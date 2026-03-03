"""Fan control state machine.

States: IDLE → FAN_ON → COOLDOWN → IDLE
Triggers: panting detection, temperature threshold, manual override.
"""

from __future__ import annotations

import logging
import time
from enum import Enum
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from fanbient.config import FanControlConfig

logger = logging.getLogger(__name__)


class FanState(str, Enum):
    IDLE = "idle"
    FAN_ON = "fan_on"
    COOLDOWN = "cooldown"


class TriggerType(str, Enum):
    PANTING = "panting"
    TEMPERATURE = "temperature"
    MANUAL = "manual"


class FanStateMachine:
    """Manages fan state transitions with cooldown logic.

    Call `trigger()` when a detection event occurs (panting or temp threshold).
    Call `clear_trigger()` when the trigger condition clears.
    Call `tick()` periodically to advance cooldown timers.
    """

    def __init__(
        self,
        config: FanControlConfig,
        on_fan_change: Callable[[bool], None] | None = None,
        on_state_change: Callable[[FanState, TriggerType | None], None] | None = None,
    ) -> None:
        self.config = config
        self._state = FanState.IDLE
        self._active_triggers: set[TriggerType] = set()
        self._cooldown_start: float | None = None
        self._on_fan_change = on_fan_change
        self._on_state_change = on_state_change
        # Consecutive detection counter for panting confirmation
        self._panting_count = 0

    @property
    def state(self) -> FanState:
        return self._state

    @property
    def active_triggers(self) -> set[TriggerType]:
        return self._active_triggers.copy()

    def _set_state(self, new_state: FanState, trigger: TriggerType | None = None) -> None:
        if new_state == self._state:
            return
        old = self._state
        self._state = new_state
        logger.info("State: %s → %s (trigger=%s)", old.value, new_state.value, trigger)
        if self._on_state_change:
            self._on_state_change(new_state, trigger)

    def _fan_on(self) -> None:
        if self._on_fan_change:
            self._on_fan_change(True)

    def _fan_off(self) -> None:
        if self._on_fan_change:
            self._on_fan_change(False)

    def trigger(self, trigger_type: TriggerType) -> None:
        """Report that a trigger condition is active."""
        # Panting requires consecutive confirmations
        if trigger_type == TriggerType.PANTING:
            self._panting_count += 1
            if self._panting_count < self.config.detection_confirmations:
                logger.debug(
                    "Panting detection %d/%d",
                    self._panting_count, self.config.detection_confirmations,
                )
                return
        self._active_triggers.add(trigger_type)
        primary = trigger_type if len(self._active_triggers) == 1 else None

        if self._state == FanState.IDLE:
            self._set_state(FanState.FAN_ON, trigger_type)
            self._fan_on()
        elif self._state == FanState.COOLDOWN:
            # Re-trigger during cooldown — go back to FAN_ON
            self._cooldown_start = None
            self._set_state(FanState.FAN_ON, trigger_type)
        # If already FAN_ON, just update triggers

    def clear_trigger(self, trigger_type: TriggerType) -> None:
        """Report that a trigger condition has cleared."""
        if trigger_type == TriggerType.PANTING:
            self._panting_count = 0
        self._active_triggers.discard(trigger_type)

        if not self._active_triggers and self._state == FanState.FAN_ON:
            # All triggers cleared — start cooldown
            self._cooldown_start = time.monotonic()
            self._set_state(FanState.COOLDOWN)

    def tick(self) -> None:
        """Advance timers. Call periodically (e.g. every second)."""
        if self._state == FanState.COOLDOWN and self._cooldown_start is not None:
            elapsed = time.monotonic() - self._cooldown_start
            if elapsed >= self.config.cooldown_seconds:
                self._cooldown_start = None
                self._set_state(FanState.IDLE)
                self._fan_off()

    def manual_on(self) -> None:
        """Manual fan override — on."""
        self._active_triggers.add(TriggerType.MANUAL)
        if self._state != FanState.FAN_ON:
            self._set_state(FanState.FAN_ON, TriggerType.MANUAL)
            self._fan_on()

    def manual_off(self) -> None:
        """Manual fan override — off immediately (skip cooldown)."""
        self._active_triggers.clear()
        self._panting_count = 0
        self._cooldown_start = None
        self._set_state(FanState.IDLE)
        self._fan_off()

    def reset(self) -> None:
        """Reset state machine to IDLE."""
        self.manual_off()
