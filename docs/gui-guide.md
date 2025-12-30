# GUI Guide

A walkthrough of the Qubes desktop application.

## Main Window

```
┌─────────────────────────────────────────────────────────────────┐
│  Qubes                                              [_][□][X]   │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌───────────────────────────────────────────┐ │
│  │             │  │                                           │ │
│  │   Qube      │  │                Chat Area                  │ │
│  │   Roster    │  │                                           │ │
│  │             │  │   Messages appear here                    │ │
│  │  [Alice]    │  │                                           │ │
│  │  [Bob]      │  │                                           │ │
│  │  [Charlie]  │  │                                           │ │
│  │             │  │                                           │ │
│  │  + Create   │  ├───────────────────────────────────────────┤ │
│  │             │  │  [Type a message...]           [🎤][📤]   │ │
│  │  ⚙ Settings │  └───────────────────────────────────────────┘ │
│  └─────────────┘                                                │
└─────────────────────────────────────────────────────────────────┘
```

## Qube Roster

The left sidebar shows all your Qubes.

### Actions
- **Click a Qube**: Select for chat
- **Right-click**: Context menu (rename, delete, export)
- **+ Create**: Create a new Qube
- **Multi-select**: Hold Ctrl and click multiple Qubes for group chat

### Qube Card
Each Qube shows:
- Avatar (AI-generated or default)
- Name
- Status indicator (online/processing)
- NFT badge (if minted)

## Chat Interface

### Single Qube Chat
Standard conversation with one Qube.

### Multi-Qube Chat
Select multiple Qubes to enable group conversation:
- All selected Qubes can respond
- Each Qube maintains its own perspective
- Relationships between Qubes evolve

### Message Types
- **User messages**: Your input (right-aligned, blue)
- **Qube messages**: AI responses (left-aligned, gray)
- **System messages**: Notifications (centered, muted)
- **Tool calls**: Actions taken (expandable, yellow)

## Voice Controls

### Microphone Button (🎤)
- Click to start recording
- Click again to stop and transcribe
- Requires STT provider configured

### Speaker Button (🔊)
- Toggle auto-play of responses
- Requires TTS provider configured

### Waveform Display
When voice is active, shows audio visualization:
- 11 styles available in Settings
- Animates during playback/recording

## Settings Panel

Access via gear icon (⚙) in roster.

### Tabs

**General**
- Username
- Theme (light/dark)
- Language

**API Keys**
- OpenAI
- Anthropic
- Google
- Perplexity
- DeepSeek
- ElevenLabs

**AI**
- Default model
- Fallback chain
- Temperature
- Max tokens

**Voice**
- TTS provider and voice
- STT provider
- Visualization style
- Auto-speak toggle

**Advanced**
- Data directory
- Log level
- Ollama endpoint

## Creating a Qube

1. Click **+ Create** in roster
2. Enter name (required)
3. Set personality traits (optional):
   - Tone: friendly, professional, casual, formal
   - Verbosity: concise, balanced, detailed
   - Emoji usage: none to frequent
4. Choose initial model (optional)
5. Click **Create**

## Qube Details

Click the info icon (ℹ) next to a Qube to see:

**Identity**
- Full ID (Name_QubeID)
- Public key fingerprint
- Created date
- NFT status

**Statistics**
- Total messages
- Memory chain size
- Session count

**Relationships**
- List of known entities
- Trust levels
- Status (stranger → best_friend)

**Skills**
- Solar system visualization
- XP progress
- Unlocked tools

## Minting a Qube

1. Select a Qube
2. Click **Mint NFT** button
3. Review minting details:
   - Cost (~$0.01 BCH)
   - What gets stored on-chain
4. Click **Continue**
5. Pay displayed BCH address
6. Wait for confirmation
7. NFT badge appears on Qube

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Enter | Send message |
| Shift+Enter | New line |
| Ctrl+M | Toggle microphone |
| Ctrl+, | Open settings |
| Escape | Cancel / Close modal |
| Ctrl+N | New Qube |
| Delete | Delete selected Qube (with confirmation) |

## Context Menus

### Qube Context Menu (right-click)
- **Rename**: Change display name
- **Duplicate**: Create copy with same settings
- **Export**: Download Qube data
- **Delete**: Remove Qube (with confirmation)

### Message Context Menu (right-click)
- **Copy**: Copy message text
- **Regenerate**: Re-generate AI response
- **View Block**: See raw block data

## Troubleshooting UI Issues

### Qube not responding
- Check API key configuration
- Verify internet connection
- Check if model is available

### Slow responses
- Try a faster model
- Reduce max tokens
- Check network speed

### Voice not working
- Check microphone permissions
- Verify TTS/STT API keys
- Try different provider

### Avatar not loading
- Avatar generation requires OpenAI API key
- Check internet connection
- Try regenerating avatar
