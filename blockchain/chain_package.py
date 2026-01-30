"""
Chain Package - Package Qube data for IPFS storage

Creates encrypted packages containing all Qube data for:
- Backup to IPFS (Sync to Pinata)
- Transfer to new owner
- Recovery from NFT

Package Format:
    - Header: Magic bytes + version
    - Encrypted payload: AES-256-GCM encrypted JSON blob
    - Contains: genesis, blocks, chain_state, relationships, skills, avatar, metadata
"""

import json
import hashlib
import secrets
import base64
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass, asdict
from datetime import datetime

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from core.exceptions import EncryptionError, DecryptionError, CryptoError
from utils.logging import get_logger

logger = get_logger(__name__)

# Package constants
PACKAGE_MAGIC = b"QUBE"
PACKAGE_VERSION = 1
NONCE_SIZE = 12
KEY_SIZE = 32


@dataclass
class QubePackageMetadata:
    """Metadata about the packaged Qube"""
    qube_id: str
    qube_name: str
    public_key: str
    chain_length: int
    merkle_root: str
    package_version: str = "1.0"
    packaged_at: int = 0  # Unix timestamp
    packaged_by: str = ""  # User who created package
    has_nft: bool = False
    nft_category_id: Optional[str] = None


@dataclass
class QubePackageData:
    """
    Complete Qube data structure for packaging.

    This represents everything needed to fully restore a Qube.
    """
    # Metadata
    metadata: QubePackageMetadata

    # Identity (from genesis block)
    genesis_block: Dict[str, Any]

    # Memory chain
    memory_blocks: List[Dict[str, Any]]
    chain_state: Dict[str, Any]

    # Social
    relationships: Optional[Dict[str, Any]] = None

    # Skills
    skills: Optional[Dict[str, Any]] = None
    skill_history: Optional[List[Dict[str, Any]]] = None

    # Avatar (base64 encoded)
    avatar_data: Optional[str] = None
    avatar_filename: Optional[str] = None

    # NFT/Blockchain
    nft_metadata: Optional[Dict[str, Any]] = None
    bcmr_data: Optional[Dict[str, Any]] = None


def create_chain_package(
    qube_dir: Path,
    qube_id: str,
    qube_name: str,
    public_key: str,
    genesis_block: Dict[str, Any],
    user_id: str,
    has_nft: bool = False,
    nft_category_id: Optional[str] = None,
    encryption_key: Optional[bytes] = None
) -> Tuple[bytes, bytes]:
    """
    Create an encrypted chain package from Qube data.

    Args:
        qube_dir: Path to the Qube's data directory
        qube_id: Qube ID
        qube_name: Qube name
        public_key: Qube's public key (hex)
        genesis_block: Genesis block data
        user_id: ID of user creating the package
        has_nft: Whether Qube has an NFT
        nft_category_id: NFT category ID if minted
        encryption_key: Optional encryption key for reading encrypted chain_state.
                       If not provided, chain_state is read as plain JSON (legacy mode).

    Returns:
        Tuple of (encrypted_package_bytes, symmetric_key)

    Raises:
        EncryptionError: If packaging fails
    """
    try:
        logger.info(
            "creating_chain_package",
            qube_id=qube_id,
            qube_name=qube_name
        )

        # Collect all Qube data
        package_data = _collect_qube_data(
            qube_dir=qube_dir,
            qube_id=qube_id,
            qube_name=qube_name,
            public_key=public_key,
            genesis_block=genesis_block,
            user_id=user_id,
            has_nft=has_nft,
            nft_category_id=nft_category_id,
            encryption_key=encryption_key
        )

        # Serialize to JSON
        package_json = json.dumps(asdict(package_data), ensure_ascii=False)
        package_bytes = package_json.encode('utf-8')

        # Generate symmetric key
        symmetric_key = secrets.token_bytes(KEY_SIZE)

        # Encrypt with AES-256-GCM
        nonce = secrets.token_bytes(NONCE_SIZE)
        aesgcm = AESGCM(symmetric_key)
        ciphertext = aesgcm.encrypt(nonce, package_bytes, None)

        # Create package: magic + version + nonce + ciphertext
        encrypted_package = (
            PACKAGE_MAGIC +
            bytes([PACKAGE_VERSION]) +
            nonce +
            ciphertext
        )

        logger.info(
            "chain_package_created",
            qube_id=qube_id,
            package_size=len(encrypted_package),
            block_count=len(package_data.memory_blocks),
            has_relationships=package_data.relationships is not None,
            has_skills=package_data.skills is not None
        )

        return encrypted_package, symmetric_key

    except Exception as e:
        import traceback
        logger.error(
            "chain_package_creation_failed",
            qube_id=qube_id,
            error=str(e),
            traceback=traceback.format_exc()
        )
        # Include actual error details in message for debugging
        raise EncryptionError(
            f"Failed to create chain package for {qube_name}: {str(e)}",
            context={"qube_id": qube_id},
            cause=e
        )


