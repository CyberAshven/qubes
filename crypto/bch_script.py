"""
BCH Script Support for P2SH Wallets

Handles:
- Script opcode construction
- P2SH address derivation (CashAddr format)
- Transaction building with BCH format
- Signing with SIGHASH_FORKID (0x41)

This module enables Qubes to have their own BCH wallets with asymmetric
multi-sig control: owner can spend alone, or owner + Qube together.
"""

import hashlib
import struct
from typing import List, Tuple, Optional
from dataclasses import dataclass

# =============================================================================
# OPCODES
# =============================================================================

OP_0 = 0x00
OP_FALSE = 0x00
OP_TRUE = 0x51  # Also OP_1
OP_1 = 0x51
OP_2 = 0x52
OP_IF = 0x63
OP_ELSE = 0x67
OP_ENDIF = 0x68
OP_DUP = 0x76
OP_HASH160 = 0xa9
OP_EQUALVERIFY = 0x88
OP_CHECKSIG = 0xac
OP_CHECKMULTISIG = 0xae

# Sighash types
SIGHASH_ALL = 0x01
SIGHASH_FORKID = 0x40
SIGHASH_ALL_FORKID = SIGHASH_ALL | SIGHASH_FORKID  # 0x41

# BCH fork ID (used in sighash calculation)
BCH_FORK_ID = 0x00


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class UTXO:
    """Unspent transaction output"""
    txid: str           # Transaction ID (hex, big-endian display format)
    vout: int           # Output index
    value: int          # Amount in satoshis
    script_pubkey: bytes  # Locking script


@dataclass
class TxOutput:
    """Transaction output"""
    address: str        # Destination address (CashAddr)
    value: int          # Amount in satoshis


# =============================================================================
# HASH FUNCTIONS
# =============================================================================

def sha256(data: bytes) -> bytes:
    """Single SHA256 hash"""
    return hashlib.sha256(data).digest()


def double_sha256(data: bytes) -> bytes:
    """Double SHA256 (used for txid, sighash)"""
    return sha256(sha256(data))


def hash160(data: bytes) -> bytes:
    """HASH160 = RIPEMD160(SHA256(data)) - used for P2SH address"""
    sha = hashlib.sha256(data).digest()
    try:
        ripemd = hashlib.new('ripemd160', sha, usedforsecurity=False).digest()
    except (ValueError, TypeError):
        # Fallback: pure Python RIPEMD-160 (for Linux with OpenSSL 3.0+ legacy disabled)
        from bitcash._ripemd160 import ripemd160
        ripemd = ripemd160(sha)
    return ripemd


# =============================================================================
# SCRIPT BUILDING
# =============================================================================

def push_data(data: bytes) -> bytes:
    """
    Create push data opcode for script.

    For data <= 75 bytes: single byte length prefix
    For data 76-255 bytes: OP_PUSHDATA1 + 1-byte length
    For data 256-65535 bytes: OP_PUSHDATA2 + 2-byte length
    """
    length = len(data)

    if length <= 75:
        return bytes([length]) + data
    elif length <= 255:
        return bytes([0x4c, length]) + data  # OP_PUSHDATA1
    elif length <= 65535:
        return bytes([0x4d]) + struct.pack('<H', length) + data  # OP_PUSHDATA2
    else:
        raise ValueError(f"Data too large: {length} bytes")


def build_asymmetric_multisig_script(owner_pubkey: bytes, qube_pubkey: bytes) -> bytes:
    """
    Build IF/ELSE redeem script for asymmetric multi-sig.

    Script structure:
        OP_IF
            <owner_pubkey> OP_CHECKSIG
        OP_ELSE
            OP_2 <owner_pubkey> <qube_pubkey> OP_2 OP_CHECKMULTISIG
        OP_ENDIF

    Spending paths:
        1. Owner alone: <owner_sig> OP_TRUE <redeem_script>
        2. Both required: OP_0 <owner_sig> <qube_sig> OP_FALSE <redeem_script>

    Args:
        owner_pubkey: 33-byte compressed public key (02... or 03...)
        qube_pubkey: 33-byte compressed public key (02... or 03...)

    Returns:
        Redeem script bytes
    """
    if len(owner_pubkey) != 33:
        raise ValueError(f"Owner pubkey must be 33 bytes (compressed), got {len(owner_pubkey)}")
    if len(qube_pubkey) != 33:
        raise ValueError(f"Qube pubkey must be 33 bytes (compressed), got {len(qube_pubkey)}")

    script = bytes()

    # OP_IF
    script += bytes([OP_IF])

    # <owner_pubkey> OP_CHECKSIG
    script += push_data(owner_pubkey)
    script += bytes([OP_CHECKSIG])

    # OP_ELSE
    script += bytes([OP_ELSE])

    # OP_2 <owner_pubkey> <qube_pubkey> OP_2 OP_CHECKMULTISIG
    script += bytes([OP_2])
    script += push_data(owner_pubkey)
    script += push_data(qube_pubkey)
    script += bytes([OP_2])
    script += bytes([OP_CHECKMULTISIG])

    # OP_ENDIF
    script += bytes([OP_ENDIF])

    return script


