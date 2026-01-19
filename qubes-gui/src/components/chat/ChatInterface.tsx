import React, { useState, useEffect, useRef } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { convertFileSrc } from '@tauri-apps/api/core';
import { emit, emitTo, listen } from '@tauri-apps/api/event';
import { open } from '@tauri-apps/plugin-dialog';
import { readFile } from '@tauri-apps/plugin-fs';
import { GlassCard } from '../glass/GlassCard';
import { GlassButton } from '../glass/GlassButton';
import { Qube } from '../../types';
import { useAuth } from '../../hooks/useAuth';
import { useAudio } from '../../contexts/AudioContext';
import { useChainState } from '../../contexts/ChainStateContext';
import { useChatMessages, Message } from '../../hooks/useChatMessages';
import { useQubeSelection } from '../../hooks/useQubeSelection';
import { TypewriterText } from './TypewriterText';
import { ChatHeader } from './ChatHeader';
import EmojiPicker, { EmojiClickData, Theme } from 'emoji-picker-react';
import { WaveformOverlay } from '../visualizer/WaveformOverlay';
import type { WaveformStyle, ColorTheme, GradientStyle, AnimationSmoothness } from '../../types';

interface ChatInterfaceProps {
  selectedQubes: Qube[];
  onQubeModelChange?: (qubeId: string, newModel: string) => void;
}

interface ChatResponse {
  success: boolean;
  qube_id?: string;
  qube_name?: string;
  message?: string;
  response?: string;
  timestamp?: string;
  current_model?: string;
  error?: string;
}

