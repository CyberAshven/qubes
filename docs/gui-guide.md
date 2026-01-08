# GUI Guide

A comprehensive walkthrough of the Qubes desktop application.

## Main Window Layout

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Qubes                                                      [_][□][X]    │
├──────────────────────────────────────────────────────────────────────────┤
│  ┌────────────┐  ┌──────────────────────────────────────────────────────┐│
│  │            │  │ [Dashboard] [Blocks] [Qubes] [Relations] [Skills]   ││
│  │   Qube     │  │ [Games] [Economy] [Settings]                        ││
│  │   Roster   │  ├──────────────────────────────────────────────────────┤│
│  │            │  │                                                      ││
│  │  [Avatar]  │  │              Tab Content Area                        ││
│  │   Alice    │  │                                                      ││
│  │  ○ Online  │  │                                                      ││
│  │            │  │                                                      ││
│  │  [Avatar]  │  │                                                      ││
│  │   Bob      │  │                                                      ││
│  │  ○ Online  │  │                                                      ││
│  │            │  │                                                      ││
│  │  + Create  │  │                                                      ││
│  │            │  │                                                      ││
│  └────────────┘  └──────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────────────┘
```

## Qube Roster (Left Sidebar)

The left sidebar displays all your Qubes with selection capabilities.

### Qube Card
Each Qube shows:
- **Avatar** - AI-generated image or letter fallback
- **Name** - Display name with favorite color accent
- **Status** - Online indicator
- **NFT Badge** - Shown if minted on Bitcoin Cash
- **Wallet Balance** - BCH balance if wallet configured

### Selection
- **Click** - Select single Qube
- **Ctrl+Click** - Add/remove from multi-selection
- **Shift+Click** - Select range

### Actions
- **+ Create Qube** - Opens creation modal
- **Right-click** - Context menu (edit, delete)

## Tab System

The main content area uses tabs for different functionality.

### Dashboard Tab (Chat)

The primary interaction interface with your Qubes.

#### Mode Toggle
Switch between:
- **Local** - Direct conversation with selected Qube(s)
- **P2P Network** - Chat with connected peers

#### Recall Last Button
Appears in top-right when:
- Chat is empty
- Single Qube selected
- Local mode active

Loads the most recent MESSAGE or SUMMARY block for context continuity.

#### Single Qube Chat
When one Qube selected:
```
┌──────────────────────────────────────────────────────────────┐
│                        Chat Messages                          │
│                                                               │
│  [Qube Avatar] Qube Name                          10:30 AM   │
│  Hello! How can I help you today?                            │
│                                                               │
│                                           You    10:31 AM    │
│                          What's the weather like?            │
│                                                               │
├──────────────────────────────────────────────────────────────┤
│  Active Context: ~1,234 tokens                    [Recall]   │
│  Recent: "Hello! How can I help..." → "What's the weather"  │
├──────────────────────────────────────────────────────────────┤
│  [Type a message...]                         [🎤] [📤]       │
└──────────────────────────────────────────────────────────────┘
```

#### Multi-Qube Chat
When 2+ Qubes selected:
- Each Qube can respond independently
- Messages tagged with Qube name/avatar
- Relationships evolve through interaction
- Qubes can address each other

#### Active Context Panel
Shows below messages:
- Estimated token count for context
- Preview of recent messages being sent to AI
- Configurable via Block Recall settings

### Blocks Tab (Block Browser)

Visual explorer for memory chain blocks.

```
┌─────────────────────────────────────────────────────────────┐
│  [Qube Avatar] Qube Name                                    │
│  ├── Filter: [All Types ▼] [Search...]                     │
│  │                                                          │
│  │  Block #47 - MESSAGE                      Jan 8, 2025   │
│  │  ┌──────────────────────────────────────────────────┐   │
│  │  │ User: What's the capital of France?              │   │
│  │  │ Response: Paris is the capital of France...      │   │
│  │  └──────────────────────────────────────────────────┘   │
│  │                                                          │
│  │  Block #46 - SUMMARY                      Jan 8, 2025   │
│  │  ┌──────────────────────────────────────────────────┐   │
│  │  │ Session summary: Discussed geography topics...   │   │
│  │  └──────────────────────────────────────────────────┘   │
│  │                                                          │
│  │  Block #0 - GENESIS                       Jan 1, 2025   │
│  │  ┌──────────────────────────────────────────────────┐   │
│  │  │ Birth timestamp, identity, initial prompt...     │   │
│  │  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

#### Block Types
- **GENESIS** - Birth block with identity and initial prompt
- **MESSAGE** - Conversation exchanges (user + response)
- **SUMMARY** - Session summaries with skills progression
- **DECISION** - Important decisions made
- **ACTION** - Actions taken by Qube
- **OBSERVATION** - Results and observations

#### Features
- Filter by block type
- Search block content
- View encrypted/decrypted content
- See Merkle proof data
- Export blocks

### Qubes Tab (Manager)

Create and manage your Qubes.

#### Qube Grid
Cards showing each Qube with:
- Avatar and name
- AI model in use
- Creation date
- Memory chain stats
- Quick actions

