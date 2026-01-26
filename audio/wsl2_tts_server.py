#!/usr/bin/env python3
"""
Qwen3-TTS Server for WSL2
Provides HTTP API for TTS generation with torch.compile optimization.
Supports both CustomVoice (presets) and VoiceDesign (voice descriptions).
"""

import os
import io
import time
import json
import logging
from pathlib import Path

# Suppress warnings before imports
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import torch
import soundfile as sf
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

# Global model instances
CUSTOM_VOICE_MODEL = None
VOICE_DESIGN_MODEL = None
MODEL_READY = False

# Check both WSL2 home and Windows mount for models
MODELS_DIR_WSL = Path.home() / ".qubes/models/qwen3-tts"
MODELS_DIR_WIN = Path("/mnt/c/Users/bit_f/.qubes/models/qwen3-tts")

def get_model_path(model_name: str) -> Path | None:
    """Find model path, checking WSL2 home first, then Windows mount."""
    for models_dir in [MODELS_DIR_WSL, MODELS_DIR_WIN]:
        path = models_dir / model_name
        if path.exists():
            return path
    return None

def load_models():
    """Load and compile the TTS models."""
    global CUSTOM_VOICE_MODEL, VOICE_DESIGN_MODEL, MODEL_READY

    torch.set_float32_matmul_precision("high")

    from qwen_tts import Qwen3TTSModel

    # Load CustomVoice model (for presets with style instructions)
    custom_voice_path = get_model_path("1.7B-CustomVoice")
    if custom_voice_path:
        logger.info("Loading CustomVoice model...")
        CUSTOM_VOICE_MODEL = Qwen3TTSModel.from_pretrained(
            str(custom_voice_path),
            device_map="cuda",
            dtype=torch.bfloat16,
        )

        # Apply torch.compile
        logger.info("Compiling CustomVoice model...")
        if hasattr(CUSTOM_VOICE_MODEL.model, "talker"):
            talker = CUSTOM_VOICE_MODEL.model.talker
            talker.model = torch.compile(talker.model, mode="default", dynamic=True)
            talker.code_predictor = torch.compile(talker.code_predictor, mode="default", dynamic=True)

        # Warmup
        logger.info("Warming up CustomVoice (this takes ~2 minutes)...")
        start = time.time()
        CUSTOM_VOICE_MODEL.generate_custom_voice(
            text="Warmup generation.",
            language="English",
            speaker="Vivian",
            instruct="",
        )
        logger.info(f"CustomVoice warmup complete in {time.time()-start:.1f}s")
    else:
        logger.warning("CustomVoice model not found")

    # Load VoiceDesign model (for voice descriptions)
    voice_design_path = get_model_path("1.7B-VoiceDesign")
    if voice_design_path:
        logger.info(f"Loading VoiceDesign model from {voice_design_path}...")
        VOICE_DESIGN_MODEL = Qwen3TTSModel.from_pretrained(
            str(voice_design_path),
            device_map="cuda",
            dtype=torch.bfloat16,
        )

        # Apply torch.compile
        logger.info("Compiling VoiceDesign model...")
        if hasattr(VOICE_DESIGN_MODEL.model, "talker"):
            talker = VOICE_DESIGN_MODEL.model.talker
            talker.model = torch.compile(talker.model, mode="default", dynamic=True)
            talker.code_predictor = torch.compile(talker.code_predictor, mode="default", dynamic=True)

        # Warmup
        logger.info("Warming up VoiceDesign...")
        start = time.time()
        VOICE_DESIGN_MODEL.generate_voice_design(
            text="Warmup generation.",
            language="English",
            instruct="A warm, friendly voice.",
        )
        logger.info(f"VoiceDesign warmup complete in {time.time()-start:.1f}s")
    else:
        logger.warning("VoiceDesign model not found")

    MODEL_READY = CUSTOM_VOICE_MODEL is not None or VOICE_DESIGN_MODEL is not None
    logger.info(f"TTS server ready! CustomVoice: {CUSTOM_VOICE_MODEL is not None}, VoiceDesign: {VOICE_DESIGN_MODEL is not None}")

