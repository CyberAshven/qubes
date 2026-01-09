import React from 'react';

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

interface TraitBadgesProps {
  traitScores: Record<string, TraitScore>;
  traitDefinitions: Record<string, TraitDefinition>;
  maxDisplay?: number;
  showEmerging?: boolean;
  onRemoveTrait?: (trait: string) => void;
}

const WARNING_TRAITS = [
  'manipulative', 'gaslighting', 'toxic', 'narcissistic',
  'passive-aggressive', 'controlling', 'two-faced', 'deceptive',
  'disloyal', 'love-bombing', 'ghosting', 'breadcrumbing',
  'jealous', 'petty', 'condescending', 'antagonistic'
];

export const TraitBadges: React.FC<TraitBadgesProps> = ({
  traitScores,
  traitDefinitions,
  maxDisplay = 8,
  showEmerging = true,
  onRemoveTrait,
}) => {
  // Sort traits: warning first, then by confidence
  const sortedTraits = Object.entries(traitScores)
    .filter(([name, score]) => {
      if (score.is_confident) return true;
      if (showEmerging && score.score >= 40) return true;
      return false;
    })
    .sort(([aName, aScore], [bName, bScore]) => {
      const aWarning = WARNING_TRAITS.includes(aName) ? 1 : 0;
      const bWarning = WARNING_TRAITS.includes(bName) ? 1 : 0;
      if (aWarning !== bWarning) return bWarning - aWarning;
      return bScore.score - aScore.score;
    })
    .slice(0, maxDisplay);

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'rising': return '↑';
      case 'falling': return '↓';
      default: return '';
    }
  };

  const getOpacityClass = (score: TraitScore) => {
    if (score.is_confident && score.score >= 75) return 'opacity-100';
    if (score.is_confident) return 'opacity-90';
    return 'opacity-60';  // Emerging
  };

  const formatTimestamp = (ts: number): string => {
    if (!ts) return 'Unknown';
    const date = new Date(ts * 1000);
    return date.toLocaleDateString();
  };

  return (
    <div className="flex flex-wrap gap-1.5">
      {sortedTraits.map(([name, score]) => {
        const def = traitDefinitions[name];
        const isWarning = WARNING_TRAITS.includes(name);

        const bgClass = isWarning
          ? 'bg-red-500/20 border-red-500/40'
          : score.is_confident
            ? 'bg-accent-primary/20 border-accent-primary/40'
            : 'bg-gray-500/20 border-gray-500/40';

        const textClass = isWarning
          ? 'text-red-400'
          : score.is_confident
            ? 'text-accent-primary'
            : 'text-gray-400';

        const tooltip = [
          def?.description || name,
          `Confidence: ${score.score.toFixed(0)}%`,
          `Evidence: ${score.evidence_count} evaluations`,
          `First detected: ${formatTimestamp(score.first_detected)}`,
          score.volatility > 25 ? `Volatility: ${score.volatility.toFixed(0)}% (inconsistent)` : '',
          score.source === 'ai_direct' ? 'Source: AI detected' :
            score.source === 'both' ? 'Source: Metrics + AI' : 'Source: Metrics',
        ].filter(Boolean).join('\n');

        return (
          <span
            key={name}
            className={`
              inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs
              border ${bgClass} ${textClass} ${getOpacityClass(score)}
              transition-all hover:brightness-110 cursor-default
            `}
            title={tooltip}
          >
            <span>{def?.icon || '🏷️'}</span>
            <span className="capitalize">{name.replace(/-/g, ' ')}</span>
            <span className="text-[10px] opacity-70">
              {score.score.toFixed(0)}%
            </span>
            {score.volatility > 25 && (
              <span className="text-yellow-400" title="Volatile/inconsistent">⚡</span>
            )}
            {getTrendIcon(score.trend) && (
              <span className={score.trend === 'rising' ? 'text-green-400' : 'text-orange-400'}>
                {getTrendIcon(score.trend)}
              </span>
            )}
            {!score.is_confident && (
              <span className="text-[9px] text-gray-500">(emerging)</span>
            )}
            {onRemoveTrait && (
              <button
                onClick={(e) => { e.stopPropagation(); onRemoveTrait(name); }}
                className="ml-0.5 hover:text-red-400 transition-colors"
                title="Hide this trait"
              >
                ×
              </button>
            )}
          </span>
        );
      })}

      {sortedTraits.length === 0 && (
        <span className="text-text-tertiary text-xs italic">
          No traits detected yet
        </span>
      )}

      {Object.keys(traitScores).length > maxDisplay && (
        <span className="text-text-tertiary text-xs">
          +{Object.keys(traitScores).length - maxDisplay} more
        </span>
      )}
    </div>
  );
};
