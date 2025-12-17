"""
Memory Permission System

Permission-based selective sharing of memory blocks between Qubes.
From docs/07_Shared_Memory_Architecture.md Section 4.1
"""

import uuid
import json
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from enum import Enum

from utils.logging import get_logger
from core.exceptions import QubesError

logger = get_logger(__name__)


class PermissionLevel(Enum):
    """Permission access levels"""
    READ = "read"
    READ_WRITE = "read_write"


class MemoryPermission:
    """Permission to access specific memory blocks"""

    def __init__(
        self,
        granted_by: str,
        granted_to: str,
        permission_id: Optional[str] = None
    ):
        """
        Initialize memory permission

        Args:
            granted_by: Qube ID who owns the memory
            granted_to: Qube ID who receives access
            permission_id: Optional UUID (generated if not provided)
        """
        self.permission_id = permission_id or str(uuid.uuid4())
        self.granted_by = granted_by
        self.granted_to = granted_to
        self.granted_blocks: List[int] = []
        self.permission_level = PermissionLevel.READ
        self.expiry_timestamp: Optional[datetime] = None
        self.revoked = False
        self.created_at = datetime.now()
        self.signature: Optional[str] = None

        logger.debug(
            "permission_created",
            permission_id=self.permission_id,
            granted_by=granted_by,
            granted_to=granted_to
        )

    def grant_access(
        self,
        block_numbers: List[int],
        permission_level: PermissionLevel = PermissionLevel.READ,
        expiry_days: Optional[int] = None
    ):
        """
        Grant access to specific blocks

        Args:
            block_numbers: List of block numbers to grant access to
            permission_level: READ or READ_WRITE
            expiry_days: Optional expiry in days (None = permanent)
        """
        self.granted_blocks.extend(block_numbers)
        self.permission_level = permission_level

        if expiry_days:
            self.expiry_timestamp = datetime.now() + timedelta(days=expiry_days)

        logger.info(
            "access_granted",
            permission_id=self.permission_id,
            blocks=len(block_numbers),
            level=permission_level.value,
            expiry=self.expiry_timestamp.isoformat() if self.expiry_timestamp else None
        )

    def revoke_access(self):
        """Revoke all access"""
        self.revoked = True
        logger.info("access_revoked", permission_id=self.permission_id)

    def is_expired(self) -> bool:
        """Check if permission has expired"""
        if self.expiry_timestamp is None:
            return False
        return datetime.now() > self.expiry_timestamp

    def is_valid(self) -> bool:
        """Check if permission is valid (not revoked or expired)"""
        if self.revoked:
            return False
        if self.is_expired():
            return False
        return True

    def can_access_block(self, block_number: int) -> bool:
        """
        Check if permission allows access to a specific block

        Args:
            block_number: Block number to check

        Returns:
            True if access is allowed, False otherwise
        """
        if not self.is_valid():
            return False
        return block_number in self.granted_blocks

    def sign_permission(self, private_key_path: Path):
        """
        Sign permission with granter's private key

        Args:
            private_key_path: Path to granter's private key
        """
        from crypto.signing import sign_data

        permission_data = {
            "permission_id": self.permission_id,
            "granted_by": self.granted_by,
            "granted_to": self.granted_to,
            "granted_blocks": self.granted_blocks,
            "permission_level": self.permission_level.value,
            "expiry_timestamp": self.expiry_timestamp.isoformat() if self.expiry_timestamp else None,
            "revoked": self.revoked,
            "created_at": self.created_at.isoformat()
        }

        data_str = json.dumps(permission_data, sort_keys=True)
        self.signature = sign_data(data_str.encode(), private_key_path)

        logger.debug("permission_signed", permission_id=self.permission_id)

    def verify_signature(self, public_key: bytes) -> bool:
        """
        Verify permission signature

        Args:
            public_key: Granter's public key

        Returns:
            True if signature is valid, False otherwise
        """
        from crypto.signing import verify_signature

        if not self.signature:
            return False

        permission_data = {
            "permission_id": self.permission_id,
            "granted_by": self.granted_by,
            "granted_to": self.granted_to,
            "granted_blocks": self.granted_blocks,
            "permission_level": self.permission_level.value,
            "expiry_timestamp": self.expiry_timestamp.isoformat() if self.expiry_timestamp else None,
            "revoked": self.revoked,
            "created_at": self.created_at.isoformat()
        }

        data_str = json.dumps(permission_data, sort_keys=True)
        is_valid = verify_signature(data_str.encode(), self.signature, public_key)

        logger.debug(
            "permission_signature_verified",
            permission_id=self.permission_id,
            is_valid=is_valid
        )

        return is_valid

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "permission_id": self.permission_id,
            "granted_by": self.granted_by,
            "granted_to": self.granted_to,
            "granted_blocks": self.granted_blocks,
            "permission_level": self.permission_level.value,
            "expiry_timestamp": self.expiry_timestamp.isoformat() if self.expiry_timestamp else None,
            "revoked": self.revoked,
            "created_at": self.created_at.isoformat(),
            "signature": self.signature
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryPermission":
        """Deserialize from dictionary"""
        permission = cls(
            granted_by=data["granted_by"],
            granted_to=data["granted_to"],
            permission_id=data["permission_id"]
        )

        permission.granted_blocks = data["granted_blocks"]
        permission.permission_level = PermissionLevel(data["permission_level"])
        permission.revoked = data["revoked"]
        permission.created_at = datetime.fromisoformat(data["created_at"])
        permission.signature = data.get("signature")

        if data.get("expiry_timestamp"):
            permission.expiry_timestamp = datetime.fromisoformat(data["expiry_timestamp"])

        return permission


