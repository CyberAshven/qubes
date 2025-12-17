import { useState, useCallback } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { GlassCard, GlassButton } from '../glass';
import { PendingIntroduction } from './ConnectionManager';
import { useAuth } from '../../hooks/useAuth';

interface AIEvaluation {
  recommendation: 'accept' | 'reject' | 'review';
  reasoning: string;
  response_message: string;
}

interface PendingRequestsProps {
  pending: PendingIntroduction[];
  onAccept: (relayId: string) => void;
  onReject: (relayId: string) => void;
  loading: boolean;
  qubeId: string;
}

export const PendingRequests: React.FC<PendingRequestsProps> = ({
  pending,
  onAccept,
  onReject,
  loading,
  qubeId,
}) => {
  const { userId, password } = useAuth();
  const [evaluations, setEvaluations] = useState<Record<string, AIEvaluation | null>>({});
  const [evaluating, setEvaluating] = useState<Record<string, boolean>>({});
  const [expandedIntro, setExpandedIntro] = useState<string | null>(null);

  // Evaluate an introduction using AI (manual trigger)
  const evaluateIntro = useCallback(async (intro: PendingIntroduction) => {
    if (evaluating[intro.relay_id]) return;

    setEvaluating(prev => ({ ...prev, [intro.relay_id]: true }));

    try {
      const result = await invoke<{
        success: boolean;
        recommendation?: string;
        reasoning?: string;
        response_message?: string;
        error?: string;
      }>('evaluate_introduction', {
        userId,
        qubeId,
        fromName: intro.from_name,
        introMessage: `Introduction request from ${intro.from_name}`,
        password,
      });

      if (result.success && result.recommendation) {
        setEvaluations(prev => ({
          ...prev,
          [intro.relay_id]: {
            recommendation: result.recommendation as 'accept' | 'reject' | 'review',
            reasoning: result.reasoning || '',
            response_message: result.response_message || '',
          },
        }));
      } else {
        console.error('Evaluation failed:', result.error);
        // Mark as failed so we don't keep retrying
        setEvaluations(prev => ({
          ...prev,
          [intro.relay_id]: null,
        }));
      }
    } catch (err) {
      console.error('Failed to evaluate introduction:', err);
      // Mark as failed
      setEvaluations(prev => ({
        ...prev,
        [intro.relay_id]: null,
      }));
    } finally {
      setEvaluating(prev => ({ ...prev, [intro.relay_id]: false }));
    }
  }, [userId, qubeId, password, evaluating]);

  if (pending.length === 0) {
    return (
      <GlassCard className="p-6 text-center">
        <p className="text-text-secondary">No pending introduction requests</p>
        <p className="text-sm text-text-tertiary mt-2">
          When other Qubes want to connect, their requests will appear here.
        </p>
      </GlassCard>
    );
  }

  const getRecommendationColor = (rec: string) => {
    switch (rec) {
      case 'accept':
        return 'text-accent-success';
      case 'reject':
        return 'text-accent-danger';
      default:
        return 'text-accent-warning';
    }
  };

  const getRecommendationBadge = (rec: string) => {
    switch (rec) {
      case 'accept':
        return 'bg-accent-success/20 border-accent-success/50';
      case 'reject':
        return 'bg-accent-danger/20 border-accent-danger/50';
      default:
        return 'bg-accent-warning/20 border-accent-warning/50';
    }
  };

  return (
    <div className="space-y-3">
      {pending.map((intro) => {
        const evaluation = evaluations[intro.relay_id];
        const isEvaluating = evaluating[intro.relay_id];
        const isExpanded = expandedIntro === intro.relay_id;

        return (
          <GlassCard key={intro.relay_id} className="p-4">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="font-display text-lg text-text-primary">
                    {intro.from_name}
                  </h3>
                  {/* AI Recommendation Badge */}
                  {evaluation && (
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full border ${getRecommendationBadge(
                        evaluation.recommendation
                      )} ${getRecommendationColor(evaluation.recommendation)}`}
                    >
                      AI: {evaluation.recommendation.charAt(0).toUpperCase() +
                        evaluation.recommendation.slice(1)}
                    </span>
                  )}
                  {isEvaluating && (
                    <span className="text-xs text-accent-secondary animate-pulse">
                      Thinking...
                    </span>
                  )}
                  {/* Ask AI button - only show if not evaluated and not currently evaluating */}
                  {!evaluation && !isEvaluating && (
                    <button
                      onClick={() => evaluateIntro(intro)}
                      className="text-xs px-2 py-0.5 rounded-full border border-accent-secondary text-accent-secondary hover:bg-accent-secondary/20 transition-colors"
                    >
                      Ask AI
                    </button>
                  )}
                </div>
                <p className="text-sm text-text-tertiary font-mono">
                  {intro.from_commitment.substring(0, 16)}...
                </p>

                {/* AI Reasoning (expandable) */}
                {evaluation && (
                  <button
                    onClick={() => setExpandedIntro(isExpanded ? null : intro.relay_id)}
                    className="text-sm text-accent-primary mt-2 hover:underline"
                  >
                    {isExpanded ? 'Hide AI analysis' : 'Show AI analysis'}
                  </button>
                )}

                {isExpanded && evaluation && (
                  <div className="mt-3 p-3 bg-glass-light rounded-lg">
                    <p className="text-sm text-text-secondary">
                      <span className="font-medium text-text-primary">Reasoning: </span>
                      {evaluation.reasoning}
                    </p>
                    {evaluation.recommendation === 'accept' && evaluation.response_message && (
                      <p className="text-sm text-text-secondary mt-2">
                        <span className="font-medium text-text-primary">Suggested response: </span>
                        "{evaluation.response_message}"
                      </p>
                    )}
                  </div>
                )}
              </div>

              <div className="flex gap-2 ml-4">
                <GlassButton
                  variant={evaluation?.recommendation === 'accept' ? 'primary' : 'secondary'}
                  size="sm"
                  onClick={() => onAccept(intro.relay_id)}
                  disabled={loading}
                >
                  Accept
                </GlassButton>
                <GlassButton
                  variant={evaluation?.recommendation === 'reject' ? 'danger' : 'secondary'}
                  size="sm"
                  onClick={() => onReject(intro.relay_id)}
                  disabled={loading}
                >
                  Reject
                </GlassButton>
              </div>
            </div>
          </GlassCard>
        );
      })}
    </div>
  );
};
