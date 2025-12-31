import { create } from 'zustand';
import { Tab } from '../types';

interface QubeSelectionStore {
  // Per-tab active qube (for pulsing glow)
  activeQubeByTab: Record<Tab, string | null>;
  // Per-tab selection state
  selectionByTab: Record<Tab, string[]>;
  currentTab: Tab;

  setActiveQube: (id: string) => void;
  setCurrentTab: (tab: Tab) => void;
  toggleSelection: (id: string, isCtrl: boolean, isShift: boolean) => void;
  clearSelection: () => void;

  // Get selected IDs for current tab
  getSelectedQubeIds: () => string[];

  // Helper to check if multi-select is allowed for current tab
  isMultiSelectAllowed: () => boolean;
}

export const useQubeSelection = create<QubeSelectionStore>((set, get) => ({
  activeQubeByTab: {
    dashboard: null,
    blocks: null,
    qubes: null,
    relationships: null,
    skills: null,
    economy: null,
    settings: null,
    connections: null
  },
  selectionByTab: {
    dashboard: [],
    blocks: [],
    qubes: [],
    relationships: [],
    skills: [],
    economy: [],
    settings: [],
    connections: []
  },
  currentTab: 'qubes',

  setActiveQube: (id: string) => {
    const { currentTab, activeQubeByTab } = get();
    set({ activeQubeByTab: { ...activeQubeByTab, [currentTab]: id } });
  },

  setCurrentTab: (tab: Tab) => {
    set({ currentTab: tab });
    // Tab switching no longer modifies selection - each tab has its own selection state
  },

  getSelectedQubeIds: () => {
    const { currentTab, selectionByTab } = get();
    return selectionByTab[currentTab] || [];
  },

  toggleSelection: (id: string, isCtrl: boolean, isShift: boolean) => {
    const { currentTab, selectionByTab } = get();
    const selectedQubeIds = selectionByTab[currentTab] || [];
    const isMultiAllowed = get().isMultiSelectAllowed();

    if (!isMultiAllowed) {
      // Single-select mode: always replace
      const { activeQubeByTab } = get();
      set({
        selectionByTab: { ...selectionByTab, [currentTab]: [id] },
        activeQubeByTab: { ...activeQubeByTab, [currentTab]: id }
      });
      return;
    }

    // Multi-select mode
    if (isCtrl) {
      // Toggle selection
      if (selectedQubeIds.includes(id)) {
        set({
          selectionByTab: {
            ...selectionByTab,
            [currentTab]: selectedQubeIds.filter(qid => qid !== id)
          }
        });
      } else {
        set({
          selectionByTab: {
            ...selectionByTab,
            [currentTab]: [...selectedQubeIds, id]
          }
        });
      }
    } else if (isShift && selectedQubeIds.length > 0) {
      // Range selection (would need qube list for proper implementation)
      // For now, just add to selection
      if (!selectedQubeIds.includes(id)) {
        set({
          selectionByTab: {
            ...selectionByTab,
            [currentTab]: [...selectedQubeIds, id]
          }
        });
      }
    } else {
      // Regular click: single selection
      const { activeQubeByTab } = get();
      set({
        selectionByTab: { ...selectionByTab, [currentTab]: [id] },
        activeQubeByTab: { ...activeQubeByTab, [currentTab]: id }
      });
    }
  },

  clearSelection: () => {
    const { currentTab, selectionByTab, activeQubeByTab } = get();
    set({
      selectionByTab: { ...selectionByTab, [currentTab]: [] },
      activeQubeByTab: { ...activeQubeByTab, [currentTab]: null }
    });
  },

  isMultiSelectAllowed: () => {
    const { currentTab } = get();
    return currentTab === 'dashboard' || currentTab === 'economy';
  },
}));
