"""
Clearance Audit Log

Tracks all owner info access for security review.
"""

import json
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime, timezone

from utils.logging import get_logger

logger = get_logger(__name__)


class ClearanceAuditLog:
    """Tracks owner info access events."""

    def __init__(self, qube_dir: Path):
        self.qube_dir = qube_dir
        self.audit_dir = qube_dir / "audit"
        self.audit_dir.mkdir(exist_ok=True)
        self.audit_file = self.audit_dir / "clearance_access.jsonl"

    def log_access(
        self,
        entity_id: str,
        field_key: str,
        field_category: str,
        clearance_level: str,
        access_granted: bool,
        context: str = None
    ) -> None:
        """Log an access attempt."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "entity_id": entity_id,
            "field_key": field_key,
            "field_category": field_category,
            "clearance_level": clearance_level,
            "access_granted": access_granted,
            "context": context,
        }

        with open(self.audit_file, 'a') as f:
            f.write(json.dumps(entry) + "\n")

    def get_recent_access(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent access log entries."""
        if not self.audit_file.exists():
            return []

        entries = []
        with open(self.audit_file, 'r') as f:
            for line in f:
                if line.strip():
                    entries.append(json.loads(line))

        return entries[-limit:]

    def get_access_by_entity(self, entity_id: str) -> List[Dict[str, Any]]:
        """Get all access by a specific entity."""
        return [
            e for e in self.get_recent_access(1000)
            if e.get("entity_id") == entity_id
        ]
