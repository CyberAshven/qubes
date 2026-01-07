import React, { useState, useMemo, useCallback, useEffect, useRef } from 'react';
import { Chessboard } from 'react-chessboard';
import { Chess, Square } from 'chess.js';
import { GamePlayer, MoveResult, MoveRecord, GameChatMessage } from '../../types';
import { GlassButton } from '../glass';
import { ChessSounds } from '../../utils/sounds';

// Define handler argument types to match react-chessboard v5
interface SquareHandlerArgs {
  piece: { pieceType: string } | null;
  square: string;
}

interface PieceDropHandlerArgs {
  piece: { isSparePiece: boolean; position: string; pieceType: string };
  sourceSquare: string;
  targetSquare: string | null;
}

interface PermanentStats {
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
}

interface ChessGameProps {
  fen: string;
  playerColor: 'white' | 'black';
  onMove: (move: string) => Promise<MoveResult>;
  onRequestQubeMove: () => Promise<void>;
  onSendChat?: (message: string) => Promise<void>;
  onRematch?: () => void;
  isQubeThinking: boolean;
  gameMode: 'human-vs-qube' | 'qube-vs-qube';
  currentTurn: 'white' | 'black';
  whitePlayer?: GamePlayer;
  blackPlayer?: GamePlayer;
  moveHistory?: MoveRecord[];
  chatMessages?: GameChatMessage[];
  startTime?: string;
  permanentStats?: PermanentStats | null;
  whitePlayerStats?: PermanentStats | null;
  blackPlayerStats?: PermanentStats | null;
}

