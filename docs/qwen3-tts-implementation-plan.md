# Qwen3-TTS Integration Plan (Detailed)

## Overview

Add Qwen3-TTS as a new TTS provider with voice design, voice cloning, and a Voice Library for managing reusable voices.

## User Flow Summary

1. **First-time setup**: User downloads models via Settings > Voice Settings
2. **Create voices**: Design via natural language or clone from audio recording
3. **Assign to qubes**: Select voices from library for each qube
4. **Background loading**: Models load when user sends message (parallel to AI response)
5. **Group chats**: Single VoiceDesign model handles all designed voices

---

## Phase 1: Voice Library Data Model

### New Dataclass: `config/user_preferences.py`

Add after `AudioPreferences` (around line 37):

```python
@dataclass
class VoiceLibraryEntry:
    """A saved voice in the user's library."""
    name: str                          # User-given name (e.g., "Wise Mentor")
    voice_type: str                    # "designed" or "cloned"
    created_at: str                    # ISO timestamp
    language: str = "en"               # Language code (en, zh, ja, ko, de, fr, ru, pt, es, it)

    # For designed voices
    design_prompt: Optional[str] = None  # Natural language description

    # For cloned voices
    clone_audio_path: Optional[str] = None   # Path to audio file (~/.qubes/voice_clones/{user_id}/{voice_id}.wav)
    clone_audio_text: Optional[str] = None   # Transcript of audio


@dataclass
class Qwen3Preferences:
    """Qwen3-TTS specific preferences."""
    model_variant: str = "1.7B"           # "1.7B" or "0.6B"
    use_flash_attention: bool = True

    # Voice library: Dict[voice_id, VoiceLibraryEntry]
    # voice_id is a slugified version of name (e.g., "wise_mentor")
    voice_library: Dict[str, Dict] = field(default_factory=dict)
```

Update `AudioPreferences`:

```python
@dataclass
class AudioPreferences:
    """Preferences for audio/TTS configuration."""
    google_tts_credentials_path: Optional[str] = None

    # NEW: Qwen3-TTS preferences
    qwen3: Optional[Dict] = None  # Serialized Qwen3Preferences
```

### Update: `UserPreferences` class

Add to `__init__` and serialization methods.

### New Manager Methods: `UserPreferencesManager`

```python
# Voice Library Management
def get_voice_library(self) -> Dict[str, VoiceLibraryEntry]: ...
def add_voice_to_library(self, voice: VoiceLibraryEntry) -> str: ...  # Returns voice_id
def update_voice_in_library(self, voice_id: str, updates: Dict) -> None: ...
def delete_voice_from_library(self, voice_id: str) -> None: ...
def get_voice_by_id(self, voice_id: str) -> Optional[VoiceLibraryEntry]: ...

# Qwen3 Settings
def get_qwen3_preferences(self) -> Qwen3Preferences: ...
def update_qwen3_preferences(self, **kwargs) -> None: ...
```

---

## Phase 2: Per-Qube Voice Settings

### Update: `core/chain_state.py`

#### Add to `create_default_chain_state()` settings section (line ~111):

```python
"settings": {
    # ... existing fields ...
    "tts_enabled": tts_enabled,
    "voice_model": voice_model,           # Existing: "openai:alloy", "qwen3:wise_mentor"
    # NEW fields for Qwen3
    "voice_library_ref": None,            # Reference to voice library entry (e.g., "designed:wise_mentor")
}
```

#### Add to `GUI_MANAGED_FIELDS` set (line ~262):

```python
GUI_MANAGED_FIELDS = {
    # ... existing ...
    "tts_enabled",
    "voice_model",
    "voice_library_ref",  # NEW
}
```

#### Add accessor methods (after line ~3145):

```python
def get_voice_library_ref(self) -> Optional[str]:
    """Get the voice library reference for this qube."""
    self._ensure_fresh()
    return self.state.get("settings", {}).get("voice_library_ref")

def set_voice_library_ref(self, ref: Optional[str]) -> None:
    """Set the voice library reference (e.g., 'designed:wise_mentor')."""
    settings = self.state.setdefault("settings", {})
    settings["voice_library_ref"] = ref

    # Also update voice_model for compatibility
    if ref:
        settings["voice_model"] = f"qwen3:{ref.split(':')[1]}"

    self._save(preserve_gui_fields=False)
```

