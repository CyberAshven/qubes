/**
 * WalletConnect v2 Service for BCH
 *
 * Implements the wc2-bch-bcr spec (mainnet-pat) for connecting to
 * BCH wallets (Cashonize, Paytaca, Zapit, Electron Cash).
 *
 * The app never sees private keys. The wallet handles all signing.
 *
 * All WC imports are dynamic to avoid crashing the app on platforms
 * where the WC packages have issues (e.g. WebKitGTK web components).
 */

// ── Types ──────────────────────────────────────────────────────────

export interface WcSession {
  topic: string;
  address: string;
}

export interface WcSignResult {
  signedTransaction: string;
  signedTransactionHash: string;
}

// ── Constants ──────────────────────────────────────────────────────

const BCH_CHAIN_ID = 'bch:bitcoincash';

const BCH_NAMESPACE = {
  bch: {
    chains: [BCH_CHAIN_ID],
    methods: [
      'bch_getAddresses',
      'bch_signTransaction',
      'bch_signMessage',
      'bch_getTokens_V0',
      'bch_getBalance_V0',
      'bch_getChangeLockingBytecode_V0',
    ],
    events: ['addressesChanged'],
  },
};

// ── Singleton State ────────────────────────────────────────────────

let signClient: any | null = null;
let currentSession: WcSession | null = null;

// Event listeners
type Listener = (session: WcSession | null) => void;
const listeners: Set<Listener> = new Set();

function notifyListeners() {
  listeners.forEach((fn) => fn(currentSession));
}

