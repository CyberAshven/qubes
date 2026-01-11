import React, { useState, useEffect } from 'react';
import { invoke } from '@tauri-apps/api/core';
import type { WizardData } from '../SetupWizard';

interface CreateAccountStepProps {
  data: WizardData;
  onUpdate: (updates: Partial<WizardData>) => void;
  onNext: () => void;
  onBack: () => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

const CreateAccountStep: React.FC<CreateAccountStepProps> = ({
  data,
  onUpdate,
  onNext,
  onBack,
  setLoading,
  setError,
}) => {
  const [userId, setUserId] = useState(data.userId || '');
  const [password, setPassword] = useState(data.password || '');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [passwordStrength, setPasswordStrength] = useState(0);

  // Calculate password strength
  useEffect(() => {
    let strength = 0;
    if (password.length >= 8) strength++;
    if (password.length >= 12) strength++;
    if (/[A-Z]/.test(password)) strength++;
    if (/[0-9]/.test(password)) strength++;
    if (/[^A-Za-z0-9]/.test(password)) strength++;
    setPasswordStrength(Math.min(strength, 4));
  }, [password]);

  const getStrengthLabel = () => {
    switch (passwordStrength) {
      case 0:
      case 1: return 'Weak';
      case 2: return 'Fair';
      case 3: return 'Good';
      case 4: return 'Strong';
      default: return '';
    }
  };

  const getStrengthClass = (index: number) => {
    if (index >= passwordStrength) return '';
    switch (passwordStrength) {
      case 1: return 'weak';
      case 2: return 'fair';
      case 3: return 'good';
      case 4: return 'strong';
      default: return '';
    }
  };

  const isValid = () => {
    return (
      userId.length >= 3 &&
      userId.length <= 30 &&
      /^[a-zA-Z0-9_-]+$/.test(userId) &&
      password.length >= 8 &&
      password === confirmPassword
    );
  };

  const handleNext = async () => {
    if (!isValid()) {
      if (password !== confirmPassword) {
        setError('Passwords do not match');
      } else if (password.length < 8) {
        setError('Password must be at least 8 characters');
      } else {
        setError('Please enter a valid username (3-30 characters, letters, numbers, - and _ only)');
      }
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Create user account via Tauri
      const result = await invoke<{ success: boolean; data_dir: string; error?: string }>('create_user_account', {
        userId: userId,
        password: password,
      });

      if (result.success) {
        onUpdate({
          userId: userId,
          password: password,
          dataDir: result.data_dir,
        });
        onNext();
      } else {
        // On error, try to get backend diagnostics for debugging
        let errorMsg = result.error || 'Failed to create account';
        try {
          const diagnostics = await invoke<Record<string, unknown>>('get_backend_diagnostics');
          console.error('[CreateAccount] Backend diagnostics:', diagnostics);
          // Add key diagnostic info to error message for Linux users
          if (diagnostics.os === 'linux' || diagnostics.os === 'macos') {
            if (!diagnostics.backend_found) {
              errorMsg += ` [Backend not found. Checked: ${diagnostics.paths_checked}]`;
            } else if (diagnostics.is_executable === false) {
              errorMsg += ` [Backend found but not executable: ${diagnostics.backend_path}]`;
            } else if (diagnostics.test_run_error) {
              errorMsg += ` [Backend test failed: ${diagnostics.test_run_error}]`;
            }
          }
        } catch (diagErr) {
          console.error('[CreateAccount] Failed to get diagnostics:', diagErr);
        }
        setError(errorMsg);
      }
    } catch (err: any) {
      // On catch error, try to get backend diagnostics
      let errorMsg = err.message || 'Failed to create account';
      try {
        const diagnostics = await invoke<Record<string, unknown>>('get_backend_diagnostics');
        console.error('[CreateAccount] Backend diagnostics on error:', diagnostics);
        if (!diagnostics.backend_found) {
          errorMsg += ` [Backend not found at: ${diagnostics.exe_dir}]`;
        } else if (diagnostics.test_run_error) {
          errorMsg += ` [${diagnostics.test_run_error}]`;
        }
      } catch {
        // Ignore diagnostic errors
      }
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="wizard-step">
      <h1 className="wizard-step-title">Create Your Account</h1>
      <p className="wizard-step-subtitle">
        Your account secures all your Qubes and their memories with encryption.
      </p>

      <div className="wizard-form">
        <div className="wizard-field">
          <label className="wizard-label">Username</label>
          <input
            type="text"
            className="wizard-input"
            placeholder="Enter a username"
            value={userId}
            onChange={(e) => setUserId(e.target.value.replace(/[^a-zA-Z0-9_-]/g, ''))}
            maxLength={30}
          />
          <span style={{ fontSize: '12px', color: 'rgba(255,255,255,0.4)' }}>
            3-30 characters, letters, numbers, - and _ only
          </span>
        </div>

        <div className="wizard-field">
          <label className="wizard-label">Master Password</label>
          <div style={{ position: 'relative' }}>
            <input
              type={showPassword ? 'text' : 'password'}
              className="wizard-input"
              placeholder="Enter a strong password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              style={{ paddingRight: '50px' }}
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
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
              {showPassword ? '🙈' : '👁️'}
            </button>
          </div>
          <div className="password-strength">
            {[0, 1, 2, 3].map((i) => (
              <div
                key={i}
                className={`password-strength-bar ${getStrengthClass(i)}`}
              />
            ))}
          </div>
          <span className="password-strength-text">
            Password strength: {getStrengthLabel()}
          </span>
        </div>

        <div className="wizard-field">
          <label className="wizard-label">Confirm Password</label>
          <input
            type={showPassword ? 'text' : 'password'}
            className="wizard-input"
            placeholder="Confirm your password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
          />
          {confirmPassword && password !== confirmPassword && (
            <span style={{ fontSize: '12px', color: '#ef4444' }}>
              Passwords do not match
            </span>
          )}
        </div>

        <div className="wizard-info">
          <span className="wizard-info-icon">🔐</span>
          <strong>Important:</strong> Your master password encrypts all your data using AES-256.
          There is no password recovery - if you forget it, your data cannot be recovered.
          Please store it securely!
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
          Create Account <span>→</span>
        </button>
      </div>
    </div>
  );
};

export default CreateAccountStep;
