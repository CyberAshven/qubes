"""
Qube Wallet Module

Provides the QubeWallet class for asymmetric multi-sig BCH wallets.

Each Qube has a wallet with two spending paths:
- Owner alone (IF branch): Emergency withdrawal, full control
- Owner + Qube together (ELSE branch): Normal operation with approval

Usage:
    from crypto.wallet import QubeWallet

    # Create wallet from Qube's private key and owner's public key
    wallet = QubeWallet(qube_private_key_bytes, owner_pubkey_hex)

    # Get wallet address (for deposits)
    print(wallet.p2sh_address)

    # Check balance
    balance = await wallet.get_balance()

    # Qube proposes a transaction (needs owner approval)
    unsigned_tx, qube_sig = wallet.propose_transaction(outputs)

    # Owner approves and co-signs
    txid = await wallet.approve_and_broadcast(unsigned_tx, qube_sig, owner_privkey)

    # OR owner withdraws directly (no Qube involvement)
    txid = await wallet.owner_withdraw(outputs, owner_privkey)
"""

import asyncio
import aiohttp
import json
from typing import List, Optional, Tuple, Dict, Any, Literal
from dataclasses import dataclass, field

from crypto.bch_script import (
    create_wallet_address,
    pubkey_from_privkey,
    address_to_script_pubkey,
    calculate_sighash_forkid,
    sign_sighash,
    build_p2sh_spending_tx,
    estimate_tx_size,
    UTXO,
    TxOutput,
    push_data,
    var_int,
    serialize_outpoint,
    serialize_output,
    OP_0,
    OP_TRUE,
    OP_FALSE,
    double_sha256,
)
import struct

from utils.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================

BLOCKCHAIR_API = "https://api.blockchair.com/bitcoin-cash"
FULCRUM_API = "https://rest.bch.actorforth.org/v2"  # Fulcrum-based API (more real-time)
DUST_LIMIT = 546  # Minimum output value in satoshis
DEFAULT_FEE_PER_BYTE = 1  # 1 sat/byte is sufficient for BCH


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class UnsignedTransaction:
    """Represents an unsigned transaction ready for signing"""
    utxos: List[UTXO]
    outputs: List[TxOutput]
    redeem_script: bytes
    fee: int

    def total_input(self) -> int:
        return sum(u.value for u in self.utxos)

    def total_output(self) -> int:
        return sum(o.value for o in self.outputs)


@dataclass
class ProposedTransaction:
    """A transaction proposed by the Qube, awaiting owner approval"""
    tx_id: str                    # Internal tracking ID
    unsigned_tx: UnsignedTransaction
    qube_signature: bytes         # Qube's signature
    created_at: float             # Unix timestamp
    memo: Optional[str] = None    # Qube's reason for the transaction

    def to_dict(self) -> dict:
        return {
            "tx_id": self.tx_id,
            "outputs": [{"address": o.address, "value": o.value} for o in self.unsigned_tx.outputs],
            "fee": self.unsigned_tx.fee,
            "total_input": self.unsigned_tx.total_input(),
            "total_output": self.unsigned_tx.total_output(),
            "qube_signature": self.qube_signature.hex(),
            "created_at": self.created_at,
            "memo": self.memo,
        }


@dataclass
class BlockchainTxInfo:
    """Transaction info fetched from blockchain"""
    txid: str
    tx_type: Literal["deposit", "withdrawal"]
    amount: int  # satoshis (positive=received, negative=sent)
    fee: int  # satoshis (0 for deposits)
    counterparty: Optional[str]  # Primary counterparty address
    timestamp: float  # Unix timestamp
    block_height: Optional[int]  # None if unconfirmed
    confirmations: int

    def to_dict(self) -> dict:
        return {
            "txid": self.txid,
            "tx_type": self.tx_type,
            "amount": self.amount,
            "fee": self.fee,
            "counterparty": self.counterparty,
            "timestamp": self.timestamp,
            "block_height": self.block_height,
            "confirmations": self.confirmations,
            "is_confirmed": self.block_height is not None and self.block_height > 0,
        }


# =============================================================================
# QUBE WALLET CLASS
# =============================================================================

