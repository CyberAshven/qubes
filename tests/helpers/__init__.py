"""
Test utilities package

Provides factories, assertions, and mocks for testing.
"""

from .factories import (
    create_test_qube,
    create_test_qube_with_blocks,
    create_test_message,
    create_test_thought,
    create_test_relationship,
    create_test_permission,
)

from .assertions import (
    assert_valid_qube_id,
    assert_valid_block_structure,
    assert_valid_signature,
    assert_valid_timestamp,
    assert_blocks_linked,
    assert_encrypted_data,
    assert_json_serializable,
)

__all__ = [
    # Factories
    "create_test_qube",
    "create_test_qube_with_blocks",
    "create_test_message",
    "create_test_thought",
    "create_test_relationship",
    "create_test_permission",
    # Assertions
    "assert_valid_qube_id",
    "assert_valid_block_structure",
    "assert_valid_signature",
    "assert_valid_timestamp",
    "assert_blocks_linked",
    "assert_encrypted_data",
    "assert_json_serializable",
]
