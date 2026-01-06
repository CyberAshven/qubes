"""
BCH Wallet Mainnet Test

This script tests the P2SH wallet implementation on BCH mainnet.

Test flow:
1. Generate (or load) owner + qube keypairs
2. Create P2SH wallet address
3. Fund the wallet (manual step - send BCH to address)
4. Spend via owner-only path (IF branch)
5. Fund again
6. Spend via 2-of-2 multisig path (ELSE branch)

Run with:
    python -m tests.test_bch_wallet_mainnet

Environment variables:
    OWNER_PRIVKEY_HEX - Owner's 32-byte private key (hex)
    QUBE_PRIVKEY_HEX  - Qube's 32-byte private key (hex)
    DESTINATION_ADDRESS - Where to send the BCH after spending
"""

import os
import sys
import json
import asyncio
import aiohttp
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from crypto.bch_script import (
    create_wallet_address,
    spend_owner_only,
    spend_multisig,
    pubkey_from_privkey,
    address_to_script_pubkey,
    UTXO,
    TxOutput
)


# =============================================================================
# BLOCKCHAIN API HELPERS
# =============================================================================

CHAINGRAPH_URL = "https://gql.chaingraph.pat.mn/v1/graphql"


async def query_utxos(address: str) -> list:
    """
    Query UTXOs for a CashAddr address using Chaingraph.

    Args:
        address: CashAddr (bitcoincash:p... or bitcoincash:q...)

    Returns:
        List of UTXOs
    """
    # Strip prefix for Chaingraph query
    if ':' in address:
        address_without_prefix = address.split(':', 1)[1]
    else:
        address_without_prefix = address

    query = """
    query GetUtxos($address: String!) {
      search_output(
        args: { locking_bytecode_hex: "" }
        where: {
          _and: [
            { _not: { spent_by: {} } }
            { locking_bytecode: { _has_key: $address } }
          ]
        }
      ) {
        transaction_hash
        output_index
        value_satoshis
        locking_bytecode
      }
    }
    """

    # Alternative simpler query for P2SH
    # Use the Fulcrum/Electrum-style query via alternative endpoint
    pass


