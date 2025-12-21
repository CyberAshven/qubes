"""
Mock objects for testing.

Provides mock implementations of external services and complex dependencies.
"""

from typing import Optional, Dict, Any, List
from unittest.mock import MagicMock, AsyncMock


class MockAIProvider:
    """
    Mock AI provider for testing without real API calls.

    Usage:
        mock_ai = MockAIProvider(response="Test response")
        result = await mock_ai.generate("prompt")
    """

    def __init__(self, response: str = "Mock AI response", raise_error: bool = False):
        self.response = response
        self.raise_error = raise_error
        self.call_count = 0
        self.last_prompt = None

    async def generate(self, prompt: str, **kwargs) -> str:
        """Mock generate method"""
        self.call_count += 1
        self.last_prompt = prompt

        if self.raise_error:
            raise Exception("Mock AI error")

        return self.response

    def reset(self):
        """Reset call tracking"""
        self.call_count = 0
        self.last_prompt = None


class MockIPFSUploader:
    """
    Mock IPFS uploader for testing without real IPFS operations.

    Usage:
        mock_ipfs = MockIPFSUploader()
        cid = await mock_ipfs.upload_file("/path/to/file")
    """

    def __init__(self, mock_cid: str = "QmMockCID123456789"):
        self.mock_cid = mock_cid
        self.uploaded_files = []

    async def upload_file(self, file_path: str, **kwargs) -> str:
        """Mock file upload"""
        self.uploaded_files.append(file_path)
        return f"ipfs://{self.mock_cid}"

    async def upload_json(self, data: Dict[str, Any], **kwargs) -> str:
        """Mock JSON upload"""
        return f"ipfs://{self.mock_cid}"

    def reset(self):
        """Reset tracking"""
        self.uploaded_files = []


class MockBlockchainClient:
    """
    Mock blockchain client for testing without real transactions.

    Usage:
        mock_bc = MockBlockchainClient()
        result = await mock_bc.mint_nft(...)
    """

    def __init__(self, mock_txid: str = "a" * 64, mock_category_id: str = "b" * 64):
        self.mock_txid = mock_txid
        self.mock_category_id = mock_category_id
        self.transactions = []

    async def mint_nft(self, recipient_address: str, **kwargs) -> Dict[str, str]:
        """Mock NFT minting"""
        result = {
            "mint_txid": self.mock_txid,
            "category_id": self.mock_category_id,
            "recipient": recipient_address,
        }
        self.transactions.append(result)
        return result

    async def verify_nft(self, category_id: str) -> bool:
        """Mock NFT verification"""
        return category_id == self.mock_category_id

    def reset(self):
        """Reset tracking"""
        self.transactions = []


class MockP2PNetwork:
    """
    Mock P2P network for testing without real network operations.

    Usage:
        mock_net = MockP2PNetwork()
        await mock_net.connect_to_peer(peer_id)
    """

    def __init__(self, mock_peer_id: str = "12D3KooWMock123"):
        self.mock_peer_id = mock_peer_id
        self.connected_peers = []
        self.sent_messages = []

    async def connect_to_peer(self, peer_id: str):
        """Mock peer connection"""
        if peer_id not in self.connected_peers:
            self.connected_peers.append(peer_id)

    async def send_message(self, peer_id: str, message: str):
        """Mock message sending"""
        self.sent_messages.append({
            "peer_id": peer_id,
            "message": message
        })

    async def disconnect_from_peer(self, peer_id: str):
        """Mock peer disconnection"""
        if peer_id in self.connected_peers:
            self.connected_peers.remove(peer_id)

    def reset(self):
        """Reset tracking"""
        self.connected_peers = []
        self.sent_messages = []


class MockTTSEngine:
    """
    Mock TTS engine for testing without audio generation.

    Usage:
        mock_tts = MockTTSEngine()
        audio_data = await mock_tts.synthesize("Hello")
    """

    def __init__(self, mock_audio: bytes = b"mock_audio_data"):
        self.mock_audio = mock_audio
        self.synthesis_calls = []

    async def synthesize(self, text: str, **kwargs) -> bytes:
        """Mock speech synthesis"""
        self.synthesis_calls.append(text)
        return self.mock_audio

    def reset(self):
        """Reset tracking"""
        self.synthesis_calls = []


class MockSTTEngine:
    """
    Mock STT engine for testing without audio transcription.

    Usage:
        mock_stt = MockSTTEngine(transcript="Hello world")
        text = await mock_stt.transcribe(audio_data)
    """

    def __init__(self, transcript: str = "Mock transcription"):
        self.transcript = transcript
        self.transcription_calls = []

    async def transcribe(self, audio_data: bytes, **kwargs) -> str:
        """Mock audio transcription"""
        self.transcription_calls.append(len(audio_data))
        return self.transcript

    def reset(self):
        """Reset tracking"""
        self.transcription_calls = []


def create_mock_qube_dict(
    qube_id: str = "TEST0001",
    name: str = "MockQube",
    **kwargs
) -> Dict[str, Any]:
    """
    Create a mock Qube dictionary for testing serialization.

    Args:
        qube_id: Qube ID
        name: Qube name
        **kwargs: Additional fields

    Returns:
        Dictionary with Qube structure
    """
    defaults = {
        "qube_id": qube_id,
        "genesis_block": {
            "block_number": 0,
            "block_type": "GENESIS",
            "qube_id": qube_id,
            "qube_name": name,
            "creator": "test_user",
            "ai_model": "gpt-4o-mini",
            "voice_model": "test",
            "favorite_color": "#FF0000",
        }
    }
    defaults.update(kwargs)
    return defaults


def create_mock_block_dict(
    block_number: int = 1,
    block_type: str = "MESSAGE",
    qube_id: str = "TEST0001",
    **kwargs
) -> Dict[str, Any]:
    """
    Create a mock block dictionary for testing.

    Args:
        block_number: Block number
        block_type: Type of block
        qube_id: Qube ID
        **kwargs: Additional fields

    Returns:
        Dictionary with block structure
    """
    import time

    defaults = {
        "block_number": block_number,
        "block_type": block_type,
        "qube_id": qube_id,
        "timestamp": int(time.time()),
        "previous_hash": "0" * 64,
        "block_hash": "a" * 64,
        "signature": "b" * 140,
        "content": {},
    }
    defaults.update(kwargs)
    return defaults
