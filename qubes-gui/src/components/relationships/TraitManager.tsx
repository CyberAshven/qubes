import React, { useState } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { TraitBadges } from './TraitBadges';

interface TraitScore {
  score: number;
  evidence_count: number;
  first_detected: number;
  last_updated: number;
  consistency: number;
  volatility: number;
  trend: 'rising' | 'stable' | 'falling';
  source: 'metric_derived' | 'ai_direct' | 'both';
  is_confident: boolean;
}

interface TraitDefinition {
  name: string;
  category: string;
  description: string;
  icon: string;
  color: string;
  polarity: 'positive' | 'negative' | 'neutral' | 'warning';
  is_warning?: boolean;
}

interface TraitManagerProps {
  entityId: string;
  traitScores: Record<string, TraitScore>;
  traitDefinitions: Record<string, TraitDefinition>;
  manualOverrides: Record<string, boolean>;
  qubeId: string;
  userId: string;
  password: string;
  onTraitOverride: (trait: string, visible: boolean) => void;
  disabled?: boolean;
  maxDisplay?: number;
}

export const TraitManager: React.FC<TraitManagerProps> = ({
  entityId,
  traitScores,
  traitDefinitions,
  manualOverrides,
  qubeId,
  userId,
  password,
  onTraitOverride,
  disabled = false,
  maxDisplay = 8,
}) => {
  const [loading, setLoading] = useState<string | null>(null);

  // Filter out manually hidden traits
  const visibleTraits: Record<string, TraitScore> = {};
  for (const [name, score] of Object.entries(traitScores)) {
    if (manualOverrides[name] !== false) {
      visibleTraits[name] = score;
    }
  }

  const handleRemoveTrait = async (trait: string) => {
    if (disabled || loading) return;

    setLoading(trait);
    try {
      // Call backend to update manual override
      const result = await invoke<{ success: boolean; error?: string }>(
        'set_trait_override',
        { userId, qubeId, entityId, trait, visible: false, password }
      );
      if (result.success) {
        onTraitOverride(trait, false);
      }
    } catch (error) {
      // If command doesn't exist yet, just update locally
      console.debug('Trait override not yet implemented in backend:', error);
      onTraitOverride(trait, false);
    } finally {
      setLoading(null);
    }
  };

  // Count hidden traits
  const hiddenCount = Object.keys(traitScores).length - Object.keys(visibleTraits).length;

  return (
    <div className="space-y-2">
      <h4 className="text-text-secondary font-semibold text-xs flex items-center gap-1">
        🧬 Traits
        <span className="text-text-tertiary font-normal">(AI-detected)</span>
        {hiddenCount > 0 && (
          <span className="text-text-tertiary font-normal">
            ({hiddenCount} hidden)
          </span>
        )}
      </h4>

      <TraitBadges
        traitScores={visibleTraits}
        traitDefinitions={traitDefinitions}
        maxDisplay={maxDisplay}
        showEmerging={true}
        onRemoveTrait={disabled ? undefined : handleRemoveTrait}
      />

      {loading && (
        <div className="text-text-tertiary text-xs">
          Updating...
        </div>
      )}
    </div>
  );
};
