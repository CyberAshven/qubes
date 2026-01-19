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
from typing import Dict, Any, List, Optional, Literal, TYPE_CHECKING
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

from crypto.wallet import QubeWallet, TxOutput, validate_address
from crypto.bch_script import pubkey_from_privkey, UTXO, address_to_script_pubkey
from crypto.keys import get_raw_private_key_bytes
from utils.logging import get_logger

if TYPE_CHECKING:
    from core.chain_state import ChainState

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


@dataclass
class MergedTxHistoryEntry:
    """Transaction history entry merged from blockchain + local data"""
    txid: str
    tx_type: Literal["deposit", "withdrawal", "qube_spend"]
    amount: int                     # In satoshis
    fee: int                        # Fee paid
    counterparty: Optional[str]     # Address sent to/from
    timestamp: float                # Unix timestamp
    block_height: Optional[int]     # None if unconfirmed
    confirmations: int              # Number of confirmations
    memo: Optional[str] = None      # From local storage
    is_confirmed: bool = True
    explorer_url: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# =============================================================================
# WALLET TRANSACTION MANAGER
# =============================================================================

class WalletTransactionManager:
    """
    Manages transactions for a Qube's wallet.

    UPDATED FOR CHAIN STATE CONSOLIDATION:
    - Pending transactions stored in chain_state.json under "financial.pending"
    - Transaction history stored in "financial.transactions.history" (capped at 50)
    - Balance cache stored in "financial.wallet"
    - Data automatically encrypted at rest

    Handles the full lifecycle:
    1. Qube proposes a transaction
    2. Transaction is stored as pending
    3. Owner reviews and approves/rejects
    4. If approved, transaction is broadcast
    5. Transaction history is updated
    """

    # Pending transactions expire after 24 hours
    DEFAULT_EXPIRY_HOURS = 24

    # Maximum transaction history entries
    MAX_TRANSACTION_HISTORY = 50

    def __init__(self, qube, chain_state: "ChainState"):
        """
        Initialize transaction manager for a Qube.

        Args:
            qube: Qube instance with wallet info in genesis block
            chain_state: ChainState instance for persistence
        """
        self.qube = qube
        self.qube_id = qube.qube_id
        self.chain_state = chain_state

        # Get wallet info from genesis block (handle both Block and SimpleNamespace)
        if not qube.genesis_block:
            raise ValueError(f"Qube {qube.qube_id} does not have genesis block")

        # Handle both Block objects (with .content dict) and SimpleNamespace (from dict)
        genesis = qube.genesis_block
        if hasattr(genesis, 'content') and isinstance(getattr(genesis, 'content', None), dict):
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
        self.qube_pubkey = wallet_info.get("qube_pubkey")

        if not self.owner_pubkey or not self.p2sh_address:
            raise ValueError(f"Qube {qube.qube_id} has incomplete wallet info")

        # Create wallet instance (use raw 32-byte private key, not PEM format)
        private_key_bytes = get_raw_private_key_bytes(qube.private_key)

        self.wallet = QubeWallet(
            qube_private_key=private_key_bytes,
            owner_pubkey_hex=self.owner_pubkey,
            network="mainnet",
            qube_pubkey_hex=self.qube_pubkey
        )

        # In-memory cache (loaded from chain_state)
        self._pending_txs: Dict[str, PendingTx] = {}
        self._load_pending_transactions()

        # Load persisted balance cache into wallet
        self._load_balance_cache()

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

    def _load_balance_cache(self) -> None:
        """
        Load persisted balance cache from chain_state into the wallet's in-memory cache.

        This ensures balance is available immediately even if the API is slow/down.
        """
        try:
            financial = self.chain_state.state.get("financial", {})
            cache_data = financial.get("wallet", {})

            cached_balance = cache_data.get("balance_satoshis")
            cached_timestamp = cache_data.get("last_sync", 0)

            if cached_balance is not None:
                # Load into wallet's in-memory cache
                self.wallet._cached_balance = cached_balance
                self.wallet._balance_last_updated = cached_timestamp
                logger.debug(
                    "balance_cache_loaded",
                    balance=cached_balance,
                    cache_age=int(time.time() - cached_timestamp) if cached_timestamp else 0
                )
        except Exception as e:
            logger.debug(f"Could not load balance cache: {e}")

    def _save_balance_cache(self, balance: int) -> None:
        """
        Persist balance to chain_state for fast startup.

        Args:
            balance: Balance in satoshis
        """
        try:
            financial = self.chain_state.state.setdefault("financial", {})
            wallet_data = financial.setdefault("wallet", {})

            wallet_data["balance_satoshis"] = balance
            wallet_data["balance_bch"] = balance / 100_000_000
            wallet_data["last_sync"] = time.time()
            wallet_data["address"] = self.p2sh_address

            self.chain_state._save()
            logger.debug("balance_cache_saved", balance=balance)
        except Exception as e:
            logger.debug(f"Could not save balance cache: {e}")

    async def get_balance_with_cache(self) -> int:
        """
        Get wallet balance with persistent caching.

        Returns cached balance immediately if API fails or times out.
        Saves balance to disk on successful fetch for future sessions.

        Returns:
            Balance in satoshis
        """
        try:
            # Try to fetch fresh balance
            balance = await self.wallet.get_balance()
            # Save to disk on success
            if balance is not None:
                self._save_balance_cache(balance)
            return balance
        except Exception as e:
            logger.debug(f"API balance fetch failed: {e}")
            # Return cached value if available
            if self.wallet._cached_balance is not None:
                return self.wallet._cached_balance
            return 0

    async def sync_balances_to_chain_state(self, owner_pubkey: str = None) -> None:
        """
        Sync all wallet balances from blockchain to chain_state.

        Called on qube load to ensure chain_state has current data.
        UI reads from chain_state for instant response.

        Args:
            owner_pubkey: Owner's public key for NFT balance lookup
        """
        import aiohttp

        try:
            # Fetch P2SH balance and UTXO count
            p2sh_balance = 0
            utxo_count = 0
            try:
                addr = self.p2sh_address.split(":")[-1] if ":" in self.p2sh_address else self.p2sh_address
                timeout = aiohttp.ClientTimeout(total=10)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    url = f"https://rest.bch.actorforth.org/v2/address/details/{addr}"
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            balance = data.get("balanceSat") or data.get("balance")
                            if balance is not None:
                                p2sh_balance = int(balance)
                            # Get UTXO count from unconfirmedTxApperances or txApperances
                            utxo_count = data.get("unspentTxCount", 0) or data.get("txApperances", 0)
            except Exception as e:
                logger.debug(f"P2SH balance sync failed: {e}")

            # If we didn't get utxo_count from API, try to fetch UTXOs directly
            if utxo_count == 0 and p2sh_balance > 0:
                try:
                    utxos = await self.wallet.get_utxos()
                    utxo_count = len(utxos)
                except Exception as e:
                    logger.debug(f"UTXO count fetch failed: {e}")

            # Fetch NFT/BCH balance (q address)
            nft_balance = 0
            if owner_pubkey:
                try:
                    from crypto.bch_script import pubkey_to_p2pkh_address
                    q_address = pubkey_to_p2pkh_address(owner_pubkey, "mainnet", token_aware=False)

                    timeout = aiohttp.ClientTimeout(total=10)
                    async with aiohttp.ClientSession(timeout=timeout) as session:
                        url = f"https://api.blockchair.com/bitcoin-cash/dashboards/address/{q_address}"
                        async with session.get(url) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                if "data" in data and q_address in data["data"]:
                                    nft_balance = data["data"][q_address]["address"]["balance"]
                except Exception as e:
                    logger.debug(f"NFT balance sync failed: {e}")

            # Fetch recent transactions and sync to chain_state history
            recent_transactions = []
            new_tx_count = 0
            try:
                tx_history_result = await self.wallet.get_transaction_history(limit=20)
                # get_transaction_history returns dict with "transactions" key
                tx_history = tx_history_result.get("transactions", [])

                # Get existing txids from chain_state to avoid duplicates
                existing_txids = set()
                existing_history = self.chain_state.get_transaction_history(limit=0)  # Get all
                for tx in existing_history:
                    if tx.get("txid"):
                        existing_txids.add(tx.get("txid"))

                for tx in tx_history:
                    txid = tx.get("txid", "")
                    amount = tx.get("amount", 0)
                    tx_type = "received" if amount > 0 else "sent"

                    recent_transactions.append({
                        "txid": txid,
                        "amount": amount,
                        "type": tx_type,
                        "timestamp": tx.get("timestamp"),
                        "confirmations": tx.get("confirmations", 0)
                    })

                    # Add NEW incoming transactions to chain_state history
                    # (Outgoing transactions are already added by owner_approve/withdraw/auto_send)
                    if txid and txid not in existing_txids and amount > 0:
                        self.chain_state.add_transaction({
                            "txid": txid,
                            "direction": "received",
                            "from_address": tx.get("counterparty"),
                            "amount_satoshis": amount,
                            "amount_bch": amount / 100_000_000,
                            "timestamp": tx.get("timestamp", time.time()),
                            "status": "confirmed" if tx.get("confirmations", 0) > 0 else "unconfirmed",
                            "confirmations": tx.get("confirmations", 0),
                            "block_height": tx.get("block_height")
                        })
                        new_tx_count += 1
                        logger.debug(f"Added incoming transaction to chain_state: {txid[:16]}...")

            except Exception as e:
                logger.debug(f"Transaction history sync failed: {e}")

            # Update chain_state
            financial = self.chain_state.state.setdefault("financial", {})

            # P2SH wallet balance
            wallet_data = financial.setdefault("wallet", {})
            wallet_data["balance_satoshis"] = p2sh_balance
            wallet_data["balance_bch"] = p2sh_balance / 100_000_000
            wallet_data["last_sync"] = time.time()
            wallet_data["address"] = self.p2sh_address
            wallet_data["recent_transactions"] = recent_transactions
            wallet_data["utxo_count"] = utxo_count

            # NFT/BCH balance
            nft_data = financial.setdefault("nft_balance", {})
            nft_data["balance_satoshis"] = nft_balance
            nft_data["balance_bch"] = nft_balance / 100_000_000
            nft_data["last_sync"] = time.time()

            self.chain_state._save()
            logger.info("wallet_balances_synced_to_chain_state", p2sh=p2sh_balance, nft=nft_balance, txs=len(recent_transactions), new_txs=new_tx_count)

        except Exception as e:
            logger.warning(f"Failed to sync wallet balances: {e}")

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

        # Update chain_state balance (optimistic update - subtract sent amount + fee)
        try:
            total_spent = pending.total_amount + pending.fee
            financial = self.chain_state.state.setdefault("financial", {})
            wallet_data = financial.setdefault("wallet", {})
            current_balance = wallet_data.get("balance_satoshis", 0)
            new_balance = max(0, current_balance - total_spent)
            wallet_data["balance_satoshis"] = new_balance
            wallet_data["balance_bch"] = new_balance / 100_000_000
            wallet_data["last_sync"] = time.time()
            self.chain_state._save()
        except Exception as e:
            logger.debug(f"Could not update chain_state after tx: {e}")

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

        # Update chain_state balance (optimistic update - subtract sent amount)
        try:
            financial = self.chain_state.state.setdefault("financial", {})
            wallet_data = financial.setdefault("wallet", {})
            current_balance = wallet_data.get("balance_satoshis", 0)
            new_balance = max(0, current_balance - amount_sats - 200)  # Include approx fee
            wallet_data["balance_satoshis"] = new_balance
            wallet_data["balance_bch"] = new_balance / 100_000_000
            wallet_data["last_sync"] = time.time()
            self.chain_state._save()
        except Exception as e:
            logger.debug(f"Could not update chain_state after withdrawal: {e}")

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

        # Update chain_state balance (full withdrawal = 0 balance)
        try:
            financial = self.chain_state.state.setdefault("financial", {})
            wallet_data = financial.setdefault("wallet", {})
            wallet_data["balance_satoshis"] = 0
            wallet_data["balance_bch"] = 0.0
            wallet_data["last_sync"] = time.time()
            self.chain_state._save()
        except Exception as e:
            logger.debug(f"Could not update chain_state after full withdrawal: {e}")

        logger.info(
            "owner_full_withdrawal",
            qube_id=self.qube_id,
            txid=txid,
            amount=balance,
            to=to_address
        )

        return txid

    # =========================================================================
    # AUTO-SEND (WHITELISTED)
    # =========================================================================

    async def auto_send(
        self,
        to_address: str,
        amount_sats: int,
        owner_wif: str,
        memo: str = ""
    ) -> str:
        """
        Create, sign, and broadcast a transaction in one step.
        Used for whitelisted auto-approval - bypasses pending transaction flow.

        Args:
            to_address: Destination address
            amount_sats: Amount in satoshis
            owner_wif: Owner's private key in WIF format
            memo: Optional memo for history

        Returns:
            Transaction ID (txid)
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

        # Convert WIF to private key bytes
        owner_privkey = self._wif_to_privkey(owner_wif)

        # Owner signs and finalize
        tx_hex = self.wallet.finalize_multisig(
            proposed.unsigned_tx,
            proposed.qube_signature,
            owner_privkey
        )

        # Broadcast
        try:
            txid = await self.wallet.broadcast(tx_hex)
        except Exception as e:
            logger.error("auto_send_broadcast_failed", error=str(e))
            raise ValueError(f"Broadcast failed: {e}")

        # Log to history
        self._add_to_history(TxHistoryEntry(
            txid=txid,
            tx_type="qube_spend",
            amount=-amount_sats,
            fee=proposed.unsigned_tx.fee,
            counterparty=to_address,
            timestamp=time.time(),
            block_height=None,
            memo=memo or "Auto-approved (whitelisted)"
        ))

        # Update chain_state balance (optimistic update - subtract sent amount + fee)
        try:
            total_sent = amount_sats + proposed.unsigned_tx.fee
            financial = self.chain_state.state.setdefault("financial", {})
            wallet_data = financial.setdefault("wallet", {})
            current_balance = wallet_data.get("balance_satoshis", 0)
            new_balance = max(0, current_balance - total_sent)
            wallet_data["balance_satoshis"] = new_balance
            wallet_data["balance_bch"] = new_balance / 100_000_000
            wallet_data["last_sync"] = time.time()
            self.chain_state._save()
        except Exception as e:
            logger.debug(f"Could not update chain_state after auto_send: {e}")

        logger.info(
            "auto_send_completed",
            qube_id=self.qube_id,
            txid=txid,
            amount=amount_sats,
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
        """Load pending transactions from chain_state."""
        financial = self.chain_state.state.get("financial", {})
        pending_list = financial.get("pending", [])

        self._pending_txs = {}
        for tx_data in pending_list:
            try:
                tx = PendingTx.from_dict(tx_data)
                self._pending_txs[tx.tx_id] = tx
            except Exception as e:
                logger.warning(f"Failed to load pending tx: {e}")

        logger.debug(f"Loaded {len(self._pending_txs)} pending transactions from chain_state")

    def _save_pending_transactions(self) -> None:
        """Save pending transactions to chain_state."""
        try:
            pending_list = [tx.to_dict() for tx in self._pending_txs.values()]

            financial = self.chain_state.state.setdefault("financial", {})
            financial["pending"] = pending_list
            self.chain_state._save()

            logger.debug(f"Saved {len(pending_list)} pending transactions to chain_state")
        except Exception as e:
            logger.error(f"Failed to save pending transactions: {e}")

    # =========================================================================
    # TRANSACTION HISTORY
    # =========================================================================

    def get_transaction_history(self, limit: int = 50) -> List[TxHistoryEntry]:
        """Get transaction history from chain_state."""
        financial = self.chain_state.state.get("financial", {})
        transactions = financial.get("transactions", {})
        history_data = transactions.get("history", [])

        history = []
        for entry_data in history_data:
            try:
                if isinstance(entry_data, dict):
                    history.append(TxHistoryEntry(**entry_data))
                else:
                    history.append(entry_data)
            except Exception as e:
                logger.warning(f"Failed to parse history entry: {e}")

        # Sort by timestamp descending
        history.sort(key=lambda x: x.timestamp, reverse=True)
        return history[:limit]

    async def get_full_transaction_history(
        self,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Get merged transaction history from blockchain + local metadata.

        Combines blockchain data with local transaction history to provide
        memos and tx_type distinctions (qube_spend vs withdrawal).

        Args:
            limit: Maximum number of transactions to return
            offset: Pagination offset

        Returns:
            Dict with:
            - transactions: List of MergedTxHistoryEntry dicts
            - total_count: Total transaction count
            - has_more: Whether more transactions exist
        """
        # Fetch blockchain history
        blockchain_result = await self.wallet.get_transaction_history(
            limit=limit,
            offset=offset
        )

        if "error" in blockchain_result:
            return blockchain_result

        blockchain_txs = blockchain_result.get("transactions", [])
        total_count = blockchain_result.get("total_count", 0)
        has_more = blockchain_result.get("has_more", False)

        # Load local history for memo matching
        local_history = self.get_transaction_history(limit=1000)
        local_by_txid = {entry.txid: entry for entry in local_history}

        # Track which blockchain txids we've seen
        blockchain_txids = {bc_tx["txid"] for bc_tx in blockchain_txs}

        # Merge blockchain data with local metadata
        merged_transactions = []
        for bc_tx in blockchain_txs:
            txid = bc_tx["txid"]
            local_entry = local_by_txid.get(txid)

            # Determine tx_type - prefer local (which distinguishes qube_spend)
            if local_entry:
                tx_type = local_entry.tx_type
                memo = local_entry.memo
            else:
                tx_type = bc_tx["tx_type"]
                memo = None

            # Build explorer URL
            explorer_url = f"https://blockchair.com/bitcoin-cash/transaction/{txid}"

            merged = MergedTxHistoryEntry(
                txid=txid,
                tx_type=tx_type,
                amount=bc_tx["amount"],
                fee=bc_tx["fee"],
                counterparty=bc_tx["counterparty"],
                timestamp=bc_tx["timestamp"],
                block_height=bc_tx["block_height"],
                confirmations=bc_tx["confirmations"],
                memo=memo,
                is_confirmed=bc_tx["is_confirmed"],
                explorer_url=explorer_url
            )
            merged_transactions.append(merged)

        # Check for local transactions not yet in blockchain address history
        # These may be recently broadcast - verify by querying txid directly
        for local_entry in local_history:
            if local_entry.txid not in blockchain_txids:
                # Query blockchain to verify this txid exists
                tx_info = await self.wallet.get_transaction_info(local_entry.txid)
                if tx_info and not tx_info.get("error"):
                    # Transaction exists on blockchain - add it
                    explorer_url = f"https://blockchair.com/bitcoin-cash/transaction/{local_entry.txid}"
                    merged = MergedTxHistoryEntry(
                        txid=local_entry.txid,
                        tx_type=local_entry.tx_type,
                        amount=local_entry.amount,
                        fee=local_entry.fee,
                        counterparty=local_entry.counterparty,
                        timestamp=local_entry.timestamp,
                        block_height=tx_info.get("block_height"),
                        confirmations=tx_info.get("confirmations", 0),
                        memo=local_entry.memo,
                        is_confirmed=tx_info.get("confirmations", 0) > 0,
                        explorer_url=explorer_url
                    )
                    # Insert at appropriate position based on timestamp
                    inserted = False
                    for i, existing in enumerate(merged_transactions):
                        if local_entry.timestamp > existing.timestamp:
                            merged_transactions.insert(i, merged)
                            inserted = True
                            break
                    if not inserted:
                        merged_transactions.append(merged)
                    total_count += 1

        return {
            "transactions": [tx.to_dict() for tx in merged_transactions],
            "total_count": total_count,
            "has_more": has_more
        }

    def _add_to_history(self, entry: TxHistoryEntry) -> None:
        """Add entry to transaction history (capped at MAX_TRANSACTION_HISTORY)."""
        try:
            financial = self.chain_state.state.setdefault("financial", {})
            transactions = financial.setdefault("transactions", {"history": [], "total_count": 0, "archived_count": 0})
            history = transactions.get("history", [])

            # Append new entry
            history.append(entry.to_dict())
            transactions["total_count"] = transactions.get("total_count", 0) + 1

            # Cap at MAX_TRANSACTION_HISTORY
            if len(history) > self.MAX_TRANSACTION_HISTORY:
                overflow = len(history) - self.MAX_TRANSACTION_HISTORY
                transactions["archived_count"] = transactions.get("archived_count", 0) + overflow
                history = history[-self.MAX_TRANSACTION_HISTORY:]

            transactions["history"] = history
            self.chain_state._save()

            logger.debug(f"Added transaction to history, total: {len(history)}")
        except Exception as e:
            logger.error(f"Failed to add transaction to history: {e}")

    # =========================================================================
    # MIGRATION HELPER
    # =========================================================================

    @classmethod
    def migrate_from_files(cls, qube, chain_state: "ChainState", data_dir: Path) -> "WalletTransactionManager":
        """
        Migrate wallet data from old file-based storage to chain_state.

        Args:
            qube: Qube instance
            chain_state: ChainState instance to migrate into
            data_dir: Path to qube's data directory

        Returns:
            New WalletTransactionManager instance with migrated data
        """
        pending_file = data_dir / "pending_transactions.json"
        history_file = data_dir / "transaction_history.json"
        balance_file = data_dir / "balance_cache.json"

        financial = chain_state.state.setdefault("financial", {})

        # Migrate pending transactions
        if pending_file.exists():
            try:
                with open(pending_file, 'r') as f:
                    pending_data = json.load(f)
                financial["pending"] = list(pending_data.values())
                logger.info(f"Migrated {len(pending_data)} pending transactions")
            except Exception as e:
                logger.error(f"Failed to migrate pending transactions: {e}")

        # Migrate transaction history
        if history_file.exists():
            try:
                with open(history_file, 'r') as f:
                    history_data = json.load(f)
                # Cap during migration
                if len(history_data) > 50:
                    history_data = history_data[-50:]
                financial["transactions"] = {
                    "history": history_data,
                    "total_count": len(history_data),
                    "archived_count": 0
                }
                logger.info(f"Migrated {len(history_data)} transaction history entries")
            except Exception as e:
                logger.error(f"Failed to migrate transaction history: {e}")

        # Migrate balance cache
        if balance_file.exists():
            try:
                with open(balance_file, 'r') as f:
                    balance_data = json.load(f)
                # Convert to new format
                financial["wallet"] = {
                    "balance_satoshis": balance_data.get("balance", 0),
                    "balance_bch": balance_data.get("balance", 0) / 100_000_000,
                    "last_sync": balance_data.get("timestamp"),
                    "address": balance_data.get("address"),
                }
                logger.info("Migrated balance cache")
            except Exception as e:
                logger.error(f"Failed to migrate balance cache: {e}")

        # Save to chain_state
        chain_state._save()

        # Delete old files
        try:
            for old_file in [pending_file, history_file, balance_file]:
                if old_file.exists():
                    old_file.unlink()
                    logger.info(f"Deleted old file: {old_file}")
        except Exception as e:
            logger.warning(f"Failed to cleanup old wallet files: {e}")

        return cls(qube, chain_state)

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
    Get the wallet manager for a Qube.

    Since Qube now initializes wallet_manager in __init__, this simply
    returns the existing instance.

    Args:
        qube: Qube instance

    Returns:
        WalletTransactionManager instance
    """
    return qube.wallet_manager
