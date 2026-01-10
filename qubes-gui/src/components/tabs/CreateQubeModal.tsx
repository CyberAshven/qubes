import React, { useState, useEffect, useCallback, useRef } from 'react';
import { open } from '@tauri-apps/plugin-dialog';
import { invoke, convertFileSrc } from '@tauri-apps/api/core';
import { QRCodeSVG } from 'qrcode.react';
import { GlassCard, GlassButton, GlassInput } from '../glass';
import { PendingMintingResult, MintingStatusResult, MintingStatus } from '../../types';
import { useAuth } from '../../hooks/useAuth';
import { useModels } from '../../hooks/useModels';

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

// Voice gender mapping
const getVoiceGender = (voiceId: string): string => {
  const voiceName = voiceId.includes(':') ? voiceId.split(':')[1].toLowerCase() : voiceId.toLowerCase();

  // Gemini voices
  const geminiMale = ['achernar', 'algenib', 'alnilam', 'charon', 'fenrir', 'gacrux', 'iapetus', 'orus', 'puck', 'rasalgethi', 'sadachbia', 'sadaltager', 'umbriel', 'zephyr'];
  const geminiFemale = ['achird', 'algieba', 'aoede', 'autonoe', 'callirrhoe', 'despina', 'enceladus', 'erinome', 'kore', 'laomedeia', 'leda', 'pulcherrima', 'schedar', 'sulafat', 'vindemiatrix', 'zubenelgenubi'];

  // OpenAI voices
  const openaiMale = ['echo', 'fable', 'onyx'];
  const openaiFemale = ['alloy', 'nova', 'shimmer'];

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

  if (geminiMale.includes(voiceName)) return ' (male)';
  if (geminiFemale.includes(voiceName)) return ' (female)';
  if (openaiMale.includes(voiceName)) return ' (male)';
  if (openaiFemale.includes(voiceName)) return ' (female)';
  if (googleMale.includes(voiceName)) return ' (male)';
  if (googleFemale.includes(voiceName)) return ' (female)';

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

  // Fetch models when modal opens
  useEffect(() => {
    if (isOpen && !modelsLoaded) {
      fetchModels();
    }
  }, [isOpen, modelsLoaded, fetchModels]);

  // Fallback providers if dynamic data hasn't loaded yet
  const fallbackProviders = [
    { value: 'openai', label: 'OpenAI' },
    { value: 'anthropic', label: 'Anthropic' },
    { value: 'google', label: 'Google' },
    { value: 'perplexity', label: 'Perplexity' },
    { value: 'deepseek', label: 'DeepSeek' },
    { value: 'venice', label: 'Venice (Private)' },
    { value: 'ollama', label: 'Ollama (Local)' },
  ];

  // Fallback models by provider (matches backend ModelRegistry)
  const fallbackModels: Record<string, { value: string; label: string }[]> = {
    openai: [
      { value: 'gpt-5.2', label: 'GPT-5.2 ' },
      { value: 'gpt-5.2-pro', label: 'GPT-5.2 Pro' },
      { value: 'gpt-5.2-chat-latest', label: 'GPT-5.2 Instant' },
      { value: 'gpt-5.2-codex', label: 'GPT-5.2 Codex' },
      { value: 'gpt-5.1', label: 'GPT-5.1' },
      { value: 'gpt-5.1-chat-latest', label: 'GPT-5.1 Instant' },
      { value: 'gpt-5-turbo', label: 'GPT-5 Turbo' },
      { value: 'gpt-5', label: 'GPT-5' },
      { value: 'gpt-5-mini', label: 'GPT-5 Mini' },
      { value: 'gpt-4.1', label: 'GPT-4.1' },
      { value: 'gpt-4.1-mini', label: 'GPT-4.1 Mini' },
      { value: 'gpt-4o', label: 'GPT-4o' },
      { value: 'gpt-4o-mini', label: 'GPT-4o Mini' },
      { value: 'o4', label: 'o4 (Reasoning)' },
      { value: 'o4-mini', label: 'o4-mini (Reasoning)' },
      { value: 'o3-mini', label: 'o3-mini (Reasoning)' },
      { value: 'o1', label: 'o1 (Reasoning)' },
    ],
    anthropic: [
      { value: 'claude-sonnet-4-5-20250929', label: 'Claude Sonnet 4.5' },
      { value: 'claude-opus-4-1-20250805', label: 'Claude Opus 4.1' },
      { value: 'claude-opus-4-20250514', label: 'Claude Opus 4' },
      { value: 'claude-sonnet-4-20250514', label: 'Claude Sonnet 4' },
      { value: 'claude-3-7-sonnet-20250219', label: 'Claude 3.7 Sonnet' },
      { value: 'claude-3-5-haiku-20241022', label: 'Claude 3.5 Haiku' },
      { value: 'claude-3-haiku-20240307', label: 'Claude 3 Haiku' },
    ],
    google: [
      { value: 'gemini-3-pro-preview', label: 'Gemini 3 Pro ' },
      { value: 'gemini-3-flash-preview', label: 'Gemini 3 Flash' },
      { value: 'gemini-3-pro-image-preview', label: 'Gemini 3 Pro Image' },
      { value: 'gemini-2.5-pro', label: 'Gemini 2.5 Pro' },
      { value: 'gemini-2.5-flash', label: 'Gemini 2.5 Flash' },
      { value: 'gemini-2.5-flash-preview-09-2025', label: 'Gemini 2.5 Flash Preview' },
      { value: 'gemini-2.5-flash-lite', label: 'Gemini 2.5 Flash Lite' },
      { value: 'gemini-2.0-flash', label: 'Gemini 2.0 Flash' },
      { value: 'gemini-1.5-pro', label: 'Gemini 1.5 Pro' },
    ],
    perplexity: [
      { value: 'sonar-pro', label: 'Sonar Pro' },
      { value: 'sonar', label: 'Sonar' },
      { value: 'sonar-reasoning-pro', label: 'Sonar Reasoning Pro' },
      { value: 'sonar-reasoning', label: 'Sonar Reasoning' },
      { value: 'sonar-deep-research', label: 'Sonar Deep Research' },
    ],
    deepseek: [
      { value: 'deepseek-chat', label: 'DeepSeek Chat (V3.2)' },
      { value: 'deepseek-reasoner', label: 'DeepSeek Reasoner (R1)' },
    ],
    venice: [
      { value: 'venice-uncensored', label: 'Venice Uncensored' },
      { value: 'llama-3.3-70b', label: 'Llama 3.3 70B' },
      { value: 'llama-3.2-3b', label: 'Llama 3.2 3B (Fast)' },
      { value: 'qwen3-235b-a22b-instruct-2507', label: 'Qwen3 235B Instruct' },
      { value: 'qwen3-235b-a22b-thinking-2507', label: 'Qwen3 235B Thinking' },
      { value: 'qwen3-next-80b', label: 'Qwen3 Next 80B' },
      { value: 'qwen3-coder-480b-a35b-instruct', label: 'Qwen3 Coder 480B' },
      { value: 'qwen3-4b', label: 'Qwen3 4B (Fast)' },
      { value: 'mistral-31-24b', label: 'Mistral 3.1 24B' },
      { value: 'claude-opus-45', label: 'Claude Opus 4.5 (Venice)' },
      { value: 'openai-gpt-52', label: 'GPT-5.2 (Venice)' },
      { value: 'openai-gpt-oss-120b', label: 'GPT OSS 120B (Venice)' },
      { value: 'gemini-3-pro-preview', label: 'Gemini 3 Pro (Venice)' },
      { value: 'gemini-3-flash-preview', label: 'Gemini 3 Flash (Venice)' },
      { value: 'grok-41-fast', label: 'Grok 4.1 Fast' },
      { value: 'grok-code-fast-1', label: 'Grok Code Fast' },
      { value: 'zai-org-glm-4.7', label: 'GLM 4.7' },
      { value: 'kimi-k2-thinking', label: 'Kimi K2 Thinking' },
      { value: 'minimax-m21', label: 'MiniMax M2.1' },
      { value: 'deepseek-v3.2', label: 'DeepSeek V3.2 (Venice)' },
      { value: 'google-gemma-3-27b-it', label: 'Gemma 3 27B' },
      { value: 'hermes-3-llama-3.1-405b', label: 'Hermes 3 Llama 405B' },
    ],
    ollama: [
      { value: 'llama3.3:70b', label: 'Llama 3.3 70B' },
      { value: 'llama3.2', label: 'Llama 3.2' },
      { value: 'llama3.2:1b', label: 'Llama 3.2 1B' },
      { value: 'llama3.2:3b', label: 'Llama 3.2 3B' },
      { value: 'llama3.2-vision:11b', label: 'Llama 3.2 Vision 11B' },
      { value: 'llama3.2-vision:90b', label: 'Llama 3.2 Vision 90B' },
      { value: 'qwen3:235b', label: 'Qwen3 235B' },
      { value: 'qwen3:30b', label: 'Qwen3 30B' },
      { value: 'qwen2.5:7b', label: 'Qwen 2.5 7B' },
      { value: 'deepseek-r1:8b', label: 'DeepSeek R1 8B' },
      { value: 'phi4:14b', label: 'Phi-4 14B' },
      { value: 'gemma2:9b', label: 'Gemma 2 9B' },
      { value: 'mistral:7b', label: 'Mistral 7B' },
      { value: 'codellama:7b', label: 'CodeLlama 7B' },
    ],
  };

  const fallbackDefaults: Record<string, string> = {
    openai: 'gpt-5.2',
    anthropic: 'claude-sonnet-4-5-20250929',
    google: 'gemini-3-pro-preview',
    perplexity: 'sonar-pro',
    deepseek: 'deepseek-chat',
    venice: 'venice-uncensored',
    ollama: 'llama3.3:70b',
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
  const [voiceProvider, setVoiceProvider] = useState('google');

  // Fee-based minting state
  const [pendingMinting, setPendingMinting] = useState<PendingMintingResult | null>(null);
  const [mintingStatus, setMintingStatus] = useState<MintingStatus | null>(null);
  const [statusPollingInterval, setStatusPollingInterval] = useState<ReturnType<typeof setInterval> | null>(null);
  const [paymentError, setPaymentError] = useState<string | null>(null);
  const [expiresIn, setExpiresIn] = useState<number>(0);
  const [txidInput, setTxidInput] = useState<string>('');
  const [submittingTxid, setSubmittingTxid] = useState<boolean>(false);
  const [voiceDropdownOpen, setVoiceDropdownOpen] = useState(false);
  const voiceDropdownRef = useRef<HTMLDivElement>(null);

  const [formData, setFormData] = useState<CreateQubeData>({
    name: '',
    genesisPrompt: '',
    aiProvider: 'openai',
    aiModel: 'gpt-5.2',
    voiceModel: 'google:en-US-Neural2-A',  // Default to Google Cloud TTS Neural2!
    ownerPubkey: '',  // NFT address derived automatically from this
    encryptGenesis: false,
    favoriteColor: '#00ff88',
    generateAvatar: true,
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
      'google': 'google:en-US-Neural2-A',
      'gemini': 'gemini:puck',
      'openai': 'openai:alloy',
      'elevenlabs': 'elevenlabs:default'
    };

    if (voiceProvider && defaultVoices[voiceProvider]) {
      setFormData(prev => ({ ...prev, voiceModel: defaultVoices[voiceProvider] }));
    }
  }, [voiceProvider]);

  // Close voice dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (voiceDropdownRef.current && !voiceDropdownRef.current.contains(event.target as Node)) {
        setVoiceDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Cleanup polling on unmount or close
  useEffect(() => {
    return () => {
      if (statusPollingInterval) {
        clearInterval(statusPollingInterval);
      }
    };
  }, [statusPollingInterval]);

  // Countdown timer for payment expiry
  useEffect(() => {
    if (expiresIn > 0 && step === 6) {
      const timer = setTimeout(() => {
        setExpiresIn(prev => Math.max(0, prev - 1));
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [expiresIn, step]);

  // Poll minting status
  const pollMintingStatus = useCallback(async (registrationId: string) => {
    try {
      console.log('[Minting] Polling status for:', registrationId);
      const result = await invoke<MintingStatusResult>('check_minting_status', {
        userId,
        registrationId,
        password,
      });
      console.log('[Minting] Poll result:', JSON.stringify(result, null, 2));

      if (result.success) {
        setMintingStatus(result.status || null);

        if (result.status === 'complete') {
          console.log('[Minting] Status is COMPLETE! Transitioning to success step.');
          // Stop polling FIRST before any state changes
          if (statusPollingInterval) {
            console.log('[Minting] Clearing polling interval');
            clearInterval(statusPollingInterval);
            setStatusPollingInterval(null);
          }
          // Set states to show success screen
          // NOTE: Don't call onQubesChange here - it causes parent re-render that
          // closes the modal before the success screen can display.
          // onQubesChange will be called in handleClose instead.
          console.log('[Minting] Setting success=true, step=7');
          setSuccess(true);
          setStep(7);  // Success step
          console.log('[Minting] Success screen should now be visible.');
        } else if (result.status === 'failed') {
          console.log('[Minting] Status is FAILED:', result.error_message);
          if (statusPollingInterval) {
            clearInterval(statusPollingInterval);
            setStatusPollingInterval(null);
          }
          setPaymentError(result.error_message || 'Minting failed');
        } else if (result.status === 'expired') {
          console.log('[Minting] Status is EXPIRED');
          if (statusPollingInterval) {
            clearInterval(statusPollingInterval);
            setStatusPollingInterval(null);
          }
          setPaymentError('Payment window expired. Please try again.');
        }
      } else {
        console.warn('[Minting] Poll returned success=false. Error:', result.error, 'Full result:', JSON.stringify(result, null, 2));
      }
    } catch (error) {
      console.error('[Minting] Failed to check minting status:', error);
    }
  }, [userId, password, statusPollingInterval, onQubesChange]);

  // Start fee-based minting
  const handleStartMinting = async () => {
    setLoading(true);
    setPaymentError(null);

    try {
      const result = await invoke<PendingMintingResult>('prepare_qube_for_minting', {
        userId,
        name: formData.name,
        genesisPrompt: formData.genesisPrompt,
        aiProvider: formData.aiProvider,
        aiModel: formData.aiModel,
        voiceModel: formData.voiceModel,
        ownerPubkey: formData.ownerPubkey,  // NFT address derived from this by backend
        password,
        encryptGenesis: formData.encryptGenesis || false,
        favoriteColor: formData.favoriteColor,
        avatarFile: formData.avatarFile || null,
        generateAvatar: formData.generateAvatar || false,
        avatarStyle: formData.avatarStyle || null,
      });

      if (result.success && result.registration_id) {
        setPendingMinting(result);
        setExpiresIn(result.expires_in_seconds || 1800);
        setStep(6);  // Payment step

        // Start polling for status
        const interval = setInterval(() => {
          pollMintingStatus(result.registration_id!);
        }, 5000);  // Poll every 5 seconds
        setStatusPollingInterval(interval);
      } else {
        setPaymentError(result.error || 'Failed to prepare minting');
      }
    } catch (error) {
      console.error('Failed to prepare minting:', error);
      setPaymentError(`Failed to prepare minting: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  // Submit transaction ID
  const handleSubmitTxid = async () => {
    if (!pendingMinting?.registration_id || !txidInput.trim()) return;

    setSubmittingTxid(true);
    setPaymentError(null);

    try {
      const result = await invoke<{ success: boolean; status?: string; error?: string }>('submit_payment_txid', {
        userId,
        registrationId: pendingMinting.registration_id,
        txid: txidInput.trim(),
      });

      if (result.success) {
        setMintingStatus('paid');
        // Continue polling - the status will update to 'minting' then 'complete'
      } else {
        setPaymentError(result.error || 'Failed to verify payment');
      }
    } catch (error) {
      console.error('Failed to submit txid:', error);
      setPaymentError(`Failed to submit transaction: ${error}`);
    } finally {
      setSubmittingTxid(false);
    }
  };

  // Cancel pending minting
  const handleCancelMinting = async () => {
    if (!pendingMinting?.registration_id) return;

    try {
      await invoke('cancel_pending_minting', {
        userId,
        registrationId: pendingMinting.registration_id,
      });
    } catch (error) {
      console.error('Failed to cancel minting:', error);
    }

    // Stop polling
    if (statusPollingInterval) {
      clearInterval(statusPollingInterval);
      setStatusPollingInterval(null);
    }

    setPendingMinting(null);
    setMintingStatus(null);
    setStep(5);  // Go back to confirmation
  };

  if (!isOpen) return null;

  // Legacy submit handler (for dev mode if needed)
  const handleSubmit = async () => {
    // Use fee-based minting flow
    await handleStartMinting();
  };

  const handleClose = () => {
    // Stop any polling
    if (statusPollingInterval) {
      clearInterval(statusPollingInterval);
      setStatusPollingInterval(null);
    }

    // If minting was successful, refresh the qube list NOW (after user saw success screen)
    if (success) {
      console.log('[Minting] Closing after successful minting - refreshing qube list');
      onQubesChange?.();
    }

    // Reset form
    setFormData({
      name: '',
      genesisPrompt: '',
      aiProvider: 'openai',
      aiModel: 'gpt-5.2',
      voiceModel: 'google:en-US-Neural2-A',  // Default to Google Cloud TTS Neural2!
      ownerPubkey: '',  // NFT address derived automatically from this
      encryptGenesis: false,
      favoriteColor: '#00ff88',
      generateAvatar: true,
      avatarStyle: 'cyberpunk',
      avatarFile: undefined,
    });
    setVoiceProvider('google');
    setStep(1);
    setSuccess(false);
    setErrors({});

    // Reset minting state
    setPendingMinting(null);
    setMintingStatus(null);
    setPaymentError(null);
    setExpiresIn(0);
    setTxidInput('');
    setSubmittingTxid(false);

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
      // Only ownerPubkey is required - NFT address is derived automatically
      if (!formData.ownerPubkey.trim()) {
        newErrors.ownerPubkey = 'BCH public key is required for Qube wallet and NFT minting';
      } else if (!/^(02|03)[a-fA-F0-9]{64}$/.test(formData.ownerPubkey.trim())) {
        newErrors.ownerPubkey = 'Must be compressed public key (02... or 03... + 64 hex chars)';
      }
    }

    if (currentStep === 4) {
      // Avatar is mandatory - must either upload or generate
      if (!formData.avatarFile && !formData.generateAvatar) {
        newErrors.avatarFile = 'Avatar is required. Please upload an image or enable AI generation.';
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
                {step === 6 ? 'Payment Required' : step === 7 ? 'Success!' : 'Create New Qube'}
              </h2>
              <div className="flex gap-2">
                {[1, 2, 3, 4, 5, 6].map((s) => (
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
              <select
                value={formData.aiProvider}
                onChange={(e) => {
                  const newProvider = e.target.value;
                  const defaultModel = getDefault(newProvider);
                  setFormData({ ...formData, aiProvider: newProvider, aiModel: defaultModel });
                }}
                className="w-full px-4 py-2 bg-glass-bg backdrop-blur-glass border border-glass-border rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-primary/50"
              >
                {providers.map(provider => (
                  <option key={provider.value} value={provider.value}>
                    {provider.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-text-secondary mb-2">
                AI Model
              </label>
              <select
                value={formData.aiModel}
                onChange={(e) => setFormData({ ...formData, aiModel: e.target.value })}
                className="w-full px-4 py-2 bg-glass-bg backdrop-blur-glass border border-glass-border rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-primary/50 scrollable-select"
                size={Math.min(8, getModels(formData.aiProvider).length)}
              >
                {getModels(formData.aiProvider).map(model => (
                  <option key={model.value} value={model.value}>
                    {model.label}
                  </option>
                ))}
              </select>
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
              <select
                value={voiceProvider}
                onChange={(e) => setVoiceProvider(e.target.value)}
                className="w-full px-4 py-2 bg-glass-bg backdrop-blur-glass border border-glass-border rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-primary/50"
              >
                <option value="google">Google Cloud TTS (380+ voices)</option>
                <option value="gemini">Gemini TTS (30 voices)</option>
                <option value="openai">OpenAI TTS (6 voices)</option>
                <option value="elevenlabs">ElevenLabs</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-text-secondary mb-2">
                Voice
              </label>
              <div className="relative" ref={voiceDropdownRef}>
                <button
                  type="button"
                  onClick={() => setVoiceDropdownOpen(!voiceDropdownOpen)}
                  className="w-full px-4 py-2 bg-glass-bg backdrop-blur-glass border border-glass-border rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-primary/50 text-left flex justify-between items-center"
                >
                  <span>
                    {formData.voiceModel?.split(':')[1] || 'Select voice'}{getVoiceGender(formData.voiceModel || '')}
                  </span>
                  <svg className={`w-4 h-4 transition-transform ${voiceDropdownOpen ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
                {voiceDropdownOpen && (
                  <div className="absolute z-50 w-full mt-1 bg-[#2a3441] border border-glass-border rounded-lg shadow-lg max-h-48 overflow-y-auto">
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
                        {['alloy', 'echo', 'fable', 'nova', 'onyx', 'shimmer'].map(voice => (
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
                  </div>
                )}
              </div>
              <p className="text-xs text-text-tertiary mt-1">
                {voiceProvider === 'google' && 'Google Cloud TTS requires service account credentials. 1M free chars/month for Neural2/WaveNet!'}
                {voiceProvider === 'gemini' && 'Gemini voices use your Google API key - FREE during preview!'}
                {voiceProvider === 'openai' && 'OpenAI voices use your OpenAI API key.'}
                {voiceProvider === 'elevenlabs' && 'ElevenLabs uses your ElevenLabs API key.'}
              </p>
            </div>

            {/* Owner Public Key - NFT address derived automatically */}
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-2">
                Your BCH Public Key *
              </label>
              <input
                type="text"
                placeholder="02abc123... or 03def456..."
                value={formData.ownerPubkey}
                onChange={(e) => setFormData({ ...formData, ownerPubkey: e.target.value })}
                className={`w-full px-4 py-2 bg-glass-bg backdrop-blur-glass border rounded-lg text-text-primary font-mono text-sm placeholder-text-tertiary focus:outline-none focus:ring-2 ${
                  errors.ownerPubkey
                    ? 'border-accent-danger focus:ring-accent-danger'
                    : 'border-glass-border focus:ring-accent-primary/50'
                }`}
              />
              {errors.ownerPubkey && (
                <span className="text-sm text-accent-danger">{errors.ownerPubkey}</span>
              )}
              <p className="text-xs text-text-tertiary mt-1">
                Your compressed public key (66 hex characters starting with 02 or 03).
                <br />
                <strong>In Electron Cash:</strong> Addresses tab → Right-click address → Details → Public key
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
                        setFormData({
                          ...formData,
                          avatarFile: filePath,
                          generateAvatar: false
                        });
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

              {/* Generate Avatar Option */}
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
                {formData.avatarFile && (
                  <button
                    onClick={() => setFormData({ ...formData, avatarFile: undefined })}
                    className="text-xs text-accent-danger hover:underline"
                  >
                    Remove uploaded file
                  </button>
                )}
              </div>
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
                ⚠️ Creating this Qube requires a small minting fee (0.0001 BCH / ~10,000 sats).
                You'll be shown payment details on the next step.
              </p>
            </div>

            {paymentError && (
              <div className="bg-accent-danger/10 border border-accent-danger/30 rounded-lg p-4">
                <p className="text-accent-danger text-sm">{paymentError}</p>
              </div>
            )}
          </div>
        )}

        {/* Step 6: Payment */}
        {step === 6 && pendingMinting && (
          <div className="space-y-4">
            <h3 className="text-xl text-text-primary font-medium mb-4">
              Complete Payment to Mint NFT
            </h3>

            <div className="text-center mb-6">
              <div className="text-text-tertiary text-sm mb-2">Time remaining</div>
              <div className="text-3xl font-mono text-accent-primary">
                {Math.floor(expiresIn / 60)}:{(expiresIn % 60).toString().padStart(2, '0')}
              </div>
            </div>

            <GlassCard className="p-6 bg-bg-secondary/50">
              <div className="text-center space-y-4">
                <div className="text-text-tertiary text-sm">Send exactly</div>
                <div className="text-4xl font-display text-accent-primary">
                  {pendingMinting.payment?.amount_bch} BCH
                </div>
                <div className="text-text-secondary text-sm">
                  ({pendingMinting.payment?.amount_satoshis.toLocaleString()} satoshis)
                </div>

                <div className="text-text-tertiary text-sm mt-4">to this address:</div>
                <div className="bg-bg-primary/50 p-3 rounded-lg">
                  <code className="text-accent-primary text-xs break-all font-mono">
                    {pendingMinting.payment?.address}
                  </code>
                </div>

                {/* QR Code */}
                {pendingMinting.payment?.qr_data && (
                  <div className="bg-white p-3 rounded-lg inline-block mt-4">
                    <QRCodeSVG
                      value={pendingMinting.payment.qr_data}
                      size={192}
                      level="M"
                      includeMargin={false}
                    />
                  </div>
                )}

                {/* Payment URI button */}
                {pendingMinting.payment?.payment_uri && (
                  <div className="mt-4">
                    <a
                      href={pendingMinting.payment.payment_uri}
                      className="inline-flex items-center gap-2 px-4 py-2 bg-accent-primary/10 border border-accent-primary/30 rounded-lg text-accent-primary hover:bg-accent-primary/20 transition-colors"
                    >
                      Open in Wallet App
                    </a>
                  </div>
                )}
              </div>
            </GlassCard>

            {/* Transaction ID Input */}
            <GlassCard className="p-4 bg-bg-secondary/30 mt-4">
              <div className="space-y-3">
                <div className="text-text-secondary text-sm text-center">
                  Already paid? Enter your transaction ID:
                </div>
                <div className="flex gap-2">
                  <input
                    type="text"
                    placeholder="Enter transaction ID (txid)..."
                    value={txidInput}
                    onChange={(e) => setTxidInput(e.target.value)}
                    className="flex-1 px-3 py-2 bg-glass-bg backdrop-blur-glass border border-glass-border rounded-lg text-text-primary font-mono text-xs placeholder-text-tertiary focus:outline-none focus:ring-2 focus:ring-accent-primary/50"
                  />
                  <GlassButton
                    variant="primary"
                    onClick={handleSubmitTxid}
                    loading={submittingTxid}
                    disabled={!txidInput.trim() || submittingTxid}
                  >
                    Verify
                  </GlassButton>
                </div>
              </div>
            </GlassCard>

            {/* Status indicator */}
            <div className="text-center mt-4">
              <div className="text-text-secondary text-sm">
                Status: <span className="font-medium text-text-primary capitalize">{mintingStatus || 'Waiting for payment...'}</span>
              </div>
              {mintingStatus === 'paid' && (
                <div className="text-accent-primary text-sm mt-1">
                  Payment received! Minting NFT...
                </div>
              )}
              {mintingStatus === 'minting' && (
                <div className="text-accent-primary text-sm mt-1 flex items-center justify-center gap-2">
                  <span className="animate-spin">⟳</span>
                  Minting in progress...
                </div>
              )}
            </div>

            {paymentError && (
              <div className="bg-accent-danger/10 border border-accent-danger/30 rounded-lg p-4 mt-4">
                <p className="text-accent-danger text-sm">{paymentError}</p>
              </div>
            )}

            <p className="text-text-tertiary text-xs text-center mt-4">
              Creating: <span className="text-text-primary">{pendingMinting.qube_name}</span>
            </p>
          </div>
        )}

        {/* Step 7: Success (after minting completes) */}
        {step === 7 && (
          <div className="text-center py-8">
            <div className="text-6xl mb-6">🎉</div>
            <h2 className="text-3xl font-display text-accent-primary mb-4">
              Qube Created Successfully!
            </h2>
            <p className="text-text-secondary mb-2">
              {formData.name} has been created and their NFT has been minted on Bitcoin Cash.
            </p>
            <p className="text-text-tertiary text-sm mb-8">
              Your new Qube is ready to chat!
            </p>
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-between mt-8">
          {step === 6 ? (
            <>
              <GlassButton variant="ghost" onClick={handleCancelMinting}>
                Cancel & Go Back
              </GlassButton>
              <div className="flex gap-2">
                <GlassButton
                  variant="secondary"
                  onClick={() => {
                    // Copy address to clipboard
                    if (pendingMinting?.payment?.address) {
                      navigator.clipboard.writeText(pendingMinting.payment.address);
                    }
                  }}
                >
                  Copy Address
                </GlassButton>
              </div>
            </>
          ) : step === 7 ? (
            <div className="w-full flex justify-center">
              <GlassButton variant="primary" onClick={handleClose}>
                Done
              </GlassButton>
            </div>
          ) : (
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
                  <GlassButton variant="primary" onClick={handleSubmit} loading={loading}>
                    Pay & Create Qube
                  </GlassButton>
                )}
              </div>
            </>
          )}
        </div>
          </>
        )}
      </GlassCard>
    </div>
  );
};
