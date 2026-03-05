import { describe, it, expect } from 'vitest';
import {
  BCH_CHAINS,
  WC_METHODS,
  CASHRPC_METHODS,
  ALL_METHODS,
  WC_EVENTS,
  buildBchNamespace,
  normalizeAddresses,
  sessionSupportsMethod,
  BchNamespaceConfig,
  WalletAddress,
} from '../../src/wallet/walletconnect';

// ---------------------------------------------------------------------------
// Constants Tests
// ---------------------------------------------------------------------------

describe('Constants', () => {
  describe('BCH_CHAINS', () => {
    it('should have mainnet chain', () => {
      expect(BCH_CHAINS.mainnet).toBe('bch:bitcoincash');
    });

    it('should have testnet chain', () => {
      expect(BCH_CHAINS.testnet).toBe('bch:bchtest');
    });

    it('should have regtest chain', () => {
      expect(BCH_CHAINS.regtest).toBe('bch:bchreg');
    });

    it('should have 3 chains total', () => {
      const chains = Object.entries(BCH_CHAINS);
      expect(chains).toHaveLength(3);
    });
  });

  describe('WC_METHODS', () => {
    it('should have getAddresses method', () => {
      expect(WC_METHODS.getAddresses).toBe('bch_getAddresses');
    });

    it('should have signTransaction method', () => {
      expect(WC_METHODS.signTransaction).toBe('bch_signTransaction');
    });

    it('should have signMessage method', () => {
      expect(WC_METHODS.signMessage).toBe('bch_signMessage');
    });

    it('should have 3 methods total', () => {
      expect(Object.keys(WC_METHODS)).toHaveLength(3);
    });
  });

  describe('CASHRPC_METHODS', () => {
    it('should have getTokens method', () => {
      expect(CASHRPC_METHODS.getTokens).toBe('bch_getTokens_V0');
    });

    it('should have getBalance method', () => {
      expect(CASHRPC_METHODS.getBalance).toBe('bch_getBalance_V0');
    });

    it('should have getChangeLockingBytecode method', () => {
      expect(CASHRPC_METHODS.getChangeLockingBytecode).toBe('bch_getChangeLockingBytecode_V0');
    });

    it('should have 3 methods total', () => {
      expect(Object.keys(CASHRPC_METHODS)).toHaveLength(3);
    });
  });

  describe('ALL_METHODS', () => {
    it('should include all WC_METHODS', () => {
      expect(ALL_METHODS).toHaveProperty('getAddresses', WC_METHODS.getAddresses);
      expect(ALL_METHODS).toHaveProperty('signTransaction', WC_METHODS.signTransaction);
      expect(ALL_METHODS).toHaveProperty('signMessage', WC_METHODS.signMessage);
    });

    it('should include all CASHRPC_METHODS', () => {
      expect(ALL_METHODS).toHaveProperty('getTokens', CASHRPC_METHODS.getTokens);
      expect(ALL_METHODS).toHaveProperty('getBalance', CASHRPC_METHODS.getBalance);
      expect(ALL_METHODS).toHaveProperty(
        'getChangeLockingBytecode',
        CASHRPC_METHODS.getChangeLockingBytecode,
      );
    });

    it('should be the union of WC_METHODS and CASHRPC_METHODS', () => {
      expect(Object.keys(ALL_METHODS)).toHaveLength(6);
    });
  });

  describe('WC_EVENTS', () => {
    it('should have addressesChanged event', () => {
      expect(WC_EVENTS.addressesChanged).toBe('addressesChanged');
    });
  });
});

// ---------------------------------------------------------------------------
// buildBchNamespace Tests
// ---------------------------------------------------------------------------