---

## Phase 3: Qwen3-TTS Provider

### New File: `audio/qwen_tts.py`

```python
"""
Qwen3-TTS Provider

Local high-quality TTS with voice cloning and voice design.
"""

from abc import ABC
from pathlib import Path
from typing import AsyncIterator, Dict, Any, Optional
import asyncio
import struct

from audio.tts_engine import TTSProvider, VoiceConfig
from core.exceptions import AIError
from utils.logging import get_logger
from monitoring.metrics import MetricsRecorder

logger = get_logger(__name__)


class Qwen3TTSProvider(TTSProvider):
    """Local Qwen3-TTS provider with voice design and cloning."""

    MODELS = {
        "1.7B-VoiceDesign": "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
        "1.7B-Base": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        "0.6B-VoiceDesign": "Qwen/Qwen3-TTS-12Hz-0.6B-VoiceDesign",
        "0.6B-Base": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
    }

    PRESET_VOICES = {
        "Vivian": "A warm, friendly young female voice with clear enunciation",
        "Serena": "A calm, soothing female voice with professional demeanor",
        "Dylan": "A confident young male voice with energetic American accent",
        "Ryan": "A friendly, approachable male voice with natural conversation style",
        # ... more presets as design prompts
    }

    VRAM_REQUIREMENTS = {
        "1.7B": {"single": 5.0, "both": 9.0},  # VoiceDesign only vs VoiceDesign+Base
        "0.6B": {"single": 2.5, "both": 4.5},
    }

    def __init__(
        self,
        models_dir: Optional[Path] = None,
        variant: str = "1.7B",
        device: str = "cuda",
        use_flash_attention: bool = True
    ):
        self.models_dir = Path(models_dir or Path.home() / ".qubes" / "models" / "qwen3-tts")
        self.variant = variant
        self.device = device
        self.use_flash_attention = use_flash_attention

        # Lazy-loaded models
        self._voice_design_model = None
        self._base_model = None
        self._tokenizer = None
        self._loading_lock = asyncio.Lock()
        self._loading_task: Optional[asyncio.Task] = None

    # --- Availability Check ---

    def check_availability(self) -> Dict[str, Any]:
        """Check GPU/VRAM/model status."""
        # Returns: available, gpu_name, vram_total_gb, vram_available_gb,
        #          recommended_variant, models_downloaded, error
        ...

    def get_downloaded_models(self) -> list[str]:
        """List downloaded model names."""
        ...

    # --- Model Loading (Background) ---

    def start_background_load(self, need_cloning: bool = False) -> None:
        """
        Start loading models in background (non-blocking).

        Call this when user sends a message to a TTS-enabled qube.
        Loading happens in parallel with AI response generation.

        Args:
            need_cloning: If True, also load Base model for voice cloning
        """
        if self._loading_task and not self._loading_task.done():
            return  # Already loading

        self._loading_task = asyncio.create_task(
            self._load_models_async(need_cloning)
        )

    async def _load_models_async(self, need_cloning: bool) -> None:
        """Async model loading (runs in background)."""
        async with self._loading_lock:
            if self._voice_design_model is None:
                await self._load_voice_design_model()

            if need_cloning and self._base_model is None:
                await self._load_base_model()

    async def ensure_ready(self, need_cloning: bool = False) -> None:
        """
        Ensure models are loaded (blocking if necessary).

        Call this before synthesis. If background loading started,
        this will wait for it to complete.
        """
        if self._loading_task:
            await self._loading_task

        if self._voice_design_model is None:
            await self._load_voice_design_model()

        if need_cloning and self._base_model is None:
            await self._load_base_model()

    def unload_models(self) -> None:
        """Unload all models to free VRAM."""
        ...

    # --- Synthesis Methods ---

    async def synthesize_stream(
        self, text: str, voice_config: VoiceConfig
    ) -> AsyncIterator[bytes]:
        """Stream audio chunks (TTSProvider interface)."""
        ...

    async def synthesize_file(
        self, text: str, voice_config: VoiceConfig, output_path: Path
    ) -> Path:
        """Generate complete audio file (TTSProvider interface)."""
        ...

    async def generate_voice_design(
        self, text: str, design_prompt: str, language: str = "en"
    ) -> bytes:
        """Generate speech using voice design."""
        ...

    async def generate_voice_clone(
        self, text: str, ref_audio_path: Path, ref_audio_text: str, language: str = "en"
    ) -> bytes:
        """Generate speech using voice cloning."""
        ...

    async def generate_preview(
        self, design_prompt: Optional[str] = None,
        clone_audio_path: Optional[Path] = None,
        clone_audio_text: Optional[str] = None
    ) -> bytes:
        """Generate a short preview (~10 words) for the voice."""
        preview_text = "Hello! This is a sample of how I will sound."

        if design_prompt:
            return await self.generate_voice_design(preview_text, design_prompt)
        elif clone_audio_path:
            return await self.generate_voice_clone(
                preview_text, clone_audio_path, clone_audio_text
            )
        else:
            raise AIError("Must provide design_prompt or clone_audio_path")


# Standalone availability check
def check_qwen3_availability() -> Dict[str, Any]:
    """Check Qwen3-TTS availability without instantiating provider."""
    ...
```

