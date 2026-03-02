import React from 'react';
import { GlassCard } from './glass/GlassCard';
import { GlassButton } from './glass/GlassButton';
import { open } from '@tauri-apps/plugin-shell';

export const AppImageErrorScreen: React.FC = () => {
  const handleDownload = async () => {
    try {
      await open('https://qube.cash/releases');
    } catch {
      // Fallback: copy URL to clipboard
      navigator.clipboard?.writeText('https://qube.cash/releases');
    }
  };

  return (
    <div className="h-screen w-screen flex items-center justify-center bg-bg-primary relative overflow-hidden">
      <div className="absolute inset-0 opacity-30">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-accent-danger/20 rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-accent-primary/20 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '1s' }}></div>
      </div>

      <GlassCard variant="elevated" className="w-full max-w-lg p-8 relative z-10">
        <div className="text-center mb-6">
          <h1 className="text-3xl font-display text-accent-primary mb-2">
            QUBES
          </h1>
          <h2 className="text-xl font-display text-accent-danger">
            Backend Not Included
          </h2>
        </div>

        <div className="space-y-4 text-text-secondary text-sm">
          <p>
            The AppImage build does not include the AI backend required to run Qubes.
          </p>
          <p>
            Please download the <span className="text-accent-primary font-medium">full ZIP distribution</span> from
            the Qubes website, which includes all required components (AI backend, models, etc).
          </p>
        </div>

        <div className="mt-6">
          <GlassButton
            variant="primary"
            size="lg"
            className="w-full"
            onClick={handleDownload}
          >
            Download Full Version
          </GlassButton>
        </div>

        <div className="mt-4 text-center text-text-tertiary text-xs">
          <p>qube.cash/releases</p>
        </div>
      </GlassCard>
    </div>
  );
};
