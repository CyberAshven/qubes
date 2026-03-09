/**
 * WalletConnect v2 Service for BCH — Multi-Session
 *
 * Implements the wc2-bch-bcr spec (mainnet-pat) for connecting to
 * BCH wallets (Cashonize, Paytaca, Zapit, Electron Cash).
 *
 * Supports multiple simultaneous wallet sessions. Each session is
 * identified by its topic and tracked in a Map.
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

// ── Multi-Session State ───────────────────────────────────────────

let signClient: any | null = null;
const sessions: Map<string, WcSession> = new Map();

// Event listeners — notified with the full sessions array on any change
type Listener = (sessions: WcSession[]) => void;
const listeners: Set<Listener> = new Set();

function notifyListeners() {
  listeners.forEach((fn) => fn(Array.from(sessions.values())));
}

export function onSessionsChange(fn: Listener): () => void {
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

  // Restore ALL existing BCH sessions — clean up stale ones
  const allSessions = signClient.session.getAll();
  const bchSessions = allSessions.filter((s: any) =>
    Object.keys(s.namespaces).includes('bch')
  );

  for (const bchSession of bchSessions) {
    try {
      await signClient.ping({ topic: bchSession.topic });
      const address = extractAddress(bchSession);
      if (address) {
        sessions.set(bchSession.topic, { topic: bchSession.topic, address });
      }
    } catch {
      console.warn('[WC] Stale session detected, cleaning up:', bchSession.topic);
      try {
        await signClient.disconnect({
          topic: bchSession.topic,
          reason: { code: 6000, message: 'Stale session cleanup' },
        });
      } catch {
        signClient.session.delete(bchSession.topic, { code: 6000, message: 'Stale session cleanup' });
      }
    }
  }

  if (sessions.size > 0) {
    notifyListeners();
  }

  // Handle session delete (wallet disconnected) — match by topic
  signClient.on('session_delete', (event: any) => {
    const topic = event.topic;
    if (topic && sessions.has(topic)) {
      sessions.delete(topic);
      notifyListeners();
    }
  });

  // Handle addressesChanged events — update matching session
  signClient.on('session_event', (event: any) => {
    if (event.params?.event?.name === 'addressesChanged') {
      const topic = event.topic;
      const session = sessions.get(topic);
      if (!session) return;

      const newAddresses = event.params.event.data;
      if (Array.isArray(newAddresses) && newAddresses.length > 0) {
        const addr = typeof newAddresses[0] === 'string'
          ? newAddresses[0]
          : newAddresses[0]?.address;
        if (addr) {
          session.address = addr;
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

function getSessionOrThrow(topic?: string): WcSession {
  if (topic) {
    const session = sessions.get(topic);
    if (!session) throw new Error(`No session with topic ${topic}`);
    return session;
  }
  // Default to first session
  const first = sessions.values().next().value;
  if (!first) throw new Error('No wallet connected');
  return first;
}

// ── Public API ─────────────────────────────────────────────────────

/**
 * Eagerly initialize the WC SignClient and restore any existing sessions.
 * Called on app mount so the connection state is available immediately.
 */
export async function initClient(): Promise<void> {
  await getClient();
}

/**
 * Connect to a BCH wallet via WalletConnect.
 * Adds the new session to the sessions map (does NOT replace existing sessions).
 */
export async function connect(onUri?: (uri: string) => void): Promise<WcSession> {
  const client = await getClient();

  const { uri, approval } = await client.connect({
    requiredNamespaces: BCH_NAMESPACE,
  });

  if (!uri) throw new Error('Failed to generate WalletConnect URI');

  onUri?.(uri);

  const session = await approval();

  const address = extractAddress(session);
  if (!address) {
    throw new Error('Wallet did not provide a BCH address');
  }

  const wcSession: WcSession = { topic: session.topic, address };
  sessions.set(session.topic, wcSession);
  notifyListeners();
  return wcSession;
}

/**
 * Disconnect a specific session by topic, or all sessions if no topic given.
 */
export async function disconnectSession(topic: string): Promise<void> {
  if (!signClient) return;

  const session = sessions.get(topic);
  if (!session) return;

  try {
    await signClient.disconnect({
      topic,
      reason: { code: 6000, message: 'User disconnected' },
    });
  } catch {
    // Ignore disconnect errors
  }

  sessions.delete(topic);
  notifyListeners();
}

/**
 * Disconnect all sessions.
 */
export async function disconnectAll(): Promise<void> {
  const topics = Array.from(sessions.keys());
  for (const topic of topics) {
    await disconnectSession(topic);
  }
}

/**
 * Get all active sessions.
 */
export function getAllSessions(): WcSession[] {
  return Array.from(sessions.values());
}

/**
 * Get a session by its topic.
 */
export function getSessionByTopic(topic: string): WcSession | null {
  return sessions.get(topic) || null;
}

/**
 * Get the first session (backward compat).
 */
export function getSession(): WcSession | null {
  return sessions.values().next().value || null;
}

/**
 * Request addresses (and possibly public keys) from a specific session.
 */