def build_p2sh_script_pubkey(script_hash: bytes) -> bytes:
    """
    Build P2SH locking script (scriptPubKey).

    Format: OP_HASH160 <20-byte-hash> OP_EQUAL
    """
    if len(script_hash) != 20:
        raise ValueError(f"Script hash must be 20 bytes, got {len(script_hash)}")

    return bytes([OP_HASH160]) + push_data(script_hash) + bytes([0x87])  # OP_EQUAL


# =============================================================================
# CASHADDR ENCODING
# =============================================================================

# CashAddr character set (base32)
CASHADDR_CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"


def _cashaddr_polymod(values: List[int]) -> int:
    """CashAddr polymod checksum calculation"""
    c = 1
    for d in values:
        c0 = c >> 35
        c = ((c & 0x07ffffffff) << 5) ^ d
        if c0 & 0x01:
            c ^= 0x98f2bc8e61
        if c0 & 0x02:
            c ^= 0x79b76d99e2
        if c0 & 0x04:
            c ^= 0xf33e5fb3c4
        if c0 & 0x08:
            c ^= 0xae2eabe2a8
        if c0 & 0x10:
            c ^= 0x1e4f43e470
    return c ^ 1


def _cashaddr_hrp_expand(hrp: str) -> List[int]:
    """Expand human-readable part for checksum"""
    return [ord(c) & 0x1f for c in hrp] + [0]


def _create_checksum(hrp: str, data: List[int]) -> List[int]:
    """Create CashAddr checksum"""
    values = _cashaddr_hrp_expand(hrp) + data
    polymod = _cashaddr_polymod(values + [0, 0, 0, 0, 0, 0, 0, 0])
    return [(polymod >> 5 * (7 - i)) & 31 for i in range(8)]


def _convert_bits(data: bytes, from_bits: int, to_bits: int, pad: bool = True) -> List[int]:
    """Convert between bit sizes"""
    acc = 0
    bits = 0
    result = []
    maxv = (1 << to_bits) - 1

    for value in data:
        acc = (acc << from_bits) | value
        bits += from_bits
        while bits >= to_bits:
            bits -= to_bits
            result.append((acc >> bits) & maxv)

    if pad and bits:
        result.append((acc << (to_bits - bits)) & maxv)

    return result


def script_to_p2sh_address(script: bytes, network: str = "mainnet") -> str:
    """
    Derive P2SH CashAddr (bitcoincash:p...) from redeem script.

    Process:
    1. HASH160 the redeem script
    2. Prepend version byte (0x08 for P2SH mainnet, 0x0f for testnet)
    3. Encode as CashAddr

    Args:
        script: Redeem script bytes
        network: "mainnet" or "testnet"/"chipnet"

    Returns:
        CashAddr string (e.g., "bitcoincash:pq...")
    """
    # HASH160 the script
    script_hash = hash160(script)

    # Version byte: 0x08 for P2SH mainnet, 0x0f for P2SH testnet
    # (version byte encodes both type and size)
    if network == "mainnet":
        version_byte = 0x08  # P2SH, 160-bit hash
        prefix = "bitcoincash"
    else:
        version_byte = 0x08  # Same version byte, different prefix
        prefix = "bchtest"

    # Prepend version byte to hash
    payload = bytes([version_byte]) + script_hash

    # Convert to 5-bit groups
    data = _convert_bits(payload, 8, 5)

    # Create checksum
    checksum = _create_checksum(prefix, data)

    # Encode
    combined = data + checksum
    addr = ''.join([CASHADDR_CHARSET[d] for d in combined])

    return f"{prefix}:{addr}"


