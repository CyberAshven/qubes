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
    connections: null,
    games: null
  },
  selectionByTab: {
    dashboard: [],
    blocks: [],
    qubes: [],
    relationships: [],
    skills: [],
    economy: [],
    settings: [],
    connections: [],
    games: []
  },
  currentTab: 'qubes',

  setActiveQube: (id: string) => {
    const { currentTab, activeQubeByTab } = get();
    set({ activeQubeByTab: { ...activeQubeByTab, [currentTab]: id } });
  },

  setCurrentTab: (tab: Tab) => {
    // Simply switch tabs - each tab maintains its own independent selection
    set({ currentTab: tab });
  },

  getSelectedQubeIds: () => {
    const { currentTab, selectionByTab } = get();
    return selectionByTab[currentTab] || [];
  },

  toggleSelection: (id: string, isCtrl: boolean, isShift: boolean) => {
    const { currentTab, selectionByTab } = get();
    const selectedQubeIds = selectionByTab[currentTab] || [];
    const isMultiAllowed = get().isMultiSelectAllowed();
    const isAlreadySelected = selectedQubeIds.includes(id);

    if (!isMultiAllowed) {
      // Single-select mode: toggle if already selected, otherwise select
      const { activeQubeByTab } = get();
      if (isAlreadySelected) {
        // Deselect
        set({
          selectionByTab: { ...selectionByTab, [currentTab]: [] },
          activeQubeByTab: { ...activeQubeByTab, [currentTab]: null }
        });
      } else {
        // Select
        set({
          selectionByTab: { ...selectionByTab, [currentTab]: [id] },
          activeQubeByTab: { ...activeQubeByTab, [currentTab]: id }
        });
      }
      return;
    }

    // Multi-select mode
    if (isCtrl) {
      // Toggle selection
      if (isAlreadySelected) {
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
      if (!isAlreadySelected) {
        set({
          selectionByTab: {
            ...selectionByTab,
            [currentTab]: [...selectedQubeIds, id]
          }
        });
      }
    } else {
      // Regular click in multi-select mode: if already selected, deselect; otherwise single-select
      const { activeQubeByTab } = get();
      if (isAlreadySelected && selectedQubeIds.length === 1) {
        // Only item selected, deselect it
        set({
          selectionByTab: { ...selectionByTab, [currentTab]: [] },
          activeQubeByTab: { ...activeQubeByTab, [currentTab]: null }
        });
      } else {
        // Select only this one (replacing any multi-selection)
        set({
          selectionByTab: { ...selectionByTab, [currentTab]: [id] },
          activeQubeByTab: { ...activeQubeByTab, [currentTab]: id }
        });
      }
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
    // Only Chat tab (id='dashboard', for group chat) and Games tab (for multi-player) allow multi-select
    return currentTab === 'dashboard' || currentTab === 'games';
  },
}));
