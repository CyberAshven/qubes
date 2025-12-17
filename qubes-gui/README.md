# Qubes GUI

A modern desktop application for interacting with Qubes AI agents, built with Tauri, React, and TypeScript.

## Features

### 🎨 Modern UI
- **Dashboard**: Real-time chat interface with your Qubes
- **Qube Manager**: Create, edit, and manage your AI agents
- **Blocks**: View and manage conversation memory blocks
- **Economy**: Track your Qube's blockchain activity
- **Settings**: Configure API keys and preferences

### 📎 File Upload System
- **Multi-File Support**: Upload multiple files at once
- **Vision AI**: Automatic image analysis with multi-provider support (Claude, GPT-4V, Gemini)
- **Document Support**: Upload text files (TXT, MD, JSON) of any size
- **Grid Preview**: Beautiful horizontal grid layout with individual file previews
- **Smart Processing**: Images analyzed sequentially, text files combined intelligently

### 🎤 Voice & Audio
- **Text-to-Speech**: Natural voice responses from your Qubes
- **Voice Input**: Speak to your Qubes with Web Speech API
- **Typewriter Effect**: TTS-synchronized letter-by-letter display
- **Audio Controls**: Built-in audio player with progress tracking

### 🎯 Advanced Features
- **Drag & Drop**: Reorder Qube cards in the Manager
- **Auto-Scroll**: Chat messages automatically scroll into view
- **Color-Coded**: Each Qube has unique colored borders and UI elements
- **State Persistence**: Files and settings persist across tab switches
- **Large File Support**: Handles files of any size via temp file strategy

## Tech Stack

- **Frontend**: React 19.2 + TypeScript + Vite
- **Desktop**: Tauri 2.4
- **State Management**: Zustand
- **UI Components**: Custom glass-morphism components
- **File Handling**: Tauri plugins (dialog, fs)
- **Drag & Drop**: @dnd-kit

## Recommended IDE Setup

- [VS Code](https://code.visualstudio.com/) + [Tauri](https://marketplace.visualstudio.com/items?itemName=tauri-apps.tauri-vscode) + [rust-analyzer](https://marketplace.visualstudio.com/items?itemName=rust-lang.rust-analyzer)

## Development

```bash
# Install dependencies
npm install

# Run in development mode
npm run tauri dev

# Build for production
npm run tauri build
```

## File Upload Usage

1. Click the 📎 button in the Dashboard chat
2. Select one or more files (images or documents)
3. Preview files in the grid layout
4. Remove individual files if needed
5. Type your message or question
6. Press Send - files will be processed automatically

**Supported Formats:**
- Images: PNG, JPG, JPEG, GIF, WEBP (analyzed with vision AI)
- Documents: TXT, MD, JSON (content included in message)

## Vision AI

When you upload images, the system automatically:
- Selects the best vision model based on your API keys
- Analyzes each image with the Qube's personality
- Combines multiple image analyses with clear numbering
- Handles large images via temporary file strategy
