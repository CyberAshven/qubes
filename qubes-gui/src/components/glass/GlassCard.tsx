import React from 'react';

interface GlassCardProps {
  children: React.ReactNode;
  className?: string;
  variant?: 'default' | 'elevated' | 'interactive';
  onClick?: (e: React.MouseEvent) => void;
  style?: React.CSSProperties;
}

export const GlassCard: React.FC<GlassCardProps> = ({
  children,
  className = '',
  variant = 'default',
  onClick,
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
    <div className={classes} onClick={onClick} style={style}>
      {children}
    </div>
  );
};
