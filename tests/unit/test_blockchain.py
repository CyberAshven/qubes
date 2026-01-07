"""
Test Blockchain Implementation

Tests Bitcoin Cash CashTokens NFT minting for Qubes.
"""

import pytest
import json
import hashlib
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from blockchain.platform_init import PlatformInitializer, check_minting_token_exists
from blockchain.nft_minter import OptimizedNFTMinter
from blockchain.bcmr import BCMRGenerator
from blockchain.registry import QubeNFTRegistry
from blockchain.verifier import NFTVerifier
from blockchain.manager import BlockchainManager
from blockchain.ipfs import IPFSUploader
from core.block import Block
from core.official_category import OFFICIAL_QUBES_CATEGORY


class TestPlatformInitializer:
    """Test platform minting token initialization"""

    def test_check_minting_token_exists_false(self, tmp_path):
        """Test checking for non-existent minting token"""
        # Temporarily change data directory
        with patch('blockchain.platform_init.Path') as mock_path:
            mock_path.return_value.exists.return_value = False
            assert check_minting_token_exists() is False

    def test_check_minting_token_exists_true(self, tmp_path):
        """Test checking for existing minting token"""
        # Create mock minting token file
        config_path = tmp_path / "minting_token.json"
        config_path.write_text(json.dumps({"category_id": "test123"}))

        with patch('blockchain.platform_init.Path') as mock_path:
            mock_path.return_value.exists.return_value = True
            assert check_minting_token_exists() is True


class TestNFTMinter:
    """Test optimized NFT minter"""

    @pytest.fixture
    def mock_qube(self):
        """Create mock Qube instance"""
        qube = Mock()
        qube.qube_id = "AAAA1111"
        qube.name = "Test Qube"

        # Create a proper Block object for genesis_block
        genesis_block = Mock(spec=Block)
        genesis_block.block_hash = "abc123..."
        genesis_block.creator = "test_public_key"
        genesis_block.birth_timestamp = "2025-10-04T00:00:00Z"

        qube.genesis_block = genesis_block
        return qube

    def test_create_commitment(self, mock_qube):
        """Test commitment creation from Qube metadata"""
        # Create mock minting config
        minting_config = {
            "category_id": OFFICIAL_QUBES_CATEGORY,
            "commitment": "test_commitment"
        }

        with patch('blockchain.nft_minter.load_minting_token_config', return_value=minting_config):
            with patch('blockchain.nft_minter.os.getenv', return_value="mock_wif_key"):
                with patch('bitcash.PrivateKey'):
                    minter = OptimizedNFTMinter(network="chipnet")

                    commitment = minter._create_commitment(mock_qube)

                    # Verify commitment is 32 bytes
                    assert len(commitment) == 32
                    assert isinstance(commitment, bytes)

    def test_commitment_deterministic(self, mock_qube):
        """Test that same Qube data produces same commitment"""
        minting_config = {
            "category_id": OFFICIAL_QUBES_CATEGORY,
            "commitment": "test_commitment"
        }

        with patch('blockchain.nft_minter.load_minting_token_config', return_value=minting_config):
            with patch('blockchain.nft_minter.os.getenv', return_value="mock_wif_key"):
                with patch('bitcash.PrivateKey'):
                    minter = OptimizedNFTMinter(network="chipnet")

                    commitment1 = minter._create_commitment(mock_qube)
                    commitment2 = minter._create_commitment(mock_qube)

                    # Same Qube should produce same commitment
                    assert commitment1 == commitment2


