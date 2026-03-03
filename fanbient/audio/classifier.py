"""T1 panting detection via spectral analysis.

Panting has a distinct spectral signature:
- Rhythmic breathing at 1-3 Hz
- Broadband noise bursts
- Elevated energy in mid-frequency bands

This module extracts features with librosa and classifies with a simple
sklearn model (SVM or RandomForest). Before a trained model is available,
a threshold-based heuristic is used.
"""

from __future__ import annotations

import json
import logging
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import librosa
import numpy as np

if TYPE_CHECKING:
    from sklearn.base import ClassifierMixin

    from fanbient.config import AudioConfig

logger = logging.getLogger(__name__)


@dataclass
class DetectionResult:
    """Result of a panting detection analysis on one audio chunk."""

    detected: bool
    confidence: float
    tier: str = "T1"
    features: dict | None = None


def extract_features(audio: np.ndarray, config: AudioConfig) -> np.ndarray:
    """Extract spectral features from an audio chunk.

    Returns a 1D feature vector suitable for classification.
    """
    sr = config.sample_rate

    # MFCCs — capture spectral envelope
    mfccs = librosa.feature.mfcc(
        y=audio, sr=sr, n_mfcc=config.n_mfcc,
        hop_length=config.hop_length, n_fft=config.n_fft,
    )
    mfcc_mean = np.mean(mfccs, axis=1)
    mfcc_std = np.std(mfccs, axis=1)

    # Spectral centroid — brightness
    centroid = librosa.feature.spectral_centroid(
        y=audio, sr=sr, hop_length=config.hop_length,
    )
    centroid_mean = np.mean(centroid)
    centroid_std = np.std(centroid)

    # RMS energy — loudness
    rms = librosa.feature.rms(y=audio, hop_length=config.hop_length)
    rms_mean = np.mean(rms)
    rms_std = np.std(rms)

    # Spectral rolloff
    rolloff = librosa.feature.spectral_rolloff(
        y=audio, sr=sr, hop_length=config.hop_length,
    )
    rolloff_mean = np.mean(rolloff)

    # Zero crossing rate — noisiness
    zcr = librosa.feature.zero_crossing_rate(y=audio, hop_length=config.hop_length)
    zcr_mean = np.mean(zcr)

    # Tempo / onset strength — rhythmic breathing detection
    onset_env = librosa.onset.onset_strength(
        y=audio, sr=sr, hop_length=config.hop_length,
    )
    tempo = librosa.feature.tempo(onset_envelope=onset_env, sr=sr)[0]

    features = np.concatenate([
        mfcc_mean, mfcc_std,
        [centroid_mean, centroid_std],
        [rms_mean, rms_std],
        [rolloff_mean],
        [zcr_mean],
        [tempo],
    ])
    return features


class PantingClassifier:
    """Detects panting from audio chunks.

    Supports two modes:
    1. Trained model: Load a pickled sklearn classifier from disk
    2. Heuristic: Threshold-based detection using spectral features

    Use `train()` to create a model from labeled samples, then `save()`/`load()`.
    """

    def __init__(self, config: AudioConfig) -> None:
        self.config = config
        self._model: ClassifierMixin | None = None

    def load(self, model_path: str | Path) -> None:
        """Load a trained sklearn model from pickle file."""
        path = Path(model_path)
        with path.open("rb") as f:
            self._model = pickle.load(f)  # noqa: S301
        logger.info("Loaded panting classifier from %s", path)

    def save(self, model_path: str | Path) -> None:
        """Save the trained model to pickle file."""
        if self._model is None:
            raise ValueError("No model to save — call train() first")
        path = Path(model_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as f:
            pickle.dump(self._model, f)
        logger.info("Saved panting classifier to %s", path)

    def train(
        self,
        audio_chunks: list[np.ndarray],
        labels: list[int],
    ) -> dict:
        """Train a classifier on labeled audio chunks.

        Args:
            audio_chunks: List of audio arrays (each one chunk duration).
            labels: 1 = panting, 0 = not panting.

        Returns:
            Training metrics dict.
        """
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import cross_val_score

        X = np.array([extract_features(chunk, self.config) for chunk in audio_chunks])
        y = np.array(labels)

        self._model = RandomForestClassifier(n_estimators=50, random_state=42)
        min_class = min(int(y.sum()), len(y) - int(y.sum()))
        n_cv = max(2, min(5, min_class))
        scores = cross_val_score(self._model, X, y, cv=n_cv, scoring="f1")
        self._model.fit(X, y)

        metrics = {
            "n_samples": len(y),
            "n_positive": int(y.sum()),
            "cv_f1_mean": float(np.mean(scores)),
            "cv_f1_std": float(np.std(scores)),
        }
        logger.info("Trained panting classifier: %s", json.dumps(metrics))
        return metrics

    def detect(self, audio: np.ndarray) -> DetectionResult:
        """Classify an audio chunk as panting or not.

        Uses the trained model if available, otherwise falls back to heuristic.
        """
        features = extract_features(audio, self.config)

        if self._model is not None:
            return self._detect_with_model(features)
        return self._detect_heuristic(features)

    def _detect_with_model(self, features: np.ndarray) -> DetectionResult:
        proba = self._model.predict_proba(features.reshape(1, -1))[0]
        confidence = float(proba[1]) if len(proba) > 1 else float(proba[0])
        detected = confidence >= self.config.panting_confidence_threshold
        return DetectionResult(
            detected=detected,
            confidence=confidence,
        )

    def _detect_heuristic(self, features: np.ndarray) -> DetectionResult:
        """Threshold-based heuristic when no trained model is available.

        Uses RMS energy and spectral centroid as primary indicators.
        Panting tends to have moderate-high energy with mid-range spectral centroid
        and rhythmic onset patterns (tempo in 60-180 BPM range, ~1-3 Hz breathing).
        """
        n_mfcc = self.config.n_mfcc
        # Feature vector layout: mfcc_mean(n), mfcc_std(n), centroid_m, centroid_s,
        #                         rms_m, rms_s, rolloff_m, zcr_m, tempo
        rms_mean = features[2 * n_mfcc + 2]
        zcr_mean = features[2 * n_mfcc + 5]
        tempo = features[2 * n_mfcc + 6]

        score = 0.0
        # Moderate to high energy (not silence, not extremely loud)
        if 0.01 < rms_mean < 0.3:
            score += 0.3
        # Rhythmic pattern in panting range (60-180 BPM)
        if 60 < tempo < 180:
            score += 0.4
        # Moderate zero-crossing rate (broadband but not pure noise)
        if 0.02 < zcr_mean < 0.15:
            score += 0.3

        detected = score >= self.config.panting_confidence_threshold
        return DetectionResult(
            detected=detected,
            confidence=score,
        )