def decode_cashaddr(address: str) -> Tuple[str, int, bytes]:
    """
    Decode CashAddr to prefix, version, and hash.

    Returns:
        Tuple of (prefix, version_byte, hash_bytes)
    """
    if ':' in address:
        prefix, addr = address.split(':', 1)
    else:
        # Assume mainnet if no prefix
        prefix = "bitcoincash"
        addr = address

    # Decode base32
    data = [CASHADDR_CHARSET.index(c) for c in addr.lower()]

    # Verify checksum
    hrp_expanded = _cashaddr_hrp_expand(prefix)
    if _cashaddr_polymod(hrp_expanded + data) != 0:
        raise ValueError("Invalid checksum")

    # Remove checksum (last 8 characters)
    data = data[:-8]

    # Convert from 5-bit to 8-bit
    payload = bytes(_convert_bits(data, 5, 8, pad=False))

    version_byte = payload[0]
    hash_bytes = payload[1:]

    return prefix, version_byte, hash_bytes


def address_to_script_pubkey(address: str) -> bytes:
    """
    Convert CashAddr to scriptPubKey.

    Args:
        address: CashAddr string

    Returns:
        scriptPubKey bytes
    """
    prefix, version, hash_bytes = decode_cashaddr(address)

    # Extract type from version byte
    # Bits 7-4: reserved (0)
    # Bit 3: 0 = P2PKH, 1 = P2SH
    # Bits 2-0: size (0 = 160 bits)
    addr_type = (version >> 3) & 0x01

    if addr_type == 0:
        # P2PKH: OP_DUP OP_HASH160 <hash> OP_EQUALVERIFY OP_CHECKSIG
        return bytes([OP_DUP, OP_HASH160]) + push_data(hash_bytes) + bytes([OP_EQUALVERIFY, OP_CHECKSIG])
    else:
        # P2SH: OP_HASH160 <hash> OP_EQUAL
        return build_p2sh_script_pubkey(hash_bytes)


# =============================================================================
# TRANSACTION SERIALIZATION
# =============================================================================

def var_int(n: int) -> bytes:
    """Encode variable-length integer (CompactSize)"""
    if n < 0xfd:
        return bytes([n])
    elif n <= 0xffff:
        return bytes([0xfd]) + struct.pack('<H', n)
    elif n <= 0xffffffff:
        return bytes([0xfe]) + struct.pack('<I', n)
    else:
        return bytes([0xff]) + struct.pack('<Q', n)


def serialize_outpoint(txid: str, vout: int) -> bytes:
    """Serialize transaction outpoint (txid + vout)"""
    # txid is displayed big-endian, but stored little-endian
    txid_bytes = bytes.fromhex(txid)[::-1]
    return txid_bytes + struct.pack('<I', vout)


def serialize_output(value: int, script_pubkey: bytes) -> bytes:
    """Serialize transaction output"""
    return struct.pack('<Q', value) + var_int(len(script_pubkey)) + script_pubkey


# =============================================================================
# BIP143 SIGHASH (BCH with FORKID)
# =============================================================================

