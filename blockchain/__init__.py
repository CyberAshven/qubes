"""
Blockchain Module

Implements Bitcoin Cash CashTokens NFT minting for Qube identities.
From docs/10_Blockchain_Integration.md Section 7
"""

from blockchain.platform_init import (
    PlatformInitializer,
    check_minting_token_exists,
    load_minting_token_config
)
from blockchain.manager import BlockchainManager
from blockchain.covenant_client import CovenantMinter
from blockchain.nft_minter import OptimizedNFTMinter
from blockchain.bcmr import BCMRGenerator
from blockchain.ipfs import IPFSUploader, upload_to_ipfs
from blockchain.verifier import NFTVerifier
from blockchain.registry import QubeNFTRegistry
from blockchain.nft_auth import (
    NFTAuthenticator,
    AuthChallenge,
    AuthResult,
    sign_challenge,
    authenticate_qube
)

__all__ = [
    # Platform initialization
    "PlatformInitializer",
    "check_minting_token_exists",
    "load_minting_token_config",

    # Main interface
    "BlockchainManager",

    # Covenant minting
    "CovenantMinter",

    # Legacy minter (deprecated)
    "OptimizedNFTMinter",
    "BCMRGenerator",
    "IPFSUploader",
    "upload_to_ipfs",
    "NFTVerifier",
    "QubeNFTRegistry",

    # NFT Authentication
    "NFTAuthenticator",
    "AuthChallenge",
    "AuthResult",
    "sign_challenge",
    "authenticate_qube"
]
