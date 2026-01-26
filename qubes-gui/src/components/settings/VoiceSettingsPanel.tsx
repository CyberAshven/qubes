import { useState, useEffect, useCallback } from 'react';
import { invoke, convertFileSrc } from '@tauri-apps/api/core';
import { GlassCard, GlassButton, GlassInput } from '../glass';
import { useAuth } from '../../hooks/useAuth';
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

  // Voice settings state
  const [ttsEnabled, setTtsEnabled] = useState(false);
  const [voiceLibraryRef, setVoiceLibraryRef] = useState<string | null>(null);
  const [voiceLibrary, setVoiceLibrary] = useState<Record<string, VoiceLibraryEntry>>({});
  const [qwen3Status, setQwen3Status] = useState<Qwen3Status | null>(null);

  // UI state
  const [loading, setLoading] = useState(true);
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
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [isPreviewing, setIsPreviewing] = useState(false);

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

  // Load voice settings when qube changes
  useEffect(() => {
    if (selectedQubeId && password) {
      loadVoiceSettings();
    }
  }, [selectedQubeId, password]);

  // Load Qwen3 status on mount
  useEffect(() => {
    if (userId) {
      checkQwen3Status();
    }
  }, [userId]);

  const loadVoiceSettings = async () => {
    if (!selectedQubeId || !password) return;

    setLoading(true);
    setError(null);

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
        setVoiceLibrary(result.voice_library || {});
      } else {
        setError(result.error || 'Failed to load voice settings');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load voice settings');
    } finally {
      setLoading(false);
    }
  };

  const checkQwen3Status = async () => {
    try {
      const result = await invoke<Qwen3Status & { success: boolean; error?: string }>('check_qwen3_status', {
        userId,
      });

      if (result.success) {
        setQwen3Status(result);
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
        // Refresh voice library
        await loadVoiceSettings();
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
        await loadVoiceSettings();
      } else {
        setError(result.error || 'Failed to delete voice');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete voice');
    }
  };

  const handleRecordCloneAudio = async () => {
    setIsRecording(true);
    try {
      // Use browser's MediaRecorder API for reliable recording
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      const chunks: Blob[] = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunks.push(e.data);
        }
      };

      // Start recording
      mediaRecorder.start();

      // Stop after 5 seconds
      await new Promise<void>((resolve) => {
        setTimeout(() => {
          mediaRecorder.stop();
          stream.getTracks().forEach(track => track.stop());
        }, 5000);

        mediaRecorder.onstop = () => resolve();
      });

      // Convert to blob and save via Tauri
      const blob = new Blob(chunks, { type: 'audio/webm' });
      const arrayBuffer = await blob.arrayBuffer();
      const uint8Array = new Uint8Array(arrayBuffer);

      // Save to temp file via backend
      const result = await invoke<{ success: boolean; audio_path?: string; error?: string }>('save_recorded_audio', {
        userId,
        audioData: Array.from(uint8Array),
      });

      if (result.success && result.audio_path) {
        setCloneAudioPath(result.audio_path);
        // Auto-transcribe
        await handleTranscribeAudio(result.audio_path);
      } else {
        setError(result.error || 'Failed to save recorded audio');
      }
    } catch (err) {
      if (err instanceof Error && err.name === 'NotAllowedError') {
        setError('Microphone access denied. Please allow microphone access in your browser settings.');
      } else {
        setError(err instanceof Error ? err.message : 'Failed to record audio');
      }
    } finally {
      setIsRecording(false);
    }
  };

  const handleTranscribeAudio = async (audioPath: string) => {
    setIsTranscribing(true);
    try {
      const result = await invoke<{ success: boolean; text?: string; error?: string }>('transcribe_audio', {
        userId,
        audioPath,
      });

      if (result.success && result.text) {
        setCloneAudioText(result.text);
      }
    } catch (err) {
      console.error('Failed to transcribe audio:', err);
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

  if (!selectedQubeId) {
    return (
      <div className="text-center text-text-tertiary text-sm py-4">
        Select a Qube from the roster to configure its voice settings.
      </div>
    );
  }

  if (loading) {
    return (
      <div className="text-center text-text-tertiary text-sm py-4">
        Loading voice settings...
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* GPU Status Banner */}
      {qwen3Status && (
        <div className={`p-3 rounded-lg text-xs ${qwen3Status.available ? 'bg-green-500/10 border border-green-500/30' : 'bg-yellow-500/10 border border-yellow-500/30'}`}>
          {qwen3Status.available ? (
            <>
              <div className="flex items-center gap-2">
                <span className="text-green-400">✓</span>
                <span className="text-text-primary font-medium">Qwen3-TTS Available</span>
              </div>
              <p className="text-text-secondary mt-1">
                {qwen3Status.gpu_name} • {qwen3Status.vram_total_gb}GB VRAM • Recommended: {qwen3Status.recommended_variant}
              </p>
            </>
          ) : (
            <>
              <div className="flex items-center gap-2">
                <span className="text-yellow-400">⚠</span>
                <span className="text-text-primary font-medium">Qwen3-TTS Not Available</span>
              </div>
              <p className="text-text-secondary mt-1">
                GPU not detected or insufficient VRAM. Using {qwen3Status.fallback_provider} as fallback.
              </p>
            </>
          )}
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-xs text-red-400">
          {error}
          <button onClick={() => setError(null)} className="ml-2 underline">Dismiss</button>
        </div>
      )}

      {/* TTS Toggle */}
      <div className="flex items-center justify-between">
        <div>
          <span className="text-text-primary text-sm font-medium">Enable TTS for {selectedQubeName || selectedQubeId}</span>
          <p className="text-text-tertiary text-[10px]">Generate voice audio for responses</p>
        </div>
        <button
          onClick={() => handleTtsToggle(!ttsEnabled)}
          disabled={saving}
          className={`w-12 h-6 rounded-full transition-colors ${ttsEnabled ? 'bg-accent-primary' : 'bg-white/10'}`}
        >
          <div className={`w-5 h-5 rounded-full bg-white shadow transition-transform ${ttsEnabled ? 'translate-x-6' : 'translate-x-0.5'}`} />
        </button>
      </div>

      {ttsEnabled && (
        <>
          {/* Voice Selection */}
          <div className="space-y-2">
            <label className="text-text-secondary text-xs font-medium block">Select Voice</label>

            {/* Voice Library */}
            <div className="grid grid-cols-2 gap-2 max-h-40 overflow-y-auto">
              {Object.entries(voiceLibrary).map(([id, voice]) => (
                <button
                  key={id}
                  onClick={() => handleVoiceSelect(`${voice.voice_type}d:${id}`)}
                  className={`p-2 rounded text-left text-xs transition-all ${
                    voiceLibraryRef === `${voice.voice_type}d:${id}`
                      ? 'bg-accent-primary/20 border-2 border-accent-primary/40'
                      : 'bg-white/5 border border-white/10 hover:bg-white/10'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-text-primary font-medium truncate">{voice.name}</span>
                    <button
                      onClick={(e) => { e.stopPropagation(); handleDeleteVoice(id); }}
                      className="text-text-tertiary hover:text-red-400 text-[10px]"
                    >
                      ✕
                    </button>
                  </div>
                  <span className="text-text-tertiary text-[10px] capitalize">{voice.voice_type}</span>
                </button>
              ))}

              {Object.keys(voiceLibrary).length === 0 && (
                <div className="col-span-2 text-center text-text-tertiary text-xs py-4">
                  No voices saved yet. Create one below!
                </div>
              )}
            </div>

            {/* Create Voice Button */}
            <button
              onClick={() => setShowVoiceCreator(!showVoiceCreator)}
              className="w-full py-2 rounded bg-white/5 border border-white/10 text-text-secondary hover:bg-white/10 text-xs"
            >
              {showVoiceCreator ? 'Cancel' : '+ Create New Voice'}
            </button>
          </div>

          {/* Voice Creator */}
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
                  <label className="text-text-secondary text-[10px] block">Voice Sample</label>
                  <div className="flex gap-2">
                    <button
                      onClick={handleRecordCloneAudio}
                      disabled={isRecording}
                      className={`flex-1 py-2 rounded text-xs transition-colors ${
                        isRecording
                          ? 'bg-red-500/20 text-red-400 animate-pulse'
                          : 'bg-white/5 border border-white/10 text-text-secondary hover:bg-white/10'
                      }`}
                    >
                      {isRecording ? '🔴 Recording...' : '🎙️ Record (5s)'}
                    </button>
                    <button
                      onClick={() => {/* File upload */}}
                      className="flex-1 py-2 rounded bg-white/5 border border-white/10 text-text-secondary hover:bg-white/10 text-xs"
                    >
                      📁 Upload File
                    </button>
                  </div>
                  {cloneAudioPath && (
                    <div className="text-[10px] text-text-tertiary">
                      ✓ Audio recorded
                    </div>
                  )}
                  <div>
                    <label className="text-text-secondary text-[10px] block mb-1">Transcript</label>
                    <textarea
                      value={cloneAudioText}
                      onChange={(e) => setCloneAudioText(e.target.value)}
                      placeholder={isTranscribing ? 'Transcribing...' : 'Enter or auto-transcribe the audio content...'}
                      disabled={isTranscribing}
                      className="w-full h-16 px-2 py-1.5 text-xs rounded bg-bg-secondary border border-border-subtle text-text-primary resize-none disabled:opacity-50"
                    />
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

          {/* Model Manager */}
          {qwen3Status?.available && (
            <div>
              <button
                onClick={() => setShowModelManager(!showModelManager)}
                className="text-[10px] text-text-tertiary hover:text-text-secondary"
              >
                ⚙️ Manage Models {showModelManager ? '▲' : '▼'}
              </button>

              {showModelManager && (
                <GlassCard className="p-3 mt-2 space-y-2">
                  <p className="text-[10px] text-text-tertiary">
                    Downloaded models: {qwen3Status.models_downloaded.length > 0 ? qwen3Status.models_downloaded.join(', ') : 'None'}
                  </p>
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
                      {['1.7B-CustomVoice', '1.7B-VoiceDesign', '0.6B-CustomVoice'].map((model) => {
                        const isDownloaded = qwen3Status.models_downloaded.includes(model);
                        return (
                          <div key={model} className="flex items-center gap-1">
                            <button
                              onClick={() => isDownloaded ? null : handleDownloadModel(model)}
                              disabled={isDownloaded}
                              className="flex-1 py-1.5 px-2 rounded bg-white/5 border border-white/10 text-[10px] text-text-secondary hover:bg-white/10 disabled:opacity-50 disabled:cursor-default"
                            >
                              {isDownloaded ? '✓ ' : '⬇️ '}{model}
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
                      })}
                    </div>
                  )}
                </GlassCard>
              )}
            </div>
          )}
        </>
      )}

      {/* Local TTS Setup Section */}
      <GlassCard className="p-4">
        <LocalTTSSetupPanel />
      </GlassCard>
    </div>
  );
};

export default VoiceSettingsPanel;
