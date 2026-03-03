"""Audio stream capture with chunked processing."""

from __future__ import annotations

import logging
import queue
import threading
from typing import TYPE_CHECKING, Callable

import numpy as np
import sounddevice as sd

if TYPE_CHECKING:
    from fanbient.config import AudioConfig

logger = logging.getLogger(__name__)


class AudioCapture:
    """Captures audio from a microphone in fixed-duration chunks.

    Uses sounddevice InputStream with a callback that fills a queue.
    Consumer calls `read_chunk()` to get the next complete chunk as a numpy array.
    """

    def __init__(self, config: AudioConfig) -> None:
        self.config = config
        self.chunk_samples = int(config.sample_rate * config.chunk_duration)
        self._queue: queue.Queue[np.ndarray] = queue.Queue(maxsize=4)
        self._buffer = np.zeros(0, dtype=np.float32)
        self._lock = threading.Lock()
        self._stream: sd.InputStream | None = None
        self._running = False

    def _audio_callback(
        self,
        indata: np.ndarray,
        frames: int,
        time_info: object,
        status: sd.CallbackFlags,
    ) -> None:
        if status:
            logger.warning("Audio callback status: %s", status)
        # indata is (frames, channels) — take channel 0
        mono = indata[:, 0].copy()
        with self._lock:
            self._buffer = np.concatenate([self._buffer, mono])
            while len(self._buffer) >= self.chunk_samples:
                chunk = self._buffer[: self.chunk_samples]
                self._buffer = self._buffer[self.chunk_samples :]
                try:
                    self._queue.put_nowait(chunk)
                except queue.Full:
                    # Drop oldest chunk if consumer is slow
                    try:
                        self._queue.get_nowait()
                    except queue.Empty:
                        pass
                    self._queue.put_nowait(chunk)

    def start(self) -> None:
        """Start capturing audio."""
        if self._running:
            return
        logger.info(
            "Starting audio capture: %d Hz, chunk=%.1fs, device=%s",
            self.config.sample_rate,
            self.config.chunk_duration,
            self.config.device,
        )
        self._stream = sd.InputStream(
            samplerate=self.config.sample_rate,
            channels=self.config.channels,
            dtype="float32",
            device=self.config.device,
            callback=self._audio_callback,
        )
        self._stream.start()
        self._running = True

    def stop(self) -> None:
        """Stop capturing audio."""
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        self._running = False
        logger.info("Audio capture stopped")

    def read_chunk(self, timeout: float = 5.0) -> np.ndarray | None:
        """Read the next audio chunk. Returns None on timeout."""
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    @property
    def is_running(self) -> bool:
        return self._running


def run_capture_loop(
    config: AudioConfig,
    on_chunk: Callable[[np.ndarray], None],
    stop_event: threading.Event,
) -> None:
    """Convenience: run capture loop calling on_chunk for each audio chunk."""
    capture = AudioCapture(config)
    capture.start()
    try:
        while not stop_event.is_set():
            chunk = capture.read_chunk(timeout=1.0)
            if chunk is not None:
                on_chunk(chunk)
    finally:
        capture.stop()
