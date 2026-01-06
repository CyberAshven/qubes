"""
Wallet Transaction Manager

Manages Qube wallet transactions including:
- Qube proposing transactions (needs owner approval)
- Owner approving/rejecting proposed transactions
- Owner withdrawing directly (no Qube involvement)
- Transaction history and pending transaction storage
"""

import json
import time
import hashlib
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Literal
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

from crypto.wallet import QubeWallet, TxOutput, validate_address
from crypto.bch_script import pubkey_from_privkey, UTXO, address_to_script_pubkey
from crypto.keys import get_raw_private_key_bytes
from utils.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class PendingTx:
    """A transaction proposed by the Qube, awaiting owner approval"""
    tx_id: str                              # Unique transaction ID
    qube_id: str                            # Which Qube proposed this
    outputs: List[Dict[str, Any]]           # [{address, value}, ...]
    total_amount: int                       # Total output amount in sats
    fee: int                                # Transaction fee in sats
    qube_signature_hex: str                 # Qube's signature (hex)
    utxos: List[Dict[str, Any]]             # UTXOs being spent
    redeem_script_hex: str                  # Redeem script (hex)
    created_at: float                       # Unix timestamp
    expires_at: float                       # Unix timestamp
    memo: Optional[str] = None              # Qube's reason for the transaction
    status: Literal["pending", "approved", "rejected", "expired", "broadcast"] = "pending"
    broadcast_txid: Optional[str] = None    # Set when broadcast succeeds

    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def time_remaining(self) -> int:
        """Seconds until expiry"""
        return max(0, int(self.expires_at - time.time()))

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PendingTx":
        return cls(**data)


@dataclass
class TxHistoryEntry:
    """A completed transaction in the wallet's history"""
    txid: str
    tx_type: Literal["deposit", "withdrawal", "qube_spend"]
    amount: int                     # In satoshis (positive for deposit, negative for spend)
    fee: int                        # Fee paid (0 for deposits)
    counterparty: Optional[str]     # Address sent to/from
    timestamp: float                # Unix timestamp
    block_height: Optional[int]     # None if unconfirmed
    memo: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# =============================================================================
# WALLET TRANSACTION MANAGER
# =============================================================================