### Update: `audio/tts_engine.py` - VoiceConfig

Add new fields (after line 30):

```python
class VoiceConfig:
    def __init__(
        self,
        provider: str = "openai",
        voice_id: str = "alloy",
        speed: float = 1.0,
        pitch: float | None = None,
        stability: float | None = None,
        # NEW: Qwen3-TTS fields
        voice_mode: str | None = None,           # "designed", "cloned", "preset"
        voice_design_prompt: str | None = None,
        clone_audio_path: str | None = None,
        clone_audio_text: str | None = None,
        language: str | None = None,             # Language code for Qwen3 (en, zh, ja, ko, de, fr, ru, pt, es, it)
    ):
        # ... existing assignments ...
        self.voice_mode = voice_mode
        self.voice_design_prompt = voice_design_prompt
        self.clone_audio_path = clone_audio_path
        self.clone_audio_text = clone_audio_text
        self.language = language
```

### Update: `audio/audio_manager.py`

Add lazy loading in `_init_tts_providers()` (after Piper, ~line 207):

```python
# Qwen3-TTS (local GPU) - lazy initialization
# Check is deferred to first use to avoid loading torch at startup
self.tts_providers["qwen3"] = None  # Lazy load marker
```

Add helper method:

```python
def _check_gpu_available(self) -> bool:
    """Check if CUDA GPU is available for Qwen3-TTS."""
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False

def _get_qwen3_provider(self) -> Optional['Qwen3TTSProvider']:
    """Get or lazily initialize Qwen3 provider."""
    if "qwen3" not in self.tts_providers:
        return None

    if self.tts_providers["qwen3"] is None:
        if not self._check_gpu_available():
            logger.warning("qwen3_gpu_not_available")
            del self.tts_providers["qwen3"]
            return None

        from audio.qwen_tts import Qwen3TTSProvider
        self.tts_providers["qwen3"] = Qwen3TTSProvider(
            variant=self.config.get("qwen3_variant", "1.7B"),
            use_flash_attention=self.config.get("qwen3_flash_attention", True),
        )

    return self.tts_providers["qwen3"]

def start_qwen3_background_load(self, need_cloning: bool = False) -> None:
    """
    Start loading Qwen3 models in background.

    Call when user sends message to TTS-enabled qube with Qwen3 provider.
    """
    provider = self._get_qwen3_provider()
    if provider:
        provider.start_background_load(need_cloning)
```

---

## Phase 4: GUI Bridge Commands

### Add to `gui_bridge.py` (in the command dispatch section ~line 9900+):

