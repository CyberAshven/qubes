"""
Game Manager - Manages active game state for Qubes

Handles chess games (and future game types) with:
- In-memory game state during play
- File-based crash recovery (active_game.json)
- GAME block creation at game end
- XP calculation and awarding
"""

import json
import uuid
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime

import chess
import chess.pgn
from io import StringIO

from utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class GameState:
    """Active game state stored in memory and backed up to file"""
    game_id: str
    game_type: str  # "chess"

    # Players
    white_player: Dict[str, str]  # {"id": "...", "type": "human|qube"}
    black_player: Dict[str, str]

    # Chess state
    fen: str  # Current position in FEN notation
    moves: List[Dict[str, Any]] = field(default_factory=list)  # Move history

    # Chat messages
    chat_messages: List[Dict[str, Any]] = field(default_factory=list)

    # Metadata
    status: str = "in_progress"  # "in_progress", "completed", "abandoned"
    started_at: float = field(default_factory=time.time)
    last_move_at: float = field(default_factory=time.time)

    # Draw offer state: None or {"offered_by": "white"|"black", "timestamp": float}
    pending_draw_offer: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GameState':
        """Create GameState from dictionary"""
        return cls(**data)


class GameManager:
    """
    Manages active games for a Qube

    - Only one active game at a time per Qube
    - Game state backed up to active_game.json after each move
    - Creates GAME block when game ends
    """

    def __init__(self, qube):
        """
        Initialize GameManager

        Args:
            qube: The Qube instance that owns this GameManager
        """
        self.qube = qube
        self.active_game: Optional[GameState] = None
        self.active_game_file = qube.data_dir / "active_game.json"
        self.game_stats_file = qube.data_dir / "game_stats.json"

        # Check for interrupted game on initialization
        self._load_interrupted_game()

        logger.info("game_manager_initialized", qube_id=qube.qube_id)

    def _load_interrupted_game(self) -> None:
        """Load game from file if app crashed mid-game"""
        if self.active_game_file.exists():
            try:
                with open(self.active_game_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.active_game = GameState.from_dict(data)
                logger.info(
                    "interrupted_game_loaded",
                    qube_id=self.qube.qube_id,
                    game_id=self.active_game.game_id,
                    moves=len(self.active_game.moves)
                )
            except Exception as e:
                logger.error("failed_to_load_interrupted_game", error=str(e))
                # Remove corrupt file
                self.active_game_file.unlink(missing_ok=True)

    def _save_game_state(self) -> None:
        """Atomically save game state to file for crash recovery"""
        if not self.active_game:
            return

        try:
            temp_path = self.active_game_file.with_suffix('.tmp')
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(self.active_game.to_dict(), f, indent=2)
            temp_path.replace(self.active_game_file)  # Atomic on POSIX
        except Exception as e:
            logger.error("failed_to_save_game_state", error=str(e))

    def _clear_game_file(self) -> None:
        """Remove the active game file"""
        self.active_game_file.unlink(missing_ok=True)

    def _load_game_stats(self) -> Dict[str, Any]:
        """Load game stats from file"""
        if self.game_stats_file.exists():
            try:
                with open(self.game_stats_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error("failed_to_load_game_stats", error=str(e))
        return {}

    def _save_game_stats(self, stats: Dict[str, Any]) -> None:
        """Save game stats to file"""
        try:
            temp_path = self.game_stats_file.with_suffix('.tmp')
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=2)
            temp_path.replace(self.game_stats_file)
        except Exception as e:
            logger.error("failed_to_save_game_stats", error=str(e))

    def _calculate_elo_change(
        self,
        player_elo: int,
        opponent_elo: int,
        score: float,  # 1.0 for win, 0.5 for draw, 0.0 for loss
        k_factor: int = 32  # K-factor for beginners
    ) -> int:
        """
        Calculate Elo rating change using standard formula.

        Args:
            player_elo: Current Elo of the player
            opponent_elo: Elo of the opponent
            score: Actual score (1.0 win, 0.5 draw, 0.0 loss)
            k_factor: K-factor (32 for beginners, lower for higher rated)

        Returns:
            Elo change (can be positive or negative)
        """
        # Expected score
        expected = 1.0 / (1.0 + 10 ** ((opponent_elo - player_elo) / 400.0))
        # Elo change
        change = round(k_factor * (score - expected))
        return change

    def _update_game_stats(
        self,
        game_type: str,
        result: str,
        termination: str,
        total_moves: int,
        duration_seconds: int,
        opponent_id: str,
        opponent_type: str,
        qube_color: str,
        xp_earned: int,
        opponent_elo: Optional[int] = None
    ) -> None:
        """
        Update game stats after a game ends

        Args:
            game_type: Type of game (e.g., "chess")
            result: Game result ("1-0", "0-1", "1/2-1/2", "*")
            termination: How game ended (checkmate, resignation, etc.)
            total_moves: Number of moves in the game
            duration_seconds: Game duration
            opponent_id: ID of the opponent
            opponent_type: Type of opponent (human/qube)
            qube_color: Color the Qube played ("white" or "black")
            xp_earned: XP earned from this game
        """
        stats = self._load_game_stats()

        # Initialize game type stats if needed
        if game_type not in stats:
            stats[game_type] = {
                "total_games": 0,
                "wins": 0,
                "losses": 0,
                "draws": 0,
                "checkmate_wins": 0,
                "checkmate_losses": 0,
                "resignation_wins": 0,
                "resignation_losses": 0,
                "stalemate_draws": 0,
                "by_opponent": {},
                "total_moves_played": 0,
                "total_time_played_seconds": 0,
                "longest_game_moves": 0,
                "shortest_win_moves": None,
                "total_xp_earned": 0,
                "last_game_at": None,
                "elo": 1200  # Starting Elo for beginners
            }

        # Ensure elo field exists for existing stats
        if "elo" not in stats[game_type]:
            stats[game_type]["elo"] = 1200

        game_stats = stats[game_type]

        # Determine outcome from Qube's perspective
        qube_won = (qube_color == "white" and result == "1-0") or \
                   (qube_color == "black" and result == "0-1")
        qube_lost = (qube_color == "white" and result == "0-1") or \
                    (qube_color == "black" and result == "1-0")
        is_draw = result == "1/2-1/2"

        # Update overall stats
        game_stats["total_games"] += 1
        game_stats["total_moves_played"] += total_moves
        game_stats["total_time_played_seconds"] += duration_seconds
        game_stats["total_xp_earned"] += xp_earned
        game_stats["last_game_at"] = datetime.now().isoformat()

        if total_moves > game_stats["longest_game_moves"]:
            game_stats["longest_game_moves"] = total_moves

        if qube_won:
            game_stats["wins"] += 1
            if termination == "checkmate":
                game_stats["checkmate_wins"] += 1
            elif termination == "resignation":
                game_stats["resignation_wins"] += 1
            # Track shortest win
            if game_stats["shortest_win_moves"] is None or \
               total_moves < game_stats["shortest_win_moves"]:
                game_stats["shortest_win_moves"] = total_moves
        elif qube_lost:
            game_stats["losses"] += 1
            if termination == "checkmate":
                game_stats["checkmate_losses"] += 1
            elif termination == "resignation":
                game_stats["resignation_losses"] += 1
        elif is_draw:
            game_stats["draws"] += 1
            if termination == "stalemate":
                game_stats["stalemate_draws"] += 1

        # Update opponent-specific stats
        opponent_key = f"{opponent_type}_{opponent_id}"
        if opponent_key not in game_stats["by_opponent"]:
            game_stats["by_opponent"][opponent_key] = {
                "wins": 0,
                "losses": 0,
                "draws": 0,
                "games": 0
            }

        opp_stats = game_stats["by_opponent"][opponent_key]
        opp_stats["games"] += 1
        if qube_won:
            opp_stats["wins"] += 1
        elif qube_lost:
            opp_stats["losses"] += 1
        elif is_draw:
            opp_stats["draws"] += 1

        # Update Elo rating
        current_elo = game_stats["elo"]
        # Default opponent Elo to 1200 if not provided (for humans or unknown)
        opp_elo = opponent_elo if opponent_elo is not None else 1200

        # Determine score for Elo calculation
        if qube_won:
            score = 1.0
        elif qube_lost:
            score = 0.0
        else:  # draw
            score = 0.5

        # Calculate and apply Elo change
        elo_change = self._calculate_elo_change(current_elo, opp_elo, score)
        new_elo = max(100, current_elo + elo_change)  # Minimum Elo of 100
        game_stats["elo"] = new_elo

        self._save_game_stats(stats)

        logger.info(
            "game_stats_updated",
            qube_id=self.qube.qube_id,
            game_type=game_type,
            outcome="win" if qube_won else ("loss" if qube_lost else "draw"),
            total_games=game_stats["total_games"],
            elo=new_elo,
            elo_change=elo_change
        )

    def get_game_stats(self, game_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Get game statistics

        Args:
            game_type: Specific game type to get stats for, or None for all

        Returns:
            Game statistics dictionary
        """
        stats = self._load_game_stats()
        if game_type:
            return stats.get(game_type, {})
        return stats

    def get_elo(self, game_type: str = "chess") -> int:
        """
        Get current Elo rating for a game type.

        Args:
            game_type: Type of game (default: "chess")

        Returns:
            Current Elo rating (default 1200 if not set)
        """
        stats = self._load_game_stats()
        if game_type in stats and "elo" in stats[game_type]:
            return stats[game_type]["elo"]
        return 1200  # Default starting Elo

    def has_active_game(self) -> bool:
        """Check if there's an active game"""
        return self.active_game is not None and self.active_game.status == "in_progress"

    def get_active_game(self) -> Optional[GameState]:
        """Get the active game state"""
        return self.active_game

    def create_game(
        self,
        game_type: str,
        qube_plays_as: str,  # "white" or "black"
        opponent_id: str = "human",
        opponent_type: str = "human"
    ) -> Dict[str, Any]:
        """
        Create a new game

        Args:
            game_type: Type of game (currently only "chess")
            qube_plays_as: Which color the Qube plays ("white" or "black")
            opponent_id: ID of the opponent (default "human")
            opponent_type: Type of opponent ("human" or "qube")

        Returns:
            Dict with game_id, initial FEN, and whose turn it is
        """
        if self.has_active_game():
            return {
                "success": False,
                "error": "A game is already in progress"
            }

        if game_type != "chess":
            return {
                "success": False,
                "error": f"Unsupported game type: {game_type}"
            }

        game_id = str(uuid.uuid4())

        # Determine player assignments
        if qube_plays_as == "white":
            white_player = {"id": self.qube.qube_id, "type": "qube"}
            black_player = {"id": opponent_id, "type": opponent_type}
        else:
            white_player = {"id": opponent_id, "type": opponent_type}
            black_player = {"id": self.qube.qube_id, "type": "qube"}

        # Create initial chess position
        board = chess.Board()

        self.active_game = GameState(
            game_id=game_id,
            game_type=game_type,
            white_player=white_player,
            black_player=black_player,
            fen=board.fen(),
            moves=[],
            chat_messages=[],
            status="in_progress",
            started_at=time.time(),
            last_move_at=time.time()
        )

        self._save_game_state()

        logger.info(
            "game_created",
            qube_id=self.qube.qube_id,
            game_id=game_id,
            qube_plays_as=qube_plays_as
        )

        return {
            "success": True,
            "game_id": game_id,
            "fen": board.fen(),
            "turn": "white",  # White always moves first
            "white_player": white_player,
            "black_player": black_player
        }

    def record_move(
        self,
        move_uci: str,
        player_id: str,
        reasoning: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Record a move in the active game

        Args:
            move_uci: Move in UCI notation (e.g., "e2e4", "e7e8q")
            player_id: ID of the player making the move
            reasoning: Optional reasoning for the move (for Qube moves)

        Returns:
            Dict with success, new FEN, SAN notation, and game status
        """
        if not self.active_game:
            return {"success": False, "error": "No active game"}

        if self.active_game.status != "in_progress":
            return {"success": False, "error": "Game is not in progress"}

        # Load current position
        board = chess.Board(self.active_game.fen)

        # Determine whose turn it is
        current_turn = "white" if board.turn == chess.WHITE else "black"

        # Verify it's the correct player's turn
        expected_player = self.active_game.white_player if current_turn == "white" else self.active_game.black_player
        if expected_player["id"] != player_id:
            return {
                "success": False,
                "error": f"Not {player_id}'s turn. Expected {expected_player['id']}"
            }

        # Parse and validate the move
        try:
            move = chess.Move.from_uci(move_uci)
            if move not in board.legal_moves:
                return {
                    "success": False,
                    "error": f"Illegal move: {move_uci}",
                    "legal_moves": [m.uci() for m in board.legal_moves]
                }
        except ValueError as e:
            return {"success": False, "error": f"Invalid move format: {e}"}

        # Get SAN notation before making the move
        san = board.san(move)
        fen_before = board.fen()

        # Make the move
        board.push(move)
        fen_after = board.fen()

        # Record the move
        move_record = {
            "move_number": len(self.active_game.moves) + 1,
            "player": current_turn,
            "player_id": player_id,
            "uci": move_uci,
            "san": san,
            "fen_before": fen_before,
            "fen_after": fen_after,
            "timestamp": time.time()
        }

        if reasoning:
            move_record["reasoning"] = reasoning

        self.active_game.moves.append(move_record)
        self.active_game.fen = fen_after
        self.active_game.last_move_at = time.time()

        # Cancel any pending draw offer when a move is made
        # (making a move implicitly declines a draw offer)
        if self.active_game.pending_draw_offer:
            logger.debug(
                "draw_offer_cancelled_by_move",
                qube_id=self.qube.qube_id,
                game_id=self.active_game.game_id
            )
            self.active_game.pending_draw_offer = None

        # Save state for crash recovery
        self._save_game_state()

        # Check game end conditions
        is_game_over = board.is_game_over()
        result = None
        termination = None

        if is_game_over:
            if board.is_checkmate():
                # The player who just moved wins
                result = "1-0" if current_turn == "white" else "0-1"
                termination = "checkmate"
            elif board.is_stalemate():
                result = "1/2-1/2"
                termination = "stalemate"
            elif board.is_insufficient_material():
                result = "1/2-1/2"
                termination = "insufficient_material"
            elif board.is_fifty_moves():
                result = "1/2-1/2"
                termination = "fifty_move_rule"
            elif board.is_repetition():
                result = "1/2-1/2"
                termination = "threefold_repetition"
            else:
                result = "1/2-1/2"
                termination = "draw"

        logger.info(
            "move_recorded",
            qube_id=self.qube.qube_id,
            game_id=self.active_game.game_id,
            move=san,
            move_number=len(self.active_game.moves)
        )

        return {
            "success": True,
            "move": move_uci,
            "san": san,
            "fen": fen_after,
            "is_check": board.is_check(),
            "is_game_over": is_game_over,
            "result": result,
            "termination": termination,
            "turn": "black" if current_turn == "white" else "white",
            "move_number": len(self.active_game.moves)
        }

    def add_chat_message(
        self,
        sender_id: str,
        sender_type: str,
        message: str,
        trigger: str = "manual"
    ) -> Dict[str, Any]:
        """
        Add a chat message to the game

        Args:
            sender_id: ID of the sender
            sender_type: "human" or "qube"
            message: The chat message
            trigger: "manual" or "auto_reaction"

        Returns:
            Dict with success status
        """
        if not self.active_game:
            return {"success": False, "error": "No active game"}

        chat_entry = {
            "sender_id": sender_id,
            "sender_type": sender_type,
            "message": message,
            "timestamp": time.time(),
            "trigger": trigger,
            "move_number": len(self.active_game.moves)
        }

        self.active_game.chat_messages.append(chat_entry)
        self._save_game_state()

        return {"success": True, "message": chat_entry}

    def _generate_pgn(self) -> str:
        """Generate PGN string from the game"""
        if not self.active_game:
            return ""

        game = chess.pgn.Game()

        # Set headers
        game.headers["Event"] = "Qubes Game"
        game.headers["Site"] = "Qubes"
        game.headers["Date"] = datetime.fromtimestamp(self.active_game.started_at).strftime("%Y.%m.%d")
        game.headers["White"] = self.active_game.white_player["id"]
        game.headers["Black"] = self.active_game.black_player["id"]

        # Determine result
        if self.active_game.status == "completed":
            # Check last position to determine result
            board = chess.Board(self.active_game.fen)
            if board.is_checkmate():
                # The player who can't move loses
                game.headers["Result"] = "0-1" if board.turn == chess.WHITE else "1-0"
            elif board.is_game_over():
                game.headers["Result"] = "1/2-1/2"
            else:
                game.headers["Result"] = "*"
        else:
            game.headers["Result"] = "*"

        # Add moves
        node = game
        board = chess.Board()
        for move_record in self.active_game.moves:
            move = chess.Move.from_uci(move_record["uci"])
            node = node.add_variation(move)
            board.push(move)

        # Generate PGN string
        exporter = chess.pgn.StringExporter(headers=True, variations=False, comments=False)
        return game.accept(exporter)

    def _extract_key_moments(self) -> List[Dict[str, Any]]:
        """Extract key moments (moves with reasoning) from the game"""
        key_moments = []

        for move_record in self.active_game.moves:
            if move_record.get("reasoning"):
                key_moments.append({
                    "move_number": move_record["move_number"],
                    "player": move_record["player"],
                    "san": move_record["san"],
                    "reasoning": move_record["reasoning"]
                })

        return key_moments

    def _calculate_xp(self, result: str, total_moves: int, termination: str) -> int:
        """
        Calculate XP earned from the game

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
        qube_color = "white" if self.active_game.white_player["id"] == self.qube.qube_id else "black"

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

        # Length bonuses
        if total_moves >= 20:
            xp += 5
        if total_moves >= 40:
            xp += 5

        # Checkmate bonus
        if termination == "checkmate":
            xp += 5

        return xp

    def end_game(
        self,
        result: str,
        termination: str
    ) -> Dict[str, Any]:
        """
        End the current game and create a GAME block

        Args:
            result: Game result ("1-0", "0-1", "1/2-1/2", "*")
            termination: How game ended ("checkmate", "resignation", "stalemate",
                                         "draw_agreement", "timeout", "abandoned")

        Returns:
            Dict with game summary and XP earned
        """
        if not self.active_game:
            return {"success": False, "error": "No active game"}

        # Mark game as completed
        self.active_game.status = "completed"

        # Calculate stats
        total_moves = len(self.active_game.moves)
        duration_seconds = int(time.time() - self.active_game.started_at)

        # Generate PGN
        pgn = self._generate_pgn()

        # Extract key moments
        key_moments = self._extract_key_moments()

        # Calculate XP
        xp_earned = self._calculate_xp(result, total_moves, termination)

        # Create game summary for GAME block
        game_summary = {
            "game_id": self.active_game.game_id,
            "game_type": self.active_game.game_type,
            "white_player": self.active_game.white_player,
            "black_player": self.active_game.black_player,
            "result": result,
            "termination": termination,
            "total_moves": total_moves,
            "pgn": pgn,
            "duration_seconds": duration_seconds,
            "xp_earned": xp_earned,
            "key_moments": key_moments,
            "chat_log": self.active_game.chat_messages
        }

        logger.info(
            "game_ended",
            qube_id=self.qube.qube_id,
            game_id=self.active_game.game_id,
            result=result,
            termination=termination,
            total_moves=total_moves,
            xp_earned=xp_earned
        )

        # Update permanent game stats
        # Determine which color the Qube played
        white_player = self.active_game.white_player
        black_player = self.active_game.black_player

        if white_player.get("type") == "qube" and white_player.get("id") == self.qube.qube_id:
            qube_color = "white"
            opponent_id = black_player.get("id", "unknown")
            opponent_type = black_player.get("type", "human")
        else:
            qube_color = "black"
            opponent_id = white_player.get("id", "unknown")
            opponent_type = white_player.get("type", "human")

        # Get opponent Elo for Qube vs Qube games (will be passed from gui_bridge)
        # For human opponents, default to 1200
        opponent_elo = None  # Will be set by gui_bridge for qube opponents

        self._update_game_stats(
            game_type=self.active_game.game_type,
            result=result,
            termination=termination,
            total_moves=total_moves,
            duration_seconds=duration_seconds,
            opponent_id=opponent_id,
            opponent_type=opponent_type,
            qube_color=qube_color,
            xp_earned=xp_earned,
            opponent_elo=opponent_elo
        )

        # Clear the active game
        self.active_game = None
        self._clear_game_file()

        return {
            "success": True,
            "game_summary": game_summary
        }

    def abandon_game(self) -> Dict[str, Any]:
        """
        Abandon the current game without creating a GAME block

        Returns:
            Dict with success status
        """
        if not self.active_game:
            return {"success": False, "error": "No active game"}

        game_id = self.active_game.game_id

        logger.info(
            "game_abandoned",
            qube_id=self.qube.qube_id,
            game_id=game_id
        )

        # Clear without creating block
        self.active_game = None
        self._clear_game_file()

        return {"success": True, "game_id": game_id}

    def resign_game(self, resigning_player: str) -> Dict[str, Any]:
        """
        Resign the current game (counts as a loss for the resigning player)

        Args:
            resigning_player: "white" or "black" - which color is resigning

        Returns:
            Dict with game result
        """
        if not self.active_game:
            return {"success": False, "error": "No active game"}

        if resigning_player not in ("white", "black"):
            return {"success": False, "error": "Invalid player color"}

        # The resigning player loses
        result = "0-1" if resigning_player == "white" else "1-0"

        logger.info(
            "game_resignation",
            qube_id=self.qube.qube_id,
            game_id=self.active_game.game_id,
            resigning_player=resigning_player,
            result=result
        )

        # End the game with resignation termination
        return self.end_game(result=result, termination="resignation")

    def offer_draw(self, offering_player: str) -> Dict[str, Any]:
        """
        Offer a draw to the opponent

        Args:
            offering_player: "white" or "black" - which color is offering the draw

        Returns:
            Dict with offer status
        """
        if not self.active_game:
            return {"success": False, "error": "No active game"}

        if offering_player not in ("white", "black"):
            return {"success": False, "error": "Invalid player color"}

        # Check if there's already a pending draw offer
        if self.active_game.pending_draw_offer:
            return {
                "success": False,
                "error": "There is already a pending draw offer",
                "pending_offer": self.active_game.pending_draw_offer
            }

        # Create the draw offer
        self.active_game.pending_draw_offer = {
            "offered_by": offering_player,
            "timestamp": time.time()
        }

        # Save game state
        self._save_game_state()

        logger.info(
            "draw_offered",
            qube_id=self.qube.qube_id,
            game_id=self.active_game.game_id,
            offering_player=offering_player
        )

        return {
            "success": True,
            "offer": self.active_game.pending_draw_offer
        }

    def respond_to_draw(self, accepting: bool, responding_player: str) -> Dict[str, Any]:
        """
        Accept or decline a draw offer

        Args:
            accepting: True to accept the draw, False to decline
            responding_player: "white" or "black" - which color is responding

        Returns:
            Dict with response result
        """
        if not self.active_game:
            return {"success": False, "error": "No active game"}

        if responding_player not in ("white", "black"):
            return {"success": False, "error": "Invalid player color"}

        # Check if there's a pending draw offer
        if not self.active_game.pending_draw_offer:
            return {"success": False, "error": "No pending draw offer"}

        # Verify the responding player is not the one who offered
        if self.active_game.pending_draw_offer["offered_by"] == responding_player:
            return {"success": False, "error": "Cannot respond to your own draw offer"}

        if accepting:
            logger.info(
                "draw_accepted",
                qube_id=self.qube.qube_id,
                game_id=self.active_game.game_id,
                responding_player=responding_player
            )
            # End the game as a draw
            return self.end_game(result="1/2-1/2", termination="draw_agreement")
        else:
            # Clear the draw offer
            self.active_game.pending_draw_offer = None
            self._save_game_state()

            logger.info(
                "draw_declined",
                qube_id=self.qube.qube_id,
                game_id=self.active_game.game_id,
                responding_player=responding_player
            )

            return {
                "success": True,
                "accepted": False,
                "message": "Draw offer declined"
            }

    def cancel_draw_offer(self) -> Dict[str, Any]:
        """
        Cancel a pending draw offer (can only be done by the offerer or automatically on move)

        Returns:
            Dict with cancellation status
        """
        if not self.active_game:
            return {"success": False, "error": "No active game"}

        if not self.active_game.pending_draw_offer:
            return {"success": False, "error": "No pending draw offer to cancel"}

        self.active_game.pending_draw_offer = None
        self._save_game_state()

        logger.info(
            "draw_offer_cancelled",
            qube_id=self.qube.qube_id,
            game_id=self.active_game.game_id
        )

        return {"success": True, "message": "Draw offer cancelled"}

    def get_game_context(self) -> Optional[Dict[str, Any]]:
        """
        Get context about the current game for AI prompts

        Returns:
            Dict with game context or None if no active game
        """
        if not self.active_game:
            return None

        board = chess.Board(self.active_game.fen)

        # Build move history in algebraic notation
        move_history = []
        temp_board = chess.Board()
        for i, move_record in enumerate(self.active_game.moves):
            move_num = (i // 2) + 1
            if i % 2 == 0:
                move_history.append(f"{move_num}. {move_record['san']}")
            else:
                move_history[-1] += f" {move_record['san']}"

        # Determine whose turn it is
        qube_color = "white" if self.active_game.white_player["id"] == self.qube.qube_id else "black"
        is_qube_turn = (board.turn == chess.WHITE and qube_color == "white") or \
                       (board.turn == chess.BLACK and qube_color == "black")

        return {
            "game_id": self.active_game.game_id,
            "game_type": self.active_game.game_type,
            "qube_color": qube_color,
            "is_qube_turn": is_qube_turn,
            "fen": self.active_game.fen,
            "move_history": " ".join(move_history) if move_history else "(No moves yet)",
            "total_moves": len(self.active_game.moves),
            "is_check": board.is_check(),
            "is_checkmate": board.is_checkmate(),
            "is_stalemate": board.is_stalemate(),
            "is_draw": board.is_insufficient_material() or board.is_fifty_moves() or board.is_repetition(),
            "is_game_over": board.is_game_over(),
            "legal_moves": [m.uci() for m in board.legal_moves],
            "moves": self.active_game.moves,  # Full move records for display
            "chat_messages": self.active_game.chat_messages,  # Chat history
            "status": self.active_game.status,
            "pending_draw_offer": self.active_game.pending_draw_offer,  # Draw offer state
        }
