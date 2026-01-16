import React, { useState, useEffect } from 'react';
import { convertFileSrc } from '@tauri-apps/api/core';
import { GlassCard } from '../glass/GlassCard';
import { Qube } from '../../types';
import { formatModelName } from '../../utils/modelFormatter';

interface ChatHeaderProps {
  qube: Qube;
  userId: string;
  currentModel: string | null;
}

/**
 * Isolated header component that manages its own model display state.
 * This prevents model updates from causing the entire ChatInterface to re-render,
 * which would break the typewriter effect.
 */
export const ChatHeader: React.FC<ChatHeaderProps> = ({ qube, userId, currentModel }) => {
  // Local state for displayed model - updates independently of parent
  const [displayedModel, setDisplayedModel] = useState(qube.ai_model);

  // Update displayed model when currentModel prop changes (from API response)
  useEffect(() => {
    if (currentModel && currentModel !== displayedModel) {
      setDisplayedModel(currentModel);
    }
  }, [currentModel]);

  // Also sync with qube.ai_model if it changes externally (e.g., Dashboard)
  useEffect(() => {
    if (qube.ai_model !== displayedModel && !currentModel) {
      setDisplayedModel(qube.ai_model);
    }
  }, [qube.ai_model]);

  // Construct avatar path
  const getAvatarPath = (): string => {
    if (qube.avatar_url) return qube.avatar_url;
    if (qube.avatar_local_path) return convertFileSrc(qube.avatar_local_path);
    const projectRoot = 'C:/Users/bit_f/Projects/Qubes';
    const filePath = `${projectRoot}/data/users/${userId}/qubes/${qube.name}_${qube.qube_id}/chain/${qube.qube_id}_avatar.png`;
    return convertFileSrc(filePath);
  };

  return (
    <GlassCard
      className="sticky top-0 z-10 p-6 border-l-4 bg-bg-primary/95 backdrop-blur-sm"
      style={{ borderLeftColor: qube.favorite_color }}
    >
      <div
        className="grid items-center gap-4"
        style={{ gridTemplateColumns: '200px 180px 110px 100px 110px 140px 130px' }}
      >
        {/* Avatar + Name */}
        <div className="flex items-center gap-3">
          <img
            src={getAvatarPath()}
            alt={`${qube.name} avatar`}
            className="w-16 h-16 rounded-xl object-cover shadow-lg transition-transform hover:scale-105 flex-shrink-0"
            style={{
              border: `2px solid ${qube.favorite_color}`,
              boxShadow: `0 0 15px ${qube.favorite_color}40`
            }}
            onError={(e) => {
              const target = e.target as HTMLImageElement;
              target.style.display = 'none';
              const fallback = target.nextElementSibling as HTMLElement;
              if (fallback) fallback.style.display = 'flex';
            }}
          />
          <div
            className="w-16 h-16 rounded-xl flex items-center justify-center text-2xl font-display font-bold shadow-lg transition-transform hover:scale-105 flex-shrink-0"
            style={{
              background: `linear-gradient(135deg, ${qube.favorite_color}40, ${qube.favorite_color}20)`,
              color: qube.favorite_color,
              border: `2px solid ${qube.favorite_color}`,
              boxShadow: `0 0 15px ${qube.favorite_color}40`,
              display: 'none',
            }}
          >
            {qube.name[0]}
          </div>
          <div className="flex flex-col min-w-0">
            <div className="text-xs text-text-tertiary uppercase tracking-wider font-semibold">Name</div>
            <h1 className="text-xl font-display font-bold truncate" style={{ color: qube.favorite_color }}>
              {qube.name}
            </h1>
          </div>
        </div>

        {/* Model - Uses local state, updates independently */}
        <div className="flex flex-col min-w-0">
          <div className="text-xs text-text-tertiary uppercase tracking-wider font-semibold">Model</div>
          <div className="text-xl font-display font-bold flex items-center gap-2 truncate" style={{ color: qube.favorite_color }}>
            🤖 <span className="truncate">{formatModelName(displayedModel)}</span>
          </div>
        </div>

        {/* ID */}
        <div className="flex flex-col">
          <div className="text-xs text-text-tertiary uppercase tracking-wider font-semibold">Qube ID</div>
          <div className="text-xl font-display font-bold flex items-center gap-2" style={{ color: qube.favorite_color }}>
            🆔 {qube.qube_id.substring(0, 8)}
          </div>
        </div>

        {/* Voice */}
        <div className="flex flex-col min-w-0">
          <div className="text-xs text-text-tertiary uppercase tracking-wider font-semibold">Voice</div>
          <div className="text-xl font-display font-bold flex items-center gap-2 truncate" style={{ color: qube.favorite_color }}>
            🎤 <span className="truncate">{(() => {
              const voiceName = qube.voice_model?.split(':')[1] || qube.voice_model || 'Not set';
              return voiceName.charAt(0).toUpperCase() + voiceName.slice(1);
            })()}</span>
          </div>
        </div>

        {/* Creator */}
        <div className="flex flex-col min-w-0">
          <div className="text-xs text-text-tertiary uppercase tracking-wider font-semibold">Creator</div>
          <div className="text-xl font-display font-bold flex items-center gap-2 truncate" style={{ color: qube.favorite_color }}>
            👤 <span className="truncate">{qube.creator || 'Unknown'}</span>
          </div>
        </div>

        {/* Blockchain */}
        <div className="flex flex-col min-w-0">
          <div className="text-xs text-text-tertiary uppercase tracking-wider font-semibold">Blockchain</div>
          <div className="text-xl font-display font-bold flex items-center gap-2 truncate" style={{ color: qube.favorite_color }}>
            {qube.home_blockchain === 'bitcoincash' ? (
              <img src="/bitcoin_cash_logo.svg" alt="BCH" className="w-5 h-5 flex-shrink-0" />
            ) : '⛓️'}
            <span className="truncate">{qube.home_blockchain === 'bitcoincash' ? 'Bitcoin Cash' : qube.home_blockchain || 'Unknown'}</span>
          </div>
        </div>

        {/* Birth Date */}
        <div className="flex flex-col">
          <div className="text-xs text-text-tertiary uppercase tracking-wider font-semibold">Born</div>
          <div className="text-xl font-display font-bold flex items-center gap-2" style={{ color: qube.favorite_color }}>
            🎂 {qube.birth_timestamp
              ? new Date(qube.birth_timestamp * 1000).toLocaleDateString('en-US', {
                  month: 'short',
                  day: 'numeric',
                  year: 'numeric'
                })
              : 'Unknown'}
          </div>
        </div>
      </div>
    </GlassCard>
  );
};
