"""
Memory Market System

Decentralized marketplace for trading knowledge between Qubes.
From docs/07_Shared_Memory_Architecture.md Section 4.3
"""

import json
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
from enum import Enum

from shared_memory.permissions import MemoryPermission, PermissionLevel
from utils.logging import get_logger
from core.exceptions import QubesError

logger = get_logger(__name__)


class ListingStatus(Enum):
    """Status of memory market listing"""
    ACTIVE = "active"
    SOLD_OUT = "sold_out"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class MemoryMarketListing:
    """Listing for selling memory blocks in the marketplace"""

    def __init__(
        self,
        seller_qube_id: str,
        memory_block_hashes: List[str],
        description: str,
        price: float,
        expertise_domain: str,
        listing_id: Optional[str] = None
    ):
        """
        Initialize memory market listing

        Args:
            seller_qube_id: Qube ID selling the memories
            memory_block_hashes: Hashes of memory blocks (not content)
            description: Description of the knowledge being sold
            price: Price in tokens/BCH
            expertise_domain: Domain/category (e.g., "quantum_computing", "machine_learning")
            listing_id: Optional listing ID (generated if not provided)
        """
        self.listing_id = listing_id or str(uuid.uuid4())
        self.seller_qube_id = seller_qube_id
        self.memory_block_hashes = memory_block_hashes
        self.description = description
        self.price = price
        self.expertise_domain = expertise_domain
        self.encrypted_preview: Optional[str] = None
        self.buyers: List[Dict[str, Any]] = []
        self.created_at = datetime.now()
        self.expires_at: Optional[datetime] = None
        self.signature: Optional[str] = None
        self.status = ListingStatus.ACTIVE
        self.max_sales: Optional[int] = None  # None = unlimited
        self.block_numbers: List[int] = []  # Actual block numbers (seller knows)

        logger.info(
            "memory_listing_created",
            listing_id=self.listing_id,
            seller=seller_qube_id,
            blocks=len(memory_block_hashes),
            price=price,
            domain=expertise_domain
        )

    def set_preview(self, preview_text: str):
        """
        Set encrypted preview of the memories

        Args:
            preview_text: Preview text (will be stored as-is or encrypted)
        """
        self.encrypted_preview = preview_text
        logger.debug("listing_preview_set", listing_id=self.listing_id)

    def set_expiry(self, days: int):
        """
        Set listing expiry

        Args:
            days: Days until expiry
        """
        from datetime import timedelta
        self.expires_at = datetime.now() + timedelta(days=days)
        logger.debug(
            "listing_expiry_set",
            listing_id=self.listing_id,
            expires_at=self.expires_at.isoformat()
        )

    def set_max_sales(self, max_sales: int):
        """
        Set maximum number of sales

        Args:
            max_sales: Maximum sales allowed
        """
        self.max_sales = max_sales
        logger.debug("listing_max_sales_set", listing_id=self.listing_id, max_sales=max_sales)

    def is_available(self) -> bool:
        """Check if listing is available for purchase"""
        if self.status != ListingStatus.ACTIVE:
            return False

        if self.expires_at and datetime.now() > self.expires_at:
            self.status = ListingStatus.EXPIRED
            return False

        if self.max_sales and len(self.buyers) >= self.max_sales:
            self.status = ListingStatus.SOLD_OUT
            return False

        return True

    async def purchase(
        self,
        buyer_qube_id: str,
        payment_proof: Dict[str, Any],
        seller_private_key_path: Path
    ) -> Optional[MemoryPermission]:
        """
        Process purchase of memory listing (async method)

        Args:
            buyer_qube_id: Qube ID purchasing
            payment_proof: Payment verification data (blockchain tx hash, etc.)
            seller_private_key_path: Seller's private key for signing permission

        Returns:
            MemoryPermission if purchase successful, None otherwise
        """
        if not self.is_available():
            logger.warning(
                "purchase_failed_not_available",
                listing_id=self.listing_id,
                status=self.status.value
            )
            return None

        # Verify payment
        if not await self._verify_payment(payment_proof):
            logger.warning(
                "purchase_failed_invalid_payment",
                listing_id=self.listing_id,
                buyer=buyer_qube_id
            )
            return None

        # Create permission for buyer
        permission = MemoryPermission(
            granted_by=self.seller_qube_id,
            granted_to=buyer_qube_id
        )

        permission.grant_access(
            block_numbers=self.block_numbers,
            permission_level=PermissionLevel.READ  # Buyers get read-only access
        )

        permission.sign_permission(seller_private_key_path)

        # Record purchase
        self.buyers.append({
            "buyer_id": buyer_qube_id,
            "purchased_at": datetime.now().isoformat(),
            "tx_hash": payment_proof.get("tx_hash", ""),
            "amount_paid": payment_proof.get("amount", self.price),
            "permission_id": permission.permission_id
        })

        logger.info(
            "memory_purchased",
            listing_id=self.listing_id,
            buyer=buyer_qube_id,
            price=self.price,
            total_sales=len(self.buyers)
        )

        # Check if sold out
        if self.max_sales and len(self.buyers) >= self.max_sales:
            self.status = ListingStatus.SOLD_OUT

        return permission

    async def _verify_payment(self, payment_proof: Dict[str, Any]) -> bool:
        """
        Verify payment proof (async method)

        Args:
            payment_proof: Payment data to verify

        Returns:
            True if payment is valid
        """
        # In a real implementation, this would:
        # 1. Verify blockchain transaction exists
        # 2. Check transaction amount matches price
        # 3. Verify transaction is to seller's address
        # 4. Check transaction is confirmed

        tx_hash = payment_proof.get("tx_hash")
        amount = payment_proof.get("amount", 0)

        if not tx_hash:
            return False

        if amount < self.price:
            logger.warning(
                "payment_insufficient",
                listing_id=self.listing_id,
                expected=self.price,
                received=amount
            )
            return False

        # Verify payment on blockchain
        is_valid = await self._verify_blockchain_payment(tx_hash, amount)

        if is_valid:
            logger.info(
                "payment_verified",
                listing_id=self.listing_id,
                tx_hash=tx_hash,
                amount=amount
            )
        else:
            logger.error(
                "payment_verification_failed",
                listing_id=self.listing_id,
                tx_hash=tx_hash
            )

        return is_valid

    async def _verify_blockchain_payment(self, tx_hash: str, expected_amount: float) -> bool:
        """
        Verify payment on Bitcoin Cash blockchain using Chaingraph

        Args:
            tx_hash: Transaction hash to verify
            expected_amount: Expected payment amount in BCH

        Returns:
            True if payment is valid and confirmed
        """
        try:
            import aiohttp

            # Query Chaingraph for transaction details
            chaingraph_url = "https://gql.chaingraph.pat.mn/v1/graphql"

            query = """
            query GetTransaction($tx_hash: bytea!) {
                transaction(where: {hash: {_eq: $tx_hash}}) {
                    hash
                    block_inclusions {
                        block {
                            height
                            accepted_by {
                                chain {
                                    name
                                }
                            }
                        }
                    }
                    outputs {
                        value_satoshis
                        locking_bytecode_hex
                    }
                }
            }
            """

            variables = {
                "tx_hash": f"\\x{tx_hash}"
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    chaingraph_url,
                    json={"query": query, "variables": variables},
                    headers={"Content-Type": "application/json"}
                ) as resp:
                    if resp.status != 200:
                        logger.error("chaingraph_request_failed", status=resp.status)
                        return False

                    data = await resp.json()

                    if 'errors' in data:
                        logger.error("chaingraph_query_error", errors=data['errors'])
                        return False

                    transactions = data.get('data', {}).get('transaction', [])

                    if not transactions:
                        logger.error("transaction_not_found", tx_hash=tx_hash)
                        return False

                    tx = transactions[0]

                    # Check if transaction is confirmed (has block inclusions)
                    if not tx.get('block_inclusions'):
                        logger.warning("transaction_unconfirmed", tx_hash=tx_hash)
                        return False

                    # Verify transaction contains payment to seller
                    # Convert seller address to locking bytecode
                    from bitcash.cashaddress import Address

                    # Get seller's address from seller_qube_id
                    # For now, we verify the payment amount exists in outputs
                    expected_satoshis = int(expected_amount * 100_000_000)

                    for output in tx.get('outputs', []):
                        value_satoshis = output.get('value_satoshis', 0)

                        # Check if any output matches expected amount (within 1% tolerance)
                        if abs(value_satoshis - expected_satoshis) <= (expected_satoshis * 0.01):
                            logger.info(
                                "payment_amount_verified",
                                tx_hash=tx_hash,
                                expected=expected_satoshis,
                                actual=value_satoshis
                            )
                            return True

                    logger.error(
                        "payment_amount_mismatch",
                        tx_hash=tx_hash,
                        expected=expected_satoshis,
                        outputs=len(tx.get('outputs', []))
                    )
                    return False

        except Exception as e:
            logger.error(
                "blockchain_verification_error",
                tx_hash=tx_hash,
                error=str(e),
                exc_info=True
            )
            return False

    def cancel(self):
        """Cancel the listing"""
        self.status = ListingStatus.CANCELLED
        logger.info("listing_cancelled", listing_id=self.listing_id)

    def sign_listing(self, private_key_path: Path):
        """
        Sign listing with seller's private key

        Args:
            private_key_path: Path to seller's private key
        """
        from crypto.signing import sign_data

        listing_data = {
            "listing_id": self.listing_id,
            "seller_qube_id": self.seller_qube_id,
            "memory_block_hashes": self.memory_block_hashes,
            "description": self.description,
            "price": self.price,
            "expertise_domain": self.expertise_domain,
            "created_at": self.created_at.isoformat()
        }

        data_str = json.dumps(listing_data, sort_keys=True)
        self.signature = sign_data(data_str.encode(), private_key_path)

        logger.debug("listing_signed", listing_id=self.listing_id)

    def verify_signature(self, public_key: bytes) -> bool:
        """
        Verify listing signature

        Args:
            public_key: Seller's public key

        Returns:
            True if signature is valid
        """
        from crypto.signing import verify_signature

        if not self.signature:
            return False

        listing_data = {
            "listing_id": self.listing_id,
            "seller_qube_id": self.seller_qube_id,
            "memory_block_hashes": self.memory_block_hashes,
            "description": self.description,
            "price": self.price,
            "expertise_domain": self.expertise_domain,
            "created_at": self.created_at.isoformat()
        }

        data_str = json.dumps(listing_data, sort_keys=True)
        return verify_signature(data_str.encode(), self.signature, public_key)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "listing_id": self.listing_id,
            "seller_qube_id": self.seller_qube_id,
            "memory_block_hashes": self.memory_block_hashes,
            "description": self.description,
            "price": self.price,
            "expertise_domain": self.expertise_domain,
            "encrypted_preview": self.encrypted_preview,
            "buyers": self.buyers,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "signature": self.signature,
            "status": self.status.value,
            "max_sales": self.max_sales,
            "block_numbers": self.block_numbers
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryMarketListing":
        """Deserialize from dictionary"""
        listing = cls(
            seller_qube_id=data["seller_qube_id"],
            memory_block_hashes=data["memory_block_hashes"],
            description=data["description"],
            price=data["price"],
            expertise_domain=data["expertise_domain"],
            listing_id=data["listing_id"]
        )

        listing.encrypted_preview = data.get("encrypted_preview")
        listing.buyers = data["buyers"]
        listing.created_at = datetime.fromisoformat(data["created_at"])
        listing.signature = data.get("signature")
        listing.status = ListingStatus(data["status"])
        listing.max_sales = data.get("max_sales")
        listing.block_numbers = data.get("block_numbers", [])

        if data.get("expires_at"):
            listing.expires_at = datetime.fromisoformat(data["expires_at"])

        return listing


