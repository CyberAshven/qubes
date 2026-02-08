/**
 * GroupChatInterface - Clean rewrite of multi-qube chat
 *
 * Based on the working ChatInterface, with group-specific features:
 * 1. Multiple qubes taking turns
 * 2. Auto-continue after each response
 * 3. Status indicator showing current state
 * 4. Pause/Resume controls
 * 5. Per-qube pipeline for prefetch (seamless transitions)
 *
 * Pipeline Architecture:
 * - Each qube has its own pipeline state (idle/processing/generating_tts/ready)
 * - While current qube speaks, next qube's response + TTS is prefetched
 * - When typewriter finishes, if next pipeline is ready → immediate playback
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { convertFileSrc } from '@tauri-apps/api/core';
import { listen } from '@tauri-apps/api/event';
import { open } from '@tauri-apps/plugin-dialog';
import { readFile } from '@tauri-apps/plugin-fs';
import { GlassCard } from '../glass/GlassCard';
import { GlassButton } from '../glass/GlassButton';
import { Qube } from '../../types';
import { useAuth } from '../../hooks/useAuth';
import { useAudio } from '../../contexts/AudioContext';
import { TypewriterText } from './TypewriterText';
import { ToolCallBubble } from './ToolCallBubble';
import { formatModelName } from '../../utils/modelFormatter';
import EmojiPicker, { EmojiClickData, Theme } from 'emoji-picker-react';

// Voice name aliases for display (same as ChatHeader)
const VOICE_NAME_ALIASES: Record<string, string> = {
  'af_heart': 'Heart', 'af_sarah': 'Sarah', 'af_nicole': 'Nicole', 'af_sky': 'Sky',
  'af_bella': 'Bella', 'af_alloy': 'Alloy', 'af_aoede': 'Aoede', 'af_jessica': 'Jessica',
  'af_kore': 'Kore', 'af_nova': 'Nova', 'af_river': 'River', 'af_stella': 'Stella',
  'am_adam': 'Adam', 'am_echo': 'Echo', 'am_eric': 'Eric', 'am_fenrir': 'Fenrir',
  'am_liam': 'Liam', 'am_michael': 'Michael', 'am_onyx': 'Onyx', 'am_puck': 'Puck',
  'am_santa': 'Santa', 'bf_emma': 'Emma', 'bf_isabella': 'Isabella', 'bf_alice': 'Alice',
  'bf_lily': 'Lily', 'bm_george': 'George', 'bm_lewis': 'Lewis', 'bm_daniel': 'Daniel',
  'bm_fable': 'Fable',
};

const formatVoiceDisplay = (voiceModel: string | undefined): string => {
  if (!voiceModel) return 'Not set';
  const voiceId = voiceModel.includes(':') ? voiceModel.split(':')[1] : voiceModel;
  return VOICE_NAME_ALIASES[voiceId] || voiceId.charAt(0).toUpperCase() + voiceId.slice(1);
};

// =============================================================================
// TYPES
// =============================================================================

interface GroupChatInterfaceProps {
  selectedQubes: Qube[];
  allQubes: Qube[];  // For P2P mode qube lookup
  isP2P?: boolean;
}

interface ToolCallData {
  action_type: string;
  parameters?: any;
  status: 'in_progress' | 'completed' | 'failed';
  result?: any;
  timestamp: number;
}

interface ConversationMessage {
  conversation_id: string;
  turn_number: number;
  speaker_id: string;
  speaker_name: string;
  message: string;
  timestamp: number;
  next_speaker_id?: string;
  voice_model?: string;
  tool_calls?: ToolCallData[];  // Tool calls that happened during this turn
}

interface DisplayMessage {
  id: string;
  speakerId: string;
  speakerName: string;
  content: string;
  timestamp: Date;
  turnNumber: number;
  isUser?: boolean;
}

interface UploadedFile {
  name: string;
  path: string;
  type: 'image' | 'text' | 'pdf' | 'binary';
  data: string;
}

type ConversationStatus =
  | { stage: 'idle' }
  | { stage: 'processing'; speakerName?: string; speakerId?: string }
  | { stage: 'generating_tts'; speakerName: string; speakerId: string }
  | { stage: 'playing'; speakerName: string; speakerId: string };

// Per-qube pipeline state for prefetch
interface QubePipeline {
  qubeId: string;
  qubeName: string;
  status: 'idle' | 'processing' | 'generating_tts' | 'ready';
  pendingResponse: ConversationMessage | null;
  prefetchedAudio: string | null;  // Base64 audio data URL
}

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

/** Clean content for display - remove action blocks, clean markdown */
const cleanContentForDisplay = (content: string): string => {
  let cleaned = content;

  // Remove [ACTION]...[/ACTION] blocks
  cleaned = cleaned.replace(/\[ACTION\][\s\S]*?\[\/ACTION\]/g, '');

  // Clean up extra whitespace
  cleaned = cleaned.replace(/\n{3,}/g, '\n\n').trim();

  return cleaned;
};

