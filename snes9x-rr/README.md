# SNES Emulator Integration for Qubes

This directory contains Lua scripts for integrating SNES gameplay with Qubes AI.

## Setup

1. **Download Snes9x-rr** from [GitHub](https://github.com/gocha/snes9x-rr/releases)
2. Extract `snes9x-x64.exe`, `lua5.1.dll`, and `lua51.dll` to this directory
3. Create a `roms/` folder and add your legally obtained ROM files

## Directory Structure

```
snes9x-rr/
├── snes9x-x64.exe      # Download separately
├── lua5.1.dll          # Download separately
├── lua51.dll           # Download separately
├── lua/
│   └── smw_test.lua    # RAM reading test script
└── roms/
    └── (your ROMs)     # Not committed - add your own
```

## Usage

1. Launch `snes9x-x64.exe`
2. Load a ROM: File → Load Game
3. Load Lua script: File → Lua Scripting → New Lua Script Window
4. Browse to `lua/smw_test.lua` and click Run

## RAM Addresses (Super Mario World)

See `lua/smw_test.lua` for documented memory addresses.