def calculate_sighash_forkid(
    tx_version: int,
    inputs: List[Tuple[str, int, int, bytes]],  # [(txid, vout, value, scriptPubKey), ...]
    outputs: List[Tuple[int, bytes]],           # [(value, scriptPubKey), ...]
    input_idx: int,
    redeem_script: bytes,
    sighash_type: int = SIGHASH_ALL_FORKID
) -> bytes:
    """
    Calculate BIP143-style sighash with FORKID for BCH.

    This is the digest that gets signed for each input.

    Args:
        tx_version: Transaction version (usually 1 or 2)
        inputs: List of (txid, vout, value, scriptPubKey) tuples
        outputs: List of (value, scriptPubKey) tuples
        input_idx: Index of input being signed
        redeem_script: The redeem script (for P2SH) or scriptPubKey
        sighash_type: Sighash flags (default: SIGHASH_ALL | FORKID)

    Returns:
        32-byte sighash to sign
    """
    # BIP143 sighash preimage components:
    # 1. nVersion (4 bytes, little-endian)
    # 2. hashPrevouts (32 bytes) - double SHA256 of all outpoints
    # 3. hashSequence (32 bytes) - double SHA256 of all sequences
    # 4. outpoint (36 bytes) - txid + vout of input being signed
    # 5. scriptCode (varlen) - the script being executed
    # 6. value (8 bytes) - value of UTXO being spent
    # 7. nSequence (4 bytes) - sequence of input being signed
    # 8. hashOutputs (32 bytes) - double SHA256 of all outputs
    # 9. nLockTime (4 bytes)
    # 10. sighash type (4 bytes, with FORKID in bits 8-31)

    # 1. Version
    preimage = struct.pack('<I', tx_version)

    # 2. hashPrevouts (for SIGHASH_ALL)
    prevouts = b''
    for txid, vout, _, _ in inputs:
        prevouts += serialize_outpoint(txid, vout)
    preimage += double_sha256(prevouts)

    # 3. hashSequence (for SIGHASH_ALL)
    sequences = b''
    for _ in inputs:
        sequences += struct.pack('<I', 0xffffffff)  # Default sequence
    preimage += double_sha256(sequences)

    # 4. Outpoint of input being signed
    txid, vout, value, _ = inputs[input_idx]
    preimage += serialize_outpoint(txid, vout)

    # 5. scriptCode (varlen) - the redeem script for P2SH
    preimage += var_int(len(redeem_script)) + redeem_script

    # 6. Value of UTXO being spent
    preimage += struct.pack('<Q', value)

    # 7. nSequence of input being signed
    preimage += struct.pack('<I', 0xffffffff)

    # 8. hashOutputs (for SIGHASH_ALL)
    outputs_serialized = b''
    for out_value, script_pubkey in outputs:
        outputs_serialized += serialize_output(out_value, script_pubkey)
    preimage += double_sha256(outputs_serialized)

    # 9. nLockTime
    preimage += struct.pack('<I', 0)

    # 10. Sighash type (with fork ID in upper bytes for BCH)
    # BCH uses fork ID 0 in bits 8-31, so just add FORKID to sighash type
    preimage += struct.pack('<I', sighash_type)

    return double_sha256(preimage)


# =============================================================================
# SIGNATURE HANDLING
# =============================================================================

def sign_sighash(sighash: bytes, private_key_bytes: bytes) -> bytes:
    """
    Sign sighash with private key, return DER-encoded signature + sighash byte.

    Args:
        sighash: 32-byte hash to sign
        private_key_bytes: 32-byte private key

    Returns:
        DER-encoded signature + SIGHASH_ALL_FORKID byte
    """
    from ecdsa import SigningKey, SECP256k1
    from ecdsa.util import sigencode_der_canonize

    # Create signing key
    sk = SigningKey.from_string(private_key_bytes, curve=SECP256k1)

    # Sign with canonical DER encoding (low-S)
    signature = sk.sign_digest(
        sighash,
        sigencode=sigencode_der_canonize
    )

    # Append sighash type byte
    return signature + bytes([SIGHASH_ALL_FORKID])


def pubkey_from_privkey(private_key_bytes: bytes) -> bytes:
    """
    Derive compressed public key from private key.

    Args:
        private_key_bytes: 32-byte private key

    Returns:
        33-byte compressed public key
    """
    from ecdsa import SigningKey, SECP256k1

    sk = SigningKey.from_string(private_key_bytes, curve=SECP256k1)
    vk = sk.get_verifying_key()

    # Get compressed public key
    # Prefix: 02 if y is even, 03 if y is odd
    x = vk.pubkey.point.x()
    y = vk.pubkey.point.y()
    prefix = b'\x02' if y % 2 == 0 else b'\x03'

    return prefix + x.to_bytes(32, 'big')


# =============================================================================
# TRANSACTION BUILDING
# =============================================================================

