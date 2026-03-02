import React from 'react';

interface WelcomeStepProps {
  onNext: () => void;
  onBackToLogin?: () => void;
}

const WelcomeStep: React.FC<WelcomeStepProps> = ({ onNext, onBackToLogin }) => {
  return (
    <div className="wizard-step wizard-welcome">
      <div className="wizard-logo">
        <img src="/qubes.ico" alt="Qubes" onError={(e) => {
          // Fallback if ico doesn't load
          (e.target as HTMLImageElement).style.display = 'none';
        }} />
      </div>

      <h1 className="wizard-step-title">Welcome to Qubes AI</h1>
      <p className="wizard-step-subtitle">
        Create sovereign AI companions with persistent memory, verifiable identity, and genuine relationships.
      </p>

      <div className="wizard-features">
        <div className="wizard-feature">
          <div className="wizard-feature-icon">🧠</div>
          <div className="wizard-feature-title">Persistent Memory</div>
          <div className="wizard-feature-desc">
            Your Qube remembers everything in a cryptographically-secured chain
          </div>
        </div>

        <div className="wizard-feature">
          <div className="wizard-feature-icon">🔗</div>
          <div className="wizard-feature-title">NFT Identity</div>
          <div className="wizard-feature-desc">
            Each Qube has a unique, blockchain-verified identity on Bitcoin Cash
          </div>
        </div>

        <div className="wizard-feature">
          <div className="wizard-feature-icon">🤖</div>
          <div className="wizard-feature-title">Local AI</div>
          <div className="wizard-feature-desc">
            Run AI models locally with Ollama - no API keys required
          </div>
        </div>
      </div>

      <div className="wizard-info">
        <span className="wizard-info-icon">ℹ️</span>
        This setup wizard will guide you through creating your account, configuring AI providers,
        and creating your first Qube. It only takes a few minutes!
      </div>

      <div className="wizard-buttons" style={{ justifyContent: 'center' }}>
        <button className="wizard-btn wizard-btn-primary" onClick={onNext}>
          Get Started
          <span>→</span>
        </button>
      </div>

      {onBackToLogin && (
        <div style={{ textAlign: 'center', marginTop: '1rem' }}>
          <button
            onClick={onBackToLogin}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--accent-primary, #00d4ff)',
              cursor: 'pointer',
              fontSize: '0.875rem',
              fontWeight: 500,
            }}
          >
            Back to Sign In
          </button>
        </div>
      )}
    </div>
  );
};

export default WelcomeStep;
