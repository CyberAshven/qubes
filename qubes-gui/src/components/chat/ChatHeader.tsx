import React, { useState, useEffect } from 'react';
import { convertFileSrc } from '@tauri-apps/api/core';
import { GlassCard } from '../glass/GlassCard';
import { Qube } from '../../types';
import { formatModelName } from '../../utils/modelFormatter';

// Voice name aliases for display
const VOICE_NAME_ALIASES: Record<string, string> = {
  'af_heart': 'Heart',
  'af_sarah': 'Sarah',
  'af_nicole': 'Nicole',
  'af_sky': 'Sky',
  'af_bella': 'Bella',
  'af_alloy': 'Alloy',
  'af_aoede': 'Aoede',
  'af_jessica': 'Jessica',
  'af_kore': 'Kore',
  'af_nova': 'Nova',
  'af_river': 'River',
  'af_stella': 'Stella',
  'am_adam': 'Adam',
  'am_echo': 'Echo',
  'am_eric': 'Eric',
  'am_fenrir': 'Fenrir',
  'am_liam': 'Liam',
  'am_michael': 'Michael',
  'am_onyx': 'Onyx',
  'am_puck': 'Puck',
  'am_santa': 'Santa',
  'bf_emma': 'Emma',
  'bf_isabella': 'Isabella',
  'bf_alice': 'Alice',
  'bf_lily': 'Lily',
  'bm_george': 'George',
  'bm_lewis': 'Lewis',
  'bm_daniel': 'Daniel',
  'bm_fable': 'Fable',
};

const formatVoiceDisplay = (voiceModel: string | undefined): string => {
  if (!voiceModel) return 'Not set';
  // Extract voice ID (e.g., 'kokoro:af_heart' -> 'af_heart')
  const voiceId = voiceModel.includes(':') ? voiceModel.split(':')[1] : voiceModel;
  // Look up friendly name
  return VOICE_NAME_ALIASES[voiceId] || voiceId.charAt(0).toUpperCase() + voiceId.slice(1);
};

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
      <div className="flex items-center justify-between">
        {/* Avatar + Name */}
        <div className="flex items-center gap-3">
          <img
            src={getAvatarPath()}
            alt={`${qube.name} avatar`}
            className="w-16 h-16 rounded-xl object-cover shadow-lg transition-transform hover:scale-105"
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
            className="w-16 h-16 rounded-xl flex items-center justify-center text-2xl font-display font-bold shadow-lg transition-transform hover:scale-105"
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
          <div className="flex flex-col">
            <div className="text-xs text-text-tertiary uppercase tracking-wider font-semibold">Name</div>
            <h1 className="text-xl font-display font-bold" style={{ color: qube.favorite_color }}>
              {qube.name}
            </h1>
          </div>
        </div>

        {/* Model - Uses local state, updates independently */}
        <div className="flex flex-col">
          <div className="text-xs text-text-tertiary uppercase tracking-wider font-semibold">Model</div>
          <div className="text-xl font-display font-bold flex items-center gap-2" style={{ color: qube.favorite_color }}>
            🤖 {formatModelName(displayedModel)}
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
        <div className="flex flex-col">
          <div className="text-xs text-text-tertiary uppercase tracking-wider font-semibold">Voice</div>
          <div className="text-xl font-display font-bold flex items-center gap-2" style={{ color: qube.favorite_color }}>
            🎤 {formatVoiceDisplay(qube.voice_model)}
          </div>
        </div>

        {/* Creator */}
        <div className="flex flex-col">
          <div className="text-xs text-text-tertiary uppercase tracking-wider font-semibold">Creator</div>
          <div className="text-xl font-display font-bold flex items-center gap-2" style={{ color: qube.favorite_color }}>
            👤 {qube.creator || 'Unknown'}
          </div>
        </div>

        {/* Blockchain */}
        <div className="flex flex-col">
          <div className="text-xs text-text-tertiary uppercase tracking-wider font-semibold">Blockchain</div>
          <div className="text-xl font-display font-bold flex items-center gap-2" style={{ color: qube.favorite_color }}>
            {qube.home_blockchain === 'bitcoincash' ? (
              <img src="/bitcoin_cash_logo.svg" alt="BCH" className="w-5 h-5" />
            ) : '⛓️'}
            {qube.home_blockchain === 'bitcoincash' ? 'Bitcoin Cash' : qube.home_blockchain || 'Unknown'}
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