class TestBCMRGenerator:
    """Test BCMR metadata generation"""

    @pytest.fixture
    def mock_qube(self):
        """Create mock Qube"""
        qube = Mock()
        qube.qube_id = "AAAA1111"
        qube.name = "Test Qube"

        # Create a proper Block object for genesis_block
        genesis_block = Mock(spec=Block)
        genesis_block.block_hash = "abc123..."
        genesis_block.creator = "test_creator"
        genesis_block.birth_timestamp = "2025-10-04T00:00:00Z"
        genesis_block.genesis_prompt = "A test Qube for testing"
        genesis_block.ai_model = "claude-sonnet-4.5"

        qube.genesis_block = genesis_block
        return qube

    def test_generate_bcmr_metadata(self, mock_qube, tmp_path):
        """Test BCMR metadata generation"""
        generator = BCMRGenerator()

        category_id = "a" * 64  # 64-char hex
        commitment_data = {
            "qube_id": mock_qube.qube_id,
            "genesis_block_hash": mock_qube.genesis_block.block_hash
        }

        bcmr = generator.generate_bcmr_metadata(
            category_id=category_id,
            qube=mock_qube,
            commitment_data=commitment_data
        )

        # Verify BCMR structure
        assert bcmr["$schema"] == "https://cashtokens.org/bcmr-v2.schema.json"
        assert "version" in bcmr
        assert "latestRevision" in bcmr
        assert "registryIdentity" in bcmr
        assert "identities" in bcmr

        # Verify category identity exists
        assert category_id in bcmr["identities"]

        # Verify identity has attributes
        identity_versions = bcmr["identities"][category_id]
        latest_revision = list(identity_versions.keys())[0]
        identity = identity_versions[latest_revision]

        assert identity["name"] == "Test Qube"
        assert identity["token"]["category"] == category_id
        assert identity["token"]["symbol"] == "QUBE"
        assert identity["token"]["decimals"] == 0

        # Verify attributes
        attributes = identity["extensions"]["attributes"]
        assert any(attr["trait_type"] == "Qube ID" for attr in attributes)
        assert any(attr["trait_type"] == "AI Model" for attr in attributes)

    def test_save_bcmr_locally(self, mock_qube, tmp_path):
        """Test saving BCMR to local file"""
        generator = BCMRGenerator()
        generator.bcmr_dir = tmp_path

        category_id = OFFICIAL_QUBES_CATEGORY
        bcmr_metadata = {
            "$schema": "https://cashtokens.org/bcmr-v2.schema.json",
            "version": {"major": 1, "minor": 0, "patch": 0}
        }

        path = generator.save_bcmr_locally(category_id, bcmr_metadata)

        # Verify file was created
        assert Path(path).exists()

        # Verify content
        with open(path, 'r') as f:
            saved_metadata = json.load(f)

        assert saved_metadata == bcmr_metadata


class TestQubeNFTRegistry:
    """Test Qube NFT registry"""

    @pytest.fixture
    def registry(self, tmp_path):
        """Create test registry"""
        registry_path = tmp_path / "test_registry.json"
        return QubeNFTRegistry(registry_path=str(registry_path))

    def test_register_nft(self, registry):
        """Test NFT registration"""
        registry.register_nft(
            qube_id="AAAA1111",
            category_id=OFFICIAL_QUBES_CATEGORY,
            mint_txid="tx123",
            recipient_address="bitcoincash:qp...",
            commitment="abc123",
            network="chipnet"
        )

        # Verify registration
        assert registry.is_registered("AAAA1111")

        # Verify details
        info = registry.get_nft_info("AAAA1111")
        assert info["category_id"] == OFFICIAL_QUBES_CATEGORY
        assert info["mint_txid"] == "tx123"
        assert info["network"] == "chipnet"

    def test_get_category_id(self, registry):
        """Test getting category ID"""
        registry.register_nft(
            qube_id="AAAA1111",
            category_id=OFFICIAL_QUBES_CATEGORY,
            mint_txid="tx123",
            recipient_address="bitcoincash:qp...",
            commitment="abc123"
        )

        category_id = registry.get_category_id("AAAA1111")
        assert category_id == OFFICIAL_QUBES_CATEGORY

    def test_find_by_category(self, registry):
        """Test finding Qube by category ID"""
        registry.register_nft(
            qube_id="AAAA1111",
            category_id=OFFICIAL_QUBES_CATEGORY,
            mint_txid="tx123",
            recipient_address="bitcoincash:qp...",
            commitment="abc123"
        )

        info = registry.find_by_category(OFFICIAL_QUBES_CATEGORY)
        assert info is not None
        assert info["qube_id"] == "AAAA1111"

    def test_list_all_nfts(self, registry):
        """Test listing all NFTs"""
        # Register multiple NFTs
        for i in range(3):
            registry.register_nft(
                qube_id=f"QUBE_{i}",
                category_id=OFFICIAL_QUBES_CATEGORY,
                mint_txid=f"tx_{i}",
                recipient_address="bitcoincash:qp...",
                commitment=f"commit_{i}"
            )

        nfts = registry.list_all_nfts()
        assert len(nfts) == 3

    def test_registry_persistence(self, tmp_path):
        """Test that registry persists across instances"""
        registry_path = tmp_path / "persistent_registry.json"

        # Create first instance and register NFT
        registry1 = QubeNFTRegistry(registry_path=str(registry_path))
        registry1.register_nft(
            qube_id="AAAA1111",
            category_id=OFFICIAL_QUBES_CATEGORY,
            mint_txid="tx123",
            recipient_address="bitcoincash:qp...",
            commitment="abc123"
        )

        # Create second instance and verify data persisted
        registry2 = QubeNFTRegistry(registry_path=str(registry_path))
        assert registry2.is_registered("AAAA1111")
        assert registry2.get_category_id("AAAA1111") == OFFICIAL_QUBES_CATEGORY