def build_p2sh_spending_tx(
    utxos: List[UTXO],
    outputs: List[TxOutput],
    redeem_script: bytes,
    signatures: List[bytes],
    spending_path: str,
    fee_per_byte: int = 1
) -> bytes:
    """
    Build complete signed P2SH spending transaction.

    Args:
        utxos: List of UTXOs to spend
        outputs: List of outputs (address, value)
        redeem_script: The redeem script
        signatures: One signature per input for owner_only,
                    or [owner_sig, qube_sig] for multisig (single-input only)
        spending_path: "owner_only" or "multisig"
        fee_per_byte: Fee in satoshis per byte (default 1)

    Returns:
        Serialized signed transaction
    """
    # Calculate output scripts
    output_scripts = []
    for out in outputs:
        script = address_to_script_pubkey(out.address)
        output_scripts.append((out.value, script))

    # Build scriptSigs for each input
    script_sigs = []
    if spending_path == "owner_only":
        # One signature per input: <owner_sig> OP_TRUE <redeem_script>
        if len(signatures) != len(utxos):
            raise ValueError(f"Owner-only path requires one signature per input ({len(utxos)} inputs, got {len(signatures)} signatures)")
        for sig in signatures:
            script_sigs.append(push_data(sig) + bytes([OP_TRUE]) + push_data(redeem_script))
    elif spending_path == "multisig":
        # OP_0 <owner_sig> <qube_sig> OP_FALSE <redeem_script>
        if len(utxos) != 1:
            raise ValueError("Multisig path currently supports single-input only")
        if len(signatures) != 2:
            raise ValueError("Multisig path requires exactly 2 signatures")
        owner_sig, qube_sig = signatures
        script_sigs.append(bytes([OP_0]) + push_data(owner_sig) + push_data(qube_sig) + bytes([OP_FALSE]) + push_data(redeem_script))
    else:
        raise ValueError(f"Unknown spending path: {spending_path}")

    # Build transaction
    tx = b''

    # Version (4 bytes)
    tx += struct.pack('<I', 2)

    # Input count
    tx += var_int(len(utxos))

    # Inputs
    for i, utxo in enumerate(utxos):
        tx += serialize_outpoint(utxo.txid, utxo.vout)
        tx += var_int(len(script_sigs[i])) + script_sigs[i]
        tx += struct.pack('<I', 0xffffffff)  # Sequence

    # Output count
    tx += var_int(len(output_scripts))

    # Outputs
    for value, script in output_scripts:
        tx += serialize_output(value, script)

    # Locktime
    tx += struct.pack('<I', 0)

    return tx


def estimate_tx_size(num_inputs: int, num_outputs: int, spending_path: str) -> int:
    """
    Estimate transaction size in bytes.

    Args:
        num_inputs: Number of inputs
        num_outputs: Number of outputs
        spending_path: "owner_only" or "multisig"

    Returns:
        Estimated size in bytes
    """
    # Base transaction overhead
    base = 10  # version (4) + locktime (4) + varint for inputs/outputs (2)

    # Input size depends on scriptSig
    # P2SH input with our script:
    #   - outpoint: 36 bytes (txid + vout)
    #   - scriptSig length: ~1-3 bytes
    #   - sequence: 4 bytes
    #   - scriptSig content varies by path

    if spending_path == "owner_only":
        # <sig> OP_TRUE <redeem_script>
        # sig: ~72 bytes, OP_TRUE: 1 byte, redeem_script: ~76 bytes
        input_size = 36 + 3 + 4 + 72 + 1 + 76 + 3  # ~195 bytes
    else:
        # OP_0 <sig1> <sig2> OP_FALSE <redeem_script>
        # OP_0: 1, sig1: ~72, sig2: ~72, OP_FALSE: 1, script: ~76
        input_size = 36 + 3 + 4 + 1 + 72 + 72 + 1 + 76 + 3  # ~268 bytes

    # P2PKH output: ~34 bytes each
    # P2SH output: ~32 bytes each
    output_size = 34  # average

    return base + (input_size * num_inputs) + (output_size * num_outputs)


def calculate_fee(tx_size: int, fee_per_byte: int = 1) -> int:
    """Calculate transaction fee"""
    return tx_size * fee_per_byte


# =============================================================================
# HIGH-LEVEL HELPERS
# =============================================================================