describe('buildBchNamespace', () => {
  it('should return object with bch namespace', () => {
    const ns = buildBchNamespace();
    expect(ns).toHaveProperty('bch');
  });

  it('should include all 6 methods by default', () => {
    const ns = buildBchNamespace();
    expect(ns.bch.methods).toHaveLength(6);
    expect(ns.bch.methods).toEqual([
      WC_METHODS.getAddresses,
      WC_METHODS.signTransaction,
      WC_METHODS.signMessage,
      CASHRPC_METHODS.getTokens,
      CASHRPC_METHODS.getBalance,
      CASHRPC_METHODS.getChangeLockingBytecode,
    ]);
  });

  it('should default to mainnet chain', () => {
    const ns = buildBchNamespace();
    expect(ns.bch.chains).toEqual([BCH_CHAINS.mainnet]);
  });

  it('should include addressesChanged event by default', () => {
    const ns = buildBchNamespace();
    expect(ns.bch.events).toEqual([WC_EVENTS.addressesChanged]);
  });

  it('should accept custom chains', () => {
    const config: BchNamespaceConfig = {
      chains: [BCH_CHAINS.testnet, BCH_CHAINS.regtest],
    };
    const ns = buildBchNamespace(config);
    expect(ns.bch.chains).toEqual([BCH_CHAINS.testnet, BCH_CHAINS.regtest]);
  });

  it('should override default chains with custom config', () => {
    const config: BchNamespaceConfig = {
      chains: [BCH_CHAINS.mainnet, BCH_CHAINS.testnet],
    };
    const ns = buildBchNamespace(config);
    expect(ns.bch.chains).toHaveLength(2);
    expect(ns.bch.chains).toContain(BCH_CHAINS.mainnet);
    expect(ns.bch.chains).toContain(BCH_CHAINS.testnet);
    expect(ns.bch.chains).not.toContain(BCH_CHAINS.regtest);
  });

  it('should accept custom methods', () => {
    const config: BchNamespaceConfig = {
      methods: [WC_METHODS.getAddresses, WC_METHODS.signMessage],
    };
    const ns = buildBchNamespace(config);
    expect(ns.bch.methods).toEqual([WC_METHODS.getAddresses, WC_METHODS.signMessage]);
  });

  it('should override default methods with custom config', () => {
    const config: BchNamespaceConfig = {
      methods: [
        WC_METHODS.getAddresses,
        WC_METHODS.signTransaction,
        CASHRPC_METHODS.getBalance,
      ],
    };
    const ns = buildBchNamespace(config);
    expect(ns.bch.methods).toHaveLength(3);
    expect(ns.bch.methods).toContain(WC_METHODS.getAddresses);
    expect(ns.bch.methods).toContain(WC_METHODS.signTransaction);
    expect(ns.bch.methods).toContain(CASHRPC_METHODS.getBalance);
  });

  it('should accept custom events', () => {
    const config: BchNamespaceConfig = {
      events: ['customEvent'],
    };
    const ns = buildBchNamespace(config);
    expect(ns.bch.events).toEqual(['customEvent']);
  });

  it('should support full custom config', () => {
    const config: BchNamespaceConfig = {
      chains: [BCH_CHAINS.testnet],
      methods: [WC_METHODS.getAddresses, CASHRPC_METHODS.getTokens],
      events: ['customEvent'],
    };
    const ns = buildBchNamespace(config);
    expect(ns.bch.chains).toEqual([BCH_CHAINS.testnet]);
    expect(ns.bch.methods).toEqual([WC_METHODS.getAddresses, CASHRPC_METHODS.getTokens]);
    expect(ns.bch.events).toEqual(['customEvent']);
  });

  it('should return correct structure for WC v2', () => {
    const ns = buildBchNamespace();
    expect(ns).toEqual({
      bch: {
        chains: [BCH_CHAINS.mainnet],
        methods: expect.arrayContaining([
          WC_METHODS.getAddresses,
          WC_METHODS.signTransaction,
          WC_METHODS.signMessage,
          CASHRPC_METHODS.getTokens,
          CASHRPC_METHODS.getBalance,
          CASHRPC_METHODS.getChangeLockingBytecode,
        ]),
        events: [WC_EVENTS.addressesChanged],
      },
    });
  });

  it('should preserve namespace structure with partial config', () => {
    const config: BchNamespaceConfig = {
      chains: [BCH_CHAINS.regtest],
    };
    const ns = buildBchNamespace(config);
    // Should still have all properties with defaults for non-overridden values
    expect(ns.bch).toHaveProperty('chains');
    expect(ns.bch).toHaveProperty('methods');
    expect(ns.bch).toHaveProperty('events');
    expect(ns.bch.chains).toEqual([BCH_CHAINS.regtest]);
    expect(ns.bch.methods).toHaveLength(6); // default methods
    expect(ns.bch.events).toEqual([WC_EVENTS.addressesChanged]); // default event
  });
});

// ---------------------------------------------------------------------------
// normalizeAddresses Tests
// ---------------------------------------------------------------------------

