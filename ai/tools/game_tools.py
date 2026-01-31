"""
Board Games Tools (Phase 7)

Theme: Play (Have Fun and Entertain)
XP Model: 0.1 XP per turn + outcome bonuses (Win:5, Draw:2, Loss:0, Resign:-2)

6 tools total:
- Sun: play_game (universal entry point)
- Planet 1: chess_move (existing implementation)
- Planet 2: property_tycoon_action
- Planet 3: race_home_action
- Planet 4: mystery_mansion_action
- Planet 5: life_journey_action

NOTE: Game engines are placeholders except for Chess which uses existing implementation.
Real game logic will be added later.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import random
import uuid

from utils.logging import get_logger

logger = get_logger(__name__)


# ============================================================================
# XP CALCULATION
# ============================================================================

def calculate_game_xp(turns: int, outcome: str, resigned: bool = False) -> Dict[str, Any]:
    """
    Calculate XP for a game session.

    Args:
        turns: Number of turns played
        outcome: 'win', 'loss', 'draw', '1st', '2nd', '3rd', '4th'
        resigned: Whether player resigned

    Returns:
        Dict with turn_xp, outcome_xp, penalty, total
    """
    turn_xp = turns * 0.1

    outcome_bonuses = {
        'win': 5, '1st': 5,
        'draw': 2, '2nd': 2,
        '3rd': 1,
        'loss': 0, '4th': 0
    }
    outcome_xp = outcome_bonuses.get(outcome, 0)

    penalty = -2 if resigned else 0

    total = max(0, turn_xp + outcome_xp + penalty)

    return {
        "turn_xp": round(turn_xp, 1),
        "outcome_xp": outcome_xp,
        "penalty": penalty,
        "total": round(total, 1),
        "breakdown": f"{turns} turns × 0.1 + {outcome}({outcome_xp})" + (f" + resign({penalty})" if resigned else "")
    }


# ============================================================================
# SUN TOOL: play_game
# ============================================================================

async def play_game(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sun Tool: play_game

    Universal entry point to start any board game.
    All games unlocked once Board Games Sun is reached.

    Parameters:
        game_type: str - Which game to play (chess, property_tycoon, race_home, mystery_mansion, life_journey)
        opponent: str - Who to play against ('owner', 'ai', or qube_id)

    Returns:
        success: bool
        game_type: str
        session_id: str
        board: initial game state
        your_turn: bool
    """
    game_type = params.get("game_type", "chess")
    opponent = params.get("opponent", "owner")

    valid_games = ["chess", "property_tycoon", "race_home", "mystery_mansion", "life_journey"]
    if game_type not in valid_games:
        return {
            "success": False,
            "error": f"Unknown game type: {game_type}. Valid: {valid_games}"
        }

    # Check if already in a game
    if hasattr(qube, 'active_game') and qube.active_game:
        return {
            "success": False,
            "error": "Already in a game. Finish current game first.",
            "current_game": qube.active_game.get("game_type")
        }

    session_id = str(uuid.uuid4())[:8]

    # Initialize game based on type
    if game_type == "chess":
        game_state = await _init_chess(qube, session_id, opponent)
    elif game_type == "property_tycoon":
        game_state = _init_property_tycoon(session_id, opponent)
    elif game_type == "race_home":
        game_state = _init_race_home(session_id, opponent)
    elif game_type == "mystery_mansion":
        game_state = _init_mystery_mansion(session_id, opponent)
    elif game_type == "life_journey":
        game_state = _init_life_journey(session_id, opponent)

    # Store active game
    qube.active_game = game_state

    logger.info("game_started", game_type=game_type, session_id=session_id, opponent=opponent)

    return {
        "success": True,
        "game_type": game_type,
        "session_id": session_id,
        "board": game_state.get("board"),
        "your_turn": game_state.get("current_player") == "qube",
        "message": f"Let's play {game_type.replace('_', ' ').title()}! Good luck!"
    }


