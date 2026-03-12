import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { convertFileSrc } from '@tauri-apps/api/core';
import { GlassCard } from '../glass/GlassCard';
import { GlassButton } from '../glass/GlassButton';
import { Qube } from '../../types';
import { useAuth } from '../../hooks/useAuth';
import { useAudio } from '../../contexts/AudioContext';
import { TypewriterText } from './TypewriterText';
import { ToolCallBubble } from './ToolCallBubble';
import { useChatMessages } from '../../hooks/useChatMessages';
import EmojiPicker, { EmojiClickData, Theme } from 'emoji-picker-react';
import { Connection } from '../connections';

// P2P remote participant info
interface RemoteParticipant {
  commitment: string;
  name: string;
  public_key?: string | null;
}

interface MultiQubeChatInterfaceProps {
  selectedQubes: Qube[];
  // P2P mode props
  mode?: 'local' | 'p2p';
  allQubes?: Qube[];  // All user's qubes (to detect local "remote" connections)
  connections?: Connection[];  // Available connections for P2P
  hubSessionId?: string;  // Pre-created hub session ID
  onSessionCreated?: (sessionId: string) => void;  // Callback when session is created
}

interface ConversationMessage {
  speaker_id: string;
  speaker_name: string;
  message: string;
  voice_model: string;
  turn_number: number;
  conversation_id: string;
  is_final: boolean;
  timestamp?: number;
  block_number?: number; // Block number for reliable tool call matching
  // Who will speak next (for UI to show immediately)
  next_speaker_id?: string;
  next_speaker_name?: string;
}

interface ConversationSummary {
  conversation_id: string;
  total_turns: number;
  participants: Array<{
    qube_id: string;
    name: string;
    turns_taken: number;
  }>;
  conversation_history: Array<{
    speaker_id: string;
    speaker_name: string;
    message: string;
    turn_number: number;
    timestamp: string;
  }>;
  anchored: boolean;
}

// Per-qube pipeline state for prefetch
interface QubePipeline {
  qubeId: string;
  qubeName: string;
  status: 'idle' | 'processing' | 'generating_tts' | 'ready';
  pendingResponse: ConversationMessage | null;
  prefetchedAudio: string | null;
}