export function onSessionChange(fn: Listener): () => void {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

// ── Initialization ─────────────────────────────────────────────────

/** Official Qubes WalletConnect project ID (registered at cloud.reown.com) */
const WC_PROJECT_ID = '1aaaf275500b1ad21b22b33edf354983';

async function getClient() {
  if (signClient) return signClient;

  const projectId = WC_PROJECT_ID;

  // Dynamic imports — only load WC packages when actually needed
  const { default: SignClient } = await import('@walletconnect/sign-client');

  signClient = await SignClient.init({
    projectId,
    metadata: {
      name: 'Qubes',
      description: 'Sovereign AI Agents on Bitcoin Cash',
      url: 'https://qube.cash',
      icons: ['https://qube.cash/icon.png'],
    },
  });

  // Restore existing session if any — clean up stale sessions
  const sessions = signClient.session.getAll();
  const bchSession = sessions.find((s: any) =>
    Object.keys(s.namespaces).includes('bch')
  );

  if (bchSession) {
    try {
      // Ping the session to verify it's still alive on the relay
      await signClient.ping({ topic: bchSession.topic });
      const address = extractAddress(bchSession);
      if (address) {
        currentSession = { topic: bchSession.topic, address };
        notifyListeners();
      }
    } catch {
      // Session is stale (deleted on relay or wallet side) — clean up locally
      console.warn('[WC] Stale session detected, cleaning up:', bchSession.topic);
      try {
        await signClient.disconnect({
          topic: bchSession.topic,
          reason: { code: 6000, message: 'Stale session cleanup' },
        });
      } catch {
        // Force-remove from local storage if disconnect also fails
        signClient.session.delete(bchSession.topic, { code: 6000, message: 'Stale session cleanup' });
      }
    }
  }

  // Handle session delete (wallet disconnected)
  signClient.on('session_delete', () => {
    currentSession = null;
    notifyListeners();
  });

  // Handle addressesChanged events — update current session address in place
  signClient.on('session_event', (event: any) => {
    if (event.params?.event?.name === 'addressesChanged') {
      // Re-fetch addresses when wallet notifies of change
      const newAddresses = event.params.event.data;
      if (Array.isArray(newAddresses) && newAddresses.length > 0) {
        const addr = typeof newAddresses[0] === 'string'
          ? newAddresses[0]
          : newAddresses[0]?.address;
        if (addr && currentSession) {
          currentSession.address = addr;
          notifyListeners();
        }
      }
    }
  });

  return signClient;
}

// ── Helpers ────────────────────────────────────────────────────────

function extractAddress(session: any): string | null {
  const bchNs = session.namespaces?.bch;
  if (!bchNs?.accounts?.length) return null;
  // Account format: "bch:bitcoincash:qz..." or "bch:bitcoincash:bitcoincash:qz..."
  const account = bchNs.accounts[0];
  const parts = account.split(':');
  // Remove the chain prefix, reconstruct the address
  if (parts.length >= 3) {
    // "bch" : "bitcoincash" : "qz..." → "bitcoincash:qz..."
    return parts.slice(1).join(':');
  }
  return null;
}

// ── Public API ─────────────────────────────────────────────────────

/**
 * Connect to a BCH wallet via WalletConnect.
 * Calls onUri with the WC URI so the caller can display it (QR code, copy button, etc.).
 */
export async function connect(onUri?: (uri: string) => void): Promise<WcSession> {
  const client = await getClient();

  const { uri, approval } = await client.connect({
    requiredNamespaces: BCH_NAMESPACE,
  });

  if (!uri) throw new Error('Failed to generate WalletConnect URI');

  // Pass URI to caller for display (QR code + copy button)
  onUri?.(uri);

  const session = await approval();

  const address = extractAddress(session);
  if (!address) {
    throw new Error('Wallet did not provide a BCH address');
  }

  currentSession = { topic: session.topic, address };
  notifyListeners();
  return currentSession;
}

/**
 * Disconnect the current wallet session.
 */
export async function disconnect(): Promise<void> {
  if (!currentSession || !signClient) return;

  try {
    await signClient.disconnect({
      topic: currentSession.topic,
      reason: { code: 6000, message: 'User disconnected' },
    });
  } catch {
    // Ignore disconnect errors
  }

  currentSession = null;
  notifyListeners();
}

/**
 * Get the current session (if connected).
 */
export function getSession(): WcSession | null {
  return currentSession;
}

/**
 * Request addresses (and possibly public keys) from the connected wallet.
 * Uses bch_getAddresses from the wc2-bch-bcr spec.
 *
 * @returns Array of address info objects. May include publicKey if wallet supports it.
 */
export async function getAddresses(): Promise<Array<{ address: string; publicKey?: string }>> {
  if (!currentSession || !signClient) {
    throw new Error('No wallet connected');
  }

  try {
    const result = await signClient.request({
      topic: currentSession.topic,
      chainId: BCH_CHAIN_ID,
      request: {
        method: 'bch_getAddresses',
        params: {},
      },
    });

    // Response format varies by wallet. Normalize to array.
    if (Array.isArray(result)) return result;
    if (result?.addresses && Array.isArray(result.addresses)) return result.addresses;
    return [];
  } catch {
    // Wallet may not support bch_getAddresses — return empty
    return [];
  }
}

/**
 * Broadcast a raw transaction via Fulcrum Electrum WebSocket.
 * Handles the required server.version negotiation before broadcasting.
 */
function broadcastViaElectrum(txHex: string, server: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(server);
    let reqId = 0;
    const timeout = setTimeout(() => {
      ws.close();
      reject(new Error(`Timeout connecting to ${server}`));
    }, 15000);

    ws.onopen = () => {
      // Fulcrum requires server.version negotiation first
      ws.send(JSON.stringify({
        jsonrpc: '2.0',
        method: 'server.version',
        params: ['Qubes', '1.4'],
        id: ++reqId,
      }));
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.id === 1) {
          // Version negotiation done, now broadcast
          ws.send(JSON.stringify({
            jsonrpc: '2.0',
            method: 'blockchain.transaction.broadcast',
            params: [txHex],
            id: ++reqId,
          }));
        } else if (data.id === 2) {
          // Broadcast response
          clearTimeout(timeout);
          ws.close();
          if (data.error) {
            reject(new Error(data.error.message || JSON.stringify(data.error)));
          } else if (typeof data.result === 'string' && data.result.length === 64) {
            resolve(data.result);
          } else {
            // Fulcrum returns error string directly in result field on failure
            reject(new Error(String(data.result)));
          }
        }
      } catch (e) {
        clearTimeout(timeout);
        ws.close();
        reject(new Error(`Invalid response from ${server}`));
      }
    };

    ws.onerror = () => {
      clearTimeout(timeout);
      reject(new Error(`WebSocket error connecting to ${server}`));
    };
  });
}

/**
 * Broadcast a raw transaction to the BCH network.
 * Tries Fulcrum WebSocket servers, falls back to REST API.
 * Returns the txid on success, throws on failure with the exact network error.
 */