def pubkey_to_p2pkh_address(pubkey_hex: str, network: str = "mainnet", token_aware: bool = False) -> str:
    """
    Convert a compressed public key to its P2PKH CashAddr.

    Args:
        pubkey_hex: 33-byte compressed public key (hex string, 66 characters)
        network: "mainnet" or "testnet"/"chipnet"
        token_aware: If True, returns 'z' address (token-aware). If False, returns 'q' address.

    Returns:
        CashAddr string:
        - token_aware=False: "bitcoincash:q..." (standard P2PKH)
        - token_aware=True:  "bitcoincash:z..." (token-aware P2PKH for CashTokens)
    """
    pubkey = bytes.fromhex(pubkey_hex)

    if len(pubkey) != 33:
        raise ValueError(f"Public key must be 33 bytes (compressed), got {len(pubkey)}")

    # Hash160 the public key
    pubkey_hash = hash160(pubkey)

    # Version byte (CashAddr encoding):
    # Bits: [7-5: reserved=0] [4: token=0/1] [3: type=0(P2PKH)/1(P2SH)] [2-0: size=0(160bit)]
    # P2PKH standard:    0x00 (produces 'q' address)
    # P2PKH token-aware: 0x10 (produces 'z' address)
    if token_aware:
        version_byte = 0x10  # Token-aware P2PKH (bit 4 set)
    else:
        version_byte = 0x00  # Standard P2PKH

    if network == "mainnet":
        prefix = "bitcoincash"
    else:
        prefix = "bchtest"

    # Prepend version byte to hash
    payload = bytes([version_byte]) + pubkey_hash

    # Convert to 5-bit groups
    data = _convert_bits(payload, 8, 5)

    # Create checksum
    checksum = _create_checksum(prefix, data)

    # Encode
    combined = data + checksum
    addr = ''.join([CASHADDR_CHARSET[d] for d in combined])

    return f"{prefix}:{addr}"


def pubkey_to_token_address(pubkey_hex: str, network: str = "mainnet") -> str:
    """
    Convenience function: Convert public key to token-aware 'z' address.

    This is the address format needed for receiving CashTokens (NFTs).

    Args:
        pubkey_hex: 33-byte compressed public key (hex)
        network: "mainnet" or "testnet"

    Returns:
        Token-aware CashAddr (bitcoincash:z...)
    """
    return pubkey_to_p2pkh_address(pubkey_hex, network, token_aware=True)


def pubkey_to_cash_address(pubkey_hex: str, network: str = "mainnet") -> str:
    """
    Convenience function: Convert public key to standard 'q' address.

    Args:
        pubkey_hex: 33-byte compressed public key (hex)
        network: "mainnet" or "testnet"

    Returns:
        Standard CashAddr (bitcoincash:q...)
    """
    return pubkey_to_p2pkh_address(pubkey_hex, network, token_aware=False)


def cash_address_to_token_address(q_address: str) -> str:
    """
    Convert a standard 'q' address to its corresponding token-aware 'z' address.

    Both addresses share the same pubkey hash - only the version byte differs.
    This allows users to provide their standard BCH address instead of a public key
    when they only need NFT functionality (not wallet owner control).

    Args:
        q_address: Standard CashAddr (bitcoincash:q... or just q...)

    Returns:
        Token-aware CashAddr (bitcoincash:z...)

    Raises:
        ValueError: If address is not a valid P2PKH address
    """
    # Decode the address
    prefix, version, pubkey_hash = decode_cashaddr(q_address)

    # Verify it's a P2PKH address (version byte has bit 3 = 0)
    addr_type = (version >> 3) & 0x01
    if addr_type != 0:
        raise ValueError(f"Address is P2SH (version {version}), not P2PKH. Cannot convert to token address.")

    # Check if already token-aware (bit 4 set)
    is_token = (version >> 4) & 0x01
    if is_token:
        # Already a 'z' address, return as-is
        return q_address

    # Convert to token-aware version (set bit 4)
    token_version = version | 0x10  # 0x00 → 0x10

    # Re-encode with token version
    payload = bytes([token_version]) + pubkey_hash
    data = _convert_bits(payload, 8, 5)
    checksum = _create_checksum(prefix, data)
    combined = data + checksum
    addr = ''.join([CASHADDR_CHARSET[d] for d in combined])

    return f"{prefix}:{addr}"


def token_address_to_cash_address(z_address: str) -> str:
    """
    Convert a token-aware 'z' address to its corresponding standard 'q' address.

    Args:
        z_address: Token-aware CashAddr (bitcoincash:z...)

    Returns:
        Standard CashAddr (bitcoincash:q...)
    """
    # Decode the address
    prefix, version, pubkey_hash = decode_cashaddr(z_address)

    # Clear the token bit (bit 4)
    standard_version = version & ~0x10  # 0x10 → 0x00

    # Re-encode with standard version
    payload = bytes([standard_version]) + pubkey_hash
    data = _convert_bits(payload, 8, 5)
    checksum = _create_checksum(prefix, data)
    combined = data + checksum
    addr = ''.join([CASHADDR_CHARSET[d] for d in combined])

    return f"{prefix}:{addr}"