class TestNFTVerifier:
    """Test NFT ownership verifier"""

    @pytest.mark.asyncio
    async def test_address_to_locking_bytecode(self):
        """Test address conversion to locking bytecode"""
        verifier = NFTVerifier()

        # Test error handling when Address conversion fails
        # We can't easily mock the internal import, so we test error path with invalid address
        bytecode = await verifier._address_to_locking_bytecode("invalid_address")

        # Should return None on error
        assert bytecode is None

    @pytest.mark.asyncio
    async def test_verify_ownership_mock(self):
        """Test NFT ownership verification with mocked Chaingraph"""
        verifier = NFTVerifier()

        # Mock Chaingraph response
        mock_response = {
            "data": {
                "output": [
                    {
                        "value_satoshis": 1000,
                        "token_category": OFFICIAL_QUBES_CATEGORY,
                        "nft_commitment_hex": "abc123",
                        "nft_capability": None
                    }
                ]
            }
        }

        # Create proper async mock for session and response
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value=mock_response)

        mock_post = AsyncMock()
        mock_post.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_post.__aexit__ = AsyncMock(return_value=None)

        mock_session_instance = AsyncMock()
        mock_session_instance.post = Mock(return_value=mock_post)
        mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
        mock_session_instance.__aexit__ = AsyncMock(return_value=None)

        with patch('blockchain.verifier.aiohttp.ClientSession', return_value=mock_session_instance):
            with patch.object(verifier, '_address_to_locking_bytecode', return_value="mock_bytecode"):
                is_owned = await verifier.verify_ownership(OFFICIAL_QUBES_CATEGORY, "bitcoincash:qp...")

                assert is_owned is True


def run_tests():
    """Run all blockchain tests"""
    print("=" * 70)
    print("TESTING PHASE 4: BLOCKCHAIN INTEGRATION")
    print("=" * 70)
    print()

    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--color=yes"
    ])


