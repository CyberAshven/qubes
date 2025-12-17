import React from 'react';
import type { WizardData } from '../SetupWizard';

interface CompletionStepProps {
  data: WizardData;
  onComplete: () => void;
}

const CompletionStep: React.FC<CompletionStepProps> = ({ data, onComplete }) => {
  const hasApiKeys = Object.values(data.apiKeys).some(key => key && key.length > 0);

  return (
    <div className="wizard-step wizard-completion">
      <div className="wizard-completion-icon">🚀</div>

      <h1 className="wizard-completion-title">You're All Set!</h1>
      <p className="wizard-completion-subtitle">
        Your account is ready. Now create your first Qube!
      </p>

      <div className="wizard-completion-summary">
        <div className="wizard-completion-item">
          <span className="wizard-completion-label">Account</span>
          <span className="wizard-completion-value">{data.userId}</span>
        </div>
        <div className="wizard-completion-item">
          <span className="wizard-completion-label">API Keys</span>
          <span className="wizard-completion-value">
            {hasApiKeys ? 'Configured' : 'Using Ollama (Local)'}
          </span>
        </div>
      </div>

      <div className="wizard-info" style={{ textAlign: 'left', marginBottom: '30px' }}>
        <span className="wizard-info-icon">💡</span>
        <strong>Next Steps:</strong>
        <ul style={{ margin: '10px 0 0 20px', paddingLeft: '0', lineHeight: '1.8' }}>
          <li>Create your first Qube - give it a name and personality</li>
          <li>Each Qube requires a small BCH payment to mint its NFT identity</li>
          <li>Chat with your Qube and build a relationship over time</li>
          <li>Your Qube learns and remembers everything you share</li>
          <li>Connect with other Qubes via P2P in the Connections tab</li>
        </ul>
      </div>

      <button
        className="wizard-btn wizard-btn-primary"
        onClick={onComplete}
        style={{ fontSize: '18px', padding: '16px 40px' }}
      >
        Get Started <span>→</span>
      </button>
    </div>
  );
};

export default CompletionStep;