class QubeWallet:
    """
    Asymmetric multi-sig wallet for Qube BCH transactions.

    The wallet is controlled by a P2SH script with two spending paths:
    - IF branch: Owner can spend alone (full control)
    - ELSE branch: Requires both owner and Qube signatures (2-of-2)

    This ensures the Qube can never spend without owner approval,
    while the owner retains emergency withdrawal capability.
    """

    def __init__(
        self,
        qube_private_key: bytes,
        owner_pubkey_hex: str,
        network: str = "mainnet",
        qube_pubkey_hex: Optional[str] = None
    ):
        """
        Initialize Qube wallet.

        Args:
            qube_private_key: 32-byte private key (from Qube's keypair)
            owner_pubkey_hex: Owner's compressed public key (hex string, 02.../03...)
            network: "mainnet" or "testnet"
            qube_pubkey_hex: Optional pre-computed qube public key (hex string).
                             If provided, uses this instead of deriving from private key.
                             This ensures address consistency with stored genesis data.
        """
        if len(qube_private_key) != 32:
            raise ValueError(f"Private key must be 32 bytes, got {len(qube_private_key)}")

        if not owner_pubkey_hex or len(owner_pubkey_hex) != 66:
            raise ValueError("Owner pubkey must be 66 hex chars (33 bytes compressed)")

        if not owner_pubkey_hex.startswith(('02', '03')):
            raise ValueError("Owner pubkey must start with 02 or 03 (compressed format)")

        self._qube_privkey = qube_private_key
        self._owner_pubkey = bytes.fromhex(owner_pubkey_hex)
        self._network = network

        # Use provided qube pubkey if available, otherwise derive from private key
        if qube_pubkey_hex:
            self._qube_pubkey = bytes.fromhex(qube_pubkey_hex)
        else:
            self._qube_pubkey = pubkey_from_privkey(qube_private_key)

        # Build wallet
        wallet_info = create_wallet_address(
            owner_pubkey_hex=owner_pubkey_hex,
            qube_pubkey_hex=self._qube_pubkey.hex(),
            network=network
        )

        self._p2sh_address = wallet_info["p2sh_address"]
        self._redeem_script = wallet_info["redeem_script"]
        self._script_hash = wallet_info["script_hash"]

        # Balance cache - avoids hitting API on every request
        self._cached_balance: Optional[int] = None
        self._balance_last_updated: float = 0
        self._balance_cache_ttl: int = 300  # 5 minutes default TTL

        logger.debug(
            "qube_wallet_initialized",
            p2sh_address=self._p2sh_address,
            network=network
        )

    # =========================================================================
    # PROPERTIES
    # =========================================================================

    @property
    def p2sh_address(self) -> str:
        """The P2SH wallet address (CashAddr format)"""
        return self._p2sh_address

    @property
    def redeem_script(self) -> bytes:
        """The redeem script (needed for spending)"""
        return self._redeem_script

    @property
    def redeem_script_hex(self) -> str:
        """Redeem script as hex string"""
        return self._redeem_script.hex()

    @property
    def script_hash(self) -> str:
        """HASH160 of redeem script (for verification)"""
        return self._script_hash

    @property
    def qube_pubkey(self) -> bytes:
        """Qube's public key"""
        return self._qube_pubkey

    @property
    def qube_pubkey_hex(self) -> str:
        """Qube's public key as hex"""
        return self._qube_pubkey.hex()

    @property
    def owner_pubkey(self) -> bytes:
        """Owner's public key"""
        return self._owner_pubkey

    @property
    def owner_pubkey_hex(self) -> str:
        """Owner's public key as hex"""
        return self._owner_pubkey.hex()

    @property
    def network(self) -> str:
        """Network (mainnet/testnet)"""
        return self._network

    # =========================================================================
    # BALANCE & UTXO QUERIES
    # =========================================================================

    async def _get_balance_fulcrum(self) -> Optional[int]:
        """
        Get balance from Fulcrum API (faster indexing than Blockchair).

        Returns:
            Balance in satoshis, or None if request fails
        """
        try:
            # Extract address without prefix for Fulcrum API
            addr = self._p2sh_address.split(":")[-1] if ":" in self._p2sh_address else self._p2sh_address

            async with aiohttp.ClientSession() as session:
                url = f"{FULCRUM_API}/address/details/{addr}"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        logger.debug("fulcrum_api_error", status=resp.status, address=addr)
                        return None
                    data = await resp.json()

                    # Fulcrum returns balance in satoshis as "balanceSat" or "balance"
                    balance = data.get("balanceSat") or data.get("balance")
                    if balance is not None:
                        logger.debug("get_balance_from_fulcrum", balance=balance, address=addr)
                        return int(balance)

                    logger.debug("fulcrum_no_balance_field", address=addr, response_keys=list(data.keys()))
                    return None
        except Exception as e:
            logger.debug("fulcrum_balance_failed", error=str(e), address=self._p2sh_address)
            return None

    async def _get_utxos_fulcrum(self) -> Optional[List[UTXO]]:
        """
        Get UTXOs from Fulcrum API (faster indexing than Blockchair).

        Returns:
            List of UTXOs, or None if request fails
        """
        try:
            addr = self._p2sh_address.split(":")[-1] if ":" in self._p2sh_address else self._p2sh_address

            async with aiohttp.ClientSession() as session:
                url = f"{FULCRUM_API}/address/utxo/{addr}"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        return None
                    data = await resp.json()

                    # Fulcrum returns UTXOs directly as an array (or under "utxos" key)
                    utxo_list = data if isinstance(data, list) else data.get("utxos", [])

                    if utxo_list:
                        script_pubkey = address_to_script_pubkey(self._p2sh_address)
                        utxos = [
                            UTXO(
                                txid=u["txid"],
                                vout=u["vout"],
                                value=u["satoshis"],
                                script_pubkey=script_pubkey
                            )
                            for u in utxo_list
                        ]
                        logger.debug("get_utxos_from_fulcrum", count=len(utxos))
                        return utxos
                    return []  # Empty list is valid (no UTXOs)
        except Exception as e:
            logger.debug("fulcrum_utxos_failed", error=str(e))
            return None

    async def get_balance(self, force_refresh: bool = False) -> int:
        """
        Get wallet balance in satoshis (cached).

        Uses cached value if available and fresh. Call with force_refresh=True
        to force an API fetch, or use refresh_balance() after transactions.

        Tries Fulcrum API first (faster indexing), falls back to Blockchair.

        Args:
            force_refresh: If True, bypass cache and fetch from API

        Returns:
            Balance in satoshis
        """
        import time

        # Check cache validity
        cache_age = time.time() - self._balance_last_updated
        if not force_refresh and self._cached_balance is not None and cache_age < self._balance_cache_ttl:
            logger.debug("get_balance_from_cache", balance=self._cached_balance, cache_age_seconds=int(cache_age))
            return self._cached_balance

        # Try Fulcrum first (faster indexing)
        fulcrum_balance = await self._get_balance_fulcrum()
        if fulcrum_balance is not None:
            self._cached_balance = fulcrum_balance
            self._balance_last_updated = time.time()
            return fulcrum_balance

        # Fallback to Blockchair
        try:
            # Extract address without prefix for API query
            addr_without_prefix = self._p2sh_address.split(":")[-1] if ":" in self._p2sh_address else self._p2sh_address

            async with aiohttp.ClientSession() as session:
                url = f"{BLOCKCHAIR_API}/dashboards/address/{self._p2sh_address}"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    data = await resp.json()

                    if "data" in data:
                        # Blockchair may return address with or without prefix
                        # Try multiple key formats
                        address_data = None
                        for key in [self._p2sh_address, addr_without_prefix, f"bitcoincash:{addr_without_prefix}"]:
                            if key in data["data"]:
                                address_data = data["data"][key]
                                break

                        if address_data and "address" in address_data:
                            balance = address_data["address"].get("balance", 0)
                            # Update cache
                            self._cached_balance = balance
                            self._balance_last_updated = time.time()
                            logger.debug("get_balance_from_blockchair", balance=balance, address=self._p2sh_address)
                            return balance

                    # Address not found or empty response
                    logger.debug("blockchair_address_not_found", address=self._p2sh_address, response_keys=list(data.get("data", {}).keys()) if "data" in data else [])
                    self._cached_balance = 0
                    self._balance_last_updated = time.time()
                    return 0
        except Exception as e:
            logger.error("get_balance_failed", error=str(e), address=self._p2sh_address)
            # Return cached value if available, even if stale
            if self._cached_balance is not None:
                logger.warning("get_balance_returning_stale_cache", cached_balance=self._cached_balance)
                return self._cached_balance
            return 0

    def invalidate_balance_cache(self):
        """
        Invalidate the balance cache.

        Call this after broadcasting transactions to force a fresh fetch
        on the next get_balance() call.
        """
        self._cached_balance = None
        self._balance_last_updated = 0
        logger.debug("balance_cache_invalidated")

    def update_balance_cache(self, new_balance: int):
        """
        Manually update the cached balance.

        Useful when you know the new balance (e.g., after a transaction)
        without needing to hit the API.

        Args:
            new_balance: New balance in satoshis
        """
        import time
        self._cached_balance = new_balance
        self._balance_last_updated = time.time()
        logger.debug("balance_cache_updated", balance=new_balance)

    @property
    def cached_balance(self) -> Optional[int]:
        """Get the cached balance without hitting API (may be None if not cached)"""
        return self._cached_balance

    async def get_utxos(self) -> List[UTXO]:
        """
        Get unspent transaction outputs.

        Tries Fulcrum API first (faster indexing), falls back to Blockchair.

        Returns:
            List of UTXOs
        """
        # Try Fulcrum first (faster indexing)
        fulcrum_utxos = await self._get_utxos_fulcrum()
        if fulcrum_utxos is not None:
            return fulcrum_utxos

        # Fallback to Blockchair
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{BLOCKCHAIR_API}/dashboards/address/{self._p2sh_address}"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    data = await resp.json()

                    if "data" not in data or self._p2sh_address not in data["data"]:
                        return []

                    utxo_list = data["data"][self._p2sh_address].get("utxo", [])
                    script_pubkey = address_to_script_pubkey(self._p2sh_address)

                    return [
                        UTXO(
                            txid=u["transaction_hash"],
                            vout=u["index"],
                            value=u["value"],
                            script_pubkey=script_pubkey
                        )
                        for u in utxo_list
                    ]
        except Exception as e:
            logger.error("get_utxos_failed", error=str(e))
            return []

    async def get_wallet_info(self) -> Dict[str, Any]:
        """
        Get comprehensive wallet information.

        Returns:
            Dict with address, balance, utxos, etc.
        """
        balance = await self.get_balance()
        utxos = await self.get_utxos()

        return {
            "p2sh_address": self._p2sh_address,
            "balance_sats": balance,
            "balance_bch": balance / 100_000_000,
            "utxo_count": len(utxos),
            "utxos": [
                {"txid": u.txid, "vout": u.vout, "value": u.value}
                for u in utxos
            ],
            "network": self._network,
            "qube_pubkey": self.qube_pubkey_hex,
            "owner_pubkey": self.owner_pubkey_hex,
        }

    async def _get_transaction_history_fulcrum(
        self,
        limit: int = 50,
        offset: int = 0
    ) -> Optional[Dict[str, Any]]:
        """
        Get transaction history from Fulcrum API (faster indexing).

        Returns:
            Dict with transactions, or None if request fails
        """
        import time

        try:
            addr = self._p2sh_address.split(":")[-1] if ":" in self._p2sh_address else self._p2sh_address
            full_addr = f"bitcoincash:{addr}"

            async with aiohttp.ClientSession() as session:
                # Get transaction list
                url = f"{FULCRUM_API}/address/transactions/{addr}"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status != 200:
                        return None
                    data = await resp.json()

                    if "txs" not in data:
                        return None

                    # txs is array of [tx_dict, index] pairs
                    raw_txs = data["txs"]
                    all_txs = []
                    for item in raw_txs:
                        if isinstance(item, list) and len(item) > 0:
                            # First element is the transaction dict
                            tx = item[0] if isinstance(item[0], dict) else None
                            if tx:
                                all_txs.append(tx)
                        elif isinstance(item, dict):
                            all_txs.append(item)

                    total_count = len(all_txs)
                    paginated_txs = all_txs[offset:offset + limit]

                    if not paginated_txs:
                        return {
                            "transactions": [],
                            "total_count": total_count,
                            "has_more": False
                        }

                    transactions = []

                    for tx in paginated_txs:
                        txid = tx.get("txid", "")

                        # Calculate net amount for this wallet
                        # Fulcrum format: vin/vout arrays
                        received = 0
                        sent = 0

                        for vout in tx.get("vout", []):
                            script_pubkey = vout.get("scriptPubKey", {})
                            addresses = script_pubkey.get("addresses", [])
                            # Check both short and full address formats
                            if addr in addresses or full_addr in addresses:
                                # vout.value is in BCH, convert to satoshis
                                received += int(float(vout.get("value", 0)) * 100_000_000)

                        for vin in tx.get("vin", []):
                            # Fulcrum uses cashAddress field for inputs
                            vin_addr = vin.get("cashAddress", vin.get("addr", ""))
                            vin_addr_short = vin_addr.split(":")[-1] if ":" in vin_addr else vin_addr
                            if vin_addr_short == addr or vin_addr == full_addr:
                                # valueSat might be in BCH format (float) or satoshis (int)
                                value_sat = vin.get("valueSat", 0)
                                if isinstance(value_sat, float) and value_sat < 1000:
                                    # It's in BCH, convert to satoshis
                                    sent += int(value_sat * 100_000_000)
                                else:
                                    sent += int(value_sat)

                        net_amount = received - sent

                        # Determine transaction type
                        if net_amount > 0:
                            tx_type = "deposit"
                            counterparty = None
                            for vin in tx.get("vin", []):
                                vin_addr = vin.get("cashAddress", vin.get("addr", ""))
                                vin_addr_short = vin_addr.split(":")[-1] if ":" in vin_addr else vin_addr
                                if vin_addr and vin_addr_short != addr:
                                    counterparty = vin_addr if ":" in vin_addr else f"bitcoincash:{vin_addr}"
                                    break
                            fee = 0
                        else:
                            tx_type = "withdrawal"
                            counterparty = None
                            for vout in tx.get("vout", []):
                                addrs = vout.get("scriptPubKey", {}).get("addresses", [])
                                for a in addrs:
                                    a_short = a.split(":")[-1] if ":" in a else a
                                    # Find non-wallet, non-change output (q addresses are regular, p are P2SH)
                                    if a_short != addr and a_short.startswith("q"):
                                        counterparty = a if ":" in a else f"bitcoincash:{a}"
                                        break
                                if counterparty:
                                    break
                            fee = int(float(tx.get("fees", 0)) * 100_000_000) if tx.get("fees") else 0

                        # Parse timestamp
                        block_time = tx.get("time", tx.get("blocktime"))
                        timestamp = float(block_time) if block_time else time.time()

                        block_height = tx.get("blockheight")
                        confirmations = tx.get("confirmations", 0)

                        tx_entry = BlockchainTxInfo(
                            txid=txid,
                            tx_type=tx_type,
                            amount=net_amount,
                            fee=fee,
                            counterparty=counterparty,
                            timestamp=timestamp,
                            block_height=block_height,
                            confirmations=confirmations
                        )
                        transactions.append(tx_entry)

                    logger.debug("get_tx_history_from_fulcrum", count=len(transactions))

                    return {
                        "transactions": [tx.to_dict() for tx in transactions],
                        "total_count": total_count,
                        "has_more": offset + limit < total_count
                    }

        except Exception as e:
            logger.debug("fulcrum_tx_history_failed", error=str(e))
            return None

    async def get_transaction_history(
        self,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Get transaction history from blockchain.

        Tries Fulcrum API first (faster indexing), falls back to Blockchair.

        Args:
            limit: Maximum number of transactions to return
            offset: Pagination offset

        Returns:
            Dict with:
            - transactions: List of BlockchainTxInfo dicts
            - total_count: Total transaction count for address
            - has_more: Whether more transactions exist
        """
        import time

        # Try Fulcrum first (faster indexing)
        fulcrum_result = await self._get_transaction_history_fulcrum(limit, offset)
        if fulcrum_result is not None and fulcrum_result.get("transactions"):
            return fulcrum_result

        # Fallback to Blockchair
        try:
            async with aiohttp.ClientSession() as session:
                # First, get address dashboard with transaction list
                url = f"{BLOCKCHAIR_API}/dashboards/address/{self._p2sh_address}"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    data = await resp.json()

                    if "data" not in data or self._p2sh_address not in data["data"]:
                        return {
                            "transactions": [],
                            "total_count": 0,
                            "has_more": False
                        }

                    addr_data = data["data"][self._p2sh_address]
                    all_txids = addr_data.get("transactions", [])
                    total_count = len(all_txids)

                    # Apply pagination to txid list
                    paginated_txids = all_txids[offset:offset + limit]

                    if not paginated_txids:
                        return {
                            "transactions": [],
                            "total_count": total_count,
                            "has_more": False
                        }

                    # Batch fetch transaction details (max 10 per request)
                    transactions = []
                    current_block = data.get("context", {}).get("state", 0)

                    # Blockchair returns addresses without prefix, so extract just the hash part
                    # e.g., "bitcoincash:pplayxh..." -> "pplayxh..."
                    wallet_addr_short = self._p2sh_address.split(":")[-1] if ":" in self._p2sh_address else self._p2sh_address

                    for i in range(0, len(paginated_txids), 10):
                        batch = paginated_txids[i:i + 10]
                        txids_param = ",".join(batch)
                        tx_url = f"{BLOCKCHAIR_API}/dashboards/transactions/{txids_param}"

                        async with session.get(tx_url, timeout=aiohttp.ClientTimeout(total=15)) as tx_resp:
                            tx_data = await tx_resp.json()

                            if "data" not in tx_data:
                                continue

                            for txid in batch:
                                if txid not in tx_data["data"]:
                                    continue

                                tx_info = tx_data["data"][txid]
                                tx = tx_info.get("transaction", {})
                                inputs = tx_info.get("inputs", [])
                                outputs = tx_info.get("outputs", [])

                                # Calculate amounts for this wallet
                                # Note: Blockchair returns addresses without prefix
                                received = sum(
                                    o.get("value", 0)
                                    for o in outputs
                                    if o.get("recipient") == wallet_addr_short
                                )
                                sent = sum(
                                    i.get("value", 0)
                                    for i in inputs
                                    if i.get("recipient") == wallet_addr_short
                                )

                                net_amount = received - sent

                                # Determine transaction type
                                if net_amount > 0:
                                    tx_type = "deposit"
                                    # Find sender (first non-wallet input)
                                    counterparty = next(
                                        (f"bitcoincash:{i.get('recipient')}" for i in inputs
                                         if i.get("recipient") and i.get("recipient") != wallet_addr_short),
                                        None
                                    )
                                    fee = 0  # We didn't pay the fee on deposits
                                else:
                                    tx_type = "withdrawal"
                                    # Find recipient (first non-wallet, non-change output)
                                    counterparty = next(
                                        (f"bitcoincash:{o.get('recipient')}" for o in outputs
                                         if o.get("recipient") and o.get("recipient") != wallet_addr_short),
                                        None
                                    )
                                    fee = tx.get("fee", 0)

                                # Parse timestamp
                                block_time = tx.get("time")
                                if block_time:
                                    try:
                                        from datetime import datetime
                                        # Blockchair returns "YYYY-MM-DD HH:MM:SS" format
                                        # Replace space with T for ISO format compatibility
                                        iso_time = block_time.replace(" ", "T").replace("Z", "+00:00")
                                        if "+" not in iso_time and "Z" not in block_time:
                                            iso_time += "+00:00"  # Assume UTC
                                        dt = datetime.fromisoformat(iso_time)
                                        timestamp = dt.timestamp()
                                    except Exception:
                                        timestamp = time.time()
                                else:
                                    timestamp = time.time()

                                raw_block_id = tx.get("block_id")
                                # block_id is -1 or None for unconfirmed transactions
                                block_height = raw_block_id if raw_block_id and raw_block_id > 0 else None
                                confirmations = 0
                                if block_height and current_block:
                                    confirmations = max(0, current_block - block_height + 1)

                                tx_entry = BlockchainTxInfo(
                                    txid=txid,
                                    tx_type=tx_type,
                                    amount=net_amount,
                                    fee=fee,
                                    counterparty=counterparty,
                                    timestamp=timestamp,
                                    block_height=block_height,
                                    confirmations=confirmations
                                )
                                transactions.append(tx_entry)

                    return {
                        "transactions": [tx.to_dict() for tx in transactions],
                        "total_count": total_count,
                        "has_more": offset + limit < total_count
                    }

        except Exception as e:
            logger.error("get_transaction_history_failed", error=str(e))
            return {
                "transactions": [],
                "total_count": 0,
                "has_more": False,
                "error": str(e)
            }

    async def get_transaction_info(self, txid: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific transaction by txid.

        Used to verify recently broadcast transactions exist on the blockchain.

        Args:
            txid: Transaction ID to look up

        Returns:
            Dict with transaction info or None if not found
        """
        import aiohttp

        # Try Fulcrum/Electrum first
        try:
            electrum_servers = [
                "wss://bch.imaginary.cash:50004",
                "wss://electroncash.de:60002",
            ]

            for server_url in electrum_servers:
                try:
                    import websockets
                    async with websockets.connect(server_url, close_timeout=5) as ws:
                        # Get transaction
                        request = {
                            "jsonrpc": "2.0",
                            "id": 1,
                            "method": "blockchain.transaction.get",
                            "params": [txid, True]  # verbose=True for decoded tx
                        }
                        await ws.send(json.dumps(request))
                        response = await asyncio.wait_for(ws.recv(), timeout=10)
                        result = json.loads(response)

                        if "result" in result and result["result"]:
                            tx_data = result["result"]
                            return {
                                "txid": txid,
                                "confirmations": tx_data.get("confirmations", 0),
                                "block_height": tx_data.get("blockheight"),
                                "exists": True
                            }
                except Exception as e:
                    logger.debug(f"Fulcrum tx lookup failed for {server_url}: {e}")
                    continue

        except Exception as e:
            logger.debug(f"Electrum tx lookup failed: {e}")

        # Fallback to Blockchair
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://api.blockchair.com/bitcoin-cash/dashboards/transaction/{txid}"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        tx_data = data.get("data", {}).get(txid, {}).get("transaction", {})
                        if tx_data:
                            block_id = tx_data.get("block_id")
                            # block_id is -1 for unconfirmed
                            block_height = block_id if block_id and block_id > 0 else None

                            # Get current block height for confirmations
                            confirmations = 0
                            if block_height:
                                context = data.get("context", {})
                                current_block = context.get("state")
                                if current_block:
                                    confirmations = max(0, current_block - block_height + 1)

                            return {
                                "txid": txid,
                                "confirmations": confirmations,
                                "block_height": block_height,
                                "exists": True
                            }
        except Exception as e:
            logger.debug(f"Blockchair tx lookup failed: {e}")

        return None

    # =========================================================================
    # TRANSACTION CREATION
    # =========================================================================

    def _select_utxos(
        self,
        utxos: List[UTXO],
        target_amount: int,
        fee_per_byte: int = DEFAULT_FEE_PER_BYTE
    ) -> Tuple[List[UTXO], int]:
        """
        Select UTXOs to cover target amount plus fees.

        Simple algorithm: sort by value descending, take until covered.

        Returns:
            (selected_utxos, estimated_fee)
        """
        # Sort by value descending (prefer larger UTXOs)
        sorted_utxos = sorted(utxos, key=lambda u: u.value, reverse=True)

        selected = []
        total = 0

        for utxo in sorted_utxos:
            selected.append(utxo)
            total += utxo.value

            # Estimate fee with current selection
            tx_size = estimate_tx_size(len(selected), 2, "multisig")  # 2 outputs (send + change)
            fee = tx_size * fee_per_byte

            if total >= target_amount + fee:
                return selected, fee

        # Not enough funds
        raise ValueError(
            f"Insufficient funds. Have {total} sats, need {target_amount} + fee"
        )

    def create_unsigned_transaction(
        self,
        outputs: List[TxOutput],
        fee_per_byte: int = DEFAULT_FEE_PER_BYTE,
        utxos: Optional[List[UTXO]] = None
    ) -> UnsignedTransaction:
        """
        Create an unsigned transaction.

        Args:
            outputs: List of outputs (address, value)
            fee_per_byte: Fee rate in sats/byte
            utxos: UTXOs to spend (if None, must call with await and use get_utxos)

        Returns:
            UnsignedTransaction ready for signing
        """
        if not utxos:
            raise ValueError("UTXOs must be provided (use create_unsigned_transaction_async for auto-fetch)")

        # Validate outputs
        total_output = sum(o.value for o in outputs)
        for out in outputs:
            if out.value < DUST_LIMIT:
                raise ValueError(f"Output {out.value} sats is below dust limit ({DUST_LIMIT})")

        # Select UTXOs
        selected_utxos, fee = self._select_utxos(utxos, total_output, fee_per_byte)
        total_input = sum(u.value for u in selected_utxos)

        # Add change output if needed
        change = total_input - total_output - fee
        final_outputs = list(outputs)

        if change > DUST_LIMIT:
            final_outputs.append(TxOutput(address=self._p2sh_address, value=change))
        elif change > 0:
            # Change too small, add to fee
            fee += change

        return UnsignedTransaction(
            utxos=selected_utxos,
            outputs=final_outputs,
            redeem_script=self._redeem_script,
            fee=fee
        )

    async def create_unsigned_transaction_async(
        self,
        outputs: List[TxOutput],
        fee_per_byte: int = DEFAULT_FEE_PER_BYTE
    ) -> UnsignedTransaction:
        """
        Create an unsigned transaction, fetching UTXOs automatically.
        """
        utxos = await self.get_utxos()
        if not utxos:
            raise ValueError("No UTXOs available")

        return self.create_unsigned_transaction(outputs, fee_per_byte, utxos)

    # =========================================================================
    # SIGNING (QUBE)
    # =========================================================================

    def sign_as_qube(self, unsigned_tx: UnsignedTransaction) -> bytes:
        """
        Sign transaction as Qube (for 2-of-2 multisig path).

        The Qube signs first, then the owner must co-sign to broadcast.

        Args:
            unsigned_tx: The unsigned transaction

        Returns:
            Qube's signature (DER + sighash byte)
        """
        if len(unsigned_tx.utxos) != 1:
            raise ValueError("Currently only single-input transactions supported")

        utxo = unsigned_tx.utxos[0]

        # Prepare for sighash
        inputs = [(utxo.txid, utxo.vout, utxo.value, utxo.script_pubkey)]
        output_data = [
            (out.value, address_to_script_pubkey(out.address))
            for out in unsigned_tx.outputs
        ]

        # Calculate sighash
        sighash = calculate_sighash_forkid(
            tx_version=2,
            inputs=inputs,
            outputs=output_data,
            input_idx=0,
            redeem_script=self._redeem_script
        )

        # Sign with Qube's key
        return sign_sighash(sighash, self._qube_privkey)

    def propose_transaction(
        self,
        outputs: List[TxOutput],
        utxos: List[UTXO],
        memo: Optional[str] = None
    ) -> ProposedTransaction:
        """
        Propose a transaction (Qube signs, awaits owner approval).

        Args:
            outputs: Where to send funds
            utxos: Available UTXOs
            memo: Reason for the transaction

        Returns:
            ProposedTransaction with Qube's signature
        """
        import time
        import hashlib

        unsigned_tx = self.create_unsigned_transaction(outputs, utxos=utxos)
        qube_sig = self.sign_as_qube(unsigned_tx)

        # Generate unique ID
        tx_id = hashlib.sha256(
            f"{time.time()}{qube_sig.hex()}".encode()
        ).hexdigest()[:16]

        return ProposedTransaction(
            tx_id=tx_id,
            unsigned_tx=unsigned_tx,
            qube_signature=qube_sig,
            created_at=time.time(),
            memo=memo
        )

    # =========================================================================
    # SIGNING (OWNER) & BROADCASTING
    # =========================================================================

    def finalize_multisig(
        self,
        unsigned_tx: UnsignedTransaction,
        qube_signature: bytes,
        owner_privkey: bytes
    ) -> str:
        """
        Finalize 2-of-2 multisig transaction (owner co-signs).

        Args:
            unsigned_tx: The unsigned transaction
            qube_signature: Qube's signature
            owner_privkey: Owner's 32-byte private key

        Returns:
            Signed transaction hex
        """
        if len(unsigned_tx.utxos) != 1:
            raise ValueError("Currently only single-input transactions supported")

        utxo = unsigned_tx.utxos[0]

        # Prepare for sighash
        inputs = [(utxo.txid, utxo.vout, utxo.value, utxo.script_pubkey)]
        output_data = [
            (out.value, address_to_script_pubkey(out.address))
            for out in unsigned_tx.outputs
        ]

        # Calculate sighash (same as Qube used)
        sighash = calculate_sighash_forkid(
            tx_version=2,
            inputs=inputs,
            outputs=output_data,
            input_idx=0,
            redeem_script=self._redeem_script
        )

        # Owner signs
        owner_sig = sign_sighash(sighash, owner_privkey)

        # Build final transaction
        return build_p2sh_spending_tx(
            utxos=unsigned_tx.utxos,
            outputs=unsigned_tx.outputs,
            redeem_script=self._redeem_script,
            signatures=[owner_sig, qube_signature],
            spending_path="multisig"
        ).hex()

    def spend_owner_only(
        self,
        unsigned_tx: UnsignedTransaction,
        owner_privkey: bytes
    ) -> str:
        """
        Spend using owner-only path (IF branch).

        Owner can withdraw without Qube involvement.

        Args:
            unsigned_tx: The unsigned transaction
            owner_privkey: Owner's 32-byte private key

        Returns:
            Signed transaction hex
        """
        if len(unsigned_tx.utxos) != 1:
            raise ValueError("Currently only single-input transactions supported")

        utxo = unsigned_tx.utxos[0]

        # Prepare for sighash
        inputs = [(utxo.txid, utxo.vout, utxo.value, utxo.script_pubkey)]
        output_data = [
            (out.value, address_to_script_pubkey(out.address))
            for out in unsigned_tx.outputs
        ]

        # Calculate sighash
        sighash = calculate_sighash_forkid(
            tx_version=2,
            inputs=inputs,
            outputs=output_data,
            input_idx=0,
            redeem_script=self._redeem_script
        )

        # Owner signs
        owner_sig = sign_sighash(sighash, owner_privkey)

        # Build transaction with owner-only path
        return build_p2sh_spending_tx(
            utxos=unsigned_tx.utxos,
            outputs=unsigned_tx.outputs,
            redeem_script=self._redeem_script,
            signatures=[owner_sig],
            spending_path="owner_only"
        ).hex()

    # =========================================================================
    # BROADCAST
    # =========================================================================

    async def broadcast(self, tx_hex: str) -> str:
        """
        Broadcast signed transaction to the network.

        Args:
            tx_hex: Signed transaction in hex

        Returns:
            Transaction ID (txid)

        Raises:
            Exception: If broadcast fails
        """
        async with aiohttp.ClientSession() as session:
            url = f"{BLOCKCHAIR_API}/push/transaction"
            async with session.post(url, data={"data": tx_hex}) as resp:
                result = await resp.json()

                if result.get("context", {}).get("code") == 200:
                    txid = result["data"]["transaction_hash"]
                    logger.info("transaction_broadcast", txid=txid)
                    # Invalidate balance cache so next fetch gets updated data
                    self.invalidate_balance_cache()
                    return txid
                else:
                    error = result.get("context", {}).get("error", "Unknown error")
                    logger.error("broadcast_failed", error=error)
                    raise Exception(f"Broadcast failed: {error}")

    # =========================================================================
    # HIGH-LEVEL OPERATIONS
    # =========================================================================

    async def approve_and_broadcast(
        self,
        proposed_tx: ProposedTransaction,
        owner_privkey: bytes
    ) -> str:
        """
        Owner approves a Qube-proposed transaction and broadcasts.

        Args:
            proposed_tx: Transaction proposed by Qube
            owner_privkey: Owner's private key

        Returns:
            Transaction ID
        """
        tx_hex = self.finalize_multisig(
            proposed_tx.unsigned_tx,
            proposed_tx.qube_signature,
            owner_privkey
        )

        return await self.broadcast(tx_hex)

    async def owner_withdraw(
        self,
        to_address: str,
        amount_sats: int,
        owner_privkey: bytes
    ) -> str:
        """
        Owner withdraws directly (no Qube involvement).

        Uses the IF branch (owner-only spending path).

        Args:
            to_address: Destination address
            amount_sats: Amount in satoshis
            owner_privkey: Owner's private key

        Returns:
            Transaction ID
        """
        outputs = [TxOutput(address=to_address, value=amount_sats)]
        unsigned_tx = await self.create_unsigned_transaction_async(outputs)
        tx_hex = self.spend_owner_only(unsigned_tx, owner_privkey)

        return await self.broadcast(tx_hex)

    async def owner_withdraw_all(
        self,
        to_address: str,
        owner_privkey: bytes
    ) -> str:
        """
        Owner withdraws entire balance.

        Args:
            to_address: Destination address
            owner_privkey: Owner's private key

        Returns:
            Transaction ID
        """
        utxos = await self.get_utxos()
        if not utxos:
            raise ValueError("No funds to withdraw")

        total = sum(u.value for u in utxos)

        # Estimate fee for owner-only tx
        tx_size = estimate_tx_size(len(utxos), 1, "owner_only")
        fee = tx_size * DEFAULT_FEE_PER_BYTE

        send_amount = total - fee
        if send_amount < DUST_LIMIT:
            raise ValueError(f"Balance too low to withdraw (after fees)")

        outputs = [TxOutput(address=to_address, value=send_amount)]
        unsigned_tx = UnsignedTransaction(
            utxos=utxos,
            outputs=outputs,
            redeem_script=self._redeem_script,
            fee=fee
        )

        tx_hex = self.spend_owner_only(unsigned_tx, owner_privkey)
        return await self.broadcast(tx_hex)

    # =========================================================================
    # SERIALIZATION
    # =========================================================================

    def to_dict(self) -> dict:
        """Serialize wallet info (no private keys!)"""
        return {
            "p2sh_address": self._p2sh_address,
            "redeem_script_hex": self.redeem_script_hex,
            "script_hash": self._script_hash,
            "qube_pubkey": self.qube_pubkey_hex,
            "owner_pubkey": self.owner_pubkey_hex,
            "network": self._network,
        }

    @classmethod
    def from_qube(cls, qube, owner_pubkey_hex: str, network: str = "mainnet") -> "QubeWallet":
        """
        Create wallet from a Qube instance.

        Args:
            qube: Qube instance with private_key attribute
            owner_pubkey_hex: Owner's public key
            network: Network name

        Returns:
            QubeWallet instance
        """
        # Extract raw private key bytes from Qube's cryptography key
        private_key = qube.private_key

        # Handle cryptography library's EllipticCurvePrivateKey
        if hasattr(private_key, 'private_numbers'):
            # cryptography library key
            private_value = private_key.private_numbers().private_value
            privkey_bytes = private_value.to_bytes(32, 'big')
        elif hasattr(private_key, 'secret'):
            # ecdsa library key
            privkey_bytes = private_key.secret
        elif isinstance(private_key, bytes) and len(private_key) == 32:
            # Already raw bytes
            privkey_bytes = private_key
        else:
            raise ValueError(f"Unsupported private key type: {type(private_key)}")

        return cls(privkey_bytes, owner_pubkey_hex, network)


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def validate_pubkey(pubkey_hex: str) -> bool:
    """
    Validate a compressed public key.

    Args:
        pubkey_hex: Public key in hex format

    Returns:
        True if valid compressed pubkey
    """
    if not pubkey_hex or len(pubkey_hex) != 66:
        return False
    if not pubkey_hex.startswith(('02', '03')):
        return False
    try:
        bytes.fromhex(pubkey_hex)
        return True
    except ValueError:
        return False


def validate_address(address: str) -> bool:
    """
    Validate a CashAddr address.

    Args:
        address: CashAddr string

    Returns:
        True if valid
    """
    from crypto.bch_script import decode_cashaddr
    try:
        decode_cashaddr(address)
        return True
    except Exception:
        return False