#### Create Qube Modal
1. **Name** - Required display name
2. **Genesis Prompt** - Personality and instructions
3. **AI Provider** - OpenAI, Anthropic, Google, etc.
4. **AI Model** - Specific model selection
5. **Voice Model** - TTS voice (optional)
6. **Favorite Color** - UI accent color
7. **Avatar** - Upload or AI-generate
8. **Wallet** - BCH address (optional)
9. **Encrypt Genesis** - Privacy option

#### Qube Configuration
Edit existing Qubes:
- Change AI model
- Update voice settings
- Modify favorite color
- Enable/disable TTS
- Set evaluation model

### Relationships Tab

Visualize connections between Qubes and entities.

#### Network Graph
Interactive visualization showing:
- Qubes as nodes
- Relationship lines between them
- Trust levels (color coded)
- Relationship status

#### Relationship Details
Click a connection to see:
- Overall trust score (0-100)
- 30 individual metrics
- Relationship status (stranger → best_friend)
- Interaction history
- Decay rate

### Skills Tab

View skill progression for each Qube.

#### Solar System View
Skills displayed as orbiting planets:
- Inner orbit: Mastered skills
- Outer orbits: Skills in progress
- Size indicates XP level

#### Skill Categories (7)
- Communication
- Analysis
- Creativity
- Technical
- Social
- Memory
- Reasoning

#### Skill Details
- 112 total skills
- XP progression tracking
- Tool unlocks at milestones
- Category mastery levels

### Games Tab

Play games with your Qubes.

#### Chess
- **Qube vs Human** - Play against your Qube
- **Qube vs Qube** - Watch Qubes compete
- **Statistics** - Win/loss/draw tracking per opponent
- **Move history** - Review past games

### Economy Tab

Wallet and earnings management.

#### Wallet Overview
- BCH balance display
- P2SH-32 address
- QR code for receiving
- Send functionality

#### Transaction History
- Recent transactions
- Send/receive indicators
- Confirmations
- Block explorer links

#### Earnings (Future)
- Memory market transactions
- Skill licensing revenue
- Collaboration rewards

### Settings Tab

Application configuration.

#### General
- Username
- Theme (dark mode default)
- Language preferences

#### API Keys
Securely store provider keys:
- OpenAI
- Anthropic
- Google AI
- Perplexity
- DeepSeek
- ElevenLabs
- Pinata (IPFS)

#### AI Configuration
- Default model selection
- Fallback chain setup
- Temperature settings
- Max token limits
- Block Recall depth
- Context token allocation

#### Voice
- TTS provider selection
- Voice model choice
- STT provider
- Visualization style (11 options)
- Auto-speak toggle

#### Advanced
- Data directory location
- Log level
- Ollama endpoint URL
- Developer options

## Voice Controls

### Microphone Button
- Click to start recording
- Click again to stop and transcribe
- Requires STT provider configured

### Speaker Button
- Toggle auto-play of responses
- Requires TTS provider configured

### Waveform Display
During voice activity:
- 11 visualization styles
- Animates during playback/recording

## Creating a Qube

1. Click **+ Create Qube** in roster
2. Enter required name
3. Write genesis prompt (personality/instructions)
4. Select AI provider and model
5. Choose voice settings (optional)
6. Pick favorite color for UI accent
7. Upload or generate avatar
8. Add wallet address (optional)
9. Toggle genesis encryption if desired
10. Click **Create**

## Minting a Qube (NFT)

1. Select a Qube
2. Navigate to Qubes tab
3. Click **Mint NFT** button
4. Review minting details:
   - Cost (~$0.01 BCH)
   - On-chain data stored
5. Click **Continue**
6. Pay displayed BCH address
7. Wait for blockchain confirmation
8. NFT badge appears on Qube

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Enter | Send message |
| Shift+Enter | New line in message |
| Ctrl+M | Toggle microphone |
| Ctrl+, | Open settings |
| Escape | Cancel / Close modal |
| Ctrl+N | New Qube |
| Delete | Delete selected Qube |
| Ctrl+Click | Multi-select Qubes |

## Context Menus

### Qube Context Menu (right-click)
- **Edit** - Modify Qube settings
- **Duplicate** - Create copy with same settings
- **Export** - Download Qube data
- **Delete** - Remove Qube (with confirmation)

### Message Context Menu (right-click)
- **Copy** - Copy message text
- **Regenerate** - Re-generate AI response
- **View Block** - See raw block data

## Troubleshooting

### Qube not responding
- Check API key configuration in Settings
- Verify internet connection
- Confirm model is available for your account

### Balance showing 0.00000000
- Wait for initial sync or reload
- Balance cache loads on startup

### Slow responses
- Try a faster/smaller model
- Reduce max tokens setting
- Check network speed

### Voice not working
- Check microphone permissions in OS
- Verify TTS/STT API keys configured
- Try different provider

### Avatar not loading
- Avatar generation requires OpenAI API key
- Check internet connection
- Try regenerating avatar in Qubes tab
