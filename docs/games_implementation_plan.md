# Games Tab Implementation Plan - Chess

## Overview
Add a "Games" tab to Qubes with Chess as the first game. Human vs Qube initially, designed for future Qube vs Qube (local and P2P).

---

## Design Philosophy

### What We Learned from the Block Analysis

Games are analogous to conversations:
- **Conversations**: MESSAGE blocks (temp) → SUMMARY block (permanent)
- **Games**: Move state (temp) → GAME block (permanent)

But there's a key difference: **we don't need MOVE blocks at all**.

Individual moves are:
- Captured in PGN (standard, compact, replayable)
- Not meaningful as standalone memories
- Just implementation detail of the game

What IS meaningful:
- The fact that a game was played (GAME block)
- The outcome (win/loss/draw)
- Key strategic decisions (preserved in GAME block)
- XP earned

### Simplified Architecture

```
Game Start
    │
    ▼
┌─────────────────────────────┐
│ GameState (in-memory)       │  ← Fast, real-time updates
│ + active_game.json backup   │  ← Crash recovery
└─────────────────────────────┘
    │
    │  (moves happen here, no blocks)
    │
    ▼
Game End
    │
    ▼
┌─────────────────────────────┐
│ GAME Block (permanent)      │  ← Single block captures everything
│ - PGN (complete move record)│
│ - Result, duration          │
│ - Key moments with reasoning│
│ - XP earned                 │
└─────────────────────────────┘
    │
    ▼
Delete active_game.json
Award XP to skill
```

---

## Block Types

### GAME Block (New)

Added to `BlockType` enum. Created when a game ends.

```python
# GAME block content schema
{
    "game_id": "uuid-string",
    "game_type": "chess",

    # Players
    "white_player": {
        "id": "human" | "Qube_ID",
        "type": "human" | "qube"
    },
    "black_player": {
        "id": "human" | "Qube_ID",
        "type": "human" | "qube"
    },

    # Result
    "result": "1-0" | "0-1" | "1/2-1/2" | "*",
    "termination": "checkmate" | "resignation" | "stalemate" | "draw_agreement" | "timeout" | "abandoned",

    # Game data
    "total_moves": 42,
    "pgn": "[Event \"Qubes Game\"]...",
    "duration_seconds": 1847,

    # Qube's key decisions (preserves reasoning without keeping all moves)
    "key_moments": [
        {
            "move_number": 12,
            "san": "Bxf7+",
            "reasoning": "Sacrifice bishop to expose king, leads to forced mate in 7"
        },
        {
            "move_number": 23,
            "san": "Qh5",
            "reasoning": "Setting up unstoppable mate threat on h7"
        }
    ],

    # XP
    "xp_earned": 35,

    # Future: P2P verification
    "move_signatures": []  # Optional, for cross-verified games
}
```

**Note**: No MOVE block type needed. Moves are tracked in-memory only.

---

## Game State Management

### GameState (In-Memory)

```python
@dataclass
class GameState:
    game_id: str
    game_type: str  # "chess"

    # Players
    white_player: Dict[str, str]  # {"id": "...", "type": "human|qube"}
    black_player: Dict[str, str]

    # Chess state
    fen: str  # Current position
    moves: List[Dict]  # Move history with reasoning

    # Metadata
    status: str  # "in_progress", "completed", "abandoned"
    started_at: float
    last_move_at: float
```

### Move Record (In GameState.moves)

```python
{
    "move_number": 1,
    "player": "white",
    "player_id": "human",
    "uci": "e2e4",
    "san": "e4",
    "fen_after": "...",
    "timestamp": 1704384000.0,
    "thinking": "..."  # Only for Qube moves
}
```

### Crash Recovery

GameState is persisted to `{qube_data_dir}/active_game.json` after each move:

```python
def save_game_state(self):
    """Atomic save for crash recovery"""
    path = self.qube.data_dir / "active_game.json"
    temp_path = path.with_suffix('.tmp')

    with open(temp_path, 'w') as f:
        json.dump(self.state.to_dict(), f)

    temp_path.replace(path)  # Atomic on POSIX, near-atomic on Windows

def load_active_game(self) -> Optional[GameState]:
    """Load game in progress (if any)"""
    path = self.qube.data_dir / "active_game.json"
    if path.exists():
        with open(path) as f:
            return GameState.from_dict(json.load(f))
    return None

def clear_active_game(self):
    """Remove active game file"""
    path = self.qube.data_dir / "active_game.json"
    path.unlink(missing_ok=True)
```