def normalize_to_token_address(address_or_pubkey: str, network: str = "mainnet") -> tuple[str, str | None]:
    """
    Accept either a public key, 'q' address, or 'z' address and return the token address.

    This is the main entry point for flexible address input.

    Args:
        address_or_pubkey: One of:
            - Compressed public key (66 hex chars starting with 02 or 03)
            - Standard 'q' address (bitcoincash:q...)
            - Token 'z' address (bitcoincash:z...)
        network: "mainnet" or "testnet"

    Returns:
        Tuple of (token_address, pubkey_or_none):
            - token_address: The 'z' address for NFT recipient
            - pubkey_or_none: The public key if provided, None if only address was given

    Example:
        # From public key - can use for both NFT and wallet
        z_addr, pubkey = normalize_to_token_address("02abc...def")
        # z_addr = "bitcoincash:z...", pubkey = "02abc...def"

        # From q address - can only use for NFT (no wallet owner control)
        z_addr, pubkey = normalize_to_token_address("bitcoincash:qxyz...")
        # z_addr = "bitcoincash:z...", pubkey = None
    """
    input_str = address_or_pubkey.strip()

    # Check if it's a public key (66 hex chars, starts with 02 or 03)
    if len(input_str) == 66 and input_str[:2] in ('02', '03'):
        try:
            bytes.fromhex(input_str)  # Validate hex
            token_addr = pubkey_to_token_address(input_str, network)
            return token_addr, input_str
        except ValueError:
            pass  # Not valid hex, try as address

    # Check if it's a CashAddr
    if ':' in input_str or input_str.startswith(('q', 'z', 'p', 'r')):
        try:
            # Normalize - add prefix if missing
            if ':' not in input_str:
                input_str = f"bitcoincash:{input_str}"

            prefix, version, _ = decode_cashaddr(input_str)

            # Check address type
            is_token = (version >> 4) & 0x01
            addr_type = (version >> 3) & 0x01

            if addr_type == 1:
                raise ValueError("P2SH addresses (p/r) cannot be converted. Need P2PKH (q) or public key.")

            if is_token:
                # Already a 'z' address
                return input_str, None
            else:
                # Convert 'q' to 'z'
                token_addr = cash_address_to_token_address(input_str)
                return token_addr, None
        except Exception as e:
            raise ValueError(f"Invalid address format: {e}")

    raise ValueError(
        f"Invalid input. Expected one of:\n"
        f"  - Compressed public key (66 hex chars, starts with 02 or 03)\n"
        f"  - Standard BCH address (bitcoincash:q...)\n"
        f"  - Token address (bitcoincash:z...)\n"
        f"Got: {input_str[:30]}..."
    )


def create_wallet_address(owner_pubkey_hex: str, qube_pubkey_hex: str, network: str = "mainnet") -> dict:
    """
    Create P2SH wallet address from owner and Qube public keys.

    Args:
        owner_pubkey_hex: Owner's compressed public key (hex)
        qube_pubkey_hex: Qube's compressed public key (hex)
        network: "mainnet" or "testnet"

    Returns:
        {
            "p2sh_address": "bitcoincash:p...",
            "redeem_script": <bytes>,
            "redeem_script_hex": "...",
            "script_hash": "..."
        }
    """
    owner_pubkey = bytes.fromhex(owner_pubkey_hex)
    qube_pubkey = bytes.fromhex(qube_pubkey_hex)

    # Build redeem script
    redeem_script = build_asymmetric_multisig_script(owner_pubkey, qube_pubkey)

    # Derive P2SH address
    p2sh_address = script_to_p2sh_address(redeem_script, network)

    # Script hash for verification
    script_hash = hash160(redeem_script)

    return {
        "p2sh_address": p2sh_address,
        "redeem_script": redeem_script,
        "redeem_script_hex": redeem_script.hex(),
        "script_hash": script_hash.hex()
    }


