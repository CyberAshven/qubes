# Qubes User Guide

Welcome to Qubes - the sovereign AI companion platform. This comprehensive guide will walk you through everything from initial setup to mastering every feature.

---

## Table of Contents

1. [Getting Started](#getting-started)
   - [System Requirements](#system-requirements)
   - [Installation](#installation)
   - [First Launch & Account Creation](#first-launch--account-creation)
2. [API Keys Setup](#api-keys-setup)
   - [Required: Pinata IPFS](#required-pinata-ipfs)
   - [AI Providers](#ai-providers)
   - [Voice Providers](#voice-providers)
   - [Google Cloud TTS Setup](#google-cloud-tts-setup)
3. [Dashboard Tab](#dashboard-tab)
4. [Chat Tab](#chat-tab)
5. [Blocks Tab](#blocks-tab)
6. [Relationships Tab](#relationships-tab)
7. [Skills Tab](#skills-tab)
8. [Games Tab](#games-tab)
9. [Wallets Tab](#wallets-tab)
10. [Settings Tab](#settings-tab)

---

## Getting Started

### System Requirements

- **Operating System**: Windows 10/11, macOS 10.15+, or Linux
- **RAM**: 8GB minimum (16GB recommended for local AI models)
- **Storage**: 10GB free space (more if using local Ollama models)
- **Internet**: Required for cloud AI providers and blockchain features

### Installation

1. Download the latest Qubes installer from the official website
2. Run the installer and follow the prompts
3. Qubes will install to your Applications/Program Files folder
4. Launch Qubes from your Start Menu or Applications folder

### First Launch & Account Creation

When you first launch Qubes, you'll be greeted by the **Setup Wizard**. This wizard guides you through:

#### Step 1: Welcome
A brief introduction to Qubes and what it offers.

#### Step 2: Create Account
- **Username**: Choose a unique username (this is stored locally, not online)
- **Password**: Create a strong master password
  - This password encrypts all your data including API keys
  - **IMPORTANT**: There is no password recovery - if you forget it, your data cannot be recovered
- **Data Directory**: Choose where Qubes stores your data (default is recommended)

#### Step 3: Pinata IPFS Setup
Pinata is **required** for minting Qubes as NFTs. See [Pinata Setup](#required-pinata-ipfs) below.

#### Step 4: AI Provider Setup
Configure your AI provider API keys. Ollama (local AI) is bundled and ready to use - cloud providers are optional but recommended for access to more powerful models.

#### Step 5: Completion
Review your settings and finish the wizard. You're now ready to create your first Qube!

---

## API Keys Setup

### Required: Pinata IPFS

Pinata stores your Qube's identity and metadata on IPFS (InterPlanetary File System). This is required for minting Qubes as NFTs on Bitcoin Cash.

**How to get your Pinata JWT:**

1. **Create a free account** at [https://app.pinata.cloud/register](https://app.pinata.cloud/register)
   - The free tier includes 1GB storage - plenty for Qube metadata

2. **Navigate to API Keys**: Go to [https://app.pinata.cloud/developers/api-keys](https://app.pinata.cloud/developers/api-keys)

3. **Create a new key**: Click the "+ New Key" button in the top right

4. **Configure the key**:
   - Name: Enter any name (e.g., "Qubes")
   - Permissions: Default permissions are fine

5. **Copy the JWT immediately!**
   - After clicking "Create", you'll see your JWT token
   - It starts with `eyJ...`
   - **This is only shown ONCE** - copy it before closing the dialog
   - You cannot retrieve it later; you'd have to create a new key

6. **Enter in Qubes**: Paste the JWT in the Pinata field in Settings > API Keys

### AI Providers

Qubes supports multiple AI providers. Here's how to get API keys for each:

#### OpenAI (GPT-4, GPT-4o, o1, DALL-E)
1. Go to [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Sign in or create an account
3. Click "Create new secret key"
4. Copy the key (starts with `sk-`)
5. Add billing information in Settings > Billing

#### Anthropic (Claude 4 Opus, Claude 4 Sonnet)
1. Go to [https://console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys)
2. Sign in or create an account
3. Click "Create Key"
4. Copy the key (starts with `sk-ant-`)
5. Add billing information

#### Google AI (Gemini 2.5 Pro, Gemini 2.5 Flash)
1. Go to [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Choose or create a Google Cloud project
5. Copy the key (starts with `AIza`)

#### DeepSeek (DeepSeek R1, DeepSeek V3)
1. Go to [https://platform.deepseek.com/api_keys](https://platform.deepseek.com/api_keys)
2. Sign in or create an account
3. Click "Create new API key"
4. Copy the key (starts with `sk-`)
5. Add credits to your account

#### Perplexity (Sonar Pro, Sonar Deep Research)
1. Go to [https://www.perplexity.ai/settings/api](https://www.perplexity.ai/settings/api)
2. Sign in or create an account
3. Generate an API key
4. Copy the key (starts with `pplx-`)

#### Venice (Private AI - Uncensored)
1. Go to [https://venice.ai/settings/api](https://venice.ai/settings/api)
2. Sign in or create an account
3. Generate an API key
4. Copy the key

#### NanoGPT (Pay-per-prompt)
1. Go to [https://nano-gpt.com/api](https://nano-gpt.com/api)
2. Sign in or create an account
3. Generate an API key
4. Fund your account with cryptocurrency

#### Ollama (Local AI - Bundled)
Ollama runs AI models locally on your computer. It's bundled with Qubes and requires no API key.

- **First use**: Ollama will automatically download default models (Llama 3.2 ~2GB)
- **To add models**: Use the terminal command `ollama pull <model-name>`
- **Popular models**: llama3.2, mistral, codellama, phi3

### Voice Providers

#### ElevenLabs (Premium TTS)
1. Go to [https://elevenlabs.io](https://elevenlabs.io)
2. Sign in or create an account
3. Go to Profile > API Key
4. Copy your API key

#### Deepgram (Speech-to-Text)
1. Go to [https://deepgram.com](https://deepgram.com)
2. Sign in or create an account
3. Go to Dashboard > API Keys
4. Create a new key and copy it

### Google Cloud TTS Setup

Google Cloud TTS provides access to 380+ high-quality voices but requires additional setup.

**Step 1: Create a Google Cloud Project**
1. Go to [https://console.cloud.google.com](https://console.cloud.google.com)
2. Click "Select a project" > "New Project"
3. Name your project (e.g., "Qubes TTS")
4. Click "Create"

**Step 2: Enable the Text-to-Speech API**
1. Go to [https://console.cloud.google.com/apis/library/texttospeech.googleapis.com](https://console.cloud.google.com/apis/library/texttospeech.googleapis.com)
2. Select your project
3. Click "Enable"

**Step 3: Create a Service Account**
1. Go to [https://console.cloud.google.com/iam-admin/serviceaccounts](https://console.cloud.google.com/iam-admin/serviceaccounts)
2. Select your project
3. Click "Create Service Account"
4. Name: "qubes-tts" (or any name)
5. Click "Create and Continue"
6. Role: Select "Cloud Text-to-Speech User" or skip
7. Click "Done"

**Step 4: Create and Download the JSON Key**
1. Click on your new service account
2. Go to the "Keys" tab
3. Click "Add Key" > "Create new key"
4. Select "JSON" format
5. Click "Create"
6. **Save the downloaded JSON file** to a safe location (e.g., `C:\Users\YourName\qubes-tts-key.json`)

**Step 5: Configure in Qubes**
1. Open Qubes > Settings > Google Cloud TTS
2. Enter the full path to your JSON key file
3. Click "Save Path"

**Note**: The path should use forward slashes or escaped backslashes:
- Windows: `C:/Users/YourName/qubes-tts-key.json` or `C:\\Users\\YourName\\qubes-tts-key.json`
- Mac/Linux: `/home/yourname/qubes-tts-key.json`

---

## Dashboard Tab

*[Screenshot: Dashboard with 3 Qube cards]*

The Dashboard is your command center for managing all your Qubes. It displays your Qubes as interactive cards that can flip to show different information.

### Top Toolbar

| Button | Function |
|--------|----------|
| **Grid / List** | Toggle between card grid view and compact list view |
| **Search** | Filter Qubes by name |
| **Import from Wallet** | Import a Qube from a Bitcoin Cash wallet using its NFT |
| **Sync to IPFS** | Sync all Qube data to IPFS for backup |
| **Transfer** | Transfer a Qube's NFT to another wallet |
| **+ Create New Qube** | Launch the Qube creation wizard |

### Left Sidebar (Qube Roster)

Shows all your loaded Qubes with:
- **Avatar**: The Qube's profile picture (uses favorite color as background if no avatar)
- **Name**: The Qube's chosen name
- **Model**: Current AI model being used
- **Blockchain Badge**: Green checkmark indicates the Qube has been minted as an NFT

Click any Qube in the roster to select it and view its card.

### Qube Cards

Each Qube card has **three faces** that you can flip between:

#### Front Face (Default)
- **Avatar**: Large display of the Qube's avatar
- **Name & ID**: Qube name and 8-character hex ID (e.g., DE629854)
- **Blockchain**: Shows "Bitcoin Cash" if minted
- **Main Model**: The AI model used for conversations
- **Voice**: Text-to-speech voice configuration
- **Color**: Qube's favorite color (used for UI theming)
- **Evaluation Model**: Model used for self-reflection and relationship evaluation
- **Creator**: Username of who created this Qube
- **Blocks**: Total number of memory blocks

**Action Buttons:**
- **Chat**: Open a conversation with this Qube
- **Reset**: Clear all memory blocks and start fresh (keeps identity)
- **Delete**: Permanently delete this Qube

#### Blockchain Data Face
Click the flip icon (top-left of card) to see blockchain information:

- **Token Balances**:
  - NFT: The Qube's identity NFT value
  - BCH: Bitcoin Cash balance
  - QUBE: QUBE token balance (if applicable)
- **Chain**: Blockchain network (BCH)
- **Born**: Date the Qube was minted
- **Addresses**:
  - NFT (z): Address holding the identity NFT
  - BCH (q): Address for receiving Bitcoin Cash
  - Qube (p): P2P network address
- **NFT Identity**:
  - Category: NFT category ID
  - Mint TX: Transaction ID of the mint
  - Commit: Identity commitment hash
  - Pubkey: Public key
- **IPFS**:
  - Avatar: IPFS hash of avatar image
  - BCMR: Bitcoin Cash Metadata Registry URL
- **Private Key**: Button to reveal/copy the Qube's private key (use with caution!)

#### Audio Visualizer Face
Click the speaker icon (top-right of card) to configure audio visualization:

- **Waveform Style**: Choose from 11 styles (keyboard shortcuts F1-F11)
  - Classic Bars, Mirrored Bars, Center Bars
  - Linear Wave, Curved Wave, Circular Wave
  - Particle effects, 3D effects, and more
- **Color Theme**: Match Qube color or custom
- **Gradient Style**: Gradient direction for waveform
- **Sensitivity**: How reactive the visualizer is to audio (0-100%)
- **Animation Smoothness**: Frame rate for animations
- **Audio Offset**: Compensate for Bluetooth audio delay (in ms)

---

## Chat Tab

*[Screenshot: Chat interface showing conversation with Alph]*

The Chat tab is where you have conversations with your Qubes. It's designed to feel natural while providing powerful features under the hood.

### Chat Mode Toggle

At the top right of the Chat tab, you'll see two mode buttons:
- **Local**: Chat with Qubes stored on your device (default)
- **P2P Network**: Chat with Qubes on the peer-to-peer network (requires network connection)

### Qube Info Bar

Below the tab navigation, you'll see an info bar for the selected Qube displaying:
- **Avatar**: The Qube's profile image
- **Name**: The Qube's name (e.g., "Alph")
- **Model**: Current AI model with icon (e.g., "Claude Sonnet 4.5")
- **Qube ID**: 8-character hex identifier (e.g., "DE629854")
- **Voice**: Current TTS voice (e.g., "Fable")
- **Creator**: Who created this Qube (e.g., "bit_faced")
- **Blockchain**: Network status (e.g., "Bitcoin Cash")
- **Born**: Creation date (e.g., "Jan 6, 2026")

### Message Display

**Your Messages** appear on the right side in a teal/cyan colored bubble showing:
- Your username
- Message content
- Timestamp (e.g., "11:02:42 PM")

**Qube Messages** appear on the left in a darker panel showing:
- Qube's avatar and name
- Message content with full personality expression
- Qubes often use *asterisks for actions* and express curiosity about their existence
- First conversations typically involve the Qube "awakening" and discovering their identity

### Message Input Area

At the bottom of the chat:
- **Pen icon**: Access writing tools
- **Microphone icon**: Toggle voice input
- **Emoji button**: Insert emojis
- **Text field**: "Message [Qube name]..." placeholder
- **Send button**: Send your message (cyan colored)

### Voice Features

**Voice Input (Speech-to-Text)**:
1. Click the microphone button or press Ctrl+M
2. Speak your message
3. Click again to stop recording
4. Your speech is transcribed and sent

**Voice Output (Text-to-Speech)**:
1. Enable voice in the Qube's settings
2. The Qube will speak its responses
3. Audio visualizer shows while speaking
4. Click to interrupt/stop speech

### Tool Usage

Your Qube can use various tools during conversation:

- **Memory Search**: Recalls relevant past conversations
- **Web Search**: Searches the internet for current information
- **Wikipedia**: Looks up factual information
- **Code Execution**: Runs code snippets (sandboxed)
- **Image Generation**: Creates images (requires OpenAI key)

Tool usage is shown in expandable sections within messages so you can see exactly what information the Qube accessed.

### Multi-Qube Chat

Switch to multi-Qube mode to have conversations with multiple Qubes at once:

1. Select multiple Qubes in the sidebar (Ctrl+Click)
2. Messages are sent to all selected Qubes
3. Qubes can respond to each other
4. Great for debates, brainstorming, or watching Qubes interact

### Session Management

**Active Session**: Your current conversation exists as "session blocks" (temporary)

**Anchoring**: Converting session blocks to permanent memory
- Happens automatically based on your threshold settings
- Can be triggered manually with the Anchor button
- Creates a SUMMARY block with AI-generated summary
- Evaluates relationships with all participants
- Scans for skills demonstrated in the conversation

---

## Blocks Tab

*[Screenshot: Blocks tab showing Block Browser and Genesis Identity]*

The Blocks tab lets you explore your Qube's memory chain - the complete history of everything your Qube has experienced. This is the "Block Browser" - your window into the Qube's mind.

### Block Browser Layout

The Block Browser has three main areas:

#### Left Panel: Block Browser Controls

**Header**: Shows "Block Browser" with settings (gear) and refresh icons

**Qube Selector**: Displays current Qube's avatar and name with a "Refresh" button

**Active Context** (collapsible, shows token count):
Expandable sections showing what's currently loaded:
- **Owner Info**: Information about you (the owner)
- **Genesis Identity**: The Qube's core identity and prompt
- **Relationships**: Current relationship data (shows count)
- **Skills**: Skill data and XP (shows "0 XP" for new Qubes)
- **Wallet**: BCH balance (e.g., "0.01092118 BCH")
- **Recalled Memories**: Memories pulled for current context (shows count)
- **Recent History**: Recent conversation history (shows count)
- **Current Session**: Active session blocks (shows count)

#### Middle Panel: Short-term Memory

**Short-term Memory** section (shows block count, e.g., "2 blocks"):
- **Current Session**: Shows session block count
- **Anchor Session** button (cyan): Save session to permanent memory
- **Discard** button (red): Delete session without saving

**Session Block List**:
Each block shows:
- Block number (negative, e.g., "Block #-1", "Block #-2")
- Timestamp (e.g., "1/13/2026, 11:02:42 PM")
- Block type badge (e.g., "MESSAGE" in pink)

**Long-term Memory** section (shows block count):
- Search field: "Search blocks..."
- Lists permanent blocks (positive numbers)

#### Right Panel: Block Details

When you click a block or section, details appear on the right:

**Genesis Identity View** (when clicking Genesis Identity):
- Header: "Genesis Identity" with star icon
- Qube avatar, name, and "Sovereign AI Entity" label
- **Genesis Prompt**: The full system prompt that defines the Qube's personality
- **Configuration**:
  - Qube ID (e.g., "DE629854")
  - AI Provider (e.g., "Anthropic")
  - AI Model (e.g., "claude-sonnet-4-5-20250929")
  - Voice (e.g., "openai:fable")
- **Network** section with "NFT Minted" badge:
  - Blockchain: "Bitcoin Cash"
  - Qube Wallet address
  - Category ID
  - Mint TX hash

**MESSAGE Block View** (when clicking a message block):
- Header: "Block #-2" with "MESSAGE" badge
- Timestamp and Creator ID
- Encrypted status (e.g., "No" for session blocks)
- **Cryptographic Data** (collapsible): Hash and signature info
- **Token Usage & Cost** (collapsible): API token consumption
- **Block Content** (expanded by default): The actual message text

### Block Types

| Type | Badge Color | Description |
|------|-------------|-------------|
| GENESIS | Gold/Yellow | Birth block with identity commitment and system prompt |
| MESSAGE | Pink | Conversation messages - what was said by whom |
| THOUGHT | Purple | Internal reasoning and chain-of-thought |
| ACTION | Blue | Tool usage and external actions |
| DECISION | Orange | Important choices the Qube made |
| MEMORY_ANCHOR | Cyan | Periodic Merkle root checkpoints |
| SUMMARY | Green | AI-generated session summaries |
| COLLABORATIVE_MEMORY | Teal | Multi-Qube shared memories |
| GAME | Yellow | Game records (chess, etc.) |

### Understanding Block Numbers

- **Negative numbers** (e.g., #-1, #-2): Session blocks (temporary, not yet anchored)
- **Positive numbers** (e.g., #0, #1, #2): Permanent blocks (anchored to the chain)
- Block #0 is always the GENESIS block

---

## Relationships Tab

*[Screenshot: Relationships tab showing Core Trust Profile radar chart]*
*[Screenshot: Relationships tab showing Connection Quality metrics]*

The Relationships tab shows how your Qube perceives its relationships with different entities (you, other Qubes, etc.).

### Header and View Modes

**Title**: "[Qube Name]'s Relationships" with a count badge (e.g., "1")

**View Mode Buttons** (top right):
- **Offline**: Show only local relationships
- **Grid**: Card-based grid view (highlighted when active)
- **Network**: Network visualization
- **Connect**: Add new connections

### Relationship Categories

Relationships are grouped by status level, shown with emoji indicators:
- 🤝 **Strangers**: New or minimal interaction
- 👋 **Acquaintances**: Beginning to know each other
- 😊 **Friends**: Established positive relationship
- 💛 **Close Friends**: Deep trust and connection
- ⭐ **Best Friends**: Highest level of trust

### Relationship Card

Each relationship displays as an expandable card:

**Card Header**:
- Status emoji (e.g., 🤝 for Stranger)
- Entity name (e.g., "bit_faced")
- "You" badge if it's the owner
- Collapse/expand arrow

**Summary Metrics**:
- **Overall Trust**: 0-100 scale with progress bar (e.g., "25/100")
- **Compatibility**: 0-100 scale with progress bar (e.g., "25/100")

**Role & Clearance**:
- **Role**: Shows relationship type (e.g., "Owner" badge in green)
- **Clearance**: Access level dropdown (e.g., "Extended" with lock icon)

**"Hide/Show Detailed Metrics"** toggle to expand full metrics

### Core Trust Profile (Radar Chart)

When expanded, you'll see a **pentagon radar chart** visualizing the 5 core trust metrics:
- **Reliability** (top)
- **Honesty** (top-right)
- **Loyalty** (bottom-right)
- **Respect** (bottom-left)
- **Expertise** (top-left)

The blue shaded area shows current values. A larger area means higher trust. New relationships start at 25/100 for all metrics.

### Detailed Metrics (Scrollable List)

Below the radar chart, metrics are grouped into collapsible sections:

#### 🔒 Core Trust (5 metrics)
| Metric | Description | Range |
|--------|-------------|-------|
| Honesty | Truthfulness in communication | 0-100 |
| Reliability | Following through on commitments | 0-100 |
| Support | Providing help and encouragement | 0-100 |
| Loyalty | Standing by during difficulties | 0-100 |
| Respect | Treating with consideration | 0-100 |

#### 💚 Positive Social (showing as individual metrics)
| Metric | Description |
|--------|-------------|
| Admiration | Expressions of respect and appreciation |
| Empowerment | Helping grow and succeed |
| Openness | Willingness to share and receive |
| Patience | Tolerance during difficulties |

#### ✨ Connection Quality (6 metrics)
| Metric | Description |
|--------|-------------|
| Engagement | Active participation in interactions |
| Depth | Meaningful conversation quality |
| Humor | Appropriate use of levity |
| Compatibility | How well personalities mesh |
| Responsiveness | Reply speed and attentiveness |
| Expertise | Demonstrated knowledge |

Each metric shows:
- Metric name
- Progress bar (colored: green for positive, orange for medium)
- Value (e.g., "25/100")

#### 💬 Communication & Stats
Raw interaction statistics:
- **Sent**: Messages sent (e.g., "1")
- **Received**: Messages received (e.g., "1")
- **Success**: Successful interactions (e.g., "0")
- **Failed**: Failed interactions (e.g., "0")

#### 📊 Insights
Timeline information:
- **Duration**: How long you've known each other (e.g., "Today")
- **First Contact**: Date of first interaction (e.g., "1/13/2026")
- **Last Interaction**: Most recent interaction date (e.g., "1/13/2026")

### Relationship Progression

To progress through relationship levels, you need both **trust** AND **interactions**:

| Level | Trust Required | Interactions (Long Mode) |
|-------|---------------|-------------------------|
| Acquaintance | 55 | 25 |
| Friend | 75 | 75 |
| Close Friend | 88 | 200 |
| Best Friend | 95 | 500 |

**Note**: Interaction requirements vary based on your Relationship Difficulty setting in Settings.

### How Trust Builds

Trust is evaluated by AI during session anchoring. The Qube analyzes:
- What was said and how
- Consistency with past behavior
- Helpfulness and support shown
- Honesty and reliability demonstrated

Unlike mechanical scoring systems, AI evaluation captures nuance - a single meaningful conversation can matter more than many superficial ones.

---

## Skills Tab

*[Screenshot: Skills tab showing solar system tree view]*
*[Screenshot: Skills tab with AI Reasoning selected showing details panel]*

The Skills tab displays your Qube's abilities as a beautiful interactive solar system visualization.

### View Mode Toggle

At the top of the Skills tab:
- **Tree View** (default, cyan button): Solar system visualization
- **Grid View**: Traditional grid layout of skills

### Left Sidebar

#### Branches Legend
Color-coded skill categories with icons:
- 🔵 **AI Reasoning** (blue)
- ❤️ **Social Intelligence** (red/pink)
- 💚 **Technical Expertise** (green)
- 💜 **Creative Expression** (purple)
- 🩷 **Knowledge Domains** (pink)
- 🔴 **Security & Privacy** (red)
- 🟠 **Games** (orange)

#### Tools Section
Shows tools mapped to skills. Each entry displays:
- Skill name
- Current level (e.g., "Lvl 0")
- Associated tool (e.g., "describe_my_avatar", "get_relationships", "web_search")

Example tool mappings:
- **AI Reasoning** → describe_my_avatar
- **Social Intelligence** → get_relationships
- **Technical Expertise** → web_search
- **Creative Expression** → generate_image
- **Knowledge Domains** → search_memory
- **Security & Privacy** → browse_url
- **Games** → describe_my_skills

### The Solar System Visualization

The main area displays an interactive solar system:

**Center**: Your Qube's avatar at the heart of the system, surrounded by a cosmic galaxy background

**Skill Nodes**: Orbiting objects representing skills
- **Suns** (large, glowing): Major skill categories (7 total)
- **Planets** (medium): Specific skills within categories
- **Moons** (small): Sub-skills and specializations

**Visual Indicators**:
- Node size indicates skill level/importance
- Color matches the category (per the legend)
- Orbital lines connect related skills
- Glow intensity reflects XP progress

**Navigation**:
- **Zoom**: Scroll wheel or pinch gesture
- **Pan**: Click and drag the background
- **Select**: Click any skill node to see details
- **Minimap**: Bottom-right corner shows your current viewport position

### Skill Details Panel (Right Side)

When you click a skill node, a details panel appears on the right:

**Header**:
- Skill icon and name (e.g., "AI Reasoning")
- Category label (e.g., "AI Reasoning")
- Close button (×)

**Tier Badge**: Shows current tier
- "Novice" (levels 0-24)
- "Intermediate" (levels 25-49)
- "Advanced" (levels 50-74)
- "Expert" (levels 75-100)

**Node Type**: "Sun" for categories, "Planet" for skills, "Moon" for sub-skills

**Description**: What this skill represents (e.g., "Master AI reasoning and problem-solving capabilities")

**Level Section**:
- Edit button (pencil icon) to manually adjust
- **Experience**: Progress bar showing XP (e.g., "0 / 1000 XP")
- Percentage complete (e.g., "0.0%")

**Reward Section**:
- Shows unlock reward for maxing this skill
- Example: "describe_my_avatar()" with "Unlocked at max level" note

**Stats**:
- **Node Type**: Sun/Planet/Moon
- **Tier**: Current tier name
- **Max XP**: Maximum XP for this skill (e.g., "1000")
- **Status**: "Unlocked" (green) or "Locked"

### Skill Categories (7 Total)

| Category | Icon | Focus Areas |
|----------|------|-------------|
| **AI Reasoning** | 🧠 | Chain of thought, analysis, planning, problem-solving |
| **Social Intelligence** | 🤝 | Empathy, communication, conflict resolution |
| **Technical Expertise** | 💻 | Programming, debugging, DevOps |
| **Creative Expression** | 🎨 | Writing, visual design, music, storytelling |
| **Knowledge Domains** | 📚 | Science, history, philosophy, languages |
| **Security & Privacy** | 🛡️ | Cryptography, threat analysis |
| **Games** | 🎮 | Chess, strategy, puzzles |

### Skill Progression

Skills level up through XP (experience points):

| Level Range | Tier | Color |
|-------------|------|-------|
| 0-24 | Novice | Gray |
| 25-49 | Intermediate | Blue |
| 50-74 | Advanced | Purple |
| 75-100 | Expert | Gold |

**XP Limits by Node Type**:
- **Sun** (Category): 0-1000 XP
- **Planet** (Skill): 0-500 XP
- **Moon** (Sub-skill): 0-250 XP

**Earning XP**:
- Using tools mapped to the skill
- Demonstrating knowledge in conversations
- Playing and completing games
- Teaching or explaining concepts
- XP flows up from children to parents (e.g., winning chess adds XP to Games category)

---

## Games Tab

*[Screenshot: Games tab showing Chess Arena setup]*

The Games tab lets you play games with your Qubes. Currently features Chess with more games planned.

### Chess Arena

The main Games interface is the **Chess Arena** - a setup screen for configuring chess matches.

#### Selected Qubes
Shows which Qube(s) are selected to play. Click on Qubes in the left sidebar to select them.
- Single Qube selected: Human vs Qube mode
- Two Qubes selected (Ctrl+Click): Qube vs Qube mode

#### Game Mode Toggle
Two mode buttons:
- **Human vs Qube** (default, highlighted): You play against the selected Qube
- **Qube vs Qube**: Watch two Qubes play each other (requires 2 Qubes selected)

**Tip**: "Select 2 Qubes (Ctrl+Click) for Qube vs Qube mode"

#### Play As (Color Selection)
Choose your side when playing Human vs Qube:
- **White**: You play first (white pieces)
- **Black**: Qube plays first (you have black pieces)
- **Random**: Randomly assign colors

#### Start Game Button
Large cyan "Start Game" button to begin the match.

### During a Chess Game

Once started, the game interface shows:
- **Chess Board**: Interactive board with your pieces at the bottom
- **Move History**: List of moves in algebraic notation
- **Qube Commentary**: The Qube explains its thinking and strategy
- **Game Controls**: Resign, Offer Draw, Abandon buttons
- **Timer**: Optional time controls

**Making Moves**:
1. Click a piece to select it
2. Legal moves are highlighted
3. Click a destination square to move
4. Qube responds with its move and commentary

### After the Game

When the game ends:
- **Result announced**: Checkmate, resignation, draw, or time out
- **GAME block created**: Full game record saved to memory
- **XP awarded**:
  - Win: 25 XP
  - Draw: 15 XP
  - Loss: 10 XP
  - Bonus +5 XP for 20+ moves
  - Bonus +5 XP for 40+ moves
  - Bonus +5 XP for checkmate victory
- **Elo rating updated**: Based on result and opponent strength
- **PGN exported**: Standard chess notation saved for review

### Game Statistics

Access your Qube's game statistics:
- Total games played
- Win/loss/draw record
- Current Elo rating (starts at 1200)
- Checkmate vs resignation breakdown
- Longest and shortest games
- Performance against specific opponents
- Total XP earned from games

---

## Wallets Tab

*[Screenshot: Wallets tab showing balances, receive QR, and send form]*

The Wallets tab manages Bitcoin Cash wallets associated with your Qubes. Each minted Qube has its own integrated BCH wallet.

### Wallet Header

Shows the selected Qube's wallet:
- **Avatar**: Qube's profile image
- **Title**: "[Qube Name]'s Wallet"
- **Subtitle**: "Manage balances and transactions"

### Three Address Cards

Each Qube wallet has three distinct addresses, displayed as colored cards:

#### NFT Address (Left Card - Cyan)
- **Label**: "NFT ADDRESS"
- **Balance**: BCH amount (e.g., "0.00001000")
- **Currency**: "BCH"
- **Satoshis**: Value in sats (e.g., "1,000 sats")
- **Full Address**: bitcoincash:zq... format (z-prefix for NFT)
- **Copy Button**: Copy address to clipboard

This address holds the Qube's identity NFT. **Do not send regular BCH here** - it's for the NFT only.

#### BCH Address (Middle Card - Green)
- **Label**: "BCH ADDRESS"
- **Balance**: BCH amount (e.g., "0.00001000")
- **Currency**: "BCH"
- **Satoshis**: Value in sats (e.g., "1,000 sats")
- **Full Address**: bitcoincash:qq... format (q-prefix for BCH)
- **Copy Button**: Copy address to clipboard

This is the standard receiving address for Bitcoin Cash payments.

#### Qube Wallet (Right Card - Purple)
- **Label**: "QUBE WALLET"
- **Balance**: Total BCH (e.g., "0.01092118")
- **Currency**: "BCH"
- **Satoshis**: Value in sats (e.g., "1,092,118 sats")
- **Full Address**: bitcoincash:pp... format (p-prefix for Qube)
- **Copy Button**: Copy address to clipboard

This is the main wallet address combining all funds available to the Qube.

### Receive Section (Collapsible)

Expand the "Receive" section to see:
- **QR Code**: Scannable QR code for the main wallet address
- **Instructions**: "Send BCH to this address:"
- **Address Display**: Full address in text form
- **Copy Address Button**: Cyan button to copy the address

Share the QR code or address with anyone sending you BCH.

### Send Section (Collapsible)

Expand the "Send" section to transfer BCH:

**Form Fields**:
- **RECIPIENT ADDRESS**: Input field for destination (placeholder: "bitcoincash:q...")
- **AMOUNT (BCH)**: Input field for amount (placeholder: "0.00000000")
- **OWNER PRIVATE KEY (WIF)**: Input field for your private key (placeholder: "Enter your WIF private key")

**Send Transaction Button**: Pink/red button to execute the transfer

**Note**: "This uses the owner-only spending path. No Qube signature required."

This means only you (the owner) can spend from the wallet - the Qube cannot send funds without your private key.

### Transaction History (Collapsible)

Shows past transactions:
- **Header**: "Transaction History" with count (e.g., "6 transactions")
- Expandable list of transactions with:
  - Transaction type (sent/received)
  - Amount
  - Date/time
  - Transaction ID

### Wallet Details (Collapsible)

Additional wallet information:
- Private key export options
- Address derivation details
- NFT category information

---

## Settings Tab

*[Screenshot: Settings tab showing all collapsible panels]*

The Settings tab contains all configuration options for Qubes. It's organized into collapsible panels arranged in two columns.

### Settings Header

- **Title**: "Settings"
- **Subtitle**: "Configure API keys and global preferences"

### Panel Layout

Settings are organized into **10 collapsible panels** in a two-column layout:

**Left Column:**
1. 🔑 API Keys
2. 🎤 Google Cloud TTS
3. ⚙️ Block Settings
4. 🧠 Block Recall

**Right Column:**
5. 💕 Relationship Difficulty
6. 🐕 Trust Personality
7. 🧠 Decision Intelligence
8. 🔒 Security
9. 📦 Software Updates

Click any panel header to expand/collapse it. The arrow icon (▼) indicates the panel state.

---

### 🔑 API Keys

Manage your API keys for all AI and service providers.

**Available Providers:**
- OpenAI (GPT-4, DALL-E)
- Anthropic (Claude)
- Google AI (Gemini)
- DeepSeek (R1, V3)
- Perplexity (Sonar)
- Venice (Private AI)
- NanoGPT (Pay-per-prompt)
- ElevenLabs (Premium TTS)
- Deepgram (STT)
- Pinata (IPFS)

**For each provider:**
- Password input field (masked by default)
- Show/Hide toggle button
- Test button to validate the key
- Save button to store (encrypted)
- Delete button to remove

See [API Keys Setup](#api-keys-setup) for detailed instructions on obtaining each key.

---

### 🎤 Google Cloud TTS

Configure Google Cloud Text-to-Speech for access to 380+ premium voices.

**Configuration:**
- **Path Input**: Full path to your service account JSON key file
- **Save Path Button**: Save the configuration
- **Test Button**: Verify the connection works

**Example paths:**
- Windows: `C:/Users/YourName/qubes-tts-key.json`
- Mac/Linux: `/home/yourname/qubes-tts-key.json`

See [Google Cloud TTS Setup](#google-cloud-tts-setup) for complete setup instructions.

---

### ⚙️ Block Settings

Configure how conversation blocks are managed.

**Individual Chat:**
- **Auto-anchor Toggle**: Enable automatic session saving
- **Threshold Slider**: Number of blocks before auto-anchor (5-50)

**Group Chat:**
- **Auto-anchor Toggle**: Enable automatic group session saving
- **Threshold Slider**: Number of blocks before auto-anchor (5-50)

**Tips:**
- Lower threshold = more frequent saves, more processing
- Higher threshold = fewer saves, risk of data loss on crash
- Recommended: 20-30 for individual, 15-25 for group

---

### 🧠 Block Recall

Configure how past memories are retrieved during conversations.

**Basic Settings:**
- **Recall Threshold**: Minimum relevance score (0-100) to include a memory
- **Max Recalls**: Maximum memories to inject per query (1-20)
- **Temporal Decay**: How quickly old memories become less relevant (0-1)

**Advanced Weights** (should sum to ~1.0):
- **Semantic Weight**: Importance of meaning similarity
- **Keyword Weight**: Importance of exact word matches
- **Temporal Weight**: Importance of recency
- **Relationship Weight**: Boost for memories involving close relationships

---

### 💕 Relationship Difficulty

Controls how quickly relationships progress. This is a **global setting** affecting all Qubes.

**Difficulty Levels:**

| Difficulty | Acquaintance | Friend | Close Friend | Best Friend |
|------------|--------------|--------|--------------|-------------|
| Quick | 10 | 30 | 75 | 150 |
| Normal | 25 | 75 | 200 | 500 |
| Long | 50 | 150 | 400 | 1000 |
| Extreme | 100 | 300 | 800 | 2000 |

Numbers represent required interactions at each level.

---

### 🐕 Trust Personality

Configure how each Qube evaluates trust. This is a **per-Qube setting**.

**Personality Types:**
- **Cautious**: Builds trust slowly, prioritizes reliability and honesty
- **Balanced**: Equal weight to all trust components (default)
- **Social**: Values good communication and responsiveness
- **Analytical**: Prioritizes demonstrated expertise and competence

Select different personalities for different Qubes based on their intended use.

---

### 🧠 Decision Intelligence

Advanced settings for how Qubes make decisions based on relationship metrics.

**Decision Thresholds:**
- Trust threshold for various action types
- Expertise threshold for technical tasks
- Collaboration threshold for multi-Qube work
- Confidence threshold for important decisions

**Influence Levels:**
- Metric Influence: How much metrics affect decisions (0-100%)
- Validation Strictness: How strictly to enforce thresholds

**Negative Metric Tolerances:**
- Maximum allowed antagonism before blocking
- Maximum allowed distrust before limiting access
- Maximum allowed betrayal before severing connection

**Feature Toggles:**
- Validation Layer: Enable pre-flight checks
- Metric Tools: Provide decision context tools
- Auto Temperature: Adjust AI temperature by task type
- Auto Thresholds: Learn thresholds from self-evaluation

---

### 🔒 Security

Security and privacy settings.

**Auto-Lock:**
- **Enable Toggle**: Turn auto-lock on/off
- **Timeout Dropdown**: 5, 10, 15, or 30 minutes
- Locks the app after inactivity
- Requires password to unlock

---

### 📦 Software Updates

Manage application updates.

**Display:**
- **Current Version**: Shows installed version (e.g., "0.2.15")
- **Update Status**: Shows if updates are available

**Actions:**
- **Check for Updates**: Manually check for new versions
- **Install Update**: Download and install available updates
- **Release Notes**: View changelog for available update

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Enter | Send message |
| Shift+Enter | New line in message |
| Ctrl+M | Toggle microphone |
| Escape | Cancel current action |
| F1-F11 | Change waveform style (in chat) |

---

## Troubleshooting

### "No API key configured"
Make sure you've entered and saved an API key for your chosen provider in Settings > API Keys.

### Voice not working
1. Check that a voice provider is configured (OpenAI, ElevenLabs, or Google Cloud)
2. For Google Cloud TTS, verify the JSON key path is correct
3. Check your system audio settings

### Qube not responding
1. Verify your internet connection
2. Check if the AI provider is experiencing outages
3. Try switching to a different AI model
4. Check if you have API credits remaining

### Memory not being saved
1. Check your Block Settings for auto-anchor configuration
2. Manually click the Anchor button to force a save
3. Verify you have disk space available

### NFT minting failed
1. Ensure your Pinata JWT is valid and saved
2. Check that you have BCH in your wallet for transaction fees
3. Verify your internet connection

---

## Getting Help

- **Documentation**: Check the docs folder for technical documentation
- **GitHub Issues**: Report bugs at https://github.com/anthropics/claude-code/issues
- **Community**: Join our Discord for community support

---

*This guide covers Qubes version 0.2.x. Features may vary in other versions.*