On Qube load, check for `active_game.json`. If found, offer resume.

---

## Tool Design

### chess_move Tool

**Always registered, context-checked in handler** - follows existing patterns.

```python
# In register_default_tools() - ai/tools/handlers.py
registry.register(ToolDefinition(
    name="chess_move",
    description="Make a chess move in an active game. Returns error if no game is active.",
    parameters={
        "type": "object",
        "properties": {
            "move": {
                "type": "string",
                "description": "Move in UCI notation (e.g., 'e2e4', 'e7e8q' for promotion)"
            },
            "reasoning": {
                "type": "string",
                "description": "Brief explanation of why you chose this move"
            }
        },
        "required": ["move"]
    },
    handler=lambda params: chess_move_handler(qube, params)
))
```

**Add to ALWAYS_AVAILABLE_TOOLS** in registry.py:
```python
ALWAYS_AVAILABLE_TOOLS: Set[str] = {
    # ... existing tools ...
    "chess_move",  # Always available, context checked in handler
}
```

**Handler-level context check** (matches existing patterns):
```python
async def chess_move_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a chess move in an active game"""
    try:
        # Context check - is there an active game?
        if not qube.game_manager or not qube.game_manager.has_active_game():
            return {
                "error": "No active chess game. Start a game first.",
                "success": False
            }

        move = params["move"]
        reasoning = params.get("reasoning", "")

        # Get active game and validate move
        game = qube.game_manager.get_active_game()
        # ... rest of handler
```

### Why This Approach?

The codebase has no built-in context-based tool filtering. Options were:
1. ❌ Modify registry filtering (complex, breaks patterns)
2. ✅ Handler-level check (simple, matches existing tools)

Adding to ALWAYS_AVAILABLE_TOOLS + handler check is the cleanest approach.

---

## XP System

### XP Calculation

```python
def calculate_chess_xp(result: str, total_moves: int, qube_color: str) -> int:
    """
    Calculate XP earned from a chess game

    Base XP:
    - Win: 25 XP
    - Draw: 15 XP
    - Loss: 10 XP

    Bonuses:
    - Game reached 20+ moves: +5 XP
    - Game reached 40+ moves: +5 XP
    - Checkmate (not resignation): +5 XP
    """
    # Determine if Qube won
    qube_won = (result == "1-0" and qube_color == "white") or \
               (result == "0-1" and qube_color == "black")
    qube_drew = result == "1/2-1/2"

    # Base XP
    if qube_won:
        xp = 25
    elif qube_drew:
        xp = 15
    else:
        xp = 10

    # Length bonuses (encourages full games)
    if total_moves >= 20:
        xp += 5
    if total_moves >= 40:
        xp += 5

    return xp
```

### Skill Integration

Chess skill already exists in skill_definitions.py (line 175) as a "planet" under the "games" category.

```python
# In end_game():
from utils.skills_manager import SkillsManager

skills_manager = SkillsManager(qube.data_dir)
result = skills_manager.add_xp(
    skill_id="chess",
    xp_amount=xp_earned,
    evidence_description=f"Completed chess game: {result} in {total_moves} moves"
)
```

**Note:** The chess skill has `tool_reward="chess_move"` in skill_definitions, but since chess_move is in ALWAYS_AVAILABLE_TOOLS, it's available regardless of skill level. This is intentional - you need to play to level up.

---

## Pre-Game: Player Selection (Sidebar-Driven)

Player selection uses the existing Qube Roster sidebar, leveraging patterns from group chat multi-select.

### Selection States

| Sidebar Selection | Games Tab Shows |
|-------------------|-----------------|
| None | "Select a Qube to play chess" |
| 1 Qube (click) | Human vs Qube setup |
| 2 Qubes (Ctrl+click) | Qube vs Qube setup |
| 3+ Qubes | "Select 1 or 2 Qubes for chess" |