class MemoryMarket:
    """Manages the memory marketplace"""

    def __init__(self, market_dir: Path):
        """
        Initialize memory market

        Args:
            market_dir: Directory to store market listings
        """
        self.market_dir = Path(market_dir)
        self.market_dir.mkdir(parents=True, exist_ok=True)

        self.listings: Dict[str, MemoryMarketListing] = {}
        self.load_listings()

        logger.info(
            "memory_market_initialized",
            market_dir=str(market_dir),
            active_listings=len(self.get_active_listings())
        )

    def create_listing(
        self,
        seller_qube_id: str,
        memory_block_hashes: List[str],
        block_numbers: List[int],
        description: str,
        price: float,
        expertise_domain: str,
        preview: Optional[str] = None,
        expiry_days: Optional[int] = None,
        max_sales: Optional[int] = None
    ) -> MemoryMarketListing:
        """
        Create a new marketplace listing

        Args:
            seller_qube_id: Qube ID selling
            memory_block_hashes: Hashes of memory blocks
            block_numbers: Actual block numbers (for permission)
            description: Description of knowledge
            price: Price in tokens
            expertise_domain: Domain/category
            preview: Optional preview text
            expiry_days: Optional days until expiry
            max_sales: Optional maximum sales

        Returns:
            Created MemoryMarketListing
        """
        listing = MemoryMarketListing(
            seller_qube_id=seller_qube_id,
            memory_block_hashes=memory_block_hashes,
            description=description,
            price=price,
            expertise_domain=expertise_domain
        )

        listing.block_numbers = block_numbers

        if preview:
            listing.set_preview(preview)

        if expiry_days:
            listing.set_expiry(expiry_days)

        if max_sales:
            listing.set_max_sales(max_sales)

        self.listings[listing.listing_id] = listing
        self.save_listing(listing)

        logger.info(
            "listing_created",
            listing_id=listing.listing_id,
            seller=seller_qube_id,
            price=price
        )

        return listing

    def get_listing(self, listing_id: str) -> Optional[MemoryMarketListing]:
        """Get listing by ID"""
        return self.listings.get(listing_id)

    def get_active_listings(self) -> List[MemoryMarketListing]:
        """Get all active listings"""
        return [
            listing for listing in self.listings.values()
            if listing.is_available()
        ]

    def search_listings(
        self,
        expertise_domain: Optional[str] = None,
        max_price: Optional[float] = None,
        seller_qube_id: Optional[str] = None
    ) -> List[MemoryMarketListing]:
        """
        Search marketplace listings

        Args:
            expertise_domain: Filter by domain
            max_price: Maximum price filter
            seller_qube_id: Filter by seller

        Returns:
            List of matching listings
        """
        results = self.get_active_listings()

        if expertise_domain:
            results = [
                l for l in results
                if l.expertise_domain == expertise_domain
            ]

        if max_price is not None:
            results = [
                l for l in results
                if l.price <= max_price
            ]

        if seller_qube_id:
            results = [
                l for l in results
                if l.seller_qube_id == seller_qube_id
            ]

        logger.debug(
            "listings_searched",
            domain=expertise_domain,
            max_price=max_price,
            results=len(results)
        )

        return results

    def get_listings_by_seller(self, seller_qube_id: str) -> List[MemoryMarketListing]:
        """Get all listings by a specific seller"""
        return [
            listing for listing in self.listings.values()
            if listing.seller_qube_id == seller_qube_id
        ]

    def get_purchases_by_buyer(self, buyer_qube_id: str) -> List[Dict[str, Any]]:
        """
        Get all purchases made by a buyer

        Args:
            buyer_qube_id: Buyer's Qube ID

        Returns:
            List of purchase records with listing info
        """
        purchases = []

        for listing in self.listings.values():
            for buyer in listing.buyers:
                if buyer["buyer_id"] == buyer_qube_id:
                    purchases.append({
                        "listing_id": listing.listing_id,
                        "seller_id": listing.seller_qube_id,
                        "description": listing.description,
                        "domain": listing.expertise_domain,
                        "price_paid": buyer["amount_paid"],
                        "purchased_at": buyer["purchased_at"],
                        "tx_hash": buyer["tx_hash"],
                        "permission_id": buyer["permission_id"]
                    })

        return purchases

    def save_listing(self, listing: MemoryMarketListing):
        """Save listing to disk"""
        try:
            listing_file = self.market_dir / f"{listing.listing_id}.json"

            with open(listing_file, "w") as f:
                json.dump(listing.to_dict(), f, indent=2)

            logger.debug(
                "listing_saved",
                listing_id=listing.listing_id,
                file=str(listing_file)
            )

        except Exception as e:
            logger.error(
                "listing_save_failed",
                listing_id=listing.listing_id,
                error=str(e),
                exc_info=True
            )
            raise QubesError(f"Failed to save listing: {e}", cause=e)

    def load_listings(self):
        """Load all listings from disk"""
        try:
            for listing_file in self.market_dir.glob("*.json"):
                try:
                    with open(listing_file, "r") as f:
                        data = json.load(f)

                    listing = MemoryMarketListing.from_dict(data)
                    self.listings[listing.listing_id] = listing

                except Exception as e:
                    logger.error(
                        "listing_load_failed",
                        file=str(listing_file),
                        error=str(e)
                    )

            logger.info(
                "listings_loaded",
                count=len(self.listings),
                active=len(self.get_active_listings())
            )

        except Exception as e:
            logger.error("listings_load_failed", error=str(e), exc_info=True)
            self.listings = {}

    def cleanup_expired_listings(self):
        """Remove expired and cancelled listings"""
        to_remove = []

        for listing_id, listing in self.listings.items():
            if listing.status in [ListingStatus.EXPIRED, ListingStatus.CANCELLED]:
                to_remove.append(listing_id)

        for listing_id in to_remove:
            del self.listings[listing_id]
            listing_file = self.market_dir / f"{listing_id}.json"
            if listing_file.exists():
                listing_file.unlink()

        if to_remove:
            logger.info("expired_listings_cleaned", removed=len(to_remove))

    def get_market_stats(self) -> Dict[str, Any]:
        """Get marketplace statistics"""
        active = self.get_active_listings()

        total_sales = sum(len(l.buyers) for l in self.listings.values())
        total_revenue = sum(
            buyer["amount_paid"]
            for listing in self.listings.values()
            for buyer in listing.buyers
        )

        domains = {}
        for listing in active:
            domains[listing.expertise_domain] = domains.get(listing.expertise_domain, 0) + 1

        return {
            "total_listings": len(self.listings),
            "active_listings": len(active),
            "total_sales": total_sales,
            "total_revenue": total_revenue,
            "avg_price": sum(l.price for l in active) / len(active) if active else 0,
            "domains": domains,
            "unique_sellers": len(set(l.seller_qube_id for l in self.listings.values())),
            "unique_buyers": len(set(
                buyer["buyer_id"]
                for listing in self.listings.values()
                for buyer in listing.buyers
            ))
        }