async function broadcastRawTransaction(txHex: string): Promise<string> {
  const electrumServers = [
    'wss://bch.imaginary.cash:50004',
    'wss://electroncash.de:60004',
  ];

  let lastError: Error | null = null;

  // Try Electrum WebSocket servers
  for (const server of electrumServers) {
    try {
      return await broadcastViaElectrum(txHex, server);
    } catch (e: any) {
      console.error(`[WC] Broadcast via ${server} failed:`, e.message);
      lastError = e;
      // If we got a script validation error, don't retry — the tx is invalid
      if (e.message?.includes('mandatory-script') || e.message?.includes('scriptpubkey')) {
        throw e;
      }
    }
  }

  // REST API fallback
  try {
    console.log('[WC] Trying REST API fallback...');
    const resp = await fetch('https://api.blockchair.com/bitcoin-cash/push/transaction', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ data: txHex }),
    });
    const data = await resp.json();
    if (!resp.ok || !data?.data?.transaction_hash) {
      throw new Error(data?.context?.error || data?.error || 'REST broadcast failed');
    }
    return data.data.transaction_hash;
  } catch (e: any) {
    console.error('[WC] REST broadcast failed:', e.message);
    // Return the more specific Electrum error if we have one
    if (lastError && !lastError.message?.includes('Timeout') && !lastError.message?.includes('WebSocket error')) {
      throw lastError;
    }
    throw e;
  }
}

/**
 * Parse libauth's extended JSON format.
 * Converts "<Uint8Array: 0x...>" strings to Uint8Array and "<bigint: ...n>" to BigInt.
 */
function parseExtendedJson(jsonString: string): any {
  const uint8ArrayRegex = /^<Uint8Array: 0x(?<hex>[0-9a-f]*)>$/u;
  const bigIntRegex = /^<bigint: (?<bigint>[0-9]*)n>$/;

  return JSON.parse(jsonString, (_key, value) => {
    if (typeof value === 'string') {
      const bigintMatch = value.match(bigIntRegex);
      if (bigintMatch?.groups?.bigint !== undefined) {
        return BigInt(bigintMatch.groups.bigint);
      }
      const uint8ArrayMatch = value.match(uint8ArrayRegex);
      if (uint8ArrayMatch?.groups?.hex !== undefined) {
        const hex = uint8ArrayMatch.groups.hex;
        const bytes = new Uint8Array(hex.length / 2);
        for (let i = 0; i < hex.length; i += 2) {
          bytes[i / 2] = parseInt(hex.substring(i, i + 2), 16);
        }
        return bytes;
      }
    }
    return value;
  });
}

/**
 * Validate the signed transaction against the original WC transaction.
 * Returns a diagnostic report showing any differences.
 */
