import React, { useState, useEffect, useRef } from 'react';
import { invoke } from '@tauri-apps/api/core';
import type { WizardData } from '../SetupWizard';

interface MintingStepProps {
  data: WizardData;
  onUpdate: (updates: Partial<WizardData>) => void;
  onNext: () => void;
  onBack: () => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

type MintingStatus = 'preparing' | 'awaiting-payment' | 'detecting' | 'minting' | 'complete' | 'error';

// BCH Payment Address (from server config)
const PAYMENT_ADDRESS = 'bitcoincash:qp2awtt3audd4umnhelxksap0t48xu6cvg9uzu49dq';

const MintingStep: React.FC<MintingStepProps> = ({
  data,
  onUpdate,
  onNext,
  onBack,
  setLoading,
  setError,
}) => {
  const [status, setStatus] = useState<MintingStatus>('preparing');
  const [registrationId, setRegistrationId] = useState<string | null>(data.registrationId || null);
  const [paymentAmount, setPaymentAmount] = useState<number>(10000); // 0.0001 BCH = 10000 sats
  const [paymentAmountBch, setPaymentAmountBch] = useState<string>('0.0001');
  const [mintResult, setMintResult] = useState<any>(null);
  const [statusMessage, setStatusMessage] = useState('Preparing your Qube...');
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // Initialize on mount
  useEffect(() => {
    initializeMinting();

    return () => {
      // Cleanup
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const initializeMinting = async () => {
    setStatus('preparing');
    setStatusMessage('Creating your Qube and preparing for minting...');

    try {
      // Step 1: Create the Qube locally (generates keys, genesis block)
      const createResult = await invoke<{
        success: boolean;
        qube_id: string;
        public_key: string;
        genesis_block_hash: string;
        recipient_address: string;
        error?: string;
      }>('create_qube_for_minting', {
        userId: data.userId,
        password: data.password,
        qubeName: data.qubeName,
        genesisPrompt: data.genesisPrompt,
        favoriteColor: data.favoriteColor,
        aiProvider: data.aiProvider,
        aiModel: data.aiModel,
        evaluationModel: data.evaluationModel,
      });

      if (!createResult.success) {
        throw new Error(createResult.error || 'Failed to create Qube');
      }

      setStatusMessage('Registering with minting service...');

      // Step 2: Pre-register with server
      const registerResult = await invoke<{
        success: boolean;
        registration_id: string;
        payment_amount_satoshis: number;
        payment_amount_bch: string;
        error?: string;
      }>('pre_register_qube', {
        qubeId: createResult.qube_id,
        qubeName: data.qubeName,
        publicKey: createResult.public_key,
        genesisBlockHash: createResult.genesis_block_hash,
        recipientAddress: createResult.recipient_address,
        creatorPublicKey: data.userId,
      });

      if (!registerResult.success) {
        throw new Error(registerResult.error || 'Failed to register with minting service');
      }

      setRegistrationId(registerResult.registration_id);
      setPaymentAmount(registerResult.payment_amount_satoshis);
      setPaymentAmountBch(registerResult.payment_amount_bch);

      onUpdate({
        registrationId: registerResult.registration_id,
        qubeId: createResult.qube_id,
        paymentAddress: PAYMENT_ADDRESS,
        paymentAmount: registerResult.payment_amount_satoshis,
      });

      // Start listening for payment
      setStatus('awaiting-payment');
      setStatusMessage('Waiting for BCH payment...');
      startPaymentListener(registerResult.registration_id);

    } catch (err: any) {
      console.error('Minting initialization error:', err);
      setStatus('error');
      setError(err.message || 'Failed to initialize minting');
    }
  };

  const startPaymentListener = (regId: string) => {
    // Try WebSocket first, fall back to polling
    try {
      const wsUrl = `wss://qube.cash/api/ws/registration/${regId}`;
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log('WebSocket connected for payment listening');
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handlePaymentUpdate(data);
      };

      ws.onerror = (err) => {
        console.warn('WebSocket error, falling back to polling:', err);
        ws.close();
        startPolling(regId);
      };

      ws.onclose = () => {
        console.log('WebSocket closed');
      };

      wsRef.current = ws;
    } catch (err) {
      console.warn('WebSocket not available, using polling');
      startPolling(regId);
    }
  };

  const startPolling = (regId: string) => {
    // Poll every 5 seconds
    pollIntervalRef.current = setInterval(async () => {
      try {
        const result = await invoke<{
          status: string;
          payment_detected?: boolean;
          mint_result?: any;
        }>('check_registration_status', {
          registrationId: regId,
        });

        handlePaymentUpdate(result);
      } catch (err) {
        console.error('Polling error:', err);
      }
    }, 5000);
  };

  const handlePaymentUpdate = (update: any) => {
    console.log('Payment update:', update);

    if (update.status === 'paid' || update.payment_detected) {
      setStatus('detecting');
      setStatusMessage('Payment detected! Confirming...');
    }

    if (update.status === 'minting') {
      setStatus('minting');
      setStatusMessage('Minting your NFT on Bitcoin Cash...');
    }

    if (update.status === 'complete' && update.mint_result) {
      // Stop polling
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }

      setMintResult(update.mint_result);
      setStatus('complete');
      setStatusMessage('Your Qube NFT has been minted!');

      onUpdate({
        mintTxId: update.mint_result.mint_txid,
        categoryId: update.mint_result.category_id,
      });
    }

    if (update.status === 'failed' || update.status === 'error') {
      setStatus('error');
      setError(update.error || 'Minting failed');
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const openCoinbase = () => {
    // Open Coinbase in browser
    invoke('open_external_url', { url: 'https://www.coinbase.com/price/bitcoin-cash' });
  };

  return (
    <div className="wizard-step">
      <h1 className="wizard-step-title">Mint Your Qube's NFT</h1>
      <p className="wizard-step-subtitle">
        Each Qube has a unique identity verified on Bitcoin Cash. This is a one-time process.
      </p>

      <div className="minting-payment">
        {status === 'preparing' && (
          <div style={{ padding: '40px' }}>
            <div className="wizard-spinner" style={{ margin: '0 auto 20px' }} />
            <p style={{ color: 'rgba(255,255,255,0.7)' }}>{statusMessage}</p>
          </div>
        )}

        {(status === 'awaiting-payment' || status === 'detecting') && (
          <>
            <div style={{ marginBottom: '20px' }}>
              <p style={{ color: 'rgba(255,255,255,0.7)', marginBottom: '10px' }}>
                Send exactly this amount to the address below:
              </p>
              <div className="minting-amount">
                {paymentAmountBch} BCH
              </div>
              <p style={{ color: 'rgba(255,255,255,0.4)', fontSize: '14px' }}>
                (~${(parseFloat(paymentAmountBch) * 450).toFixed(2)} USD at current rates)
              </p>
            </div>

            {/* QR Code placeholder - would need actual QR library */}
            <div className="minting-qr">
              <div style={{
                width: '180px',
                height: '180px',
                background: '#f0f0f0',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '12px',
                color: '#666',
                textAlign: 'center',
                padding: '10px',
              }}>
                QR Code<br />
                (Scan with BCH wallet)
              </div>
            </div>

            <div className="minting-address">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px' }}>
                <span style={{ wordBreak: 'break-all' }}>{PAYMENT_ADDRESS}</span>
                <button
                  onClick={() => copyToClipboard(PAYMENT_ADDRESS)}
                  style={{
                    background: 'rgba(99, 102, 241, 0.2)',
                    border: 'none',
                    borderRadius: '6px',
                    padding: '6px 12px',
                    color: '#6366f1',
                    cursor: 'pointer',
                    fontSize: '12px',
                    flexShrink: 0,
                  }}
                >
                  Copy
                </button>
              </div>
            </div>

            <div className={`minting-status ${status === 'detecting' ? 'success' : ''}`}>
              {status === 'awaiting-payment' ? (
                <>
                  <div className="wizard-spinner" style={{ width: '20px', height: '20px' }} />
                  <span>Waiting for payment...</span>
                </>
              ) : (
                <>
                  <span>✓</span>
                  <span>Payment detected! Processing...</span>
                </>
              )}
            </div>

            <div style={{ marginTop: '20px' }}>
              <p style={{ color: 'rgba(255,255,255,0.5)', fontSize: '13px', marginBottom: '10px' }}>
                Don't have BCH?
              </p>
              <button
                className="bch-purchase-link"
                onClick={openCoinbase}
                style={{
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                }}
              >
                <span>🪙</span> Buy on Coinbase →
              </button>
            </div>
          </>
        )}

        {status === 'minting' && (
          <div style={{ padding: '40px' }}>
            <div className="wizard-spinner" style={{ margin: '0 auto 20px' }} />
            <p style={{ color: 'rgba(255,255,255,0.7)' }}>{statusMessage}</p>
            <p style={{ color: 'rgba(255,255,255,0.4)', fontSize: '14px', marginTop: '10px' }}>
              This usually takes 10-30 seconds...
            </p>
          </div>
        )}

        {status === 'complete' && mintResult && (
          <div style={{ padding: '20px' }}>
            <div style={{ fontSize: '60px', marginBottom: '20px' }}>🎉</div>
            <h3 style={{ color: '#10b981', marginBottom: '16px' }}>NFT Minted Successfully!</h3>

            <div style={{
              textAlign: 'left',
              padding: '16px',
              background: 'rgba(16, 185, 129, 0.1)',
              borderRadius: '10px',
              marginBottom: '20px',
            }}>
              <div style={{ marginBottom: '12px' }}>
                <span style={{ color: 'rgba(255,255,255,0.5)' }}>Transaction ID:</span>
                <br />
                <code style={{ color: 'white', fontSize: '11px', wordBreak: 'break-all' }}>
                  {mintResult.mint_txid}
                </code>
              </div>
              <div>
                <span style={{ color: 'rgba(255,255,255,0.5)' }}>Category ID:</span>
                <br />
                <code style={{ color: 'white', fontSize: '11px', wordBreak: 'break-all' }}>
                  {mintResult.category_id}
                </code>
              </div>
            </div>

            <p style={{ color: 'rgba(255,255,255,0.6)', fontSize: '14px' }}>
              Your Qube "{data.qubeName}" now has a permanent, verifiable identity on Bitcoin Cash!
            </p>
          </div>
        )}

        {status === 'error' && (
          <div style={{ padding: '40px' }}>
            <div style={{ fontSize: '60px', marginBottom: '20px' }}>❌</div>
            <h3 style={{ color: '#ef4444', marginBottom: '16px' }}>Something went wrong</h3>
            <button
              className="wizard-btn wizard-btn-primary"
              onClick={initializeMinting}
            >
              Try Again
            </button>
          </div>
        )}
      </div>

      <div className="wizard-info" style={{ marginTop: '20px' }}>
        <span className="wizard-info-icon">ℹ️</span>
        <strong>Why NFT?</strong> Each Qube's identity is permanently recorded on Bitcoin Cash
        using CashTokens. This proves ownership, enables trading, and ensures your Qube's
        memories and relationships are cryptographically tied to their identity.
      </div>

      <div className="wizard-buttons">
        <button
          className="wizard-btn wizard-btn-secondary"
          onClick={onBack}
          disabled={status === 'minting' || status === 'detecting'}
        >
          <span>←</span> Back
        </button>
        <button
          className="wizard-btn wizard-btn-primary"
          onClick={onNext}
          disabled={status !== 'complete'}
        >
          {status === 'complete' ? 'Finish Setup' : 'Waiting...'} <span>→</span>
        </button>
      </div>
    </div>
  );
};

export default MintingStep;