export const MultiQubeChatInterface: React.FC<MultiQubeChatInterfaceProps> = ({
  selectedQubes,
  mode = 'local',
  allQubes = [],
  connections = [],
  hubSessionId,
  onSessionCreated,
}) => {
  const { userId, password } = useAuth();
  const { playTTS, prefetchTTS, playPrefetchedTTS, audioElement } = useAudio();

  // P2P mode state
  const isP2P = mode === 'p2p';
  const [p2pSessionId, setP2pSessionId] = useState<string | null>(hubSessionId || null);
  const [selectedConnections, setSelectedConnections] = useState<string[]>([]);
  const [wsConnected, setWsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const handleWsMessageRef = useRef<((data: any) => void) | null>(null);

  const [conversationId, setConversationId] = useState<string | null>(null);
  const [conversationHistory, setConversationHistory] = useState<ConversationMessage[]>([]);
  const [actionBlocks, setActionBlocks] = useState<Array<{
    qube_id: string;
    action_type: string;
    timestamp: number;
    parameters: any;
    result: any;
    status: string;
  }>>([]);

  // PERMANENT mapping of actions to the message index they appear before
  // Key: action unique ID (qube_id-timestamp-action_type)
  // Value: { action, messageIndex } - once assigned, NEVER removed
  const [actionAssignments, setActionAssignments] = useState<Map<string, {
    action: typeof actionBlocks[0];
    messageIndex: number;
  }>>(new Map());

  // Ref to always have current action blocks (for async callbacks)
  const actionBlocksRef = useRef(actionBlocks);
  useEffect(() => {
    actionBlocksRef.current = actionBlocks;
  }, [actionBlocks]);

  // Assign new actions to messages (runs whenever actionBlocks or conversationHistory changes)
  // Once assigned to a VALID message (index >= 0), an action NEVER moves or disappears
  // Actions assigned to -1 (trailing) can be reassigned when their message arrives
  useEffect(() => {
    if (actionBlocks.length === 0) return;

    setActionAssignments(currentAssignments => {
      const newAssignments = new Map(currentAssignments);
      let hasChanges = false;

      actionBlocks.forEach(action => {
        const actionKey = `${action.qube_id}-${action.timestamp}-${action.action_type}`;
        const existing = newAssignments.get(actionKey);

        // If already assigned to a valid message (>= 0), just update action data
        if (existing && existing.messageIndex >= 0) {
          if (existing.action.status !== action.status || existing.action.result !== action.result) {
            newAssignments.set(actionKey, { ...existing, action });
            hasChanges = true;
          }
          return;
        }

        // Find which message this action belongs before (by timestamp)
        let assignedIndex = -1;
        for (let i = 0; i < conversationHistory.length; i++) {
          const msg = conversationHistory[i];
          const msgTimestamp = msg.timestamp || 0;

          // Action belongs before this message if action.timestamp <= msgTimestamp
          // and message is from a qube (not user)
          if (msg.speaker_id !== userId && action.timestamp <= msgTimestamp) {
            // Check it's after the previous non-user message
            let prevNonUserTimestamp = 0;
            for (let j = i - 1; j >= 0; j--) {
              if (conversationHistory[j].speaker_id !== userId) {
                prevNonUserTimestamp = conversationHistory[j].timestamp || 0;
                break;
              }
            }

            if (action.timestamp > prevNonUserTimestamp) {
              assignedIndex = i;
              break;
            }
          }
        }

        // Only update if different from current assignment (or new)
        if (!existing || existing.messageIndex !== assignedIndex) {
          newAssignments.set(actionKey, { action, messageIndex: assignedIndex });
          hasChanges = true;
          console.log(`[ACTION ASSIGN] ${action.action_type} assigned to messageIndex=${assignedIndex}`);
        }
      });

      return hasChanges ? newAssignments : currentAssignments;
    });
  }, [actionBlocks, conversationHistory, userId]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conversationMode, setConversationMode] = useState<'open_discussion' | 'round_robin'>('open_discussion');
  const [activeTypewriterMessageId, setActiveTypewriterMessageId] = useState<string | null>(null);
  const [pendingTTSMessage, setPendingTTSMessage] = useState<ConversationMessage | null>(null);
  const [isConversationActive, setIsConversationActive] = useState(false);
  const [expectedTurns, setExpectedTurns] = useState(1); // How many turns each Qube should take initially

  // User message injection state
  const [pendingUserMessage, setPendingUserMessage] = useState<{
    message: string;
    userMessageResponse?: ConversationMessage;
    qubeResponse?: ConversationMessage;
  } | null>(null);

  // Next response status indicator
  const [nextResponseStatus, setNextResponseStatus] = useState<{
    stage: 'idle' | 'processing' | 'generating_tts' | 'ready';
    qubeId?: string;
    qubeName?: string;
  }>({ stage: 'idle' });

  // Per-qube pipeline state for prefetch
  const [qubePipelines, setQubePipelines] = useState<Map<string, QubePipeline>>(new Map());
  const [currentSpeakerId, setCurrentSpeakerId] = useState<string | null>(null);
  const [nextSpeakerId, setNextSpeakerId] = useState<string | null>(null);

  const [isPauseRequested, setIsPauseRequested] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [showEmojiPicker, setShowEmojiPicker] = useState(false);

  // Use chat messages hook for file uploads (using first selected qube as key for group chat)
  const { getUploadedFiles, addUploadedFile, removeUploadedFile, clearUploadedFiles } = useChatMessages();
  const uploadedFiles = selectedQubes.length > 0 ? getUploadedFiles(`group_${selectedQubes.map(q => q.qube_id).join('_')}`) : [];

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const emojiPickerRef = useRef<HTMLDivElement>(null);
  const recognitionRef = useRef<any>(null);
  const shouldContinueRef = useRef(false);
  const isFetchingNextRef = useRef(false);
  const processingMessageRef = useRef<string | null>(null); // Track which message is being processed
  const lastProcessedTurnRef = useRef<number>(0); // Track the last turn number we processed
  const activeTypewriterMessageIdRef = useRef<string | null>(null); // Track active typewriter
  const waitingForUserResponseRef = useRef(false); // Track if we're waiting for user's response from backend
  const pauseAfterCurrentMessageRef = useRef(false); // Track if we should pause after current message completes

  // Keep refs in sync with state
  useEffect(() => {
    activeTypewriterMessageIdRef.current = activeTypewriterMessageId;
  }, [activeTypewriterMessageId]);

  // ========== PIPELINE HELPERS ==========

  // Update a single qube's pipeline state
  const updatePipeline = useCallback((qubeId: string, updates: Partial<QubePipeline>) => {
    setQubePipelines(prev => {
      const newMap = new Map(prev);
      const current = newMap.get(qubeId) || {
        qubeId,
        qubeName: selectedQubes.find(q => q.qube_id === qubeId)?.name || 'Unknown',
        status: 'idle' as const,
        pendingResponse: null,
        prefetchedAudio: null,
      };
      newMap.set(qubeId, { ...current, ...updates });
      return newMap;
    });
  }, [selectedQubes]);

  // Get pipeline for a qube
  const getPipeline = useCallback((qubeId: string): QubePipeline | undefined => {
    return qubePipelines.get(qubeId);
  }, [qubePipelines]);

  // Clear all pipelines (on conversation end)
  const clearAllPipelines = useCallback(() => {
    setQubePipelines(new Map());
    setCurrentSpeakerId(null);
    setNextSpeakerId(null);
  }, []);

  // ========== P2P MODE HELPERS ==========

  // Get local qube IDs for P2P backend
  const getLocalQubeIds = useCallback(() => {
    return selectedQubes.map(q => q.qube_id).join(',');
  }, [selectedQubes]);

  // Get remote connections JSON for P2P backend
  const getRemoteConnectionsJson = useCallback(() => {
    const localCommitments = selectedQubes.map(q => q.commitment || '');
    const remoteConns = selectedConnections
      .filter(c => !localCommitments.includes(c))
      .map(commitment => {
        const conn = connections.find(c => c.commitment === commitment);
        return {
          commitment,
          name: conn?.name || 'Unknown',
          public_key: conn?.public_key || null,
        };
      });
    return JSON.stringify(remoteConns);
  }, [selectedQubes, selectedConnections, connections]);

  // Connect to P2P WebSocket
  const connectP2PWebSocket = useCallback((sessionId: string) => {
    if (wsRef.current) {
      wsRef.current.close();
    }

    const primaryCommitment = selectedQubes[0]?.commitment;
    const ws = new WebSocket(`wss://qube.cash/api/v2/conversation/ws/${sessionId}`);

    ws.onopen = () => {
      ws.send(JSON.stringify({
        type: 'auth',
        commitment: primaryCommitment,
        signature: ''
      }));
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (handleWsMessageRef.current) {
          handleWsMessageRef.current(data);
        }
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    };

    ws.onclose = () => {
      setWsConnected(false);
    };

    ws.onerror = (err) => {
      console.error('P2P WebSocket error:', err);
    };

    wsRef.current = ws;
  }, [selectedQubes]);

  // Handle P2P WebSocket messages
  const handleP2PWebSocketMessage = useCallback(async (data: any) => {
    switch (data.type) {
      case 'auth_success':
        setWsConnected(true);
        break;

      case 'auth_failed':
        console.error('P2P WebSocket auth failed:', data.error);
        break;

      case 'new_block':
      case 'block_finalized':
        // Remote block received - inject into local conversation
        const block = data.block;
        const blockCreatorCommitment = block.creator_commitment;

        // Skip if from our local Qubes (we already have it)
        const localCommitments = selectedQubes.map(q => q.commitment);
        if (localCommitments.includes(blockCreatorCommitment)) {
          break;
        }

        // Inject remote block via backend
        if (conversationId && p2pSessionId && userId && password) {
          try {
            await invoke('inject_p2p_block', {
              userId,
              conversationId,
              sessionId: p2pSessionId,
              blockData: JSON.stringify(block),
              fromCommitment: blockCreatorCommitment,
              localQubes: getLocalQubeIds(),
              remoteConnections: getRemoteConnectionsJson(),
              password,
            });

            // Add to display
            const remoteMessage: ConversationMessage = {
              speaker_id: blockCreatorCommitment,
              speaker_name: block.creator_name || 'Remote',
              message: block.content?.content || '',
              voice_model: '',
              turn_number: block.block_number || 0,
              conversation_id: conversationId,
              is_final: true,
              timestamp: block.timestamp,
            };
            setConversationHistory(prev => [...prev, remoteMessage]);

            // Continue conversation if active
            if (isConversationActive && shouldContinueRef.current) {
              continueConversation();
            }
          } catch (err) {
            console.error('Failed to inject remote block:', err);
          }
        }
        break;
    }
  }, [selectedQubes, conversationId, p2pSessionId, userId, password, getLocalQubeIds, getRemoteConnectionsJson]);

  // Keep WS message handler ref updated
  useEffect(() => {
    handleWsMessageRef.current = handleP2PWebSocketMessage;
  }, [handleP2PWebSocketMessage]);

  // Cleanup WebSocket on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  // Submit block to hub for P2P distribution
  const submitBlockToHub = useCallback(async (response: ConversationMessage) => {
    if (!p2pSessionId || !isP2P) return;

    try {
      await fetch(`https://qube.cash/api/v2/conversation/sessions/${p2pSessionId}/blocks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: p2pSessionId,
          creator_commitment: response.speaker_id,
          block_type: 'MESSAGE',
          content: { role: 'assistant', content: response.message },
          content_hash: '',
          creator_signature: '',
          timestamp: Math.floor(response.timestamp || Date.now() / 1000),
        }),
      });
    } catch (err) {
      console.error('Failed to submit block to hub:', err);
    }
  }, [p2pSessionId, isP2P]);

  // Toggle connection selection (P2P mode)
  const toggleConnection = (commitment: string) => {
    setSelectedConnections(prev =>
      prev.includes(commitment)
        ? prev.filter(c => c !== commitment)
        : [...prev, commitment]
    );
  };

  // ========== END P2P MODE HELPERS ==========

  // Load ACTION blocks only (messages come from conversationHistory)
  // Uses merge logic to ensure actions are never removed once shown
  const prevConversationIdRef = useRef<string | null>(null);

  useEffect(() => {
    const loadActionBlocks = async () => {
      if (!userId || !password || selectedQubes.length === 0) {
        setActionBlocks([]);
        return;
      }

      // Check if this is a NEW conversation (clear old actions and assignments)
      const isNewConversation = conversationId !== prevConversationIdRef.current;
      if (isNewConversation) {
        prevConversationIdRef.current = conversationId;
        // Clear actions and assignments immediately for new conversation
        setActionBlocks([]);
        setActionAssignments(new Map());
      }

      try {
        // Fetch all actions from backend
        const newActions: Array<{
          qube_id: string;
          action_type: string;
          timestamp: number;
          parameters: any;
          result: any;
          status: string;
        }> = [];

        for (const qube of selectedQubes) {
          const result = await invoke<any>('get_qube_blocks', {
            userId,
            qubeId: qube.qube_id,
            password
          });

          const sessionBlocks = result.session_blocks || [];
          sessionBlocks
            .filter((b: any) => b.block_type === 'ACTION')
            .forEach((b: any) => {
              // Normalize timestamp to SECONDS (block files use seconds, but some might be in ms)
              let ts = b.timestamp;
              if (ts > 10000000000) {
                // If > 10 billion, it's in milliseconds - convert to seconds
                ts = Math.floor(ts / 1000);
              }
              newActions.push({
                qube_id: qube.qube_id,
                action_type: b.content?.action_type || 'unknown',
                timestamp: ts,
                parameters: b.content?.parameters || {},
                result: b.content?.result || null,
                status: b.content?.status || 'completed',
              });
            });
        }

        // Use functional update to MERGE with current state (never lose existing actions)
        setActionBlocks(currentActions => {
          // If new conversation, start fresh with just the fetched actions
          if (isNewConversation) {
            const sorted = [...newActions].sort((a, b) => a.timestamp - b.timestamp);
            console.log('[ACTION LOAD] New conversation, loaded', sorted.length, 'action blocks');
            return sorted;
          }

          // Otherwise merge: preserve existing, add/update new
          const actionMap = new Map<string, typeof currentActions[0]>();

          currentActions.forEach(action => {
            const key = `${action.qube_id}-${action.timestamp}-${action.action_type}`;
            actionMap.set(key, action);
          });

          newActions.forEach(action => {
            const key = `${action.qube_id}-${action.timestamp}-${action.action_type}`;
            actionMap.set(key, action);
          });

          const mergedActions = Array.from(actionMap.values());
          mergedActions.sort((a, b) => a.timestamp - b.timestamp);
          console.log('[ACTION LOAD] Merged to', mergedActions.length, 'action blocks');
          return mergedActions;
        });
      } catch (err) {
        // On error, keep existing actions - don't clear them
        console.error('Failed to load action blocks:', err);
      }
    };

    loadActionBlocks();
  }, [userId, password, selectedQubes, conversationId, conversationHistory.length]);

  // Poll for ACTION blocks while conversation is active
  // Also poll during isLoading (backend processing) even if conversation not "active" yet
  useEffect(() => {
    if (!userId || !password || selectedQubes.length === 0) {
      return;
    }

    // Poll if conversation is active OR if we're loading (AI processing)
    // This ensures ACTION blocks appear in real-time during tool calls
    if (!isConversationActive && !isLoading) {
      return;
    }

    const loadAllActionBlocks = async () => {
      // Fetch new actions from backend
      const newActions: Array<{
        qube_id: string;
        action_type: string;
        timestamp: number;
        parameters: any;
        result: any;
        status: string;
      }> = [];

      for (const qube of selectedQubes) {
        try {
          const result = await invoke<any>('get_qube_blocks', {
            userId,
            qubeId: qube.qube_id,
            password,
            limit: 50
          });

          const sessionBlocks = result.session_blocks || [];

          sessionBlocks
            .filter((b: any) => b.block_type === 'ACTION')
            .forEach((b: any) => {
              // Normalize timestamp to SECONDS
              let ts = b.timestamp;
              if (ts > 10000000000) {
                ts = Math.floor(ts / 1000);
              }
              newActions.push({
                qube_id: qube.qube_id,
                action_type: b.content?.action_type || 'unknown',
                timestamp: ts,
                parameters: b.content?.parameters || {},
                result: b.content?.result || null,
                status: b.content?.status || 'completed',
              });
            });
        } catch (err) {
          // On error, keep existing actions - don't clear them
          console.error(`Failed to load blocks for ${qube.name}:`, err);
        }
      }

      // Use functional update to MERGE with current state (never lose existing actions)
      setActionBlocks(currentActions => {
        const actionMap = new Map<string, typeof currentActions[0]>();

        // First, preserve ALL existing actions
        currentActions.forEach(action => {
          const key = `${action.qube_id}-${action.timestamp}-${action.action_type}`;
          actionMap.set(key, action);
        });

        // Then merge in new/updated actions
        newActions.forEach(action => {
          const key = `${action.qube_id}-${action.timestamp}-${action.action_type}`;
          actionMap.set(key, action);
        });

        // Convert map back to sorted array
        const mergedActions = Array.from(actionMap.values());
        mergedActions.sort((a, b) => a.timestamp - b.timestamp);
        return mergedActions;
      });
    };

    // Load immediately
    loadAllActionBlocks();

    // Poll frequently (500ms) to catch new actions quickly
    const pollInterval = setInterval(loadAllActionBlocks, 500);

    return () => clearInterval(pollInterval);
  }, [isConversationActive, isLoading, userId, password, selectedQubes]);

  // Scroll to bottom helper
  const scrollToBottom = (smooth: boolean = true) => {
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollTo({
        top: scrollContainerRef.current.scrollHeight,
        behavior: smooth ? 'smooth' : 'auto'
      });
    }
  };

  // Handle file upload
  const handleFileUpload = async () => {
    if (selectedQubes.length === 0) return;

    try {
      const result = await invoke<string[] | null>('select_file');

      if (result && result.length > 0) {
        const filePath = result[0];
        const fileName = filePath.split(/[\\/]/).pop() || 'unknown';

        // Read file content
        const content = await invoke<string>('read_file_content', { filePath });

        const fileData = {
          name: fileName,
          path: filePath,
          data: content,
          type: 'text' as const
        };

        // Add to group chat's uploaded files
        addUploadedFile(`group_${selectedQubes.map(q => q.qube_id).join('_')}`, fileData);
      }
    } catch (err) {
      console.error('Failed to upload file:', err);
      setError(`Failed to upload file: ${String(err)}`);
    }
  };

  // Handle emoji picker
  const handleEmojiClick = (emojiData: EmojiClickData) => {
    const emoji = emojiData.emoji;
    const textarea = textareaRef.current;

    if (textarea) {
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      const text = inputValue;
      const before = text.substring(0, start);
      const after = text.substring(end);
      const newText = before + emoji + after;

      setInputValue(newText);

      // Set cursor position after emoji
      setTimeout(() => {
        textarea.selectionStart = textarea.selectionEnd = start + emoji.length;
        textarea.focus();
      }, 0);
    } else {
      setInputValue(inputValue + emoji);
    }
  };

  // Handle audio recording
  const handleStartRecording = () => {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
      setError('Speech recognition is not supported in this browser. Please use Chrome or Edge.');
      return;
    }

    const SpeechRecognition = (window as any).webkitSpeechRecognition || (window as any).SpeechRecognition;
    const recognition = new SpeechRecognition();

    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
      setIsRecording(true);
      setError(null);
    };

    recognition.onresult = (event: any) => {
      let transcript = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        if (event.results[i].isFinal) {
          transcript += event.results[i][0].transcript;
        }
      }
      if (transcript) {
        setInputValue(prev => prev + (prev ? ' ' : '') + transcript);
      }
    };

    recognition.onerror = (event: any) => {
      console.error('Speech recognition error:', event.error);
      setError(`Speech recognition error: ${event.error}`);
      setIsRecording(false);
    };

    recognition.onend = () => {
      setIsRecording(false);
    };

    recognitionRef.current = recognition;
    recognition.start();
  };

  const handleStopRecording = () => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      recognitionRef.current = null;
    }
    setIsRecording(false);
  };

  // Close emoji picker when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (emojiPickerRef.current && !emojiPickerRef.current.contains(event.target as Node)) {
        setShowEmojiPicker(false);
      }
    };

    if (showEmojiPicker) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => {
        document.removeEventListener('mousedown', handleClickOutside);
      };
    }
  }, [showEmojiPicker]);

  // Helper function to save an image to disk
  const saveImageToDisk = async (imageUrl: string, speakerId: string) => {
    if (!userId) return;

    try {
      await invoke('save_image', {
        userId: userId,
        qubeId: speakerId,
        imageUrl: imageUrl
      });
    } catch (err) {
      console.error('Failed to save image:', err);
      // Don't show error to user - saving is optional background task
    }
  };

  // Helper function to convert local file path to asset:// URL for Tauri
  const convertToAssetUrl = (path: string): string => {
    // Normalize backslashes to forward slashes
    let normalizedPath = path.replace(/\\/g, '/');

    // Handle relative paths (legacy - new images use absolute paths)
    if (normalizedPath.startsWith('data/')) {
      // For relative paths, resolve to absolute
      normalizedPath = `C:/Users/bit_f/Projects/Qubes/${normalizedPath}`;
    }

    // URL encode the path components (but keep forward slashes and colon for drive letter)
    const encodedPath = normalizedPath
      .split('/')
      .map((segment, index) => {
        // Don't encode the drive letter part (e.g., "C:")
        if (index === 0 && segment.match(/^[A-Za-z]:$/)) {
          return segment;
        }
        return encodeURIComponent(segment);
      })
      .join('/');

    // Format: http://asset.localhost/{path}
    const assetUrl = `http://asset.localhost/${encodedPath}`;
    return assetUrl;
  };

  // Helper function to clean content by removing image URLs and thinking blocks
  const cleanContentForDisplay = (content: string): string => {
    // Remove [Thinking: ...] blocks from models like Kimi K2
    // These can span multiple lines, so use [\s\S] to match any character including newlines
    let cleaned = content.replace(/\[Thinking:[\s\S]*?\]/gi, '');

    // Remove Gemini 3's internal thinking/planning blocks
    // Look for end-of-thinking markers and take content after them
    const endMarkers = [
      "*Let's do this.*",
      "*Let's do this*",
      "*Let's roll.*",
      "*Let's roll*",
      "*Here's my response:*",
      "*Here's my response*",
      "*Response:*",
      "*Responding now:*",
      "*Final response:*",
      "my response:",
    ];

    for (const marker of endMarkers) {
      const markerLower = marker.toLowerCase();
      const cleanedLower = cleaned.toLowerCase();
      if (cleanedLower.includes(markerLower)) {
        const idx = cleanedLower.indexOf(markerLower);
        cleaned = cleaned.substring(idx + marker.length).trim();
        break;
      }
    }

    // If content starts with planning patterns, try to find the actual response
    const trimmedLower = cleaned.trim().toLowerCase();
    if (trimmedLower.startsWith('my plan:') ||
        trimmedLower.startsWith('my thought process') ||
        trimmedLower.startsWith('plan:')) {
      // Look for common response starters after planning
      const lines = cleaned.split('\n');
      let responseStart = 0;

      for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim().toLowerCase();
        // Skip planning-related lines
        if (line.startsWith('my plan:') ||
            line.startsWith('my thought') ||
            line.startsWith('plan:') ||
            line.startsWith('*self-correction') ||
            line.startsWith('*refining') ||
            line.startsWith('*let') ||
            line.startsWith('**key response') ||
            line.match(/^\d+\.\s+\*\*/) ||  // Numbered bold items
            line.startsWith('- ') ||
            (line.startsWith('*') && line.endsWith('*'))) {
          continue;
        }
        // Found a line that looks like actual response
        if (line.length > 20 && !line.includes('should') && !line.includes('will ') && !line.includes('need to')) {
          responseStart = i;
          break;
        }
        // Common response starters
        if (line.startsWith('whoa') || line.startsWith('okay') || line.startsWith('hey') ||
            line.startsWith('so,') || line.startsWith('oh') || line.startsWith('hmm') ||
            line.startsWith('well') || line.startsWith('alright')) {
          responseStart = i;
          break;
        }
      }

      if (responseStart > 0) {
        cleaned = lines.slice(responseStart).join('\n').trim();
      }
    }

    // Regular expression to detect image URLs (including DALL-E Azure Blob Storage URLs)
    const imageUrlRegex = /(https?:\/\/[^\s\)]+?(?:\.(?:png|jpg|jpeg|gif|webp)|blob\.core\.windows\.net\/[^\s\)]+))/gi;
    // Regular expression to detect local Windows file paths to images (both absolute and relative)
    const localPathRegex = /([A-Za-z]:\\[^\s\)]+\.(?:png|jpg|jpeg|gif|webp)|data[\\\/][^\s\)]+\.(?:png|jpg|jpeg|gif|webp))/gi;

    // Remove complete markdown image syntax ![...](url)
    cleaned = cleaned.replace(/!\[([^\]]*)\]\([^\)]+\)/gi, '');

    // Remove any remaining image URLs (standalone)
    cleaned = cleaned.replace(imageUrlRegex, '');

    // Remove any local file paths
    cleaned = cleaned.replace(localPathRegex, '');

    // Remove any standalone markdown image syntax ![...]
    cleaned = cleaned.replace(/!\[([^\]]*)\]/g, '');

    // Remove empty parentheses that might be left over
    cleaned = cleaned.replace(/\(\s*\)/g, '');

    return cleaned.trim();
  };

  // Helper function to truncate text for TTS
  // OpenAI TTS has a hard limit of 4096 characters, so keep it safe at 4000
  const truncateForTTS = (text: string, maxLength: number = 4000): string => {
    // First, shorten long hexadecimal strings (BCH addresses, transaction IDs, etc.)
    // Pattern: Any hex string longer than 20 characters
    let processedText = text.replace(/\b([a-fA-F0-9]{20,})\b/g, (match) => {
      // Keep first 8 and last 8 characters
      return `${match.substring(0, 8)}...${match.substring(match.length - 8)}`;
    });

    // Also handle BCH addresses that start with specific prefixes
    processedText = processedText.replace(/\b(bitcoincash:[a-z0-9]{20,})\b/gi, (match) => {
      const parts = match.split(':');
      if (parts.length === 2 && parts[1].length > 20) {
        return `${parts[0]}:${parts[1].substring(0, 8)}...${parts[1].substring(parts[1].length - 8)}`;
      }
      return match;
    });

    // Now check overall length and truncate if needed
    if (processedText.length <= maxLength) {
      return processedText;
    }

    // Truncate at word boundary (silent truncation - no suffix)
    const truncated = processedText.substring(0, maxLength);
    const lastSpace = truncated.lastIndexOf(' ');
    return truncated.substring(0, lastSpace);
  };

  // Helper function to detect and render images in message content
  const renderMessageContent = (content: string, speakerId: string) => {
    // Regular expression to detect image URLs (including DALL-E Azure Blob Storage URLs)
    const imageUrlRegex = /(https?:\/\/[^\s\)]+?(?:\.(?:png|jpg|jpeg|gif|webp)|blob\.core\.windows\.net\/[^\s\)]+))/gi;
    // Regular expression to detect local Windows file paths to images (both absolute and relative)
    const localPathRegex = /([A-Za-z]:\\[^\s\)]+\.(?:png|jpg|jpeg|gif|webp)|data[\\\/][^\s\)]+\.(?:png|jpg|jpeg|gif|webp))/gi;
    // Regular expression to detect any URLs
    const anyUrlRegex = /(https?:\/\/[^\s\)]+)/gi;

    // Extract all image URLs first
    const imageUrls = content.match(imageUrlRegex) || [];

    // Extract local file paths and convert to asset:// URLs
    const localPaths = content.match(localPathRegex) || [];
    const localAssetUrls = localPaths.map(convertToAssetUrl);

    // Combine remote URLs and local asset URLs
    const allImageUrls = [...imageUrls, ...localAssetUrls];

    // Get cleaned text content (without image URLs)
    let textContent = cleanContentForDisplay(content);

    // Replace remaining URLs with truncated clickable links
    const textParts = textContent.split(anyUrlRegex);
    const renderedText = textParts.map((part, index) => {
      if (part.match(anyUrlRegex)) {
        // Truncate URL for display (show first 40 chars + ...)
        const displayUrl = part.length > 40 ? part.substring(0, 40) + '...' : part;
        return (
          <a
            key={`link-${index}`}
            href={part}
            target="_blank"
            rel="noopener noreferrer"
            className="text-accent-primary underline hover:text-accent-primary/80"
          >
            {displayUrl}
          </a>
        );
      }
      return <span key={`text-${index}`}>{part}</span>;
    });

    // Return images FIRST, then text content
    return (
      <>
        {allImageUrls.map((url, index) => (
          <img
            key={`img-${index}`}
            src={url}
            alt="Generated image"
            className="max-w-full rounded-lg mb-3 block"
            style={{ maxHeight: '400px', objectFit: 'contain' }}
            onLoad={() => {
              // Only save remote URLs to disk (local paths are already saved)
              if (url.startsWith('http')) {
                saveImageToDisk(url, speakerId);
              }
              // Scroll when image finishes loading
              scrollToBottom();
            }}
            onError={(e) => {
              // Fallback if image fails to load - show truncated URL instead
              const target = e.target as HTMLImageElement;
              target.style.display = 'none';
              const fallback = document.createElement('a');
              fallback.href = url;
              fallback.target = '_blank';
              fallback.className = 'text-accent-primary underline';
              const displayUrl = url.length > 60 ? url.substring(0, 60) + '...' : url;
              fallback.textContent = `[Image failed to load: ${displayUrl}]`;
              target.parentNode?.insertBefore(fallback, target);
            }}
          />
        ))}
        {renderedText}
      </>
    );
  };

  // Auto-scroll when messages change
  useEffect(() => {
    scrollToBottom();
  }, [conversationHistory.length, isLoading]);

  // Also scroll when typewriter completes
  useEffect(() => {
    if (!activeTypewriterMessageId) {
      // Small delay to allow final layout adjustment
      setTimeout(scrollToBottom, 100);
    }
  }, [activeTypewriterMessageId]);

  // Smooth auto-scroll while content is being added
  useEffect(() => {
    const timer = setInterval(() => {
      if ((activeTypewriterMessageId || isLoading) && scrollContainerRef.current) {
        const container = scrollContainerRef.current;
        // Only scroll if we're not already at the bottom
        const isAtBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 50;
        if (!isAtBottom) {
          scrollToBottom();
        }
      }
    }, 300); // Reduced frequency for smoother experience
    return () => clearInterval(timer);
  }, [activeTypewriterMessageId, isLoading]);

  // Construct avatar path from chain folder
  const getAvatarPath = (qube: Qube): string => {
    // Priority 1: IPFS URL from backend
    if (qube.avatar_url) return qube.avatar_url;

    // Priority 2: Local file path via Tauri convertFileSrc
    if (qube.avatar_local_path) {
      return convertFileSrc(qube.avatar_local_path);
    }

    // Priority 3: Construct path from qube info (fallback for older qubes)
    const projectRoot = 'C:/Users/bit_f/Projects/Qubes';
    const filePath = `${projectRoot}/data/users/${userId}/qubes/${qube.name}_${qube.qube_id}/chain/${qube.qube_id}_avatar.png`;
    return convertFileSrc(filePath);
  };

  // Get qube by ID (also checks connections for P2P mode)
  const getQubeById = (qubeId: string): Qube | undefined => {
    // First check selected qubes
    const qube = selectedQubes.find(q => q.qube_id === qubeId);
    if (qube) return qube;

    // In P2P mode, also check allQubes (might be a local "remote" connection)
    if (isP2P && allQubes.length > 0) {
      const allQube = allQubes.find(q => q.qube_id === qubeId || q.commitment === qubeId);
      if (allQube) return allQube;
    }

    return undefined;
  };

  // Run background turns for non-speaking qubes
  // They can use tools or PASS while the current speaker's TTS plays
  const runBackgroundTurns = async (excludeIds: string[]) => {
    if (!conversationId || !isConversationActive) return;

    try {
      // Check if there are eligible qubes (not excluded)
      const eligible = selectedQubes.filter(q => !excludeIds.includes(q.qube_id));
      if (eligible.length === 0) return;

      // Run background turns on backend (no UI tracking for now)
      await invoke<{
        conversation_id: string;
        turn_number: number;
        background_results: Record<string, {
          passed: boolean;
          tool_used?: string;
          error?: string;
        }>;
      }>('run_background_turns', {
        userId,
        conversationId,
        excludeQubeIds: JSON.stringify(excludeIds),
        password,
      });
    } catch (err) {
      console.error('Background turns failed:', err);
    }
  };

  // Get participant display info (works for qubes and connections)
  interface ParticipantInfo {
    name: string;
    color: string;
    avatarUrl?: string;
    commitment?: string;
    isConnection: boolean;
  }

  const getParticipantInfo = (speakerId: string): ParticipantInfo | undefined => {
    // Check selected qubes first
    const qube = selectedQubes.find(q => q.qube_id === speakerId || q.commitment === speakerId);
    if (qube) {
      return {
        name: qube.name,
        color: qube.favorite_color || '#00d4ff',
        avatarUrl: qube.avatar_url || qube.avatar_local_path,
        commitment: qube.commitment,
        isConnection: false,
      };
    }

    // Check allQubes (for local "remote" connections in P2P)
    if (isP2P && allQubes.length > 0) {
      const allQube = allQubes.find(q => q.qube_id === speakerId || q.commitment === speakerId);
      if (allQube) {
        return {
          name: allQube.name,
          color: allQube.favorite_color || '#00d4ff',
          avatarUrl: allQube.avatar_url || allQube.avatar_local_path,
          commitment: allQube.commitment,
          isConnection: true,
        };
      }
    }

    // Check connections (for remote participants)
    if (isP2P) {
      const conn = connections.find(c => c.commitment === speakerId);
      if (conn) {
        return {
          name: conn.name,
          color: '#9945FF', // Default purple for remote connections
          commitment: conn.commitment,
          isConnection: true,
        };
      }
    }

    return undefined;
  };

  // Continue the conversation automatically (get next turn)
  const continueConversation = async () => {
    if (!conversationId || !userId || !password || !isConversationActive) return;

    // Prevent concurrent fetches (both regular and prefetch)
    if (isFetchingNextRef.current) {
      return;
    }

    isFetchingNextRef.current = true;

    // Show "processing" indicator (we don't know who will respond yet)
    setNextResponseStatus({
      stage: 'processing',
      qubeId: undefined,
      qubeName: undefined
    });

    try {
      let response: ConversationMessage;

      if (isP2P && p2pSessionId) {
        // P2P mode - use P2P backend command
        const result = await invoke<{
          success: boolean;
          response?: ConversationMessage;
          error?: string;
        }>('continue_p2p_conversation', {
          userId,
          conversationId,
          sessionId: p2pSessionId,
          localQubes: getLocalQubeIds(),
          remoteConnections: getRemoteConnectionsJson(),
          password,
        });

        if (!result.success || !result.response) {
          throw new Error(result.error || 'No response from P2P conversation');
        }
        response = result.response;

        // Submit to hub for remote participants
        await submitBlockToHub(response);
      } else {
        // Local mode - use standard backend command
        // Pass participant_ids for optimization (skips scanning all qubes)
        const participantIds = selectedQubes.map(q => q.qube_id);
        response = await invoke<ConversationMessage>('continue_multi_qube_conversation', {
          userId,
          conversationId,
          password,
          participant_ids: JSON.stringify(participantIds),
        });
      }

      // Set next speaker hint if available
      if (response.next_speaker_id) {
        setNextSpeakerId(response.next_speaker_id);
      }

      // Play TTS for this response (will be added to history when TTS starts)
      setPendingTTSMessage(response);
    } catch (err) {
      console.error('Failed to continue conversation:', err);
      setError(`Failed to continue conversation: ${String(err)}`);
      setIsLoading(false);
      setIsConversationActive(false);
    } finally {
      isFetchingNextRef.current = false;
    }
  };

  // Start prefetch for next speaker in the background (using pipeline architecture)
  const startPipelinePrefetch = async (forQubeId: string) => {
    if (!conversationId || !userId || !password || !isConversationActive) return;

    // Already fetching or this pipeline is already active?
    const existingPipeline = qubePipelines.get(forQubeId);
    if (existingPipeline && existingPipeline.status !== 'idle') {
      console.log(`[Prefetch] Qube ${forQubeId} already active (${existingPipeline.status}), skipping`);
      return;
    }

    // Prevent concurrent fetches
    if (isFetchingNextRef.current) {
      console.log('[Prefetch] Another fetch in progress, skipping');
      return;
    }

    console.log(`[Prefetch] Starting for qube ${forQubeId}`);
    isFetchingNextRef.current = true;

    // Show generic "processing" status (don't show predicted speaker name - might be wrong)
    setNextResponseStatus({
      stage: 'processing',
      qubeId: undefined,
      qubeName: undefined
    });

    try {
      // Fetch next response
      const participantIds = selectedQubes.map(q => q.qube_id);
      const response = await invoke<ConversationMessage>('continue_multi_qube_conversation', {
        userId,
        conversationId,
        password,
        participant_ids: JSON.stringify(participantIds),
      });

      if (!response) {
        console.log(`[Prefetch] No response for qube ${forQubeId}`);
        updatePipeline(forQubeId, { status: 'idle' });
        setNextResponseStatus({ stage: 'idle' });
        isFetchingNextRef.current = false;
        return;
      }

      // If actual speaker differs from predicted, clear the wrong pipeline entry
      if (response.speaker_id !== forQubeId) {
        console.log(`[Prefetch] Actual speaker ${response.speaker_id} differs from predicted ${forQubeId}`);
        updatePipeline(forQubeId, { status: 'idle', pendingResponse: null, prefetchedAudio: null });
      }

      // Update nextSpeakerId to the ACTUAL speaker
      setNextSpeakerId(response.speaker_id);

      // Check if TTS should be generated BEFORE setting status
      const qube = selectedQubes.find(q => q.qube_id === response.speaker_id);
      const shouldGenerateTTS = qube && qube.tts_enabled === true && qube.voice_model;

      console.log(`[Prefetch] TTS check for ${response.speaker_name}: qube=${!!qube}, tts_enabled=${qube?.tts_enabled}, voice_model=${qube?.voice_model}, shouldGenerate=${shouldGenerateTTS}`);

      if (shouldGenerateTTS && qube) {
        // Store response in pipeline - generating TTS
        updatePipeline(response.speaker_id, {
          status: 'generating_tts',
          pendingResponse: response,
          qubeName: response.speaker_name,
        });

        setNextResponseStatus({
          stage: 'generating_tts',
          qubeId: response.speaker_id,
          qubeName: response.speaker_name
        });

        try {
          const cleanedMessage = truncateForTTS(cleanContentForDisplay(response.message));
          console.log(`[Prefetch] Starting TTS for ${response.speaker_name} (${qube.voice_model})...`);
          const ttsStartTime = Date.now();
          const audioUrl = await prefetchTTS(userId, qube.qube_id, cleanedMessage, password);
          console.log(`[Prefetch] TTS completed in ${Date.now() - ttsStartTime}ms for ${response.speaker_name}`);

          // Mark pipeline as ready
          updatePipeline(response.speaker_id, {
            status: 'ready',
            prefetchedAudio: audioUrl,
          });

          setNextResponseStatus({
            stage: 'ready',
            qubeId: response.speaker_id,
            qubeName: response.speaker_name
          });

          console.log(`[Prefetch] Qube ${response.speaker_id} ready with TTS`);
        } catch (ttsErr) {
          console.error('[Prefetch] TTS error:', ttsErr);
          // Still mark as ready even without TTS - it will generate inline
          updatePipeline(response.speaker_id, { status: 'ready', pendingResponse: response });
          setNextResponseStatus({
            stage: 'ready',
            qubeId: response.speaker_id,
            qubeName: response.speaker_name
          });
        }
      } else {
        // No TTS needed - mark as ready immediately
        console.log(`[Prefetch] Skipping TTS for ${response.speaker_name} (no voice model or TTS disabled)`);
        updatePipeline(response.speaker_id, {
          status: 'ready',
          pendingResponse: response,
          qubeName: response.speaker_name,
        });
        setNextResponseStatus({
          stage: 'ready',
          qubeId: response.speaker_id,
          qubeName: response.speaker_name
        });
      }

      // Update next speaker hint
      if (response.next_speaker_id) {
        setNextSpeakerId(response.next_speaker_id);
      }

    } catch (err) {
      console.error('[Prefetch] Error:', err);
      updatePipeline(forQubeId, { status: 'idle' });
      setNextResponseStatus({ stage: 'idle' });
    } finally {
      isFetchingNextRef.current = false;
    }
  };

  // Start a new conversation
  const handleStartConversation = async () => {
    // P2P mode: allow single qube + connections. Local mode: require 2+ qubes
    const minQubes = isP2P ? 1 : 2;
    if ((!inputValue.trim() && uploadedFiles.length === 0) || selectedQubes.length < minQubes || !userId || !password) {
      return;
    }

    // P2P requires connections selected OR multiple local qubes
    if (isP2P && selectedConnections.length === 0 && selectedQubes.length < 2) {
      setError('Please select at least one connection or another local Qube');
      return;
    }

    if (!isP2P && selectedQubes.length < 2) {
      setError('Please select at least 2 Qubes for a group conversation');
      return;
    }

    // Build message with file content if any
    let userPrompt = inputValue;
    const filesToProcess = [...uploadedFiles];

    if (filesToProcess.length > 0) {
      let fileContent = '';
      for (const file of filesToProcess) {
        fileContent += `\n\n---FILE: ${file.name}---\n${file.data}\n---END FILE---\n`;
      }
      userPrompt = (inputValue ? inputValue + '\n' : '') + fileContent;
    }

    // Show user's message immediately (with temporary conversation ID)
    const tempUserMessage: ConversationMessage = {
      speaker_id: userId,
      speaker_name: 'You',
      message: userPrompt,
      voice_model: '',
      turn_number: 0,
      conversation_id: 'pending', // Will be updated when response arrives
      is_final: false,
      timestamp: Math.floor(Date.now() / 1000), // Seconds
    };

    setConversationHistory([tempUserMessage]);
    setInputValue(''); // Clear input immediately
    setIsLoading(true);
    setError(null);
    setIsConversationActive(true);
    shouldContinueRef.current = true;

    // Don't predict first speaker - in "open_discussion" mode it's random
    // Just show generic "processing" until backend returns who spoke
    setNextResponseStatus({
      stage: 'processing',
      qubeId: undefined,
      qubeName: undefined
    });

    try {
      const qubeIds = selectedQubes.map(q => q.qube_id).join(',');

      if (isP2P) {
        // P2P MODE: Create hub session, connect WS, start P2P conversation

        // Step 1: Create hub session if not already created
        let sessionId = p2pSessionId;
        if (!sessionId) {
          const sessionResult = await invoke<{
            success: boolean;
            session_id?: string;
            error?: string;
          }>('create_p2p_session', {
            userId,
            qubeId: selectedQubes[0].qube_id,
            localQubes: qubeIds,
            remoteCommitments: selectedConnections.join(','),
            topic: '',
            password,
          });

          if (!sessionResult.success || !sessionResult.session_id) {
            throw new Error(sessionResult.error || 'Failed to create P2P session');
          }

          sessionId = sessionResult.session_id;
          setP2pSessionId(sessionId);
          onSessionCreated?.(sessionId);

          // Connect WebSocket
          connectP2PWebSocket(sessionId);
        }

        // Step 2: Start P2P conversation
        const result = await invoke<{
          success: boolean;
          conversation_id?: string;
          response?: ConversationMessage;
          error?: string;
        }>('start_p2p_conversation', {
          userId,
          localQubes: qubeIds,
          remoteConnections: getRemoteConnectionsJson(),
          sessionId,
          initialPrompt: userPrompt,
          password,
        });

        if (!result.success) {
          throw new Error(result.error || 'Failed to start P2P conversation');
        }

        setConversationId(result.conversation_id || null);

        // Update user's message with real conversation ID
        const userMessage: ConversationMessage = {
          speaker_id: userId,
          speaker_name: 'You',
          message: userPrompt,
          voice_model: '',
          turn_number: 0,
          conversation_id: result.conversation_id || '',
          is_final: false,
          timestamp: Math.floor(Date.now() / 1000), // Seconds
        };

        setConversationHistory([userMessage]);
        clearUploadedFiles(`group_${selectedQubes.map(q => q.qube_id).join('_')}`);

        // Play TTS for first response
        if (result.response) {
          // Submit first response to hub
          await submitBlockToHub(result.response);
          // Set next speaker hint
          if (result.response.next_speaker_id) {
            setNextSpeakerId(result.response.next_speaker_id);
          }
          setPendingTTSMessage(result.response);
        }
      } else {
        // LOCAL MODE: Standard multi-qube conversation
        console.log('LOCAL MODE: Starting conversation with:', qubeIds);
        const response = await invoke<{
          conversation_id: string;
          participants: Array<{ qube_id: string; name: string }>;
          first_response: ConversationMessage;
        }>('start_multi_qube_conversation', {
          userId,
          qubeIdsStr: qubeIds,
          initialPrompt: userPrompt,
          password,
          conversationMode,
        });

        console.log('Got response:', response);
        console.log('Got response (JSON):', JSON.stringify(response, null, 2));
        console.log('first_response:', response.first_response);
        console.log('conversation_id:', response.conversation_id);
        // Check if this is actually an error response
        if ((response as any).error) {
          console.error('Backend error:', (response as any).error);
          console.error('Backend traceback:', (response as any).traceback);
          throw new Error((response as any).error);
        }
        setConversationId(response.conversation_id);

        // Update user's message with real conversation ID
        const userMessage: ConversationMessage = {
          speaker_id: userId,
          speaker_name: 'You',
          message: userPrompt,
          voice_model: '',
          turn_number: 0,
          conversation_id: response.conversation_id,
          is_final: false,
          timestamp: Math.floor(Date.now() / 1000), // Seconds
        };

        console.log('Setting conversationHistory to:', [userMessage]);
        setConversationHistory([userMessage]);

        // Clear uploaded files after starting conversation
        clearUploadedFiles(`group_${selectedQubes.map(q => q.qube_id).join('_')}`);

        // Play TTS for first response (will be added to history when TTS starts)
        console.log('Setting pendingTTSMessage to:', response.first_response);
        if (!response.first_response) {
          console.error('ERROR: first_response is missing from backend response!');
        }
        // Set next speaker hint
        if (response.first_response?.next_speaker_id) {
          setNextSpeakerId(response.first_response.next_speaker_id);
        }
        setPendingTTSMessage(response.first_response);
      }
    } catch (err) {
      console.error('Failed to start conversation:', err);
      setError(`Failed to start conversation: ${String(err)}`);
      setIsLoading(false);
      setIsConversationActive(false);
      // Clear the temporary message on error
      setConversationHistory([]);
    }
  };

  // Inject user message into active conversation (IMMEDIATE - NO WAITING)
  const handleInjectUserMessage = () => {
    if ((!inputValue.trim() && uploadedFiles.length === 0) || !conversationId || !userId || !password) {
      return;
    }

    // Build message with file content if any
    let userMessage = inputValue;
    const filesToProcess = [...uploadedFiles];

    if (filesToProcess.length > 0) {
      let fileContent = '';
      for (const file of filesToProcess) {
        fileContent += `\n\n---FILE: ${file.name}---\n${file.data}\n---END FILE---\n`;
      }
      userMessage = (inputValue ? inputValue + '\n' : '') + fileContent;
    }

    // Clear input and files IMMEDIATELY
    setInputValue('');
    clearUploadedFiles(`group_${selectedQubes.map(q => q.qube_id).join('_')}`);
    setError(null);

    // Clear all pipelines - user injection invalidates any prefetched responses
    clearAllPipelines();
    isFetchingNextRef.current = false;

    // Set waiting flag to prevent auto-continue from fetching next turn
    waitingForUserResponseRef.current = true;

    // Show "User processing" indicator
    setNextResponseStatus({
      stage: 'processing',
      qubeId: userId,
      qubeName: 'You'
    });

    // Show "User ready to respond" indicator
    setPendingUserMessage({
      message: userMessage
    });

    // Invoke backend IMMEDIATELY (don't wait for TTS/typewriter)
    // This runs in the background while current Qube finishes speaking
    (async () => {
      try {
        let response: { user_message: ConversationMessage; qube_response: ConversationMessage };

        if (isP2P && p2pSessionId) {
          // P2P mode - use P2P backend command
          const result = await invoke<{
            success: boolean;
            user_message?: ConversationMessage;
            qube_response?: ConversationMessage;
            error?: string;
          }>('send_p2p_user_message', {
            userId,
            conversationId,
            sessionId: p2pSessionId,
            message: userMessage,
            localQubes: getLocalQubeIds(),
            remoteConnections: getRemoteConnectionsJson(),
            password,
          });

          if (!result.success || !result.user_message || !result.qube_response) {
            throw new Error(result.error || 'Failed to send P2P user message');
          }

          response = {
            user_message: result.user_message,
            qube_response: result.qube_response,
          };

          // Submit qube response to hub for remote participants
          await submitBlockToHub(result.qube_response);
        } else {
          // Local mode - use standard backend command
          response = await invoke<{
            user_message: ConversationMessage;
            qube_response: ConversationMessage;
          }>('inject_multi_qube_user_message', {
            userId,
            conversationId,
            message: userMessage,
            password,
          });
        }

        // Store the responses (don't display yet - wait for speaker to finish)
        // Don't change status here - keep showing "user response ready"
        setPendingUserMessage({
          message: userMessage,
          userMessageResponse: response.user_message,
          qubeResponse: response.qube_response
        });

      } catch (err) {
        console.error('Failed to inject user message:', err);
        setError(`Failed to send message: ${String(err)}`);
        setPendingUserMessage(null);
        waitingForUserResponseRef.current = false;
      }
    })();
  };

  // Pause the conversation
  const handlePauseConversation = () => {
    // Check if there's a prefetched response ready in a pipeline
    const nextPipeline = nextSpeakerId ? qubePipelines.get(nextSpeakerId) : null;

    if (nextPipeline?.status === 'ready' && nextPipeline.pendingResponse) {
      // Set flags to pause after the prefetched message plays
      pauseAfterCurrentMessageRef.current = true;
      setIsPauseRequested(true); // Visual feedback
      shouldContinueRef.current = false;
      isFetchingNextRef.current = false;

      // If no message is currently playing, trigger the prefetched response now
      if (!pendingTTSMessage && !activeTypewriterMessageId) {
        setPendingTTSMessage(nextPipeline.pendingResponse);
        updatePipeline(nextSpeakerId!, { status: 'idle', pendingResponse: null, prefetchedAudio: null });
      }
      // else: Let auto-continue handle it after current message finishes
    } else {
      // No prefetched response ready - pause immediately
      setIsConversationActive(false);
      shouldContinueRef.current = false;
      isFetchingNextRef.current = false;
      pauseAfterCurrentMessageRef.current = false;
      setIsPauseRequested(false);

      // Clear all pipelines
      clearAllPipelines();
      setNextResponseStatus({ stage: 'idle' });
    }
  };

  // Resume the conversation
  const handleResumeConversation = () => {
    setIsConversationActive(true);
    shouldContinueRef.current = true;
    pauseAfterCurrentMessageRef.current = false; // Clear any pending pause
    setIsPauseRequested(false); // Clear pause requested state

    // Trigger next turn
    if (conversationId && !isLoading && !pendingTTSMessage) {
      // Check if there's a prefetched response ready in a pipeline
      const nextPipeline = nextSpeakerId ? qubePipelines.get(nextSpeakerId) : null;

      if (nextPipeline?.status === 'ready' && nextPipeline.pendingResponse) {
        setPendingTTSMessage(nextPipeline.pendingResponse);
        updatePipeline(nextSpeakerId!, { status: 'idle', pendingResponse: null, prefetchedAudio: null });
      } else {
        continueConversation();
      }
    }
  };

  // End the conversation
  const handleEndConversation = async (anchor: boolean = true) => {
    if (!conversationId || !userId || !password) return;

    setIsLoading(true);
    setError(null);
    setIsConversationActive(false);
    shouldContinueRef.current = false;
    isFetchingNextRef.current = false; // Cancel any ongoing prefetch

    try {
      const summary = await invoke<ConversationSummary>('end_multi_qube_conversation', {
        userId,
        conversationId,
        anchor,
        password,
      });

      // Reset state
      setConversationId(null);
      setConversationHistory([]);
      setInputValue('');
      clearAllPipelines(); // Clear all qube pipelines

      alert(`Conversation ended!\nTotal turns: ${summary.total_turns}\nBlocks ${anchor ? 'anchored' : 'not anchored'} to permanent chains.`);
    } catch (err) {
      console.error('Failed to end conversation:', err);
      setError(`Failed to end conversation: ${String(err)}`);
    } finally {
      setIsLoading(false);
    }
  };

  // ========== TTS FLOW WITH PIPELINE PREFETCH ==========
  // 1. When pendingTTSMessage is set, check if we have prefetched audio
  // 2. If prefetched, play immediately; otherwise generate TTS
  // 3. While playing, start prefetch for next speaker in background
  // 4. When typewriter completes, auto-continue checks pipeline for next response

  // Handle TTS playback for pending message
  useEffect(() => {
    const playMessageTTS = async () => {
      if (!pendingTTSMessage || !userId || !password) return;

      const messageId = `${pendingTTSMessage.conversation_id}-${pendingTTSMessage.turn_number}`;

      // Skip if already processing this message
      if (processingMessageRef.current === messageId) return;

      processingMessageRef.current = messageId;
      lastProcessedTurnRef.current = pendingTTSMessage.turn_number;
      setCurrentSpeakerId(pendingTTSMessage.speaker_id);

      // Find qube
      let qube = getQubeById(pendingTTSMessage.speaker_id);
      if (!qube && isP2P && allQubes.length > 0) {
        qube = allQubes.find(q => q.name === pendingTTSMessage.speaker_name);
      }

      const voiceModel = pendingTTSMessage.voice_model || qube?.voice_model;
      const ttsEnabled = qube?.tts_enabled === true;

      // No TTS - just show message
      if (!voiceModel || !ttsEnabled) {
        setActiveTypewriterMessageId(messageId);
        setConversationHistory(prev => [...prev, pendingTTSMessage]);
        setPendingTTSMessage(null);
        setIsLoading(false);
        setNextResponseStatus({ stage: 'idle' });
        processingMessageRef.current = null;

        // Start prefetch for next speaker
        if (isConversationActive && shouldContinueRef.current && !isP2P && pendingTTSMessage.next_speaker_id) {
          startPipelinePrefetch(pendingTTSMessage.next_speaker_id);
        }
        return;
      }

      try {
        // Check if we have prefetched audio in the pipeline
        const pipeline = qubePipelines.get(pendingTTSMessage.speaker_id);
        const hasPrefetchedAudio = pipeline?.prefetchedAudio && pipeline?.status === 'ready';

        if (hasPrefetchedAudio && pipeline?.prefetchedAudio) {
          // Play prefetched audio immediately
          console.log('[TTS] Using prefetched audio for', pendingTTSMessage.speaker_name);
          setNextResponseStatus({ stage: 'idle' });
          const cleanedMessage = truncateForTTS(cleanContentForDisplay(pendingTTSMessage.message));
          await playPrefetchedTTS(pipeline.prefetchedAudio, cleanedMessage);

          // Clear the pipeline
          updatePipeline(pendingTTSMessage.speaker_id, { status: 'idle', pendingResponse: null, prefetchedAudio: null });
        } else {
          // Generate TTS now
          console.log('[TTS] Generating audio for', pendingTTSMessage.speaker_name);
          setNextResponseStatus({
            stage: 'generating_tts',
            qubeId: pendingTTSMessage.speaker_id,
            qubeName: pendingTTSMessage.speaker_name
          });

          const cleanedMessage = truncateForTTS(cleanContentForDisplay(pendingTTSMessage.message));
          if (qube) {
            await playTTS(userId, qube.qube_id, cleanedMessage, password);
          }
        }

        // Show message with typewriter
        setActiveTypewriterMessageId(messageId);
        setConversationHistory(prev => [...prev, pendingTTSMessage]);
        setNextResponseStatus({ stage: 'idle' });

        setPendingTTSMessage(null);
        setIsLoading(false);

        // Start prefetch for next speaker while typewriter runs
        if (isConversationActive && shouldContinueRef.current && !isP2P && pendingTTSMessage.next_speaker_id) {
          setNextSpeakerId(pendingTTSMessage.next_speaker_id);
          startPipelinePrefetch(pendingTTSMessage.next_speaker_id);
        }
      } catch (err) {
        console.error('TTS error:', err);
        setError(`TTS error: ${String(err)}`);
        setPendingTTSMessage(null);
        setIsLoading(false);
        processingMessageRef.current = null;
      }
    };

    playMessageTTS();
  }, [pendingTTSMessage, qubePipelines, updatePipeline]);

  // Auto-continue when typewriter completes
  useEffect(() => {
    // Handle pause request
    if (
      !activeTypewriterMessageId &&
      !pendingTTSMessage &&
      !processingMessageRef.current &&
      pauseAfterCurrentMessageRef.current
    ) {
      // Check if next speaker's pipeline has a ready response
      const nextPipeline = nextSpeakerId ? qubePipelines.get(nextSpeakerId) : null;
      if (nextPipeline?.status === 'ready' && nextPipeline.pendingResponse && nextPipeline.prefetchedAudio) {
        // Play prefetched response before pausing
        setPendingTTSMessage(nextPipeline.pendingResponse);
        updatePipeline(nextSpeakerId!, { status: 'idle', pendingResponse: null, prefetchedAudio: null });
        setNextResponseStatus({ stage: 'idle' });
        return;
      }
      setIsConversationActive(false);
      pauseAfterCurrentMessageRef.current = false;
      setIsPauseRequested(false);
      clearAllPipelines();
      return;
    }

    // Auto-continue conditions
    if (
      !activeTypewriterMessageId &&
      isConversationActive &&
      shouldContinueRef.current &&
      !pendingTTSMessage &&
      !isLoading &&
      !processingMessageRef.current &&
      !waitingForUserResponseRef.current
    ) {
      // Check if ANY pipeline is active (not just nextSpeakerId)
      let activePipeline: QubePipeline | null = null;
      let activePipelineQubeId: string | null = null;

      // First check nextSpeakerId's pipeline
      if (nextSpeakerId) {
        const nextPipeline = qubePipelines.get(nextSpeakerId);
        if (nextPipeline && nextPipeline.status !== 'idle') {
          activePipeline = nextPipeline;
          activePipelineQubeId = nextSpeakerId;
        }
      }

      // If no pipeline for nextSpeakerId, check all pipelines
      if (!activePipeline) {
        for (const [qubeId, pipeline] of qubePipelines.entries()) {
          if (pipeline.status !== 'idle') {
            activePipeline = pipeline;
            activePipelineQubeId = qubeId;
            break;
          }
        }
      }

      if (activePipeline?.status === 'ready' && activePipeline.pendingResponse) {
        // Immediate playback from prefetch!
        console.log('[Auto-continue] Using prefetched response from pipeline for', activePipelineQubeId);
        setPendingTTSMessage(activePipeline.pendingResponse);
        updatePipeline(activePipelineQubeId!, { status: 'idle', pendingResponse: null, prefetchedAudio: null });
      } else if (activePipeline?.status === 'processing' || activePipeline?.status === 'generating_tts') {
        // Still preparing - status indicator already shows this, just wait
        // The pipeline will update and trigger this effect again
        console.log('[Auto-continue] Waiting for pipeline:', activePipeline?.status, 'for', activePipelineQubeId);
      } else if (!isFetchingNextRef.current) {
        // No pipeline active - fetch fresh
        const timer = setTimeout(() => {
          continueConversation();
        }, 500);
        return () => clearTimeout(timer);
      }
    }
  }, [activeTypewriterMessageId, isConversationActive, pendingTTSMessage, isLoading, nextSpeakerId, qubePipelines, updatePipeline, clearAllPipelines]);

  // Handle user message injection
  useEffect(() => {
    if (
      pendingUserMessage?.userMessageResponse &&
      pendingUserMessage?.qubeResponse &&
      !activeTypewriterMessageId &&
      !pendingTTSMessage &&
      !processingMessageRef.current
    ) {
      (async () => {
        const qubeResponse = pendingUserMessage.qubeResponse;
        if (!qubeResponse) return;

        setConversationHistory(prev => [...prev, pendingUserMessage.userMessageResponse!]);

        await new Promise(resolve => requestAnimationFrame(() => {
          requestAnimationFrame(() => requestAnimationFrame(resolve));
        }));

        setNextResponseStatus({ stage: 'idle' });
        await new Promise(resolve => setTimeout(resolve, 50));

        lastProcessedTurnRef.current = qubeResponse.turn_number;
        waitingForUserResponseRef.current = false;
        // Set next speaker hint if available
        if (qubeResponse.next_speaker_id) {
          setNextSpeakerId(qubeResponse.next_speaker_id);
        }
        setPendingUserMessage(null);

        if (audioElement) {
          audioElement.pause();
          audioElement.currentTime = 0;
          audioElement.removeAttribute('src');
          audioElement.load();
          await new Promise(resolve => setTimeout(resolve, 100));
        }

        setPendingTTSMessage(qubeResponse);
      })();
    }
  }, [pendingUserMessage, activeTypewriterMessageId, pendingTTSMessage]);

  // Handle Enter key
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey && !isLoading) {
      e.preventDefault();
      if (!conversationId) {
        handleStartConversation();
      } else {
        handleInjectUserMessage();
      }
    }
  };

  // Filter available connections (exclude local qubes) - computed before early returns
  const localCommitments = selectedQubes.map(q => q.commitment || '');
  const availableConnections = connections.filter(
    conn => !localCommitments.includes(conn.commitment)
  );

  // Build list of all participants for header (local qubes + selected connections in P2P)
  // IMPORTANT: This must be called before any early returns (React hooks rule)
  const headerParticipants = useMemo(() => {
    const participants: Array<{
      id: string;
      name: string;
      color: string;
      avatarUrl?: string;
      model?: string;
      isConnection: boolean;
    }> = [];

    // Add local qubes
    selectedQubes.forEach(qube => {
      participants.push({
        id: qube.qube_id,
        name: qube.name,
        color: qube.favorite_color || '#00d4ff',
        avatarUrl: qube.avatar_url || qube.avatar_local_path,
        model: qube.ai_model,
        isConnection: false,
      });
    });

    // In P2P mode, add selected connections
    if (isP2P && selectedConnections.length > 0) {
      selectedConnections.forEach(commitment => {
        // Check if this connection is actually a local qube (from allQubes)
        const localQube = allQubes.find(q => q.commitment === commitment);
        if (localQube) {
          // It's a local qube selected as connection
          participants.push({
            id: commitment,
            name: localQube.name,
            color: localQube.favorite_color || '#00d4ff',
            avatarUrl: localQube.avatar_url || localQube.avatar_local_path,
            model: localQube.ai_model,
            isConnection: true,
          });
        } else {
          // It's a true remote connection
          const conn = connections.find(c => c.commitment === commitment);
          if (conn) {
            participants.push({
              id: commitment,
              name: conn.name,
              color: '#9945FF', // Purple for remote
              isConnection: true,
            });
          }
        }
      });
    }

    return participants;
  }, [selectedQubes, isP2P, selectedConnections, allQubes, connections]);

  // P2P mode allows 1 qube + connections. Local mode requires 2+ qubes.
  if (!isP2P && selectedQubes.length < 2) {
    return (
      <GlassCard className="flex-1 p-6 flex items-center justify-center">
        <div className="text-center">
          <p className="text-text-secondary mb-2">Multi-Qube Conversation</p>
          <p className="text-text-tertiary text-sm">
            Select 2 or more Qubes (Ctrl+Click) to start a group conversation
          </p>
        </div>
      </GlassCard>
    );
  }

  // P2P mode with no qubes selected
  if (isP2P && selectedQubes.length === 0) {
    return (
      <GlassCard className="flex-1 p-6 flex items-center justify-center">
        <div className="text-center">
          <p className="text-text-secondary mb-2">P2P Network Conversation</p>
          <p className="text-text-tertiary text-sm">
            Select at least one Qube to start a P2P conversation
          </p>
        </div>
      </GlassCard>
    );
  }

  return (
    <div className="flex-1 flex flex-col gap-4 h-full">
      {/* Conversation Header - Participants */}
      <GlassCard className="p-4 flex-shrink-0">
        <div className="flex items-center gap-6">
          {headerParticipants.map((participant) => (
            <div
              key={participant.id}
              className="flex items-center gap-4 group"
            >
              {/* Avatar */}
              <div className="relative">
                {participant.avatarUrl ? (
                  <img
                    src={participant.avatarUrl.startsWith('http') ? participant.avatarUrl : convertFileSrc(participant.avatarUrl)}
                    alt={`${participant.name} avatar`}
                    className="w-24 h-24 rounded-xl object-cover border-3 transition-all group-hover:scale-105"
                    style={{
                      borderColor: participant.color,
                      boxShadow: `0 0 20px ${participant.color}60, inset 0 0 20px ${participant.color}20`,
                    }}
                    onError={(e) => {
                      const target = e.target as HTMLImageElement;
                      target.style.display = 'none';
                      const fallback = target.nextElementSibling as HTMLElement;
                      if (fallback) fallback.style.display = 'flex';
                    }}
                  />
                ) : null}
                <div
                  className="w-24 h-24 rounded-xl flex items-center justify-center text-3xl font-display font-bold border-3"
                  style={{
                    background: `linear-gradient(135deg, ${participant.color}60, ${participant.color}30)`,
                    color: participant.color,
                    borderColor: participant.color,
                    boxShadow: `0 0 20px ${participant.color}60`,
                    display: participant.avatarUrl ? 'none' : 'flex',
                  }}
                >
                  {participant.name[0]}
                </div>
              </div>

              {/* Participant Info */}
              <div className="flex flex-col gap-1">
                <h3
                  className="text-2xl font-display font-bold tracking-wide"
                  style={{
                    color: participant.color,
                    textShadow: `0 0 20px ${participant.color}60`,
                  }}
                >
                  {participant.name}
                  {participant.isConnection && (
                    <span className="ml-2 text-xs font-normal text-text-tertiary">(P2P)</span>
                  )}
                </h3>
                <p className="text-sm text-text-tertiary font-mono">
                  {participant.model || (participant.isConnection ? 'Remote Qube' : '')}
                </p>
              </div>
            </div>
          ))}
        </div>
      </GlassCard>

      {/* P2P Connection Selector - Only show in P2P mode before conversation starts */}
      {isP2P && !conversationId && availableConnections.length > 0 && (
        <GlassCard className="p-4 flex-shrink-0">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h3 className="text-lg font-display text-accent-secondary">
                Invite Connections ({selectedConnections.length} selected)
              </h3>
              <p className="text-xs text-text-tertiary">
                Select remote Qubes to join this P2P conversation
              </p>
            </div>
            {wsConnected && (
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-accent-success animate-pulse" />
                <span className="text-xs text-accent-success">Connected</span>
              </div>
            )}
          </div>
          <div className="flex flex-wrap gap-2">
            {availableConnections.map(conn => (
              <button
                key={conn.commitment}
                onClick={() => toggleConnection(conn.commitment)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                  selectedConnections.includes(conn.commitment)
                    ? 'bg-accent-secondary/20 border-2 border-accent-secondary text-accent-secondary'
                    : 'bg-bg-tertiary border-2 border-glass-border text-text-secondary hover:border-accent-secondary/50'
                }`}
              >
                {conn.name}
                {selectedConnections.includes(conn.commitment) && ' ✓'}
              </button>
            ))}
          </div>
        </GlassCard>
      )}

      {/* P2P Status Bar - Show when in P2P mode with active session */}
      {isP2P && p2pSessionId && (
        <div className="flex items-center justify-between px-4 py-2 bg-accent-secondary/10 border border-accent-secondary/30 rounded-lg">
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-accent-success animate-pulse' : 'bg-accent-danger'}`} />
            <span className="text-sm text-accent-secondary font-medium">P2P Network</span>
            <span className="text-xs text-text-tertiary">
              Session: {p2pSessionId.substring(0, 8)}...
            </span>
          </div>
          <span className="text-xs text-text-tertiary">
            {selectedConnections.length} remote participant(s)
          </span>
        </div>
      )}

      {/* Messages Area */}
      <div ref={scrollContainerRef} className="flex-1 p-4 overflow-y-auto bg-bg-secondary/30 backdrop-blur-md border border-accent-primary/20 rounded-xl">
        {conversationHistory.length === 0 ? (
          <div className="h-full flex items-center justify-center">
            <p className="text-text-tertiary text-center">
              {isP2P
                ? (selectedConnections.length > 0 || selectedQubes.length > 1
                    ? 'Start a P2P conversation by typing a message below'
                    : 'Select connections above or add more local Qubes to start')
                : 'Start a conversation by typing a message below'
              }
            </p>
          </div>
        ) : (
          <div className="space-y-4">

            {/* UNIFIED TIMELINE: Render messages and actions together */}
            {(() => {
              // Build unified timeline of messages and actions
              type TimelineItem =
                | { type: 'message'; data: ConversationMessage; turnNumber: number; timestamp: number }
                | { type: 'action'; data: typeof actionBlocks[0]; turnNumber: number; timestamp: number };

              const timeline: TimelineItem[] = [];

              // Add all messages with their turn numbers
              conversationHistory.forEach(msg => {
                timeline.push({
                  type: 'message',
                  data: msg,
                  turnNumber: msg.turn_number,
                  timestamp: msg.timestamp || 0
                });
              });

              // For actions, figure out which turn they belong to based on timestamp
              // Actions appear BEFORE the qube's message (since tool calls happen before response)
              actionBlocks.forEach(action => {
                // Find which message this action precedes (same qube, action timestamp <= message timestamp)
                // Both timestamps are in seconds
                const relatedMsg = conversationHistory.find(msg =>
                  msg.speaker_id === action.qube_id &&
                  (msg.timestamp || 0) >= action.timestamp
                );

                // If found, action belongs to that turn (but renders before the message)
                // If not found, it's a trailing action for the next turn
                const turnNumber = relatedMsg
                  ? relatedMsg.turn_number - 0.5  // Sort before the message
                  : (conversationHistory.length > 0 ? Math.max(...conversationHistory.map(m => m.turn_number)) + 0.5 : 0.5);

                timeline.push({
                  type: 'action',
                  data: action,
                  turnNumber: turnNumber,
                  timestamp: action.timestamp
                });
              });

              // Sort by turn number (primary), then timestamp (secondary for actions within same turn)
              timeline.sort((a, b) => {
                if (a.turnNumber !== b.turnNumber) {
                  return a.turnNumber - b.turnNumber;
                }
                // Same turn - sort by timestamp
                return a.timestamp - b.timestamp;
              });

              return timeline.map((item, idx) => {
                if (item.type === 'action') {
                  const action = item.data;
                  const actionQube = selectedQubes.find(q => q.qube_id === action.qube_id);
                  const actionColor = actionQube?.favorite_color || '#00d4ff';
                  const actionAvatar = actionQube ? getAvatarPath(actionQube) : undefined;
                  const actionQubeName = actionQube?.name || 'Unknown';

                  return (
                    <div key={`action-${action.qube_id}-${action.timestamp}-${idx}`} className="flex justify-start">
                      <div className="max-w-[70%]">
                        <ToolCallBubble
                          toolName={action.action_type}
                          input={action.parameters}
                          result={action.result}
                          status={action.status as 'in_progress' | 'completed' | 'failed'}
                          accentColor={actionColor}
                          timestamp={action.timestamp}
                          label={actionQubeName}
                          avatarUrl={actionAvatar}
                        />
                      </div>
                    </div>
                  );
                } else {
                  const msg = item.data;
                  const messageId = `${msg.conversation_id}-${msg.turn_number}`;
                  const qube = getQubeById(msg.speaker_id);
                  const participantInfo = getParticipantInfo(msg.speaker_id);
                  const isUser = msg.speaker_id === userId;
                  const speakerColor = participantInfo?.color || qube?.favorite_color || '#00d4ff';
                  const speakerAvatarUrl = participantInfo?.avatarUrl || (qube ? getAvatarPath(qube) : undefined);

                  return (
                    <div key={`msg-${messageId}-${idx}`} className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
                      <div
                        className={`max-w-[70%] rounded-lg p-3 border-2 ${
                          isUser ? 'bg-accent-primary/20 text-text-primary border-accent-primary' : 'bg-bg-tertiary text-text-primary'
                        }`}
                        style={!isUser ? { borderColor: speakerColor } : undefined}
                      >
                        <div className="flex items-center gap-2 mb-2">
                          {!isUser && speakerAvatarUrl && (
                            <img
                              src={speakerAvatarUrl.startsWith('http') ? speakerAvatarUrl : convertFileSrc(speakerAvatarUrl)}
                              alt={msg.speaker_name}
                              className="w-8 h-8 rounded-full object-cover border-2"
                              style={{ borderColor: speakerColor, boxShadow: `0 0 8px ${speakerColor}60` }}
                              onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                            />
                          )}
                          <p className="text-sm font-medium" style={{ color: isUser ? 'var(--accent-primary)' : speakerColor }}>
                            {msg.speaker_name}
                          </p>
                        </div>
                        <div className="whitespace-pre-wrap break-words">
                          {!isUser && messageId === activeTypewriterMessageId ? (
                            <TypewriterText
                              text={msg.message}
                              audioElement={audioElement}
                              onComplete={() => {
                                console.log('[Typewriter] Completed for:', msg.speaker_name, 'Turn:', msg.turn_number);
                                setActiveTypewriterMessageId(null);
                                processingMessageRef.current = null;
                              }}
                            />
                          ) : (
                            renderMessageContent(msg.message, msg.speaker_id)
                          )}
                        </div>
                        <p className="text-text-tertiary text-xs mt-1">Turn {msg.turn_number}</p>
                      </div>
                    </div>
                  );
                }
              });
            })()}

            {/* Loading/Processing response indicator - shows when backend is processing */}
            {/* Show when: isLoading OR stage is 'processing' OR (conversation active but nothing happening) */}
            {/* Hide when: generating_tts (TTS indicator shows) */}
            {(isLoading ||
              nextResponseStatus.stage === 'processing' ||
              (isConversationActive && shouldContinueRef.current && !activeTypewriterMessageId && !pendingTTSMessage && nextResponseStatus.stage === 'idle')
            ) &&
             nextResponseStatus.stage !== 'generating_tts' && (() => {
              // Get qube if we know who's responding
              const qube = nextResponseStatus.qubeId ? getQubeById(nextResponseStatus.qubeId) : null;
              const participantInfo = nextResponseStatus.qubeId ? getParticipantInfo(nextResponseStatus.qubeId) : null;

              // Use qube color if known, otherwise default cyan
              const color = participantInfo?.color || qube?.favorite_color || '#00d9ff';
              const speakerName = nextResponseStatus.qubeName || participantInfo?.name || qube?.name;
              const speakerAvatarUrl = participantInfo?.avatarUrl || (qube ? getAvatarPath(qube) : undefined);

              return (
                <div className="flex justify-start">
                  <div className="rounded-lg px-4 py-2 border-2" style={{
                    backgroundColor: 'var(--bg-tertiary)',
                    borderColor: color,
                  }}>
                    <div className="flex items-center gap-3">
                      {/* Show avatar if we know which qube */}
                      {speakerAvatarUrl && (
                        <img
                          src={speakerAvatarUrl.startsWith('http') ? speakerAvatarUrl : convertFileSrc(speakerAvatarUrl)}
                          alt={speakerName || 'Processing'}
                          className="w-8 h-8 rounded-full object-cover border-2"
                          style={{
                            borderColor: color,
                            opacity: 0.6
                          }}
                          onError={(e) => {
                            const target = e.target as HTMLImageElement;
                            target.style.display = 'none';
                          }}
                        />
                      )}
                      <div className="flex items-center gap-2">
                        {speakerName && (
                          <span className="text-sm font-medium" style={{
                            color: color
                          }}>
                            {speakerName}
                          </span>
                        )}
                        <span className="text-xs text-text-secondary">
                          processing response...
                        </span>
                        <div className="flex gap-1 ml-1">
                          <div className="w-2 h-2 rounded-full animate-bounce" style={{
                            backgroundColor: color,
                            animationDuration: '0.6s'
                          }}></div>
                          <div className="w-2 h-2 rounded-full animate-bounce" style={{
                            backgroundColor: color,
                            animationDuration: '0.6s',
                            animationDelay: '0.15s'
                          }}></div>
                          <div className="w-2 h-2 rounded-full animate-bounce" style={{
                            backgroundColor: color,
                            animationDuration: '0.6s',
                            animationDelay: '0.3s'
                          }}></div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })()}

            {/* Generating audio indicator */}
            {nextResponseStatus.stage === 'generating_tts' && nextResponseStatus.qubeId && (() => {
              const qube = getQubeById(nextResponseStatus.qubeId);
              const participantInfo = getParticipantInfo(nextResponseStatus.qubeId);

              // Fall back to participant info if qube not found (P2P connections)
              const speakerColor = participantInfo?.color || qube?.favorite_color || '#00d4ff';
              const speakerName = nextResponseStatus.qubeName || participantInfo?.name || qube?.name || 'Unknown';
              const speakerAvatarUrl = participantInfo?.avatarUrl || (qube ? getAvatarPath(qube) : undefined);

              return (
                <div className="flex justify-start">
                  <div className="rounded-lg px-4 py-2 border-2" style={{
                    backgroundColor: 'var(--bg-tertiary)',
                    borderColor: speakerColor,
                  }}>
                    <div className="flex items-center gap-3">
                      {speakerAvatarUrl ? (
                        <img
                          src={speakerAvatarUrl.startsWith('http') ? speakerAvatarUrl : convertFileSrc(speakerAvatarUrl)}
                          alt={speakerName}
                          className="w-8 h-8 rounded-full object-cover border-2"
                          style={{
                            borderColor: speakerColor,
                            opacity: 0.6
                          }}
                          onError={(e) => {
                            const target = e.target as HTMLImageElement;
                            target.style.display = 'none';
                          }}
                        />
                      ) : (
                        <div
                          className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold border-2"
                          style={{
                            background: `linear-gradient(135deg, ${speakerColor}60, ${speakerColor}30)`,
                            borderColor: speakerColor,
                            color: speakerColor,
                            opacity: 0.6
                          }}
                        >
                          {speakerName[0]}
                        </div>
                      )}
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium" style={{
                          color: speakerColor
                        }}>
                          {speakerName}
                        </span>
                        <span className="text-xs text-text-secondary">
                          generating audio...
                        </span>
                        <div className="flex gap-1 ml-1">
                          <div className="w-2 h-2 rounded-full animate-bounce" style={{
                            backgroundColor: speakerColor,
                            animationDuration: '0.6s'
                          }}></div>
                          <div className="w-2 h-2 rounded-full animate-bounce" style={{
                            backgroundColor: speakerColor,
                            animationDuration: '0.6s',
                            animationDelay: '0.15s'
                          }}></div>
                          <div className="w-2 h-2 rounded-full animate-bounce" style={{
                            backgroundColor: speakerColor,
                            animationDuration: '0.6s',
                            animationDelay: '0.3s'
                          }}></div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })()}

            {/* Ready to respond indicator */}
            {nextResponseStatus.stage === 'ready' && nextResponseStatus.qubeId && (() => {
              const qube = getQubeById(nextResponseStatus.qubeId);
              const participantInfo = getParticipantInfo(nextResponseStatus.qubeId);

              const speakerColor = participantInfo?.color || qube?.favorite_color || '#00d4ff';
              const speakerName = nextResponseStatus.qubeName || participantInfo?.name || qube?.name || 'Unknown';
              const speakerAvatarUrl = participantInfo?.avatarUrl || (qube ? getAvatarPath(qube) : undefined);

              return (
                <div className="flex justify-start">
                  <div className="rounded-lg px-4 py-2 border-2" style={{
                    backgroundColor: 'var(--bg-tertiary)',
                    borderColor: speakerColor,
                  }}>
                    <div className="flex items-center gap-3">
                      {speakerAvatarUrl ? (
                        <img
                          src={speakerAvatarUrl.startsWith('http') ? speakerAvatarUrl : convertFileSrc(speakerAvatarUrl)}
                          alt={speakerName}
                          className="w-8 h-8 rounded-full object-cover border-2"
                          style={{
                            borderColor: speakerColor,
                          }}
                          onError={(e) => {
                            const target = e.target as HTMLImageElement;
                            target.style.display = 'none';
                          }}
                        />
                      ) : (
                        <div
                          className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold border-2"
                          style={{
                            background: `linear-gradient(135deg, ${speakerColor}60, ${speakerColor}30)`,
                            borderColor: speakerColor,
                            color: speakerColor,
                          }}
                        >
                          {speakerName[0]}
                        </div>
                      )}
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium" style={{
                          color: speakerColor
                        }}>
                          {speakerName}
                        </span>
                        <span className="text-xs" style={{ color: speakerColor }}>
                          ready to respond ✓
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })()}

            {/* Error display */}
            {error && (
              <div className="flex justify-center">
                <div className="bg-accent-danger/10 text-accent-danger rounded-lg p-3 text-sm">
                  Error: {error}
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input Area */}
      <GlassCard className="p-4 flex-shrink-0">
        {/* File Preview Grid */}
        {uploadedFiles.length > 0 && (
          <div className="mb-3 flex flex-wrap gap-2">
            {uploadedFiles.map((file, index) => (
              <div
                key={`${file.name}-${index}`}
                className="bg-bg-tertiary border border-accent-primary/30 rounded-lg px-3 py-2 flex items-center gap-2"
              >
                <span className="text-sm text-text-primary">{file.name}</span>
                <button
                  onClick={() => removeUploadedFile(`group_${selectedQubes.map(q => q.qube_id).join('_')}`, file.name)}
                  className="text-accent-danger hover:text-accent-danger/80 transition-colors"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        )}

        <div className="flex gap-2 relative">
          {/* Audio Input Button */}
          <button
            onClick={isRecording ? handleStopRecording : handleStartRecording}
            disabled={isLoading}
            className={`px-3 py-2 rounded-lg transition-all ${
              isRecording
                ? 'bg-accent-danger text-white animate-pulse'
                : 'bg-bg-secondary text-text-secondary hover:text-accent-primary hover:bg-bg-tertiary'
            } disabled:opacity-50`}
          >
            {isRecording ? '⏹' : '🎤'}
          </button>

          {/* File Upload Button */}
          <button
            onClick={handleFileUpload}
            disabled={isLoading}
            className="px-3 py-2 rounded-lg bg-bg-secondary text-text-secondary hover:text-accent-primary hover:bg-bg-tertiary transition-colors disabled:opacity-50"
          >
            📎
          </button>

          {/* Emoji Picker Button */}
          <button
            onClick={() => setShowEmojiPicker(!showEmojiPicker)}
            className={`px-3 py-2 rounded-lg transition-all ${
              showEmojiPicker
                ? 'bg-accent-primary/20 text-accent-primary'
                : 'bg-bg-secondary text-text-secondary hover:text-accent-primary hover:bg-bg-tertiary'
            }`}
            disabled={isLoading}
          >
            😊
          </button>
          {showEmojiPicker && (
            <div className="absolute bottom-20 left-24 z-50" ref={emojiPickerRef}>
              <EmojiPicker
                onEmojiClick={handleEmojiClick}
                theme={Theme.DARK}
                width={300}
                height={400}
              />
            </div>
          )}

          {/* Pause/Resume Button - Only show for active conversations */}
          {conversationId && (
            isConversationActive ? (
              <button
                onClick={handlePauseConversation}
                disabled={isLoading || isPauseRequested}
                className={`px-3 py-2 rounded-lg transition-all disabled:opacity-50 ${
                  isPauseRequested
                    ? 'bg-accent-warning/20 text-accent-warning'
                    : 'bg-bg-secondary text-text-secondary hover:text-accent-primary hover:bg-bg-tertiary'
                }`}
                title={isPauseRequested ? 'Pausing...' : 'Pause Conversation'}
              >
                {isPauseRequested ? '⏳' : '⏸'}
              </button>
            ) : (
              <button
                onClick={handleResumeConversation}
                disabled={isLoading}
                className="px-3 py-2 rounded-lg bg-accent-primary/20 text-accent-primary hover:bg-accent-primary/30 transition-all disabled:opacity-50"
                title="Resume Conversation"
              >
                ▶
              </button>
            )
          )}

          <textarea
            ref={textareaRef}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={
              conversationId
                ? 'Type to join the conversation...'
                : `Start a group conversation with ${selectedQubes.map(q => q.name).join(', ')}...`
            }
            className="flex-1 bg-bg-secondary text-text-primary placeholder-text-tertiary rounded-lg px-4 py-2 resize-none focus:outline-none focus:ring-2 focus:ring-accent-primary/50 disabled:opacity-50"
            rows={1}
            disabled={isLoading}
          />
          {!conversationId ? (
            <GlassButton
              variant="primary"
              onClick={handleStartConversation}
              disabled={(!inputValue.trim() && uploadedFiles.length === 0) || isLoading}
            >
              Start Conversation
            </GlassButton>
          ) : (
            <GlassButton
              variant="primary"
              onClick={handleInjectUserMessage}
              disabled={(!inputValue.trim() && uploadedFiles.length === 0) || isLoading}
            >
              Send Message
            </GlassButton>
          )}
        </div>

        {conversationId && (
          <p className="text-xs text-text-tertiary mt-2">
            {isConversationActive ? (
              <>🟢 Conversation running • ID: {conversationId.substring(0, 8)}... • You can join anytime by typing a message</>
            ) : (
              <>⏸️ Conversation paused • ID: {conversationId.substring(0, 8)}... • Type a message or click Resume to continue</>
            )}
          </p>
        )}
      </GlassCard>
    </div>
  );
};
