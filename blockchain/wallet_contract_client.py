"""
Wallet Contract Client

Calls covenant/wallet-cli.ts via subprocess to build and broadcast
CashScript wallet transactions.

Mirrors covenant_client.py but for the QubesWallet contract.
"""

import json
import subprocess
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional

from utils.logging import get_logger

logger = get_logger(__name__)


def _find_covenant_dir() -> Path:
    """Find the covenant/ directory relative to this file."""
    return Path(__file__).resolve().parent.parent / "covenant"


def _find_tsx() -> str:
    """Find the tsx binary (local node_modules or global)."""
    import sys
    covenant_dir = _find_covenant_dir()
    bin_dir = covenant_dir / "node_modules" / ".bin"

    if sys.platform == "win32":
        local_cmd = bin_dir / "tsx.cmd"
        if local_cmd.exists():
            return str(local_cmd)
    else:
        local_tsx = bin_dir / "tsx"
        if local_tsx.exists():
            return str(local_tsx)

    return "tsx"


class WalletContractClient:
    """
    Client for the QubesWallet CashScript contract.

    Delegates transaction building to covenant/wallet-cli.ts via subprocess.
    """

    def __init__(self):
        self.covenant_dir = _find_covenant_dir()

    async def _call_wallet_cli(self, cli_args: Dict[str, Any]) -> Dict[str, Any]:
        """Call covenant/wallet-cli.ts via subprocess in a thread pool."""
        tsx_bin = _find_tsx()
        wallet_cli = str(self.covenant_dir / "wallet-cli.ts")
        args_json = json.dumps(cli_args)

        def _run():
            try:
                proc = subprocess.run(
                    [tsx_bin, wallet_cli, args_json],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    cwd=str(self.covenant_dir)
                )

                stdout = proc.stdout.strip()
                if not stdout:
                    return {
                        "success": False,
                        "error": f"wallet-cli produced no output. stderr: {proc.stderr.strip()}"
                    }

                try:
                    return json.loads(stdout)
                except json.JSONDecodeError:
                    return {
                        "success": False,
                        "error": f"wallet-cli returned invalid JSON: {stdout[:200]}"
                    }

            except subprocess.TimeoutExpired:
                return {"success": False, "error": "wallet-cli timed out after 60s"}
            except FileNotFoundError:
                return {
                    "success": False,
                    "error": f"tsx not found. Install: cd covenant && npm install"
                }
            except Exception as e:
                return {"success": False, "error": str(e)}

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _run)

    async def derive_address(
        self, owner_pubkey: str, qube_pubkey: str
    ) -> Dict[str, str]:
        """
        Derive the CashScript contract address from owner + qube pubkeys.

        Returns:
            {"contract_address": "bitcoincash:p...", "token_address": "bitcoincash:r..."}
        """
        result = await self._call_wallet_cli({
            "mode": "derive_address",
            "owner_pubkey": owner_pubkey,
            "qube_pubkey": qube_pubkey
        })
        if not result.get("success"):
            raise RuntimeError(f"derive_address failed: {result.get('error')}")
        return {
            "contract_address": result["contract_address"],
            "token_address": result["token_address"]
        }

    async def owner_spend_broadcast(
        self,
        owner_pubkey: str,
        qube_pubkey: str,
        owner_wif: str,
        outputs: List[Dict[str, Any]]
    ) -> str:
        """
        Owner withdraws directly, sign and broadcast immediately.

        Returns: txid
        """
        result = await self._call_wallet_cli({
            "mode": "owner_spend_broadcast",
            "owner_pubkey": owner_pubkey,
            "qube_pubkey": qube_pubkey,
            "owner_wif": owner_wif,
            "outputs": outputs
        })
        if not result.get("success"):
            raise RuntimeError(f"owner_spend_broadcast failed: {result.get('error')}")
        return result["txid"]

    async def owner_spend_wc(
        self,
        owner_pubkey: str,
        qube_pubkey: str,
        owner_address: str,
        outputs: List[Dict[str, Any]]
    ) -> str:
        """
        Owner withdraws via WalletConnect.

        Returns: WC transaction object (stringified JSON)
        """
        result = await self._call_wallet_cli({
            "mode": "owner_spend_wc",
            "owner_pubkey": owner_pubkey,
            "qube_pubkey": qube_pubkey,
            "owner_address": owner_address,
            "outputs": outputs
        })
        if not result.get("success"):
            raise RuntimeError(f"owner_spend_wc failed: {result.get('error')}")
        return result["wc_transaction"]

    async def qube_approved_broadcast(
        self,
        owner_pubkey: str,
        qube_pubkey: str,
        qube_wif: str,
        owner_wif: str,
        outputs: List[Dict[str, Any]]
    ) -> str:
        """
        Qube proposes + owner co-signs, broadcast immediately.

        Returns: txid
        """
        result = await self._call_wallet_cli({
            "mode": "qube_approved_broadcast",
            "owner_pubkey": owner_pubkey,
            "qube_pubkey": qube_pubkey,
            "qube_wif": qube_wif,
            "owner_wif": owner_wif,
            "outputs": outputs
        })
        if not result.get("success"):
            raise RuntimeError(f"qube_approved_broadcast failed: {result.get('error')}")
        return result["txid"]

    async def qube_approved_wc(
        self,
        owner_pubkey: str,
        qube_pubkey: str,
        qube_wif: str,
        owner_address: str,
        outputs: List[Dict[str, Any]]
    ) -> str:
        """
        Qube proposes, owner signs via WalletConnect.

        Returns: WC transaction object (stringified JSON)
        """
        result = await self._call_wallet_cli({
            "mode": "qube_approved_wc",
            "owner_pubkey": owner_pubkey,
            "qube_pubkey": qube_pubkey,
            "qube_wif": qube_wif,
            "owner_address": owner_address,
            "outputs": outputs
        })
        if not result.get("success"):
            raise RuntimeError(f"qube_approved_wc failed: {result.get('error')}")
        return result["wc_transaction"]
