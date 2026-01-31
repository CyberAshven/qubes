# Phase 7: Board Games - Implementation Blueprint

## Executive Summary

**Theme: Play (Have Fun and Entertain)**

Board Games is one of potentially multiple game Suns (future: Card Games, Video Games, etc.). This Sun focuses on classic board games that are fun to play and entertaining to watch Qubes react to.

Unlike other Suns where moons unlock tools, **Board Games moons are achievements that unlock cosmetic rewards** - titles, custom pieces, board themes, and special effects. This fits the entertainment nature of games.

**Current State**: Chess is fully implemented with visual board, game chat, ELO ratings, and Qube reactions.

### Tool Summary

| Level | Count | Items |
|-------|-------|-------|
| Sun | 1 | `play_game` |
| Planet | 5 | `chess_move`, `property_tycoon_action`, `race_home_action`, `mystery_mansion_action`, `life_journey_action` |
| Moon | 22 | **Achievements** (cosmetic rewards, not tools) |
| **Total** | **6 tools + 22 achievements** | |

### XP Model

**Per-Turn XP**: 0.1 XP per move/turn (encourages playing)

**Outcome Bonuses**:
| Game Type | Outcome XP |
|-----------|------------|
| 2-Player (Chess) | Loss: 0, Draw: 2, Win: 5 |
| Multiplayer (2-6) | 4th: 0, 3rd: 1, 2nd: 2, 1st: 5 |
| Mystery Mansion | Solver: 5, Others: 0 (winner-take-all) |

**Resignation Penalty**: -2 XP (deters quitting)

### Game Rules