async def query_utxos_electrum(address: str) -> list:
    """
    Query UTXOs using Fulcrum (Electrum-style API).

    This is more reliable for arbitrary addresses.
    """
    # Use a public Fulcrum server
    electrum_url = "https://bch.imaginary.cash:50004"

    # Convert to scripthash for electrum query
    from crypto.bch_script import decode_cashaddr, build_p2sh_script_pubkey, sha256

    prefix, version, hash_bytes = decode_cashaddr(address)

    # Build scriptPubKey
    if (version >> 3) & 1:  # P2SH
        script_pubkey = build_p2sh_script_pubkey(hash_bytes)
    else:  # P2PKH
        from crypto.bch_script import OP_DUP, OP_HASH160, OP_EQUALVERIFY, OP_CHECKSIG, push_data
        script_pubkey = bytes([OP_DUP, OP_HASH160]) + push_data(hash_bytes) + bytes([OP_EQUALVERIFY, OP_CHECKSIG])

    # Electrum scripthash is SHA256 of scriptPubKey, reversed
    scripthash = sha256(script_pubkey)[::-1].hex()

    print(f"Scripthash: {scripthash}")

    # JSON-RPC request
    payload = {
        "jsonrpc": "2.0",
        "method": "blockchain.scripthash.listunspent",
        "params": [scripthash],
        "id": 1
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(electrum_url, json=payload, ssl=True) as resp:
            result = await resp.json()
            if "error" in result:
                raise Exception(f"Electrum error: {result['error']}")
            return result.get("result", [])


async def get_balance_blockchair(address: str) -> dict:
    """
    Query balance using Blockchair API (simpler, rate-limited).
    """
    url = f"https://api.blockchair.com/bitcoin-cash/dashboards/address/{address}"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            if "data" in data and address in data["data"]:
                addr_data = data["data"][address]
                return {
                    "balance": addr_data.get("address", {}).get("balance", 0),
                    "utxo_count": addr_data.get("address", {}).get("unspent_output_count", 0),
                    "utxos": addr_data.get("utxo", [])
                }
            return {"balance": 0, "utxo_count": 0, "utxos": []}


async def broadcast_tx(tx_hex: str) -> str:
    """
    Broadcast transaction using Blockchair API.

    Returns txid on success.
    """
    url = "https://api.blockchair.com/bitcoin-cash/push/transaction"

    async with aiohttp.ClientSession() as session:
        async with session.post(url, data={"data": tx_hex}) as resp:
            result = await resp.json()
            if result.get("context", {}).get("code") == 200:
                return result["data"]["transaction_hash"]
            else:
                raise Exception(f"Broadcast failed: {result}")


# =============================================================================
# KEY MANAGEMENT
# =============================================================================

KEYS_FILE = Path(__file__).parent / "test_wallet_keys.json"


def generate_or_load_keys():
    """
    Generate new keypairs or load existing ones.
    """
    if KEYS_FILE.exists():
        print(f"Loading existing keys from {KEYS_FILE}")
        with open(KEYS_FILE) as f:
            data = json.load(f)
            return {
                "owner_privkey": bytes.fromhex(data["owner_privkey_hex"]),
                "qube_privkey": bytes.fromhex(data["qube_privkey_hex"]),
            }

    # Check environment variables
    owner_hex = os.environ.get("OWNER_PRIVKEY_HEX")
    qube_hex = os.environ.get("QUBE_PRIVKEY_HEX")

    if owner_hex and qube_hex:
        print("Using keys from environment variables")
        return {
            "owner_privkey": bytes.fromhex(owner_hex),
            "qube_privkey": bytes.fromhex(qube_hex),
        }

    # Generate new keys
    print("Generating new keypairs...")
    owner_privkey = os.urandom(32)
    qube_privkey = os.urandom(32)

    # Save for future runs
    data = {
        "owner_privkey_hex": owner_privkey.hex(),
        "qube_privkey_hex": qube_privkey.hex(),
        "warning": "THESE ARE TEST KEYS - DO NOT USE FOR REAL FUNDS"
    }

    with open(KEYS_FILE, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"Keys saved to {KEYS_FILE}")

    return {
        "owner_privkey": owner_privkey,
        "qube_privkey": qube_privkey,
    }


# =============================================================================
# TEST FUNCTIONS
# =============================================================================

async def test_create_wallet():
    """Step 1: Create P2SH wallet address"""
    print("\n" + "=" * 70)
    print("STEP 1: CREATE P2SH WALLET")
    print("=" * 70)

    keys = generate_or_load_keys()

    owner_pubkey = pubkey_from_privkey(keys["owner_privkey"])
    qube_pubkey = pubkey_from_privkey(keys["qube_privkey"])

    print(f"\nOwner private key: {keys['owner_privkey'].hex()}")
    print(f"Owner public key:  {owner_pubkey.hex()}")
    print(f"\nQube private key:  {keys['qube_privkey'].hex()}")
    print(f"Qube public key:   {qube_pubkey.hex()}")

    # Create wallet
    wallet = create_wallet_address(owner_pubkey.hex(), qube_pubkey.hex())

    print(f"\n{'=' * 70}")
    print(f"P2SH WALLET ADDRESS: {wallet['p2sh_address']}")
    print(f"{'=' * 70}")
    print(f"\nRedeem script ({len(wallet['redeem_script'])} bytes):")
    print(f"  {wallet['redeem_script_hex']}")
    print(f"\nScript hash: {wallet['script_hash']}")

    return wallet, keys


async def test_check_balance(address: str):
    """Step 2: Check wallet balance"""
    print("\n" + "=" * 70)
    print("STEP 2: CHECK BALANCE")
    print("=" * 70)

    print(f"\nQuerying balance for: {address}")

    try:
        result = await get_balance_blockchair(address)
        balance_bch = result["balance"] / 100_000_000

        print(f"\nBalance: {result['balance']} satoshis ({balance_bch:.8f} BCH)")
        print(f"UTXO count: {result['utxo_count']}")

        if result["utxos"]:
            print("\nUTXOs:")
            for utxo in result["utxos"]:
                print(f"  - {utxo['transaction_hash']}:{utxo['index']} = {utxo['value']} sats")

        return result
    except Exception as e:
        print(f"Error querying balance: {e}")
        return None


async def test_spend_owner_only(wallet: dict, keys: dict, destination: str):
    """Step 3: Spend via owner-only path (IF branch)"""
    print("\n" + "=" * 70)
    print("STEP 3: SPEND VIA OWNER-ONLY PATH (IF branch)")
    print("=" * 70)

    # Get current UTXOs
    result = await get_balance_blockchair(wallet["p2sh_address"])

    if not result or result["balance"] == 0:
        print("\nNo funds in wallet. Please send some BCH first!")
        print(f"Send to: {wallet['p2sh_address']}")
        return None

    utxos = result["utxos"]
    if not utxos:
        print("No UTXOs found!")
        return None

    # Use first UTXO
    utxo_data = utxos[0]
    utxo = UTXO(
        txid=utxo_data["transaction_hash"],
        vout=utxo_data["index"],
        value=utxo_data["value"],
        script_pubkey=address_to_script_pubkey(wallet["p2sh_address"])
    )

    print(f"\nSpending UTXO: {utxo.txid}:{utxo.vout}")
    print(f"Value: {utxo.value} satoshis")

    # Calculate fee (1 sat/byte, ~200 bytes for owner-only tx)
    fee = 200
    send_amount = utxo.value - fee

    if send_amount <= 546:  # Dust limit
        print(f"Amount after fee ({send_amount} sats) is below dust limit!")
        return None

    print(f"Sending: {send_amount} satoshis to {destination}")
    print(f"Fee: {fee} satoshis")

    # Create outputs
    outputs = [TxOutput(address=destination, value=send_amount)]

    # Build and sign transaction
    tx_hex = spend_owner_only(
        utxo=utxo,
        outputs=outputs,
        redeem_script=wallet["redeem_script"],
        owner_privkey_bytes=keys["owner_privkey"]
    )

    print(f"\nSigned transaction ({len(tx_hex) // 2} bytes):")
    print(f"  {tx_hex[:100]}...")

    # Ask for confirmation before broadcast
    confirm = input("\nBroadcast this transaction? (yes/no): ")
    if confirm.lower() != "yes":
        print("Aborted.")
        return tx_hex

    # Broadcast
    try:
        txid = await broadcast_tx(tx_hex)
        print(f"\nTransaction broadcast successfully!")
        print(f"TXID: {txid}")
        print(f"Explorer: https://blockchair.com/bitcoin-cash/transaction/{txid}")
        return txid
    except Exception as e:
        print(f"\nBroadcast failed: {e}")
        return tx_hex


async def test_spend_multisig(wallet: dict, keys: dict, destination: str):
    """Step 4: Spend via 2-of-2 multisig path (ELSE branch)"""
    print("\n" + "=" * 70)
    print("STEP 4: SPEND VIA 2-OF-2 MULTISIG PATH (ELSE branch)")
    print("=" * 70)

    # Get current UTXOs
    result = await get_balance_blockchair(wallet["p2sh_address"])

    if not result or result["balance"] == 0:
        print("\nNo funds in wallet. Please send some BCH first!")
        print(f"Send to: {wallet['p2sh_address']}")
        return None

    utxos = result["utxos"]
    if not utxos:
        print("No UTXOs found!")
        return None

    # Use first UTXO
    utxo_data = utxos[0]
    utxo = UTXO(
        txid=utxo_data["transaction_hash"],
        vout=utxo_data["index"],
        value=utxo_data["value"],
        script_pubkey=address_to_script_pubkey(wallet["p2sh_address"])
    )

    print(f"\nSpending UTXO: {utxo.txid}:{utxo.vout}")
    print(f"Value: {utxo.value} satoshis")

    # Calculate fee (1 sat/byte, ~280 bytes for multisig tx)
    fee = 280
    send_amount = utxo.value - fee

    if send_amount <= 546:  # Dust limit
        print(f"Amount after fee ({send_amount} sats) is below dust limit!")
        return None

    print(f"Sending: {send_amount} satoshis to {destination}")
    print(f"Fee: {fee} satoshis")

    # Create outputs
    outputs = [TxOutput(address=destination, value=send_amount)]

    # Build and sign transaction
    tx_hex = spend_multisig(
        utxo=utxo,
        outputs=outputs,
        redeem_script=wallet["redeem_script"],
        owner_privkey_bytes=keys["owner_privkey"],
        qube_privkey_bytes=keys["qube_privkey"]
    )

    print(f"\nSigned transaction ({len(tx_hex) // 2} bytes):")
    print(f"  {tx_hex[:100]}...")

    # Ask for confirmation before broadcast
    confirm = input("\nBroadcast this transaction? (yes/no): ")
    if confirm.lower() != "yes":
        print("Aborted.")
        return tx_hex

    # Broadcast
    try:
        txid = await broadcast_tx(tx_hex)
        print(f"\nTransaction broadcast successfully!")
        print(f"TXID: {txid}")
        print(f"Explorer: https://blockchair.com/bitcoin-cash/transaction/{txid}")
        return txid
    except Exception as e:
        print(f"\nBroadcast failed: {e}")
        return tx_hex


async def main():
    """Main test runner"""
    print("\n" + "=" * 70)
    print("BCH P2SH WALLET MAINNET TEST")
    print("=" * 70)

    # Get destination address from env or prompt
    destination = os.environ.get("DESTINATION_ADDRESS")
    if not destination:
        print("\nNo DESTINATION_ADDRESS set.")
        destination = input("Enter destination address for test spends: ").strip()
        if not destination:
            print("Using same P2SH address as destination (sending to self)")

    # Step 1: Create wallet
    wallet, keys = await test_create_wallet()

    if not destination:
        destination = wallet["p2sh_address"]

    # Step 2: Check balance
    await test_check_balance(wallet["p2sh_address"])

    # Menu
    while True:
        print("\n" + "-" * 50)
        print("OPTIONS:")
        print("  1. Check balance")
        print("  2. Spend via owner-only path (IF branch)")
        print("  3. Spend via 2-of-2 multisig path (ELSE branch)")
        print("  4. Show wallet info")
        print("  5. Set destination address")
        print("  q. Quit")
        print("-" * 50)

        choice = input("Select option: ").strip().lower()

        if choice == "1":
            await test_check_balance(wallet["p2sh_address"])
        elif choice == "2":
            await test_spend_owner_only(wallet, keys, destination)
        elif choice == "3":
            await test_spend_multisig(wallet, keys, destination)
        elif choice == "4":
            print(f"\nP2SH Address: {wallet['p2sh_address']}")
            print(f"Destination: {destination}")
            print(f"Redeem script: {wallet['redeem_script_hex']}")
        elif choice == "5":
            destination = input("Enter new destination address: ").strip()
        elif choice == "q":
            break
        else:
            print("Invalid option")

    print("\nTest complete!")


if __name__ == "__main__":
    asyncio.run(main())
