/**
 * NFT ownership verification via Chaingraph GraphQL.
 *
 * This module is **browser-compatible** — it only uses `fetch()` and the
 * SDK's own CashAddr decoder (no Node.js dependencies).
 *
 * @module covenant/verify
 */

import { decodeCashAddr } from '../wallet/cashaddr.js';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** Default Chaingraph GraphQL endpoint. */
const DEFAULT_CHAINGRAPH_URL = 'https://gql.chaingraph.pat.mn/v1/graphql';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Details of a verified NFT. */
export interface NFTDetails {
  categoryId: string;
  ownerAddress: string;
  valueSatoshis: number;
  nftCommitment: string;
  nftCapability: string;
  transactionHash: string;
  outputIndex: number;
  totalUtxos: number;
}

// ---------------------------------------------------------------------------
// Address → locking bytecode
// ---------------------------------------------------------------------------

/**
 * Convert a CashAddr address to its locking bytecode hex representation.
 *
 * Supports:
 * - P2PKH (version byte bit 3 == 0): `OP_DUP OP_HASH160 <hash> OP_EQUALVERIFY OP_CHECKSIG`
 * - P2SH-20 (version byte == 0x08): `OP_HASH160 <20-byte hash> OP_EQUAL`
 * - P2SH-32 (version byte == 0x0b): `OP_HASH256 <32-byte hash> OP_EQUAL`  (VM limits variant)
 *
 * Note: CashAddr version byte encoding:
 *   - Bits 7-4: reserved (0)
 *   - Bit 3: address type (0 = P2PKH, 1 = P2SH)
 *   - Bits 2-0: hash size (0 = 160-bit, 3 = 256-bit, etc.)
 *
 * @param address - CashAddr string (with or without prefix).
 * @returns Locking bytecode hex, or `null` if address cannot be decoded.
 */
export function addressToLockingBytecodeHex(address: string): string | null {
  try {
    const { version, hash } = decodeCashAddr(address);
    const hashHex = bytesToHex(hash);

    const isP2SH = (version & 0x08) !== 0;

    if (isP2SH) {
      if (hash.length === 20) {
        // P2SH-20:  OP_HASH160 OP_PUSHBYTES_20 <hash> OP_EQUAL
        return 'a914' + hashHex + '87';
      }
      if (hash.length === 32) {
        // P2SH-32:  OP_HASH256 OP_PUSHBYTES_32 <hash> OP_EQUAL
        return 'aa20' + hashHex + '87';
      }
      // Unknown P2SH variant
      return null;
    }

    // P2PKH:  OP_DUP OP_HASH160 OP_PUSHBYTES_20 <hash> OP_EQUALVERIFY OP_CHECKSIG
    if (hash.length === 20) {
      return '76a914' + hashHex + '88ac';
    }

    return null;
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// Hex helpers
// ---------------------------------------------------------------------------

function bytesToHex(bytes: Uint8Array): string {
  let hex = '';
  for (let i = 0; i < bytes.length; i++) {
    hex += bytes[i].toString(16).padStart(2, '0');
  }
  return hex;
}

// ---------------------------------------------------------------------------
// GraphQL queries
// ---------------------------------------------------------------------------

const OWNERSHIP_QUERY = `
query GetTokenOwnership($category: bytea!, $locking_bytecode: bytea!) {
  output(where: {
    token_category: {_eq: $category}
    locking_bytecode: {_eq: $locking_bytecode}
    _not: {spent_by: {}}
  }) {
    value_satoshis
    token_category
    fungible_token_amount
    nonfungible_token_capability
    nonfungible_token_commitment
    transaction_hash
    output_index
  }
}
`;

const LIST_BY_CATEGORY_QUERY = `
query GetAllNFTs($category: bytea!, $limit: Int!) {
  output(
    where: {
      token_category: {_eq: $category}
      _not: {spent_by: {}}
    }
    limit: $limit
  ) {
    value_satoshis
    token_category
    fungible_token_amount
    nonfungible_token_capability
    nonfungible_token_commitment
    transaction_hash
    output_index
    locking_bytecode
  }
}
`;

// ---------------------------------------------------------------------------
// Internal: Chaingraph fetch
// ---------------------------------------------------------------------------

async function queryChaingraph(
  query: string,
  variables: Record<string, unknown>,
  chaingraphUrl: string,
): Promise<any[]> {
  const resp = await fetch(chaingraphUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, variables }),
  });

  if (!resp.ok) {
    throw new Error(`Chaingraph request failed with status ${resp.status}`);
  }

  const data = await resp.json();

  if (data.errors) {
    throw new Error(`Chaingraph query error: ${JSON.stringify(data.errors)}`);
  }

  return data?.data?.output ?? [];
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Verify NFT ownership by querying Chaingraph for unspent outputs.
 *
 * Browser-compatible (uses `fetch()`).
 *
 * @param categoryId    - CashToken category ID (hex).
 * @param ownerAddress  - Owner's CashAddr.
 * @param chaingraphUrl - Chaingraph endpoint. Default: `gql.chaingraph.pat.mn`.
 * @returns `true` if the owner holds at least one NFT with this category.
 *
 * @example
 * ```ts
 * import { verifyNftOwnership, OFFICIAL_CATEGORY } from '@qubesai/sdk/covenant';
 *
 * const owns = await verifyNftOwnership(OFFICIAL_CATEGORY, 'bitcoincash:qr...');
 * ```
 */