```python
# =========================================================================
# VOICE LIBRARY & QWEN3-TTS COMMANDS
# =========================================================================

elif command == "get-voice-library":
    # Get all voices in user's library
    # Args: user_id
    # Returns: { voices: [{voice_id, name, voice_type, created_at, ...}] }
    ...

elif command == "add-voice-to-library":
    # Add a new voice (designed or cloned)
    # Args: user_id, name, voice_type, design_prompt?, clone_audio_path?, clone_audio_text?
    # Returns: { success, voice_id }
    ...

elif command == "update-voice-in-library":
    # Update an existing voice
    # Args: user_id, voice_id, updates_json
    # Returns: { success }
    ...

elif command == "delete-voice-from-library":
    # Delete a voice
    # Args: user_id, voice_id
    # Returns: { success, warning? } (warning if voice is in use)
    ...

elif command == "preview-voice":
    # Generate preview audio for a voice config
    # Args: user_id, voice_type, design_prompt?, clone_audio_path?, clone_audio_text?
    # Returns: { success, audio_path }
    ...

elif command == "record-voice-clone":
    # Start recording for voice cloning (uses existing STT infrastructure)
    # Args: user_id, duration_seconds (default: 5)
    # Returns: { success, audio_path, transcript }
    ...

elif command == "get-qube-voice-settings":
    # Get voice settings for a qube
    # Args: user_id, qube_id, password
    # Returns: { tts_enabled, voice_provider, voice_library_ref, ... }
    ...

elif command == "update-qube-voice-settings":
    # Update voice settings for a qube
    # Args: user_id, qube_id, password, settings_json
    # Returns: { success }
    ...

elif command == "check-qwen3-status":
    # Check GPU/models/VRAM status
    # Args: user_id
    # Returns: { available, gpu_name, vram_total_gb, vram_available_gb,
    #            recommended_variant, models_downloaded }
    ...

elif command == "download-qwen3-model":
    # Start model download (background, with progress events)
    # Args: user_id, model_name
    # Returns: { success, download_id }
    ...

elif command == "get-download-progress":
    # Get download progress
    # Args: user_id, download_id
    # Returns: { status, progress_percent, bytes_downloaded, bytes_total, speed_mbps }
    ...

elif command == "cancel-qwen3-download":
    # Cancel in-progress download
    # Args: user_id, download_id
    # Returns: { success }
    ...

elif command == "delete-qwen3-model":
    # Delete a downloaded model
    # Args: user_id, model_name
    # Returns: { success }
    ...
```

### Add Tauri Commands: `qubes-gui/src-tauri/src/lib.rs`

Add corresponding `#[tauri::command]` functions that call gui_bridge.

---

## Phase 5: Voice Settings UI

### Fix: SettingsTab Qube Selection (Use Roster Instead of Dropdown)

**Problem**: SettingsTab currently uses a dropdown (`selectedQubeForTrust`) for Trust Personality settings. This is inconsistent with other tabs that use roster selection.

**Solution**: Wire up `useQubeSelection` hook to SettingsTab so both Trust Personality AND Voice Settings use the roster-selected qube.

**Changes to `SettingsTab.tsx`**:

```tsx
// REMOVE these lines:
const [selectedQubeForTrust, setSelectedQubeForTrust] = useState<string>('');

// ADD this import:
import { useQubeSelection } from '../../hooks/useQubeSelection';

// ADD this hook usage:
const { selectionByTab } = useQubeSelection();
const selectedQubeId = selectionByTab['settings']?.[0] || null;

// REMOVE the qube dropdown from Trust Personality section

// ADD "no qube selected" message when selectedQubeId is null:
{!selectedQubeId && (
  <div className="p-4 text-center text-text-secondary">
    <p>Select a qube from the roster to configure settings.</p>
  </div>
)}
```

This change affects:
1. **Trust Personality** - Remove dropdown, use `selectedQubeId` from roster
2. **Voice Settings** - Use same `selectedQubeId` from roster

### New File: `qubes-gui/src/components/settings/VoiceSettingsPanel.tsx`

