import React, { useState, useRef, useEffect, useCallback } from 'react';

export interface SelectOption {
  value: string;
  label: string;
}

interface DarkSelectProps {
  value: string;
  onChange: (value: string) => void;
  options: SelectOption[];
  className?: string;
  /** Show as always-expanded scrollable list (like size > 1) */
  expanded?: boolean;
  /** Max visible items before scrolling (default 8) */
  maxVisible?: number;
  disabled?: boolean;
  placeholder?: string;
}

export default function DarkSelect({
  value,
  onChange,
  options,
  className = '',
  expanded = false,
  maxVisible = 8,
  disabled = false,
  placeholder,
}: DarkSelectProps) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const selectedLabel = options.find(o => o.value === value)?.label
    ?? placeholder ?? (options.length > 0 ? options[0].label : '');

  // Close dropdown when clicking outside
  useEffect(() => {
    if (!open) return;
    const handleClick = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [open]);

  // Scroll selected item into view when dropdown opens
  useEffect(() => {
    if ((open || expanded) && dropdownRef.current) {
      const selected = dropdownRef.current.querySelector('[data-selected="true"]');
      if (selected) selected.scrollIntoView({ block: 'nearest' });
    }
  }, [open, expanded, value]);

  const handleSelect = useCallback((optionValue: string) => {
    onChange(optionValue);
    setOpen(false);
  }, [onChange]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (disabled) return;
    const idx = options.findIndex(o => o.value === value);
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (!open && !expanded) { setOpen(true); return; }
      if (idx < options.length - 1) onChange(options[idx + 1].value);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (idx > 0) onChange(options[idx - 1].value);
    } else if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      if (!expanded) setOpen(o => !o);
    } else if (e.key === 'Escape') {
      setOpen(false);
    }
  }, [disabled, options, value, onChange, open, expanded]);

  const itemHeight = 28; // ~py-1.5 + text-xs
  const listMaxHeight = Math.min(maxVisible, options.length) * itemHeight;

  // Prevent scroll from bubbling to the page when the list hits top/bottom
  const handleWheel = useCallback((e: React.WheelEvent<HTMLDivElement>) => {
    const el = e.currentTarget;
    const atTop = el.scrollTop === 0 && e.deltaY < 0;
    const atBottom = el.scrollTop + el.clientHeight >= el.scrollHeight && e.deltaY > 0;
    if (atTop || atBottom) {
      e.preventDefault();
    }
    e.stopPropagation();
  }, []);

  const optionList = (
    <div
      ref={dropdownRef}
      onWheel={handleWheel}
      className={expanded
        ? 'overflow-y-auto rounded border border-glass-border'
        : 'absolute left-0 right-0 top-full mt-0.5 z-50 overflow-y-auto rounded border border-glass-border shadow-lg'
      }
      style={{
        maxHeight: listMaxHeight,
        backgroundColor: 'rgba(20, 20, 35, 0.97)',
        overscrollBehavior: 'contain',
      }}
    >
      {options.map((option) => (
        <div
          key={option.value}
          data-selected={option.value === value}
          onClick={() => handleSelect(option.value)}
          className={`px-2 py-1.5 text-xs cursor-pointer transition-colors
            ${option.value === value
              ? 'bg-accent-primary/20 text-accent-primary'
              : 'text-text-primary hover:bg-accent-primary/10'
            }`}
        >
          {option.label}
        </div>
      ))}
    </div>
  );

  // Expanded mode: always-visible scrollable list
  if (expanded) {
    return (
      <div
        ref={containerRef}
        className={`relative ${className}`}
        tabIndex={0}
        onKeyDown={handleKeyDown}
      >
        {optionList}
      </div>
    );
  }

  // Dropdown mode: button that toggles a dropdown
  return (
    <div ref={containerRef} className={`relative ${className}`}>
      <button
        type="button"
        disabled={disabled}
        onClick={() => !disabled && setOpen(o => !o)}
        onKeyDown={handleKeyDown}
        className={`w-full text-left flex justify-between items-center gap-1
          px-2 py-1 rounded border text-xs transition-colors
          ${disabled
            ? 'bg-bg-tertiary border-glass-border text-text-tertiary opacity-50 cursor-not-allowed'
            : 'bg-bg-tertiary border-glass-border text-text-primary hover:border-accent-primary/40 focus:outline-none focus:ring-1 focus:ring-accent-primary/50'
          }`}
      >
        <span className="truncate">{selectedLabel}</span>
        <svg
          className={`w-3 h-3 flex-shrink-0 transition-transform ${open ? 'rotate-180' : ''}`}
          fill="none" stroke="currentColor" viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {open && optionList}
    </div>
  );
}