def spend_owner_only(
    utxo: UTXO,
    outputs: List[TxOutput],
    redeem_script: bytes,
    owner_privkey_bytes: bytes
) -> str:
    """
    Spend from P2SH wallet using owner-only path (IF branch).

    Args:
        utxo: UTXO to spend
        outputs: Outputs (address, value pairs)
        redeem_script: The redeem script
        owner_privkey_bytes: Owner's 32-byte private key

    Returns:
        Signed transaction hex
    """
    # Prepare inputs and outputs for sighash
    inputs = [(utxo.txid, utxo.vout, utxo.value, utxo.script_pubkey)]
    output_data = [(out.value, address_to_script_pubkey(out.address)) for out in outputs]

    # Calculate sighash
    sighash = calculate_sighash_forkid(
        tx_version=2,
        inputs=inputs,
        outputs=output_data,
        input_idx=0,
        redeem_script=redeem_script
    )

    # Sign
    signature = sign_sighash(sighash, owner_privkey_bytes)

    # Build transaction
    tx = build_p2sh_spending_tx(
        utxos=[utxo],
        outputs=outputs,
        redeem_script=redeem_script,
        signatures=[signature],
        spending_path="owner_only"
    )

    return tx.hex()


def spend_multisig(
    utxo: UTXO,
    outputs: List[TxOutput],
    redeem_script: bytes,
    owner_privkey_bytes: bytes,
    qube_privkey_bytes: bytes
) -> str:
    """
    Spend from P2SH wallet using 2-of-2 multisig path (ELSE branch).

    Args:
        utxo: UTXO to spend
        outputs: Outputs (address, value pairs)
        redeem_script: The redeem script
        owner_privkey_bytes: Owner's 32-byte private key
        qube_privkey_bytes: Qube's 32-byte private key

    Returns:
        Signed transaction hex
    """
    # Prepare inputs and outputs for sighash
    inputs = [(utxo.txid, utxo.vout, utxo.value, utxo.script_pubkey)]
    output_data = [(out.value, address_to_script_pubkey(out.address)) for out in outputs]

    # Calculate sighash
    sighash = calculate_sighash_forkid(
        tx_version=2,
        inputs=inputs,
        outputs=output_data,
        input_idx=0,
        redeem_script=redeem_script
    )

    # Sign with both keys
    owner_sig = sign_sighash(sighash, owner_privkey_bytes)
    qube_sig = sign_sighash(sighash, qube_privkey_bytes)

    # Build transaction (signatures in order: owner, qube)
    tx = build_p2sh_spending_tx(
        utxos=[utxo],
        outputs=outputs,
        redeem_script=redeem_script,
        signatures=[owner_sig, qube_sig],
        spending_path="multisig"
    )

    return tx.hex()


# =============================================================================
# TESTING / VALIDATION
# =============================================================================

if __name__ == "__main__":
    # Quick validation test
    print("BCH Script Module - Validation Test")
    print("=" * 50)

    # Generate test keys
    import os
    owner_privkey = os.urandom(32)
    qube_privkey = os.urandom(32)

    owner_pubkey = pubkey_from_privkey(owner_privkey)
    qube_pubkey = pubkey_from_privkey(qube_privkey)

    print(f"Owner pubkey: {owner_pubkey.hex()}")
    print(f"Qube pubkey:  {qube_pubkey.hex()}")

    # Create wallet
    wallet = create_wallet_address(owner_pubkey.hex(), qube_pubkey.hex())

    print(f"\nP2SH Address: {wallet['p2sh_address']}")
    print(f"Redeem script ({len(wallet['redeem_script'])} bytes): {wallet['redeem_script_hex'][:50]}...")
    print(f"Script hash: {wallet['script_hash']}")

    # Decode address back
    prefix, version, hash_bytes = decode_cashaddr(wallet['p2sh_address'])
    print(f"\nDecoded address:")
    print(f"  Prefix: {prefix}")
    print(f"  Version: {version} (P2SH={version >> 3 & 1})")
    print(f"  Hash: {hash_bytes.hex()}")

    # Verify hash matches
    assert hash_bytes.hex() == wallet['script_hash'], "Script hash mismatch!"
    print("\n[OK] Script hash verification passed!")

    print("\nTo test on mainnet:")
    print(f"1. Send small amount to: {wallet['p2sh_address']}")
    print("2. Use spend_owner_only() or spend_multisig() to spend")
