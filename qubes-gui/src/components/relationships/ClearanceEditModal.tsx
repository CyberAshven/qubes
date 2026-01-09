import React, { useState, useEffect } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { GlassCard, GlassButton } from '../glass';

interface ClearanceEditModalProps {
  isOpen: boolean;
  entityId: string;
  entityName: string;
  currentProfile: string;
  currentFieldGrants: string[];
  currentFieldDenials: string[];
  qubeId: string;
  userId: string;
  password: string;
  onClose: () => void;
  onSave: (profile: string, grants: string[], denials: string[]) => void;
}

// Common owner info fields that can be granted/denied
const AVAILABLE_FIELDS = [
  { key: 'name', label: 'Full Name', category: 'standard' },
  { key: 'nickname', label: 'Nickname', category: 'standard' },
  { key: 'occupation', label: 'Occupation', category: 'standard' },
  { key: 'employer', label: 'Employer', category: 'standard' },
  { key: 'email', label: 'Email', category: 'standard' },
  { key: 'phone', label: 'Phone', category: 'standard' },
  { key: 'address', label: 'Address', category: 'standard' },
  { key: 'birthday', label: 'Birthday', category: 'dates' },
  { key: 'anniversary', label: 'Anniversary', category: 'dates' },
  { key: 'hobbies', label: 'Hobbies', category: 'preferences' },
  { key: 'favorites', label: 'Favorites', category: 'preferences' },
  { key: 'medical', label: 'Medical Info', category: 'medical' },
];

export const ClearanceEditModal: React.FC<ClearanceEditModalProps> = ({
  isOpen,
  entityId,
  entityName,
  currentProfile,
  currentFieldGrants,
  currentFieldDenials,
  qubeId,
  userId,
  password,
  onClose,
  onSave,
}) => {
  const [fieldGrants, setFieldGrants] = useState<string[]>(currentFieldGrants);
  const [fieldDenials, setFieldDenials] = useState<string[]>(currentFieldDenials);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setFieldGrants(currentFieldGrants);
    setFieldDenials(currentFieldDenials);
  }, [currentFieldGrants, currentFieldDenials, isOpen]);

  if (!isOpen) return null;

  const toggleGrant = (field: string) => {
    if (fieldGrants.includes(field)) {
      setFieldGrants(fieldGrants.filter(f => f !== field));
    } else {
      setFieldGrants([...fieldGrants, field]);
      // Remove from denials if present
      setFieldDenials(fieldDenials.filter(f => f !== field));
    }
  };

  const toggleDenial = (field: string) => {
    if (fieldDenials.includes(field)) {
      setFieldDenials(fieldDenials.filter(f => f !== field));
    } else {
      setFieldDenials([...fieldDenials, field]);
      // Remove from grants if present
      setFieldGrants(fieldGrants.filter(f => f !== field));
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const result = await invoke<{ success: boolean; error?: string }>(
        'set_relationship_clearance',
        {
          userId,
          qubeId,
          entityId,
          profile: currentProfile,
          password,
          field_grants: fieldGrants.length > 0 ? fieldGrants : null,
          field_denials: fieldDenials.length > 0 ? fieldDenials : null,
        }
      );
      if (result.success) {
        onSave(currentProfile, fieldGrants, fieldDenials);
        onClose();
      }
    } catch (error) {
      console.error('Failed to save clearance:', error);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <GlassCard className="w-full max-w-lg max-h-[80vh] p-6 m-4 overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-display text-accent-primary">
            🔐 Clearance Overrides
          </h2>
          <button onClick={onClose} className="text-text-tertiary hover:text-text-primary text-xl">
            ×
          </button>
        </div>

        <p className="text-text-secondary text-sm mb-4">
          Customize field-level access for <span className="text-text-primary font-medium">{entityName}</span>
        </p>

        {/* Content */}
        <div className="flex-1 overflow-y-auto space-y-4">
          {/* Field Grants */}
          <div>
            <h3 className="text-sm font-semibold text-green-400 mb-2">
              + Extra Access (grants beyond profile)
            </h3>
            <div className="grid grid-cols-2 gap-2">
              {AVAILABLE_FIELDS.map(field => (
                <label
                  key={`grant-${field.key}`}
                  className="flex items-center gap-2 text-xs cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={fieldGrants.includes(field.key)}
                    onChange={() => toggleGrant(field.key)}
                    className="rounded border-glass-border bg-glass-bg text-green-500 focus:ring-green-500"
                  />
                  <span className="text-text-primary">{field.label}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Field Denials */}
          <div>
            <h3 className="text-sm font-semibold text-red-400 mb-2">
              - Restricted (blocks even if profile allows)
            </h3>
            <div className="grid grid-cols-2 gap-2">
              {AVAILABLE_FIELDS.map(field => (
                <label
                  key={`deny-${field.key}`}
                  className="flex items-center gap-2 text-xs cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={fieldDenials.includes(field.key)}
                    onChange={() => toggleDenial(field.key)}
                    className="rounded border-glass-border bg-glass-bg text-red-500 focus:ring-red-500"
                  />
                  <span className="text-text-primary">{field.label}</span>
                </label>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-3 mt-4 pt-4 border-t border-glass-border">
          <GlassButton variant="secondary" onClick={onClose} size="sm">
            Cancel
          </GlassButton>
          <GlassButton variant="primary" onClick={handleSave} loading={saving} size="sm">
            Save Changes
          </GlassButton>
        </div>
      </GlassCard>
    </div>
  );
};