```tsx
interface VoiceSettingsPanelProps {
  userId: string;
  password: string;
  selectedQubeId: string | null;  // From useQubeSelection, not a dropdown
}

export const VoiceSettingsPanel: React.FC<VoiceSettingsPanelProps> = ({
  userId, password, selectedQubeId
}) => {
  // State
  const [qwen3Status, setQwen3Status] = useState<Qwen3Status | null>(null);
  const [voiceLibrary, setVoiceLibrary] = useState<VoiceEntry[]>([]);
  const [qubeVoiceSettings, setQubeVoiceSettings] = useState<VoiceSettings | null>(null);
  const [activeTab, setActiveTab] = useState<'library' | 'qube' | 'models'>('qube');

  // Load data on mount
  useEffect(() => { loadQwen3Status(); loadVoiceLibrary(); }, [userId]);
  useEffect(() => { if (selectedQubeId) loadQubeVoiceSettings(); }, [selectedQubeId]);

  return (
    <div className="space-y-4">
      {/* GPU Status Banner */}
      {qwen3Status && (
        <div className={`p-3 rounded ${qwen3Status.available ? 'bg-accent-success/10' : 'bg-accent-warning/10'}`}>
          {qwen3Status.available ? (
            <>
              <p className="text-xs font-medium">GPU: {qwen3Status.gpu_name}</p>
              <p className="text-[10px] text-text-secondary">
                VRAM: {qwen3Status.vram_available_gb}GB available / {qwen3Status.vram_total_gb}GB total
              </p>
            </>
          ) : (
            <p className="text-xs text-accent-warning">
              Qwen3-TTS requires NVIDIA GPU. Using cloud TTS providers.
            </p>
          )}
        </div>
      )}

      {/* Tab Navigation */}
      <div className="flex gap-2 border-b border-white/10 pb-2">
        <TabButton active={activeTab === 'qube'} onClick={() => setActiveTab('qube')}>
          Qube Voice
        </TabButton>
        <TabButton active={activeTab === 'library'} onClick={() => setActiveTab('library')}>
          Voice Library
        </TabButton>
        <TabButton active={activeTab === 'models'} onClick={() => setActiveTab('models')}>
          Models
        </TabButton>
      </div>

      {/* Qube Voice Tab - Configure voice for selected qube */}
      {activeTab === 'qube' && selectedQubeId && (
        <QubeVoiceConfig
          qubeId={selectedQubeId}
          settings={qubeVoiceSettings}
          voiceLibrary={voiceLibrary}
          onSave={handleSaveQubeVoice}
        />
      )}

      {/* Voice Library Tab - Manage saved voices */}
      {activeTab === 'library' && (
        <VoiceLibraryManager
          voices={voiceLibrary}
          onAddVoice={handleAddVoice}
          onEditVoice={handleEditVoice}
          onDeleteVoice={handleDeleteVoice}
          onPreviewVoice={handlePreviewVoice}
        />
      )}

      {/* Models Tab - Download/manage Qwen3 models */}
      {activeTab === 'models' && qwen3Status?.available && (
        <ModelManager
          status={qwen3Status}
          onDownload={handleDownloadModel}
          onDelete={handleDeleteModel}
        />
      )}
    </div>
  );
};
```

### Sub-components:

**QubeVoiceConfig.tsx** - Per-qube voice selection
```tsx
// Provider dropdown (OpenAI, ElevenLabs, Gemini, Qwen3)
// If Qwen3: Voice selector from library
// Preview button
// Save button
```

**VoiceLibraryManager.tsx** - Voice library CRUD
```tsx
// List of saved voices with preview/edit/delete
// "New Designed Voice" button -> DesignVoiceModal
// "New Cloned Voice" button -> CloneVoiceModal
```

**DesignVoiceModal.tsx** - Create designed voice
```tsx
// Name input
// Language dropdown (English, Chinese, Japanese, Korean, German, French, Russian, Portuguese, Spanish, Italian)
// Design prompt textarea
// Preview button
// Save button
```

**CloneVoiceModal.tsx** - Create cloned voice
```tsx
// Name input
// Language dropdown (same options)
// Record button (hold to record) OR Upload file
// Playback of recording
// Transcript textarea (auto-filled via STT, editable)
// Save button
```

