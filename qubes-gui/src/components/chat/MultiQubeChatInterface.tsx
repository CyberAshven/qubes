import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { convertFileSrc } from '@tauri-apps/api/core';
import { GlassCard } from '../glass/GlassCard';
import { GlassButton } from '../glass/GlassButton';
import { Qube } from '../../types';
import { useAuth } from '../../hooks/useAuth';
import { useAudio } from '../../contexts/AudioContext';
import { TypewriterText } from './TypewriterText';
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
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conversationMode, setConversationMode] = useState<'open_discussion' | 'round_robin'>('open_discussion');
  const [activeTypewriterMessageId, setActiveTypewriterMessageId] = useState<string | null>(null);
  const [pendingTTSMessage, setPendingTTSMessage] = useState<ConversationMessage | null>(null);
  const [nextResponsePrefetch, setNextResponsePrefetch] = useState<ConversationMessage | null>(null);
  const [nextTTSPrefetch, setNextTTSPrefetch] = useState<string | null>(null);
  const [prefetchedMessageId, setPrefetchedMessageId] = useState<string | null>(null); // Track which message the TTS belongs to
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

  // Tool call indicators (shown during processing)
  const [activeToolCalls, setActiveToolCalls] = useState<Array<{
    action_type: string;
    timestamp: number;
    qube_id?: string;
  }>>([]);
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
  const typewriterReadyRef = useRef(false); // Track if typewriter is ready to start
  const lastProcessedTurnRef = useRef<number>(0); // Track the last turn number we processed
  const activeTypewriterMessageIdRef = useRef<string | null>(null); // Track active typewriter
  const prefetchCancelledRef = useRef(false); // Track if prefetch was explicitly cancelled
  const waitingForUserResponseRef = useRef(false); // Track if we're waiting for user's response from backend
  const pauseAfterCurrentMessageRef = useRef(false); // Track if we should pause after current message completes

  // Refs for prefetch state (so timer callbacks see latest values)
  const nextResponsePrefetchRef = useRef<ConversationMessage | null>(null);
  const nextTTSPrefetchRef = useRef<string | null>(null);
  const prefetchedMessageIdRef = useRef<string | null>(null);

  // Keep refs in sync with state
  useEffect(() => {
    nextResponsePrefetchRef.current = nextResponsePrefetch;
  }, [nextResponsePrefetch]);

  useEffect(() => {
    nextTTSPrefetchRef.current = nextTTSPrefetch;
  }, [nextTTSPrefetch]);

  useEffect(() => {
    prefetchedMessageIdRef.current = prefetchedMessageId;
  }, [prefetchedMessageId]);

  useEffect(() => {
    activeTypewriterMessageIdRef.current = activeTypewriterMessageId;
  }, [activeTypewriterMessageId]);

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

  // Helper function to clean content by removing image URLs
  const cleanContentForDisplay = (content: string): string => {
    // Regular expression to detect image URLs (including DALL-E Azure Blob Storage URLs)
    const imageUrlRegex = /(https?:\/\/[^\s\)]+?(?:\.(?:png|jpg|jpeg|gif|webp)|blob\.core\.windows\.net\/[^\s\)]+))/gi;
    // Regular expression to detect local Windows file paths to images (both absolute and relative)
    const localPathRegex = /([A-Za-z]:\\[^\s\)]+\.(?:png|jpg|jpeg|gif|webp)|data[\\\/][^\s\)]+\.(?:png|jpg|jpeg|gif|webp))/gi;

    // Remove complete markdown image syntax ![...](url)
    let cleaned = content.replace(/!\[([^\]]*)\]\([^\)]+\)/gi, '');

    // Remove any remaining image URLs (standalone)
    cleaned = cleaned.replace(imageUrlRegex, '');

    // Remove any local file paths
    cleaned = cleaned.replace(localPathRegex, '');

    // Remove any standalone markdown image syntax ![...]
    cleaned = cleaned.replace(/!\[([^\]]*)\]/g, '');

    // Remove empty parentheses that might be left over
    cleaned = cleaned.replace(/\(\s*\)/g, '');

    return cleaned;
  };

  // Helper function to truncate text for TTS
  // Gemini has higher limits than OpenAI, so we can increase this
  const truncateForTTS = (text: string, maxLength: number = 20000): string => {
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
        response = await invoke<ConversationMessage>('continue_multi_qube_conversation', {
          userId,
          conversationId,
          password,
        });
      }

      // Don't add to history yet - wait for TTS to start
      // setConversationHistory(prev => [...prev, response]);

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
      speaker_name: 'bit_faced',
      message: userPrompt,
      voice_model: '',
      turn_number: 0,
      conversation_id: 'pending', // Will be updated when response arrives
      is_final: false,
    };

    setConversationHistory([tempUserMessage]);
    setInputValue(''); // Clear input immediately
    setIsLoading(true);
    setError(null);
    setIsConversationActive(true);
    shouldContinueRef.current = true;

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
          speaker_name: 'bit_faced',
          message: userPrompt,
          voice_model: '',
          turn_number: 0,
          conversation_id: result.conversation_id || '',
          is_final: false,
        };

        setConversationHistory([userMessage]);
        clearUploadedFiles(`group_${selectedQubes.map(q => q.qube_id).join('_')}`);

        // Play TTS for first response
        if (result.response) {
          // Submit first response to hub
          await submitBlockToHub(result.response);
          setPendingTTSMessage(result.response);
        }
      } else {
        // LOCAL MODE: Standard multi-qube conversation
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

        setConversationId(response.conversation_id);

        // Update user's message with real conversation ID
        const userMessage: ConversationMessage = {
          speaker_id: userId,
          speaker_name: 'bit_faced',
          message: userPrompt,
          voice_model: '',
          turn_number: 0,
          conversation_id: response.conversation_id,
          is_final: false,
        };

        setConversationHistory([userMessage]);

        // Clear uploaded files after starting conversation
        clearUploadedFiles(`group_${selectedQubes.map(q => q.qube_id).join('_')}`);

        // Play TTS for first response (will be added to history when TTS starts)
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

    // Cancel ALL prefetch work immediately - it's now stale
    // Set cancellation flag FIRST
    prefetchCancelledRef.current = true;

    // Clear state immediately
    setNextResponsePrefetch(null);
    setNextTTSPrefetch(null);
    setPrefetchedMessageId(null);

    // Clear refs too (to stop ongoing operations from completing)
    nextResponsePrefetchRef.current = null;
    nextTTSPrefetchRef.current = null;
    prefetchedMessageIdRef.current = null;

    // Stop any ongoing prefetch
    isFetchingNextRef.current = false;

    // Set waiting flag to prevent auto-continue from fetching next turn
    waitingForUserResponseRef.current = true;

    // Show "User response ready" indicator
    setNextResponseStatus({
      stage: 'ready',
      qubeId: userId,
      qubeName: 'bit_faced'
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
        // Don't change status here - keep showing "bit_faced response ready"
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
    // If there's a prefetched response ready, keep it and play it before pausing
    if (nextResponsePrefetch) {
      // Set flags to pause after the prefetched message plays
      pauseAfterCurrentMessageRef.current = true;
      setIsPauseRequested(true); // Visual feedback
      shouldContinueRef.current = false;
      isFetchingNextRef.current = false;
      prefetchCancelledRef.current = false; // We're keeping this prefetch

      // If no message is currently playing, trigger the prefetched response now
      if (!pendingTTSMessage && !activeTypewriterMessageId) {
        setPendingTTSMessage(nextResponsePrefetch);
        setNextResponsePrefetch(null);
        // NOTE: Keep nextTTSPrefetch and prefetchedMessageId intact!
        // The playMessageTTS effect needs them to use the prefetched audio.
        // It will clear them after successfully playing.
      }
      // else: Don't clear the prefetch - let it play after current message finishes
    } else {
      // No prefetched response - cancel any ongoing prefetch and pause immediately
      setIsConversationActive(false);
      shouldContinueRef.current = false;
      isFetchingNextRef.current = false;
      prefetchCancelledRef.current = true; // Mark prefetch as cancelled
      pauseAfterCurrentMessageRef.current = false;
      setIsPauseRequested(false);

      // Clear any prefetch state that might be in progress
      setNextResponsePrefetch(null);
      setNextTTSPrefetch(null);
      setPrefetchedMessageId(null);
      setNextResponseStatus({ stage: 'idle' });
    }
  };

  // Resume the conversation
  const handleResumeConversation = () => {
    setIsConversationActive(true);
    shouldContinueRef.current = true;
    pauseAfterCurrentMessageRef.current = false; // Clear any pending pause
    setIsPauseRequested(false); // Clear pause requested state
    prefetchCancelledRef.current = false; // Allow new prefetches
    // Trigger next turn
    if (conversationId && !isLoading && !pendingTTSMessage) {
      // Use prefetched response if available, otherwise fetch
      if (nextResponsePrefetch) {
        setPendingTTSMessage(nextResponsePrefetch);
        setNextResponsePrefetch(null);
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
      setNextResponsePrefetch(null); // Clear any prefetched response
      setNextTTSPrefetch(null); // Clear any prefetched TTS
      setPrefetchedMessageId(null); // Clear prefetch tracking

      alert(`Conversation ended!\nTotal turns: ${summary.total_turns}\nBlocks ${anchor ? 'anchored' : 'not anchored'} to permanent chains.`);
    } catch (err) {
      console.error('Failed to end conversation:', err);
      setError(`Failed to end conversation: ${String(err)}`);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle TTS playback for pending message
  useEffect(() => {
    const playMessageTTS = async () => {
      if (!pendingTTSMessage || !userId || !password) return;

      // Create unique ID for this message
      const messageId = `${pendingTTSMessage.conversation_id}-${pendingTTSMessage.turn_number}`;

      // Skip if we're already processing this exact message (prevents duplicates)
      if (processingMessageRef.current === messageId) {
        return;
      }

      // Mark as processing and track turn number
      processingMessageRef.current = messageId;
      lastProcessedTurnRef.current = pendingTTSMessage.turn_number;

      // Try to find qube from selectedQubes first, then allQubes (for P2P connections)
      let qube = getQubeById(pendingTTSMessage.speaker_id);

      // In P2P mode, also try to find by speaker_name in allQubes
      if (!qube && isP2P && allQubes.length > 0) {
        qube = allQubes.find(q => q.name === pendingTTSMessage.speaker_name);
      }

      // Get voice model - prioritize from the response itself, then from qube
      const voiceModel = pendingTTSMessage.voice_model || qube?.voice_model;
      const ttsEnabled = qube?.tts_enabled !== false; // Default to enabled if not specified

      if (!voiceModel || !ttsEnabled) {
        // TTS disabled or no voice model - add message to history and show without TTS
        setConversationHistory(prev => [...prev, pendingTTSMessage]);
        setPendingTTSMessage(null);
        setIsLoading(false);
        setNextResponseStatus({ stage: 'idle' });
        processingMessageRef.current = null; // Clear processing flag

        // Auto-continue if conversation is still active
        if (isConversationActive && shouldContinueRef.current) {
          setTimeout(() => continueConversation(), 500);
        }
        return;
      }

      try {
        // Validate if we have prefetched TTS for THIS EXACT message
        const hasPrefetchedTTS = nextTTSPrefetch !== null && prefetchedMessageId === messageId;

        if (!hasPrefetchedTTS && nextTTSPrefetch !== null && prefetchedMessageId !== messageId) {
          console.warn(`⚠ Prefetched TTS mismatch! Expected: ${messageId}, Got: ${prefetchedMessageId}. Discarding and regenerating.`);
          // Clear mismatched prefetch
          setNextTTSPrefetch(null);
          setPrefetchedMessageId(null);
        }

        // Lock in this response as "spoken" BEFORE starting TTS
        // This marks it as prefetch=false so it won't be removed if user interjects
        if (pendingTTSMessage.timestamp && conversationId) {
          try {
            await invoke('lock_in_multi_qube_response', {
              userId,
              conversationId,
              timestamp: pendingTTSMessage.timestamp,
              password
            });
          } catch (err) {
            console.error('Failed to lock in response:', err);
            // Don't fail - continue with TTS
          }
        }

        // Check if this was a "ready to respond" case (smooth transition) or needs indicator
        const wasReady = nextResponseStatus.stage === 'ready';

        if (wasReady) {
          // Prefetched response - smooth transition: add message FIRST, then clear indicator
          setConversationHistory(prev => [...prev, pendingTTSMessage]);

          // Wait for React to render the message bubble
          await new Promise(resolve => setTimeout(resolve, 50));

          // Clear the "ready to respond" indicator now that message is visible
          setNextResponseStatus({ stage: 'idle' });
        } else {
          // First response or no prefetch - show "generating audio" indicator
          setNextResponseStatus({
            stage: 'generating_tts',
            qubeId: pendingTTSMessage.speaker_id,
            qubeName: pendingTTSMessage.speaker_name
          });
        }

        // Clean the message content to remove image URLs before TTS
        // Then truncate hex strings (addresses, tx hashes) for better TTS readability
        const cleanedMessage = truncateForTTS(cleanContentForDisplay(pendingTTSMessage.message));

        if (hasPrefetchedTTS && nextTTSPrefetch) {
          // Use prefetched TTS audio - instant playback!
          await playPrefetchedTTS(nextTTSPrefetch, cleanedMessage);
          setNextTTSPrefetch(null);
          setPrefetchedMessageId(null);
        } else if (qube) {
          // Generate TTS normally and WAIT for it to finish
          await playTTS(userId, qube.qube_id, cleanedMessage, password);
        }
        // If qube not found locally (rare case) - skip TTS but continue

        // TTS is ready! Now add message to history if we didn't already (first response case)
        if (!wasReady) {
          setConversationHistory(prev => [...prev, pendingTTSMessage]);

          // Clear the generating indicator
          setNextResponseStatus({ stage: 'idle' });
        }

        // Wait for React to render the DOM element for typewriter
        await new Promise(resolve => setTimeout(resolve, 50));

        // NOW activate typewriter - audio is playing
        setActiveTypewriterMessageId(messageId);

        // Start prefetching immediately (in parallel with TTS playback)
        // This maximizes the time available for the next qube to prepare their response
        // NOTE: PREFETCH IS DISABLED FOR P2P MODE - blocks can't be "un-sent" from hub
        const prefetchPromise = (async () => {
          // P2P MODE: Skip prefetch entirely - blocks are immediately sent to hub
          if (isP2P) {
            return;
          }

          // Small delay to ensure current message processing has set its flags
          await new Promise(resolve => setTimeout(resolve, 50));

          // Check if prefetch was cancelled before we even start
          if (prefetchCancelledRef.current) {
            return;
          }

          if (isConversationActive && shouldContinueRef.current && !isFetchingNextRef.current && !nextResponsePrefetch && conversationId && userId && password) {
            isFetchingNextRef.current = true;

            // Clear cancellation flag when starting a NEW prefetch
            prefetchCancelledRef.current = false;

            try {
              // Check again right before calling backend (race condition check)
              if (prefetchCancelledRef.current) {
                isFetchingNextRef.current = false;
                return;
              }

              // Start polling for ACTION blocks during processing
              // (we'll set processing status after we get the response and know which qube)
              const pollInterval = setInterval(async () => {
                try {
                  // Poll all participating qubes for recent ACTION blocks
                  const now = Date.now();
                  const recentActions: Array<{ action_type: string; timestamp: number; qube_id: string }> = [];

                  for (const qube of selectedQubes) {
                    try {
                      const result = await invoke<any>('get_qube_blocks', {
                        userId,
                        qubeId: qube.qube_id,
                        password,
                        limit: 50, // Only check recent blocks
                      });

                      if (result?.session_blocks && Array.isArray(result.session_blocks)) {
                        // Find ACTION blocks from the last 5 seconds (but skip prefetch actions)
                        const actionBlocks = result.session_blocks.filter((b: any) =>
                          b.block_type === 'ACTION' &&
                          b.content?.action_type &&
                          b.timestamp &&
                          (now - b.timestamp) < 5000 && // Within last 5 seconds
                          b.content?.prefetch !== true // Skip prefetch actions to avoid showing background work
                        );

                        // Add to recent actions with qube_id
                        actionBlocks.forEach((b: any) => {
                          recentActions.push({
                            action_type: b.content.action_type,
                            timestamp: b.timestamp,
                            qube_id: qube.qube_id
                          });
                        });
                      }
                    } catch (err) {
                      // Ignore errors for individual qubes
                    }
                  }

                  // Update active tool calls with unique actions
                  if (recentActions.length > 0) {
                    // Deduplicate by action_type (show each tool once even if called multiple times)
                    const uniqueActions = Array.from(
                      new Map(recentActions.map(a => [a.action_type, a])).values()
                    );
                    setActiveToolCalls(uniqueActions);
                  } else {
                    setActiveToolCalls([]);
                  }
                } catch (err) {
                  // Silently ignore polling errors
                }
              }, 500); // Poll every 500ms

              // STEP 1: Get next speaker info (lightweight call)
              const speakerInfo = await invoke<{ speaker_id: string; speaker_name: string }>('get_next_speaker', {
                userId,
                conversationId,
                password,
              });

              // Show "processing response" indicator with the specific qube
              setNextResponseStatus({
                stage: 'processing',
                qubeId: speakerInfo.speaker_id,
                qubeName: speakerInfo.speaker_name
              });

              // STEP 2: Prefetch next response - THIS IS WHERE THE ACTUAL PROCESSING HAPPENS
              const nextResponse = await invoke<ConversationMessage>('continue_multi_qube_conversation', {
                userId,
                conversationId,
                password,
              });

              // Stop polling when response is received
              clearInterval(pollInterval);

              // Clear tool call indicators
              setActiveToolCalls([]);

              // Response is now complete - processing is done, will show "generating audio" next

              // Create message ID for validation
              const nextMessageId = `${nextResponse.conversation_id}-${nextResponse.turn_number}`;

              // CHECK: Was prefetch cancelled while we were fetching?
              if (prefetchCancelledRef.current) {
                // Only clear status if it's not a user indicator (preserve "bit_faced response ready")
                setNextResponseStatus(prev =>
                  prev.qubeId === userId ? prev : { stage: 'idle' }
                );
                setActiveToolCalls([]); // Clear tool indicators

                // Delete the prefetched blocks from all participating qubes
                // The backend created blocks, so we need to query and delete them
                (async () => {
                  for (const qube of selectedQubes) {
                    try {
                      // Get all blocks for this qube
                      const blocksResponse = await invoke<any>('get_qube_blocks', {
                        userId,
                        qubeId: qube.qube_id,
                        password
                      });

                      // Find session blocks matching this turn number
                      const sessionBlocks = blocksResponse.session_blocks || [];
                      for (const block of sessionBlocks) {
                        if (block.content?.turn_number === nextResponse.turn_number) {
                          await invoke('delete_session_block', {
                            userId,
                            qubeId: qube.qube_id,
                            blockNumber: block.block_number,
                            password
                          });
                        }
                      }
                    } catch (err) {
                      console.error(`Failed to delete cancelled blocks from ${qube.name}:`, err);
                    }
                  }
                })();
                return;
              }

              setNextResponsePrefetch(nextResponse);

              // Get next speaker info
              const nextQube = getQubeById(nextResponse.speaker_id);
              if (!nextQube) {
                console.error('Next qube not found');
                setNextResponseStatus({ stage: 'idle' });
                return;
              }

              // CHECK: Status update
              if (prefetchCancelledRef.current) {
                // Only clear status if it's not a user indicator (preserve "bit_faced response ready")
                setNextResponseStatus(prev =>
                  prev.qubeId === userId ? prev : { stage: 'idle' }
                );
                return;
              }

              // Also prefetch the TTS for this next response
              if (nextQube && nextQube.tts_enabled) {
                try {
                  // Now update status: Generating TTS for next response
                  setNextResponseStatus({
                    stage: 'generating_tts',
                    qubeId: nextQube.qube_id,
                    qubeName: nextQube.name
                  });

                  // Clean the message content to remove image URLs before TTS
                  // Then truncate hex strings (addresses, tx hashes) for better TTS readability
                  const cleanedMessage = truncateForTTS(cleanContentForDisplay(nextResponse.message));
                  const prefetchedAudio = await prefetchTTS(userId, nextQube.qube_id, cleanedMessage, password);

                  // CHECK AGAIN: Was prefetch cancelled while we were generating TTS?
                  if (prefetchCancelledRef.current) {
                    // Only clear status if it's not a user indicator (preserve "bit_faced response ready")
                    setNextResponseStatus(prev =>
                      prev.qubeId === userId ? prev : { stage: 'idle' }
                    );

                    // Delete blocks from all qubes
                    (async () => {
                      for (const qube of selectedQubes) {
                        try {
                          const blocksResponse = await invoke<any>('get_qube_blocks', {
                            userId,
                            qubeId: qube.qube_id,
                            password
                          });

                          const sessionBlocks = blocksResponse.session_blocks || [];
                          for (const block of sessionBlocks) {
                            if (block.content?.turn_number === nextResponse.turn_number) {
                              await invoke('delete_session_block', {
                                userId,
                                qubeId: qube.qube_id,
                                blockNumber: block.block_number,
                                password
                              });
                            }
                          }
                        } catch (err) {
                          console.error(`Failed to delete cancelled blocks from ${qube.name}:`, err);
                        }
                      }
                    })();
                    return;
                  }

                  // Store BOTH the audio and which message it belongs to
                  setNextTTSPrefetch(prefetchedAudio);
                  setPrefetchedMessageId(nextMessageId);

                  // CHECK ONE MORE TIME before showing "ready"
                  if (prefetchCancelledRef.current) {
                    setNextResponsePrefetch(null);
                    setNextTTSPrefetch(null);
                    setPrefetchedMessageId(null);
                    // Only clear status if it's not a user indicator (preserve "bit_faced response ready")
                    setNextResponseStatus(prev =>
                      prev.qubeId === userId ? prev : { stage: 'idle' }
                    );

                    // Delete blocks from all qubes
                    (async () => {
                      for (const qube of selectedQubes) {
                        try {
                          const blocksResponse = await invoke<any>('get_qube_blocks', {
                            userId,
                            qubeId: qube.qube_id,
                            password
                          });

                          const sessionBlocks = blocksResponse.session_blocks || [];
                          for (const block of sessionBlocks) {
                            if (block.content?.turn_number === nextResponse.turn_number) {
                              await invoke('delete_session_block', {
                                userId,
                                qubeId: qube.qube_id,
                                blockNumber: block.block_number,
                                password
                              });
                            }
                          }
                        } catch (err) {
                          console.error(`Failed to delete cancelled blocks from ${qube.name}:`, err);
                        }
                      }
                    })();
                    return;
                  }

                  // Update status: Ready!
                  setNextResponseStatus({
                    stage: 'ready',
                    qubeId: nextQube.qube_id,
                    qubeName: nextQube.name
                  });
                } catch (err) {
                  console.error('Failed to prefetch TTS:', err);
                  setPrefetchedMessageId(null);
                  // Only clear status if it's not a user indicator (preserve "bit_faced response ready")
                  setNextResponseStatus(prev =>
                    prev.qubeId === userId ? prev : { stage: 'idle' }
                  );
                }
              } else {
                setPrefetchedMessageId(null);
                // No TTS needed, mark as ready (if not cancelled)
                if (nextQube && !prefetchCancelledRef.current) {
                  setNextResponseStatus({
                    stage: 'ready',
                    qubeId: nextQube.qube_id,
                    qubeName: nextQube.name
                  });
                } else if (prefetchCancelledRef.current) {
                  // Only clear status if it's not a user indicator (preserve "bit_faced response ready")
                  setNextResponseStatus(prev =>
                    prev.qubeId === userId ? prev : { stage: 'idle' }
                  );

                  // Delete blocks from all qubes
                  (async () => {
                    for (const qube of selectedQubes) {
                      try {
                        const blocksResponse = await invoke<any>('get_qube_blocks', {
                          userId,
                          qubeId: qube.qube_id,
                          password
                        });

                        const sessionBlocks = blocksResponse.session_blocks || [];
                        for (const block of sessionBlocks) {
                          if (block.content?.turn_number === nextResponse.turn_number) {
                            await invoke('delete_session_block', {
                              userId,
                              qubeId: qube.qube_id,
                              blockNumber: block.block_number,
                              password
                            });
                          }
                        }
                      } catch (err) {
                        console.error(`Failed to delete cancelled blocks from ${qube.name}:`, err);
                      }
                    }
                  })();
                }
              }
            } catch (err) {
              console.error('Failed to prefetch next response:', err);
              setPrefetchedMessageId(null);
              // Only clear status if it's not a user indicator (preserve "bit_faced response ready")
              setNextResponseStatus(prev =>
                prev.qubeId === userId ? prev : { stage: 'idle' }
              );
            } finally {
              isFetchingNextRef.current = false;
            }
          }
        })();

        // TTS is already awaited above, prefetch continues in background
        // Clear pending and stop loading
        setPendingTTSMessage(null);
        setIsLoading(false);
        // NOTE: We do NOT clear processingMessageRef here!
        // It will be cleared when the typewriter completes (in the onComplete callback)
      } catch (err) {
        console.error('TTS error:', err);
        setError(`TTS error: ${String(err)}`);
        setPendingTTSMessage(null);
        setIsLoading(false);
        processingMessageRef.current = null; // Clear processing flag
      }
    };

    playMessageTTS();
  }, [pendingTTSMessage]); // Only trigger when pendingTTSMessage changes

  // Auto-continue conversation when typewriter completes
  useEffect(() => {
    // Check if we should pause after current message completes
    // BUT: if there's a prefetched response, play it first before pausing
    if (
      !activeTypewriterMessageId &&
      !pendingTTSMessage &&
      !processingMessageRef.current &&
      pauseAfterCurrentMessageRef.current
    ) {
      // If there's a prefetched response, play it before pausing
      if (nextResponsePrefetch) {
        setPendingTTSMessage(nextResponsePrefetch);
        setNextResponsePrefetch(null);
        // NOTE: Keep nextTTSPrefetch and prefetchedMessageId intact!
        // The playMessageTTS effect needs them to use the prefetched audio.
        setNextResponseStatus({ stage: 'idle' });
        // Keep pauseAfterCurrentMessageRef.current = true so it pauses after THIS message
        return;
      }

      // No prefetch, pause now
      setIsConversationActive(false);
      pauseAfterCurrentMessageRef.current = false;
      setIsPauseRequested(false); // Clear pause requested state
      return;
    }

    // Only continue if:
    // - No active typewriter (typewriter finished)
    // - Conversation is active
    // - No pending message being processed
    // - Not currently loading
    // - Not currently processing a message (prevents race conditions)
    // - Not waiting for user response from backend
    if (
      !activeTypewriterMessageId &&
      isConversationActive &&
      shouldContinueRef.current &&
      !pendingTTSMessage &&
      !isLoading &&
      !processingMessageRef.current && // Make sure we're not in the middle of processing
      !waitingForUserResponseRef.current // Don't fetch next turn if waiting for user's message
    ) {
      // Check if we have a COMPLETE prefetch ready (both response AND TTS)
      const nextMessageId = nextResponsePrefetch ? `${nextResponsePrefetch.conversation_id}-${nextResponsePrefetch.turn_number}` : null;
      const hasPrefetchedTTS = nextTTSPrefetch !== null && prefetchedMessageId === nextMessageId;
      const hasCompletePrefetch = nextResponsePrefetch !== null && hasPrefetchedTTS;

      // Fixed 1 second delay between responses for natural conversation pacing
      const delay = 1000; // 1 second delay for all responses

      const timer = setTimeout(async () => {
        // First, wait for any in-progress prefetch to complete (max 20 seconds)
        if (isFetchingNextRef.current) {
          const maxWait = 20000; // 20 seconds for very long TTS generation
          const checkInterval = 100;
          let waited = 0;

          while (isFetchingNextRef.current && waited < maxWait) {
            await new Promise(resolve => setTimeout(resolve, checkInterval));
            waited += checkInterval;
          }

          // If still fetching, we'll set up polling to wait for it
        }

        // Use REFS to get the LATEST values (not stale closure values)
        let currentPrefetch = nextResponsePrefetchRef.current;
        let currentTTSPrefetch = nextTTSPrefetchRef.current;
        let currentPrefetchedId = prefetchedMessageIdRef.current;

        // Double-check we haven't already processed the next turn
        const nextTurn = currentPrefetch?.turn_number || (lastProcessedTurnRef.current + 1);

        if (nextTurn <= lastProcessedTurnRef.current) {
          return;
        }

        // If prefetch is STILL in progress (even after 20s wait), set up polling instead of fetching
        if (isFetchingNextRef.current) {
          // Poll every 500ms to check if prefetch completes
          const pollInterval = setInterval(() => {
            const latestPrefetch = nextResponsePrefetchRef.current;
            const latestTTS = nextTTSPrefetchRef.current;
            const latestPrefetchedId = prefetchedMessageIdRef.current;
            const stillFetching = isFetchingNextRef.current;

            if (!latestPrefetch && !stillFetching) {
              // Prefetch failed or was cleared, fetch fresh
              clearInterval(pollInterval);
              continueConversation();
              return;
            }

            if (latestPrefetch) {
              const latestMessageId = `${latestPrefetch.conversation_id}-${latestPrefetch.turn_number}`;
              const latestHasTTS = latestTTS !== null && latestPrefetchedId === latestMessageId;

              if (latestHasTTS) {
                // Prefetch completed!
                clearInterval(pollInterval);
                setPendingTTSMessage(latestPrefetch);
                setNextResponsePrefetch(null);
              }
            }
          }, 500);

          // Stop polling after 60 seconds (safety timeout)
          setTimeout(() => {
            clearInterval(pollInterval);
            // Last resort: fetch fresh if we still don't have anything
            if (!nextResponsePrefetchRef.current) {
              continueConversation();
            }
          }, 60000);

          return; // Exit early - polling will handle it
        }

        // Check if prefetch is COMPLETE (both response AND TTS ready)
        let nextMessageId = currentPrefetch ? `${currentPrefetch.conversation_id}-${currentPrefetch.turn_number}` : null;
        let hasTTS = currentTTSPrefetch !== null && currentPrefetchedId === nextMessageId;
        let isComplete = currentPrefetch !== null && hasTTS;

        if (isComplete && currentPrefetch) {
          // Use the COMPLETE prefetched response (response + TTS ready!)
          setPendingTTSMessage(currentPrefetch);
          setNextResponsePrefetch(null);
          // NOTE: We do NOT clear nextTTSPrefetch/prefetchedMessageId here!
          // They will be cleared when the message actually uses the TTS
        } else if (currentPrefetch && !hasTTS) {
          // Prefetch has response but TTS isn't ready yet - poll for completion
          const pollInterval = setInterval(() => {
            const latestPrefetch = nextResponsePrefetchRef.current;
            const latestTTS = nextTTSPrefetchRef.current;
            const latestPrefetchedId = prefetchedMessageIdRef.current;

            if (!latestPrefetch) {
              // Prefetch was cleared, stop polling
              clearInterval(pollInterval);
              return;
            }

            const latestMessageId = `${latestPrefetch.conversation_id}-${latestPrefetch.turn_number}`;
            const latestHasTTS = latestTTS !== null && latestPrefetchedId === latestMessageId;

            if (latestHasTTS && latestPrefetch) {
              // Prefetch completed!
              clearInterval(pollInterval);
              setPendingTTSMessage(latestPrefetch);
              setNextResponsePrefetch(null);
            }
          }, 500);

          // Stop polling after 30 seconds (safety timeout)
          setTimeout(() => {
            clearInterval(pollInterval);
          }, 30000);
        } else {
          // No prefetch at all - fetch fresh
          continueConversation();
        }
      }, delay);

      return () => clearTimeout(timer);
    }
  }, [activeTypewriterMessageId, isConversationActive, pendingTTSMessage, isLoading]);
  // NOTE: nextResponsePrefetch is intentionally NOT in dependencies
  // We only want to trigger when typewriter completes, not when prefetch updates

  // Handle displaying pending user message when speaker finishes
  useEffect(() => {
    // Check if we have a pending user message with backend response
    // AND the speaker has finished (no active typewriter, no pending TTS)
    if (
      pendingUserMessage?.userMessageResponse &&
      pendingUserMessage?.qubeResponse &&
      !activeTypewriterMessageId &&
      !pendingTTSMessage &&
      !processingMessageRef.current
    ) {
      (async () => {
        // Capture qubeResponse early to satisfy TypeScript
        const qubeResponse = pendingUserMessage.qubeResponse;
        if (!qubeResponse) return;

        // Add user message to history
        setConversationHistory(prev => [...prev, pendingUserMessage.userMessageResponse!]);

        // Wait for the browser to actually paint the user message before clearing indicator
        // Use multiple animation frames to ensure the message is fully rendered and visible
        await new Promise(resolve => requestAnimationFrame(() => {
          requestAnimationFrame(() => {
            requestAnimationFrame(resolve);
          });
        }));

        // NOW clear the "bit_faced response ready" indicator (after message is painted)
        setNextResponseStatus({ stage: 'idle' });

        // Brief moment before showing qube indicator
        await new Promise(resolve => setTimeout(resolve, 50));

        // Now show the qube's "ready to respond" indicator
        setNextResponseStatus({
          stage: 'ready',
          qubeId: qubeResponse.speaker_id,
          qubeName: qubeResponse.speaker_name
        });

        // Update last processed turn
        lastProcessedTurnRef.current = qubeResponse.turn_number;

        // Clear waiting flag
        waitingForUserResponseRef.current = false;

        // CRITICAL: Clear prefetch cancelled flag to allow prefetch to resume
        prefetchCancelledRef.current = false;

        // Clear pending user message
        setPendingUserMessage(null);

        // CRITICAL: Wait for audio element to fully reset before starting new TTS
        // After the previous speaker finishes, the audio element is in "ended" state
        // We need to ensure it's fully paused and reset before the new TypewriterText mounts
        // Otherwise TypewriterText sees stale audio state and doesn't wait for 'play' event
        if (audioElement) {
          // Reset the audio element completely
          audioElement.pause();
          audioElement.currentTime = 0;
          audioElement.removeAttribute('src');
          audioElement.load();

          // Wait for load() to complete (it's async)
          await new Promise(resolve => setTimeout(resolve, 100));
        }

        // Now it's safe to start the new TTS/typewriter
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
            {conversationHistory.map((msg, index) => {
              const qube = getQubeById(msg.speaker_id);
              const participantInfo = getParticipantInfo(msg.speaker_id);
              const isUser = msg.speaker_id === userId;
              const messageId = `${msg.conversation_id}-${msg.turn_number}`;

              // Use participant info for styling (works for qubes and connections)
              const speakerColor = participantInfo?.color || qube?.favorite_color || '#00d4ff';
              const speakerAvatarUrl = participantInfo?.avatarUrl || (qube ? getAvatarPath(qube) : undefined);

              return (
                <div
                  key={messageId}
                  className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[70%] rounded-lg p-3 border-2 ${
                      isUser
                        ? 'bg-accent-primary/20 text-text-primary border-accent-primary'
                        : 'bg-bg-tertiary text-text-primary'
                    }`}
                    style={
                      !isUser
                        ? { borderColor: speakerColor }
                        : undefined
                    }
                  >
                    {/* Speaker Name */}
                    <div className="flex items-center gap-2 mb-2">
                      {!isUser && speakerAvatarUrl && (
                        <img
                          src={speakerAvatarUrl.startsWith('http') ? speakerAvatarUrl : convertFileSrc(speakerAvatarUrl)}
                          alt={msg.speaker_name}
                          className="w-8 h-8 rounded-full object-cover border-2"
                          style={{
                            borderColor: speakerColor,
                            boxShadow: `0 0 8px ${speakerColor}60`
                          }}
                          onError={(e) => {
                            const target = e.target as HTMLImageElement;
                            target.style.display = 'none';
                          }}
                        />
                      )}
                      {!isUser && !speakerAvatarUrl && participantInfo && (
                        <div
                          className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold border-2"
                          style={{
                            background: `linear-gradient(135deg, ${speakerColor}60, ${speakerColor}30)`,
                            borderColor: speakerColor,
                            color: speakerColor,
                          }}
                        >
                          {msg.speaker_name[0]}
                        </div>
                      )}
                      <p
                        className="text-sm font-medium"
                        style={
                          !isUser
                            ? { color: speakerColor }
                            : { color: 'var(--accent-primary)' }
                        }
                      >
                        {msg.speaker_name}
                        {participantInfo?.isConnection && (
                          <span className="ml-1 text-xs text-text-tertiary">(P2P)</span>
                        )}
                      </p>
                    </div>

                    {/* Message Content */}
                    <div className="whitespace-pre-wrap break-words">
                      {!isUser && messageId === activeTypewriterMessageId ? (
                        <>
                          {/* Render images first (non-typewriter) - both HTTP URLs and local paths */}
                          {(() => {
                            const imageUrlRegex = /(https?:\/\/[^\s\)]+?(?:\.(?:png|jpg|jpeg|gif|webp)|blob\.core\.windows\.net\/[^\s\)]+))/gi;
                            const localPathRegex = /([A-Za-z]:\\[^\s\)]+\.(?:png|jpg|jpeg|gif|webp)|data[\\\/][^\s\)]+\.(?:png|jpg|jpeg|gif|webp))/gi;
                            const imageUrls = msg.message.match(imageUrlRegex) || [];
                            const localPaths = msg.message.match(localPathRegex) || [];

                            // Render HTTP URLs
                            const httpImages = imageUrls.map((url, index) => (
                              <img
                                key={`http-img-${index}`}
                                src={url}
                                alt="Generated image"
                                className="max-w-full rounded-lg mb-3 block"
                                style={{ maxHeight: '400px', objectFit: 'contain' }}
                                onLoad={() => {
                                  saveImageToDisk(url, msg.speaker_id);
                                  scrollToBottom();
                                }}
                              />
                            ));

                            // Render local paths (convert to asset URLs)
                            const localImages = localPaths.map((path, index) => {
                              const assetUrl = convertToAssetUrl(path);
                              return (
                                <img
                                  key={`local-img-${index}`}
                                  src={assetUrl}
                                  alt="Generated image"
                                  className="max-w-full rounded-lg mb-3 block"
                                  style={{ maxHeight: '400px', objectFit: 'contain' }}
                                  onLoad={() => scrollToBottom()}
                                  onError={(e) => {
                                    console.error(`Image failed to load: ${assetUrl}`, e);
                                  }}
                                />
                              );
                            });

                            return [...httpImages, ...localImages];
                          })()}
                          {/* Then typewriter effect for cleaned text (without URLs) */}
                          <TypewriterText
                            text={cleanContentForDisplay(msg.message)}
                            audioElement={audioElement}
                            onComplete={() => {
                              setActiveTypewriterMessageId(null);
                              processingMessageRef.current = null; // Clear processing flag NOW
                              setTimeout(scrollToBottom, 200);
                            }}
                          />
                        </>
                      ) : !isUser && msg.turn_number === lastProcessedTurnRef.current && index === conversationHistory.length - 1 && processingMessageRef.current === messageId ? (
                        // Message just added but typewriter not activated yet - show nothing
                        <div className="h-4 flex items-center">
                          <div className="flex gap-1">
                            <div className="w-1.5 h-1.5 bg-accent-primary rounded-full animate-bounce"></div>
                            <div className="w-1.5 h-1.5 bg-accent-primary rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                            <div className="w-1.5 h-1.5 bg-accent-primary rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                          </div>
                        </div>
                      ) : (
                        // Completed message or user message - render with inline images
                        renderMessageContent(msg.message, msg.speaker_id)
                      )}
                    </div>

                    {/* Turn number */}
                    <p className="text-text-tertiary text-xs mt-1">
                      Turn {msg.turn_number}
                    </p>
                  </div>
                </div>
              );
            })}

            {/* Generic loading indicator for initial response */}
            {isLoading && conversationHistory.length <= 1 && !pendingTTSMessage && (
              <div className="flex justify-start">
                <div className="rounded-lg px-4 py-3 border-2" style={{
                  backgroundColor: 'var(--bg-tertiary)',
                  borderColor: '#00d9ff',
                }}>
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full animate-pulse" style={{
                      backgroundColor: '#00d9ff',
                      animationDuration: '1s'
                    }}></div>
                    <div className="w-2 h-2 rounded-full animate-pulse" style={{
                      backgroundColor: '#00d9ff',
                      animationDuration: '1s',
                      animationDelay: '0.2s'
                    }}></div>
                    <div className="w-2 h-2 rounded-full animate-pulse" style={{
                      backgroundColor: '#00d9ff',
                      animationDuration: '1s',
                      animationDelay: '0.4s'
                    }}></div>
                  </div>
                </div>
              </div>
            )}

            {/* Processing response indicator */}
            {nextResponseStatus.stage === 'processing' && activeToolCalls.length === 0 && (() => {
              // Get qube if we know who's responding
              const qube = nextResponseStatus.qubeId ? getQubeById(nextResponseStatus.qubeId) : null;
              const color = qube?.favorite_color || 'var(--accent-primary)';

              return (
                <div className="flex justify-start">
                  <div className="rounded-lg px-4 py-2 border-2" style={{
                    backgroundColor: 'var(--bg-tertiary)',
                    borderColor: color,
                  }}>
                    <div className="flex items-center gap-3">
                      {/* Only show avatar if we know which qube */}
                      {qube && (
                        <img
                          src={getAvatarPath(qube)}
                          alt={qube.name}
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
                        {qube && (
                          <span className="text-sm font-medium" style={{
                            color: color
                          }}>
                            {qube.name}
                          </span>
                        )}
                        <span className="text-xs text-text-secondary">
                          processing response...
                        </span>
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
                      </div>
                    </div>
                  </div>
                </div>
              );
            })()}

            {/* Tool call indicator - adapts based on tool type */}
            {activeToolCalls.length > 0 && nextResponseStatus.stage === 'processing' && (() => {
              const tool = activeToolCalls[activeToolCalls.length - 1];
              const toolQube = tool.qube_id ? getQubeById(tool.qube_id) : null;
              if (!toolQube) return null;

              const toolDisplay: Record<string, string> = {
                // Regular tools
                'web_search': 'searching the web',
                'generate_image': 'generating image',
                'browse_url': 'browsing URL',
                'memory_search': 'searching memory',
                'list_files': 'listing files',
                'read_file': 'reading file',
                'write_file': 'writing file',
                'run_command': 'running command',
                'calculate': 'calculating',
                // AI Reasoning Tools
                'think_step_by_step': 'thinking step by step',
                'self_critique': 'self-critiquing',
                'explore_alternatives': 'exploring alternatives',
                // Social Intelligence Tools
                'draft_message_variants': 'drafting messages',
                'predict_reaction': 'predicting reaction',
                'build_rapport_strategy': 'building rapport',
                // Technical Expertise Tools
                'debug_systematically': 'debugging',
                'research_with_synthesis': 'researching deeply',
                'validate_solution': 'validating solution',
                // Creative Expression Tools
                'brainstorm_variants': 'brainstorming ideas',
                'iterate_design': 'iterating on design',
                'cross_pollinate_ideas': 'cross-pollinating ideas',
                // Knowledge Domains Tools
                'deep_research': 'researching deeply',
                'synthesize_knowledge': 'synthesizing knowledge',
                'explain_like_im_five': 'simplifying explanation',
                // Security & Privacy Tools
                'assess_security_risks': 'assessing security',
                'privacy_impact_analysis': 'analyzing privacy',
                'verify_authenticity': 'verifying authenticity',
                // Games Tools
                'analyze_game_state': 'analyzing game',
                'plan_strategy': 'planning strategy',
                'learn_from_game': 'learning from game',
              };

              const displayText = toolDisplay[tool.action_type] || tool.action_type;

              return (
                <div className="flex justify-start">
                  <div className="rounded-lg px-4 py-2 border-2" style={{
                    backgroundColor: 'var(--bg-tertiary)',
                    borderColor: toolQube.favorite_color,
                  }}>
                    <div className="flex items-center gap-3">
                      <img
                        src={getAvatarPath(toolQube)}
                        alt={toolQube.name}
                        className="w-8 h-8 rounded-full object-cover border-2"
                        style={{
                          borderColor: toolQube.favorite_color,
                          opacity: 0.6
                        }}
                        onError={(e) => {
                          const target = e.target as HTMLImageElement;
                          target.style.display = 'none';
                        }}
                      />
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium" style={{
                          color: toolQube.favorite_color
                        }}>
                          {toolQube.name}
                        </span>
                        <span className="text-xs text-text-secondary">
                          {displayText}...
                        </span>
                        <div className="flex gap-1">
                          <div className="w-1.5 h-1.5 rounded-full animate-pulse" style={{
                            backgroundColor: toolQube.favorite_color,
                            animationDuration: '1s'
                          }}></div>
                          <div className="w-1.5 h-1.5 rounded-full animate-pulse" style={{
                            backgroundColor: toolQube.favorite_color,
                            animationDuration: '1s',
                            animationDelay: '0.2s'
                          }}></div>
                          <div className="w-1.5 h-1.5 rounded-full animate-pulse" style={{
                            backgroundColor: toolQube.favorite_color,
                            animationDuration: '1s',
                            animationDelay: '0.4s'
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
                        <div className="flex gap-1">
                          <div className="w-1.5 h-1.5 rounded-full animate-pulse" style={{
                            backgroundColor: speakerColor,
                            animationDuration: '1s'
                          }}></div>
                          <div className="w-1.5 h-1.5 rounded-full animate-pulse" style={{
                            backgroundColor: speakerColor,
                            animationDuration: '1s',
                            animationDelay: '0.2s'
                          }}></div>
                          <div className="w-1.5 h-1.5 rounded-full animate-pulse" style={{
                            backgroundColor: speakerColor,
                            animationDuration: '1s',
                            animationDelay: '0.4s'
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
              // Check if this is the user
              const isUser = nextResponseStatus.qubeId === userId;

              if (isUser) {
                // User indicator - on the RIGHT side
                return (
                  <div className="flex justify-end">
                    <div className="rounded-lg px-4 py-2 border-2" style={{
                      backgroundColor: '#00d9ff20',
                      borderColor: '#00d9ff',
                      boxShadow: '0 0 15px #00d9ff60'
                    }}>
                      <div className="flex items-center gap-3">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-bold" style={{
                            color: '#00d9ff'
                          }}>
                            bit_faced
                          </span>
                          <span className="text-xs font-medium text-text-primary">
                            response ready
                          </span>
                          <span className="text-lg">✓</span>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              } else {
                // Qube/participant indicator
                const qube = getQubeById(nextResponseStatus.qubeId);
                const participantInfo = getParticipantInfo(nextResponseStatus.qubeId);

                // Fall back to participant info for P2P connections
                const speakerColor = participantInfo?.color || qube?.favorite_color || '#00d4ff';
                const speakerName = nextResponseStatus.qubeName || participantInfo?.name || qube?.name || 'Unknown';
                const speakerAvatarUrl = participantInfo?.avatarUrl || (qube ? getAvatarPath(qube) : undefined);

                return (
                  <div className="flex justify-start">
                    <div className="rounded-lg px-4 py-2 border-2" style={{
                      backgroundColor: `${speakerColor}20`,
                      borderColor: speakerColor,
                      boxShadow: `0 0 15px ${speakerColor}60`
                    }}>
                      <div className="flex items-center gap-3">
                        {speakerAvatarUrl ? (
                          <img
                            src={speakerAvatarUrl.startsWith('http') ? speakerAvatarUrl : convertFileSrc(speakerAvatarUrl)}
                            alt={speakerName}
                            className="w-8 h-8 rounded-full object-cover border-2"
                            style={{
                              borderColor: speakerColor,
                              opacity: 1
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
                          <span className="text-sm font-bold" style={{
                            color: speakerColor
                          }}>
                            {speakerName}
                          </span>
                          <span className="text-xs font-medium text-text-primary">
                            ready to respond
                          </span>
                          <span className="text-lg">✓</span>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              }
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
