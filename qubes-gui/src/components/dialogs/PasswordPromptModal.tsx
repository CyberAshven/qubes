import React, { useState } from 'react';
import { GlassCard, GlassButton, GlassInput } from '../glass';

interface PasswordPromptModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (password: string) => void;
  title?: string;
  message?: string;
}

export const PasswordPromptModal: React.FC<PasswordPromptModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  title = 'Password Required',
  message = 'Please enter your password to decrypt this content',
}) => {
  const [password, setPassword] = useState('');

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (password) {
      onSubmit(password);
      setPassword('');
    }
  };

  const handleClose = () => {
    setPassword('');
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <GlassCard className="w-full max-w-md p-6 m-4">
        <h2 className="text-2xl font-display text-accent-primary mb-4">
          {title}
        </h2>
        <p className="text-text-secondary mb-6">{message}</p>

        <form onSubmit={handleSubmit}>
          <div className="mb-6">
            <label className="block text-sm font-medium text-text-secondary mb-2">
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoFocus
              className="w-full px-4 py-3 bg-glass-bg backdrop-blur-glass border border-glass-border rounded-lg text-text-primary placeholder-text-tertiary focus:outline-none focus:ring-2 focus:ring-accent-primary/50"
              placeholder="Enter password..."
            />
          </div>

          <div className="flex gap-3">
            <GlassButton
              type="button"
              variant="secondary"
              onClick={handleClose}
              className="flex-1"
            >
              Cancel
            </GlassButton>
            <GlassButton
              type="submit"
              variant="primary"
              className="flex-1"
              disabled={!password}
            >
              Decrypt
            </GlassButton>
          </div>
        </form>
      </GlassCard>
    </div>
  );
};
