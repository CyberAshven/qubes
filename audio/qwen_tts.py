"""
Qwen3-TTS Provider

Local high-quality TTS with voice cloning and voice design capabilities.
Requires NVIDIA GPU with 4-6GB VRAM for 1.7B models, 2-3GB for 0.6B models.

Uses the qwen_tts package: pip install qwen-tts
"""

import asyncio
import struct
from pathlib import Path
from typing import AsyncIterator, Dict, Any, Optional
from datetime import datetime
import numpy as np

from audio.tts_engine import TTSProvider, VoiceConfig
from core.exceptions import AIError
from utils.logging import get_logger
from monitoring.metrics import MetricsRecorder

logger = get_logger(__name__)


class Qwen3TTSProvider(TTSProvider):
    """
    Local Qwen3-TTS provider with voice design and cloning.

    Supports three voice modes:
    - preset: Use predefined speakers (CustomVoice model) - Vivian, Ryan, etc.
    - designed: Create voices from natural language descriptions (VoiceDesign model)
    - cloned: Clone voices from 3-second audio samples (Base model)

    Model variants:
    - 1.7B: Higher quality, requires ~4-6GB VRAM
    - 0.6B: Lighter weight, requires ~2-3GB VRAM
    """

    # HuggingFace model identifiers
    MODELS = {
        "1.7B-CustomVoice": "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
        "1.7B-VoiceDesign": "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
        "1.7B-Base": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        "0.6B-CustomVoice": "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
        "0.6B-Base": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
        "Tokenizer": "Qwen/Qwen3-TTS-Tokenizer-12Hz",
    }

    # Predefined speakers available in CustomVoice model
    PRESET_SPEAKERS = ["Vivian", "Serena", "Uncle_Fu", "Dylan", "Eric", "Ryan", "Aiden", "Ono_Anna", "Sohee"]

    # Language code mapping (our codes -> Qwen3 format)
    LANGUAGE_MAP = {
        "en": "English",
        "zh": "Chinese",
        "ja": "Japanese",
        "ko": "Korean",
        "de": "German",
        "fr": "French",
        "ru": "Russian",
        "pt": "Portuguese",
        "es": "Spanish",
        "it": "Italian",
        "auto": "Auto",
    }

    # Supported languages
    SUPPORTED_LANGUAGES = ["en", "zh", "ja", "ko", "de", "fr", "ru", "pt", "es", "it"]

    # VRAM requirements (approximate, in GB)
    VRAM_REQUIREMENTS = {
        "1.7B": {"single": 5.0, "both": 9.0},
        "0.6B": {"single": 2.5, "both": 4.5},
    }

    # Maximum text length per generation to avoid VRAM overflow
    # Longer text is automatically chunked
    MAX_TEXT_LENGTH = 500  # ~500 chars is safe for most VRAM configs

    # Simplified TTS progress - just "generating" and "complete"
    STAGES = {
        "idle": {"progress": 0, "message": ""},
        "generating": {"progress": 50, "message": "Generating audio..."},
        "complete": {"progress": 100, "message": "Complete"},
        "error": {"progress": 0, "message": "Error"},
    }

    # Global singleton model instance - stays loaded across calls
    _global_model = None
    _global_model_type = None
    _global_model_lock = None

    def __init__(
        self,
        models_dir: Optional[Path] = None,
        model_variant: str = "1.7B",
        device: str = "cuda",
        use_flash_attention: bool = True
    ):
        """
        Initialize Qwen3-TTS provider.

        Args:
            models_dir: Directory containing downloaded models.
                       Defaults to ~/.qubes/models/qwen3-tts/
            model_variant: Model variant ("1.7B" or "0.6B")
            device: Computation device ("cuda" or "cpu")
            use_flash_attention: Whether to use FlashAttention2 for memory efficiency
        """
        self.models_dir = Path(models_dir or Path.home() / ".qubes" / "models" / "qwen3-tts")
        self.variant = model_variant
        self.device = device
        self.use_flash_attention = use_flash_attention

        # Initialize global lock if not already done
        if Qwen3TTSProvider._global_model_lock is None:
            Qwen3TTSProvider._global_model_lock = asyncio.Lock()

        # Progress tracking file
        self._progress_file = self.models_dir / ".tts_progress.json"

        logger.info(
            "qwen3_tts_provider_initialized",
            models_dir=str(self.models_dir),
            variant=model_variant,
            device=device,
            flash_attention=use_flash_attention,
            model_already_loaded=Qwen3TTSProvider._global_model is not None
        )

    # =========================================================================
    # PROGRESS TRACKING
    # =========================================================================

    def _update_progress(self, stage: str, extra_message: str = "") -> None:
        """Update progress file for UI polling."""
        import json
        stage_info = self.STAGES.get(stage, self.STAGES["idle"])
        progress_data = {
            "stage": stage,
            "progress": stage_info["progress"],
            "message": extra_message or stage_info["message"],
            "timestamp": datetime.now().isoformat(),
        }
        try:
            self._progress_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._progress_file, 'w') as f:
                json.dump(progress_data, f)
        except Exception as e:
            logger.debug("progress_update_failed", error=str(e))

    @classmethod
    def get_generation_progress(cls) -> Dict[str, Any]:
        """Get current TTS generation progress (for UI polling)."""
        import json
        progress_file = Path.home() / ".qubes" / "models" / "qwen3-tts" / ".tts_progress.json"
        try:
            if progress_file.exists():
                with open(progress_file, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return {"stage": "idle", "progress": 0, "message": ""}

    # =========================================================================
    # AVAILABILITY CHECK
    # =========================================================================

    def check_availability(self) -> Dict[str, Any]:
        """
        Check GPU availability and model status.

        Returns:
            Dict with availability information:
            - available: Whether Qwen3-TTS can be used
            - gpu_name: Name of detected GPU (if any)
            - vram_total_gb: Total VRAM in GB
            - vram_available_gb: Available VRAM in GB
            - recommended_variant: Recommended model variant based on VRAM
            - models_downloaded: List of downloaded model names
            - error: Error message (if not available)
        """
        result = {
            "available": False,
            "gpu_name": None,
            "vram_total_gb": None,
            "vram_available_gb": None,
            "recommended_variant": None,
            "models_downloaded": [],
            "error": None,
        }

        try:
            import torch

            if not torch.cuda.is_available():
                result["error"] = "No NVIDIA GPU detected. Qwen3-TTS requires CUDA."
                return result

            # Get GPU info
            result["gpu_name"] = torch.cuda.get_device_name(0)

            # Get VRAM info
            props = torch.cuda.get_device_properties(0)
            total_vram = props.total_memory / (1024**3)
            allocated_vram = torch.cuda.memory_allocated(0) / (1024**3)
            available_vram = total_vram - allocated_vram

            result["vram_total_gb"] = round(total_vram, 1)
            result["vram_available_gb"] = round(available_vram, 1)

            # Determine recommended variant
            if available_vram >= self.VRAM_REQUIREMENTS["1.7B"]["single"]:
                result["recommended_variant"] = "1.7B"
            elif available_vram >= self.VRAM_REQUIREMENTS["0.6B"]["single"]:
                result["recommended_variant"] = "0.6B"
            else:
                result["error"] = f"Insufficient VRAM. Need at least {self.VRAM_REQUIREMENTS['0.6B']['single']}GB, have {available_vram:.1f}GB available."
                return result

            # Check which models are downloaded
            result["models_downloaded"] = self.get_downloaded_models()
            result["available"] = True

        except ImportError:
            result["error"] = "PyTorch not installed. GPU features unavailable."
        except Exception as e:
            result["error"] = f"GPU check failed: {str(e)}"

        return result

    def get_downloaded_models(self) -> list[str]:
        """Get list of downloaded model names."""
        downloaded = []
        for name in self.MODELS.keys():
            if name == "Tokenizer":
                continue  # Skip tokenizer in model list
            model_path = self._get_model_path(name)
            if model_path.exists() and any(model_path.iterdir()):
                downloaded.append(name)
        return downloaded

    def _get_model_path(self, model_key: str) -> Path:
        """Get the local path for a model."""
        # Models are stored by their short name, not HuggingFace ID
        return self.models_dir / model_key

    # =========================================================================
    # MODEL LOADING
    # =========================================================================

    async def ensure_ready(self, voice_mode: str = "preset") -> None:
        """
        Ensure the appropriate model is loaded for the voice mode.

        Uses a global singleton model that persists across all provider instances.
        Only one model is loaded at a time to conserve VRAM.

        Args:
            voice_mode: "preset", "designed", or "cloned"
        """
        # Ensure lock exists
        if Qwen3TTSProvider._global_model_lock is None:
            Qwen3TTSProvider._global_model_lock = asyncio.Lock()

        async with Qwen3TTSProvider._global_model_lock:
            needed_model = self._get_model_type_for_mode(voice_mode)

            # Check if global model is already the right type
            if Qwen3TTSProvider._global_model_type == needed_model and Qwen3TTSProvider._global_model is not None:
                logger.debug("model_already_loaded", model_type=needed_model)
                return

            # Need to load/switch model
            await self._load_model(needed_model)

    def _get_model_type_for_mode(self, voice_mode: str) -> str:
        """Map voice mode to model type."""
        if voice_mode == "preset":
            return "CustomVoice"
        elif voice_mode == "designed":
            return "VoiceDesign"
        elif voice_mode == "cloned":
            return "Base"
        else:
            # Default to CustomVoice for preset speakers
            return "CustomVoice"

    async def _load_model(self, model_type: str) -> None:
        """Load a specific model type into global singleton."""
        model_key = f"{self.variant}-{model_type}"
        model_path = self._get_model_path(model_key)

        if not model_path.exists():
            self._update_progress("error", f"{model_type} model not downloaded")
            raise AIError(
                f"{model_type} model not downloaded. Download it from Settings.",
                context={"model": model_key, "path": str(model_path)}
            )

        # Check/free VRAM before loading
        required_vram = self.VRAM_REQUIREMENTS.get(self.variant, {}).get("single", 5.0)
        self._free_vram_if_needed(required_vram)

        logger.info("loading_qwen3_model", model=model_key, path=str(model_path))

        try:
            loop = asyncio.get_running_loop()
            model = await loop.run_in_executor(
                None, self._load_model_sync, str(model_path)
            )

            # Store in global singleton
            Qwen3TTSProvider._global_model = model
            Qwen3TTSProvider._global_model_type = model_type
            logger.info("qwen3_model_loaded", model=model_key, persistent=True)

        except Exception as e:
            self._update_progress("error", str(e))
            logger.error("qwen3_model_load_failed", model=model_key, error=str(e), exc_info=True)
            raise AIError(f"Failed to load {model_type} model: {e}", cause=e)

    def _load_model_sync(self, model_path: str):
        """
        Load a Qwen3-TTS model synchronously (called in thread pool).

        Uses the qwen_tts package for proper model loading.
        Applies torch.compile() for faster inference.
        """
        import os
        import sys
        import warnings
        import torch

        # Suppress SoX warning (it's optional)
        os.environ.setdefault('SOX_SKIP_VALIDATION', '1')
        warnings.filterwarnings('ignore', message='.*sox.*', category=UserWarning)
        warnings.filterwarnings('ignore', message='.*flash.*', category=UserWarning)

        # Suppress warnings from transformers/qwen_tts libraries
        os.environ.setdefault('TRANSFORMERS_VERBOSITY', 'error')
        os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '3')

        # Suppress C-level stdout/stderr during import and loading
        # This catches warnings from native libraries
        # Flush before redirecting to ensure no buffered output leaks through
        sys.stdout.flush()
        sys.stderr.flush()

        devnull_fd = os.open(os.devnull, os.O_WRONLY)
        old_stdout_fd = os.dup(1)
        old_stderr_fd = os.dup(2)

        # Also redirect Python's sys.stdout/stderr
        old_py_stdout, old_py_stderr = sys.stdout, sys.stderr
        sys.stdout = sys.stderr = open(os.devnull, 'w')

        # Track if torch.compile was applied (for logging after stdout restored)
        compile_status = {"applied": False, "error": None}

        try:
            os.dup2(devnull_fd, 1)
            os.dup2(devnull_fd, 2)

            from qwen_tts import Qwen3TTSModel

            # Build loading kwargs
            load_kwargs = {
                "device_map": self.device,
                "dtype": torch.bfloat16,
            }

            # Add FlashAttention2 if available and requested
            if self.use_flash_attention:
                try:
                    import flash_attn  # noqa: F401
                    load_kwargs["attn_implementation"] = "flash_attention_2"
                except ImportError:
                    pass  # Will be logged after stdout is restored

            model = Qwen3TTSModel.from_pretrained(model_path, **load_kwargs)

            # Apply torch.compile() for faster inference
            # Only works effectively on Linux with Triton installed
            # On Windows, torch.compile overhead exceeds benefits, so skip it
            compile_status["components"] = []

            # Check if Triton is available (required for GPU optimization)
            try:
                import triton  # noqa: F401
                has_triton = True
            except ImportError:
                has_triton = False

            if has_triton:
                # Linux with Triton: use reduce-overhead for CUDA graphs
                try:
                    if hasattr(model, 'model') and hasattr(model.model, 'talker'):
                        talker = model.model.talker

                        # Compile the main talker model
                        if hasattr(talker, 'model'):
                            talker.model = torch.compile(
                                talker.model,
                                mode="reduce-overhead",
                                fullgraph=False,
                            )
                            compile_status["components"].append("talker.model")

                        # Compile code_predictor - this is called 15 times per token
                        if hasattr(talker, 'code_predictor'):
                            talker.code_predictor = torch.compile(
                                talker.code_predictor,
                                mode="reduce-overhead",
                                fullgraph=False,
                            )
                            compile_status["components"].append("code_predictor")

                        compile_status["applied"] = True
                        compile_status["backend"] = "inductor"
                except Exception as compile_err:
                    compile_status["error"] = str(compile_err)
            else:
                # Windows or no Triton: skip torch.compile
                # The eager backend adds overhead without GPU benefits
                compile_status["skipped"] = True
                compile_status["reason"] = "Triton not available (required for GPU optimization)"

        finally:
            # Restore Python stdout/stderr first
            sys.stdout.close()  # Close the devnull file
            sys.stdout, sys.stderr = old_py_stdout, old_py_stderr

            # Restore OS-level stdout/stderr
            os.dup2(old_stdout_fd, 1)
            os.dup2(old_stderr_fd, 2)
            os.close(old_stdout_fd)
            os.close(old_stderr_fd)
            os.close(devnull_fd)

        # Log flash attention status after stdout restored
        if not self.use_flash_attention or "attn_implementation" not in load_kwargs:
            logger.debug("flash_attention_not_available")
        else:
            logger.info("using_flash_attention")

        # Log torch.compile status
        if compile_status.get("applied"):
            components = compile_status.get("components", [])
            backend = compile_status.get("backend", "unknown")
            logger.info("torch_compile_applied", components=components, backend=backend)
        elif compile_status.get("skipped"):
            logger.debug("torch_compile_skipped", reason=compile_status.get("reason"))
        elif compile_status.get("error"):
            logger.warning("torch_compile_failed", error=compile_status["error"])

        return model

    def _unload_current_model(self) -> None:
        """Unload the currently loaded model to free VRAM."""
        import gc

        if Qwen3TTSProvider._global_model is not None:
            del Qwen3TTSProvider._global_model
            Qwen3TTSProvider._global_model = None
            Qwen3TTSProvider._global_model_type = None

        # Force garbage collection and clear CUDA cache
        gc.collect()

        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass

        logger.info("qwen3_model_unloaded")

    def unload_models(self) -> None:
        """Unload all models to free VRAM."""
        self._unload_current_model()
        logger.info("qwen3_tts_models_unloaded")

    def _check_vram_available(self, required_gb: float) -> bool:
        """Check if enough VRAM is available for model loading."""
        try:
            import torch
            if not torch.cuda.is_available():
                return False

            # Get available VRAM
            device = torch.cuda.current_device()
            free_memory = torch.cuda.mem_get_info(device)[0]
            available_gb = free_memory / (1024**3)

            # Add 0.5GB buffer for safety
            return available_gb >= (required_gb + 0.5)

        except Exception as e:
            logger.warning("vram_check_failed", error=str(e))
            return True  # Assume available if check fails

    def _free_vram_if_needed(self, required_gb: float) -> None:
        """Try to free VRAM if needed by unloading models."""
        if not self._check_vram_available(required_gb):
            logger.info("freeing_vram_for_model_load", required_gb=required_gb)
            self._unload_current_model()

            # Also try to clear any cached tensors
            try:
                import torch
                import gc
                gc.collect()
                torch.cuda.empty_cache()
            except Exception:
                pass

    # =========================================================================
    # SYNTHESIS METHODS
    # =========================================================================

    async def synthesize_stream(
        self, text: str, voice_config: VoiceConfig
    ) -> AsyncIterator[bytes]:
        """
        Stream audio chunks for low-latency playback.

        Implements TTSProvider interface.
        """
        # Generate full audio first (Qwen3-TTS doesn't support true streaming yet)
        audio_bytes = await self._generate_from_config(text, voice_config)

        # Stream in chunks
        chunk_size = 4096
        for i in range(0, len(audio_bytes), chunk_size):
            yield audio_bytes[i:i + chunk_size]

    async def synthesize_file(
        self, text: str, voice_config: VoiceConfig, output_path: Path
    ) -> Path:
        """
        Generate complete audio file.

        Implements TTSProvider interface.
        """
        audio_bytes = await self._generate_from_config(text, voice_config)

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "wb") as f:
            f.write(audio_bytes)

        logger.info(
            "tts_file_saved",
            path=str(output_path),
            size_bytes=len(audio_bytes)
        )

        return output_path

    async def _generate_from_config(self, text: str, voice_config: VoiceConfig) -> bytes:
        """
        Generate audio based on voice configuration.

        Routes to appropriate method based on voice_mode.
        Automatically chunks long text to avoid VRAM overflow.
        """
        # Determine voice mode - default to "preset" for named speakers
        voice_mode = voice_config.voice_mode or "preset"
        language = voice_config.language or "en"
        speaker = voice_config.voice_id

        # If speaker is a known preset, use preset mode
        if speaker in self.PRESET_SPEAKERS:
            voice_mode = "preset"

        # Chunk long text to avoid VRAM overflow
        chunks = self._chunk_text(text)

        if len(chunks) == 1:
            # Single chunk - generate directly
            return await self._generate_single_chunk(
                chunks[0], voice_mode, speaker, language, voice_config
            )
        else:
            # Multiple chunks - generate and concatenate
            logger.info("chunking_long_text", chunks=len(chunks), total_chars=len(text))
            audio_parts = []
            for i, chunk in enumerate(chunks):
                logger.debug("generating_chunk", chunk=i+1, of=len(chunks))
                part = await self._generate_single_chunk(
                    chunk, voice_mode, speaker, language, voice_config
                )
                audio_parts.append(part)

            # Concatenate audio chunks
            return self._concatenate_wav_files(audio_parts)

    def _chunk_text(self, text: str) -> list[str]:
        """Split text into chunks at sentence boundaries to avoid VRAM overflow."""
        if len(text) <= self.MAX_TEXT_LENGTH:
            return [text]

        chunks = []
        current_chunk = ""

        # Split on sentence boundaries
        import re
        sentences = re.split(r'([.!?]+[\s\n]+)', text)

        # Recombine punctuation with sentences
        combined = []
        for i in range(0, len(sentences) - 1, 2):
            combined.append(sentences[i] + (sentences[i+1] if i+1 < len(sentences) else ''))
        if len(sentences) % 2 == 1:
            combined.append(sentences[-1])

        for sentence in combined:
            if len(sentence) > self.MAX_TEXT_LENGTH:
                # Single sentence too long - split on words
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                words = sentence.split()
                for word in words:
                    if len(current_chunk) + len(word) + 1 <= self.MAX_TEXT_LENGTH:
                        current_chunk += word + " "
                    else:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        current_chunk = word + " "
            elif len(current_chunk) + len(sentence) > self.MAX_TEXT_LENGTH:
                chunks.append(current_chunk.strip())
                current_chunk = sentence
            else:
                current_chunk += sentence

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks if chunks else [text]

    async def _generate_single_chunk(
        self,
        text: str,
        voice_mode: str,
        speaker: str,
        language: str,
        voice_config: VoiceConfig
    ) -> bytes:
        """Generate audio for a single text chunk."""
        if voice_mode == "preset":
            return await self.generate_custom_voice(
                text=text,
                speaker=speaker or "Vivian",
                language=language,
                instruct=voice_config.voice_design_prompt,
            )
        elif voice_mode == "designed":
            design_prompt = voice_config.voice_design_prompt or "A clear, natural speaking voice"
            return await self.generate_voice_design(
                text=text,
                instruct=design_prompt,
                language=language,
            )
        elif voice_mode == "cloned":
            if not voice_config.clone_audio_path:
                raise AIError("Voice cloning requires clone_audio_path")
            return await self.generate_voice_clone(
                text=text,
                ref_audio_path=Path(voice_config.clone_audio_path),
                ref_text=voice_config.clone_audio_text,
                language=language,
            )
        else:
            raise AIError(f"Unknown voice mode: {voice_mode}")

    def _concatenate_wav_files(self, wav_parts: list[bytes]) -> bytes:
        """Concatenate multiple WAV files into one with smooth transitions."""
        import io
        import soundfile as sf

        if not wav_parts:
            return b''

        if len(wav_parts) == 1:
            return wav_parts[0]

        # Read all parts
        audio_arrays = []
        sample_rate = None

        for i, wav_bytes in enumerate(wav_parts):
            buffer = io.BytesIO(wav_bytes)
            try:
                data, sr = sf.read(buffer)
            except Exception as e:
                logger.warning(f"Failed to read audio chunk {i}: {e}")
                continue

            if sample_rate is None:
                sample_rate = sr
            elif sr != sample_rate:
                logger.warning(f"Sample rate mismatch: chunk {i} has {sr}, expected {sample_rate}")

            audio_arrays.append(data)

        if not audio_arrays:
            return b''

        # Add small silence padding (50ms) between chunks to smooth transitions
        silence_samples = int(sample_rate * 0.05)  # 50ms of silence
        silence = np.zeros(silence_samples, dtype=audio_arrays[0].dtype)

        # Interleave audio with silence padding
        combined_parts = []
        for i, audio in enumerate(audio_arrays):
            combined_parts.append(audio)
            if i < len(audio_arrays) - 1:  # Don't add silence after last chunk
                combined_parts.append(silence)

        combined = np.concatenate(combined_parts)

        # Write back to WAV
        output = io.BytesIO()
        sf.write(output, combined, sample_rate, format='WAV')
        output.seek(0)
        return output.read()

    async def generate_custom_voice(
        self,
        text: str,
        speaker: str = "Vivian",
        language: str = "en",
        instruct: Optional[str] = None,
    ) -> bytes:
        """
        Generate speech using a predefined speaker (CustomVoice model).

        Args:
            text: Text to synthesize
            speaker: Speaker name (Vivian, Ryan, Eric, etc.)
            language: Language code (default: "en")
            instruct: Optional style instruction (e.g., "cheerful and energetic")

        Returns:
            Raw audio bytes (WAV format)
        """
        await self.ensure_ready(voice_mode="preset")

        logger.debug(
            "generating_custom_voice",
            text_length=len(text),
            speaker=speaker,
            language=language,
            instruct=instruct,
        )

        MetricsRecorder.record_ai_api_call("qwen3_tts", "custom_voice", "started")
        self._update_progress("generating")

        try:
            loop = asyncio.get_running_loop()
            audio_bytes = await loop.run_in_executor(
                None,
                self._synthesize_custom_voice_sync,
                text,
                speaker,
                language,
                instruct,
            )

            MetricsRecorder.record_ai_api_call("qwen3_tts", "custom_voice", "success")
            self._update_progress("complete")

            logger.info(
                "custom_voice_generated",
                text_length=len(text),
                speaker=speaker,
                audio_size=len(audio_bytes)
            )

            return audio_bytes

        except Exception as e:
            MetricsRecorder.record_ai_api_call("qwen3_tts", "custom_voice", "error")
            self._update_progress("error", str(e))
            logger.error("custom_voice_failed", error=str(e), exc_info=True)
            raise AIError(f"Custom voice synthesis failed: {e}", cause=e)

    def _synthesize_custom_voice_sync(
        self,
        text: str,
        speaker: str,
        language: str,
        instruct: Optional[str],
    ) -> bytes:
        """Synchronous custom voice synthesis (runs in thread pool)."""
        import os
        import time
        import torch

        # Map language code to Qwen3 format
        qwen_language = self.LANGUAGE_MAP.get(language.lower(), "Auto")

        # Suppress C-level stdout/stderr during generation
        # This catches "Setting pad_token_id..." and similar warnings
        devnull_fd = os.open(os.devnull, os.O_WRONLY)
        old_stdout_fd = os.dup(1)
        old_stderr_fd = os.dup(2)

        start_time = time.time()

        try:
            os.dup2(devnull_fd, 1)
            os.dup2(devnull_fd, 2)

            # Use inference_mode for maximum performance
            with torch.inference_mode():
                # Warmup CUDA if first generation
                if torch.cuda.is_available():
                    torch.cuda.synchronize()

                wavs, sr = Qwen3TTSProvider._global_model.generate_custom_voice(
                    text=text,
                    language=qwen_language,
                    speaker=speaker,
                    instruct=instruct or "",
                    max_new_tokens=2048,
                )

                # Ensure CUDA operations complete before timing
                if torch.cuda.is_available():
                    torch.cuda.synchronize()

        finally:
            os.dup2(old_stdout_fd, 1)
            os.dup2(old_stderr_fd, 2)
            os.close(old_stdout_fd)
            os.close(old_stderr_fd)
            os.close(devnull_fd)

        gen_time = time.time() - start_time
        logger.info(
            "tts_generation_timing",
            text_length=len(text),
            generation_seconds=round(gen_time, 2),
            chars_per_second=round(len(text) / gen_time, 1) if gen_time > 0 else 0,
        )

        # Convert numpy array to WAV bytes
        return self._numpy_to_wav(wavs[0], sr)

    async def generate_voice_design(
        self,
        text: str,
        instruct: str,
        language: str = "en",
    ) -> bytes:
        """
        Generate speech using voice design (natural language description).

        Args:
            text: Text to synthesize
            instruct: Natural language voice description
            language: Language code (default: "en")

        Returns:
            Raw audio bytes (WAV format)
        """
        await self.ensure_ready(voice_mode="designed")

        logger.debug(
            "generating_voice_design",
            text_length=len(text),
            instruct=instruct[:100] if instruct else None,
            language=language,
        )

        MetricsRecorder.record_ai_api_call("qwen3_tts", "voice_design", "started")
        self._update_progress("generating")

        try:
            loop = asyncio.get_running_loop()
            audio_bytes = await loop.run_in_executor(
                None,
                self._synthesize_voice_design_sync,
                text,
                instruct,
                language,
            )

            MetricsRecorder.record_ai_api_call("qwen3_tts", "voice_design", "success")
            self._update_progress("complete")

            logger.info(
                "voice_design_generated",
                text_length=len(text),
                audio_size=len(audio_bytes)
            )

            return audio_bytes

        except Exception as e:
            MetricsRecorder.record_ai_api_call("qwen3_tts", "voice_design", "error")
            self._update_progress("error", str(e))
            logger.error("voice_design_failed", error=str(e), exc_info=True)
            raise AIError(f"Voice design synthesis failed: {e}", cause=e)

    def _synthesize_voice_design_sync(
        self,
        text: str,
        instruct: str,
        language: str,
    ) -> bytes:
        """Synchronous voice design synthesis (runs in thread pool)."""
        import os

        # Map language code to Qwen3 format
        qwen_language = self.LANGUAGE_MAP.get(language.lower(), "Auto")

        # Suppress C-level stdout/stderr during generation
        devnull_fd = os.open(os.devnull, os.O_WRONLY)
        old_stdout_fd = os.dup(1)
        old_stderr_fd = os.dup(2)

        try:
            os.dup2(devnull_fd, 1)
            os.dup2(devnull_fd, 2)

            wavs, sr = Qwen3TTSProvider._global_model.generate_voice_design(
                text=text,
                language=qwen_language,
                instruct=instruct,
                max_new_tokens=2048,
            )
        finally:
            os.dup2(old_stdout_fd, 1)
            os.dup2(old_stderr_fd, 2)
            os.close(old_stdout_fd)
            os.close(old_stderr_fd)
            os.close(devnull_fd)

        # Convert numpy array to WAV bytes
        return self._numpy_to_wav(wavs[0], sr)

    async def generate_voice_clone(
        self,
        text: str,
        ref_audio_path: Path,
        ref_text: Optional[str] = None,
        language: str = "en",
    ) -> bytes:
        """
        Generate speech using voice cloning.

        Args:
            text: Text to synthesize
            ref_audio_path: Path to reference audio file (3+ seconds)
            ref_text: Transcript of the reference audio (optional)
            language: Language code (default: "en")

        Returns:
            Raw audio bytes (WAV format)
        """
        await self.ensure_ready(voice_mode="cloned")

        ref_audio_path = Path(ref_audio_path)
        if not ref_audio_path.exists():
            raise AIError(f"Reference audio file not found: {ref_audio_path}")

        logger.debug(
            "generating_voice_clone",
            text_length=len(text),
            ref_audio=str(ref_audio_path),
            language=language,
        )

        MetricsRecorder.record_ai_api_call("qwen3_tts", "voice_clone", "started")
        self._update_progress("generating")

        try:
            loop = asyncio.get_running_loop()
            audio_bytes = await loop.run_in_executor(
                None,
                self._synthesize_voice_clone_sync,
                text,
                ref_audio_path,
                ref_text,
                language,
            )

            MetricsRecorder.record_ai_api_call("qwen3_tts", "voice_clone", "success")
            self._update_progress("complete")

            logger.info(
                "voice_clone_generated",
                text_length=len(text),
                audio_size=len(audio_bytes)
            )

            return audio_bytes

        except Exception as e:
            MetricsRecorder.record_ai_api_call("qwen3_tts", "voice_clone", "error")
            self._update_progress("error", str(e))
            logger.error("voice_clone_failed", error=str(e), exc_info=True)
            raise AIError(f"Voice cloning synthesis failed: {e}", cause=e)

    def _synthesize_voice_clone_sync(
        self,
        text: str,
        ref_audio_path: Path,
        ref_text: Optional[str],
        language: str,
    ) -> bytes:
        """Synchronous voice cloning synthesis (runs in thread pool)."""
        import os
        import soundfile as sf

        # Load reference audio
        ref_audio, ref_sr = sf.read(str(ref_audio_path))

        # Map language code to Qwen3 format
        qwen_language = self.LANGUAGE_MAP.get(language.lower(), "Auto")

        # Suppress C-level stdout/stderr during generation
        devnull_fd = os.open(os.devnull, os.O_WRONLY)
        old_stdout_fd = os.dup(1)
        old_stderr_fd = os.dup(2)

        try:
            os.dup2(devnull_fd, 1)
            os.dup2(devnull_fd, 2)

            wavs, sr = Qwen3TTSProvider._global_model.generate_voice_clone(
                text=text,
                language=qwen_language,
                ref_audio=(ref_sr, ref_audio),
                ref_text=ref_text or "",
                max_new_tokens=2048,
            )
        finally:
            os.dup2(old_stdout_fd, 1)
            os.dup2(old_stderr_fd, 2)
            os.close(old_stdout_fd)
            os.close(old_stderr_fd)
            os.close(devnull_fd)

        # Convert numpy array to WAV bytes
        return self._numpy_to_wav(wavs[0], sr)

    def _numpy_to_wav(self, audio_array: np.ndarray, sample_rate: int) -> bytes:
        """Convert numpy audio array to WAV bytes."""
        import io
        import soundfile as sf

        # Write to bytes buffer
        buffer = io.BytesIO()
        sf.write(buffer, audio_array, sample_rate, format='WAV')
        buffer.seek(0)
        return buffer.read()

    async def generate_preview(
        self,
        speaker: Optional[str] = None,
        design_prompt: Optional[str] = None,
        clone_audio_path: Optional[Path] = None,
        clone_audio_text: Optional[str] = None,
        language: str = "en",
    ) -> bytes:
        """
        Generate a short preview (~10 words) for the voice.

        Args:
            speaker: For preset voices (CustomVoice model)
            design_prompt: For designed voices (VoiceDesign model)
            clone_audio_path: For cloned voices (Base model)
            clone_audio_text: For cloned voices
            language: Language code

        Returns:
            Audio bytes (WAV format)
        """
        preview_text = "Hello! This is a sample of how I will sound."

        if speaker and speaker in self.PRESET_SPEAKERS:
            return await self.generate_custom_voice(
                text=preview_text,
                speaker=speaker,
                language=language,
            )
        elif design_prompt:
            return await self.generate_voice_design(
                text=preview_text,
                instruct=design_prompt,
                language=language,
            )
        elif clone_audio_path:
            return await self.generate_voice_clone(
                text=preview_text,
                ref_audio_path=Path(clone_audio_path),
                ref_text=clone_audio_text,
                language=language,
            )
        else:
            # Default to Vivian preset
            return await self.generate_custom_voice(
                text=preview_text,
                speaker="Vivian",
                language=language,
            )


def check_qwen3_availability() -> Dict[str, Any]:
    """
    Standalone function to check Qwen3-TTS availability.

    Can be called without instantiating the provider.

    Returns:
        Dict with availability information
    """
    provider = Qwen3TTSProvider()
    return provider.check_availability()
