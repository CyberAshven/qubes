/**
 * Tests for the storage module — StorageError, PinataAdapter, getGatewayUrl,
 * downloadFromIpfs, and DEFAULT_GATEWAYS.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { StorageError } from '../../src/storage/adapter.js';
import { PinataAdapter } from '../../src/storage/pinata.js';
import { getGatewayUrl, downloadFromIpfs, DEFAULT_GATEWAYS } from '../../src/storage/download.js';

// ---------------------------------------------------------------------------
// StorageError
// ---------------------------------------------------------------------------

describe('StorageError', () => {
  it('has the correct name', () => {
    const err = new StorageError('something went wrong');
    expect(err.name).toBe('StorageError');
  });

  it('stores the message', () => {
    const err = new StorageError('Invalid Pinata JWT');
    expect(err.message).toBe('Invalid Pinata JWT');
  });

  it('is an instance of Error', () => {
    const err = new StorageError('boom');
    expect(err).toBeInstanceOf(Error);
  });

  it('stores the optional code when provided', () => {
    const err = new StorageError('auth failed', 'AUTH_FAILED');
    expect(err.code).toBe('AUTH_FAILED');
  });

  it('leaves code undefined when not provided', () => {
    const err = new StorageError('no code here');
    expect(err.code).toBeUndefined();
  });
});

// ---------------------------------------------------------------------------
// PinataAdapter constructor
// ---------------------------------------------------------------------------

describe('PinataAdapter constructor', () => {
  it('stores the JWT', () => {
    const adapter = new PinataAdapter({ jwt: 'test-jwt-token' });
    // Access the private field via casting to verify storage.
    const internal = adapter as unknown as { jwt: string };
    expect(internal.jwt).toBe('test-jwt-token');
  });

  it('uses the default gateway when none is provided', () => {
    const adapter = new PinataAdapter({ jwt: 'tok' });
    const internal = adapter as unknown as { gateway: string };
    expect(internal.gateway).toBe('https://gateway.pinata.cloud');
  });

  it('uses the custom gateway when provided', () => {
    const adapter = new PinataAdapter({
      jwt: 'tok',
      gateway: 'https://my-custom-gateway.example.com',
    });
    const internal = adapter as unknown as { gateway: string };
    expect(internal.gateway).toBe('https://my-custom-gateway.example.com');
  });

  it('strips a trailing slash from the custom gateway', () => {
    const adapter = new PinataAdapter({
      jwt: 'tok',
      gateway: 'https://my-custom-gateway.example.com/',
    });
    const internal = adapter as unknown as { gateway: string };
    expect(internal.gateway).toBe('https://my-custom-gateway.example.com');
  });
});

// ---------------------------------------------------------------------------
// getGatewayUrl
// ---------------------------------------------------------------------------

describe('getGatewayUrl', () => {
  it('converts an ipfs:// URI to a gateway URL', () => {
    const url = getGatewayUrl('ipfs://QmFooBarBaz');
    expect(url).toBe('https://ipfs.io/ipfs/QmFooBarBaz');
  });

  it('handles a bare CID with no ipfs:// prefix', () => {
    const url = getGatewayUrl('QmFooBarBaz');
    expect(url).toBe('https://ipfs.io/ipfs/QmFooBarBaz');
  });

  it('uses the default gateway (ipfs.io) when no gateway is supplied', () => {
    const url = getGatewayUrl('ipfs://QmTest');
    expect(url).toContain('https://ipfs.io');
  });

  it('uses a custom gateway when provided', () => {
    const url = getGatewayUrl('ipfs://QmTest', 'https://gateway.pinata.cloud');
    expect(url).toBe('https://gateway.pinata.cloud/ipfs/QmTest');
  });

  it('strips a trailing slash from the gateway base URL', () => {
    const url = getGatewayUrl('QmAbc', 'https://cloudflare-ipfs.com/');
    expect(url).toBe('https://cloudflare-ipfs.com/ipfs/QmAbc');
  });
});

// ---------------------------------------------------------------------------
// downloadFromIpfs (mocked fetch)
// ---------------------------------------------------------------------------

describe('downloadFromIpfs', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('returns bytes from the first gateway on success', async () => {
    const mockBytes = new Uint8Array([1, 2, 3, 4]);
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      arrayBuffer: () => Promise.resolve(mockBytes.buffer),
    });
    vi.stubGlobal('fetch', mockFetch);

    const result = await downloadFromIpfs('QmSuccess', [
      'https://gateway.pinata.cloud',
      'https://ipfs.io',
    ]);

    expect(result).toEqual(mockBytes);
    // Only one fetch call should have been made.
    expect(mockFetch).toHaveBeenCalledTimes(1);
    expect(mockFetch).toHaveBeenCalledWith(
      'https://gateway.pinata.cloud/ipfs/QmSuccess',
    );
  });

  it('falls back to the second gateway when the first fails', async () => {
    const mockBytes = new Uint8Array([9, 8, 7]);
    const mockFetch = vi.fn()
      .mockResolvedValueOnce({ ok: false, arrayBuffer: () => Promise.resolve(new ArrayBuffer(0)) })
      .mockResolvedValueOnce({
        ok: true,
        arrayBuffer: () => Promise.resolve(mockBytes.buffer),
      });
    vi.stubGlobal('fetch', mockFetch);

    const result = await downloadFromIpfs('QmFallback', [
      'https://gateway.pinata.cloud',
      'https://ipfs.io',
    ]);

    expect(result).toEqual(mockBytes);
    expect(mockFetch).toHaveBeenCalledTimes(2);
    expect(mockFetch).toHaveBeenNthCalledWith(
      1,
      'https://gateway.pinata.cloud/ipfs/QmFallback',
    );
    expect(mockFetch).toHaveBeenNthCalledWith(
      2,
      'https://ipfs.io/ipfs/QmFallback',
    );
  });

  it('also falls back when the first gateway throws a network error', async () => {
    const mockBytes = new Uint8Array([5, 6]);
    const mockFetch = vi.fn()
      .mockRejectedValueOnce(new Error('Network error'))
      .mockResolvedValueOnce({
        ok: true,
        arrayBuffer: () => Promise.resolve(mockBytes.buffer),
      });
    vi.stubGlobal('fetch', mockFetch);

    const result = await downloadFromIpfs('QmNetErr', [
      'https://gateway.pinata.cloud',
      'https://ipfs.io',
    ]);

    expect(result).toEqual(mockBytes);
    expect(mockFetch).toHaveBeenCalledTimes(2);
  });

  it('throws StorageError with ALL_GATEWAYS_FAILED when every gateway fails', async () => {
    const mockFetch = vi.fn().mockResolvedValue({ ok: false });
    vi.stubGlobal('fetch', mockFetch);

    await expect(
      downloadFromIpfs('QmAllFail', [
        'https://gateway.pinata.cloud',
        'https://ipfs.io',
      ]),
    ).rejects.toThrow(StorageError);

    await expect(
      downloadFromIpfs('QmAllFail', [
        'https://gateway.pinata.cloud',
        'https://ipfs.io',
      ]),
    ).rejects.toMatchObject({ code: 'ALL_GATEWAYS_FAILED' });
  });

  it('includes the attempted URLs in the error message', async () => {
    const mockFetch = vi.fn().mockResolvedValue({ ok: false });
    vi.stubGlobal('fetch', mockFetch);

    let caught: StorageError | undefined;
    try {
      await downloadFromIpfs('QmMsg', [
        'https://gateway.pinata.cloud',
        'https://ipfs.io',
      ]);
    } catch (e) {
      caught = e as StorageError;
    }

    expect(caught).toBeDefined();
    expect(caught!.message).toContain('https://gateway.pinata.cloud/ipfs/QmMsg');
    expect(caught!.message).toContain('https://ipfs.io/ipfs/QmMsg');
  });
});

// ---------------------------------------------------------------------------
// DEFAULT_GATEWAYS
// ---------------------------------------------------------------------------

describe('DEFAULT_GATEWAYS', () => {
  it('has exactly 4 entries', () => {
    expect(DEFAULT_GATEWAYS).toHaveLength(4);
  });

  it('contains gateway.pinata.cloud', () => {
    expect(DEFAULT_GATEWAYS).toContain('https://gateway.pinata.cloud');
  });

  it('contains ipfs.io', () => {
    expect(DEFAULT_GATEWAYS).toContain('https://ipfs.io');
  });

  it('contains cloudflare-ipfs.com', () => {
    expect(DEFAULT_GATEWAYS).toContain('https://cloudflare-ipfs.com');
  });

  it('contains dweb.link', () => {
    expect(DEFAULT_GATEWAYS).toContain('https://dweb.link');
  });
});
