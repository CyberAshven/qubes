import React from 'react';
import { Qube } from '../../types';
import { useQubeSelection } from '../../hooks/useQubeSelection';
import { QubeRosterItem } from './QubeRosterItem';

interface QubeRosterProps {
  qubes: Qube[];
}

// Stable empty array to avoid infinite loops with Zustand selectors
const EMPTY_ARRAY: string[] = [];

export const QubeRoster: React.FC<QubeRosterProps> = ({ qubes }) => {
  const currentTab = useQubeSelection((state) => state.currentTab);
  const toggleSelection = useQubeSelection((state) => state.toggleSelection);
  const isMultiSelectAllowed = useQubeSelection((state) => state.isMultiSelectAllowed);

  // Get selected IDs and active qube for CURRENT tab only
  const selectedQubeIds = useQubeSelection((state) => state.selectionByTab[state.currentTab] ?? EMPTY_ARRAY);
  const activeQubeId = useQubeSelection((state) => state.activeQubeByTab[state.currentTab]);

  const handleQubeClick = (qubeId: string, event: React.MouseEvent) => {
    const isCtrl = event.ctrlKey || event.metaKey;
    const isShift = event.shiftKey;
    toggleSelection(qubeId, isCtrl, isShift);
  };

  const multiSelectAllowed = isMultiSelectAllowed();
  const selectionCount = selectedQubeIds.length;

  return (
    <div className="w-[280px] h-full flex flex-col bg-bg-secondary border-r border-glass-border">
      {/* Header */}
      <div className="p-6 border-b border-accent-primary/30 bg-accent-primary/10">
        <div className="flex items-center justify-center gap-3">
          <h2 className="text-3xl font-cyber text-accent-primary font-bold tracking-wide uppercase">
            Qubes
          </h2>
          <span className="px-3 py-1 bg-accent-primary/30 text-accent-primary text-lg font-mono rounded-md font-semibold shadow-sm">
            {qubes.length}
          </span>
        </div>
      </div>

      {/* Selection Badge (multi-select tabs only) */}
      {multiSelectAllowed && selectionCount > 1 && (
        <div className="px-4 py-2 bg-accent-primary/10 border-b border-accent-primary/30">
          <p className="text-sm text-accent-primary font-medium">
            {selectionCount} qubes selected
          </p>
        </div>
      )}

      {/* Qube List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        {qubes.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-text-tertiary text-sm">No qubes yet</p>
            <p className="text-text-disabled text-xs mt-1">
              Create your first qube to get started
            </p>
          </div>
        ) : (
          qubes.map((qube) => {
            const isSelected = selectedQubeIds.includes(qube.qube_id);
            return (
              <QubeRosterItem
                key={qube.qube_id}
                qube={qube}
                isSelected={isSelected}
                isActive={activeQubeId === qube.qube_id && currentTab === 'dashboard'}
                onClick={(e) => handleQubeClick(qube.qube_id, e)}
              />
            );
          })
        )}
      </div>

    </div>
  );
};