async function validateSignedTransaction(
  signedTxHex: string,
  originalWcTransaction: any
): Promise<{ valid: boolean; report: string }> {
  try {
    const { decodeTransaction, hexToBin, binToHex } = await import('@bitauth/libauth');

    const signedBytes = hexToBin(signedTxHex);
    const decoded = decodeTransaction(signedBytes);
    if (typeof decoded === 'string') {
      return { valid: false, report: `Failed to decode signed tx: ${decoded}` };
    }

    const lines: string[] = [];
    lines.push(`Signed tx: ${signedTxHex.length / 2} bytes, ${decoded.inputs.length} inputs, ${decoded.outputs.length} outputs`);

    // Compare with original WC transaction outputs
    const origTx = originalWcTransaction.transaction;
    if (!origTx) {
      lines.push('WARNING: No original transaction for comparison');
      // Still report signed tx structure
      for (let i = 0; i < decoded.outputs.length; i++) {
        const out = decoded.outputs[i];
        lines.push(`Out${i}: lock=${binToHex(out.lockingBytecode).substring(0, 40)}... val=${out.valueSatoshis}`);
        if (out.token) {
          lines.push(`  token: cat=${binToHex(out.token.category).substring(0, 16)}... cap=${out.token.nft?.capability || 'ft'}`);
        }
      }
      return { valid: true, report: lines.join('\n') };
    }

    // Compare outputs
    const origOutputs = origTx.outputs;
    if (decoded.outputs.length !== origOutputs.length) {
      lines.push(`OUTPUT COUNT MISMATCH: signed=${decoded.outputs.length} orig=${origOutputs.length}`);
    }

    for (let i = 0; i < Math.max(decoded.outputs.length, origOutputs.length); i++) {
      const signed = decoded.outputs[i];
      const orig = origOutputs[i];

      if (!signed) { lines.push(`Out${i}: MISSING in signed tx`); continue; }
      if (!orig) { lines.push(`Out${i}: EXTRA in signed tx`); continue; }

      const sLock = binToHex(signed.lockingBytecode);
      const oLock = orig.lockingBytecode instanceof Uint8Array ? binToHex(orig.lockingBytecode) : String(orig.lockingBytecode);

      const lockMatch = sLock === oLock;
      const valMatch = signed.valueSatoshis === (typeof orig.valueSatoshis === 'bigint' ? orig.valueSatoshis : BigInt(orig.valueSatoshis));

      if (!lockMatch) {
        lines.push(`Out${i} LOCK MISMATCH: signed=${sLock.substring(0, 40)} orig=${oLock.substring(0, 40)}`);
      }
      if (!valMatch) {
        lines.push(`Out${i} VALUE MISMATCH: signed=${signed.valueSatoshis} orig=${orig.valueSatoshis}`);
      }

      // Compare token data
      const sToken = signed.token;
      const oToken = orig.token;
      if (sToken && oToken) {
        const sCat = binToHex(sToken.category);
        const oCat = oToken.category instanceof Uint8Array ? binToHex(oToken.category) : String(oToken.category);
        if (sCat !== oCat) {
          lines.push(`Out${i} TOKEN CAT MISMATCH: signed=${sCat} orig=${oCat}`);
        }
        const sCap = sToken.nft?.capability || 'none';
        const oCap = oToken.nft?.capability || 'none';
        if (sCap !== oCap) {
          lines.push(`Out${i} NFT CAP MISMATCH: signed=${sCap} orig=${oCap}`);
        }
        if (sToken.nft?.commitment && oToken.nft?.commitment) {
          const sComm = binToHex(sToken.nft.commitment);
          const oComm = oToken.nft.commitment instanceof Uint8Array ? binToHex(oToken.nft.commitment) : String(oToken.nft.commitment);
          if (sComm !== oComm) {
            lines.push(`Out${i} COMMITMENT MISMATCH: signed=${sComm} orig=${oComm}`);
          }
        }
      } else if (sToken && !oToken) {
        lines.push(`Out${i}: signed has token, orig does not`);
      } else if (!sToken && oToken) {
        lines.push(`Out${i}: signed MISSING token (orig has one)`);
      }

      if (lockMatch && valMatch) {
        lines.push(`Out${i}: OK (lock=${sLock.substring(0, 20)}... val=${signed.valueSatoshis})`);
      }
    }

    // Compare covenant input (input 0) unlocking bytecode
    if (decoded.inputs.length > 0 && origTx.inputs?.length > 0) {
      const signedUnlock = binToHex(decoded.inputs[0].unlockingBytecode);
      const origInput = origTx.inputs[0];
      const origUnlock = origInput.unlockingBytecode instanceof Uint8Array
        ? binToHex(origInput.unlockingBytecode)
        : String(origInput.unlockingBytecode);

      if (signedUnlock === origUnlock) {
        lines.push(`In0 (covenant): OK (${signedUnlock.length / 2} bytes)`);
      } else {
        lines.push(`In0 UNLOCK MISMATCH: signed=${signedUnlock.length / 2}B orig=${origUnlock.length / 2}B`);
        lines.push(`  signed: ${signedUnlock.substring(0, 60)}...`);
        lines.push(`  orig:   ${origUnlock.substring(0, 60)}...`);
      }
    }

    // Report P2PKH inputs
    for (let i = 1; i < decoded.inputs.length; i++) {
      const unlock = decoded.inputs[i].unlockingBytecode;
      lines.push(`In${i} (P2PKH): ${unlock.length} bytes ${unlock.length > 0 ? 'signed' : 'EMPTY!'}`);
    }

    const hasMismatch = lines.some(l => l.includes('MISMATCH') || l.includes('MISSING') || l.includes('EMPTY!'));
    return { valid: !hasMismatch, report: lines.join('\n') };
  } catch (e: any) {
    return { valid: false, report: `Validation error: ${e.message}` };
  }
}

/**
 * Send a transaction to the connected wallet for signing, then broadcast.
 *
 * The WC transaction uses broadcast: false so we get the signed tx back.
 * We then broadcast ourselves for better error reporting and diagnostics.
 *
 * @param wcTransaction - The stringified WC transaction object from mint-cli.ts
 * @returns The signed transaction hash (txid) and hex
 */
