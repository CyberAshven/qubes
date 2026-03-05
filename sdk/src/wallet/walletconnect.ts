/**
 * WalletConnect v2 + CashRPC protocol definitions for Bitcoin Cash.
 *
 * Merges Pat's wc2-bch-bcr specification (bch_getAddresses, bch_signTransaction,
 * bch_signMessage) with Jim's CashRPC utility methods (bch_getTokens,
 * bch_getBalance, bch_getChangeLockingBytecode).
 *
 * WalletConnect v2 serves as the transport layer. CashRPC methods provide
 * richer wallet state queries.
 *
 * @see https://github.com/mainnet-pat/wc2-bch-bcr
 * @see https://bitcoincashresearch.org/t/cashrpc-protocol-to-attempt-to-unify-wallet-app-comms/1201
 *
 * @module wallet/walletconnect
 */

// ---------------------------------------------------------------------------
// Chain IDs (CAIP-2 format)
// ---------------------------------------------------------------------------

export const BCH_CHAINS = {
  mainnet: 'bch:bitcoincash',
  testnet: 'bch:bchtest',
  regtest: 'bch:bchreg',
} as const;

export type BchChainId = typeof BCH_CHAINS[keyof typeof BCH_CHAINS];

// ---------------------------------------------------------------------------
// Method names — Pat's wc2-bch-bcr spec
// ---------------------------------------------------------------------------

export const WC_METHODS = {
  /** Get wallet addresses (and optionally public keys) */
  getAddresses: 'bch_getAddresses',
  /** Sign a transaction (with optional broadcast) */
  signTransaction: 'bch_signTransaction',
  /** Sign an arbitrary message (Electron Cash compatible) */
  signMessage: 'bch_signMessage',
} as const;

// ---------------------------------------------------------------------------
// Method names — Jim's CashRPC extensions
// ---------------------------------------------------------------------------

export const CASHRPC_METHODS = {
  /** Get token UTXOs held by the wallet */
  getTokens: 'bch_getTokens_V0',
  /** Get wallet BCH balance in satoshis */
  getBalance: 'bch_getBalance_V0',
  /** Get the wallet's change locking bytecode */
  getChangeLockingBytecode: 'bch_getChangeLockingBytecode_V0',
} as const;

// ---------------------------------------------------------------------------
// All methods combined
// ---------------------------------------------------------------------------

export const ALL_METHODS = {
  ...WC_METHODS,
  ...CASHRPC_METHODS,
} as const;

// ---------------------------------------------------------------------------
// WC Events
// ---------------------------------------------------------------------------

export const WC_EVENTS = {
  addressesChanged: 'addressesChanged',
} as const;

// ---------------------------------------------------------------------------
// Namespace builder
// ---------------------------------------------------------------------------

export interface BchNamespaceConfig {
  chains?: BchChainId[];
  methods?: string[];
  events?: string[];
}

/**
 * Build the WalletConnect v2 `requiredNamespaces` object for BCH.
 *
 * By default includes all Pat + CashRPC methods and the addressesChanged event.
 * Pass options to customize.
 */
export function buildBchNamespace(config?: BchNamespaceConfig) {
  return {
    bch: {
      chains: config?.chains ?? [BCH_CHAINS.mainnet],
      methods: config?.methods ?? [
        WC_METHODS.getAddresses,
        WC_METHODS.signTransaction,
        WC_METHODS.signMessage,
        CASHRPC_METHODS.getTokens,
        CASHRPC_METHODS.getBalance,
        CASHRPC_METHODS.getChangeLockingBytecode,
      ],
      events: config?.events ?? [WC_EVENTS.addressesChanged],
    },
  };
}

// ---------------------------------------------------------------------------
// Request / Response types — bch_getAddresses
// ---------------------------------------------------------------------------

export interface GetAddressesRequest {
  method: typeof WC_METHODS.getAddresses;
  params: Record<string, never>;
}

export interface WalletAddress {
  address: string;
  publicKey?: string;
  tokenAddress?: string;
}

// Response can be WalletAddress[] or string[] depending on wallet
export type GetAddressesResponse = WalletAddress[] | string[];

// ---------------------------------------------------------------------------
// Request / Response types — bch_signTransaction
// ---------------------------------------------------------------------------

export interface SignTransactionRequest {
  method: typeof WC_METHODS.signTransaction;
  params: SignTransactionParams;
}

export interface SignTransactionParams {
  /** Libauth-serialized transaction object or hex string */
  transaction: Record<string, unknown> | string;
  /** Source outputs with optional contract metadata */
  sourceOutputs?: SourceOutput[];
  /** Whether the wallet should broadcast after signing (default: true) */
  broadcast?: boolean;
  /** User-facing prompt shown in the wallet UI */
  userPrompt?: string;
}

