import React, { useState, useEffect, useRef, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { open } from '@tauri-apps/plugin-dialog';
import { invoke, convertFileSrc } from '@tauri-apps/api/core';
import Cropper, { Area } from 'react-easy-crop';
import { GlassCard, GlassButton, GlassInput } from '../glass';
import DarkSelect from '../DarkSelect';
import { Qube } from '../../types';
import { useAuth } from '../../hooks/useAuth';
import { useModels } from '../../hooks/useModels';
import { useVoiceLibrary } from '../../contexts/VoiceLibraryContext';
import { useWallet } from '../../contexts/WalletContext';
import WalletConnectButton from '../WalletConnectButton';

// Helper: create a cropped image from canvas and return base64 PNG
async function getCroppedImg(imageSrc: string, croppedAreaPixels: Area): Promise<string> {
  const image = new Image();
  image.crossOrigin = 'anonymous';
  await new Promise<void>((resolve, reject) => {
    image.onload = () => resolve();
    image.onerror = reject;
    image.src = imageSrc;
  });

  const canvas = document.createElement('canvas');
  const size = Math.min(croppedAreaPixels.width, croppedAreaPixels.height, 512);
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext('2d')!;

  ctx.drawImage(
    image,
    croppedAreaPixels.x,
    croppedAreaPixels.y,
    croppedAreaPixels.width,
    croppedAreaPixels.height,
    0, 0, size, size
  );

  // Return raw base64 (no data: prefix)
  return canvas.toDataURL('image/png').replace(/^data:image\/png;base64,/, '');
}

interface CreateQubeModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreate: (data: CreateQubeData) => Promise<void>;
  onQubesChange?: () => void;  // Called when qube creation is complete (for refreshing list)
}

export interface CreateQubeData {
  name: string;
  genesisPrompt: string;
  aiProvider: string;
  aiModel: string;
  voiceModel?: string;
  ownerPubkey: string;  // Compressed public key - NFT address derived automatically
  walletAddress?: string;  // Optional - derived from ownerPubkey by backend
  encryptGenesis?: boolean;
  favoriteColor: string;
  avatarFile?: string;
  generateAvatar?: boolean;
  avatarStyle?: string;
}

// Voice name aliases for cleaner display
const VOICE_NAME_ALIASES: Record<string, string> = {
  // Kokoro voices
  'af_heart': 'Heart',
  'af_bella': 'Bella',
  'af_nova': 'Nova',
  'af_sarah': 'Sarah',
  'am_adam': 'Adam',
  'am_michael': 'Michael',
  'bf_emma': 'Emma',
  'bf_lily': 'Lily',
  'bm_george': 'George',
  'bm_daniel': 'Daniel',
  'jf_alpha': 'Alpha',
  'jm_kumo': 'Kumo',
  'zf_xiaoxiao': 'Xiaoxiao',
  'zm_yunxi': 'Yunxi',
  'ef_dora': 'Dora',
  'ff_siwis': 'Siwis',
  // Qwen3 voices
  'Vivian': 'Vivian',
  'Serena': 'Serena',
  'Dylan': 'Dylan',
  'Eric': 'Eric',
  'Ryan': 'Ryan',
  'Aiden': 'Aiden',
  'Ono_Anna': 'Ono Anna',
  'Uncle_Fu': 'Uncle Fu',
  'Sohee': 'Sohee',
};

// Format voice name for display (use alias or capitalize)
const formatVoiceName = (voiceId: string): string => {
  if (!voiceId) return 'Select voice';
  const voice = voiceId.includes(':') ? voiceId.split(':')[1] : voiceId;
  return VOICE_NAME_ALIASES[voice] || voice.charAt(0).toUpperCase() + voice.slice(1);
};

// Voice gender mapping
const getVoiceGender = (voiceId: string): string => {
  const voiceName = voiceId.includes(':') ? voiceId.split(':')[1].toLowerCase() : voiceId.toLowerCase();

  // Gemini voices
  const geminiMale = ['achernar', 'algenib', 'alnilam', 'charon', 'fenrir', 'gacrux', 'iapetus', 'orus', 'puck', 'rasalgethi', 'sadachbia', 'sadaltager', 'umbriel', 'zephyr'];
  const geminiFemale = ['achird', 'algieba', 'aoede', 'autonoe', 'callirrhoe', 'despina', 'enceladus', 'erinome', 'kore', 'laomedeia', 'leda', 'pulcherrima', 'schedar', 'sulafat', 'vindemiatrix', 'zubenelgenubi'];

  // OpenAI voices (9 total for tts-1 model)
  const openaiMale = ['ash', 'echo', 'fable', 'onyx'];
  const openaiFemale = ['alloy', 'coral', 'nova', 'sage', 'shimmer'];

  // Google Cloud TTS voices (Standard, WaveNet, Neural2, Studio, Chirp)
  const googleMale = [
    'standard-a', 'standard-b', 'standard-d', 'standard-i', 'standard-j',
    'wavenet-a', 'wavenet-b', 'wavenet-d', 'wavenet-i', 'wavenet-j',
    'neural2-a', 'neural2-d', 'neural2-i', 'neural2-j',
    'studio-q', 'chirp-hd-d'
  ];
  const googleFemale = [
    'standard-c', 'standard-e', 'standard-f', 'standard-g', 'standard-h',
    'wavenet-c', 'wavenet-e', 'wavenet-f', 'wavenet-g', 'wavenet-h',
    'neural2-c', 'neural2-e', 'neural2-f', 'neural2-g', 'neural2-h',
    'studio-o', 'chirp-hd-f'
  ];

  // Qwen3-TTS voices
  const qwen3Male = ['dylan', 'eric', 'ryan', 'aiden', 'uncle_fu'];
  const qwen3Female = ['vivian', 'serena', 'ono_anna', 'sohee'];

  // Kokoro TTS voices (pattern: first char = lang, second char = gender)
  // af_ = American female, am_ = American male, bf_ = British female, etc.
  const kokoroFemale = voiceName.length > 1 && voiceName[1] === 'f';
  const kokoroMale = voiceName.length > 1 && voiceName[1] === 'm';

  if (geminiMale.includes(voiceName)) return ' (male)';
  if (geminiFemale.includes(voiceName)) return ' (female)';
  if (openaiMale.includes(voiceName)) return ' (male)';
  if (openaiFemale.includes(voiceName)) return ' (female)';
  if (googleMale.includes(voiceName)) return ' (male)';
  if (googleFemale.includes(voiceName)) return ' (female)';
  if (qwen3Male.includes(voiceName)) return ' (male)';
  if (qwen3Female.includes(voiceName)) return ' (female)';
  if (kokoroFemale) return ' (female)';
  if (kokoroMale) return ' (male)';

  return ''; // Unknown or no gender info
};

