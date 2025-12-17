import React, { useState, useEffect } from 'react';
import { invoke } from '@tauri-apps/api/core';
import type { WizardData } from '../SetupWizard';

interface ApiKeysStepProps {
  data: WizardData;
  onUpdate: (updates: Partial<WizardData>) => void;
  onNext: () => void;
  onBack: () => void;
}

const ApiKeysStep: React.FC<ApiKeysStepProps> = ({
  data,
  onUpdate,
  onNext,
  onBack,
}) => {
  const [apiKeys, setApiKeys] = useState(data.apiKeys || {});
  const [ollamaStatus, setOllamaStatus] = useState<'checking' | 'running' | 'not-running' | 'error'>('checking');
  const [ollamaModels, setOllamaModels] = useState<string[]>([]);

  // Check Ollama status on mount
  useEffect(() => {
    checkOllamaStatus();
  }, []);

  const checkOllamaStatus = async () => {
    setOllamaStatus('checking');
    try {
      const result = await invoke<{ running: boolean; models: string[] }>('check_ollama_status');
      if (result.running) {
        setOllamaStatus('running');
        setOllamaModels(result.models || []);
      } else {
        setOllamaStatus('not-running');
      }
    } catch (err) {
      setOllamaStatus('error');
    }
  };

  const startOllama = async () => {
    setOllamaStatus('checking');
    try {
      await invoke('start_ollama');
      // Wait a moment for Ollama to start
      setTimeout(checkOllamaStatus, 3000);
    } catch (err) {
      setOllamaStatus('error');
    }
  };

  const updateApiKey = (provider: string, value: string) => {
    const updated = { ...apiKeys, [provider]: value || undefined };
    setApiKeys(updated);
  };

  const handleNext = () => {
    onUpdate({ apiKeys });
    onNext();
  };

  const handleSkip = () => {
    onUpdate({ apiKeys: {} });
    onNext();
  };

  return (
    <div className="wizard-step">
      <h1 className="wizard-step-title">AI Provider Setup</h1>
      <p className="wizard-step-subtitle">
        Configure AI providers. Ollama (local) is included - cloud providers are optional.
      </p>

      {/* Ollama Status */}
      <div style={{
        padding: '20px',
        background: ollamaStatus === 'running'
          ? 'rgba(16, 185, 129, 0.1)'
          : 'rgba(255, 255, 255, 0.03)',
        border: `1px solid ${ollamaStatus === 'running' ? 'rgba(16, 185, 129, 0.3)' : 'rgba(255, 255, 255, 0.1)'}`,
        borderRadius: '12px',
        marginBottom: '24px',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
              <span style={{ fontSize: '24px' }}>🦙</span>
              <span style={{ fontWeight: '600', color: 'white', fontSize: '16px' }}>Ollama (Local AI)</span>
              <span style={{
                padding: '4px 10px',
                background: ollamaStatus === 'running' ? '#10b981' : '#6366f1',
                borderRadius: '20px',
                fontSize: '11px',
                fontWeight: '600',
                color: 'white',
              }}>
                {ollamaStatus === 'checking' ? 'Checking...' :
                 ollamaStatus === 'running' ? 'Running' :
                 ollamaStatus === 'not-running' ? 'Not Running' : 'Error'}
              </span>
            </div>
            <p style={{ color: 'rgba(255, 255, 255, 0.6)', fontSize: '14px', margin: 0 }}>
              {ollamaStatus === 'running'
                ? `Models available: ${ollamaModels.length > 0 ? ollamaModels.join(', ') : 'None (will download on first use)'}`
                : 'Run AI models locally without API keys. Included with Qubes.'}
            </p>
          </div>
          {ollamaStatus !== 'running' && ollamaStatus !== 'checking' && (
            <button
              className="wizard-btn wizard-btn-primary"
              style={{ padding: '10px 20px', fontSize: '14px' }}
              onClick={startOllama}
            >
              Start Ollama
            </button>
          )}
          {ollamaStatus === 'checking' && (
            <div className="wizard-spinner" style={{ width: '24px', height: '24px' }} />
          )}
        </div>
      </div>

      <div className="wizard-info" style={{ marginBottom: '24px' }}>
        <span className="wizard-info-icon">💡</span>
        <strong>Tip:</strong> Ollama is already bundled and ready to use! On first chat,
        it will download the default models (Llama 3.2 ~2GB, Mistral 7B ~4GB).
        Add cloud API keys below for access to more models like GPT-4 and Claude.
      </div>

      {/* Cloud API Keys */}
      <h3 style={{ color: 'white', marginBottom: '16px', fontSize: '16px' }}>
        Cloud Providers <span style={{ color: 'rgba(255,255,255,0.4)', fontWeight: 'normal' }}>(Optional)</span>
      </h3>

      <div className="api-keys-grid">
        <div className="api-key-item">
          <label className="api-key-label">
            OpenAI <span className="api-key-optional">(GPT-4, DALL-E)</span>
          </label>
          <input
            type="password"
            className="wizard-input"
            placeholder="sk-..."
            value={apiKeys.openai || ''}
            onChange={(e) => updateApiKey('openai', e.target.value)}
          />
        </div>

        <div className="api-key-item">
          <label className="api-key-label">
            Anthropic <span className="api-key-optional">(Claude)</span>
          </label>
          <input
            type="password"
            className="wizard-input"
            placeholder="sk-ant-..."
            value={apiKeys.anthropic || ''}
            onChange={(e) => updateApiKey('anthropic', e.target.value)}
          />
        </div>

        <div className="api-key-item">
          <label className="api-key-label">
            Google AI <span className="api-key-optional">(Gemini)</span>
          </label>
          <input
            type="password"
            className="wizard-input"
            placeholder="AI..."
            value={apiKeys.google || ''}
            onChange={(e) => updateApiKey('google', e.target.value)}
          />
        </div>

        <div className="api-key-item">
          <label className="api-key-label">
            DeepSeek <span className="api-key-optional">(R1, V3)</span>
          </label>
          <input
            type="password"
            className="wizard-input"
            placeholder="sk-..."
            value={apiKeys.deepseek || ''}
            onChange={(e) => updateApiKey('deepseek', e.target.value)}
          />
        </div>

        <div className="api-key-item">
          <label className="api-key-label">
            Perplexity <span className="api-key-optional">(Sonar)</span>
          </label>
          <input
            type="password"
            className="wizard-input"
            placeholder="pplx-..."
            value={apiKeys.perplexity || ''}
            onChange={(e) => updateApiKey('perplexity', e.target.value)}
          />
        </div>
      </div>

      <div className="wizard-buttons">
        <button className="wizard-btn wizard-btn-secondary" onClick={onBack}>
          <span>←</span> Back
        </button>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button className="wizard-btn wizard-btn-skip" onClick={handleSkip}>
            Skip for now
          </button>
          <button className="wizard-btn wizard-btn-primary" onClick={handleNext}>
            Continue <span>→</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default ApiKeysStep;
