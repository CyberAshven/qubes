import React from 'react';

interface GlassInputProps {
  label?: string;
  placeholder?: string;
  type?: 'text' | 'password' | 'email' | 'number';
  value?: string;
  onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onPaste?: (e: React.ClipboardEvent<HTMLInputElement>) => void;
  error?: string;
  disabled?: boolean;
  className?: string;
  autoFocus?: boolean;
}

export const GlassInput: React.FC<GlassInputProps> = ({
  label,
  placeholder,
  type = 'text',
  value,
  onChange,
  error,
  disabled = false,
  className = '',
  autoFocus = false,
}) => {
  return (
    <div className={`flex flex-col gap-2 ${className}`}>
      {label && (
        <label className="text-sm font-medium text-text-secondary">
          {label}
        </label>
      )}
      <input
        type={type}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        disabled={disabled}
        autoFocus={autoFocus}
        className={`
          glass-input
          ${error ? 'border-accent-danger focus:ring-accent-danger' : ''}
          ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
        `}
      />
      {error && (
        <span className="text-sm text-accent-danger">{error}</span>
      )}
    </div>
  );
};
