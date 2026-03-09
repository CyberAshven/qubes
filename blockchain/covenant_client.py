"""
Covenant Minting Client

Replaces OptimizedNFTMinter with permissionless CashScript covenant minting.
Calls covenant/mint-cli.ts via subprocess to build and broadcast mint transactions.

The covenant enforces:
  - Minting token returned to covenant (Output 0)
  - Immutable NFT sent to recipient (Output 1)
  - No other constraints (fees are frontend-level)
"""

import json
import subprocess
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional

from crypto.keys import derive_commitment, serialize_public_key
from core.official_category import OFFICIAL_QUBES_CATEGORY, OFFICIAL_PLATFORM_PUBLIC_KEY
from utils.logging import get_logger

logger = get_logger(__name__)


def _find_covenant_dir() -> Path:
    """Find the covenant/ directory relative to this file."""
    # blockchain/covenant_client.py -> project_root/covenant/
    return Path(__file__).resolve().parent.parent / "covenant"


def _find_tsx() -> str:
    """Find the tsx binary (local node_modules or global)."""
    import sys
    covenant_dir = _find_covenant_dir()
    bin_dir = covenant_dir / "node_modules" / ".bin"

    if sys.platform == "win32":
        # Windows: use .cmd wrapper, or fall back to npx
        local_cmd = bin_dir / "tsx.cmd"
        if local_cmd.exists():
            return str(local_cmd)
    else:
        # Unix: use symlink directly
        local_tsx = bin_dir / "tsx"
        if local_tsx.exists():
            return str(local_tsx)

    return "tsx"  # Fall back to global