def unpack_chain_package(
    encrypted_package: bytes,
    symmetric_key: bytes
) -> QubePackageData:
    """
    Decrypt and unpack a chain package.

    Args:
        encrypted_package: Encrypted package bytes
        symmetric_key: AES-256 key for decryption

    Returns:
        QubePackageData with all Qube data

    Raises:
        DecryptionError: If unpacking fails (wrong key, corrupted data)
    """
    try:
        # Validate magic bytes
        if not encrypted_package.startswith(PACKAGE_MAGIC):
            raise ValueError("Invalid package format: wrong magic bytes")

        offset = len(PACKAGE_MAGIC)

        # Read version
        version = encrypted_package[offset]
        if version != PACKAGE_VERSION:
            raise ValueError(f"Unsupported package version: {version}")
        offset += 1

        # Extract nonce
        nonce = encrypted_package[offset:offset + NONCE_SIZE]
        offset += NONCE_SIZE

        # Extract ciphertext
        ciphertext = encrypted_package[offset:]

        # Decrypt
        aesgcm = AESGCM(symmetric_key)
        package_bytes = aesgcm.decrypt(nonce, ciphertext, None)

        # Parse JSON
        package_dict = json.loads(package_bytes.decode('utf-8'))

        # Convert to dataclass
        metadata = QubePackageMetadata(**package_dict['metadata'])
        package_data = QubePackageData(
            metadata=metadata,
            genesis_block=package_dict['genesis_block'],
            memory_blocks=package_dict['memory_blocks'],
            chain_state=package_dict['chain_state'],
            relationships=package_dict.get('relationships'),
            skills=package_dict.get('skills'),
            skill_history=package_dict.get('skill_history'),
            avatar_data=package_dict.get('avatar_data'),
            avatar_filename=package_dict.get('avatar_filename'),
            nft_metadata=package_dict.get('nft_metadata'),
            bcmr_data=package_dict.get('bcmr_data')
        )

        logger.info(
            "chain_package_unpacked",
            qube_id=metadata.qube_id,
            block_count=len(package_data.memory_blocks)
        )

        return package_data

    except Exception as e:
        logger.error(
            "chain_package_unpack_failed",
            error=str(e)
        )
        raise DecryptionError(
            "Failed to unpack chain package - wrong key or corrupted data",
            cause=e
        )


def verify_package_integrity(package_data: QubePackageData) -> bool:
    """
    Verify the integrity of unpacked data by checking merkle root.

    Args:
        package_data: Unpacked Qube data

    Returns:
        True if integrity verified, False otherwise
    """
    try:
        # Calculate merkle root from blocks
        block_hashes = []

        # Add genesis block hash
        genesis_hash = package_data.genesis_block.get('block_hash', '')
        if genesis_hash:
            block_hashes.append(genesis_hash)

        # Add memory block hashes
        for block in package_data.memory_blocks:
            block_hash = block.get('block_hash', '')
            if block_hash:
                block_hashes.append(block_hash)

        # Calculate merkle root
        calculated_root = _calculate_merkle_root(block_hashes)

        # Compare with stored merkle root
        stored_root = package_data.metadata.merkle_root

        if calculated_root == stored_root:
            logger.info(
                "package_integrity_verified",
                qube_id=package_data.metadata.qube_id,
                merkle_root=stored_root[:16] + "..."
            )
            return True
        else:
            logger.warning(
                "package_integrity_failed",
                qube_id=package_data.metadata.qube_id,
                expected=stored_root[:16] + "...",
                calculated=calculated_root[:16] + "..."
            )
            return False

    except Exception as e:
        logger.error(
            "package_integrity_check_failed",
            error=str(e)
        )
        return False


