import { useState, useMemo, useEffect } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { Qube } from '../../types';
import { useQubeSelection } from '../../hooks/useQubeSelection';
import { useAuth } from '../../hooks/useAuth';
import { GlassCard, GlassButton } from '../glass';
import { QubeManagerTab } from './QubeManagerTab';
import { CreateQubeModal, CreateQubeData } from './CreateQubeModal';
import { ChatInterface } from '../chat/ChatInterface';
import { MultiQubeChatInterface } from '../chat/MultiQubeChatInterface';
import { BlocksTab } from './BlocksTab';
import { RelationshipsTab } from './RelationshipsTab';
import { SkillsTab } from './SkillsTab';
import { GamesTab } from './GamesTab';
import { SettingsTab } from './SettingsTab';
import { Connection } from '../connections';

type ChatMode = 'local' | 'p2p';

// Stable empty array to avoid infinite loops with Zustand selectors
const EMPTY_ARRAY: string[] = [];

interface TabContentProps {
  qubes: Qube[];
  setQubes: React.Dispatch<React.SetStateAction<Qube[]>>;
  onQubesChange: () => void;
}

export const TabContent: React.FC<TabContentProps> = ({ qubes, setQubes, onQubesChange }) => {
  const currentTab = useQubeSelection((state) => state.currentTab);
  const { userId, password } = useAuth();
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [qubeToDelete, setQubeToDelete] = useState<Qube | null>(null);
  const [chatMode, setChatMode] = useState<ChatMode>('local');

  // P2P mode state
  const [p2pConnections, setP2pConnections] = useState<Connection[]>([]);

  // Get selection for current tab
  const selectedQubeIds = useQubeSelection((state) => state.selectionByTab[state.currentTab] ?? EMPTY_ARRAY);

  // Get Dashboard selection specifically (for chat interfaces that should persist)
  const dashboardSelection = useQubeSelection((state) => state.selectionByTab['dashboard'] ?? EMPTY_ARRAY);

  // Fetch connections when P2P mode is selected
  useEffect(() => {
    const fetchConnections = async () => {
      if (chatMode !== 'p2p' || !userId || qubes.length === 0) return;

      // Get connections from first selected qube (or first qube)
      const primaryQube = qubes.find(q => dashboardSelection.includes(q.qube_id)) || qubes[0];
      if (!primaryQube) return;

      try {
        const result = await invoke<{ success: boolean; connections?: Connection[]; error?: string }>(
          'get_connections',
          { userId, qubeId: primaryQube.qube_id }
        );

        if (result.success && result.connections) {
          setP2pConnections(result.connections);
        }
      } catch (err) {
        console.error('Failed to fetch connections:', err);
      }
    };

    fetchConnections();
  }, [chatMode, userId, qubes, dashboardSelection]);

  const handleCreateQube = async (data: CreateQubeData) => {
    await invoke('create_qube', {
      userId,
      name: data.name,
      genesisPrompt: data.genesisPrompt,
      aiProvider: data.aiProvider,
      aiModel: data.aiModel,
      voiceModel: data.voiceModel,
      walletAddress: data.walletAddress,
      password: password,
      encryptGenesis: data.encryptGenesis || false,
      favoriteColor: data.favoriteColor,
      avatarFile: data.avatarFile || null,
      generateAvatar: data.generateAvatar || false,
      avatarStyle: data.avatarStyle || null,
    });
    await onQubesChange();
  };

  const handleEditQube = (qube: Qube) => {
    console.log('Edit qube:', qube);
    // TODO: Open edit modal
  };

  const handleDeleteQube = (qube: Qube) => {
    // Show confirmation dialog
    setQubeToDelete(qube);
  };

  const confirmDelete = async () => {
    if (!qubeToDelete) return;

    try {
      const result = await invoke<{ success: boolean; error?: string }>('delete_qube', {
        userId,
        qubeId: qubeToDelete.qube_id,
      });

      if (result.success) {
        console.log('Qube deleted successfully:', qubeToDelete.qube_id);
        setQubeToDelete(null);
        await onQubesChange(); // Refresh the qube list
      } else {
        console.error('Failed to delete qube:', result.error);
        alert(`Failed to delete qube: ${result.error}`);
      }
    } catch (err) {
      console.error('Error deleting qube:', err);
      alert(`Error deleting qube: ${String(err)}`);
    }
  };

  const cancelDelete = () => {
    setQubeToDelete(null);
  };

  const handleUpdateQubeConfig = async (qubeId: string, updates: { ai_model?: string; voice_model?: string; favorite_color?: string; tts_enabled?: boolean; evaluation_model?: string }) => {
    await invoke('update_qube_config', {
      userId,
      qubeId,
      aiModel: updates.ai_model,
      voiceModel: updates.voice_model,
      favoriteColor: updates.favorite_color,
      ttsEnabled: updates.tts_enabled,
      evaluationModel: updates.evaluation_model,
    });

    // Update local state instead of reloading all qubes
    setQubes(prevQubes => prevQubes.map(q => {
      if (q.qube_id === qubeId) {
        return {
          ...q,
          ...(updates.ai_model && { ai_model: updates.ai_model }),
          ...(updates.voice_model && { voice_model: updates.voice_model }),
          ...(updates.favorite_color && { favorite_color: updates.favorite_color }),
          ...(updates.tts_enabled !== undefined && { tts_enabled: updates.tts_enabled }),
          ...(updates.evaluation_model && { evaluation_model: updates.evaluation_model as any }),
        };
      }
      return q;
    }));
  };

  // Keep all tabs mounted but show/hide with CSS to preserve state
  // Use useMemo to prevent unnecessary re-renders when selectedQubes array reference changes
  // Dashboard chat uses dashboard selection (persists even when on other tabs)
  const selectedQubesForDashboard = useMemo(
    () => qubes.filter(q => dashboardSelection.includes(q.qube_id)),
    [qubes, dashboardSelection]
  );

  // Blocks tab uses current tab's selection
  const selectedQubesForBlocks = useMemo(
    () => qubes.filter(q => selectedQubeIds.includes(q.qube_id)),
    [qubes, selectedQubeIds]
  );

  return (
    <>
      <div className="flex-1 relative">
        {/* Dashboard Tab - Chat Interface */}
        <div
          className={`absolute inset-0 flex flex-col overflow-y-auto ${
            currentTab === 'dashboard' ? 'z-10 opacity-100' : 'z-0 opacity-0 pointer-events-none'
          }`}
        >
          {/* Mode Toggle - Local vs P2P */}
          <div className="flex items-center justify-center gap-2 py-3 bg-bg-secondary/50 border-b border-glass-border">
            <span className="text-text-secondary text-sm mr-2">Chat Mode:</span>
            <button
              onClick={() => setChatMode('local')}
              className={`px-4 py-1.5 rounded-l-lg text-sm font-medium transition-all ${
                chatMode === 'local'
                  ? 'bg-accent-primary text-bg-primary'
                  : 'bg-glass-bg text-text-secondary hover:text-text-primary border border-glass-border'
              }`}
            >
              Local
            </button>
            <button
              onClick={() => setChatMode('p2p')}
              className={`px-4 py-1.5 rounded-r-lg text-sm font-medium transition-all ${
                chatMode === 'p2p'
                  ? 'bg-accent-secondary text-bg-primary'
                  : 'bg-glass-bg text-text-secondary hover:text-text-primary border border-glass-border'
              }`}
            >
              P2P Network
            </button>
          </div>

          {/* Local Chat Mode */}
          <div className={`relative flex-1 ${chatMode === 'local' ? 'block' : 'hidden'}`}>
            {/* Keep both chat interfaces mounted to preserve state */}
            {/* Use opacity and z-index for visibility to avoid display:none issues */}
            {/* Chat interfaces always use Dashboard selection, not current tab */}
            <div className="absolute inset-0">
              <div className={`absolute inset-0 p-6 flex flex-col ${selectedQubesForDashboard.length >= 2 ? 'z-10 opacity-100' : 'z-0 opacity-0 pointer-events-none'}`}>
                <MultiQubeChatInterface key="multi-qube-chat" selectedQubes={selectedQubesForDashboard} />
              </div>
              <div className={`absolute inset-0 p-6 flex flex-col ${selectedQubesForDashboard.length >= 2 ? 'z-0 opacity-0 pointer-events-none' : 'z-10 opacity-100'}`}>
                <ChatInterface key="single-qube-chat" selectedQubes={selectedQubesForDashboard} />
              </div>
            </div>
          </div>

          {/* P2P Chat Mode - Uses same MultiQubeChatInterface with mode='p2p' */}
          <div className={`relative flex-1 ${chatMode === 'p2p' ? 'block' : 'hidden'}`}>
            <div className="absolute inset-0 p-6 flex flex-col">
              <MultiQubeChatInterface
                key="p2p-multi-qube-chat"
                selectedQubes={selectedQubesForDashboard}
                mode="p2p"
                allQubes={qubes}
                connections={p2pConnections}
              />
            </div>
          </div>
        </div>

        {/* Blocks Tab */}
        <div
          className={`absolute inset-0 overflow-hidden ${
            currentTab === 'blocks' ? 'z-10 opacity-100' : 'z-0 opacity-0 pointer-events-none'
          }`}
        >
          <BlocksTab
            selectedQubes={selectedQubesForBlocks}
            userId={userId || ''}
            password={password || ''}
          />
        </div>

        {/* Qubes Tab */}
        <div
          className={`absolute inset-0 overflow-y-auto ${
            currentTab === 'qubes' ? 'z-10 opacity-100' : 'z-0 opacity-0 pointer-events-none'
          }`}
        >
          <QubeManagerTab
            qubes={qubes}
            onCreateQube={() => setIsCreateModalOpen(true)}
            onEditQube={handleEditQube}
            onDeleteQube={handleDeleteQube}
            onUpdateQubeConfig={handleUpdateQubeConfig}
          />
          <CreateQubeModal
            isOpen={isCreateModalOpen}
            onClose={() => setIsCreateModalOpen(false)}
            onCreate={handleCreateQube}
            onQubesChange={onQubesChange}
          />
        </div>

        {/* Relationships Tab */}
        <div
          className={`absolute inset-0 overflow-hidden ${
            currentTab === 'relationships' ? 'z-10 opacity-100' : 'z-0 opacity-0 pointer-events-none'
          }`}
        >
          <RelationshipsTab qubes={qubes} />
        </div>

        {/* Skills Tab */}
        <div
          className={`absolute inset-0 overflow-hidden ${
            currentTab === 'skills' ? 'z-10 opacity-100' : 'z-0 opacity-0 pointer-events-none'
          }`}
        >
          <SkillsTab qubes={qubes} />
        </div>

        {/* Games Tab */}
        <div
          className={`absolute inset-0 overflow-hidden ${
            currentTab === 'games' ? 'z-10 opacity-100' : 'z-0 opacity-0 pointer-events-none'
          }`}
        >
          <GamesTab qubes={qubes} />
        </div>

        {/* Earnings Tab */}
        <div
          className={`absolute inset-0 overflow-y-auto ${
            currentTab === 'economy' ? 'z-10 opacity-100' : 'z-0 opacity-0 pointer-events-none'
          }`}
        >
          <div className="p-6">
            <GlassCard className="p-6">
              <p className="text-text-secondary mb-4">
                Cost tracking and metrics will go here
              </p>
              {selectedQubeIds.length > 0 ? (
                <div>
                  <p className="text-text-primary">
                    Showing costs for {selectedQubeIds.length} qube(s)
                  </p>
                  <p className="text-sm text-text-tertiary mt-2">
                    Multi-select: <span className="text-accent-success">Enabled</span>
                  </p>
                </div>
              ) : (
                <p className="text-text-tertiary">
                  Showing aggregate costs for all qubes
                </p>
              )}
            </GlassCard>
          </div>
        </div>

        {/* Settings Tab */}
        <div
          className={`absolute inset-0 overflow-y-auto ${
            currentTab === 'settings' ? 'z-10 opacity-100' : 'z-0 opacity-0 pointer-events-none'
          }`}
        >
          <SettingsTab />
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {qubeToDelete && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50">
          <GlassCard className="p-6 max-w-md mx-4">
            <h2 className="text-xl font-display text-accent-danger mb-4">
              ⚠️ Delete Qube?
            </h2>

            <p className="text-text-primary mb-6">
              Are you sure you want to delete <span className="font-bold text-accent-danger">{qubeToDelete.name}</span>?
              This will permanently delete all of its data, including memory blocks, relationships, and cryptographic keys.
              This action cannot be undone.
            </p>

            <div className="flex gap-3 justify-end">
              <GlassButton
                variant="secondary"
                onClick={cancelDelete}
              >
                Cancel
              </GlassButton>

              <GlassButton
                variant="danger"
                onClick={confirmDelete}
              >
                Delete Qube
              </GlassButton>
            </div>
          </GlassCard>
        </div>
      )}
    </>
  );
};
