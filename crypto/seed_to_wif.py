"""
Derive a BCH WIF private key from a BIP39 seed phrase.

Uses standard BIP44 derivation path m/44'/145'/0'/0/0 (BCH mainnet).
Pure Python implementation using hashlib, hmac, and ecdsa.
No additional dependencies required beyond what's already installed.
"""

import hashlib
import hmac
import struct
import base58
from ecdsa import SECP256k1
from ecdsa.ellipticcurve import INFINITY


# BIP32 constants
HARDENED = 0x80000000
BCH_DERIVATION_PATH = [44 + HARDENED, 145 + HARDENED, 0 + HARDENED, 0, 0]


def _pbkdf2_seed(mnemonic: str, passphrase: str = "") -> bytes:
    """BIP39: mnemonic → 64-byte seed via PBKDF2-HMAC-SHA512."""
    password = mnemonic.encode("utf-8")
    salt = ("mnemonic" + passphrase).encode("utf-8")
    return hashlib.pbkdf2_hmac("sha512", password, salt, 2048)


def _hmac_sha512(key: bytes, data: bytes) -> bytes:
    return hmac.new(key, data, hashlib.sha512).digest()


def _ser32(i: int) -> bytes:
    return struct.pack(">I", i)


def _parse256(b: bytes) -> int:
    return int.from_bytes(b, "big")


def _point_from_privkey(privkey_int: int):
    """Derive public key point from private key integer."""
    return SECP256k1.generator * privkey_int


def _ser_compressed_pubkey(point) -> bytes:
    """Serialize EC point as compressed public key (33 bytes)."""
    prefix = b'\x02' if point.y() % 2 == 0 else b'\x03'
    return prefix + point.x().to_bytes(32, "big")


def _master_key(seed: bytes) -> tuple:
    """BIP32: seed → (master_privkey, master_chaincode)."""
    I = _hmac_sha512(b"Bitcoin seed", seed)
    IL, IR = I[:32], I[32:]
    key_int = _parse256(IL)
    if key_int == 0 or key_int >= SECP256k1.order:
        raise ValueError("Invalid master key derived from seed")
    return IL, IR  # privkey bytes, chaincode bytes


def _derive_child(privkey: bytes, chaincode: bytes, index: int) -> tuple:
    """BIP32: derive child key at given index."""
    key_int = _parse256(privkey)

    if index >= HARDENED:
        # Hardened: HMAC-SHA512(chaincode, 0x00 || privkey || index)
        data = b'\x00' + privkey + _ser32(index)
    else:
        # Normal: HMAC-SHA512(chaincode, pubkey || index)
        point = _point_from_privkey(key_int)
        pubkey = _ser_compressed_pubkey(point)
        data = pubkey + _ser32(index)

    I = _hmac_sha512(chaincode, data)
    IL, IR = I[:32], I[32:]

    child_int = (_parse256(IL) + key_int) % SECP256k1.order
    if _parse256(IL) >= SECP256k1.order or child_int == 0:
        raise ValueError(f"Invalid child key at index {index}")

    return child_int.to_bytes(32, "big"), IR


def _privkey_to_wif(privkey: bytes, compressed: bool = True) -> str:
    """Convert raw 32-byte private key to WIF format (mainnet)."""
    payload = b'\x80' + privkey
    if compressed:
        payload += b'\x01'
    return base58.b58encode_check(payload).decode("ascii")


def seed_phrase_to_wif(mnemonic: str, passphrase: str = "") -> str:
    """
    Derive BCH WIF private key from BIP39 seed phrase.

    Uses derivation path m/44'/145'/0'/0/0 (BCH mainnet, first address).

    Args:
        mnemonic: BIP39 seed phrase (12 or 24 words)
        passphrase: Optional BIP39 passphrase (default: empty)

    Returns:
        WIF-encoded private key (compressed, mainnet)
    """
    # Normalize mnemonic
    words = mnemonic.strip().lower().split()
    if len(words) not in (12, 15, 18, 21, 24):
        raise ValueError(f"Invalid mnemonic: expected 12-24 words, got {len(words)}")
    mnemonic_clean = " ".join(words)

    # BIP39: mnemonic → seed
    seed = _pbkdf2_seed(mnemonic_clean, passphrase)

    # BIP32: seed → master key
    privkey, chaincode = _master_key(seed)

    # Derive path m/44'/145'/0'/0/0
    for index in BCH_DERIVATION_PATH:
        privkey, chaincode = _derive_child(privkey, chaincode, index)

    return _privkey_to_wif(privkey)
