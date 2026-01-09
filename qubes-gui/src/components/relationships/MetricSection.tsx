import React, { useState } from 'react';

interface Metric {
  key: string;
  label: string;
  value: number;
  color: string;
}

interface MetricSectionProps {
  title: string;
  icon: string;
  metrics: Metric[];
  defaultExpanded?: boolean;
}

const ProgressBar: React.FC<{ value: number; color: string }> = ({ value, color }) => (
  <div className="w-full bg-glass-bg rounded-full h-1.5 overflow-hidden">
    <div
      className="h-full transition-all duration-300"
      style={{ width: `${Math.min(value, 100)}%`, backgroundColor: color }}
    />
  </div>
);

export const MetricSection: React.FC<MetricSectionProps> = ({
  title,
  icon,
  metrics,
  defaultExpanded = false,
}) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  // Calculate average for collapsed display
  const avgValue = metrics.length > 0
    ? Math.round(metrics.reduce((sum, m) => sum + m.value, 0) / metrics.length)
    : 0;

  // Don't render if no metrics
  if (metrics.length === 0) return null;

  return (
    <div className="border-t border-glass-border/50">
      {/* Collapsible Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between py-2 text-left hover:bg-white/5 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span>{icon}</span>
          <span className="text-text-secondary font-semibold text-xs">
            {title}
          </span>
          <span className="text-text-tertiary text-xs">
            ({metrics.length})
          </span>
        </div>
        <div className="flex items-center gap-2">
          {!isExpanded && (
            <span className="text-text-tertiary text-xs">
              avg: {avgValue}
            </span>
          )}
          <span className={`text-text-tertiary text-xs transition-transform ${isExpanded ? 'rotate-180' : ''}`}>
            ▼
          </span>
        </div>
      </button>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="pb-2 space-y-2">
          {metrics.map((metric) => (
            <div key={metric.key}>
              <div className="flex justify-between mb-1">
                <span className="text-text-tertiary text-xs">{metric.label}:</span>
                <span className="text-text-primary text-xs">{Math.round(metric.value)}/100</span>
              </div>
              <ProgressBar value={metric.value} color={metric.color} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
