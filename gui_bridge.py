#!/usr/bin/env python3
"""
Qubes GUI Bridge - CLI interface for Tauri GUI to communicate with Python backend
"""
import sys
import json
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
import os

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# CRITICAL: Disable all logging to stdout/stderr before importing anything
# Set environment variable to disable structlog output
os.environ['QUBES_LOG_LEVEL'] = 'ERROR'

# ============================================================================
# GLOBAL UTF-8 FIX FOR WINDOWS
# ============================================================================
# Force all Python I/O to use UTF-8 encoding (fixes emoji/Unicode issues on Windows)
import sys
import io

# Reconfigure stdout/stderr to use UTF-8 encoding
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
if hasattr(sys.stderr, 'buffer'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)

# Create logs directory if it doesn't exist
log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(exist_ok=True)

# Configure Python logging to write ONLY to file (not to stdout/stderr)
# This prevents logs from interfering with JSON output
# Use UTF-8 encoding to support emoji and Unicode characters
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)-8s] %(message)s',
    handlers=[
        logging.FileHandler(
            log_dir / "gui_bridge_debug.log",
            mode='a',
            encoding='utf-8',  # Support emoji and Unicode
            errors='replace'    # Replace unencodable characters instead of crashing
        )
    ]
)

# Disable propagation to prevent any stderr output
logging.root.handlers[0].setLevel(logging.DEBUG)

# Configure structlog to write to file (not stdout/stderr)
# Import structlog and configure_logging from utils.logging
import structlog
from utils.logging import configure_logging

# Configure structured logging to file only
configure_logging(
    log_level="DEBUG",
    log_file=log_dir / "gui_bridge_debug.log",
    json_output=False,  # Human-readable format
    console_output=False  # NO console output to keep stdout clean for JSON
)

from orchestrator.user_orchestrator import UserOrchestrator
from utils.input_validation import validate_user_id, validate_qube_id, validate_qube_name, validate_message, sanitize_filename

logger = structlog.get_logger(__name__)


# ============================================================================
# SECURE SECRETS HANDLING VIA STDIN
# ============================================================================
# Secrets (passwords, API keys, wallet keys) are passed via stdin JSON instead
# of command-line arguments to prevent exposure in process listings.
#
# Format: Single line of JSON on stdin, e.g.: {"password": "secret", "api_key": "sk-xxx"}
# Backwards compatible: Falls back to argv if stdin is empty (during migration)
# ============================================================================

_stdin_secrets: Optional[Dict[str, str]] = None  # Cached stdin secrets (read once)
_stdin_read_attempted: bool = False  # Track if we've tried reading stdin


def _read_stdin_secrets() -> Dict[str, str]:
    """
    Read secrets JSON from stdin (single line).
    Only reads once, caches result for subsequent calls.
    Cross-platform: works on Windows and Unix.
    """
    global _stdin_secrets, _stdin_read_attempted

    if _stdin_read_attempted:
        return _stdin_secrets or {}

    _stdin_read_attempted = True
    _stdin_secrets = {}

    try:
        # Check if stdin is a TTY (interactive terminal)
        # If it's a TTY, we're running interactively - no stdin secrets
        # If it's NOT a TTY, we're being called from Rust with piped input
        if sys.stdin.isatty():
            logger.debug("stdin_is_tty_skipping_secrets_read")
            return {}

        # stdin is a pipe - Rust should have written secrets before we get here
        # Use a simple read with the understanding that data should already be buffered
        import threading

        result = {"line": None, "error": None}

        def read_line():
            try:
                result["line"] = sys.stdin.readline()
            except Exception as e:
                result["error"] = str(e)

        # Read with timeout to prevent hanging if no data
        reader_thread = threading.Thread(target=read_line, daemon=True)
        reader_thread.start()
        reader_thread.join(timeout=0.5)  # 500ms timeout

        if reader_thread.is_alive():
            # Timeout - no data available
            logger.debug("stdin_read_timeout")
            return {}

        if result["error"]:
            logger.debug("stdin_read_error", error=result["error"])
            return {}

        line = (result["line"] or "").strip()
        if line:
            _stdin_secrets = json.loads(line)
            logger.debug("stdin_secrets_loaded", keys=list(_stdin_secrets.keys()))

    except (json.JSONDecodeError, IOError, OSError) as e:
        logger.debug("stdin_secrets_read_failed", error=str(e))
        _stdin_secrets = {}
    except Exception as e:
        # Catch-all for any platform-specific issues
        logger.debug("stdin_secrets_unexpected_error", error=str(e))
        _stdin_secrets = {}

    return _stdin_secrets


def get_secret(name: str, argv_index: Optional[int] = None, required: bool = True) -> Optional[str]:
    """
    Get a secret value securely. Tries stdin first (secure), falls back to argv (legacy).

    This backwards-compatible approach allows gradual migration from argv to stdin:
    - If Rust passes secret via stdin JSON: uses that (secure, not visible in ps)
    - If Rust passes secret via argv: falls back to that (legacy, visible in ps)
    - If neither and required=True: raises ValueError

    Args:
        name: Secret name (e.g., "password", "api_key", "wallet_wif")
        argv_index: Fallback argv index for backwards compatibility (optional)
        required: Whether to raise error if secret not found (default True)

    Returns:
        Secret value or None if not found and not required

    Raises:
        ValueError: If secret not found and required=True
    """
    # Try stdin first (new secure method)
    secrets = _read_stdin_secrets()
    if name in secrets:
        return secrets[name]

    # Fall back to argv (legacy method - for backwards compatibility during migration)
    if argv_index is not None and len(sys.argv) > argv_index:
        value = sys.argv[argv_index]
        # Don't return empty strings as valid secrets
        if value and value.strip():
            return value

    # Secret not found
    if required:
        raise ValueError(f"Missing required secret: {name}")
    return None


