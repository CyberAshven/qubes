import { useState, useEffect, useCallback } from 'react';
import { invoke, convertFileSrc } from '@tauri-apps/api/core';
import { GlassCard, GlassButton, GlassInput } from '../glass';
import { useAuth } from '../../hooks/useAuth';
import { useVoiceLibrary } from '../../contexts/VoiceLibraryContext';
import { LocalTTSSetupPanel } from './LocalTTSSetupPanel';

interface VoiceLibraryEntry {
  name: string;
  voice_type: 'designed' | 'cloned';
  created_at: string;
  language: string;
  design_prompt?: string;
  clone_audio_path?: string;
  clone_audio_text?: string;
}

interface Qwen3Status {
  available: boolean;
  gpu_name?: string;
  vram_total_gb?: number;
  vram_available_gb?: number;
  recommended_variant?: string;
  models_downloaded: string[];
  is_loaded: boolean;
  fallback_provider: string;
  model_variant?: string;  // Current user preference: "1.7B" or "0.6B"
}

interface VoiceSettingsPanelProps {
  selectedQubeId: string | null;
  selectedQubeName?: string;
}

const SUPPORTED_LANGUAGES = [
  { code: 'en', name: 'English' },
  { code: 'zh', name: 'Chinese' },
  { code: 'ja', name: 'Japanese' },
  { code: 'ko', name: 'Korean' },
  { code: 'de', name: 'German' },
  { code: 'fr', name: 'French' },
  { code: 'ru', name: 'Russian' },
  { code: 'pt', name: 'Portuguese' },
  { code: 'es', name: 'Spanish' },
  { code: 'it', name: 'Italian' },
];

const PRESET_VOICES = [
  { id: 'Vivian', name: 'Vivian', description: 'Female, warm and natural' },
  { id: 'Serena', name: 'Serena', description: 'Female, calm and professional' },
  { id: 'Dylan', name: 'Dylan', description: 'Male, friendly and conversational' },
  { id: 'Eric', name: 'Eric', description: 'Male, confident and clear' },
  { id: 'Ryan', name: 'Ryan', description: 'Male, energetic and engaging' },
  { id: 'Aiden', name: 'Aiden', description: 'Male, youthful and casual' },
  { id: 'Ono_Anna', name: 'Ono Anna', description: 'Female, Japanese accent' },
  { id: 'Sohee', name: 'Sohee', description: 'Female, Korean accent' },
  { id: 'Uncle_Fu', name: 'Uncle Fu', description: 'Male, Chinese accent' },
];