**ModelManager.tsx** - Qwen3 model downloads
```tsx
// List of models with status (Downloaded / Not downloaded)
// Download buttons with progress bars
// Delete buttons for downloaded models
// VRAM usage indicator
```

### Update: `qubes-gui/src/components/tabs/SettingsTab.tsx`

Add Voice Settings panel (after Google TTS, ~line 997):

```tsx
{/* Voice Settings */}
<GlassCard className="p-4 mt-4">
  <button
    onClick={() => togglePanel('voiceSettings')}
    className="w-full flex items-center justify-between text-left"
  >
    <h2 className="text-lg font-display text-text-primary">
      🎙️ Voice Settings
    </h2>
    <span className={`text-text-tertiary transition-transform ${collapsedPanels.voiceSettings ? '' : 'rotate-180'}`}>
      ▼
    </span>
  </button>

  {!collapsedPanels.voiceSettings && (
    <VoiceSettingsPanel
      userId={userId}
      password={password}
      selectedQubeId={selectedQubeFromRoster}  // From context/props
    />
  )}
</GlassCard>
```

---

## Phase 6: Background Model Loading Integration

### Where to Trigger Background Loading

In the message sending flow, when user sends a message to a TTS-enabled qube with Qwen3:

**File**: Likely in `gui_bridge.py` or the orchestrator

```python
# In send-message handler, before calling AI:

# Check if qube uses Qwen3 TTS
chain_state = qube_manager.get_chain_state(qube_id)
if chain_state.is_tts_enabled():
    voice_model = chain_state.get_voice_model()
    if voice_model.startswith("qwen3:"):
        # Start background model loading
        voice_ref = chain_state.get_voice_library_ref()
        need_cloning = voice_ref and voice_ref.startswith("cloned:")
        audio_manager.start_qwen3_background_load(need_cloning)

# Now proceed with AI call (models load in parallel)
response = await qube.send_message(...)
```

### Model Loading Timeline

```
T+0ms    User sends message
         ├─ Check TTS settings
         ├─ Start background model load (if Qwen3 + TTS enabled)
         └─ Send to AI provider

T+100ms  Model loading begins (async)

T+2000ms AI response starts streaming

T+3000ms Model loading completes (typical)

T+5000ms AI response complete
         └─ TTS generation begins (model already loaded)

T+5500ms TTS audio ready, playback starts
```

---

## Phase 7: Model Download Manager

### New File: `audio/model_downloader.py`

```python
"""
Qwen3-TTS Model Downloader

Downloads models from HuggingFace with progress tracking.
"""

import asyncio
from pathlib import Path
from typing import Callable, Optional
from huggingface_hub import hf_hub_download, snapshot_download

from utils.logging import get_logger

logger = get_logger(__name__)


class ModelDownloader:
    """Manages Qwen3-TTS model downloads."""

    MODELS = {
        "1.7B-VoiceDesign": {
            "repo_id": "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
            "size_gb": 4.2,
            "description": "Create voices from text descriptions",
        },
        "1.7B-Base": {
            "repo_id": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
            "size_gb": 4.0,
            "description": "Voice cloning from audio samples",
        },
        "0.6B-VoiceDesign": {
            "repo_id": "Qwen/Qwen3-TTS-12Hz-0.6B-VoiceDesign",
            "size_gb": 1.8,
            "description": "Lightweight voice design (lower quality)",
        },
        "0.6B-Base": {
            "repo_id": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
            "size_gb": 1.6,
            "description": "Lightweight voice cloning (lower quality)",
        },
    }

    def __init__(self, models_dir: Optional[Path] = None):
        self.models_dir = Path(models_dir or Path.home() / ".qubes" / "models" / "qwen3-tts")
        self.models_dir.mkdir(parents=True, exist_ok=True)

        self._active_downloads: Dict[str, asyncio.Task] = {}
        self._download_progress: Dict[str, Dict] = {}

    def get_model_status(self) -> Dict[str, Dict]:
        """Get status of all models."""
        status = {}
        for name, info in self.MODELS.items():
            model_path = self.models_dir / info["repo_id"].split("/")[-1]
            status[name] = {
                **info,
                "downloaded": model_path.exists(),
                "path": str(model_path) if model_path.exists() else None,
            }
        return status

    async def download_model(
        self,
        model_name: str,
        progress_callback: Optional[Callable[[float, int, int], None]] = None
    ) -> Path:
        """
        Download a model from HuggingFace.

        Args:
            model_name: Model name (e.g., "1.7B-VoiceDesign")
            progress_callback: Called with (progress_percent, bytes_done, bytes_total)

        Returns:
            Path to downloaded model directory
        """
        ...

    def cancel_download(self, model_name: str) -> bool:
        """Cancel an in-progress download."""
        ...

    def delete_model(self, model_name: str) -> bool:
        """Delete a downloaded model."""
        ...
```

