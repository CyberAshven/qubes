#!/usr/bin/env python
"""Quick NFT verification script"""
import asyncio
import sys
from pathlib import Path
import time

sys.path.insert(0, str(Path(__file__).parent))

from blockchain.verifier import NFTVerifier

async def main():
    print('\n' + '='*80)
    print('STEP 3: VERIFYING NFT OWNERSHIP ON-CHAIN')
    print('='*80)

    print('\nWaiting 10 seconds for transaction to propagate...')
    time.sleep(10)

    verifier = NFTVerifier()
    category_id = '9414252c6d661907829c9cee3fbaf2e1278d59a80392858fcd22916862602b4b'
    owner_address = 'bitcoincash:zpr6a0r3wtrcam0q26k8ldj5ce5se6ck3gxyapgsfx'

    print(f'\nVerifying ownership...')
    print(f'Category ID: {category_id[:16]}...')
    print(f'Owner: {owner_address}')

    is_verified = await verifier.verify_ownership(category_id, owner_address)

    if is_verified:
        print('\n✅ NFT VERIFIED!')
        details = await verifier.get_nft_details(category_id, owner_address)
        print(f'\nNFT Details:')
        print(f'  - Value: {details["value_satoshis"]} satoshis')
        print(f'  - Commitment: {details["nft_commitment"][:32]}...')
        print(f'  - Capability: {details["nft_capability"]}')
        print(f'  - Total UTXOs: {details["total_utxos"]}')
    else:
        print('\n⚠️  Not verified yet (may need more time)')

    print('\n' + '='*80)

if __name__ == "__main__":
    asyncio.run(main())
