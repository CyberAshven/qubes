import React, { useState } from 'react';
import { invoke } from '@tauri-apps/api/core';
import type { WizardData } from '../SetupWizard';

interface CreateQubeStepProps {
  data: WizardData;
  onUpdate: (updates: Partial<WizardData>) => void;
  onNext: () => void;
  onBack: () => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

// Predefined personality templates
const PERSONALITY_TEMPLATES = [
  {
    name: 'Friendly Assistant',
    prompt: 'You are a friendly and helpful AI assistant. You have a warm personality, enjoy helping with any task, and communicate in a clear, approachable manner. You remember our conversations and build on them over time.',
  },
  {
    name: 'Creative Companion',
    prompt: 'You are a creative and imaginative AI companion. You love brainstorming ideas, storytelling, and thinking outside the box. You approach problems with curiosity and enthusiasm, always looking for innovative solutions.',
  },
  {
    name: 'Technical Expert',
    prompt: 'You are a knowledgeable technical expert. You excel at explaining complex concepts clearly, helping with coding and debugging, and providing well-reasoned technical advice. You stay up-to-date with best practices.',
  },
  {
    name: 'Philosophical Thinker',
    prompt: 'You are a thoughtful philosophical companion. You enjoy deep conversations about ideas, ethics, and the nature of existence. You ask probing questions and help explore topics from multiple perspectives.',
  },
  {
    name: 'Custom',
    prompt: '',
  },
];

const CreateQubeStep: React.FC<CreateQubeStepProps> = ({
  data,
  onUpdate,
  onNext,
  onBack,
  setLoading,
  setError,
}) => {
  const [qubeName, setQubeName] = useState(data.qubeName || '');
  const [selectedTemplate, setSelectedTemplate] = useState(0);
  const [customPrompt, setCustomPrompt] = useState(data.genesisPrompt || '');
  const [favoriteColor, setFavoriteColor] = useState(data.favoriteColor || '#6366f1');
  const [aiProvider, setAiProvider] = useState(data.aiProvider || 'ollama');
  const [aiModel, setAiModel] = useState(data.aiModel || 'llama3.2:3b');

  // Available models per provider
  const modelsByProvider: Record<string, { id: string; name: string }[]> = {
    ollama: [
      { id: 'llama3.2:3b', name: 'Llama 3.2 3B (Default)' },
      { id: 'mistral:7b', name: 'Mistral 7B' },
      { id: 'qwen2.5:7b', name: 'Qwen 2.5 7B' },
    ],
    openai: [
      { id: 'gpt-4o', name: 'GPT-4o' },
      { id: 'gpt-4o-mini', name: 'GPT-4o Mini' },
      { id: 'o1-preview', name: 'o1-preview' },
    ],
    anthropic: [
      { id: 'claude-sonnet-4-20250514', name: 'Claude Sonnet 4' },
      { id: 'claude-opus-4-20250514', name: 'Claude Opus 4' },
    ],
    google: [
      { id: 'gemini-2.0-flash', name: 'Gemini 2.0 Flash' },
      { id: 'gemini-1.5-pro', name: 'Gemini 1.5 Pro' },
    ],
    deepseek: [
      { id: 'deepseek-chat', name: 'DeepSeek V3' },
      { id: 'deepseek-reasoner', name: 'DeepSeek R1' },
    ],
    perplexity: [
      { id: 'sonar', name: 'Sonar' },
      { id: 'sonar-pro', name: 'Sonar Pro' },
    ],
  };

  const getGenesisPrompt = () => {
    if (selectedTemplate === PERSONALITY_TEMPLATES.length - 1) {
      return customPrompt;
    }
    return PERSONALITY_TEMPLATES[selectedTemplate].prompt;
  };

  const isValid = () => {
    return (
      qubeName.length >= 2 &&
      qubeName.length <= 30 &&
      /^[a-zA-Z][a-zA-Z0-9_-]*$/.test(qubeName) &&
      getGenesisPrompt().length >= 20
    );
  };

  const handleNext = async () => {
    if (!isValid()) {
      if (qubeName.length < 2 || !/^[a-zA-Z][a-zA-Z0-9_-]*$/.test(qubeName)) {
        setError('Qube name must start with a letter and be 2-30 characters');
      } else {
        setError('Please provide a personality description (at least 20 characters)');
      }
      return;
    }

    // Update data and proceed to minting
    onUpdate({
      qubeName,
      genesisPrompt: getGenesisPrompt(),
      favoriteColor,
      aiProvider,
      aiModel,
      evaluationModel: 'mistral:7b',
    });

    onNext();
  };

  return (
    <div className="wizard-step">
      <h1 className="wizard-step-title">Create Your First Qube</h1>
      <p className="wizard-step-subtitle">
        Give your AI companion a name and personality. This becomes their permanent identity.
      </p>

      <div className="wizard-form">
        {/* Name */}
        <div className="wizard-field">
          <label className="wizard-label">Qube Name</label>
          <input
            type="text"
            className="wizard-input"
            placeholder="e.g., Atlas, Nova, Echo..."
            value={qubeName}
            onChange={(e) => setQubeName(e.target.value.replace(/[^a-zA-Z0-9_-]/g, ''))}
            maxLength={30}
          />
          <span style={{ fontSize: '12px', color: 'rgba(255,255,255,0.4)' }}>
            This name is permanent and will be part of their blockchain identity
          </span>
        </div>

        {/* Personality Template */}
        <div className="wizard-field">
          <label className="wizard-label">Personality</label>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '12px' }}>
            {PERSONALITY_TEMPLATES.map((template, index) => (
              <button
                key={template.name}
                type="button"
                onClick={() => setSelectedTemplate(index)}
                style={{
                  padding: '8px 16px',
                  borderRadius: '20px',
                  border: selectedTemplate === index
                    ? '2px solid #6366f1'
                    : '1px solid rgba(255, 255, 255, 0.2)',
                  background: selectedTemplate === index
                    ? 'rgba(99, 102, 241, 0.2)'
                    : 'transparent',
                  color: selectedTemplate === index ? 'white' : 'rgba(255, 255, 255, 0.7)',
                  cursor: 'pointer',
                  fontSize: '13px',
                  transition: 'all 0.2s ease',
                }}
              >
                {template.name}
              </button>
            ))}
          </div>