export const VoiceSettingsPanel: React.FC<VoiceSettingsPanelProps> = ({
  selectedQubeId,
  selectedQubeName,
}) => {
  const { userId, password } = useAuth();
  const { voiceLibrary, refreshVoiceLibrary, isLoading: voiceLibraryLoading } = useVoiceLibrary();

  // Voice settings state
  const [ttsEnabled, setTtsEnabled] = useState(false);
  const [voiceLibraryRef, setVoiceLibraryRef] = useState<string | null>(null);
  const [qwen3Status, setQwen3Status] = useState<Qwen3Status | null>(null);

  // UI state - loading tracks Qwen3 status check
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Voice creation state
  const [showVoiceCreator, setShowVoiceCreator] = useState(false);
  const [voiceCreatorMode, setVoiceCreatorMode] = useState<'design' | 'clone' | 'preset'>('preset');
  const [newVoiceName, setNewVoiceName] = useState('');
  const [newVoiceLanguage, setNewVoiceLanguage] = useState('en');
  const [designPrompt, setDesignPrompt] = useState('');
  const [selectedPreset, setSelectedPreset] = useState('Vivian');
  const [cloneAudioPath, setCloneAudioPath] = useState('');
  const [cloneAudioText, setCloneAudioText] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [recordingCountdown, setRecordingCountdown] = useState<number | null>(null);
  const [recordingSuccess, setRecordingSuccess] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [isPreviewing, setIsPreviewing] = useState(false);
  const [previewingVoiceId, setPreviewingVoiceId] = useState<string | null>(null);
  const [transcriptionError, setTranscriptionError] = useState<string | null>(null);

  // Model variant preference
  const [modelVariant, setModelVariant] = useState<string>("1.7B");
  const [savingVariant, setSavingVariant] = useState(false);

  // Model download state
  const [showModelManager, setShowModelManager] = useState(false);
  const [downloadingModel, setDownloadingModel] = useState<string | null>(null);
  const [downloadProgress, setDownloadProgress] = useState(0);
  const [downloadCurrentFile, setDownloadCurrentFile] = useState('');
  const [downloadSpeed, setDownloadSpeed] = useState(0);
  const [downloadEta, setDownloadEta] = useState(0);
  const [downloadFilesCompleted, setDownloadFilesCompleted] = useState(0);
  const [downloadFilesTotal, setDownloadFilesTotal] = useState(0);
  const [downloadedBytes, setDownloadedBytes] = useState(0);
  const [totalBytes, setTotalBytes] = useState(0);

  // Format bytes to human readable
  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
  };

  // Check Qwen3 status on mount
  useEffect(() => {
    if (userId) {
      checkQwen3Status();
    }
  }, [userId]);

  // Load qube-specific settings when qube changes (for TTS toggle)
  useEffect(() => {
    if (selectedQubeId && password) {
      loadQubeVoiceSettings();
    }
  }, [selectedQubeId, password]);

  // Load qube-specific voice settings (TTS enabled, selected voice)
  const loadQubeVoiceSettings = async () => {
    if (!selectedQubeId || !password) return;

    try {
      const result = await invoke<{
        success: boolean;
        error?: string;
        voice_library_ref?: string;
        tts_enabled?: boolean;
        voice_library?: Record<string, VoiceLibraryEntry>;
      }>('get_voice_settings', {
        userId,
        qubeId: selectedQubeId,
        password,
      });

      if (result.success) {
        setVoiceLibraryRef(result.voice_library_ref || null);
        setTtsEnabled(result.tts_enabled || false);
        // Voice library is now managed by VoiceLibraryContext
      } else {
        setError(result.error || 'Failed to load voice settings');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load voice settings');
    }
  };

  // Deprecated - replaced by loadVoiceLibrary and loadQubeVoiceSettings
  const loadVoiceSettings = loadQubeVoiceSettings;

  const checkQwen3Status = async () => {
    try {
      const result = await invoke<Qwen3Status & { success: boolean; error?: string }>('check_qwen3_status', {
        userId,
      });

      if (result.success) {
        setQwen3Status(result);
        // Initialize model variant from preferences
        if (result.model_variant) {
          setModelVariant(result.model_variant);
        }
      }
    } catch (err) {
      console.error('Failed to check Qwen3 status:', err);
    }
  };

  const handleTtsToggle = async (enabled: boolean) => {
    if (!selectedQubeId || !password) return;

    setSaving(true);
    try {
      const result = await invoke<{ success: boolean; error?: string }>('update_voice_settings', {
        userId,
        qubeId: selectedQubeId,
        password,
        ttsEnabled: enabled,
      });

      if (result.success) {
        setTtsEnabled(enabled);
      } else {
        setError(result.error || 'Failed to update TTS setting');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update TTS setting');
    } finally {
      setSaving(false);
    }
  };

  const handleVoiceSelect = async (ref: string) => {
    if (!selectedQubeId || !password) return;

    setSaving(true);
    try {
      const result = await invoke<{ success: boolean; error?: string }>('update_voice_settings', {
        userId,
        qubeId: selectedQubeId,
        password,
        voiceLibraryRef: ref,
      });

      if (result.success) {
        setVoiceLibraryRef(ref);
      } else {
        setError(result.error || 'Failed to select voice');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to select voice');
    } finally {
      setSaving(false);
    }
  };

  const handlePreviewVoice = async () => {
    setIsPreviewing(true);
    try {
      const previewText = "Hello! This is a preview of your selected voice.";
      const result = await invoke<{ success: boolean; audio_path?: string; error?: string }>('preview_voice', {
        userId,
        text: previewText,
        voiceType: voiceCreatorMode,
        language: newVoiceLanguage,
        designPrompt: voiceCreatorMode === 'design' ? designPrompt : undefined,
        cloneAudioPath: voiceCreatorMode === 'clone' ? cloneAudioPath : undefined,
        cloneAudioText: voiceCreatorMode === 'clone' ? cloneAudioText : undefined,
        presetVoice: voiceCreatorMode === 'preset' ? selectedPreset : undefined,
      });

      if (result.success && result.audio_path) {
        // Play the preview audio (use convertFileSrc for Tauri security)
        const audioUrl = convertFileSrc(result.audio_path);
        const audio = new Audio(audioUrl);
        await audio.play();
      } else {
        setError(result.error || 'Failed to generate preview');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to preview voice');
    } finally {
      setIsPreviewing(false);
    }
  };

  // Preview a voice from the library
  const handlePreviewLibraryVoice = async (voiceId: string) => {
    const voice = voiceLibrary[voiceId];
    if (!voice) return;

    setPreviewingVoiceId(voiceId);
    try {
      const previewText = "Hello! This is a preview of your custom voice.";
      const result = await invoke<{ success: boolean; audio_path?: string; error?: string }>('preview_voice', {
        userId,
        text: previewText,
        voiceType: voice.voice_type === 'cloned' ? 'clone' : 'design',
        language: voice.language,
        designPrompt: voice.design_prompt,
        cloneAudioPath: voice.clone_audio_path,
        cloneAudioText: voice.clone_audio_text,
      });

      if (result.success && result.audio_path) {
        const audioUrl = convertFileSrc(result.audio_path);
        const audio = new Audio(audioUrl);
        await audio.play();
      } else {
        setError(result.error || 'Failed to generate preview');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to preview voice');
    } finally {
      setPreviewingVoiceId(null);
    }
  };

  const handleSaveVoice = async () => {
    if (!newVoiceName.trim()) {
      setError('Please enter a name for your voice');
      return;
    }

    setSaving(true);
    try {
      const voiceType = voiceCreatorMode === 'clone' ? 'cloned' : 'designed';
      const result = await invoke<{ success: boolean; voice_id?: string; error?: string }>('add_voice_to_library', {
        userId,
        name: newVoiceName,
        voiceType,
        language: newVoiceLanguage,
        designPrompt: voiceCreatorMode === 'design' ? designPrompt : undefined,
        cloneAudioPath: voiceCreatorMode === 'clone' ? cloneAudioPath : undefined,
        cloneAudioText: voiceCreatorMode === 'clone' ? cloneAudioText : undefined,
      });

      if (result.success) {
        // Refresh voice library via shared context (updates all components)
        console.log('[VoiceSettingsPanel] Refreshing voice library via context');
        await refreshVoiceLibrary();
        // Reset creator
        setShowVoiceCreator(false);
        setNewVoiceName('');
        setDesignPrompt('');
        setCloneAudioPath('');
        setCloneAudioText('');
      } else {
        setError(result.error || 'Failed to save voice');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save voice');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteVoice = async (voiceId: string) => {
    try {
      const result = await invoke<{ success: boolean; error?: string }>('delete_voice_from_library', {
        userId,
        voiceId,
      });

      if (result.success) {
        // Refresh voice library via shared context (updates all components)
        await refreshVoiceLibrary();
      } else {
        setError(result.error || 'Failed to delete voice');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete voice');
    }
  };

  const handleRecordCloneAudio = async () => {
    setIsRecording(true);
    setRecordingSuccess(false);
    setError(null);
    setTranscriptionError(null);
    setRecordingCountdown(10);

    // Track live transcription
    let liveTranscript = '';

    try {
      console.log('[Recording] Requesting microphone access...');

      // Use browser's MediaRecorder API for reliable recording
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      console.log('[Recording] Got microphone stream');

      // Try different mime types for compatibility
      let mimeType = 'audio/webm';
      if (!MediaRecorder.isTypeSupported(mimeType)) {
        mimeType = 'audio/ogg';
        if (!MediaRecorder.isTypeSupported(mimeType)) {
          mimeType = 'audio/mp4';
          if (!MediaRecorder.isTypeSupported(mimeType)) {
            mimeType = ''; // Let browser choose default
          }
        }
      }
      console.log('[Recording] Using mime type:', mimeType || 'default');

      const mediaRecorder = mimeType
        ? new MediaRecorder(stream, { mimeType })
        : new MediaRecorder(stream);
      const chunks: Blob[] = [];

      mediaRecorder.ondataavailable = (e) => {
        console.log('[Recording] Data available:', e.data.size, 'bytes');
        if (e.data.size > 0) {
          chunks.push(e.data);
        }
      };

      mediaRecorder.onerror = (e) => {
        console.error('[Recording] MediaRecorder error:', e);
      };

      // Start browser's native speech recognition for live transcription (same as Chat tab)
      let recognition: any = null;
      let recognitionStarted = false;
      let recognitionGotResults = false;
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      console.log('[Recording] SpeechRecognition API available:', !!SpeechRecognition);

      if (SpeechRecognition) {
        recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        const lang = newVoiceLanguage === 'zh' ? 'zh-CN' :
                    newVoiceLanguage === 'ja' ? 'ja-JP' :
                    newVoiceLanguage === 'ko' ? 'ko-KR' :
                    newVoiceLanguage === 'de' ? 'de-DE' :
                    newVoiceLanguage === 'fr' ? 'fr-FR' :
                    newVoiceLanguage === 'ru' ? 'ru-RU' :
                    newVoiceLanguage === 'pt' ? 'pt-BR' :
                    newVoiceLanguage === 'es' ? 'es-ES' :
                    newVoiceLanguage === 'it' ? 'it-IT' : 'en-US';
        recognition.lang = lang;
        console.log('[Recording] Speech recognition language:', lang);

        recognition.onstart = () => {
          console.log('[Recording] Speech recognition actually started');
          recognitionStarted = true;
        };

        recognition.onaudiostart = () => {
          console.log('[Recording] Speech recognition audio started');
        };

        recognition.onsoundstart = () => {
          console.log('[Recording] Speech recognition sound detected');
        };

        recognition.onspeechstart = () => {
          console.log('[Recording] Speech recognition speech detected');
        };

        recognition.onresult = (event: any) => {
          recognitionGotResults = true;
          let transcript = '';
          // Use resultIndex to properly handle continuous results (same as Chat tab)
          for (let i = event.resultIndex; i < event.results.length; i++) {
            const result = event.results[i];
            transcript += result[0].transcript;
            console.log('[Recording] Result', i, '- isFinal:', result.isFinal, 'transcript:', result[0].transcript);
          }
          if (transcript) {
            liveTranscript = transcript;
            // Update transcript field in real-time
            setCloneAudioText(transcript);
            console.log('[Recording] Live transcript:', transcript);
          }
        };

        recognition.onerror = (event: any) => {
          console.warn('[Recording] Speech recognition error:', event.error, event.message);
          // Common errors: 'no-speech', 'audio-capture', 'not-allowed', 'network'
          if (event.error === 'network') {
            console.error('[Recording] Network error - speech recognition requires internet connection');
          }
        };

        recognition.onnomatch = () => {
          console.log('[Recording] Speech recognition: no match found (speech detected but not recognized)');
        };

        recognition.onend = () => {
          console.log('[Recording] Speech recognition ended. Got results:', recognitionGotResults);
          // If recognition ended without results but we detected speech, it might be a network issue
          if (!recognitionGotResults && recognitionStarted) {
            console.warn('[Recording] Speech was detected but no transcript - possible network issue with speech recognition service');
          }
        };

        try {
          recognition.start();
          console.log('[Recording] Called recognition.start()');
        } catch (e) {
          console.warn('[Recording] Could not start speech recognition:', e);
        }
      } else {
        console.log('[Recording] Speech recognition not available - will need manual transcript');
      }

      // Start recording
      mediaRecorder.start(1000); // Collect data every 1 second
      console.log('[Recording] Started recording...');

      // Countdown timer
      const countdownInterval = setInterval(() => {
        setRecordingCountdown(prev => {
          if (prev === null || prev <= 1) {
            clearInterval(countdownInterval);
            return null;
          }
          return prev - 1;
        });
      }, 1000);

      // Stop after 10 seconds (more audio = better voice cloning)
      await new Promise<void>((resolve, reject) => {
        const timeout = setTimeout(() => {
          console.log('[Recording] Stopping after 10 seconds...');
          clearInterval(countdownInterval);
          setRecordingCountdown(null);
          mediaRecorder.stop();
          stream.getTracks().forEach(track => track.stop());
          // Delay stopping speech recognition to let it finish processing
          // The recognition service may still be processing audio
          if (recognition) {
            setTimeout(() => {
              try {
                console.log('[Recording] Now stopping speech recognition...');
                recognition.stop();
              } catch (e) {
                // Ignore
              }
            }, 1500); // Wait 1.5 seconds for results to come in
          }
        }, 10000);

        mediaRecorder.onstop = () => {
          clearTimeout(timeout);
          console.log('[Recording] Stopped, total chunks:', chunks.length);
          resolve();
        };

        mediaRecorder.onerror = (e) => {
          clearTimeout(timeout);
          clearInterval(countdownInterval);
          if (recognition) {
            try { recognition.stop(); } catch (e) { /* ignore */ }
          }
          reject(new Error('MediaRecorder error: ' + e));
        };
      });

      // Convert to blob and save via Tauri
      const actualMimeType = mediaRecorder.mimeType || 'audio/webm';
      console.log('[Recording] Creating blob with type:', actualMimeType);
      const blob = new Blob(chunks, { type: actualMimeType });
      console.log('[Recording] Blob size:', blob.size, 'bytes');

      if (blob.size === 0) {
        throw new Error('Recording produced no audio data');
      }

      const arrayBuffer = await blob.arrayBuffer();
      const uint8Array = new Uint8Array(arrayBuffer);
      console.log('[Recording] Sending', uint8Array.length, 'bytes to backend...');

      // Save to temp file via backend
      const result = await invoke<{ success: boolean; audio_path?: string; error?: string }>('save_recorded_audio', {
        userId,
        audioData: Array.from(uint8Array),
      });
      console.log('[Recording] Backend result:', JSON.stringify(result));

      if (result.success && result.audio_path) {
        console.log('[Recording] Success! Audio saved to:', result.audio_path);
        setCloneAudioPath(result.audio_path);
        setRecordingSuccess(true);

        // Use the live transcript if we got one
        if (liveTranscript) {
          console.log('[Recording] Using live transcript:', liveTranscript);
          setCloneAudioText(liveTranscript);
        } else if (!cloneAudioText) {
          // No transcript - show hint to type manually
          setTranscriptionError('Speech recognition did not capture text. Please type the transcript manually.');
        }
      } else {
        console.log('[Recording] Failed:', result.error);
        setError(result.error || 'Failed to save recorded audio');
      }
    } catch (err) {
      console.error('[Recording] Error:', err);
      if (err instanceof Error) {
        if (err.name === 'NotAllowedError') {
          setError('Microphone access denied. Please allow microphone access.');
        } else if (err.name === 'NotFoundError') {
          setError('No microphone found. Please connect a microphone.');
        } else {
          setError(`Recording failed: ${err.message}`);
        }
      } else {
        setError('Failed to record audio: ' + String(err));
      }
    } finally {
      setIsRecording(false);
      setRecordingCountdown(null);
    }
  };

  const handleTranscribeAudio = async (audioPath: string) => {
    setIsTranscribing(true);
    setTranscriptionError(null);
    try {
      console.log('[Transcribe] Starting transcription for:', audioPath);
      const result = await invoke<{ success: boolean; text?: string; error?: string; stt_available?: boolean; debug?: any }>('transcribe_audio', {
        userId,
        audioPath,
      });
      console.log('[Transcribe] Full result:', JSON.stringify(result, null, 2));
      if (result.debug) {
        console.log('[Transcribe] Debug info:', result.debug);
      }

      if (result.success && result.text) {
        setCloneAudioText(result.text);
        console.log('[Transcribe] Success! Text:', result.text);
      } else if (result.error) {
        // Transcription failed - show a helpful message
        console.warn('[Transcribe] Failed:', result.error);
        if (result.error.includes('OPENAI_API_KEY')) {
          setTranscriptionError('Auto-transcription requires OpenAI API key. Please type the transcript manually.');
        } else if (result.error.includes('All STT providers failed')) {
          setTranscriptionError('Transcription service error. Please type the transcript manually.');
        } else {
          setTranscriptionError('Auto-transcription unavailable. Please type the transcript manually.');
        }
      }
    } catch (err) {
      console.error('[Transcribe] Exception:', err);
      setTranscriptionError('Transcription failed. Please type the transcript manually.');
    } finally {
      setIsTranscribing(false);
    }
  };

  const handleDeleteModel = async (modelName: string) => {
    if (!confirm(`Delete ${modelName}? This will remove the downloaded model files.`)) {
      return;
    }

    try {
      const result = await invoke<{ success: boolean; error?: string }>('delete_qwen3_model', {
        userId,
        modelName,
      });

      if (result.success) {
        await checkQwen3Status(); // Refresh the list
      } else {
        setError(result.error || 'Failed to delete model');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete model');
    }
  };

  const handleModelVariantChange = async (variant: string) => {
    setSavingVariant(true);
    try {
      const result = await invoke<{ success: boolean; error?: string }>('update_qwen3_preferences', {
        userId,
        modelVariant: variant,
      });

      if (result.success) {
        setModelVariant(variant);
      } else {
        setError(result.error || 'Failed to update model variant');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update model variant');
    } finally {
      setSavingVariant(false);
    }
  };

  const handleDownloadModel = async (modelName: string) => {
    setDownloadingModel(modelName);
    setDownloadProgress(0);

    try {
      const result = await invoke<{ success: boolean; download_id?: string; error?: string }>('download_qwen3_model', {
        userId,
        modelName,
      });

      if (result.success && result.download_id) {
        // Poll for progress
        const pollProgress = async () => {
          try {
            const progress = await invoke<{
              success: boolean;
              percentage?: number;
              status?: string;
              current_file?: string;
              files_completed?: number;
              files_total?: number;
              speed_mbps?: number;
              eta_seconds?: number;
              downloaded_bytes?: number;
              total_bytes?: number;
              error?: string;
            }>('get_qwen3_download_progress', {
              userId,
              downloadId: result.download_id,
            });

            if (progress.success) {
              setDownloadProgress(progress.percentage || 0);
              setDownloadCurrentFile(progress.current_file || '');
              setDownloadSpeed(progress.speed_mbps || 0);
              setDownloadEta(progress.eta_seconds || 0);
              setDownloadFilesCompleted(progress.files_completed || 0);
              setDownloadFilesTotal(progress.files_total || 0);
              setDownloadedBytes(progress.downloaded_bytes || 0);
              setTotalBytes(progress.total_bytes || 0);

              if (progress.status === 'completed') {
                setDownloadingModel(null);
                await checkQwen3Status();
              } else if (progress.status === 'failed') {
                setError(progress.error || 'Download failed');
                setDownloadingModel(null);
              } else if (progress.status === 'cancelled') {
                setDownloadingModel(null);
              } else {
                setTimeout(pollProgress, 500); // Poll more frequently for smoother updates
              }
            }
          } catch {
            setDownloadingModel(null);
          }
        };
        pollProgress();
      } else {
        setError(result.error || 'Failed to start download');
        setDownloadingModel(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to download model');
      setDownloadingModel(null);
    }
  };

  if (loading) {
    return (
      <div className="text-center text-text-tertiary text-sm py-4">
        Loading voice settings...
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Error Display */}
      {error && (
        <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-xs text-red-400">
          {error}
          <button onClick={() => setError(null)} className="ml-2 underline">Dismiss</button>
        </div>
      )}

      {/* Voice Library - Always visible (user-level, not qube-specific) */}
      <div className="space-y-2">
        <label className="text-text-secondary text-xs font-medium block">Your Voice Library</label>

        {/* Voice Library Grid */}
        <div className="grid grid-cols-2 gap-2 max-h-48 overflow-y-auto">
          {Object.entries(voiceLibrary).map(([id, voice]) => (
            <div
              key={id}
              className="p-3 rounded-lg text-left bg-white/5 border border-white/10 hover:bg-white/10 transition-colors"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-text-primary font-medium truncate text-sm">{voice.name}</span>
                <button
                  onClick={() => handleDeleteVoice(id)}
                  className="text-text-tertiary hover:text-red-400 text-xs"
                  title="Delete voice"
                >
                  ✕
                </button>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-text-tertiary text-xs capitalize">{voice.voice_type} • {voice.language}</span>
                <button
                  onClick={() => handlePreviewLibraryVoice(id)}
                  disabled={previewingVoiceId === id}
                  className={`px-3 py-1.5 rounded-md text-sm font-medium transition-all ${
                    previewingVoiceId === id
                      ? 'bg-accent-primary/30 text-accent-primary'
                      : 'bg-accent-primary/20 text-accent-primary hover:bg-accent-primary/30'
                  } disabled:opacity-70`}
                  title="Preview voice"
                >
                  {previewingVoiceId === id ? '🔊 Playing...' : '▶ Preview'}
                </button>
              </div>
            </div>
          ))}

          {Object.keys(voiceLibrary).length === 0 && (
            <div className="col-span-2 text-center text-text-tertiary text-xs py-4">
              No custom voices yet. Create one below!
            </div>
          )}
        </div>

        {/* Create Voice Button */}
        <button
          onClick={() => setShowVoiceCreator(!showVoiceCreator)}
          className="w-full py-2 rounded bg-accent-primary/20 border border-accent-primary/40 text-accent-primary hover:bg-accent-primary/30 text-xs font-medium"
        >
          {showVoiceCreator ? 'Cancel' : '+ Create New Voice'}
        </button>
      </div>


      {/* Voice Creator - Always available */}
      {showVoiceCreator && (
            <GlassCard className="p-3 space-y-3">
              {/* Mode Tabs */}
              <div className="flex gap-1 bg-white/5 p-1 rounded">
                {(['preset', 'design', 'clone'] as const).map((mode) => (
                  <button
                    key={mode}
                    onClick={() => setVoiceCreatorMode(mode)}
                    className={`flex-1 py-1.5 rounded text-xs transition-colors ${
                      voiceCreatorMode === mode
                        ? 'bg-accent-primary/20 text-accent-primary'
                        : 'text-text-secondary hover:text-text-primary'
                    }`}
                  >
                    {mode === 'preset' && '🎤 Preset'}
                    {mode === 'design' && '✨ Design'}
                    {mode === 'clone' && '🧬 Clone'}
                  </button>
                ))}
              </div>

              {/* Voice Name */}
              <div>
                <label className="text-text-secondary text-[10px] block mb-1">Voice Name</label>
                <GlassInput
                  value={newVoiceName}
                  onChange={(e) => setNewVoiceName(e.target.value)}
                  placeholder="My Custom Voice"
                  className="h-7 text-xs"
                />
              </div>

              {/* Language */}
              <div>
                <label className="text-text-secondary text-[10px] block mb-1">Language</label>
                <select
                  value={newVoiceLanguage}
                  onChange={(e) => setNewVoiceLanguage(e.target.value)}
                  className="w-full h-7 px-2 text-xs rounded bg-bg-secondary border border-border-subtle text-text-primary"
                >
                  {SUPPORTED_LANGUAGES.map((lang) => (
                    <option key={lang.code} value={lang.code}>{lang.name}</option>
                  ))}
                </select>
              </div>

              {/* Mode-specific inputs */}
              {voiceCreatorMode === 'preset' && (
                <div>
                  <label className="text-text-secondary text-[10px] block mb-1">Select Preset Voice</label>
                  <div className="grid grid-cols-3 gap-1 max-h-32 overflow-y-auto">
                    {PRESET_VOICES.map((voice) => (
                      <button
                        key={voice.id}
                        onClick={() => setSelectedPreset(voice.id)}
                        className={`p-1.5 rounded text-[10px] text-left ${
                          selectedPreset === voice.id
                            ? 'bg-accent-primary/20 border border-accent-primary/40'
                            : 'bg-white/5 border border-white/10 hover:bg-white/10'
                        }`}
                        title={voice.description}
                      >
                        {voice.name}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {voiceCreatorMode === 'design' && (
                <div>
                  <label className="text-text-secondary text-[10px] block mb-1">Describe the Voice</label>
                  <textarea
                    value={designPrompt}
                    onChange={(e) => setDesignPrompt(e.target.value)}
                    placeholder="A warm, friendly female voice with a slight British accent..."
                    className="w-full h-20 px-2 py-1.5 text-xs rounded bg-bg-secondary border border-border-subtle text-text-primary resize-none"
                  />
                </div>
              )}

              {voiceCreatorMode === 'clone' && (
                <div className="space-y-2">
                  <label className="text-text-secondary text-[10px] block">Voice Sample (10 seconds of clear speech for best results)</label>
                  <div className="flex gap-2">
                    <button
                      onClick={handleRecordCloneAudio}
                      disabled={isRecording}
                      className={`flex-1 py-2 rounded text-xs transition-colors ${
                        isRecording
                          ? 'bg-red-500/20 text-red-400 border-2 border-red-500/50'
                          : 'bg-white/5 border border-white/10 text-text-secondary hover:bg-white/10'
                      }`}
                    >
                      {isRecording
                        ? `🔴 Recording... ${recordingCountdown !== null ? `${recordingCountdown}s` : ''}`
                        : '🎙️ Record (10s)'}
                    </button>
                    <label className="flex-1 py-2 rounded bg-white/5 border border-white/10 text-text-secondary hover:bg-white/10 text-xs text-center cursor-pointer">
                      📁 Upload File
                      <input
                        type="file"
                        accept="audio/*"
                        className="hidden"
                        onChange={async (e) => {
                          const file = e.target.files?.[0];
                          if (!file) return;

                          try {
                            setIsRecording(true);
                            setRecordingSuccess(false);
                            setError(null);

                            const arrayBuffer = await file.arrayBuffer();
                            const uint8Array = new Uint8Array(arrayBuffer);

                            const result = await invoke<{ success: boolean; audio_path?: string; error?: string }>('save_recorded_audio', {
                              userId,
                              audioData: Array.from(uint8Array),
                            });

                            if (result.success && result.audio_path) {
                              setCloneAudioPath(result.audio_path);
                              setRecordingSuccess(true);
                              await handleTranscribeAudio(result.audio_path);
                            } else {
                              setError(result.error || 'Failed to upload audio');
                            }
                          } catch (err) {
                            setError(err instanceof Error ? err.message : 'Failed to upload audio');
                          } finally {
                            setIsRecording(false);
                          }
                        }}
                      />
                    </label>
                  </div>
                  {/* Success message - more prominent */}
                  {recordingSuccess && cloneAudioPath && (
                    <div className="p-2 rounded-lg bg-green-500/10 border border-green-500/30 flex items-center gap-2">
                      <span className="text-green-400 text-lg">✓</span>
                      <div>
                        <p className="text-green-400 text-xs font-medium">Audio captured successfully!</p>
                        <p className="text-green-400/70 text-[10px]">{cloneAudioPath.split(/[/\\]/).pop()}</p>
                      </div>
                    </div>
                  )}
                  {/* Transcribing indicator */}
                  {isTranscribing && (
                    <div className="p-2 rounded-lg bg-blue-500/10 border border-blue-500/30 flex items-center gap-2">
                      <span className="text-blue-400 animate-spin">⟳</span>
                      <p className="text-blue-400 text-xs">Transcribing audio...</p>
                    </div>
                  )}
                  {/* Transcription error/notice */}
                  {transcriptionError && !isTranscribing && (
                    <div className="p-2 rounded-lg bg-yellow-500/10 border border-yellow-500/30 flex items-center gap-2">
                      <span className="text-yellow-400">⚠</span>
                      <p className="text-yellow-400 text-xs">{transcriptionError}</p>
                    </div>
                  )}
                  <div>
                    <label className="text-text-secondary text-[10px] block mb-1">
                      Transcript {cloneAudioText && <span className="text-green-400">(ready)</span>}
                    </label>
                    <textarea
                      value={cloneAudioText}
                      onChange={(e) => setCloneAudioText(e.target.value)}
                      placeholder={isTranscribing ? 'Transcribing...' : 'Type exactly what was said in the recording...'}
                      disabled={isTranscribing}
                      className={`w-full h-16 px-2 py-1.5 text-xs rounded bg-bg-secondary border text-text-primary resize-none disabled:opacity-50 ${
                        recordingSuccess && !cloneAudioText && !isTranscribing
                          ? 'border-yellow-500/50 focus:border-yellow-500'
                          : 'border-border-subtle'
                      }`}
                    />
                    <p className="text-text-tertiary text-[9px] mt-0.5">
                      {recordingSuccess && !cloneAudioText && !isTranscribing
                        ? '↑ Type the words spoken in the recording to enable voice cloning'
                        : 'Accurate transcript improves voice cloning quality'}
                    </p>
                  </div>
                </div>
              )}

              {/* Actions */}
              <div className="flex gap-2">
                <button
                  onClick={handlePreviewVoice}
                  disabled={isPreviewing}
                  className="flex-1 py-2 rounded bg-white/5 border border-white/10 text-text-secondary hover:bg-white/10 text-xs disabled:opacity-50"
                >
                  {isPreviewing ? '🔊 Playing...' : '🔊 Preview'}
                </button>
                <button
                  onClick={handleSaveVoice}
                  disabled={saving || !newVoiceName.trim()}
                  className="flex-1 py-2 rounded bg-accent-primary/20 border border-accent-primary/40 text-accent-primary hover:bg-accent-primary/30 text-xs disabled:opacity-50"
                >
                  {saving ? 'Saving...' : '💾 Save to Library'}
                </button>
              </div>
            </GlassCard>
          )}

          {/* Download Voice Models */}
          {qwen3Status?.available && (
            <GlassCard className="p-3 space-y-3">
              <div
                className="flex items-center justify-between cursor-pointer"
                onClick={() => setShowModelManager(!showModelManager)}
              >
                <div>
                  <h4 className="text-sm font-medium text-text-primary">📥 Download Qwen Voice Models</h4>
                  <p className="text-[10px] text-text-tertiary mt-0.5">
                    Download AI models to enable voice design, cloning, and presets
                  </p>
                </div>
                <span className={`text-text-tertiary transition-transform ${showModelManager ? 'rotate-180' : ''}`}>
                  ▼
                </span>
              </div>

              {showModelManager && (
                <div className="space-y-2 pt-2 border-t border-white/10">
                  {/* Model Variant Selector */}
                  <div className="bg-white/5 rounded p-2">
                    <div className="flex items-center justify-between">
                      <div>
                        <label className="text-text-secondary text-[10px] font-medium">Model Size</label>
                        <p className="text-[9px] text-text-tertiary">Larger = better quality, Smaller = faster</p>
                      </div>
                      <select
                        value={modelVariant}
                        onChange={(e) => handleModelVariantChange(e.target.value)}
                        disabled={savingVariant}
                        className="h-7 px-2 text-xs rounded bg-bg-secondary border border-border-subtle text-text-primary disabled:opacity-50"
                      >
                        <option value="1.7B">1.7B (Best Quality)</option>
                        <option value="0.6B">0.6B (Faster)</option>
                      </select>
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-1 text-[9px]">
                    {qwen3Status.models_downloaded.length > 0 ? (
                      qwen3Status.models_downloaded.map(m => (
                        <span key={m} className="bg-green-500/20 text-green-400 px-1.5 py-0.5 rounded">✓ {m}</span>
                      ))
                    ) : (
                      <span className="text-text-tertiary">No models downloaded yet</span>
                    )}
                  </div>
                  {downloadingModel && (
                    <div className="bg-white/5 rounded p-2 space-y-1.5">
                      <div className="flex items-center justify-between">
                        <p className="text-[10px] text-text-secondary">Downloading {downloadingModel}</p>
                        <p className="text-[10px] text-text-tertiary">
                          {downloadFilesTotal > 0 ? `${downloadFilesCompleted}/${downloadFilesTotal} files` : 'Preparing...'}
                        </p>
                      </div>
                      <div className="w-full bg-white/10 rounded-full h-2">
                        <div
                          className={`h-2 rounded-full transition-all duration-300 ${
                            totalBytes === 0 ? 'bg-accent-primary/50 animate-pulse w-full' : 'bg-accent-primary'
                          }`}
                          style={totalBytes > 0 ? { width: `${downloadProgress}%` } : undefined}
                        />
                      </div>
                      <div className="flex items-center justify-between text-[10px] text-text-tertiary">
                        <span>
                          {totalBytes > 0
                            ? `${downloadProgress.toFixed(1)}% • ${formatBytes(downloadedBytes)} / ${formatBytes(totalBytes)}`
                            : 'Calculating size...'
                          }
                        </span>
                        <span>
                          {downloadSpeed > 0 && `${downloadSpeed.toFixed(1)} MB/s`}
                          {downloadEta > 0 && downloadSpeed > 0 && ' • '}
                          {downloadEta > 0 && (
                            downloadEta > 60
                              ? `${Math.floor(downloadEta / 60)}m ${Math.round(downloadEta % 60)}s left`
                              : `${Math.round(downloadEta)}s left`
                          )}
                        </span>
                      </div>
                      {downloadCurrentFile && (
                        <p className="text-[9px] text-text-tertiary truncate" title={downloadCurrentFile}>
                          📄 {downloadCurrentFile}
                        </p>
                      )}
                    </div>
                  )}
                  {!downloadingModel && (
                    <div className="grid grid-cols-2 gap-1">
                      {(() => {
                        // Model sizes in GB (approximate, from HuggingFace)
                        // Note: 0.6B-VoiceDesign doesn't exist - VoiceDesign only available in 1.7B
                        const modelSizes: Record<string, string> = {
                          '1.7B-CustomVoice': '3.5 GB',
                          '1.7B-VoiceDesign': '3.5 GB',
                          '1.7B-Base': '3.4 GB',
                          '0.6B-CustomVoice': '1.3 GB',
                          '0.6B-Base': '1.2 GB',
                        };
                        return ['1.7B-CustomVoice', '1.7B-VoiceDesign', '1.7B-Base', '0.6B-CustomVoice', '0.6B-Base'].map((model) => {
                          const isDownloaded = qwen3Status.models_downloaded.includes(model);
                          const size = modelSizes[model] || '';
                          return (
                            <div key={model} className="flex items-center gap-1">
                              <button
                                onClick={() => isDownloaded ? null : handleDownloadModel(model)}
                                disabled={isDownloaded}
                                className="flex-1 py-1.5 px-2 rounded bg-white/5 border border-white/10 text-[10px] text-text-secondary hover:bg-white/10 disabled:opacity-50 disabled:cursor-default"
                              >
                                {isDownloaded ? '✓ ' : '⬇️ '}{model} <span className="text-text-tertiary">({size})</span>
                              </button>
                            {isDownloaded && (
                              <button
                                onClick={() => handleDeleteModel(model)}
                                className="p-1.5 rounded bg-red-500/10 border border-red-500/20 text-red-400 hover:bg-red-500/20 text-[10px]"
                                title={`Delete ${model}`}
                              >
                                🗑️
                              </button>
                            )}
                            </div>
                          );
                        });
                      })()}
                    </div>
                  )}
                </div>
              )}
            </GlassCard>
          )}

      {/* Local TTS Setup Section */}
      <GlassCard className="p-4">
        <LocalTTSSetupPanel />
      </GlassCard>
    </div>
  );
};

export default VoiceSettingsPanel;