export interface SourceOutput {
  outpointIndex: number;
  outpointTransactionHash: string;
  sequenceNumber: number;
  unlockingBytecode: string;
  lockingBytecode: string;
  valueSatoshis: string | number;
  token?: TokenData;
  contract?: ContractMetadata;
}

export interface TokenData {
  amount: string | number;
  category: string;
  nft?: {
    capability: 'none' | 'mutable' | 'minting';
    commitment: string;
  };
}

export interface ContractMetadata {
  abiFunction: Record<string, unknown>;
  redeemScript: string;
  artifact: Record<string, unknown>;
}

export interface SignTransactionResponse {
  signedTransaction: string;
  signedTransactionHash: string;
}

// ---------------------------------------------------------------------------
// Request / Response types — bch_signMessage
// ---------------------------------------------------------------------------

export interface SignMessageRequest {
  method: typeof WC_METHODS.signMessage;
  params: SignMessageParams;
}

export interface SignMessageParams {
  message: string;
  userPrompt?: string;
}

/** Base64-encoded signature (Electron Cash compatible) */
export type SignMessageResponse = string;

// ---------------------------------------------------------------------------
// Request / Response types — CashRPC: bch_getTokens_V0
// ---------------------------------------------------------------------------

export interface GetTokensRequest {
  method: typeof CASHRPC_METHODS.getTokens;
  params: Record<string, never>;
}

export interface TokenUtxo {
  txid: string;
  vout: number;
  satoshis: number;
  token: {
    amount: string;
    category: string;
    nft?: {
      capability: 'none' | 'mutable' | 'minting';
      commitment: string;
    };
  };
}

export type GetTokensResponse = TokenUtxo[];

// ---------------------------------------------------------------------------
// Request / Response types — CashRPC: bch_getBalance_V0
// ---------------------------------------------------------------------------

export interface GetBalanceRequest {
  method: typeof CASHRPC_METHODS.getBalance;
  params: Record<string, never>;
}

/** Balance in satoshis */
export interface GetBalanceResponse {
  /** Total confirmed balance in satoshis */
  confirmed: number;
  /** Unconfirmed balance in satoshis */
  unconfirmed?: number;
}

// ---------------------------------------------------------------------------
// Request / Response types — CashRPC: bch_getChangeLockingBytecode_V0
// ---------------------------------------------------------------------------

export interface GetChangeLockingBytecodeRequest {
  method: typeof CASHRPC_METHODS.getChangeLockingBytecode;
  params: Record<string, never>;
}

/** Hex-encoded locking bytecode for the wallet's change address */
export type GetChangeLockingBytecodeResponse = string;

// ---------------------------------------------------------------------------
// Union types for all requests/responses
// ---------------------------------------------------------------------------

export type BchRpcRequest =
  | GetAddressesRequest
  | SignTransactionRequest
  | SignMessageRequest
  | GetTokensRequest
  | GetBalanceRequest
  | GetChangeLockingBytecodeRequest;

export type BchRpcResponse =
  | GetAddressesResponse
  | SignTransactionResponse
  | SignMessageResponse
  | GetTokensResponse
  | GetBalanceResponse
  | GetChangeLockingBytecodeResponse;

// ---------------------------------------------------------------------------
// Helper: normalize getAddresses response
// ---------------------------------------------------------------------------

/**
 * Normalize the variable response formats from different wallets'
 * `bch_getAddresses` into a consistent WalletAddress array.
 *
 * Some wallets return `string[]`, others `WalletAddress[]`, others
 * `{ addresses: [...] }`.
 */
export function normalizeAddresses(response: unknown): WalletAddress[] {
  // Handle { addresses: [...] } wrapper
  if (response && typeof response === 'object' && !Array.isArray(response)) {
    const obj = response as Record<string, unknown>;
    if (Array.isArray(obj.addresses)) {
      return normalizeAddresses(obj.addresses);
    }
  }

  if (!Array.isArray(response)) return [];

  return response.map((entry) => {
    if (typeof entry === 'string') {
      return { address: entry };
    }
    if (entry && typeof entry === 'object') {
      return {
        address: String((entry as Record<string, unknown>).address ?? ''),
        publicKey: (entry as Record<string, unknown>).publicKey as string | undefined,
        tokenAddress: (entry as Record<string, unknown>).tokenAddress as string | undefined,
      };
    }
    return { address: '' };
  }).filter((a) => a.address.length > 0);
}

// ---------------------------------------------------------------------------
// Helper: check if wallet supports a specific method
// ---------------------------------------------------------------------------

/**
 * Check if a WC session's approved methods include a specific method.
 *
 * @param sessionNamespaces - The `session.namespaces` from an approved WC session.
 * @param method - The method name to check.
 */
export function sessionSupportsMethod(
  sessionNamespaces: Record<string, { methods?: string[] }>,
  method: string,
): boolean {
  const bchNs = sessionNamespaces['bch'];
  if (!bchNs?.methods) return false;
  return bchNs.methods.includes(method);
}
