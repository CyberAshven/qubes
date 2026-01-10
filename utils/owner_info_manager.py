"""
Owner Info Manager - Handles personal information storage for Qube owners

Storage Structure:
    data/users/{user_id}/qubes/{qube_id}/owner_info/
        owner_info.json - Encrypted owner information (AES-256-GCM)

Owner Info System Design:
    - Stores personal information about the Qube's owner
    - Hybrid structure: standard fields + dynamic fields
    - Sensitivity tiers: public, private, secret
    - Secret fields are NEVER injected into AI context
    - Encrypted at rest using same key derivation as blocks

Integration Points:
    - Context Injection: Injected into AI system prompt based on chat context
    - AI Tool: remember_about_owner tool for Qube to store info
    - Active Context Panel: Displayed in Block Browser UI
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import structlog

from crypto.encryption import encrypt_block_data, decrypt_block_data
from core.exceptions import EncryptionError, DecryptionError

logger = structlog.get_logger(__name__)

# Field limits
MAX_FIELD_VALUE_LENGTH = 1000    # Max chars per field value
MAX_DYNAMIC_FIELDS = 50          # Max dynamic fields
MAX_FIELDS_IN_CONTEXT = 30       # Max fields injected to AI context

# Default sensitivity levels for standard fields
DEFAULT_SENSITIVITIES = {
    # Standard fields
    "name": "public",
    "nickname": "public",
    "birthday": "private",
    "location_city": "private",
    "location_country": "private",
    "occupation": "public",
    "timezone": "public",
    # Physical fields
    "eye_color": "public",
    "hair_color": "public",
    "height": "public",
    "distinguishing_features": "public",
    # Preference fields
    "favorite_color": "public",
    "favorite_food": "public",
    "favorite_music": "public",
    "favorite_movie": "public",
    "hobbies": "public",
    "dislikes": "public",
    # People fields
    "family_members": "private",
    "pets": "private",
    "significant_other": "private",
    # Date fields
    "anniversary": "private",
    "important_dates": "private",
}


class OwnerInfoManager:
    """Manages owner information storage and retrieval for a Qube."""

    def __init__(self, qube_dir: Path, encryption_key: bytes = None):
        """
        Initialize OwnerInfoManager for a specific qube.

        Args:
            qube_dir: Path to qube's data directory
            encryption_key: 32-byte AES key for encryption (derived from Qube's private key)
        """
        self.qube_dir = qube_dir
        self.owner_info_dir = qube_dir / "owner_info"
        self.owner_info_file = self.owner_info_dir / "owner_info.json"
        self.encryption_key = encryption_key

        # Ensure owner_info directory exists
        self.owner_info_dir.mkdir(exist_ok=True)

    def load(self) -> Dict[str, Any]:
        """
        Load owner info from owner_info.json.

        Returns:
            Dictionary containing owner info data, or empty structure if not found.
        """
        if not self.owner_info_file.exists():
            logger.info("owner_info_not_found", path=str(self.owner_info_file))
            return self._initialize_empty()

        try:
            with open(self.owner_info_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Check if file is encrypted (has ciphertext field)
            if "ciphertext" in data:
                if not self.encryption_key:
                    raise EncryptionError("Encryption key required to read owner info")
                decrypted = decrypt_block_data(data, self.encryption_key)
                logger.debug("owner_info_loaded_encrypted", path=str(self.owner_info_file))
                return decrypted
            else:
                # Legacy unencrypted format - will be encrypted on next save
                logger.warning("owner_info_loaded_unencrypted", path=str(self.owner_info_file))
                return data

        except (EncryptionError, DecryptionError) as e:
            logger.error("owner_info_decryption_failed", error=str(e))
            raise
        except Exception as e:
            logger.error("owner_info_load_failed", error=str(e), exc_info=True)
            return self._initialize_empty()

    def save(self, owner_info: Dict[str, Any]) -> bool:
        """
        Save owner info to owner_info.json (encrypted).

        Args:
            owner_info: Dictionary containing owner info data

        Returns:
            True if successful, False otherwise
        """
        try:
            # Update timestamp
            owner_info["last_updated"] = datetime.utcnow().isoformat() + "Z"

            if self.encryption_key:
                # Encrypt and save
                encrypted = encrypt_block_data(owner_info, self.encryption_key)
                with open(self.owner_info_file, 'w', encoding='utf-8') as f:
                    json.dump(encrypted, f, indent=2)
                logger.info("owner_info_saved_encrypted", path=str(self.owner_info_file))
            else:
                # Fallback to unencrypted (not recommended for production)
                logger.warning("owner_info_saving_unencrypted", path=str(self.owner_info_file))
                with open(self.owner_info_file, 'w', encoding='utf-8') as f:
                    json.dump(owner_info, f, indent=2, ensure_ascii=False)

            return True

        except Exception as e:
            logger.error("owner_info_save_failed", error=str(e), exc_info=True)
            return False

    def _initialize_empty(self) -> Dict[str, Any]:
        """Return empty owner info structure."""
        return {
            "created_at": datetime.utcnow().isoformat() + "Z",
            "last_updated": datetime.utcnow().isoformat() + "Z",
            "standard": {},
            "physical": {},
            "preferences": {},
            "people": {},
            "dates": {},
            "dynamic": []
        }

    def _create_field(
        self,
        key: str,
        value: str,
        sensitivity: str = "private",
        source: str = "explicit",
        confidence: int = 100,
        block_id: str = None
    ) -> Dict[str, Any]:
        """Create a new field dictionary."""
        # Validate and truncate value
        if len(value) > MAX_FIELD_VALUE_LENGTH:
            value = value[:MAX_FIELD_VALUE_LENGTH]
            logger.warning("owner_info_field_truncated", key=key, max_length=MAX_FIELD_VALUE_LENGTH)

        # Validate sensitivity
        if sensitivity not in ("public", "private", "secret"):
            sensitivity = "private"

        return {
            "key": key,
            "value": value,
            "sensitivity": sensitivity,
            "source": source,
            "confidence": min(100, max(0, confidence)),
            "learned_at": datetime.utcnow().isoformat() + "Z",
            "block_id": block_id,
            "last_confirmed": None
        }

    def get_field(self, category: str, key: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific field.

        Args:
            category: Field category (standard, physical, preferences, people, dates, dynamic)
            key: Field key

        Returns:
            Field dictionary or None if not found
        """
        owner_info = self.load()

        if category == "dynamic":
            for field in owner_info.get("dynamic", []):
                if field.get("key") == key:
                    return field
            return None
        else:
            return owner_info.get(category, {}).get(key)

    def set_field(
        self,
        category: str,
        key: str,
        value: str,
        sensitivity: str = None,
        source: str = "explicit",
        confidence: int = 100,
        block_id: str = None
    ) -> bool:
        """
        Set or update a field.

        Args:
            category: Field category
            key: Field key
            value: Field value
            sensitivity: Sensitivity level (public/private/secret), uses default if None
            source: How info was obtained (explicit/inferred)
            confidence: Confidence level 0-100
            block_id: Evidence block ID

        Returns:
            True if successful
        """
        owner_info = self.load()

        # Use default sensitivity if not provided
        if sensitivity is None:
            sensitivity = DEFAULT_SENSITIVITIES.get(key, "private")

        field = self._create_field(key, value, sensitivity, source, confidence, block_id)

        if category == "dynamic":
            # Check limit
            dynamic_fields = owner_info.get("dynamic", [])
            if len(dynamic_fields) >= MAX_DYNAMIC_FIELDS:
                # Check if updating existing
                existing_idx = None
                for idx, f in enumerate(dynamic_fields):
                    if f.get("key") == key:
                        existing_idx = idx
                        break

                if existing_idx is None:
                    logger.warning("owner_info_max_dynamic_fields", max=MAX_DYNAMIC_FIELDS)
                    return False

                dynamic_fields[existing_idx] = field
            else:
                # Update existing or add new
                found = False
                for idx, f in enumerate(dynamic_fields):
                    if f.get("key") == key:
                        dynamic_fields[idx] = field
                        found = True
                        break
                if not found:
                    dynamic_fields.append(field)

            owner_info["dynamic"] = dynamic_fields
        else:
            # Standard category field
            if category not in owner_info:
                owner_info[category] = {}
            owner_info[category][key] = field

        logger.info("owner_info_field_set", category=category, key=key, sensitivity=sensitivity)
        return self.save(owner_info)

    def delete_field(self, category: str, key: str) -> bool:
        """
        Delete a field.

        Args:
            category: Field category
            key: Field key

        Returns:
            True if deleted, False if not found
        """
        owner_info = self.load()

        if category == "dynamic":
            dynamic_fields = owner_info.get("dynamic", [])
            original_len = len(dynamic_fields)
            owner_info["dynamic"] = [f for f in dynamic_fields if f.get("key") != key]
            if len(owner_info["dynamic"]) == original_len:
                return False
        else:
            if category not in owner_info or key not in owner_info.get(category, {}):
                return False
            del owner_info[category][key]

        logger.info("owner_info_field_deleted", category=category, key=key)
        return self.save(owner_info)

    def update_sensitivity(self, category: str, key: str, sensitivity: str) -> bool:
        """
        Update the sensitivity level of a field.

        Args:
            category: Field category
            key: Field key
            sensitivity: New sensitivity level

        Returns:
            True if updated, False if not found
        """
        if sensitivity not in ("public", "private", "secret"):
            return False

        owner_info = self.load()

        if category == "dynamic":
            for field in owner_info.get("dynamic", []):
                if field.get("key") == key:
                    field["sensitivity"] = sensitivity
                    return self.save(owner_info)
            return False
        else:
            if category not in owner_info or key not in owner_info.get(category, {}):
                return False
            owner_info[category][key]["sensitivity"] = sensitivity
            return self.save(owner_info)

    def get_all_fields(self) -> List[Dict[str, Any]]:
        """
        Get all fields across all categories as a flat list.

        Returns:
            List of field dictionaries with category attached
        """
        owner_info = self.load()
        fields = []

        for category in ["standard", "physical", "preferences", "people", "dates"]:
            for key, field in owner_info.get(category, {}).items():
                field_copy = field.copy()
                field_copy["category"] = category
                fields.append(field_copy)

        for field in owner_info.get("dynamic", []):
            field_copy = field.copy()
            field_copy["category"] = "dynamic"
            fields.append(field_copy)

        return fields

    def get_fields_by_sensitivity(self, sensitivity: str) -> List[Dict[str, Any]]:
        """Get all fields with a specific sensitivity level."""
        return [f for f in self.get_all_fields() if f.get("sensitivity") == sensitivity]

    def get_injectable_fields(self, is_public_chat: bool) -> List[Dict[str, Any]]:
        """
        Get fields appropriate for injection into AI context.

        Args:
            is_public_chat: If True, only return public fields.
                           If False, return public + private fields.
                           Secret fields are NEVER returned.

        Returns:
            List of field dictionaries, limited to MAX_FIELDS_IN_CONTEXT
        """
        all_fields = self.get_all_fields()

        if is_public_chat:
            # Only public fields
            filtered = [f for f in all_fields if f.get("sensitivity") == "public"]
        else:
            # Public and private fields (never secret)
            filtered = [f for f in all_fields if f.get("sensitivity") in ("public", "private")]

        # Sort by confidence (highest first) and limit
        filtered.sort(key=lambda f: f.get("confidence", 0), reverse=True)
        return filtered[:MAX_FIELDS_IN_CONTEXT]

    def get_fields_for_entity(
        self,
        entity_id: str,
        relationship: Optional['Relationship'] = None,
        is_owner: bool = False,
        audit_log: Optional['ClearanceAuditLog'] = None,
        clearance_config: Optional['ClearanceConfig'] = None
    ) -> List[Dict[str, Any]]:
        """
        Get owner info fields accessible to a specific entity.

        Uses clearance profiles and per-entity overrides to filter fields.
        Owner always gets all fields (except secret in AI context).

        Args:
            entity_id: Who is requesting access
            relationship: The entity's Relationship object (if known)
            is_owner: If True, returns all non-secret fields
            audit_log: Optional audit logger for tracking access
            clearance_config: Optional ClearanceConfig for custom profiles

        Returns:
            List of accessible field dictionaries
        """
        all_fields = self.get_all_fields()

        # Owner gets everything except secret (which is never in AI context)
        if is_owner:
            accessible = [f for f in all_fields if f.get("sensitivity") != "secret"]

            # Log owner access if auditing
            if audit_log:
                for field in accessible:
                    audit_log.log_access(
                        entity_id=entity_id,
                        field_key=field.get("key", ""),
                        field_category=field.get("category", "dynamic"),
                        clearance_level="owner",
                        access_granted=True,
                        context="owner_access"
                    )

            return accessible

        # No relationship = no access
        if not relationship:
            return []

        # Blocked entities get nothing
        if relationship.status == "blocked":
            return []

        # Filter by clearance using profile system
        accessible = []
        for field in all_fields:
            field_key = field.get("key", "")
            sensitivity = field.get("sensitivity", "private")
            category = field.get("category", "dynamic")

            # Secret fields are NEVER accessible through clearance
            if sensitivity == "secret":
                continue

            # Pass config to can_access_owner_field for profile resolution
            granted = relationship.can_access_owner_field(
                field_key, sensitivity, category, clearance_config
            )

            # Log the access attempt if auditing
            if audit_log:
                audit_log.log_access(
                    entity_id=entity_id,
                    field_key=field_key,
                    field_category=category,
                    clearance_level=relationship.clearance_profile,
                    access_granted=granted,
                    context=f"status:{relationship.status}"
                )

            if granted:
                accessible.append(field)

        return accessible

    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics for Active Context display.

        Returns:
            Dictionary with counts and top fields
        """
        all_fields = self.get_all_fields()
        owner_info = self.load()

        public_count = len([f for f in all_fields if f.get("sensitivity") == "public"])
        private_count = len([f for f in all_fields if f.get("sensitivity") == "private"])
        secret_count = len([f for f in all_fields if f.get("sensitivity") == "secret"])

        # Count populated categories
        categories_populated = 0
        for category in ["standard", "physical", "preferences", "people", "dates"]:
            if owner_info.get(category):
                categories_populated += 1
        if owner_info.get("dynamic"):
            categories_populated += 1

        # Get all fields with category info for full display in UI
        top_fields = [
            {
                "key": f["key"],
                "value": f["value"][:200],  # Allow longer values for detail view
                "sensitivity": f["sensitivity"],
                "category": f.get("category", "dynamic")
            }
            for f in sorted(
                all_fields,
                key=lambda x: (
                    # Sort order: private first, then public, then secret
                    0 if x.get("sensitivity") == "private" else
                    1 if x.get("sensitivity") == "public" else 2,
                    -x.get("confidence", 0)  # Higher confidence first within each group
                )
            )
        ]

        return {
            "total_fields": len(all_fields),
            "public_fields": public_count,
            "private_fields": private_count,
            "secret_fields": secret_count,
            "categories_populated": categories_populated,
            "last_updated": owner_info.get("last_updated"),
            "top_fields": top_fields
        }

    def clear(self) -> bool:
        """
        Clear all owner info (used during ownership transfer).

        Returns:
            True if cleared successfully
        """
        try:
            if self.owner_info_file.exists():
                self.owner_info_file.unlink()
                logger.info("owner_info_cleared", path=str(self.owner_info_file))
            return True
        except Exception as e:
            logger.error("owner_info_clear_failed", error=str(e))
            return False