/** Truncate and clean text for TTS */
const truncateForTTS = (text: string, maxLength: number = 4000): string => {
  let processed = text;

  // Remove code blocks
  processed = processed.replace(/```[\s\S]*?```/g, '');
  processed = processed.replace(/`[^`]+`/g, '');

  // Handle markdown formatting
  processed = processed.replace(/\*\*\*([^*]+)\*\*\*/g, '$1');
  processed = processed.replace(/\*\*([^*]+)\*\*/g, '$1');
  processed = processed.replace(/__([^_]+)__/g, '$1');
  processed = processed.replace(/\*([^*]+)\*/g, '$1,');

  // Shorten hex strings
  processed = processed.replace(/\b([a-fA-F0-9]{20,})\b/g, (match) => {
    return `${match.substring(0, 8)}...${match.substring(match.length - 8)}`;
  });

  // Normalize whitespace
  processed = processed.replace(/\s+/g, ' ').trim();

  // Truncate if needed
  if (processed.length <= maxLength) return processed;

  const truncated = processed.substring(0, maxLength);
  const lastSpace = truncated.lastIndexOf(' ');
  return truncated.substring(0, lastSpace);
};

// =============================================================================
// COMPONENT
// =============================================================================

export const GroupChatInterface: React.FC<GroupChatInterfaceProps> = ({
  selectedQubes,
  allQubes,
  isP2P = false,
}) => {
  const { userId, password } = useAuth();
  const { playTTS, prefetchTTS, playPrefetchedTTS, stopAudio, audioElement } = useAudio();

  // ---------------------------------------------------------------------------
  // STATE
  // ---------------------------------------------------------------------------

  // Input
  const [inputValue, setInputValue] = useState('');
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);

  // Conversation state
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [conversationHistory, setConversationHistory] = useState<DisplayMessage[]>([]);
  const [isConversationActive, setIsConversationActive] = useState(false);
  const [isPaused, setIsPaused] = useState(false);

  // Current turn state
  const [isLoading, setIsLoading] = useState(false);
  const [status, setStatus] = useState<ConversationStatus>({ stage: 'idle' });
  const [error, setError] = useState<string | null>(null);
  const [nextSpeakerId, setNextSpeakerId] = useState<string | null>(null);

  // Per-qube pipelines for prefetch
  const [qubePipelines, setQubePipelines] = useState<Map<string, QubePipeline>>(new Map());
  const [currentSpeakerId, setCurrentSpeakerId] = useState<string | null>(null);

  // Typewriter state
  const [activeTypewriterMessageId, setActiveTypewriterMessageId] = useState<string | null>(null);

  // Tool calls - messageId is set when the message arrives
  const [activeToolCalls, setActiveToolCalls] = useState<Array<{
    action_type: string;
    timestamp: number;
    speakerId: string;
    status: 'in_progress' | 'completed' | 'failed';
    input?: any;
    result?: any;
    messageId?: string;  // Set when the message that used this tool arrives
  }>>([]);

  // UI state
  const [showEmojiPicker, setShowEmojiPicker] = useState(false);
  const [isRecording, setIsRecording] = useState(false);

  // ---------------------------------------------------------------------------
  // REFS
  // ---------------------------------------------------------------------------

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const shouldContinueRef = useRef(false);
  const currentTurnRef = useRef(0);
  const processingRef = useRef(false);  // Guard against double processing
  const isFetchingRef = useRef(false);  // Guard against concurrent fetches (prefetch OR continue)
  const isPlayingRef = useRef(false);   // Guard against concurrent plays (prevents interruption)
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const emojiPickerRef = useRef<HTMLDivElement>(null);
  const recognitionRef = useRef<any>(null);
  const isUserAtBottomRef = useRef<boolean>(true);  // Track if user is at bottom for smart scroll
  const conversationHistoryRef = useRef<DisplayMessage[]>([]);

  // Keep ref in sync with state for use in async functions
  useEffect(() => {
    conversationHistoryRef.current = conversationHistory;
  }, [conversationHistory]);

  // ---------------------------------------------------------------------------
  // SCROLL HELPERS (Smart scroll - only auto-scroll if user is at bottom)
  // ---------------------------------------------------------------------------

  const checkIfAtBottom = useCallback(() => {
    const container = messagesContainerRef.current;
    if (!container) return true;
    const threshold = 100; // pixels from bottom to consider "at bottom"
    return container.scrollHeight - container.scrollTop - container.clientHeight < threshold;
  }, []);

  const handleScroll = useCallback(() => {
    isUserAtBottomRef.current = checkIfAtBottom();
  }, [checkIfAtBottom]);

  const scrollToBottom = useCallback((force = false) => {
    if (force || isUserAtBottomRef.current) {
      const container = messagesContainerRef.current;
      if (container) {
        container.scrollTo({
          top: container.scrollHeight,
          behavior: 'smooth'
        });
      }
    }
  }, []);

  const forceScrollToBottom = useCallback(() => {
    isUserAtBottomRef.current = true;
    const container = messagesContainerRef.current;
    if (container) {
      container.scrollTo({
        top: container.scrollHeight,
        behavior: 'smooth'
      });
    }
  }, []);

  // Auto-scroll when messages change
  useEffect(() => {
    scrollToBottom();
  }, [conversationHistory.length, scrollToBottom]);

  // Also scroll during typewriter effect
  useEffect(() => {
    if (!activeTypewriterMessageId) return;

    const interval = setInterval(() => {
      scrollToBottom();
    }, 100);

    return () => clearInterval(interval);
  }, [activeTypewriterMessageId, scrollToBottom]);

  // ---------------------------------------------------------------------------
  // REAL-TIME TOOL CALL EVENTS (from Tauri backend)
  // ---------------------------------------------------------------------------

  useEffect(() => {
    // Listen for tool call events emitted by the backend in real-time
    const setupListener = async () => {
      const unlisten = await listen<{
        event_type: string;
        action_type: string;
        status: string;
        speaker_id: string;
        speaker_name: string;
        timestamp: number;
        parameters?: any;
        result?: any;
      }>('tool-call-event', (event) => {
        const data = event.payload;
        console.log('[ToolEvent] Received:', data.action_type, data.status);

        setActiveToolCalls(prev => {
          // Check if this tool call already exists (by timestamp)
          const existing = prev.find(t => t.timestamp === data.timestamp);
          if (existing) {
            // Update existing tool call (status change from in_progress -> completed)
            return prev.map(t => t.timestamp === data.timestamp
              ? { ...t, status: data.status as 'in_progress' | 'completed' | 'failed', result: data.result }
              : t
            );
          } else {
            // Add new tool call
            return [...prev, {
              action_type: data.action_type,
              timestamp: data.timestamp,
              speakerId: data.speaker_id,
              status: data.status as 'in_progress' | 'completed' | 'failed',
              input: data.parameters,
              result: data.result,
              // No messageId yet - will be associated when message arrives
            }].sort((a, b) => a.timestamp - b.timestamp);
          }
        });
      });

      return unlisten;
    };

    const unlistenPromise = setupListener();

    return () => {
      unlistenPromise.then(unlisten => unlisten());
    };
  }, []);

  // ---------------------------------------------------------------------------
  // QUBE HELPERS
  // ---------------------------------------------------------------------------

  const getQubeById = useCallback((qubeId: string): Qube | undefined => {
    return selectedQubes.find(q => q.qube_id === qubeId) ||
           allQubes.find(q => q.qube_id === qubeId);
  }, [selectedQubes, allQubes]);

  const getQubeColor = useCallback((qubeId: string): string => {
    const qube = getQubeById(qubeId);
    return qube?.favorite_color || '#8B5CF6';
  }, [getQubeById]);

  const getAvatarPath = useCallback((qube: Qube): string => {
    if (qube.avatar_url) return qube.avatar_url;
    if (qube.avatar_local_path) return convertFileSrc(qube.avatar_local_path);
    const projectRoot = 'C:/Users/bit_f/Projects/Qubes';
    const filePath = `${projectRoot}/data/users/${userId}/qubes/${qube.name}_${qube.qube_id}/chain/${qube.qube_id}_avatar.png`;
    return convertFileSrc(filePath);
  }, [userId]);

  // ---------------------------------------------------------------------------
  // PIPELINE HELPERS (Per-qube prefetch state management)
  // ---------------------------------------------------------------------------

  // Update a single qube's pipeline state
  const updatePipeline = useCallback((qubeId: string, updates: Partial<QubePipeline>) => {
    setQubePipelines(prev => {
      const newMap = new Map(prev);
      const qube = getQubeById(qubeId);
      const current = newMap.get(qubeId) || {
        qubeId,
        qubeName: qube?.name || 'Unknown',
        status: 'idle' as const,
        pendingResponse: null,
        prefetchedAudio: null,
      };
      newMap.set(qubeId, { ...current, ...updates });
      return newMap;
    });
  }, [getQubeById]);

  // Get pipeline for a qube
  const getPipeline = useCallback((qubeId: string): QubePipeline | undefined => {
    return qubePipelines.get(qubeId);
  }, [qubePipelines]);

  // Clear all pipelines (on conversation end or stop)
  const clearAllPipelines = useCallback(() => {
    setQubePipelines(new Map());
    setCurrentSpeakerId(null);
    setNextSpeakerId(null);
  }, []);

  // ---------------------------------------------------------------------------
  // FILE UPLOAD
  // ---------------------------------------------------------------------------

  const handleFileUpload = async () => {
    try {
      const selected = await open({
        multiple: true,
        filters: [{
          name: 'Images and Documents',
          extensions: ['png', 'jpg', 'jpeg', 'gif', 'webp', 'txt', 'md', 'json', 'pdf']
        }]
      });

      if (!selected) return;

      const filePaths = Array.isArray(selected) ? selected : [selected];

      for (const filePath of filePaths) {
        const fileBytes = await readFile(filePath);
        const fileName = filePath.split(/[\\/]/).pop() || 'file';
        const extension = fileName.split('.').pop()?.toLowerCase() || '';

        const imageExtensions = ['png', 'jpg', 'jpeg', 'gif', 'webp'];
        const textExtensions = ['txt', 'md', 'json'];
        const isImage = imageExtensions.includes(extension);
        const isText = textExtensions.includes(extension);
        const isPDF = extension === 'pdf';

        let fileData: UploadedFile;

        if (isImage || isPDF) {
          const uint8Array = new Uint8Array(fileBytes);
          let binaryString = '';
          for (let i = 0; i < uint8Array.length; i += 8192) {
            const chunk = uint8Array.slice(i, i + 8192);
            binaryString += String.fromCharCode(...chunk);
          }
          fileData = {
            name: fileName,
            path: filePath,
            type: isPDF ? 'pdf' : 'image',
            data: isImage ? `data:image/${extension};base64,${btoa(binaryString)}` : btoa(binaryString)
          };
        } else if (isText) {
          fileData = {
            name: fileName,
            path: filePath,
            type: 'text',
            data: new TextDecoder().decode(fileBytes)
          };
        } else {
          continue; // Skip unsupported files
        }

        setUploadedFiles(prev => [...prev, fileData]);
      }
    } catch (err) {
      console.error('Failed to upload file:', err);
      setError(`Failed to upload file: ${String(err)}`);
    }
  };

  const removeFile = (index: number) => {
    setUploadedFiles(prev => prev.filter((_, i) => i !== index));
  };

  // ---------------------------------------------------------------------------
  // EMOJI HANDLER
  // ---------------------------------------------------------------------------

  const handleEmojiClick = (emojiData: EmojiClickData) => {
    const emoji = emojiData.emoji;
    const textarea = textareaRef.current;

    if (textarea) {
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      const newValue = inputValue.slice(0, start) + emoji + inputValue.slice(end);
      setInputValue(newValue);

      // Set cursor position after emoji
      setTimeout(() => {
        textarea.selectionStart = textarea.selectionEnd = start + emoji.length;
        textarea.focus();
      }, 0);
    } else {
      setInputValue(prev => prev + emoji);
    }

    setShowEmojiPicker(false);
  };

  // ---------------------------------------------------------------------------
  // VOICE RECORDING
  // ---------------------------------------------------------------------------

  const startRecording = () => {
    if (!('webkitSpeechRecognition' in window)) {
      setError('Speech recognition not supported in this browser');
      return;
    }

    const SpeechRecognition = (window as any).webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;

    recognition.onresult = (event: any) => {
      const transcript = Array.from(event.results)
        .map((result: any) => result[0])
        .map((result: any) => result.transcript)
        .join('');
      setInputValue(transcript);
    };

    recognition.onerror = (event: any) => {
      console.error('Speech recognition error:', event.error);
      setIsRecording(false);
    };

    recognition.onend = () => {
      setIsRecording(false);
    };

    recognitionRef.current = recognition;
    recognition.start();
    setIsRecording(true);
  };

  const stopRecording = () => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      recognitionRef.current = null;
    }
    setIsRecording(false);
  };

  // ---------------------------------------------------------------------------
  // START CONVERSATION
  // ---------------------------------------------------------------------------

  const startConversation = async () => {
    if (!inputValue.trim() && uploadedFiles.length === 0) return;
    if (selectedQubes.length < 2 && !isP2P) return;
    if (!userId || !password) return;

    setIsLoading(true);
    setError(null);
    setStatus({ stage: 'processing' });
    shouldContinueRef.current = true;
    processingRef.current = true;

    try {
      // Prepare file data
      const imageFiles = uploadedFiles
        .filter(f => f.type === 'image')
        .map(f => ({ name: f.name, data: f.data }));
      const textFiles = uploadedFiles
        .filter(f => f.type === 'text')
        .map(f => ({ name: f.name, content: f.data }));
      const pdfFiles = uploadedFiles
        .filter(f => f.type === 'pdf')
        .map(f => ({ name: f.name, data: f.data }));

      const qubeIds = selectedQubes.map(q => q.qube_id).join(',');

      // Add user message to history
      const userMessage: DisplayMessage = {
        id: `user-${Date.now()}`,
        speakerId: 'user',
        speakerName: userId,
        content: inputValue,
        timestamp: new Date(),
        turnNumber: 0,
        isUser: true,
      };
      setConversationHistory([userMessage]);
      forceScrollToBottom();

      // Clear input
      const messageText = inputValue;
      setInputValue('');
      setUploadedFiles([]);

      // Build the prompt with file contents if any
      let userPrompt = messageText;
      if (textFiles.length > 0) {
        const textContent = textFiles.map(f => `[File: ${f.name}]\n${f.content}`).join('\n\n');
        userPrompt = `${messageText}\n\n${textContent}`;
      }

      // Start the conversation
      const response = await invoke<{
        conversation_id: string;
        participants: Array<{ qube_id: string; name: string }>;
        first_response: ConversationMessage;
      }>('start_multi_qube_conversation', {
        userId,
        qubeIdsStr: qubeIds,
        initialPrompt: userPrompt,
        password,
        conversationMode: 'discussion',
      });

      console.log('[GroupChat] Started conversation:', response.conversation_id);

      setConversationId(response.conversation_id);
      currentTurnRef.current = response.first_response.turn_number;
      setIsConversationActive(true);

      // Note: Don't clear tool calls here - real-time events have already populated them
      // during the invoke call above. They'll be associated with the message in processResponse.

      // Process first response
      await processResponse(response.first_response);

      // Reset processing flag so auto-continue can work
      processingRef.current = false;

    } catch (err) {
      console.error('Failed to start conversation:', err);
      setError(`Failed to start conversation: ${String(err)}`);
      setIsLoading(false);
      setStatus({ stage: 'idle' });
      processingRef.current = false;
    }
  };

  // ---------------------------------------------------------------------------
  // PROCESS RESPONSE (TTS + Display)
  // ---------------------------------------------------------------------------

  const processResponse = async (response: ConversationMessage) => {
    const qube = getQubeById(response.speaker_id);
    const messageId = `${response.conversation_id}-${response.turn_number}`;

    // Guard: Prevent duplicate messages
    const existingMessage = conversationHistoryRef.current.find((m: DisplayMessage) => m.id === messageId);
    if (existingMessage) {
      console.log(`[ProcessResponse] Message ${messageId} already exists, skipping duplicate`);
      return;
    }

    isPlayingRef.current = true;

    // Generate TTS if enabled
    if (qube?.tts_enabled !== false && qube?.voice_model) {
      setStatus({ stage: 'generating_tts', speakerName: response.speaker_name, speakerId: response.speaker_id });

      try {
        const ttsText = truncateForTTS(cleanContentForDisplay(response.message));
        await playTTS(userId!, qube.qube_id, ttsText, password!);
      } catch (err) {
        console.error('TTS error:', err);
        // Continue without TTS
      }
    }

    // Associate pending tool calls (from real-time events) with this message
    // Also add any tool calls from response that weren't captured in real-time
    setActiveToolCalls(prev => {
      // First, associate any pending tool calls from this speaker with this message
      const updated = prev.map(tc => {
        if (!tc.messageId && tc.speakerId === response.speaker_id) {
          return { ...tc, messageId };
        }
        return tc;
      });

      // Then add any tool calls from response that we don't already have (by timestamp)
      if (response.tool_calls && response.tool_calls.length > 0) {
        const existingTimestamps = new Set(updated.map(t => t.timestamp));
        const newToolCalls = response.tool_calls
          .filter(tc => !existingTimestamps.has(tc.timestamp))
          .map(tc => ({
            action_type: tc.action_type,
            timestamp: tc.timestamp,
            speakerId: response.speaker_id,
            status: tc.status,
            input: tc.parameters,
            result: tc.result,
            messageId,
          }));
        return [...updated, ...newToolCalls].sort((a, b) => a.timestamp - b.timestamp);
      }

      return updated;
    });

    // Add message to history
    const displayMessage: DisplayMessage = {
      id: messageId,
      speakerId: response.speaker_id,
      speakerName: response.speaker_name,
      content: response.message,
      timestamp: new Date(response.timestamp * 1000),
      turnNumber: response.turn_number,
    };

    setConversationHistory(prev => [...prev, displayMessage]);
    setStatus({ stage: 'playing', speakerName: response.speaker_name, speakerId: response.speaker_id });
    setActiveTypewriterMessageId(messageId);
    setIsLoading(false);

    // Track current and next speaker
    setCurrentSpeakerId(response.speaker_id);
    console.log(`[GroupChat] Response from ${response.speaker_name}, next_speaker_id: ${response.next_speaker_id || 'none'}`);

    if (response.next_speaker_id) {
      setNextSpeakerId(response.next_speaker_id);

      // Start prefetching next response while this one plays
      if (shouldContinueRef.current && !isPaused) {
        // Small delay to let React flush state updates
        setTimeout(() => {
          if (shouldContinueRef.current && !isPaused) {
            startPipelinePrefetch(response.next_speaker_id!, response.turn_number, response.conversation_id);
          }
        }, 100);
      }
    }
  };

  // ---------------------------------------------------------------------------
  // PIPELINE PREFETCH (Fetch next response + TTS in background)
  // ---------------------------------------------------------------------------

  // Store conversationId in a ref for use in async functions
  const conversationIdRef = useRef<string | null>(null);
  useEffect(() => {
    conversationIdRef.current = conversationId;
  }, [conversationId]);

  // Store qubePipelines in a ref for polling access
  const qubePipelinesRef = useRef<Map<string, QubePipeline>>(new Map());
  useEffect(() => {
    qubePipelinesRef.current = qubePipelines;
  }, [qubePipelines]);

  // Store nextSpeakerId in a ref for consistent access in async callbacks
  const nextSpeakerIdRef = useRef<string | null>(null);
  useEffect(() => {
    nextSpeakerIdRef.current = nextSpeakerId;
  }, [nextSpeakerId]);

  const startPipelinePrefetch = useCallback(async (forQubeId: string, afterTurnNumber: number, convId?: string) => {
    // Guard: Only one fetch at a time (prevents race conditions)
    if (isFetchingRef.current) {
      console.log(`[Prefetch] Already fetching, skipping prefetch for ${forQubeId}`);
      return;
    }

    // Check if already fetching for this qube
    const existingPipeline = qubePipelinesRef.current.get(forQubeId);
    if (existingPipeline && existingPipeline.status !== 'idle') {
      console.log(`[Prefetch] Qube ${forQubeId} already active (${existingPipeline.status}), skipping`);
      return;
    }

    // Use passed convId or fall back to ref
    const activeConversationId = convId || conversationIdRef.current;
    if (!activeConversationId || !userId || !password) {
      console.log(`[Prefetch] Missing required data`);
      return;
    }

    console.log(`[Prefetch] Starting for qube ${forQubeId} after turn ${afterTurnNumber}`);
    isFetchingRef.current = true;

    // Mark pipeline as processing
    updatePipeline(forQubeId, { status: 'processing' });

    // Also set status for immediate feedback (fallback for status indicator)
    setStatus({ stage: 'processing' });

    try {
      const participantIds = selectedQubes.map(q => q.qube_id);

      const response = await invoke<ConversationMessage | null>('continue_multi_qube_conversation', {
        userId,
        conversationId: activeConversationId,
        password,
        skipTools: false,
        participantIds: JSON.stringify(participantIds),
      });

      if (!response) {
        console.log(`[Prefetch] No response (conversation ended)`);
        updatePipeline(forQubeId, { status: 'idle', pendingResponse: null });
        isFetchingRef.current = false;
        return;
      }

      console.log(`[Prefetch] Got response from ${response.speaker_name}, turn ${response.turn_number}`);
      currentTurnRef.current = response.turn_number;

      // If actual speaker differs from expected, clear the expected pipeline
      if (response.speaker_id !== forQubeId) {
        console.log(`[Prefetch] Speaker mismatch: expected ${forQubeId}, got ${response.speaker_id}`);
        updatePipeline(forQubeId, { status: 'idle', pendingResponse: null, prefetchedAudio: null });
        // Update nextSpeakerId to actual speaker
        setNextSpeakerId(response.speaker_id);
      }

      // Store response in actual speaker's pipeline
      updatePipeline(response.speaker_id, {
        status: 'generating_tts',
        pendingResponse: response,
        qubeName: response.speaker_name,
      });

      // Update status with actual speaker info
      setStatus({ stage: 'generating_tts', speakerName: response.speaker_name, speakerId: response.speaker_id });

      // Track who speaks AFTER this response (for the next prefetch cycle)
      // But only update nextSpeakerId if speaker matched (otherwise we already updated it above)
      if (response.next_speaker_id && response.speaker_id === forQubeId) {
        // Don't update nextSpeakerId here - we need to play current response first
        // nextSpeakerId should stay as the current prefetch target until it's played
      }

      // Prefetch TTS
      const qube = getQubeById(response.speaker_id);
      if (qube?.tts_enabled !== false && qube?.voice_model) {
        try {
          const cleanedMessage = truncateForTTS(cleanContentForDisplay(response.message));
          const audioUrl = await prefetchTTS(userId, qube.qube_id, cleanedMessage, password);

          updatePipeline(response.speaker_id, {
            status: 'ready',
            prefetchedAudio: audioUrl,
          });
          console.log(`[Prefetch] Qube ${response.speaker_name} ready with TTS`);
        } catch (err) {
          console.error(`[Prefetch] TTS error:`, err);
          // Still mark as ready, TTS will generate on play
          updatePipeline(response.speaker_id, {
            status: 'ready',
            prefetchedAudio: null,
          });
        }
      } else {
        // No TTS needed, mark as ready
        updatePipeline(response.speaker_id, {
          status: 'ready',
          prefetchedAudio: null,
        });
        console.log(`[Prefetch] Qube ${response.speaker_name} ready (no TTS)`);
      }

    } catch (err) {
      console.error(`[Prefetch] Error for qube ${forQubeId}:`, err);
      updatePipeline(forQubeId, { status: 'idle', pendingResponse: null });
    } finally {
      isFetchingRef.current = false;
    }
  }, [userId, password, selectedQubes, getQubeById, updatePipeline, prefetchTTS]);

  // ---------------------------------------------------------------------------
  // PLAY PREFETCHED RESPONSE
  // ---------------------------------------------------------------------------

  const playPrefetchedResponse = useCallback(async (pipeline: QubePipeline) => {
    if (!pipeline.pendingResponse) return;

    // Guard: Don't start if already playing
    if (isPlayingRef.current) {
      console.log(`[Prefetch] Already playing, skipping`);
      return;
    }

    const response = pipeline.pendingResponse;
    const messageId = `${response.conversation_id}-${response.turn_number}`;

    // Guard: Check if this message already exists (prevents duplicates)
    const existingMessage = conversationHistoryRef.current.find((m: DisplayMessage) => m.id === messageId);
    if (existingMessage) {
      console.log(`[Prefetch] Message ${messageId} already exists, skipping duplicate`);
      // Clear the pipeline since message is already displayed
      updatePipeline(response.speaker_id, { status: 'idle', pendingResponse: null, prefetchedAudio: null });
      return;
    }

    isPlayingRef.current = true;
    console.log(`[Prefetch] Playing prefetched response from ${response.speaker_name}`);

    // Associate pending tool calls (from real-time events) with this message
    // Also add any tool calls from response that weren't captured in real-time
    setActiveToolCalls(prev => {
      // First, associate any pending tool calls from this speaker with this message
      const updated = prev.map(tc => {
        if (!tc.messageId && tc.speakerId === response.speaker_id) {
          return { ...tc, messageId };
        }
        return tc;
      });

      // Then add any tool calls from response that we don't already have (by timestamp)
      if (response.tool_calls && response.tool_calls.length > 0) {
        const existingTimestamps = new Set(updated.map(t => t.timestamp));
        const newToolCalls = response.tool_calls
          .filter(tc => !existingTimestamps.has(tc.timestamp))
          .map(tc => ({
            action_type: tc.action_type,
            timestamp: tc.timestamp,
            speakerId: response.speaker_id,
            status: tc.status,
            input: tc.parameters,
            result: tc.result,
            messageId,
          }));
        return [...updated, ...newToolCalls].sort((a, b) => a.timestamp - b.timestamp);
      }

      return updated;
    });

    // Play TTS - use prefetched audio if available, otherwise generate
    const qube = getQubeById(response.speaker_id);
    if (qube?.tts_enabled !== false && qube?.voice_model) {
      if (pipeline.prefetchedAudio) {
        // Use prefetched TTS - instant playback!
        console.log(`[Prefetch] Using prefetched TTS audio`);
        try {
          const ttsText = truncateForTTS(cleanContentForDisplay(response.message));
          await playPrefetchedTTS(pipeline.prefetchedAudio, ttsText);
        } catch (err) {
          console.error('Prefetched TTS playback error:', err);
        }
      } else {
        // No prefetched audio, generate now
        setStatus({ stage: 'generating_tts', speakerName: response.speaker_name, speakerId: response.speaker_id });
        try {
          const ttsText = truncateForTTS(cleanContentForDisplay(response.message));
          await playTTS(userId!, qube.qube_id, ttsText, password!);
        } catch (err) {
          console.error('TTS error:', err);
        }
      }
    }

    // Add message to history
    const displayMessage: DisplayMessage = {
      id: messageId,
      speakerId: response.speaker_id,
      speakerName: response.speaker_name,
      content: response.message,
      timestamp: new Date(response.timestamp * 1000),
      turnNumber: response.turn_number,
    };

    setConversationHistory(prev => [...prev, displayMessage]);
    setStatus({ stage: 'playing', speakerName: response.speaker_name, speakerId: response.speaker_id });
    setActiveTypewriterMessageId(messageId);
    setCurrentSpeakerId(response.speaker_id);
    setIsLoading(false);

    // Clear this pipeline
    updatePipeline(response.speaker_id, {
      status: 'idle',
      pendingResponse: null,
      prefetchedAudio: null,
    });

    // Start prefetch for NEXT speaker (if conversation should continue)
    if (response.next_speaker_id && shouldContinueRef.current && !isPaused) {
      // Small delay to let state settle
      setTimeout(() => {
        if (shouldContinueRef.current && !isPaused) {
          startPipelinePrefetch(response.next_speaker_id!, response.turn_number, response.conversation_id);
        }
      }, 100);
    }
  }, [userId, password, getQubeById, updatePipeline, playTTS, playPrefetchedTTS, isPaused, startPipelinePrefetch]);

  // ---------------------------------------------------------------------------
  // TYPEWRITER COMPLETE HANDLER
  // ---------------------------------------------------------------------------

  const handleTypewriterComplete = useCallback(() => {
    console.log('[Typewriter] Complete');
    isPlayingRef.current = false;  // Allow next response to play
    setActiveTypewriterMessageId(null);
    setCurrentSpeakerId(null);

    // Check if we should auto-continue
    if (!isConversationActive || !shouldContinueRef.current || isPaused) {
      setStatus({ stage: 'idle' });
      return;
    }

    // The useEffect with 500ms delay will handle triggering the next response
    // This ensures consistent timing between speakers
    console.log('[Typewriter] Waiting for 500ms before next response...');
  }, [isConversationActive, isPaused]);

  // ---------------------------------------------------------------------------
  // POLL FOR READY PREFETCH (when typewriter done but prefetch still running)
  // ---------------------------------------------------------------------------

  // Ref to track the polling interval for cleanup
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    // Only run if no typewriter and conversation active
    if (activeTypewriterMessageId) return;
    if (!isConversationActive || !shouldContinueRef.current || isPaused) return;
    // Don't start if still playing (TTS might be finishing)
    if (isPlayingRef.current) return;

    // Add 500ms delay before starting next response (natural pause between speakers)
    const delayTimer = setTimeout(() => {
      // Re-check conditions after delay
      if (!isConversationActive || !shouldContinueRef.current || isPaused) return;
      if (isPlayingRef.current) return;

      // First, check if there's already a ready pipeline to play
      for (const [, pipeline] of qubePipelinesRef.current) {
        if (pipeline.status === 'ready' && pipeline.pendingResponse) {
          console.log(`[Prefetch] Found ready pipeline, playing ${pipeline.qubeName}`);
          playPrefetchedResponse(pipeline);
          return;
        }
      }

      // Check if any pipeline is still processing (need to poll for it)
      let anyProcessing = false;
      for (const [, pipeline] of qubePipelinesRef.current) {
        if (pipeline.status === 'processing' || pipeline.status === 'generating_tts') {
          anyProcessing = true;
          break;
        }
      }

      // If no prefetch in progress, continue sequentially
      if (!anyProcessing) {
        console.log('[AutoContinue] No prefetch in progress, continuing sequentially');
        if (!isFetchingRef.current) {
          // Use invoke to continue - continueConversation may not be defined yet
          const doSequentialContinue = async () => {
            if (!conversationId || !userId || !password || processingRef.current) return;
            processingRef.current = true;
            isFetchingRef.current = true;
            setIsLoading(true);
            setStatus({ stage: 'processing' });

            try {
              const participantIds = selectedQubes.map(q => q.qube_id).join(',');
              const responseStr = await invoke<string>('continue_multi_qube_conversation', {
                userId,
                conversationId,
                password,
                skipTools: false,
                participantIds,
              });

              const response = JSON.parse(responseStr) as ConversationMessage;
              isFetchingRef.current = false;
              processingRef.current = false;
              await processResponse(response);
            } catch (err) {
              console.error('[AutoContinue] Error:', err);
              isFetchingRef.current = false;
              processingRef.current = false;
              setIsLoading(false);
              setStatus({ stage: 'idle' });
            }
          };
          doSequentialContinue();
        }
        return;
      }

      console.log('[Prefetch] Polling for ready pipeline...');

      // Clear any existing poll interval
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }

      pollIntervalRef.current = setInterval(() => {
        if (!shouldContinueRef.current || isPaused || isPlayingRef.current) {
          if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
          pollIntervalRef.current = null;
          return;
        }

        const pipelines = qubePipelinesRef.current;
        for (const [, pipeline] of pipelines) {
          if (pipeline.status === 'ready' && pipeline.pendingResponse) {
            console.log(`[Prefetch] Pipeline ready, playing ${pipeline.qubeName}`);
            if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
            pollIntervalRef.current = null;
            playPrefetchedResponse(pipeline);
            return;
          }
        }
      }, 100);
    }, 500); // 500ms pause between speakers

    return () => {
      clearTimeout(delayTimer);
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    };
  }, [activeTypewriterMessageId, isConversationActive, isPaused, qubePipelines, playPrefetchedResponse, conversationId, userId, password, selectedQubes, processResponse]);

  // ---------------------------------------------------------------------------
  // CONTINUE CONVERSATION
  // ---------------------------------------------------------------------------

  const continueConversation = async () => {
    if (!conversationId || !userId || !password || processingRef.current) return;
    if (!shouldContinueRef.current || isPaused) return;

    // Don't call if prefetch is already fetching
    if (isFetchingRef.current) {
      console.log('[GroupChat] Skipping continue - prefetch in progress');
      return;
    }

    processingRef.current = true;
    isFetchingRef.current = true;  // Mark as fetching
    setIsLoading(true);

    // Use nextSpeakerId if we know who's next, otherwise show generic
    const nextQube = nextSpeakerId ? getQubeById(nextSpeakerId) : undefined;
    setStatus({
      stage: 'processing',
      speakerName: nextQube?.name,
      speakerId: nextSpeakerId || undefined
    });

    try {
      const participantIds = selectedQubes.map(q => q.qube_id);

      const response = await invoke<ConversationMessage | null>('continue_multi_qube_conversation', {
        userId,
        conversationId,
        password,
        skipTools: false,
        participantIds: JSON.stringify(participantIds),
      });

      if (!response) {
        // Conversation ended
        console.log('[GroupChat] Conversation ended (no response)');
        setIsConversationActive(false);
        shouldContinueRef.current = false;
        setIsLoading(false);
        setStatus({ stage: 'idle' });
        processingRef.current = false;
        isFetchingRef.current = false;
        return;
      }

      console.log('[GroupChat] Got response from:', response.speaker_name);
      currentTurnRef.current = response.turn_number;

      await processResponse(response);
      processingRef.current = false;
      isFetchingRef.current = false;

    } catch (err) {
      console.error('Failed to continue conversation:', err);
      setError(`Error: ${String(err)}`);
      setIsLoading(false);
      setStatus({ stage: 'idle' });
      processingRef.current = false;
      isFetchingRef.current = false;
    }
  };

  // ---------------------------------------------------------------------------
  // PAUSE / RESUME
  // ---------------------------------------------------------------------------

  const handlePause = () => {
    // Don't stop audio - let current response finish
    // Just prevent auto-continue after this message
    setIsPaused(true);
    shouldContinueRef.current = false;
    // Note: We don't call stopAudio() here - let TTS/typewriter finish naturally
    // Also don't clear pipelines - resume can pick up where we left off
  };

  const handleResume = () => {
    setIsPaused(false);
    shouldContinueRef.current = true;

    // If not currently processing or playing, continue conversation
    if (!activeTypewriterMessageId && !isLoading) {
      continueConversation();
    }
  };

  const handleStop = () => {
    setIsConversationActive(false);
    shouldContinueRef.current = false;
    setIsPaused(false);
    stopAudio();
    setStatus({ stage: 'idle' });
    setIsLoading(false);
    clearAllPipelines();  // Clear all prefetch state
    processingRef.current = false;
    isFetchingRef.current = false;
  };

  // ---------------------------------------------------------------------------
  // USER MESSAGE INJECTION
  // ---------------------------------------------------------------------------

  const injectUserMessage = async () => {
    if (!inputValue.trim() || !conversationId || !userId || !password) return;

    const messageText = inputValue;
    setInputValue('');

    // Add to display
    const userMessage: DisplayMessage = {
      id: `user-${Date.now()}`,
      speakerId: 'user',
      speakerName: userId!,
      content: messageText,
      timestamp: new Date(),
      turnNumber: currentTurnRef.current + 1,
      isUser: true,
    };
    setConversationHistory(prev => [...prev, userMessage]);
    forceScrollToBottom();

    // Send to backend
    try {
      await invoke('inject_multi_qube_user_message', {
        userId,
        conversationId,
        message: messageText,
        password,
      });

      // Resume if paused
      if (isPaused) {
        handleResume();
      } else if (!isLoading && !activeTypewriterMessageId) {
        continueConversation();
      }
    } catch (err) {
      console.error('Failed to inject message:', err);
      setError(`Failed to send message: ${String(err)}`);
    }
  };

  // ---------------------------------------------------------------------------
  // RENDER HELPERS
  // ---------------------------------------------------------------------------

  const renderMessageContent = (content: string) => {
    const cleaned = cleanContentForDisplay(content);
    const imageUrlRegex = /(https?:\/\/[^\s\)]+?(?:\.(?:png|jpg|jpeg|gif|webp)|blob\.core\.windows\.net\/[^\s\)]+))/gi;
    const imageUrls = cleaned.match(imageUrlRegex) || [];
    const textContent = cleaned.replace(imageUrlRegex, '').trim();

    return (
      <>
        {imageUrls.map((url, index) => (
          <img
            key={`img-${index}`}
            src={url}
            alt="Generated"
            className="max-w-full rounded-lg mb-3 block"
            style={{ maxHeight: '400px', objectFit: 'contain' }}
          />
        ))}
        <span>{textContent}</span>
      </>
    );
  };

  // ---------------------------------------------------------------------------
  // RENDER
  // ---------------------------------------------------------------------------

  return (
    <div className="flex-1 flex flex-col gap-4 overflow-hidden">
      {/* Header - large avatar with credentials stacked vertically */}
      <GlassCard className="p-4">
        <div className="flex items-center gap-8 overflow-x-auto">
          {selectedQubes.map((qube, index) => (
            <div
              key={qube.qube_id}
              className={`flex items-center gap-4 flex-shrink-0 ${index > 0 ? 'pl-8 border-l border-glass-border' : ''}`}
            >
              {/* Large Avatar */}
              <img
                src={getAvatarPath(qube)}
                alt={`${qube.name} avatar`}
                className="w-20 h-20 rounded-xl object-cover shadow-lg transition-transform hover:scale-105"
                style={{
                  border: `3px solid ${qube.favorite_color}`,
                  boxShadow: `0 0 20px ${qube.favorite_color}40`
                }}
                onError={(e) => {
                  const target = e.target as HTMLImageElement;
                  target.style.display = 'none';
                }}
              />

              {/* Credentials stacked vertically - no labels */}
              <div className="flex flex-col gap-0.5">
                <span className="text-xl font-display font-bold" style={{ color: qube.favorite_color }}>
                  {qube.name}
                </span>
                <span className="text-base font-display font-medium flex items-center gap-1" style={{ color: qube.favorite_color }}>
                  🤖 {formatModelName(qube.ai_model)}
                </span>
                <span className="text-base font-display font-medium flex items-center gap-1" style={{ color: qube.favorite_color }}>
                  🎤 {formatVoiceDisplay(qube.voice_model)}
                </span>
              </div>
            </div>
          ))}

          {/* Pause/Resume/Stop buttons - right side */}
          {isConversationActive && (
            <div className="flex items-center gap-2 ml-auto flex-shrink-0">
              {isPaused ? (
                <GlassButton onClick={handleResume} size="sm">
                  Resume
                </GlassButton>
              ) : (
                <GlassButton onClick={handlePause} size="sm">
                  Pause
                </GlassButton>
              )}
              <GlassButton onClick={handleStop} size="sm" variant="danger">
                Stop
              </GlassButton>
            </div>
          )}
        </div>
      </GlassCard>

      {/* Messages Area */}
      <GlassCard className="flex-1 p-4 overflow-hidden flex flex-col">
        <div
          ref={messagesContainerRef}
          onScroll={handleScroll}
          className="flex-1 overflow-y-auto"
        >
          {conversationHistory.length === 0 ? (
            <div className="h-full flex items-center justify-center">
              <p className="text-text-tertiary text-center">
                Start a conversation with {selectedQubes.map(q => q.name).join(' & ')}
              </p>
            </div>
          ) : (
            <div className="space-y-4 pb-4">
              {(() => {
                // Sort tool calls by timestamp (oldest first)
                const sortedToolCalls = [...activeToolCalls].sort((a, b) => a.timestamp - b.timestamp);

                // Get tool calls that belong to a specific message
                // Only uses messageId for stable association
                const getToolCallsForMessage = (message: DisplayMessage) => {
                  if (message.isUser) return [];
                  return sortedToolCalls.filter(tool => tool.messageId === message.id);
                };

                // Get remaining tool calls (not associated with any message yet)
                // These are shown as pending at the bottom
                const getPendingToolCalls = () => {
                  return sortedToolCalls.filter(tool => !tool.messageId);
                };

                return (
                  <>
                    {conversationHistory.map((message) => {
                      const toolCallsForMessage = getToolCallsForMessage(message);

                      return (
                        <React.Fragment key={message.id}>
                          {/* Tool calls that led to this message */}
                          {toolCallsForMessage.map((tool, index) => {
                            const qube = getQubeById(tool.speakerId);
                            const color = getQubeColor(tool.speakerId);
                            return (
                              <div key={`tool-${tool.timestamp}-${index}`} className="flex justify-start">
                                <div className="max-w-[70%]">
                                  <ToolCallBubble
                                    toolName={tool.action_type}
                                    input={tool.input}
                                    result={tool.result}
                                    status={tool.status}
                                    accentColor={color}
                                    timestamp={tool.timestamp}
                                    label={qube?.name}
                                    avatarUrl={qube ? getAvatarPath(qube) : undefined}
                                  />
                                </div>
                              </div>
                            );
                          })}

                          {/* The message itself */}
                          <div className={`flex ${message.isUser ? 'justify-end' : 'justify-start'}`}>
                            <div
                              className={`max-w-[70%] rounded-lg p-3 border-2 ${
                                message.isUser
                                  ? 'bg-accent-primary/20 text-text-primary border-accent-primary'
                                  : 'bg-bg-tertiary text-text-primary'
                              }`}
                              style={
                                !message.isUser
                                  ? { borderColor: getQubeColor(message.speakerId) }
                                  : undefined
                              }
                            >
                              {/* Speaker Name with Avatar */}
                              <div className="flex items-center gap-2 mb-2">
                                {!message.isUser && getQubeById(message.speakerId) && (
                                  <img
                                    src={getAvatarPath(getQubeById(message.speakerId)!)}
                                    alt={message.speakerName}
                                    className="w-8 h-8 rounded-full object-cover border-2"
                                    style={{
                                      borderColor: getQubeColor(message.speakerId),
                                      boxShadow: `0 0 8px ${getQubeColor(message.speakerId)}60`
                                    }}
                                    onError={(e) => {
                                      const target = e.target as HTMLImageElement;
                                      target.style.display = 'none';
                                    }}
                                  />
                                )}
                                <p className="text-sm font-medium" style={{
                                  color: message.isUser ? 'var(--accent-primary)' : getQubeColor(message.speakerId)
                                }}>
                                  {message.speakerName}
                                </p>
                              </div>
                              <div className="whitespace-pre-wrap break-words">
                                {activeTypewriterMessageId === message.id ? (
                                  <TypewriterText
                                    text={cleanContentForDisplay(message.content)}
                                    audioElement={audioElement}
                                    onComplete={handleTypewriterComplete}
                                  />
                                ) : (
                                  renderMessageContent(message.content)
                                )}
                              </div>
                            </div>
                          </div>
                        </React.Fragment>
                      );
                    })}

                    {/* Pending tool calls (for message currently being generated) */}
                    {getPendingToolCalls().map((tool, index) => {
                      const qube = getQubeById(tool.speakerId);
                      const color = getQubeColor(tool.speakerId);
                      return (
                        <div key={`pending-tool-${tool.timestamp}-${index}`} className="flex justify-start">
                          <div className="max-w-[70%]">
                            <ToolCallBubble
                              toolName={tool.action_type}
                              input={tool.input}
                              result={tool.result}
                              status={tool.status}
                              accentColor={color}
                              timestamp={tool.timestamp}
                              label={qube?.name}
                              avatarUrl={qube ? getAvatarPath(qube) : undefined}
                            />
                          </div>
                        </div>
                      );
                    })}
                  </>
                );
              })()}

              {/* Processing/TTS/Prefetch Status Indicator */}
              {(() => {
                // Check if there are in-progress tool calls - if so, don't show this indicator
                // (the tool call bubbles themselves serve as the indicator)
                if (activeToolCalls.some(t => t.status === 'in_progress' && !t.messageId)) {
                  return null;
                }

                // Determine what to show:
                // 1. Check pending tool calls - if we have them, we know who's responding
                // 2. Check all pipelines for prefetch activity
                // 3. Fall back to status-based indicator (sequential mode)
                let speakerId: string | undefined;
                let speakerName: string | undefined;
                let displayText: string = '';

                // First check pending tool calls - if we have completed ones, we KNOW who's responding
                const pendingToolCalls = activeToolCalls.filter(t => !t.messageId);
                if (pendingToolCalls.length > 0) {
                  const firstTool = pendingToolCalls[0];
                  speakerId = firstTool.speakerId;
                  const qube = getQubeById(firstTool.speakerId);
                  speakerName = qube?.name;
                  // Use current status stage to determine text
                  displayText = status.stage === 'generating_tts' ? 'generating audio' : 'processing response';
                }

                // Check pipelines for prefetch activity (if no pending tool calls)
                if (!speakerId && isConversationActive) {
                  for (const [qubeId, pipeline] of qubePipelines) {
                    if (pipeline.status === 'processing') {
                      // Still fetching - check if we have tool calls to know who
                      displayText = 'processing response';
                      break;
                    } else if (pipeline.status === 'generating_tts' || pipeline.status === 'ready') {
                      // We have the response, show the actual speaker
                      speakerId = qubeId;
                      speakerName = pipeline.qubeName;
                      displayText = pipeline.status === 'ready' ? 'ready' : 'generating audio';
                      break;
                    }
                  }
                }

                // Fall back to status-based indicator (sequential mode)
                if (!speakerId && (status.stage === 'processing' || status.stage === 'generating_tts')) {
                  speakerId = status.speakerId;
                  speakerName = status.speakerName;
                  displayText = status.stage === 'generating_tts' ? 'generating audio' : 'processing response';
                }

                // Nothing specific to show - check if we're still loading/processing
                if (!speakerId) {
                  if (isLoading || status.stage === 'processing') {
                    // Show generic processing indicator
                    displayText = 'processing response';
                  } else {
                    return null;
                  }
                }

                const qube = speakerId ? getQubeById(speakerId) : undefined;
                const color = speakerId ? getQubeColor(speakerId) : '#8B5CF6';
                const name = speakerName || qube?.name;

                return (
                  <div className="flex justify-start">
                    <div className="rounded-lg px-4 py-2 border-2" style={{
                      backgroundColor: 'var(--bg-tertiary)',
                      borderColor: color,
                    }}>
                      <div className="flex items-center gap-3">
                        {qube && (
                          <img
                            src={getAvatarPath(qube)}
                            alt={name || qube.name}
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
                          {name ? (
                            <>
                              <span className="text-sm font-medium" style={{ color }}>
                                {name}
                              </span>
                              <span className="text-xs text-text-secondary">
                                {displayText}
                              </span>
                            </>
                          ) : (
                            <span className="text-sm text-text-secondary">
                              {displayText || 'processing response'}
                            </span>
                          )}
                          {displayText === 'ready' ? (
                            <span style={{ color }}>✓</span>
                          ) : (
                            <div className="flex gap-1">
                              <div className="w-1.5 h-1.5 rounded-full animate-pulse" style={{
                                backgroundColor: color,
                                animationDuration: '1s'
                              }}></div>
                              <div className="w-1.5 h-1.5 rounded-full animate-pulse" style={{
                                backgroundColor: color,
                                animationDuration: '1s',
                                animationDelay: '0.2s'
                              }}></div>
                              <div className="w-1.5 h-1.5 rounded-full animate-pulse" style={{
                                backgroundColor: color,
                                animationDuration: '1s',
                                animationDelay: '0.4s'
                              }}></div>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })()}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Error display */}
        {error && (
          <div className="mt-3 p-3 bg-red-500/20 border border-red-500/50 rounded-lg text-red-200 text-sm">
            {error}
            <button
              onClick={() => setError(null)}
              className="ml-2 text-red-300 hover:text-red-100"
            >
              ✕
            </button>
          </div>
        )}
      </GlassCard>

      {/* Input Area - separate GlassCard like ChatInterface */}
      <GlassCard className="p-4">
        {/* Uploaded files */}
        {uploadedFiles.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-3">
            {uploadedFiles.map((file, index) => (
              <div
                key={index}
                className="relative p-2 bg-bg-tertiary rounded-lg border-2 border-accent-primary/50 flex flex-col items-center"
                style={{ width: '120px' }}
              >
                {file.type === 'image' ? (
                  <img
                    src={file.data}
                    alt={file.name}
                    className="w-20 h-20 rounded object-cover mb-1"
                  />
                ) : (
                  <div className="w-20 h-20 rounded bg-accent-primary/20 flex items-center justify-center text-3xl mb-1">
                    📄
                  </div>
                )}
                <p className="text-text-primary text-xs font-medium truncate w-full text-center" title={file.name}>
                  {file.name.length > 12 ? file.name.substring(0, 12) + '...' : file.name}
                </p>
                <button
                  onClick={() => removeFile(index)}
                  className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-accent-danger text-white hover:bg-accent-danger/80 transition-all flex items-center justify-center text-xs"
                  title="Remove file"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        )}

        <div className="flex gap-2 relative">
          <button
            onClick={isRecording ? stopRecording : startRecording}
            className={`px-3 py-2 rounded-lg transition-all ${
              isRecording
                ? 'bg-accent-danger/20 text-accent-danger animate-pulse'
                : 'bg-bg-secondary text-text-secondary hover:text-accent-primary hover:bg-bg-tertiary'
            }`}
            title={isRecording ? 'Stop recording' : 'Start voice input'}
            disabled={isLoading}
          >
            {isRecording ? '🔴' : '🎤'}
          </button>
          <button
            onClick={handleFileUpload}
            className="px-3 py-2 rounded-lg transition-all bg-bg-secondary text-text-secondary hover:text-accent-primary hover:bg-bg-tertiary"
            title="Upload file or image"
            disabled={isLoading}
          >
            📎
          </button>
          <button
            onClick={() => setShowEmojiPicker(!showEmojiPicker)}
            className={`px-3 py-2 rounded-lg transition-all ${
              showEmojiPicker
                ? 'bg-accent-primary/20 text-accent-primary'
                : 'bg-bg-secondary text-text-secondary hover:text-accent-primary hover:bg-bg-tertiary'
            }`}
            title="Insert emoji"
            disabled={isLoading}
          >
            😊
          </button>
          {showEmojiPicker && (
            <div className="absolute bottom-20 left-24 z-50" ref={emojiPickerRef}>
              <EmojiPicker
                onEmojiClick={handleEmojiClick}
                theme={Theme.DARK}
                width={350}
                height={450}
                searchPlaceHolder="Search emoji..."
                previewConfig={{ showPreview: false }}
              />
            </div>
          )}
          <textarea
            ref={textareaRef}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                if (isConversationActive) {
                  injectUserMessage();
                } else {
                  startConversation();
                }
              }
            }}
            placeholder={`Message ${selectedQubes.map(q => q.name).join(' & ')}...`}
            className="flex-1 bg-bg-secondary text-text-primary placeholder-text-tertiary rounded-lg px-4 py-2 resize-none focus:outline-none focus:ring-2 focus:ring-accent-primary/50"
            rows={1}
            disabled={isLoading}
          />
          <GlassButton
            variant="primary"
            onClick={isConversationActive ? injectUserMessage : startConversation}
            disabled={(!inputValue.trim() && uploadedFiles.length === 0) || isLoading}
          >
            Send
          </GlassButton>
        </div>
      </GlassCard>
    </div>
  );
};

export default GroupChatInterface;