class TTSHandler(BaseHTTPRequestHandler):
    """HTTP request handler for TTS API."""

    def log_message(self, format, *args):
        pass

    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def send_audio(self, audio_bytes):
        self.send_response(200)
        self.send_header("Content-Type", "audio/wav")
        self.send_header("Content-Length", len(audio_bytes))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(audio_bytes)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/health":
            self.send_json({
                "status": "ok",
                "ready": MODEL_READY,
                "custom_voice": CUSTOM_VOICE_MODEL is not None,
                "voice_design": VOICE_DESIGN_MODEL is not None,
            })
        elif path == "/speakers":
            self.send_json({
                "speakers": ["Vivian", "Serena", "Uncle_Fu", "Dylan", "Eric", "Ryan", "Aiden", "Ono_Anna", "Sohee"]
            })
        else:
            self.send_json({"error": "Not found"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path

        if path != "/generate":
            self.send_json({"error": "Not found"}, 404)
            return

        if not MODEL_READY:
            self.send_json({"error": "Model not ready"}, 503)
            return

        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)

            text = data.get("text", "")
            mode = data.get("mode", "preset")  # "preset" or "design"
            speaker = data.get("speaker", "Vivian")
            language = data.get("language", "English")
            instruct = data.get("instruct", "")

            if not text:
                self.send_json({"error": "No text provided"}, 400)
                return

            logger.info(f"Generating: mode={mode}, {len(text)} chars")

            start = time.time()
            torch.cuda.synchronize()

            if mode == "design":
                # Use VoiceDesign model
                if VOICE_DESIGN_MODEL is None:
                    self.send_json({"error": "VoiceDesign model not loaded"}, 503)
                    return

                logger.info(f"VoiceDesign: instruct='{instruct[:50]}...'")
                wavs, sr = VOICE_DESIGN_MODEL.generate_voice_design(
                    text=text,
                    language=language,
                    instruct=instruct,
                    max_new_tokens=2048,
                )
            else:
                # Use CustomVoice model (preset with optional style instruct)
                if CUSTOM_VOICE_MODEL is None:
                    self.send_json({"error": "CustomVoice model not loaded"}, 503)
                    return

                logger.info(f"CustomVoice: speaker={speaker}, instruct='{instruct[:30] if instruct else ''}'")
                wavs, sr = CUSTOM_VOICE_MODEL.generate_custom_voice(
                    text=text,
                    language=language,
                    speaker=speaker,
                    instruct=instruct,
                )

            torch.cuda.synchronize()
            gen_time = time.time() - start
            audio_duration = len(wavs[0]) / sr
            rtf = gen_time / audio_duration

            logger.info(f"Generated in {gen_time:.2f}s (audio={audio_duration:.2f}s, RTF={rtf:.2f})")

            # Convert to WAV bytes
            buffer = io.BytesIO()
            sf.write(buffer, wavs[0], sr, format="WAV")
            buffer.seek(0)

            self.send_audio(buffer.read())

        except Exception as e:
            logger.error(f"Generation error: {e}")
            import traceback
            traceback.print_exc()
            self.send_json({"error": str(e)}, 500)

def main():
    host = "0.0.0.0"
    port = 19533

    print(f"\n{'='*50}")
    print(f"  Qwen3-TTS Server for WSL2")
    print(f"  Listening on http://{host}:{port}")
    print(f"{'='*50}\n")

    load_models()

    server = HTTPServer((host, port), TTSHandler)

    print(f"\nServer running at http://localhost:{port}")
    print(f"API endpoints:")
    print(f"  GET  /health   - Check server status")
    print(f"  GET  /speakers - List available speakers")
    print(f"  POST /generate - Generate TTS audio")
    print(f"    mode: 'preset' (CustomVoice) or 'design' (VoiceDesign)")
    print(f"\nPress Ctrl+C to stop\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()

if __name__ == "__main__":
    main()