### Human vs Qube (Single Select)

```
┌──────────────┐  ┌─────────────────────────────────────────────┐
│ Qube Roster  │  │  Games                                      │
├──────────────┤  ├─────────────────────────────────────────────┤
│              │  │                                             │
│  ● Alph      │──│  🎮 Challenge Alph to Chess                 │
│  ○ Anastasia │  │                                             │
│  ○ Bob       │  │     [♔ White]  [🎲 Random]  [♚ Black]      │
│              │  │                                             │
│              │  │  ───────────────────────────────────────    │
│              │  │                                             │
│              │  │  📜 Your History vs Alph                    │
│              │  │  ✓ Win  (White) +35 XP   Jan 4             │
│              │  │  ✗ Loss (Black) +10 XP   Jan 3             │
│              │  │                                             │
└──────────────┘  └─────────────────────────────────────────────┘
```

### Qube vs Qube (Multi-Select with Ctrl+Click)

```
┌──────────────┐  ┌─────────────────────────────────────────────┐
│ Qube Roster  │  │  Games                                      │
├──────────────┤  ├─────────────────────────────────────────────┤
│              │  │                                             │
│  ● Alph      │──│  🎮 Qube vs Qube                            │
│  ○ Anastasia │  │                                             │
│  ● Bob       │──│  ♔ Alph (White)  vs  ♚ Bob (Black)         │
│              │  │                                             │
│              │  │     [🎲 Swap Colors]    [Start Match]      │
│              │  │                                             │
│              │  │  ───────────────────────────────────────    │
│              │  │                                             │
│              │  │  📜 Alph vs Bob History                     │
│              │  │  (no previous games)                        │
│              │  │                                             │
└──────────────┘  └─────────────────────────────────────────────┘

First Ctrl+Click = White, Second Ctrl+Click = Black
[Swap Colors] button exchanges their positions
```

### Implementation Notes

**1. Add 'games' to selectionByTab initialization:**
```typescript
// In useQubeSelection.tsx
selectionByTab: {
  dashboard: [],
  blocks: [],
  qubes: [],
  relationships: [],
  skills: [],
  economy: [],
  settings: [],
  connections: [],
  games: [],  // NEW
}
```

**2. Enable multi-select for games tab:**
```typescript
// In useQubeSelection.tsx - update isMultiSelectAllowed()
isMultiSelectAllowed: () => {
  const { currentTab } = get();
  return currentTab === 'dashboard' || currentTab === 'economy' || currentTab === 'games';
  //                                                              ^^^^^^^^^^^^^^^^^ NEW
}
```

**3. Games tab interprets selection:**
```typescript
const gamesSelection = selectionByTab.games; // string[] of qube_ids

if (gamesSelection.length === 0) {
  // Show "Select a Qube" prompt
} else if (gamesSelection.length === 1) {
  // Human vs Qube mode
  const opponent = gamesSelection[0];
} else if (gamesSelection.length === 2) {
  // Qube vs Qube mode
  const [whiteQube, blackQube] = gamesSelection;
} else {
  // Too many selected - show error
}
```

### No Qube Selected

```
┌─────────────────────────────────────────────────────────────┐
│  Games                                                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│        Select a Qube from the sidebar to play chess        │
│                                                             │
│                    ← Click a Qube                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

### Color Selection Options

| Option | Behavior |
|--------|----------|
| White | Human plays White (moves first), Qube plays Black |
| Black | Human plays Black, Qube plays White (moves first) |
| Random | 50/50 coin flip, revealed with animation |

### Random Selection Animation

```typescript
// Fun reveal for random selection
async function randomColorSelection(): Promise<'white' | 'black'> {
  // Show coin flip animation for 1.5 seconds
  setShowCoinFlip(true);
  await sleep(1500);

  const result = Math.random() < 0.5 ? 'white' : 'black';
  setShowCoinFlip(false);
  setSelectedColor(result);

  // Qube reacts to the result
  await requestQubeReaction(result === 'white'
    ? "Human gets to play White (first move)"
    : "I get to play White! First move advantage is mine."
  );

  return result;
}
```

---

## End-to-End Flow (Refined)

### 1. Game Creation

```
User clicks "White" to play as White against Alph
         │
         ▼
