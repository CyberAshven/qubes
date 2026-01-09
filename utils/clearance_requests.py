"""
Clearance Request System

Allows other Qubes to request clearance to owner information.
Owner receives notification and can approve/deny.
"""

import json
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from enum import Enum

from utils.logging import get_logger

logger = get_logger(__name__)


class RequestStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"


class ClearanceRequest:
    """A request for clearance from another entity."""

    def __init__(
        self,
        requester_id: str,
        requester_name: str,
        requested_level: str,
        requested_categories: List[str] = None,
        reason: str = None,
        expires_in_days: int = 7
    ):
        self.request_id = f"req-{uuid.uuid4()}"
        self.requester_id = requester_id
        self.requester_name = requester_name
        self.requested_level = requested_level
        self.requested_categories = requested_categories or []
        self.reason = reason
        self.status = RequestStatus.PENDING
        self.created_at = int(datetime.now(timezone.utc).timestamp())
        self.expires_at = self.created_at + (expires_in_days * 86400)
        self.resolved_at: Optional[int] = None
        self.resolved_by: Optional[str] = None
        self.denial_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "requester_id": self.requester_id,
            "requester_name": self.requester_name,
            "requested_level": self.requested_level,
            "requested_categories": self.requested_categories,
            "reason": self.reason,
            "status": self.status.value,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "resolved_at": self.resolved_at,
            "resolved_by": self.resolved_by,
            "denial_reason": self.denial_reason,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ClearanceRequest':
        req = cls(
            requester_id=data["requester_id"],
            requester_name=data.get("requester_name", data["requester_id"]),
            requested_level=data["requested_level"],
            requested_categories=data.get("requested_categories", []),
            reason=data.get("reason"),
        )
        req.request_id = data["request_id"]
        req.status = RequestStatus(data.get("status", "pending"))
        req.created_at = data.get("created_at", req.created_at)
        req.expires_at = data.get("expires_at", req.expires_at)
        req.resolved_at = data.get("resolved_at")
        req.resolved_by = data.get("resolved_by")
        req.denial_reason = data.get("denial_reason")
        return req


class ClearanceRequestManager:
    """Manages clearance requests for a Qube."""

    def __init__(self, qube_dir: Path):
        self.qube_dir = Path(qube_dir)
        self.requests_dir = self.qube_dir / "clearance_requests"
        self.requests_dir.mkdir(exist_ok=True)
        self.requests_file = self.requests_dir / "requests.json"

        self.requests: Dict[str, ClearanceRequest] = self._load_requests()

    def _load_requests(self) -> Dict[str, ClearanceRequest]:
        if self.requests_file.exists():
            try:
                with open(self.requests_file, 'r') as f:
                    data = json.load(f)
                return {
                    rid: ClearanceRequest.from_dict(rdata)
                    for rid, rdata in data.items()
                }
            except Exception as e:
                logger.error("clearance_requests_load_failed", error=str(e))
                return {}
        return {}

    def _save_requests(self) -> None:
        try:
            with open(self.requests_file, 'w') as f:
                data = {rid: req.to_dict() for rid, req in self.requests.items()}
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error("clearance_requests_save_failed", error=str(e))

    def create_request(
        self,
        requester_id: str,
        requester_name: str,
        level: str,
        categories: List[str] = None,
        reason: str = None
    ) -> ClearanceRequest:
        """Create a new clearance request."""
        req = ClearanceRequest(
            requester_id=requester_id,
            requester_name=requester_name,
            requested_level=level,
            requested_categories=categories,
            reason=reason
        )

        self.requests[req.request_id] = req
        self._save_requests()

        logger.info(
            "clearance_request_created",
            request_id=req.request_id,
            requester=requester_id,
            level=level
        )

        return req

    def approve_request(
        self,
        request_id: str,
        approved_by: str = "owner"
    ) -> Optional[ClearanceRequest]:
        """Approve a pending request."""
        if request_id not in self.requests:
            return None

        req = self.requests[request_id]
        if req.status != RequestStatus.PENDING:
            return None

        req.status = RequestStatus.APPROVED
        req.resolved_at = int(datetime.now(timezone.utc).timestamp())
        req.resolved_by = approved_by

        self._save_requests()

        logger.info(
            "clearance_request_approved",
            request_id=request_id,
            approved_by=approved_by
        )

        return req

    def deny_request(
        self,
        request_id: str,
        denied_by: str = "owner",
        reason: str = None
    ) -> Optional[ClearanceRequest]:
        """Deny a pending request."""
        if request_id not in self.requests:
            return None

        req = self.requests[request_id]
        if req.status != RequestStatus.PENDING:
            return None

        req.status = RequestStatus.DENIED
        req.resolved_at = int(datetime.now(timezone.utc).timestamp())
        req.resolved_by = denied_by
        req.denial_reason = reason

        self._save_requests()

        logger.info(
            "clearance_request_denied",
            request_id=request_id,
            denied_by=denied_by,
            reason=reason
        )

        return req

    def get_pending_requests(self) -> List[ClearanceRequest]:
        """Get all pending requests, expiring any that have timed out."""
        now = int(datetime.now(timezone.utc).timestamp())
        pending = []
        expired_count = 0

        for req in self.requests.values():
            if req.status == RequestStatus.PENDING:
                if now > req.expires_at:
                    req.status = RequestStatus.EXPIRED
                    expired_count += 1
                else:
                    pending.append(req)

        if expired_count > 0:
            self._save_requests()
            logger.info("clearance_requests_expired", count=expired_count)

        return pending

    def get_request(self, request_id: str) -> Optional[ClearanceRequest]:
        """Get a specific request by ID."""
        return self.requests.get(request_id)

    def get_requests_by_requester(self, requester_id: str) -> List[ClearanceRequest]:
        """Get all requests from a specific requester."""
        return [
            req for req in self.requests.values()
            if req.requester_id == requester_id
        ]

    def get_all_requests(self) -> List[ClearanceRequest]:
        """Get all requests."""
        return list(self.requests.values())
