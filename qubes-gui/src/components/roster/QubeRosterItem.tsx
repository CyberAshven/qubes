import React from 'react';
import { Qube } from '../../types';
import { formatModelName } from '../../utils/modelFormatter';

interface QubeRosterItemProps {
  qube: Qube;
  isSelected: boolean;
  isActive: boolean;
  onClick: (e: React.MouseEvent) => void;
}

// Helper function to convert hex to RGB
function hexToRgb(hex: string): { r: number; g: number; b: number } | null {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result ? {
    r: parseInt(result[1], 16),
    g: parseInt(result[2], 16),
    b: parseInt(result[3], 16)
  } : null;
}

export const QubeRosterItem: React.FC<QubeRosterItemProps> = ({
  qube,
  isSelected,
  isActive,
  onClick,
}) => {
  const statusColors = {
    active: 'bg-[#00ff88]', // Neon dark green
    inactive: 'bg-[#ff3366]', // Neon red
    busy: 'bg-accent-warning',
  };

  const baseClasses = `
    relative p-4 rounded-lg
    bg-glass-bg backdrop-blur-glass
    border transition-all duration-200
    cursor-pointer select-none
  `;

  const favoriteColor = qube.favorite_color || '#00ff88';

  // Create custom glow colors based on favorite color
  const glowColor = favoriteColor;
  const glowColorRgb = hexToRgb(glowColor);
  const strongGlow = `0 0 25px ${glowColor}80, 0 0 50px ${glowColor}40`;
  const mediumGlow = `0 0 20px ${glowColor}60`;
  const hoverGlow = `0 0 15px ${glowColorRgb ? `rgba(${glowColorRgb.r}, ${glowColorRgb.g}, ${glowColorRgb.b}, 0.2)` : `${glowColor}33`}`;

  // Background tint color (5% opacity of favorite color)
  const bgTint = glowColorRgb ? `rgba(${glowColorRgb.r}, ${glowColorRgb.g}, ${glowColorRgb.b}, 0.05)` : `${glowColor}0D`;

  const stateClasses = isActive
    ? 'border-l-4'
    : isSelected
    ? 'border-l-4'
    : 'border border-glass-border';

  const borderColor = (isActive || isSelected) ? favoriteColor : undefined;
  const backgroundColor = (isActive || isSelected) ? bgTint : undefined;
  const hoverBorderColor = favoriteColor + '4D'; // 30% opacity

  // Create custom pulse animation keyframes for active qube
  const pulseKeyframes = isActive ? `
    @keyframes custom-pulse-${qube.qube_id} {
      0%, 100% {
        box-shadow: ${strongGlow};
      }
      50% {
        box-shadow: 0 0 35px ${glowColor}99, 0 0 60px ${glowColor}66;
      }
    }
  ` : '';

  return (
    <>
      {isActive && <style>{pulseKeyframes}</style>}
      <div
        className={`${baseClasses} ${stateClasses} relative`}
        onClick={onClick}
        style={{
          borderColor: borderColor,
          backgroundColor: backgroundColor,
          boxShadow: isActive ? strongGlow : isSelected ? mediumGlow : undefined,
          animation: isActive ? `custom-pulse-${qube.qube_id} 2s ease-in-out infinite` : undefined,
          ...(!(isActive || isSelected) && {
            '--hover-border-color': hoverBorderColor,
            '--hover-glow': hoverGlow,
          } as React.CSSProperties),
        }}
      onMouseEnter={(e) => {
        if (!isActive && !isSelected) {
          e.currentTarget.style.borderColor = hoverBorderColor;
          e.currentTarget.style.boxShadow = hoverGlow;
        }
      }}
      onMouseLeave={(e) => {
        if (!isActive && !isSelected) {
          e.currentTarget.style.borderColor = '';
          e.currentTarget.style.boxShadow = '';
        }
      }}
    >
      {/* Blockchain Badge - Top Right Corner */}
      {qube.home_blockchain === 'bitcoincash' && (
        <div className="absolute top-2 right-2 opacity-85 hover:opacity-100 transition-opacity">
          <img
            src="/bitcoin_cash_logo.svg"
            alt="BCH"
            className="w-6 h-6"
            title="Bitcoin Cash"
          />
        </div>
      )}

      {/* Avatar */}
      <div className="flex items-start gap-3">
        <div
          className="relative w-12 h-12 rounded-xl flex items-center justify-center text-2xl font-display font-bold shadow-lg"
          style={{
            background: `linear-gradient(135deg, ${qube.favorite_color || '#00ff88'}40, ${qube.favorite_color || '#00ff88'}20)`,
            color: qube.favorite_color || '#00ff88',
            border: `2px solid ${qube.favorite_color || '#00ff88'}`,
            boxShadow: `0 0 15px ${qube.favorite_color || '#00ff88'}40`,
          }}
        >
          {qube.name.charAt(0).toUpperCase()}
        </div>

        <div className="flex-1 min-w-0">
          {/* Name */}
          <h3 className="text-base font-semibold text-text-primary truncate">
            {qube.name}
          </h3>

          {/* Model */}
          <p className="text-sm text-text-tertiary truncate">
            {formatModelName(qube.ai_model)}
          </p>

          {/* Stats - Status dot removed */}
        </div>
      </div>
      </div>
    </>
  );
};