def _collect_qube_data(
    qube_dir: Path,
    qube_id: str,
    qube_name: str,
    public_key: str,
    genesis_block: Dict[str, Any],
    user_id: str,
    has_nft: bool,
    nft_category_id: Optional[str],
    encryption_key: Optional[bytes] = None
) -> QubePackageData:
    """
    Collect all Qube data from filesystem.

    Args:
        encryption_key: If provided, chain_state is read using ChainState class
                       with decryption. If None, falls back to plain JSON read.
    """
    from core.chain_state import ChainState

    # Load memory blocks
    memory_blocks = _load_memory_blocks(qube_dir)

    # Load chain state (using ChainState class if encryption_key provided)
    if encryption_key:
        try:
            chain_dir = qube_dir / "chain"
            cs = ChainState(chain_dir, encryption_key, qube_id)
            chain_state = cs.get_state()  # Returns full state, not just settings
        except Exception as e:
            logger.warning(f"Failed to read encrypted chain_state, falling back to plain JSON: {e}")
            chain_state = _load_json_file(qube_dir / "chain" / "chain_state.json") or {}
    else:
        chain_state = _load_json_file(qube_dir / "chain" / "chain_state.json") or {}

    # Load relationships from chain_state if available, otherwise fall back to file
    relationships = chain_state.get("relationships") if chain_state else None
    if relationships is None:
        relationships = _load_json_file(qube_dir / "relationships" / "relationships.json")

    # Load skills from chain_state if available, otherwise fall back to file
    skills = chain_state.get("skills") if chain_state else None
    if skills is None:
        skills = _load_json_file(qube_dir / "skills" / "skills.json")

    skill_history = chain_state.get("skill_history") if chain_state else None
    if skill_history is None:
        skill_history = _load_json_list(qube_dir / "skills" / "skill_history.json")

    # Load avatar
    avatar_data, avatar_filename = _load_avatar(qube_dir, qube_id)

    # Load NFT metadata
    nft_metadata = _load_json_file(qube_dir / "chain" / "nft_metadata.json")

    # Load BCMR data
    bcmr_data = _load_json_file(qube_dir / "blockchain" / f"{qube_name}_bcmr.json")

    # Calculate merkle root
    block_hashes = [genesis_block.get('block_hash', '')]
    block_hashes.extend([b.get('block_hash', '') for b in memory_blocks])
    merkle_root = _calculate_merkle_root(block_hashes)

    # Create metadata
    metadata = QubePackageMetadata(
        qube_id=qube_id,
        qube_name=qube_name,
        public_key=public_key,
        chain_length=len(memory_blocks) + 1,  # +1 for genesis
        merkle_root=merkle_root,
        packaged_at=int(datetime.utcnow().timestamp()),
        packaged_by=user_id,
        has_nft=has_nft,
        nft_category_id=nft_category_id
    )

    return QubePackageData(
        metadata=metadata,
        genesis_block=genesis_block,
        memory_blocks=memory_blocks,
        chain_state=chain_state,
        relationships=relationships,
        skills=skills,
        skill_history=skill_history,
        avatar_data=avatar_data,
        avatar_filename=avatar_filename,
        nft_metadata=nft_metadata,
        bcmr_data=bcmr_data
    )