async def _init_chess(qube, session_id: str, opponent: str) -> Dict:
    """Initialize chess game using existing game_manager if available."""
    if hasattr(qube, 'game_manager'):
        try:
            return await qube.game_manager.new_game(game_type="chess", player=opponent)
        except Exception as e:
            logger.warning("game_manager_unavailable", error=str(e))

    # Fallback placeholder
    return {
        "session_id": session_id,
        "game_type": "chess",
        "board": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "current_player": "qube",
        "opponent": opponent,
        "turns": 0
    }


def _init_property_tycoon(session_id: str, opponent: str) -> Dict:
    """Initialize Property Tycoon (Monopoly-style) game."""
    return {
        "session_id": session_id,
        "game_type": "property_tycoon",
        "board": "[40 spaces - properties, railroads, utilities, specials]",
        "players": ["qube", opponent],
        "current_player": "qube",
        "money": {"qube": 1500, "opponent": 1500},
        "properties": {"qube": [], "opponent": []},
        "position": {"qube": 0, "opponent": 0},
        "turns": 0
    }


def _init_race_home(session_id: str, opponent: str) -> Dict:
    """Initialize Race Home (Sorry-style) game."""
    return {
        "session_id": session_id,
        "game_type": "race_home",
        "board": "[60 space track with start, home, safety zones]",
        "players": ["qube", opponent],
        "current_player": "qube",
        "pawns": {
            "qube": [{"id": i, "position": "start"} for i in range(1, 5)],
            "opponent": [{"id": i, "position": "start"} for i in range(1, 5)]
        },
        "turns": 0
    }


def _init_mystery_mansion(session_id: str, opponent: str) -> Dict:
    """Initialize Mystery Mansion (Clue-style) game."""
    suspects = ["Colonel Mustard", "Miss Scarlet", "Professor Plum",
                "Mrs. Peacock", "Mr. Green", "Mrs. White"]
    weapons = ["Knife", "Candlestick", "Revolver", "Rope", "Lead Pipe", "Wrench"]
    rooms = ["Kitchen", "Ballroom", "Conservatory", "Dining Room",
             "Lounge", "Hall", "Library", "Study", "Billiard Room"]

    return {
        "session_id": session_id,
        "game_type": "mystery_mansion",
        "board": "[Mansion with 9 rooms]",
        "players": ["qube", opponent],
        "current_player": "qube",
        "suspects": suspects,
        "weapons": weapons,
        "rooms": rooms,
        "solution": {
            "suspect": random.choice(suspects),
            "weapon": random.choice(weapons),
            "room": random.choice(rooms)
        },
        "notes": {"qube": [], "opponent": []},
        "turns": 0
    }


def _init_life_journey(session_id: str, opponent: str) -> Dict:
    """Initialize Life Journey (Game of Life-style) game."""
    return {
        "session_id": session_id,
        "game_type": "life_journey",
        "board": "[Life path with career, family, and retirement spaces]",
        "players": ["qube", opponent],
        "current_player": "qube",
        "position": {"qube": 0, "opponent": 0},
        "money": {"qube": 10000, "opponent": 10000},
        "career": {"qube": None, "opponent": None},
        "family": {"qube": {"spouse": False, "kids": 0}, "opponent": {"spouse": False, "kids": 0}},
        "retired": {"qube": False, "opponent": False},
        "turns": 0
    }


# ============================================================================
# PLANET 1: chess_move (existing)
# ============================================================================

