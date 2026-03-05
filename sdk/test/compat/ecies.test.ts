/**
 * Cross-compatibility test: ECIES encrypt/decrypt
 */
import { describe, it, expect } from 'vitest';
import { eciesEncrypt, eciesDecrypt } from '../../src/crypto/ecies.js';
import {
  getPublicKey,
  privateKeyFromHex,
  generateKeyPair,
} from '../../src/crypto/keys.js';
import vectors from './vectors.json';

/** Convert hex string to Uint8Array */
function fromHex(hex: string): Uint8Array {
  const len = hex.length >>> 1;
  const bytes = new Uint8Array(len);
  for (let i = 0; i < len; i++) {
    bytes[i] = parseInt(hex.substring(i * 2, i * 2 + 2), 16);
  }
  return bytes;
}

/** Convert Uint8Array to hex string */
function toHex(bytes: Uint8Array): string {
  let hex = '';
  for (let i = 0; i < bytes.length; i++) {
    hex += bytes[i].toString(16).padStart(2, '0');
  }
  return hex;
}

describe('ECIES ↔ Python ecies_encrypt / ecies_decrypt', () => {
  const recipientPrivateKey = privateKeyFromHex(vectors.ecies.recipientPrivateKeyHex);
  const recipientPublicKey = getPublicKey(recipientPrivateKey);

  it('can decrypt Python-generated ECIES ciphertext', async () => {
    const ciphertext = fromHex(vectors.ecies.ciphertextHex);
    const decrypted = await eciesDecrypt(ciphertext, recipientPrivateKey);
    const decryptedText = new TextDecoder().decode(decrypted);
    expect(decryptedText).toBe(vectors.ecies.plaintext);
  });

  it('encrypt → decrypt round-trip', async () => {
    const plaintext = new TextEncoder().encode('test message for ECIES round-trip');
    const ciphertext = await eciesEncrypt(plaintext, recipientPublicKey);

    // Verify format: ephemeralPubKey(33) + nonce(12) + ciphertext + tag(16)
    expect(ciphertext.length).toBe(33 + 12 + plaintext.length + 16);

    // Verify ephemeral pubkey starts with 02 or 03
    expect(ciphertext[0] === 0x02 || ciphertext[0] === 0x03).toBe(true);

    const decrypted = await eciesDecrypt(ciphertext, recipientPrivateKey);
    expect(new TextDecoder().decode(decrypted)).toBe('test message for ECIES round-trip');
  });

  it('wrong private key fails decryption', async () => {
    const plaintext = new TextEncoder().encode('secret');
    const ciphertext = await eciesEncrypt(plaintext, recipientPublicKey);

    const { privateKey: wrongKey } = generateKeyPair();
    await expect(eciesDecrypt(ciphertext, wrongKey)).rejects.toThrow();
  });

  it('ciphertext too short throws', async () => {
    const shortData = new Uint8Array(10);
    await expect(eciesDecrypt(shortData, recipientPrivateKey)).rejects.toThrow(
      /too short/,
    );
  });
});
