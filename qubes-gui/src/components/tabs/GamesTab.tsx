import React, { useState, useEffect, useCallback, useRef } from 'react';
import { invoke, convertFileSrc } from '@tauri-apps/api/core';
import { Qube, GameState, MoveResult } from '../../types';
import { useQubeSelection } from '../../hooks/useQubeSelection';
import { useAuth } from '../../hooks/useAuth';
import { GlassCard, GlassButton } from '../glass';
import { ChessGame } from '../games/ChessGame';

interface GamesTabProps {
  qubes: Qube[];
}

type GameSetupState = 'idle' | 'selecting' | 'playing';

export const GamesTab: React.FC<GamesTabProps> = ({ qubes }) => {
  const { userId, password } = useAuth();
  const selectedQubeIds = useQubeSelection((state) => state.selectionByTab['games'] ?? []);

  // Game setup state
  const [setupState, setSetupState] = useState<GameSetupState>('idle');
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Player configuration
  const [selectedColor, setSelectedColor] = useState<'white' | 'black' | 'random'>('random');
  const [gameMode, setGameMode] = useState<'human-vs-qube' | 'qube-vs-qube'>('human-vs-qube');

  // Flag to trigger Qube's auto-move (avoids stale closure in setTimeout)
  const [pendingQubeMove, setPendingQubeMove] = useState(false);

  // Permanent game statistics for both players
  type GameStats = {
    total_games?: number;
    wins?: number;
    losses?: number;
    draws?: number;
    checkmate_wins?: number;
    checkmate_losses?: number;
    longest_game_moves?: number;
    shortest_win_moves?: number | null;
    total_xp_earned?: number;
    elo?: number;
  };
  const [primaryStats, setPrimaryStats] = useState<GameStats | null>(null);
  const [secondaryStats, setSecondaryStats] = useState<GameStats | null>(null);
  // Legacy alias for compatibility
  const permanentStats = primaryStats;

  // Ref to hold the latest handleRequestQubeMove without causing effect re-runs
  const handleRequestQubeMoveRef = useRef<(() => Promise<void>) | undefined>(undefined);

  // Get selected qubes
  const selectedQubes = qubes.filter(q => selectedQubeIds.includes(q.qube_id));
  const primaryQube = selectedQubes[0];
  const secondaryQube = selectedQubes[1];

  // Check for active game on mount
  useEffect(() => {
    const checkActiveGame = async () => {
      if (!primaryQube || !password) return;

      try {
        const result = await invoke<{
          success: boolean;
          has_active_game: boolean;
          game?: any;
          error?: string;
        }>('get_game_state', {
          userId,
          qubeId: primaryQube.qube_id,
          password,
        });

        if (result.success && result.has_active_game && result.game) {
          setGameState(result.game);
          setSetupState('playing');
        }
      } catch (err) {
        console.error('Failed to check active game:', err);
      }
    };

    checkActiveGame();
  }, [primaryQube?.qube_id, userId, password]);

  // Fetch permanent game stats for both players
  useEffect(() => {
    const fetchStats = async (qubeId: string): Promise<GameStats | null> => {
      try {
        const result = await invoke<{
          success: boolean;
          stats?: GameStats;
          error?: string;
        }>('get_game_stats', {
          userId,
          qubeId,
          password,
          gameType: 'chess',
        });
        return result.success && result.stats ? result.stats : null;
      } catch (err) {
        console.error('Failed to fetch game stats for', qubeId, err);
        return null;
      }
    };

    const fetchAllStats = async () => {
      if (!primaryQube || !password) return;

      // Fetch primary Qube stats
      const primary = await fetchStats(primaryQube.qube_id);
      setPrimaryStats(primary);

      // Fetch secondary Qube stats if selected
      if (secondaryQube) {
        const secondary = await fetchStats(secondaryQube.qube_id);
        setSecondaryStats(secondary);
      } else {
        setSecondaryStats(null);
      }
    };

    fetchAllStats();
  }, [primaryQube?.qube_id, secondaryQube?.qube_id, userId, password]);

  const handleStartGame = async () => {
    if (!primaryQube || !password) {
      setError('Please select a Qube to play with');
      return;
    }

    // For Qube vs Qube, need two qubes
    if (gameMode === 'qube-vs-qube' && !secondaryQube) {
      setError('Please select two Qubes for Qube vs Qube mode');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const result = await invoke<{
        success: boolean;
        game_id?: string;
        fen?: string;
        white_player?: any;
        black_player?: any;
        status?: string;
        current_turn?: string;
        error?: string;
      }>('start_game', {
        userId,
        qubeId: primaryQube.qube_id,
        gameType: 'chess',
        opponentType: gameMode === 'human-vs-qube' ? 'human' : 'qube',
        opponentId: gameMode === 'qube-vs-qube' ? secondaryQube?.qube_id : null,
        qubeColor: gameMode === 'human-vs-qube'
          ? (selectedColor === 'white' ? 'black' : selectedColor === 'black' ? 'white' : 'random')
          : 'white', // First qube plays white in Qube vs Qube
        password,
      });

      if (result.success && result.game_id) {
        const newGameState: GameState = {
          game_id: result.game_id,
          game_type: 'chess',
          fen: result.fen || 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
          moves: [],
          white_player: result.white_player,
          black_player: result.black_player,
          status: 'active',
          current_turn: 'white',
          total_moves: 0,
          chat_messages: [],
          start_time: new Date().toISOString(),
          your_color: gameMode === 'human-vs-qube'
            ? (result.white_player?.type === 'human' ? 'white' : 'black')
            : undefined,
        };
        setGameState(newGameState);
        setSetupState('playing');

        // Auto-start Qube vs Qube game - trigger first Qube's move
        if (gameMode === 'qube-vs-qube') {
          console.log('🎯 Qube vs Qube: Auto-starting first move...');
          setPendingQubeMove(true);
        }
      } else {
        setError(result.error || 'Failed to start game');
      }
    } catch (err) {
      console.error('Failed to start game:', err);
      setError(String(err));
    } finally {
      setIsLoading(false);
    }
  };

  // Define handleRequestQubeMove first (used by handleMove)
  const handleRequestQubeMove = useCallback(async () => {
    console.log('🤖 handleRequestQubeMove called', {
      current_turn: gameState?.current_turn,
      your_color: gameState?.your_color,
      status: gameState?.status,
      gameMode,
    });

    if (!primaryQube || !password || !gameState) {
      console.log('❌ Missing primaryQube, password, or gameState');
      return;
    }

    // Guard: Only request Qube move when it's NOT the human's turn (for human-vs-qube mode only)
    // In qube-vs-qube mode, always allow since both players are Qubes
    if (gameMode === 'human-vs-qube') {
      const yourColor = gameState.your_color || 'white';
      if (gameState.current_turn === yourColor) {
        console.log('❌ handleRequestQubeMove: It\'s the human\'s turn, not requesting Qube move');
        return;
      }
    }

    setIsLoading(true);

    // Determine which Qube should move based on current turn
    let movingQubeId = primaryQube.qube_id;
    if (gameMode === 'qube-vs-qube' && gameState) {
      // In Qube vs Qube, we need to find which qube is playing the current turn's color
      const currentTurn = gameState.current_turn; // 'white' or 'black'
      const whitePlayerId = gameState.white_player?.id;
      const blackPlayerId = gameState.black_player?.id;

      if (currentTurn === 'white' && whitePlayerId) {
        movingQubeId = whitePlayerId;
      } else if (currentTurn === 'black' && blackPlayerId) {
        movingQubeId = blackPlayerId;
      }
      console.log('🎯 Qube vs Qube: Requesting move from', movingQubeId, 'for', currentTurn);
    }

    console.log('🔄 Requesting Qube move from backend...');
    try {
      const result = await invoke<{
        success: boolean;
        qube_response?: string;
        game_state?: any;
        error?: string;
      }>('request_qube_move', {
        userId,
        qubeId: movingQubeId,
        password,
      });
      console.log('📥 request_qube_move result:', JSON.stringify(result, null, 2));

      if (result.success && result.game_state) {
        console.log('✅ Qube move successful, updating game state with FEN:', result.game_state.fen);

        // Check if game is over from the game state (backend now provides is_game_over)
        const isGameOver = result.game_state.is_game_over ||
                           result.game_state.status === 'completed' ||
                           result.game_state.is_checkmate ||
                           result.game_state.is_stalemate ||
                           result.game_state.is_draw;

        setGameState(prev => prev ? {
          ...prev,
          fen: result.game_state.fen,
          moves: result.game_state.moves || prev.moves,
          total_moves: result.game_state.total_moves || prev.total_moves,
          current_turn: result.game_state.fen.split(' ')[1] === 'w' ? 'white' : 'black',
          status: isGameOver ? 'completed' : (result.game_state.status || prev.status),
          chat_messages: result.game_state.chat_messages || prev.chat_messages,
          pending_draw_offer: result.game_state.pending_draw_offer ?? prev.pending_draw_offer,
        } : null);

        // Check if game is over - trigger end_game to create GAME block
        if (isGameOver) {
          console.log('🏁 Game over detected after Qube move!', {
            status: result.game_state.status,
            is_checkmate: result.game_state.is_checkmate,
            is_stalemate: result.game_state.is_stalemate,
            is_draw: result.game_state.is_draw,
          });

          // Determine result and termination from game state
          let gameResult = 'draw';
          let termination = 'unknown';

          if (result.game_state.is_checkmate) {
            // If it's checkmate and black just moved, black wins (since white is now in checkmate)
            const winner = result.game_state.fen.split(' ')[1] === 'w' ? 'black' : 'white';
            gameResult = winner === 'white' ? '1-0' : '0-1';
            termination = 'checkmate';
          } else if (result.game_state.is_stalemate) {
            gameResult = '1/2-1/2';
            termination = 'stalemate';
          } else if (result.game_state.is_draw) {
            gameResult = '1/2-1/2';
            termination = 'draw';
          }

          // Call end_game to create GAME block and award XP
          invoke('end_game', {
            userId,
            qubeId: primaryQube.qube_id,
            result: gameResult,
            termination,
            password,
          }).then(() => {
            console.log('✅ GAME block created successfully');
          }).catch(err => {
            console.error('❌ Failed to create GAME block:', err);
          });
        } else if (gameMode === 'qube-vs-qube') {
          // Auto-continue Qube vs Qube game - trigger next Qube's move
          console.log('⏳ Qube vs Qube: Setting pendingQubeMove for next Qube...');
          setPendingQubeMove(true);
        }
      } else {
        console.log('❌ Qube move failed or no game_state returned:', {
          success: result.success,
          hasGameState: !!result.game_state,
          error: result.error,
          qubeResponse: result.qube_response
        });
      }
    } catch (err) {
      console.error('Failed to request qube move:', err);
    } finally {
      setIsLoading(false);
    }
  }, [primaryQube, password, userId, gameState, gameMode]);

  // Keep the ref updated with the latest callback
  useEffect(() => {
    handleRequestQubeMoveRef.current = handleRequestQubeMove;
  }, [handleRequestQubeMove]);

  // Effect to trigger Qube's auto-move (uses ref to avoid stale closure AND dependency issues)
  useEffect(() => {
    if (!pendingQubeMove) return;

    console.log('🎯 pendingQubeMove effect triggered, scheduling move...');
    const timer = setTimeout(() => {
      console.log('⏰ Timer fired, calling handleRequestQubeMove');
      if (handleRequestQubeMoveRef.current) {
        handleRequestQubeMoveRef.current();
      }
      setPendingQubeMove(false);
    }, 500);

    return () => {
      console.log('🧹 Cleanup: clearing timer');
      clearTimeout(timer);
    };
  }, [pendingQubeMove]); // Only depend on pendingQubeMove, use ref for callback

  const handleMove = useCallback(async (move: string): Promise<MoveResult> => {
    console.log('🎮 handleMove called with move:', move, 'gameState:', {
      current_turn: gameState?.current_turn,
      your_color: gameState?.your_color,
      status: gameState?.status,
    });

    if (!primaryQube || !password || !gameState) {
      console.log('❌ handleMove: No active game or missing data');
      return { success: false, error: 'No active game' };
    }

    // Guard: Only allow human moves when it's the human's turn
    const yourColor = gameState.your_color || 'white';
    if (gameState.current_turn !== yourColor) {
      console.log('❌ handleMove: Not human\'s turn, ignoring');
      return { success: false, error: 'Not your turn' };
    }

    try {
      const result = await invoke<MoveResult>('make_move', {
        userId,
        qubeId: primaryQube.qube_id,
        chessMove: move,
        playerType: 'human',
        password,
      });

      if (result.success && result.fen) {
        // Update basic game state - moves array will be fully refreshed by handleRequestQubeMove
        setGameState(prev => prev ? {
          ...prev,
          fen: result.fen!,
          // Don't append move_made string here - wait for full game state refresh with MoveRecord objects
          total_moves: result.move_number || prev.total_moves + 1,
          current_turn: result.fen!.split(' ')[1] === 'w' ? 'white' : 'black',
          status: result.game_over ? 'completed' : 'active',
        } : null);

        // Check if game is over - trigger end_game to create GAME block
        if (result.game_over) {
          console.log('🏁 Game over detected after human move!', {
            result: result.result,
            termination: result.termination
          });
          // Call end_game to create GAME block and award XP
          invoke('end_game', {
            userId,
            qubeId: primaryQube.qube_id,
            result: result.result || 'unknown',
            termination: result.termination || 'unknown',
            password,
          }).then(() => {
            console.log('✅ GAME block created successfully');
          }).catch(err => {
            console.error('❌ Failed to create GAME block:', err);
          });
        } else if (gameMode === 'human-vs-qube') {
          // Auto-trigger Qube's move in Human vs Qube mode (if game not over)
          console.log('⏳ Setting pendingQubeMove flag to trigger auto-move...');
          setPendingQubeMove(true);
        }
      }

      return result;
    } catch (err) {
      console.error('Failed to make move:', err);
      return { success: false, error: String(err) };
    }
  }, [primaryQube, password, gameState, userId, gameMode]);

  const handleAbandonGame = async () => {
    if (!primaryQube || !password) return;

    try {
      await invoke('abandon_game', {
        userId,
        qubeId: primaryQube.qube_id,
        password,
      });
      setGameState(null);
      setSetupState('idle');
    } catch (err) {
      console.error('Failed to abandon game:', err);
    }
  };

  const handleRematch = useCallback(async () => {
    if (!primaryQube || !password) return;

    // Determine swapped color for human vs qube (swap who plays white)
    // For qube vs qube, swap the primary and secondary qubes
    const currentYourColor = gameState?.your_color;
    const newColor: 'white' | 'black' | 'random' = currentYourColor === 'white' ? 'black' : 'white';

    // Clear current game state
    setGameState(null);
    setIsLoading(true);
    setError(null);

    try {
      // Start new game with swapped colors
      const result = await invoke<{
        success: boolean;
        game_id?: string;
        fen?: string;
        white_player?: any;
        black_player?: any;
        status?: string;
        current_turn?: string;
        error?: string;
      }>('start_game', {
        userId,
        qubeId: primaryQube.qube_id,
        gameType: 'chess',
        opponentType: gameMode === 'human-vs-qube' ? 'human' : 'qube',
        opponentId: gameMode === 'qube-vs-qube' ? secondaryQube?.qube_id : null,
        qubeColor: gameMode === 'human-vs-qube'
          ? (newColor === 'white' ? 'black' : 'white') // Qube gets opposite of human's color
          : 'white',
        password,
      });

      if (result.success && result.game_id) {
        const newGameState: GameState = {
          game_id: result.game_id,
          game_type: 'chess',
          fen: result.fen || 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
          moves: [],
          white_player: result.white_player,
          black_player: result.black_player,
          status: 'active',
          current_turn: 'white',
          total_moves: 0,
          chat_messages: [],
          start_time: new Date().toISOString(),
          your_color: gameMode === 'human-vs-qube' ? newColor : undefined,
        };
        setGameState(newGameState);

        // For human vs qube, if human is black, trigger Qube's first move
        if (gameMode === 'human-vs-qube' && newColor === 'black') {
          setPendingQubeMove(true);
        }

        // For qube vs qube, auto-start first move
        if (gameMode === 'qube-vs-qube') {
          setPendingQubeMove(true);
        }
      } else {
        setError(result.error || 'Failed to start rematch');
        setSetupState('idle');
      }
    } catch (err) {
      console.error('Failed to start rematch:', err);
      setError(String(err));
      setSetupState('idle');
    } finally {
      setIsLoading(false);
    }
  }, [primaryQube, password, gameState, userId, gameMode, secondaryQube]);

  const handleEndGame = async (result: string, termination: string) => {
    if (!primaryQube || !password) return;

    try {
      await invoke('end_game', {
        userId,
        qubeId: primaryQube.qube_id,
        result,
        termination,
        password,
      });
      setGameState(null);
      setSetupState('idle');
    } catch (err) {
      console.error('Failed to end game:', err);
    }
  };

  // Handle sending chat message during game
  const handleSendChat = useCallback(async (message: string) => {
    if (!primaryQube || !password || !gameState) return;

    try {
      const result = await invoke<{
        success: boolean;
        game_state?: any;
        qube_response?: string;
        error?: string;
      }>('add_game_chat', {
        userId,
        qubeId: primaryQube.qube_id,
        message,
        senderType: 'human',
        password,
      });

      if (result.success && result.game_state) {
        // Update game state with new chat messages (includes human message + Qube response)
        setGameState(prev => prev ? {
          ...prev,
          chat_messages: result.game_state.chat_messages || prev.chat_messages,
        } : null);
      }
    } catch (err) {
      console.error('Failed to send chat:', err);
    }
  }, [primaryQube, password, gameState, userId]);

  // Handle resign
  const handleResign = useCallback(async () => {
    if (!primaryQube || !password || !gameState) return;

    const yourColor = gameState.your_color || 'white';

    try {
      const result = await invoke<{
        success: boolean;
        game_summary?: any;
        error?: string;
      }>('resign_game', {
        userId,
        qubeId: primaryQube.qube_id,
        resigningPlayer: yourColor,
        password,
      });

      if (result.success) {
        console.log('Game resigned:', result.game_summary);
        setGameState(prev => prev ? {
          ...prev,
          status: 'completed',
        } : null);
        // Return to setup after a short delay
        setTimeout(() => {
          setGameState(null);
          setSetupState('idle');
        }, 2000);
      }
    } catch (err) {
      console.error('Failed to resign:', err);
    }
  }, [primaryQube, password, gameState, userId]);

  // Handle offering draw
  const handleOfferDraw = useCallback(async () => {
    if (!primaryQube || !password || !gameState) return;

    const yourColor = gameState.your_color || 'white';

    try {
      const result = await invoke<{
        success: boolean;
        pending_draw_offer?: any;
        error?: string;
      }>('offer_draw', {
        userId,
        qubeId: primaryQube.qube_id,
        offeringPlayer: yourColor,
        password,
      });

      if (result.success) {
        console.log('Draw offered');
        setGameState(prev => prev ? {
          ...prev,
          pending_draw_offer: result.pending_draw_offer || {
            offered_by: yourColor,
            timestamp: Date.now() / 1000,
          },
        } : null);
      }
    } catch (err) {
      console.error('Failed to offer draw:', err);
    }
  }, [primaryQube, password, gameState, userId]);

  // Handle responding to draw offer
  const handleRespondToDraw = useCallback(async (accepting: boolean) => {
    if (!primaryQube || !password || !gameState) return;

    const yourColor = gameState.your_color || 'white';

    try {
      const result = await invoke<{
        success: boolean;
        game_summary?: any;
        error?: string;
      }>('respond_to_draw', {
        userId,
        qubeId: primaryQube.qube_id,
        accepting,
        respondingPlayer: yourColor,
        password,
      });

      if (result.success) {
        if (accepting) {
          console.log('Draw accepted:', result.game_summary);
          setGameState(prev => prev ? {
            ...prev,
            status: 'completed',
            pending_draw_offer: null,
          } : null);
          // Return to setup after a short delay
          setTimeout(() => {
            setGameState(null);
            setSetupState('idle');
          }, 2000);
        } else {
          console.log('Draw declined');
          setGameState(prev => prev ? {
            ...prev,
            pending_draw_offer: null,
          } : null);
        }
      }
    } catch (err) {
      console.error('Failed to respond to draw:', err);
    }
  }, [primaryQube, password, gameState, userId]);

  // Render game selection
  if (setupState !== 'playing') {
    return (
      <div className="h-full flex flex-col items-center justify-center p-6">
        <GlassCard className="p-8 max-w-lg w-full">
          <h2 className="text-2xl font-display text-accent-primary mb-6 text-center">
            Chess Arena
          </h2>

          {selectedQubes.length === 0 ? (
            <div className="text-center">
              <p className="text-text-secondary mb-4">
                Select a Qube from the sidebar to play chess
              </p>
              <p className="text-text-tertiary text-sm">
                You can select one Qube for Human vs Qube, or two Qubes for Qube vs Qube
              </p>
            </div>
          ) : (
            <>
              {/* Selected Qubes Display */}
              <div className="mb-6">
                <h3 className="text-sm text-text-secondary mb-2">Selected Qubes:</h3>
                <div className="flex gap-2 flex-wrap">
                  {selectedQubes.map(qube => {
                    // Get avatar URL - prioritize IPFS, then local file
                    const getAvatarUrl = () => {
                      if (qube.avatar_ipfs_cid) {
                        return `https://ipfs.io/ipfs/${qube.avatar_ipfs_cid}`;
                      }
                      if (qube.avatar_local_path) {
                        return convertFileSrc(qube.avatar_local_path);
                      }
                      return null;
                    };
                    const avatarUrl = getAvatarUrl();

                    return (
                      <div
                        key={qube.qube_id}
                        className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-glass-bg border border-glass-border"
                      >
                        {avatarUrl ? (
                          <img
                            src={avatarUrl}
                            alt={qube.name}
                            className="w-6 h-6 rounded-full object-cover"
                          />
                        ) : (
                          <div
                            className="w-6 h-6 rounded-full"
                            style={{ backgroundColor: qube.favorite_color }}
                          />
                        )}
                        <span className="text-text-primary text-sm">{qube.name}</span>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Game Mode Selection */}
              <div className="mb-6">
                <h3 className="text-sm text-text-secondary mb-2">Game Mode:</h3>
                <div className="flex gap-2">
                  <button
                    onClick={() => setGameMode('human-vs-qube')}
                    className={`flex-1 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                      gameMode === 'human-vs-qube'
                        ? 'bg-accent-primary text-bg-primary'
                        : 'bg-glass-bg text-text-secondary hover:text-text-primary border border-glass-border'
                    }`}
                  >
                    Human vs Qube
                  </button>
                  <button
                    onClick={() => setGameMode('qube-vs-qube')}
                    disabled={selectedQubes.length < 2}
                    className={`flex-1 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                      gameMode === 'qube-vs-qube'
                        ? 'bg-accent-secondary text-bg-primary'
                        : selectedQubes.length < 2
                          ? 'bg-glass-bg text-text-tertiary border border-glass-border cursor-not-allowed opacity-50'
                          : 'bg-glass-bg text-text-secondary hover:text-text-primary border border-glass-border'
                    }`}
                  >
                    Qube vs Qube
                  </button>
                </div>
                {selectedQubes.length < 2 && (
                  <p className="text-text-tertiary text-xs mt-1">
                    Select 2 Qubes (Ctrl+Click) for Qube vs Qube mode
                  </p>
                )}
              </div>

              {/* Color Selection (Human vs Qube only) */}
              {gameMode === 'human-vs-qube' && (
                <div className="mb-6">
                  <h3 className="text-sm text-text-secondary mb-2">Play as:</h3>
                  <div className="flex gap-2">
                    {(['white', 'black', 'random'] as const).map(color => (
                      <button
                        key={color}
                        onClick={() => setSelectedColor(color)}
                        className={`flex-1 px-4 py-2 rounded-lg text-sm font-medium transition-all capitalize ${
                          selectedColor === color
                            ? color === 'white'
                              ? 'bg-white text-black'
                              : color === 'black'
                                ? 'bg-gray-800 text-white'
                                : 'bg-gradient-to-r from-white to-gray-800 text-gray-500'
                            : 'bg-glass-bg text-text-secondary hover:text-text-primary border border-glass-border'
                        }`}
                      >
                        {color}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Error Display */}
              {error && (
                <div className="mb-4 p-3 rounded-lg bg-accent-danger/20 border border-accent-danger text-accent-danger text-sm">
                  {error}
                </div>
              )}

              {/* Start Game Button */}
              <GlassButton
                variant="primary"
                size="lg"
                className="w-full"
                onClick={handleStartGame}
                disabled={isLoading}
              >
                {isLoading ? 'Starting...' : 'Start Game'}
              </GlassButton>
            </>
          )}
        </GlassCard>
      </div>
    );
  }

  // Render active game
  return (
    <div className="h-full flex flex-col">
      {/* Game Header */}
      <div className="flex items-center justify-between p-4 bg-bg-secondary/50 border-b border-glass-border">
        <div className="flex items-center gap-4">
          {/* White Player */}
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded-full bg-white border border-gray-300" />
            <span className="text-text-primary text-sm">
              {gameState?.white_player?.name || 'White'}
            </span>
          </div>
          <span className="text-text-tertiary">vs</span>
          {/* Black Player */}
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded-full bg-gray-800 border border-gray-600" />
            <span className="text-text-primary text-sm">
              {gameState?.black_player?.name || 'Black'}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className={`px-2 py-1 rounded text-xs ${
            gameState?.current_turn === 'white'
              ? 'bg-white text-black'
              : 'bg-gray-800 text-white'
          }`}>
            {gameState?.current_turn === 'white' ? 'White' : 'Black'} to move
          </span>

          {/* Draw Offer notification */}
          {gameState?.pending_draw_offer && gameState.pending_draw_offer.offered_by !== gameState.your_color && (
            <div className="flex items-center gap-2 px-3 py-1 rounded-lg bg-accent-secondary/20 border border-accent-secondary">
              <span className="text-accent-secondary text-xs">Draw offered!</span>
              <button
                onClick={() => handleRespondToDraw(true)}
                className="px-2 py-0.5 rounded bg-accent-success text-bg-primary text-xs hover:brightness-110"
              >
                Accept
              </button>
              <button
                onClick={() => handleRespondToDraw(false)}
                className="px-2 py-0.5 rounded bg-accent-danger text-bg-primary text-xs hover:brightness-110"
              >
                Decline
              </button>
            </div>
          )}

          {/* Game status indicator if you offered draw */}
          {gameState?.pending_draw_offer && gameState.pending_draw_offer.offered_by === gameState.your_color && (
            <span className="px-2 py-1 rounded text-xs bg-accent-secondary/20 text-accent-secondary">
              Draw offered...
            </span>
          )}

          <GlassButton
            variant="secondary"
            size="sm"
            onClick={handleOfferDraw}
            disabled={!!gameState?.pending_draw_offer || gameState?.status === 'completed'}
          >
            Offer Draw
          </GlassButton>
          <GlassButton
            variant="secondary"
            size="sm"
            onClick={handleResign}
            disabled={gameState?.status === 'completed'}
            className="text-accent-danger border-accent-danger/50 hover:bg-accent-danger/10"
          >
            Resign
          </GlassButton>
          <GlassButton
            variant="secondary"
            size="sm"
            onClick={handleAbandonGame}
          >
            Abandon
          </GlassButton>
        </div>
      </div>

      {/* Chess Board */}
      <div className="flex-1 flex items-center justify-center p-4 overflow-hidden">
        {gameState && (
          <ChessGame
            fen={gameState.fen}
            playerColor={gameState.your_color || 'white'}
            onMove={handleMove}
            onRequestQubeMove={handleRequestQubeMove}
            onSendChat={handleSendChat}
            onRematch={handleRematch}
            isQubeThinking={isLoading}
            gameMode={gameMode}
            currentTurn={gameState.current_turn}
            whitePlayer={gameState.white_player}
            blackPlayer={gameState.black_player}
            moveHistory={gameState.moves}
            chatMessages={gameState.chat_messages}
            startTime={gameState.start_time}
            permanentStats={permanentStats}
            whitePlayerStats={gameMode === 'qube-vs-qube' ? primaryStats : null}
            blackPlayerStats={gameMode === 'qube-vs-qube' ? secondaryStats : null}
          />
        )}
      </div>
    </div>
  );
};