export async function signTransaction(
  wcTransaction: string
): Promise<WcSignResult> {
  if (!currentSession || !signClient) {
    throw new Error('No wallet connected');
  }

  // Parse the stringified WC transaction object
  const txObj = JSON.parse(wcTransaction);

  // Also parse with extended JSON to get proper Uint8Arrays for comparison
  let parsedWcObj: any = null;
  try {
    parsedWcObj = parseExtendedJson(wcTransaction);
  } catch {
    // If parsing fails, we'll skip validation
  }

  console.log('[WC] Sending transaction to wallet for signing (broadcast: false)...');

  const result: WcSignResult = await signClient.request({
    topic: currentSession.topic,
    chainId: BCH_CHAIN_ID,
    request: {
      method: 'bch_signTransaction',
      params: txObj,
    },
  });

  if (!result.signedTransaction) {
    throw new Error('Wallet did not return a signed transaction');
  }

  console.log('[WC] Signed tx received:', result.signedTransactionHash);

  // Save signed tx hex to localStorage for debugging
  try {
    localStorage.setItem('debug_signed_tx_hex', result.signedTransaction);
    localStorage.setItem('debug_signed_tx_time', new Date().toISOString());
  } catch { /* ignore */ }

  // Validate signed tx against original before broadcasting
  let validationReport = '';
  if (parsedWcObj) {
    const validation = await validateSignedTransaction(result.signedTransaction, parsedWcObj);
    validationReport = validation.report;
    console.log('[WC] Validation:', validationReport);
  }

  // Save signed tx to file for debugging (before broadcast attempt)
  try {
    const { writeTextFile, BaseDirectory } = await import('@tauri-apps/plugin-fs');
    await writeTextFile('signed-mint-tx.hex', result.signedTransaction, { baseDir: BaseDirectory.AppLocalData });
    console.log('[WC] Saved signed tx hex to AppLocalData/signed-mint-tx.hex');
  } catch {
    // Ignore file write errors
  }

  // Broadcast the signed transaction ourselves
  console.log('[WC] Broadcasting signed transaction...');
  try {
    const txid = await broadcastRawTransaction(result.signedTransaction);
    console.log('[WC] Broadcast successful! txid:', txid);
    return { signedTransaction: result.signedTransaction, signedTransactionHash: txid };
  } catch (broadcastError: any) {
    // Include validation report and full signed tx hex in the error for debugging
    const debugInfo = [
      `Broadcast error: ${broadcastError.message}`,
      '',
      'Transaction validation:',
      validationReport || '(no validation data)',
      '',
      `Full signed tx hex (${result.signedTransaction.length / 2} bytes):`,
      result.signedTransaction,
    ].join('\n');

    console.error('[WC] Broadcast failed with diagnostics:\n', debugInfo);
    throw new Error(`Transaction signed but broadcast failed:\n${debugInfo}`);
  }
}

/**
 * Sign an arbitrary message via bch_signMessage.
 * Returns base64-encoded signature (Electron Cash compatible).
 */
export async function signMessage(message: string, userPrompt?: string): Promise<string> {
  const client = await getClient();
  if (!currentSession) throw new Error('No active WalletConnect session');

  const result = await client.request({
    topic: currentSession.topic,
    chainId: BCH_CHAIN_ID,
    request: {
      method: 'bch_signMessage',
      params: { message, userPrompt },
    },
  });

  return result as string;
}

/**
 * Get token UTXOs held by the connected wallet (CashRPC).
 * Returns null if the wallet doesn't support this method.
 */
export async function getTokens(): Promise<Array<{
  txid: string;
  vout: number;
  satoshis: number;
  token: {
    amount: string;
    category: string;
    nft?: { capability: string; commitment: string };
  };
}> | null> {
  const client = await getClient();
  if (!currentSession) throw new Error('No active WalletConnect session');

  try {
    const result = await client.request({
      topic: currentSession.topic,
      chainId: BCH_CHAIN_ID,
      request: {
        method: 'bch_getTokens_V0',
        params: {},
      },
    });
    return result as any[];
  } catch {
    // Wallet doesn't support this method
    return null;
  }
}

/**
 * Get the BCH balance of the connected wallet (CashRPC).
 * Returns null if the wallet doesn't support this method.
 */
export async function getBalance(): Promise<{
  confirmed: number;
  unconfirmed?: number;
} | null> {
  const client = await getClient();
  if (!currentSession) throw new Error('No active WalletConnect session');

  try {
    const result = await client.request({
      topic: currentSession.topic,
      chainId: BCH_CHAIN_ID,
      request: {
        method: 'bch_getBalance_V0',
        params: {},
      },
    });
    return result as { confirmed: number; unconfirmed?: number };
  } catch {
    // Wallet doesn't support this method
    return null;
  }
}

/**
 * Get the wallet's change locking bytecode (CashRPC).
 * Useful for building transactions with proper change outputs.
 * Returns null if the wallet doesn't support this method.
 */
export async function getChangeLockingBytecode(): Promise<string | null> {
  const client = await getClient();
  if (!currentSession) throw new Error('No active WalletConnect session');

  try {
    const result = await client.request({
      topic: currentSession.topic,
      chainId: BCH_CHAIN_ID,
      request: {
        method: 'bch_getChangeLockingBytecode_V0',
        params: {},
      },
    });
    return result as string;
  } catch {
    // Wallet doesn't support this method
    return null;
  }
}
