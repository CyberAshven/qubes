import { useState } from 'react';
import { invoke } from '@tauri-apps/api/core';

interface ExitConfirmDialogProps {
  userId: string;
  password: string;
  qubes: Array<{ qube_id: string; name: string }>;
  onComplete: () => void;
  onCancel: () => void;
}

export function ExitConfirmDialog({ userId, password, qubes, onComplete, onCancel }: ExitConfirmDialogProps) {
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleAnchor = async () => {
    try {
      setProcessing(true);
      setError(null);

      console.log('Anchoring sessions for', qubes.length, 'qubes...');

      // Anchor sessions for all qubes
      for (const qube of qubes) {
        console.log('Anchoring session for qube:', qube.qube_id);
        await invoke('anchor_session', {
          userId,
          qubeId: qube.qube_id,
          password
        });
      }

      console.log('All sessions anchored, calling onComplete');
      onComplete();
    } catch (err) {
      console.error('Failed to anchor sessions:', err);
      setError(String(err));
      setProcessing(false);
    }
  };

  const handleDiscard = async () => {
    try {
      setProcessing(true);
      setError(null);

      console.log('Discarding sessions for', qubes.length, 'qubes...');

      // Discard sessions for all qubes
      for (const qube of qubes) {
        console.log('Discarding session for qube:', qube.qube_id);
        await invoke('discard_session', {
          userId,
          qubeId: qube.qube_id,
          password
        });
      }

      console.log('All sessions discarded, calling onComplete');
      onComplete();
    } catch (err) {
      console.error('Failed to discard sessions:', err);
      setError(String(err));
      setProcessing(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
      <div className="bg-bg-secondary border border-glass-border rounded-lg shadow-2xl max-w-md w-full mx-4 p-6">
        <h2 className="text-xl font-display text-accent-primary mb-4">
          Save Your Conversation?
        </h2>

        <p className="text-text-secondary mb-6">
          You have active session blocks. Would you like to save them to permanent memory or discard them?
        </p>

        <div className="space-y-3 mb-6">
          <div className="bg-bg-tertiary border border-glass-border rounded p-3">
            <h3 className="text-sm font-semibold text-accent-success mb-1">
              💾 Anchor (Save)
            </h3>
            <p className="text-xs text-text-tertiary">
              Saves session blocks to permanent memory. Your conversation history will be encrypted and stored on the blockchain.
            </p>
          </div>

          <div className="bg-bg-tertiary border border-glass-border rounded p-3">
            <h3 className="text-sm font-semibold text-accent-danger mb-1">
              🗑️ Discard
            </h3>
            <p className="text-xs text-text-tertiary">
              Deletes all session blocks. Your conversation will be lost permanently.
            </p>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-accent-danger/10 border border-accent-danger/30 rounded text-sm text-accent-danger">
            {error}
          </div>
        )}

        <div className="flex gap-3">
          <button
            onClick={handleAnchor}
            disabled={processing}
            className="flex-1 px-4 py-2 bg-accent-success text-bg-primary rounded font-medium hover:bg-accent-success/80 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {processing ? 'Saving...' : 'Anchor'}
          </button>

          <button
            onClick={handleDiscard}
            disabled={processing}
            className="flex-1 px-4 py-2 bg-accent-danger text-bg-primary rounded font-medium hover:bg-accent-danger/80 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {processing ? 'Discarding...' : 'Discard'}
          </button>

          <button
            onClick={onCancel}
            disabled={processing}
            className="px-4 py-2 bg-bg-quaternary text-text-secondary rounded font-medium hover:bg-bg-quaternary/80 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
