"""
Audio Playback

Handles audio playback for TTS output using sounddevice.
From docs/27_Audio_TTS_STT_Integration.md Section 3.4
"""

from typing import AsyncIterator
from pathlib import Path
import asyncio

from utils.logging import get_logger

logger = get_logger(__name__)


class AudioPlayer:
    """Audio playback handler"""

    def __init__(self, sample_rate: int = 24000):
        """
        Initialize audio player

        Args:
            sample_rate: Audio sample rate (Hz)
        """
        self.sample_rate = sample_rate
        self.stream = None

        logger.debug("audio_player_initialized", sample_rate=sample_rate)

    async def play_stream(self, audio_chunks: AsyncIterator[bytes]):
        """
        Play audio chunks as they arrive (low latency)

        Args:
            audio_chunks: Async iterator of audio byte chunks
        """
        try:
            import sounddevice as sd
            import numpy as np
            from pydub import AudioSegment
            import io

            logger.debug("starting_audio_playback")

            # Collect all chunks first (for mp3 decoding)
            chunks = []
            async for chunk in audio_chunks:
                chunks.append(chunk)

            # Combine all chunks
            audio_data = b"".join(chunks)

            # Decode MP3 to PCM
            audio_segment = AudioSegment.from_mp3(io.BytesIO(audio_data))
            samples = np.array(audio_segment.get_array_of_samples(), dtype=np.int16)

            # Convert to float32 for sounddevice
            samples_float = samples.astype(np.float32) / 32768.0

            # Play audio
            sd.play(samples_float, samplerate=audio_segment.frame_rate)
            sd.wait()  # Wait until playback finishes

            logger.info("audio_playback_completed", duration_seconds=len(audio_segment) / 1000.0)

        except ImportError as e:
            logger.error(
                "audio_library_not_installed",
                error=str(e),
                message="Install sounddevice and pydub: pip install sounddevice pydub"
            )
            raise
        except Exception as e:
            logger.error("audio_playback_failed", error=str(e), exc_info=True)
            raise

    async def play_file(self, file_path: Path):
        """
        Play complete audio file

        Args:
            file_path: Path to audio file (mp3, wav, etc.)
        """
        try:
            import sounddevice as sd
            import numpy as np
            from pydub import AudioSegment

            logger.debug("playing_audio_file", path=str(file_path))

            # Load audio file
            audio = AudioSegment.from_file(file_path)
            samples = np.array(audio.get_array_of_samples(), dtype=np.int16)

            # Convert to float32
            samples_float = samples.astype(np.float32) / 32768.0

            # Play
            sd.play(samples_float, samplerate=audio.frame_rate)
            sd.wait()

            logger.info("audio_file_played", path=str(file_path))

        except Exception as e:
            logger.error("audio_file_playback_failed", error=str(e), exc_info=True)
            raise


class StreamingAudioPlayer:
    """Low-latency streaming audio player with buffering"""

    def __init__(self, buffer_size: int = 4096):
        """
        Initialize streaming audio player

        Args:
            buffer_size: Size of audio buffer (bytes)
        """
        self.buffer_size = buffer_size
        self.buffer = asyncio.Queue(maxsize=10)

        logger.debug("streaming_audio_player_initialized", buffer_size=buffer_size)

    async def play_streaming_tts(self, audio_chunks: AsyncIterator[bytes]):
        """
        Play audio with minimal latency

        Args:
            audio_chunks: Async iterator of audio byte chunks
        """
        try:
            import sounddevice as sd
            import numpy as np

            # Start playback task
            playback_task = asyncio.create_task(self._playback_loop())

            # Stream audio chunks to buffer
            async for chunk in audio_chunks:
                await self.buffer.put(chunk)

            # Signal end of stream
            await self.buffer.put(None)
            await playback_task

        except Exception as e:
            logger.error("streaming_playback_failed", error=str(e), exc_info=True)
            raise

    async def _playback_loop(self):
        """Consume buffer and play audio"""
        try:
            import sounddevice as sd
            import numpy as np

            stream = sd.OutputStream(samplerate=self.buffer_size, channels=1)
            stream.start()

            while True:
                chunk = await self.buffer.get()
                if chunk is None:  # End of stream
                    break

                # Convert bytes to numpy array
                audio_array = np.frombuffer(chunk, dtype=np.int16)

                # Write to output stream
                stream.write(audio_array)

            stream.stop()
            stream.close()

            logger.debug("playback_loop_completed")

        except Exception as e:
            logger.error("playback_loop_failed", error=str(e), exc_info=True)
            raise