class WalletTransactionManager:
    """
    Manages transactions for a Qube's wallet.

    Handles the full lifecycle:
    1. Qube proposes a transaction
    2. Transaction is stored as pending
    3. Owner reviews and approves/rejects
    4. If approved, transaction is broadcast
    5. Transaction history is updated
    """

    # Pending transactions expire after 24 hours
    DEFAULT_EXPIRY_HOURS = 24

    def __init__(self, qube, data_dir: Optional[Path] = None):
        """
        Initialize transaction manager for a Qube.

        Args:
            qube: Qube instance with wallet info in genesis block
            data_dir: Directory to store pending transactions (defaults to qube's data dir)
        """
        self.qube = qube
        self.qube_id = qube.qube_id

        # Get wallet info from genesis block (handle both Block and SimpleNamespace)
        if not qube.genesis_block:
            raise ValueError(f"Qube {qube.qube_id} does not have genesis block")

        # Handle both Block objects (with .content dict) and SimpleNamespace (from dict)
        genesis = qube.genesis_block
        if hasattr(genesis, 'content') and isinstance(genesis.content, dict):
            wallet_info = genesis.content.get("wallet")
        elif hasattr(genesis, 'wallet'):
            wallet_info = genesis.wallet
            # Convert SimpleNamespace to dict if needed
            if hasattr(wallet_info, '__dict__') and not isinstance(wallet_info, dict):
                wallet_info = vars(wallet_info)
        else:
            wallet_info = None

        if not wallet_info:
            raise ValueError(f"Qube {qube.qube_id} does not have wallet info in genesis block")

        self.owner_pubkey = wallet_info.get("owner_pubkey")
        self.p2sh_address = wallet_info.get("p2sh_address")

        if not self.owner_pubkey or not self.p2sh_address:
            raise ValueError(f"Qube {qube.qube_id} has incomplete wallet info")

        # Create wallet instance (use raw 32-byte private key, not PEM format)
        private_key_bytes = get_raw_private_key_bytes(qube.private_key)
        self.wallet = QubeWallet(
            qube_private_key=private_key_bytes,
            owner_pubkey_hex=self.owner_pubkey,
            network="mainnet"
        )

        # Storage directory
        self.data_dir = data_dir or Path(qube.qube_dir)
        self.pending_tx_file = self.data_dir / "pending_transactions.json"
        self.tx_history_file = self.data_dir / "transaction_history.json"

        # In-memory cache
        self._pending_txs: Dict[str, PendingTx] = {}
        self._load_pending_transactions()

        logger.debug(
            "wallet_tx_manager_initialized",
            qube_id=self.qube_id,
            p2sh_address=self.p2sh_address
        )

    # =========================================================================
    # BALANCE & INFO
    # =========================================================================

    async def get_balance(self) -> int:
        """Get wallet balance in satoshis"""
        return await self.wallet.get_balance()

    async def get_utxos(self) -> List[UTXO]:
        """Get available UTXOs"""
        return await self.wallet.get_utxos()

    async def get_wallet_info(self) -> Dict[str, Any]:
        """Get comprehensive wallet information"""
        info = await self.wallet.get_wallet_info()
        info["pending_tx_count"] = len(self.get_pending_transactions())
        return info

    # =========================================================================
    # QUBE PROPOSES TRANSACTION
    # =========================================================================

    async def propose_send(
        self,
        to_address: str,
        amount_sats: int,
        memo: Optional[str] = None,
        expiry_hours: int = DEFAULT_EXPIRY_HOURS
    ) -> PendingTx:
        """
        Qube proposes a transaction. Owner must approve before broadcast.

        Args:
            to_address: Destination address
            amount_sats: Amount to send in satoshis
            memo: Optional reason for the transaction
            expiry_hours: Hours until this pending tx expires

        Returns:
            PendingTx object

        Raises:
            ValueError: If validation fails or insufficient funds
        """
        # Validate address
        if not validate_address(to_address):
            raise ValueError(f"Invalid address: {to_address}")

        # Get UTXOs
        utxos = await self.wallet.get_utxos()
        if not utxos:
            raise ValueError("No funds available")

        # Create outputs
        outputs = [TxOutput(address=to_address, value=amount_sats)]

        # Create unsigned transaction and get Qube's signature
        try:
            proposed = self.wallet.propose_transaction(
                outputs=outputs,
                utxos=utxos,
                memo=memo
            )
        except ValueError as e:
            raise ValueError(f"Failed to create transaction: {e}")

        # Generate unique ID
        tx_id = hashlib.sha256(
            f"{self.qube_id}:{time.time()}:{amount_sats}".encode()
        ).hexdigest()[:16]

        # Create pending transaction
        now = time.time()
        pending = PendingTx(
            tx_id=tx_id,
            qube_id=self.qube_id,
            outputs=[{"address": o.address, "value": o.value} for o in proposed.unsigned_tx.outputs],
            total_amount=amount_sats,
            fee=proposed.unsigned_tx.fee,
            qube_signature_hex=proposed.qube_signature.hex(),
            utxos=[{"txid": u.txid, "vout": u.vout, "value": u.value} for u in proposed.unsigned_tx.utxos],
            redeem_script_hex=proposed.unsigned_tx.redeem_script.hex(),
            created_at=now,
            expires_at=now + (expiry_hours * 3600),
            memo=memo,
            status="pending"
        )

        # Store pending transaction
        self._pending_txs[tx_id] = pending
        self._save_pending_transactions()

        logger.info(
            "transaction_proposed",
            qube_id=self.qube_id,
            tx_id=tx_id,
            amount=amount_sats,
            to=to_address
        )

        return pending

    # =========================================================================
    # OWNER APPROVES/REJECTS
    # =========================================================================

    async def owner_approve(
        self,
        tx_id: str,
        owner_wif: str
    ) -> str:
        """
        Owner approves and co-signs a pending transaction.

        Args:
            tx_id: Pending transaction ID
            owner_wif: Owner's private key in WIF format

        Returns:
            Broadcast transaction ID (txid)

        Raises:
            ValueError: If tx not found, expired, or broadcast fails
        """
        pending = self._pending_txs.get(tx_id)
        if not pending:
            raise ValueError(f"Pending transaction not found: {tx_id}")

        if pending.status != "pending":
            raise ValueError(f"Transaction is not pending: {pending.status}")

        if pending.is_expired():
            pending.status = "expired"
            self._save_pending_transactions()
            raise ValueError("Transaction has expired")

        # Convert WIF to raw private key
        owner_privkey = self._wif_to_privkey(owner_wif)

        # Reconstruct the unsigned transaction
        from crypto.wallet import UnsignedTransaction
        utxos = [
            UTXO(
                txid=u["txid"],
                vout=u["vout"],
                value=u["value"],
                script_pubkey=address_to_script_pubkey(self.p2sh_address)
            )
            for u in pending.utxos
        ]
        outputs = [TxOutput(address=o["address"], value=o["value"]) for o in pending.outputs]
        redeem_script = bytes.fromhex(pending.redeem_script_hex)

        unsigned_tx = UnsignedTransaction(
            utxos=utxos,
            outputs=outputs,
            redeem_script=redeem_script,
            fee=pending.fee
        )

        # Finalize with both signatures
        qube_sig = bytes.fromhex(pending.qube_signature_hex)
        tx_hex = self.wallet.finalize_multisig(unsigned_tx, qube_sig, owner_privkey)

        # Broadcast
        try:
            txid = await self.wallet.broadcast(tx_hex)
        except Exception as e:
            logger.error("broadcast_failed", tx_id=tx_id, error=str(e))
            raise ValueError(f"Broadcast failed: {e}")

        # Update pending transaction
        pending.status = "broadcast"
        pending.broadcast_txid = txid
        self._save_pending_transactions()

        # Add to history
        self._add_to_history(TxHistoryEntry(
            txid=txid,
            tx_type="qube_spend",
            amount=-pending.total_amount,
            fee=pending.fee,
            counterparty=pending.outputs[0]["address"] if pending.outputs else None,
            timestamp=time.time(),
            block_height=None,
            memo=pending.memo
        ))

        logger.info(
            "transaction_approved_and_broadcast",
            qube_id=self.qube_id,
            tx_id=tx_id,
            txid=txid
        )

        return txid

    def owner_reject(self, tx_id: str) -> None:
        """
        Owner rejects a pending transaction.

        Args:
            tx_id: Pending transaction ID
        """
        pending = self._pending_txs.get(tx_id)
        if not pending:
            raise ValueError(f"Pending transaction not found: {tx_id}")

        pending.status = "rejected"
        self._save_pending_transactions()

        logger.info(
            "transaction_rejected",
            qube_id=self.qube_id,
            tx_id=tx_id
        )

    # =========================================================================
    # OWNER DIRECT WITHDRAWAL
    # =========================================================================

    async def owner_withdraw(
        self,
        to_address: str,
        amount_sats: int,
        owner_wif: str
    ) -> str:
        """
        Owner withdraws directly using IF branch (no Qube involvement).

        Args:
            to_address: Destination address
            amount_sats: Amount to send in satoshis
            owner_wif: Owner's private key in WIF format

        Returns:
            Transaction ID (txid)
        """
        if not validate_address(to_address):
            raise ValueError(f"Invalid address: {to_address}")

        owner_privkey = self._wif_to_privkey(owner_wif)

        txid = await self.wallet.owner_withdraw(to_address, amount_sats, owner_privkey)

        # Add to history
        self._add_to_history(TxHistoryEntry(
            txid=txid,
            tx_type="withdrawal",
            amount=-amount_sats,
            fee=200,  # Approximate
            counterparty=to_address,
            timestamp=time.time(),
            block_height=None,
            memo="Owner direct withdrawal"
        ))

        logger.info(
            "owner_withdrawal",
            qube_id=self.qube_id,
            txid=txid,
            amount=amount_sats,
            to=to_address
        )

        return txid

    async def owner_withdraw_all(
        self,
        to_address: str,
        owner_wif: str
    ) -> str:
        """
        Owner withdraws entire wallet balance.

        Args:
            to_address: Destination address
            owner_wif: Owner's private key in WIF format

        Returns:
            Transaction ID (txid)
        """
        if not validate_address(to_address):
            raise ValueError(f"Invalid address: {to_address}")

        owner_privkey = self._wif_to_privkey(owner_wif)

        balance = await self.wallet.get_balance()
        txid = await self.wallet.owner_withdraw_all(to_address, owner_privkey)

        # Add to history
        self._add_to_history(TxHistoryEntry(
            txid=txid,
            tx_type="withdrawal",
            amount=-balance,
            fee=200,  # Approximate
            counterparty=to_address,
            timestamp=time.time(),
            block_height=None,
            memo="Owner full withdrawal"
        ))

        logger.info(
            "owner_full_withdrawal",
            qube_id=self.qube_id,
            txid=txid,
            amount=balance,
            to=to_address
        )

        return txid

    # =========================================================================
    # PENDING TRANSACTIONS
    # =========================================================================

    def get_pending_transactions(self) -> List[PendingTx]:
        """Get all pending (non-expired, non-processed) transactions"""
        self._expire_old_transactions()
        return [tx for tx in self._pending_txs.values() if tx.status == "pending"]

    def get_pending_transaction(self, tx_id: str) -> Optional[PendingTx]:
        """Get a specific pending transaction"""
        return self._pending_txs.get(tx_id)

    def get_all_transactions(self) -> List[PendingTx]:
        """Get all transactions (including processed)"""
        return list(self._pending_txs.values())

    def get_completed_transactions(self) -> List[PendingTx]:
        """Get all completed (broadcast or rejected) transactions"""
        return [tx for tx in self._pending_txs.values() if tx.status in ("broadcast", "rejected", "expired")]

    def _expire_old_transactions(self) -> None:
        """Mark expired transactions"""
        changed = False
        for tx in self._pending_txs.values():
            if tx.status == "pending" and tx.is_expired():
                tx.status = "expired"
                changed = True

        if changed:
            self._save_pending_transactions()

    def _load_pending_transactions(self) -> None:
        """Load pending transactions from disk"""
        if self.pending_tx_file.exists():
            try:
                with open(self.pending_tx_file) as f:
                    data = json.load(f)
                self._pending_txs = {
                    tx_id: PendingTx.from_dict(tx_data)
                    for tx_id, tx_data in data.items()
                }
            except Exception as e:
                logger.warning("failed_to_load_pending_txs", error=str(e))
                self._pending_txs = {}

    def _save_pending_transactions(self) -> None:
        """Save pending transactions to disk"""
        try:
            data = {tx_id: tx.to_dict() for tx_id, tx in self._pending_txs.items()}
            with open(self.pending_tx_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error("failed_to_save_pending_txs", error=str(e))

    # =========================================================================
    # TRANSACTION HISTORY
    # =========================================================================

    def get_transaction_history(self, limit: int = 50) -> List[TxHistoryEntry]:
        """Get transaction history"""
        if not self.tx_history_file.exists():
            return []

        try:
            with open(self.tx_history_file) as f:
                data = json.load(f)
            entries = [TxHistoryEntry(**entry) for entry in data]
            # Sort by timestamp descending
            entries.sort(key=lambda x: x.timestamp, reverse=True)
            return entries[:limit]
        except Exception as e:
            logger.warning("failed_to_load_tx_history", error=str(e))
            return []

    def _add_to_history(self, entry: TxHistoryEntry) -> None:
        """Add entry to transaction history"""
        history = self.get_transaction_history(limit=1000)
        history.insert(0, entry)

        try:
            with open(self.tx_history_file, 'w') as f:
                json.dump([e.to_dict() for e in history], f, indent=2)
        except Exception as e:
            logger.error("failed_to_save_tx_history", error=str(e))

    # =========================================================================
    # HELPERS
    # =========================================================================

    def _wif_to_privkey(self, wif: str) -> bytes:
        """
        Convert WIF (Wallet Import Format) to raw 32-byte private key.

        WIF format:
        - Mainnet: starts with K, L, or 5
        - Base58Check encoded
        """
        import base58

        # Decode base58check
        decoded = base58.b58decode_check(wif)

        # Remove version byte (first byte)
        # For compressed keys, also remove compression flag (last byte)
        if len(decoded) == 34:
            # Compressed (has 0x01 suffix)
            return decoded[1:33]
        elif len(decoded) == 33:
            # Uncompressed
            return decoded[1:]
        else:
            raise ValueError(f"Invalid WIF length: {len(decoded)}")


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_wallet_manager(qube) -> WalletTransactionManager:
    """
    Factory function to create wallet manager for a Qube.

    Args:
        qube: Qube instance

    Returns:
        WalletTransactionManager instance
    """
    return WalletTransactionManager(qube)
