"""Tests for panting classifier."""

import numpy as np

from fanbient.config import AudioConfig
from fanbient.audio.classifier import (
    DetectionResult,
    PantingClassifier,
    extract_features,
)


def _make_config() -> AudioConfig:
    return AudioConfig()


def _make_silence(config: AudioConfig) -> np.ndarray:
    """Generate a silent audio chunk."""
    n_samples = int(config.sample_rate * config.chunk_duration)
    return np.zeros(n_samples, dtype=np.float32)


def _make_noise(config: AudioConfig, amplitude: float = 0.1) -> np.ndarray:
    """Generate random noise audio chunk."""
    n_samples = int(config.sample_rate * config.chunk_duration)
    rng = np.random.default_rng(42)
    return (rng.random(n_samples).astype(np.float32) - 0.5) * amplitude


def _make_rhythmic(config: AudioConfig, freq_hz: float = 2.0, amplitude: float = 0.05) -> np.ndarray:
    """Generate a rhythmic pulsing signal (simulated panting)."""
    n_samples = int(config.sample_rate * config.chunk_duration)
    t = np.linspace(0, config.chunk_duration, n_samples, dtype=np.float32)
    # Amplitude-modulated noise at breathing rate
    envelope = 0.5 * (1 + np.sin(2 * np.pi * freq_hz * t))
    rng = np.random.default_rng(42)
    noise = rng.random(n_samples).astype(np.float32) - 0.5
    return (noise * envelope * amplitude).astype(np.float32)


def test_extract_features_shape():
    config = _make_config()
    audio = _make_noise(config)
    features = extract_features(audio, config)
    # Expected: n_mfcc*2 (mean+std) + 2 (centroid) + 2 (rms) + 1 (rolloff) + 1 (zcr) + 1 (tempo)
    expected_len = config.n_mfcc * 2 + 2 + 2 + 1 + 1 + 1
    assert features.shape == (expected_len,)


def test_extract_features_deterministic():
    config = _make_config()
    audio = _make_noise(config)
    f1 = extract_features(audio, config)
    f2 = extract_features(audio, config)
    np.testing.assert_array_almost_equal(f1, f2)


def test_heuristic_silence_not_detected():
    config = _make_config()
    classifier = PantingClassifier(config)
    result = classifier.detect(_make_silence(config))
    assert isinstance(result, DetectionResult)
    assert not result.detected
    assert result.confidence < config.panting_confidence_threshold


def test_heuristic_returns_detection_result():
    config = _make_config()
    classifier = PantingClassifier(config)
    result = classifier.detect(_make_noise(config))
    assert isinstance(result, DetectionResult)
    assert result.tier == "T1"
    assert 0.0 <= result.confidence <= 1.0


def test_classifier_train_and_predict():
    """Test that we can train a model and get predictions."""
    config = _make_config()
    classifier = PantingClassifier(config)

    # Create minimal training data
    chunks = [
        _make_rhythmic(config, freq_hz=2.0, amplitude=0.05),
        _make_rhythmic(config, freq_hz=2.5, amplitude=0.06),
        _make_rhythmic(config, freq_hz=1.5, amplitude=0.04),
        _make_silence(config),
        _make_noise(config, amplitude=0.01),
        _make_noise(config, amplitude=0.005),
    ]
    labels = [1, 1, 1, 0, 0, 0]

    metrics = classifier.train(chunks, labels)
    assert "n_samples" in metrics
    assert metrics["n_samples"] == 6

    # Should produce a result without error
    result = classifier.detect(_make_rhythmic(config))
    assert isinstance(result, DetectionResult)
    assert 0.0 <= result.confidence <= 1.0
