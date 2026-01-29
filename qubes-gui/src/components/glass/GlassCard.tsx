import React from 'react';

export interface GlassCardProps {
  children: React.ReactNode;
  className?: string;
  variant?: 'default' | 'elevated' | 'interactive';
  onClick?: (e: React.MouseEvent) => void;
  onMouseDown?: (e: React.MouseEvent) => void;
  style?: React.CSSProperties;
}

export const GlassCard: React.FC<GlassCardProps> = ({
  children,
  className = '',
  variant = 'default',
  onClick,
  onMouseDown,
  style,
}) => {
  const baseClasses = 'glass-card';

  const variantClasses = {
    default: '',
    elevated: 'shadow-glass-hover',
    interactive: 'glass-card-hover cursor-pointer',
  };

  const classes = `${baseClasses} ${variantClasses[variant]} ${className}`;

  return (
    <div className={classes} onClick={onClick} onMouseDown={onMouseDown} style={style}>
      {children}
    </div>
  );
};