export const ChessGame: React.FC<ChessGameProps> = ({
  fen,
  playerColor,
  onMove,
  onRequestQubeMove,
  onSendChat,
  onRematch,
  isQubeThinking,
  gameMode,
  currentTurn,
  whitePlayer,
  blackPlayer,
  moveHistory = [],
  chatMessages = [],
  startTime,
  permanentStats,
  whitePlayerStats,
  blackPlayerStats,
}) => {
  const [moveFrom, setMoveFrom] = useState<Square | null>(null);
  const [rightClickedSquares, setRightClickedSquares] = useState<Record<string, React.CSSProperties>>({});
  const [optionSquares, setOptionSquares] = useState<Record<string, React.CSSProperties>>({});
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [chatInput, setChatInput] = useState('');
  const [isSendingChat, setIsSendingChat] = useState(false);
  const chatContainerRef = React.useRef<HTMLDivElement>(null);

  // Auto-scroll chat to bottom when new messages arrive
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [chatMessages]);

  // Handle sending chat message
  const handleSendChat = async () => {
    if (!chatInput.trim() || !onSendChat || isSendingChat) return;

    setIsSendingChat(true);
    try {
      await onSendChat(chatInput.trim());
      setChatInput('');
    } catch (err) {
      console.error('Failed to send chat:', err);
    } finally {
      setIsSendingChat(false);
    }
  };

  // Handle Enter key in chat input
  const handleChatKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendChat();
    }
  };

  // Elapsed time timer - stops when game is over
  useEffect(() => {
    if (!startTime) return;

    // Check if game is over
    const tempGame = new Chess(fen);
    const gameOver = tempGame.isGameOver();

    const updateElapsed = () => {
      const start = new Date(startTime).getTime();
      const now = Date.now();
      setElapsedSeconds(Math.floor((now - start) / 1000));
    };

    updateElapsed();

    // Only run the interval if game is still in progress
    if (!gameOver) {
      const interval = setInterval(updateElapsed, 1000);
      return () => clearInterval(interval);
    }
  }, [startTime, fen]);

  // Format elapsed time as MM:SS
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Track move count for sound effects
  const prevMoveCountRef = useRef(moveHistory.length);

  // Play sound effects when moves occur
  useEffect(() => {
    const currentMoveCount = moveHistory.length;

    // Only play sound if a new move was added (not on initial render or going backwards)
    if (currentMoveCount > prevMoveCountRef.current && currentMoveCount > 0) {
      const lastMove = moveHistory[currentMoveCount - 1];
      const san = lastMove?.san || '';

      // Check if this move results in checkmate, check, or capture
      const tempGame = new Chess(fen);
      const isCheckmate = tempGame.isCheckmate();
      const isCheck = tempGame.isCheck() && !isCheckmate;
      const isDraw = tempGame.isDraw();

      // Capture is indicated by 'x' in SAN notation
      const isCapture = san.includes('x');

      ChessSounds.playMoveSound(isCapture, isCheck, isCheckmate, isDraw);
    }

    prevMoveCountRef.current = currentMoveCount;
  }, [moveHistory, fen]);

  // Create chess instance from FEN
  const game = useMemo(() => {
    const chess = new Chess();
    try {
      chess.load(fen);
    } catch (e) {
      console.error('Invalid FEN:', fen);
    }
    return chess;
  }, [fen]);

  // Calculate material advantage
  const materialAdvantage = useMemo(() => {
    const pieceValues: Record<string, number> = { p: 1, n: 3, b: 3, r: 5, q: 9 };
    let whiteMaterial = 0;
    let blackMaterial = 0;

    const board = game.board();
    for (const row of board) {
      for (const square of row) {
        if (square && square.type !== 'k') {
          const value = pieceValues[square.type] || 0;
          if (square.color === 'w') {
            whiteMaterial += value;
          } else {
            blackMaterial += value;
          }
        }
      }
    }

    const diff = whiteMaterial - blackMaterial;
    if (diff === 0) return { text: 'Equal', color: 'text-text-secondary' };
    if (diff > 0) return { text: `White +${diff}`, color: 'text-white' };
    return { text: `Black +${Math.abs(diff)}`, color: 'text-gray-400' };
  }, [game]);

  // Calculate captured pieces by comparing to starting position
  const capturedPieces = useMemo(() => {
    const startingPieces = {
      white: { p: 8, n: 2, b: 2, r: 2, q: 1 },
      black: { p: 8, n: 2, b: 2, r: 2, q: 1 }
    };

    const currentPieces = {
      white: { p: 0, n: 0, b: 0, r: 0, q: 0 },
      black: { p: 0, n: 0, b: 0, r: 0, q: 0 }
    };

    const board = game.board();
    for (const row of board) {
      for (const square of row) {
        if (square && square.type !== 'k') {
          const color = square.color === 'w' ? 'white' : 'black';
          const piece = square.type as 'p' | 'n' | 'b' | 'r' | 'q';
          currentPieces[color][piece]++;
        }
      }
    }

    const captured = {
      byWhite: [] as string[],
      byBlack: [] as string[]
    };

    const pieceSymbols: Record<string, { white: string; black: string }> = {
      p: { white: '♙', black: '♟' },
      n: { white: '♘', black: '♞' },
      b: { white: '♗', black: '♝' },
      r: { white: '♖', black: '♜' },
      q: { white: '♕', black: '♛' }
    };

    for (const piece of ['q', 'r', 'b', 'n', 'p'] as const) {
      const whiteMissing = startingPieces.white[piece] - currentPieces.white[piece];
      const blackMissing = startingPieces.black[piece] - currentPieces.black[piece];

      for (let i = 0; i < whiteMissing; i++) {
        captured.byBlack.push(pieceSymbols[piece].white);
      }
      for (let i = 0; i < blackMissing; i++) {
        captured.byWhite.push(pieceSymbols[piece].black);
      }
    }

    return captured;
  }, [game]);

  // Group moves into pairs for display (1. e4 e5, 2. Nf3 Nc6, etc.)
  const movePairs = useMemo(() => {
    const pairs: { moveNum: number; white?: MoveRecord; black?: MoveRecord }[] = [];

    for (const move of moveHistory) {
      const moveNum = Math.ceil(move.move_number / 2);
      let pair = pairs.find(p => p.moveNum === moveNum);

      if (!pair) {
        pair = { moveNum };
        pairs.push(pair);
      }

      if (move.player === 'white') {
        pair.white = move;
      } else {
        pair.black = move;
      }
    }

    return pairs;
  }, [moveHistory]);

  const isHumanTurn = gameMode === 'human-vs-qube' && currentTurn === playerColor;
  const canInteract = gameMode === 'human-vs-qube' ? isHumanTurn : false;

  const getMoveOptions = useCallback((square: Square) => {
    const moves = game.moves({ square, verbose: true });

    if (moves.length === 0) {
      setOptionSquares({});
      return false;
    }

    const newSquares: Record<string, React.CSSProperties> = {};
    moves.forEach((move) => {
      newSquares[move.to] = {
        background:
          game.get(move.to as Square) &&
          game.get(move.to as Square)?.color !== game.get(square)?.color
            ? 'radial-gradient(circle, rgba(255,0,0,.4) 85%, transparent 85%)'
            : 'radial-gradient(circle, rgba(0,255,136,.3) 25%, transparent 25%)',
      };
    });
    newSquares[square] = { background: 'rgba(0, 255, 136, 0.4)' };
    setOptionSquares(newSquares);
    return true;
  }, [game]);

  const handleSquareClick = useCallback(({ square }: SquareHandlerArgs) => {
    if (!canInteract) return;

    const sq = square as Square;
    setRightClickedSquares({});

    if (moveFrom) {
      const moves = game.moves({ square: moveFrom, verbose: true });
      const foundMove = moves.find((m) => m.from === moveFrom && m.to === sq);

      if (!foundMove) {
        const piece = game.get(sq);
        if (piece && piece.color === (playerColor === 'white' ? 'w' : 'b')) {
          setMoveFrom(sq);
          getMoveOptions(sq);
          return;
        }
        setMoveFrom(null);
        setOptionSquares({});
        return;
      }

      let promotionPiece = '';
      if (
        (foundMove.color === 'w' && foundMove.piece === 'p' && sq[1] === '8') ||
        (foundMove.color === 'b' && foundMove.piece === 'p' && sq[1] === '1')
      ) {
        promotionPiece = 'q';
      }

      const moveString = `${moveFrom}${sq}${promotionPiece}`;
      onMove(moveString).then((result) => {
        if (!result.success) console.error('Move failed:', result.error);
      });

      setMoveFrom(null);
      setOptionSquares({});
      return;
    }

    const piece = game.get(sq);
    if (piece && piece.color === (playerColor === 'white' ? 'w' : 'b')) {
      setMoveFrom(sq);
      getMoveOptions(sq);
    }
  }, [moveFrom, game, canInteract, playerColor, onMove, getMoveOptions]);

  const handleSquareRightClick = useCallback(({ square }: SquareHandlerArgs) => {
    const colour: React.CSSProperties = { backgroundColor: 'rgba(255, 0, 0, 0.4)' };
    setRightClickedSquares((prev) => ({
      ...prev,
      [square]: prev[square]?.backgroundColor === colour.backgroundColor ? {} : colour,
    }));
  }, []);

  const handlePieceDrop = useCallback(
    ({ sourceSquare, targetSquare }: PieceDropHandlerArgs): boolean => {
      if (!canInteract || !targetSquare) return false;

      const source = sourceSquare as Square;
      const target = targetSquare as Square;

      const moves = game.moves({ square: source, verbose: true });
      const foundMove = moves.find((m) => m.from === source && m.to === target);

      if (!foundMove) return false;

      let promotionPiece = '';
      if (
        (foundMove.color === 'w' && foundMove.piece === 'p' && target[1] === '8') ||
        (foundMove.color === 'b' && foundMove.piece === 'p' && target[1] === '1')
      ) {
        promotionPiece = 'q';
      }

      const moveString = `${source}${target}${promotionPiece}`;
      onMove(moveString).then((result) => {
        if (!result.success) console.error('Move failed:', result.error);
      });

      setOptionSquares({});
      setMoveFrom(null);
      return true;
    },
    [game, canInteract, onMove]
  );

  // Calculate last move squares for highlighting
  const lastMoveSquares = useMemo(() => {
    if (moveHistory.length === 0) return {};
    const lastMove = moveHistory[moveHistory.length - 1];
    if (!lastMove?.uci || lastMove.uci.length < 4) return {};

    const from = lastMove.uci.slice(0, 2);
    const to = lastMove.uci.slice(2, 4);

    return {
      [from]: { backgroundColor: 'rgba(255, 255, 0, 0.4)' },
      [to]: { backgroundColor: 'rgba(255, 255, 0, 0.5)' },
    };
  }, [moveHistory]);

  const customSquareStyles = useMemo(() => ({
    ...lastMoveSquares,
    ...optionSquares,
    ...rightClickedSquares,
  }), [lastMoveSquares, optionSquares, rightClickedSquares]);

  const isCheck = game.isCheck();
  const isCheckmate = game.isCheckmate();
  const isStalemate = game.isStalemate();
  const isDraw = game.isDraw();
  const isGameOver = game.isGameOver();

  const allowDrag = canInteract && !isGameOver;

  const chessboardOptions = {
    position: fen,
    boardOrientation: gameMode === 'human-vs-qube' ? playerColor : 'white',
    squareStyles: customSquareStyles,
    allowDragging: allowDrag,
    onSquareClick: handleSquareClick,
    onSquareRightClick: handleSquareRightClick,
    onPieceDrop: handlePieceDrop,
    showBoardNotation: true,
    boardStyle: {
      borderRadius: '8px',
      boxShadow: '0 4px 12px rgba(0, 0, 0, 0.4)',
    },
    darkSquareStyle: { backgroundColor: '#1a3a2a' },
    lightSquareStyle: { backgroundColor: '#2d5a42' },
  };

  return (
    <div className="flex justify-center gap-6 w-full h-full">
      {/* Left Column - Move History */}
      <div className="w-72 flex flex-col">
        <div className="text-sm text-text-secondary mb-2 font-medium">Move History</div>
        <div className="flex-1 p-4 rounded-lg bg-glass-bg border border-glass-border overflow-y-auto max-h-[520px]">
          {movePairs.length === 0 ? (
            <span className="text-text-tertiary italic text-sm">No moves yet</span>
          ) : (
            <div className="space-y-1.5">
              {movePairs.map((pair, i) => (
                <div
                  key={pair.moveNum}
                  className={`flex items-center gap-3 text-base py-1.5 px-3 rounded ${
                    i === movePairs.length - 1 ? 'bg-accent-primary/10' : ''
                  }`}
                >
                  <span className="text-text-tertiary w-8 font-mono">{pair.moveNum}.</span>
                  <span className="text-text-primary w-16 font-medium">
                    {pair.white?.san || '...'}
                  </span>
                  <span className="text-text-secondary w-16">
                    {pair.black?.san || ''}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Center Column - Chess Board */}
      <div className="flex flex-col items-center w-[580px]">
        {/* Game Status */}
        {isGameOver && (
          <div className="flex items-center gap-4 mb-2">
            <div className={`px-4 py-2 rounded-lg font-bold text-lg ${
              isCheckmate
                ? 'bg-accent-success/20 text-accent-success'
                : 'bg-accent-warning/20 text-accent-warning'
            }`}>
              {isCheckmate ? (
                `Checkmate! ${game.turn() === 'w' ? 'Black' : 'White'} wins!`
              ) : isStalemate ? (
                'Stalemate! Draw.'
              ) : isDraw ? (
                'Draw!'
              ) : (
                'Game Over'
              )}
            </div>
            {onRematch && (
              <GlassButton
                variant="primary"
                size="sm"
                onClick={onRematch}
              >
                Rematch
              </GlassButton>
            )}
          </div>
        )}

        {isCheck && !isCheckmate && (
          <div className="px-4 py-2 rounded-lg bg-accent-danger/20 text-accent-danger font-bold mb-2">
            Check!
          </div>
        )}

        {/* Top Player (opponent) */}
        <div className="w-full flex items-center justify-between mb-2 px-1">
          <div className="flex items-center gap-2">
            <div className={`w-3 h-3 rounded-full ${
              (playerColor === 'white' ? 'black' : 'white') === currentTurn
                ? 'bg-accent-success animate-pulse'
                : 'bg-gray-600'
            }`} />
            <span className="text-text-primary font-medium">
              {playerColor === 'white' ? blackPlayer?.name || 'Black' : whitePlayer?.name || 'White'}
            </span>
            <span className="text-xs text-text-tertiary">
              {gameMode === 'qube-vs-qube'
                ? '(Qube)'
                : playerColor === 'white' ? '(Qube)' : '(You)'}
            </span>
          </div>
          <div className="flex items-center gap-0.5 text-lg">
            {(playerColor === 'white' ? capturedPieces.byBlack : capturedPieces.byWhite).map((piece, i) => (
              <span key={i} className="opacity-80">{piece}</span>
            ))}
          </div>
        </div>

        {/* Chessboard - fixed size container to maintain square aspect */}
        <div className="w-full aspect-square">
          {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
          <Chessboard options={chessboardOptions as any} />
        </div>

        {/* Bottom Player */}
        <div className="w-full flex items-center justify-between mt-2 px-1">
          <div className="flex items-center gap-2">
            <div className={`w-3 h-3 rounded-full ${
              playerColor === currentTurn
                ? 'bg-accent-success animate-pulse'
                : 'bg-gray-600'
            }`} />
            <span className="text-text-primary font-medium">
              {playerColor === 'white' ? whitePlayer?.name || 'White' : blackPlayer?.name || 'Black'}
            </span>
            <span className="text-xs text-text-tertiary">
              {gameMode === 'qube-vs-qube'
                ? '(Qube)'
                : playerColor === 'white' ? '(You)' : '(Qube)'}
            </span>
          </div>
          <div className="flex items-center gap-0.5 text-lg">
            {(playerColor === 'white' ? capturedPieces.byWhite : capturedPieces.byBlack).map((piece, i) => (
              <span key={i} className="opacity-80">{piece}</span>
            ))}
          </div>
        </div>

        {/* Turn Indicator & Controls */}
        <div className="mt-4 flex items-center gap-4">
          {gameMode === 'human-vs-qube' && !isGameOver && (
            <>
              {!isHumanTurn ? (
                <GlassButton
                  variant="primary"
                  onClick={onRequestQubeMove}
                  disabled={isQubeThinking}
                >
                  {isQubeThinking ? (
                    <span className="flex items-center gap-2">
                      <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                      </svg>
                      Thinking...
                    </span>
                  ) : (
                    "Request Move"
                  )}
                </GlassButton>
              ) : (
                <span className="text-accent-primary font-medium">Your turn!</span>
              )}
            </>
          )}

          {gameMode === 'qube-vs-qube' && !isGameOver && (
            <GlassButton
              variant="primary"
              onClick={onRequestQubeMove}
              disabled={isQubeThinking}
            >
              {isQubeThinking ? (
                <span className="flex items-center gap-2">
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  {currentTurn === 'white' ? whitePlayer?.name : blackPlayer?.name} thinking...
                </span>
              ) : (
                `${currentTurn === 'white' ? whitePlayer?.name : blackPlayer?.name}'s Move`
              )}
            </GlassButton>
          )}
        </div>
      </div>

      {/* Right Column - Stats & Chat */}
      <div className="w-80 flex flex-col gap-4">
        {/* Game Stats */}
        <div>
          <div className="text-sm text-text-secondary mb-2 font-medium">Game Stats</div>
          <div className="p-4 rounded-lg bg-glass-bg border border-glass-border">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <div className="text-xs text-text-tertiary">Time</div>
                <div className="text-lg text-text-primary font-mono">{formatTime(elapsedSeconds)}</div>
              </div>
              <div>
                <div className="text-xs text-text-tertiary">Moves</div>
                <div className="text-lg text-text-primary font-mono">{moveHistory.length}</div>
              </div>
              <div className="col-span-2">
                <div className="text-xs text-text-tertiary">Material</div>
                <div className={`text-lg font-medium ${materialAdvantage.color}`}>
                  {materialAdvantage.text}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Player Stats */}
        {(permanentStats || (gameMode === 'qube-vs-qube' && (whitePlayerStats || blackPlayerStats))) && (
          <div>
            <div className="text-sm text-text-secondary mb-2 font-medium">
              {gameMode === 'qube-vs-qube' ? 'Player Stats' : 'Record'}
            </div>

            {/* Qube vs Qube Mode - Show both players */}
            {gameMode === 'qube-vs-qube' ? (
              <div className="space-y-3">
                {/* White Player Stats */}
                <div className="p-3 rounded-lg bg-glass-bg border border-glass-border">
                  <div className="flex items-center gap-2 mb-2 pb-2 border-b border-glass-border">
                    <div className="w-3 h-3 rounded-full bg-white"></div>
                    <span className="text-sm font-medium text-text-primary">{whitePlayer?.name || 'White'}</span>
                    <span className="ml-auto text-lg font-bold text-accent-primary">{whitePlayerStats?.elo ?? 1200}</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-green-400">{whitePlayerStats?.wins ?? 0}W</span>
                    <span className="text-red-400">{whitePlayerStats?.losses ?? 0}L</span>
                    <span className="text-gray-400">{whitePlayerStats?.draws ?? 0}D</span>
                    {(whitePlayerStats?.checkmate_wins ?? 0) > 0 && (
                      <span className="text-text-tertiary">♔{whitePlayerStats?.checkmate_wins}</span>
                    )}
                  </div>
                </div>

                {/* Black Player Stats */}
                <div className="p-3 rounded-lg bg-glass-bg border border-glass-border">
                  <div className="flex items-center gap-2 mb-2 pb-2 border-b border-glass-border">
                    <div className="w-3 h-3 rounded-full bg-gray-600"></div>
                    <span className="text-sm font-medium text-text-primary">{blackPlayer?.name || 'Black'}</span>
                    <span className="ml-auto text-lg font-bold text-accent-secondary">{blackPlayerStats?.elo ?? 1200}</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-green-400">{blackPlayerStats?.wins ?? 0}W</span>
                    <span className="text-red-400">{blackPlayerStats?.losses ?? 0}L</span>
                    <span className="text-gray-400">{blackPlayerStats?.draws ?? 0}D</span>
                    {(blackPlayerStats?.checkmate_wins ?? 0) > 0 && (
                      <span className="text-text-tertiary">♔{blackPlayerStats?.checkmate_wins}</span>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              /* Human vs Qube Mode - Single player stats */
              permanentStats && (
                <div className="p-3 rounded-lg bg-glass-bg border border-glass-border">
                  {/* Elo Rating - prominently displayed */}
                  <div className="text-center mb-3 pb-2 border-b border-glass-border">
                    <div className="text-2xl font-bold text-accent-primary">{permanentStats.elo ?? 1200}</div>
                    <div className="text-xs text-text-tertiary">Elo Rating</div>
                  </div>
                  {(permanentStats.total_games ?? 0) > 0 && (
                    <>
                      <div className="flex justify-center gap-6 mb-2">
                        <div className="text-center">
                          <div className="text-lg font-bold text-green-400">{permanentStats.wins ?? 0}</div>
                          <div className="text-xs text-text-tertiary">Wins</div>
                        </div>
                        <div className="text-center">
                          <div className="text-lg font-bold text-red-400">{permanentStats.losses ?? 0}</div>
                          <div className="text-xs text-text-tertiary">Losses</div>
                        </div>
                        <div className="text-center">
                          <div className="text-lg font-bold text-gray-400">{permanentStats.draws ?? 0}</div>
                          <div className="text-xs text-text-tertiary">Draws</div>
                        </div>
                      </div>
                      {((permanentStats.checkmate_wins ?? 0) > 0 || (permanentStats.total_xp_earned ?? 0) > 0) && (
                        <div className="text-xs text-text-tertiary text-center border-t border-glass-border pt-2 mt-2">
                          {(permanentStats.checkmate_wins ?? 0) > 0 && (
                            <span className="mr-3">♔ {permanentStats.checkmate_wins} checkmates</span>
                          )}
                          {(permanentStats.total_xp_earned ?? 0) > 0 && (
                            <span>⭐ {permanentStats.total_xp_earned} XP</span>
                          )}
                        </div>
                      )}
                    </>
                  )}
                </div>
              )
            )}
          </div>
        )}

        {/* Game Chat */}
        <div className="flex-1 flex flex-col">
          <div className="text-sm text-text-secondary mb-2 font-medium">Game Chat</div>
          <div
            ref={chatContainerRef}
            className="flex-1 p-4 rounded-lg bg-glass-bg border border-glass-border overflow-y-auto max-h-[320px]"
          >
            {chatMessages.length === 0 ? (
              <span className="text-text-tertiary italic text-sm">No messages yet</span>
            ) : (
              <div className="space-y-3">
                {chatMessages.map((msg, i) => {
                  // Determine sender name based on sender_id for correct Qube attribution
                  let senderName = 'Qube';
                  if (msg.sender_type === 'human') {
                    senderName = 'You';
                  } else if (msg.sender_id) {
                    // Match sender_id to player to get correct name
                    if (whitePlayer?.id === msg.sender_id) {
                      senderName = whitePlayer.name || 'White';
                    } else if (blackPlayer?.id === msg.sender_id) {
                      senderName = blackPlayer.name || 'Black';
                    } else {
                      // Fallback: use any available name
                      senderName = blackPlayer?.name || whitePlayer?.name || 'Qube';
                    }
                  } else {
                    // Legacy fallback when sender_id is not available
                    senderName = blackPlayer?.name || 'Qube';
                  }

                  return (
                  <div key={i}>
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className={`text-xs font-medium ${
                        msg.sender_type === 'human' ? 'text-accent-primary' : 'text-accent-secondary'
                      }`}>
                        {senderName}
                      </span>
                      {msg.move_number && (
                        <span className="text-xs text-text-tertiary">
                          (move {msg.move_number})
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-text-primary leading-relaxed">{msg.message}</p>
                  </div>
                  );
                })}
              </div>
            )}
          </div>
          {/* Chat Input */}
          {gameMode === 'human-vs-qube' && onSendChat && (
            <div className="mt-2 flex gap-2">
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyDown={handleChatKeyDown}
                placeholder="Trash talk..."
                disabled={isSendingChat}
                className="flex-1 px-3 py-2 text-sm rounded-lg bg-glass-bg border border-glass-border text-text-primary placeholder-text-tertiary focus:outline-none focus:border-accent-primary"
              />
              <button
                onClick={handleSendChat}
                disabled={!chatInput.trim() || isSendingChat}
                className="px-3 py-2 rounded-lg bg-accent-primary/20 text-accent-primary text-sm font-medium hover:bg-accent-primary/30 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isSendingChat ? '...' : 'Send'}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