---

## Files to Create/Modify Summary

| File | Action | Changes |
|------|--------|---------|
| `config/user_preferences.py` | MODIFY | Add `VoiceLibraryEntry`, `Qwen3Preferences`, voice library methods |
| `core/chain_state.py` | MODIFY | Add `voice_library_ref` to settings, GUI_MANAGED_FIELDS, accessor methods |
| `audio/qwen_tts.py` | CREATE | `Qwen3TTSProvider` class with background loading |
| `audio/model_downloader.py` | CREATE | Model download manager |
| `audio/tts_engine.py` | MODIFY | Add Qwen3 fields to `VoiceConfig` |
| `audio/audio_manager.py` | MODIFY | Add Qwen3 lazy loading, background load trigger |
| `gui_bridge.py` | MODIFY | Add 12 voice-related commands |
| `qubes-gui/src-tauri/src/lib.rs` | MODIFY | Add Tauri command wrappers |
| `qubes-gui/src/components/settings/VoiceSettingsPanel.tsx` | CREATE | Main voice settings UI |
| `qubes-gui/src/components/settings/VoiceLibraryManager.tsx` | CREATE | Voice library CRUD |
| `qubes-gui/src/components/settings/DesignVoiceModal.tsx` | CREATE | Create designed voice |
| `qubes-gui/src/components/settings/CloneVoiceModal.tsx` | CREATE | Create cloned voice |
| `qubes-gui/src/components/settings/ModelManager.tsx` | CREATE | Model download UI |
| `qubes-gui/src/components/tabs/SettingsTab.tsx` | MODIFY | Add Voice Settings panel, **remove qube dropdown**, use `useQubeSelection` for both Trust Personality and Voice Settings |

---

## Implementation Order

1. **Phase 1**: Voice Library data model (`user_preferences.py`)
2. **Phase 2**: Per-qube settings (`chain_state.py`)
3. **Phase 3**: Qwen3 provider (`qwen_tts.py`, `audio_manager.py`)
4. **Phase 7**: Model downloader (`model_downloader.py`)
5. **Phase 4**: GUI bridge commands (`gui_bridge.py`)
6. **Phase 5**: Voice Settings UI (all TSX files)
7. **Phase 6**: Background loading integration

---

## Testing Checklist

- [ ] Voice library CRUD (create designed, create cloned, update, delete)
- [ ] Preview generation (designed, cloned)
- [ ] Voice recording via microphone
- [ ] Auto-transcription of recording
- [ ] Per-qube voice assignment
- [ ] Model download with progress
- [ ] Model loading (immediate + background)
- [ ] TTS generation with designed voice
- [ ] TTS generation with cloned voice
- [ ] Language selection (test non-English languages)
- [ ] Group chat with multiple Qwen3 voices
- [ ] VRAM check and warnings
- [ ] Graceful handling when GPU unavailable

---

## Phase 8: Dependencies & Bundling

### Update: `requirements.txt`

Add new section after "AUDIO INTEGRATION" (~line 124):

