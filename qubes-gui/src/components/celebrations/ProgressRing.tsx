import React from 'react';
import { motion } from 'framer-motion';
import { useCelebration } from '../../contexts/CelebrationContext';

interface ProgressRingProps {
  progress: number; // 0-100
  size: number;
  strokeWidth: number;
  color: string;
  backgroundColor?: string;
  animated?: boolean;
  showPercentage?: boolean;
  children?: React.ReactNode;
}

export const ProgressRing: React.FC<ProgressRingProps> = ({
  progress,
  size,
  strokeWidth,
  color,
  backgroundColor = 'rgba(255,255,255,0.1)',
  animated = true,
  showPercentage = false,
  children,
}) => {
  const { settings } = useCelebration();
  const shouldAnimate = animated && !settings.reducedMotion;

  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const strokeDashoffset = circumference - (progress / 100) * circumference;

  // Calculate the position of the progress tip for the glow effect
  const progressAngle = (progress / 100) * Math.PI * 2 - Math.PI / 2;
  const tipX = size / 2 + radius * Math.cos(progressAngle);
  const tipY = size / 2 + radius * Math.sin(progressAngle);

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg
        width={size}
        height={size}
        className="transform -rotate-90"
      >
        {/* Background circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={backgroundColor}
          strokeWidth={strokeWidth}
        />

        {/* Progress circle */}
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset }}
          transition={shouldAnimate ? { duration: 0.5, ease: 'easeOut' } : { duration: 0 }}
          style={{
            filter: `drop-shadow(0 0 4px ${color})`,
          }}
        />

        {/* Glow effect at progress tip */}
        {progress > 0 && progress < 100 && shouldAnimate && (
          <motion.circle
            cx={tipX}
            cy={tipY}
            r={strokeWidth / 2 + 2}
            fill={color}
            initial={{ opacity: 0, scale: 0 }}
            animate={{ opacity: [0.5, 1, 0.5], scale: [1, 1.2, 1] }}
            transition={{ duration: 1, repeat: Infinity }}
            style={{
              filter: `blur(2px)`,
            }}
          />
        )}
      </svg>

      {/* Center content */}
      <div className="absolute inset-0 flex items-center justify-center">
        {showPercentage ? (
          <span className="text-sm font-bold" style={{ color }}>
            {Math.round(progress)}%
          </span>
        ) : (
          children
        )}
      </div>

      {/* Full completion sparkle */}
      {progress >= 100 && !settings.reducedMotion && (
        <motion.div
          className="absolute inset-0 flex items-center justify-center pointer-events-none"
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: [0, 1, 0], scale: [0.8, 1.2, 0.8] }}
          transition={{ duration: 2, repeat: Infinity }}
        >
          <div
            className="absolute w-full h-full rounded-full"
            style={{
              background: `radial-gradient(circle, ${color}40, transparent 70%)`,
            }}
          />
        </motion.div>
      )}
    </div>
  );
};

export default ProgressRing;