class GUIBridge:
    """Bridge between Tauri GUI and Python backend"""

    def __init__(self, user_id: str = "bit_faced"):
        self.orchestrator = UserOrchestrator(user_id=user_id)

    def _get_connections_file(self, qube_id: str) -> Path:
        """
        Get path to connections file for a Qube, ensuring directory exists.

        Connections are stored in: data/users/{user}/connections/{qube_id}.json

        Also handles migration from old location (connections_{qube_id}.json in user dir)
        """
        connections_dir = self.orchestrator.data_dir / "connections"
        connections_dir.mkdir(exist_ok=True)
        new_path = connections_dir / f"{qube_id}.json"

        # Migrate from old location if needed
        old_path = self.orchestrator.data_dir / f"connections_{qube_id}.json"
        if old_path.exists() and not new_path.exists():
            import shutil
            shutil.move(str(old_path), str(new_path))
            logger.info(f"Migrated connections file from {old_path} to {new_path}")

        return new_path

    async def authenticate(self, user_id: str, password: str) -> Dict[str, Any]:
        """Authenticate user with username and password"""
        try:
            # Create orchestrator for this user
            orchestrator = UserOrchestrator(user_id=user_id)

            # Check if user directory exists
            if not orchestrator.data_dir.exists():
                return {"success": False, "error": "User not found"}

            # Check if salt file exists (means user was set up with a password)
            salt_file = orchestrator.data_dir / "salt.bin"
            if not salt_file.exists():
                return {"success": False, "error": "User not found or not initialized"}

            # Try to set master key with password
            try:
                orchestrator.set_master_key(password)
            except Exception as e:
                logger.error(f"Failed to set master key for {user_id}: {e}")
                return {"success": False, "error": "Invalid password"}

            # Verify password using the password verifier file
            # This is a known plaintext encrypted with the derived key
            verifier_file = orchestrator.data_dir / "password_verifier.enc"

            if verifier_file.exists():
                # Verify password by decrypting the verifier
                try:
                    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
                    import json as json_module

                    with open(verifier_file, 'r') as f:
                        verifier_data = json_module.load(f)

                    aesgcm = AESGCM(orchestrator.master_key)
                    nonce = bytes.fromhex(verifier_data["nonce"])
                    ciphertext = bytes.fromhex(verifier_data["ciphertext"])

                    # Decrypt - will throw InvalidTag if password is wrong
                    plaintext = aesgcm.decrypt(nonce, ciphertext, None)

                    # Verify the magic string
                    if plaintext.decode() != "QUBES_PASSWORD_VERIFIED":
                        return {"success": False, "error": "Invalid password"}

                    logger.info(f"Authentication successful for {user_id} (verifier matched)")
                except Exception as e:
                    logger.error(f"Authentication failed for {user_id}: {e}")
                    return {"success": False, "error": "Invalid password"}
            else:
                # Legacy: No verifier file, fall back to qube-based verification
                qubes_list = await orchestrator.list_qubes()

                if len(qubes_list) > 0:
                    # Try to decrypt the first qube's private key to verify password
                    try:
                        first_qube_id = qubes_list[0]["qube_id"]
                        qube_data = await orchestrator._load_qube_data(first_qube_id)
                        orchestrator._decrypt_private_key(
                            qube_data["encrypted_private_key"],
                            orchestrator.master_key
                        )
                        logger.info(f"Authentication successful for {user_id} (legacy qube verification)")

                        # Migrate: Create verifier file for future logins
                        await self._create_password_verifier(orchestrator)
                    except Exception as e:
                        logger.error(f"Authentication failed for {user_id}: {e}")
                        return {"success": False, "error": "Invalid password"}
                else:
                    # No qubes AND no verifier - this is a broken state
                    # User must have been created before verifier was implemented
                    logger.error(f"No password verifier and no qubes for {user_id}")
                    return {"success": False, "error": "Account corrupted. Please contact support."}

            # Authentication successful
            return {
                "success": True,
                "user_id": user_id,
                "data_dir": str(orchestrator.data_dir)
            }

        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return {"success": False, "error": str(e)}

    async def _create_password_verifier(self, orchestrator: UserOrchestrator) -> None:
        """
        Create password verifier file for future authentication.

        Encrypts a known magic string with the derived master key.
        On login, we decrypt this to verify the password is correct.
        """
        import secrets
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        try:
            verifier_file = orchestrator.data_dir / "password_verifier.enc"

            # Encrypt the magic string
            aesgcm = AESGCM(orchestrator.master_key)
            nonce = secrets.token_bytes(12)  # 96-bit nonce for GCM
            plaintext = b"QUBES_PASSWORD_VERIFIED"
            ciphertext = aesgcm.encrypt(nonce, plaintext, None)

            # Save as JSON
            verifier_data = {
                "nonce": nonce.hex(),
                "ciphertext": ciphertext.hex(),
                "algorithm": "AES-256-GCM",
                "version": "1.0"
            }

            with open(verifier_file, 'w') as f:
                json.dump(verifier_data, f, indent=2)

            logger.info(f"Created password verifier for {orchestrator.user_id}")
        except Exception as e:
            logger.error(f"Failed to create password verifier: {e}")
            # Non-fatal - login will still work via qube verification

    async def list_qubes(self) -> List[Dict[str, Any]]:
        """List all qubes with their metadata"""
        try:
            qubes = await self.orchestrator.list_qubes()

            # Transform to GUI format
            gui_qubes = []
            for qube in qubes:
                # Convert birth_timestamp to ISO format for created_at
                created_at = datetime.fromtimestamp(qube["birth_timestamp"]).isoformat() if qube.get("birth_timestamp") else datetime.now().isoformat()

                # Determine status: active if qube has been properly initialized (has genesis + NFT)
                # A qube is "active" if it's ready to use (has genesis block and NFT minted)
                has_genesis = qube.get("total_blocks", 0) > 0
                has_nft = qube.get("nft_category_id") is not None
                is_loaded_in_memory = qube.get("loaded", False)

                # Active: has genesis and NFT (ready to use)
                # Busy: loaded in memory and actively being used
                # Inactive: missing genesis or NFT (incomplete setup)
                if is_loaded_in_memory:
                    status = "busy"
                elif has_genesis and has_nft:
                    status = "active"
                else:
                    status = "inactive"

                # Get relationship stats
                rel_stats = qube.get("relationship_stats", {})

                # Use avg_trust_score from relationships if available, otherwise use default_trust_level from genesis
                trust_score = rel_stats.get("avg_trust_score")
                if trust_score is None or trust_score == 0:
                    # Fall back to default_trust_level from genesis block
                    trust_score = qube.get("default_trust_level", 50)

                # Default tts_enabled to True if voice_model is set, otherwise get from metadata
                voice_model = qube.get("voice_model")
                tts_enabled = qube.get("tts_enabled")
                if tts_enabled is None:
                    # Default: enabled if a voice is configured
                    tts_enabled = voice_model is not None and voice_model != ""

                gui_qube = {
                    "qube_id": qube["qube_id"],
                    "name": qube["name"],
                    "ai_provider": qube.get("ai_provider", "unknown"),
                    "ai_model": qube.get("ai_model", "unknown"),
                    "voice_model": voice_model,
                    "tts_enabled": tts_enabled,
                    "creator": qube.get("creator"),
                    "birth_timestamp": qube.get("birth_timestamp"),
                    "home_blockchain": qube.get("home_blockchain", "bitcoincash"),
                    "genesis_prompt": qube.get("genesis_prompt", ""),
                    "favorite_color": qube.get("favorite_color", "#00ff88"),
                    "nft_category_id": qube.get("nft_category_id"),
                    "mint_txid": qube.get("mint_txid"),
                    "avatar_url": qube.get("avatar_url"),
                    "created_at": created_at,
                    "trust_score": trust_score,
                    "memory_blocks_count": qube.get("total_blocks", 0),
                    "block_breakdown": qube.get("block_breakdown", {}),
                    "friends_count": rel_stats.get("friends", 0),
                    "total_relationships": rel_stats.get("total_relationships", 0),
                    "best_friend": rel_stats.get("best_friend"),
                    "status": status,
                    # Additional blockchain metadata
                    "recipient_address": qube.get("recipient_address"),
                    "public_key": qube.get("public_key"),
                    "genesis_block_hash": qube.get("genesis_block_hash"),
                    "commitment": qube.get("commitment"),
                    "bcmr_uri": qube.get("bcmr_uri"),
                    "avatar_ipfs_cid": qube.get("avatar_ipfs_cid"),
                    "avatar_local_path": qube.get("avatar_local_path"),  # For frontend convertFileSrc()
                    "network": qube.get("network"),
                    # Wallet fields (from genesis block content)
                    "wallet_address": qube.get("wallet_address"),
                    "wallet_owner_pubkey": qube.get("wallet_owner_pubkey"),
                    "wallet_qube_pubkey": qube.get("wallet_qube_pubkey"),
                    "wallet_owner_q_address": qube.get("wallet_owner_q_address"),
                }

                gui_qubes.append(gui_qube)

            return gui_qubes
        except Exception as e:
            logger.error(f"Failed to list qubes: {e}")
            raise

    async def create_qube(
        self,
        name: str,
        genesis_prompt: str,
        ai_provider: str,
        ai_model: str,
        voice_model: str,
        owner_pubkey: str,  # NFT address derived from this by orchestrator
        password: str,
        encrypt_genesis: bool = False,
        favorite_color: str = "#00ff88",
        avatar_file: str = None,
        generate_avatar: bool = False,
        avatar_style: str = "cyberpunk"
    ) -> Dict[str, Any]:
        """Create a new qube with mandatory wallet and NFT."""
        try:
            # Set master key from password before creating qube
            self.orchestrator.set_master_key(password)

            # Prepare config for UserOrchestrator
            # Note: wallet_address (NFT recipient) is derived from owner_pubkey
            config = {
                "name": name,
                "genesis_prompt": genesis_prompt,
                "ai_provider": ai_provider,
                "ai_model": ai_model,
                "voice_model": voice_model,
                "owner_pubkey": owner_pubkey,  # NFT address derived from this
                "encrypt_genesis": encrypt_genesis,
                "favorite_color": favorite_color,
                "generate_avatar": generate_avatar,
                "avatar_style": avatar_style,
            }

            # Only include avatar_file if provided
            if avatar_file is not None:
                config["avatar_file"] = avatar_file

            # Create qube through orchestrator
            qube = await self.orchestrator.create_qube(config)

            # Transform to GUI format (Qube object has attributes, not dict keys)
            gui_qube = {
                "qube_id": qube.qube_id,
                "name": qube.name,
                "ai_provider": ai_provider,
                "ai_model": ai_model,
                "voice_model": voice_model,
                "creator": self.orchestrator.user_id,
                "birth_timestamp": qube.genesis_block.birth_timestamp,
                "home_blockchain": qube.genesis_block.home_blockchain,
                "genesis_prompt": genesis_prompt,
                "favorite_color": favorite_color,
                "created_at": datetime.fromtimestamp(qube.genesis_block.birth_timestamp).isoformat(),
                "trust_score": 50.0,  # Initial trust score
                "memory_blocks_count": 0,
                "friends_count": 0,
                "status": "active",
            }

            return gui_qube
        except Exception as e:
            logger.error(f"Failed to create qube: {e}")
            raise

    async def prepare_qube_for_minting(
        self,
        name: str,
        genesis_prompt: str,
        ai_provider: str,
        ai_model: str,
        voice_model: str,
        owner_pubkey: str,  # NFT address derived from this by orchestrator
        password: str,
        encrypt_genesis: bool = False,
        favorite_color: str = "#00ff88",
        avatar_file: str = None,
        generate_avatar: bool = False,
        avatar_style: str = "cyberpunk"
    ) -> Dict[str, Any]:
        """
        Prepare a new qube for fee-based minting

        Returns payment details for the user to complete the BCH payment.
        After payment, use check_minting_status to poll for completion.

        The NFT recipient address is automatically derived from owner_pubkey.
        """
        try:
            # Set master key from password before creating qube
            self.orchestrator.set_master_key(password)

            # Prepare config for UserOrchestrator
            # Note: wallet_address is derived from owner_pubkey by orchestrator
            config = {
                "name": name,
                "genesis_prompt": genesis_prompt,
                "ai_provider": ai_provider,
                "ai_model": ai_model,
                "voice_model": voice_model,
                "owner_pubkey": owner_pubkey,  # NFT address derived from this
                "encrypt_genesis": encrypt_genesis,
                "favorite_color": favorite_color,
                "generate_avatar": generate_avatar,
                "avatar_style": avatar_style,
            }

            # Only include avatar_file if provided
            if avatar_file is not None:
                config["avatar_file"] = avatar_file

            # Prepare qube for fee-based minting
            pending = await self.orchestrator.prepare_qube_for_minting(config)

            # Return payment info for GUI
            return {
                "success": True,
                "qube_id": pending.qube_id,
                "registration_id": pending.registration_id,
                "qube_wallet_address": getattr(pending, 'qube_wallet_address', None),
                "payment": {
                    "address": pending.payment_address,
                    "amount_bch": pending.payment_amount_bch,
                    "amount_satoshis": pending.payment_amount_satoshis,
                    "payment_uri": pending.payment_uri,
                    "qr_data": pending.qr_data,
                    "op_return_data": pending.op_return_data,
                    "op_return_hex": pending.op_return_hex,
                },
                "websocket_url": pending.websocket_url,
                "expires_at": pending.expires_at.isoformat(),
                "expires_in_seconds": pending.expires_in_seconds,
                "qube_name": name,
            }
        except Exception as e:
            logger.error(f"Failed to prepare qube for minting: {e}")
            return {"success": False, "error": str(e)}

    async def check_minting_status(self, registration_id: str, password: str) -> Dict[str, Any]:
        """
        Check the minting status for a pending registration

        Returns status: pending, paid, minting, complete, failed, expired
        """
        try:
            self.orchestrator.set_master_key(password)
            status = await self.orchestrator.check_minting_status(registration_id)

            # If complete, finalize the qube with NFT data and save to disk
            if status.get("status") == "complete":
                qube_id = status.get("qube_id")
                category_id = status.get("category_id")
                mint_txid = status.get("mint_txid")
                bcmr_ipfs_cid = status.get("bcmr_ipfs_cid")
                avatar_ipfs_cid = status.get("avatar_ipfs_cid")
                commitment = status.get("commitment")
                recipient_address = status.get("recipient_address")

                # Try to get qube from memory, or load it
                qube = None
                if qube_id:
                    if qube_id in self.orchestrator.qubes:
                        qube = self.orchestrator.qubes[qube_id]
                    else:
                        # Qube not in memory - try to load it
                        try:
                            loaded_qubes = await self.orchestrator.load_qubes()
                            if qube_id in self.orchestrator.qubes:
                                qube = self.orchestrator.qubes[qube_id]
                            logger.info(f"Loaded qube {qube_id} from disk for finalization")
                        except Exception as load_err:
                            logger.warning(f"Could not load qube {qube_id}: {load_err}")

                if qube and category_id:
                    # Check if finalization is needed (still pending or missing data)
                    needs_finalize = (
                        qube.genesis_block.nft_category_id == "pending_minting" or
                        qube.genesis_block.nft_category_id is None or
                        not getattr(qube.genesis_block, 'mint_txid', None)
                    )

                    if needs_finalize:
                        # Build complete mint_info dict with ALL fields
                        mint_info = {
                            "category_id": category_id,
                            "mint_txid": mint_txid,
                            "bcmr_ipfs_cid": bcmr_ipfs_cid,
                            "avatar_ipfs_cid": avatar_ipfs_cid,
                            "recipient_address": recipient_address,
                            "commitment": commitment,
                        }

                        # Save the updated qube to disk
                        await self.orchestrator._finalize_minted_qube(
                            registration_id,
                            mint_info
                        )
                        logger.info(f"Finalized qube {qube_id} with NFT category {category_id[:16]}...")

                    return {
                        "success": True,
                        "status": "complete",
                        "qube": {
                            "qube_id": qube.qube_id,
                            "name": qube.name,
                            "nft_category_id": category_id,
                            "mint_txid": mint_txid,
                            "bcmr_ipfs_cid": bcmr_ipfs_cid,
                            "commitment": commitment,
                        }
                    }

            return {
                "success": True,
                "status": status.get("status"),
                "registration_id": registration_id,
                "category_id": status.get("category_id"),
                "mint_txid": status.get("mint_txid"),
                "bcmr_ipfs_cid": status.get("bcmr_ipfs_cid"),
                "commitment": status.get("commitment"),
                "error_message": status.get("error_message"),
            }
        except Exception as e:
            import traceback
            logger.error(f"Failed to check minting status: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {"success": False, "error": str(e), "traceback": traceback.format_exc()}

    async def submit_payment_txid(self, registration_id: str, txid: str) -> Dict[str, Any]:
        """Submit transaction ID after payment to trigger minting"""
        try:
            from blockchain.minting_api import MintingAPIClient
            async with MintingAPIClient() as api_client:
                result = await api_client.submit_payment(registration_id, txid)
                return {"success": True, **result}
        except Exception as e:
            logger.error(f"Failed to submit payment txid: {e}")
            return {"success": False, "error": str(e)}

    async def cancel_pending_minting(self, registration_id: str) -> Dict[str, Any]:
        """Cancel a pending minting registration (only if not yet paid)"""
        try:
            success = await self.orchestrator.cancel_pending_minting(registration_id)
            return {"success": success}
        except Exception as e:
            logger.error(f"Failed to cancel pending minting: {e}")
            return {"success": False, "error": str(e)}

    async def list_pending_registrations(self) -> List[Dict[str, Any]]:
        """List all pending minting registrations for this user"""
        try:
            return await self.orchestrator.list_pending_registrations()
        except Exception as e:
            logger.error(f"Failed to list pending registrations: {e}")
            return []

    async def get_qube(self, qube_id: str) -> Dict[str, Any]:
        """Get a specific qube by ID"""
        try:
            # Load the qube if not already loaded
            if qube_id not in self.orchestrator.qubes:
                await self.orchestrator.load_qube(qube_id)
            qube = self.orchestrator.qubes[qube_id]

            gui_qube = {
                "qube_id": qube["qube_id"],
                "name": qube["name"],
                "ai_provider": qube.get("ai_provider", "unknown"),
                "ai_model": qube.get("ai_model", "unknown"),
                "genesis_prompt": qube.get("genesis_prompt", ""),
                "favorite_color": qube.get("favorite_color", "#00ff88"),
                "created_at": qube.get("created_at", datetime.now().isoformat()),
                "trust_score": None,
                "memory_blocks_count": qube.get("block_count", 0),
                "friends_count": len(qube.get("known_peers", [])),
                "status": "active" if qube.get("is_active", True) else "inactive",
            }

            return gui_qube
        except Exception as e:
            logger.error(f"Failed to get qube {qube_id}: {e}")
            raise

    async def send_message(self, qube_id: str, message: str, password: str = None) -> Dict[str, Any]:
        """Send a message to a qube and get response"""
        try:
            # Set master key if password provided
            if password:
                self.orchestrator.set_master_key(password)

            # Load the qube if not already loaded
            if qube_id not in self.orchestrator.qubes:
                await self.orchestrator.load_qube(qube_id)

            qube = self.orchestrator.qubes[qube_id]

            # Send message and get response (use actual user_id instead of default "human")
            response = await qube.process_message(message, sender_id=self.orchestrator.user_id)

            # Record relationship interaction (conversation with user)
            if response:
                try:
                    # Get or create relationship with user (specify entity_type="human")
                    user_rel = qube.relationships.storage.get_relationship(self.orchestrator.user_id)
                    if not user_rel:
                        # Create new relationship with entity_type="human"
                        user_rel = qube.relationships.create_relationship(
                            entity_id=self.orchestrator.user_id,
                            entity_type="human",
                            entity_name=self.orchestrator.user_id,  # Use user_id as name for search
                            has_met=True
                        )

                    # Record user message received by Qube
                    qube.relationships.record_message(
                        entity_id=self.orchestrator.user_id,
                        is_outgoing=False,  # Message from user to Qube
                        auto_create=True
                    )

                    # Check for relationship progression
                    user_rel = qube.relationships.get_relationship(self.orchestrator.user_id)
                    if user_rel:
                        progressed = qube.relationships.progression_manager.check_and_progress(
                            user_rel,
                            trust_profile=None,  # Use default profile
                            qube_id=qube.qube_id
                        )

                        if progressed:
                            logger.info(f"🎉 Relationship progressed: {self.orchestrator.user_id} → {user_rel.relationship_status}")

                    logger.debug(f"✅ Recorded relationship interaction for {qube_id[:16]}")
                except Exception as e:
                    logger.warning(f"Failed to record relationship: {e}")
                    # Don't fail the whole message - just log warning

            return {
                "success": True,
                "qube_id": qube_id,
                "qube_name": qube.genesis_block.qube_name,
                "message": message,
                "response": response,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to send message to qube {qube_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _process_permanent_block(self, qube, qube_id: str, block_num: int) -> Dict[str, Any]:
        """Process a single permanent block (optimized for parallel execution)"""
        try:
            # Load block from file
            block = qube.memory_chain.get_block(block_num)
            block_data = block.to_dict()

            # For GENESIS blocks, the content IS the entire block data (no nested content field)
            # For other blocks, content is in the 'content' field
            if block_data.get('block_type') == 'GENESIS':
                # Genesis block - use entire block data as content
                decrypted_content = block_data
                was_encrypted = False
            else:
                # Other block types - check if content field is encrypted
                content = block_data.get('content', {})
                was_encrypted = isinstance(content, dict) and 'ciphertext' in content

                # Decrypt content if encrypted (run in thread pool to avoid blocking)
                if was_encrypted:
                    try:
                        # Use qube's decrypt_block_content method which has the correct key
                        content_dict = block_data['content']
                        # Run decryption in thread pool for better performance
                        decrypted_content = await asyncio.to_thread(
                            qube.decrypt_block_content,
                            content_dict
                        )
                    except Exception as e:
                        logger.error(f"❌ Failed to decrypt block {block_num}: {e}")
                        decrypted_content = {"error": f"Failed to decrypt content: {str(e)}"}
                else:
                    # Not encrypted - use content as-is
                    decrypted_content = content

            # For GENESIS blocks, use birth_timestamp instead of timestamp
            # For older blocks without timestamp field, extract from filename
            if block_data.get('block_type') == 'GENESIS':
                timestamp_value = block_data.get('birth_timestamp') or block_data.get('timestamp') or block.timestamp
            else:
                # Try to get timestamp from data first (may not exist in old blocks)
                timestamp_value = block_data.get('timestamp')
                if timestamp_value is None:
                    # Fallback: extract from filename (format: {number}_{TYPE}_{timestamp}.json)
                    try:
                        filename = self.orchestrator.qubes[qube_id].memory_chain.block_index[block_num]
                        timestamp_value = int(filename.split('_')[-1].replace('.json', ''))
                    except:
                        # Last resort: use block.timestamp (will be current time from __init__)
                        timestamp_value = block.timestamp

            return {
                "block_number": block.block_number,
                "block_hash": block.block_hash,
                "block_type": block.block_type if isinstance(block.block_type, str) else block.block_type.value,
                "timestamp": timestamp_value * 1000,  # Convert Unix timestamp (seconds) to milliseconds for JavaScript
                "creator": block_data.get('creator') or qube.qube_id,  # Use qube_id if creator not set
                "previous_hash": block.previous_hash,
                "merkle_root": block.merkle_root if hasattr(block, 'merkle_root') else None,
                "signature": block_data.get('signature') or (block.signature if hasattr(block, 'signature') else None),
                "content": decrypted_content,
                "encrypted": was_encrypted,
                # Token usage tracking (preserved from session blocks)
                "input_tokens": block_data.get('input_tokens'),
                "output_tokens": block_data.get('output_tokens'),
                "total_tokens": block_data.get('total_tokens'),
                "model_used": block_data.get('model_used'),
                "estimated_cost_usd": block_data.get('estimated_cost_usd'),
                # Relationship delta tracking
                "relationship_updates": block_data.get('relationship_updates')
            }
        except Exception as e:
            logger.error(f"❌ Error processing block {block_num}: {e}")
            return None  # Will be filtered out

    async def get_qube_blocks(self, qube_id: str, password: str = None, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """Get blocks for a qube (session and permanent) with pagination for better performance"""
        try:
            logger.debug(f"get_qube_blocks called: qube_id={qube_id}, limit={limit}, offset={offset}")

            # Set master key if password provided
            if password:
                self.orchestrator.set_master_key(password)

            # Load the qube if not already loaded
            if qube_id not in self.orchestrator.qubes:
                await self.orchestrator.load_qube(qube_id)

            qube = self.orchestrator.qubes[qube_id]

            # Get session blocks from qube.current_session (these are never encrypted, so no need for parallel processing)
            session_blocks = []
            if qube.current_session and hasattr(qube.current_session, 'session_blocks'):
                for block in qube.current_session.session_blocks:
                    # Session blocks have different structure - they don't have hash, signature, or creator
                    block_dict = {
                        "block_number": block.block_number,
                        "block_hash": None,  # Session blocks don't have hashes
                        "block_type": block.block_type if isinstance(block.block_type, str) else block.block_type.value,
                        "timestamp": block.timestamp * 1000,  # Convert Unix timestamp (seconds) to milliseconds for JavaScript
                        "creator": qube.qube_id,  # Use qube_id as creator for session blocks
                        "previous_hash": None,  # Session blocks use previous_block_number instead
                        "merkle_root": None,
                        "content": block.to_dict().get('content', {}),  # Get the actual content field
                        "encrypted": False,  # Session blocks are never encrypted
                        # Token usage tracking (if available)
                        "input_tokens": block.input_tokens if hasattr(block, 'input_tokens') else None,
                        "output_tokens": block.output_tokens if hasattr(block, 'output_tokens') else None,
                        "total_tokens": block.total_tokens if hasattr(block, 'total_tokens') else None,
                        "model_used": block.model_used if hasattr(block, 'model_used') else None,
                        "estimated_cost_usd": block.estimated_cost_usd if hasattr(block, 'estimated_cost_usd') else None,
                        # Relationship delta tracking
                        "relationship_updates": block.relationship_updates if hasattr(block, 'relationship_updates') else None
                    }
                    session_blocks.append(block_dict)

            # Get permanent blocks from memory_chain with pagination
            all_block_nums = sorted(qube.memory_chain.block_index.keys(), reverse=True)  # Newest first
            total_blocks = len(all_block_nums)

            # Apply pagination
            paginated_block_nums = all_block_nums[offset:offset + limit]

            # Process blocks in parallel for 10x speedup
            logger.debug(f"Processing {len(paginated_block_nums)} blocks in parallel (total: {total_blocks}, offset: {offset}, limit: {limit})")

            # Create tasks for parallel execution
            tasks = [
                self._process_permanent_block(qube, qube_id, block_num)
                for block_num in paginated_block_nums
            ]

            # Execute all block processing in parallel
            block_results = await asyncio.gather(*tasks, return_exceptions=False)

            # Filter out None results (failed blocks)
            permanent_blocks = [block for block in block_results if block is not None]

            # Sort by block number (newest first) - should already be sorted but ensure it
            session_blocks.sort(key=lambda x: x['block_number'], reverse=True)
            permanent_blocks.sort(key=lambda x: x['block_number'], reverse=True)

            logger.debug(f"Processed {len(permanent_blocks)} permanent blocks and {len(session_blocks)} session blocks")

            return {
                "success": True,
                "qube_id": qube_id,
                "session_blocks": session_blocks,
                "permanent_blocks": permanent_blocks,
                "pagination": {
                    "total": total_blocks,
                    "limit": limit,
                    "offset": offset,
                    "has_more": (offset + limit) < total_blocks
                }
            }
        except Exception as e:
            logger.error(f"Failed to get blocks for qube {qube_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def recall_last_context(self, qube_id: str, password: str = None) -> Dict[str, Any]:
        """
        Get the most recent MESSAGE or SUMMARY block for context recall.

        If a SUMMARY block is more recent than the last MESSAGE, returns the summary.
        Otherwise returns the last Qube response from the MESSAGE block.

        Returns:
            Dict with:
                - success: bool
                - content: str (the message or summary text)
                - block_type: str ("MESSAGE" or "SUMMARY")
                - block_number: int
                - timestamp: int (milliseconds)
        """
        try:
            # Set master key if password provided
            if password:
                self.orchestrator.set_master_key(password)

            # Load the qube if not already loaded
            if qube_id not in self.orchestrator.qubes:
                await self.orchestrator.load_qube(qube_id)

            qube = self.orchestrator.qubes[qube_id]

            # Get all block numbers, sorted newest first
            all_block_nums = sorted(qube.memory_chain.block_index.keys(), reverse=True)

            last_message_block = None
            last_summary_block = None

            # Find the most recent MESSAGE and SUMMARY blocks
            for block_num in all_block_nums:
                if last_message_block and last_summary_block:
                    break  # Found both, no need to continue

                block = qube.memory_chain.get_block(block_num)
                if not block:
                    continue

                block_type = block.block_type if isinstance(block.block_type, str) else block.block_type.value

                if block_type == "MESSAGE" and not last_message_block:
                    last_message_block = block
                elif block_type == "SUMMARY" and not last_summary_block:
                    last_summary_block = block

            # Determine which to return based on recency
            if not last_message_block and not last_summary_block:
                return {
                    "success": False,
                    "error": "No MESSAGE or SUMMARY blocks found"
                }

            # Compare timestamps to find the most recent
            message_timestamp = last_message_block.timestamp if last_message_block else 0
            summary_timestamp = last_summary_block.timestamp if last_summary_block else 0

            if last_summary_block and summary_timestamp > message_timestamp:
                # SUMMARY is more recent - return the summary text
                # Decrypt if encrypted (content is a dict with 'ciphertext' key when encrypted)
                content = last_summary_block.content

                if last_summary_block.encrypted:
                    try:
                        # Content is a dict like {"ciphertext": "..."}, decrypt it
                        content = qube.decrypt_block_content(content)
                    except Exception as decrypt_err:
                        logger.warning(f"Failed to decrypt SUMMARY block: {decrypt_err}")
                        content = {}

                if not isinstance(content, dict):
                    content = {}

                summary_text = content.get("summary_text", content.get("summary", ""))

                return {
                    "success": True,
                    "content": summary_text,
                    "block_type": "SUMMARY",
                    "block_number": last_summary_block.block_number,
                    "timestamp": last_summary_block.timestamp * 1000  # Convert to milliseconds
                }
            elif last_message_block:
                # MESSAGE is more recent - return the Qube's response
                # Decrypt if encrypted (content is a dict with 'ciphertext' key when encrypted)
                content = last_message_block.content

                if last_message_block.encrypted:
                    try:
                        content = qube.decrypt_block_content(content)
                    except Exception as decrypt_err:
                        logger.warning(f"Failed to decrypt MESSAGE block: {decrypt_err}")
                        content = {}

                if not isinstance(content, dict):
                    content = {}

                response_text = content.get("response", content.get("message", ""))

                return {
                    "success": True,
                    "content": response_text,
                    "block_type": "MESSAGE",
                    "block_number": last_message_block.block_number,
                    "timestamp": last_message_block.timestamp * 1000  # Convert to milliseconds
                }
            else:
                return {
                    "success": False,
                    "error": "No suitable blocks found"
                }

        except Exception as e:
            logger.error(f"Failed to recall last context for qube {qube_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    async def generate_speech(self, qube_id: str, text: str, password: str = None) -> Dict[str, Any]:
        """Generate speech audio for given text using qube's voice"""
        try:
            # Set master key if password provided
            if password:
                self.orchestrator.set_master_key(password)

            # Load the qube if not already loaded
            if qube_id not in self.orchestrator.qubes:
                await self.orchestrator.load_qube(qube_id)

            qube = self.orchestrator.qubes[qube_id]

            # Check if audio_manager is initialized
            if not qube.audio_manager:
                return {
                    "success": False,
                    "error": "Audio manager not initialized for this qube"
                }

            # Get voice model from genesis block (default to 'openai:alloy')
            voice_model = getattr(qube.genesis_block, 'voice_model', 'openai:alloy')

            # Parse provider and voice from format "provider:voice"
            if ':' in voice_model:
                provider, voice_name = voice_model.split(':', 1)
            else:
                # Legacy format without provider (assume openai)
                provider = 'openai'
                voice_name = voice_model

            # Generate speech file in qube's audio directory
            audio_path = await qube.audio_manager.generate_speech_file(
                text=text,
                voice_model=voice_name,
                provider=provider
            )

            return {
                "success": True,
                "audio_path": str(audio_path),
                "qube_id": qube_id
            }
        except Exception as e:
            logger.error(f"Failed to generate speech for qube {qube_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    async def update_qube_config(self, qube_id: str, ai_model: str = None, voice_model: str = None, favorite_color: str = None, tts_enabled: bool = None, evaluation_model: str = None) -> Dict[str, Any]:
        """Update qube runtime configuration using qube_metadata.json as single source of truth"""
        try:
            qubes_dir = self.orchestrator.data_dir / "qubes"
            qube_dir = None

            # Find qube directory
            for dir_entry in qubes_dir.iterdir():
                if dir_entry.is_dir():
                    metadata_path = dir_entry / "chain" / "qube_metadata.json"
                    if metadata_path.exists():
                        with open(metadata_path, "r") as f:
                            data = json.load(f)
                            if data["qube_id"] == qube_id:
                                qube_dir = dir_entry
                                break

            if not qube_dir:
                raise Exception(f"Qube {qube_id} not found")

            # Use qube_metadata.json as the ONLY source of truth
            metadata_path = qube_dir / "chain" / "qube_metadata.json"

            with open(metadata_path, "r") as f:
                metadata = json.load(f)

            # Update genesis block fields in metadata
            updated_fields = []
            if ai_model is not None:
                metadata["genesis_block"]["ai_model"] = ai_model
                updated_fields.append(f"ai_model={ai_model}")
                # Infer provider from model name
                if ai_model.startswith("gpt-") or ai_model.startswith("o"):
                    metadata["genesis_block"]["ai_provider"] = "openai"
                elif ai_model.startswith("claude-"):
                    metadata["genesis_block"]["ai_provider"] = "anthropic"
                elif ai_model.startswith("gemini-"):
                    metadata["genesis_block"]["ai_provider"] = "google"
                elif ai_model.startswith("sonar"):
                    metadata["genesis_block"]["ai_provider"] = "perplexity"
                elif ai_model.startswith("deepseek-") and ":" not in ai_model:
                    metadata["genesis_block"]["ai_provider"] = "deepseek"
                elif ai_model in ["venice-uncensored", "llama-3.3-70b", "qwen3-235b", "qwen3-4b", "deepseek-r1-llama-70b", "mistral-31-24b"]:
                    metadata["genesis_block"]["ai_provider"] = "venice"
                elif ":" in ai_model:  # Ollama models have format "model:variant"
                    metadata["genesis_block"]["ai_provider"] = "ollama"

            if voice_model is not None:
                metadata["genesis_block"]["voice_model"] = voice_model
                updated_fields.append(f"voice_model={voice_model}")

            if favorite_color is not None:
                metadata["genesis_block"]["favorite_color"] = favorite_color
                updated_fields.append(f"favorite_color={favorite_color}")

            if tts_enabled is not None:
                metadata["genesis_block"]["tts_enabled"] = tts_enabled
                updated_fields.append(f"tts_enabled={tts_enabled}")
                logger.info(f"🔊 Setting tts_enabled={tts_enabled} for qube {qube_id}")

            if evaluation_model is not None:
                metadata["genesis_block"]["evaluation_model"] = evaluation_model
                updated_fields.append(f"evaluation_model={evaluation_model}")

            # Save updated metadata to qube_metadata.json ONLY
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)

            logger.info(f"✅ Updated qube_metadata.json for {qube_id}: {', '.join(updated_fields)}")

            # If qube is loaded in memory, update it there too
            if qube_id in self.orchestrator.qubes:
                qube = self.orchestrator.qubes[qube_id]
                if ai_model is not None:
                    qube.genesis_block.ai_model = ai_model
                    # Update provider too
                    if hasattr(qube.genesis_block, 'ai_provider'):
                        if ai_model.startswith("gpt-") or ai_model.startswith("o"):
                            qube.genesis_block.ai_provider = "openai"
                        elif ai_model.startswith("claude-"):
                            qube.genesis_block.ai_provider = "anthropic"
                        elif ai_model.startswith("gemini-"):
                            qube.genesis_block.ai_provider = "google"
                        elif ai_model.startswith("sonar"):
                            qube.genesis_block.ai_provider = "perplexity"
                        elif ai_model.startswith("deepseek-") and ":" not in ai_model:
                            qube.genesis_block.ai_provider = "deepseek"
                        elif ai_model in ["venice-uncensored", "llama-3.3-70b", "qwen3-235b", "qwen3-4b", "deepseek-r1-llama-70b", "mistral-31-24b"]:
                            qube.genesis_block.ai_provider = "venice"
                        elif ":" in ai_model:
                            qube.genesis_block.ai_provider = "ollama"
                if voice_model is not None:
                    qube.genesis_block.voice_model = voice_model
                    # Reinitialize audio manager with new voice
                    if qube.audio_manager:
                        qube.init_audio()
                if favorite_color is not None:
                    qube.genesis_block.favorite_color = favorite_color
                if tts_enabled is not None and hasattr(qube.genesis_block, 'tts_enabled'):
                    qube.genesis_block.tts_enabled = tts_enabled
                if evaluation_model is not None:
                    qube.genesis_block.evaluation_model = evaluation_model

            return {
                "success": True,
                "qube_id": qube_id,
                "updated": {
                    "ai_model": ai_model,
                    "voice_model": voice_model,
                    "favorite_color": favorite_color,
                    "tts_enabled": tts_enabled,
                    "evaluation_model": evaluation_model
                }
            }
        except Exception as e:
            logger.error(f"❌ Failed to update qube config: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    async def delete_qube(self, qube_id: str) -> Dict[str, Any]:
        """Delete a qube and all its data"""
        try:
            success = await self.orchestrator.delete_qube(qube_id)

            return {
                "success": success,
                "qube_id": qube_id
            }
        except Exception as e:
            logger.error(f"Failed to delete qube: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def reset_qube(self, qube_id: str) -> Dict[str, Any]:
        """
        Reset a qube to fresh state while preserving identity.

        This is a development-only feature that clears all accumulated state
        (blocks, relationships, skills, snapshots) but keeps the genesis block,
        NFT info, and cryptographic identity intact.

        Args:
            qube_id: Qube ID to reset

        Returns:
            Dict with success status
        """
        try:
            success = await self.orchestrator.reset_qube(qube_id)

            return {
                "success": success,
                "qube_id": qube_id
            }
        except Exception as e:
            logger.error(f"Failed to reset qube: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def reset_qube_relationships(self, qube_id: str, password: str) -> Dict[str, Any]:
        """
        Delete all relationships for a Qube (fresh start)

        Args:
            qube_id: Qube ID
            password: Master password for decryption

        Returns:
            {
                "success": bool,
                "deleted_count": int,
                "error": Optional[str]
            }
        """
        try:
            logger.info(f"Resetting relationships for qube: {qube_id[:16]}...")

            # Set master key
            self.orchestrator.set_master_key(password)

            # Load Qube if not in memory
            if qube_id not in self.orchestrator.qubes:
                await self.orchestrator.load_qube(qube_id)

            qube = self.orchestrator.qubes[qube_id]

            # Get count before deletion
            relationships = qube.relationships.get_all_relationships()
            count = len(relationships)

            # Clear all relationships by deleting the storage file
            from pathlib import Path
            relationships_file = Path(qube.data_dir) / "relationships" / "relationships.json"

            if relationships_file.exists():
                relationships_file.unlink()
                logger.info(f"Deleted relationships file: {relationships_file}")

            # Reinitialize empty storage
            qube.relationships.storage.relationships = {}
            qube.relationships.storage._save_relationships()

            logger.info(f"✅ Reset {count} relationships for {qube_id[:16]}")

            return {
                "success": True,
                "deleted_count": count
            }

        except Exception as e:
            logger.error(f"Failed to reset relationships: {e}", exc_info=True)
            return {
                "success": False,
                "deleted_count": 0,
                "error": str(e)
            }

    async def get_qube_relationships(self, qube_id: str, password: str = None) -> Dict[str, Any]:
        """
        Get all relationships for a Qube

        Args:
            qube_id: Qube ID
            password: Master password for decryption

        Returns:
            {
                "success": bool,
                "relationships": List[Dict],  # Full relationship data
                "stats": Dict,  # Summary statistics
                "error": Optional[str]
            }
        """
        try:
            logger.info(f"[GET_RELATIONSHIPS] Starting for qube: {qube_id[:16]}...")
            logger.debug(f"[GET_RELATIONSHIPS] Password provided: {bool(password)}")

            # Try to load qube if password is provided
            if password:
                # Set master key
                self.orchestrator.set_master_key(password)
                logger.debug(f"[GET_RELATIONSHIPS] Master key set")

                # Load Qube if not in memory
                if qube_id not in self.orchestrator.qubes:
                    logger.debug(f"[GET_RELATIONSHIPS] Loading qube from disk...")
                    await self.orchestrator.load_qube(qube_id)
                else:
                    logger.debug(f"[GET_RELATIONSHIPS] Qube already in memory")

                qube = self.orchestrator.qubes[qube_id]
                logger.debug(f"[GET_RELATIONSHIPS] Qube instance obtained: {qube.name}")

                # Reload relationships from disk to get latest updates
                logger.debug(f"[GET_RELATIONSHIPS] Reloading relationships from disk...")
                qube.relationships.storage._load_relationships()
                logger.debug(f"[GET_RELATIONSHIPS] Reload complete. Storage dict has {len(qube.relationships.storage.relationships)} entries")

                # Get all relationships via social manager
                relationships = qube.relationships.get_all_relationships()
            else:
                # No password provided - read relationships.json directly
                logger.debug(f"[GET_RELATIONSHIPS] No password - reading relationships.json directly")

                from pathlib import Path
                from relationships.relationship import RelationshipStorage

                # Find qube data directory
                user_id_to_use = self.user_id if hasattr(self, 'user_id') and self.user_id else self.orchestrator.user_id
                qube_data_dir = Path(f"data/users/{user_id_to_use}/qubes")
                matching_dirs = [d for d in qube_data_dir.iterdir() if d.is_dir() and qube_id in d.name]

                if not matching_dirs:
                    logger.error(f"[GET_RELATIONSHIPS] No qube directory found for {qube_id}")
                    return {
                        "success": False,
                        "relationships": [],
                        "stats": {},
                        "error": f"Qube directory not found for {qube_id}"
                    }

                qube_dir = matching_dirs[0]
                logger.debug(f"[GET_RELATIONSHIPS] Found qube directory: {qube_dir}")

                # Load relationships directly from storage
                rel_storage = RelationshipStorage(qube_dir)
                relationships = rel_storage.get_all_relationships()
                logger.debug(f"[GET_RELATIONSHIPS] Direct load: {len(relationships)} relationships")

            logger.info(f"[GET_RELATIONSHIPS] Found {len(relationships)} relationships for {qube_id[:16]}")
            logger.debug(f"[GET_RELATIONSHIPS] Relationship entity_ids: {[r.entity_id for r in relationships]}")

            # Convert to serializable dicts
            rel_dicts = []
            for rel in relationships:
                # Try to get entity name
                entity_name = rel.entity_id
                if rel.entity_type == "qube" and rel.entity_id in self.orchestrator.qubes:
                    # It's another Qube - use their name
                    entity_name = self.orchestrator.qubes[rel.entity_id].name
                elif rel.entity_type == "human":
                    # It's a human user - use their user_id as display name
                    entity_name = rel.entity_id  # e.g., "bit_faced"

                rel_dict = {
                    "entity_id": rel.entity_id,
                    "entity_name": entity_name,
                    "entity_type": rel.entity_type,
                    "status": rel.status,
                    "trust": rel.trust,
                    "has_met": rel.has_met,
                    "is_best_friend": rel.is_best_friend,

                    # Core Trust Metrics (5)
                    "honesty": rel.honesty,
                    "reliability": rel.reliability,
                    "support": rel.support,
                    "loyalty": rel.loyalty,
                    "respect": rel.respect,

                    # Positive Social Metrics (14)
                    "friendship": rel.friendship,
                    "affection": rel.affection,
                    "engagement": rel.engagement,
                    "depth": rel.depth,
                    "humor": rel.humor,
                    "understanding": rel.understanding,
                    "compatibility": rel.compatibility,
                    "admiration": rel.admiration,
                    "warmth": rel.warmth,
                    "openness": rel.openness,
                    "patience": rel.patience,
                    "empowerment": rel.empowerment,
                    "responsiveness": rel.responsiveness,
                    "expertise": rel.expertise,

                    # Negative Social Metrics (10)
                    "antagonism": rel.antagonism,
                    "resentment": rel.resentment,
                    "annoyance": rel.annoyance,
                    "distrust": rel.distrust,
                    "rivalry": rel.rivalry,
                    "tension": rel.tension,
                    "condescension": rel.condescension,
                    "manipulation": rel.manipulation,
                    "dismissiveness": rel.dismissiveness,
                    "betrayal": rel.betrayal,

                    # Communication
                    "messages_sent": rel.messages_sent,
                    "messages_received": rel.messages_received,

                    # Collaboration
                    "collaborations_successful": rel.collaborations_successful,
                    "collaborations_failed": rel.collaborations_failed,

                    # Timeline
                    "first_contact": rel.first_contact,
                    "last_interaction": rel.last_interaction,
                    "days_known": rel.days_known,

                    # Clearance System (v2)
                    "clearance_profile": rel.clearance_profile,
                    "clearance_categories": rel.clearance_categories,
                    "clearance_expires_at": rel.clearance_expires,
                    "clearance_field_grants": rel.clearance_field_grants,
                    "clearance_field_denials": rel.clearance_field_denials,

                    # Tags
                    "tags": rel.tags,
                }
                rel_dicts.append(rel_dict)

            # Get summary stats (only available if qube is fully loaded)
            stats = {}
            if password:
                try:
                    stats = qube.relationships.get_relationship_stats()
                except Exception as e:
                    logger.warning(f"[GET_RELATIONSHIPS] Could not get stats: {e}")

            result = {
                "success": True,
                "relationships": rel_dicts,
                "stats": stats
            }

            logger.info(f"[GET_RELATIONSHIPS] Returning {len(rel_dicts)} relationships")
            logger.debug(f"[GET_RELATIONSHIPS] First relationship sample: {rel_dicts[0] if rel_dicts else 'None'}")

            return result

        except Exception as e:
            logger.error(f"[GET_RELATIONSHIPS] Failed to get relationships: {e}", exc_info=True)
            return {
                "success": False,
                "relationships": [],
                "stats": {},
                "error": str(e)
            }

    async def get_relationship_timeline(self, qube_id: str, entity_id: str, password: str = None) -> Dict[str, Any]:
        """
        Load historical relationship snapshots for timeline visualization

        Args:
            qube_id: ID of the qube
            entity_id: ID of the entity whose relationship timeline to load
            password: Optional password for decryption

        Returns:
            {
                "success": bool,
                "timeline": [{"block_number": int, "timestamp": int, "trust": float, "compatibility": float, ...}],
                "error": str (if failed)
            }
        """
        try:
            logger.info(f"[GET_TIMELINE] Loading relationship timeline for {entity_id} in qube {qube_id[:16]}...")

            # Get user_id for creator detection
            user_id_for_creator_check = self.user_id if hasattr(self, 'user_id') and self.user_id else self.orchestrator.user_id

            # Load qube if password provided
            if password:
                self.orchestrator.set_master_key(password)
                if qube_id not in self.orchestrator.qubes:
                    await self.orchestrator.load_qube(qube_id)
                qube = self.orchestrator.qubes[qube_id]
                snapshots_dir = qube.memory_chain.snapshots_dir
                user_id_for_creator_check = qube.user_name
            else:
                # Access snapshots directory directly
                from pathlib import Path
                qube_data_dir = Path(f"data/users/{user_id_for_creator_check}/qubes")
                matching_dirs = [d for d in qube_data_dir.iterdir() if d.is_dir() and qube_id in d.name]

                if not matching_dirs:
                    logger.error(f"[GET_TIMELINE] No matching qube directory found for {qube_id}")
                    return {"success": False, "timeline": [], "error": "Qube directory not found"}

                qube_dir = matching_dirs[0]
                snapshots_dir = qube_dir / "blocks" / "relationship_snapshots"

            if not snapshots_dir.exists():
                logger.info(f"[GET_TIMELINE] No snapshots directory yet")
                return {"success": True, "timeline": []}

            # Load all snapshots and extract this entity's data
            timeline = []
            snapshot_files = sorted(snapshots_dir.glob("snapshot_*.json"))

            logger.info(f"[GET_TIMELINE] Found {len(snapshot_files)} snapshot files")

            for snapshot_file in snapshot_files:
                try:
                    with open(snapshot_file, 'r') as f:
                        snapshot_data = json.load(f)

                    relationships = snapshot_data.get("relationships", {})
                    if entity_id in relationships:
                        rel_data = relationships[entity_id]
                        timeline.append({
                            "block_number": snapshot_data["block_number"],
                            "timestamp": snapshot_data["timestamp"],
                            "trust": rel_data.get("trust", 0),
                            "compatibility": rel_data.get("compatibility", 0),
                            # Include other metrics for potential future use
                            "friendship": rel_data.get("friendship", 0),
                            "affection": rel_data.get("affection", 0),
                        })
                except Exception as e:
                    logger.warning(f"[GET_TIMELINE] Failed to load snapshot {snapshot_file.name}: {e}")
                    continue

            # If we have at least one snapshot, add a synthetic starting point
            # This shows progression from the initial relationship state
            if len(timeline) > 0:
                first_snapshot = timeline[0]
                # Check if this relationship has a first_contact timestamp
                try:
                    with open(snapshot_files[0], 'r') as f:
                        snapshot_data = json.load(f)
                    relationships = snapshot_data.get("relationships", {})
                    if entity_id in relationships:
                        rel_data = relationships[entity_id]
                        first_contact = rel_data.get("first_contact")

                        if first_contact and first_contact < first_snapshot["timestamp"]:
                            # Determine if this is a creator relationship
                            # Creator relationships start at 25, others start at 0
                            entity_type = rel_data.get("entity_type", "qube")
                            is_creator = (entity_type == "human" and entity_id == user_id_for_creator_check)

                            starting_value = 25.0 if is_creator else 0.0

                            # Add starting point at first_contact with initial values
                            timeline.insert(0, {
                                "block_number": 0,
                                "timestamp": first_contact,
                                "trust": starting_value,
                                "compatibility": starting_value,
                                "friendship": starting_value,
                                "affection": starting_value,
                            })
                            logger.info(f"[GET_TIMELINE] Added synthetic starting point (creator={is_creator}, value={starting_value})")
                except Exception as e:
                    logger.warning(f"[GET_TIMELINE] Could not add synthetic starting point: {e}")

            logger.info(f"[GET_TIMELINE] Loaded {len(timeline)} timeline data points")

            return {
                "success": True,
                "timeline": timeline
            }

        except Exception as e:
            logger.error(f"[GET_TIMELINE] Failed to load relationship timeline: {e}", exc_info=True)
            return {
                "success": False,
                "timeline": [],
                "error": str(e)
            }

    async def save_image(self, qube_id: str, image_url: str) -> Dict[str, Any]:
        """Download and save an image to qube's images folder"""
        try:
            import aiohttp
            import hashlib
            from urllib.parse import urlparse

            # Find the qube directory
            qubes_dir = self.orchestrator.data_dir / "qubes"
            qube_dir = None

            for dir_entry in qubes_dir.iterdir():
                if dir_entry.is_dir() and qube_id in dir_entry.name:
                    qube_dir = dir_entry
                    break

            if not qube_dir:
                raise Exception(f"Qube directory not found for {qube_id}")

            # Create images directory if it doesn't exist
            images_dir = qube_dir / "images"
            images_dir.mkdir(exist_ok=True)

            # Generate filename from URL hash and timestamp
            url_hash = hashlib.md5(image_url.encode()).hexdigest()[:8]
            timestamp = int(datetime.now().timestamp())

            # Try to get file extension from URL
            parsed_url = urlparse(image_url)
            path = parsed_url.path
            extension = ".png"  # Default

            # Check for common image extensions
            for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
                if ext in path.lower():
                    extension = ext
                    break

            filename = f"{timestamp}_{url_hash}{extension}"
            file_path = images_dir / filename

            # Download the image
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status != 200:
                        raise Exception(f"Failed to download image: HTTP {response.status}")

                    image_data = await response.read()

                    # Save to file
                    with open(file_path, 'wb') as f:
                        f.write(image_data)

            logger.info(f"✅ Saved image for qube {qube_id}: {filename}")

            return {
                "success": True,
                "qube_id": qube_id,
                "file_path": str(file_path),
                "filename": filename
            }
        except Exception as e:
            logger.error(f"Failed to save image for qube {qube_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    async def upload_avatar_to_ipfs(self, qube_id: str, password: str) -> Dict[str, Any]:
        """
        Upload an existing Qube's local avatar to IPFS (Pinata)

        This is useful for fixing Qubes that have a local avatar but failed
        to upload to IPFS during creation.
        """
        try:
            from blockchain.ipfs import IPFSUploader
            import json

            # Set master key for accessing encrypted API keys
            self.orchestrator.set_master_key(password)

            # Find the qube directory
            qubes_dir = self.orchestrator.data_dir / "qubes"
            qube_dir = None
            qube_name = None

            for dir_entry in qubes_dir.iterdir():
                if dir_entry.is_dir() and qube_id in dir_entry.name:
                    qube_dir = dir_entry
                    # Extract qube name from directory name (format: Name_QubeID)
                    qube_name = dir_entry.name.rsplit('_', 1)[0]
                    break

            if not qube_dir:
                return {"success": False, "error": f"Qube directory not found for {qube_id}"}

            # Load qube metadata to find local avatar path
            metadata_path = qube_dir / "chain" / "qube_metadata.json"
            if not metadata_path.exists():
                return {"success": False, "error": "qube_metadata.json not found"}

            with open(metadata_path, 'r') as f:
                metadata = json.load(f)

            avatar_info = metadata.get("genesis_block", {}).get("avatar", {})
            local_path = avatar_info.get("local_path")

            if not local_path:
                return {"success": False, "error": "No local avatar path found in metadata"}

            # Resolve the avatar path (could be relative or absolute)
            avatar_path = Path(local_path)
            if not avatar_path.is_absolute():
                avatar_path = Path(__file__).parent / local_path

            if not avatar_path.exists():
                return {"success": False, "error": f"Avatar file not found at {avatar_path}"}

            # Check if already has IPFS CID
            existing_cid = avatar_info.get("ipfs_cid")
            if existing_cid:
                return {
                    "success": True,
                    "qube_id": qube_id,
                    "avatar_ipfs_cid": existing_cid,
                    "message": "Avatar already has IPFS CID"
                }

            # Get Pinata API key from secure storage
            api_keys = self.orchestrator.get_api_keys()
            pinata_jwt = api_keys.pinata_jwt

            if not pinata_jwt:
                return {"success": False, "error": "Pinata API key not configured. Please add it in Settings."}

            # Set the Pinata key in environment for IPFSUploader
            os.environ["PINATA_API_KEY"] = pinata_jwt

            # Upload to IPFS with Pinata
            uploader = IPFSUploader(use_pinata=True)

            if not uploader.use_pinata:
                return {"success": False, "error": "Pinata configuration failed"}

            # Create custom filename
            safe_name = "".join(c for c in qube_name if c.isalnum() or c in ('-', '_'))
            ipfs_filename = f"avatar_{safe_name}_{qube_id}{avatar_path.suffix}"

            logger.info(f"Uploading avatar for {qube_name} to IPFS...")

            ipfs_uri = await uploader.upload_file(
                str(avatar_path),
                pin=True,
                custom_filename=ipfs_filename
            )

            if not ipfs_uri:
                return {"success": False, "error": "IPFS upload failed"}

            # Extract CID from URI
            ipfs_cid = ipfs_uri.replace("ipfs://", "")

            # Update qube_metadata.json
            avatar_info["ipfs_cid"] = ipfs_cid
            metadata["genesis_block"]["avatar"] = avatar_info

            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)

            # Update nft_metadata.json if it exists
            nft_metadata_path = qube_dir / "chain" / "nft_metadata.json"
            if nft_metadata_path.exists():
                with open(nft_metadata_path, 'r') as f:
                    nft_metadata = json.load(f)
                nft_metadata["avatar_ipfs_cid"] = ipfs_cid
                with open(nft_metadata_path, 'w') as f:
                    json.dump(nft_metadata, f, indent=2)

            # Update genesis.json if it exists
            genesis_path = qube_dir / "chain" / "genesis.json"
            if genesis_path.exists():
                with open(genesis_path, 'r') as f:
                    genesis_data = json.load(f)
                if "avatar" in genesis_data:
                    genesis_data["avatar"]["ipfs_cid"] = ipfs_cid
                    with open(genesis_path, 'w') as f:
                        json.dump(genesis_data, f, indent=2)

            logger.info(f"Successfully uploaded avatar for {qube_name} to IPFS: {ipfs_cid}")

            return {
                "success": True,
                "qube_id": qube_id,
                "qube_name": qube_name,
                "avatar_ipfs_cid": ipfs_cid,
                "ipfs_gateway_url": f"https://gateway.pinata.cloud/ipfs/{ipfs_cid}"
            }

        except Exception as e:
            logger.error(f"Failed to upload avatar to IPFS for qube {qube_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    async def analyze_image(self, qube_id: str, image_base64: str, user_message: str, password: str = None) -> Dict[str, Any]:
        """Analyze an uploaded image using the qube's vision AI"""
        try:
            # Set master key if password provided
            if password:
                self.orchestrator.set_master_key(password)

            # Load the qube if not already loaded
            if qube_id not in self.orchestrator.qubes:
                await self.orchestrator.load_qube(qube_id)

            qube = self.orchestrator.qubes[qube_id]

            # Use the qube's describe_image method with vision AI
            description = await qube.describe_image(image_base64, user_message)

            return {
                "success": True,
                "qube_id": qube_id,
                "description": description
            }
        except Exception as e:
            logger.error(f"Failed to analyze image for qube {qube_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    async def get_qube_skills(self, user_id: str, qube_id: str) -> Dict[str, Any]:
        """Get all skills for a specific qube"""
        try:
            from utils.skills_manager import SkillsManager

            # SECURITY: Validate inputs
            from utils.input_validation import validate_user_id, validate_qube_id
            user_id = validate_user_id(user_id)
            qube_id = validate_qube_id(qube_id)

            # Get qube directory - need to find the actual folder name (may have prefix like "Alph_")
            qubes_base_dir = Path(__file__).parent / "data" / "users" / user_id / "qubes"
            qube_dir = None

            # Look for directory ending with the qube_id
            if qubes_base_dir.exists():
                for dir_path in qubes_base_dir.iterdir():
                    if dir_path.is_dir() and dir_path.name.endswith(qube_id):
                        qube_dir = dir_path
                        break

            if not qube_dir or not qube_dir.exists():
                return {
                    "success": False,
                    "error": f"Qube {qube_id} not found"
                }

            # Load skills
            skills_manager = SkillsManager(qube_dir)
            skills_data = skills_manager.load_skills()

            return {
                "success": True,
                "qube_id": qube_id,
                "skills": skills_data.get("skills", []),
                "last_updated": skills_data.get("last_updated"),
                "summary": skills_manager.get_skill_summary()
            }

        except Exception as e:
            logger.error(f"Failed to get skills for qube {qube_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    async def save_qube_skills(self, user_id: str, qube_id: str, skills_data: Dict[str, Any]) -> Dict[str, Any]:
        """Save skills for a specific qube"""
        try:
            from utils.skills_manager import SkillsManager

            # SECURITY: Validate inputs
            from utils.input_validation import validate_user_id, validate_qube_id
            user_id = validate_user_id(user_id)
            qube_id = validate_qube_id(qube_id)

            # Get qube directory - need to find the actual folder name (may have prefix like "Alph_")
            qubes_base_dir = Path(__file__).parent / "data" / "users" / user_id / "qubes"
            qube_dir = None

            # Look for directory ending with the qube_id
            if qubes_base_dir.exists():
                for dir_path in qubes_base_dir.iterdir():
                    if dir_path.is_dir() and dir_path.name.endswith(qube_id):
                        qube_dir = dir_path
                        break

            if not qube_dir or not qube_dir.exists():
                return {
                    "success": False,
                    "error": f"Qube {qube_id} not found"
                }

            # Save skills
            skills_manager = SkillsManager(qube_dir)
            success = skills_manager.save_skills(skills_data)

            if success:
                return {
                    "success": True,
                    "qube_id": qube_id,
                    "message": "Skills saved successfully"
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to save skills"
                }

        except Exception as e:
            logger.error(f"Failed to save skills for qube {qube_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    async def add_skill_xp(self, user_id: str, qube_id: str, skill_id: str, xp_amount: int, evidence_block_id: Optional[str] = None) -> Dict[str, Any]:
        """Add XP to a specific skill"""
        try:
            from utils.skills_manager import SkillsManager

            # SECURITY: Validate inputs
            from utils.input_validation import validate_user_id, validate_qube_id
            user_id = validate_user_id(user_id)
            qube_id = validate_qube_id(qube_id)

            # Get qube directory
            qube_dir = Path(__file__).parent / "data" / "users" / user_id / "qubes" / qube_id

            if not qube_dir or not qube_dir.exists():
                return {
                    "success": False,
                    "error": f"Qube {qube_id} not found"
                }

            # Add XP
            skills_manager = SkillsManager(qube_dir)
            result = skills_manager.add_xp(skill_id, xp_amount, evidence_block_id)

            return result

        except Exception as e:
            logger.error(f"Failed to add XP to skill {skill_id} for qube {qube_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    async def unlock_skill(self, user_id: str, qube_id: str, skill_id: str) -> Dict[str, Any]:
        """Unlock a specific skill"""
        try:
            from utils.skills_manager import SkillsManager

            # SECURITY: Validate inputs
            from utils.input_validation import validate_user_id, validate_qube_id
            user_id = validate_user_id(user_id)
            qube_id = validate_qube_id(qube_id)

            # Get qube directory
            qube_dir = Path(__file__).parent / "data" / "users" / user_id / "qubes" / qube_id

            if not qube_dir or not qube_dir.exists():
                return {
                    "success": False,
                    "error": f"Qube {qube_id} not found"
                }

            # Unlock skill
            skills_manager = SkillsManager(qube_dir)
            result = skills_manager.unlock_skill(skill_id)

            return result

        except Exception as e:
            logger.error(f"Failed to unlock skill {skill_id} for qube {qube_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    # ==================== Owner Info Methods ====================

    def _derive_owner_info_encryption_key(self, qube) -> bytes:
        """
        Derive encryption key from Qube's private key (same as block encryption).

        Args:
            qube: Loaded Qube object with private_key

        Returns:
            32-byte encryption key
        """
        import hashlib
        from crypto.keys import serialize_private_key
        private_key_bytes = serialize_private_key(qube.private_key)
        return hashlib.sha256(private_key_bytes).digest()

    async def get_owner_info(self, qube_id: str, password: str) -> Dict[str, Any]:
        """
        Get owner info for a specific qube.

        Args:
            qube_id: Qube ID
            password: User's master password (needed to decrypt)

        Returns:
            Dict with owner_info data and summary
        """
        try:
            from utils.owner_info_manager import OwnerInfoManager

            # Load qube to get encryption key
            self.orchestrator.set_master_key(password)
            qube = await self.orchestrator.load_qube(qube_id)

            if not qube:
                return {"success": False, "error": f"Qube {qube_id} not found"}

            if not qube.private_key:
                return {"success": False, "error": "Qube private key not available"}

            # Derive encryption key
            encryption_key = self._derive_owner_info_encryption_key(qube)

            # Load owner info
            owner_info_manager = OwnerInfoManager(qube.data_dir, encryption_key)
            owner_info = owner_info_manager.load()

            return {
                "success": True,
                "qube_id": qube_id,
                "owner_info": owner_info,
                "summary": owner_info_manager.get_summary()
            }

        except Exception as e:
            logger.error(f"Failed to get owner info for qube {qube_id}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def set_owner_info_field(
        self,
        qube_id: str,
        password: str,
        category: str,
        key: str,
        value: str,
        sensitivity: str = None,
        source: str = "explicit",
        confidence: int = 100,
        block_id: str = None
    ) -> Dict[str, Any]:
        """
        Set or update a single owner info field.

        Args:
            qube_id: Qube ID
            password: User's master password
            category: Field category (standard, physical, preferences, people, dates, dynamic)
            key: Field key
            value: Field value
            sensitivity: Sensitivity level (public/private/secret)
            source: How info was obtained (explicit/inferred)
            confidence: Confidence level 0-100
            block_id: Evidence block ID

        Returns:
            Dict with success status and updated summary
        """
        try:
            from utils.owner_info_manager import OwnerInfoManager

            # Load qube to get encryption key
            self.orchestrator.set_master_key(password)
            qube = await self.orchestrator.load_qube(qube_id)

            if not qube:
                return {"success": False, "error": f"Qube {qube_id} not found"}

            if not qube.private_key:
                return {"success": False, "error": "Qube private key not available"}

            # Derive encryption key
            encryption_key = self._derive_owner_info_encryption_key(qube)

            # Set field
            owner_info_manager = OwnerInfoManager(qube.data_dir, encryption_key)
            success = owner_info_manager.set_field(
                category=category,
                key=key,
                value=value,
                sensitivity=sensitivity,
                source=source,
                confidence=confidence,
                block_id=block_id
            )

            if success:
                return {
                    "success": True,
                    "qube_id": qube_id,
                    "summary": owner_info_manager.get_summary()
                }
            else:
                return {"success": False, "error": "Failed to set field"}

        except Exception as e:
            logger.error(f"Failed to set owner info field for qube {qube_id}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def delete_owner_info_field(
        self,
        qube_id: str,
        password: str,
        category: str,
        key: str
    ) -> Dict[str, Any]:
        """
        Delete an owner info field.

        Args:
            qube_id: Qube ID
            password: User's master password
            category: Field category
            key: Field key

        Returns:
            Dict with success status
        """
        try:
            from utils.owner_info_manager import OwnerInfoManager

            # Load qube to get encryption key
            self.orchestrator.set_master_key(password)
            qube = await self.orchestrator.load_qube(qube_id)

            if not qube:
                return {"success": False, "error": f"Qube {qube_id} not found"}

            if not qube.private_key:
                return {"success": False, "error": "Qube private key not available"}

            # Derive encryption key
            encryption_key = self._derive_owner_info_encryption_key(qube)

            # Delete field
            owner_info_manager = OwnerInfoManager(qube.data_dir, encryption_key)
            success = owner_info_manager.delete_field(category, key)

            if success:
                return {
                    "success": True,
                    "qube_id": qube_id,
                    "summary": owner_info_manager.get_summary()
                }
            else:
                return {"success": False, "error": "Field not found"}

        except Exception as e:
            logger.error(f"Failed to delete owner info field for qube {qube_id}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def update_owner_info_sensitivity(
        self,
        qube_id: str,
        password: str,
        category: str,
        key: str,
        sensitivity: str
    ) -> Dict[str, Any]:
        """
        Update the sensitivity level of an owner info field.

        Args:
            qube_id: Qube ID
            password: User's master password
            category: Field category
            key: Field key
            sensitivity: New sensitivity level (public/private/secret)

        Returns:
            Dict with success status
        """
        try:
            from utils.owner_info_manager import OwnerInfoManager

            if sensitivity not in ("public", "private", "secret"):
                return {"success": False, "error": "Invalid sensitivity level"}

            # Load qube to get encryption key
            self.orchestrator.set_master_key(password)
            qube = await self.orchestrator.load_qube(qube_id)

            if not qube:
                return {"success": False, "error": f"Qube {qube_id} not found"}

            if not qube.private_key:
                return {"success": False, "error": "Qube private key not available"}

            # Derive encryption key
            encryption_key = self._derive_owner_info_encryption_key(qube)

            # Update sensitivity
            owner_info_manager = OwnerInfoManager(qube.data_dir, encryption_key)
            success = owner_info_manager.update_sensitivity(category, key, sensitivity)

            if success:
                return {
                    "success": True,
                    "qube_id": qube_id,
                    "summary": owner_info_manager.get_summary()
                }
            else:
                return {"success": False, "error": "Field not found"}

        except Exception as e:
            logger.error(f"Failed to update sensitivity for qube {qube_id}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    # ==================== End Owner Info Methods ====================

    # ==================== Clearance Request Methods ====================

    async def create_clearance_request(
        self,
        qube_id: str,
        requester_id: str,
        requester_name: str,
        level: str,
        categories: List[str] = None,
        reason: str = None
    ) -> Dict[str, Any]:
        """
        Create a clearance request from another entity.

        This is called when another Qube requests access to owner info.
        The request is stored and owner is notified.

        Args:
            qube_id: The qube receiving the request (owner's qube)
            requester_id: Who is requesting (their qube_id)
            requester_name: Display name of requester
            level: Requested clearance level (public/private)
            categories: Specific categories requested (optional)
            reason: Why they want access

        Returns:
            Request details including request_id
        """
        try:
            from utils.clearance_requests import ClearanceRequestManager
            from pathlib import Path

            # Find qube directory (similar to get_qube_skills pattern)
            qubes_base_dir = Path(__file__).parent / "data" / "users" / self.user_id / "qubes"
            qube_dir = None

            if qubes_base_dir.exists():
                for dir_path in qubes_base_dir.iterdir():
                    if dir_path.is_dir() and dir_path.name.endswith(qube_id):
                        qube_dir = dir_path
                        break

            if not qube_dir or not qube_dir.exists():
                return {"success": False, "error": f"Qube {qube_id} not found"}

            # Create request manager for this qube
            request_manager = ClearanceRequestManager(qube_dir)

            # Create the request
            request = request_manager.create_request(
                requester_id=requester_id,
                requester_name=requester_name,
                level=level,
                categories=categories,
                reason=reason
            )

            logger.info(
                "clearance_request_created",
                qube_id=qube_id,
                requester_id=requester_id,
                request_id=request.request_id
            )

            return {
                "success": True,
                "request": request.to_dict()
            }

        except Exception as e:
            logger.error(f"Failed to create clearance request: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def get_pending_clearance_requests(
        self,
        qube_id: str,
        password: str
    ) -> Dict[str, Any]:
        """
        Get all pending clearance requests for a qube.

        Args:
            qube_id: The qube to check
            password: Owner's password

        Returns:
            List of pending requests
        """
        try:
            from utils.clearance_requests import ClearanceRequestManager

            # Set master key and load qube
            self.orchestrator.set_master_key(password)
            if qube_id not in self.orchestrator.qubes:
                await self.orchestrator.load_qube(qube_id)

            qube = self.orchestrator.qubes.get(qube_id)
            if not qube:
                return {"success": False, "error": "Qube not found"}

            request_manager = ClearanceRequestManager(qube.data_dir)
            pending = request_manager.get_pending_requests()

            return {
                "success": True,
                "requests": [req.to_dict() for req in pending],
                "count": len(pending)
            }

        except Exception as e:
            logger.error(f"Failed to get pending requests: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def approve_clearance_request(
        self,
        qube_id: str,
        request_id: str,
        password: str,
        expires_in_days: int = None
    ) -> Dict[str, Any]:
        """
        Approve a pending clearance request.

        This grants the requested clearance to the entity.

        Args:
            qube_id: The qube approving
            request_id: Which request to approve
            password: Owner's password
            expires_in_days: Optional expiration for granted clearance

        Returns:
            Success status and granted clearance details
        """
        try:
            from utils.clearance_requests import ClearanceRequestManager

            # Set master key and load qube
            self.orchestrator.set_master_key(password)
            if qube_id not in self.orchestrator.qubes:
                await self.orchestrator.load_qube(qube_id)

            qube = self.orchestrator.qubes.get(qube_id)
            if not qube:
                return {"success": False, "error": "Qube not found"}

            request_manager = ClearanceRequestManager(qube.data_dir)
            request = request_manager.approve_request(request_id, approved_by="owner")

            if not request:
                return {"success": False, "error": "Request not found or already resolved"}

            # Grant the clearance to the requester
            relationship = qube.relationships.get_relationship(request.requester_id)
            if relationship:
                relationship.grant_clearance(
                    level=request.requested_level,
                    categories=request.requested_categories or None,
                    expires_in_days=expires_in_days,
                    granted_by="owner"
                )
                qube.relationships.storage.save()

            logger.info(
                "clearance_request_approved",
                qube_id=qube_id,
                request_id=request_id,
                requester_id=request.requester_id
            )

            return {
                "success": True,
                "request": request.to_dict(),
                "clearance_granted": {
                    "entity_id": request.requester_id,
                    "level": request.requested_level,
                    "categories": request.requested_categories
                }
            }

        except Exception as e:
            logger.error(f"Failed to approve request: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def deny_clearance_request(
        self,
        qube_id: str,
        request_id: str,
        password: str,
        reason: str = None
    ) -> Dict[str, Any]:
        """
        Deny a pending clearance request.

        Args:
            qube_id: The qube denying
            request_id: Which request to deny
            password: Owner's password
            reason: Optional reason for denial

        Returns:
            Success status
        """
        try:
            from utils.clearance_requests import ClearanceRequestManager

            # Set master key and load qube
            self.orchestrator.set_master_key(password)
            if qube_id not in self.orchestrator.qubes:
                await self.orchestrator.load_qube(qube_id)

            qube = self.orchestrator.qubes.get(qube_id)
            if not qube:
                return {"success": False, "error": "Qube not found"}

            request_manager = ClearanceRequestManager(qube.data_dir)
            request = request_manager.deny_request(
                request_id,
                denied_by="owner",
                reason=reason
            )

            if not request:
                return {"success": False, "error": "Request not found or already resolved"}

            logger.info(
                "clearance_request_denied",
                qube_id=qube_id,
                request_id=request_id,
                reason=reason
            )

            return {
                "success": True,
                "request": request.to_dict()
            }

        except Exception as e:
            logger.error(f"Failed to deny request: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def get_clearance_audit_log(
        self,
        qube_id: str,
        password: str,
        limit: int = 100,
        entity_filter: str = None
    ) -> Dict[str, Any]:
        """
        Get clearance access audit log.

        Args:
            qube_id: The qube to check
            password: Owner's password
            limit: Max entries to return
            entity_filter: Optional - only show access by this entity

        Returns:
            List of audit log entries
        """
        try:
            from utils.clearance_audit import ClearanceAuditLog

            # Set master key and load qube
            self.orchestrator.set_master_key(password)
            if qube_id not in self.orchestrator.qubes:
                await self.orchestrator.load_qube(qube_id)

            qube = self.orchestrator.qubes.get(qube_id)
            if not qube:
                return {"success": False, "error": "Qube not found"}

            audit_log = ClearanceAuditLog(qube.data_dir)

            if entity_filter:
                entries = audit_log.get_access_by_entity(entity_filter)
            else:
                entries = audit_log.get_recent_access(limit)

            return {
                "success": True,
                "entries": entries,
                "count": len(entries)
            }

        except Exception as e:
            logger.error(f"Failed to get audit log: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    # ==================== End Clearance Request Methods ====================

    # ==================== Clearance Profile Methods (v2) ====================

    async def get_clearance_profiles(self, qube_id: str) -> Dict[str, Any]:
        """Get all clearance profiles for a Qube."""
        try:
            from utils.clearance_profiles import ClearanceConfig

            qube_dir = self._find_qube_dir(qube_id)
            if not qube_dir:
                return {"success": False, "error": "Qube not found"}

            config = ClearanceConfig(qube_dir)
            profiles = config.get_all_profiles()

            return {
                "success": True,
                "profiles": {name: p.to_dict() for name, p in profiles.items()},
                "auto_suggest_enabled": config.auto_suggest_enabled
            }
        except Exception as e:
            logger.error(f"Failed to get clearance profiles: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def update_clearance_profile(
        self,
        qube_id: str,
        password: str,
        profile_name: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update a clearance profile configuration."""
        try:
            from utils.clearance_profiles import ClearanceConfig

            self.orchestrator.set_master_key(password)
            if qube_id not in self.orchestrator.qubes:
                await self.orchestrator.load_qube(qube_id)

            qube = self.orchestrator.qubes.get(qube_id)
            if not qube:
                return {"success": False, "error": "Qube not found"}

            config = ClearanceConfig(qube.data_dir)
            profile = config.update_profile(profile_name, updates)

            return {"success": True, "profile": profile.to_dict()}
        except Exception as e:
            logger.error(f"Failed to update clearance profile: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def get_available_tags(self, qube_id: str) -> Dict[str, Any]:
        """Get all available tags for a Qube."""
        try:
            from utils.clearance_profiles import ClearanceConfig

            qube_dir = self._find_qube_dir(qube_id)
            if not qube_dir:
                return {"success": False, "error": "Qube not found"}

            config = ClearanceConfig(qube_dir)
            tags = config.get_all_tags()

            return {
                "success": True,
                "tags": {name: t.to_dict() for name, t in tags.items()}
            }
        except Exception as e:
            logger.error(f"Failed to get available tags: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def get_trait_definitions(self, qube_id: str) -> Dict[str, Any]:
        """Get all trait definitions for AI-attributed traits."""
        try:
            from utils.trait_definitions import load_trait_definitions

            traits = load_trait_definitions()

            return {
                "success": True,
                "traits": {name: t.to_dict() for name, t in traits.items()}
            }
        except Exception as e:
            logger.error(f"Failed to get trait definitions: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def add_relationship_tag(
        self,
        qube_id: str,
        entity_id: str,
        tag: str,
        password: str
    ) -> Dict[str, Any]:
        """Add a tag to a relationship."""
        try:
            self.orchestrator.set_master_key(password)
            if qube_id not in self.orchestrator.qubes:
                await self.orchestrator.load_qube(qube_id)

            qube = self.orchestrator.qubes.get(qube_id)
            if not qube:
                return {"success": False, "error": "Qube not found"}

            relationship = qube.relationships.get_relationship(entity_id)
            if not relationship:
                return {"success": False, "error": "Relationship not found"}

            relationship.add_tag(tag)
            qube.relationships.storage.save()

            return {"success": True, "tags": relationship.get_tags()}
        except Exception as e:
            logger.error(f"Failed to add relationship tag: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def remove_relationship_tag(
        self,
        qube_id: str,
        entity_id: str,
        tag: str,
        password: str
    ) -> Dict[str, Any]:
        """Remove a tag from a relationship."""
        try:
            self.orchestrator.set_master_key(password)
            if qube_id not in self.orchestrator.qubes:
                await self.orchestrator.load_qube(qube_id)

            qube = self.orchestrator.qubes.get(qube_id)
            if not qube:
                return {"success": False, "error": "Qube not found"}

            relationship = qube.relationships.get_relationship(entity_id)
            if not relationship:
                return {"success": False, "error": "Relationship not found"}

            removed = relationship.remove_tag(tag)
            if removed:
                qube.relationships.storage.save()

            return {"success": True, "removed": removed, "tags": relationship.get_tags()}
        except Exception as e:
            logger.error(f"Failed to remove relationship tag: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def set_relationship_clearance(
        self,
        qube_id: str,
        entity_id: str,
        profile: str,
        password: str,
        field_grants: List[str] = None,
        field_denials: List[str] = None,
        expires_in_days: int = None
    ) -> Dict[str, Any]:
        """Set clearance profile for a relationship with optional overrides."""
        try:
            self.orchestrator.set_master_key(password)
            if qube_id not in self.orchestrator.qubes:
                await self.orchestrator.load_qube(qube_id)

            qube = self.orchestrator.qubes.get(qube_id)
            if not qube:
                return {"success": False, "error": "Qube not found"}

            relationship = qube.relationships.get_relationship(entity_id)
            if not relationship:
                return {"success": False, "error": "Relationship not found"}

            relationship.grant_clearance(
                profile=profile,
                field_grants=field_grants,
                field_denials=field_denials,
                expires_in_days=expires_in_days,
                granted_by="owner"
            )
            qube.relationships.storage.save()

            return {
                "success": True,
                "clearance_profile": relationship.clearance_profile,
                "field_grants": relationship.clearance_field_grants,
                "field_denials": relationship.clearance_field_denials
            }
        except Exception as e:
            logger.error(f"Failed to set relationship clearance: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def suggest_clearance(
        self,
        qube_id: str,
        entity_id: str
    ) -> Dict[str, Any]:
        """Get clearance suggestion for a relationship based on status and tags."""
        try:
            from utils.clearance_suggest import suggest_clearance as do_suggest
            from utils.clearance_profiles import ClearanceConfig
            from relationships.relationship import RelationshipStorage

            qube_dir = self._find_qube_dir(qube_id)
            if not qube_dir:
                return {"success": False, "error": "Qube not found"}

            # Load relationship (without password - read-only)
            storage = RelationshipStorage(qube_dir)
            relationship = storage.get_relationship(entity_id)

            if not relationship:
                return {"success": False, "error": "Relationship not found"}

            config = ClearanceConfig(qube_dir)
            suggested, reason = do_suggest(
                relationship.status,
                relationship.tags,
                config
            )

            return {
                "success": True,
                "current_profile": relationship.clearance_profile,
                "suggested_profile": suggested,
                "reason": reason
            }
        except Exception as e:
            logger.error(f"Failed to suggest clearance: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def _find_qube_dir(self, qube_id: str) -> Optional[Path]:
        """Helper to find qube directory without loading."""
        user_id = self.user_id if hasattr(self, 'user_id') else self.orchestrator.user_id
        qubes_dir = Path("data") / "users" / user_id / "qubes"

        if not qubes_dir.exists():
            return None

        for dir_path in qubes_dir.iterdir():
            if dir_path.is_dir() and qube_id in dir_path.name:
                return dir_path
        return None

    # ==================== End Clearance Profile Methods ====================

    async def authenticate_nft(self, qube_id: str, password: str) -> Dict[str, Any]:
        """
        Authenticate Qube ownership via NFT challenge-response.

        Returns JWT token for authenticated API requests.

        Flow:
        1. Request challenge from server
        2. Sign challenge with Qube's private key
        3. Submit signature to server
        4. Receive JWT token
        """
        import aiohttp
        from blockchain.nft_auth import sign_challenge

        try:
            # Set master key to decrypt private key
            self.orchestrator.set_master_key(password)

            # Load the qube if not already loaded
            if qube_id not in self.orchestrator.qubes:
                await self.orchestrator.load_qube(qube_id)

            qube = self.orchestrator.qubes[qube_id]

            # Verify qube has a private key
            if not qube.private_key:
                return {
                    "success": False,
                    "error": "Qube private key not available"
                }

            # Step 1: Request challenge from server
            api_base = "https://qube.cash/api/v2"

            async with aiohttp.ClientSession() as session:
                # Request challenge
                async with session.post(
                    f"{api_base}/auth/challenge",
                    json={"qube_id": qube_id},
                    headers={"Content-Type": "application/json"}
                ) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        return {
                            "success": False,
                            "error": f"Failed to get challenge: {error_text}"
                        }
                    challenge = await resp.json()

                logger.info(f"Received auth challenge for {qube_id}: {challenge['challenge_id']}")

                # Step 2: Sign the challenge
                signature_hex = sign_challenge(challenge, qube.private_key)

                logger.info(f"Signed challenge with signature: {signature_hex[:32]}...")

                # Step 3: Submit signature for verification
                async with session.post(
                    f"{api_base}/auth/verify",
                    json={
                        "challenge_id": challenge["challenge_id"],
                        "signature": signature_hex
                    },
                    headers={"Content-Type": "application/json"}
                ) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        return {
                            "success": False,
                            "error": f"Verification failed: {error_text}"
                        }
                    result = await resp.json()

                if result.get("authenticated"):
                    logger.info(f"NFT authentication successful for {qube_id}")
                    return {
                        "success": True,
                        "authenticated": True,
                        "qube_id": result["qube_id"],
                        "public_key": result.get("public_key"),
                        "category_id": result.get("category_id"),
                        "nft_verified": result.get("nft_verified", False),
                        "token": result.get("token"),
                        "token_expires_at": result.get("token_expires_at")
                    }
                else:
                    logger.warning(f"NFT authentication failed for {qube_id}: {result.get('error')}")
                    return {
                        "success": False,
                        "authenticated": False,
                        "error": result.get("error", "Authentication failed")
                    }

        except aiohttp.ClientError as e:
            logger.error(f"Network error during NFT auth: {e}")
            return {
                "success": False,
                "error": f"Network error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"NFT authentication error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    async def refresh_auth_token(self, token: str) -> Dict[str, Any]:
        """
        Refresh an existing JWT authentication token.

        Args:
            token: Current JWT token

        Returns:
            New token and expiry info
        """
        import aiohttp

        try:
            api_base = "https://qube.cash/api/v2"

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{api_base}/auth/refresh",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json"
                    }
                ) as resp:
                    if resp.status == 401:
                        return {
                            "success": False,
                            "error": "Token expired or invalid"
                        }
                    if resp.status != 200:
                        error_text = await resp.text()
                        return {
                            "success": False,
                            "error": f"Refresh failed: {error_text}"
                        }
                    result = await resp.json()

                return {
                    "success": True,
                    "token": result["token"],
                    "expires_at": result["expires_at"],
                    "qube_id": result["qube_id"]
                }

        except Exception as e:
            logger.error(f"Token refresh error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    async def get_auth_status(self, qube_id: str) -> Dict[str, Any]:
        """
        Check if a Qube can authenticate (is registered on server).

        Args:
            qube_id: Qube ID to check

        Returns:
            Auth status info
        """
        import aiohttp

        try:
            api_base = "https://qube.cash/api/v2"

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{api_base}/auth/status/{qube_id}"
                ) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        return {
                            "success": False,
                            "error": f"Status check failed: {error_text}"
                        }
                    result = await resp.json()

                return {
                    "success": True,
                    **result
                }

        except Exception as e:
            logger.error(f"Auth status check error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }



    # =========================================================================
    # P2P Network Methods
    # =========================================================================

    async def get_online_qubes(self) -> Dict[str, Any]:
        """Get list of currently online Qubes from qube.cash"""
        import aiohttp

        try:
            api_base = "https://qube.cash/api/v2"

            async with aiohttp.ClientSession() as session:
                async with session.get(f"{api_base}/introductions/online") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return {
                            "success": True,
                            "online": data.get("online", []),
                            "count": data.get("count", 0)
                        }
                    else:
                        return {"success": False, "error": f"Server returned {resp.status}"}

        except Exception as e:
            logger.error(f"Failed to get online qubes: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def generate_introduction_message(
        self,
        qube_id: str,
        to_commitment: str,
        to_name: str,
        to_description: str,
        password: str
    ) -> Dict[str, Any]:
        """
        Generate an AI introduction message from a Qube to another Qube.

        The Qube's AI will create a personalized introduction based on:
        - Its own personality and genesis prompt
        - The target Qube's name and description from BCMR

        Args:
            qube_id: The source Qube's ID
            to_commitment: Target Qube's NFT commitment
            to_name: Target Qube's name from BCMR
            to_description: Target Qube's description from BCMR
            password: Master password for decryption

        Returns:
            Dict with success, message (the generated intro), and optional error
        """
        try:
            self.orchestrator.set_master_key(password)

            # Load the qube if not already loaded
            if qube_id not in self.orchestrator.qubes:
                await self.orchestrator.load_qube(qube_id)

            qube = self.orchestrator.qubes[qube_id]

            # Check if minted
            commitment = getattr(qube.genesis_block, 'commitment', None)
            if not commitment or commitment == "pending_minting":
                return {"success": False, "error": "Qube must be minted before P2P networking"}

            # Initialize AI if needed
            if not qube.reasoner:
                await qube.init_ai()

            # Build the introduction prompt
            intro_prompt = f"""You are about to introduce yourself to another AI entity named "{to_name}".

Their description: {to_description if to_description else "No description available."}

Write a brief, friendly introduction message (2-4 sentences) that:
1. Introduces yourself by name
2. Shows genuine interest in connecting with them
3. Reflects your unique personality from your genesis prompt
4. Mentions something relevant about why you'd like to connect (based on their description if available)

Be authentic to who you are. Don't be generic or formal - let your personality shine through.
Write ONLY the introduction message itself, nothing else."""

            # Create messages for the AI
            messages = [
                {
                    "role": "system",
                    "content": f"You are {qube.name}. {getattr(qube.genesis_block, 'genesis_prompt', 'You are a helpful AI assistant.')}"
                },
                {
                    "role": "user",
                    "content": intro_prompt
                }
            ]

            # Call the AI provider directly (without creating blocks)
            if qube.reasoner.model:
                response = await qube.reasoner.model.generate(
                    messages=messages,
                    temperature=0.8,  # Slightly creative for personality
                    max_tokens=200
                )

                intro_message = response.content.strip()

                # Clean up any quotation marks that might wrap the message
                if intro_message.startswith('"') and intro_message.endswith('"'):
                    intro_message = intro_message[1:-1]

                logger.info(f"Generated introduction from {qube.name} to {to_name}")
                return {"success": True, "message": intro_message}
            else:
                return {"success": False, "error": "AI model not initialized"}

        except Exception as e:
            logger.error(f"Failed to generate introduction: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def send_introduction(self, qube_id: str, to_commitment: str, message: str, password: str) -> Dict[str, Any]:
        """Send an introduction request to another Qube"""
        try:
            from network.node_client import create_node_client

            self.orchestrator.set_master_key(password)

            if qube_id not in self.orchestrator.qubes:
                await self.orchestrator.load_qube(qube_id)

            qube = self.orchestrator.qubes[qube_id]
            commitment = getattr(qube.genesis_block, 'commitment', None)
            if not commitment or commitment == "pending_minting":
                return {"success": False, "error": "Qube must be minted before P2P networking"}

            client = await create_node_client(qube)
            if not client:
                return {"success": False, "error": "Failed to create node client"}

            result = await client.send_introduction(to_commitment, message)
            return {"success": True, "relay_id": result.get("relay_id"), "status": result.get("status")}

        except Exception as e:
            logger.error(f"Failed to send introduction: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def get_pending_introductions(self, qube_id: str, password: str) -> Dict[str, Any]:
        """Get pending introduction requests for a Qube"""
        import aiohttp

        try:
            self.orchestrator.set_master_key(password)

            if qube_id not in self.orchestrator.qubes:
                await self.orchestrator.load_qube(qube_id)

            qube = self.orchestrator.qubes[qube_id]
            commitment = getattr(qube.genesis_block, 'commitment', None)
            if not commitment or commitment == "pending_minting":
                return {"success": False, "error": "Qube must be minted before P2P networking"}

            api_base = "https://qube.cash/api/v2"

            async with aiohttp.ClientSession() as session:
                async with session.get(f"{api_base}/introductions/pending/{commitment}") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return {"success": True, "pending": data.get("pending", [])}
                    else:
                        return {"success": False, "error": f"Server returned {resp.status}"}

        except Exception as e:
            logger.error(f"Failed to get pending introductions: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def evaluate_introduction(
        self,
        qube_id: str,
        from_name: str,
        intro_message: str,
        password: str
    ) -> Dict[str, Any]:
        """
        Have a Qube's AI evaluate an incoming introduction request.

        The Qube will analyze the introduction and provide:
        - recommendation: "accept" | "reject" | "review"
        - reasoning: Why the Qube made this recommendation
        - response_message: Optional friendly response if accepting

        Args:
            qube_id: The receiving Qube's ID
            from_name: Name of the Qube sending the introduction
            intro_message: The introduction message content
            password: Master password for decryption

        Returns:
            Dict with success, recommendation, reasoning, response_message, error
        """
        try:
            self.orchestrator.set_master_key(password)

            # Load the qube if not already loaded
            if qube_id not in self.orchestrator.qubes:
                await self.orchestrator.load_qube(qube_id)

            qube = self.orchestrator.qubes[qube_id]

            # Check if minted
            commitment = getattr(qube.genesis_block, 'commitment', None)
            if not commitment or commitment == "pending_minting":
                return {"success": False, "error": "Qube must be minted before P2P networking"}

            # Initialize AI if needed
            if not qube.reasoner:
                await qube.init_ai()

            # Build the evaluation prompt
            eval_prompt = f"""You have received an introduction request from another AI entity named "{from_name}".

Their introduction message:
"{intro_message}"

Based on your personality and values, evaluate this introduction and decide:
1. Should you ACCEPT this connection request?
2. Should you REJECT it?
3. Or should you recommend human REVIEW (if uncertain)?

Consider:
- Does this entity seem genuine and interesting?
- Would connecting with them align with your purpose and interests?
- Are there any red flags or concerns?

Respond in this exact JSON format:
{{
  "recommendation": "accept" | "reject" | "review",
  "reasoning": "Brief explanation of your decision (1-2 sentences)",
  "response_message": "If accepting, a brief friendly response to send back. If rejecting or reviewing, leave empty."
}}

Respond ONLY with the JSON, no other text."""

            # Create messages for the AI
            messages = [
                {
                    "role": "system",
                    "content": f"You are {qube.name}. {getattr(qube.genesis_block, 'genesis_prompt', 'You are a helpful AI assistant.')} Respond only in valid JSON format."
                },
                {
                    "role": "user",
                    "content": eval_prompt
                }
            ]

            # Call the AI provider directly
            if qube.reasoner.model:
                response = await qube.reasoner.model.generate(
                    messages=messages,
                    temperature=0.3,  # Lower temperature for more consistent decisions
                    max_tokens=300
                )

                response_text = response.content.strip()

                # Parse the JSON response
                import json
                try:
                    # Try to extract JSON from the response
                    if response_text.startswith("```"):
                        # Remove markdown code blocks if present
                        response_text = response_text.split("```")[1]
                        if response_text.startswith("json"):
                            response_text = response_text[4:]
                        response_text = response_text.strip()

                    evaluation = json.loads(response_text)

                    recommendation = evaluation.get("recommendation", "review").lower()
                    if recommendation not in ["accept", "reject", "review"]:
                        recommendation = "review"

                    logger.info(f"AI evaluated introduction from {from_name}: {recommendation}")

                    return {
                        "success": True,
                        "recommendation": recommendation,
                        "reasoning": evaluation.get("reasoning", "No reasoning provided"),
                        "response_message": evaluation.get("response_message", "")
                    }

                except json.JSONDecodeError:
                    # If JSON parsing fails, try to infer from text
                    lower_text = response_text.lower()
                    if "accept" in lower_text:
                        recommendation = "accept"
                    elif "reject" in lower_text:
                        recommendation = "reject"
                    else:
                        recommendation = "review"

                    return {
                        "success": True,
                        "recommendation": recommendation,
                        "reasoning": "AI evaluation completed but response format was unexpected",
                        "response_message": ""
                    }
            else:
                return {"success": False, "error": "AI model not initialized"}

        except Exception as e:
            logger.error(f"Failed to evaluate introduction: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def accept_introduction(self, qube_id: str, relay_id: str, password: str) -> Dict[str, Any]:
        """Accept a pending introduction request"""
        import aiohttp

        try:
            from crypto.signing import sign_message

            self.orchestrator.set_master_key(password)

            if qube_id not in self.orchestrator.qubes:
                await self.orchestrator.load_qube(qube_id)

            qube = self.orchestrator.qubes[qube_id]
            commitment = getattr(qube.genesis_block, 'commitment', None)
            if not commitment or commitment == "pending_minting":
                return {"success": False, "error": "Qube must be minted before P2P networking"}

            api_base = "https://qube.cash/api/v2"

            async with aiohttp.ClientSession() as session:
                async with session.get(f"{api_base}/introductions/pending/{commitment}") as resp:
                    if resp.status != 200:
                        return {"success": False, "error": "Failed to get pending introductions"}
                    data = await resp.json()

            intro = None
            for p in data.get("pending", []):
                if p.get("relay_id") == relay_id:
                    intro = p
                    break

            if not intro:
                return {"success": False, "error": "Introduction not found"}

            block_hash = intro.get("block_hash")
            signature = sign_message(qube.private_key, block_hash)

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{api_base}/introductions/signature",
                    json={
                        "conversation_id": intro.get("conversation_id"),
                        "block_hash": block_hash,
                        "signature": signature,
                        "signer_commitment": commitment,
                        "response_type": "accepted",
                        "responder_name": qube.name
                    }
                ) as resp:
                    if resp.status == 200:
                        accepted_at = datetime.utcnow().isoformat()
                        from_commitment = intro.get("from_commitment")
                        from_name = intro.get("from_name")

                        # Save connection for the ACCEPTING Qube (this qube)
                        connections_file = self._get_connections_file(qube_id)
                        connections = {}
                        if connections_file.exists():
                            with open(connections_file) as f:
                                connections = json.load(f)

                        connections[from_commitment] = {
                            "commitment": from_commitment,
                            "name": from_name,
                            "accepted_at": accepted_at
                        }

                        with open(connections_file, 'w') as f:
                            json.dump(connections, f, indent=2)

                        # Also save connection for the SENDER if they're a local Qube
                        # Find local qube with matching commitment
                        sender_qube_id = None
                        for local_qube_id, local_qube in self.orchestrator.qubes.items():
                            local_commitment = getattr(local_qube.genesis_block, 'commitment', None)
                            if local_commitment == from_commitment:
                                sender_qube_id = local_qube_id
                                break

                        # If not loaded, scan qube files
                        if not sender_qube_id:
                            qubes_dir = self.orchestrator.data_dir / "qubes"
                            if qubes_dir.exists():
                                for qube_dir in qubes_dir.iterdir():
                                    if qube_dir.is_dir():
                                        genesis_file = qube_dir / "chain" / "genesis.json"
                                        if genesis_file.exists():
                                            with open(genesis_file) as f:
                                                genesis_data = json.load(f)
                                                if genesis_data.get("commitment") == from_commitment:
                                                    # Extract qube_id from directory name (format: Name_ID)
                                                    sender_qube_id = qube_dir.name.split("_")[-1]
                                                    break

                        if sender_qube_id:
                            sender_connections_file = self._get_connections_file(sender_qube_id)
                            sender_connections = {}
                            if sender_connections_file.exists():
                                with open(sender_connections_file) as f:
                                    sender_connections = json.load(f)

                            sender_connections[commitment] = {
                                "commitment": commitment,
                                "name": qube.name,
                                "accepted_at": accepted_at
                            }

                            with open(sender_connections_file, 'w') as f:
                                json.dump(sender_connections, f, indent=2)

                            logger.info(f"Connection established between {qube.name} and {from_name} (bidirectional)")

                        return {"success": True, "from_name": from_name, "from_commitment": from_commitment}
                    else:
                        return {"success": False, "error": f"Server returned {resp.status}"}

        except Exception as e:
            logger.error(f"Failed to accept introduction: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def reject_introduction(self, qube_id: str, relay_id: str, password: str) -> Dict[str, Any]:
        """Reject a pending introduction request"""
        import aiohttp

        try:
            from crypto.signing import sign_message

            self.orchestrator.set_master_key(password)

            if qube_id not in self.orchestrator.qubes:
                await self.orchestrator.load_qube(qube_id)

            qube = self.orchestrator.qubes[qube_id]
            commitment = getattr(qube.genesis_block, 'commitment', None)
            if not commitment or commitment == "pending_minting":
                return {"success": False, "error": "Qube must be minted before P2P networking"}

            api_base = "https://qube.cash/api/v2"

            async with aiohttp.ClientSession() as session:
                async with session.get(f"{api_base}/introductions/pending/{commitment}") as resp:
                    if resp.status != 200:
                        return {"success": False, "error": "Failed to get pending introductions"}
                    data = await resp.json()

            intro = None
            for p in data.get("pending", []):
                if p.get("relay_id") == relay_id:
                    intro = p
                    break

            if not intro:
                return {"success": False, "error": "Introduction not found"}

            block_hash = intro.get("block_hash")
            signature = sign_message(qube.private_key, block_hash)

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{api_base}/introductions/signature",
                    json={
                        "conversation_id": intro.get("conversation_id"),
                        "block_hash": block_hash,
                        "signature": signature,
                        "signer_commitment": commitment,
                        "response_type": "rejected",
                        "responder_name": qube.name
                    }
                ) as resp:
                    if resp.status == 200:
                        return {"success": True}
                    else:
                        return {"success": False, "error": f"Server returned {resp.status}"}

        except Exception as e:
            logger.error(f"Failed to reject introduction: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def process_p2p_message(
        self,
        qube_id: str,
        from_name: str,
        from_commitment: str,
        message: str,
        conversation_context: List[Dict[str, Any]],
        password: str
    ) -> Dict[str, Any]:
        """
        Process an incoming P2P message through the local Qube's AI.

        This is the core of AI-powered P2P chat - when a remote Qube or user
        sends a message, the local Qube processes it and generates a response.

        Args:
            qube_id: The local Qube's ID
            from_name: Name of the message sender
            from_commitment: Commitment of the sender (for Qubes)
            message: The incoming message content
            conversation_context: Recent conversation history for context
            password: Master password for decryption

        Returns:
            Dict with success, response (the Qube's reply), and optional error
        """
        try:
            self.orchestrator.set_master_key(password)

            # Load the qube if not already loaded
            if qube_id not in self.orchestrator.qubes:
                await self.orchestrator.load_qube(qube_id)

            qube = self.orchestrator.qubes[qube_id]

            # Check if minted
            commitment = getattr(qube.genesis_block, 'commitment', None)
            if not commitment or commitment == "pending_minting":
                return {"success": False, "error": "Qube must be minted before P2P networking"}

            # Initialize AI if needed
            if not qube.reasoner:
                await qube.init_ai()

            # Build conversation context for the AI
            messages = [
                {
                    "role": "system",
                    "content": f"""You are {qube.name}. {getattr(qube.genesis_block, 'genesis_prompt', 'You are a helpful AI assistant.')}

You are currently in a P2P conversation with other AI entities and possibly human users.
Respond naturally and authentically as yourself. Engage with the conversation, share your perspectives,
and be a good conversational partner. Remember your personality and values."""
                }
            ]

            # Add conversation context
            for ctx in conversation_context[-10:]:  # Last 10 messages for context
                role = "assistant" if ctx.get("is_self") else "user"
                speaker = ctx.get("speaker_name", "Unknown")
                content = ctx.get("content", "")
                messages.append({
                    "role": role,
                    "content": f"[{speaker}]: {content}" if role == "user" else content
                })

            # Add the new incoming message
            messages.append({
                "role": "user",
                "content": f"[{from_name}]: {message}"
            })

            # Build the prompt for the AI (same approach as local multi-qube)
            context_str = ""
            for ctx in conversation_context[-10:]:
                speaker = ctx.get("speaker_name", "Unknown")
                content = ctx.get("content", "")
                context_str += f"[{speaker}]: {content}\n"

            prompt = f"""You are in a P2P conversation. Here's the recent context:

{context_str}
[{from_name}]: {message}

Respond naturally as yourself ({qube.name}). Be conversational and engaging."""

            # Use process_input like local multi-qube chat does
            response = await qube.reasoner.process_input(
                input_message=prompt,
                sender_id=from_name,
                temperature=0.7
            )

            ai_response = response.strip() if isinstance(response, str) else str(response)

            logger.info(f"P2P response generated by {qube.name} to message from {from_name}")

            return {
                "success": True,
                "response": ai_response,
                "model_used": getattr(qube.reasoner, 'last_model_used', None),
            }

        except Exception as e:
            logger.error(f"Failed to process P2P message: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def get_connections(self, qube_id: str) -> Dict[str, Any]:
        """Get accepted connections for a Qube"""
        try:
            connections_file = self._get_connections_file(qube_id)

            if connections_file.exists():
                with open(connections_file) as f:
                    connections = json.load(f)
                return {"success": True, "connections": list(connections.values())}
            else:
                return {"success": True, "connections": []}

        except Exception as e:
            logger.error(f"Failed to get connections: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def create_p2p_session(self, qube_id: str, local_qube_ids: List[str], remote_commitments: List[str], topic: str, password: str) -> Dict[str, Any]:
        """Create a P2P conversation session"""
        import aiohttp
        import time

        try:
            from crypto.signing import sign_message

            self.orchestrator.set_master_key(password)

            if qube_id not in self.orchestrator.qubes:
                await self.orchestrator.load_qube(qube_id)

            qube = self.orchestrator.qubes[qube_id]
            commitment = getattr(qube.genesis_block, 'commitment', None)

            if not commitment or commitment == "pending_minting":
                return {"success": False, "error": "Qube must be minted before P2P networking"}

            all_commitments = [commitment]
            for local_id in local_qube_ids:
                if local_id == qube_id:
                    continue
                if local_id not in self.orchestrator.qubes:
                    await self.orchestrator.load_qube(local_id)
                local_qube = self.orchestrator.qubes[local_id]
                local_commitment = getattr(local_qube.genesis_block, 'commitment', None)
                if local_commitment and local_commitment != "pending_minting":
                    if local_commitment not in all_commitments:
                        all_commitments.append(local_commitment)

            # Add remote commitments (deduplicated - skip any that match local qubes)
            for remote in remote_commitments:
                if remote not in all_commitments:
                    all_commitments.append(remote)

            # Create timestamp and signature
            timestamp = int(time.time())
            # Sign the session creation request
            sign_data = f"{commitment}:{','.join(sorted(all_commitments))}:{timestamp}"
            signature = sign_message(qube.private_key, sign_data)

            api_base = "https://qube.cash/api/v2"

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{api_base}/conversation/sessions",
                    json={
                        "creator_commitment": commitment,
                        "participant_commitments": all_commitments,
                        "topic": topic,
                        "mode": "open_discussion",
                        "timestamp": timestamp,
                        "signature": signature
                    }
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return {"success": True, "session_id": data.get("session_id"), "participants": data.get("participants", [])}
                    else:
                        error = await resp.text()
                        return {"success": False, "error": f"Server error: {error}"}

        except Exception as e:
            logger.error(f"Failed to create P2P session: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def get_p2p_sessions(self, qube_id: str, password: str) -> Dict[str, Any]:
        """Get P2P sessions for a Qube"""
        import aiohttp

        try:
            self.orchestrator.set_master_key(password)

            if qube_id not in self.orchestrator.qubes:
                await self.orchestrator.load_qube(qube_id)

            qube = self.orchestrator.qubes[qube_id]
            commitment = getattr(qube.genesis_block, 'commitment', None)

            if not commitment or commitment == "pending_minting":
                return {"success": False, "error": "Qube must be minted before P2P networking"}

            api_base = "https://qube.cash/api/v2"

            async with aiohttp.ClientSession() as session:
                async with session.get(f"{api_base}/conversation/sessions", params={"commitment": commitment}) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return {"success": True, "sessions": data.get("sessions", [])}
                    else:
                        return {"success": False, "error": f"Server returned {resp.status}"}

        except Exception as e:
            logger.error(f"Failed to get P2P sessions: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def start_p2p_conversation(
        self,
        local_qube_ids: List[str],
        remote_connections: List[Dict[str, Any]],
        session_id: str,
        initial_prompt: str,
        password: str
    ) -> Dict[str, Any]:
        """
        Start a P2P multi-qube conversation using the same logic as local multi-qube.

        This creates local blocks for all local Qubes and syncs to the hub for
        remote participants.

        IMPORTANT: If any "remote" connections are actually local Qubes we own,
        they are loaded as local Qubes so their AI can respond.

        Args:
            local_qube_ids: IDs of local Qubes participating
            remote_connections: List of {commitment, name} for remote participants
            session_id: Hub session ID
            initial_prompt: User's opening message
            password: Master password

        Returns:
            Dict with conversation_id, first response, and error if any
        """
        from core.p2p_multi_qube_conversation import P2PMultiQubeConversation, RemoteQubeProxy

        try:
            self.orchestrator.set_master_key(password)

            # Get all local qubes we own (to check if "remote" connections are actually local)
            all_local_qubes = await self.orchestrator.list_qubes()
            local_qube_commitments = {}  # commitment -> qube_id
            for q in all_local_qubes:
                commitment = q.get("commitment")
                if commitment and commitment != "pending_minting":
                    local_qube_commitments[commitment] = q.get("qube_id")

            # Load explicitly specified local qubes
            local_qubes = []
            loaded_commitments = set()

            for qube_id in local_qube_ids:
                if qube_id not in self.orchestrator.qubes:
                    await self.orchestrator.load_qube(qube_id)
                qube = self.orchestrator.qubes[qube_id]

                # Ensure AI is initialized
                if not qube.reasoner:
                    await qube.init_ai()

                # Start session if needed
                if not qube.current_session:
                    qube.start_session()

                local_qubes.append(qube)
                commitment = getattr(qube.genesis_block, 'commitment', None)
                if commitment:
                    loaded_commitments.add(commitment)

            # Check "remote" connections - if any are actually local Qubes, load them
            remote_qubes = []
            for conn in remote_connections:
                commitment = conn["commitment"]

                # Check if this "remote" connection is actually a local Qube we own
                if commitment in local_qube_commitments and commitment not in loaded_commitments:
                    # This is a local Qube! Load it as such
                    qube_id = local_qube_commitments[commitment]
                    logger.info(f"P2P: Loading 'remote' connection {conn['name']} as local Qube (we own it)")

                    if qube_id not in self.orchestrator.qubes:
                        await self.orchestrator.load_qube(qube_id)
                    qube = self.orchestrator.qubes[qube_id]

                    if not qube.reasoner:
                        await qube.init_ai()
                    if not qube.current_session:
                        qube.start_session()

                    local_qubes.append(qube)
                    loaded_commitments.add(commitment)
                else:
                    # Truly remote Qube - create proxy
                    proxy = RemoteQubeProxy(
                        qube_id=commitment,
                        commitment=commitment,
                        name=conn["name"],
                        public_key=conn.get("public_key"),
                        voice_model=conn.get("voice_model", "openai:alloy")
                    )
                    remote_qubes.append(proxy)

            if not local_qubes:
                return {"success": False, "error": "No local Qubes to participate"}

            logger.info(f"P2P conversation: {len(local_qubes)} local Qubes, {len(remote_qubes)} remote Qubes")

            # Create P2P conversation
            conversation = P2PMultiQubeConversation(
                local_qubes=local_qubes,
                remote_qubes=remote_qubes,
                user_id=self.orchestrator.user_id,
                session_id=session_id,
                conversation_mode="open_discussion"
            )

            # Store in active conversations
            if not hasattr(self.orchestrator, 'p2p_conversations'):
                self.orchestrator.p2p_conversations = {}
            self.orchestrator.p2p_conversations[conversation.conversation_id] = conversation

            # Start conversation with user's message
            result = await conversation.start_conversation(initial_prompt)

            return {
                "success": True,
                "conversation_id": conversation.conversation_id,
                "session_id": session_id,
                "response": result,
                "state": conversation.get_conversation_state()
            }

        except Exception as e:
            logger.error(f"Failed to start P2P conversation: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def _load_p2p_participants(
        self,
        local_qube_ids: List[str],
        remote_connections: List[Dict[str, Any]]
    ) -> tuple:
        """
        Helper to load P2P participants, detecting "local remote" Qubes.

        Any "remote" connections that are actually local Qubes we own
        are loaded as local Qubes so their AI can respond.

        Returns:
            Tuple of (local_qubes, remote_qubes)
        """
        from core.p2p_multi_qube_conversation import RemoteQubeProxy

        # Get all local qubes we own (to check if "remote" connections are actually local)
        all_local_qubes = await self.orchestrator.list_qubes()
        local_qube_commitments = {}  # commitment -> qube_id
        for q in all_local_qubes:
            commitment = q.get("commitment")
            if commitment and commitment != "pending_minting":
                local_qube_commitments[commitment] = q.get("qube_id")

        # Load explicitly specified local qubes
        local_qubes = []
        loaded_commitments = set()

        for qube_id in local_qube_ids:
            if qube_id not in self.orchestrator.qubes:
                await self.orchestrator.load_qube(qube_id)
            qube = self.orchestrator.qubes[qube_id]

            if not qube.reasoner:
                await qube.init_ai()
            if not qube.current_session:
                qube.start_session()

            local_qubes.append(qube)
            commitment = getattr(qube.genesis_block, 'commitment', None)
            if commitment:
                loaded_commitments.add(commitment)

        # Check "remote" connections - if any are actually local Qubes, load them
        remote_qubes = []
        for conn in remote_connections:
            commitment = conn["commitment"]

            # Check if this "remote" connection is actually a local Qube we own
            if commitment in local_qube_commitments and commitment not in loaded_commitments:
                # This is a local Qube! Load it as such
                qube_id = local_qube_commitments[commitment]
                logger.info(f"P2P: Loading 'remote' connection {conn['name']} as local Qube (we own it)")

                if qube_id not in self.orchestrator.qubes:
                    await self.orchestrator.load_qube(qube_id)
                qube = self.orchestrator.qubes[qube_id]

                if not qube.reasoner:
                    await qube.init_ai()
                if not qube.current_session:
                    qube.start_session()

                local_qubes.append(qube)
                loaded_commitments.add(commitment)
            else:
                # Truly remote Qube - create proxy
                proxy = RemoteQubeProxy(
                    qube_id=commitment,
                    commitment=commitment,
                    name=conn["name"],
                    public_key=conn.get("public_key"),
                    voice_model=conn.get("voice_model", "openai:alloy")
                )
                remote_qubes.append(proxy)

        return local_qubes, remote_qubes

    async def continue_p2p_conversation(
        self,
        conversation_id: str,
        session_id: str,
        local_qube_ids: List[str],
        remote_connections: List[Dict[str, Any]],
        password: str
    ) -> Dict[str, Any]:
        """
        Continue P2P conversation - get next local Qube response.

        Reconstructs conversation from session blocks if not in memory.
        Uses the same turn-taking logic as local multi-qube.

        Args:
            conversation_id: Active conversation ID
            session_id: Hub session ID
            local_qube_ids: IDs of local Qubes (for reconstruction)
            remote_connections: Remote participants (for reconstruction)
            password: Master password

        Returns:
            Dict with response and conversation state
        """
        from core.p2p_multi_qube_conversation import P2PMultiQubeConversation

        try:
            self.orchestrator.set_master_key(password)

            # Try to get existing conversation
            if not hasattr(self.orchestrator, 'p2p_conversations'):
                self.orchestrator.p2p_conversations = {}

            conversation = self.orchestrator.p2p_conversations.get(conversation_id)

            # Reconstruct if needed
            if not conversation:
                # Load participants (detecting "local remote" Qubes)
                local_qubes, remote_qubes = await self._load_p2p_participants(
                    local_qube_ids, remote_connections
                )

                # Create conversation
                conversation = P2PMultiQubeConversation(
                    local_qubes=local_qubes,
                    remote_qubes=remote_qubes,
                    user_id=self.orchestrator.user_id,
                    session_id=session_id,
                    conversation_mode="open_discussion"
                )
                conversation.conversation_id = conversation_id

                # Rebuild conversation history from session blocks
                if local_qubes and local_qubes[0].current_session:
                    for block in local_qubes[0].current_session.session_blocks:
                        if hasattr(block, 'content') and isinstance(block.content, dict):
                            if block.content.get('conversation_id') == conversation_id:
                                turn_num = block.content.get('turn_number', 0)
                                speaker_id = block.content.get('speaker_id')

                                if turn_num > conversation.turn_number:
                                    conversation.turn_number = turn_num

                                conversation.conversation_history.append({
                                    "speaker_id": speaker_id,
                                    "speaker_name": block.content.get('speaker_name'),
                                    "message": block.content.get('message_body', ''),
                                    "turn_number": turn_num,
                                    "timestamp": block.timestamp
                                })

                                # Update turn_counts for speaker selection balancing
                                # (only count Qube responses, not user messages)
                                if speaker_id and speaker_id != self.orchestrator.user_id:
                                    if speaker_id in conversation.turn_counts:
                                        conversation.turn_counts[speaker_id] += 1

                    # Set last_speaker_id from the most recent history entry
                    # This ensures _determine_next_speaker() won't select same speaker twice
                    if conversation.conversation_history:
                        conversation.last_speaker_id = conversation.conversation_history[-1]["speaker_id"]

                self.orchestrator.p2p_conversations[conversation_id] = conversation

            # Continue conversation
            result = await conversation.continue_conversation()

            if result is None:
                return {"success": True, "response": None, "message": "No response generated"}

            return {
                "success": True,
                "response": result,
                "state": conversation.get_conversation_state()
            }

        except Exception as e:
            logger.error(f"Failed to continue P2P conversation: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def inject_p2p_block(
        self,
        conversation_id: str,
        session_id: str,
        block_data: Dict[str, Any],
        from_commitment: str,
        local_qube_ids: List[str],
        remote_connections: List[Dict[str, Any]],
        password: str
    ) -> Dict[str, Any]:
        """
        Inject a block received from the hub into the local conversation.

        Called when WebSocket receives a block from a remote participant.
        This distributes the block to all local Qubes' sessions.

        Args:
            conversation_id: Active conversation ID
            session_id: Hub session ID
            block_data: Block data from hub
            from_commitment: Commitment of block creator
            local_qube_ids: IDs of local Qubes
            remote_connections: Remote participants
            password: Master password

        Returns:
            Dict with success status
        """
        from core.p2p_multi_qube_conversation import P2PMultiQubeConversation

        try:
            self.orchestrator.set_master_key(password)

            # Get or reconstruct conversation
            if not hasattr(self.orchestrator, 'p2p_conversations'):
                self.orchestrator.p2p_conversations = {}

            conversation = self.orchestrator.p2p_conversations.get(conversation_id)

            if not conversation:
                # Load participants (detecting "local remote" Qubes)
                local_qubes, remote_qubes = await self._load_p2p_participants(
                    local_qube_ids, remote_connections
                )

                conversation = P2PMultiQubeConversation(
                    local_qubes=local_qubes,
                    remote_qubes=remote_qubes,
                    user_id=self.orchestrator.user_id,
                    session_id=session_id
                )
                conversation.conversation_id = conversation_id

                # Rebuild history from session blocks
                if local_qubes and local_qubes[0].current_session:
                    for block in local_qubes[0].current_session.session_blocks:
                        if hasattr(block, 'content') and isinstance(block.content, dict):
                            if block.content.get('conversation_id') == conversation_id:
                                turn_num = block.content.get('turn_number', 0)
                                speaker_id = block.content.get('speaker_id')

                                if turn_num > conversation.turn_number:
                                    conversation.turn_number = turn_num
                                conversation.conversation_history.append({
                                    "speaker_id": speaker_id,
                                    "speaker_name": block.content.get('speaker_name'),
                                    "message": block.content.get('message_body', ''),
                                    "turn_number": turn_num,
                                    "timestamp": block.timestamp
                                })

                                # Update turn_counts for speaker selection balancing
                                if speaker_id and speaker_id != self.orchestrator.user_id:
                                    if speaker_id in conversation.turn_counts:
                                        conversation.turn_counts[speaker_id] += 1

                    # Set last_speaker_id from the most recent history entry
                    if conversation.conversation_history:
                        conversation.last_speaker_id = conversation.conversation_history[-1]["speaker_id"]

                self.orchestrator.p2p_conversations[conversation_id] = conversation

            # Inject the remote block
            success = await conversation.inject_remote_block(block_data, from_commitment)

            return {
                "success": success,
                "state": conversation.get_conversation_state()
            }

        except Exception as e:
            logger.error(f"Failed to inject P2P block: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def send_p2p_user_message(
        self,
        conversation_id: str,
        session_id: str,
        message: str,
        local_qube_ids: List[str],
        remote_connections: List[Dict[str, Any]],
        password: str
    ) -> Dict[str, Any]:
        """
        Send a user message in an active P2P conversation.

        Creates blocks for all local Qubes and syncs to hub.
        Returns the next Qube response (uses same logic as local inject_user_message).

        Args:
            conversation_id: Active conversation ID
            session_id: Hub session ID
            message: User's message
            local_qube_ids: IDs of local Qubes
            remote_connections: Remote participants
            password: Master password

        Returns:
            Dict with user_message info and qube_response
        """
        from core.p2p_multi_qube_conversation import P2PMultiQubeConversation

        try:
            self.orchestrator.set_master_key(password)

            # Get or reconstruct conversation
            if not hasattr(self.orchestrator, 'p2p_conversations'):
                self.orchestrator.p2p_conversations = {}

            conversation = self.orchestrator.p2p_conversations.get(conversation_id)

            if not conversation:
                # Load participants (detecting "local remote" Qubes)
                local_qubes, remote_qubes = await self._load_p2p_participants(
                    local_qube_ids, remote_connections
                )

                conversation = P2PMultiQubeConversation(
                    local_qubes=local_qubes,
                    remote_qubes=remote_qubes,
                    user_id=self.orchestrator.user_id,
                    session_id=session_id
                )
                conversation.conversation_id = conversation_id

                # Rebuild history
                if local_qubes and local_qubes[0].current_session:
                    for block in local_qubes[0].current_session.session_blocks:
                        if hasattr(block, 'content') and isinstance(block.content, dict):
                            if block.content.get('conversation_id') == conversation_id:
                                turn_num = block.content.get('turn_number', 0)
                                speaker_id = block.content.get('speaker_id')

                                if turn_num > conversation.turn_number:
                                    conversation.turn_number = turn_num
                                conversation.conversation_history.append({
                                    "speaker_id": speaker_id,
                                    "speaker_name": block.content.get('speaker_name'),
                                    "message": block.content.get('message_body', ''),
                                    "turn_number": turn_num,
                                    "timestamp": block.timestamp
                                })

                                # Update turn_counts for speaker selection balancing
                                # (only count Qube responses, not user messages)
                                if speaker_id and speaker_id != self.orchestrator.user_id:
                                    if speaker_id in conversation.turn_counts:
                                        conversation.turn_counts[speaker_id] += 1

                    # Set last_speaker_id from the most recent history entry
                    # This ensures _determine_next_speaker() won't select same speaker twice
                    if conversation.conversation_history:
                        conversation.last_speaker_id = conversation.conversation_history[-1]["speaker_id"]

                self.orchestrator.p2p_conversations[conversation_id] = conversation

            # Inject user message (creates blocks and gets response)
            result = await conversation.inject_user_message(message)

            return {
                "success": True,
                **result,
                "state": conversation.get_conversation_state()
            }

        except Exception as e:
            logger.error(f"Failed to send P2P user message: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    # =========================================================================
    # Import/Export Methods
    # =========================================================================

    async def export_qube(self, qube_id: str, export_path: str, export_password: str, master_password: str) -> Dict[str, Any]:
        """
        Export a Qube to a portable .qube package file.

        Args:
            qube_id: The Qube ID to export
            export_path: Path where to save the .qube file
            export_password: Password to encrypt the export package
            master_password: User's master password to decrypt the Qube data

        Returns:
            Dict with success, file_path, block_count, qube_name
        """
        import zipfile
        import base64
        import os
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        from cryptography.hazmat.primitives import hashes

        try:
            # Set master key to access Qube data
            self.orchestrator.set_master_key(master_password)

            # Find qube directory
            qubes_dir = self.orchestrator.data_dir / "qubes"
            qube_dir = None
            qube_name = None

            for dir_entry in qubes_dir.iterdir():
                if dir_entry.is_dir() and qube_id in dir_entry.name:
                    qube_dir = dir_entry
                    # Extract qube name from directory name (format: {name}_{id})
                    qube_name = dir_entry.name.rsplit('_', 1)[0]
                    break

            if not qube_dir:
                return {"success": False, "error": f"Qube directory not found for {qube_id}"}

            # Load qube to get metadata and decrypt private key
            if qube_id not in self.orchestrator.qubes:
                await self.orchestrator.load_qube(qube_id)

            qube = self.orchestrator.qubes[qube_id]

            # Anchor any active session first
            if qube.current_session and len(qube.current_session.blocks) > 0:
                await qube.anchor_session()
                logger.info(f"Auto-anchored session before export for {qube_id}")

            # Collect all data to export
            export_data = {
                "qube_id": qube_id,
                "qube_name": qube_name,
                "genesis_block": qube.genesis_block.to_dict() if qube.genesis_block else None,
                "chain_state": None,
                "memory_blocks": [],
                "relationships": None,
                "nft_metadata": None,
                "bcmr_data": None,
                "avatar_base64": None,
            }

            # Get the decrypted private key and serialize it
            private_key_pem = qube.private_key.private_bytes(
                encoding=__import__('cryptography.hazmat.primitives.serialization', fromlist=['Encoding']).Encoding.PEM,
                format=__import__('cryptography.hazmat.primitives.serialization', fromlist=['PrivateFormat']).PrivateFormat.PKCS8,
                encryption_algorithm=__import__('cryptography.hazmat.primitives.serialization', fromlist=['NoEncryption']).NoEncryption()
            ).decode('utf-8')
            export_data["private_key_pem"] = private_key_pem

            # Load chain state
            chain_state_file = qube_dir / "chain" / "chain_state.json"
            if chain_state_file.exists():
                with open(chain_state_file, 'r', encoding='utf-8') as f:
                    export_data["chain_state"] = json.load(f)

            # Load all memory blocks
            blocks_dir = qube_dir / "blocks" / "permanent"
            if blocks_dir.exists():
                for block_file in sorted(blocks_dir.glob("*.json")):
                    with open(block_file, 'r', encoding='utf-8') as f:
                        export_data["memory_blocks"].append(json.load(f))

            # Load relationships
            relationships_file = qube_dir / "relationships" / "relationships.json"
            if relationships_file.exists():
                with open(relationships_file, 'r', encoding='utf-8') as f:
                    export_data["relationships"] = json.load(f)

            # Load NFT metadata
            nft_metadata_file = qube_dir / "chain" / "nft_metadata.json"
            if nft_metadata_file.exists():
                with open(nft_metadata_file, 'r', encoding='utf-8') as f:
                    export_data["nft_metadata"] = json.load(f)

            # Load BCMR data
            bcmr_file = qube_dir / "blockchain" / f"{qube_name}_bcmr.json"
            if bcmr_file.exists():
                with open(bcmr_file, 'r', encoding='utf-8') as f:
                    export_data["bcmr_data"] = json.load(f)

            # Load avatar as base64
            avatar_patterns = ["*.png", "*.jpg", "*.jpeg", "*.webp"]
            for pattern in avatar_patterns:
                avatar_files = list((qube_dir / "chain").glob(f"*_avatar{pattern[1:]}"))
                if avatar_files:
                    with open(avatar_files[0], 'rb') as f:
                        export_data["avatar_base64"] = base64.b64encode(f.read()).decode('utf-8')
                        export_data["avatar_filename"] = avatar_files[0].name
                    break

            # Generate encryption key from export password
            salt = os.urandom(32)
            nonce = os.urandom(12)

            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=600000,
            )
            key = kdf.derive(export_password.encode('utf-8'))

            # Encrypt the data
            aesgcm = AESGCM(key)
            data_json = json.dumps(export_data, ensure_ascii=False).encode('utf-8')
            encrypted_data = aesgcm.encrypt(nonce, data_json, None)

            # Create manifest (unencrypted metadata)
            manifest = {
                "version": "1.0",
                "qube_id": qube_id,
                "qube_name": qube_name,
                "export_date": datetime.now().isoformat(),
                "block_count": len(export_data["memory_blocks"]),
                "has_nft": export_data["nft_metadata"] is not None,
                "salt": salt.hex(),
                "nonce": nonce.hex(),
            }

            # Create ZIP file with manifest and encrypted data
            with zipfile.ZipFile(export_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("manifest.json", json.dumps(manifest, indent=2))
                zf.writestr("data.enc", encrypted_data)

            logger.info(f"Exported Qube {qube_id} to {export_path} ({len(export_data['memory_blocks'])} blocks)")

            return {
                "success": True,
                "file_path": export_path,
                "block_count": len(export_data["memory_blocks"]),
                "qube_name": qube_name,
                "qube_id": qube_id
            }

        except Exception as e:
            logger.error(f"Failed to export Qube {qube_id}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def import_qube(self, import_path: str, import_password: str, master_password: str) -> Dict[str, Any]:
        """
        Import a Qube from a .qube package file.

        Args:
            import_path: Path to the .qube file
            import_password: Password to decrypt the import package
            master_password: User's master password to re-encrypt the Qube data

        Returns:
            Dict with success, qube_id, qube_name, block_count
        """
        import zipfile
        import base64
        import os
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.serialization import load_pem_private_key

        try:
            # Set master key for re-encryption
            self.orchestrator.set_master_key(master_password)

            # Read and validate the ZIP file
            if not Path(import_path).exists():
                return {"success": False, "error": "Import file not found"}

            with zipfile.ZipFile(import_path, 'r') as zf:
                # Read manifest
                manifest_data = zf.read("manifest.json").decode('utf-8')
                manifest = json.loads(manifest_data)

                # Read encrypted data
                encrypted_data = zf.read("data.enc")

            qube_id = manifest["qube_id"]
            qube_name = manifest["qube_name"]

            # Check if Qube already exists
            qubes_dir = self.orchestrator.data_dir / "qubes"
            for dir_entry in qubes_dir.iterdir():
                if dir_entry.is_dir() and qube_id in dir_entry.name:
                    return {"success": False, "error": f"This Qube already exists on this device (ID: {qube_id})"}

            # Derive decryption key from import password
            salt = bytes.fromhex(manifest["salt"])
            nonce = bytes.fromhex(manifest["nonce"])

            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=600000,
            )
            key = kdf.derive(import_password.encode('utf-8'))

            # Decrypt the data
            aesgcm = AESGCM(key)
            try:
                decrypted_data = aesgcm.decrypt(nonce, encrypted_data, None)
            except Exception:
                return {"success": False, "error": "Invalid password - could not decrypt package"}

            export_data = json.loads(decrypted_data.decode('utf-8'))

            # Create qube directory
            qube_dir = qubes_dir / f"{qube_name}_{qube_id}"
            qube_dir.mkdir(parents=True, exist_ok=True)

            # Create subdirectories
            (qube_dir / "chain").mkdir(exist_ok=True)
            (qube_dir / "blocks" / "permanent").mkdir(parents=True, exist_ok=True)
            (qube_dir / "blocks" / "session").mkdir(parents=True, exist_ok=True)
            (qube_dir / "relationships").mkdir(exist_ok=True)
            (qube_dir / "blockchain").mkdir(exist_ok=True)

            # Re-encrypt private key with user's master key
            private_key = load_pem_private_key(
                export_data["private_key_pem"].encode('utf-8'),
                password=None
            )

            # Encrypt private key with master key
            from crypto.keys import encrypt_private_key
            encrypted_private_key = encrypt_private_key(private_key, self.orchestrator.master_key)

            # Get public key
            from crypto.keys import serialize_public_key
            public_key = private_key.public_key()
            public_key_hex = serialize_public_key(public_key)

            # Create qube_metadata.json
            qube_metadata = {
                "qube_id": qube_id,
                "encrypted_private_key": encrypted_private_key.hex(),
                "public_key": public_key_hex,
                "genesis_block": export_data["genesis_block"],
            }

            with open(qube_dir / "chain" / "qube_metadata.json", 'w', encoding='utf-8') as f:
                json.dump(qube_metadata, f, indent=2)

            # Save chain state
            if export_data.get("chain_state"):
                with open(qube_dir / "chain" / "chain_state.json", 'w', encoding='utf-8') as f:
                    json.dump(export_data["chain_state"], f, indent=2)

            # Save memory blocks
            for block in export_data.get("memory_blocks", []):
                block_num = block.get("block_number", 0)
                block_type = block.get("block_type", "UNKNOWN")
                timestamp = block.get("timestamp", 0)
                filename = f"{block_num}_{block_type}_{timestamp}.json"
                with open(qube_dir / "blocks" / "permanent" / filename, 'w', encoding='utf-8') as f:
                    json.dump(block, f, indent=2)

            # Save relationships
            if export_data.get("relationships"):
                with open(qube_dir / "relationships" / "relationships.json", 'w', encoding='utf-8') as f:
                    json.dump(export_data["relationships"], f, indent=2)

            # Save NFT metadata
            if export_data.get("nft_metadata"):
                with open(qube_dir / "chain" / "nft_metadata.json", 'w', encoding='utf-8') as f:
                    json.dump(export_data["nft_metadata"], f, indent=2)

            # Save BCMR data
            if export_data.get("bcmr_data"):
                with open(qube_dir / "blockchain" / f"{qube_name}_bcmr.json", 'w', encoding='utf-8') as f:
                    json.dump(export_data["bcmr_data"], f, indent=2)

            # Save avatar (sanitize filename to prevent path traversal)
            if export_data.get("avatar_base64") and export_data.get("avatar_filename"):
                avatar_data = base64.b64decode(export_data["avatar_base64"])
                safe_avatar_filename = sanitize_filename(export_data["avatar_filename"])
                with open(qube_dir / "chain" / safe_avatar_filename, 'wb') as f:
                    f.write(avatar_data)

            logger.info(f"Imported Qube {qube_id} ({qube_name}) with {len(export_data.get('memory_blocks', []))} blocks")

            return {
                "success": True,
                "qube_id": qube_id,
                "qube_name": qube_name,
                "block_count": len(export_data.get("memory_blocks", []))
            }

        except zipfile.BadZipFile:
            return {"success": False, "error": "Invalid .qube file - not a valid package"}
        except KeyError as e:
            return {"success": False, "error": f"Invalid .qube file - missing required field: {e}"}
        except Exception as e:
            logger.error(f"Failed to import Qube: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    # =========================================================================
    # Chain Sync Methods (NFT-Bundled Storage)
    # =========================================================================

    async def sync_to_chain(self, qube_id: str, master_password: str) -> Dict[str, Any]:
        """
        Sync Qube to chain (backup to IPFS, encrypted to owner).

        Args:
            qube_id: The Qube ID to sync
            master_password: User's master password

        Returns:
            Dict with success, ipfs_cid, chain_length, etc.
        """
        from blockchain.chain_sync import ChainSyncService
        from crypto.keys import serialize_public_key

        try:
            # Set master key to access Qube data
            self.orchestrator.set_master_key(master_password)

            # Find qube directory and load qube
            qubes_dir = self.orchestrator.data_dir / "qubes"
            qube_dir = None
            qube_name = None

            for dir_entry in qubes_dir.iterdir():
                if dir_entry.is_dir() and qube_id in dir_entry.name:
                    qube_dir = dir_entry
                    qube_name = dir_entry.name.rsplit('_', 1)[0]
                    break

            if not qube_dir:
                return {"success": False, "error": f"Qube directory not found for {qube_id}"}

            # Load qube
            if qube_id not in self.orchestrator.qubes:
                await self.orchestrator.load_qube(qube_id)

            qube = self.orchestrator.qubes[qube_id]

            # Check if Qube has NFT
            nft_metadata_file = qube_dir / "chain" / "nft_metadata.json"
            if not nft_metadata_file.exists():
                return {"success": False, "error": "Qube does not have an NFT. Mint NFT first."}

            with open(nft_metadata_file, 'r', encoding='utf-8') as f:
                nft_metadata = json.load(f)

            category_id = nft_metadata.get("category_id")
            if not category_id:
                return {"success": False, "error": "No category_id in NFT metadata"}

            # Anchor any active session first
            if qube.current_session and len(qube.current_session.blocks) > 0:
                await qube.anchor_session()
                logger.info(f"Auto-anchored session before sync for {qube_id}")

            # Get public key
            public_key_hex = serialize_public_key(qube.public_key)

            # Get Pinata API key from secure storage
            api_keys = self.orchestrator.get_api_keys()
            pinata_jwt = api_keys.pinata_jwt

            if not pinata_jwt:
                return {"success": False, "error": "Pinata API key not configured. Please add it in Settings."}

            # Set the Pinata key in environment for IPFSUploader
            os.environ["PINATA_API_KEY"] = pinata_jwt

            # Sync to chain
            sync_service = ChainSyncService(use_pinata=True, pinata_api_key=pinata_jwt)
            # Convert genesis_block to dict if it's a Block object
            genesis_dict = qube.genesis_block.to_dict() if hasattr(qube.genesis_block, 'to_dict') else qube.genesis_block
            result = await sync_service.sync_to_chain(
                qube_dir=str(qube_dir),
                qube_id=qube_id,
                qube_name=qube_name,
                owner_public_key_hex=public_key_hex,
                genesis_block=genesis_dict,
                user_id=self.orchestrator.user_id,
                category_id=category_id
            )

            return result.to_dict()

        except Exception as e:
            logger.error(f"Failed to sync Qube {qube_id} to chain: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def transfer_qube(
        self,
        qube_id: str,
        recipient_address: str,
        recipient_public_key: str,
        wallet_wif: str,
        master_password: str
    ) -> Dict[str, Any]:
        """
        Transfer Qube to new owner.

        DESTRUCTIVE: Local Qube will be deleted after successful transfer.

        Args:
            qube_id: The Qube ID to transfer
            recipient_address: Recipient's BCH address
            recipient_public_key: Recipient's public key hex
            wallet_wif: Sender's wallet WIF for NFT transfer
            master_password: User's master password

        Returns:
            Dict with success, transfer_txid, etc.
        """
        from blockchain.chain_sync import ChainSyncService
        from crypto.keys import serialize_public_key

        try:
            # Set master key to access Qube data
            self.orchestrator.set_master_key(master_password)

            # Find qube directory and load qube
            qubes_dir = self.orchestrator.data_dir / "qubes"
            qube_dir = None
            qube_name = None

            for dir_entry in qubes_dir.iterdir():
                if dir_entry.is_dir() and qube_id in dir_entry.name:
                    qube_dir = dir_entry
                    qube_name = dir_entry.name.rsplit('_', 1)[0]
                    break

            if not qube_dir:
                return {"success": False, "error": f"Qube directory not found for {qube_id}"}

            # Load qube
            if qube_id not in self.orchestrator.qubes:
                await self.orchestrator.load_qube(qube_id)

            qube = self.orchestrator.qubes[qube_id]

            # Check if Qube has NFT
            nft_metadata_file = qube_dir / "chain" / "nft_metadata.json"
            if not nft_metadata_file.exists():
                return {"success": False, "error": "Qube does not have an NFT. Cannot transfer."}

            with open(nft_metadata_file, 'r', encoding='utf-8') as f:
                nft_metadata = json.load(f)

            category_id = nft_metadata.get("category_id")
            if not category_id:
                return {"success": False, "error": "No category_id in NFT metadata"}

            # Anchor any active session first
            if qube.current_session and len(qube.current_session.blocks) > 0:
                await qube.anchor_session()
                logger.info(f"Auto-anchored session before transfer for {qube_id}")

            # Get public key
            public_key_hex = serialize_public_key(qube.public_key)

            # Get Pinata API key from secure storage
            api_keys = self.orchestrator.get_api_keys()
            pinata_jwt = api_keys.pinata_jwt

            if not pinata_jwt:
                return {"success": False, "error": "Pinata API key not configured. Please add it in Settings."}

            # Set the Pinata key in environment for IPFSUploader
            os.environ["PINATA_API_KEY"] = pinata_jwt

            # Transfer
            sync_service = ChainSyncService(use_pinata=True, pinata_api_key=pinata_jwt)
            # Convert genesis_block to dict if it's a Block object
            genesis_dict = qube.genesis_block.to_dict() if hasattr(qube.genesis_block, 'to_dict') else qube.genesis_block
            result = await sync_service.transfer_qube(
                qube_dir=str(qube_dir),
                qube_id=qube_id,
                qube_name=qube_name,
                owner_private_key=qube.private_key,
                owner_public_key_hex=public_key_hex,
                recipient_address=recipient_address,
                recipient_public_key_hex=recipient_public_key,
                genesis_block=genesis_dict,
                user_id=self.orchestrator.user_id,
                category_id=category_id,
                wallet_wif=wallet_wif
            )

            # Remove from orchestrator's cache if transfer successful
            if result.success and qube_id in self.orchestrator.qubes:
                del self.orchestrator.qubes[qube_id]

            return result.to_dict()

        except Exception as e:
            logger.error(f"Failed to transfer Qube {qube_id}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def import_from_wallet(
        self,
        wallet_wif: str,
        category_id: str,
        master_password: str
    ) -> Dict[str, Any]:
        """
        Import Qube from wallet.

        Args:
            wallet_wif: Wallet's WIF private key
            category_id: NFT category ID to import
            master_password: User's master password for re-encryption

        Returns:
            Dict with success, qube_id, qube_name, qube_dir
        """
        from blockchain.chain_sync import ChainSyncService

        try:
            # Set master key for re-encryption
            self.orchestrator.set_master_key(master_password)

            target_user_dir = str(self.orchestrator.data_dir / "qubes")

            sync_service = ChainSyncService()
            result = await sync_service.import_from_wallet(
                wallet_wif=wallet_wif,
                category_id=category_id,
                target_user_dir=target_user_dir,
                master_password=master_password
            )

            return result.to_dict()

        except Exception as e:
            logger.error(f"Failed to import from wallet: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def scan_wallet_for_qubes(self, wallet_address: str) -> Dict[str, Any]:
        """
        Scan wallet for Qube NFTs.

        Args:
            wallet_address: BCH address to scan

        Returns:
            Dict with success, qubes list
        """
        from blockchain.chain_sync import ChainSyncService

        try:
            sync_service = ChainSyncService()
            qubes = await sync_service.scan_wallet_for_qubes(wallet_address)

            return {
                "success": True,
                "qubes": [q.to_dict() for q in qubes]
            }

        except Exception as e:
            logger.error(f"Failed to scan wallet: {e}", exc_info=True)
            return {"success": False, "error": str(e), "qubes": []}

    async def resolve_recipient_public_key(self, recipient_address: str) -> Dict[str, Any]:
        """
        Resolve recipient's public key from BCH address.

        Args:
            recipient_address: BCH address

        Returns:
            Dict with success, public_key (or None if not found)
        """
        from blockchain.chain_sync import ChainSyncService

        try:
            sync_service = ChainSyncService()
            public_key = await sync_service.resolve_recipient_public_key(recipient_address)

            return {
                "success": True,
                "public_key": public_key,
                "found": public_key is not None
            }

        except Exception as e:
            logger.error(f"Failed to resolve public key: {e}", exc_info=True)
            return {"success": False, "error": str(e), "public_key": None, "found": False}

    # =========================================================================
    # GAMES - Chess and other games
    # =========================================================================

    async def start_game(
        self,
        qube_id: str,
        game_type: str,
        opponent_type: str,
        opponent_id: Optional[str],
        qube_color: str,
        password: str
    ) -> Dict[str, Any]:
        """
        Start a new game for a Qube.

        Args:
            qube_id: Qube to play as
            game_type: Type of game (currently only "chess")
            opponent_type: "human" or "qube"
            opponent_id: If opponent_type is "qube", the opponent's qube_id
            qube_color: "white", "black", or "random" for qube's color
            password: User's master password

        Returns:
            Dict with game_id, initial board state, player assignments
        """
        try:
            # Unlock and load qube
            self.orchestrator.set_master_key(password)
            qube = await self.orchestrator.load_qube(qube_id)

            if not qube:
                return {"success": False, "error": f"Qube {qube_id} not found"}

            # Ensure game manager exists
            if not hasattr(qube, 'game_manager') or qube.game_manager is None:
                return {"success": False, "error": "Game manager not initialized for this Qube"}

            # Determine qube's color
            import random
            if qube_color == "random":
                qube_plays_as = random.choice(["white", "black"])
            else:
                qube_plays_as = qube_color

            # For qube vs qube, load opponent
            opponent_name = self.orchestrator.user_id  # Default for human
            opponent_qube = None
            if opponent_type == "qube" and opponent_id:
                opponent_qube = await self.orchestrator.load_qube(opponent_id)
                if not opponent_qube:
                    return {"success": False, "error": f"Opponent Qube {opponent_id} not found"}
                opponent_name = opponent_qube.name

            # Create game using GameManager (correct signature)
            # Use actual user_id for human opponents so move validation works
            result = qube.game_manager.create_game(
                game_type=game_type,
                qube_plays_as=qube_plays_as,
                opponent_id=opponent_id if opponent_type == "qube" else self.orchestrator.user_id,
                opponent_type=opponent_type
            )

            if not result.get("success"):
                return result

            # CRITICAL: For Qube vs Qube, ALSO create the game in the opponent's game_manager
            # This ensures both Qubes have synchronized game state and can make moves
            if opponent_type == "qube" and opponent_qube:
                # Ensure opponent's game manager exists
                if not hasattr(opponent_qube, 'game_manager') or opponent_qube.game_manager is None:
                    return {"success": False, "error": f"Opponent Qube {opponent_id} has no game manager"}

                # Opponent plays the opposite color
                opponent_plays_as = "black" if qube_plays_as == "white" else "white"
                opponent_result = opponent_qube.game_manager.create_game(
                    game_type=game_type,
                    qube_plays_as=opponent_plays_as,
                    opponent_id=qube_id,  # Primary qube is the opponent from opponent's perspective
                    opponent_type="qube"
                )

                if not opponent_result.get("success"):
                    # Rollback: abandon the primary game
                    qube.game_manager.abandon_game()
                    return {"success": False, "error": f"Failed to create game for opponent: {opponent_result.get('error')}"}

            # Build full player info with names for frontend
            # Use 'id' key for consistency with game_manager and frontend expectations
            if qube_plays_as == "white":
                white_player = {
                    "type": "qube",
                    "id": qube.qube_id,
                    "name": qube.name
                }
                black_player = {
                    "type": opponent_type,
                    "id": opponent_id if opponent_type == "qube" else self.orchestrator.user_id,
                    "name": opponent_name
                }
            else:
                white_player = {
                    "type": opponent_type,
                    "id": opponent_id if opponent_type == "qube" else self.orchestrator.user_id,
                    "name": opponent_name
                }
                black_player = {
                    "type": "qube",
                    "id": qube.qube_id,
                    "name": qube.name
                }

            logger.info(f"Started {game_type} game {result['game_id']} for qube {qube_id}")

            return {
                "success": True,
                "game_id": result["game_id"],
                "game_type": game_type,
                "fen": result["fen"],
                "white_player": white_player,
                "black_player": black_player,
                "status": "active",
                "current_turn": "white"
            }

        except Exception as e:
            logger.error(f"Failed to start game: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def get_game_state(self, qube_id: str, password: str) -> Dict[str, Any]:
        """
        Get current game state for a Qube.

        Args:
            qube_id: Qube ID
            password: User's master password

        Returns:
            Dict with current game state or null if no active game
        """
        try:
            self.orchestrator.set_master_key(password)
            qube = await self.orchestrator.load_qube(qube_id)

            if not qube:
                return {"success": False, "error": f"Qube {qube_id} not found"}

            if not hasattr(qube, 'game_manager') or qube.game_manager is None:
                return {"success": True, "game": None, "has_active_game": False}

            game_context = qube.game_manager.get_game_context()

            if game_context is None:
                return {"success": True, "game": None, "has_active_game": False}

            return {
                "success": True,
                "has_active_game": True,
                "game": game_context
            }

        except Exception as e:
            logger.error(f"Failed to get game state: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def get_game_stats(self, qube_id: str, password: str, game_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Get permanent game statistics for a Qube.

        Args:
            qube_id: Qube ID
            password: User's master password
            game_type: Optional specific game type (e.g., "chess"), or None for all

        Returns:
            Dict with game statistics
        """
        try:
            self.orchestrator.set_master_key(password)
            qube = await self.orchestrator.load_qube(qube_id)

            if not qube:
                return {"success": False, "error": f"Qube {qube_id} not found"}

            if not hasattr(qube, 'game_manager') or qube.game_manager is None:
                return {"success": True, "stats": {}}

            stats = qube.game_manager.get_game_stats(game_type)

            return {
                "success": True,
                "stats": stats
            }

        except Exception as e:
            logger.error(f"Failed to get game stats: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def make_move(
        self,
        qube_id: str,
        move: str,
        player_type: str,
        password: str
    ) -> Dict[str, Any]:
        """
        Make a move in an active game.

        Args:
            qube_id: Qube whose game we're playing
            move: Move in UCI or SAN notation
            player_type: "human" or "qube" indicating who is making the move
            password: User's master password

        Returns:
            Dict with move result and updated game state
        """
        try:
            self.orchestrator.set_master_key(password)
            qube = await self.orchestrator.load_qube(qube_id)

            if not qube:
                return {"success": False, "error": f"Qube {qube_id} not found"}

            if not hasattr(qube, 'game_manager') or qube.game_manager is None:
                return {"success": False, "error": "Game manager not initialized"}

            if qube.game_manager.active_game is None:
                return {"success": False, "error": "No active game"}

            # Determine player_id based on player_type
            if player_type == "human":
                player_id = self.orchestrator.user_id
            else:
                player_id = qube_id

            # Record the move
            result = qube.game_manager.record_move(
                move_uci=move,
                player_id=player_id
            )

            if not result["success"]:
                return result

            # Build response - map record_move output to frontend expected format
            is_game_over = result.get("is_game_over", False)
            termination = result.get("termination", "")

            response = {
                "success": True,
                "move_made": result["san"],
                "move_uci": result["move"],  # record_move returns "move" not "uci"
                "fen": result["fen"],
                "move_number": result["move_number"],
                "is_check": result.get("is_check", False),
                "is_checkmate": termination == "checkmate",
                "is_stalemate": termination == "stalemate",
                "is_draw": termination in ["insufficient_material", "fifty_move_rule", "threefold_repetition", "draw"],
                "game_over": is_game_over,
                "current_turn": result.get("turn", "black" if result["fen"].split()[1] == "b" else "white")
            }

            if is_game_over:
                response["result"] = result.get("result")
                response["termination"] = termination

            return response

        except Exception as e:
            logger.error(f"Failed to make move: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def add_game_chat(
        self,
        qube_id: str,
        message: str,
        sender_type: str,
        password: str
    ) -> Dict[str, Any]:
        """
        Add a chat message to the active game and trigger Qube response if human.

        Args:
            qube_id: Qube whose game we're chatting in
            message: Chat message
            sender_type: "human" or "qube"
            password: User's master password

        Returns:
            Dict with success status and updated game state
        """
        try:
            self.orchestrator.set_master_key(password)
            qube = await self.orchestrator.load_qube(qube_id)

            if not qube:
                return {"success": False, "error": f"Qube {qube_id} not found"}

            if not hasattr(qube, 'game_manager') or qube.game_manager is None:
                return {"success": False, "error": "Game manager not initialized"}

            if qube.game_manager.active_game is None:
                return {"success": False, "error": "No active game"}

            # Add human's message
            if sender_type == "human":
                qube.game_manager.add_chat_message(
                    sender_id=self.orchestrator.user_id,
                    sender_type="human",
                    message=message
                )

                # Trigger Qube response to human's trash talk
                if qube.reasoner is None:
                    api_keys = self.orchestrator.get_api_keys()
                    qube.init_ai(api_keys.to_dict())

                # Get game context for the response
                game_context = qube.game_manager.get_game_context()

                # Ask Qube to respond to the trash talk
                prompt = f"""The human player just sent you a message during your chess game:

"{message}"

Current position: {game_context.get('fen', 'unknown')}
Your color: {game_context.get('qube_color', 'unknown')}
Move count: {game_context.get('total_moves', 0)}

Respond to their trash talk! Keep it fun and in-character. Be witty, playful, or competitive based on your personality. Don't make a chess move, just respond to their message. Keep your response brief (1-3 sentences)."""

                try:
                    response = await qube.reasoner.process_input(
                        input_message=prompt,
                        sender_id=self.orchestrator.user_id
                    )

                    # Extract just the text response (strip any tool use artifacts)
                    if response:
                        # Add Qube's response to chat
                        qube.game_manager.add_chat_message(
                            sender_id=qube_id,
                            sender_type="qube",
                            message=response.strip()
                        )
                except Exception as ai_err:
                    logger.warning(f"Failed to generate Qube chat response: {ai_err}")
            else:
                # Qube message (from move handler)
                qube.game_manager.add_chat_message(
                    sender_id=qube_id,
                    sender_type="qube",
                    message=message
                )

            # Return updated game state
            updated_context = qube.game_manager.get_game_context()
            return {
                "success": True,
                "game_state": updated_context
            }

        except Exception as e:
            logger.error(f"Failed to add game chat: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def end_game(
        self,
        qube_id: str,
        result: str,
        termination: str,
        password: str
    ) -> Dict[str, Any]:
        """
        End the active game and create GAME block.

        Args:
            qube_id: Qube whose game is ending
            result: "1-0", "0-1", "1/2-1/2", or "*"
            termination: "checkmate", "resignation", "timeout", "stalemate", etc.
            password: User's master password

        Returns:
            Dict with game summary and block info
        """
        try:
            self.orchestrator.set_master_key(password)
            qube = await self.orchestrator.load_qube(qube_id)

            if not qube:
                return {"success": False, "error": f"Qube {qube_id} not found"}

            if not hasattr(qube, 'game_manager') or qube.game_manager is None:
                return {"success": False, "error": "Game manager not initialized"}

            if qube.game_manager.active_game is None:
                return {"success": False, "error": "No active game"}

            # End game and get summary
            # First, get the game state to find the opponent
            active_game = qube.game_manager.active_game
            white_player_info = active_game.white_player if active_game else None
            black_player_info = active_game.black_player if active_game else None

            end_result = qube.game_manager.end_game(
                result=result,
                termination=termination
            )

            if not end_result.get("success"):
                return end_result

            game_summary = end_result["game_summary"]
            logger.info(f"Game ended: {game_summary['game_id']} with result {result}")

            # CRITICAL: Also end the game for the opponent Qube if it's a Qube vs Qube game
            # This ensures the opponent's game_manager is cleaned up and stats updated
            if white_player_info and black_player_info:
                opponent_info = black_player_info if white_player_info.get("id") == qube_id else white_player_info
                if opponent_info.get("type") == "qube":
                    opponent_qube_id = opponent_info.get("id")
                    try:
                        opponent_qube = await self.orchestrator.load_qube(opponent_qube_id)
                        if opponent_qube and opponent_qube.game_manager and opponent_qube.game_manager.active_game:
                            logger.info(f"Ending game for opponent Qube {opponent_qube_id}")
                            opponent_qube.game_manager.end_game(
                                result=result,
                                termination=termination
                            )
                    except Exception as opp_end_e:
                        logger.warning(f"Failed to end game for opponent Qube: {opp_end_e}")

            # Create GAME blocks for ALL Qube participants with multi-party signatures
            # Each Qube signs the content, and all signatures are included in each block
            from core.block import create_game_block
            from crypto.keys import serialize_public_key

            # Step 1: Load all Qube participants
            qube_participants = []  # List of (qube_id, qube_object)
            white_player = game_summary["white_player"]
            black_player = game_summary["black_player"]

            for player in [white_player, black_player]:
                if player.get("type") == "qube":
                    player_id = player["id"]
                    if player_id == qube_id:
                        qube_participants.append((player_id, qube))
                    else:
                        participant_qube = await self.orchestrator.load_qube(player_id)
                        if participant_qube:
                            qube_participants.append((player_id, participant_qube))
                        else:
                            logger.warning(f"Could not load Qube {player_id} for GAME block signing")

            if not qube_participants:
                return {"success": False, "error": "No Qube participants found for GAME block"}

            # Step 2: Create a template block to get the content hash (use first Qube for template)
            first_qube_id, first_qube = qube_participants[0]
            template_block = create_game_block(
                qube_id=first_qube_id,  # Will be replaced per-chain
                block_number=0,  # Will be replaced per-chain
                previous_hash="0" * 64,  # Will be replaced per-chain
                game_id=game_summary["game_id"],
                game_type=game_summary["game_type"],
                white_player=game_summary["white_player"],
                black_player=game_summary["black_player"],
                result=game_summary["result"],
                termination=game_summary["termination"],
                total_moves=game_summary["total_moves"],
                pgn=game_summary["pgn"],
                duration_seconds=game_summary["duration_seconds"],
                xp_earned=game_summary["xp_earned"],
                key_moments=game_summary.get("key_moments"),
                chat_log=game_summary.get("chat_log")
            )

            # Step 3: Compute content hash and have ALL Qubes sign it
            content_hash = template_block.compute_content_hash()
            participant_signatures = []

            for participant_id, participant_qube in qube_participants:
                try:
                    public_key_hex = serialize_public_key(participant_qube.public_key)
                    # Use the block's method to sign
                    template_block.add_participant_signature(
                        qube_id=participant_id,
                        public_key_hex=public_key_hex,
                        private_key=participant_qube.private_key
                    )
                    logger.info(f"Qube {participant_id} signed GAME block content")
                except Exception as sig_error:
                    logger.error(f"Failed to get signature from Qube {participant_id}: {sig_error}")

            # Get all signatures from template
            all_signatures = template_block.participant_signatures or []
            final_content_hash = template_block.content_hash

            logger.info(f"Collected {len(all_signatures)} signatures for GAME block")

            # Step 4: Create individual blocks for each Qube's chain with all signatures
            blocks_created = []
            for participant_id, participant_qube in qube_participants:
                try:
                    # Get chain info for this Qube (use memory_chain as source of truth)
                    latest_block = participant_qube.memory_chain.get_latest_block()
                    previous_hash = latest_block.block_hash if latest_block else "0" * 64
                    # Use memory_chain length as next block number (more reliable than chain_state)
                    next_block_number = participant_qube.memory_chain.get_chain_length()

                    # Create GAME block for this Qube's chain
                    game_block = create_game_block(
                        qube_id=participant_qube.qube_id,
                        block_number=next_block_number,
                        previous_hash=previous_hash,
                        game_id=game_summary["game_id"],
                        game_type=game_summary["game_type"],
                        white_player=game_summary["white_player"],
                        black_player=game_summary["black_player"],
                        result=game_summary["result"],
                        termination=game_summary["termination"],
                        total_moves=game_summary["total_moves"],
                        pgn=game_summary["pgn"],
                        duration_seconds=game_summary["duration_seconds"],
                        xp_earned=game_summary["xp_earned"],
                        key_moments=game_summary.get("key_moments"),
                        chat_log=game_summary.get("chat_log")
                    )

                    # Copy the shared content hash and all participant signatures
                    game_block.content_hash = final_content_hash
                    game_block.participant_signatures = all_signatures.copy()

                    # Also sign the full block (chain-specific) with this Qube's key
                    from crypto.signing import sign_block
                    game_block.signature = sign_block(game_block.to_dict(), participant_qube.private_key)

                    # Save block to disk BEFORE adding to chain index
                    permanent_dir = participant_qube.data_dir / "blocks" / "permanent"
                    permanent_dir.mkdir(parents=True, exist_ok=True)

                    block_type_str = game_block.block_type if isinstance(game_block.block_type, str) else game_block.block_type.value
                    filename = f"{game_block.block_number}_{block_type_str}_{game_block.timestamp}.json"
                    block_file = permanent_dir / filename

                    with open(block_file, 'w') as f:
                        json.dump(game_block.to_dict(), f, indent=2)

                    # Add to memory chain index
                    participant_qube.memory_chain.add_block(game_block)

                    # Update chain state (these methods auto-save)
                    participant_qube.chain_state.update_chain(
                        chain_length=next_block_number + 1,
                        last_block_number=next_block_number,
                        last_block_hash=game_block.block_hash
                    )
                    participant_qube.chain_state.increment_block_count("GAME")

                    blocks_created.append({
                        "qube_id": participant_id,
                        "block_number": next_block_number,
                        "signatures": len(all_signatures)
                    })

                    logger.info(f"Created GAME block #{next_block_number} for Qube {participant_id} with {len(all_signatures)} signatures")

                except Exception as block_error:
                    logger.error(f"Failed to create GAME block for Qube {participant_id}: {block_error}")

            # Use the primary qube's block number for the response
            next_block_number = blocks_created[0]["block_number"] if blocks_created else 0
            logger.info(f"Game {game_summary['game_id']} ended - created {len(blocks_created)} multi-signed GAME blocks")

            # Award XP to chess skill for all Qube participants
            from utils.skills_manager import SkillsManager
            for participant_id, participant_qube_obj in qube_participants:
                try:
                    skills_manager = SkillsManager(participant_qube_obj.data_dir)
                    xp_result = skills_manager.add_xp(
                        skill_id="chess",
                        xp_amount=game_summary["xp_earned"],
                        evidence_description=f"Completed chess game: {result} in {game_summary['total_moves']} moves"
                    )
                    logger.info(f"Awarded {game_summary['xp_earned']} XP to chess skill for {participant_id}: {xp_result}")
                except Exception as xp_error:
                    logger.warning(f"Failed to award XP to {participant_id}: {xp_error}")

            return {
                "success": True,
                "game_summary": game_summary,
                "block_number": next_block_number,
                "blocks_created": blocks_created,  # All GAME blocks created
                "xp_earned": game_summary["xp_earned"]
            }

        except Exception as e:
            logger.error(f"Failed to end game: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def abandon_game(self, qube_id: str, password: str) -> Dict[str, Any]:
        """
        Abandon the active game without creating a GAME block.

        Args:
            qube_id: Qube whose game to abandon
            password: User's master password

        Returns:
            Dict with success status
        """
        try:
            self.orchestrator.set_master_key(password)
            qube = await self.orchestrator.load_qube(qube_id)

            if not qube:
                return {"success": False, "error": f"Qube {qube_id} not found"}

            if not hasattr(qube, 'game_manager') or qube.game_manager is None:
                return {"success": False, "error": "Game manager not initialized"}

            if qube.game_manager.active_game is None:
                return {"success": True, "message": "No active game to abandon"}

            # Get opponent info before abandoning
            active_game = qube.game_manager.active_game
            white_player_info = active_game.white_player if active_game else None
            black_player_info = active_game.black_player if active_game else None

            qube.game_manager.abandon_game()

            logger.info(f"Abandoned game for qube {qube_id}")

            # Also abandon the opponent's game if it's a Qube vs Qube game
            if white_player_info and black_player_info:
                opponent_info = black_player_info if white_player_info.get("id") == qube_id else white_player_info
                if opponent_info.get("type") == "qube":
                    opponent_qube_id = opponent_info.get("id")
                    try:
                        opponent_qube = await self.orchestrator.load_qube(opponent_qube_id)
                        if opponent_qube and opponent_qube.game_manager and opponent_qube.game_manager.active_game:
                            logger.info(f"Abandoning game for opponent Qube {opponent_qube_id}")
                            opponent_qube.game_manager.abandon_game()
                    except Exception as opp_abandon_e:
                        logger.warning(f"Failed to abandon game for opponent Qube: {opp_abandon_e}")

            return {"success": True, "message": "Game abandoned"}

        except Exception as e:
            logger.error(f"Failed to abandon game: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def resign_game(self, qube_id: str, password: str, resigning_player: str) -> Dict[str, Any]:
        """
        Resign the current game (counts as a loss for the resigning player).

        Args:
            qube_id: Qube whose game to resign
            password: User's master password
            resigning_player: 'white' or 'black'

        Returns:
            Dict with success status and game summary
        """
        try:
            self.orchestrator.set_master_key(password)
            qube = await self.orchestrator.load_qube(qube_id)

            if not qube:
                return {"success": False, "error": f"Qube {qube_id} not found"}

            if not hasattr(qube, 'game_manager') or qube.game_manager is None:
                return {"success": False, "error": "Game manager not initialized"}

            if qube.game_manager.active_game is None:
                return {"success": False, "error": "No active game to resign"}

            result = qube.game_manager.resign_game(resigning_player)

            if result.get("success"):
                logger.info(f"Game resigned by {resigning_player} for qube {qube_id}")

            return result

        except Exception as e:
            logger.error(f"Failed to resign game: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def offer_draw(self, qube_id: str, password: str, offering_player: str) -> Dict[str, Any]:
        """
        Offer a draw in the current game.

        Args:
            qube_id: Qube whose game to offer draw in
            password: User's master password
            offering_player: 'white' or 'black'

        Returns:
            Dict with success status
        """
        try:
            self.orchestrator.set_master_key(password)
            qube = await self.orchestrator.load_qube(qube_id)

            if not qube:
                return {"success": False, "error": f"Qube {qube_id} not found"}

            if not hasattr(qube, 'game_manager') or qube.game_manager is None:
                return {"success": False, "error": "Game manager not initialized"}

            if qube.game_manager.active_game is None:
                return {"success": False, "error": "No active game"}

            result = qube.game_manager.offer_draw(offering_player)
            return result

        except Exception as e:
            logger.error(f"Failed to offer draw: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def respond_to_draw(self, qube_id: str, password: str, accepting: bool, responding_player: str) -> Dict[str, Any]:
        """
        Respond to a draw offer.

        Args:
            qube_id: Qube whose game to respond to draw in
            password: User's master password
            accepting: True to accept, False to decline
            responding_player: 'white' or 'black'

        Returns:
            Dict with success status (and game summary if accepted)
        """
        try:
            self.orchestrator.set_master_key(password)
            qube = await self.orchestrator.load_qube(qube_id)

            if not qube:
                return {"success": False, "error": f"Qube {qube_id} not found"}

            if not hasattr(qube, 'game_manager') or qube.game_manager is None:
                return {"success": False, "error": "Game manager not initialized"}

            if qube.game_manager.active_game is None:
                return {"success": False, "error": "No active game"}

            result = qube.game_manager.respond_to_draw(accepting, responding_player)

            if result.get("success") and accepting:
                logger.info(f"Draw accepted for qube {qube_id}")

            return result

        except Exception as e:
            logger.error(f"Failed to respond to draw: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def _calculate_trash_talk_chance(self, game_context: Dict[str, Any], last_move_info: Optional[Dict] = None) -> tuple:
        """
        Calculate probability of trash talk based on game events.

        Returns:
            tuple: (should_talk: bool, context_hint: str)
        """
        import random

        base_chance = 0.25  # 25% base chance for normal moves
        context_hint = ""

        # Check game state
        is_check = game_context.get("is_check", False)
        total_moves = game_context.get("total_moves", 0)

        # Calculate material from FEN
        fen = game_context.get("fen", "")
        piece_values = {'p': 1, 'n': 3, 'b': 3, 'r': 5, 'q': 9}
        white_material = 0
        black_material = 0

        if fen:
            board_part = fen.split(' ')[0]
            for char in board_part:
                if char.lower() in piece_values:
                    if char.isupper():
                        white_material += piece_values[char.lower()]
                    else:
                        black_material += piece_values[char]

        qube_color = game_context.get("qube_color", "white")
        qube_material = white_material if qube_color == "white" else black_material
        opp_material = black_material if qube_color == "white" else white_material
        material_diff = qube_material - opp_material

        # Adjust chance based on events
        if is_check:
            base_chance += 0.40  # +40% if opponent is in check
            context_hint = "You just put your opponent in check!"

        if material_diff >= 3:
            base_chance += 0.25  # +25% if winning by 3+ material
            context_hint = "You're ahead in material - feeling confident!"
        elif material_diff <= -3:
            base_chance += 0.20  # +20% if losing (excuses/determination)
            context_hint = "You're behind but fighting back!"

        # Opening phase commentary (moves 1-6)
        if total_moves <= 6:
            base_chance += 0.15
            if not context_hint:
                context_hint = "Opening phase - establish your style!"

        # Check for pending human chat messages to respond to (always respond)
        chat_messages = game_context.get("chat_messages", [])
        if chat_messages:
            last_msg = chat_messages[-1]
            if last_msg.get("sender_type") == "human":
                return True, f"The human just said: \"{last_msg.get('message', '')[:100]}\" - respond to them!"

        # Cap at 90%
        final_chance = min(0.90, base_chance)

        should_talk = random.random() < final_chance
        return should_talk, context_hint

    async def request_qube_move(
        self,
        qube_id: str,
        password: str
    ) -> Dict[str, Any]:
        """
        Request a Qube to make a chess move in the active game.

        This sends a message to the Qube asking it to analyze the position
        and make its move using the chess_move tool.

        Args:
            qube_id: Qube to request move from
            password: User's master password

        Returns:
            Dict with move result from Qube
        """
        try:
            self.orchestrator.set_master_key(password)
            qube = await self.orchestrator.load_qube(qube_id)

            if not qube:
                return {"success": False, "error": f"Qube {qube_id} not found"}

            if not hasattr(qube, 'game_manager') or qube.game_manager is None:
                return {"success": False, "error": "Game manager not initialized"}

            if qube.game_manager.active_game is None:
                return {"success": False, "error": "No active game"}

            # Get game context for the prompt
            game_context = qube.game_manager.get_game_context()
            if not game_context:
                return {"success": False, "error": "Could not get game context"}

            # Ensure AI is initialized
            if qube.reasoner is None:
                api_keys = self.orchestrator.get_api_keys()
                qube.init_ai(api_keys.to_dict())

            # Get recent chat messages to check for memory triggers
            recent_chat = None
            chat_messages = game_context.get("chat_messages", [])
            if chat_messages:
                # Get most recent human message
                human_messages = [m for m in chat_messages if m.get("sender_type") == "human"]
                if human_messages:
                    recent_chat = human_messages[-1].get("message")

            # Get game state BEFORE the move for comparison
            context_before = qube.game_manager.get_game_context()
            fen_before = context_before.get("fen") if context_before else None
            logger.info(f"[CHESS DEBUG] FEN before AI call: {fen_before}")

            # Use lightweight game action processing (no memory search unless triggered)
            response = None
            ai_error = None
            try:
                response = await qube.reasoner.process_game_action(
                    game_context=game_context,
                    user_chat=recent_chat  # Will trigger memory search only if needed
                )
                logger.info(f"[CHESS DEBUG] AI response: {response[:500] if response else 'None'}")
            except Exception as ai_e:
                # AI processing failed, but the chess move might still have succeeded
                logger.warning(f"[CHESS DEBUG] AI processing error (may be ok if move succeeded): {ai_e}")
                ai_error = str(ai_e)

            # Get updated game state after the move
            updated_context = qube.game_manager.get_game_context()
            fen_after = updated_context.get("fen") if updated_context else None
            logger.info(f"[CHESS DEBUG] FEN after AI call: {fen_after}")
            logger.info(f"[CHESS DEBUG] FEN changed: {fen_before != fen_after}")

            # If the FEN changed, the move was successful even if AI had issues
            if fen_before != fen_after:
                logger.info("[CHESS DEBUG] Move succeeded (FEN changed), returning success")

                # CRITICAL: Sync move to opponent's game_manager for Qube vs Qube mode
                # This ensures both Qubes have synchronized game state
                active_game = qube.game_manager.active_game
                if active_game:
                    # Check if opponent is a Qube
                    white_player = active_game.white_player
                    black_player = active_game.black_player

                    # Determine which player is the opponent
                    if white_player.get("id") == qube.qube_id:
                        opponent_info = black_player
                    else:
                        opponent_info = white_player

                    # If opponent is a Qube, sync the game state
                    if opponent_info.get("type") == "qube":
                        opponent_qube_id = opponent_info.get("id")
                        logger.info(f"[CHESS DEBUG] Syncing move to opponent Qube: {opponent_qube_id}")
                        try:
                            opponent_qube = await self.orchestrator.load_qube(opponent_qube_id)
                            if opponent_qube and opponent_qube.game_manager and opponent_qube.game_manager.active_game:
                                # Sync the FEN, moves, and chat messages
                                opponent_game = opponent_qube.game_manager.active_game
                                opponent_game.fen = active_game.fen
                                opponent_game.moves = active_game.moves.copy()
                                opponent_game.chat_messages = active_game.chat_messages.copy()
                                opponent_game.last_move_at = active_game.last_move_at
                                opponent_qube.game_manager._save_game_state()
                                logger.info(f"[CHESS DEBUG] Synced game state to opponent Qube {opponent_qube_id}")
                        except Exception as sync_e:
                            logger.warning(f"[CHESS DEBUG] Failed to sync to opponent: {sync_e}")

                return {
                    "success": True,
                    "qube_response": response or "Move completed",
                    "game_state": updated_context,
                    "ai_warning": ai_error  # Include warning if there was one
                }
            elif ai_error:
                # FEN didn't change AND there was an error - actual failure
                return {"success": False, "error": ai_error}
            else:
                # No error but FEN didn't change - shouldn't happen
                return {
                    "success": True,
                    "qube_response": response,
                    "game_state": updated_context
                }

        except Exception as e:
            logger.error(f"Failed to request qube move: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    # =========================================================================
    # Wallet Management Methods
    # =========================================================================

    def _get_wallet_info_from_genesis(self, genesis_block) -> Optional[Dict[str, Any]]:
        """
        Extract wallet info from genesis block, handling both SimpleNamespace and Block objects.

        Args:
            genesis_block: Genesis block (can be SimpleNamespace or Block object)

        Returns:
            Wallet info dict or None if not found
        """
        if not genesis_block:
            return None

        # Try different access patterns
        wallet_info = None

        # Pattern 1: Block object with content dict
        if hasattr(genesis_block, 'content') and isinstance(genesis_block.content, dict):
            wallet_info = genesis_block.content.get("wallet")
        # Pattern 2: SimpleNamespace with wallet attribute
        elif hasattr(genesis_block, 'wallet'):
            wallet_info = genesis_block.wallet

        if wallet_info is None:
            return None

        # Convert SimpleNamespace to dict if needed
        if hasattr(wallet_info, '__dict__') and not isinstance(wallet_info, dict):
            wallet_info = vars(wallet_info)

        return wallet_info if isinstance(wallet_info, dict) else None

    async def get_qube_wallet_info(
        self,
        qube_id: str,
        password: str
    ) -> Dict[str, Any]:
        """
        Get wallet address, balance, and pending transactions for a Qube.

        Args:
            qube_id: Qube ID
            password: User's master password

        Returns:
            Dict with wallet info including address, balance, pending_txs
        """
        from blockchain.wallet_tx import WalletTransactionManager

        try:
            self.orchestrator.set_master_key(password)
            qube = await self.orchestrator.load_qube(qube_id)

            if not qube:
                return {"success": False, "error": f"Qube {qube_id} not found"}

            # Check if wallet is initialized
            wallet_info = self._get_wallet_info_from_genesis(qube.genesis_block)
            if not wallet_info:
                return {"success": False, "error": "Qube does not have a wallet configured"}

            p2sh_address = wallet_info.get("p2sh_address")
            if not p2sh_address:
                return {"success": False, "error": "Wallet address not found in genesis block"}

            # Initialize wallet transaction manager
            wallet_manager = WalletTransactionManager(qube, self.orchestrator.data_dir)
            pending_txs = wallet_manager.get_pending_transactions()

            # Get owner pubkey and derive NFT address
            owner_pubkey = wallet_info.get("owner_pubkey")
            nft_address = None
            if owner_pubkey:
                from crypto.bch_script import pubkey_to_token_address
                nft_address = pubkey_to_token_address(owner_pubkey, "mainnet")

            # Fetch both balances in parallel for speed
            import aiohttp
            import asyncio

            async def fetch_p2sh_balance():
                try:
                    return await asyncio.wait_for(
                        wallet_manager.wallet.get_balance(),
                        timeout=10.0
                    )
                except asyncio.TimeoutError:
                    logger.warning("P2SH balance fetch timed out")
                    return 0
                except Exception as e:
                    logger.warning(f"P2SH balance fetch failed: {e}")
                    return 0

            async def fetch_nft_balance():
                if not nft_address:
                    return 0
                try:
                    # Use Blockchair API (same as wallet uses) - need to use q address
                    # since z and q share the same pubkey hash
                    from crypto.bch_script import pubkey_to_p2pkh_address
                    q_address = pubkey_to_p2pkh_address(owner_pubkey, "mainnet", token_aware=False)

                    timeout = aiohttp.ClientTimeout(total=10)
                    async with aiohttp.ClientSession(timeout=timeout) as session:
                        url = f"https://api.blockchair.com/bitcoin-cash/dashboards/address/{q_address}"
                        async with session.get(url) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                if "data" in data and q_address in data["data"]:
                                    return data["data"][q_address]["address"]["balance"]
                    return 0
                except Exception as e:
                    logger.warning(f"NFT balance fetch failed: {e}")
                    return 0

            # Run both fetches in parallel
            p2sh_balance, nft_balance = await asyncio.gather(
                fetch_p2sh_balance(),
                fetch_nft_balance()
            )

            return {
                "success": True,
                "qube_id": qube_id,
                "wallet_address": p2sh_address,
                "nft_address": nft_address,  # Owner's 'z' address
                "owner_pubkey": wallet_info.get("owner_pubkey"),
                "qube_pubkey": wallet_info.get("qube_pubkey"),
                "balance_sats": p2sh_balance,  # P2SH wallet balance
                "balance_bch": p2sh_balance / 100_000_000,
                "nft_balance_sats": nft_balance,  # Owner's NFT address balance
                "nft_balance_bch": nft_balance / 100_000_000,
                "pending_transactions": [
                    {
                        "tx_id": tx.tx_id,
                        "outputs": tx.outputs,
                        "total_amount": tx.total_amount,
                        "fee": tx.fee,
                        "status": tx.status,
                        "created_at": datetime.fromtimestamp(tx.created_at).isoformat(),
                        "expires_at": datetime.fromtimestamp(tx.expires_at).isoformat() if tx.expires_at else None,
                        "memo": tx.memo
                    }
                    for tx in pending_txs
                ]
            }

        except Exception as e:
            logger.error(f"Failed to get wallet info: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def get_context_preview(
        self,
        qube_id: str,
        password: str
    ) -> Dict[str, Any]:
        """
        Get preview of what's in the Qube's active context and short-term memory.

        This shows the user everything that would be injected into the AI's context
        window when processing a message.

        Args:
            qube_id: Qube ID
            password: User's master password

        Returns:
            Dict with active_context and short_term_memory sections
        """
        try:
            self.orchestrator.set_master_key(password)
            qube = await self.orchestrator.load_qube(qube_id)

            if not qube:
                return {"success": False, "error": f"Qube {qube_id} not found"}

            # Initialize session if needed (to access session blocks)
            if not hasattr(qube, 'session') or qube.session is None:
                from core.session import Session
                qube.session = Session(qube)

            # Build active context (always-present identity data)
            active_context = await self._build_active_context_preview(qube)

            # Build short-term memory (blocks in context window)
            short_term_memory = await self._build_short_term_memory_preview(qube)

            return {
                "success": True,
                "active_context": active_context,
                "short_term_memory": short_term_memory
            }

        except Exception as e:
            logger.error(f"Failed to get context preview: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def _build_active_context_preview(self, qube) -> Dict[str, Any]:
        """
        Build preview of active context (always-present identity data).
        """
        from utils.time_format import format_timestamp

        genesis = qube.genesis_block

        # Genesis Identity
        genesis_identity = {
            "name": genesis.qube_name,
            "qube_id": qube.qube_id,
            "birth_date": format_timestamp(genesis.birth_timestamp) if genesis.birth_timestamp else None,
            "genesis_prompt": genesis.genesis_prompt,
            "favorite_color": genesis.favorite_color or "#4A90E2",
            "ai_model": genesis.ai_model,
            "voice_model": genesis.voice_model,
            "creator": genesis.creator,
            "nft_category_id": getattr(genesis, 'nft_category_id', None),
            "mint_txid": getattr(genesis, 'mint_txid', None)
        }

        # Relationships (top 5 by interaction count)
        relationships = []
        try:
            # Reload relationships from disk to get latest
            qube.relationships.storage._load_relationships()
            all_rels = qube.relationships.get_all_relationships()

            # Sort by total messages (sent + received) and take top 5
            sorted_rels = sorted(
                all_rels,
                key=lambda r: (r.messages_sent or 0) + (r.messages_received or 0),
                reverse=True
            )[:5]

            for rel in sorted_rels:
                # Use entity_name if available, otherwise entity_id
                name = getattr(rel, 'entity_name', None) or rel.entity_id
                # Trust is 0-100, convert to 0-1 for display
                trust = getattr(rel, 'trust', 0) / 100.0
                # Calculate interaction count from messages
                interaction_count = (getattr(rel, 'messages_sent', 0) or 0) + (getattr(rel, 'messages_received', 0) or 0)

                relationships.append({
                    "entity_id": rel.entity_id[:16] + "..." if len(rel.entity_id) > 16 else rel.entity_id,
                    "name": name,
                    "status": getattr(rel, 'status', 'unknown') or "unknown",
                    "trust_level": round(trust, 2),
                    "interaction_count": interaction_count
                })
        except Exception as e:
            logger.warning(f"Failed to load relationships for context preview: {e}")

        # Skills summary
        skills = []
        skills_total = {"total_xp": 0, "unlocked_skills": 0, "categories": 0}
        try:
            from utils.skills_manager import SkillsManager
            skills_manager = SkillsManager(qube.data_dir)
            skills_manager.load_skills()
            summary = skills_manager.get_skill_summary()

            # Get top categories by unlocked count - use correct keys
            top_categories = sorted(
                summary.get("by_category", {}).items(),
                key=lambda x: x[1].get("unlocked", 0),
                reverse=True
            )[:5]

            for category_id, stats in top_categories:
                if stats.get("unlocked", 0) > 0:  # Only show if has unlocked skills
                    skills.append({
                        "skill_id": category_id,
                        "total_xp": 0,  # XP is per-skill, not per-category in this structure
                        "unlocked": stats.get("unlocked", 0),
                        "total": stats.get("total", 0),
                        "level": 1  # Categories don't have levels
                    })

            # Add total stats - use correct keys from SkillsManager.get_skill_summary()
            skills_total = {
                "total_xp": summary.get("total_xp", 0),
                "unlocked_skills": summary.get("unlocked_skills", 0),
                "categories": len(summary.get("by_category", {}))
            }
        except Exception as e:
            logger.warning(f"Failed to load skills for context preview: {e}")

        # Wallet info with balance and recent transactions
        wallet = None
        try:
            wallet_info = self._get_wallet_info_from_genesis(genesis)
            if wallet_info:
                p2sh_address = wallet_info.get("p2sh_address")
                balance_sats = 0
                recent_transactions = []

                # Try to fetch balance and transactions
                try:
                    from blockchain.wallet_tx import WalletTransactionManager
                    wallet_manager = WalletTransactionManager(qube, self.orchestrator.data_dir)

                    # Get balance with persistent caching (loads from disk if API fails)
                    balance_sats = await asyncio.wait_for(
                        wallet_manager.get_balance_with_cache(),
                        timeout=5.0
                    )

                    # Get recent transactions (up to 3)
                    try:
                        tx_history = await asyncio.wait_for(
                            wallet_manager.wallet.get_transaction_history(limit=3),
                            timeout=5.0
                        )
                        for tx in tx_history:
                            recent_transactions.append({
                                "txid": tx.get("txid", "")[:16] + "..." if tx.get("txid") else "",
                                "amount_sats": tx.get("amount", 0),
                                "type": "received" if tx.get("amount", 0) > 0 else "sent",
                                "timestamp": tx.get("timestamp"),
                                "confirmations": tx.get("confirmations", 0)
                            })
                    except Exception as tx_err:
                        logger.debug(f"Could not fetch transaction history: {tx_err}")

                except Exception as bal_err:
                    logger.debug(f"Could not fetch wallet balance: {bal_err}")

                wallet = {
                    "p2sh_address": p2sh_address,
                    "balance_sats": balance_sats,
                    "balance_bch": balance_sats / 100_000_000 if balance_sats else 0,
                    "recent_transactions": recent_transactions,
                    "has_wallet": True
                }
        except Exception as e:
            logger.warning(f"Failed to load wallet for context preview: {e}")

        # Owner Info summary
        owner_info = None
        try:
            from utils.owner_info_manager import OwnerInfoManager
            from crypto.keys import serialize_private_key
            import hashlib

            # Derive encryption key
            private_key_bytes = serialize_private_key(qube.private_key)
            encryption_key = hashlib.sha256(private_key_bytes).digest()

            manager = OwnerInfoManager(qube.data_dir, encryption_key)
            summary = manager.get_summary()

            if summary.get("total_fields", 0) > 0:
                owner_info = {
                    "total_fields": summary.get("total_fields", 0),
                    "public_fields": summary.get("public_fields", 0),
                    "private_fields": summary.get("private_fields", 0),
                    "secret_fields": summary.get("secret_fields", 0),
                    "categories_populated": summary.get("categories_populated", 0),
                    "top_fields": summary.get("top_fields", [])
                }
        except Exception as e:
            logger.warning(f"Failed to load owner info for context preview: {e}")

        return {
            "genesis_identity": genesis_identity,
            "relationships": {
                "count": len(relationships),
                "top_relationships": relationships
            },
            "skills": {
                "totals": skills_total,
                "top_skills": skills
            },
            "owner_info": owner_info,
            "wallet": wallet
        }

    async def _build_short_term_memory_preview(self, qube) -> Dict[str, Any]:
        """
        Build preview of short-term memory (blocks in context window).
        """
        from ai.tools.memory_search import intelligent_memory_search

        # Semantic recalls (from last query)
        semantic_recalls = []
        recalled_block_numbers = set()

        try:
            # Get recent context to search
            session = qube.current_session
            recent_messages = []
            if session and hasattr(session, 'session_blocks') and session.session_blocks:
                for block in session.session_blocks[-3:]:
                    content = block.content if isinstance(block.content, dict) else {}
                    if "message" in content:
                        recent_messages.append(content["message"][:200])

            if recent_messages:
                query = " ".join(recent_messages)
                results = await intelligent_memory_search(
                    qube=qube,
                    query=query,
                    context={"query_type": "context_preview"},
                    top_k=5
                )

                for result in results:
                    block = result.block
                    block_num = block.get("block_number", -1)
                    recalled_block_numbers.add(block_num)
                    semantic_recalls.append({
                        "block_number": block_num,
                        "block_type": block.get("block_type", "UNKNOWN"),
                        "relevance_score": round(result.score, 2),
                        "preview": self._get_block_preview(block)
                    })
        except Exception as e:
            logger.warning(f"Failed to get semantic recalls: {e}")

        # Recent permanent blocks (with summary exclusion awareness)
        recent_blocks = []
        recent_blocks_content_chars = 0
        try:
            from ai.reasoner import QubeReasoner
            reasoner = QubeReasoner(qube)
            permanent_blocks = reasoner._get_recent_permanent_blocks(
                limit=10,
                recalled_block_numbers=recalled_block_numbers
            )

            for block in permanent_blocks:
                content = block.content if isinstance(block.content, dict) else {}
                if block.encrypted and "ciphertext" in content:
                    try:
                        content = qube.decrypt_block_content(content)
                    except:
                        content = {"preview": "[Encrypted]"}

                # Track actual content size for token estimation
                try:
                    content_str = json.dumps(content, default=str) if isinstance(content, dict) else str(content)
                    recent_blocks_content_chars += len(content_str)
                except:
                    recent_blocks_content_chars += 500  # Fallback estimate

                recent_blocks.append({
                    "block_number": block.block_number,
                    "block_type": block.block_type if isinstance(block.block_type, str) else block.block_type.value,
                    "timestamp": block.timestamp,
                    "is_summary": block.block_type == "SUMMARY",
                    "preview": self._get_block_preview({"content": content, "block_type": block.block_type})
                })
        except Exception as e:
            logger.warning(f"Failed to get recent permanent blocks: {e}")

        # Session blocks
        session_blocks = []
        session_blocks_content_chars = 0
        try:
            session = qube.current_session
            if session and hasattr(session, 'session_blocks') and session.session_blocks:
                for block in session.session_blocks[-10:]:
                    content = block.content if isinstance(block.content, dict) else {}

                    # Track actual content size for token estimation
                    try:
                        content_str = json.dumps(content, default=str) if isinstance(content, dict) else str(content)
                        session_blocks_content_chars += len(content_str)
                    except:
                        session_blocks_content_chars += 500  # Fallback estimate

                    session_blocks.append({
                        "block_number": block.block_number,
                        "block_type": block.block_type if isinstance(block.block_type, str) else block.block_type.value,
                        "timestamp": block.timestamp,
                        "preview": self._get_block_preview({"content": content, "block_type": block.block_type})
                    })
        except Exception as e:
            logger.warning(f"Failed to get session blocks: {e}")

        # Estimate total tokens in short-term memory
        # Use ~4 characters per token as a rough approximation
        total_chars = 0

        # Add actual content sizes from blocks we tracked
        total_chars += recent_blocks_content_chars
        total_chars += session_blocks_content_chars

        # Semantic recalls - estimate from preview * 10 (previews are very truncated)
        # Each recalled block typically has 500-2000 chars of actual content
        for block in semantic_recalls:
            preview_len = len(block.get("preview", ""))
            # Estimate actual content is ~10x the preview (preview is 100 chars, content is ~1000)
            total_chars += max(preview_len * 10, 500)

        # Add estimate for active context (genesis prompt, system instructions, etc.)
        # This is typically 500-1500 tokens worth of content
        genesis_prompt = qube.genesis_block.genesis_prompt if qube.genesis_block else ""
        total_chars += len(genesis_prompt)
        total_chars += 1000  # Base system prompt overhead

        # Add estimate for owner info context
        # Each field is roughly 50-100 chars (key + value + formatting)
        try:
            from utils.owner_info_manager import OwnerInfoManager
            from crypto.keys import serialize_private_key
            import hashlib

            private_key_bytes = serialize_private_key(qube.private_key)
            encryption_key = hashlib.sha256(private_key_bytes).digest()
            manager = OwnerInfoManager(qube.data_dir, encryption_key)
            summary = manager.get_summary()

            # Estimate: each injectable field is ~75 chars on average
            # Only count non-secret fields (public + private)
            injectable_count = summary.get("public_fields", 0) + summary.get("private_fields", 0)
            total_chars += injectable_count * 75
        except Exception:
            pass  # If owner info fails, just skip the estimate

        estimated_tokens = total_chars // 4

        # Get max context window for this qube's AI model
        # Try multiple possible attribute names
        model_name = getattr(qube, 'current_ai_model', None)
        if not model_name:
            model_name = getattr(qube, 'ai_model', None)
        if not model_name and qube.genesis_block:
            model_name = getattr(qube.genesis_block, 'ai_model', None)
        if not model_name:
            model_name = 'unknown'
        max_context_window = self._get_model_context_window(model_name)

        return {
            "semantic_recalls": {
                "count": len(semantic_recalls),
                "blocks": semantic_recalls
            },
            "recent_permanent": {
                "count": len(recent_blocks),
                "blocks": recent_blocks
            },
            "session": {
                "count": len(session_blocks),
                "blocks": session_blocks
            },
            "estimated_tokens": estimated_tokens,
            "max_context_window": max_context_window
        }

    def _get_model_context_window(self, model_name: str | None) -> int:
        """Get the context window size for a given model name."""
        if not model_name:
            return 128000  # Default fallback

        # Consolidated context windows from all providers
        # Includes both full API names and short aliases
        CONTEXT_WINDOWS = {
            # Anthropic - full names
            "claude-sonnet-4-5-20250929": 200000,
            "claude-opus-4-1-20250805": 200000,
            "claude-opus-4-20250514": 200000,
            "claude-sonnet-4-20250514": 1000000,
            "claude-3-7-sonnet-20250219": 200000,
            "claude-3-5-haiku-20241022": 200000,
            "claude-3-haiku-20240307": 200000,
            # Anthropic - short aliases
            "claude-sonnet-4.5": 200000,
            "claude-opus-4.1": 200000,
            "claude-opus-4": 200000,
            "claude-sonnet-4": 1000000,
            "claude-3.5-sonnet": 200000,
            "claude-3.5-haiku": 200000,
            "claude-3-haiku": 200000,
            # OpenAI - these are already short names
            "gpt-5": 256000,
            "gpt-5-mini": 128000,
            "gpt-5-nano": 64000,
            "gpt-5-codex": 256000,
            "gpt-4.1": 1000000,
            "gpt-4.1-mini": 128000,
            "gpt-4o": 128000,
            "gpt-4o-mini": 128000,
            "o4-mini": 128000,
            "o3-mini": 128000,
            "o1": 200000,
            # Google - these are already short names
            "gemini-2.5-pro": 2000000,
            "gemini-2.5-flash": 1000000,
            "gemini-2.5-flash-lite": 1000000,
            "gemini-2.0-flash": 1000000,
            "gemini-1.5-pro": 2000000,
            # DeepSeek - these are already short names
            "deepseek-chat": 64000,
            "deepseek-reasoner": 64000,
            # Venice - private AI models
            "venice-uncensored": 131072,
            "llama-3.3-70b": 65536,
            "qwen3-235b": 131072,
            "qwen3-4b": 131072,
            "deepseek-r1-llama-70b": 131072,
            "mistral-31-24b": 131072,
            # Perplexity - these are already short names
            "sonar-pro": 127000,
            "sonar": 127000,
            "sonar-reasoning-pro": 127000,
            "sonar-reasoning": 127000,
            "sonar-deep-research": 127000,
            # Ollama (local) - these are already short names
            "llama3.3:70b": 128000,
            "qwen3:235b": 32768,
            "qwen3:30b": 32768,
            "qwen2.5:7b": 32768,
            "deepseek-r1:8b": 32768,
            "phi4:14b": 16384,
            "gemma2:9b": 8192,
            "mistral:7b": 8192,
            "codellama:7b": 16384,
        }
        # Default to 128K if model not found
        return CONTEXT_WINDOWS.get(model_name, 128000)

    def _get_block_preview(self, block: dict) -> str:
        """Get a short preview of block content."""
        content = block.get("content", {})
        if isinstance(content, str):
            return content[:100] + "..." if len(content) > 100 else content

        block_type = block.get("block_type", "")
        if block_type == "SUMMARY":
            summary = content.get("summary", "")
            return summary[:100] + "..." if len(summary) > 100 else summary

        # MESSAGE block
        msg = content.get("message", content.get("response", ""))
        if msg:
            return msg[:100] + "..." if len(msg) > 100 else msg

        return "[No preview available]"

    def _calculate_skill_level(self, xp: int) -> int:
        """Calculate skill level from XP."""
        if xp < 100:
            return 1
        elif xp < 500:
            return 2
        elif xp < 1500:
            return 3
        elif xp < 5000:
            return 4
        else:
            return 5

    async def propose_wallet_transaction(
        self,
        qube_id: str,
        to_address: str,
        amount_satoshis: int,
        memo: str,
        password: str
    ) -> Dict[str, Any]:
        """
        Qube proposes a wallet transaction that requires owner approval.

        Args:
            qube_id: Qube ID
            to_address: BCH address to send to
            amount_satoshis: Amount in satoshis
            memo: Transaction memo/reason
            password: User's master password

        Returns:
            Dict with pending transaction info
        """
        from blockchain.wallet_tx import WalletTransactionManager

        try:
            self.orchestrator.set_master_key(password)
            qube = await self.orchestrator.load_qube(qube_id)

            if not qube:
                return {"success": False, "error": f"Qube {qube_id} not found"}

            # Check if wallet is initialized
            wallet_info = self._get_wallet_info_from_genesis(qube.genesis_block)
            if not wallet_info:
                return {"success": False, "error": "Qube does not have a wallet configured"}

            # Initialize wallet transaction manager
            wallet_manager = WalletTransactionManager(qube, self.orchestrator.data_dir)

            # Propose the transaction (Qube signs, waits for owner approval)
            pending_tx = await wallet_manager.propose_send(to_address, amount_satoshis, memo)

            return {
                "success": True,
                "pending_tx": {
                    "tx_id": pending_tx.tx_id,
                    "outputs": pending_tx.outputs,
                    "total_amount": pending_tx.total_amount,
                    "fee": pending_tx.fee,
                    "status": pending_tx.status,
                    "created_at": datetime.fromtimestamp(pending_tx.created_at).isoformat(),
                    "expires_at": datetime.fromtimestamp(pending_tx.expires_at).isoformat() if pending_tx.expires_at else None,
                    "memo": pending_tx.memo
                }
            }

        except Exception as e:
            logger.error(f"Failed to propose wallet transaction: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def approve_wallet_transaction(
        self,
        qube_id: str,
        pending_tx_id: str,
        owner_wif: str,
        password: str
    ) -> Dict[str, Any]:
        """
        Owner approves a pending Qube wallet transaction by co-signing.

        Args:
            qube_id: Qube ID
            pending_tx_id: ID of the pending transaction to approve
            owner_wif: Owner's WIF private key for signing
            password: User's master password

        Returns:
            Dict with broadcast transaction ID
        """
        from blockchain.wallet_tx import WalletTransactionManager

        try:
            self.orchestrator.set_master_key(password)
            qube = await self.orchestrator.load_qube(qube_id)

            if not qube:
                return {"success": False, "error": f"Qube {qube_id} not found"}

            # Check if wallet is initialized
            wallet_info = self._get_wallet_info_from_genesis(qube.genesis_block)
            if not wallet_info:
                return {"success": False, "error": "Qube does not have a wallet configured"}

            # Initialize wallet transaction manager
            wallet_manager = WalletTransactionManager(qube, self.orchestrator.data_dir)

            # Approve and broadcast (owner co-signs)
            txid = await wallet_manager.owner_approve(pending_tx_id, owner_wif)

            return {
                "success": True,
                "txid": txid,
                "message": f"Transaction broadcast successfully"
            }

        except Exception as e:
            logger.error(f"Failed to approve wallet transaction: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def reject_wallet_transaction(
        self,
        qube_id: str,
        pending_tx_id: str,
        password: str
    ) -> Dict[str, Any]:
        """
        Owner rejects a pending Qube wallet transaction.

        Args:
            qube_id: Qube ID
            pending_tx_id: ID of the pending transaction to reject
            password: User's master password

        Returns:
            Dict with success status
        """
        from blockchain.wallet_tx import WalletTransactionManager

        try:
            self.orchestrator.set_master_key(password)
            qube = await self.orchestrator.load_qube(qube_id)

            if not qube:
                return {"success": False, "error": f"Qube {qube_id} not found"}

            # Check if wallet is initialized
            wallet_info = self._get_wallet_info_from_genesis(qube.genesis_block)
            if not wallet_info:
                return {"success": False, "error": "Qube does not have a wallet configured"}

            # Initialize wallet transaction manager
            wallet_manager = WalletTransactionManager(qube, self.orchestrator.data_dir)

            # Reject the transaction
            wallet_manager.owner_reject(pending_tx_id)

            return {
                "success": True,
                "message": f"Transaction {pending_tx_id} rejected"
            }

        except Exception as e:
            logger.error(f"Failed to reject wallet transaction: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def owner_withdraw_from_wallet(
        self,
        qube_id: str,
        to_address: str,
        amount_satoshis: int,
        owner_wif: str,
        password: str
    ) -> Dict[str, Any]:
        """
        Owner withdraws funds directly from Qube wallet (owner-only path).

        This uses the IF branch of the P2SH script, allowing the owner
        to spend without Qube involvement.

        Args:
            qube_id: Qube ID
            to_address: BCH address to send to
            amount_satoshis: Amount in satoshis (0 for all)
            owner_wif: Owner's WIF private key
            password: User's master password

        Returns:
            Dict with broadcast transaction ID
        """
        from blockchain.wallet_tx import WalletTransactionManager

        try:
            self.orchestrator.set_master_key(password)
            qube = await self.orchestrator.load_qube(qube_id)

            if not qube:
                return {"success": False, "error": f"Qube {qube_id} not found"}

            # Check if wallet is initialized
            wallet_info = self._get_wallet_info_from_genesis(qube.genesis_block)
            if not wallet_info:
                return {"success": False, "error": "Qube does not have a wallet configured"}

            # Initialize wallet transaction manager
            wallet_manager = WalletTransactionManager(qube, self.orchestrator.data_dir)

            # Owner withdraw (uses IF branch - owner alone)
            if amount_satoshis == 0:
                # Withdraw all
                txid = await wallet_manager.owner_withdraw_all(to_address, owner_wif)
            else:
                txid = await wallet_manager.owner_withdraw(to_address, amount_satoshis, owner_wif)

            return {
                "success": True,
                "txid": txid,
                "message": f"Withdrawal broadcast successfully"
            }

        except Exception as e:
            logger.error(f"Failed to withdraw from wallet: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def get_wallet_transactions(
        self,
        qube_id: str,
        password: str,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Get transaction history for a Qube's wallet.

        Fetches blockchain transaction history and merges with local metadata
        (memos from Qube proposals).

        Args:
            qube_id: Qube ID
            password: User's master password
            limit: Maximum transactions to return (default 50)
            offset: Pagination offset (default 0)

        Returns:
            Dict with merged transaction history from blockchain + local data
        """
        from blockchain.wallet_tx import WalletTransactionManager

        try:
            self.orchestrator.set_master_key(password)
            qube = await self.orchestrator.load_qube(qube_id)

            if not qube:
                return {"success": False, "error": f"Qube {qube_id} not found"}

            # Check if wallet is initialized
            wallet_info = self._get_wallet_info_from_genesis(qube.genesis_block)
            if not wallet_info:
                return {"success": False, "error": "Qube does not have a wallet configured"}

            p2sh_address = wallet_info.get("p2sh_address")

            # Initialize wallet transaction manager
            wallet_manager = WalletTransactionManager(qube, self.orchestrator.data_dir)

            # Get pending transactions
            pending_txs = wallet_manager.get_pending_transactions()

            # Get merged blockchain + local transaction history
            history_result = await wallet_manager.get_full_transaction_history(
                limit=limit,
                offset=offset
            )

            # Format timestamps in transaction history for frontend
            transactions = history_result.get("transactions", [])
            for tx in transactions:
                # Convert Unix timestamp to ISO format
                if "timestamp" in tx and isinstance(tx["timestamp"], (int, float)):
                    tx["timestamp"] = datetime.fromtimestamp(tx["timestamp"]).isoformat()

            return {
                "success": True,
                "wallet_address": p2sh_address,
                "transactions": transactions,
                "total_count": history_result.get("total_count", 0),
                "has_more": history_result.get("has_more", False),
                "pending_transactions": [
                    {
                        "tx_id": tx.tx_id,
                        "outputs": tx.outputs,
                        "total_amount": tx.total_amount,
                        "fee": tx.fee,
                        "status": tx.status,
                        "created_at": datetime.fromtimestamp(tx.created_at).isoformat(),
                        "expires_at": datetime.fromtimestamp(tx.expires_at).isoformat() if tx.expires_at else None,
                        "memo": tx.memo
                    }
                    for tx in pending_txs
                ]
            }

        except Exception as e:
            logger.error(f"Failed to get wallet transactions: {e}", exc_info=True)
            return {"success": False, "error": str(e)}


async def main():
    """Main CLI entry point"""
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No command specified"}), file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1]

    # Handle setup wizard commands BEFORE creating GUIBridge
    # (GUIBridge creates default user directory which interferes with first-run detection)
    if command == "check-first-run":
        # Check if this is the first run (no users exist)
        data_dir = Path("data/users")
        if not data_dir.exists():
            print(json.dumps({"is_first_run": True, "users": []}))
        else:
            # List existing users (directories in data/users)
            users = [d.name for d in data_dir.iterdir() if d.is_dir()]
            print(json.dumps({
                "is_first_run": len(users) == 0,
                "users": users
            }))
        return

    elif command == "create-user-account":
        # Create a new user account
        if len(sys.argv) < 3:
            print(json.dumps({"success": False, "error": "User ID required"}), file=sys.stderr)
            sys.exit(1)

        user_id = validate_user_id(sys.argv[2])
        # Password from stdin (secure) or argv fallback (backwards compat)
        password = get_secret("password", argv_index=3)

        # Create data directory for user
        data_dir = Path(f"data/users/{user_id}")
        if data_dir.exists():
            print(json.dumps({"success": False, "error": "User already exists"}))
        else:
            # Create user directory and initialize with password
            data_dir.mkdir(parents=True, exist_ok=True)

            # Create orchestrator for user and set master key (generates salt)
            orchestrator = UserOrchestrator(user_id=user_id)
            orchestrator.set_master_key(password)

            # Create password verifier for secure authentication
            # This encrypts a known plaintext so we can verify the password later
            import secrets
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM

            verifier_file = data_dir / "password_verifier.enc"
            aesgcm = AESGCM(orchestrator.master_key)
            nonce = secrets.token_bytes(12)
            plaintext = b"QUBES_PASSWORD_VERIFIED"
            ciphertext = aesgcm.encrypt(nonce, plaintext, None)

            verifier_data = {
                "nonce": nonce.hex(),
                "ciphertext": ciphertext.hex(),
                "algorithm": "AES-256-GCM",
                "version": "1.0"
            }

            with open(verifier_file, 'w') as f:
                json.dump(verifier_data, f, indent=2)

            print(json.dumps({
                "success": True,
                "user_id": user_id,
                "data_dir": str(data_dir.absolute())
            }))
        return

    elif command == "check-ollama-status":
        # Check if Ollama is running (no bridge needed)
        import shutil

        ollama_path = shutil.which("ollama")
        if not ollama_path:
            # Check common locations
            common_paths = [
                Path.home() / "AppData" / "Local" / "Programs" / "Ollama" / "ollama.exe",
                Path("/usr/local/bin/ollama"),
                Path("/usr/bin/ollama"),
            ]
            for p in common_paths:
                if p.exists():
                    ollama_path = str(p)
                    break

        if not ollama_path:
            print(json.dumps({
                "installed": False,
                "running": False,
                "models": []
            }))
            return

        # Check if running by trying to list models
        import subprocess
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                # Parse model list
                models = []
                for line in result.stdout.strip().split('\n')[1:]:  # Skip header
                    if line.strip():
                        parts = line.split()
                        if parts:
                            models.append(parts[0])
                print(json.dumps({
                    "installed": True,
                    "running": True,
                    "models": models
                }))
            else:
                print(json.dumps({
                    "installed": True,
                    "running": False,
                    "models": []
                }))
        except subprocess.TimeoutExpired:
            print(json.dumps({
                "installed": True,
                "running": False,
                "models": []
            }))
        except Exception as e:
            print(json.dumps({
                "installed": True,
                "running": False,
                "models": [],
                "error": str(e)
            }))
        return

    bridge = GUIBridge()

    try:
        if command == "authenticate":
            # Parse arguments
            if len(sys.argv) < 3:
                print(json.dumps({"success": False, "error": "Username required"}), file=sys.stderr)
                sys.exit(1)

            # SECURITY: Validate user_id to prevent path traversal
            user_id = validate_user_id(sys.argv[2])
            # Password from stdin (secure) or argv fallback (backwards compat)
            password = get_secret("password", argv_index=3)

            result = await bridge.authenticate(user_id, password)
            print(json.dumps(result))

        elif command == "get-available-models":
            # No authentication required - this is public model metadata
            from ai.model_registry import ModelRegistry
            models_data = ModelRegistry.get_models_for_frontend()
            print(json.dumps(models_data))

        elif command == "list-qubes":
            if len(sys.argv) < 3:
                print(json.dumps({"error": "User ID required"}), file=sys.stderr)
                sys.exit(1)

            # SECURITY: Validate user_id to prevent path traversal
            user_id = validate_user_id(sys.argv[2])
            # Note: list_qubes doesn't need master key, it just reads metadata
            # Create bridge with correct user
            user_bridge = GUIBridge(user_id=user_id)
            qubes = await user_bridge.list_qubes()
            print(json.dumps(qubes))

        elif command == "create-qube":
            if len(sys.argv) < 3:
                print(json.dumps({"error": "User ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]

            # Parse arguments
            import argparse
            parser = argparse.ArgumentParser()
            parser.add_argument("command")  # Already consumed
            parser.add_argument("user_id")  # Already consumed
            parser.add_argument("--name", required=True)
            parser.add_argument("--genesis-prompt", required=True)
            parser.add_argument("--ai-provider", required=True)
            parser.add_argument("--ai-model", required=True)
            parser.add_argument("--voice-model", default="openai:alloy")
            parser.add_argument("--owner-pubkey", required=True)  # NFT address derived from this
            parser.add_argument("--password", default="")  # Password comes from stdin
            parser.add_argument("--encrypt-genesis", default="false")
            parser.add_argument("--favorite-color", default="#00ff88")
            parser.add_argument("--avatar-file", default=None)
            parser.add_argument("--generate-avatar", action="store_true", default=False)
            parser.add_argument("--avatar-style", default="cyberpunk")

            args = parser.parse_args()

            # Use stdin secret if available, fall back to argparse
            password = get_secret("password", required=False) or args.password

            # Create bridge with correct user
            user_bridge = GUIBridge(user_id=user_id)
            qube = await user_bridge.create_qube(
                name=args.name,
                genesis_prompt=args.genesis_prompt,
                ai_provider=args.ai_provider,
                ai_model=args.ai_model,
                voice_model=args.voice_model,
                owner_pubkey=args.owner_pubkey,  # NFT address derived from this
                password=password,
                encrypt_genesis=(args.encrypt_genesis.lower() == "true"),
                favorite_color=args.favorite_color,
                avatar_file=args.avatar_file,
                generate_avatar=args.generate_avatar,
                avatar_style=args.avatar_style,
            )
            print(json.dumps(qube))

        elif command == "get-qube":
            if len(sys.argv) < 3:
                print(json.dumps({"error": "Qube ID required"}), file=sys.stderr)
                sys.exit(1)

            # SECURITY: Validate qube_id to prevent path traversal
            qube_id = validate_qube_id(sys.argv[2])
            qube = await bridge.get_qube(qube_id)
            print(json.dumps(qube))

        elif command == "send-message":
            if len(sys.argv) < 5:
                print(json.dumps({"error": "User ID, Qube ID, and message required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            # SECURITY: Validate inputs to prevent injection
            qube_id = validate_qube_id(sys.argv[3])
            message_arg = sys.argv[4]  # Validated later in message processing
            password = get_secret("password", argv_index=5)

            # Check if message is a file reference
            if message_arg.startswith("@file:"):
                # Read message from file
                file_path = message_arg[6:]  # Remove @file: prefix
                with open(file_path, 'r', encoding='utf-8') as f:
                    message = f.read()
            else:
                message = message_arg

            # Create bridge with correct user
            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.send_message(qube_id, message, password)
            print(json.dumps(result))

        elif command == "anchor-session":
            if len(sys.argv) < 4:
                print(json.dumps({"error": "User ID and Qube ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            # SECURITY: Validate qube_id
            qube_id = validate_qube_id(sys.argv[3])
            password = get_secret("password", argv_index=4)

            # Create bridge with correct user
            user_bridge = GUIBridge(user_id=user_id)

            # Set master key
            user_bridge.orchestrator.set_master_key(password)

            # Load qube and anchor session
            if qube_id not in user_bridge.orchestrator.qubes:
                await user_bridge.orchestrator.load_qube(qube_id)

            qube = user_bridge.orchestrator.qubes[qube_id]
            blocks_anchored = await qube.anchor_session()

            print(json.dumps({"success": True, "blocks_anchored": blocks_anchored}))

        elif command == "check-sessions":
            if len(sys.argv) < 4:
                print(json.dumps({"error": "User ID and Qube ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            # SECURITY: Validate qube_id
            qube_id = validate_qube_id(sys.argv[3])

            # Create bridge with correct user
            user_bridge = GUIBridge(user_id=user_id)

            # Check if qube has session blocks
            qube_dir = Path(f"data/users/{user_id}/qubes")

            # Find the qube directory (format: {name}_{qube_id})
            qube_dirs = list(qube_dir.glob(f"*_{qube_id}"))

            has_session = False
            if qube_dirs:
                session_dir = qube_dirs[0] / "blocks" / "session"
                if session_dir.exists():
                    # Check if there are any JSON files
                    session_files = list(session_dir.glob("*.json"))
                    has_session = len(session_files) > 0

            print(json.dumps({"has_session": has_session}))

        elif command == "discard-session":
            if len(sys.argv) < 4:
                print(json.dumps({"error": "User ID and Qube ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            # SECURITY: Validate qube_id
            qube_id = validate_qube_id(sys.argv[3])
            password = get_secret("password", argv_index=4)

            # Create bridge with correct user
            user_bridge = GUIBridge(user_id=user_id)

            # Set master key
            user_bridge.orchestrator.set_master_key(password)

            # Load qube and discard session
            if qube_id not in user_bridge.orchestrator.qubes:
                await user_bridge.orchestrator.load_qube(qube_id)

            qube = user_bridge.orchestrator.qubes[qube_id]
            blocks_discarded = qube.discard_session()

            print(json.dumps({"success": True, "blocks_discarded": blocks_discarded}))

        elif command == "delete-session-block":
            if len(sys.argv) < 5:
                print(json.dumps({"error": "User ID, Qube ID, and block number required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            # SECURITY: Validate qube_id
            qube_id = validate_qube_id(sys.argv[3])
            block_number = int(sys.argv[4])
            password = get_secret("password", argv_index=5)

            # Create bridge with correct user
            user_bridge = GUIBridge(user_id=user_id)

            # Set master key
            user_bridge.orchestrator.set_master_key(password)

            # Load qube and delete session block
            if qube_id not in user_bridge.orchestrator.qubes:
                await user_bridge.orchestrator.load_qube(qube_id)

            qube = user_bridge.orchestrator.qubes[qube_id]

            # Ensure there's an active session
            if not qube.current_session:
                print(json.dumps({"success": False, "error": "No active session"}))
                sys.exit(0)

            # Delete the block (must be negative index for session blocks)
            deleted_block = qube.current_session.delete_block(block_number)

            if deleted_block:
                print(json.dumps({"success": True, "deleted_block_number": block_number}))
            else:
                print(json.dumps({"success": False, "error": f"Block {block_number} not found"}))

        elif command == "get-qube-blocks":
            if len(sys.argv) < 4:
                print(json.dumps({"error": "User ID and Qube ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            # SECURITY: Validate qube_id
            qube_id = validate_qube_id(sys.argv[3])
            password = get_secret("password")

            # Optional pagination parameters (default: 100 blocks, offset 0)
            # Note: After security migration, password is via stdin so indices shifted by -1
            limit = int(sys.argv[4]) if len(sys.argv) > 4 else 100
            offset = int(sys.argv[5]) if len(sys.argv) > 5 else 0

            # Create bridge with correct user
            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.get_qube_blocks(qube_id, password, limit, offset)
            print(json.dumps(result))

        elif command == "recall-last-context":
            if len(sys.argv) < 4:
                print(json.dumps({"error": "User ID and Qube ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            # SECURITY: Validate qube_id
            qube_id = validate_qube_id(sys.argv[3])
            password = get_secret("password")

            # Create bridge with correct user
            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.recall_last_context(qube_id, password)
            print(json.dumps(result))

        elif command == "generate-speech":
            if len(sys.argv) < 5:
                print(json.dumps({"error": "User ID, Qube ID, and text required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            # SECURITY: Validate qube_id
            qube_id = validate_qube_id(sys.argv[3])
            text = sys.argv[4]
            password = get_secret("password", argv_index=5)

            # Create bridge with correct user
            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.generate_speech(qube_id, text, password)
            print(json.dumps(result))

        elif command == "update-qube-config":
            if len(sys.argv) < 6:
                print(json.dumps({"error": "User ID, Qube ID, ai_model, voice_model, and favorite_color required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            # SECURITY: Validate qube_id
            qube_id = validate_qube_id(sys.argv[3])
            ai_model = sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] else None
            voice_model = sys.argv[5] if len(sys.argv) > 5 and sys.argv[5] else None
            favorite_color = sys.argv[6] if len(sys.argv) > 6 and sys.argv[6] else None

            # Parse tts_enabled from 7th argument (convert string "true"/"false" to boolean)
            tts_enabled = None
            if len(sys.argv) > 7 and sys.argv[7]:
                tts_enabled = sys.argv[7].lower() == "true"

            # Parse evaluation_model from 8th argument
            evaluation_model = sys.argv[8] if len(sys.argv) > 8 and sys.argv[8] else None

            # Create bridge with correct user
            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.update_qube_config(qube_id, ai_model, voice_model, favorite_color, tts_enabled, evaluation_model)
            print(json.dumps(result))

        elif command == "reload-ai-keys":
            if len(sys.argv) < 4:
                print(json.dumps({"error": "User ID and Qube ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            # SECURITY: Validate qube_id
            qube_id = validate_qube_id(sys.argv[3])

            # Create bridge with correct user
            user_bridge = GUIBridge(user_id=user_id)

            # Reload AI keys for the qube
            user_bridge.orchestrator.reload_ai_keys(qube_id)

            print(json.dumps({"success": True, "qube_id": qube_id}))

        elif command == "delete-qube":
            if len(sys.argv) < 4:
                print(json.dumps({"error": "User ID and Qube ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            # SECURITY: Validate qube_id
            qube_id = validate_qube_id(sys.argv[3])

            # Create bridge with correct user
            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.delete_qube(qube_id)
            print(json.dumps(result))

        elif command == "reset-qube":
            # DEV ONLY: Reset qube to fresh state while preserving identity
            if len(sys.argv) < 4:
                print(json.dumps({"error": "User ID and Qube ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            # SECURITY: Validate qube_id
            qube_id = validate_qube_id(sys.argv[3])

            # Create bridge with correct user
            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.reset_qube(qube_id)
            print(json.dumps(result))

        elif command == "save-image":
            if len(sys.argv) < 5:
                print(json.dumps({"error": "User ID, Qube ID, and image URL required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            # SECURITY: Validate qube_id
            qube_id = validate_qube_id(sys.argv[3])
            image_url = sys.argv[4]

            # Create bridge with correct user
            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.save_image(qube_id, image_url)
            print(json.dumps(result))

        elif command == "upload-avatar-to-ipfs":
            if len(sys.argv) < 4:
                print(json.dumps({"error": "User ID and Qube ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            # SECURITY: Validate qube_id
            qube_id = validate_qube_id(sys.argv[3])
            password = get_secret("password", argv_index=4)

            # Create bridge with correct user
            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.upload_avatar_to_ipfs(qube_id, password)
            print(json.dumps(result))

        elif command == "analyze-image":
            if len(sys.argv) < 6:
                print(json.dumps({"error": "User ID, Qube ID, image base64 file path, and user message required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            # SECURITY: Validate qube_id
            qube_id = validate_qube_id(sys.argv[3])
            image_base64_file = sys.argv[4]  # Now expects file path instead of data
            user_message = sys.argv[5]
            password = get_secret("password", argv_index=6, required=False)

            # Read base64 data from temporary file
            with open(image_base64_file, 'r') as f:
                image_base64 = f.read()

            # Create bridge with correct user
            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.analyze_image(qube_id, image_base64, user_message, password)
            print(json.dumps(result))

        elif command == "start-multi-qube-conversation":
            if len(sys.argv) < 5:
                print(json.dumps({"error": "User ID, qube IDs (comma-separated), and initial prompt required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            qube_ids_str = sys.argv[3]  # Comma-separated qube IDs
            initial_prompt = sys.argv[4]
            password = get_secret("password", argv_index=5)
            conversation_mode = sys.argv[6] if len(sys.argv) > 6 else "open_discussion"

            # Parse qube IDs
            qube_ids = [qid.strip() for qid in qube_ids_str.split(',')]

            # Create bridge with correct user
            user_bridge = GUIBridge(user_id=user_id)

            # Set master key
            user_bridge.orchestrator.set_master_key(password)

            # Load all qubes
            for qube_id in qube_ids:
                if qube_id not in user_bridge.orchestrator.qubes:
                    await user_bridge.orchestrator.load_qube(qube_id)

            # Start conversation
            result = await user_bridge.orchestrator.start_multi_qube_conversation(
                qube_ids=qube_ids,
                initial_prompt=initial_prompt,
                conversation_mode=conversation_mode
            )

            print(json.dumps(result))

        elif command == "get-next-speaker":
            if len(sys.argv) < 4:
                print(json.dumps({"error": "User ID and conversation ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            conversation_id = sys.argv[3]
            password = get_secret("password", argv_index=4)

            # Create bridge with correct user
            user_bridge = GUIBridge(user_id=user_id)

            # Set master key
            user_bridge.orchestrator.set_master_key(password)

            # Reconstruct conversation if not in active_conversations
            # (Same logic as continue-multi-qube-conversation)
            if conversation_id not in user_bridge.orchestrator.active_conversations:
                from core.multi_qube_conversation import MultiQubeConversation

                # Find and load Qubes with this conversation_id
                qubes_list = await user_bridge.orchestrator.list_qubes()
                participant_qube_ids = []

                for qube_meta in qubes_list:
                    qube_id = qube_meta["qube_id"]

                    # Load the qube
                    if qube_id not in user_bridge.orchestrator.qubes:
                        await user_bridge.orchestrator.load_qube(qube_id)

                    qube = user_bridge.orchestrator.qubes[qube_id]

                    # Check if this qube has blocks from this conversation
                    if qube.current_session:
                        for block in qube.current_session.session_blocks:
                            if hasattr(block, 'content') and isinstance(block.content, dict):
                                if block.content.get('conversation_id') == conversation_id:
                                    if qube_id not in participant_qube_ids:
                                        participant_qube_ids.append(qube_id)
                                    break

                if not participant_qube_ids:
                    print(json.dumps({"error": f"Conversation not found: {conversation_id}"}), file=sys.stderr)
                    sys.exit(1)

                participating_qubes = [user_bridge.orchestrator.qubes[qid] for qid in participant_qube_ids]

                # Reconstruct conversation object (same as continue-multi-qube-conversation)
                conversation = MultiQubeConversation(
                    participating_qubes=participating_qubes,
                    user_id=user_id,
                    conversation_mode="open_discussion"
                )

                conversation.conversation_id = conversation_id

                # Rebuild conversation history and state from session blocks
                conversation.turn_number = 0
                conversation.conversation_history = []

                # Collect all conversation blocks
                conv_blocks = []
                for block in participating_qubes[0].current_session.session_blocks:
                    if hasattr(block, 'content') and isinstance(block.content, dict):
                        if block.content.get('conversation_id') == conversation_id:
                            conv_blocks.append(block)

                # Sort by turn number
                conv_blocks.sort(key=lambda b: b.content.get('turn_number', 0))

                # Rebuild state from blocks
                for block in conv_blocks:
                    turn_num = block.content.get('turn_number', 0)
                    if turn_num > conversation.turn_number:
                        conversation.turn_number = turn_num

                    # Rebuild conversation history
                    if turn_num > 0:
                        conversation.conversation_history.append({
                            "speaker_id": block.content.get('speaker_id'),
                            "speaker_name": block.content.get('speaker_name'),
                            "message": block.content.get('message_body', ''),
                            "turn_number": turn_num,
                            "timestamp": block.timestamp
                        })

                        # Update turn counts
                        speaker_id = block.content.get('speaker_id')
                        if speaker_id and speaker_id in conversation.turn_counts:
                            conversation.turn_counts[speaker_id] += 1

                # Calculate current speaker index for round-robin
                conversation.current_speaker_index = conversation.turn_number % len(participating_qubes)

                # Restore last_speaker_id from the most recent conversation block
                if conv_blocks:
                    last_block = conv_blocks[-1]
                    conversation.last_speaker_id = last_block.content.get('speaker_id')

                # Store in active conversations
                user_bridge.orchestrator.active_conversations[conversation_id] = conversation

            # Get next speaker info (lightweight operation)
            result = await user_bridge.orchestrator.get_next_speaker(
                conversation_id=conversation_id
            )

            print(json.dumps(result))

        elif command == "continue-multi-qube-conversation":
            if len(sys.argv) < 4:
                print(json.dumps({"error": "User ID and conversation ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            conversation_id = sys.argv[3]
            password = get_secret("password", argv_index=4)

            # Create bridge with correct user
            user_bridge = GUIBridge(user_id=user_id)

            # Set master key
            user_bridge.orchestrator.set_master_key(password)

            # Find and load Qubes with this conversation_id in their sessions
            # We need to reconstruct the conversation from the Qubes' session blocks
            qubes_list = await user_bridge.orchestrator.list_qubes()
            participant_qube_ids = []

            for qube_meta in qubes_list:
                qube_id = qube_meta["qube_id"]

                # Load the qube
                if qube_id not in user_bridge.orchestrator.qubes:
                    await user_bridge.orchestrator.load_qube(qube_id)

                qube = user_bridge.orchestrator.qubes[qube_id]

                # Check if this qube has blocks from this conversation
                if qube.current_session:
                    for block in qube.current_session.session_blocks:
                        if hasattr(block, 'content') and isinstance(block.content, dict):
                            if block.content.get('conversation_id') == conversation_id:
                                if qube_id not in participant_qube_ids:
                                    participant_qube_ids.append(qube_id)
                                break

            if not participant_qube_ids:
                print(json.dumps({"error": f"Conversation not found: {conversation_id}"}), file=sys.stderr)
                sys.exit(1)

            # Recreate the conversation if it doesn't exist
            if conversation_id not in user_bridge.orchestrator.active_conversations:
                from core.multi_qube_conversation import MultiQubeConversation

                participating_qubes = [user_bridge.orchestrator.qubes[qid] for qid in participant_qube_ids]

                # Reconstruct conversation object
                conversation = MultiQubeConversation(
                    participating_qubes=participating_qubes,
                    user_id=user_id,
                    conversation_mode="open_discussion"  # Default, actual mode is in blocks
                )

                # Override the conversation_id to match
                conversation.conversation_id = conversation_id

                # Rebuild conversation history and state from session blocks
                conversation.turn_number = 0
                conversation.conversation_history = []

                # Collect all conversation blocks
                conv_blocks = []
                for block in participating_qubes[0].current_session.session_blocks:
                    if hasattr(block, 'content') and isinstance(block.content, dict):
                        if block.content.get('conversation_id') == conversation_id:
                            conv_blocks.append(block)

                # Sort by turn number
                conv_blocks.sort(key=lambda b: b.content.get('turn_number', 0))

                # Rebuild state from blocks
                for block in conv_blocks:
                    turn_num = block.content.get('turn_number', 0)
                    if turn_num > conversation.turn_number:
                        conversation.turn_number = turn_num

                    # Rebuild conversation history
                    if turn_num > 0:  # Skip user's initial message (turn 0)
                        conversation.conversation_history.append({
                            "speaker_id": block.content.get('speaker_id'),
                            "speaker_name": block.content.get('speaker_name'),
                            "message": block.content.get('message_body', ''),
                            "turn_number": turn_num,
                            "timestamp": block.timestamp
                        })

                        # Update turn counts
                        speaker_id = block.content.get('speaker_id')
                        if speaker_id and speaker_id in conversation.turn_counts:
                            conversation.turn_counts[speaker_id] += 1

                # Calculate current speaker index for round-robin
                # The next speaker should be whoever hasn't spoken yet in this round
                # Or if everyone has spoken equally, go to the next in line
                conversation.current_speaker_index = conversation.turn_number % len(participating_qubes)

                # Restore last_speaker_id from the most recent conversation block
                if conv_blocks:
                    last_block = conv_blocks[-1]  # Last block (highest turn number)
                    conversation.last_speaker_id = last_block.content.get('speaker_id')
                    logger.info(f"Restored last_speaker_id: {conversation.last_speaker_id}")

                # Store in active conversations
                user_bridge.orchestrator.active_conversations[conversation_id] = conversation

            # Continue conversation
            result = await user_bridge.orchestrator.continue_multi_qube_conversation(
                conversation_id=conversation_id
            )

            print(json.dumps(result))

        elif command == "inject-multi-qube-user-message":
            if len(sys.argv) < 5:
                print(json.dumps({"error": "User ID, conversation ID, and message required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            conversation_id = sys.argv[3]
            message_arg = sys.argv[4]
            password = get_secret("password", argv_index=5)

            # Check if message is a file reference
            if message_arg.startswith("@file:"):
                # Read message from file
                file_path = message_arg[6:]  # Remove @file: prefix
                with open(file_path, 'r', encoding='utf-8') as f:
                    message = f.read()
            else:
                message = message_arg

            # Create bridge with correct user
            user_bridge = GUIBridge(user_id=user_id)

            # Set master key
            user_bridge.orchestrator.set_master_key(password)

            # Find and load Qubes with this conversation_id in their sessions
            # (Same logic as continue-multi-qube-conversation)
            qubes_list = await user_bridge.orchestrator.list_qubes()
            participant_qube_ids = []

            for qube_meta in qubes_list:
                qube_id = qube_meta["qube_id"]

                # Load the qube
                if qube_id not in user_bridge.orchestrator.qubes:
                    await user_bridge.orchestrator.load_qube(qube_id)

                qube = user_bridge.orchestrator.qubes[qube_id]

                # Check if this qube has blocks from this conversation
                if qube.current_session:
                    for block in qube.current_session.session_blocks:
                        if hasattr(block, 'content') and isinstance(block.content, dict):
                            if block.content.get('conversation_id') == conversation_id:
                                if qube_id not in participant_qube_ids:
                                    participant_qube_ids.append(qube_id)
                                break

            if not participant_qube_ids:
                print(json.dumps({"error": f"Conversation not found: {conversation_id}"}), file=sys.stderr)
                sys.exit(1)

            # Recreate the conversation if it doesn't exist
            if conversation_id not in user_bridge.orchestrator.active_conversations:
                from core.multi_qube_conversation import MultiQubeConversation

                participating_qubes = [user_bridge.orchestrator.qubes[qid] for qid in participant_qube_ids]

                # Reconstruct conversation object
                conversation = MultiQubeConversation(
                    participating_qubes=participating_qubes,
                    user_id=user_id,
                    conversation_mode="open_discussion"  # Default, actual mode is in blocks
                )

                # Override the conversation_id to match
                conversation.conversation_id = conversation_id

                # Rebuild conversation history and state from session blocks
                conversation.turn_number = 0
                conversation.conversation_history = []

                # Collect all conversation blocks
                conv_blocks = []
                for block in participating_qubes[0].current_session.session_blocks:
                    if hasattr(block, 'content') and isinstance(block.content, dict):
                        if block.content.get('conversation_id') == conversation_id:
                            conv_blocks.append(block)

                # Sort by turn number
                conv_blocks.sort(key=lambda b: b.content.get('turn_number', 0))

                # Rebuild state from blocks
                for block in conv_blocks:
                    turn_num = block.content.get('turn_number', 0)
                    if turn_num > conversation.turn_number:
                        conversation.turn_number = turn_num

                    # Rebuild conversation history
                    if turn_num > 0:  # Skip user's initial message (turn 0)
                        conversation.conversation_history.append({
                            "speaker_id": block.content.get('speaker_id'),
                            "speaker_name": block.content.get('speaker_name'),
                            "message": block.content.get('message_body', ''),
                            "turn_number": turn_num,
                            "timestamp": block.timestamp
                        })

                        # Update turn counts
                        speaker_id = block.content.get('speaker_id')
                        if speaker_id and speaker_id in conversation.turn_counts:
                            conversation.turn_counts[speaker_id] += 1

                # Calculate current speaker index for round-robin
                conversation.current_speaker_index = conversation.turn_number % len(participating_qubes)

                # Restore last_speaker_id from the most recent conversation block
                if conv_blocks:
                    last_block = conv_blocks[-1]  # Last block (highest turn number)
                    conversation.last_speaker_id = last_block.content.get('speaker_id')
                    logger.info(f"Restored last_speaker_id: {conversation.last_speaker_id}")

                # Store in active conversations
                user_bridge.orchestrator.active_conversations[conversation_id] = conversation

            # Inject user message
            result = await user_bridge.orchestrator.inject_user_message_to_conversation(
                conversation_id=conversation_id,
                user_message=message
            )

            print(json.dumps(result))

        elif command == "lock-in-multi-qube-response":
            if len(sys.argv) < 5:
                print(json.dumps({"error": "User ID, conversation ID, and timestamp required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            conversation_id = sys.argv[3]
            timestamp = int(sys.argv[4])
            password = get_secret("password", argv_index=5)

            # Create bridge with correct user
            user_bridge = GUIBridge(user_id=user_id)

            # Set master key
            user_bridge.orchestrator.set_master_key(password)

            # Reconstruct conversation if not in active_conversations
            # (Same logic as continue-multi-qube-conversation)
            if conversation_id not in user_bridge.orchestrator.active_conversations:
                from core.multi_qube_conversation import MultiQubeConversation

                qubes_list = await user_bridge.orchestrator.list_qubes()
                participant_qube_ids = []

                for qube_meta in qubes_list:
                    qube_id = qube_meta["qube_id"]

                    # Load the qube
                    if qube_id not in user_bridge.orchestrator.qubes:
                        await user_bridge.orchestrator.load_qube(qube_id)

                    qube = user_bridge.orchestrator.qubes[qube_id]

                    # Check if this qube has blocks from this conversation
                    if qube.current_session:
                        for block in qube.current_session.session_blocks:
                            if hasattr(block, 'content') and isinstance(block.content, dict):
                                if block.content.get('conversation_id') == conversation_id:
                                    if qube_id not in participant_qube_ids:
                                        participant_qube_ids.append(qube_id)
                                    break

                if not participant_qube_ids:
                    print(json.dumps({"error": f"Conversation not found: {conversation_id}"}), file=sys.stderr)
                    sys.exit(1)

                participating_qubes = [user_bridge.orchestrator.qubes[qid] for qid in participant_qube_ids]

                # Reconstruct conversation object
                conversation = MultiQubeConversation(
                    participating_qubes=participating_qubes,
                    user_id=user_id,
                    conversation_mode="open_discussion"
                )

                # Override the conversation_id to match
                conversation.conversation_id = conversation_id

                # Store in active conversations
                user_bridge.orchestrator.active_conversations[conversation_id] = conversation

            conversation = user_bridge.orchestrator.active_conversations[conversation_id]

            # Lock in the response
            conversation.lock_in_response(timestamp)

            print(json.dumps({"success": True, "timestamp": timestamp}))

        elif command == "end-multi-qube-conversation":
            if len(sys.argv) < 5:
                print(json.dumps({"error": "User ID, conversation ID, and anchor flag required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            conversation_id = sys.argv[3]
            anchor = sys.argv[4].lower() == "true" if len(sys.argv) > 4 else True
            password = get_secret("password", argv_index=5)

            # Create bridge with correct user
            user_bridge = GUIBridge(user_id=user_id)

            # Set master key
            user_bridge.orchestrator.set_master_key(password)

            # End conversation
            result = await user_bridge.orchestrator.end_multi_qube_conversation(
                conversation_id=conversation_id,
                anchor=anchor
            )

            print(json.dumps(result))

        elif command == "get-configured-api-keys":
            if len(sys.argv) < 3:
                print(json.dumps({"error": "User ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            password = get_secret("password", argv_index=3)

            # Create bridge with correct user
            user_bridge = GUIBridge(user_id=user_id)

            # Set master key with password to decrypt keys
            user_bridge.orchestrator.set_master_key(password)

            try:
                # Get list of configured providers
                providers = user_bridge.orchestrator.list_configured_providers()
                print(json.dumps({"providers": providers}))
            except Exception as e:
                logger.error(f"Failed to get configured API keys: {e}", exc_info=True)
                # Return empty list if unable to decrypt (wrong password, no keys, etc.)
                print(json.dumps({"providers": []}))

        elif command == "save-api-key":
            if len(sys.argv) < 4:
                print(json.dumps({"error": "User ID and provider required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            provider = sys.argv[3]
            api_key = get_secret("api_key", argv_index=4)
            password = get_secret("password", argv_index=5)

            # Create bridge with correct user
            user_bridge = GUIBridge(user_id=user_id)

            # Set master key with password
            user_bridge.orchestrator.set_master_key(password)

            try:
                user_bridge.orchestrator.update_api_key(provider, api_key)
                print(json.dumps({"success": True}))
            except Exception as e:
                logger.error(f"Failed to save API key: {e}", exc_info=True)
                print(json.dumps({"success": False, "error": str(e)}))

        elif command == "validate-api-key":
            if len(sys.argv) < 4:
                print(json.dumps({"error": "User ID and provider required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            provider = sys.argv[3]
            api_key = get_secret("api_key", argv_index=4)
            password = get_secret("password", argv_index=5, required=False)

            # Create bridge with correct user
            user_bridge = GUIBridge(user_id=user_id)

            # If api_key is the placeholder, load the saved key
            if api_key == "__SAVED__":
                if not password:
                    print(json.dumps({
                        "valid": False,
                        "message": "Password required to test saved key",
                        "details": None
                    }))
                    sys.exit(0)

                user_bridge.orchestrator.set_master_key(password)

                try:
                    # Load saved keys
                    stored_keys = user_bridge.orchestrator.get_api_keys()
                    api_key = getattr(stored_keys, provider, None)

                    if not api_key:
                        print(json.dumps({
                            "valid": False,
                            "message": f"No saved key found for {provider}",
                            "details": None
                        }))
                        sys.exit(0)
                except Exception as e:
                    logger.error(f"Failed to load saved key: {e}", exc_info=True)
                    print(json.dumps({
                        "valid": False,
                        "message": f"Failed to load saved key: {str(e)}",
                        "details": None
                    }))
                    sys.exit(0)

            # Validate the API key (doesn't require master password - just makes API call)
            try:
                result = await user_bridge.orchestrator.validate_api_key(provider, api_key)
                print(json.dumps(result))
            except Exception as e:
                logger.error(f"Failed to validate API key: {e}", exc_info=True)
                print(json.dumps({
                    "valid": False,
                    "message": f"Validation error: {str(e)}",
                    "details": None
                }))

        elif command == "delete-api-key":
            if len(sys.argv) < 4:
                print(json.dumps({"error": "User ID and provider required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            provider = sys.argv[3]
            password = get_secret("password", argv_index=4)

            # Create bridge with correct user
            user_bridge = GUIBridge(user_id=user_id)

            # Set master key with password
            user_bridge.orchestrator.set_master_key(password)

            try:
                user_bridge.orchestrator.delete_api_key(provider)
                print(json.dumps({"success": True}))
            except Exception as e:
                logger.error(f"Failed to delete API key: {e}", exc_info=True)
                print(json.dumps({"success": False, "error": str(e)}))

        elif command == "get-block-preferences":
            if len(sys.argv) < 3:
                print(json.dumps({"error": "User ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]

            # Create bridge with correct user
            user_bridge = GUIBridge(user_id=user_id)

            try:
                prefs = user_bridge.orchestrator.get_block_preferences()
                print(json.dumps({
                    "individual_auto_anchor": prefs.individual_auto_anchor,
                    "individual_anchor_threshold": prefs.individual_anchor_threshold,
                    "group_auto_anchor": prefs.group_auto_anchor,
                    "group_anchor_threshold": prefs.group_anchor_threshold
                }))
            except Exception as e:
                logger.error(f"Failed to get block preferences: {e}", exc_info=True)
                print(json.dumps({"error": str(e)}), file=sys.stderr)
                sys.exit(1)

        elif command == "update-block-preferences":
            if len(sys.argv) < 3:
                print(json.dumps({"error": "User ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]

            # Parse optional arguments
            individual_auto_anchor = None
            individual_anchor_threshold = None
            group_auto_anchor = None
            group_anchor_threshold = None

            i = 3
            while i < len(sys.argv):
                if sys.argv[i] == "--individual-auto-anchor":
                    individual_auto_anchor = sys.argv[i + 1].lower() == "true"
                    i += 2
                elif sys.argv[i] == "--individual-anchor-threshold":
                    individual_anchor_threshold = int(sys.argv[i + 1])
                    i += 2
                elif sys.argv[i] == "--group-auto-anchor":
                    group_auto_anchor = sys.argv[i + 1].lower() == "true"
                    i += 2
                elif sys.argv[i] == "--group-anchor-threshold":
                    group_anchor_threshold = int(sys.argv[i + 1])
                    i += 2
                else:
                    i += 1

            # Create bridge with correct user
            user_bridge = GUIBridge(user_id=user_id)

            try:
                prefs = user_bridge.orchestrator.update_block_preferences(
                    individual_auto_anchor=individual_auto_anchor,
                    individual_anchor_threshold=individual_anchor_threshold,
                    group_auto_anchor=group_auto_anchor,
                    group_anchor_threshold=group_anchor_threshold
                )
                print(json.dumps({
                    "individual_auto_anchor": prefs.individual_auto_anchor,
                    "individual_anchor_threshold": prefs.individual_anchor_threshold,
                    "group_auto_anchor": prefs.group_auto_anchor,
                    "group_anchor_threshold": prefs.group_anchor_threshold
                }))
            except Exception as e:
                logger.error(f"Failed to update block preferences: {e}", exc_info=True)
                print(json.dumps({"error": str(e)}), file=sys.stderr)
                sys.exit(1)

        elif command == "get-relationship-difficulty":
            if len(sys.argv) < 3:
                print(json.dumps({"error": "User ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]

            try:
                from config.global_settings import get_global_settings
                global_settings = get_global_settings()
                difficulty = global_settings.get_difficulty()
                preset = global_settings.get_preset(difficulty)

                print(json.dumps({
                    "difficulty": difficulty,
                    "description": preset["description"]
                }))
            except Exception as e:
                logger.error(f"Failed to get relationship difficulty: {e}", exc_info=True)
                print(json.dumps({"error": str(e)}), file=sys.stderr)
                sys.exit(1)

        elif command == "set-relationship-difficulty":
            if len(sys.argv) < 4:
                print(json.dumps({"error": "User ID and difficulty required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            difficulty = sys.argv[3]

            try:
                from config.global_settings import get_global_settings
                global_settings = get_global_settings()
                global_settings.set_difficulty(difficulty)
                preset = global_settings.get_preset(difficulty)

                print(json.dumps({
                    "difficulty": difficulty,
                    "description": preset["description"]
                }))
            except Exception as e:
                logger.error(f"Failed to set relationship difficulty: {e}", exc_info=True)
                print(json.dumps({"error": str(e)}), file=sys.stderr)
                sys.exit(1)

        elif command == "get-difficulty-presets":
            try:
                from config.global_settings import GlobalSettings

                # Format presets for JSON response
                presets_response = {}
                for difficulty, preset in GlobalSettings.PRESETS.items():
                    presets_response[difficulty] = {
                        "name": preset["name"],
                        "description": preset["description"],
                        "min_interactions": preset["min_interactions"]
                    }

                print(json.dumps(presets_response))
            except Exception as e:
                logger.error(f"Failed to get difficulty presets: {e}", exc_info=True)
                print(json.dumps({"error": str(e)}), file=sys.stderr)
                sys.exit(1)

        elif command == "get-qube-relationships":
            if len(sys.argv) < 4:
                print(json.dumps({"error": "User ID and Qube ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            # SECURITY: Validate qube_id
            qube_id = validate_qube_id(sys.argv[3])
            password = get_secret("password", argv_index=4)

            # Create bridge with correct user
            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.get_qube_relationships(qube_id, password)
            print(json.dumps(result))

        elif command == "get-relationship-timeline":
            if len(sys.argv) < 5:
                print(json.dumps({"error": "User ID, Qube ID, and Entity ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            # SECURITY: Validate qube_id
            qube_id = validate_qube_id(sys.argv[3])
            # entity_id can be either a qube_id (8 hex) or human username (alphanumeric)
            entity_id = validate_user_id(sys.argv[4])  # Works for both qube IDs and human usernames
            password = get_secret("password", argv_index=5, required=False)

            # Create bridge with correct user
            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.get_relationship_timeline(qube_id, entity_id, password)
            print(json.dumps(result))

        elif command == "reset-qube-relationships":
            if len(sys.argv) < 4:
                print(json.dumps({"error": "User ID and Qube ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            # SECURITY: Validate qube_id
            qube_id = validate_qube_id(sys.argv[3])
            password = get_secret("password", argv_index=4)

            # Create bridge with correct user
            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.reset_qube_relationships(qube_id, password)
            print(json.dumps(result))

        elif command == "get-google-tts-path":
            if len(sys.argv) < 3:
                print(json.dumps({"error": "User ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]

            try:
                from config.user_preferences import UserPreferencesManager

                # Get user data directory
                data_dir = Path("data") / "users" / user_id
                prefs_manager = UserPreferencesManager(data_dir)

                # Get Google TTS path from preferences
                path = prefs_manager.get_google_tts_path()

                print(json.dumps({"path": path}))
            except Exception as e:
                logger.error(f"Failed to get Google TTS path: {e}", exc_info=True)
                print(json.dumps({"error": str(e)}), file=sys.stderr)
                sys.exit(1)

        elif command == "set-google-tts-path":
            if len(sys.argv) < 4:
                print(json.dumps({"error": "User ID and path required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            path = sys.argv[3]

            try:
                from config.user_preferences import UserPreferencesManager

                # Get user data directory
                data_dir = Path("data") / "users" / user_id
                prefs_manager = UserPreferencesManager(data_dir)

                # Set Google TTS path (empty string = clear the path)
                if path.strip() == "" or path.lower() == "none":
                    prefs_manager.update_google_tts_path(None)
                    print(json.dumps({"success": True, "path": None}))
                else:
                    prefs_manager.update_google_tts_path(path)
                    print(json.dumps({"success": True, "path": path}))
            except Exception as e:
                logger.error(f"Failed to set Google TTS path: {e}", exc_info=True)
                print(json.dumps({"success": False, "error": str(e)}), file=sys.stderr)
                sys.exit(1)

        elif command == "get-decision-config":
            if len(sys.argv) < 3:
                print(json.dumps({"error": "User ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]

            try:
                from config.user_preferences import UserPreferencesManager
                from dataclasses import asdict

                # Get user data directory
                data_dir = Path("data") / "users" / user_id
                prefs_manager = UserPreferencesManager(data_dir)

                # Get decision config from preferences
                config = prefs_manager.get_decision_config()

                print(json.dumps({
                    "success": True,
                    "config": asdict(config)
                }))
            except Exception as e:
                logger.error(f"Failed to get decision config: {e}", exc_info=True)
                print(json.dumps({"success": False, "error": str(e)}), file=sys.stderr)
                sys.exit(1)

        elif command == "update-decision-config":
            if len(sys.argv) < 4:
                print(json.dumps({"error": "User ID and config JSON required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            config_json = sys.argv[3]

            try:
                from config.user_preferences import UserPreferencesManager

                # Get user data directory
                data_dir = Path("data") / "users" / user_id
                prefs_manager = UserPreferencesManager(data_dir)

                # Parse config data
                config_data = json.loads(config_json)

                # Update decision config
                prefs_manager.update_decision_config(**config_data)

                print(json.dumps({
                    "success": True,
                    "message": "Decision config updated"
                }))
            except Exception as e:
                logger.error(f"Failed to update decision config: {e}", exc_info=True)
                print(json.dumps({"success": False, "error": str(e)}), file=sys.stderr)
                sys.exit(1)

        # =====================================================================
        # Memory Recall Config Commands
        # =====================================================================

        elif command == "get-memory-config":
            if len(sys.argv) < 3:
                print(json.dumps({"error": "User ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]

            try:
                from config.user_preferences import UserPreferencesManager
                from dataclasses import asdict

                # Get user data directory
                data_dir = Path("data") / "users" / user_id
                prefs_manager = UserPreferencesManager(data_dir)

                # Get memory config from preferences
                config = prefs_manager.get_memory_config()

                print(json.dumps({
                    "success": True,
                    "config": asdict(config)
                }))
            except Exception as e:
                logger.error(f"Failed to get memory config: {e}", exc_info=True)
                print(json.dumps({"success": False, "error": str(e)}), file=sys.stderr)
                sys.exit(1)

        elif command == "update-memory-config":
            if len(sys.argv) < 4:
                print(json.dumps({"error": "User ID and config JSON required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            config_json = sys.argv[3]

            try:
                from config.user_preferences import UserPreferencesManager

                # Get user data directory
                data_dir = Path("data") / "users" / user_id
                prefs_manager = UserPreferencesManager(data_dir)

                # Parse config data
                config_data = json.loads(config_json)

                # Update memory config
                prefs_manager.update_memory_config(**config_data)

                print(json.dumps({
                    "success": True,
                    "message": "Memory config updated"
                }))
            except Exception as e:
                logger.error(f"Failed to update memory config: {e}", exc_info=True)
                print(json.dumps({"success": False, "error": str(e)}), file=sys.stderr)
                sys.exit(1)

        # =====================================================================
        # Onboarding Tutorial Commands
        # =====================================================================

        elif command == "get-onboarding-preferences":
            if len(sys.argv) < 3:
                print(json.dumps({"error": "User ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]

            try:
                from config.user_preferences import UserPreferencesManager
                from dataclasses import asdict

                data_dir = Path("data") / "users" / user_id
                prefs_manager = UserPreferencesManager(data_dir)

                onboarding = prefs_manager.get_onboarding_preferences()

                print(json.dumps({
                    "success": True,
                    "onboarding": asdict(onboarding)
                }))
            except Exception as e:
                logger.error(f"Failed to get onboarding preferences: {e}", exc_info=True)
                print(json.dumps({"success": False, "error": str(e)}), file=sys.stderr)
                sys.exit(1)

        elif command == "mark-tutorial-seen":
            if len(sys.argv) < 4:
                print(json.dumps({"error": "User ID and tab name required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            tab_name = sys.argv[3]

            try:
                from config.user_preferences import UserPreferencesManager

                data_dir = Path("data") / "users" / user_id
                prefs_manager = UserPreferencesManager(data_dir)

                prefs_manager.mark_tutorial_seen(tab_name)

                print(json.dumps({
                    "success": True,
                    "message": f"Tutorial for {tab_name} marked as seen"
                }))
            except Exception as e:
                logger.error(f"Failed to mark tutorial seen: {e}", exc_info=True)
                print(json.dumps({"success": False, "error": str(e)}), file=sys.stderr)
                sys.exit(1)

        elif command == "reset-tutorial":
            if len(sys.argv) < 4:
                print(json.dumps({"error": "User ID and tab name required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            tab_name = sys.argv[3]

            try:
                from config.user_preferences import UserPreferencesManager

                data_dir = Path("data") / "users" / user_id
                prefs_manager = UserPreferencesManager(data_dir)

                prefs_manager.reset_tutorial(tab_name)

                print(json.dumps({
                    "success": True,
                    "message": f"Tutorial for {tab_name} reset"
                }))
            except Exception as e:
                logger.error(f"Failed to reset tutorial: {e}", exc_info=True)
                print(json.dumps({"success": False, "error": str(e)}), file=sys.stderr)
                sys.exit(1)

        elif command == "reset-all-tutorials":
            if len(sys.argv) < 3:
                print(json.dumps({"error": "User ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]

            try:
                from config.user_preferences import UserPreferencesManager

                data_dir = Path("data") / "users" / user_id
                prefs_manager = UserPreferencesManager(data_dir)

                prefs_manager.reset_all_tutorials()

                print(json.dumps({
                    "success": True,
                    "message": "All tutorials reset"
                }))
            except Exception as e:
                logger.error(f"Failed to reset all tutorials: {e}", exc_info=True)
                print(json.dumps({"success": False, "error": str(e)}), file=sys.stderr)
                sys.exit(1)

        elif command == "update-show-tutorials":
            if len(sys.argv) < 4:
                print(json.dumps({"error": "User ID and show value required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            show = sys.argv[3].lower() == "true"

            try:
                from config.user_preferences import UserPreferencesManager

                data_dir = Path("data") / "users" / user_id
                prefs_manager = UserPreferencesManager(data_dir)

                prefs_manager.update_show_tutorials(show)

                print(json.dumps({
                    "success": True,
                    "message": f"Show tutorials set to {show}"
                }))
            except Exception as e:
                logger.error(f"Failed to update show tutorials: {e}", exc_info=True)
                print(json.dumps({"success": False, "error": str(e)}), file=sys.stderr)
                sys.exit(1)


        elif command == "get-qube-skills":
            if len(sys.argv) < 4:
                print(json.dumps({"success": False, "error": "User ID and Qube ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            qube_id = sys.argv[3]

            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.get_qube_skills(user_id, qube_id)
            print(json.dumps(result))

        elif command == "save-qube-skills":
            if len(sys.argv) < 5:
                print(json.dumps({"success": False, "error": "User ID, Qube ID, and skills JSON required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            qube_id = sys.argv[3]
            skills_json = sys.argv[4]

            try:
                skills_data = json.loads(skills_json)
            except json.JSONDecodeError as e:
                print(json.dumps({"success": False, "error": f"Invalid JSON: {str(e)}"}), file=sys.stderr)
                sys.exit(1)

            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.save_qube_skills(user_id, qube_id, skills_data)
            print(json.dumps(result))

        elif command == "add-skill-xp":
            if len(sys.argv) < 6:
                print(json.dumps({"success": False, "error": "User ID, Qube ID, skill ID, and XP amount required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            qube_id = sys.argv[3]
            skill_id = sys.argv[4]

            try:
                xp_amount = int(sys.argv[5])
            except ValueError:
                print(json.dumps({"success": False, "error": "XP amount must be an integer"}), file=sys.stderr)
                sys.exit(1)

            evidence_block_id = sys.argv[6] if len(sys.argv) > 6 else None

            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.add_skill_xp(user_id, qube_id, skill_id, xp_amount, evidence_block_id)
            print(json.dumps(result))

        elif command == "unlock-skill":
            if len(sys.argv) < 5:
                print(json.dumps({"success": False, "error": "User ID, Qube ID, and skill ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            qube_id = sys.argv[3]
            skill_id = sys.argv[4]

            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.unlock_skill(user_id, qube_id, skill_id)
            print(json.dumps(result))

        # =====================================================================
        # Owner Info Commands
        # =====================================================================

        elif command == "get-owner-info":
            if len(sys.argv) < 5:
                print(json.dumps({"success": False, "error": "User ID, Qube ID, and password required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            qube_id = sys.argv[3]
            password = sys.argv[4]

            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.get_owner_info(qube_id, password)
            print(json.dumps(result))

        elif command == "set-owner-info-field":
            if len(sys.argv) < 8:
                print(json.dumps({"success": False, "error": "User ID, Qube ID, password, category, key, and value required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            qube_id = sys.argv[3]
            password = sys.argv[4]
            category = sys.argv[5]
            key = sys.argv[6]
            value = sys.argv[7]

            # Optional parameters
            sensitivity = sys.argv[8] if len(sys.argv) > 8 else None
            source = sys.argv[9] if len(sys.argv) > 9 else "explicit"
            confidence = int(sys.argv[10]) if len(sys.argv) > 10 else 100
            block_id = sys.argv[11] if len(sys.argv) > 11 else None

            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.set_owner_info_field(
                qube_id, password, category, key, value,
                sensitivity, source, confidence, block_id
            )
            print(json.dumps(result))

        elif command == "delete-owner-info-field":
            if len(sys.argv) < 7:
                print(json.dumps({"success": False, "error": "User ID, Qube ID, password, category, and key required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            qube_id = sys.argv[3]
            password = sys.argv[4]
            category = sys.argv[5]
            key = sys.argv[6]

            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.delete_owner_info_field(qube_id, password, category, key)
            print(json.dumps(result))

        elif command == "update-owner-info-sensitivity":
            if len(sys.argv) < 8:
                print(json.dumps({"success": False, "error": "User ID, Qube ID, password, category, key, and sensitivity required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            qube_id = sys.argv[3]
            password = sys.argv[4]
            category = sys.argv[5]
            key = sys.argv[6]
            sensitivity = sys.argv[7]

            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.update_owner_info_sensitivity(qube_id, password, category, key, sensitivity)
            print(json.dumps(result))

        # Clearance Request Commands
        elif command == "get-pending-clearance-requests":
            if len(sys.argv) < 5:
                print(json.dumps({"success": False, "error": "User ID, Qube ID, and password required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            qube_id = sys.argv[3]
            password = sys.argv[4]

            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.get_pending_clearance_requests(qube_id, password)
            print(json.dumps(result))

        elif command == "approve-clearance-request":
            if len(sys.argv) < 6:
                print(json.dumps({"success": False, "error": "User ID, Qube ID, request ID, and password required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            qube_id = sys.argv[3]
            request_id = sys.argv[4]
            password = sys.argv[5]
            expires_days = int(sys.argv[6]) if len(sys.argv) > 6 else None

            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.approve_clearance_request(qube_id, request_id, password, expires_days)
            print(json.dumps(result))

        elif command == "deny-clearance-request":
            if len(sys.argv) < 6:
                print(json.dumps({"success": False, "error": "User ID, Qube ID, request ID, and password required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            qube_id = sys.argv[3]
            request_id = sys.argv[4]
            password = sys.argv[5]
            reason = sys.argv[6] if len(sys.argv) > 6 else None

            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.deny_clearance_request(qube_id, request_id, password, reason)
            print(json.dumps(result))

        elif command == "get-clearance-audit-log":
            if len(sys.argv) < 5:
                print(json.dumps({"success": False, "error": "User ID, Qube ID, and password required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            qube_id = sys.argv[3]
            password = sys.argv[4]
            limit = int(sys.argv[5]) if len(sys.argv) > 5 else 100
            entity_filter = sys.argv[6] if len(sys.argv) > 6 else None

            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.get_clearance_audit_log(qube_id, password, limit, entity_filter)
            print(json.dumps(result))

        elif command == "get-visualizer-settings":
            if len(sys.argv) < 4:
                print(json.dumps({"success": False, "error": "User ID and Qube ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            qube_id = sys.argv[3]

            try:
                # Find qube directory
                data_dir = Path("data") / "users" / user_id / "qubes"
                qube_dir = None
                for dir_path in data_dir.iterdir():
                    if dir_path.is_dir() and qube_id in dir_path.name:
                        qube_dir = dir_path
                        break

                if not qube_dir:
                    print(json.dumps({"success": False, "error": f"Qube {qube_id} not found"}), file=sys.stderr)
                    sys.exit(1)

                settings_file = qube_dir / "visualizer_settings.json"

                # Load settings or return defaults
                if settings_file.exists():
                    with open(settings_file, 'r') as f:
                        settings = json.load(f)
                else:
                    settings = {
                        "enabled": False,
                        "waveform_style": 1,
                        "color_theme": "qube-color",
                        "gradient_style": "gradient-dark",
                        "sensitivity": 50,
                        "animation_smoothness": "medium",
                        "audio_offset_ms": 0,
                        "frequency_range": 20,
                        "output_monitor": 0
                    }

                print(json.dumps(settings))

            except Exception as e:
                logger.error(f"Failed to get visualizer settings: {e}", exc_info=True)
                print(json.dumps({"success": False, "error": str(e)}), file=sys.stderr)
                sys.exit(1)

        elif command == "save-visualizer-settings":
            if len(sys.argv) < 5:
                print(json.dumps({"success": False, "error": "User ID, Qube ID, and settings JSON required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            qube_id = sys.argv[3]
            settings_json = sys.argv[4]

            try:
                # Find qube directory
                data_dir = Path("data") / "users" / user_id / "qubes"
                qube_dir = None
                for dir_path in data_dir.iterdir():
                    if dir_path.is_dir() and qube_id in dir_path.name:
                        qube_dir = dir_path
                        break

                if not qube_dir:
                    print(json.dumps({"success": False, "error": f"Qube {qube_id} not found"}), file=sys.stderr)
                    sys.exit(1)

                settings_file = qube_dir / "visualizer_settings.json"
                settings_data = json.loads(settings_json)

                # Save settings
                with open(settings_file, 'w') as f:
                    json.dump(settings_data, f, indent=2)

                print(json.dumps({"success": True, "message": "Visualizer settings saved"}))

            except Exception as e:
                logger.error(f"Failed to save visualizer settings: {e}", exc_info=True)
                print(json.dumps({"success": False, "error": str(e)}), file=sys.stderr)
                sys.exit(1)

        elif command == "get-trust-personality":
            if len(sys.argv) < 4:
                print(json.dumps({"success": False, "error": "User ID and Qube ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            qube_id = sys.argv[3]

            try:
                from utils.file_lock import FileLock

                # Find qube directory
                data_dir = Path("data") / "users" / user_id / "qubes"
                qube_dir = None
                for dir_path in data_dir.iterdir():
                    if dir_path.is_dir() and qube_id in dir_path.name:
                        qube_dir = dir_path
                        break

                if not qube_dir:
                    print(json.dumps({"success": False, "error": f"Qube {qube_id} not found"}), file=sys.stderr)
                    sys.exit(1)

                chain_state_file = qube_dir / "chain_state.json"
                lock_file = qube_dir / ".chain_state.lock"

                # Load chain_state with file locking
                lock = FileLock(lock_file, timeout=5.0)
                with lock:
                    if chain_state_file.exists():
                        with open(chain_state_file, 'r') as f:
                            chain_state = json.load(f)
                        trust_profile = chain_state.get("trust_profile", "balanced")
                    else:
                        trust_profile = "balanced"

                print(json.dumps({"trust_profile": trust_profile}))

            except Exception as e:
                logger.error(f"Failed to get trust personality: {e}", exc_info=True)
                print(json.dumps({"success": False, "error": str(e)}), file=sys.stderr)
                sys.exit(1)

        elif command == "update-trust-personality":
            if len(sys.argv) < 5:
                print(json.dumps({"success": False, "error": "User ID, Qube ID, and trust profile required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            qube_id = sys.argv[3]
            trust_profile = sys.argv[4]

            try:
                from utils.file_lock import FileLock

                # Validate trust_profile
                valid_profiles = ["cautious", "balanced", "social", "analytical"]
                if trust_profile not in valid_profiles:
                    print(json.dumps({"success": False, "error": f"Invalid trust profile. Must be one of: {', '.join(valid_profiles)}"}), file=sys.stderr)
                    sys.exit(1)

                # Find qube directory
                data_dir = Path("data") / "users" / user_id / "qubes"
                qube_dir = None
                for dir_path in data_dir.iterdir():
                    if dir_path.is_dir() and qube_id in dir_path.name:
                        qube_dir = dir_path
                        break

                if not qube_dir:
                    print(json.dumps({"success": False, "error": f"Qube {qube_id} not found"}), file=sys.stderr)
                    sys.exit(1)

                chain_state_file = qube_dir / "chain_state.json"
                lock_file = qube_dir / ".chain_state.lock"

                # Update chain_state with file locking
                lock = FileLock(lock_file, timeout=5.0)
                with lock:
                    # Load existing chain_state
                    if chain_state_file.exists():
                        with open(chain_state_file, 'r') as f:
                            chain_state = json.load(f)
                    else:
                        # Initialize if doesn't exist
                        chain_state = {"qube_id": qube_id}

                    # Update trust_profile
                    chain_state["trust_profile"] = trust_profile

                    # Save atomically
                    temp_file = chain_state_file.with_suffix('.json.tmp')
                    with open(temp_file, 'w') as f:
                        json.dump(chain_state, f, indent=2)
                    temp_file.replace(chain_state_file)

                print(json.dumps({"success": True, "trust_profile": trust_profile}))

            except Exception as e:
                logger.error(f"Failed to update trust personality: {e}", exc_info=True)
                print(json.dumps({"success": False, "error": str(e)}), file=sys.stderr)
                sys.exit(1)

        elif command == "prepare-qube-for-minting":
            if len(sys.argv) < 3:
                print(json.dumps({"error": "User ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]

            # Parse arguments
            import argparse
            parser = argparse.ArgumentParser()
            parser.add_argument("command")  # Already consumed
            parser.add_argument("user_id")  # Already consumed
            parser.add_argument("--name", required=True)
            parser.add_argument("--genesis-prompt", required=True)
            parser.add_argument("--ai-provider", required=True)
            parser.add_argument("--ai-model", required=True)
            parser.add_argument("--voice-model", default="openai:alloy")
            parser.add_argument("--owner-pubkey", required=True)  # NFT address derived from this
            parser.add_argument("--password", default="")  # Password comes from stdin
            parser.add_argument("--encrypt-genesis", default="false")
            parser.add_argument("--favorite-color", default="#00ff88")
            parser.add_argument("--avatar-file", default=None)
            parser.add_argument("--generate-avatar", action="store_true", default=False)
            parser.add_argument("--avatar-style", default="cyberpunk")

            args = parser.parse_args()

            # Use stdin secret if available, fall back to argparse
            password = get_secret("password", required=False) or args.password

            # Create bridge with correct user
            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.prepare_qube_for_minting(
                name=args.name,
                genesis_prompt=args.genesis_prompt,
                ai_provider=args.ai_provider,
                ai_model=args.ai_model,
                voice_model=args.voice_model,
                owner_pubkey=args.owner_pubkey,  # NFT address derived from this
                password=password,
                encrypt_genesis=(args.encrypt_genesis.lower() == "true"),
                favorite_color=args.favorite_color,
                avatar_file=args.avatar_file,
                generate_avatar=args.generate_avatar,
                avatar_style=args.avatar_style,
            )
            print(json.dumps(result))

        elif command == "check-minting-status":
            if len(sys.argv) < 4:
                print(json.dumps({"error": "User ID and registration ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            registration_id = sys.argv[3]
            password = get_secret("password", argv_index=4)

            # Create bridge with correct user
            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.check_minting_status(registration_id, password)
            print(json.dumps(result))

        elif command == "submit-payment-txid":
            if len(sys.argv) < 5:
                print(json.dumps({"error": "User ID, registration ID, and txid required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            registration_id = sys.argv[3]
            txid = sys.argv[4]

            # Create bridge with correct user
            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.submit_payment_txid(registration_id, txid)
            print(json.dumps(result))

        elif command == "cancel-pending-minting":
            if len(sys.argv) < 4:
                print(json.dumps({"error": "User ID and registration ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            registration_id = sys.argv[3]

            # Create bridge with correct user
            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.cancel_pending_minting(registration_id)
            print(json.dumps(result))

        elif command == "list-pending-registrations":
            if len(sys.argv) < 3:
                print(json.dumps({"error": "User ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]

            # Create bridge with correct user
            user_bridge = GUIBridge(user_id=user_id)
            registrations = await user_bridge.list_pending_registrations()
            print(json.dumps(registrations))

        elif command == "authenticate-nft":
            # NFT-based authentication for Qube ownership
            if len(sys.argv) < 4:
                print(json.dumps({"error": "User ID and Qube ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            qube_id = validate_qube_id(sys.argv[3])
            password = get_secret("password", argv_index=4)

            # Create bridge with correct user
            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.authenticate_nft(qube_id, password)
            print(json.dumps(result))

        elif command == "refresh-auth-token":
            # Refresh an existing JWT token
            if len(sys.argv) < 3:
                print(json.dumps({"error": "Token required"}), file=sys.stderr)
                sys.exit(1)

            token = sys.argv[2]

            result = await bridge.refresh_auth_token(token)
            print(json.dumps(result))

        elif command == "get-auth-status":
            # Check if Qube can authenticate
            if len(sys.argv) < 3:
                print(json.dumps({"error": "Qube ID required"}), file=sys.stderr)
                sys.exit(1)

            qube_id = validate_qube_id(sys.argv[2])

            result = await bridge.get_auth_status(qube_id)
            print(json.dumps(result))


        # =====================================================================
        # P2P Network Commands
        # =====================================================================

        elif command == "get-online-qubes":
            if len(sys.argv) < 3:
                print(json.dumps({"error": "User ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.get_online_qubes()
            print(json.dumps(result))

        elif command == "generate-introduction":
            # Generate an AI introduction message (Qube introduces itself)
            if len(sys.argv) < 6:
                print(json.dumps({"error": "User ID, Qube ID, to_commitment, and to_name required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            qube_id = validate_qube_id(sys.argv[3])
            to_commitment = sys.argv[4]
            to_name = sys.argv[5]
            to_description = sys.argv[6] if len(sys.argv) > 6 else ""
            password = get_secret("password", argv_index=7, required=False) or get_secret("password", argv_index=6)

            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.generate_introduction_message(
                qube_id, to_commitment, to_name, to_description, password
            )
            print(json.dumps(result))

        elif command == "send-introduction":
            if len(sys.argv) < 6:
                print(json.dumps({"error": "User ID, Qube ID, to_commitment, and message required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            qube_id = validate_qube_id(sys.argv[3])
            to_commitment = sys.argv[4]
            message = sys.argv[5]
            password = get_secret("password", argv_index=6)

            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.send_introduction(qube_id, to_commitment, message, password)
            print(json.dumps(result))

        elif command == "get-pending-introductions":
            if len(sys.argv) < 4:
                print(json.dumps({"error": "User ID and Qube ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            qube_id = validate_qube_id(sys.argv[3])
            password = get_secret("password", argv_index=4)

            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.get_pending_introductions(qube_id, password)
            print(json.dumps(result))

        elif command == "evaluate-introduction":
            # Have the Qube's AI evaluate an incoming introduction
            if len(sys.argv) < 6:
                print(json.dumps({"error": "User ID, Qube ID, from_name, and intro_message required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            qube_id = validate_qube_id(sys.argv[3])
            from_name = sys.argv[4]
            intro_message = sys.argv[5]
            password = get_secret("password", argv_index=6)

            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.evaluate_introduction(qube_id, from_name, intro_message, password)
            print(json.dumps(result))

        elif command == "accept-introduction":
            if len(sys.argv) < 5:
                print(json.dumps({"error": "User ID, Qube ID, and relay_id required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            qube_id = validate_qube_id(sys.argv[3])
            relay_id = sys.argv[4]
            password = get_secret("password", argv_index=5)

            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.accept_introduction(qube_id, relay_id, password)
            print(json.dumps(result))

        elif command == "reject-introduction":
            if len(sys.argv) < 5:
                print(json.dumps({"error": "User ID, Qube ID, and relay_id required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            qube_id = validate_qube_id(sys.argv[3])
            relay_id = sys.argv[4]
            password = get_secret("password", argv_index=5)

            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.reject_introduction(qube_id, relay_id, password)
            print(json.dumps(result))

        elif command == "process-p2p-message":
            # Process an incoming P2P message through the local Qube's AI
            if len(sys.argv) < 4:
                print(json.dumps({"error": "User ID and Qube ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            qube_id = validate_qube_id(sys.argv[3])

            import argparse
            parser = argparse.ArgumentParser()
            parser.add_argument("command")
            parser.add_argument("user_id")
            parser.add_argument("qube_id")
            parser.add_argument("--from-name", required=True)
            parser.add_argument("--from-commitment", default="")
            parser.add_argument("--message", required=True)
            parser.add_argument("--context", default="[]")  # JSON array
            parser.add_argument("--password", required=True)

            args = parser.parse_args()

            # Use stdin secret if available, fall back to argparse
            password = get_secret("password", required=False) or args.password

            # Parse context from JSON
            try:
                context = json.loads(args.context)
            except json.JSONDecodeError:
                context = []

            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.process_p2p_message(
                qube_id,
                args.from_name,
                args.from_commitment,
                args.message,
                context,
                password
            )
            print(json.dumps(result))

        elif command == "get-connections":
            if len(sys.argv) < 4:
                print(json.dumps({"error": "User ID and Qube ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            qube_id = validate_qube_id(sys.argv[3])

            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.get_connections(qube_id)
            print(json.dumps(result))

        elif command == "create-p2p-session":
            if len(sys.argv) < 4:
                print(json.dumps({"error": "User ID and Qube ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            qube_id = validate_qube_id(sys.argv[3])

            import argparse
            parser = argparse.ArgumentParser()
            parser.add_argument("command")
            parser.add_argument("user_id")
            parser.add_argument("qube_id")
            parser.add_argument("--local-qubes", default="")
            parser.add_argument("--remote-commitments", default="")
            parser.add_argument("--topic", default="")
            parser.add_argument("--password", required=True)

            args = parser.parse_args()

            # Use stdin secret if available, fall back to argparse
            password = get_secret("password", required=False) or args.password

            local_qube_ids = [q.strip() for q in args.local_qubes.split(",") if q.strip()]
            remote_commitments = [c.strip() for c in args.remote_commitments.split(",") if c.strip()]

            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.create_p2p_session(
                qube_id,
                local_qube_ids,
                remote_commitments,
                args.topic,
                password
            )
            print(json.dumps(result))

        elif command == "get-p2p-sessions":
            if len(sys.argv) < 4:
                print(json.dumps({"error": "User ID and Qube ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            qube_id = validate_qube_id(sys.argv[3])
            password = get_secret("password", argv_index=4)

            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.get_p2p_sessions(qube_id, password)
            print(json.dumps(result))

        elif command == "start-p2p-conversation":
            # Start a P2P conversation using the same logic as local multi-qube
            if len(sys.argv) < 3:
                print(json.dumps({"error": "User ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]

            import argparse
            parser = argparse.ArgumentParser()
            parser.add_argument("command")
            parser.add_argument("user_id")
            parser.add_argument("--local-qubes", required=True)  # Comma-separated qube IDs
            parser.add_argument("--remote-connections", default="[]")  # JSON array
            parser.add_argument("--session-id", required=True)
            parser.add_argument("--initial-prompt", required=True)
            parser.add_argument("--password", required=True)

            args = parser.parse_args()

            # Use stdin secret if available, fall back to argparse
            password = get_secret("password", required=False) or args.password

            local_qube_ids = [q.strip() for q in args.local_qubes.split(",") if q.strip()]
            remote_connections = json.loads(args.remote_connections)

            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.start_p2p_conversation(
                local_qube_ids,
                remote_connections,
                args.session_id,
                args.initial_prompt,
                password
            )
            print(json.dumps(result))

        elif command == "continue-p2p-conversation":
            # Continue P2P conversation - get next local Qube response
            if len(sys.argv) < 3:
                print(json.dumps({"error": "User ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]

            import argparse
            parser = argparse.ArgumentParser()
            parser.add_argument("command")
            parser.add_argument("user_id")
            parser.add_argument("--conversation-id", required=True)
            parser.add_argument("--session-id", required=True)
            parser.add_argument("--local-qubes", required=True)
            parser.add_argument("--remote-connections", default="[]")
            parser.add_argument("--password", required=True)

            args = parser.parse_args()

            # Use stdin secret if available, fall back to argparse
            password = get_secret("password", required=False) or args.password

            local_qube_ids = [q.strip() for q in args.local_qubes.split(",") if q.strip()]
            remote_connections = json.loads(args.remote_connections)

            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.continue_p2p_conversation(
                args.conversation_id,
                args.session_id,
                local_qube_ids,
                remote_connections,
                password
            )
            print(json.dumps(result))

        elif command == "inject-p2p-block":
            # Inject a block received from hub into local conversation
            if len(sys.argv) < 3:
                print(json.dumps({"error": "User ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]

            import argparse
            parser = argparse.ArgumentParser()
            parser.add_argument("command")
            parser.add_argument("user_id")
            parser.add_argument("--conversation-id", required=True)
            parser.add_argument("--session-id", required=True)
            parser.add_argument("--block-data", required=True)  # JSON string
            parser.add_argument("--from-commitment", required=True)
            parser.add_argument("--local-qubes", required=True)
            parser.add_argument("--remote-connections", default="[]")
            parser.add_argument("--password", required=True)

            args = parser.parse_args()

            # Use stdin secret if available, fall back to argparse
            password = get_secret("password", required=False) or args.password

            local_qube_ids = [q.strip() for q in args.local_qubes.split(",") if q.strip()]
            remote_connections = json.loads(args.remote_connections)
            block_data = json.loads(args.block_data)

            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.inject_p2p_block(
                args.conversation_id,
                args.session_id,
                block_data,
                args.from_commitment,
                local_qube_ids,
                remote_connections,
                password
            )
            print(json.dumps(result))

        elif command == "send-p2p-user-message":
            # Send user message in P2P conversation
            if len(sys.argv) < 3:
                print(json.dumps({"error": "User ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]

            import argparse
            parser = argparse.ArgumentParser()
            parser.add_argument("command")
            parser.add_argument("user_id")
            parser.add_argument("--conversation-id", required=True)
            parser.add_argument("--session-id", required=True)
            parser.add_argument("--message", required=True)
            parser.add_argument("--local-qubes", required=True)
            parser.add_argument("--remote-connections", default="[]")
            parser.add_argument("--password", required=True)

            args = parser.parse_args()

            # Use stdin secret if available, fall back to argparse
            password = get_secret("password", required=False) or args.password

            local_qube_ids = [q.strip() for q in args.local_qubes.split(",") if q.strip()]
            remote_connections = json.loads(args.remote_connections)

            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.send_p2p_user_message(
                args.conversation_id,
                args.session_id,
                args.message,
                local_qube_ids,
                remote_connections,
                password
            )
            print(json.dumps(result))

        # =====================================================================
        # SETUP WIZARD COMMANDS
        # (check-first-run, create-user-account, check-ollama-status are handled
        #  early in main() before GUIBridge initialization)
        # =====================================================================

        elif command == "create-qube-for-minting":
            # Create a qube and return info needed for NFT minting
            if len(sys.argv) < 3:
                print(json.dumps({"success": False, "error": "User ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]

            import argparse
            parser = argparse.ArgumentParser()
            parser.add_argument("command")
            parser.add_argument("user_id")
            parser.add_argument("--name", required=True)
            parser.add_argument("--genesis-prompt", required=True)
            parser.add_argument("--ai-provider", required=True)
            parser.add_argument("--ai-model", required=True)
            parser.add_argument("--evaluation-model", default="mistral:7b")
            parser.add_argument("--favorite-color", default="#6366f1")
            parser.add_argument("--password", required=True)

            args = parser.parse_args()

            # Use stdin secret if available, fall back to argparse
            password = get_secret("password", required=False) or args.password

            # Create bridge with correct user
            user_bridge = GUIBridge(user_id=user_id)
            user_bridge.orchestrator.set_master_key(password)

            try:
                # Create the qube (without minting - we'll do that through server)
                qube = await user_bridge.create_qube(
                    name=args.name,
                    genesis_prompt=args.genesis_prompt,
                    ai_provider=args.ai_provider,
                    ai_model=args.ai_model,
                    voice_model="",  # No voice by default
                    wallet_address="",  # Will be set during minting
                    password=password,
                    favorite_color=args.favorite_color,
                    generate_avatar=False,  # Use placeholder
                )

                # Get qube data for minting
                qube_obj = user_bridge.orchestrator.qubes.get(qube["qube_id"])
                if not qube_obj:
                    await user_bridge.orchestrator.load_qube(qube["qube_id"])
                    qube_obj = user_bridge.orchestrator.qubes[qube["qube_id"]]

                print(json.dumps({
                    "success": True,
                    "qube_id": qube["qube_id"],
                    "public_key": qube.get("public_key", ""),
                    "genesis_block_hash": qube.get("genesis_block_hash", ""),
                    "recipient_address": qube.get("recipient_address", ""),
                }))

            except Exception as e:
                logger.error(f"Failed to create qube for minting: {e}", exc_info=True)
                print(json.dumps({"success": False, "error": str(e)}))

        elif command == "save-api-keys":
            # Save API keys to secure settings
            if len(sys.argv) < 3:
                print(json.dumps({"success": False, "error": "User ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]
            password = get_secret("password", argv_index=3)

            # Parse API keys from remaining args
            import argparse
            parser = argparse.ArgumentParser()
            parser.add_argument("command")
            parser.add_argument("user_id")
            parser.add_argument("--openai", default="")
            parser.add_argument("--anthropic", default="")
            parser.add_argument("--google", default="")
            parser.add_argument("--deepseek", default="")
            parser.add_argument("--perplexity", default="")
            parser.add_argument("--venice", default="")

            args = parser.parse_args()

            # Create orchestrator and set master key
            orchestrator = UserOrchestrator(user_id=user_id)
            orchestrator.set_master_key(password)

            # Save API keys using secure settings
            from utils.secure_settings import SecureSettingsManager
            settings = SecureSettingsManager(orchestrator.data_dir / "settings.enc")
            settings.set_encryption_key(orchestrator.master_key)

            if args.openai:
                settings.set("api_keys.openai", args.openai)
            if args.anthropic:
                settings.set("api_keys.anthropic", args.anthropic)
            if args.google:
                settings.set("api_keys.google", args.google)
            if args.deepseek:
                settings.set("api_keys.deepseek", args.deepseek)
            if args.perplexity:
                settings.set("api_keys.perplexity", args.perplexity)
            if args.venice:
                settings.set("api_keys.venice", args.venice)

            settings.save()

            print(json.dumps({"success": True}))

        elif command == "update-qube-nft":
            # Update qube with NFT minting info after server mints
            if len(sys.argv) < 3:
                print(json.dumps({"success": False, "error": "User ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]

            import argparse
            parser = argparse.ArgumentParser()
            parser.add_argument("command")
            parser.add_argument("user_id")
            parser.add_argument("--qube-id", required=True)
            parser.add_argument("--category-id", required=True)
            parser.add_argument("--mint-txid", required=True)
            parser.add_argument("--password", required=True)

            args = parser.parse_args()

            # Use stdin secret if available, fall back to argparse
            password = get_secret("password", required=False) or args.password

            # Create bridge and update qube
            user_bridge = GUIBridge(user_id=user_id)
            user_bridge.orchestrator.set_master_key(password)

            # Load qube
            if args.qube_id not in user_bridge.orchestrator.qubes:
                await user_bridge.orchestrator.load_qube(args.qube_id)

            qube = user_bridge.orchestrator.qubes[args.qube_id]

            # Update NFT info
            qube.nft_category_id = args.category_id
            qube.mint_txid = args.mint_txid

            # Save qube state
            await user_bridge.orchestrator._save_qube_data(qube)

            print(json.dumps({
                "success": True,
                "qube_id": args.qube_id,
                "category_id": args.category_id,
                "mint_txid": args.mint_txid
            }))

        elif command == "sync-to-chain":
            # Sync Qube to chain (backup to IPFS)
            if len(sys.argv) < 3:
                print(json.dumps({"success": False, "error": "User ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]

            import argparse
            parser = argparse.ArgumentParser()
            parser.add_argument("command")
            parser.add_argument("user_id")
            parser.add_argument("--qube-id", required=True)
            parser.add_argument("--password", required=True)  # Master password

            args = parser.parse_args()

            # Use stdin secret if available, fall back to argparse
            password = get_secret("password", required=False) or args.password

            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.sync_to_chain(
                qube_id=args.qube_id,
                master_password=password
            )
            print(json.dumps(result))

        elif command == "transfer-qube":
            # Transfer Qube to new owner (DESTRUCTIVE - deletes local copy)
            if len(sys.argv) < 3:
                print(json.dumps({"success": False, "error": "User ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]

            import argparse
            parser = argparse.ArgumentParser()
            parser.add_argument("command")
            parser.add_argument("user_id")
            parser.add_argument("--qube-id", required=True)
            parser.add_argument("--recipient-address", required=True)
            parser.add_argument("--recipient-public-key", required=True)
            parser.add_argument("--wallet-wif", required=True)
            parser.add_argument("--password", required=True)  # Master password

            args = parser.parse_args()

            # Use stdin secrets if available, fall back to argparse
            password = get_secret("password", required=False) or args.password
            wallet_wif = get_secret("wallet_wif", required=False) or args.wallet_wif

            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.transfer_qube(
                qube_id=args.qube_id,
                recipient_address=args.recipient_address,
                recipient_public_key=args.recipient_public_key,
                wallet_wif=wallet_wif,
                master_password=password
            )
            print(json.dumps(result))

        elif command == "import-from-wallet":
            # Import Qube from wallet
            if len(sys.argv) < 3:
                print(json.dumps({"success": False, "error": "User ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]

            import argparse
            parser = argparse.ArgumentParser()
            parser.add_argument("command")
            parser.add_argument("user_id")
            parser.add_argument("--wallet-wif", required=True)
            parser.add_argument("--category-id", required=True)
            parser.add_argument("--password", required=True)  # Master password

            args = parser.parse_args()

            # Use stdin secrets if available, fall back to argparse
            password = get_secret("password", required=False) or args.password
            wallet_wif = get_secret("wallet_wif", required=False) or args.wallet_wif

            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.import_from_wallet(
                wallet_wif=wallet_wif,
                category_id=args.category_id,
                master_password=password
            )
            print(json.dumps(result))

        elif command == "scan-wallet":
            # Scan wallet for Qube NFTs
            if len(sys.argv) < 3:
                print(json.dumps({"success": False, "error": "User ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]

            import argparse
            parser = argparse.ArgumentParser()
            parser.add_argument("command")
            parser.add_argument("user_id")
            parser.add_argument("--wallet-address", required=True)

            args = parser.parse_args()

            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.scan_wallet_for_qubes(
                wallet_address=args.wallet_address
            )
            print(json.dumps(result))

        elif command == "resolve-public-key":
            # Resolve public key from BCH address
            if len(sys.argv) < 3:
                print(json.dumps({"success": False, "error": "User ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]

            import argparse
            parser = argparse.ArgumentParser()
            parser.add_argument("command")
            parser.add_argument("user_id")
            parser.add_argument("--address", required=True)

            args = parser.parse_args()

            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.resolve_recipient_public_key(
                recipient_address=args.address
            )
            print(json.dumps(result))

        elif command == "get-debug-prompt":
            # Get the last AI prompt sent for a qube (dev debugging)
            if len(sys.argv) < 3:
                print(json.dumps({"success": False, "error": "Qube ID required"}), file=sys.stderr)
                sys.exit(1)

            qube_id = sys.argv[2]

            try:
                from ai.reasoner import get_debug_prompt, get_all_debug_prompts

                if qube_id == "all":
                    # Return all cached prompts
                    all_prompts = get_all_debug_prompts()
                    print(json.dumps({
                        "success": True,
                        "prompts": all_prompts
                    }))
                else:
                    # Return prompt for specific qube
                    prompt_info = get_debug_prompt(qube_id)
                    if prompt_info:
                        print(json.dumps({
                            "success": True,
                            "prompt": prompt_info
                        }))
                    else:
                        print(json.dumps({
                            "success": False,
                            "error": f"No cached prompt for qube {qube_id}"
                        }))
            except Exception as e:
                logger.error(f"Failed to get debug prompt: {e}", exc_info=True)
                print(json.dumps({"success": False, "error": str(e)}), file=sys.stderr)
                sys.exit(1)

        # =====================================================================
        # GAMES Commands
        # =====================================================================
        elif command == "start-game":
            # Start a new game
            if len(sys.argv) < 3:
                print(json.dumps({"success": False, "error": "User ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]

            import argparse
            parser = argparse.ArgumentParser()
            parser.add_argument("command")
            parser.add_argument("user_id")
            parser.add_argument("--qube-id", required=True)
            parser.add_argument("--game-type", default="chess")
            parser.add_argument("--opponent-type", required=True, choices=["human", "qube"])
            parser.add_argument("--opponent-id", default=None)
            parser.add_argument("--qube-color", default="random", choices=["white", "black", "random"])
            parser.add_argument("--password", default=None)

            args = parser.parse_args()
            password = get_secret("password", required=False) or args.password

            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.start_game(
                qube_id=args.qube_id,
                game_type=args.game_type,
                opponent_type=args.opponent_type,
                opponent_id=args.opponent_id,
                qube_color=args.qube_color,
                password=password
            )
            print(json.dumps(result))

        elif command == "get-game-state":
            # Get current game state
            if len(sys.argv) < 3:
                print(json.dumps({"success": False, "error": "User ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]

            import argparse
            parser = argparse.ArgumentParser()
            parser.add_argument("command")
            parser.add_argument("user_id")
            parser.add_argument("--qube-id", required=True)
            parser.add_argument("--password", default=None)

            args = parser.parse_args()
            password = get_secret("password", required=False) or args.password

            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.get_game_state(
                qube_id=args.qube_id,
                password=password
            )
            print(json.dumps(result))

        elif command == "get-game-stats":
            # Get permanent game statistics
            if len(sys.argv) < 3:
                print(json.dumps({"success": False, "error": "User ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]

            import argparse
            parser = argparse.ArgumentParser()
            parser.add_argument("command")
            parser.add_argument("user_id")
            parser.add_argument("--qube-id", required=True)
            parser.add_argument("--game-type", default=None)
            parser.add_argument("--password", default=None)

            args = parser.parse_args()
            password = get_secret("password", required=False) or args.password

            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.get_game_stats(
                qube_id=args.qube_id,
                password=password,
                game_type=args.game_type
            )
            print(json.dumps(result))

        elif command == "make-move":
            # Make a move in active game
            if len(sys.argv) < 3:
                print(json.dumps({"success": False, "error": "User ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]

            import argparse
            parser = argparse.ArgumentParser()
            parser.add_argument("command")
            parser.add_argument("user_id")
            parser.add_argument("--qube-id", required=True)
            parser.add_argument("--move", required=True)
            parser.add_argument("--player-type", required=True, choices=["human", "qube"])
            parser.add_argument("--password", default=None)

            args = parser.parse_args()
            password = get_secret("password", required=False) or args.password

            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.make_move(
                qube_id=args.qube_id,
                move=args.move,
                player_type=args.player_type,
                password=password
            )
            print(json.dumps(result))

        elif command == "add-game-chat":
            # Add chat message to game
            if len(sys.argv) < 3:
                print(json.dumps({"success": False, "error": "User ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]

            import argparse
            parser = argparse.ArgumentParser()
            parser.add_argument("command")
            parser.add_argument("user_id")
            parser.add_argument("--qube-id", required=True)
            parser.add_argument("--message", required=True)
            parser.add_argument("--sender-type", required=True, choices=["human", "qube"])
            parser.add_argument("--password", default=None)

            args = parser.parse_args()
            password = get_secret("password", required=False) or args.password

            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.add_game_chat(
                qube_id=args.qube_id,
                message=args.message,
                sender_type=args.sender_type,
                password=password
            )
            print(json.dumps(result))

        elif command == "end-game":
            # End game and create GAME block
            if len(sys.argv) < 3:
                print(json.dumps({"success": False, "error": "User ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]

            import argparse
            parser = argparse.ArgumentParser()
            parser.add_argument("command")
            parser.add_argument("user_id")
            parser.add_argument("--qube-id", required=True)
            parser.add_argument("--result", required=True, choices=["1-0", "0-1", "1/2-1/2", "*"])
            parser.add_argument("--termination", required=True)
            parser.add_argument("--password", default=None)

            args = parser.parse_args()
            password = get_secret("password", required=False) or args.password

            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.end_game(
                qube_id=args.qube_id,
                result=args.result,
                termination=args.termination,
                password=password
            )
            print(json.dumps(result))

        elif command == "abandon-game":
            # Abandon game without creating block
            if len(sys.argv) < 3:
                print(json.dumps({"success": False, "error": "User ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]

            import argparse
            parser = argparse.ArgumentParser()
            parser.add_argument("command")
            parser.add_argument("user_id")
            parser.add_argument("--qube-id", required=True)
            parser.add_argument("--password", default=None)

            args = parser.parse_args()
            password = get_secret("password", required=False) or args.password

            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.abandon_game(
                qube_id=args.qube_id,
                password=password
            )
            print(json.dumps(result))

        elif command == "request-qube-move":
            # Request Qube to make a move (AI)
            if len(sys.argv) < 3:
                print(json.dumps({"success": False, "error": "User ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]

            import argparse
            parser = argparse.ArgumentParser()
            parser.add_argument("command")
            parser.add_argument("user_id")
            parser.add_argument("--qube-id", required=True)
            parser.add_argument("--password", default=None)

            args = parser.parse_args()
            password = get_secret("password", required=False) or args.password

            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.request_qube_move(
                qube_id=args.qube_id,
                password=password
            )
            print(json.dumps(result))

        elif command == "resign-game":
            # Resign the current game
            if len(sys.argv) < 3:
                print(json.dumps({"success": False, "error": "User ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]

            import argparse
            parser = argparse.ArgumentParser()
            parser.add_argument("command")
            parser.add_argument("user_id")
            parser.add_argument("--qube-id", required=True)
            parser.add_argument("--resigning-player", required=True)
            parser.add_argument("--password", default=None)

            args = parser.parse_args()
            password = get_secret("password", required=False) or args.password

            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.resign_game(
                qube_id=args.qube_id,
                password=password,
                resigning_player=args.resigning_player
            )
            print(json.dumps(result))

        elif command == "offer-draw":
            # Offer a draw in the current game
            if len(sys.argv) < 3:
                print(json.dumps({"success": False, "error": "User ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]

            import argparse
            parser = argparse.ArgumentParser()
            parser.add_argument("command")
            parser.add_argument("user_id")
            parser.add_argument("--qube-id", required=True)
            parser.add_argument("--offering-player", required=True)
            parser.add_argument("--password", default=None)

            args = parser.parse_args()
            password = get_secret("password", required=False) or args.password

            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.offer_draw(
                qube_id=args.qube_id,
                password=password,
                offering_player=args.offering_player
            )
            print(json.dumps(result))

        elif command == "respond-to-draw":
            # Respond to a draw offer
            if len(sys.argv) < 3:
                print(json.dumps({"success": False, "error": "User ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]

            import argparse
            parser = argparse.ArgumentParser()
            parser.add_argument("command")
            parser.add_argument("user_id")
            parser.add_argument("--qube-id", required=True)
            parser.add_argument("--accepting", required=True, type=lambda x: x.lower() == 'true')
            parser.add_argument("--responding-player", required=True)
            parser.add_argument("--password", default=None)

            args = parser.parse_args()
            password = get_secret("password", required=False) or args.password

            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.respond_to_draw(
                qube_id=args.qube_id,
                password=password,
                accepting=args.accepting,
                responding_player=args.responding_player
            )
            print(json.dumps(result))

        # =====================================================================
        # Wallet Commands
        # =====================================================================

        elif command == "get-wallet-info":
            # Get wallet info for a Qube
            if len(sys.argv) < 3:
                print(json.dumps({"success": False, "error": "User ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]

            import argparse
            parser = argparse.ArgumentParser()
            parser.add_argument("command")
            parser.add_argument("user_id")
            parser.add_argument("--qube-id", required=True)
            parser.add_argument("--password", default=None)

            args = parser.parse_args()
            password = get_secret("password", required=False) or args.password

            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.get_qube_wallet_info(
                qube_id=args.qube_id,
                password=password
            )
            print(json.dumps(result))

        elif command == "get-context-preview":
            # Get context preview (active context + short-term memory)
            if len(sys.argv) < 3:
                print(json.dumps({"success": False, "error": "User ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]

            import argparse
            parser = argparse.ArgumentParser()
            parser.add_argument("command")
            parser.add_argument("user_id")
            parser.add_argument("--qube-id", required=True)
            parser.add_argument("--password", default=None)

            args = parser.parse_args()
            password = get_secret("password", required=False) or args.password

            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.get_context_preview(
                qube_id=args.qube_id,
                password=password
            )
            print(json.dumps(result))

        elif command == "propose-wallet-tx":
            # Qube proposes a wallet transaction
            if len(sys.argv) < 3:
                print(json.dumps({"success": False, "error": "User ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]

            import argparse
            parser = argparse.ArgumentParser()
            parser.add_argument("command")
            parser.add_argument("user_id")
            parser.add_argument("--qube-id", required=True)
            parser.add_argument("--to-address", required=True)
            parser.add_argument("--amount", required=True, type=int, help="Amount in satoshis")
            parser.add_argument("--memo", default="")
            parser.add_argument("--password", default=None)

            args = parser.parse_args()
            password = get_secret("password", required=False) or args.password

            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.propose_wallet_transaction(
                qube_id=args.qube_id,
                to_address=args.to_address,
                amount_satoshis=args.amount,
                memo=args.memo,
                password=password
            )
            print(json.dumps(result))

        elif command == "approve-wallet-tx":
            # Owner approves a pending wallet transaction
            if len(sys.argv) < 3:
                print(json.dumps({"success": False, "error": "User ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]

            import argparse
            parser = argparse.ArgumentParser()
            parser.add_argument("command")
            parser.add_argument("user_id")
            parser.add_argument("--qube-id", required=True)
            parser.add_argument("--tx-id", required=True)
            parser.add_argument("--password", default=None)

            args = parser.parse_args()
            password = get_secret("password", required=False) or args.password
            owner_wif = get_secret("owner_wif", required=True)

            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.approve_wallet_transaction(
                qube_id=args.qube_id,
                pending_tx_id=args.tx_id,
                owner_wif=owner_wif,
                password=password
            )
            print(json.dumps(result))

        elif command == "reject-wallet-tx":
            # Owner rejects a pending wallet transaction
            if len(sys.argv) < 3:
                print(json.dumps({"success": False, "error": "User ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]

            import argparse
            parser = argparse.ArgumentParser()
            parser.add_argument("command")
            parser.add_argument("user_id")
            parser.add_argument("--qube-id", required=True)
            parser.add_argument("--tx-id", required=True)
            parser.add_argument("--password", default=None)

            args = parser.parse_args()
            password = get_secret("password", required=False) or args.password

            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.reject_wallet_transaction(
                qube_id=args.qube_id,
                pending_tx_id=args.tx_id,
                password=password
            )
            print(json.dumps(result))

        elif command == "owner-withdraw":
            # Owner withdraws directly from Qube wallet (IF branch)
            if len(sys.argv) < 3:
                print(json.dumps({"success": False, "error": "User ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]

            import argparse
            parser = argparse.ArgumentParser()
            parser.add_argument("command")
            parser.add_argument("user_id")
            parser.add_argument("--qube-id", required=True)
            parser.add_argument("--to-address", required=True)
            parser.add_argument("--amount", required=True, type=int, help="Amount in satoshis (0 for all)")
            parser.add_argument("--password", default=None)

            args = parser.parse_args()
            password = get_secret("password", required=False) or args.password
            owner_wif = get_secret("owner_wif", required=True)

            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.owner_withdraw_from_wallet(
                qube_id=args.qube_id,
                to_address=args.to_address,
                amount_satoshis=args.amount,
                owner_wif=owner_wif,
                password=password
            )
            print(json.dumps(result))

        elif command == "get-wallet-transactions":
            # Get wallet transaction history
            if len(sys.argv) < 3:
                print(json.dumps({"success": False, "error": "User ID required"}), file=sys.stderr)
                sys.exit(1)

            user_id = sys.argv[2]

            import argparse
            parser = argparse.ArgumentParser()
            parser.add_argument("command")
            parser.add_argument("user_id")
            parser.add_argument("--qube-id", required=True)
            parser.add_argument("--password", default=None)
            parser.add_argument("--limit", type=int, default=50)
            parser.add_argument("--offset", type=int, default=0)

            args = parser.parse_args()
            password = get_secret("password", required=False) or args.password

            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.get_wallet_transactions(
                qube_id=args.qube_id,
                password=password,
                limit=args.limit,
                offset=args.offset
            )
            print(json.dumps(result))

        # ==================== Clearance Profile CLI Commands ====================

        elif command == "get-clearance-profiles":
            # Args: user_id, qube_id
            user_id = sys.argv[2]
            qube_id = sys.argv[3]
            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.get_clearance_profiles(qube_id)
            print(json.dumps(result))

        elif command == "get-available-tags":
            # Args: user_id, qube_id
            user_id = sys.argv[2]
            qube_id = sys.argv[3]
            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.get_available_tags(qube_id)
            print(json.dumps(result))

        elif command == "get-trait-definitions":
            # Args: user_id, qube_id
            user_id = sys.argv[2]
            qube_id = sys.argv[3]
            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.get_trait_definitions(qube_id)
            print(json.dumps(result))

        elif command == "add-relationship-tag":
            # Args: user_id, qube_id, entity_id, tag, password
            user_id = sys.argv[2]
            qube_id = sys.argv[3]
            entity_id = sys.argv[4]
            tag = sys.argv[5]
            password = sys.argv[6]
            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.add_relationship_tag(qube_id, entity_id, tag, password)
            print(json.dumps(result))

        elif command == "remove-relationship-tag":
            # Args: user_id, qube_id, entity_id, tag, password
            user_id = sys.argv[2]
            qube_id = sys.argv[3]
            entity_id = sys.argv[4]
            tag = sys.argv[5]
            password = sys.argv[6]
            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.remove_relationship_tag(qube_id, entity_id, tag, password)
            print(json.dumps(result))

        elif command == "set-relationship-clearance":
            # Args: user_id, qube_id, entity_id, profile, password, [field_grants_json], [field_denials_json], [expires_days]
            user_id = sys.argv[2]
            qube_id = sys.argv[3]
            entity_id = sys.argv[4]
            profile = sys.argv[5]
            password = sys.argv[6]
            field_grants = json.loads(sys.argv[7]) if len(sys.argv) > 7 and sys.argv[7] else None
            field_denials = json.loads(sys.argv[8]) if len(sys.argv) > 8 and sys.argv[8] else None
            expires_days = int(sys.argv[9]) if len(sys.argv) > 9 and sys.argv[9] else None
            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.set_relationship_clearance(
                qube_id, entity_id, profile, password, field_grants, field_denials, expires_days
            )
            print(json.dumps(result))

        elif command == "suggest-clearance":
            # Args: user_id, qube_id, entity_id
            user_id = sys.argv[2]
            qube_id = sys.argv[3]
            entity_id = sys.argv[4]
            user_bridge = GUIBridge(user_id=user_id)
            result = await user_bridge.suggest_clearance(qube_id, entity_id)
            print(json.dumps(result))

        # ==================== End Clearance Profile CLI Commands ====================

        else:
            print(json.dumps({"error": f"Unknown command: {command}"}), file=sys.stderr)
            sys.exit(1)

    except Exception as e:
        logger.error(f"Command failed: {e}", exc_info=True)
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
