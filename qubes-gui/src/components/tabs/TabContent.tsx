import { useState, useMemo, useEffect } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { Qube } from '../../types';
import { useQubeSelection } from '../../hooks/useQubeSelection';
import { useAuth } from '../../hooks/useAuth';
import { useChatMessages } from '../../hooks/useChatMessages';
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
import { EarningsTab } from './EarningsTab';
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
  const [deleteConfirmPassword, setDeleteConfirmPassword] = useState('');

  // P2P mode state
  const [p2pConnections, setP2pConnections] = useState<Connection[]>([]);

  // Get selection for current tab
  const selectedQubeIds = useQubeSelection((state) => state.selectionByTab[state.currentTab] ?? EMPTY_ARRAY);
  const toggleSelection = useQubeSelection((state) => state.toggleSelection);

  // Get Dashboard selection specifically (for chat interfaces that should persist)
  const dashboardSelection = useQubeSelection((state) => state.selectionByTab['dashboard'] ?? EMPTY_ARRAY);

  // Get Blocks selection specifically (for BlocksTab to persist across tab switches)
  const blocksSelection = useQubeSelection((state) => state.selectionByTab['blocks'] ?? EMPTY_ARRAY);

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

  // Chat messages for "Recall Last" feature
  const { addMessage } = useChatMessages();
  // Subscribe to the actual messages map to detect changes
  const messagesByQube = useChatMessages(state => state.messagesByQube);

  // Get the single selected qube for local chat (when only 1 is selected)
  const singleSelectedQube = useMemo(() => {
    if (dashboardSelection.length === 1) {
      return qubes.find(q => q.qube_id === dashboardSelection[0]);
    }
    return null;
  }, [dashboardSelection, qubes]);

  // Check if chat is empty for the selected qube (subscribes to message changes)
  const isChatEmpty = useMemo(() => {
    if (!singleSelectedQube) return false;
    const messages = messagesByQube.get(singleSelectedQube.qube_id) || [];
    return messages.length === 0;
  }, [singleSelectedQube, messagesByQube]);

  // State for recall loading
  const [isRecalling, setIsRecalling] = useState(false);

  // Handle "Recall Last" button click
  const handleRecallLast = async () => {
    if (!singleSelectedQube || !userId || !password) return;

    setIsRecalling(true);
    try {
      const result = await invoke<{
        success: boolean;
        content?: string;
        block_type?: string;
        block_number?: number;
        timestamp?: number;
        error?: string;
      }>('recall_last_context', {
        userId,
        qubeId: singleSelectedQube.qube_id,
        password,
      });

      if (result.success && result.content) {
        // Add the recalled message to the chat as a qube message
        addMessage(singleSelectedQube.qube_id, {
          id: `recalled-${Date.now()}`,
          sender: 'qube',
          qubeName: singleSelectedQube.name,
          content: result.block_type === 'SUMMARY'
            ? `📋 *Last session summary:*\n\n${result.content}`
            : result.content,
          timestamp: new Date(result.timestamp || Date.now()),
        });
      }
    } catch (err) {
      console.error('Failed to recall last context:', err);
    } finally {
      setIsRecalling(false);
    }
  };

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

  const handleEditQube = (_qube: Qube) => {
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
        setQubeToDelete(null);
        setDeleteConfirmPassword('');
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
    setDeleteConfirmPassword('');
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

  // Handle model change from chat (e.g., Qube used switch_model tool or revolver mode)
  const handleQubeModelChange = (qubeId: string, newModel: string) => {
    setQubes(prevQubes => prevQubes.map(q => {
      if (q.qube_id === qubeId && q.ai_model !== newModel) {
        console.log(`Model changed for ${q.name}: ${q.ai_model} → ${newModel}`);
        return { ...q, ai_model: newModel };
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

  // Blocks tab uses its own selection (persists across tab switches)
  const selectedQubesForBlocks = useMemo(
    () => qubes.filter(q => blocksSelection.includes(q.qube_id)),
    [qubes, blocksSelection]
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
          <div className="flex items-center justify-between py-3 px-4 bg-bg-secondary/50 border-b border-glass-border">
            <div>{/* Spacer for centering */}</div>
            <div className="flex items-center gap-2">
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
            {/* Recall Last button - only visible when chat is empty and single qube selected in Local mode */}
            <div className="min-w-[100px] flex justify-end">
              {chatMode === 'local' && isChatEmpty && singleSelectedQube && (
                <button
                  onClick={handleRecallLast}
                  disabled={isRecalling}
                  className="px-3 py-1.5 text-sm font-medium text-accent-primary hover:text-accent-primary/80
                             bg-accent-primary/10 hover:bg-accent-primary/20 border border-accent-primary/30
                             rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                  title="Load the most recent message or summary into the chat"
                >
                  {isRecalling ? 'Loading...' : 'Recall Last'}
                </button>
              )}
            </div>
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
                <ChatInterface key="single-qube-chat" selectedQubes={selectedQubesForDashboard} onQubeModelChange={handleQubeModelChange} />
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
            isActive={currentTab === 'blocks'}
            onQubesChange={onQubesChange}
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
          <EarningsTab
            qubes={qubes}
            selectedQubeIds={selectedQubeIds}
            onQubeSelect={(qubeId) => toggleSelection(qubeId, false, false)}
          />
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

            <p className="text-text-primary mb-4">
              Are you sure you want to delete <span className="font-bold text-accent-danger">{qubeToDelete.name}</span>?
              This will permanently delete all of its data, including memory blocks, relationships, and cryptographic keys.
              This action cannot be undone.
            </p>

            <div className="mb-6">
              <label className="text-sm text-text-secondary block mb-2">
                Enter your master password to confirm:
              </label>
              <input
                type="password"
                value={deleteConfirmPassword}
                onChange={(e) => setDeleteConfirmPassword(e.target.value)}
                placeholder="Master password"
                className="w-full bg-bg-primary border border-glass-border rounded-lg px-3 py-2 text-text-primary placeholder:text-text-disabled focus:outline-none focus:border-accent-danger"
                autoFocus
              />
            </div>

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
                disabled={deleteConfirmPassword !== password}
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
