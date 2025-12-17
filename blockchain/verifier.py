"""
NFT Ownership Verifier

Verifies CashToken NFT ownership using Chaingraph GraphQL API.
From docs/10_Blockchain_Integration.md Section 7.4.1
"""

import aiohttp
from typing import Optional, Dict, Any, List

from utils.logging import get_logger
from monitoring.metrics import MetricsRecorder

logger = get_logger(__name__)


class NFTVerifier:
    """
    Verify CashToken NFT ownership via Chaingraph

    Unlike ERC-721 which has a central registry, CashTokens are UTXO-based,
    so we query the UTXO set for tokens with the target category.

    Uses Chaingraph GraphQL API for Bitcoin Cash UTXO lookups.
    """

    def __init__(
        self,
        chaingraph_url: str = "https://gql.chaingraph.pat.mn/v1/graphql"
    ):
        """
        Initialize NFT verifier

        Args:
            chaingraph_url: Chaingraph GraphQL endpoint
        """
        self.chaingraph_url = chaingraph_url

        logger.info("nft_verifier_initialized", endpoint=chaingraph_url)

    async def verify_ownership(
        self,
        category_id: str,
        owner_address: str
    ) -> bool:
        """
        Verify ownership of a CashToken NFT
        From docs Section 7.4.1

        Args:
            category_id: CashToken category ID (32-byte hex)
            owner_address: Bitcoin Cash address (cashaddr format)

        Returns:
            True if address owns an NFT with this category
        """
        try:
            logger.info(
                "verifying_nft_ownership",
                category_id=category_id[:16] + "...",
                owner=owner_address
            )

            # Convert cashaddr to locking bytecode for query
            locking_bytecode = await self._address_to_locking_bytecode(owner_address)

            if not locking_bytecode:
                logger.error("address_conversion_failed", address=owner_address)
                return False

            # Query Chaingraph for unspent outputs
            outputs = await self._query_chaingraph(category_id, locking_bytecode)

            if outputs:
                logger.info(
                    "nft_ownership_verified",
                    category_id=category_id[:16] + "...",
                    owner=owner_address,
                    utxos_found=len(outputs)
                )

                MetricsRecorder.record_blockchain_event("nft_verified", category_id)

                return True
            else:
                logger.info(
                    "nft_ownership_not_found",
                    category_id=category_id[:16] + "...",
                    owner=owner_address
                )

                return False

        except Exception as e:
            logger.error(
                "nft_verification_failed",
                category_id=category_id[:16] + "...",
                error=str(e),
                exc_info=True
            )
            return False

    async def _query_chaingraph(
        self,
        category_id: str,
        locking_bytecode: str
    ) -> List[Dict[str, Any]]:
        """
        Query Chaingraph GraphQL API

        Args:
            category_id: Token category ID
            locking_bytecode: Locking bytecode hex

        Returns:
            List of matching outputs
        """
        query = """
        query GetTokenOwnership($category: bytea!, $locking_bytecode: bytea!) {
            output(where: {
                token_category: {_eq: $category}
                locking_bytecode: {_eq: $locking_bytecode}
                _not: {spent_by: {}}
            }) {
                value_satoshis
                token_category
                fungible_token_amount
                nonfungible_token_capability
                nonfungible_token_commitment
                transaction_hash
                output_index
            }
        }
        """

        variables = {
            "category": f"\\x{category_id}",
            "locking_bytecode": f"\\x{locking_bytecode}"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.chaingraph_url,
                    json={
                        "query": query,
                        "variables": variables
                    },
                    headers={"Content-Type": "application/json"}
                ) as resp:
                    if resp.status != 200:
                        logger.error(
                            "chaingraph_request_failed",
                            status=resp.status
                        )
                        return []

                    data = await resp.json()

                    if 'errors' in data:
                        logger.error(
                            "chaingraph_query_error",
                            errors=data['errors']
                        )
                        return []

                    outputs = data.get('data', {}).get('output', [])

                    logger.debug(
                        "chaingraph_query_complete",
                        outputs_found=len(outputs)
                    )

                    return outputs

        except Exception as e:
            logger.error("chaingraph_request_exception", error=str(e))
            return []

    async def _address_to_locking_bytecode(self, address: str) -> Optional[str]:
        """
        Convert BCH address to locking bytecode hex

        Args:
            address: Bitcoin Cash address (cashaddr format)

        Returns:
            Locking bytecode hex or None if conversion fails
        """
        try:
            from bitcash.cashaddress import Address

            # Parse the cashaddr
            addr = Address.from_string(address)

            # Get the payload (hash160) as bytes
            payload = bytes(addr.payload)

            # Construct locking bytecode for P2PKH
            # Format: OP_DUP OP_HASH160 <20 bytes> OP_EQUALVERIFY OP_CHECKSIG
            locking_bytecode = "76a914" + payload.hex() + "88ac"

            logger.debug(
                "address_converted_to_bytecode",
                address=address,
                bytecode=locking_bytecode[:16] + "..."
            )

            return locking_bytecode

        except Exception as e:
            logger.error(
                "address_conversion_failed",
                address=address,
                error=str(e)
            )
            return None

    async def get_nft_details(
        self,
        category_id: str,
        owner_address: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get detailed NFT information

        Args:
            category_id: Token category ID
            owner_address: Owner's BCH address

        Returns:
            NFT details or None if not found
        """
        try:
            locking_bytecode = await self._address_to_locking_bytecode(owner_address)

            if not locking_bytecode:
                return None

            outputs = await self._query_chaingraph(category_id, locking_bytecode)

            if not outputs:
                return None

            # Return first output's details
            output = outputs[0]

            return {
                "category_id": category_id,
                "owner_address": owner_address,
                "value_satoshis": output.get("value_satoshis"),
                "nft_commitment": output.get("nonfungible_token_commitment"),
                "nft_capability": output.get("nonfungible_token_capability"),
                "transaction_hash": output.get("transaction_hash"),
                "output_index": output.get("output_index"),
                "total_utxos": len(outputs)
            }

        except Exception as e:
            logger.error("get_nft_details_failed", error=str(e))
            return None

    async def list_all_nfts_by_category(
        self,
        category_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List all NFTs for a given category

        Args:
            category_id: Token category ID
            limit: Maximum number of results

        Returns:
            List of NFT details
        """
        query = """
        query GetAllNFTs($category: String!, $limit: Int!) {
            output(
                where: {
                    token_category: {_eq: $category}
                    spent_by: {_is_null: true}
                }
                limit: $limit
            ) {
                value_satoshis
                token_category
                nft_commitment_hex
                nft_capability
                transaction_hash
                output_index
                locking_bytecode_hex
            }
        }
        """

        variables = {
            "category": category_id,
            "limit": limit
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.chaingraph_url,
                    json={
                        "query": query,
                        "variables": variables
                    }
                ) as resp:
                    data = await resp.json()

                    outputs = data.get('data', {}).get('output', [])

                    logger.info(
                        "nfts_listed",
                        category_id=category_id[:16] + "...",
                        count=len(outputs)
                    )

                    return outputs

        except Exception as e:
            logger.error("list_nfts_failed", error=str(e))
            return []