def _load_memory_blocks(qube_dir: Path) -> List[Dict[str, Any]]:
    """Load all permanent memory blocks."""
    blocks = []
    blocks_dir = qube_dir / "blocks" / "permanent"

    if not blocks_dir.exists():
        return blocks

    # Sort by block number (filename starts with block_number)
    block_files = sorted(
        blocks_dir.glob("*.json"),
        key=lambda f: int(f.stem.split('_')[0]) if f.stem.split('_')[0].isdigit() else 0
    )

    for block_file in block_files:
        # Skip genesis (block 0) - it's handled separately
        if block_file.stem.startswith("0_"):
            continue

        try:
            with open(block_file, 'r', encoding='utf-8') as f:
                blocks.append(json.load(f))
        except Exception as e:
            logger.warning(f"Failed to load block {block_file}: {e}")

    return blocks


def _load_json_file(path: Path) -> Optional[Dict[str, Any]]:
    """Load a JSON file, return None if not found."""
    if not path.exists():
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load {path}: {e}")
        return None


def _load_json_list(path: Path) -> Optional[List[Dict[str, Any]]]:
    """Load a JSON list file, return None if not found."""
    if not path.exists():
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load {path}: {e}")
        return None


def _load_avatar(qube_dir: Path, qube_id: str) -> Tuple[Optional[str], Optional[str]]:
    """Load avatar image as base64, return (data, filename)."""
    chain_dir = qube_dir / "chain"

    # Try different extensions
    for ext in ['png', 'jpg', 'jpeg', 'webp']:
        avatar_path = chain_dir / f"{qube_id}_avatar.{ext}"
        if avatar_path.exists():
            try:
                with open(avatar_path, 'rb') as f:
                    avatar_data = base64.b64encode(f.read()).decode('ascii')
                return avatar_data, avatar_path.name
            except Exception as e:
                logger.warning(f"Failed to load avatar {avatar_path}: {e}")

    return None, None


def _calculate_merkle_root(hashes: List[str]) -> str:
    """
    Calculate Merkle root from list of hashes.

    Args:
        hashes: List of hex-encoded hashes

    Returns:
        Hex-encoded Merkle root
    """
    if not hashes:
        return hashlib.sha256(b"empty").hexdigest()

    # Filter out empty hashes
    hashes = [h for h in hashes if h]

    if not hashes:
        return hashlib.sha256(b"empty").hexdigest()

    # Convert to bytes
    nodes = [bytes.fromhex(h) for h in hashes]

    # Build tree bottom-up
    while len(nodes) > 1:
        # If odd number, duplicate last
        if len(nodes) % 2 == 1:
            nodes.append(nodes[-1])

        # Combine pairs
        new_nodes = []
        for i in range(0, len(nodes), 2):
            combined = nodes[i] + nodes[i + 1]
            new_nodes.append(hashlib.sha256(combined).digest())

        nodes = new_nodes

    return nodes[0].hex()


# =============================================================================
# IMPORT/RESTORE FUNCTIONS
# =============================================================================