export const ChatInterface: React.FC<ChatInterfaceProps> = ({ selectedQubes, onQubeModelChange }) => {
  const { userId, password } = useAuth();
  const { playTTS, audioElement } = useAudio();
  const { invalidateCache, loadChainState, startWatching, stopWatching } = useChainState();
  const { getMessages, addMessage, clearMessages, getUploadedFiles, addUploadedFile, removeUploadedFile, clearUploadedFiles } = useChatMessages();
  const currentTab = useQubeSelection(state => state.currentTab);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastResponseText, setLastResponseText] = useState<string>('');
  const [pendingResponse, setPendingResponse] = useState<{ qubeName: string; content: string } | null>(null);
  const [activeTypewriterMessageId, setActiveTypewriterMessageId] = useState<string | null>(null);
  const [currentModel, setCurrentModel] = useState<string | null>(null); // Local model state for header updates
  const [isRecording, setIsRecording] = useState(false);
  const [isGeneratingTTS, setIsGeneratingTTS] = useState(false);
  const [showEmojiPicker, setShowEmojiPicker] = useState(false);
  const [activeToolCalls, setActiveToolCalls] = useState<Array<{
    action_type: string;
    timestamp: number;
  }>>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const recognitionRef = useRef<any>(null);
  const pendingTypewriterRef = useRef<string | null>(null); // Track message waiting for typewriter activation
  const processingResponseRef = useRef<string | null>(null); // Track which response is being processed (guards against double execution)
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const emojiPickerRef = useRef<HTMLDivElement>(null);

  // Visualizer state
  const [visualizerSettings, setVisualizerSettings] = useState({
    enabled: false,
    waveform_style: 1 as WaveformStyle,
    color_theme: 'qube-color' as ColorTheme,
    gradient_style: 'gradient-dark' as GradientStyle,
    sensitivity: 50,
    animation_smoothness: 'medium' as AnimationSmoothness,
    audio_offset_ms: 0,
    frequency_range: 20,
    output_monitor: 0
  });
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);

  // Refs for latest values (to avoid stale closures)
  const visualizerSettingsRef = useRef(visualizerSettings);
  const selectedQubesRef = useRef(selectedQubes);
  const visualizerWindowOpenRef = useRef(false);

  // Keep refs updated
  useEffect(() => {
    visualizerSettingsRef.current = visualizerSettings;
  }, [visualizerSettings]);

  useEffect(() => {
    selectedQubesRef.current = selectedQubes;
  }, [selectedQubes]);

  // Listen for visualizer toggle requests from external window
  useEffect(() => {
    const setupListener = async () => {
      const unlisten = await listen('visualizer-toggle-request', () => {
        setVisualizerSettings(prev => {
          const newSettings = { ...prev, enabled: !prev.enabled };

          // Save to backend if we have a user and qube selected
          if (userId && selectedQubes.length > 0) {
            const qubeId = selectedQubes[0].qube_id;
            invoke('save_visualizer_settings', {
              userId,
              qubeId,
              settings: JSON.stringify(newSettings),
              password
            }).then(() => {
              // Invalidate and refresh chain state cache
              invalidateCache(qubeId);
              loadChainState(qubeId, true);
            }).catch(err => console.error('Failed to save visualizer settings:', err));
          }

          return newSettings;
        });
      });
      return unlisten;
    };

    const cleanupPromise = setupListener();
    return () => {
      cleanupPromise.then(cleanup => cleanup());
    };
  }, [userId, selectedQubes]);

  // Get messages and uploaded files for the selected qube
  const messages = selectedQubes.length > 0 ? getMessages(selectedQubes[0].qube_id) : [];
  const uploadedFiles = selectedQubes.length > 0 ? getUploadedFiles(selectedQubes[0].qube_id) : [];

  // Scroll to bottom helper function
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // Helper function to save an image to disk
  const saveImageToDisk = async (imageUrl: string) => {
    if (!userId || selectedQubes.length === 0) return;

    try {
      await invoke('save_image', {
        userId: userId,
        qubeId: selectedQubes[0].qube_id,
        imageUrl: imageUrl
      });
    } catch (err) {
      console.error('Failed to save image:', err);
      // Don't show error to user - saving is optional background task
    }
  };

  // Handle file upload
  const handleFileUpload = async () => {
    if (selectedQubes.length === 0) return;

    try {
      const selected = await open({
        multiple: true, // Allow multiple file selection
        filters: [{
          name: 'Images and Documents',
          extensions: ['png', 'jpg', 'jpeg', 'gif', 'webp', 'txt', 'md', 'json']
        }]
      });

      if (!selected) return;

      // Handle both single file (string) and multiple files (array)
      const filePaths = Array.isArray(selected) ? selected : [selected];

      for (const filePath of filePaths) {
        // Read file as bytes
        const fileBytes = await readFile(filePath);

        // Get file extension to determine type
        const fileName = filePath.split(/[\\/]/).pop() || 'file';
        const extension = fileName.split('.').pop()?.toLowerCase() || '';

        // Determine file type
        const imageExtensions = ['png', 'jpg', 'jpeg', 'gif', 'webp'];
        const textExtensions = ['txt', 'md', 'json'];
        const isImage = imageExtensions.includes(extension);
        const isTextFile = textExtensions.includes(extension);

        let fileData;
        if (isImage) {
          fileData = {
            name: fileName,
            path: filePath,
            type: 'image' as const,
            data: `data:image/${extension};base64,${btoa(
              new Uint8Array(fileBytes).reduce((data, byte) => data + String.fromCharCode(byte), '')
            )}`
          };
        } else if (isTextFile) {
          // Text files can be decoded as UTF-8
          fileData = {
            name: fileName,
            path: filePath,
            type: 'text' as const,
            data: new TextDecoder().decode(fileBytes)
          };
        } else {
          // PDF and other binary files - convert to base64
          fileData = {
            name: fileName,
            path: filePath,
            type: 'binary' as const,
            data: btoa(
              new Uint8Array(fileBytes).reduce((data, byte) => data + String.fromCharCode(byte), '')
            )
          };
        }

        addUploadedFile(selectedQubes[0].qube_id, fileData);
      }
    } catch (err) {
      console.error('Failed to upload file:', err);
      setError(`Failed to upload file: ${String(err)}`);
    }
  };

  // Helper function to clean content by removing image URLs and paths
  const cleanContentForDisplay = (content: string): string => {
    // Regular expression to detect image URLs (including DALL-E Azure Blob Storage URLs)
    const imageUrlRegex = /(https?:\/\/[^\s\)]+?(?:\.(?:png|jpg|jpeg|gif|webp)|blob\.core\.windows\.net\/[^\s\)]+))/gi;
    // Regular expression to detect local file paths (Windows and Unix)
    const localPathRegex = /([A-Za-z]:[\\\/][^\s\)]+\.(?:png|jpg|jpeg|gif|webp)|\/[^\s\)]+\.(?:png|jpg|jpeg|gif|webp))/gi;

    // Remove complete markdown image syntax ![...](url or path)
    let cleaned = content.replace(/!\[([^\]]*)\]\([^\)]+\)/gi, '');

    // Remove any remaining image URLs (standalone)
    cleaned = cleaned.replace(imageUrlRegex, '');

    // Remove any remaining local file paths (standalone)
    cleaned = cleaned.replace(localPathRegex, '');

    // Remove any standalone markdown image syntax ![...]
    cleaned = cleaned.replace(/!\[([^\]]*)\]/g, '');

    // Remove empty parentheses that might be left over
    cleaned = cleaned.replace(/\(\s*\)/g, '');

    // Clean up extra whitespace and newlines
    cleaned = cleaned.replace(/\n\n+/g, '\n\n').trim();

    return cleaned;
  };

  // Helper function to truncate text for TTS (OpenAI has 4096 char limit)
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

    // Truncate at word boundary and add ellipsis
    const truncated = processedText.substring(0, maxLength);
    const lastSpace = truncated.lastIndexOf(' ');
    return truncated.substring(0, lastSpace) + '... (response truncated for audio)';
  };

  // Helper function to detect and render images in message content
  const renderMessageContent = (content: string) => {
    // Regular expression to detect image URLs (including DALL-E Azure Blob Storage URLs)
    const imageUrlRegex = /(https?:\/\/[^\s\)]+?(?:\.(?:png|jpg|jpeg|gif|webp)|blob\.core\.windows\.net\/[^\s\)]+))/gi;
    // Regular expression to detect local file paths (Windows and Unix)
    const localPathRegex = /([A-Za-z]:[\\\/][^\s\)]+\.(?:png|jpg|jpeg|gif|webp)|\/[^\s\)]+\.(?:png|jpg|jpeg|gif|webp))/gi;
    // Regular expression to detect any URLs
    const anyUrlRegex = /(https?:\/\/[^\s\)]+)/gi;

    // Extract all image URLs first (both web URLs and local paths)
    const webImageUrls = content.match(imageUrlRegex) || [];
    const localImagePaths = content.match(localPathRegex) || [];

    // Convert local paths to asset:// URLs using Tauri's convertFileSrc
    const convertedLocalUrls = localImagePaths.map(path => convertFileSrc(path));

    // Combine all image sources
    const imageUrls = [...webImageUrls, ...convertedLocalUrls];

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
        {imageUrls.map((url, index) => (
          <img
            key={`img-${index}`}
            src={url}
            alt="Generated image"
            className="max-w-full rounded-lg mb-3 block"
            style={{ maxHeight: '400px', objectFit: 'contain' }}
            onLoad={() => {
              // Save image to disk
              saveImageToDisk(url);
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

  // Auto-scroll to bottom when new messages arrive or loading state changes
  useEffect(() => {
    scrollToBottom();
  }, [messages.length, isLoading]);

  // Also scroll when typewriter completes
  useEffect(() => {
    if (!activeTypewriterMessageId) {
      // Small delay to allow final layout adjustment
      setTimeout(scrollToBottom, 100);
    }
  }, [activeTypewriterMessageId]);

  // Load visualizer settings when qube changes
  useEffect(() => {
    const loadVisualizerSettings = async () => {
      if (!userId || selectedQubes.length === 0) return;

      try {
        const settings = await invoke('get_visualizer_settings', {
          userId,
          qubeId: selectedQubes[0].qube_id,
          password
        });
        // Merge with defaults to handle missing fields (like output_monitor)
        const loadedSettings = {
          enabled: (settings as any).enabled ?? false,
          waveform_style: (settings as any).waveform_style ?? 1,
          color_theme: (settings as any).color_theme ?? 'qube-color',
          gradient_style: (settings as any).gradient_style ?? 'gradient-dark',
          sensitivity: (settings as any).sensitivity ?? 50,
          animation_smoothness: (settings as any).animation_smoothness ?? 'medium',
          audio_offset_ms: (settings as any).audio_offset_ms ?? 0,
          frequency_range: (settings as any).frequency_range ?? 20,
          output_monitor: (settings as any).output_monitor ?? 0
        };
        setVisualizerSettings(loadedSettings);
      } catch (error) {
        console.error('Failed to load visualizer settings:', error);
      }
    };

    loadVisualizerSettings();
  }, [userId, selectedQubes.length > 0 ? selectedQubes[0].qube_id : null]);

  // Listen for settings changes from QubeManagerTab
  useEffect(() => {
    const setupListener = async () => {
      const unlisten = await listen('visualizer-settings-changed', async (event: any) => {
        const { qubeId } = event.payload;

        // Only reload if it's for the currently selected qube
        if (userId && selectedQubes.length > 0 && selectedQubes[0].qube_id === qubeId) {
          try {
            const settings = await invoke('get_visualizer_settings', {
              userId,
              qubeId,
              password
            });

            const loadedSettings = {
              enabled: (settings as any).enabled ?? false,
              waveform_style: (settings as any).waveform_style ?? 1,
              color_theme: (settings as any).color_theme ?? 'qube-color',
              gradient_style: (settings as any).gradient_style ?? 'gradient-dark',
              sensitivity: (settings as any).sensitivity ?? 50,
              animation_smoothness: (settings as any).animation_smoothness ?? 'medium',
              audio_offset_ms: (settings as any).audio_offset_ms ?? 0,
              frequency_range: (settings as any).frequency_range ?? 20,
              output_monitor: (settings as any).output_monitor ?? 0
            };
            setVisualizerSettings(loadedSettings);
          } catch (error) {
            console.error('Failed to reload visualizer settings:', error);
          }
        }
      });
      return unlisten;
    };

    const cleanupPromise = setupListener();
    return () => {
      cleanupPromise.then(cleanup => cleanup());
    };
  }, [userId, selectedQubes]);

  // Track audio playback state
  useEffect(() => {
    if (!audioElement) return;

    const handlePlay = () => setIsPlayingAudio(true);
    const handlePause = () => setIsPlayingAudio(false);
    const handleEnded = () => setIsPlayingAudio(false);

    audioElement.addEventListener('play', handlePlay);
    audioElement.addEventListener('pause', handlePause);
    audioElement.addEventListener('ended', handleEnded);

    return () => {
      audioElement.removeEventListener('play', handlePlay);
      audioElement.removeEventListener('pause', handlePause);
      audioElement.removeEventListener('ended', handleEnded);
    };
  }, [audioElement]);

  // Broadcast playback state to visualizer window
  useEffect(() => {
    // Use emitTo to target the specific visualizer window
    emitTo('visualizer', 'visualizer-playback-update', {
      isPlaying: isPlayingAudio
    }).catch((err) => {
      // Silently fail if visualizer window doesn't exist
    });
  }, [isPlayingAudio]);

  // Broadcast visualizer settings to visualizer window
  // Only broadcast when external monitor is selected (to avoid unnecessary events)
  useEffect(() => {
    if (selectedQubes.length > 0 && visualizerSettings.output_monitor > 0) {
      emitTo('visualizer', 'visualizer-settings-update', {
        ...visualizerSettings,
        qube_favorite_color: selectedQubes[0].favorite_color
      }).catch(() => {
        // Silently fail if visualizer window doesn't exist
      });
    }
  }, [visualizerSettings.waveform_style, visualizerSettings.color_theme, visualizerSettings.gradient_style, visualizerSettings.sensitivity, visualizerSettings.animation_smoothness, visualizerSettings.audio_offset_ms, visualizerSettings.frequency_range, selectedQubes, visualizerSettings.output_monitor]);

  // Handle visualizer window lifecycle (create/close based on playback state)
  useEffect(() => {
    const manageVisualizerWindow = async () => {
      // Only manage window if external monitor is selected
      if (visualizerSettings.output_monitor === 0) {
        // Make sure window is closed if switching back to overlay
        if (visualizerWindowOpenRef.current) {
          try {
            await invoke('close_visualizer_window');
            visualizerWindowOpenRef.current = false;
          } catch (error) {
            // Silently fail
          }
        }
        return;
      }

      const shouldBeOpen = isPlayingAudio && visualizerSettings.enabled;

      if (shouldBeOpen && !visualizerWindowOpenRef.current) {
        // Create visualizer window on external monitor when audio starts
        try {
          // Use ref to get latest value and avoid stale closures
          const monitorIndex = visualizerSettingsRef.current.output_monitor;

          await invoke('create_visualizer_window', {
            monitorIndex
          });
          visualizerWindowOpenRef.current = true;

          // Small delay to ensure window is ready to receive events
          await new Promise(resolve => setTimeout(resolve, 300));

          // Broadcast current state to the new window immediately (use refs for latest values)
          emitTo('visualizer', 'visualizer-playback-update', {
            isPlaying: true
          }).catch((err) => {
            console.error('Failed to send playback state:', err);
          });

          const currentQubes = selectedQubesRef.current;
          const currentSettings = visualizerSettingsRef.current;
          if (currentQubes.length > 0) {
            emitTo('visualizer', 'visualizer-settings-update', {
              ...currentSettings,
              qube_favorite_color: currentQubes[0].favorite_color
            }).catch((err) => {
              console.error('Failed to send settings:', err);
            });
          }
        } catch (error) {
          console.error('Failed to create visualizer window:', error);
          visualizerWindowOpenRef.current = false;
        }
      } else if (!shouldBeOpen && visualizerWindowOpenRef.current) {
        // Close visualizer window when audio stops OR when disabled
        try {
          await invoke('close_visualizer_window');
          visualizerWindowOpenRef.current = false;
        } catch (error) {
          // Silently fail - window might not exist
          visualizerWindowOpenRef.current = false;
        }
      }
    };

    manageVisualizerWindow();
  }, [isPlayingAudio, visualizerSettings.output_monitor, visualizerSettings.enabled]);

  // Initialize speech recognition
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

      if (SpeechRecognition) {
        const recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = 'en-US';

        recognition.onresult = (event: any) => {
          let transcript = '';
          for (let i = event.resultIndex; i < event.results.length; i++) {
            transcript += event.results[i][0].transcript;
          }
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
      }
    }

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
    };
  }, []);

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

  // Add Escape key listener to clear chat
  useEffect(() => {
    const handleEscapeKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && selectedQubes.length > 0) {
        clearMessages(selectedQubes[0].qube_id);
        setError(null);
        setLastResponseText('');
      }
    };

    window.addEventListener('keydown', handleEscapeKey);
    return () => window.removeEventListener('keydown', handleEscapeKey);
  }, [selectedQubes, clearMessages]);

  // Track the current qube ID to detect actual qube changes (not just array reference changes)
  const currentQubeId = selectedQubes.length > 0 ? selectedQubes[0].qube_id : null;
  const prevQubeIdRef = useRef<string | null>(currentQubeId);

  // Clear pending states when switching Qubes (only when qube ID actually changes)
  useEffect(() => {
    // Skip if qube ID hasn't actually changed
    if (prevQubeIdRef.current === currentQubeId) {
      return;
    }
    prevQubeIdRef.current = currentQubeId;

    // Clear any pending responses from previous Qube
    setPendingResponse(null);
    setLastResponseText('');
    setActiveTypewriterMessageId(null);
    setCurrentModel(null); // Reset so header uses new qube's ai_model
    setIsGeneratingTTS(false);
    setError(null);
  }, [currentQubeId]);

  // Start/stop event watching when qube changes
  useEffect(() => {
    if (!currentQubeId) return;

    // Start watching events for this qube
    startWatching(currentQubeId);

    // Cleanup: stop watching when qube changes or component unmounts
    return () => {
      stopWatching(currentQubeId);
    };
  }, [currentQubeId, startWatching, stopWatching]);

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

  // Auto-focus textarea when switching to Chat tab with a qube selected
  useEffect(() => {
    if (currentTab === 'dashboard' && selectedQubes.length > 0 && textareaRef.current) {
      // Small delay to ensure the tab transition is complete
      setTimeout(() => {
        textareaRef.current?.focus();
      }, 100);
    }
  }, [currentTab, selectedQubes.length]);

  const handleSend = async () => {
    // Guard against double-sending (e.g., double-click, Enter key repeat)
    if (isLoading) return;

    if ((!inputValue.trim() && uploadedFiles.length === 0) || selectedQubes.length === 0 || !userId) {
      return;
    }

    if (!password) {
      setError('Session expired. Please log out and log back in.');
      return;
    }

    // Store files and input for async processing
    const filesToProcess = [...uploadedFiles];
    const messageToSend = inputValue;

    // Build file indicator for user message
    let fileIndicator = '';
    if (filesToProcess.length > 0) {
      const imageCount = filesToProcess.filter(f => f.type === 'image').length;
      const textCount = filesToProcess.filter(f => f.type === 'text').length;

      if (imageCount > 0 && textCount > 0) {
        fileIndicator = `\n[${imageCount} image(s) and ${textCount} file(s) attached]`;
      } else if (imageCount > 0) {
        fileIndicator = `\n[${imageCount} image(s) attached]`;
      } else if (textCount > 0) {
        fileIndicator = `\n[${textCount} file(s) attached]`;
      }
    }

    // Create user message - SHOW IMMEDIATELY
    const userMessage: Message = {
      id: Date.now().toString(),
      sender: 'user',
      content: `${inputValue}${fileIndicator}`,
      timestamp: new Date(),
    };

    // Add message and clear input IMMEDIATELY
    addMessage(selectedQubes[0].qube_id, userMessage);
    setInputValue('');
    clearUploadedFiles(selectedQubes[0].qube_id);
    setIsLoading(true);
    setError(null);

    try {
      // Process files
      if (filesToProcess.length > 0) {
        // Separate images and text files
        const images = filesToProcess.filter(f => f.type === 'image');
        const textFiles = filesToProcess.filter(f => f.type === 'text');
        const binaryFiles = filesToProcess.filter(f => f.type === 'binary');

        // Check for unsupported binary files
        if (binaryFiles.length > 0) {
          setError(`Sorry, I cannot read PDF or binary files yet. Please copy and paste the text content, or upload a text file (.txt, .md, .json) instead.`);
          setIsLoading(false);
          return;
        }

        // Build message with text files
        let fullMessage = messageToSend;
        for (const file of textFiles) {
          fullMessage += `\n\n[Attached file: ${file.name}]\n${file.data}`;
        }

        // Process images (analyze each one separately for now)
        let allResponses = '';
        for (let i = 0; i < images.length; i++) {
          const image = images[i];
          const base64Data = image.data.split(',')[1];
          const imagePrompt = i === 0 && images.length === 1
            ? (messageToSend || "Please describe this image.")
            : (messageToSend || `Please describe image ${i + 1} of ${images.length}.`);

          const analyzeResponse = await invoke<{success: boolean; description?: string; error?: string}>('analyze_image', {
            userId: userId,
            qubeId: selectedQubes[0].qube_id,
            imageBase64: base64Data,
            userMessage: imagePrompt,
            password: password
          });

          if (analyzeResponse.success && analyzeResponse.description) {
            if (images.length > 1) {
              allResponses += `\n\n**Image ${i + 1}:**\n${analyzeResponse.description}`;
            } else {
              allResponses += analyzeResponse.description;
            }
          } else {
            throw new Error(analyzeResponse.error || `Failed to analyze image ${i + 1}`);
          }
        }

        // If we have text files after images, send them as a follow-up
        if (textFiles.length > 0) {
          const textResponse = await invoke<ChatResponse>('send_message', {
            userId: userId,
            qubeId: selectedQubes[0].qube_id,
            message: fullMessage,
            password: password
          });

          if (textResponse.success && textResponse.response) {
            // Combine image responses with text response
            const combinedResponse = allResponses
              ? `${allResponses}\n\n${textResponse.response}`
              : textResponse.response;

            setPendingResponse({
              qubeName: selectedQubes[0].name,
              content: combinedResponse,
            });
            setLastResponseText(cleanContentForDisplay(combinedResponse));

            // Check if model changed (e.g., via switch_model tool or revolver mode)
            // Use local state to update header without re-rendering entire chat (preserves typewriter)
            if (textResponse.current_model) {
              setCurrentModel(textResponse.current_model);
              // Emit event so other components (roster, etc.) can update
              emit('qube-model-changed', {
                qubeId: selectedQubes[0].qube_id,
                newModel: textResponse.current_model,
              });
            }
          } else {
            throw new Error(textResponse.error || 'Failed to get response from qube');
          }
        } else if (allResponses) {
          // Only images, no text files
          setPendingResponse({
            qubeName: selectedQubes[0].name,
            content: allResponses,
          });
          setLastResponseText(cleanContentForDisplay(allResponses));
        }
      } else {
        // No files - send regular message
        const response = await invoke<ChatResponse>('send_message', {
          userId: userId,
          qubeId: selectedQubes[0].qube_id,
          message: messageToSend,
          password: password
        });

        if (response.success && response.response) {
          setPendingResponse({
            qubeName: response.qube_name || selectedQubes[0].name,
            content: response.response,
          });
          setLastResponseText(cleanContentForDisplay(response.response));

          // Check if model changed (e.g., via switch_model tool or revolver mode)
          // Use local state to update header without re-rendering entire chat (preserves typewriter)
          if (response.current_model) {
            setCurrentModel(response.current_model);
            // Emit event so other components (roster, etc.) can update
            emit('qube-model-changed', {
              qubeId: selectedQubes[0].qube_id,
              newModel: response.current_model,
            });
          }
        } else {
          setError(response.error || 'Failed to get response from qube');
          setIsLoading(false);
        }
      }
    } catch (err) {
      console.error('Failed to process message:', err);
      setError(String(err));
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey && !isLoading) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleEmojiClick = (emojiData: EmojiClickData) => {
    const emoji = emojiData.emoji;
    const textarea = textareaRef.current;

    if (textarea) {
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      const text = inputValue;
      const before = text.substring(0, start);
      const after = text.substring(end);

      setInputValue(before + emoji + after);

      // Set cursor position after emoji
      setTimeout(() => {
        textarea.selectionStart = textarea.selectionEnd = start + emoji.length;
        textarea.focus();
      }, 0);
    } else {
      // Fallback if ref not available
      setInputValue(inputValue + emoji);
    }

    // Optionally close picker after selection (or keep it open)
    // setShowEmojiPicker(false);
  };

  const toggleRecording = () => {
    if (!recognitionRef.current) {
      setError('Speech recognition not supported in this browser');
      return;
    }

    if (isRecording) {
      recognitionRef.current.stop();
      setIsRecording(false);
    } else {
      try {
        recognitionRef.current.start();
        setIsRecording(true);
      } catch (err) {
        console.error('Failed to start recording:', err);
        setError('Failed to start voice recording');
      }
    }
  };

  // Auto-generate and play TTS when qube responds, then show the message
  useEffect(() => {
    const generateAndPlayTTS = async () => {
      // Skip if no response text or pending response
      if (!lastResponseText || !pendingResponse || !userId || !password || selectedQubes.length === 0) {
        return;
      }

      // Guard against double execution (can happen during TTS rate limiting delays)
      // Use the response content as the key - if it's the same response, skip
      const responseKey = pendingResponse.content;
      if (processingResponseRef.current === responseKey) {
        return;
      }
      processingResponseRef.current = responseKey;

      const currentQube = selectedQubes[0];
      const messageId = (Date.now() + 1).toString();
      const qubeResponse: Message = {
        id: messageId,
        sender: 'qube',
        qubeName: pendingResponse.qubeName,
        content: pendingResponse.content,
        timestamp: new Date(),
      };

      // Check if TTS is enabled for this qube
      if (currentQube.tts_enabled) {
        try {
          // Show TTS generation indicator
          setIsGeneratingTTS(true);

          // Truncate text for TTS if needed (OpenAI limit: 4096 chars)
          const ttsText = truncateForTTS(lastResponseText);

          // Generate TTS and wait for it to be ready and start playing
          await playTTS(userId, currentQube.qube_id, ttsText, password);

          // Hide TTS generation indicator - audio is now playing
          setIsGeneratingTTS(false);

          // Mark this message as pending typewriter activation
          pendingTypewriterRef.current = messageId;

          // Add message to history FIRST (so DOM element exists)
          addMessage(currentQube.qube_id, qubeResponse);

          // Small delay to let React render the message bubble
          await new Promise(resolve => setTimeout(resolve, 50));

          // NOW activate typewriter - audio is already playing
          pendingTypewriterRef.current = null;
          setActiveTypewriterMessageId(messageId);

          // Clear pending response and stop loading
          setPendingResponse(null);
          setIsLoading(false);
          processingResponseRef.current = null;
        } catch (err) {
          console.error('TTS error:', err);
          setError(`TTS error: ${String(err)}`);
          setIsGeneratingTTS(false);

          // Even if TTS fails, show the message immediately (no typewriter)
          addMessage(currentQube.qube_id, qubeResponse);
          setPendingResponse(null);
          setIsLoading(false);
          processingResponseRef.current = null;
        }
      } else {
        // TTS disabled - show message immediately without typewriter effect
        addMessage(currentQube.qube_id, qubeResponse);
        setPendingResponse(null);
        setIsLoading(false);
        processingResponseRef.current = null;
      }
    };

    generateAndPlayTTS();
  }, [lastResponseText, pendingResponse, userId, password, selectedQubes, playTTS, addMessage]);

  // Poll for active tool calls during message processing
  useEffect(() => {
    if (!isLoading || !userId || !password || selectedQubes.length === 0) {
      setActiveToolCalls([]);
      return;
    }

    const pollInterval = setInterval(async () => {
      const now = Date.now();
      const recentActions: Array<{ action_type: string; timestamp: number }> = [];

      try {
        const result = await invoke<any>('get_qube_blocks', {
          userId,
          qubeId: selectedQubes[0].qube_id,
          password,
          limit: 50
        });

        if (result?.session_blocks && Array.isArray(result.session_blocks)) {
          const actionBlocks = result.session_blocks.filter((b: any) =>
            b.block_type === 'ACTION' &&
            b.content?.action_type &&
            (now - b.timestamp) < 5000
          );

          actionBlocks.forEach((b: any) => {
            recentActions.push({
              action_type: b.content.action_type,
              timestamp: b.timestamp
            });
          });
        }

        if (recentActions.length > 0) {
          const uniqueActions = Array.from(
            new Map(recentActions.map(a => [a.action_type, a])).values()
          );
          setActiveToolCalls(uniqueActions);
        } else {
          setActiveToolCalls([]);
        }
      } catch (err) {
        console.error('Failed to poll for tool calls:', err);
      }
    }, 500);

    return () => clearInterval(pollInterval);
  }, [isLoading, userId, password, selectedQubes]);

  if (selectedQubes.length === 0) {
    return (
      <GlassCard className="flex-1 p-6 flex items-center justify-center">
        <div className="text-center">
          <p className="text-text-secondary mb-2">No qube selected</p>
          <p className="text-text-tertiary text-sm">
            Select a qube from the roster to start chatting
          </p>
        </div>
      </GlassCard>
    );
  }

  return (
    <div className="flex-1 flex flex-col gap-4 overflow-hidden">
      {/* Chat Header - Isolated component to prevent re-renders from breaking typewriter */}
      <ChatHeader qube={selectedQubes[0]} userId={userId || ''} currentModel={currentModel} />

      {/* Messages Area */}
      <GlassCard className="flex-1 p-4 pb-6 overflow-y-auto">
        {messages.length === 0 ? (
          <div className="h-full flex items-center justify-center">
            <p className="text-text-tertiary text-center">
              Start a conversation with {selectedQubes[0].name}
            </p>
          </div>
        ) : (
          <div className="space-y-4 pb-4">
            {messages.map(msg => (
              <div
                key={msg.id}
                className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[70%] rounded-lg p-3 border-2 ${
                    msg.sender === 'user'
                      ? 'bg-accent-primary/20 text-text-primary border-accent-primary'
                      : 'bg-bg-tertiary text-text-primary'
                  }`}
                  style={
                    msg.sender === 'qube'
                      ? { borderColor: selectedQubes[0].favorite_color }
                      : undefined
                  }
                >
                  {/* Speaker Name */}
                  <div className="flex items-center gap-2 mb-2">
                    {msg.sender === 'qube' && (
                      <img
                        src={getAvatarPath(selectedQubes[0])}
                        alt={msg.qubeName || selectedQubes[0].name}
                        className="w-8 h-8 rounded-full object-cover border-2"
                        style={{
                          borderColor: selectedQubes[0].favorite_color,
                          boxShadow: `0 0 8px ${selectedQubes[0].favorite_color}60`
                        }}
                        onError={(e) => {
                          const target = e.target as HTMLImageElement;
                          target.style.display = 'none';
                        }}
                      />
                    )}
                    {msg.sender === 'user' ? (
                      <p className="text-sm font-medium" style={{ color: 'var(--accent-primary)' }}>
                        {userId}
                      </p>
                    ) : msg.sender === 'qube' && msg.qubeName ? (
                      <p className="text-sm font-medium" style={{ color: selectedQubes[0].favorite_color }}>
                        {msg.qubeName}
                      </p>
                    ) : null}
                  </div>
                  <div className="whitespace-pre-wrap break-words">
                    {msg.sender === 'qube' && msg.id === pendingTypewriterRef.current ? (
                      // Message waiting for typewriter activation - show loading dots
                      <div className="h-4 flex items-center">
                        <div className="flex gap-1">
                          <div className="w-1.5 h-1.5 bg-accent-primary rounded-full animate-bounce"></div>
                          <div className="w-1.5 h-1.5 bg-accent-primary rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                          <div className="w-1.5 h-1.5 bg-accent-primary rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                        </div>
                      </div>
                    ) : msg.sender === 'qube' && msg.id === activeTypewriterMessageId ? (
                      <>
                        {/* Render images first (non-typewriter) */}
                        {(() => {
                          const imageUrlRegex = /(https?:\/\/[^\s\)]+?(?:\.(?:png|jpg|jpeg|gif|webp)|blob\.core\.windows\.net\/[^\s\)]+))/gi;
                          const imageUrls = msg.content.match(imageUrlRegex) || [];
                          return imageUrls.map((url, index) => (
                            <img
                              key={`img-${index}`}
                              src={url}
                              alt="Generated image"
                              className="max-w-full rounded-lg mb-3 block"
                              style={{ maxHeight: '400px', objectFit: 'contain' }}
                              onLoad={() => {
                                // Save image to disk
                                saveImageToDisk(url);
                                // Scroll when image finishes loading
                                scrollToBottom();
                              }}
                            />
                          ));
                        })()}
                        {/* Then typewriter effect for cleaned text (without URLs) */}
                        <TypewriterText
                          text={cleanContentForDisplay(msg.content)}
                          audioElement={audioElement}
                          onComplete={() => {
                            setActiveTypewriterMessageId(null);
                            // Scroll after typewriter completes
                            setTimeout(scrollToBottom, 200);
                          }}
                          onTextUpdate={scrollToBottom}
                        />
                      </>
                    ) : (
                      // After typewriter completes or TTS disabled, render with inline images
                      renderMessageContent(msg.content)
                    )}
                  </div>
                  <p className="text-text-tertiary text-xs mt-1">
                    {msg.timestamp.toLocaleTimeString()}
                  </p>
                </div>
              </div>
            ))}

            {/* TTS Generation Indicator */}
            {isGeneratingTTS && selectedQubes.length > 0 && (
              <div className="flex justify-start">
                <div className="rounded-lg px-4 py-2 border-2" style={{
                  backgroundColor: 'var(--bg-tertiary)',
                  borderColor: selectedQubes[0].favorite_color,
                }}>
                  <div className="flex items-center gap-3">
                    {/* Avatar */}
                    <img
                      src={getAvatarPath(selectedQubes[0])}
                      alt={selectedQubes[0].name}
                      className="w-8 h-8 rounded-full object-cover border-2"
                      style={{
                        borderColor: selectedQubes[0].favorite_color,
                        opacity: 0.6
                      }}
                      onError={(e) => {
                        const target = e.target as HTMLImageElement;
                        target.style.display = 'none';
                      }}
                    />

                    {/* Status text */}
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium" style={{
                        color: selectedQubes[0].favorite_color
                      }}>
                        {selectedQubes[0].name}
                      </span>
                      <span className="text-xs text-text-secondary">
                        generating audio...
                      </span>
                      <div className="flex gap-1">
                        <div className="w-1.5 h-1.5 rounded-full animate-pulse" style={{
                          backgroundColor: selectedQubes[0].favorite_color,
                          animationDuration: '1s'
                        }}></div>
                        <div className="w-1.5 h-1.5 rounded-full animate-pulse" style={{
                          backgroundColor: selectedQubes[0].favorite_color,
                          animationDuration: '1s',
                          animationDelay: '0.2s'
                        }}></div>
                        <div className="w-1.5 h-1.5 rounded-full animate-pulse" style={{
                          backgroundColor: selectedQubes[0].favorite_color,
                          animationDuration: '1s',
                          animationDelay: '0.4s'
                        }}></div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Tool Call Indicator */}
            {activeToolCalls.length > 0 && isLoading && !isGeneratingTTS && selectedQubes.length > 0 && (() => {
              const tool = activeToolCalls[activeToolCalls.length - 1];

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
                    borderColor: selectedQubes[0].favorite_color,
                  }}>
                    <div className="flex items-center gap-3">
                      <img
                        src={getAvatarPath(selectedQubes[0])}
                        alt={selectedQubes[0].name}
                        className="w-8 h-8 rounded-full object-cover border-2"
                        style={{
                          borderColor: selectedQubes[0].favorite_color,
                          opacity: 0.6
                        }}
                        onError={(e) => {
                          const target = e.target as HTMLImageElement;
                          target.style.display = 'none';
                        }}
                      />
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium" style={{
                          color: selectedQubes[0].favorite_color
                        }}>
                          {selectedQubes[0].name}
                        </span>
                        <span className="text-xs text-text-secondary">
                          {displayText}...
                        </span>
                        <div className="flex gap-1">
                          <div className="w-1.5 h-1.5 rounded-full animate-pulse" style={{
                            backgroundColor: selectedQubes[0].favorite_color,
                            animationDuration: '1s'
                          }}></div>
                          <div className="w-1.5 h-1.5 rounded-full animate-pulse" style={{
                            backgroundColor: selectedQubes[0].favorite_color,
                            animationDuration: '1s',
                            animationDelay: '0.2s'
                          }}></div>
                          <div className="w-1.5 h-1.5 rounded-full animate-pulse" style={{
                            backgroundColor: selectedQubes[0].favorite_color,
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

            {isLoading && !isGeneratingTTS && activeToolCalls.length === 0 && selectedQubes.length > 0 && (
              <div className="flex justify-start">
                <div className="rounded-lg px-4 py-2 border-2" style={{
                  backgroundColor: 'var(--bg-tertiary)',
                  borderColor: selectedQubes[0].favorite_color,
                }}>
                  <div className="flex items-center gap-3">
                    {/* Avatar */}
                    <img
                      src={getAvatarPath(selectedQubes[0])}
                      alt={selectedQubes[0].name}
                      className="w-8 h-8 rounded-full object-cover border-2"
                      style={{
                        borderColor: selectedQubes[0].favorite_color,
                        opacity: 0.6
                      }}
                      onError={(e) => {
                        const target = e.target as HTMLImageElement;
                        target.style.display = 'none';
                      }}
                    />

                    {/* Status text */}
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium" style={{
                        color: selectedQubes[0].favorite_color
                      }}>
                        {selectedQubes[0].name}
                      </span>
                      <span className="text-xs text-text-secondary">
                        processing response...
                      </span>
                      <div className="flex gap-1">
                        <div className="w-1.5 h-1.5 rounded-full animate-pulse" style={{
                          backgroundColor: selectedQubes[0].favorite_color,
                          animationDuration: '1s'
                        }}></div>
                        <div className="w-1.5 h-1.5 rounded-full animate-pulse" style={{
                          backgroundColor: selectedQubes[0].favorite_color,
                          animationDuration: '1s',
                          animationDelay: '0.2s'
                        }}></div>
                        <div className="w-1.5 h-1.5 rounded-full animate-pulse" style={{
                          backgroundColor: selectedQubes[0].favorite_color,
                          animationDuration: '1s',
                          animationDelay: '0.4s'
                        }}></div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
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
      </GlassCard>

      {/* Input Area */}
      <GlassCard className="p-4">
        {/* File Preview Grid */}
        {uploadedFiles.length > 0 && (
          <div className="mb-3 flex flex-wrap gap-2">
            {uploadedFiles.map((file, index) => (
              <div
                key={`${file.name}-${index}`}
                className="relative p-2 bg-bg-tertiary rounded-lg border-2 border-accent-primary/50 flex flex-col items-center"
                style={{ width: '120px' }}
              >
                {/* File preview */}
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

                {/* File name (truncated) */}
                <p className="text-text-primary text-xs font-medium truncate w-full text-center" title={file.name}>
                  {file.name.length > 12 ? file.name.substring(0, 12) + '...' : file.name}
                </p>

                {/* Remove button */}
                <button
                  onClick={() => selectedQubes.length > 0 && removeUploadedFile(selectedQubes[0].qube_id, file.name)}
                  className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-accent-danger text-white hover:bg-accent-danger/80 transition-all flex items-center justify-center text-xs"
                  title="Remove file"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        )}

        <div className="flex gap-2">
          <button
            onClick={toggleRecording}
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
            onKeyPress={handleKeyPress}
            placeholder={`Message ${selectedQubes[0].name}...`}
            className="flex-1 bg-bg-secondary text-text-primary placeholder-text-tertiary rounded-lg px-4 py-2 resize-none focus:outline-none focus:ring-2 focus:ring-accent-primary/50"
            rows={1}
            disabled={isLoading}
          />
          <GlassButton
            variant="primary"
            onClick={handleSend}
            disabled={(!inputValue.trim() && uploadedFiles.length === 0) || isLoading}
          >
            Send
          </GlassButton>
        </div>
      </GlassCard>

      {/* Waveform Visualizer Overlay */}
      {selectedQubes.length > 0 && (
        <WaveformOverlay
          audioElement={audioElement}
          isPlaying={isPlayingAudio}
          qubeFavoriteColor={selectedQubes[0].favorite_color}
          waveformStyle={visualizerSettings.waveform_style}
          colorTheme={visualizerSettings.color_theme}
          gradientStyle={visualizerSettings.gradient_style}
          sensitivity={visualizerSettings.sensitivity}
          animationSmoothness={visualizerSettings.animation_smoothness}
          audioOffsetMs={visualizerSettings.audio_offset_ms}
          frequencyRange={visualizerSettings.frequency_range}
          enabled={visualizerSettings.enabled}
          outputMonitor={visualizerSettings.output_monitor}
          onWaveformChange={async (style) => {
            const newSettings = { ...visualizerSettings, waveform_style: style };
            setVisualizerSettings(newSettings);

            // Save to backend
            if (userId && selectedQubes.length > 0) {
              const qubeId = selectedQubes[0].qube_id;
              try {
                await invoke('save_visualizer_settings', {
                  userId,
                  qubeId,
                  settings: JSON.stringify(newSettings),
                  password
                });
                // Invalidate and refresh chain state cache
                invalidateCache(qubeId);
                await loadChainState(qubeId, true);
              } catch (error) {
                console.error('Failed to save waveform style:', error);
              }
            }
          }}
          onToggle={async (enabled) => {
            const newSettings = { ...visualizerSettings, enabled };
            setVisualizerSettings(newSettings);

            // Save to backend
            if (userId && selectedQubes.length > 0) {
              const qubeId = selectedQubes[0].qube_id;
              try {
                await invoke('save_visualizer_settings', {
                  userId,
                  qubeId,
                  settings: JSON.stringify(newSettings),
                  password
                });
                // Invalidate and refresh chain state cache
                invalidateCache(qubeId);
                await loadChainState(qubeId, true);
              } catch (error) {
                console.error('Failed to save visualizer toggle:', error);
              }
            }
          }}
        />
      )}
    </div>
  );
};
