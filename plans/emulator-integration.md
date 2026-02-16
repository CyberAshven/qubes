# Retro Game Emulator Integration — Qube Battle System

## Context

Users want Qubes to battle each other in retro games. The app already has a chess implementation in the Games tab with human-vs-qube and qube-vs-qube modes. This plan adds SNES (and later GBA/Genesis/NES) emulation where Qubes play games by reading RAM state and making controller input decisions via their configured LLM.

**Two play modes:**
- **Turn-based (real-time):** Game pauses for input, LLM decides in 1-2s, feels like a real opponent. User can also play against their Qube.
- **Action (pre-rendered):** Pause-and-play loop — advance N frames, both Qubes decide, buffer frames, play back at 60fps.

**Key discovery:** Nostalgist.js does NOT support N64 (no mupen64plus core). Plan targets **SNES as primary**, with GBA/Genesis/NES as secondary. N64 is a future stretch goal requiring EmulatorJS or custom RetroArch builds.

**Emulator library:** [Nostalgist.js](https://nostalgist.js.org/) — JavaScript library built on RetroArch Emscripten builds. npm package, runs in WebView, exposes `getEmscriptenModule()` for RAM access, `saveState()`/`loadState()` for pause-and-play.

**Reference project:** [GamingAgent](https://github.com/lmgame-org/GamingAgent) (ICLR 2026) — LLM gaming agents benchmark. Validates the concept with Claude, GPT, Gemini, DeepSeek playing retro games.

---

## Architecture

```
ROM Library (user's local directory)
    ↓
GameLibrary.tsx (browse/select ROM)
    ↓
Nostalgist.js (WASM emulator in WebView canvas)
    ↓
RAM Reading (Module.HEAPU8 → per-game RAM map → structured JSON)
    ↓
Tauri invoke('request_emulator_move', { gameState })
    ↓
Rust → Python subprocess → QubeReasoner.process_emulator_action()
    ↓
LLM returns: { inputs: ["A", "RIGHT"], hold_duration: 5, commentary?: "Nice combo!" }
    ↓
Frontend injects inputs → emulator advances → repeat
```

The emulator runs **entirely in the frontend**. The backend is only involved for AI reasoning, TTS commentary, and game stats persistence.

### Turn-Based vs Action Mode

**Turn-based (real-time):** Game naturally pauses at decision points (RPG menus, turn-based combat). Emulator waits until input arrives. One qube plays, or user plays against qube. Feels like the existing chess flow.

**Action (pre-rendered):** Game never naturally pauses. We create an artificial pause-decide-play cycle:
1. Advance N frames → pause
2. Read RAM → send to both Qubes
3. Both decide (takes however long — latency irrelevant)
4. Queue inputs → advance next N frames
5. Buffer all frames → play back at 60fps

User sees smooth full-speed gameplay. The "thinking" happened offline.

---

## Phase 1: Emulator Foundation (MVP)

**Goal:** SNES emulator running in Games tab, human plays with keyboard.

### New Files

| File | Purpose |
|------|---------|
| `qubes-gui/src/components/games/emulator/EmulatorView.tsx` | Canvas wrapper + Nostalgist lifecycle + keyboard input |
| `qubes-gui/src/components/games/emulator/GameLibrary.tsx` | ROM directory browser with grid view |
| `qubes-gui/src/components/games/emulator/GameSetup.tsx` | Mode selection (human-vs-qube, qube-vs-qube, spectate) |
| `qubes-gui/src/components/games/emulator/EmulatorControls.tsx` | Play/Pause/Speed/SaveState buttons |
| `qubes-gui/src/hooks/useEmulatorStore.ts` | Zustand store for ROM library + active game state |

### Modified Files

| File | Changes |
|------|---------|
| `qubes-gui/package.json` | Add `nostalgist` dependency |
| `qubes-gui/src/components/tabs/GamesTab.tsx` | Add Chess/Emulator category toggle (currently chess-only, 886 lines) |
| `qubes-gui/src/types/index.ts` | Add `ROMEntry`, `EmulatorGameState`, `EmulatorSystem`, `RAMMap` types |
| `qubes-gui/src-tauri/src/lib.rs` | Add `scan_rom_directory` command (pure Rust, scans for .smc/.sfc/.gba/.nes files) |
| `qubes-gui/src-tauri/tauri.conf.json` | Add `'wasm-unsafe-eval'` to CSP for WASM execution |

### Key Details

- **Nostalgist.js** launches with `element: canvasRef.current` and `core: 'snes9x'`
- ROM loaded via `@tauri-apps/plugin-fs` `readFile()`, passed as `{ fileName, fileContent }` to Nostalgist
- SNES core WASM files bundled locally in `qubes-gui/public/emulator-cores/` to avoid CSP issues with CDN
- ROM directory stored in localStorage (non-sensitive, no Python round-trip needed)
- Directory picker uses existing `@tauri-apps/plugin-dialog` (`open({ directory: true })`) — already used in `CreateQubeModal.tsx` and `ChatInterface.tsx`
- `GamesTab.tsx` gets a `gameCategory` state: `'chess' | 'emulator'` — when `'emulator'`, renders `GameLibrary` instead of chess setup
- Existing `useQubeSelection` store already supports multi-select on games tab (line 166: `currentTab === 'games'`)
- `scan_rom_directory` implemented entirely in Rust — scans by extension (.smc/.sfc → snes, .gba → gba, .nes → nes, .md/.gen → genesis)

---

## Phase 2: RAM Reading & AI Input

**Goal:** Qube can read game state from RAM and make input decisions.

### New Files

| File | Purpose |
|------|---------|
| `qubes-gui/src/components/games/emulator/ramMaps/index.ts` | RAM map registry + `readGameState()` function |
| `qubes-gui/src/components/games/emulator/ramMaps/types.ts` | `RAMField`, `RAMMap` TypeScript types |
| `qubes-gui/src/components/games/emulator/ramMaps/smw.json` | Super Mario World RAM map |
| `qubes-gui/src/components/games/emulator/ramMaps/sf2.json` | Street Fighter II RAM map |

### Modified Files

| File | Changes |
|------|---------|
| `qubes-gui/src-tauri/src/lib.rs` | Add `request_emulator_move` command (30s timeout) |
| `gui_bridge.py` | Add `request-emulator-move` CLI dispatch + handler |
| `ai/reasoner.py` | Add `process_emulator_action()` method (modeled on `process_game_action()` at line 1071) |

### RAM Reading Approach

```javascript
const Module = nostalgist.getEmscriptenModule();
const ramPtr = Module._retro_get_memory_data(2);  // RETRO_MEMORY_SYSTEM_RAM
const ramSize = Module._retro_get_memory_size(2);  // SNES WRAM = 128KB
const wram = new Uint8Array(Module.HEAPU8.buffer, ramPtr, ramSize);
```

**Risk:** `_retro_get_memory_data` may not be exported in Nostalgist's Emscripten builds. Fallback: parse `saveState()` blob which contains full RAM. Test this early.

### RAM Map Format (per-game JSON)

```json
{
  "id": "sf2",
  "gameTitle": "Street Fighter II",
  "system": "snes",
  "fields": [
    { "address": "0x0468", "size": 1, "name": "p1_health", "type": "uint", "category": "player" },
    { "address": "0x0868", "size": 1, "name": "p2_health", "type": "uint", "category": "opponent" },
    { "address": "0x0401", "size": 1, "name": "round_number", "type": "uint", "category": "game_state" }
  ],
  "stateDescription": "Street Fighter II. P1 Health: {p1_health}/176, P2 Health: {p2_health}/176, Round: {round_number}"
}
```

`readGameState(wram, ramMap)` reads all fields and produces a flat JSON object sent to the LLM.

### AI Prompt Structure

```python
async def process_emulator_action(self, game_state, game_title, system):
    system_prompt = f"""You are {self.qube.name} playing {game_title} on {system}.

Game State:
{json.dumps(game_state, indent=2)}

Return ONLY valid JSON:
{{"inputs": ["A", "RIGHT"], "hold_duration": 5, "commentary": null}}

Valid buttons: UP, DOWN, LEFT, RIGHT, A, B, X, Y, L, R, START, SELECT
Only include commentary for significant moments (~10% of decisions)."""
```

Uses lower temperature (0.5) for more deterministic gameplay. No tool calling — just structured JSON output.

---

## Phase 3: Turn-Based Play

**Goal:** Qube plays turn-based games in real-time. User can play against their Qube.

### Implementation

- Turn-based detection: poll RAM every ~500ms, check if game is waiting for input (game-specific RAM field)
- When input needed: read full state → `invoke('request_emulator_move')` → inject returned inputs
- Human-vs-Qube: human uses keyboard, Qube controls player 2
- `GameSetup.tsx` reuses the qube selection pattern from chess (roster Ctrl+Click for 2 qubes)
- Add 2-3 more RAM maps (Pokemon, Zelda, etc.)

---

## Phase 4: Action Pre-Rendered Mode

**Goal:** Two Qubes fight in Street Fighter II. User watches playback.

### Loop

```
1. Advance 20 frames (333ms game-time)
2. saveState() — pause emulation
3. Read RAM → serialize game state
4. Send to BOTH qubes in parallel (Promise.all)
5. loadState() — restore to pause point
6. Queue both qubes' inputs for next 20 frames
7. Advance 20 frames with queued inputs
8. Repeat
9. Play back buffered frames at 60fps
```

### Key Details

- `FRAME_BATCH = 20` (tunable per game — faster for fighters, slower for platformers)
- Both qubes queried in parallel via two `invoke()` calls
- Commentary collected during processing, overlaid on playback
- Progress indicator: "Processing match... 45% complete"
- Spectator UI: full-screen emulator canvas + commentary sidebar
- Processing time estimate: ~12 minutes for a 90-second Street Fighter match (local model), plays back at full speed

---

## Phase 5: Commentary & TTS

**Goal:** Qubes speak about what's happening in the game.

### New Files

| File | Purpose |
|------|---------|
| `qubes-gui/src/components/games/emulator/GameCommentary.tsx` | Commentary panel + TTS queue |

### Commentary Sources

1. **Inline with decisions** — LLM's `commentary` field (~10% of responses, free — no extra API call)
2. **RAM triggers** — Health drops below 25%, boss appears, game over → `invoke('generate_game_commentary')`
3. **Post-game summary** — Full stats sent to Qube for a closing statement

### TTS Flow

Reuses existing pipeline:
```
commentary text → invoke('generate_speech') → audio file path → invoke('play_audio_native') → pw-play/ffplay
```

Throttle: max one spoken commentary per 15 seconds during action mode. Queue prevents overlapping speech.

---

## Phase 6: Polish & Additional Systems

- Add GBA (mgba core), Genesis (genesis_plus_gx), NES (fceumm) support
- Pokemon GBA RAM maps (perfect for turn-based AI battles)
- Save state management UI
- CRT shader toggle (Nostalgist `shader` option)
- Game stats persistence + GAME block creation (reuse existing `end_game` flow)
- Settings panel in SettingsTab: ROM directory, default system, commentary frequency
- User playing against other people's qubes (P2P network integration)

---

## What Already Exists & Can Be Reused

| Existing | Reuse For |
|----------|-----------|
| `useQubeSelection` (Zustand) | Qube selection for games — multi-select already enabled on games tab |
| `GlassCard` / `GlassButton` | All new UI components |
| `@tauri-apps/plugin-dialog` | ROM directory picker |
| `@tauri-apps/plugin-fs` | ROM file reading |
| `execute_with_secrets_timeout` (lib.rs) | Emulator move requests (30s timeout) |
| `QubeReasoner.process_game_action()` | Template for `process_emulator_action()` |
| `generate_speech` + `play_audio_native` | Game commentary TTS |
| `CelebrationProvider` | XP/achievement popups on game events |
| `GamePlayer` / `GameChatMessage` types | Reuse for emulator games |
| Chess game stats flow (`end_game` → GAME block) | Emulator game stats |

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| `_retro_get_memory_data` not exported in WASM build | Can't read RAM | Fallback: parse saveState() blob; or fork Emscripten build |
| WASM performance in Tauri WebView | Slow emulation | SNES is lightweight; benchmark early; reduce resolution if needed |
| LLM latency for action games | Slow processing | Pre-rendered mode decouples thinking from playback; use fast models |
| N64 not supported by Nostalgist.js | No N64 games | Start with SNES; evaluate EmulatorJS for N64 in future phase |
| Per-game RAM maps required | Only works for mapped games | Start with 3-5 well-documented games; community maps exist for hundreds |
| Subprocess overhead per decision | Slow for frequent decisions | 20-frame batches; consider long-running event watcher for game sessions later |
| CSP blocks WASM | Emulator won't load | Add `'wasm-unsafe-eval'` to CSP; bundle cores locally |
| Legal (ROMs) | Liability | App does NOT distribute ROMs; user provides their own; no download features |

---

## Verification

1. **Phase 1:** Launch SNES ROM in Games tab, play with keyboard, confirm 60fps
2. **Phase 2:** Console-log RAM state for Super Mario World, confirm values match expected (lives, coins, etc.)
3. **Phase 3:** Qube plays a turn-based game, makes sensible moves, commentary appears
4. **Phase 4:** Two Qubes fight in Street Fighter II, match plays back at full speed
5. **Phase 5:** Qube speaks commentary via Kokoro TTS during/after game
6. **Cross-platform:** Test on Linux (dev) and Windows (bundled) — ROM path resolution, WASM performance

---

## Resources

- [Nostalgist.js Documentation](https://nostalgist.js.org/)
- [Nostalgist.js getEmscriptenModule API](https://nostalgist.js.org/apis/get-emscripten-module/)
- [GamingAgent (ICLR 2026)](https://github.com/lmgame-org/GamingAgent)
- [EmulatorJS (for future N64)](https://emulatorjs.org/docs/systems/nintendo-64/)
- [Data Crystal SNES RAM Maps](https://datacrystal.tcrf.net/)
- [SMW Central Memory Map](https://www.smwcentral.net/?p=memorymap&game=smw&region=ram)
- [snes9x-fastlink (RAM API reference)](https://github.com/mattseabrook/snes9x-fastlink)
