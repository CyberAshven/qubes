"""
Audio Recording

Handles microphone recording for STT input with PTT and VAD modes.
From docs/27_Audio_TTS_STT_Integration.md Section 4.4
"""

from pathlib import Path
from typing import AsyncIterator
import asyncio
import wave
from collections import deque

from utils.logging import get_logger

logger = get_logger(__name__)


class AudioRecorder:
    """Audio recording handler"""

    def __init__(
        self,
        sample_rate: int = 16000,  # Whisper prefers 16kHz
        channels: int = 1,          # Mono
        chunk_size: int = 1024,
    ):
        """
        Initialize audio recorder

        Args:
            sample_rate: Audio sample rate (Hz)
            channels: Number of audio channels (1=mono, 2=stereo)
            chunk_size: Audio buffer chunk size
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.audio = None

        logger.debug(
            "audio_recorder_initialized",
            sample_rate=sample_rate,
            channels=channels,
            chunk_size=chunk_size
        )

    def _init_pyaudio(self):
        """Lazy initialize PyAudio"""
        if self.audio is None:
            try:
                import pyaudio
                self.audio = pyaudio.PyAudio()
            except ImportError:
                logger.error("pyaudio_not_installed", message="Install PyAudio: pip install pyaudio")
                raise

    async def record_ptt(self, output_path: Path) -> Path:
        """
        Record audio with push-to-talk (manual stop)

        Args:
            output_path: Path to save recorded audio

        Returns:
            Path to saved audio file
        """
        try:
            import pyaudio

            self._init_pyaudio()

            logger.info("recording_started", mode="ptt")

            stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size,
            )

            frames = []
            print("🎤 Recording... (press Enter to stop)")

            # Record until user stops
            recording = True

            async def stop_on_enter():
                nonlocal recording
                await asyncio.get_event_loop().run_in_executor(None, input)
                recording = False

            stop_task = asyncio.create_task(stop_on_enter())

            while recording:
                data = await asyncio.get_event_loop().run_in_executor(
                    None, stream.read, self.chunk_size
                )
                frames.append(data)

            stream.stop_stream()
            stream.close()

            # Save to WAV file
            with wave.open(str(output_path), "wb") as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(self.audio.get_sample_size(pyaudio.paInt16))
                wf.setframerate(self.sample_rate)
                wf.writeframes(b"".join(frames))

            logger.info("recording_saved", path=str(output_path), frames=len(frames))

            return output_path

        except Exception as e:
            logger.error("recording_failed", error=str(e), exc_info=True)
            raise

    async def record_vad(
        self,
        output_path: Path,
        silence_duration: float = 1.5
    ) -> Path:
        """
        Record audio with voice activity detection

        Args:
            output_path: Path to save recorded audio
            silence_duration: Seconds of silence to stop recording

        Returns:
            Path to saved audio file
        """
        try:
            import pyaudio

            self._init_pyaudio()

            logger.info("recording_started", mode="vad", silence_duration=silence_duration)

            try:
                import webrtcvad
                vad = webrtcvad.Vad(3)  # Aggressiveness: 0 (least) to 3 (most)
            except ImportError:
                logger.warning(
                    "webrtcvad_not_installed",
                    message="Install webrtcvad: pip install webrtcvad. Falling back to PTT mode."
                )
                return await self.record_ptt(output_path)

            stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size,
            )

            frames = []
            speech_detected = False
            silence_chunks = 0
            max_silence_chunks = int(silence_duration * self.sample_rate / self.chunk_size)

            print("🎤 Listening... (speak to start recording)")

            while True:
                data = await asyncio.get_event_loop().run_in_executor(
                    None, stream.read, self.chunk_size
                )

                # Check if chunk contains speech
                is_speech = vad.is_speech(data, self.sample_rate)

                if is_speech:
                    if not speech_detected:
                        print("🎤 Recording...")
                    speech_detected = True
                    silence_chunks = 0
                    frames.append(data)
                elif speech_detected:
                    silence_chunks += 1
                    frames.append(data)

                    # Stop after prolonged silence
                    if silence_chunks > max_silence_chunks:
                        print("🎤 Recording stopped (silence detected)")
                        break

            stream.stop_stream()
            stream.close()

            # Save to WAV file
            with wave.open(str(output_path), "wb") as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(self.audio.get_sample_size(pyaudio.paInt16))
                wf.setframerate(self.sample_rate)
                wf.writeframes(b"".join(frames))

            logger.info("recording_saved", path=str(output_path), frames=len(frames))

            return output_path

        except Exception as e:
            logger.error("vad_recording_failed", error=str(e), exc_info=True)
            raise

    async def record_fixed_duration(
        self,
        output_path: Path,
        duration_seconds: float
    ) -> Path:
        """
        Record audio for a fixed duration.

        Used for voice cloning where a specific length sample is needed.

        Args:
            output_path: Path to save recorded audio
            duration_seconds: Recording duration in seconds

        Returns:
            Path to saved audio file
        """
        try:
            import pyaudio

            self._init_pyaudio()

            logger.info(
                "recording_started",
                mode="fixed_duration",
                duration=duration_seconds
            )

            stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size,
            )

            frames = []
            total_chunks = int(duration_seconds * self.sample_rate / self.chunk_size)

            print(f"🎤 Recording for {duration_seconds} seconds...")

            for chunk_num in range(total_chunks):
                data = await asyncio.get_event_loop().run_in_executor(
                    None, stream.read, self.chunk_size
                )
                frames.append(data)

                # Show progress every second
                elapsed = (chunk_num + 1) * self.chunk_size / self.sample_rate
                if chunk_num % int(self.sample_rate / self.chunk_size) == 0:
                    remaining = duration_seconds - elapsed
                    if remaining > 0:
                        print(f"🎤 {remaining:.0f}s remaining...")

            stream.stop_stream()
            stream.close()

            print("🎤 Recording complete!")

            # Save to WAV file
            with wave.open(str(output_path), "wb") as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(self.audio.get_sample_size(pyaudio.paInt16))
                wf.setframerate(self.sample_rate)
                wf.writeframes(b"".join(frames))

            logger.info(
                "recording_saved",
                path=str(output_path),
                frames=len(frames),
                duration=duration_seconds
            )

            return output_path

        except Exception as e:
            logger.error("fixed_duration_recording_failed", error=str(e), exc_info=True)
            raise

    async def record_stream(self) -> AsyncIterator[bytes]:
        """
        Record audio as a stream (for real-time STT)

        Yields:
            Audio chunks as bytes
        """
        try:
            import pyaudio

            self._init_pyaudio()

            logger.debug("streaming_recording_started")

            stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size,
            )

            try:
                while True:
                    data = await asyncio.get_event_loop().run_in_executor(
                        None, stream.read, self.chunk_size
                    )
                    yield data
            finally:
                stream.stop_stream()
                stream.close()
                logger.debug("streaming_recording_stopped")

        except Exception as e:
            logger.error("stream_recording_failed", error=str(e), exc_info=True)
            raise

    def __del__(self):
        """Cleanup PyAudio on destruction"""
        if self.audio is not None:
            self.audio.terminate()


class VADBuffer:
    """Voice Activity Detection buffer with pre-buffer and silence detection"""

    def __init__(
        self,
        pre_buffer_duration: float = 0.5,
        silence_duration: float = 1.5,
        sample_rate: int = 16000,
        chunk_size: int = 1024
    ):
        """
        Initialize VAD buffer

        Args:
            pre_buffer_duration: Seconds of audio to keep before speech detected
            silence_duration: Seconds of silence to stop recording
            sample_rate: Audio sample rate (Hz)
            chunk_size: Audio chunk size
        """
        max_pre_buffer_chunks = int(pre_buffer_duration * sample_rate / chunk_size)
        self.pre_buffer = deque(maxlen=max_pre_buffer_chunks)
        self.recording_buffer = []
        self.silence_duration = silence_duration
        self.silence_chunks = 0
        self.max_silence_chunks = int(silence_duration * sample_rate / chunk_size)

        logger.debug(
            "vad_buffer_initialized",
            pre_buffer_duration=pre_buffer_duration,
            silence_duration=silence_duration
        )

    def add_chunk(self, chunk: bytes, is_speech: bool) -> bool:
        """
        Add audio chunk, return True if recording complete

        Args:
            chunk: Audio chunk (bytes)
            is_speech: Whether chunk contains speech

        Returns:
            True if recording is complete, False otherwise
        """
        if not is_speech:
            # Add to pre-buffer (circular)
            self.pre_buffer.append(chunk)

            if self.recording_buffer:
                # In recording mode, count silence
                self.silence_chunks += 1
                self.recording_buffer.append(chunk)

                # Stop if silence threshold exceeded
                if self.silence_chunks > self.max_silence_chunks:
                    logger.debug("vad_recording_complete", total_chunks=len(self.recording_buffer))
                    return True  # Recording complete
        else:
            # Speech detected
            if not self.recording_buffer:
                # Start recording - copy pre-buffer
                self.recording_buffer = list(self.pre_buffer)
                logger.debug("vad_speech_detected", pre_buffer_chunks=len(self.pre_buffer))

            self.silence_chunks = 0
            self.recording_buffer.append(chunk)

        return False

    def get_audio(self) -> bytes:
        """
        Get complete recording

        Returns:
            Complete audio data (bytes)
        """
        return b"".join(self.recording_buffer)

    def reset(self):
        """Reset buffer for new recording"""
        self.recording_buffer = []
        self.silence_chunks = 0
        logger.debug("vad_buffer_reset")
