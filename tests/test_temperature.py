"""Tests for temperature monitor."""

from unittest.mock import MagicMock

from fanbient.config import TemperatureConfig
from fanbient.sensors.temperature import TemperatureMonitor, _extract_temperature


def _make_monitor(on_threshold: float = 98.8, off_threshold: float = 98.2):
    config = TemperatureConfig()
    config.on_threshold_f = on_threshold
    config.off_threshold_f = off_threshold
    cb = MagicMock()
    monitor = TemperatureMonitor(config, on_threshold_crossed=cb)
    return monitor, cb


def test_initial_state():
    monitor, _ = _make_monitor()
    assert not monitor.is_triggered
    assert monitor.last_temp is None


def test_below_threshold():
    monitor, cb = _make_monitor()
    monitor.update(97.0)
    assert not monitor.is_triggered
    cb.assert_not_called()


def test_above_on_threshold():
    monitor, cb = _make_monitor()
    monitor.update(99.0)
    assert monitor.is_triggered
    cb.assert_called_once_with(True, 99.0)


def test_deadband_hysteresis():
    monitor, cb = _make_monitor(on_threshold=98.8, off_threshold=98.2)

    # Go above on threshold
    monitor.update(99.0)
    assert monitor.is_triggered
    assert cb.call_count == 1

    # Stay in deadband — should remain triggered
    monitor.update(98.5)
    assert monitor.is_triggered
    assert cb.call_count == 1  # No new call

    # Drop below off threshold
    monitor.update(98.0)
    assert not monitor.is_triggered
    assert cb.call_count == 2
    cb.assert_called_with(False, 98.0)


def test_repeated_readings_no_spam():
    monitor, cb = _make_monitor()
    for _ in range(10):
        monitor.update(99.0)
    # Should only trigger once
    assert cb.call_count == 1


def test_extract_temperature_direct():
    assert _extract_temperature({"temperature": 98.6}) == 98.6


def test_extract_temperature_payload():
    assert _extract_temperature({"payload": {"temperature": 99.1}}) == 99.1


def test_extract_temperature_readings():
    data = {
        "readings": [
            {"name": "wristTemperature", "value": 98.4},
            {"name": "heartRate", "value": 72},
        ]
    }
    assert _extract_temperature(data) == 98.4


def test_extract_temperature_missing():
    assert _extract_temperature({"foo": "bar"}) is None
