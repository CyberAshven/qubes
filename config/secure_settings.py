"""
Secure Settings Manager with Encrypted API Key Storage

Extends the existing SettingsManager with encrypted credential management.
API keys are stored encrypted with AES-256-GCM using user's master password.
"""

import json
import secrets
from pathlib import Path
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, asdict, field
from datetime import datetime

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

from utils.logging import get_logger
from core.exceptions import EncryptionError, DecryptionError

logger = get_logger(__name__)


@dataclass
class APIKeys:
    """
    API keys for AI providers and services

    All keys are optional - users only need to configure the providers they use.
    """
    openai: Optional[str] = None
    anthropic: Optional[str] = None
    google: Optional[str] = None
    deepseek: Optional[str] = None
    perplexity: Optional[str] = None
    venice: Optional[str] = None
    nanogpt: Optional[str] = None
    pinata_jwt: Optional[str] = None
    elevenlabs: Optional[str] = None
    deepgram: Optional[str] = None

    def to_dict(self) -> Dict[str, Optional[str]]:
        """Convert to dictionary, excluding None values"""
        return {k: v for k, v in asdict(self).items() if v is not None}

    def is_empty(self) -> bool:
        """Check if all keys are None"""
        return all(v is None for v in asdict(self).values())


@dataclass
class WalletSecurityConfig:
    """
    Wallet security settings for storing owner keys and auto-send whitelists.

    Keys are stored by NFT ADDRESS (multiple qubes at same address share key).
    Whitelists are stored by QUBE_ID (each qube has its own permissions).
    """
    # NFT address -> WIF (shared by all qubes at that address)
    owner_keys: Dict[str, str] = field(default_factory=dict)

    # qube_id -> list of whitelisted addresses (per-qube permissions)
    whitelists: Dict[str, List[str]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'owner_keys': self.owner_keys,
            'whitelists': self.whitelists
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WalletSecurityConfig':
        return cls(
            owner_keys=data.get('owner_keys', {}),
            whitelists=data.get('whitelists', {})
        )

    def has_key_for_address(self, nft_address: str) -> bool:
        """Check if we have a stored key for this NFT address."""
        return nft_address in self.owner_keys and bool(self.owner_keys[nft_address])

    def get_key_for_address(self, nft_address: str) -> Optional[str]:
        """Get stored WIF for NFT address."""
        return self.owner_keys.get(nft_address)

    def is_whitelisted(self, qube_id: str, address: str) -> bool:
        """Check if address is whitelisted for this qube."""
        whitelist = self.whitelists.get(qube_id, [])
        is_in_whitelist = address in whitelist
        # Debug logging for whitelist check
        import logging
        logger = logging.getLogger(__name__)
        logger.info(
            f"WHITELIST CHECK: qube_id={qube_id}, address={address[:30]}..., "
            f"whitelist_count={len(whitelist)}, found={is_in_whitelist}"
        )
        if whitelist:
            logger.info(f"WHITELIST CONTENTS: {[a[:30] + '...' for a in whitelist]}")
        return is_in_whitelist


class SecureSettingsManager:
    """
    Secure settings manager with encrypted API key storage

    Features:
    - AES-256-GCM encryption for API keys
    - PBKDF2-SHA256 key derivation (600K iterations)
    - Per-user encrypted storage
    - API key validation
    """

    def __init__(self, user_data_dir: Path, master_password: Optional[str] = None):
        """
        Initialize secure settings manager

        Args:
            user_data_dir: User's data directory (e.g., data/users/{username})
            master_password: Optional master password (required for encryption/decryption)
        """
        self.user_data_dir = user_data_dir
        self.user_data_dir.mkdir(parents=True, exist_ok=True)

        self.api_keys_file = self.user_data_dir / "api_keys.enc"
        self.salt_file = self.user_data_dir / "salt.bin"
        self.iterations_file = self.user_data_dir / "pbkdf2_iterations.txt"

        self._master_password = master_password
        self._encryption_key: Optional[bytes] = None

        logger.info("secure_settings_initialized", user_data_dir=str(user_data_dir))

    def set_master_password(self, password: str):
        """
        Set master password for encryption/decryption

        Args:
            password: User's master password
        """
        self._master_password = password
        self._encryption_key = None  # Force re-derivation
        logger.debug("master_password_set")

    def _derive_encryption_key(self) -> bytes:
        """
        Derive encryption key from master password using PBKDF2

        Returns:
            32-byte encryption key

        Raises:
            EncryptionError: If master password not set
        """
        if not self._master_password:
            raise EncryptionError(
                "Master password not set. Call set_master_password() first.",
                context={"user_data_dir": str(self.user_data_dir)}
            )

        # Return cached key if available
        if self._encryption_key:
            return self._encryption_key

        # Load or generate salt
        if self.salt_file.exists():
            salt = self.salt_file.read_bytes()

            # Check for iteration count (backward compatibility)
            if self.iterations_file.exists():
                iterations = int(self.iterations_file.read_text().strip())
            else:
                # Old user - default to 100K for backward compatibility
                iterations = 100000
        else:
            # New user - use OWASP 2025 recommendation
            salt = secrets.token_bytes(32)
            self.salt_file.write_bytes(salt)
            iterations = 600000
            self.iterations_file.write_text(str(iterations))

        # Derive key using PBKDF2-SHA256
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=iterations,
            backend=default_backend()
        )

        self._encryption_key = kdf.derive(self._master_password.encode())

        logger.debug("encryption_key_derived", iterations=iterations)

        return self._encryption_key

    def save_api_keys(self, api_keys: APIKeys):
        """
        Save API keys encrypted to disk

        Args:
            api_keys: APIKeys instance with credentials

        Raises:
            EncryptionError: If encryption fails
        """
        try:
            # Get encryption key
            key = self._derive_encryption_key()

            # Convert to JSON
            keys_dict = api_keys.to_dict()
            plaintext = json.dumps(keys_dict, sort_keys=True).encode()

            # Encrypt using AES-256-GCM
            aesgcm = AESGCM(key)
            nonce = secrets.token_bytes(12)  # 96-bit nonce for GCM
            ciphertext = aesgcm.encrypt(nonce, plaintext, None)

            # Store nonce + ciphertext
            encrypted_data = {
                "nonce": nonce.hex(),
                "ciphertext": ciphertext.hex(),
                "algorithm": "AES-256-GCM",
                "version": "1.0"
            }

            with open(self.api_keys_file, 'w') as f:
                json.dump(encrypted_data, f, indent=2)

            logger.info("api_keys_saved", num_keys=len(keys_dict))

        except Exception as e:
            logger.error("api_key_save_failed", exc_info=True)
            raise EncryptionError(
                "Failed to save encrypted API keys",
                context={"file": str(self.api_keys_file)},
                cause=e
            )

    def load_api_keys(self) -> APIKeys:
        """
        Load and decrypt API keys from disk

        Returns:
            APIKeys instance with decrypted credentials

        Raises:
            DecryptionError: If decryption fails or master password incorrect
        """
        # Return empty if file doesn't exist
        if not self.api_keys_file.exists():
            logger.debug("no_api_keys_file_found")
            return APIKeys()

        try:
            # Load encrypted data
            with open(self.api_keys_file, 'r') as f:
                encrypted_data = json.load(f)

            # Get encryption key
            key = self._derive_encryption_key()

            # Decrypt using AES-256-GCM
            aesgcm = AESGCM(key)
            nonce = bytes.fromhex(encrypted_data["nonce"])
            ciphertext = bytes.fromhex(encrypted_data["ciphertext"])

            plaintext = aesgcm.decrypt(nonce, ciphertext, None)

            # Parse JSON
            keys_dict = json.loads(plaintext.decode())

            logger.debug("api_keys_loaded", num_keys=len(keys_dict))

            return APIKeys(**keys_dict)

        except Exception as e:
            logger.error("api_key_load_failed", exc_info=True)
            raise DecryptionError(
                "Failed to decrypt API keys. Incorrect master password?",
                context={"file": str(self.api_keys_file)},
                cause=e
            )

    def update_api_key(self, provider: str, api_key: str):
        """
        Update a single API key

        Args:
            provider: Provider name (openai, anthropic, google, etc.)
            api_key: API key value

        Raises:
            ValueError: If provider invalid
        """
        # Load existing keys (start fresh if decryption fails — stale password)
        try:
            api_keys = self.load_api_keys()
        except DecryptionError:
            logger.warning("api_key_load_failed_starting_fresh", provider=provider)
            api_keys = APIKeys()

        # Validate provider
        if not hasattr(api_keys, provider):
            valid_providers = list(APIKeys.__annotations__.keys())
            raise ValueError(
                f"Invalid provider '{provider}'. Valid providers: {valid_providers}"
            )

        # Update key
        setattr(api_keys, provider, api_key)

        # Save
        self.save_api_keys(api_keys)

        logger.info("api_key_updated", provider=provider)

    def get_api_key(self, provider: str) -> Optional[str]:
        """
        Get a single API key

        Args:
            provider: Provider name (openai, anthropic, google, etc.)

        Returns:
            API key or None if not set
        """
        api_keys = self.load_api_keys()
        return getattr(api_keys, provider, None)

    def delete_api_key(self, provider: str):
        """
        Delete a single API key

        Args:
            provider: Provider name (openai, anthropic, google, etc.)
        """
        # Load existing keys
        api_keys = self.load_api_keys()

        # Clear key
        if hasattr(api_keys, provider):
            setattr(api_keys, provider, None)

            # Save
            self.save_api_keys(api_keys)

            logger.info("api_key_deleted", provider=provider)

    def clear_all_api_keys(self):
        """Delete all API keys"""
        if self.api_keys_file.exists():
            self.api_keys_file.unlink()
            logger.info("all_api_keys_cleared")

    def has_api_keys(self) -> bool:
        """Check if any API keys are stored"""
        if not self.api_keys_file.exists():
            return False

        try:
            api_keys = self.load_api_keys()
            return not api_keys.is_empty()
        except:
            return False

    def list_configured_providers(self) -> list[str]:
        """
        Get list of providers with configured API keys

        Returns:
            List of provider names (e.g., ['openai', 'anthropic'])
        """
        try:
            api_keys = self.load_api_keys()
            return [k for k, v in api_keys.to_dict().items() if v is not None]
        except:
            return []

    async def validate_api_key(self, provider: str, api_key: str) -> Dict[str, Any]:
        """
        Validate an API key by making a test request

        Args:
            provider: Provider name (openai, anthropic, google, etc.)
            api_key: API key to validate

        Returns:
            Dictionary with validation result:
            {
                "valid": bool,
                "message": str,
                "details": Optional[dict]
            }
        """
        logger.info("validating_api_key", provider=provider)

        try:
            if provider == "openai":
                return await self._validate_openai(api_key)
            elif provider == "anthropic":
                return await self._validate_anthropic(api_key)
            elif provider == "google":
                return await self._validate_google(api_key)
            elif provider == "deepseek":
                return await self._validate_deepseek(api_key)
            elif provider == "perplexity":
                return await self._validate_perplexity(api_key)
            elif provider == "venice":
                return await self._validate_venice(api_key)
            elif provider == "nanogpt":
                return await self._validate_nanogpt(api_key)
            elif provider == "pinata_jwt":
                return await self._validate_pinata(api_key)
            elif provider == "elevenlabs":
                return await self._validate_elevenlabs(api_key)
            elif provider == "deepgram":
                return await self._validate_deepgram(api_key)
            else:
                return {
                    "valid": False,
                    "message": f"Validation not implemented for {provider}",
                    "details": None
                }

        except Exception as e:
            logger.error("api_key_validation_failed", provider=provider, exc_info=True)
            return {
                "valid": False,
                "message": f"Validation error: {str(e)}",
                "details": {"error": str(e)}
            }

    async def _validate_openai(self, api_key: str) -> Dict[str, Any]:
        """Validate OpenAI API key"""
        import httpx

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=10.0
                )

                if response.status_code == 200:
                    return {
                        "valid": True,
                        "message": "OpenAI API key is valid",
                        "details": {"models_available": len(response.json().get("data", []))}
                    }
                elif response.status_code == 401:
                    return {
                        "valid": False,
                        "message": "Invalid OpenAI API key",
                        "details": {"status_code": 401}
                    }
                else:
                    return {
                        "valid": False,
                        "message": f"OpenAI API error: {response.status_code}",
                        "details": {"status_code": response.status_code}
                    }
        except Exception as e:
            return {
                "valid": False,
                "message": f"Connection error: {str(e)}",
                "details": {"error": str(e)}
            }

    async def _validate_anthropic(self, api_key: str) -> Dict[str, Any]:
        """Validate Anthropic API key"""
        import httpx

        try:
            async with httpx.AsyncClient() as client:
                # Anthropic doesn't have a models endpoint, so we make a minimal request
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json"
                    },
                    json={
                        "model": "claude-sonnet-4-5-20250929",
                        "max_tokens": 1,
                        "messages": [{"role": "user", "content": "test"}]
                    },
                    timeout=10.0
                )

                # 200 = success, 400 = likely valid key but bad request format
                if response.status_code in [200, 400]:
                    return {
                        "valid": True,
                        "message": "Anthropic API key is valid",
                        "details": {"status_code": response.status_code}
                    }
                elif response.status_code == 401:
                    return {
                        "valid": False,
                        "message": "Invalid Anthropic API key",
                        "details": {"status_code": 401}
                    }
                else:
                    return {
                        "valid": False,
                        "message": f"Anthropic API error: {response.status_code}",
                        "details": {"status_code": response.status_code}
                    }
        except Exception as e:
            return {
                "valid": False,
                "message": f"Connection error: {str(e)}",
                "details": {"error": str(e)}
            }

    async def _validate_google(self, api_key: str) -> Dict[str, Any]:
        """Validate Google AI API key"""
        import httpx

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}",
                    timeout=10.0
                )

                if response.status_code == 200:
                    return {
                        "valid": True,
                        "message": "Google AI API key is valid",
                        "details": {"models_available": len(response.json().get("models", []))}
                    }
                elif response.status_code == 400:
                    return {
                        "valid": False,
                        "message": "Invalid Google AI API key",
                        "details": {"status_code": 400}
                    }
                else:
                    return {
                        "valid": False,
                        "message": f"Google AI API error: {response.status_code}",
                        "details": {"status_code": response.status_code}
                    }
        except Exception as e:
            return {
                "valid": False,
                "message": f"Connection error: {str(e)}",
                "details": {"error": str(e)}
            }

    async def _validate_deepseek(self, api_key: str) -> Dict[str, Any]:
        """Validate DeepSeek API key"""
        import httpx

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.deepseek.com/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=10.0
                )

                if response.status_code == 200:
                    return {
                        "valid": True,
                        "message": "DeepSeek API key is valid",
                        "details": {"models_available": len(response.json().get("data", []))}
                    }
                elif response.status_code == 401:
                    return {
                        "valid": False,
                        "message": "Invalid DeepSeek API key",
                        "details": {"status_code": 401}
                    }
                else:
                    return {
                        "valid": False,
                        "message": f"DeepSeek API error: {response.status_code}",
                        "details": {"status_code": response.status_code}
                    }
        except Exception as e:
            return {
                "valid": False,
                "message": f"Connection error: {str(e)}",
                "details": {"error": str(e)}
            }

    async def _validate_perplexity(self, api_key: str) -> Dict[str, Any]:
        """Validate Perplexity API key"""
        import httpx

        try:
            async with httpx.AsyncClient() as client:
                # Perplexity uses OpenAI-compatible API
                response = await client.post(
                    "https://api.perplexity.ai/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "sonar",
                        "messages": [{"role": "user", "content": "test"}],
                        "max_tokens": 1
                    },
                    timeout=10.0
                )

                if response.status_code in [200, 400]:
                    return {
                        "valid": True,
                        "message": "Perplexity API key is valid",
                        "details": {"status_code": response.status_code}
                    }
                elif response.status_code == 401:
                    return {
                        "valid": False,
                        "message": "Invalid Perplexity API key",
                        "details": {"status_code": 401}
                    }
                else:
                    return {
                        "valid": False,
                        "message": f"Perplexity API error: {response.status_code}",
                        "details": {"status_code": response.status_code}
                    }
        except Exception as e:
            return {
                "valid": False,
                "message": f"Connection error: {str(e)}",
                "details": {"error": str(e)}
            }

    async def _validate_pinata(self, jwt_token: str) -> Dict[str, Any]:
        """Validate Pinata JWT token by testing both authentication AND pinning capability"""
        import httpx

        try:
            async with httpx.AsyncClient() as client:
                # Step 1: Test basic authentication
                auth_response = await client.get(
                    "https://api.pinata.cloud/data/testAuthentication",
                    headers={"Authorization": f"Bearer {jwt_token}"},
                    timeout=10.0
                )

                if auth_response.status_code == 401:
                    return {
                        "valid": False,
                        "message": "Invalid Pinata JWT - authentication failed",
                        "details": {"status_code": 401}
                    }
                elif auth_response.status_code != 200:
                    return {
                        "valid": False,
                        "message": f"Pinata authentication error: {auth_response.status_code}",
                        "details": {"status_code": auth_response.status_code}
                    }

                # Step 2: Test pinning capability by uploading a tiny JSON test
                # This catches JWTs that authenticate but lack pinFileToIPFS permission
                test_json = {"test": "qubes_validation", "timestamp": str(datetime.now())}
                pin_response = await client.post(
                    "https://api.pinata.cloud/pinning/pinJSONToIPFS",
                    headers={
                        "Authorization": f"Bearer {jwt_token}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "pinataContent": test_json,
                        "pinataMetadata": {"name": "qubes_test_validation"}
                    },
                    timeout=15.0
                )

                if pin_response.status_code == 200:
                    result = pin_response.json()
                    test_cid = result.get("IpfsHash", "")

                    # Clean up: unpin the test file (optional, ignore errors)
                    try:
                        await client.delete(
                            f"https://api.pinata.cloud/pinning/unpin/{test_cid}",
                            headers={"Authorization": f"Bearer {jwt_token}"},
                            timeout=5.0
                        )
                    except:
                        pass  # Cleanup failure is not critical

                    return {
                        "valid": True,
                        "message": "Pinata JWT is valid (authentication + pinning verified)",
                        "details": {"test_cid": test_cid, "capabilities": ["auth", "pin"]}
                    }
                elif pin_response.status_code == 401:
                    return {
                        "valid": False,
                        "message": "Pinata JWT lacks pinning permission. Regenerate with 'pinFileToIPFS' enabled.",
                        "details": {"status_code": 401, "issue": "missing_pin_permission"}
                    }
                elif pin_response.status_code == 403:
                    return {
                        "valid": False,
                        "message": "Pinata access forbidden. Check your account status or JWT permissions.",
                        "details": {"status_code": 403}
                    }
                elif pin_response.status_code == 429:
                    # Rate limited but key is valid - still pass the test
                    return {
                        "valid": True,
                        "message": "Pinata JWT is valid (rate limited during test, but should work)",
                        "details": {"status_code": 429, "warning": "rate_limited"}
                    }
                else:
                    error_text = pin_response.text[:200] if pin_response.text else "No details"
                    return {
                        "valid": False,
                        "message": f"Pinata pinning test failed ({pin_response.status_code}): {error_text}",
                        "details": {"status_code": pin_response.status_code, "error": error_text}
                    }

        except httpx.TimeoutException:
            return {
                "valid": False,
                "message": "Connection timeout - check your internet connection",
                "details": {"error": "timeout"}
            }
        except Exception as e:
            return {
                "valid": False,
                "message": f"Connection error: {str(e)}",
                "details": {"error": str(e)}
            }

    async def _validate_elevenlabs(self, api_key: str) -> Dict[str, Any]:
        """Validate ElevenLabs API key"""
        import httpx

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.elevenlabs.io/v1/user",
                    headers={"xi-api-key": api_key},
                    timeout=10.0
                )

                if response.status_code == 200:
                    return {
                        "valid": True,
                        "message": "ElevenLabs API key is valid",
                        "details": {"user_id": response.json().get("xi_user_id")}
                    }
                elif response.status_code == 401:
                    return {
                        "valid": False,
                        "message": "Invalid ElevenLabs API key",
                        "details": {"status_code": 401}
                    }
                else:
                    return {
                        "valid": False,
                        "message": f"ElevenLabs API error: {response.status_code}",
                        "details": {"status_code": response.status_code}
                    }
        except Exception as e:
            return {
                "valid": False,
                "message": f"Connection error: {str(e)}",
                "details": {"error": str(e)}
            }

    async def _validate_deepgram(self, api_key: str) -> Dict[str, Any]:
        """Validate Deepgram API key"""
        import httpx

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.deepgram.com/v1/projects",
                    headers={"Authorization": f"Token {api_key}"},
                    timeout=10.0
                )

                if response.status_code == 200:
                    return {
                        "valid": True,
                        "message": "Deepgram API key is valid",
                        "details": {"projects": len(response.json().get("projects", []))}
                    }
                elif response.status_code == 401:
                    return {
                        "valid": False,
                        "message": "Invalid Deepgram API key",
                        "details": {"status_code": 401}
                    }
                else:
                    return {
                        "valid": False,
                        "message": f"Deepgram API error: {response.status_code}",
                        "details": {"status_code": response.status_code}
                    }
        except Exception as e:
            return {
                "valid": False,
                "message": f"Connection error: {str(e)}",
                "details": {"error": str(e)}
            }

    async def _validate_venice(self, api_key: str) -> Dict[str, Any]:
        """Validate Venice.ai API key"""
        import httpx

        try:
            async with httpx.AsyncClient() as client:
                # Venice uses OpenAI-compatible API
                response = await client.get(
                    "https://api.venice.ai/api/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=10.0
                )

                if response.status_code == 200:
                    models = response.json().get("data", [])
                    return {
                        "valid": True,
                        "message": "Venice API key is valid",
                        "details": {"models_available": len(models)}
                    }
                elif response.status_code == 401:
                    return {
                        "valid": False,
                        "message": "Invalid Venice API key",
                        "details": {"status_code": 401}
                    }
                else:
                    return {
                        "valid": False,
                        "message": f"Venice API error: {response.status_code}",
                        "details": {"status_code": response.status_code}
                    }
        except Exception as e:
            return {
                "valid": False,
                "message": f"Connection error: {str(e)}",
                "details": {"error": str(e)}
            }

    async def _validate_nanogpt(self, api_key: str) -> Dict[str, Any]:
        """Validate NanoGPT API key"""
        import httpx

        try:
            async with httpx.AsyncClient() as client:
                # NanoGPT uses OpenAI-compatible API
                response = await client.get(
                    "https://nano-gpt.com/api/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=10.0
                )

                if response.status_code == 200:
                    models = response.json().get("data", [])
                    return {
                        "valid": True,
                        "message": "NanoGPT API key is valid",
                        "details": {"models_available": len(models)}
                    }
                elif response.status_code == 401:
                    return {
                        "valid": False,
                        "message": "Invalid NanoGPT API key",
                        "details": {"status_code": 401}
                    }
                else:
                    return {
                        "valid": False,
                        "message": f"NanoGPT API error: {response.status_code}",
                        "details": {"status_code": response.status_code}
                    }
        except Exception as e:
            return {
                "valid": False,
                "message": f"Connection error: {str(e)}",
                "details": {"error": str(e)}
            }

    def save_wallet_security(self, config: WalletSecurityConfig) -> None:
        """
        Save encrypted wallet security config (owner keys and whitelists).

        Args:
            config: WalletSecurityConfig instance with keys and whitelists

        Raises:
            EncryptionError: If encryption fails
        """
        try:
            # Get encryption key (same pattern as save_api_keys)
            key = self._derive_encryption_key()

            # Convert to JSON
            plaintext = json.dumps(config.to_dict(), sort_keys=True).encode()

            # Encrypt using AES-256-GCM
            aesgcm = AESGCM(key)
            nonce = secrets.token_bytes(12)  # 96-bit nonce for GCM
            ciphertext = aesgcm.encrypt(nonce, plaintext, None)

            # Store nonce + ciphertext
            wallet_file = self.user_data_dir / "wallet_security.enc"
            with open(wallet_file, 'w') as f:
                json.dump({
                    'nonce': nonce.hex(),
                    'ciphertext': ciphertext.hex(),
                    'algorithm': 'AES-256-GCM',
                    'version': '1.0'
                }, f, indent=2)

            logger.info("wallet_security_saved")

        except Exception as e:
            logger.error("wallet_security_save_failed", exc_info=True)
            raise EncryptionError(
                "Failed to save wallet security config",
                context={"file": str(self.user_data_dir / "wallet_security.enc")},
                cause=e
            )

    def load_wallet_security(self) -> WalletSecurityConfig:
        """
        Load and decrypt wallet security config.

        Returns:
            WalletSecurityConfig instance with decrypted keys and whitelists

        Raises:
            DecryptionError: If decryption fails or master password incorrect
        """
        wallet_file = self.user_data_dir / "wallet_security.enc"

        if not wallet_file.exists():
            return WalletSecurityConfig()

        try:
            with open(wallet_file, 'r') as f:
                data = json.load(f)

            # Get encryption key
            key = self._derive_encryption_key()

            # Decrypt using AES-256-GCM
            aesgcm = AESGCM(key)
            nonce = bytes.fromhex(data['nonce'])
            ciphertext = bytes.fromhex(data['ciphertext'])

            plaintext = aesgcm.decrypt(nonce, ciphertext, None)
            config_data = json.loads(plaintext.decode('utf-8'))

            return WalletSecurityConfig.from_dict(config_data)

        except Exception as e:
            logger.error("wallet_security_load_failed", exc_info=True)
            raise DecryptionError(
                "Failed to load wallet security config",
                context={"file": str(wallet_file)},
                cause=e
            )
