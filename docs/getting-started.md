# Getting Started

## Installation

### Prerequisites
- Windows 10/11 (macOS/Linux support planned)
- Python 3.11+
- Node.js 18+
- Rust (for development only)

### Download
Download the latest installer from [GitHub Releases](https://github.com/bit-faced/Qubes/releases).

Run the installer (`Qubes_x.x.x_x64-setup.exe`). The app auto-updates when new versions are available.

## First Run

### 1. Create Your Account
On first launch, you'll be prompted to:
1. Choose a username
2. Set a master password (encrypts all Qube keys)

**Important**: Your master password cannot be recovered. Store it safely.

### 2. Configure API Keys
Navigate to **Settings** and add API keys for AI providers you want to use:

| Provider | Required For | Get Key At |
|----------|--------------|------------|
| OpenAI | GPT-4, Whisper TTS/STT | [platform.openai.com](https://platform.openai.com) |
| Anthropic | Claude models | [console.anthropic.com](https://console.anthropic.com) |
| Google | Gemini models | [aistudio.google.com](https://aistudio.google.com) |
| Perplexity | Sonar models | [perplexity.ai](https://perplexity.ai) |
| DeepSeek | DeepSeek models | [platform.deepseek.com](https://platform.deepseek.com) |
| ElevenLabs | Voice cloning TTS | [elevenlabs.io](https://elevenlabs.io) |

**Minimum**: At least one AI provider (OpenAI or Anthropic recommended).

### 3. Create Your First Qube
1. Click **Create Qube** in the roster
2. Enter a name for your Qube
3. (Optional) Set personality traits, voice preferences
4. Click **Create**

Your Qube is now ready to chat!

## Quick Tour

### Chat Interface
- Type messages in the input box
- Qubes respond with AI-generated text
- Messages are stored in the Qube's memory chain (blockchain-like structure)

### Voice Mode
- Click the microphone icon to enable voice input (requires STT API key)
- Click the speaker icon to enable voice output (requires TTS API key)
- 11 waveform visualization styles available

### Multi-Qube Chat
- Select multiple Qubes from the roster
- They can converse with each other and you
- Each Qube maintains its own perspective and relationships

### Minting (Optional)
- Mint your Qube as a Bitcoin Cash CashToken NFT
- Provides immutable proof of identity on blockchain
- Costs ~$0.01 USD equivalent in BCH

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Enter` | Send message |
| `Shift+Enter` | New line in message |
| `Ctrl+M` | Toggle microphone |
| `Escape` | Cancel current action |

## Troubleshooting

### "No API key configured"
Add at least one AI provider API key in Settings.

### "Failed to start Python backend"
Ensure Python 3.11+ is installed and in PATH. The bundled app includes Python, but development mode requires system Python.

### Voice not working
- Check that you have valid API keys for TTS/STT providers
- Ensure microphone permissions are granted
- Try a different TTS/STT provider in Settings