export async function verifyNftOwnership(
  categoryId: string,
  ownerAddress: string,
  chaingraphUrl: string = DEFAULT_CHAINGRAPH_URL,
): Promise<boolean> {
  const lockingBytecode = addressToLockingBytecodeHex(ownerAddress);
  if (!lockingBytecode) return false;

  const outputs = await queryChaingraph(
    OWNERSHIP_QUERY,
    {
      category: `\\x${categoryId}`,
      locking_bytecode: `\\x${lockingBytecode}`,
    },
    chaingraphUrl,
  );

  return outputs.length > 0;
}

/**
 * Get detailed NFT information for a specific owner and category.
 *
 * Browser-compatible (uses `fetch()`).
 *
 * @param categoryId    - CashToken category ID (hex).
 * @param ownerAddress  - Owner's CashAddr.
 * @param chaingraphUrl - Chaingraph endpoint. Default: `gql.chaingraph.pat.mn`.
 * @returns NFT details or `null` if no matching NFT is found.
 */
export async function getNftDetails(
  categoryId: string,
  ownerAddress: string,
  chaingraphUrl: string = DEFAULT_CHAINGRAPH_URL,
): Promise<NFTDetails | null> {
  const lockingBytecode = addressToLockingBytecodeHex(ownerAddress);
  if (!lockingBytecode) return null;

  const outputs = await queryChaingraph(
    OWNERSHIP_QUERY,
    {
      category: `\\x${categoryId}`,
      locking_bytecode: `\\x${lockingBytecode}`,
    },
    chaingraphUrl,
  );

  if (outputs.length === 0) return null;

  const output = outputs[0];
  return {
    categoryId,
    ownerAddress,
    valueSatoshis: typeof output.value_satoshis === 'string'
      ? parseInt(output.value_satoshis, 10)
      : Number(output.value_satoshis),
    nftCommitment: output.nonfungible_token_commitment ?? '',
    nftCapability: output.nonfungible_token_capability ?? '',
    transactionHash: output.transaction_hash ?? '',
    outputIndex: typeof output.output_index === 'string'
      ? parseInt(output.output_index, 10)
      : Number(output.output_index ?? 0),
    totalUtxos: outputs.length,
  };
}

/**
 * List all NFTs for a given category.
 *
 * Browser-compatible (uses `fetch()`).
 *
 * @param categoryId    - CashToken category ID (hex).
 * @param limit         - Maximum number of results. Default: 100.
 * @param chaingraphUrl - Chaingraph endpoint.
 * @returns Array of raw output records from Chaingraph.
 */
export async function listNftsByCategory(
  categoryId: string,
  limit: number = 100,
  chaingraphUrl: string = DEFAULT_CHAINGRAPH_URL,
): Promise<Array<Record<string, unknown>>> {
  return queryChaingraph(
    LIST_BY_CATEGORY_QUERY,
    {
      category: `\\x${categoryId}`,
      limit,
    },
    chaingraphUrl,
  );
}