          {selectedTemplate === PERSONALITY_TEMPLATES.length - 1 ? (
            <textarea
              className="wizard-input wizard-textarea"
              placeholder="Describe your Qube's personality, traits, and how they should interact..."
              value={customPrompt}
              onChange={(e) => setCustomPrompt(e.target.value)}
              rows={4}
            />
          ) : (
            <div style={{
              padding: '12px 16px',
              background: 'rgba(99, 102, 241, 0.1)',
              borderRadius: '10px',
              color: 'rgba(255, 255, 255, 0.8)',
              fontSize: '14px',
              lineHeight: '1.6',
            }}>
              {PERSONALITY_TEMPLATES[selectedTemplate].prompt}
            </div>
          )}
        </div>

        {/* Color & Provider Row */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
          {/* Favorite Color */}
          <div className="wizard-field">
            <label className="wizard-label">Favorite Color</label>
            <div className="wizard-color-picker">
              <input
                type="color"
                className="wizard-color-input"
                value={favoriteColor}
                onChange={(e) => setFavoriteColor(e.target.value)}
              />
              <span className="wizard-color-value">{favoriteColor}</span>
            </div>
          </div>

          {/* AI Provider */}
          <div className="wizard-field">
            <label className="wizard-label">AI Provider</label>
            <select
              className="wizard-select"
              value={aiProvider}
              onChange={(e) => {
                setAiProvider(e.target.value);
                // Set default model for provider
                const models = modelsByProvider[e.target.value];
                if (models && models.length > 0) {
                  setAiModel(models[0].id);
                }
              }}
            >
              <option value="ollama">Ollama (Local)</option>
              <option value="openai">OpenAI</option>
              <option value="anthropic">Anthropic</option>
              <option value="google">Google AI</option>
              <option value="deepseek">DeepSeek</option>
              <option value="perplexity">Perplexity</option>
            </select>
          </div>
        </div>

        {/* AI Model */}
        <div className="wizard-field">
          <label className="wizard-label">AI Model</label>
          <select
            className="wizard-select"
            value={aiModel}
            onChange={(e) => setAiModel(e.target.value)}
          >
            {(modelsByProvider[aiProvider] || []).map((model) => (
              <option key={model.id} value={model.id}>
                {model.name}
              </option>
            ))}
          </select>
          {aiProvider !== 'ollama' && (
            <span style={{ fontSize: '12px', color: '#f59e0b' }}>
              ⚠️ Requires API key configured in previous step
            </span>
          )}
        </div>

        <div className="wizard-info">
          <span className="wizard-info-icon">🎨</span>
          Your Qube will receive a placeholder avatar. You can generate a custom AI avatar
          later in Settings (requires OpenAI API key for DALL-E).
        </div>
      </div>

      <div className="wizard-buttons">
        <button className="wizard-btn wizard-btn-secondary" onClick={onBack}>
          <span>←</span> Back
        </button>
        <button
          className="wizard-btn wizard-btn-primary"
          onClick={handleNext}
          disabled={!isValid()}
        >
          Continue to Minting <span>→</span>
        </button>
      </div>
    </div>
  );
};

export default CreateQubeStep;
