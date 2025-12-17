"""
Shared pytest fixtures for Qubes test suite

Available to all test modules without explicit import.
"""

import pytest
import tempfile
import shutil
import os
from pathlib import Path
from typing import Generator, Dict, Any

# =============================================================================
# DIRECTORY & FILE FIXTURES
# =============================================================================

@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """
    Temporary directory that is cleaned up after test.

    Usage:
        def test_something(temp_dir):
            file = temp_dir / "test.json"
            file.write_text("data")
    """
    tmpdir = Path(tempfile.mkdtemp())
    yield tmpdir
    if tmpdir.exists():
        shutil.rmtree(tmpdir)


@pytest.fixture
def temp_data_dir(temp_dir) -> Path:
    """
    Temporary data directory for Qubes with structure.

    Creates:
        temp_dir/
            users/
            qubes/
            settings.json
    """
    data_dir = temp_dir / "data"
    data_dir.mkdir(parents=True)
    (data_dir / "users").mkdir()
    (data_dir / "qubes").mkdir()
    return data_dir


# =============================================================================
# ORCHESTRATOR FIXTURES
# =============================================================================

@pytest.fixture
def test_user_id() -> str:
    """Test user ID"""
    return "test_user"


@pytest.fixture
def test_orchestrator(temp_data_dir, test_user_id):
    """
    Test UserOrchestrator with master key set.

    Usage:
        def test_qube_creation(test_orchestrator):
            qube = await test_orchestrator.create_qube({...})
    """
    from orchestrator.user_orchestrator import UserOrchestrator

    orch = UserOrchestrator(user_id=test_user_id, data_dir=temp_data_dir)
    orch.set_master_key("test_password_12345")

    yield orch

    # Cleanup: close all loaded qubes
    for qube in orch.qubes.values():
        try:
            qube.close()
        except:
            pass


# =============================================================================
# QUBE FIXTURES
# =============================================================================

@pytest.fixture
def test_qube(temp_data_dir):
    """
    Basic test Qube instance.

    Returns:
        Qube instance ready for testing
    """
    from core.qube import Qube

    qube = Qube.create_new(
        qube_name="TestQube",
        creator="test_user",
        genesis_prompt="A test AI agent",
        ai_model="gpt-4o-mini",
        voice_model="test",
        data_dir=temp_data_dir,
        user_name="test_user",
        favorite_color="#FF0000"
    )

    yield qube

    try:
        qube.close()
    except:
        pass


@pytest.fixture
def test_qube_pair(temp_data_dir):
    """
    Two Qubes for testing interactions.

    Returns:
        Tuple of (qube_a, qube_b)
    """
    from core.qube import Qube

    qube_a = Qube.create_new(
        qube_name="QubeA",
        creator="test_user",
        genesis_prompt="First test Qube",
        ai_model="gpt-4o-mini",
        voice_model="test",
        data_dir=temp_data_dir,
        user_name="test_user"
    )

    qube_b = Qube.create_new(
        qube_name="QubeB",
        creator="test_user",
        genesis_prompt="Second test Qube",
        ai_model="gpt-4o-mini",
        voice_model="test",
        data_dir=temp_data_dir,
        user_name="test_user"
    )

    yield (qube_a, qube_b)

    try:
        qube_a.close()
        qube_b.close()
    except:
        pass


# =============================================================================
# API KEY FIXTURES
# =============================================================================

@pytest.fixture
def mock_openai_key() -> str:
    """Mock OpenAI API key for testing"""
    return "sk-test-mock-openai-key-1234567890abcdef"


@pytest.fixture
def mock_anthropic_key() -> str:
    """Mock Anthropic API key for testing"""
    return "sk-ant-test-mock-key-1234567890abcdef"


@pytest.fixture
def mock_api_keys(mock_openai_key, mock_anthropic_key) -> Dict[str, str]:
    """
    Dictionary of mock API keys for all providers.

    Usage:
        def test_ai_init(qube, mock_api_keys):
            qube.init_ai(mock_api_keys)
    """
    return {
        "openai": mock_openai_key,
        "anthropic": mock_anthropic_key,
        "google": "test-google-key-1234567890",
        "deepseek": "test-deepseek-key-1234567890",
        "perplexity": "test-perplexity-key-1234567890",
    }


# =============================================================================
# BLOCKCHAIN FIXTURES
# =============================================================================

@pytest.fixture
def mock_wallet_address() -> str:
    """Mock Bitcoin Cash wallet address"""
    return "bitcoincash:qr4aadjrpu73d2wxwkxkcrt6gqxgu6a7usxfm96fst"


@pytest.fixture
def mock_nft_category_id() -> str:
    """Mock NFT category ID (64-char hex string)"""
    return "a" * 64


@pytest.fixture
def mock_ipfs_cid() -> str:
    """Mock IPFS CID (CIDv0 format)"""
    return "QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG"


# =============================================================================
# NETWORK FIXTURES
# =============================================================================

@pytest.fixture
def mock_peer_id() -> str:
    """Mock libp2p peer ID"""
    return "12D3KooWTest1234567890ABCDEF"


# =============================================================================
# CLEANUP HOOKS
# =============================================================================

@pytest.fixture(autouse=True)
def cleanup_global_state():
    """
    Auto-cleanup global state after each test.

    Resets any global singletons or module-level state.
    """
    yield

    # Reset global replay protector
    try:
        from utils.replay_protection import reset_global_protector
        reset_global_protector()
    except:
        pass


@pytest.fixture(autouse=True)
def set_test_environment():
    """
    Set test environment variables before each test.

    Automatically applied to all tests.
    """
    # Store original env vars
    original_env = os.environ.copy()

    # Set test environment
    os.environ["QUBES_ENV"] = "test"
    os.environ["QUBES_LOG_LEVEL"] = "WARNING"  # Reduce noise

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


# =============================================================================
# PYTEST CONFIGURATION HOOKS
# =============================================================================

def pytest_configure(config):
    """
    Pytest configuration hook.

    Called before test collection.
    """
    # Ensure test data directories exist
    Path("tests/test_data").mkdir(exist_ok=True)


def pytest_collection_modifyitems(config, items):
    """
    Modify test items after collection.

    Auto-mark tests based on patterns.
    """
    for item in items:
        # Auto-mark integration tests
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)

        # Auto-mark unit tests
        elif "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)

        # Mark slow tests based on name
        if "performance" in item.name or "load" in item.name:
            item.add_marker(pytest.mark.slow)
            item.add_marker(pytest.mark.performance)

        # Mark security tests
        if "security" in item.name or "validation" in item.name or "inject" in item.name:
            item.add_marker(pytest.mark.security)


def pytest_addoption(parser):
    """
    Add custom command-line options.
    """
    parser.addoption(
        "--run-slow",
        action="store_true",
        default=False,
        help="Run slow tests (performance, load tests)"
    )


def pytest_runtest_setup(item):
    """
    Called before each test runs.

    Skip slow tests unless --run-slow flag is passed.
    """
    if "slow" in item.keywords and not item.config.getoption("--run-slow"):
        pytest.skip("need --run-slow option to run")