describe('normalizeAddresses', () => {
  it('should handle string array input', () => {
    const input = ['bitcoincash:qz2su80jwypa0y9xukayh0nkvl4dxvfjycwzxq5p7'];
    const result = normalizeAddresses(input);
    expect(result).toHaveLength(1);
    expect(result[0]).toEqual({
      address: 'bitcoincash:qz2su80jwypa0y9xukayh0nkvl4dxvfjycwzxq5p7',
    });
  });

  it('should handle multiple string addresses', () => {
    const input = [
      'bitcoincash:qz2su80jwypa0y9xukayh0nkvl4dxvfjycwzxq5p7',
      'bitcoincash:qp2rdyf0f9xkmh39w7a9t7dn0f9xk44z25mxmh39w7',
    ];
    const result = normalizeAddresses(input);
    expect(result).toHaveLength(2);
    expect(result[0].address).toBe('bitcoincash:qz2su80jwypa0y9xukayh0nkvl4dxvfjycwzxq5p7');
    expect(result[1].address).toBe('bitcoincash:qp2rdyf0f9xkmh39w7a9t7dn0f9xk44z25mxmh39w7');
  });

  it('should handle WalletAddress array', () => {
    const input: WalletAddress[] = [
      {
        address: 'bitcoincash:qz2su80jwypa0y9xukayh0nkvl4dxvfjycwzxq5p7',
        publicKey: '021234567890abcdef',
      },
    ];
    const result = normalizeAddresses(input);
    expect(result).toHaveLength(1);
    expect(result[0]).toEqual({
      address: 'bitcoincash:qz2su80jwypa0y9xukayh0nkvl4dxvfjycwzxq5p7',
      publicKey: '021234567890abcdef',
    });
  });

  it('should preserve optional publicKey and tokenAddress fields', () => {
    const input: WalletAddress[] = [
      {
        address: 'bitcoincash:qz2su80jwypa0y9xukayh0nkvl4dxvfjycwzxq5p7',
        publicKey: '021234567890abcdef',
        tokenAddress: 'simpleledger:qz2su80jwypa0y9xukayh0nkvl4dxvfjycwzxq5p7',
      },
    ];
    const result = normalizeAddresses(input);
    expect(result).toHaveLength(1);
    expect(result[0]).toEqual({
      address: 'bitcoincash:qz2su80jwypa0y9xukayh0nkvl4dxvfjycwzxq5p7',
      publicKey: '021234567890abcdef',
      tokenAddress: 'simpleledger:qz2su80jwypa0y9xukayh0nkvl4dxvfjycwzxq5p7',
    });
  });

  it('should handle {addresses: [...]} wrapper object', () => {
    const input = {
      addresses: ['bitcoincash:qz2su80jwypa0y9xukayh0nkvl4dxvfjycwzxq5p7'],
    };
    const result = normalizeAddresses(input);
    expect(result).toHaveLength(1);
    expect(result[0]).toEqual({
      address: 'bitcoincash:qz2su80jwypa0y9xukayh0nkvl4dxvfjycwzxq5p7',
    });
  });

  it('should handle nested wrapper with WalletAddress array', () => {
    const input = {
      addresses: [
        {
          address: 'bitcoincash:qz2su80jwypa0y9xukayh0nkvl4dxvfjycwzxq5p7',
          publicKey: '021234567890abcdef',
        },
      ],
    };
    const result = normalizeAddresses(input);
    expect(result).toHaveLength(1);
    expect(result[0]).toEqual({
      address: 'bitcoincash:qz2su80jwypa0y9xukayh0nkvl4dxvfjycwzxq5p7',
      publicKey: '021234567890abcdef',
    });
  });

  it('should return empty array for null input', () => {
    const result = normalizeAddresses(null);
    expect(result).toEqual([]);
  });

  it('should return empty array for undefined input', () => {
    const result = normalizeAddresses(undefined);
    expect(result).toEqual([]);
  });

  it('should return empty array for non-array, non-object input', () => {
    expect(normalizeAddresses('string')).toEqual([]);
    expect(normalizeAddresses(123)).toEqual([]);
    expect(normalizeAddresses(true)).toEqual([]);
  });

  it('should return empty array for empty array input', () => {
    const result = normalizeAddresses([]);
    expect(result).toEqual([]);
  });

  it('should filter out entries with empty address string', () => {
    const input = [
      { address: 'bitcoincash:qz2su80jwypa0y9xukayh0nkvl4dxvfjycwzxq5p7' },
      { address: '' },
      { address: 'bitcoincash:qp2rdyf0f9xkmh39w7a9t7dn0f9xk44z25mxmh39w7' },
    ];
    const result = normalizeAddresses(input);
    expect(result).toHaveLength(2);
    expect(result[0].address).toBe('bitcoincash:qz2su80jwypa0y9xukayh0nkvl4dxvfjycwzxq5p7');
    expect(result[1].address).toBe('bitcoincash:qp2rdyf0f9xkmh39w7a9t7dn0f9xk44z25mxmh39w7');
  });

  it('should filter out string entries that are empty strings', () => {
    const input = ['bitcoincash:qz2su80jwypa0y9xukayh0nkvl4dxvfjycwzxq5p7', ''];
    const result = normalizeAddresses(input);
    expect(result).toHaveLength(1);
    expect(result[0].address).toBe('bitcoincash:qz2su80jwypa0y9xukayh0nkvl4dxvfjycwzxq5p7');
  });

  it('should handle mixed string and object array', () => {
    const input = [
      'bitcoincash:qz2su80jwypa0y9xukayh0nkvl4dxvfjycwzxq5p7',
      { address: 'bitcoincash:qp2rdyf0f9xkmh39w7a9t7dn0f9xk44z25mxmh39w7', publicKey: '021234' },
    ];
    const result = normalizeAddresses(input);
    expect(result).toHaveLength(2);
    expect(result[0]).toEqual({
      address: 'bitcoincash:qz2su80jwypa0y9xukayh0nkvl4dxvfjycwzxq5p7',
    });
    expect(result[1]).toEqual({
      address: 'bitcoincash:qp2rdyf0f9xkmh39w7a9t7dn0f9xk44z25mxmh39w7',
      publicKey: '021234',
    });
  });

  it('should coerce non-string address values to string', () => {
    const input = [{ address: 123 as unknown }];
    const result = normalizeAddresses(input);
    expect(result).toHaveLength(1);
    expect(result[0].address).toBe('123');
  });

  it('should handle missing address field in object', () => {
    const input = [{ publicKey: '021234' }];
    const result = normalizeAddresses(input);
    expect(result).toHaveLength(0); // filtered out because address is empty
  });

  it('should preserve only address fields from extra properties', () => {
    const input = [
      {
        address: 'bitcoincash:qz2su80jwypa0y9xukayh0nkvl4dxvfjycwzxq5p7',
        publicKey: '021234',
        tokenAddress: 'simpleledger:qz2su80jwypa0y9xukayh0nkvl4dxvfjycwzxq5p7',
        extra: 'should be ignored',
      },
    ];
    const result = normalizeAddresses(input);
    expect(result).toHaveLength(1);
    expect(result[0]).toEqual({
      address: 'bitcoincash:qz2su80jwypa0y9xukayh0nkvl4dxvfjycwzxq5p7',
      publicKey: '021234',
      tokenAddress: 'simpleledger:qz2su80jwypa0y9xukayh0nkvl4dxvfjycwzxq5p7',
    });
    expect(result[0]).not.toHaveProperty('extra');
  });
});