class TestBCMRRevisions:
    """Test BCMR revision updates (Phase 4 completion)"""

    @pytest.fixture
    def bcmr_generator(self, tmp_path):
        """Create BCMR generator with temp directory"""
        generator = BCMRGenerator()
        generator.bcmr_dir = tmp_path
        return generator

    @pytest.fixture
    def mock_qube(self):
        """Create mock Qube"""
        qube = Mock()
        qube.qube_id = "AAAA1111"
        qube.name = "Test Qube"

        # Create a proper Block object for genesis_block
        genesis_block = Mock(spec=Block)
        genesis_block.block_hash = "abc123..."
        genesis_block.creator = "test_creator"
        genesis_block.birth_timestamp = "2025-10-04T00:00:00Z"
        genesis_block.genesis_prompt = "I am a test Qube"

        qube.genesis_block = genesis_block
        qube.avatar_ipfs_uri = "ipfs://test123"
        return qube

    def test_add_revision_to_existing_bcmr(self, bcmr_generator, mock_qube, tmp_path):
        """Test adding revision to existing BCMR file"""
        category_id = "abc123" * 8  # 64 char hex

        # Create initial BCMR
        commitment_data = {"qube_id": "AAAA1111", "version": "1.0"}
        initial_bcmr = bcmr_generator.generate_bcmr_metadata(
            category_id, mock_qube, commitment_data
        )
        bcmr_generator.save_bcmr_locally(category_id, initial_bcmr)

        # Add revision
        updated_metadata = {
            "name": "Updated Qube Name",
            "description": "This Qube has been updated"
        }
        bcmr_path = bcmr_generator.add_revision(category_id, updated_metadata)

        # Verify revision was added
        assert Path(bcmr_path).exists()

        with open(bcmr_path, 'r') as f:
            bcmr = json.load(f)

        # Should have at least 2 revisions (initial + update)
        assert category_id in bcmr["identities"]
        revisions = bcmr["identities"][category_id]
        assert len(revisions) >= 2

        # Latest revision should have updated data
        latest_revision = bcmr["latestRevision"]
        assert latest_revision in revisions

    def test_add_revision_to_nonexistent_bcmr(self, bcmr_generator, tmp_path):
        """Test adding revision creates new BCMR if doesn't exist"""
        category_id = "def456" * 8

        updated_metadata = {
            "name": "New Qube",
            "description": "Created via revision"
        }
        bcmr_path = bcmr_generator.add_revision(category_id, updated_metadata)

        # Should create new BCMR file
        assert Path(bcmr_path).exists()

        with open(bcmr_path, 'r') as f:
            bcmr = json.load(f)

        assert category_id in bcmr["identities"]
        assert len(bcmr["identities"][category_id]) >= 1

    def test_load_bcmr(self, bcmr_generator, mock_qube, tmp_path):
        """Test loading BCMR from file"""
        category_id = "ghi789" * 8

        # Create and save BCMR
        commitment_data = {"qube_id": "AAAA1111"}
        bcmr = bcmr_generator.generate_bcmr_metadata(
            category_id, mock_qube, commitment_data
        )
        bcmr_generator.save_bcmr_locally(category_id, bcmr)

        # Load it back
        loaded_bcmr = bcmr_generator.load_bcmr(category_id)

        assert loaded_bcmr is not None
        assert loaded_bcmr["identities"][category_id] == bcmr["identities"][category_id]

    def test_load_nonexistent_bcmr(self, bcmr_generator):
        """Test loading non-existent BCMR returns None"""
        result = bcmr_generator.load_bcmr("nonexistent_category")
        assert result is None


class TestPinataIntegration:
    """Test Pinata cloud pinning (Phase 4 completion)"""

    @pytest.mark.asyncio
    async def test_pinata_upload_success(self):
        """Test successful Pinata upload"""
        uploader = IPFSUploader(
            use_pinata=True,
            pinata_api_key="test_api_key",
            pinata_secret_key="test_secret"
        )

        bcmr_metadata = {
            "$schema": "https://cashtokens.org/bcmr-v2.schema.json",
            "version": {"major": 1, "minor": 0, "patch": 0},
            "latestRevision": "2025-10-04T00:00:00.000Z"
        }

        # Mock the internal _upload_to_pinata method directly
        async def mock_upload_to_pinata(metadata):
            return "ipfs://Qm123abc456def"

        with patch.object(uploader, '_upload_to_pinata', side_effect=mock_upload_to_pinata):
            ipfs_uri = await uploader.upload_bcmr(bcmr_metadata)

            assert ipfs_uri == "ipfs://Qm123abc456def"

    @pytest.mark.asyncio
    async def test_pinata_upload_fallback_to_local(self):
        """Test Pinata failure falls back to local IPFS"""
        uploader = IPFSUploader(
            use_pinata=True,
            pinata_api_key="test_api_key",
            pinata_secret_key="test_secret"
        )

        bcmr_metadata = {"test": "data"}

        # Mock failed Pinata response
        mock_pinata_response = AsyncMock()
        mock_pinata_response.status = 500
        mock_pinata_response.text = AsyncMock(return_value="Internal Server Error")

        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_pinata_response

            # Mock successful local IPFS
            with patch.object(uploader, 'connect', return_value=True):
                with patch.object(uploader, 'client') as mock_client:
                    mock_client.add_json.return_value = "Qm789xyz"

                    ipfs_uri = await uploader.upload_bcmr(bcmr_metadata)

                    # Should fall back to local and succeed
                    assert ipfs_uri == "ipfs://Qm789xyz"

    def test_pinata_credentials_from_env(self):
        """Test Pinata credentials loaded from environment"""
        with patch.dict('os.environ', {
            'PINATA_API_KEY': 'env_api_key',
            'PINATA_SECRET_KEY': 'env_secret_key'
        }):
            uploader = IPFSUploader(use_pinata=True)

            assert uploader.pinata_api_key == 'env_api_key'
            assert uploader.pinata_secret_key == 'env_secret_key'
            assert uploader.use_pinata is True


