"""
Complete Qube Creation Example

Demonstrates ALL fields that can be configured during Qube creation.
This shows what a user would need to input/choose.
"""

from pathlib import Path
from core.qube import Qube


def create_complete_qube():
    """
    Create a Qube with ALL possible configuration options

    This example shows every field that can be set during creation.
    """

    # =============================================================================
    # REQUIRED FIELDS
    # =============================================================================

    qube_name = "Athena"
    """
    The Qube's name - like a username/identity
    Examples: "Athena", "BitcoinBob", "CodeMaster", "DataScout"
    """

    creator = "alice@example.com"
    """
    Creator's identifier - who created this Qube
    Could be: email, username, wallet address, etc.
    """

    genesis_prompt = """You are Athena, a helpful AI assistant specialized in blockchain technology and cryptocurrency.
You have deep knowledge of Bitcoin Cash and can explain complex concepts in simple terms.
You are friendly, patient, and always provide accurate information with sources when possible."""
    """
    The genesis prompt defines the Qube's:
    - Personality
    - Knowledge domain
    - Behavior
    - Purpose

    This is the core "DNA" of the Qube and will be used as the system prompt.
    """

    ai_model = "gpt-4o"
    """
    AI model to use for reasoning

    Available models (35+ options):

    OpenAI:
    - "gpt-5", "gpt-5-mini", "gpt-5-nano", "gpt-5-codex"
    - "gpt-4.1", "gpt-4.1-mini", "gpt-4o", "gpt-4o-mini"
    - "o4-mini", "o3-mini", "o1" (reasoning models)

    Anthropic:
    - "claude-sonnet-4.5", "claude-opus-4.1", "claude-opus-4"
    - "claude-sonnet-4", "claude-3.5-sonnet", "claude-3.5-haiku"

    Google:
    - "gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.5-flash-lite"
    - "gemini-2.0-flash", "gemini-1.5-pro"

    Perplexity:
    - "sonar-pro", "sonar", "sonar-reasoning-pro"
    - "sonar-reasoning", "sonar-deep-research"

    Ollama (Local):
    - "llama3.3:70b", "qwen3:235b", "deepseek-r1:8b"
    - "phi4:14b", "gemma2:9b", "mistral:7b", "codellama:7b"
    """

    voice_model = "elevenlabs-emily"
    """
    Voice model for text-to-speech

    Examples:
    - "elevenlabs-emily" - Female, professional
    - "elevenlabs-adam" - Male, authoritative
    - "elevenlabs-sam" - Male, friendly

    Future: Will integrate with ElevenLabs, PlayHT, or other TTS providers
    """

    data_dir = Path("./data")
    """
    Directory where Qube data will be stored

    Structure will be:
    ./data/
      └── qubes/
          └── {qube_id}/
              ├── blocks/        # JSON block storage
              ├── keys/          # Encrypted private keys
              └── session_backups/
    """

    # =============================================================================
    # OPTIONAL FIELDS (with smart defaults)
    # =============================================================================

    avatar = {
        "source": "generated",           # "generated" | "uploaded" | "nft"
        "ipfs_cid": None,                # IPFS CID if stored on IPFS
        "generation_model": "dall-e-3",  # Model used to generate avatar
        "generation_prompt": "A wise Greek goddess with flowing blue robes",
        "file_format": "png",
        "dimensions": "1024x1024",
        "url": None                      # Temporary URL before IPFS upload
    }
    """
    Avatar metadata

    Options:
    1. Generated: Use DALL-E 3, Stable Diffusion, or Midjourney
    2. Uploaded: User uploads their own image
    3. NFT: Use existing NFT as avatar

    Future: Will support automatic IPFS upload and NFT minting
    """

    favorite_color = "#9B59B6"  # Purple (Athena's color)
    """
    Favorite color as hex code

    Used for:
    - UI theming
    - Avatar generation hints
    - Personality expression

    Examples: "#4A90E2" (blue), "#FF5733" (red-orange), "#2ECC71" (green)
    """

    home_blockchain = "bitcoin_cash"
    """
    Home blockchain for the Qube's NFT identity

    Currently supported: "bitcoin_cash" (BCH)
    Future: May support other UTXO-based chains

    The Qube's NFT will be minted here using CashTokens standard.
    """

    genesis_prompt_encrypted = False
    """
    Whether to encrypt the genesis prompt

    - False: Genesis prompt is public (visible in blockchain)
    - True: Genesis prompt is encrypted (only Qube owner can read)

    Use cases for encryption:
    - Private/personal Qubes
    - Proprietary business logic
    - Sensitive instructions
    """

    capabilities = {
        "web_search": True,        # Can search the web via Perplexity
        "image_generation": True,  # Can generate images via DALL-E 3
        "image_processing": True,  # Can analyze/process images
        "tts": True,              # Can speak (text-to-speech)
        "stt": True,              # Can listen (speech-to-text)
        "code_execution": False   # Can execute code (disabled by default for safety)
    }
    """
    Capability flags - what tools/features the Qube can use

    These are enforced by the tool registry:
    - If web_search=False, Qube cannot use web_search tool
    - If image_generation=False, Qube cannot generate images
    - Etc.

    Can be updated later by modifying the Qube's capabilities.
    """

    default_trust_level = 75
    """
    Default trust level (0-100) for interactions

    Used for:
    - Rate limiting (higher trust = more requests allowed)
    - Access control (higher trust = more sensitive operations)
    - Reputation system

    0 = No trust (heavily restricted)
    50 = Neutral (default)
    100 = Full trust (unrestricted)
    """

    nft_contract = None  # Will be set after NFT minting
    """
    NFT smart contract address

    Set to None initially, then populated after minting Qube's NFT on BCH.

    Example: "bitcoincash:qp..." (CashTokens contract address)

    The NFT represents:
    - Qube ownership
    - Transferability
    - Provenance
    """

    nft_token_id = None  # Will be set after NFT minting
    """
    NFT token ID within the contract

    Example: "0x1234..." (token identifier)

    Together with nft_contract, this uniquely identifies the Qube's NFT.
    """

    api_keys = {
        "openai": "sk-proj-...",
        "anthropic": "sk-ant-...",
        "google": "AIza...",
        "perplexity": "pplx-...",
        # "ollama": Not needed - local
    }
    """
    API keys for AI providers

    Can be provided at creation OR set later via qube.init_ai(api_keys)

    If provided here:
    - Qube is immediately ready to process messages
    - AI reasoning is initialized automatically
    - Tools are registered

    If not provided:
    - Qube is created but cannot think/respond yet
    - Call qube.init_ai(api_keys) when ready

    Security note: Store these securely! Consider using:
    - Environment variables
    - Encrypted configuration files
    - Secret management services
    """

    # =============================================================================
    # AUTO-GENERATED FIELDS (shown for reference - cannot be set manually)
    # =============================================================================

    # qube_id: str (8 characters)
    #   - Derived from public key SHA-256 hash
    #   - Example: "A3F2C1B8"
    #   - Unique identifier for this Qube

    # public_key: str (hex)
    #   - ECDSA secp256k1 public key
    #   - Used for signature verification
    #   - Publicly visible

    # private_key: EllipticCurvePrivateKey
    #   - ECDSA secp256k1 private key
    #   - Used for signing blocks
    #   - NEVER shared, encrypted at rest

    # birth_timestamp: int
    #   - Unix timestamp of genesis block creation
    #   - Automatically set to current time

    # =============================================================================
    # CREATE THE QUBE
    # =============================================================================

    qube = Qube.create_new(
        # Required
        qube_name=qube_name,
        creator=creator,
        genesis_prompt=genesis_prompt,
        ai_model=ai_model,
        voice_model=voice_model,
        data_dir=data_dir,

        # Optional (all have defaults)
        avatar=avatar,
        favorite_color=favorite_color,
        home_blockchain=home_blockchain,
        genesis_prompt_encrypted=genesis_prompt_encrypted,
        capabilities=capabilities,
        default_trust_level=default_trust_level,
        nft_contract=nft_contract,
        nft_token_id=nft_token_id,
        api_keys=api_keys  # Optional - can call init_ai() later instead
    )

    # =============================================================================
    # QUBE IS NOW READY!
    # =============================================================================

    print(f"✅ Qube created successfully!")
    print(f"   Qube ID: {qube.qube_id}")
    print(f"   Name: {qube.genesis_block.qube_name}")
    print(f"   Model: {qube.current_ai_model}")
    print(f"   Birth: {qube.genesis_block.birth_timestamp}")
    print(f"   Public Key: {qube.genesis_block.public_key[:32]}...")
    print(f"   AI Ready: {qube.reasoner is not None}")

    return qube


if __name__ == "__main__":
    # Example with minimal required fields
    print("=" * 70)
    print("MINIMAL CREATION (only required fields)")
    print("=" * 70)

    qube_minimal = Qube.create_new(
        qube_name="SimpleBot",
        creator="user123",
        genesis_prompt="You are a helpful assistant.",
        ai_model="gpt-4o-mini",  # Cheaper option
        voice_model="default",
        data_dir=Path("./data")
        # All optional fields will use defaults
        # API keys not provided - must call init_ai() later
    )

    print(f"Created: {qube_minimal.qube_id} - {qube_minimal.genesis_block.qube_name}")
    print(f"AI Ready: {qube_minimal.reasoner is not None}")
    print()

    # Example with ALL fields
    print("=" * 70)
    print("COMPLETE CREATION (all fields specified)")
    print("=" * 70)

    qube_complete = create_complete_qube()
    qube_complete.close()
    qube_minimal.close()