```
# ============================================================================
# QWEN3-TTS LOCAL GPU (Phase 7 - Voice Design & Cloning)
# ============================================================================
# Note: These dependencies add ~2-3GB to the installer but enable
# high-quality local TTS with voice design and cloning capabilities.

# PyTorch with CUDA support
torch>=2.0.0                    # Deep learning framework with CUDA
torchaudio>=2.0.0               # Audio processing for TTS

# HuggingFace ecosystem
transformers>=4.40.0            # Model loading and inference
huggingface_hub>=0.23.0         # Model downloads from HuggingFace
accelerate>=0.30.0              # Optimized model loading
safetensors>=0.4.0              # Fast model weight loading

# Optional: FlashAttention for ~20% VRAM reduction
# Requires CUDA compilation, may not work on all systems
# flash-attn>=2.0.0
```

### Update: `qubes-gui/src-tauri/qubes-backend.spec`

Add hidden imports for PyTorch and transformers:

```python
a = Analysis(
    ['..\\..\\gui_bridge.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'chess',
        # Qwen3-TTS dependencies
        'torch',
        'torchaudio',
        'transformers',
        'transformers.models.qwen2',
        'huggingface_hub',
        'accelerate',
        'safetensors',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
```

### PyInstaller Considerations

PyTorch with CUDA requires special handling:

1. **Collect all torch files**:
   ```python
   from PyInstaller.utils.hooks import collect_all

   torch_datas, torch_binaries, torch_hiddenimports = collect_all('torch')
   torchaudio_datas, torchaudio_binaries, torchaudio_hiddenimports = collect_all('torchaudio')

   a = Analysis(
       ...
       datas=torch_datas + torchaudio_datas,
       binaries=torch_binaries + torchaudio_binaries,
       hiddenimports=[...] + torch_hiddenimports + torchaudio_hiddenimports,
   )
   ```

2. **CUDA libraries**: PyInstaller should automatically include CUDA DLLs from the torch installation. Verify these are present in the bundle:
   - `cublas64_*.dll`
   - `cudnn64_*.dll`
   - `cudart64_*.dll`
   - `cufft64_*.dll`

3. **Bundle size**: Expect final installer to be ~2.5-3GB (up from ~100MB)

### Files to Modify Summary (Updated)

| File | Action | Changes |
|------|--------|---------|
| `requirements.txt` | MODIFY | Add torch, torchaudio, transformers, huggingface_hub, accelerate, safetensors |
| `qubes-gui/src-tauri/qubes-backend.spec` | MODIFY | Add hidden imports and collect_all for torch |

### Installer Size Breakdown (Estimated)

| Component | Size |
|-----------|------|
| Base Qubes app | ~100 MB |
| PyTorch + CUDA | ~2.0 GB |
| Transformers + dependencies | ~300 MB |
| Qwen3-TTS models (downloaded separately) | ~4-8 GB |
| **Total installer** | **~2.5 GB** |
| **Total with models** | **~6-10 GB** |

### Runtime GPU Detection

Even with torch bundled, we still need graceful handling for non-GPU systems:

```python
# In qwen_tts.py
def check_availability() -> Dict[str, Any]:
    result = {
        "available": False,
        "gpu_name": None,
        "vram_total_gb": None,
        "vram_available_gb": None,
        "error": None,
    }

    try:
        import torch
        if not torch.cuda.is_available():
            result["error"] = "No NVIDIA GPU detected. Qwen3-TTS requires CUDA."
            return result

        result["gpu_name"] = torch.cuda.get_device_name(0)
        props = torch.cuda.get_device_properties(0)
        result["vram_total_gb"] = round(props.total_memory / (1024**3), 1)
        result["vram_available_gb"] = round(
            (props.total_memory - torch.cuda.memory_allocated(0)) / (1024**3), 1
        )
        result["available"] = True

    except Exception as e:
        result["error"] = f"GPU check failed: {str(e)}"

    return result
```

In the UI, if GPU is not available, show:
```
+------------------------------------------+
| Qwen3-TTS Unavailable                    |
+------------------------------------------+
| No NVIDIA GPU detected.                  |
|                                          |
| Qwen3-TTS requires an NVIDIA GPU with    |
| at least 4GB VRAM for voice design.      |
|                                          |
| You can still use cloud TTS providers:   |
| • OpenAI TTS                             |
| • ElevenLabs                             |
| • Google Cloud TTS                       |
| • Gemini TTS                             |
+------------------------------------------+
```
