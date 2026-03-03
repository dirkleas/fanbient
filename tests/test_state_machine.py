"""Tests for fan state machine."""

import time
from unittest.mock import MagicMock

from fanbient.config import FanControlConfig
from fanbient.control.state_machine import FanState, FanStateMachine, TriggerType


def _make_sm(cooldown: float = 1.0, confirmations: int = 1) -> tuple[FanStateMachine, MagicMock, MagicMock]:
    config = FanControlConfig()
    config.cooldown_seconds = cooldown
    config.detection_confirmations = confirmations
    fan_cb = MagicMock()
    state_cb = MagicMock()
    sm = FanStateMachine(config, on_fan_change=fan_cb, on_state_change=state_cb)
    return sm, fan_cb, state_cb


def test_initial_state():
    sm, _, _ = _make_sm()
    assert sm.state == FanState.IDLE
    assert sm.active_triggers == set()


def test_trigger_transitions_to_fan_on():
    sm, fan_cb, state_cb = _make_sm()
    sm.trigger(TriggerType.PANTING)
    assert sm.state == FanState.FAN_ON
    fan_cb.assert_called_once_with(True)
    state_cb.assert_called_once_with(FanState.FAN_ON, TriggerType.PANTING)


def test_clear_trigger_starts_cooldown():
    sm, fan_cb, _ = _make_sm()
    sm.trigger(TriggerType.PANTING)
    sm.clear_trigger(TriggerType.PANTING)
    assert sm.state == FanState.COOLDOWN
    # Fan should still be on during cooldown
    assert fan_cb.call_count == 1  # Only the initial ON call


def test_cooldown_expires():
    sm, fan_cb, _ = _make_sm(cooldown=0.1)
    sm.trigger(TriggerType.PANTING)
    sm.clear_trigger(TriggerType.PANTING)
    assert sm.state == FanState.COOLDOWN
    time.sleep(0.15)
    sm.tick()
    assert sm.state == FanState.IDLE
    fan_cb.assert_any_call(False)


def test_retrigger_during_cooldown():
    sm, _, _ = _make_sm(cooldown=10.0)
    sm.trigger(TriggerType.PANTING)
    sm.clear_trigger(TriggerType.PANTING)
    assert sm.state == FanState.COOLDOWN
    sm.trigger(TriggerType.PANTING)
    assert sm.state == FanState.FAN_ON


def test_multiple_triggers():
    sm, fan_cb, _ = _make_sm()
    sm.trigger(TriggerType.PANTING)
    sm.trigger(TriggerType.TEMPERATURE)
    assert sm.state == FanState.FAN_ON
    assert TriggerType.PANTING in sm.active_triggers
    assert TriggerType.TEMPERATURE in sm.active_triggers

    # Clear one trigger — should stay FAN_ON
    sm.clear_trigger(TriggerType.PANTING)
    assert sm.state == FanState.FAN_ON

    # Clear second trigger — now cooldown
    sm.clear_trigger(TriggerType.TEMPERATURE)
    assert sm.state == FanState.COOLDOWN


def test_manual_on_off():
    sm, fan_cb, _ = _make_sm()
    sm.manual_on()
    assert sm.state == FanState.FAN_ON
    fan_cb.assert_called_with(True)

    sm.manual_off()
    assert sm.state == FanState.IDLE
    fan_cb.assert_called_with(False)


def test_detection_confirmations():
    sm, fan_cb, _ = _make_sm(confirmations=3)
    # First two triggers shouldn't activate
    sm.trigger(TriggerType.PANTING)
    assert sm.state == FanState.IDLE
    sm.trigger(TriggerType.PANTING)
    assert sm.state == FanState.IDLE
    # Third should
    sm.trigger(TriggerType.PANTING)
    assert sm.state == FanState.FAN_ON


def test_temperature_trigger_no_confirmation():
    """Temperature triggers should not require confirmations."""
    sm, fan_cb, _ = _make_sm(confirmations=3)
    sm.trigger(TriggerType.TEMPERATURE)
    assert sm.state == FanState.FAN_ON


def test_reset():
    sm, fan_cb, _ = _make_sm()
    sm.trigger(TriggerType.PANTING)
    sm.reset()
    assert sm.state == FanState.IDLE
    assert sm.active_triggers == set()