async def chess_move(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Planet Tool: chess_move

    Make a chess move. Uses existing game_manager if available.
    XP: 0.1/move + outcome (Loss:0, Draw:2, Win:5, Resign:-2)

    Parameters:
        move: str - Move in algebraic notation (e.g., 'e4', 'Nf3', 'O-O')
        session_id: str - Game session ID (optional)
        resign: bool - Resign the game

    Returns:
        success: bool
        move: str
        valid: bool
        board: updated position
        game_over: bool
        xp_earned: float
    """
    move = params.get("move")
    resign = params.get("resign", False)

    if not hasattr(qube, 'active_game') or qube.active_game.get("game_type") != "chess":
        return {"success": False, "error": "No active chess game"}

    game = qube.active_game

    # Handle resignation
    if resign:
        xp = calculate_game_xp(game.get("turns", 0), "loss", resigned=True)
        qube.active_game = None
        return {
            "success": True,
            "resigned": True,
            "game_over": True,
            "outcome": "loss",
            "xp": xp
        }

    if not move:
        return {"success": False, "error": "Move is required"}

    # Use existing game_manager if available
    if hasattr(qube, 'game_manager'):
        try:
            result = await qube.game_manager.make_move(
                session_id=game.get("session_id"),
                move=move
            )
            return result
        except Exception as e:
            logger.warning("game_manager_move_failed", error=str(e))

    # Placeholder response
    game["turns"] = game.get("turns", 0) + 1

    return {
        "success": True,
        "move": move,
        "valid": True,
        "board": "[placeholder - move applied]",
        "game_over": False,
        "your_turn": False,
        "xp_earned": 0.1,
        "message": f"Move {move} played. Opponent's turn."
    }


# ============================================================================
# PLANET 2: property_tycoon_action
# ============================================================================

async def property_tycoon_action(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Planet Tool: property_tycoon_action

    Take a Property Tycoon turn.
    XP: 0.1/turn + placement (4th:0, 3rd:1, 2nd:2, 1st:5)

    Parameters:
        action: str - roll, buy, build, trade, mortgage, end_turn, resign
        property_id: int - Property to act on (for buy/build/mortgage)

    Returns:
        success: bool
        action: str
        result: action-specific result
        xp_earned: float
    """
    action = params.get("action")

    if not hasattr(qube, 'active_game') or qube.active_game.get("game_type") != "property_tycoon":
        return {"success": False, "error": "No active Property Tycoon game"}

    game = qube.active_game
    valid_actions = ["roll", "buy", "build", "trade", "mortgage", "end_turn", "resign"]

    if action not in valid_actions:
        return {"success": False, "error": f"Invalid action. Valid: {valid_actions}"}

    if action == "resign":
        xp = calculate_game_xp(game.get("turns", 0), "loss", resigned=True)
        qube.active_game = None
        return {"success": True, "resigned": True, "game_over": True, "xp": xp}

    result = {"action": action}

    if action == "roll":
        dice = [random.randint(1, 6), random.randint(1, 6)]
        result["dice"] = dice
        result["total"] = sum(dice)
        result["message"] = f"Rolled {dice[0]} + {dice[1]} = {sum(dice)}"
        game["turns"] = game.get("turns", 0) + 1

    elif action == "buy":
        result["message"] = "[Placeholder] Property purchased"

    elif action == "build":
        result["message"] = "[Placeholder] House/hotel built"

    elif action == "end_turn":
        result["message"] = "Turn ended. Opponent's turn."
        game["current_player"] = "opponent"

    result["success"] = True
    result["xp_earned"] = 0.1
    return result


# ============================================================================
# PLANET 3: race_home_action
# ============================================================================

async def race_home_action(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Planet Tool: race_home_action

    Take a Race Home (Sorry-style) action.
    XP: 0.1/turn + placement

    Parameters:
        action: str - draw, move, resign
        pawn: int - Which pawn to move (1-4)

    Returns:
        success: bool
        action: str
        card: int (if draw)
        xp_earned: float
    """
    action = params.get("action")
    pawn = params.get("pawn", 1)

    if not hasattr(qube, 'active_game') or qube.active_game.get("game_type") != "race_home":
        return {"success": False, "error": "No active Race Home game"}

    game = qube.active_game
    valid_actions = ["draw", "move", "resign"]

    if action not in valid_actions:
        return {"success": False, "error": f"Invalid action. Valid: {valid_actions}"}

    if action == "resign":
        xp = calculate_game_xp(game.get("turns", 0), "loss", resigned=True)
        qube.active_game = None
        return {"success": True, "resigned": True, "game_over": True, "xp": xp}

    result = {"action": action}

    if action == "draw":
        # Cards: 1,2,3,4,5,7,8,10,11,12 (no 6 or 9)
        card = random.choice([1, 2, 3, 4, 5, 7, 8, 10, 11, 12])
        result["card"] = card
        result["message"] = f"Drew a {card}"
        game["last_card"] = card

    elif action == "move":
        card = game.get("last_card", 0)
        result["pawn"] = pawn
        result["moved"] = card
        result["message"] = f"Moved pawn {pawn} forward {card} spaces"
        game["turns"] = game.get("turns", 0) + 1

    result["success"] = True
    result["xp_earned"] = 0.1
    return result


# ============================================================================
# PLANET 4: mystery_mansion_action
# ============================================================================

async def mystery_mansion_action(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Planet Tool: mystery_mansion_action

    Take a Mystery Mansion (Clue-style) action.
    XP: 0.1/turn + Solver gets 5 XP

    Parameters:
        action: str - move, suggest, accuse, resign
        room: str - Room to move to or include in suggestion
        suspect: str - Suspect to suggest/accuse
        weapon: str - Weapon to suggest/accuse

    Returns:
        success: bool
        action: str
        disproven: bool (for suggestions)
        correct: bool (for accusations)
        xp_earned: float
    """
    action = params.get("action")

    if not hasattr(qube, 'active_game') or qube.active_game.get("game_type") != "mystery_mansion":
        return {"success": False, "error": "No active Mystery Mansion game"}

    game = qube.active_game
    valid_actions = ["move", "suggest", "accuse", "resign"]

    if action not in valid_actions:
        return {"success": False, "error": f"Invalid action. Valid: {valid_actions}"}

    if action == "resign":
        xp = calculate_game_xp(game.get("turns", 0), "loss", resigned=True)
        qube.active_game = None
        return {"success": True, "resigned": True, "game_over": True, "xp": xp}

    result = {"action": action}

    if action == "move":
        room = params.get("room")
        if room and room in game["rooms"]:
            result["room"] = room
            result["message"] = f"Moved to the {room}"
        else:
            return {"success": False, "error": f"Invalid room. Valid: {game['rooms']}"}

    elif action == "suggest":
        suspect = params.get("suspect")
        weapon = params.get("weapon")
        room = params.get("room")

        result["suggestion"] = {"suspect": suspect, "weapon": weapon, "room": room}
        # Placeholder - randomly disprove
        result["disproven"] = random.choice([True, False])
        result["message"] = f"Suggested {suspect} with {weapon} in {room}"
        game["turns"] = game.get("turns", 0) + 1

    elif action == "accuse":
        suspect = params.get("suspect")
        weapon = params.get("weapon")
        room = params.get("room")

        solution = game["solution"]
        correct = (suspect == solution["suspect"] and
                   weapon == solution["weapon"] and
                   room == solution["room"])

        result["accusation"] = {"suspect": suspect, "weapon": weapon, "room": room}
        result["correct"] = correct
        result["game_over"] = True

        if correct:
            xp = calculate_game_xp(game.get("turns", 0), "win")
            result["message"] = f"Correct! It was {suspect} with the {weapon} in the {room}!"
        else:
            xp = calculate_game_xp(game.get("turns", 0), "loss")
            result["message"] = f"Wrong! The real solution: {solution['suspect']} with {solution['weapon']} in {solution['room']}"
            result["solution"] = solution

        result["xp"] = xp
        qube.active_game = None
        return {"success": True, **result}

    result["success"] = True
    result["xp_earned"] = 0.1
    return result


# ============================================================================
# PLANET 5: life_journey_action
# ============================================================================

async def life_journey_action(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Planet Tool: life_journey_action

    Take a Life Journey (Game of Life-style) action.
    XP: 0.1/turn + placement based on final wealth

    Parameters:
        action: str - spin, choose_career, choose_path, retire, resign
        choice: str - For career/path choices

    Returns:
        success: bool
        action: str
        spin: int (if spin)
        event: str (what happened)
        xp_earned: float
    """
    action = params.get("action")
    choice = params.get("choice")

    if not hasattr(qube, 'active_game') or qube.active_game.get("game_type") != "life_journey":
        return {"success": False, "error": "No active Life Journey game"}

    game = qube.active_game
    valid_actions = ["spin", "choose_career", "choose_path", "retire", "resign"]

    if action not in valid_actions:
        return {"success": False, "error": f"Invalid action. Valid: {valid_actions}"}

    if action == "resign":
        xp = calculate_game_xp(game.get("turns", 0), "loss", resigned=True)
        qube.active_game = None
        return {"success": True, "resigned": True, "game_over": True, "xp": xp}

    result = {"action": action}

    if action == "spin":
        spin = random.randint(1, 10)
        result["spin"] = spin
        result["message"] = f"Spun a {spin}! Moving forward."
        game["turns"] = game.get("turns", 0) + 1

        # Random life events
        events = [
            "Payday! +$5000",
            "Tax return: +$2000",
            "Car repair: -$1000",
            "Got married!",
            "Had a baby!",
            "Promotion!",
            "Nothing eventful"
        ]
        result["event"] = random.choice(events)

    elif action == "choose_career":
        careers = ["Doctor ($100k)", "Lawyer ($90k)", "Teacher ($50k)",
                   "Artist ($40k)", "Entrepreneur ($??)"]
        result["available_careers"] = careers
        if choice:
            result["chosen"] = choice
            result["message"] = f"Chose career: {choice}"
        else:
            result["message"] = "Choose a career from the list"

    elif action == "retire":
        final_money = game["money"]["qube"]
        # Determine placement based on wealth
        if final_money >= 1000000:
            outcome = "1st"
        elif final_money >= 500000:
            outcome = "2nd"
        elif final_money >= 100000:
            outcome = "3rd"
        else:
            outcome = "4th"

        xp = calculate_game_xp(game.get("turns", 0), outcome)
        result["final_wealth"] = final_money
        result["placement"] = outcome
        result["game_over"] = True
        result["xp"] = xp
        result["message"] = f"Retired with ${final_money}! Placed {outcome}."
        qube.active_game = None
        return {"success": True, **result}

    result["success"] = True
    result["xp_earned"] = 0.1
    return result


# ============================================================================
# HELPER: End game and calculate XP
# ============================================================================

async def end_game(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    End the current game and calculate final XP.

    Parameters:
        outcome: str - 'win', 'loss', 'draw', '1st', '2nd', '3rd', '4th'
        resign: bool - Whether resigning
    """
    if not hasattr(qube, 'active_game') or not qube.active_game:
        return {"success": False, "error": "No active game"}

    game = qube.active_game
    outcome = params.get("outcome", "loss")
    resign = params.get("resign", False)

    xp = calculate_game_xp(game.get("turns", 0), outcome, resign)

    qube.active_game = None

    return {
        "success": True,
        "game_type": game["game_type"],
        "outcome": outcome,
        "xp": xp
    }


# ============================================================================
# EXPORT HANDLERS
# ============================================================================

GAME_TOOL_HANDLERS = {
    # Sun
    "play_game": play_game,

    # Planets
    "chess_move": chess_move,
    "property_tycoon_action": property_tycoon_action,
    "race_home_action": race_home_action,
    "mystery_mansion_action": mystery_mansion_action,
    "life_journey_action": life_journey_action,
}