def restore_qube_from_package(
    package_data: QubePackageData,
    target_dir: Path,
    new_encrypted_private_key: Dict[str, Any],
    encryption_key: Optional[bytes] = None
) -> bool:
    """
    Restore a Qube from unpacked package data.

    Args:
        package_data: Unpacked Qube data
        target_dir: Directory to restore to
        new_encrypted_private_key: Private key encrypted with new owner's password
        encryption_key: Optional encryption key for writing encrypted chain_state.
                       If provided, chain_state is written encrypted. If None,
                       falls back to plain JSON (legacy mode).

    Returns:
        True if successful
    """
    try:
        qube_id = package_data.metadata.qube_id
        qube_name = package_data.metadata.qube_name

        logger.info(
            "restoring_qube_from_package",
            qube_id=qube_id,
            qube_name=qube_name,
            target_dir=str(target_dir),
            encrypted=encryption_key is not None
        )

        # Create directory structure (only essential dirs - skills/relationships now in chain_state)
        (target_dir / "blocks" / "permanent").mkdir(parents=True, exist_ok=True)
        (target_dir / "blocks" / "session").mkdir(parents=True, exist_ok=True)
        (target_dir / "chain").mkdir(parents=True, exist_ok=True)
        (target_dir / "blockchain").mkdir(parents=True, exist_ok=True)

        # Save genesis block
        genesis_path = target_dir / "chain" / "genesis.json"
        with open(genesis_path, 'w', encoding='utf-8') as f:
            json.dump(package_data.genesis_block, f, indent=2)

        # Also save to blocks/permanent
        genesis_block_path = target_dir / "blocks" / "permanent" / f"0_GENESIS_{package_data.genesis_block.get('timestamp', 0)}.json"
        with open(genesis_block_path, 'w', encoding='utf-8') as f:
            json.dump(package_data.genesis_block, f, indent=2)

        # Save memory blocks
        for block in package_data.memory_blocks:
            block_num = block.get('block_number', 0)
            block_type = block.get('block_type', 'UNKNOWN')
            timestamp = block.get('timestamp', 0)
            block_path = target_dir / "blocks" / "permanent" / f"{block_num}_{block_type}_{timestamp}.json"
            with open(block_path, 'w', encoding='utf-8') as f:
                json.dump(block, f, indent=2)

        # Save qube metadata with new encrypted private key
        qube_metadata = {
            "qube_id": qube_id,
            "qube_name": qube_name,
            "public_key": package_data.metadata.public_key,
            "encrypted_private_key": new_encrypted_private_key,
            "imported_from_nft": True,
            "import_timestamp": int(datetime.utcnow().timestamp())
        }
        metadata_path = target_dir / "chain" / "qube_metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(qube_metadata, f, indent=2)

        # Save chain state with encryption if key provided
        # Merge relationships and skills into chain_state for consolidated storage
        merged_chain_state = dict(package_data.chain_state) if package_data.chain_state else {}

        # Add relationships to chain_state if present
        if package_data.relationships:
            merged_chain_state["relationships"] = package_data.relationships

        # Add skills to chain_state if present
        if package_data.skills:
            merged_chain_state["skills"] = package_data.skills

        if package_data.skill_history:
            merged_chain_state["skill_history"] = package_data.skill_history

        if encryption_key:
            # Use ChainState class to write encrypted chain_state
            from core.chain_state import ChainState
            chain_dir = target_dir / "chain"
            chain_state = ChainState(chain_dir, encryption_key, qube_id)
            chain_state.update_settings(merged_chain_state)
            logger.debug("wrote_encrypted_chain_state")
        else:
            # Legacy: write plain JSON
            chain_state_path = target_dir / "chain" / "chain_state.json"
            with open(chain_state_path, 'w', encoding='utf-8') as f:
                json.dump(merged_chain_state, f, indent=2)
            logger.debug("wrote_plain_chain_state")

        # Save avatar
        if package_data.avatar_data and package_data.avatar_filename:
            avatar_path = target_dir / "chain" / package_data.avatar_filename
            avatar_bytes = base64.b64decode(package_data.avatar_data)
            with open(avatar_path, 'wb') as f:
                f.write(avatar_bytes)

        # Save NFT metadata
        if package_data.nft_metadata:
            nft_path = target_dir / "chain" / "nft_metadata.json"
            with open(nft_path, 'w', encoding='utf-8') as f:
                json.dump(package_data.nft_metadata, f, indent=2)

        # Save BCMR data
        if package_data.bcmr_data:
            bcmr_path = target_dir / "blockchain" / f"{qube_name}_bcmr.json"
            with open(bcmr_path, 'w', encoding='utf-8') as f:
                json.dump(package_data.bcmr_data, f, indent=2)

        logger.info(
            "qube_restored_from_package",
            qube_id=qube_id,
            block_count=len(package_data.memory_blocks) + 1,
            encrypted=encryption_key is not None
        )

        return True

    except Exception as e:
        logger.error(
            "qube_restore_failed",
            error=str(e)
        )
        return False