// ---------------------------------------------------------------------------
// sessionSupportsMethod Tests
// ---------------------------------------------------------------------------

describe('sessionSupportsMethod', () => {
  it('should return true when method is in bch namespace methods', () => {
    const sessionNamespaces = {
      bch: {
        methods: [WC_METHODS.getAddresses, WC_METHODS.signTransaction, WC_METHODS.signMessage],
      },
    };
    expect(sessionSupportsMethod(sessionNamespaces, WC_METHODS.getAddresses)).toBe(true);
    expect(sessionSupportsMethod(sessionNamespaces, WC_METHODS.signTransaction)).toBe(true);
    expect(sessionSupportsMethod(sessionNamespaces, WC_METHODS.signMessage)).toBe(true);
  });

  it('should return true when CashRPC method is in bch namespace methods', () => {
    const sessionNamespaces = {
      bch: {
        methods: [CASHRPC_METHODS.getTokens, CASHRPC_METHODS.getBalance],
      },
    };
    expect(sessionSupportsMethod(sessionNamespaces, CASHRPC_METHODS.getTokens)).toBe(true);
    expect(sessionSupportsMethod(sessionNamespaces, CASHRPC_METHODS.getBalance)).toBe(true);
  });

  it('should return false when method is not in methods', () => {
    const sessionNamespaces = {
      bch: {
        methods: [WC_METHODS.getAddresses],
      },
    };
    expect(sessionSupportsMethod(sessionNamespaces, WC_METHODS.signTransaction)).toBe(false);
    expect(sessionSupportsMethod(sessionNamespaces, CASHRPC_METHODS.getBalance)).toBe(false);
  });

  it('should return false when methods array is empty', () => {
    const sessionNamespaces = {
      bch: {
        methods: [],
      },
    };
    expect(sessionSupportsMethod(sessionNamespaces, WC_METHODS.getAddresses)).toBe(false);
  });

  it('should return false when bch namespace is missing', () => {
    const sessionNamespaces = {
      eth: {
        methods: [WC_METHODS.getAddresses],
      },
    };
    expect(sessionSupportsMethod(sessionNamespaces, WC_METHODS.getAddresses)).toBe(false);
  });

  it('should return false when methods property is missing from bch namespace', () => {
    const sessionNamespaces = {
      bch: {
        chains: ['bch:bitcoincash'],
      },
    };
    expect(sessionSupportsMethod(sessionNamespaces, WC_METHODS.getAddresses)).toBe(false);
  });

  it('should return false when methods property is undefined', () => {
    const sessionNamespaces = {
      bch: {
        methods: undefined,
      },
    };
    expect(sessionSupportsMethod(sessionNamespaces, WC_METHODS.getAddresses)).toBe(false);
  });

  it('should handle empty sessionNamespaces object', () => {
    const sessionNamespaces = {};
    expect(sessionSupportsMethod(sessionNamespaces, WC_METHODS.getAddresses)).toBe(false);
  });

  it('should handle multiple namespaces and check only bch', () => {
    const sessionNamespaces = {
      eth: {
        methods: ['eth_sendTransaction', 'eth_signMessage'],
      },
      bch: {
        methods: [WC_METHODS.getAddresses, WC_METHODS.signTransaction],
      },
      sol: {
        methods: ['solana_signMessage'],
      },
    };
    expect(sessionSupportsMethod(sessionNamespaces, WC_METHODS.getAddresses)).toBe(true);
    expect(sessionSupportsMethod(sessionNamespaces, WC_METHODS.signTransaction)).toBe(true);
    expect(sessionSupportsMethod(sessionNamespaces, 'eth_sendTransaction')).toBe(false);
    expect(sessionSupportsMethod(sessionNamespaces, 'solana_signMessage')).toBe(false);
  });

  it('should support checking arbitrary method strings', () => {
    const sessionNamespaces = {
      bch: {
        methods: ['custom_method', 'another_method'],
      },
    };
    expect(sessionSupportsMethod(sessionNamespaces, 'custom_method')).toBe(true);
    expect(sessionSupportsMethod(sessionNamespaces, 'another_method')).toBe(true);
    expect(sessionSupportsMethod(sessionNamespaces, 'unknown_method')).toBe(false);
  });

  it('should handle all 6 default methods', () => {
    const sessionNamespaces = {
      bch: {
        methods: [
          WC_METHODS.getAddresses,
          WC_METHODS.signTransaction,
          WC_METHODS.signMessage,
          CASHRPC_METHODS.getTokens,
          CASHRPC_METHODS.getBalance,
          CASHRPC_METHODS.getChangeLockingBytecode,
        ],
      },
    };
    expect(sessionSupportsMethod(sessionNamespaces, WC_METHODS.getAddresses)).toBe(true);
    expect(sessionSupportsMethod(sessionNamespaces, WC_METHODS.signTransaction)).toBe(true);
    expect(sessionSupportsMethod(sessionNamespaces, WC_METHODS.signMessage)).toBe(true);
    expect(sessionSupportsMethod(sessionNamespaces, CASHRPC_METHODS.getTokens)).toBe(true);
    expect(sessionSupportsMethod(sessionNamespaces, CASHRPC_METHODS.getBalance)).toBe(true);
    expect(sessionSupportsMethod(sessionNamespaces, CASHRPC_METHODS.getChangeLockingBytecode)).toBe(
      true,
    );
  });
});