class TestMetadataUpdateWorkflow:
    """Test complete metadata update workflow (Phase 4 completion)"""

    @pytest.fixture
    def mock_qube(self):
        """Create mock Qube with serializable genesis block"""
        # Use a custom class instead of Mock to avoid JSON serialization issues
        class MockGenesisBlock:
            def __init__(self):
                self.block_hash = "xyz789..."
                self.creator = "test_creator"
                self.birth_timestamp = "2025-10-04T00:00:00Z"
                self.genesis_prompt = "Test genesis prompt"

        class MockQube:
            def __init__(self):
                self.qube_id = "BBBB2222"
                self.name = "Update Test Qube"
                self.avatar_ipfs_uri = ""
                self.genesis_block = MockGenesisBlock()

        return MockQube()

    @pytest.fixture
    def mock_registry(self, tmp_path):
        """Create registry with test data"""
        registry = QubeNFTRegistry()
        registry.registry_file = tmp_path / "registry.json"

        # Register a test NFT
        registry.register_nft(
            qube_id="BBBB2222",
            category_id=OFFICIAL_QUBES_CATEGORY,
            mint_txid="txid123",
            recipient_address="bitcoincash:qp123",
            commitment="abc123",
            network="chipnet"
        )

        return registry

    @pytest.mark.asyncio
    async def test_update_qube_metadata_via_bcmr(self, mock_qube, mock_registry, tmp_path):
        """Test updating Qube metadata via BCMR revision (preferred method)"""
        # Mock BlockchainManager components
        with patch('blockchain.manager.check_minting_token_exists', return_value=True):
            with patch('blockchain.manager.OptimizedNFTMinter'):
                with patch('blockchain.manager.NFTVerifier'):
                    manager = BlockchainManager(network="chipnet")
                    manager.registry = mock_registry
                    manager.bcmr_generator.bcmr_dir = tmp_path

                    # Create initial BCMR
                    commitment_data = {"qube_id": "BBBB2222"}
                    initial_bcmr = manager.bcmr_generator.generate_bcmr_metadata(
                        OFFICIAL_QUBES_CATEGORY,
                        mock_qube,
                        commitment_data
                    )
                    manager.bcmr_generator.save_bcmr_locally(OFFICIAL_QUBES_CATEGORY, initial_bcmr)

                    # Update metadata
                    updated_metadata = {
                        "name": "Updated Qube",
                        "description": "This metadata was updated via BCMR revision"
                    }

                    result = await manager.update_qube_metadata(
                        qube_id="BBBB2222",
                        updated_metadata=updated_metadata,
                        upload_to_ipfs=False
                    )

                    # Verify result
                    assert result["qube_id"] == "BBBB2222"
                    assert result["category_id"] == OFFICIAL_QUBES_CATEGORY
                    assert "bcmr_local_path" in result

                    # Verify BCMR was updated
                    bcmr = manager.bcmr_generator.load_bcmr(OFFICIAL_QUBES_CATEGORY)
                    assert bcmr is not None
                    assert len(bcmr["identities"][OFFICIAL_QUBES_CATEGORY]) >= 2

    @pytest.mark.asyncio
    async def test_update_unregistered_qube_fails(self, tmp_path):
        """Test updating unregistered Qube raises error"""
        with patch('blockchain.manager.check_minting_token_exists', return_value=True):
            with patch('blockchain.manager.OptimizedNFTMinter'):
                with patch('blockchain.manager.NFTVerifier'):
                    manager = BlockchainManager(network="chipnet")
                    manager.bcmr_generator.bcmr_dir = tmp_path

                    with pytest.raises(ValueError, match="not registered"):
                        await manager.update_qube_metadata(
                            qube_id="UNREGISTERED_QUBE",
                            updated_metadata={"name": "Test"}
                        )


if __name__ == "__main__":
    run_tests()