export async function getAddresses(topic?: string): Promise<Array<{ address: string; publicKey?: string }>> {
  const session = getSessionOrThrow(topic);

  try {
    const result = await signClient.request({
      topic: session.topic,
      chainId: BCH_CHAIN_ID,
      request: {
        method: 'bch_getAddresses',
        params: {},
      },
    });

    if (Array.isArray(result)) return result;
    if (result?.addresses && Array.isArray(result.addresses)) return result.addresses;
    return [];
  } catch {
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
          ws.send(JSON.stringify({
            jsonrpc: '2.0',
            method: 'blockchain.transaction.broadcast',
            params: [txHex],
            id: ++reqId,
          }));
        } else if (data.id === 2) {
          clearTimeout(timeout);
          ws.close();
          if (data.error) {
            reject(new Error(data.error.message || JSON.stringify(data.error)));
          } else if (typeof data.result === 'string' && data.result.length === 64) {
            resolve(data.result);
          } else {
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
 */
async function broadcastRawTransaction(txHex: string): Promise<string> {
  const electrumServers = [
    'wss://bch.imaginary.cash:50004',
    'wss://electroncash.de:60004',
    'wss://bch.loping.net:50004',
    'wss://fulcrum.fountainhead.cash:50004',
  ];

  let lastError: Error | null = null;

  for (const server of electrumServers) {
    try {
      return await broadcastViaElectrum(txHex, server);
    } catch (e: any) {
      console.error(`[WC] Broadcast via ${server} failed:`, e.message);
      lastError = e;
      if (e.message?.includes('mandatory-script') || e.message?.includes('scriptpubkey')) {
        throw e;
      }
    }
  }

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
    if (lastError && !lastError.message?.includes('Timeout') && !lastError.message?.includes('WebSocket error')) {
      throw lastError;
    }
    throw e;
  }
}

/**
 * Parse libauth's extended JSON format.
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

    const origTx = originalWcTransaction.transaction;
    if (!origTx) {
      lines.push('WARNING: No original transaction for comparison');
      for (let i = 0; i < decoded.outputs.length; i++) {
        const out = decoded.outputs[i];
        lines.push(`Out${i}: lock=${binToHex(out.lockingBytecode).substring(0, 40)}... val=${out.valueSatoshis}`);
        if (out.token) {
          lines.push(`  token: cat=${binToHex(out.token.category).substring(0, 16)}... cap=${out.token.nft?.capability || 'ft'}`);
        }
      }
      return { valid: true, report: lines.join('\n') };
    }

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
 * Send a transaction to a specific wallet session for signing, then broadcast.
 *
 * @param wcTransaction - The stringified WC transaction object
 * @param topic - Optional session topic. Defaults to first session.
 */
export async function signTransaction(
  wcTransaction: string,
  topic?: string
): Promise<WcSignResult> {
  const session = getSessionOrThrow(topic);

  const txObj = JSON.parse(wcTransaction);

  let parsedWcObj: any = null;
  try {
    parsedWcObj = parseExtendedJson(wcTransaction);
  } catch {
    // If parsing fails, we'll skip validation
  }

  console.log(`[WC] Sending transaction to wallet (topic: ${session.topic.slice(0, 8)}...) for signing...`);

  const result: WcSignResult = await signClient.request({
    topic: session.topic,
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

  try {
    localStorage.setItem('debug_signed_tx_hex', result.signedTransaction);
    localStorage.setItem('debug_signed_tx_time', new Date().toISOString());
  } catch { /* ignore */ }

  let validationReport = '';
  if (parsedWcObj) {
    const validation = await validateSignedTransaction(result.signedTransaction, parsedWcObj);
    validationReport = validation.report;
    console.log('[WC] Validation:', validationReport);

    if (!validation.valid) {
      console.error('[WC] Transaction validation FAILED — not broadcasting');
      throw new Error(
        `Wallet returned a modified transaction — refusing to broadcast.\n\n` +
        `Validation report:\n${validationReport}`
      );
    }
  }

  try {
    const { writeTextFile, BaseDirectory } = await import('@tauri-apps/plugin-fs');
    await writeTextFile('signed-mint-tx.hex', result.signedTransaction, { baseDir: BaseDirectory.AppLocalData });
  } catch {
    // Ignore file write errors
  }

  console.log('[WC] Broadcasting signed transaction...');
  try {
    const txid = await broadcastRawTransaction(result.signedTransaction);
    console.log('[WC] Broadcast successful! txid:', txid);
    return { signedTransaction: result.signedTransaction, signedTransactionHash: txid };
  } catch (broadcastError: any) {
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
 */
export async function signMessage(message: string, userPrompt?: string, topic?: string): Promise<string> {
  const client = await getClient();
  const session = getSessionOrThrow(topic);

  const result = await client.request({
    topic: session.topic,
    chainId: BCH_CHAIN_ID,
    request: {
      method: 'bch_signMessage',
      params: { message, userPrompt },
    },
  });

  return result as string;
}

/**
 * Get token UTXOs held by a wallet session.
 */
export async function getTokens(topic?: string): Promise<Array<{
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
  const session = getSessionOrThrow(topic);

  try {
    const result = await client.request({
      topic: session.topic,
      chainId: BCH_CHAIN_ID,
      request: {
        method: 'bch_getTokens_V0',
        params: {},
      },
    });
    return result as any[];
  } catch {
    return null;
  }
}

/**
 * Get the BCH balance of a wallet session.
 */
export async function getBalance(topic?: string): Promise<{
  confirmed: number;
  unconfirmed?: number;
} | null> {
  const client = await getClient();
  const session = getSessionOrThrow(topic);

  try {
    const result = await client.request({
      topic: session.topic,
      chainId: BCH_CHAIN_ID,
      request: {
        method: 'bch_getBalance_V0',
        params: {},
      },
    });
    return result as { confirmed: number; unconfirmed?: number };
  } catch {
    return null;
  }
}

/**
 * Get the wallet's change locking bytecode.
 */
export async function getChangeLockingBytecode(topic?: string): Promise<string | null> {
  const client = await getClient();
  const session = getSessionOrThrow(topic);

  try {
    const result = await client.request({
      topic: session.topic,
      chainId: BCH_CHAIN_ID,
      request: {
        method: 'bch_getChangeLockingBytecode_V0',
        params: {},
      },
    });
    return result as string;
  } catch {
    return null;
  }
}