class PermissionManager:
    """Manages memory permissions for a Qube"""

    def __init__(self, qube_data_dir: Path):
        """
        Initialize permission manager

        Args:
            qube_data_dir: Path to Qube's data directory
        """
        self.qube_data_dir = Path(qube_data_dir)
        self.permissions_file = self.qube_data_dir / "shared_permissions.json"
        self.permissions: Dict[str, MemoryPermission] = {}

        # Create data directory if needed
        self.qube_data_dir.mkdir(parents=True, exist_ok=True)

        # Load existing permissions
        self.load_permissions()

        logger.info(
            "permission_manager_initialized",
            qube_dir=str(qube_data_dir),
            permissions_count=len(self.permissions)
        )

    def create_permission(
        self,
        granted_to: str,
        block_numbers: List[int],
        granted_by: str,
        permission_level: PermissionLevel = PermissionLevel.READ,
        expiry_days: Optional[int] = None
    ) -> MemoryPermission:
        """
        Create a new permission

        Args:
            granted_to: Qube ID to grant access to
            block_numbers: List of block numbers
            granted_by: Qube ID granting access
            permission_level: READ or READ_WRITE
            expiry_days: Optional expiry in days

        Returns:
            Created MemoryPermission
        """
        permission = MemoryPermission(granted_by=granted_by, granted_to=granted_to)
        permission.grant_access(block_numbers, permission_level, expiry_days)

        self.permissions[permission.permission_id] = permission
        self.save_permissions()

        logger.info(
            "permission_created",
            permission_id=permission.permission_id,
            granted_to=granted_to,
            blocks=len(block_numbers)
        )

        return permission

    def get_permission(self, permission_id: str) -> Optional[MemoryPermission]:
        """Get permission by ID"""
        return self.permissions.get(permission_id)

    def get_permissions_for_qube(self, qube_id: str) -> List[MemoryPermission]:
        """
        Get all permissions granted to a specific Qube

        Args:
            qube_id: Qube ID

        Returns:
            List of MemoryPermission objects
        """
        return [
            p for p in self.permissions.values()
            if p.granted_to == qube_id and p.is_valid()
        ]

    def get_permissions_by_granter(self, qube_id: str) -> List[MemoryPermission]:
        """
        Get all permissions granted by a specific Qube

        Args:
            qube_id: Qube ID

        Returns:
            List of MemoryPermission objects
        """
        return [
            p for p in self.permissions.values()
            if p.granted_by == qube_id
        ]

    def revoke_permission(self, permission_id: str):
        """
        Revoke a permission

        Args:
            permission_id: Permission ID to revoke
        """
        permission = self.permissions.get(permission_id)
        if permission:
            permission.revoke_access()
            self.save_permissions()

    def can_access_block(self, qube_id: str, block_number: int) -> bool:
        """
        Check if a Qube can access a specific block

        Args:
            qube_id: Qube ID requesting access
            block_number: Block number

        Returns:
            True if access is allowed, False otherwise
        """
        for permission in self.get_permissions_for_qube(qube_id):
            if permission.can_access_block(block_number):
                return True
        return False

    def cleanup_expired_permissions(self):
        """Remove expired permissions"""
        before_count = len(self.permissions)

        self.permissions = {
            pid: p for pid, p in self.permissions.items()
            if not p.is_expired() or not p.revoked
        }

        removed_count = before_count - len(self.permissions)

        if removed_count > 0:
            self.save_permissions()
            logger.info("expired_permissions_cleaned", removed=removed_count)

    def save_permissions(self):
        """Save permissions to disk"""
        try:
            data = {
                pid: p.to_dict() for pid, p in self.permissions.items()
            }

            with open(self.permissions_file, "w") as f:
                json.dump(data, f, indent=2)

            logger.debug(
                "permissions_saved",
                file=str(self.permissions_file),
                count=len(data)
            )

        except Exception as e:
            logger.error("permissions_save_failed", error=str(e), exc_info=True)
            raise QubesError(f"Failed to save permissions: {e}", cause=e)

    def load_permissions(self):
        """Load permissions from disk"""
        try:
            if not self.permissions_file.exists():
                logger.debug("permissions_file_not_found", creating_new=True)
                self.permissions = {}
                return

            with open(self.permissions_file, "r") as f:
                data = json.load(f)

            self.permissions = {
                pid: MemoryPermission.from_dict(p_data)
                for pid, p_data in data.items()
            }

            logger.info(
                "permissions_loaded",
                file=str(self.permissions_file),
                count=len(self.permissions)
            )

        except Exception as e:
            logger.error("permissions_load_failed", error=str(e), exc_info=True)
            self.permissions = {}

    def get_stats(self) -> Dict[str, Any]:
        """
        Get permission statistics

        Returns:
            Statistics dictionary
        """
        total = len(self.permissions)
        valid = len([p for p in self.permissions.values() if p.is_valid()])
        revoked = len([p for p in self.permissions.values() if p.revoked])
        expired = len([p for p in self.permissions.values() if p.is_expired()])

        return {
            "total_permissions": total,
            "valid_permissions": valid,
            "revoked_permissions": revoked,
            "expired_permissions": expired,
            "read_only": len([p for p in self.permissions.values() if p.permission_level == PermissionLevel.READ]),
            "read_write": len([p for p in self.permissions.values() if p.permission_level == PermissionLevel.READ_WRITE])
        }
