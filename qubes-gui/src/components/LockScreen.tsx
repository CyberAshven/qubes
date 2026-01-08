import { useState, useEffect, useRef } from 'react';
import { useAuth } from '../hooks/useAuth';
import { GlassCard, GlassButton } from './glass';

export const LockScreen: React.FC = () => {
  const { isLocked, unlock, logout, userId } = useAuth();
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [shake, setShake] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  // Focus input when lock screen appears
  useEffect(() => {
    if (isLocked && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isLocked]);

  // Clear password when lock screen appears
  useEffect(() => {
    if (isLocked) {
      setPassword('');
      setError(null);
    }
  }, [isLocked]);

  const handleUnlock = (e: React.FormEvent) => {
    e.preventDefault();

    if (!password.trim()) {
      setError('Please enter your password');
      return;
    }

    const success = unlock(password);
    if (success) {
      setPassword('');
      setError(null);
    } else {
      setError('Incorrect password');
      setShake(true);
      setTimeout(() => setShake(false), 500);
      setPassword('');
    }
  };

  const handleLogout = () => {
    logout();
  };

  if (!isLocked) return null;

  return (
    <div className="fixed inset-0 z-[100] bg-bg-primary/95 backdrop-blur-xl flex items-center justify-center">
      {/* Background decoration */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-accent-primary/10 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-accent-secondary/10 rounded-full blur-3xl" />
      </div>

      <GlassCard className={`p-8 max-w-md w-full mx-4 relative ${shake ? 'animate-shake' : ''}`}>
        {/* Lock icon */}
        <div className="flex justify-center mb-6">
          <div className="w-20 h-20 rounded-full bg-accent-primary/20 flex items-center justify-center">
            <span className="text-4xl">🔒</span>
          </div>
        </div>

        {/* Title */}
        <h1 className="text-2xl font-display text-text-primary text-center mb-2">
          Session Locked
        </h1>
        <p className="text-text-tertiary text-center mb-6 text-sm">
          Welcome back, <span className="text-accent-primary font-medium">{userId}</span>
        </p>

        {/* Unlock form */}
        <form onSubmit={handleUnlock} className="space-y-4">
          <div>
            <label className="text-sm text-text-secondary block mb-2">
              Enter your password to unlock
            </label>
            <input
              ref={inputRef}
              type="password"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                setError(null);
              }}
              placeholder="Master password"
              className="w-full bg-bg-primary border border-glass-border rounded-lg px-4 py-3 text-text-primary placeholder:text-text-disabled focus:outline-none focus:border-accent-primary transition-colors"
              autoFocus
            />
            {error && (
              <p className="text-accent-danger text-sm mt-2">{error}</p>
            )}
          </div>

          <GlassButton
            type="submit"
            className="w-full py-3"
          >
            🔓 Unlock
          </GlassButton>
        </form>

        {/* Logout option */}
        <div className="mt-6 pt-4 border-t border-glass-border text-center">
          <button
            onClick={handleLogout}
            className="text-sm text-text-tertiary hover:text-accent-danger transition-colors"
          >
            Not {userId}? Sign out
          </button>
        </div>
      </GlassCard>

      {/* Custom shake animation */}
      <style>{`
        @keyframes shake {
          0%, 100% { transform: translateX(0); }
          10%, 30%, 50%, 70%, 90% { transform: translateX(-8px); }
          20%, 40%, 60%, 80% { transform: translateX(8px); }
        }
        .animate-shake {
          animation: shake 0.5s ease-in-out;
        }
      `}</style>
    </div>
  );
};

export default LockScreen;