export const CreateQubeModal: React.FC<CreateQubeModalProps> = ({
  isOpen,
  onClose,
  onCreate,
  onQubesChange,
}) => {
  const { userId, password } = useAuth();
  const { providers: dynamicProviders, getModelsForProvider, getDefaultModel, isLoaded: modelsLoaded, fetchModels } = useModels();
  const { voiceLibrary: customVoices } = useVoiceLibrary();

  // Fetch models when modal opens
  useEffect(() => {
    if (isOpen && !modelsLoaded) {
      fetchModels();
    }
  }, [isOpen, modelsLoaded, fetchModels]);

  // Fallback providers if dynamic data hasn't loaded yet
  const fallbackProviders = [
    { value: 'ollama', label: 'Ollama (Local)' },
    { value: 'openai', label: 'OpenAI' },
    { value: 'anthropic', label: 'Anthropic' },
    { value: 'google', label: 'Google' },
    { value: 'perplexity', label: 'Perplexity' },
    { value: 'deepseek', label: 'DeepSeek' },
    { value: 'venice', label: 'Venice (Private)' },
    { value: 'nanogpt', label: 'NanoGPT (Pay-per-prompt)' },
  ];

  // Fallback models by provider (matches backend ModelRegistry)
  const fallbackModels: Record<string, { value: string; label: string }[]> = {
    openai: [
      { value: 'gpt-5.4', label: 'GPT-5.4' },
      { value: 'gpt-5.4-mini', label: 'GPT-5.4 Mini' },
      { value: 'gpt-5.4-nano', label: 'GPT-5.4 Nano' },
      { value: 'gpt-5.2', label: 'GPT-5.2' },
      { value: 'gpt-5', label: 'GPT-5' },
      { value: 'gpt-5-mini', label: 'GPT-5 Mini' },
      { value: 'gpt-4.1', label: 'GPT-4.1' },
      { value: 'gpt-4.1-mini', label: 'GPT-4.1 Mini' },
      { value: 'gpt-4o', label: 'GPT-4o' },
      { value: 'gpt-4o-mini', label: 'GPT-4o Mini' },
      { value: 'o4-mini', label: 'O4 Mini (Reasoning)' },
      { value: 'o3', label: 'O3 (Reasoning)' },
      { value: 'o3-pro', label: 'O3 Pro (Reasoning)' },
      { value: 'o3-mini', label: 'O3 Mini (Reasoning)' },
      { value: 'o1', label: 'O1 (Reasoning)' },
    ],
    anthropic: [
      { value: 'claude-opus-4-6-20260204', label: 'Claude Opus 4.6' },
      { value: 'claude-sonnet-4-6-20260217', label: 'Claude Sonnet 4.6' },
      { value: 'claude-haiku-4-5-20251001', label: 'Claude Haiku 4.5' },
      { value: 'claude-sonnet-4-5-20250929', label: 'Claude Sonnet 4.5' },
      { value: 'claude-opus-4-1-20250805', label: 'Claude Opus 4.1' },
      { value: 'claude-sonnet-4-20250514', label: 'Claude Sonnet 4' },
      { value: 'claude-3-5-haiku-20241022', label: 'Claude 3.5 Haiku' },
    ],
    google: [
      { value: 'gemini-3.1-pro-preview', label: 'Gemini 3.1 Pro' },
      { value: 'gemini-3-flash-preview', label: 'Gemini 3 Flash' },
      { value: 'gemini-2.5-pro', label: 'Gemini 2.5 Pro' },
      { value: 'gemini-2.5-flash', label: 'Gemini 2.5 Flash' },
      { value: 'gemini-2.5-flash-lite', label: 'Gemini 2.5 Flash Lite' },
      { value: 'gemini-2.0-flash', label: 'Gemini 2.0 Flash' },
      { value: 'gemini-1.5-pro', label: 'Gemini 1.5 Pro' },
    ],
    perplexity: [
      { value: 'sonar-pro', label: 'Sonar Pro' },
      { value: 'sonar', label: 'Sonar' },
      { value: 'sonar-reasoning-pro', label: 'Sonar Reasoning Pro' },
      { value: 'sonar-deep-research', label: 'Sonar Deep Research' },
    ],
    deepseek: [
      { value: 'deepseek-chat', label: 'DeepSeek Chat (V3.2)' },
      { value: 'deepseek-reasoner', label: 'DeepSeek Reasoner (R1)' },
    ],
    venice: [
      { value: 'openai-gpt-54', label: 'GPT-5.4 (Venice)' },
      { value: 'claude-opus-46', label: 'Claude Opus 4.6 (Venice)' },
      { value: 'claude-sonnet-46', label: 'Claude Sonnet 4.6 (Venice)' },
      { value: 'venice-uncensored', label: 'Venice Uncensored' },
      { value: 'llama-3.3-70b', label: 'Llama 3.3 70B' },
      { value: 'llama-3.2-3b', label: 'Llama 3.2 3B (Fast)' },
      { value: 'qwen3-235b-a22b-instruct-2507', label: 'Qwen3 235B Instruct' },
      { value: 'qwen3-235b-a22b-thinking-2507', label: 'Qwen3 235B Thinking' },
      { value: 'qwen3-next-80b', label: 'Qwen3 Next 80B' },
      { value: 'qwen3-coder-480b-a35b-instruct', label: 'Qwen3 Coder 480B' },
      { value: 'qwen3.5-35b-a3b', label: 'Qwen 3.5 35B' },
      { value: 'qwen3-4b', label: 'Venice Small (Fast)' },
      { value: 'mistral-31-24b', label: 'Venice Medium' },
      { value: 'grok-41-fast', label: 'Grok 4.1 Fast' },
      { value: 'grok-code-fast-1', label: 'Grok Code Fast' },
      { value: 'glm-5', label: 'GLM 5' },
      { value: 'zai-org-glm-4.7', label: 'GLM 4.7' },
      { value: 'kimi-k2-thinking', label: 'Kimi K2 Thinking' },
      { value: 'minimax-m25', label: 'MiniMax M2.5' },
      { value: 'minimax-m21', label: 'MiniMax M2.1' },
      { value: 'deepseek-v3.2', label: 'DeepSeek V3.2 (Venice)' },
      { value: 'google-gemma-3-27b-it', label: 'Gemma 3 27B' },
      { value: 'hermes-3-llama-3.1-405b', label: 'Hermes 3 405B' },
    ],
    nanogpt: [
      { value: 'nanogpt/gpt-4o', label: 'GPT-4o (NanoGPT)' },
      { value: 'nanogpt/gpt-4o-mini', label: 'GPT-4o Mini (NanoGPT)' },
      { value: 'nanogpt/claude-3-5-sonnet', label: 'Claude 3.5 Sonnet (NanoGPT)' },
      { value: 'nanogpt/claude-3-haiku', label: 'Claude 3 Haiku (NanoGPT)' },
      { value: 'nanogpt/llama-3.1-70b', label: 'Llama 3.1 70B (NanoGPT)' },
      { value: 'nanogpt/llama-3.1-8b', label: 'Llama 3.1 8B (NanoGPT)' },
      { value: 'nanogpt/mistral-large', label: 'Mistral Large (NanoGPT)' },
      { value: 'nanogpt/mixtral-8x7b', label: 'Mixtral 8x7B (NanoGPT)' },
    ],
    ollama: [
      { value: 'deepseek-r1:8b', label: 'DeepSeek R1 8B (bundled)' },
      { value: 'llama3.3:70b', label: 'Llama 3.3 70B' },
      { value: 'llama3.2', label: 'Llama 3.2' },
      { value: 'llama3.2:1b', label: 'Llama 3.2 1B' },
      { value: 'llama3.2:3b', label: 'Llama 3.2 3B' },
      { value: 'llama3.2-vision:11b', label: 'Llama 3.2 Vision 11B' },
      { value: 'llama3.2-vision:90b', label: 'Llama 3.2 Vision 90B' },
      { value: 'qwen3:235b', label: 'Qwen3 235B' },
      { value: 'qwen3:30b', label: 'Qwen3 30B' },
      { value: 'qwen2.5:7b', label: 'Qwen 2.5 7B' },
      { value: 'phi4:14b', label: 'Phi-4 14B' },
      { value: 'gemma2:9b', label: 'Gemma 2 9B' },
      { value: 'mistral:7b', label: 'Mistral 7B' },
      { value: 'codellama:7b', label: 'CodeLlama 7B' },
    ],
  };

  const fallbackDefaults: Record<string, string> = {
    openai: 'gpt-5.4',
    anthropic: 'claude-sonnet-4-6-20260217',
    google: 'gemini-3.1-pro-preview',
    perplexity: 'sonar-pro',
    deepseek: 'deepseek-chat',
    venice: 'openai-gpt-54',
    nanogpt: 'nanogpt/gpt-4o-mini',
    ollama: 'deepseek-r1:8b',
  };

  // Use dynamic data if loaded, otherwise fallback
  const providers = modelsLoaded && dynamicProviders.length > 0 ? dynamicProviders : fallbackProviders;
  const getModels = (provider: string) => {
    if (modelsLoaded) {
      const dynamicModels = getModelsForProvider(provider);
      if (dynamicModels.length > 0) return dynamicModels;
    }
    return fallbackModels[provider] || [];
  };
  const getDefault = (provider: string) => {
    if (modelsLoaded) {
      const dynamicDefault = getDefaultModel(provider);
      if (dynamicDefault) return dynamicDefault;
    }
    return fallbackDefaults[provider] || '';
  };
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [voiceProvider, setVoiceProvider] = useState('kokoro');

  // Minting state
  const [mintError, setMintError] = useState<string | null>(null);

  // Avatar crop state
  const [cropImageSrc, setCropImageSrc] = useState<string | null>(null);
  const [crop, setCrop] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const [croppedAreaPixels, setCroppedAreaPixels] = useState<Area | null>(null);
  const [isCropping, setIsCropping] = useState(false);

  const onCropComplete = useCallback((_croppedArea: Area, croppedPixels: Area) => {
    setCroppedAreaPixels(croppedPixels);
  }, []);

  const handleCropConfirm = async () => {
    if (!cropImageSrc || !croppedAreaPixels) return;
    setIsCropping(true);
    try {
      const base64 = await getCroppedImg(cropImageSrc, croppedAreaPixels);
      const tempPath = await invoke<string>('save_cropped_avatar', { base64Data: base64 });
      setFormData({ ...formData, avatarFile: tempPath, generateAvatar: false });
      setCropImageSrc(null);
    } catch (err) {
      console.error('Failed to crop avatar:', err);
    } finally {
      setIsCropping(false);
    }
  };
  const [voiceDropdownOpen, setVoiceDropdownOpen] = useState(false);
  const voiceDropdownRef = useRef<HTMLDivElement>(null);
  const voiceButtonRef = useRef<HTMLButtonElement>(null);
  const [voiceDropdownPos, setVoiceDropdownPos] = useState({ top: 0, left: 0, width: 0 });
  // customVoices now comes from VoiceLibraryContext (see useVoiceLibrary hook above)

  const [formData, setFormData] = useState<CreateQubeData>({
    name: '',
    genesisPrompt: '',
    aiProvider: 'ollama',
    aiModel: 'deepseek-r1:8b',
    voiceModel: 'kokoro:af_heart',  // Default to Kokoro local TTS (bundled, no API key needed)
    ownerPubkey: '',  // NFT address derived automatically from this
    encryptGenesis: false,
    favoriteColor: '#00ff88',
    generateAvatar: false, // AI avatar generation temporarily disabled
    avatarStyle: 'cyberpunk',
  });

  const [errors, setErrors] = useState<Partial<CreateQubeData>>({});
  const [pinataConfigured, setPinataConfigured] = useState<boolean | null>(null);
  const [checkingPinata, setCheckingPinata] = useState(false);

  // Check if Pinata API key is configured on modal open
  useEffect(() => {
    if (isOpen && userId && password) {
      checkPinataConfiguration();
    }
  }, [isOpen, userId, password]);

  const checkPinataConfiguration = async () => {
    setCheckingPinata(true);
    try {
      const result = await invoke<{ providers: string[] }>('get_configured_api_keys', {
        userId,
        password,
      });
      const isPinataConfigured = result.providers.includes('pinata_jwt');
      setPinataConfigured(isPinataConfigured);
    } catch (error) {
      console.error('Failed to check Pinata configuration:', error);
      setPinataConfigured(false);
    } finally {
      setCheckingPinata(false);
    }
  };

  // Update model when AI provider changes
  useEffect(() => {
    if (formData.aiProvider && modelsLoaded) {
      const defaultModel = getDefaultModel(formData.aiProvider);
      if (defaultModel) {
        setFormData(prev => ({ ...prev, aiModel: defaultModel }));
      }
    }
  }, [formData.aiProvider, modelsLoaded, getDefaultModel]);

  // Update voice when voice provider changes
  useEffect(() => {
    const defaultVoices: Record<string, string> = {
      'kokoro': 'kokoro:af_heart',
      'qwen3': 'qwen3:Vivian',
      'google': 'google:en-US-Neural2-A',
      'gemini': 'gemini:puck',
      'openai': 'openai:alloy',
      'elevenlabs': 'elevenlabs:default'
    };

    if (voiceProvider === 'custom') {
      // Use first custom voice as default
      const firstVoiceId = Object.keys(customVoices)[0];
      if (firstVoiceId) {
        const voice = customVoices[firstVoiceId];
        setFormData(prev => ({ ...prev, voiceModel: `custom:${firstVoiceId}` }));
      }
    } else if (voiceProvider && defaultVoices[voiceProvider]) {
      setFormData(prev => ({ ...prev, voiceModel: defaultVoices[voiceProvider] }));
    }
  }, [voiceProvider, customVoices]);

  // Close voice dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Node;
      if (voiceDropdownRef.current && !voiceDropdownRef.current.contains(target) &&
          voiceButtonRef.current && !voiceButtonRef.current.contains(target)) {
        setVoiceDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Position voice dropdown portal
  useEffect(() => {
    if (voiceDropdownOpen && voiceButtonRef.current) {
      const rect = voiceButtonRef.current.getBoundingClientRect();
      setVoiceDropdownPos({ top: rect.bottom + 4, left: rect.left, width: rect.width });
    }
  }, [voiceDropdownOpen]);

  // Custom voices now come from VoiceLibraryContext - no need for local loading

  const wallet = useWallet();
  const [pubkeyOverride, setPubkeyOverride] = useState(false);

  // Auto-populate ownerPubkey when wallet provides it
  useEffect(() => {
    if (wallet.publicKey && !formData.ownerPubkey && !pubkeyOverride) {
      setFormData((prev) => ({ ...prev, ownerPubkey: wallet.publicKey! }));
    }
  }, [wallet.publicKey, pubkeyOverride]);

  // Mint status for multi-step WC flow
  const [mintStatus, setMintStatus] = useState<string>('');

  // Create qube via WalletConnect covenant minting
  const handleCreateQube = async () => {
    if (!wallet.connected || !wallet.address) {
      setMintError('Please connect your wallet first');
      return;
    }

    setLoading(true);
    setMintError(null);

    try {
      // Step 1: Prepare mint (generate keys, build unsigned WC transaction)
      setMintStatus('Preparing transaction...');
      const prepResult = await invoke<{
        pending_id: string;
        qube_id: string;
        wc_transaction: string;
        category_id: string;
        commitment: string;
      }>('prepare_qube_mint', {
        userId,
        name: formData.name,
        genesisPrompt: formData.genesisPrompt,
        aiProvider: formData.aiProvider,
        aiModel: formData.aiModel,
        voiceModel: formData.voiceModel || '',
        ownerPubkey: formData.ownerPubkey,
        userAddress: wallet.address,
        password,
        encryptGenesis: formData.encryptGenesis || false,
        favoriteColor: formData.favoriteColor,
        avatarFile: formData.avatarFile || null,
        generateAvatar: formData.generateAvatar || false,
        avatarStyle: formData.avatarStyle || null,
      });

      console.log('[Minting] WC transaction prepared:', prepResult.qube_id);

      // Step 2: Send to wallet for signing + broadcast (use session matching owner pubkey)
      setMintStatus('Approve in your wallet...');
      const qubeSession = wallet.getSessionForQube(formData.ownerPubkey);
      const signResult = qubeSession
        ? await wallet.signTransactionWith(qubeSession.topic, prepResult.wc_transaction)
        : await wallet.signTransaction(prepResult.wc_transaction);

      if (!signResult.signedTransactionHash) {
        throw new Error('Wallet did not return a transaction hash');
      }

      console.log('[Minting] Transaction broadcast:', signResult.signedTransactionHash);

      // Step 3: Finalize (create Qube with txid, BCMR, IPFS)
      setMintStatus('Finalizing...');
      const qube = await invoke<Qube>('finalize_qube_mint', {
        userId,
        pendingId: prepResult.pending_id,
        mintTxid: signResult.signedTransactionHash,
        password,
      });

      console.log('[Minting] Qube created via WC covenant:', qube.qube_id);
      setMintStatus('');
      setSuccess(true);
    } catch (error: any) {
      console.error('Failed to create qube:', error);
      const msg = error?.message || String(error);
      if (msg.includes('broadcast failed')) {
        // Show the full broadcast error for diagnostics (check before 'rejected' —
        // network rejection errors also contain the word "rejected")
        setMintError(msg);
      } else if (msg.includes('User rejected') || msg.includes('USER_REJECTED')) {
        setMintError('Transaction rejected by wallet');
      } else {
        setMintError(`Failed to create Qube: ${msg}`);
      }
      setMintStatus('');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  const handleClose = () => {
    // If minting was successful, refresh the qube list NOW (after user saw success screen)
    if (success) {
      console.log('[Minting] Closing after successful minting - refreshing qube list');
      onQubesChange?.();
    }

    // Reset form
    setFormData({
      name: '',
      genesisPrompt: '',
      aiProvider: 'ollama',
      aiModel: 'deepseek-r1:8b',
      voiceModel: 'kokoro:af_heart',
      ownerPubkey: '',
      encryptGenesis: false,
      favoriteColor: '#00ff88',
      generateAvatar: false,
      avatarStyle: 'cyberpunk',
      avatarFile: undefined,
    });
    setVoiceProvider('kokoro');
    setStep(1);
    setSuccess(false);
    setErrors({});
    setMintError(null);
    setPubkeyOverride(false);

    onClose();
  };

  const validateStep = (currentStep: number): boolean => {
    const newErrors: Partial<CreateQubeData> = {};

    if (currentStep === 1) {
      if (!formData.name.trim()) {
        newErrors.name = 'Name is required';
      }
      if (!formData.genesisPrompt.trim()) {
        newErrors.genesisPrompt = 'Genesis prompt is required';
      }
    }

    if (currentStep === 3) {
      if (!wallet.connected) {
        newErrors.ownerPubkey = 'Please connect your wallet first';
      } else if (!formData.ownerPubkey.trim()) {
        newErrors.ownerPubkey = 'BCH public key is required for Qube wallet and NFT minting';
      } else if (!/^(02|03)[a-fA-F0-9]{64}$/.test(formData.ownerPubkey.trim())) {
        newErrors.ownerPubkey = 'Must be compressed public key (02... or 03... + 64 hex chars)';
      }
    }

    if (currentStep === 4) {
      // Avatar is mandatory - must upload
      if (!formData.avatarFile) {
        newErrors.avatarFile = 'Avatar is required. Please upload an image.';
      }
      // Pinata must be configured for IPFS upload
      if (pinataConfigured === false) {
        newErrors.avatarFile = 'Pinata IPFS API key is required. Please configure it in Settings first.';
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const nextStep = () => {
    if (validateStep(step)) {
      setStep(step + 1);
    }
  };

  const prevStep = () => {
    setStep(step - 1);
  };

  // Debug: Log render state when success changes
  if (success) {
    console.log('[Minting] RENDER: success=true, showing success view');
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <GlassCard className="w-full max-w-2xl max-h-[90vh] overflow-y-auto p-8">
        {success ? (
          // Success View - Celebratory Qube Minted Screen
          <div className="text-center py-8 relative overflow-hidden">
            {/* Animated confetti background */}
            <div className="absolute inset-0 pointer-events-none overflow-hidden">
              {[...Array(20)].map((_, i) => (
                <div
                  key={i}
                  className="absolute animate-bounce"
                  style={{
                    left: `${Math.random() * 100}%`,
                    top: `${Math.random() * 100}%`,
                    animationDelay: `${Math.random() * 2}s`,
                    animationDuration: `${1 + Math.random() * 2}s`,
                    fontSize: `${12 + Math.random() * 16}px`,
                    opacity: 0.6,
                  }}
                >
                  {['✨', '🎉', '🎊', '⭐', '💫', '🌟'][Math.floor(Math.random() * 6)]}
                </div>
              ))}
            </div>

            {/* Main content */}
            <div className="relative z-10">
              {/* Large celebration icon */}
              <div className="text-7xl mb-4 animate-pulse">🎉</div>

              <h2 className="text-4xl font-display text-accent-primary mb-2">
                Qube Minted!
              </h2>

              <p className="text-xl text-text-primary mb-6">
                Welcome to the world, <span className="font-bold text-accent-primary">{formData.name}</span>!
              </p>

              {/* Qube card preview */}
              <div
                className="mx-auto mb-6 p-6 rounded-2xl max-w-sm"
                style={{
                  background: `linear-gradient(135deg, ${formData.favoriteColor}22 0%, transparent 50%)`,
                  border: `2px solid ${formData.favoriteColor}66`,
                  boxShadow: `0 0 30px ${formData.favoriteColor}33`,
                }}
              >
                {/* Avatar with glow */}
                <div
                  className="w-24 h-24 mx-auto mb-4 rounded-full bg-glass-bg flex items-center justify-center text-4xl overflow-hidden"
                  style={{
                    boxShadow: `0 0 20px ${formData.favoriteColor}`,
                    border: `3px solid ${formData.favoriteColor}`,
                  }}
                >
                  {formData.avatarFile ? (
                    <img
                      src={convertFileSrc(formData.avatarFile)}
                      alt={`${formData.name} avatar`}
                      className="w-full h-full object-cover"
                    />
                  ) : formData.generateAvatar ? (
                    <span className="text-3xl">✨</span>
                  ) : (
                    <span>🤖</span>
                  )}
                </div>

                <h3 className="text-2xl font-display text-text-primary mb-2">{formData.name}</h3>

                <div className="text-sm text-text-tertiary space-y-1">
                  <p><span className="text-text-secondary">AI:</span> {formData.aiProvider} / {formData.aiModel}</p>
                  <p><span className="text-text-secondary">Voice:</span> {formData.voiceModel?.split(':')[1]}</p>
                </div>
              </div>

              {/* NFT Badge with BCH logo */}
              <div className="inline-flex items-center gap-2 px-4 py-2 bg-accent-success/20 border border-accent-success/40 rounded-full mb-6">
                <img src="/bitcoin_cash_logo.svg" alt="BCH" className="w-5 h-5" />
                <span className="text-accent-success font-medium">NFT Minted on Bitcoin Cash</span>
              </div>

              <p className="text-text-tertiary text-sm mb-8">
                Your new Qube is ready to chat! Their identity is now permanently recorded on the blockchain.
              </p>

              <GlassButton variant="primary" onClick={handleClose} className="px-8 py-3">
                Done
              </GlassButton>
            </div>
          </div>
        ) : (
          <>
            {/* Header */}
            <div className="mb-6">
              <h2 className="text-3xl font-display text-accent-primary mb-2">
                Create New Qube
              </h2>
              <div className="flex gap-2">
                {[1, 2, 3, 4, 5].map((s) => (
                  <div
                    key={s}
                    className={`h-1 flex-1 rounded ${
                      s <= step ? 'bg-accent-primary' : 'bg-glass-border'
                    }`}
                  />
                ))}
              </div>
            </div>
            {/* Step 1: Basic Info */}
            {step === 1 && (
          <div className="space-y-4">
            <h3 className="text-xl text-text-primary font-medium mb-4">
              Basic Information
            </h3>

            <GlassInput
              label="Qube Name *"
              placeholder="e.g., Athena, Hermes, Apollo..."
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              error={errors.name}
            />

            <div>
              <label className="block text-sm font-medium text-text-secondary mb-2">
                Genesis Prompt *
              </label>
              <textarea
                placeholder="Describe your Qube's purpose, personality, and expertise..."
                value={formData.genesisPrompt}
                onChange={(e) => setFormData({ ...formData, genesisPrompt: e.target.value })}
                rows={5}
                className={`w-full px-4 py-2 bg-glass-bg backdrop-blur-glass border rounded-lg text-text-primary placeholder-text-tertiary focus:outline-none focus:ring-2 ${
                  errors.genesisPrompt
                    ? 'border-accent-danger focus:ring-accent-danger'
                    : 'border-glass-border focus:ring-accent-primary/50'
                }`}
              />
              {errors.genesisPrompt && (
                <span className="text-sm text-accent-danger">{errors.genesisPrompt}</span>
              )}
            </div>
          </div>
        )}

        {/* Step 2: AI Configuration */}
        {step === 2 && (
          <div className="space-y-4">
            <h3 className="text-xl text-text-primary font-medium mb-4">
              AI Configuration
            </h3>

            <div>
              <label className="block text-sm font-medium text-text-secondary mb-2">
                AI Provider
              </label>
              <DarkSelect
                value={formData.aiProvider}
                onChange={(v) => {
                  const defaultModel = getDefault(v);
                  setFormData({ ...formData, aiProvider: v, aiModel: defaultModel });
                }}
                options={providers}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-text-secondary mb-2">
                AI Model
              </label>
              <DarkSelect
                value={formData.aiModel}
                onChange={(v) => setFormData({ ...formData, aiModel: v })}
                options={getModels(formData.aiProvider)}
                expanded
                maxVisible={8}
              />
            </div>
          </div>
        )}

        {/* Step 3: Voice & Wallet */}
        {step === 3 && (
          <div className="space-y-4">
            <h3 className="text-xl text-text-primary font-medium mb-4">
              Voice & Blockchain Configuration
            </h3>

            <div>
              <label className="block text-sm font-medium text-text-secondary mb-2">
                Voice Provider
              </label>
              <DarkSelect
                value={voiceProvider}
                onChange={(v) => setVoiceProvider(v)}
                options={[
                  { value: 'kokoro', label: 'Kokoro (local)' },
                  { value: 'qwen3', label: 'Qwen3 (local)' },
                  ...(Object.keys(customVoices).length > 0 ? [{ value: 'custom', label: 'Custom Voices (local)' }] : []),
                  { value: 'google', label: 'Google Cloud' },
                  { value: 'gemini', label: 'Google Gemini' },
                  { value: 'openai', label: 'OpenAI' },
                  { value: 'elevenlabs', label: 'ElevenLabs' },
                ]}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-text-secondary mb-2">
                Voice
              </label>
              <div>
                <button
                  type="button"
                  ref={voiceButtonRef}
                  onClick={() => setVoiceDropdownOpen(!voiceDropdownOpen)}
                  className="w-full px-4 py-2 bg-glass-bg backdrop-blur-glass border border-glass-border rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-primary/50 text-left flex justify-between items-center"
                >
                  <span>
                    {formatVoiceName(formData.voiceModel || '')}{getVoiceGender(formData.voiceModel || '')}
                  </span>
                  <svg className={`w-4 h-4 transition-transform ${voiceDropdownOpen ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
                {voiceDropdownOpen && createPortal(
                  <div
                    ref={voiceDropdownRef}
                    className="fixed z-[9999] bg-[#2a3441] border border-glass-border rounded-lg shadow-lg max-h-48 overflow-y-auto"
                    style={{ top: voiceDropdownPos.top, left: voiceDropdownPos.left, width: voiceDropdownPos.width }}
                  >
                    {voiceProvider === 'custom' && (
                      <>
                        {Object.entries(customVoices).map(([id, voice]) => (
                          <div
                            key={id}
                            onClick={() => { setFormData({ ...formData, voiceModel: `custom:${id}` }); setVoiceDropdownOpen(false); }}
                            className={`px-4 py-2 cursor-pointer hover:bg-accent-primary/20 ${formData.voiceModel === `custom:${id}` ? 'bg-accent-primary/30' : ''}`}
                          >
                            <div className="flex justify-between items-center">
                              <span>{voice.name}</span>
                              <span className="text-xs text-text-tertiary capitalize">{voice.voice_type}</span>
                            </div>
                          </div>
                        ))}
                        {Object.keys(customVoices).length === 0 && (
                          <div className="px-4 py-2 text-text-tertiary text-sm">
                            No custom voices yet. Create one in Settings → Custom Voices.
                          </div>
                        )}
                      </>
                    )}
                    {voiceProvider === 'kokoro' && (
                      <>
                        <div className="px-4 py-1 text-xs text-text-tertiary bg-glass-border/30 sticky top-0">American English</div>
                        {[
                          { id: 'af_heart', label: 'Heart' }, { id: 'af_bella', label: 'Bella' },
                          { id: 'af_nova', label: 'Nova' }, { id: 'af_sarah', label: 'Sarah' },
                          { id: 'am_adam', label: 'Adam' }, { id: 'am_michael', label: 'Michael' },
                        ].map(v => (
                          <div
                            key={v.id}
                            onClick={() => { setFormData({ ...formData, voiceModel: `kokoro:${v.id}` }); setVoiceDropdownOpen(false); }}
                            className={`px-4 py-2 cursor-pointer hover:bg-accent-primary/20 ${formData.voiceModel === `kokoro:${v.id}` ? 'bg-accent-primary/30' : ''}`}
                          >
                            {v.label}{getVoiceGender(`kokoro:${v.id}`)}
                          </div>
                        ))}
                        <div className="px-4 py-1 text-xs text-text-tertiary bg-glass-border/30 sticky top-0">British English</div>
                        {[
                          { id: 'bf_emma', label: 'Emma' }, { id: 'bf_lily', label: 'Lily' },
                          { id: 'bm_george', label: 'George' }, { id: 'bm_daniel', label: 'Daniel' },
                        ].map(v => (
                          <div
                            key={v.id}
                            onClick={() => { setFormData({ ...formData, voiceModel: `kokoro:${v.id}` }); setVoiceDropdownOpen(false); }}
                            className={`px-4 py-2 cursor-pointer hover:bg-accent-primary/20 ${formData.voiceModel === `kokoro:${v.id}` ? 'bg-accent-primary/30' : ''}`}
                          >
                            {v.label}{getVoiceGender(`kokoro:${v.id}`)}
                          </div>
                        ))}
                        <div className="px-4 py-1 text-xs text-text-tertiary bg-glass-border/30 sticky top-0">Japanese</div>
                        {[
                          { id: 'jf_alpha', label: 'Alpha' }, { id: 'jm_kumo', label: 'Kumo' },
                        ].map(v => (
                          <div
                            key={v.id}
                            onClick={() => { setFormData({ ...formData, voiceModel: `kokoro:${v.id}` }); setVoiceDropdownOpen(false); }}
                            className={`px-4 py-2 cursor-pointer hover:bg-accent-primary/20 ${formData.voiceModel === `kokoro:${v.id}` ? 'bg-accent-primary/30' : ''}`}
                          >
                            {v.label}{getVoiceGender(`kokoro:${v.id}`)}
                          </div>
                        ))}
                        <div className="px-4 py-1 text-xs text-text-tertiary bg-glass-border/30 sticky top-0">Mandarin Chinese</div>
                        {[
                          { id: 'zf_xiaoxiao', label: 'Xiaoxiao' }, { id: 'zm_yunxi', label: 'Yunxi' },
                        ].map(v => (
                          <div
                            key={v.id}
                            onClick={() => { setFormData({ ...formData, voiceModel: `kokoro:${v.id}` }); setVoiceDropdownOpen(false); }}
                            className={`px-4 py-2 cursor-pointer hover:bg-accent-primary/20 ${formData.voiceModel === `kokoro:${v.id}` ? 'bg-accent-primary/30' : ''}`}
                          >
                            {v.label}{getVoiceGender(`kokoro:${v.id}`)}
                          </div>
                        ))}
                        <div className="px-4 py-1 text-xs text-text-tertiary bg-glass-border/30 sticky top-0">Spanish / French</div>
                        {[
                          { id: 'ef_dora', label: 'Dora (ES)' }, { id: 'ff_siwis', label: 'Siwis (FR)' },
                        ].map(v => (
                          <div
                            key={v.id}
                            onClick={() => { setFormData({ ...formData, voiceModel: `kokoro:${v.id}` }); setVoiceDropdownOpen(false); }}
                            className={`px-4 py-2 cursor-pointer hover:bg-accent-primary/20 ${formData.voiceModel === `kokoro:${v.id}` ? 'bg-accent-primary/30' : ''}`}
                          >
                            {v.label}{getVoiceGender(`kokoro:${v.id}`)}
                          </div>
                        ))}
                      </>
                    )}
                    {voiceProvider === 'qwen3' && (
                      <>
                        {[
                          { id: 'Vivian', label: 'Vivian' },
                          { id: 'Serena', label: 'Serena' },
                          { id: 'Dylan', label: 'Dylan' },
                          { id: 'Eric', label: 'Eric' },
                          { id: 'Ryan', label: 'Ryan' },
                          { id: 'Aiden', label: 'Aiden' },
                          { id: 'Ono_Anna', label: 'Ono Anna' },
                          { id: 'Sohee', label: 'Sohee' },
                          { id: 'Uncle_Fu', label: 'Uncle Fu' },
                        ].map(voice => (
                          <div
                            key={voice.id}
                            onClick={() => { setFormData({ ...formData, voiceModel: `qwen3:${voice.id}` }); setVoiceDropdownOpen(false); }}
                            className={`px-4 py-2 cursor-pointer hover:bg-accent-primary/20 ${formData.voiceModel === `qwen3:${voice.id}` ? 'bg-accent-primary/30' : ''}`}
                          >
                            {voice.label}{getVoiceGender(`qwen3:${voice.id}`)}
                          </div>
                        ))}
                      </>
                    )}
                    {voiceProvider === 'gemini' && (
                      <>
                        {['achernar', 'achird', 'algenib', 'algieba', 'alnilam', 'aoede', 'autonoe', 'callirrhoe', 'charon', 'despina', 'enceladus', 'erinome', 'fenrir', 'gacrux', 'iapetus', 'kore', 'laomedeia', 'leda', 'orus', 'puck', 'pulcherrima', 'rasalgethi', 'sadachbia', 'sadaltager', 'schedar', 'sulafat', 'umbriel', 'vindemiatrix', 'zephyr', 'zubenelgenubi'].map(voice => (
                          <div
                            key={voice}
                            onClick={() => { setFormData({ ...formData, voiceModel: `gemini:${voice}` }); setVoiceDropdownOpen(false); }}
                            className={`px-4 py-2 cursor-pointer hover:bg-accent-primary/20 ${formData.voiceModel === `gemini:${voice}` ? 'bg-accent-primary/30' : ''}`}
                          >
                            {voice.charAt(0).toUpperCase() + voice.slice(1)}{getVoiceGender(`gemini:${voice}`)}
                          </div>
                        ))}
                      </>
                    )}
                    {voiceProvider === 'openai' && (
                      <>
                        {['alloy', 'ash', 'coral', 'echo', 'fable', 'nova', 'onyx', 'sage', 'shimmer'].map(voice => (
                          <div
                            key={voice}
                            onClick={() => { setFormData({ ...formData, voiceModel: `openai:${voice}` }); setVoiceDropdownOpen(false); }}
                            className={`px-4 py-2 cursor-pointer hover:bg-accent-primary/20 ${formData.voiceModel === `openai:${voice}` ? 'bg-accent-primary/30' : ''}`}
                          >
                            {voice.charAt(0).toUpperCase() + voice.slice(1)}{getVoiceGender(`openai:${voice}`)}
                          </div>
                        ))}
                      </>
                    )}
                    {voiceProvider === 'google' && (
                      <>
                        <div className="px-4 py-1 text-xs text-text-tertiary bg-glass-border/30 sticky top-0">Neural2 (High Quality - $16/1M chars)</div>
                        {['A', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J'].map(v => (
                          <div
                            key={`neural2-${v}`}
                            onClick={() => { setFormData({ ...formData, voiceModel: `google:en-US-Neural2-${v}` }); setVoiceDropdownOpen(false); }}
                            className={`px-4 py-2 cursor-pointer hover:bg-accent-primary/20 ${formData.voiceModel === `google:en-US-Neural2-${v}` ? 'bg-accent-primary/30' : ''}`}
                          >
                            Neural2-{v}{getVoiceGender(`google:Neural2-${v}`)}
                          </div>
                        ))}
                        <div className="px-4 py-1 text-xs text-text-tertiary bg-glass-border/30 sticky top-0">WaveNet (High Quality - $16/1M chars)</div>
                        {['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J'].map(v => (
                          <div
                            key={`wavenet-${v}`}
                            onClick={() => { setFormData({ ...formData, voiceModel: `google:en-US-Wavenet-${v}` }); setVoiceDropdownOpen(false); }}
                            className={`px-4 py-2 cursor-pointer hover:bg-accent-primary/20 ${formData.voiceModel === `google:en-US-Wavenet-${v}` ? 'bg-accent-primary/30' : ''}`}
                          >
                            Wavenet-{v}{getVoiceGender(`google:Wavenet-${v}`)}
                          </div>
                        ))}
                        <div className="px-4 py-1 text-xs text-text-tertiary bg-glass-border/30 sticky top-0">Studio (Premium - $160/1M chars)</div>
                        {['O', 'Q'].map(v => (
                          <div
                            key={`studio-${v}`}
                            onClick={() => { setFormData({ ...formData, voiceModel: `google:en-US-Studio-${v}` }); setVoiceDropdownOpen(false); }}
                            className={`px-4 py-2 cursor-pointer hover:bg-accent-primary/20 ${formData.voiceModel === `google:en-US-Studio-${v}` ? 'bg-accent-primary/30' : ''}`}
                          >
                            Studio-{v}{getVoiceGender(`google:Studio-${v}`)}
                          </div>
                        ))}
                        <div className="px-4 py-1 text-xs text-text-tertiary bg-glass-border/30 sticky top-0">Chirp-HD (High Quality - $16/1M chars)</div>
                        {['D', 'F'].map(v => (
                          <div
                            key={`chirp-${v}`}
                            onClick={() => { setFormData({ ...formData, voiceModel: `google:en-US-Chirp-HD-${v}` }); setVoiceDropdownOpen(false); }}
                            className={`px-4 py-2 cursor-pointer hover:bg-accent-primary/20 ${formData.voiceModel === `google:en-US-Chirp-HD-${v}` ? 'bg-accent-primary/30' : ''}`}
                          >
                            Chirp-HD-{v}{getVoiceGender(`google:Chirp-HD-${v}`)}
                          </div>
                        ))}
                        <div className="px-4 py-1 text-xs text-text-tertiary bg-glass-border/30 sticky top-0">Standard (Budget - $4/1M chars)</div>
                        {['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J'].map(v => (
                          <div
                            key={`standard-${v}`}
                            onClick={() => { setFormData({ ...formData, voiceModel: `google:en-US-Standard-${v}` }); setVoiceDropdownOpen(false); }}
                            className={`px-4 py-2 cursor-pointer hover:bg-accent-primary/20 ${formData.voiceModel === `google:en-US-Standard-${v}` ? 'bg-accent-primary/30' : ''}`}
                          >
                            Standard-{v}{getVoiceGender(`google:Standard-${v}`)}
                          </div>
                        ))}
                      </>
                    )}
                    {voiceProvider === 'elevenlabs' && (
                      <div
                        onClick={() => { setFormData({ ...formData, voiceModel: 'elevenlabs:default' }); setVoiceDropdownOpen(false); }}
                        className={`px-4 py-2 cursor-pointer hover:bg-accent-primary/20 ${formData.voiceModel === 'elevenlabs:default' ? 'bg-accent-primary/30' : ''}`}
                      >
                        Default
                      </div>
                    )}
                  </div>,
                  document.body
                )}
              </div>
              <p className="text-xs text-text-tertiary mt-1">
                {voiceProvider === 'custom' && 'Your custom voices created with voice cloning or voice design. Runs locally on GPU.'}
                {voiceProvider === 'kokoro' && 'Kokoro runs locally (CPU/GPU) - FREE and fast! 82M params, no WSL2 setup required.'}
                {voiceProvider === 'qwen3' && 'Qwen3-TTS runs locally on your GPU - FREE with voice cloning! Requires WSL2 setup.'}
                {voiceProvider === 'google' && 'Google Cloud TTS requires service account credentials. 1M free chars/month for Neural2/WaveNet!'}
                {voiceProvider === 'gemini' && 'Gemini voices use your Google API key - FREE during preview!'}
                {voiceProvider === 'openai' && 'OpenAI voices use your OpenAI API key.'}
                {voiceProvider === 'elevenlabs' && 'ElevenLabs uses your ElevenLabs API key.'}
              </p>
            </div>

            {/* WalletConnect — required for minting (connect first, pubkey derived automatically) */}
            <div className="p-4 bg-glass-bg border border-glass-border rounded-lg">
              <label className="block text-sm font-medium text-text-secondary mb-2">
                Connect Wallet *
              </label>
              <p className="text-xs text-text-tertiary mb-3">
                Your wallet signs the mint transaction. Your public key is detected automatically.
                <br />
                Supported: Cashonize, Paytaca, Zapit, Electron Cash
              </p>
              <WalletConnectButton />
              {wallet.connected && wallet.address && (
                <p className="text-xs text-accent-primary mt-2">
                  Connected: {wallet.address.length > 30
                    ? wallet.address.slice(0, 20) + '...' + wallet.address.slice(-8)
                    : wallet.address}
                </p>
              )}
            </div>

            {/* Owner Public Key — auto-filled from wallet connection */}
            <div className="mt-4">
              <label className="block text-sm font-medium text-text-secondary mb-2">
                Your BCH Public Key *
                {wallet.publicKeySource === 'wallet' && (
                  <span className="ml-2 text-xs text-green-400 font-normal">(provided by wallet)</span>
                )}
                {wallet.publicKeySource === 'recovered' && (
                  <span className="ml-2 text-xs text-green-400 font-normal">(verified from wallet)</span>
                )}
                {wallet.recoveringPubkey && (
                  <span className="ml-2 text-xs text-amber-400 font-normal animate-pulse">(verifying with wallet...)</span>
                )}
              </label>
              <input
                type="text"
                placeholder={wallet.connected ? 'Detecting from wallet...' : 'Connect your wallet above'}
                value={formData.ownerPubkey}
                onChange={(e) => setFormData({ ...formData, ownerPubkey: e.target.value })}
                readOnly={!!wallet.publicKey && !pubkeyOverride}
                className={`w-full px-4 py-2 bg-glass-bg backdrop-blur-glass border rounded-lg text-text-primary font-mono text-sm placeholder-text-tertiary focus:outline-none focus:ring-2 ${
                  wallet.publicKey && !pubkeyOverride ? 'cursor-not-allowed opacity-80' : ''
                } ${
                  errors.ownerPubkey
                    ? 'border-accent-danger focus:ring-accent-danger'
                    : 'border-glass-border focus:ring-accent-primary/50'
                }`}
              />
              {wallet.publicKey && !pubkeyOverride && (
                <button
                  type="button"
                  onClick={() => {
                    setPubkeyOverride(true);
                    setFormData((prev) => ({ ...prev, ownerPubkey: '' }));
                  }}
                  className="text-xs text-text-tertiary hover:text-accent-primary mt-1 underline"
                >
                  Use a different key
                </button>
              )}
              {errors.ownerPubkey && (
                <span className="text-sm text-accent-danger block mt-1">{errors.ownerPubkey}</span>
              )}
              <p className="text-xs text-text-tertiary mt-1">
                {wallet.connected && !wallet.publicKey && !wallet.recoveringPubkey ? (
                  <>
                    Automatic key detection was not supported by your wallet.
                    Enter your compressed public key manually (66 hex characters starting with 02 or 03).
                  </>
                ) : !wallet.connected ? (
                  <>Connect your wallet above to auto-detect your public key.</>
                ) : null}
              </p>

              {/* Show what this pubkey does */}
              {formData.ownerPubkey && /^(02|03)[a-fA-F0-9]{64}$/.test(formData.ownerPubkey.trim()) && (
                <div className="mt-3 p-3 bg-accent-primary/10 border border-accent-primary/30 rounded-lg">
                  <p className="text-xs text-accent-primary font-medium mb-1">This public key will:</p>
                  <ul className="text-xs text-text-secondary space-y-1">
                    <li>• Receive the Qube's NFT (token-aware address derived automatically)</li>
                    <li>• Control the Qube's wallet (owner can withdraw without Qube approval)</li>
                    <li>• Co-sign any spending the Qube proposes</li>
                  </ul>
                </div>
              )}
            </div>

            <div>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.encryptGenesis}
                  onChange={(e) =>
                    setFormData({ ...formData, encryptGenesis: e.target.checked })
                  }
                  className="w-5 h-5 rounded bg-glass-bg border-glass-border text-accent-primary focus:ring-2 focus:ring-accent-primary/50"
                />
                <span className="text-text-primary">Encrypt Genesis Block</span>
              </label>
              <p className="text-xs text-text-tertiary mt-1 ml-7">
                If enabled, the genesis prompt will be encrypted and only visible when unlocked with your password. The private key is always encrypted.
              </p>
            </div>
          </div>
        )}

        {/* Step 4: Appearance */}
        {step === 4 && (
          <div className="space-y-4">
            <h3 className="text-xl text-text-primary font-medium mb-4">
              Appearance
            </h3>

            <div>
              <label className="block text-sm font-medium text-text-secondary mb-2">
                Favorite Color (for glow effects)
              </label>
              <div className="flex gap-4">
                <input
                  type="color"
                  value={formData.favoriteColor}
                  onChange={(e) => setFormData({ ...formData, favoriteColor: e.target.value })}
                  className="h-12 w-20 rounded-lg cursor-pointer"
                />
                <input
                  type="text"
                  value={formData.favoriteColor}
                  onChange={(e) => setFormData({ ...formData, favoriteColor: e.target.value })}
                  placeholder="#00ff88"
                  className="flex-1 px-4 py-2 bg-glass-bg backdrop-blur-glass border border-glass-border rounded-lg text-text-primary font-mono focus:outline-none focus:ring-2 focus:ring-accent-primary/50"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-text-secondary mb-2">
                Avatar
              </label>

              {/* Upload Avatar Option */}
              <div className="mb-3">
                <button
                  type="button"
                  onClick={async (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    try {
                      const filePath = await open({
                        multiple: false,
                        filters: [{
                          name: 'Image',
                          extensions: ['png', 'jpg', 'jpeg', 'gif', 'webp']
                        }]
                      });

                      if (filePath && typeof filePath === 'string') {
                        // Open crop modal with the selected image
                        setCropImageSrc(convertFileSrc(filePath));
                        setCrop({ x: 0, y: 0 });
                        setZoom(1);
                      }
                    } catch (err) {
                      console.error('Error opening file dialog:', err);
                    }
                  }}
                  className="block w-full px-4 py-3 bg-glass-bg backdrop-blur-glass border border-glass-border rounded-lg text-text-primary hover:border-accent-primary/50 transition-colors cursor-pointer"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-lg">📁</span>
                    <span>{formData.avatarFile ? 'Avatar Selected' : 'Upload Avatar Image'}</span>
                  </div>
                  {formData.avatarFile && (
                    <p className="text-xs text-text-tertiary mt-1 ml-7 text-left">
                      {formData.avatarFile}
                    </p>
                  )}
                </button>
              </div>

              {/* Remove uploaded file button */}
              {formData.avatarFile && (
                <button
                  onClick={() => setFormData({ ...formData, avatarFile: undefined })}
                  className="text-xs text-accent-danger hover:underline"
                >
                  Remove uploaded file
                </button>
              )}
            </div>

            {/* AI Avatar Generation - temporarily disabled
            <div className="flex items-center justify-between">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.generateAvatar}
                  disabled={!!formData.avatarFile}
                  onChange={(e) =>
                    setFormData({ ...formData, generateAvatar: e.target.checked })
                  }
                  className="w-5 h-5 rounded bg-glass-bg border-glass-border text-accent-primary focus:ring-2 focus:ring-accent-primary/50 disabled:opacity-50"
                />
                <span className={formData.avatarFile ? 'text-text-tertiary' : 'text-text-primary'}>
                  Generate AI Avatar (DALL-E 3)
                </span>
              </label>
            </div>
            {formData.generateAvatar && (
              <div>
                <label className="block text-sm font-medium text-text-secondary mb-2">
                  Avatar Style
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {['cyberpunk', 'realistic', 'cartoon', 'abstract', 'anime'].map((style) => (
                    <button
                      key={style}
                      onClick={() => setFormData({ ...formData, avatarStyle: style })}
                      className={`px-4 py-2 rounded-lg capitalize transition-all ${
                        formData.avatarStyle === style
                          ? 'bg-accent-primary/10 text-accent-primary border border-accent-primary/30'
                          : 'bg-glass-bg text-text-secondary border border-glass-border hover:text-text-primary'
                      }`}
                    >
                      {style}
                    </button>
                  ))}
                </div>
              </div>
            )}
            */}

            {/* Pinata IPFS Warning */}
            {checkingPinata ? (
              <div className="p-3 bg-glass-bg border border-glass-border rounded-lg">
                <p className="text-text-tertiary text-sm">Checking IPFS configuration...</p>
              </div>
            ) : pinataConfigured === false ? (
              <div className="p-3 bg-accent-danger/10 border border-accent-danger/30 rounded-lg">
                <p className="text-accent-danger text-sm font-medium mb-1">
                  Pinata IPFS API Key Required
                </p>
                <p className="text-text-secondary text-xs">
                  Avatar images must be uploaded to IPFS. Please configure your Pinata API key in the Settings tab before creating a Qube.
                </p>
              </div>
            ) : pinataConfigured === true ? (
              <div className="p-3 bg-accent-success/10 border border-accent-success/30 rounded-lg">
                <p className="text-accent-success text-sm">
                  Pinata IPFS configured - avatar will be uploaded to IPFS
                </p>
              </div>
            ) : null}

            {/* Avatar validation error */}
            {errors.avatarFile && (
              <p className="text-accent-danger text-sm mt-2">{errors.avatarFile}</p>
            )}
          </div>
        )}

        {/* Step 5: Confirm */}
        {step === 5 && (
          <div className="space-y-4">
            <h3 className="text-xl text-text-primary font-medium mb-4">
              Confirm & Create
            </h3>

            <GlassCard className="p-4 bg-bg-secondary/50">
              <div className="space-y-3">
                <div>
                  <span className="text-text-tertiary text-sm">Name:</span>
                  <p className="text-text-primary font-medium">{formData.name}</p>
                </div>
                <div>
                  <span className="text-text-tertiary text-sm">AI Model:</span>
                  <p className="text-text-primary font-medium">
                    {formData.aiProvider} - {formData.aiModel}
                  </p>
                </div>
                <div>
                  <span className="text-text-tertiary text-sm">Voice Model:</span>
                  <p className="text-text-primary font-medium">{formData.voiceModel}</p>
                </div>
                <div>
                  <span className="text-text-tertiary text-sm">Owner Public Key:</span>
                  <p className="text-text-primary font-mono text-xs break-all">{formData.ownerPubkey}</p>
                  <p className="text-text-tertiary text-xs mt-1">NFT address will be derived automatically</p>
                </div>
                <div>
                  <span className="text-text-tertiary text-sm">Encrypt Genesis:</span>
                  <p className="text-text-primary">{formData.encryptGenesis ? 'Yes' : 'No'}</p>
                </div>
                <div>
                  <span className="text-text-tertiary text-sm">Genesis Prompt:</span>
                  <p className="text-text-primary">{formData.genesisPrompt}</p>
                </div>
                <div>
                  <span className="text-text-tertiary text-sm">Avatar:</span>
                  <p className="text-text-primary">
                    {formData.avatarFile
                      ? 'Uploaded'
                      : formData.generateAvatar
                        ? `Generate (${formData.avatarStyle})`
                        : 'None'}
                  </p>
                </div>
              </div>
            </GlassCard>

            <div className="bg-accent-primary/10 border border-accent-primary/30 rounded-lg p-4">
              <p className="text-text-primary text-sm">
                Your connected wallet will sign the mint transaction. This creates your Qube's identity as an immutable NFT on Bitcoin Cash via the on-chain covenant.
              </p>
            </div>

            {mintError && (
              <div className="bg-accent-danger/10 border border-accent-danger/30 rounded-lg p-4">
                <pre className="text-accent-danger text-xs whitespace-pre-wrap break-all font-mono max-h-64 overflow-y-auto select-all">{mintError}</pre>
              </div>
            )}
          </div>
        )}

        {/* Steps 6-7 removed: Covenant minting is single-step (no payment QR / polling).
            Success is handled by the 'success' state view above. */}

        {/* Actions */}
        <div className="flex justify-between mt-8">
            <>
              <GlassButton variant="ghost" onClick={handleClose}>
                Cancel
              </GlassButton>

              <div className="flex gap-2">
                {step > 1 && (
                  <GlassButton variant="secondary" onClick={prevStep}>
                    Back
                  </GlassButton>
                )}
                {step < 5 ? (
                  <GlassButton variant="primary" onClick={nextStep}>
                    Next
                  </GlassButton>
                ) : (
                  <GlassButton
                    variant="primary"
                    onClick={handleCreateQube}
                    loading={loading}
                    disabled={!wallet.connected}
                    title={!wallet.connected ? 'Connect your wallet first' : ''}
                  >
                    {mintStatus || 'Create & Mint Qube'}
                  </GlassButton>
                )}
              </div>
            </>
        </div>
          </>
        )}
      </GlassCard>

      {/* Avatar Crop Modal */}
      {cropImageSrc && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/70 backdrop-blur-sm">
          <div className="bg-surface-primary border border-border-subtle rounded-xl w-full max-w-lg p-4">
            <h3 className="text-lg font-display text-text-primary mb-3 text-center">Crop Avatar</h3>
            <div className="relative w-full" style={{ height: '400px' }}>
              <Cropper
                image={cropImageSrc}
                crop={crop}
                zoom={zoom}
                aspect={1}
                cropShape="round"
                showGrid={false}
                onCropChange={setCrop}
                onZoomChange={setZoom}
                onCropComplete={onCropComplete}
              />
            </div>
            <div className="flex items-center gap-2 mt-3 px-2">
              <span className="text-xs text-text-tertiary">Zoom</span>
              <input
                type="range"
                min={1}
                max={3}
                step={0.1}
                value={zoom}
                onChange={(e) => setZoom(Number(e.target.value))}
                className="flex-1 accent-accent-primary"
              />
            </div>
            <div className="flex gap-3 mt-4 justify-end">
              <button
                onClick={() => setCropImageSrc(null)}
                className="px-4 py-2 text-sm text-text-secondary hover:text-text-primary transition-colors"
              >
                Cancel
              </button>
              <GlassButton variant="primary" onClick={handleCropConfirm} loading={isCropping}>
                Apply Crop
              </GlassButton>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