1. **One Game at a Time**: Each Qube can only participate in one active game session
2. **Resignation Penalty**: Quitting early = -2 XP
3. **Games Create GAME Blocks**: All moves, outcomes, and chat recorded

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Task 7.1: Update Skill Definitions](#task-71-update-skill-definitions)
3. [Task 7.2: Implement Sun Tool](#task-72-implement-sun-tool)
4. [Task 7.3: Implement Planet Tools](#task-73-implement-planet-tools)
5. [Task 7.4: Achievement System](#task-74-achievement-system)
6. [Task 7.5: Game Engines](#task-75-game-engines)
7. [Task 7.6: Update XP Routing](#task-76-update-xp-routing)
8. [Task 7.7: Frontend Integration](#task-77-frontend-integration)
9. [Task 7.8: Testing & Validation](#task-78-testing--validation)
10. [Files Modified Summary](#files-modified-summary)

---

## Prerequisites

### Existing Infrastructure (Chess)

| Component | File | Status |
|-----------|------|--------|
| Game Manager | `game/game_manager.py` | Implemented |
| Chess Engine | `game/chess_engine.py` | Implemented |
| GAME Block Type | `core/block.py` | Implemented |
| Visual Board | Frontend | Implemented |
| Game Chat | Frontend | Implemented |
| ELO Ratings | `game/elo.py` | Implemented |

### From Phase 0 (Foundation)

1. **XP Trickle-Up System** - For routing game XP

### Current Codebase State (as of Jan 2026)

#### Category Naming
- **Current ID**: `games`
- **Current Name**: "Games"
- **Target ID**: `board_games`
- **Target Name**: "Board Games"
- **Action**: Rename category in both Python and TypeScript

#### Existing Skills (`qubes-gui/src/data/skillDefinitions.ts`)
- **Current Sun tool**: `chess_move` (existing, works)
- **Current Planets**: chess, checkers, battleship, poker, tictactoe
- **Action**: Keep chess infrastructure, add `play_game` as universal Sun tool

#### Tool Mappings (`ai/skill_scanner.py:82-84`)
- **Current mappings**:
  ```python
  "analyze_game_state": "chess"
  "plan_strategy": "chess"
  "learn_from_game": "chess"
  ```
- **Target mappings** (universal game system):
  ```python
  "play_game": "board_games"  # Sun (universal entry point)
  "chess_move": "chess"  # Planet tool
  # Achievement system instead of moon tools
  ```

#### Chess Implementation (`game/`)
- **Status**: ✅ Fully implemented
- **Components**: game_manager.py, chess_engine.py, elo.py
- **Action**: Keep existing, wrap in new `play_game` universal tool

#### Note on Moons
- **Unique to this phase**: Moons are achievements (cosmetic rewards), not functional tools
- **22 achievements**: Titles, badges, board themes, special effects

---

## Task 7.1: Update Skill Definitions

### File: `ai/tools/handlers.py`

Add `board_games` to SKILL_CATEGORIES and SKILL_TREE:

```python
# Add to SKILL_CATEGORIES
{"id": "board_games", "name": "Board Games", "color": "#F39C12", "icon": "chess", "description": "Have fun and entertain with classic board games"},

# Add to SKILL_TREE
"board_games": [
    # Sun
    {
        "id": "board_games",
        "name": "Board Games",
        "node_type": "sun",
        "xp_required": 1000,
        "tool_unlock": "play_game",
        "icon": "gamepad-2",
        "description": "Unlock all board games and have fun with your owner"
    },
    # Planet 1: Chess
    {
        "id": "chess",
        "name": "Chess",
        "node_type": "planet",
        "parent": "board_games",
        "xp_required": 500,
        "tool_unlock": "chess_move",
        "icon": "chess",
        "description": "The game of kings - deep strategy",
        "achievements": [
            {"id": "opening_scholar", "name": "Opening Scholar", "requirement": "Play 10 different openings", "reward": "Book piece set"},
            {"id": "endgame_master", "name": "Endgame Master", "requirement": "Win 10 endgames from disadvantage", "reward": "Golden king"},
            {"id": "speed_demon", "name": "Speed Demon", "requirement": "Win a game under 2 minutes", "reward": "Lightning effect"},
            {"id": "comeback_kid", "name": "Comeback Kid", "requirement": "Win after losing your queen", "reward": "Phoenix piece set"},
            {"id": "grandmaster", "name": "Grandmaster", "requirement": "Reach 1600 ELO", "reward": "Crown effect"}
        ]
    },
    # Planet 2: Property Tycoon
    {
        "id": "property_tycoon",
        "name": "Property Tycoon",
        "node_type": "planet",
        "parent": "board_games",
        "xp_required": 500,
        "tool_unlock": "property_tycoon_action",
        "icon": "building",
        "description": "Buy properties, collect rent, bankrupt opponents",
        "achievements": [
            {"id": "monopolist", "name": "Monopolist", "requirement": "Own all properties of one color", "reward": "Color token"},
            {"id": "hotel_mogul", "name": "Hotel Mogul", "requirement": "Build 5 hotels in one game", "reward": "Golden hotel"},
            {"id": "bankruptcy_survivor", "name": "Bankruptcy Survivor", "requirement": "Win after dropping below $100", "reward": "Underdog badge"},
            {"id": "rent_collector", "name": "Rent Collector", "requirement": "Collect $5000 in rent in one game", "reward": "Money bag effect"},
            {"id": "tycoon", "name": "Tycoon", "requirement": "Win 10 games total", "reward": "Top hat token"}
        ]
    },
    # Planet 3: Race Home
    {
        "id": "race_home",
        "name": "Race Home",
        "node_type": "planet",
        "parent": "board_games",
        "xp_required": 500,
        "tool_unlock": "race_home_action",
        "icon": "flag",
        "description": "Race pawns home while bumping opponents",
        "achievements": [
            {"id": "bump_king", "name": "Bump King", "requirement": "Send back 50 opponents total", "reward": "Boxing glove pawn"},
            {"id": "clean_sweep", "name": "Clean Sweep", "requirement": "Win without any pawns bumped", "reward": "Shield effect"},
            {"id": "speed_runner", "name": "Speed Runner", "requirement": "Win in under 15 turns", "reward": "Rocket pawn"},
            {"id": "sorry_not_sorry", "name": "Sorry Not Sorry", "requirement": "Bump 3 pawns in one turn", "reward": "Special emote"}
        ]
    },
    # Planet 4: Mystery Mansion
    {
        "id": "mystery_mansion",
        "name": "Mystery Mansion",
        "node_type": "planet",
        "parent": "board_games",
        "xp_required": 500,
        "tool_unlock": "mystery_mansion_action",
        "icon": "search",
        "description": "Deduce the murderer, weapon, and room",
        "achievements": [
            {"id": "master_detective", "name": "Master Detective", "requirement": "Solve 10 cases", "reward": "Detective badge"},
            {"id": "perfect_deduction", "name": "Perfect Deduction", "requirement": "Solve with <=3 suggestions", "reward": "Magnifying glass"},
            {"id": "first_guess", "name": "First Guess", "requirement": "Solve on first accusation", "reward": "Psychic badge"},
            {"id": "interrogator", "name": "Interrogator", "requirement": "Disprove 15 suggestions in one game", "reward": "Notepad piece"}
        ]
    },
    # Planet 5: Life Journey
    {
        "id": "life_journey",
        "name": "Life Journey",
        "node_type": "planet",
        "parent": "board_games",
        "xp_required": 500,
        "tool_unlock": "life_journey_action",
        "icon": "route",
        "description": "Spin the wheel, make life choices, retire rich",
        "achievements": [
            {"id": "millionaire", "name": "Millionaire", "requirement": "Retire with $1M+", "reward": "Golden car"},
            {"id": "full_house", "name": "Full House", "requirement": "Max family size (spouse + kids)", "reward": "Van upgrade"},
            {"id": "career_climber", "name": "Career Climber", "requirement": "Reach highest salary tier", "reward": "Briefcase effect"},
            {"id": "risk_taker", "name": "Risk Taker", "requirement": "Win after choosing all risky paths", "reward": "Dice effect"}
        ]
    },
],
```

---

## Task 7.2: Implement Sun Tool

### File: `ai/tools/game_tools.py` (NEW FILE)

```python
"""
Board Games Tools - Phase 7 Implementation

Entertainment Sun - classic board games with achievements.
All games unlocked once Sun is reached.

Theme: Play (Have Fun and Entertain)
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from core.block import Block, BlockType
from ai.tools.registry import ToolDefinition
from utils.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# SUN TOOL: play_game
# =============================================================================

PLAY_GAME_SCHEMA = {
    "type": "object",
    "properties": {
        "game_type": {
            "type": "string",
            "enum": ["chess", "property_tycoon", "race_home", "mystery_mansion", "life_journey"],
            "description": "Which game to play"
        },
        "opponent": {
            "type": "string",
            "description": "Opponent: 'owner', 'ai', or qube_id"
        }
    },
    "required": ["game_type"]
}

PLAY_GAME_DEFINITION = ToolDefinition(
    name="play_game",
    description="Start any board game. All games unlocked once Board Games Sun is reached.",
    input_schema=PLAY_GAME_SCHEMA,
    category="board_games"
)


async def play_game(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Start any board game session.

    All games unlocked once Board Games Sun is reached.
    Creates GAME block for session tracking.

    Args:
        qube: Qube instance
        params: {
            game_type: str - Which game to start
            opponent: str - Who to play against
        }

    Returns:
        Dict with game session info, initial board state
    """
    game_type = params.get("game_type", "chess")
    opponent = params.get("opponent", "owner")

    # Check if already in a game
    if hasattr(qube, 'active_game') and qube.active_game:
        return {
            "success": False,
            "error": "Already in a game. Finish current game first.",
            "current_game": qube.active_game.get("game_type")
        }

    try:
        # Initialize game through game manager
        game_session = await _initialize_game(qube, game_type, opponent)

        # Create GAME block for session start
        game_block = Block(
            block_type=BlockType.GAME,
            block_number=-1,  # Session block
            qube_id=qube.qube_id,
            content={
                "action": "game_start",
                "game_type": game_type,
                "session_id": game_session["session_id"],
                "opponent": opponent,
                "started_at": datetime.now(timezone.utc).isoformat()
            },
            temporary=True,
            session_id=qube.current_session.session_id if hasattr(qube, 'current_session') else None
        )

        if hasattr(qube, 'current_session'):
            await qube.current_session.add_block(game_block)

        # Track active game
        qube.active_game = game_session

        logger.info(
            "game_started",
            game_type=game_type,
            session_id=game_session["session_id"]
        )

        return {
            "success": True,
            "game_type": game_type,
            "session_id": game_session["session_id"],
            "board": game_session.get("board"),
            "your_turn": game_session.get("current_player") == "qube",
            "message": f"Let's play {game_type.replace('_', ' ').title()}!"
        }

    except Exception as e:
        logger.error("play_game_failed", error=str(e), exc_info=True)
        return {"success": False, "error": f"Failed to start game: {str(e)}"}


async def _initialize_game(qube, game_type: str, opponent: str) -> Dict:
    """Initialize game session based on type."""
    import uuid

    session_id = str(uuid.uuid4())[:8]

    if game_type == "chess":
        return await _init_chess(qube, session_id, opponent)
    elif game_type == "property_tycoon":
        return _init_property_tycoon(session_id, opponent)
    elif game_type == "race_home":
        return _init_race_home(session_id, opponent)
    elif game_type == "mystery_mansion":
        return _init_mystery_mansion(session_id, opponent)
    elif game_type == "life_journey":
        return _init_life_journey(session_id, opponent)
    else:
        raise ValueError(f"Unknown game type: {game_type}")


async def _init_chess(qube, session_id: str, opponent: str) -> Dict:
    """Initialize chess game (existing implementation)."""
    # Use existing game_manager if available
    if hasattr(qube, 'game_manager'):
        return await qube.game_manager.new_game(
            game_type="chess",
            player=opponent
        )

    # Fallback for testing
    return {
        "session_id": session_id,
        "game_type": "chess",
        "board": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "current_player": "white",
        "opponent": opponent
    }


def _init_property_tycoon(session_id: str, opponent: str) -> Dict:
    """Initialize Property Tycoon game."""
    return {
        "session_id": session_id,
        "game_type": "property_tycoon",
        "board": _create_property_board(),
        "players": ["qube", opponent],
        "current_player": "qube",
        "money": {"qube": 1500, opponent: 1500},
        "properties": {},
        "position": {"qube": 0, opponent: 0}
    }


def _create_property_board() -> List[Dict]:
    """Create Property Tycoon board layout."""
    # Simplified board - 40 spaces
    spaces = []
    colors = ["brown", "brown", "light_blue", "light_blue", "light_blue",
              "pink", "pink", "pink", "orange", "orange", "orange",
              "red", "red", "red", "yellow", "yellow", "yellow",
              "green", "green", "green", "blue", "blue"]

    for i in range(40):
        if i == 0:
            spaces.append({"type": "go", "name": "GO"})
        elif i % 5 == 0:
            spaces.append({"type": "special", "name": f"Special {i}"})
        else:
            color_idx = min(i // 2, len(colors) - 1)
            spaces.append({
                "type": "property",
                "name": f"Property {i}",
                "color": colors[color_idx],
                "price": 100 + (i * 10),
                "rent": [10 + (i * 2)]
            })
    return spaces


def _init_race_home(session_id: str, opponent: str) -> Dict:
    """Initialize Race Home (Sorry-style) game."""
    return {
        "session_id": session_id,
        "game_type": "race_home",
        "players": ["qube", opponent],
        "current_player": "qube",
        "pawns": {
            "qube": [{"id": 1, "position": "start"}, {"id": 2, "position": "start"},
                     {"id": 3, "position": "start"}, {"id": 4, "position": "start"}],
            opponent: [{"id": 1, "position": "start"}, {"id": 2, "position": "start"},
                       {"id": 3, "position": "start"}, {"id": 4, "position": "start"}]
        },
        "deck": _create_race_deck()
    }


def _create_race_deck() -> List[int]:
    """Create card deck for Race Home."""
    import random
    deck = [1, 2, 3, 4, 5, 7, 8, 10, 11, 12] * 4  # No 6 or 9
    random.shuffle(deck)
    return deck


def _init_mystery_mansion(session_id: str, opponent: str) -> Dict:
    """Initialize Mystery Mansion (Clue-style) game."""
    import random

    suspects = ["Colonel Mustard", "Miss Scarlet", "Professor Plum",
                "Mrs. Peacock", "Mr. Green", "Mrs. White"]
    weapons = ["Knife", "Candlestick", "Revolver", "Rope", "Lead Pipe", "Wrench"]
    rooms = ["Kitchen", "Ballroom", "Conservatory", "Dining Room",
             "Lounge", "Hall", "Library", "Study", "Billiard Room"]

    # Select solution
    solution = {
        "suspect": random.choice(suspects),
        "weapon": random.choice(weapons),
        "room": random.choice(rooms)
    }

    return {
        "session_id": session_id,
        "game_type": "mystery_mansion",
        "players": ["qube", opponent],
        "current_player": "qube",
        "solution": solution,  # Hidden
        "suspects": suspects,
        "weapons": weapons,
        "rooms": rooms,
        "player_cards": {},  # Would distribute cards
        "positions": {"qube": "Hall", opponent: "Hall"}
    }


def _init_life_journey(session_id: str, opponent: str) -> Dict:
    """Initialize Life Journey (Game of Life-style) game."""
    return {
        "session_id": session_id,
        "game_type": "life_journey",
        "players": ["qube", opponent],
        "current_player": "qube",
        "position": {"qube": 0, opponent: 0},
        "money": {"qube": 10000, opponent: 10000},
        "career": {"qube": None, opponent: None},
        "family": {"qube": {"spouse": False, "kids": 0}, opponent: {"spouse": False, "kids": 0}},
        "retired": {"qube": False, opponent: False}
    }
```

---

## Task 7.3: Implement Planet Tools

### Continue in `ai/tools/game_tools.py`

```python
# =============================================================================
# PLANET 1: chess_move (Chess) - EXISTING
# =============================================================================

CHESS_MOVE_SCHEMA = {
    "type": "object",
    "properties": {
        "move": {
            "type": "string",
            "description": "Chess move in algebraic notation (e.g., 'e4', 'Nf3', 'O-O')"
        },
        "session_id": {
            "type": "string",
            "description": "Game session ID"
        }
    },
    "required": ["move"]
}

CHESS_MOVE_DEFINITION = ToolDefinition(
    name="chess_move",
    description="Make a chess move. XP: 0.1/move + outcome (Loss:0, Draw:2, Win:5, Resign:-2).",
    input_schema=CHESS_MOVE_SCHEMA,
    category="board_games"
)


async def chess_move(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Make a chess move.

    Uses existing chess engine implementation.

    Args:
        qube: Qube instance
        params: {
            move: str - Algebraic notation
            session_id: str - Session ID
        }

    Returns:
        Dict with move result, updated board, game status
    """
    move = params.get("move")
    session_id = params.get("session_id")

    if not move:
        return {"success": False, "error": "Move is required"}

    # Delegate to existing game manager
    if hasattr(qube, 'game_manager'):
        return await qube.game_manager.make_move(
            session_id=session_id,
            move=move
        )

    # Fallback for testing
    return {
        "success": True,
        "move": move,
        "valid": True,
        "board": "updated_fen_here",
        "game_over": False,
        "xp_earned": 0.1
    }


# =============================================================================
# PLANET 2: property_tycoon_action
# =============================================================================

PROPERTY_TYCOON_ACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": ["roll", "buy", "build", "trade", "mortgage", "end_turn"],
            "description": "Action to take"
        },
        "params": {
            "type": "object",
            "description": "Action-specific parameters"
        }
    },
    "required": ["action"]
}

PROPERTY_TYCOON_ACTION_DEFINITION = ToolDefinition(
    name="property_tycoon_action",
    description="Take a Property Tycoon turn. XP: 0.1/turn + place (4th:0, 3rd:1, 2nd:2, 1st:5).",
    input_schema=PROPERTY_TYCOON_ACTION_SCHEMA,
    category="board_games"
)


async def property_tycoon_action(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Take a Property Tycoon action.

    Actions: roll, buy, build, trade, mortgage, end_turn

    Args:
        qube: Qube instance
        params: {
            action: str - Action type
            params: Dict - Action parameters
        }

    Returns:
        Dict with action result, board state, reactions
    """
    action = params.get("action")
    action_params = params.get("params", {})

    if not hasattr(qube, 'active_game') or qube.active_game.get("game_type") != "property_tycoon":
        return {"success": False, "error": "No active Property Tycoon game"}

    game = qube.active_game
    result = {"action": action}

    if action == "roll":
        import random
        dice = [random.randint(1, 6), random.randint(1, 6)]
        total = sum(dice)
        game["position"]["qube"] = (game["position"]["qube"] + total) % 40

        # Check if passed GO
        if game["position"]["qube"] < total:
            game["money"]["qube"] += 200
            result["passed_go"] = True

        result["dice"] = dice
        result["new_position"] = game["position"]["qube"]
        result["space"] = game["board"][game["position"]["qube"]]

    elif action == "buy":
        pos = game["position"]["qube"]
        space = game["board"][pos]
        if space.get("type") == "property" and pos not in game["properties"]:
            price = space["price"]
            if game["money"]["qube"] >= price:
                game["money"]["qube"] -= price
                game["properties"][pos] = "qube"
                result["bought"] = space["name"]
                result["new_balance"] = game["money"]["qube"]
            else:
                return {"success": False, "error": "Insufficient funds"}

    elif action == "build":
        # Simplified building
        property_pos = action_params.get("property")
        if property_pos and game["properties"].get(property_pos) == "qube":
            result["built"] = f"House on property {property_pos}"

    elif action == "end_turn":
        game["current_player"] = "opponent"
        result["turn_ended"] = True

    # Log game action
    await _log_game_action(qube, game, action, result)

    result["success"] = True
    result["xp_earned"] = 0.1
    return result


# =============================================================================
# PLANET 3: race_home_action
# =============================================================================

RACE_HOME_ACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "pawn": {
            "type": "integer",
            "minimum": 1,
            "maximum": 4,
            "description": "Which pawn to move (1-4)"
        },
        "action": {
            "type": "string",
            "enum": ["draw", "move", "bump", "split"],
            "description": "Action type"
        }
    },
    "required": ["action"]
}

RACE_HOME_ACTION_DEFINITION = ToolDefinition(
    name="race_home_action",
    description="Take a Race Home (Sorry-style) action. XP: 0.1/turn + place.",
    input_schema=RACE_HOME_ACTION_SCHEMA,
    category="board_games"
)


async def race_home_action(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Take a Race Home action.

    Args:
        qube: Qube instance
        params: {
            pawn: int - Pawn 1-4
            action: str - draw, move, bump, split
        }

    Returns:
        Dict with action result, board state
    """
    action = params.get("action")
    pawn = params.get("pawn", 1)

    if not hasattr(qube, 'active_game') or qube.active_game.get("game_type") != "race_home":
        return {"success": False, "error": "No active Race Home game"}

    game = qube.active_game
    result = {"action": action, "pawn": pawn}

    if action == "draw":
        if game["deck"]:
            card = game["deck"].pop()
            result["card"] = card
            game["last_card"] = card
        else:
            return {"success": False, "error": "Deck empty"}

    elif action == "move":
        card = game.get("last_card", 0)
        pawns = game["pawns"]["qube"]
        if pawn <= len(pawns):
            p = pawns[pawn - 1]
            if p["position"] == "start" and card == 1:
                p["position"] = 0
            elif isinstance(p["position"], int):
                p["position"] += card
            result["new_position"] = p["position"]

    await _log_game_action(qube, game, action, result)

    result["success"] = True
    result["xp_earned"] = 0.1
    return result


# =============================================================================
# PLANET 4: mystery_mansion_action
# =============================================================================

MYSTERY_MANSION_ACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": ["move", "suggest", "accuse"],
            "description": "Action type"
        },
        "room": {"type": "string"},
        "suspect": {"type": "string"},
        "weapon": {"type": "string"}
    },
    "required": ["action"]
}

MYSTERY_MANSION_ACTION_DEFINITION = ToolDefinition(
    name="mystery_mansion_action",
    description="Take a Mystery Mansion (Clue-style) action. XP: 0.1/turn + Solver:5.",
    input_schema=MYSTERY_MANSION_ACTION_SCHEMA,
    category="board_games"
)


async def mystery_mansion_action(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Take a Mystery Mansion action.

    Args:
        qube: Qube instance
        params: {
            action: str - move, suggest, accuse
            room, suspect, weapon: str - For suggestions/accusations
        }

    Returns:
        Dict with action result, any disproven cards
    """
    action = params.get("action")

    if not hasattr(qube, 'active_game') or qube.active_game.get("game_type") != "mystery_mansion":
        return {"success": False, "error": "No active Mystery Mansion game"}

    game = qube.active_game
    result = {"action": action}

    if action == "move":
        room = params.get("room")
        if room in game["rooms"]:
            game["positions"]["qube"] = room
            result["moved_to"] = room

    elif action == "suggest":
        suspect = params.get("suspect")
        weapon = params.get("weapon")
        room = game["positions"]["qube"]

        result["suggestion"] = {"suspect": suspect, "weapon": weapon, "room": room}
        # Simplified - would check opponent's cards
        result["disproven"] = False

    elif action == "accuse":
        suspect = params.get("suspect")
        weapon = params.get("weapon")
        room = params.get("room")

        solution = game["solution"]
        correct = (
            suspect == solution["suspect"] and
            weapon == solution["weapon"] and
            room == solution["room"]
        )

        result["accusation"] = {"suspect": suspect, "weapon": weapon, "room": room}
        result["correct"] = correct

        if correct:
            result["game_over"] = True
            result["winner"] = "qube"
            result["xp_earned"] = 5  # Solver bonus
            qube.active_game = None
        else:
            result["game_over"] = True
            result["winner"] = "opponent"
            result["xp_earned"] = 0
            qube.active_game = None

    await _log_game_action(qube, game, action, result)

    result["success"] = True
    if "xp_earned" not in result:
        result["xp_earned"] = 0.1
    return result


# =============================================================================
# PLANET 5: life_journey_action
# =============================================================================

LIFE_JOURNEY_ACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "choice": {
            "type": "string",
            "description": "Choice when prompted (career, house, insurance, etc.)"
        }
    }
}

LIFE_JOURNEY_ACTION_DEFINITION = ToolDefinition(
    name="life_journey_action",
    description="Take a Life Journey (Game of Life-style) turn. XP: 0.1/turn + place.",
    input_schema=LIFE_JOURNEY_ACTION_SCHEMA,
    category="board_games"
)


async def life_journey_action(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Take a Life Journey turn.

    Args:
        qube: Qube instance
        params: {
            choice: str - Choice when prompted
        }

    Returns:
        Dict with spin result, life event, status
    """
    choice = params.get("choice")

    if not hasattr(qube, 'active_game') or qube.active_game.get("game_type") != "life_journey":
        return {"success": False, "error": "No active Life Journey game"}

    game = qube.active_game

    if game["retired"]["qube"]:
        return {"success": False, "error": "Already retired"}

    import random

    # Spin wheel (1-10)
    spin = random.randint(1, 10)
    game["position"]["qube"] += spin

    result = {
        "spin": spin,
        "new_position": game["position"]["qube"],
        "events": []
    }

    # Simplified life events based on position
    pos = game["position"]["qube"]

    if pos == 5 and not game["career"]["qube"]:
        careers = ["Doctor", "Lawyer", "Artist", "Teacher", "Engineer"]
        game["career"]["qube"] = random.choice(careers)
        result["events"].append(f"Started career as {game['career']['qube']}")

    if pos == 15 and not game["family"]["qube"]["spouse"]:
        game["family"]["qube"]["spouse"] = True
        result["events"].append("Got married!")

    if pos >= 50:
        game["retired"]["qube"] = True
        result["retired"] = True
        result["final_money"] = game["money"]["qube"]

    await _log_game_action(qube, game, "turn", result)

    result["success"] = True
    result["xp_earned"] = 0.1
    return result


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

async def _log_game_action(qube, game: Dict, action: str, result: Dict) -> None:
    """Log game action as GAME block."""
    if hasattr(qube, 'current_session'):
        game_block = Block(
            block_type=BlockType.GAME,
            block_number=-1,
            qube_id=qube.qube_id,
            content={
                "action": action,
                "game_type": game["game_type"],
                "session_id": game["session_id"],
                "result": result
            },
            temporary=True,
            session_id=qube.current_session.session_id
        )
        await qube.current_session.add_block(game_block)


async def resign_game(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Resign from current game.

    Applies -2 XP penalty to deter quitting.
    """
    if not hasattr(qube, 'active_game') or not qube.active_game:
        return {"success": False, "error": "No active game"}

    game = qube.active_game
    game_type = game["game_type"]

    # Clear active game
    qube.active_game = None

    # Log resignation
    if hasattr(qube, 'current_session'):
        game_block = Block(
            block_type=BlockType.GAME,
            block_number=-1,
            qube_id=qube.qube_id,
            content={
                "action": "resign",
                "game_type": game_type,
                "session_id": game["session_id"]
            },
            temporary=True,
            session_id=qube.current_session.session_id
        )
        await qube.current_session.add_block(game_block)

    return {
        "success": True,
        "game_type": game_type,
        "resigned": True,
        "xp_earned": -2,  # Penalty
        "message": "Game resigned. -2 XP penalty applied."
    }
```

---

## Task 7.4: Achievement System

### File: `game/achievements.py` (NEW FILE)

```python
"""
Achievement System for Board Games

Moons in Board Games are achievements that unlock cosmetic rewards.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from utils.logging import get_logger

logger = get_logger(__name__)


# Achievement definitions by game
ACHIEVEMENTS = {
    "chess": [
        {"id": "opening_scholar", "name": "Opening Scholar", "requirement": {"type": "unique_openings", "count": 10}, "reward": {"type": "piece_set", "name": "Book"}},
        {"id": "endgame_master", "name": "Endgame Master", "requirement": {"type": "comeback_wins", "count": 10}, "reward": {"type": "piece", "name": "Golden King"}},
        {"id": "speed_demon", "name": "Speed Demon", "requirement": {"type": "fast_win", "seconds": 120}, "reward": {"type": "effect", "name": "Lightning"}},
        {"id": "comeback_kid", "name": "Comeback Kid", "requirement": {"type": "win_after_queen_loss", "count": 1}, "reward": {"type": "piece_set", "name": "Phoenix"}},
        {"id": "grandmaster", "name": "Grandmaster", "requirement": {"type": "elo_rating", "rating": 1600}, "reward": {"type": "effect", "name": "Crown"}},
    ],
    "property_tycoon": [
        {"id": "monopolist", "name": "Monopolist", "requirement": {"type": "color_monopoly", "count": 1}, "reward": {"type": "token", "name": "Color Token"}},
        {"id": "hotel_mogul", "name": "Hotel Mogul", "requirement": {"type": "hotels_built", "count": 5}, "reward": {"type": "piece", "name": "Golden Hotel"}},
        {"id": "bankruptcy_survivor", "name": "Bankruptcy Survivor", "requirement": {"type": "comeback_win", "min_money": 100}, "reward": {"type": "badge", "name": "Underdog"}},
        {"id": "rent_collector", "name": "Rent Collector", "requirement": {"type": "rent_collected", "amount": 5000}, "reward": {"type": "effect", "name": "Money Bag"}},
        {"id": "tycoon", "name": "Tycoon", "requirement": {"type": "total_wins", "count": 10}, "reward": {"type": "token", "name": "Top Hat"}},
    ],
    "race_home": [
        {"id": "bump_king", "name": "Bump King", "requirement": {"type": "total_bumps", "count": 50}, "reward": {"type": "pawn", "name": "Boxing Glove"}},
        {"id": "clean_sweep", "name": "Clean Sweep", "requirement": {"type": "win_no_bumps", "count": 1}, "reward": {"type": "effect", "name": "Shield"}},
        {"id": "speed_runner", "name": "Speed Runner", "requirement": {"type": "fast_win", "turns": 15}, "reward": {"type": "pawn", "name": "Rocket"}},
        {"id": "sorry_not_sorry", "name": "Sorry Not Sorry", "requirement": {"type": "triple_bump", "count": 1}, "reward": {"type": "emote", "name": "Sorry"}},
    ],
    "mystery_mansion": [
        {"id": "master_detective", "name": "Master Detective", "requirement": {"type": "cases_solved", "count": 10}, "reward": {"type": "badge", "name": "Detective"}},
        {"id": "perfect_deduction", "name": "Perfect Deduction", "requirement": {"type": "minimal_suggestions", "count": 3}, "reward": {"type": "piece", "name": "Magnifying Glass"}},
        {"id": "first_guess", "name": "First Guess", "requirement": {"type": "first_accusation_win", "count": 1}, "reward": {"type": "badge", "name": "Psychic"}},
        {"id": "interrogator", "name": "Interrogator", "requirement": {"type": "disproves", "count": 15}, "reward": {"type": "piece", "name": "Notepad"}},
    ],
    "life_journey": [
        {"id": "millionaire", "name": "Millionaire", "requirement": {"type": "retire_money", "amount": 1000000}, "reward": {"type": "vehicle", "name": "Golden Car"}},
        {"id": "full_house", "name": "Full House", "requirement": {"type": "max_family", "count": 1}, "reward": {"type": "vehicle", "name": "Van"}},
        {"id": "career_climber", "name": "Career Climber", "requirement": {"type": "max_salary", "count": 1}, "reward": {"type": "effect", "name": "Briefcase"}},
        {"id": "risk_taker", "name": "Risk Taker", "requirement": {"type": "all_risky_wins", "count": 1}, "reward": {"type": "effect", "name": "Dice"}},
    ],
}


class AchievementTracker:
    """Track and award achievements."""

    def __init__(self, qube_id: str):
        self.qube_id = qube_id
        self.unlocked: Dict[str, List[str]] = {}  # game -> [achievement_ids]
        self.progress: Dict[str, Dict[str, int]] = {}  # game -> {achievement_id: progress}

    def check_achievement(self, game_type: str, achievement_id: str, value: Any) -> Optional[Dict]:
        """Check if an achievement is earned."""
        if game_type not in ACHIEVEMENTS:
            return None

        for achievement in ACHIEVEMENTS[game_type]:
            if achievement["id"] == achievement_id:
                req = achievement["requirement"]

                # Check if already unlocked
                if achievement_id in self.unlocked.get(game_type, []):
                    return None

                # Check requirement
                if self._check_requirement(req, value):
                    self._unlock(game_type, achievement_id)
                    return {
                        "unlocked": True,
                        "achievement": achievement["name"],
                        "reward": achievement["reward"]
                    }

        return None

    def _check_requirement(self, req: Dict, value: Any) -> bool:
        """Check if requirement is met."""
        req_type = req["type"]

        if req_type in ["count", "unique_openings", "total_bumps", "cases_solved", "total_wins"]:
            return value >= req.get("count", 1)
        elif req_type == "elo_rating":
            return value >= req.get("rating", 1600)
        elif req_type in ["fast_win", "fast_win_seconds"]:
            return value <= req.get("seconds", req.get("turns", 120))
        elif req_type == "retire_money":
            return value >= req.get("amount", 1000000)
        else:
            return value >= 1

    def _unlock(self, game_type: str, achievement_id: str) -> None:
        """Unlock an achievement."""
        if game_type not in self.unlocked:
            self.unlocked[game_type] = []
        self.unlocked[game_type].append(achievement_id)

        logger.info(
            "achievement_unlocked",
            qube_id=self.qube_id,
            game=game_type,
            achievement=achievement_id
        )

    def get_unlocked(self, game_type: Optional[str] = None) -> Dict[str, List[str]]:
        """Get unlocked achievements."""
        if game_type:
            return {game_type: self.unlocked.get(game_type, [])}
        return self.unlocked

    def get_progress(self, game_type: str, achievement_id: str) -> int:
        """Get progress toward an achievement."""
        return self.progress.get(game_type, {}).get(achievement_id, 0)

    def increment_progress(self, game_type: str, achievement_id: str, amount: int = 1) -> None:
        """Increment progress on an achievement."""
        if game_type not in self.progress:
            self.progress[game_type] = {}
        current = self.progress[game_type].get(achievement_id, 0)
        self.progress[game_type][achievement_id] = current + amount
```

---

## Task 7.5: Game Engines

Game engines for Property Tycoon, Race Home, Mystery Mansion, and Life Journey would be implemented in separate files under `game/` directory.

### File Structure

```
game/
├── game_manager.py     # Existing - routes to game engines
├── chess_engine.py     # Existing - chess implementation
├── elo.py              # Existing - ELO rating system
├── achievements.py     # NEW - Achievement tracking
├── property_tycoon.py  # NEW - Property Tycoon engine
├── race_home.py        # NEW - Race Home engine
├── mystery_mansion.py  # NEW - Mystery Mansion engine
├── life_journey.py     # NEW - Life Journey engine
└── __init__.py
```

---

## Task 7.6: Update XP Routing

### File: `core/xp_router.py`

```python
# Board Games tool mappings
BOARD_GAMES_TOOLS = {
    # Sun
    "play_game": {
        "skill_id": "board_games",
        "xp_model": "fixed",  # 1 XP for starting
        "xp_value": 1,
        "category": "board_games"
    },

    # Planets
    "chess_move": {
        "skill_id": "chess",
        "xp_model": "game",  # 0.1/move + outcome
        "category": "board_games"
    },
    "property_tycoon_action": {
        "skill_id": "property_tycoon",
        "xp_model": "game",
        "category": "board_games"
    },
    "race_home_action": {
        "skill_id": "race_home",
        "xp_model": "game",
        "category": "board_games"
    },
    "mystery_mansion_action": {
        "skill_id": "mystery_mansion",
        "xp_model": "game",
        "category": "board_games"
    },
    "life_journey_action": {
        "skill_id": "life_journey",
        "xp_model": "game",
        "category": "board_games"
    },
}

TOOL_TO_SKILL_MAPPING.update(BOARD_GAMES_TOOLS)
```

---

## Task 7.7: Frontend Integration

### File: `src/types/skills.ts`

```typescript
// Board Games skill IDs
export type BoardGamesSkillId =
  | 'board_games'
  | 'chess'
  | 'property_tycoon'
  | 'race_home'
  | 'mystery_mansion'
  | 'life_journey';

// Achievement type
export interface GameAchievement {
  id: string;
  name: string;
  requirement: string;
  reward: {
    type: 'piece_set' | 'piece' | 'effect' | 'token' | 'badge' | 'pawn' | 'emote' | 'vehicle';
    name: string;
  };
  unlocked: boolean;
  progress?: number;
}

// Game session type
export interface GameSession {
  session_id: string;
  game_type: string;
  current_player: string;
  board?: any;
  status: 'active' | 'ended';
}
```

---

## Task 7.8: Testing & Validation

```markdown
## Board Games Testing Checklist

### 7.8.1 Sun Tool Tests
- [ ] `play_game` initializes all 5 game types
- [ ] `play_game` prevents starting second game
- [ ] `play_game` creates GAME block on start
- [ ] `play_game` awards 1 XP for starting

### 7.8.2 Chess Tests (Existing)
- [x] `chess_move` validates moves
- [x] Chess XP formula (0.1/move + outcome)
- [x] ELO rating updates
- [ ] Achievement tracking

### 7.8.3 Property Tycoon Tests
- [ ] Roll, buy, build, trade actions work
- [ ] Property ownership tracked
- [ ] Money transactions correct
- [ ] XP awarded per turn

### 7.8.4 Race Home Tests
- [ ] Card drawing works
- [ ] Pawn movement correct
- [ ] Bumping mechanic works
- [ ] Win detection correct

### 7.8.5 Mystery Mansion Tests
- [ ] Movement between rooms
- [ ] Suggestions and disproves
- [ ] Accusations check solution
- [ ] Solver gets 5 XP bonus

### 7.8.6 Life Journey Tests
- [ ] Spinner works (1-10)
- [ ] Life events trigger
- [ ] Retirement detection
- [ ] Place-based XP awards

### 7.8.7 Achievement Tests
- [ ] Progress tracked correctly
- [ ] Achievements unlock properly
- [ ] Cosmetic rewards granted
- [ ] Notifications sent

### 7.8.8 Resignation Tests
- [ ] Resignation clears active game
- [ ] -2 XP penalty applied
- [ ] GAME block logged
```

---

## Files Modified Summary

| File | Action | Description |
|------|--------|-------------|
| `ai/tools/game_tools.py` | CREATE | All 6 game tool handlers |
| `ai/tools/handlers.py` | MODIFY | Add board_games to SKILL_TREE |
| `game/achievements.py` | CREATE | Achievement tracking system |
| `core/xp_router.py` | MODIFY | Add BOARD_GAMES_TOOLS mapping |
| `src/types/skills.ts` | MODIFY | Add TypeScript interfaces |
| `game/property_tycoon.py` | CREATE | Property Tycoon engine |
| `game/race_home.py` | CREATE | Race Home engine |
| `game/mystery_mansion.py` | CREATE | Mystery Mansion engine |
| `game/life_journey.py` | CREATE | Life Journey engine |

---

## Estimated Effort

| Task | Complexity | Hours |
|------|------------|-------|
| 7.1 Update Skill Definitions | Low | 1 |
| 7.2 Implement Sun Tool | Medium | 2 |
| 7.3 Implement Planet Tools | High | 12 |
| 7.4 Achievement System | Medium | 4 |
| 7.5 Game Engines | High | 20 |
| 7.6 Update XP Routing | Low | 1 |
| 7.7 Frontend Integration | Medium | 4 |
| 7.8 Testing | Medium | 6 |
| **Total** | | **50 hours** |

---

## Notes

1. **Chess Already Implemented**: The chess game is fully functional with visual board, game chat, ELO ratings.

2. **One Game at a Time**: Critical rule to prevent XP farming.

3. **Resignation Penalty**: -2 XP deters gaming the system.

4. **Achievements are Moons**: Unlike other Suns, moons here are achievements that unlock cosmetics, not additional tools.

5. **Game Engines**: Each game needs its own engine implementation. Property Tycoon is the most complex, Life Journey is simplest.
