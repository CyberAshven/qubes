# Voice System

Qubes support text-to-speech (TTS) and speech-to-text (STT) across multiple providers.

## TTS Providers

| Provider | Quality | Cost | Latency | Local |
|----------|---------|------|---------|-------|
| OpenAI | Excellent | $0.015/1K chars | Low | No |
| ElevenLabs | Best | $0.30/1K chars | Medium | No |
| Google Gemini | Good | Free tier | Low | No |
| Google Cloud | Excellent | $0.004/1K chars | Low | No |
| Piper | Good | Free | Very Low | Yes |

### OpenAI TTS
**Voices**: alloy, echo, fable, onyx, nova, shimmer

```python
# From audio/tts_engine.py
client = AsyncOpenAI(api_key=api_key)
response = await client.audio.speech.create(
    model="tts-1",  # or "tts-1-hd" for higher quality
    voice="alloy",
    input=text,
    response_format="mp3",
    speed=1.0
)
```

### ElevenLabs
**Features**: Voice cloning, highest quality, many voices

```python
client = ElevenLabs(api_key=api_key)
audio = client.generate(
    text=text,
    voice="Rachel",
    model="eleven_multilingual_v2"
)
```

### Google Gemini TTS
**Features**: Free tier, good quality, fast

```python
model = genai.GenerativeModel("gemini-2.0-flash")
response = model.generate_content(
    f"<speak>{text}</speak>",
    generation_config={"response_modalities": ["AUDIO"]}
)
```

### Piper (Local)
**Features**: Runs locally, no API costs, privacy-preserving

```bash
# Install Piper
pip install piper-tts

# Download voice model
# Models at: https://github.com/rhasspy/piper/releases
```

```python
voice = PiperVoice.load("en_US-lessac-medium.onnx")
audio = voice.synthesize(text)
```

## STT Providers

| Provider | Accuracy | Cost | Streaming | Local |
|----------|----------|------|-----------|-------|
| OpenAI Whisper | Excellent | $0.006/min | No | No |
| DeepGram | Excellent | $0.0043/min | Yes | No |
| Whisper.cpp | Good | Free | No | Yes |

### OpenAI Whisper
```python
client = AsyncOpenAI(api_key=api_key)
response = await client.audio.transcriptions.create(
    model="whisper-1",  # or "whisper-large-v3-turbo"
    file=audio_file,
    language="en",
    response_format="verbose_json"
)
```

### DeepGram
**Features**: True streaming, real-time transcription

```python
client = Deepgram(api_key)
response = await client.transcription.prerecorded(
    source,
    {
        "language": "en",
        "punctuate": True,
        "model": "nova-2"
    }
)
```

### Whisper.cpp (Local)
**Features**: Runs locally, privacy-preserving, no costs

```bash
# Install whisper.cpp
# https://github.com/ggerganov/whisper.cpp

whisper-cpp --model ~/.whisper/ggml-base.bin audio.wav
```

## Configuration

### Per-Qube Settings
```yaml
voice:
  tts_provider: "openai"
  tts_voice: "alloy"
  tts_speed: 1.0
  stt_provider: "openai"
  auto_speak: false  # Auto-play responses
```

### Global Settings
```yaml
audio:
  default_tts_provider: "openai"
  default_stt_provider: "openai"
  sample_rate: 16000
  channels: 1
```

## Audio Recording

The GUI handles audio recording:

```typescript
// From qubes-gui/src/components/VoiceInput.tsx
const mediaRecorder = new MediaRecorder(stream, {
    mimeType: 'audio/webm;codecs=opus'
});

mediaRecorder.ondataavailable = (event) => {
    audioChunks.push(event.data);
};
```

Audio is sent to Python backend for transcription.

## Waveform Visualization

11 visualization styles available:

1. Classic Bars
2. Smooth Wave
3. Circular
4. Frequency Spectrum
5. Particle Wave
6. Mirrored Bars
7. Gradient Flow
8. Pulse Ring
9. Line Graph
10. Dot Matrix
11. Minimalist Line

## Voice Flow

```
User clicks microphone
        │
        ▼
Browser records audio (WebM/Opus)
        │
        ▼
Audio sent to Rust backend
        │
        ▼
Python transcribes via STT provider
        │
        ▼
Transcription returned as text message
        │
        ▼
Qube processes message
        │
        ▼
Response generated
        │
        ▼
TTS converts response to audio
        │
        ▼
Audio streamed to browser
        │
        ▼
Waveform visualization plays
```

## Cost Optimization

### Recommendations
1. Use OpenAI Whisper for STT (good quality/cost ratio)
2. Use OpenAI TTS for most cases
3. Use ElevenLabs only for premium voice needs
4. Use Piper/Whisper.cpp for local/private usage

### Cost Estimates (per minute of conversation)
| Setup | Cost |
|-------|------|
| OpenAI TTS + Whisper | ~$0.02 |
| ElevenLabs + Whisper | ~$0.10 |
| Piper + Whisper.cpp | $0.00 |

## Troubleshooting

### No audio output
- Check browser audio permissions
- Verify TTS API key is configured
- Check volume settings

### Transcription errors
- Ensure microphone permissions granted
- Check STT API key
- Try speaking more clearly
- Use a better microphone

### High latency
- Switch to faster TTS provider (OpenAI or Piper)
- Use streaming where supported
- Check network connection