class CovenantMinter:
    """
    Mints Qube NFTs via CashScript covenant.

    Drop-in replacement for OptimizedNFTMinter.mint_qube_nft().
    Requires the minting token to already be at the covenant address
    (run covenant/migrate.ts first).
    """

    def __init__(self, network: str = "mainnet", platform_public_key: Optional[str] = None):
        self.network = network
        self.category_id = OFFICIAL_QUBES_CATEGORY
        self.covenant_dir = _find_covenant_dir()

        self.platform_public_key = platform_public_key or OFFICIAL_PLATFORM_PUBLIC_KEY

        logger.info(
            "covenant_minter_initialized",
            category_id=self.category_id[:16] + "...",
            network=network
        )

    def get_minting_stats(self) -> Dict[str, Any]:
        """Return platform info for status/debug endpoints."""
        return {
            "mode": "covenant",
            "network": self.network,
            "category_id": self.category_id,
            "platform_public_key": self.platform_public_key[:16] + "..." if self.platform_public_key else "NOT SET",
            "covenant_dir": str(self.covenant_dir),
        }

    async def prepare_mint_transaction(
        self,
        qube,
        recipient_address: str,
        user_address: str,
        change_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Build an unsigned WalletConnect transaction object for minting.

        The wallet will sign and broadcast this transaction.
        No private keys are needed — only the user's address from WalletConnect.

        Args:
            qube: Qube instance with public_key
            recipient_address: BCH cashaddr (token-aware, bitcoincash:z...)
            user_address: User's BCH address from WalletConnect session
            change_address: Where to send change (defaults to user_address).
                           Should differ from recipient_address to avoid inflating NFT balance.

        Returns:
            {
                "wc_transaction": str (stringified WC transaction object),
                "category_id": str,
                "commitment": str,
                "covenant_address": str,
                "recipient_address": str
            }
        """
        commitment = derive_commitment(qube.public_key)

        logger.info(
            "covenant_preparing_wc_mint",
            qube_id=qube.qube_id,
            commitment=commitment[:16] + "...",
            recipient=recipient_address,
            user_address=user_address[:20] + "..."
        )

        cli_args = {
            "commitment": commitment,
            "recipient_address": recipient_address,
            "user_address": user_address,
            "platform_public_key": self.platform_public_key,
            "mode": "walletconnect"
        }

        if change_address:
            cli_args["change_address"] = change_address

        result = await self._call_mint_cli(cli_args)

        if not result.get("success"):
            error_msg = result.get("error", "Unknown covenant error")
            logger.error(
                "covenant_prepare_mint_failed",
                qube_id=qube.qube_id,
                error=error_msg
            )
            raise RuntimeError(f"Covenant prepare mint failed: {error_msg}")

        logger.info(
            "covenant_wc_tx_prepared",
            qube_id=qube.qube_id,
            category_id=result["category_id"][:16] + "..."
        )

        return {
            "wc_transaction": result["wc_transaction"],
            "category_id": result["category_id"],
            "commitment": result["commitment"],
            "covenant_address": result["covenant_address"],
            "recipient_address": result["recipient_address"]
        }

    async def mint_qube_nft(
        self,
        qube,
        recipient_address: str,
        wallet_wif: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Mint a Qube NFT via the CashScript covenant.

        Args:
            qube: Qube instance with public_key
            recipient_address: BCH cashaddr (token-aware, bitcoincash:z...)
            wallet_wif: WIF private key for funding the transaction.
                        If not provided, reads from PLATFORM_BCH_MINTING_KEY env.

        Returns:
            {
                "category_id": str,
                "mint_txid": str,
                "commitment": str,
                "recipient_address": str,
                "network": str
            }
        """
        # Derive commitment from qube's public key
        commitment = derive_commitment(qube.public_key)

        logger.info(
            "covenant_minting_nft",
            qube_id=qube.qube_id,
            commitment=commitment[:16] + "...",
            recipient=recipient_address
        )

        # Get wallet WIF for funding
        if not wallet_wif:
            import os
            wallet_wif = os.getenv("PLATFORM_BCH_MINTING_KEY", "")

        if not wallet_wif:
            raise ValueError(
                "No wallet WIF provided for covenant minting. "
                "Pass wallet_wif or set PLATFORM_BCH_MINTING_KEY env var."
            )

        # Build CLI args
        cli_args = {
            "commitment": commitment,
            "recipient_address": recipient_address,
            "wallet_wif": wallet_wif,
            "platform_public_key": self.platform_public_key
        }

        # Call mint-cli.ts via subprocess
        result = await self._call_mint_cli(cli_args)

        if not result.get("success"):
            error_msg = result.get("error", "Unknown covenant minting error")
            logger.error(
                "covenant_mint_failed",
                qube_id=qube.qube_id,
                error=error_msg
            )
            raise RuntimeError(f"Covenant mint failed: {error_msg}")

        logger.info(
            "covenant_mint_success",
            qube_id=qube.qube_id,
            txid=result["mint_txid"],
            category_id=result["category_id"][:16] + "..."
        )

        return {
            "category_id": result["category_id"],
            "mint_txid": result["mint_txid"],
            "commitment": result["commitment"],
            "recipient_address": result["recipient_address"],
            "network": self.network
        }

    async def _call_mint_cli(self, cli_args: Dict[str, str]) -> Dict[str, Any]:
        """
        Call covenant/mint-cli.ts via subprocess.

        Runs in a thread pool to avoid blocking the event loop.
        """
        tsx_bin = _find_tsx()
        mint_cli = str(self.covenant_dir / "mint-cli.ts")
        args_json = json.dumps(cli_args)

        def _run():
            try:
                proc = subprocess.run(
                    [tsx_bin, mint_cli, args_json],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    cwd=str(self.covenant_dir)
                )

                # mint-cli.ts outputs JSON to stdout
                stdout = proc.stdout.strip()
                if not stdout:
                    return {
                        "success": False,
                        "error": f"mint-cli produced no output. stderr: {proc.stderr.strip()}"
                    }

                try:
                    return json.loads(stdout)
                except json.JSONDecodeError:
                    return {
                        "success": False,
                        "error": f"mint-cli returned invalid JSON: {stdout[:200]}"
                    }

            except subprocess.TimeoutExpired:
                return {"success": False, "error": "mint-cli timed out after 60s"}
            except FileNotFoundError:
                return {
                    "success": False,
                    "error": f"tsx not found. Install: cd covenant && npm install"
                }
            except Exception as e:
                return {"success": False, "error": str(e)}

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _run)
