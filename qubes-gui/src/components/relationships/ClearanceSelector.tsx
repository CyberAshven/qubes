import React, { useState, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { invoke } from '@tauri-apps/api/core';

interface ClearanceProfile {
  name: string;
  level: number;
  description: string;
  icon: string;
  color: string;
}

interface ClearanceSelectorProps {
  entityId: string;
  currentProfile: string;
  profiles: Record<string, ClearanceProfile>;
  qubeId: string;
  userId: string;
  password: string;
  onClearanceChange: (profile: string) => void;
  onOpenAdvanced?: () => void;
  disabled?: boolean;
}

const PROFILE_ORDER = ['none', 'public', 'professional', 'social', 'trusted', 'inner_circle', 'family'];

export const ClearanceSelector: React.FC<ClearanceSelectorProps> = ({
  entityId,
  currentProfile,
  profiles,
  qubeId,
  userId,
  password,
  onClearanceChange,
  onOpenAdvanced,
  disabled = false,
}) => {
  const [showDropdown, setShowDropdown] = useState(false);
  const [loading, setLoading] = useState(false);
  const [dropdownPosition, setDropdownPosition] = useState({ top: 0, left: 0 });
  const buttonRef = useRef<HTMLButtonElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Update dropdown position when shown
  useEffect(() => {
    if (showDropdown && buttonRef.current) {
      const rect = buttonRef.current.getBoundingClientRect();
      setDropdownPosition({
        top: rect.bottom + 4,
        left: rect.left,
      });
    }
  }, [showDropdown]);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node) &&
          buttonRef.current && !buttonRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelect = async (profile: string) => {
    if (profile === currentProfile) {
      setShowDropdown(false);
      return;
    }

    setLoading(true);
    try {
      const result = await invoke<{ success: boolean; clearance_profile?: string; error?: string }>(
        'set_relationship_clearance',
        { userId, qubeId, entityId, profile, password }
      );
      if (result.success) {
        onClearanceChange(profile);
      }
    } catch (error) {
      console.error('Failed to set clearance:', error);
    } finally {
      setLoading(false);
      setShowDropdown(false);
    }
  };

  const currentDef = profiles[currentProfile] || { icon: '🚫', name: currentProfile, description: '' };

  const getProfileBadgeClass = (profile: string): string => {
    switch (profile) {
      case 'family': return 'bg-pink-500/20 text-pink-300 border-pink-500/30';
      case 'inner_circle': return 'bg-green-500/20 text-green-300 border-green-500/30';
      case 'trusted': return 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30';
      case 'social': return 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30';
      case 'professional': return 'bg-blue-500/20 text-blue-300 border-blue-500/30';
      case 'public': return 'bg-gray-500/20 text-gray-300 border-gray-500/30';
      default: return 'bg-gray-500/20 text-gray-400 border-gray-500/30';
    }
  };

  const formatProfileName = (name: string): string => {
    switch (name) {
      case 'none': return 'None';
      case 'public': return 'Minimal';
      case 'professional': return 'Limited';
      case 'social': return 'Standard';
      case 'trusted': return 'Extended';
      case 'inner_circle': return 'Full';
      case 'family': return 'Complete';
      default: return name.charAt(0).toUpperCase() + name.slice(1);
    }
  };

  return (
    <div className="space-y-2">
      <h4 className="text-text-secondary font-semibold text-xs flex items-center gap-1">
        🔐 Clearance
      </h4>

      <div className="flex items-center gap-2 flex-wrap">
        {/* Current profile dropdown */}
        <button
          ref={buttonRef}
          onClick={() => !disabled && setShowDropdown(!showDropdown)}
          disabled={disabled || loading}
          className={`
            inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium border
            ${getProfileBadgeClass(currentProfile)}
            ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer hover:brightness-110'}
            transition-all
          `}
        >
          {loading ? (
            <span className="animate-spin">⚙️</span>
          ) : (
            <span>{currentDef.icon}</span>
          )}
          <span>{formatProfileName(currentProfile)}</span>
          {!disabled && <span className="text-current/60">▼</span>}
        </button>

        {showDropdown && createPortal(
          <div
            ref={dropdownRef}
            className="fixed z-[9999] min-w-[200px] bg-bg-secondary border border-glass-border rounded-lg shadow-lg overflow-hidden"
            style={{
              top: dropdownPosition.top,
              left: dropdownPosition.left,
            }}
          >
            {PROFILE_ORDER.map((name) => {
              const def = profiles[name];
              if (!def) return null;
              const isSelected = name === currentProfile;
              return (
                <button
                  key={name}
                  onClick={() => handleSelect(name)}
                  className={`
                    w-full px-3 py-2 text-left text-xs flex items-center gap-2 transition-colors
                    ${isSelected ? 'bg-accent-primary/20' : 'hover:bg-accent-primary/10'}
                  `}
                >
                  <span>{def.icon}</span>
                  <div className="flex-1">
                    <div className="text-text-primary font-medium">{formatProfileName(name)}</div>
                    <div className="text-text-tertiary text-[10px]">{def.description}</div>
                  </div>
                  {isSelected && <span className="text-accent-primary">✓</span>}
                </button>
              );
            })}

            {onOpenAdvanced && (
              <>
                <div className="border-t border-glass-border my-1" />
                <button
                  onClick={() => { setShowDropdown(false); onOpenAdvanced(); }}
                  className="w-full px-3 py-2 text-left text-xs text-text-tertiary hover:bg-accent-primary/10 flex items-center gap-2"
                >
                  <span>⚙️</span>
                  <span>Customize overrides...</span>
                </button>
              </>
            )}
          </div>,
          document.body
        )}
      </div>
    </div>
  );
};
