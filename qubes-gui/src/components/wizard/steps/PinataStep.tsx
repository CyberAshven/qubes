import React, { useState } from 'react';
import { invoke } from '@tauri-apps/api/core';
import type { WizardData } from '../SetupWizard';

interface PinataStepProps {
  data: WizardData;
  onUpdate: (updates: Partial<WizardData>) => void;
  onNext: () => void;
  onBack: () => void;
  setError: (error: string | null) => void;
}

const PinataStep: React.FC<PinataStepProps> = ({
  data,
  onUpdate,
  onNext,
  onBack,
  setError,
}) => {
  const [pinataJwt, setPinataJwt] = useState(data.apiKeys?.pinata || '');
  const [showKey, setShowKey] = useState(false);

  const openPinataSignup = async () => {
    try {
      await invoke('open_external_url', { url: 'https://app.pinata.cloud/register' });
    } catch (err) {
      // Fallback - just continue, user can manually navigate
      window.open('https://app.pinata.cloud/register', '_blank');
    }
  };

  const openPinataKeys = async () => {
    try {
      await invoke('open_external_url', { url: 'https://app.pinata.cloud/developers/api-keys' });
    } catch (err) {
      window.open('https://app.pinata.cloud/developers/api-keys', '_blank');
    }
  };

  const isValid = () => {
    // JWT tokens start with "eyJ" (base64 encoded JSON)
    return pinataJwt.length > 50 && pinataJwt.startsWith('eyJ');
  };

  const handleNext = () => {
    if (!isValid()) {
      setError('Please enter a valid Pinata JWT token (starts with "eyJ")');
      return;
    }

    onUpdate({
      apiKeys: {
        ...data.apiKeys,
        pinata: pinataJwt,
      }
    });
    onNext();
  };

  return (
    <div className="wizard-step">
      <h1 className="wizard-step-title">Pinata IPFS Setup</h1>
      <p className="wizard-step-subtitle">
        Pinata is required to store your Qube's NFT metadata on IPFS.
      </p>

      {/* What is Pinata */}
      <div className="wizard-info" style={{ marginBottom: '24px', textAlign: 'left' }}>
        <span className="wizard-info-icon">🌐</span>
        <div>
          <strong>What is Pinata?</strong>
          <p style={{ margin: '8px 0 0 0', lineHeight: '1.6' }}>
            Pinata is a service that stores files on IPFS (InterPlanetary File System) -
            a decentralized storage network. When you create a Qube, its identity and
            metadata are stored on IPFS and linked to its NFT on Bitcoin Cash. This
            ensures your Qube's identity is permanent and verifiable.
          </p>
        </div>
      </div>

      {/* Setup Steps */}
      <div style={{
        background: 'rgba(255, 255, 255, 0.03)',
        border: '1px solid rgba(255, 255, 255, 0.1)',
        borderRadius: '12px',
        padding: '20px',
        marginBottom: '24px',
      }}>
        <h3 style={{ color: 'white', margin: '0 0 16px 0', fontSize: '16px' }}>
          How to get your Pinata JWT:
        </h3>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
            <span style={{
              background: '#6366f1',
              color: 'white',
              borderRadius: '50%',
              width: '24px',
              height: '24px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '12px',
              fontWeight: '600',
              flexShrink: 0,
            }}>1</span>
            <div>
              <span style={{ color: 'white' }}>Create a free Pinata account</span>
              <button
                onClick={openPinataSignup}
                style={{
                  marginLeft: '12px',
                  padding: '4px 12px',
                  background: 'rgba(99, 102, 241, 0.2)',
                  border: '1px solid rgba(99, 102, 241, 0.4)',
                  borderRadius: '6px',
                  color: '#a5b4fc',
                  cursor: 'pointer',
                  fontSize: '12px',
                }}
              >
                Open Pinata Signup
              </button>
              <p style={{ color: 'rgba(255,255,255,0.5)', fontSize: '13px', margin: '4px 0 0 0' }}>
                Free tier includes 1GB storage - plenty for Qube metadata
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
            <span style={{
              background: '#6366f1',
              color: 'white',
              borderRadius: '50%',
              width: '24px',
              height: '24px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '12px',
              fontWeight: '600',
              flexShrink: 0,
            }}>2</span>
            <div>
              <span style={{ color: 'white' }}>Go to API Keys and click "+ New Key"</span>
              <button
                onClick={openPinataKeys}
                style={{
                  marginLeft: '12px',
                  padding: '4px 12px',
                  background: 'rgba(99, 102, 241, 0.2)',
                  border: '1px solid rgba(99, 102, 241, 0.4)',
                  borderRadius: '6px',
                  color: '#a5b4fc',
                  cursor: 'pointer',
                  fontSize: '12px',
                }}
              >
                Open API Keys Page
              </button>
              <p style={{ color: 'rgba(255,255,255,0.5)', fontSize: '13px', margin: '4px 0 0 0' }}>
                Look for the "+ New Key" button in the top right corner
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
            <span style={{
              background: '#6366f1',
              color: 'white',
              borderRadius: '50%',
              width: '24px',
              height: '24px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '12px',
              fontWeight: '600',
              flexShrink: 0,
            }}>3</span>
            <div>
              <span style={{ color: 'white' }}>Name your key (e.g., "Qubes") and click Create</span>
              <p style={{ color: 'rgba(255,255,255,0.5)', fontSize: '13px', margin: '4px 0 0 0' }}>
                Default permissions are fine - no need to change anything
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
            <span style={{
              background: '#ef4444',
              color: 'white',
              borderRadius: '50%',
              width: '24px',
              height: '24px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '12px',
              fontWeight: '600',
              flexShrink: 0,
            }}>4</span>
            <div>
              <span style={{ color: '#fca5a5', fontWeight: '600' }}>IMPORTANT: Copy the JWT immediately!</span>
              <p style={{ color: 'rgba(255,255,255,0.5)', fontSize: '13px', margin: '4px 0 0 0' }}>
                The JWT token (starts with "eyJ...") is only shown ONCE when you create the key.
                Copy it before closing the dialog - you cannot retrieve it later!
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* JWT Input */}
      <div className="wizard-field">
        <label className="wizard-label">Pinata JWT Token</label>
        <div style={{ position: 'relative' }}>
          <input
            type={showKey ? 'text' : 'password'}
            className="wizard-input"
            placeholder="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            value={pinataJwt}
            onChange={(e) => setPinataJwt(e.target.value)}
            style={{ paddingRight: '50px' }}
          />
          <button
            type="button"
            onClick={() => setShowKey(!showKey)}
            style={{
              position: 'absolute',
              right: '12px',
              top: '50%',
              transform: 'translateY(-50%)',
              background: 'none',
              border: 'none',
              color: 'rgba(255,255,255,0.5)',
              cursor: 'pointer',
              fontSize: '14px',
            }}
          >
            {showKey ? 'Hide' : 'Show'}
          </button>
        </div>
        {pinataJwt && !isValid() && (
          <span style={{ fontSize: '12px', color: '#ef4444', marginTop: '4px', display: 'block' }}>
            JWT token should start with "eyJ" and be at least 50 characters
          </span>
        )}
        {pinataJwt && isValid() && (
          <span style={{ fontSize: '12px', color: '#10b981', marginTop: '4px', display: 'block' }}>
            Valid JWT format
          </span>
        )}
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
          Continue <span>→</span>
        </button>
      </div>
    </div>
  );
};

export default PinataStep;
