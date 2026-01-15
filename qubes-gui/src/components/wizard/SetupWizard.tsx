import React, { useState } from 'react';
import WelcomeStep from './steps/WelcomeStep';
import CreateAccountStep from './steps/CreateAccountStep';
import ApiKeysStep from './steps/ApiKeysStep';
import PinataStep from './steps/PinataStep';
import CompletionStep from './steps/CompletionStep';
import './SetupWizard.css';

export type WizardStep = 'welcome' | 'create-account' | 'api-keys' | 'pinata' | 'completion';

export interface WizardData {
  // Account
  userId: string;
  password: string;
  dataDir: string;

  // API Keys (optional)
  apiKeys: {
    openai?: string;
    anthropic?: string;
    google?: string;
    deepseek?: string;
    perplexity?: string;
    venice?: string;
    nanogpt?: string;
    pinata?: string;
  };
}

interface SetupWizardProps {
  onComplete: (data: WizardData) => void;
}

const STEPS: WizardStep[] = ['welcome', 'create-account', 'api-keys', 'pinata', 'completion'];

const SetupWizard: React.FC<SetupWizardProps> = ({ onComplete }) => {
  const [currentStep, setCurrentStep] = useState<WizardStep>('welcome');
  const [wizardData, setWizardData] = useState<WizardData>({
    userId: '',
    password: '',
    dataDir: '',
    apiKeys: {},
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const currentStepIndex = STEPS.indexOf(currentStep);

  const goToNextStep = () => {
    const nextIndex = currentStepIndex + 1;
    if (nextIndex < STEPS.length) {
      setCurrentStep(STEPS[nextIndex]);
      setError(null);
    }
  };

  const goToPreviousStep = () => {
    const prevIndex = currentStepIndex - 1;
    if (prevIndex >= 0) {
      setCurrentStep(STEPS[prevIndex]);
      setError(null);
    }
  };

  const updateData = (updates: Partial<WizardData>) => {
    setWizardData(prev => ({ ...prev, ...updates }));
  };

  const handleComplete = () => {
    onComplete(wizardData);
  };

  const renderStep = () => {
    switch (currentStep) {
      case 'welcome':
        return (
          <WelcomeStep
            onNext={goToNextStep}
          />
        );

      case 'create-account':
        return (
          <CreateAccountStep
            data={wizardData}
            onUpdate={updateData}
            onNext={goToNextStep}
            onBack={goToPreviousStep}
            setLoading={setIsLoading}
            setError={setError}
          />
        );

      case 'api-keys':
        return (
          <ApiKeysStep
            data={wizardData}
            onUpdate={updateData}
            onNext={goToNextStep}
            onBack={goToPreviousStep}
          />
        );

      case 'pinata':
        return (
          <PinataStep
            data={wizardData}
            onUpdate={updateData}
            onNext={goToNextStep}
            onBack={goToPreviousStep}
            setError={setError}
          />
        );

      case 'completion':
        return (
          <CompletionStep
            data={wizardData}
            onComplete={handleComplete}
          />
        );

      default:
        return null;
    }
  };

  return (
    <div className="wizard-overlay">
      <div className="wizard-container">
        {/* Progress bar */}
        <div className="wizard-progress">
          {STEPS.map((step, index) => (
            <div
              key={step}
              className={`wizard-progress-step ${index <= currentStepIndex ? 'active' : ''} ${index < currentStepIndex ? 'completed' : ''}`}
            >
              <div className="wizard-progress-dot">
                {index < currentStepIndex ? '✓' : index + 1}
              </div>
              <span className="wizard-progress-label">
                {step.split('-').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
              </span>
            </div>
          ))}
        </div>

        {/* Error display */}
        {error && (
          <div className="wizard-error">
            <span className="wizard-error-icon">⚠</span>
            {error}
            <button className="wizard-error-dismiss" onClick={() => setError(null)}>×</button>
          </div>
        )}

        {/* Loading overlay */}
        {isLoading && (
          <div className="wizard-loading">
            <div className="wizard-spinner" />
            <span>Processing...</span>
          </div>
        )}

        {/* Step content */}
        <div className="wizard-content">
          {renderStep()}
        </div>
      </div>
    </div>
  );
};

export default SetupWizard;
