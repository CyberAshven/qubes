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
    methods: ['bch_getAddresses', 'bch_signTransaction', 'bch_signMessage'],
    events: ['addressesChanged'],
  },
};

// ── Singleton State ────────────────────────────────────────────────

let signClient: any | null = null;
let modal: any | null = null;
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

/**
 * Get the WalletConnect project ID from environment.
 * Register at https://cloud.reown.com (free).
 */
function getProjectId(): string {
  const id = import.meta.env.VITE_WC_PROJECT_ID;
  if (!id) {
    throw new Error(
      'VITE_WC_PROJECT_ID not set. Register at https://cloud.reown.com'
    );
  }
  return id;
}

async function getClient() {
  if (signClient) return signClient;

  const projectId = getProjectId();

  // Dynamic imports — only load WC packages when actually needed
  const { default: SignClient } = await import('@walletconnect/sign-client');
  const { WalletConnectModal } = await import('@walletconnect/modal');

  signClient = await SignClient.init({
    projectId,
    metadata: {
      name: 'Qubes',
      description: 'Sovereign AI Agents on Bitcoin Cash',
      url: 'https://qube.cash',
      icons: ['https://qube.cash/icon.png'],
    },
  });

  modal = new WalletConnectModal({ projectId });

  // Restore existing session if any
  const sessions = signClient.session.getAll();
  const bchSession = sessions.find((s: any) =>
    Object.keys(s.namespaces).includes('bch')
  );

  if (bchSession) {
    const address = extractAddress(bchSession);
    if (address) {
      currentSession = { topic: bchSession.topic, address };
      notifyListeners();
    }
  }

  // Handle session delete (wallet disconnected)
  signClient.on('session_delete', () => {
    currentSession = null;
    notifyListeners();
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
 * Connect to a BCH wallet via WalletConnect QR code.
 * Opens the WC modal for the user to scan.
 */
export async function connect(): Promise<WcSession> {
  const client = await getClient();

  const { uri, approval } = await client.connect({
    requiredNamespaces: BCH_NAMESPACE,
  });

  if (!uri) throw new Error('Failed to generate WalletConnect URI');

  // Show QR modal
  modal!.openModal({ uri });

  try {
    const session = await approval();
    modal!.closeModal();

    const address = extractAddress(session);
    if (!address) {
      throw new Error('Wallet did not provide a BCH address');
    }

    currentSession = { topic: session.topic, address };
    notifyListeners();
    return currentSession;
  } catch (e) {
    modal!.closeModal();
    throw e;
  }
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
 * Send a transaction to the connected wallet for signing.
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
  // This comes from libauth's stringify() via mint-cli.ts
  const txObj = JSON.parse(wcTransaction);

  const result: WcSignResult = await signClient.request({
    topic: currentSession.topic,
    chainId: BCH_CHAIN_ID,
    request: {
      method: 'bch_signTransaction',
      params: txObj,
    },
  });

  return result;
}
