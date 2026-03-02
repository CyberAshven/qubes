import React, { useState } from 'react';
import { GlassCard } from '../glass/GlassCard';
import { GlassInput } from '../glass/GlassInput';
import { GlassButton } from '../glass/GlassButton';

interface LoginScreenProps {
  onLogin: (username: string, password: string) => Promise<void>;
  onCreateAccount: () => void;
  onResetAccount?: (username: string) => void;
  error?: string | null;
}

export const LoginScreen: React.FC<LoginScreenProps> = ({ onLogin, onCreateAccount, onResetAccount, error }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) return;

    setIsLoading(true);
    try {
      await onLogin(username.trim(), password);
    } catch (err) {
      // Error handled by parent
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="h-screen w-screen flex items-center justify-center bg-bg-primary relative overflow-hidden">
      {/* Animated background */}
      <div className="absolute inset-0 opacity-30">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-accent-primary/20 rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-accent-secondary/20 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '1s' }}></div>
      </div>

      {/* Login card */}
      <GlassCard variant="elevated" className="w-full max-w-md p-8 relative z-10">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-display text-accent-primary mb-2">
            QUBES
          </h1>
          <p className="text-text-secondary">
            Sign in to your account
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <GlassInput
            label="Username"
            type="text"
            placeholder="Enter your username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            disabled={isLoading}
            autoFocus
          />

          <GlassInput
            label="Master Password"
            type="password"
            placeholder="Enter your master password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={isLoading}
          />

          {error && (
            <div className="p-4 bg-accent-danger/10 border border-accent-danger/30 rounded-lg">
              <p className="text-accent-danger text-sm">
                {error.includes('ACCOUNT_CORRUPTED')
                  ? 'This account appears incomplete or corrupted.'
                  : error}
              </p>
              {error.includes('ACCOUNT_CORRUPTED') && onResetAccount && username.trim() && (
                <button
                  onClick={() => onResetAccount(username.trim())}
                  className="mt-3 px-4 py-1.5 rounded bg-accent-danger/20 text-accent-danger hover:bg-accent-danger/30 transition-colors text-xs font-medium"
                >
                  Reset Account &amp; Start Over
                </button>
              )}
            </div>
          )}

          <GlassButton
            type="submit"
            variant="primary"
            size="lg"
            className="w-full"
            disabled={!username.trim() || !password.trim() || isLoading}
            loading={isLoading}
          >
            Sign In
          </GlassButton>
        </form>

        <div className="mt-6 text-center text-text-tertiary text-sm">
          <p>Secured with end-to-end encryption</p>
        </div>

        <div className="mt-4 text-center">
          <button
            onClick={onCreateAccount}
            className="text-accent-primary hover:text-accent-primary/80 text-sm font-medium transition-colors"
          >
            Create New Account
          </button>
        </div>
      </GlassCard>
    </div>
  );
};