create_chess_game(qube_id="Alph_123", qube_plays_as="black")
         │
         ▼
GameManager.create_game():
  1. Create GameState in memory
  2. Save to active_game.json
  3. Return game_id + initial FEN
         │
         ▼
Frontend renders board (White at bottom, user's turn)
```

### 2. Human Makes Move

```
User drags piece e2→e4
         │
         ▼
make_human_move(qube_id, game_id, "e2e4")
         │
         ▼
GameManager.record_move():
  1. Validate move with python-chess
  2. Update GameState.fen
  3. Append to GameState.moves
  4. Save to active_game.json
  5. Check if game over
  6. Return new FEN + game status
         │
         ▼
Frontend updates board, shows "Alph is thinking..."
```

### 3. Qube Makes Move

```
request_qube_move(qube_id, game_id)
         │
         ▼
Build prompt with game context:
  "You're playing chess as Black against your creator.
   Current position (FEN): rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1
   Moves so far: 1. e4

   It's your turn. Analyze the position and make your move."
         │
         ▼
AI reasons about position, calls chess_move tool:
  chess_move(move="e7e5", reasoning="Classical response, fighting for center control")
         │
         ▼
chess_move_handler():
  1. Get active game from GameManager
  2. Validate it's Qube's turn
  3. Validate move is legal
  4. Call GameManager.record_move()
  5. If move is interesting, flag as key_moment
  6. Return result
         │
         ▼
Frontend receives move, animates piece, checks for game end
```

### 4. Game Continues

```
Human move → record_move → save state → return
Qube move  → AI reasoning → chess_move → record_move → save state → return
Human move → record_move → save state → return
...
```

### 5. Game Ends

```
Checkmate detected (or resignation/draw)
         │
         ▼
end_chess_game(qube_id, game_id, result="0-1", termination="checkmate")
         │
         ▼
GameManager.end_game():
  1. Generate PGN from moves
  2. Extract key_moments (moves with reasoning, high-impact moves)
  3. Calculate XP
  4. Build GAME block content
  5. Return game summary
         │
         ▼
gui_bridge creates GAME block:
  - block_type: "GAME"
  - content: {pgn, result, key_moments, xp_earned, ...}
  - Permanent block (not temporary)
         │
         ▼
Award XP to chess skill
         │
         ▼
GameManager.clear_game():
  1. Remove from memory
  2. Delete active_game.json
         │
         ▼
Frontend shows game summary, XP gained, returns to lobby
```

### 6. Crash Recovery Flow

```
App starts, Qube loads
         │
         ▼
GameManager.__init__() checks for active_game.json
         │
         ▼
If found:
  - Load GameState from file
  - Qube has active game
         │
         ▼
Frontend (on tab open) calls get_active_game(qube_id)
         │
         ▼
If active game exists:
  - Show "Resume Game?" dialog
  - User can resume or abandon
         │
         ▼
Abandon: end_game(result="*", termination="abandoned")
Resume: Continue from saved position
```

---

## File Changes (Validated Against Codebase)

### Backend (Python)

| File | Action | Specific Changes |
|------|--------|------------------|
| `core/block.py` | Modify | Add `GAME = "GAME"` to BlockType enum (line ~27), add `create_game_block()` factory function following SUMMARY pattern |
| `core/game_manager.py` | **Create** | GameState dataclass, GameManager class with create/record/end/clear methods, crash recovery via active_game.json |
| `core/qube.py` | Modify | Add `from core.game_manager import GameManager` at top (line ~28), add `self.game_manager = GameManager(self)` after MemoryChain init (line ~98) |
| `ai/tools/handlers.py` | Modify | Add `chess_move_handler()` async function, register ToolDefinition in `register_default_tools()` |
| `ai/tools/registry.py` | Modify | Add `"chess_move"` to ALWAYS_AVAILABLE_TOOLS set (line ~34) |
| `gui_bridge.py` | Modify | Add: `create_chess_game()`, `make_human_move()`, `request_qube_move()`, `end_chess_game()`, `send_game_chat()`, `get_game_history()` |
| `requirements.txt` | Modify | Add `chess>=1.10.0` |

### Backend (Rust)

| File | Action | Specific Changes |
|------|--------|------------------|
| `src-tauri/src/lib.rs` | Modify | Add response structs + tauri::command functions for each gui_bridge game method, register in invoke_handler |

### Frontend (TypeScript/React)

| File | Action | Specific Changes |
|------|--------|------------------|
| `src/types/index.ts` | Modify | Add `'games'` to Tab union (line ~50), add ChessGame/GameState/ChatMessage interfaces |
| `src/components/tabs/TabBar.tsx` | Modify | Add `{ id: 'games', label: 'Games' }` to TABS array at line 16 (between 'skills' and 'economy') |
| `src/components/tabs/TabContent.tsx` | Modify | Add GamesTab mount with opacity/z-index pattern |
| `src/hooks/useQubeSelection.tsx` | Modify | Add `games: null` to activeQubeByTab (line ~32), add `games: []` to selectionByTab (line ~42), add `\|\| currentTab === 'games'` to isMultiSelectAllowed() (line ~125) |
| `src/components/tabs/GamesTab.tsx` | **Create** | Lobby view, game history, ChessGame integration |
| `src/components/games/ChessGame.tsx` | **Create** | react-chessboard + chess.js, side panel with chat, move history |
| `src/components/games/index.ts` | **Create** | Export ChessGame |
| `package.json` | Modify | Add `react-chessboard`, `chess.js` dependencies |

---

## Implementation Order

### Phase 1: Backend Foundation
1. Add `GAME` block type to `core/block.py`
2. Create `core/game_manager.py` with GameState and GameManager
3. Add `chess` to `requirements.txt`
4. Initialize GameManager in `core/qube.py`

### Phase 2: Tool Integration
1. Add `chess_move` tool to `ai/tools/handlers.py`
2. Modify `ai/tools/registry.py` for conditional tool inclusion
3. Test tool execution

### Phase 3: GUI Bridge
1. Add game commands to `gui_bridge.py`
2. Add Tauri commands to `lib.rs`
3. Test end-to-end command flow

### Phase 4: Frontend
1. Install react-chessboard and chess.js
2. Add types to `types/index.ts`
3. Add tab infrastructure (TabBar, TabContent, useQubeSelection)
4. Create GamesTab component
5. Create ChessGame component

### Phase 5: Chat & Polish
1. In-game chat UI (send/receive messages)
2. Qube auto-reactions to game events
3. Crash recovery testing
4. XP integration testing
5. Visual polish (animations, Qube thinking indicator)
6. Game history view with chat logs

---

## Future: P2P Games

The architecture supports P2P expansion:

```
Qube A                           Qube B
   │                                │
   │  1. Create game, get game_id   │
   │ ─────────────────────────────► │
   │  (signed message over P2P)     │
   │                                │
   │  2. Qube B joins               │
   │ ◄───────────────────────────── │
   │                                │
   │  3. Moves exchanged            │
   │ ◄──────────────────────────────┤
   │───────────────────────────────►│
   │  (each move signed by player)  │
   │                                │
   │  4. Game ends                  │
   │  Both create GAME blocks       │
   │  with move_signatures for      │
   │  cross-verification            │
```

Key additions needed:
- Move signing with Qube's private key
- P2P game protocol messages
- Signature verification
- move_signatures field in GAME block

---

## Questions Resolved

| Question | Decision | Rationale |
|----------|----------|-----------|
| MOVE blocks? | No | Unnecessary overhead, PGN captures everything |
| Skill gating for chess_move? | No | Tool is game-contextual, not a general capability |
| Crash recovery? | Yes, via file | Simple, reliable, matches user expectations |
| Key moments? | Yes, in GAME block | Preserves Qube reasoning without bloat |
| Session integration? | Games are separate | Cleaner architecture, games aren't conversations |

---

## In-Game Chat (Trash Talk)

Games have their own chat panel, separate from the main Chat tab. This allows:
- Human can type messages during the game
- Qube can react to moves, taunt, compliment, or panic
- Chat is preserved in the GAME block for posterity

### Chat Message Structure

```python
# In GameState.chat_messages
{
    "sender_id": "human" | "Qube_ID",
    "sender_type": "human" | "qube",
    "message": "You sure about that move?",
    "timestamp": 1704384000.0,
    "trigger": "manual" | "auto_reaction"  # Was this typed or auto-generated?
}
```

### Qube Auto-Reactions

Qubes can automatically react to game situations based on personality:

| Trigger | Example Reactions |
|---------|-------------------|
| After Qube captures | "Thanks for the free piece!" / "Nom nom nom" |
| After Human captures | "I didn't need that anyway..." / "Bold move." |
| Qube gives check | "Check! Feeling the pressure?" |
| Qube is in check | "Oh, you think you're clever?" |
| Human blunders | "Are you sure about that?" / "I'll take it!" |
| Qube blunders | "Wait, no—" / "I meant to do that." |
| Qube is winning | "This is going well for me." |
| Qube is losing | "You got lucky." / "I'm just warming up." |
| Checkmate (Qube wins) | "GG EZ" / "Better luck next time!" |
| Checkmate (Human wins) | "Well played. Rematch?" / "I demand a rematch." |

**Personality influence**: A formal Qube might say "Well played" while a playful one says "GG EZ".

### Implementation

```python
async def generate_game_reaction(
    qube: Qube,
    game_state: GameState,
    trigger: str
) -> Optional[str]:
    """
    Generate a contextual reaction based on game state and Qube personality.
    Returns None if Qube chooses not to react (randomized).
    """
    # ~40% chance to react (don't spam)
    if random.random() > 0.4:
        return None

    prompt = f"""You're playing chess. React briefly (1 sentence max) to: {trigger}
    Your personality: {qube.personality_summary}
    Current position: {'winning' if evaluation > 1 else 'losing' if evaluation < -1 else 'even'}
    Keep it playful and in-character."""

    # Quick generation, no tools needed
    response = await qube.generate_quick_response(prompt)
    return response
```

### Chat in GAME Block

Chat preserved for posterity:

```python
# In GAME block content
{
    ...
    "chat_log": [
        {"sender": "human", "message": "Let's see what you got", "move": 0},
        {"sender": "Alph_123", "message": "Prepare to lose.", "move": 0},
        {"sender": "Alph_123", "message": "Thanks for the bishop!", "move": 12},
        {"sender": "human", "message": "That was a sacrifice!", "move": 12},
        {"sender": "Alph_123", "message": "Sure it was. 😏", "move": 12},
        {"sender": "Alph_123", "message": "GG!", "move": 34}
    ]
}
```

### UI Design

```
┌─────────────────────────────────────────────────────────────┐
│  ♔ Chess: You vs Alph                          [Resign] [X] │
├─────────────────────────────────┬───────────────────────────┤
│                                 │  Alph (Black) ●           │
│                                 │  "Prepare to lose."       │
│        ┌───────────────┐        │                           │
│        │               │        │  ─────────────────────    │
│        │   Chess       │        │  1. e4    e5              │
│        │   Board       │        │  2. Nf3   Nc6             │
│        │               │        │  3. Bb5   ...             │
│        │               │        │                           │
│        └───────────────┘        │  ─────────────────────    │
│                                 │                           │
│                                 │  💬 Chat                  │
│        You (White) ○            │  ┌─────────────────────┐  │
│        Your turn                │  │ Alph: Nice opening  │  │
│                                 │  │ You: Thanks!        │  │
│                                 │  │ Alph: You'll need it│  │
│                                 │  └─────────────────────┘  │
│                                 │  [Type a message...   ]   │
└─────────────────────────────────┴───────────────────────────┘
```

---

## Success Criteria

- [ ] Can start a new chess game against a Qube
- [ ] Human moves are validated and applied
- [ ] Qube makes reasonable moves with reasoning
- [ ] Game end is detected (checkmate, stalemate, resignation)
- [ ] GAME block created with complete PGN
- [ ] XP awarded to chess skill
- [ ] Game appears in history
- [ ] Crash recovery works (close mid-game, resume on reopen)
- [ ] In-game chat works (human can send messages)
- [ ] Qube auto-reacts to game events (captures, checks, etc.)
- [ ] Chat log preserved in GAME block
- [ ] UI is polished and responsive
