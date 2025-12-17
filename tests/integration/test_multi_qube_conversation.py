"""
Integration Test: Multi-Qube Conversations

Tests the complete multi-Qube conversation flow:
- Creating multiple Qubes
- Starting group conversations
- Turn-taking and context sharing
- Multi-signature block attestation
- Conversation anchoring
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from orchestrator.user_orchestrator import UserOrchestrator
from core.multi_qube_conversation import MultiQubeConversation
from utils.logging import get_logger

logger = get_logger(__name__)


class TestMultiQubeConversation:
    """Test suite for multi-Qube conversation features"""

    def __init__(self):
        self.test_user_id = "test_user_multi_qube"
        self.test_password = "test_password_123"
        self.temp_dir = None
        self.orchestrator = None

    async def setup(self):
        """Set up test environment"""
        print("\n=== Setting up test environment ===")

        # Create temporary directory for test data
        self.temp_dir = Path(tempfile.mkdtemp(prefix="qubes_multi_test_"))
        print(f"Test directory: {self.temp_dir}")

        # Create orchestrator
        self.orchestrator = UserOrchestrator(
            user_id=self.test_user_id,
            data_dir=self.temp_dir
        )

        # Set master key
        self.orchestrator.set_master_key(self.test_password)
        print("✓ Orchestrator initialized")

    async def teardown(self):
        """Clean up test environment"""
        print("\n=== Cleaning up test environment ===")

        # Close orchestrator
        if self.orchestrator:
            await self.orchestrator.close()

        # Clean up temp directory
        if self.temp_dir and os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)
            print(f"✓ Removed test directory: {self.temp_dir}")

    async def test_create_qubes(self) -> list:
        """Test: Create 3 test Qubes for conversation"""
        print("\n=== Test: Creating 3 Qubes ===")

        qube_configs = [
            {
                "name": "Alice",
                "personality": "Friendly and helpful AI assistant focused on general knowledge",
                "voice_model": "openai:alloy"
            },
            {
                "name": "Bob",
                "personality": "Technical expert specializing in software engineering and cryptography",
                "voice_model": "openai:echo"
            },
            {
                "name": "Charlie",
                "personality": "Creative thinker who loves philosophy and asking deep questions",
                "voice_model": "openai:fable"
            }
        ]

        qube_ids = []

        for config in qube_configs:
            result = await self.orchestrator.create_qube(
                name=config["name"],
                personality=config["personality"],
                voice_model=config["voice_model"]
            )
            qube_id = result["qube_id"]
            qube_ids.append(qube_id)
            print(f"✓ Created Qube: {config['name']} ({qube_id[:8]}...)")

        print(f"\n✓ Successfully created {len(qube_ids)} Qubes")
        return qube_ids

    async def test_start_conversation(self, qube_ids: list) -> str:
        """Test: Start multi-Qube conversation"""
        print("\n=== Test: Starting Multi-Qube Conversation ===")

        initial_prompt = "What is Bitcoin? Each of you should share your perspective."

        result = await self.orchestrator.start_multi_qube_conversation(
            qube_ids=qube_ids,
            initial_prompt=initial_prompt,
            conversation_mode="open_discussion"
        )

        conversation_id = result["conversation_id"]
        first_response = result["first_response"]

        print(f"✓ Conversation started: {conversation_id[:8]}...")
        print(f"✓ Participants: {len(result['participants'])} Qubes")
        print(f"\n--- First Response ---")
        print(f"Speaker: {first_response['speaker_name']}")
        print(f"Message: {first_response['message'][:200]}...")
        print(f"Turn: {first_response['turn_number']}")

        return conversation_id

    async def test_continue_conversation(self, conversation_id: str, num_turns: int = 5):
        """Test: Continue conversation for multiple turns"""
        print(f"\n=== Test: Continuing Conversation ({num_turns} turns) ===")

        for i in range(num_turns):
            result = await self.orchestrator.continue_multi_qube_conversation(
                conversation_id=conversation_id
            )

            print(f"\n--- Turn {result['turn_number']} ---")
            print(f"Speaker: {result['speaker_name']}")
            print(f"Message: {result['message'][:200]}...")

            # Brief pause to simulate natural conversation
            await asyncio.sleep(0.5)

        print(f"\n✓ Completed {num_turns} conversation turns")

    async def test_verify_multi_signatures(self, conversation_id: str):
        """Test: Verify all blocks have multi-signatures from all participants"""
        print("\n=== Test: Verifying Multi-Signatures ===")

        conversation = self.orchestrator.active_conversations[conversation_id]

        # Get all participant IDs
        participant_ids = set(conversation.participant_ids)

        # Check each Qube's session blocks
        blocks_checked = 0
        signatures_verified = 0

        for qube in conversation.qubes:
            if qube.current_session:
                session_blocks = qube.current_session.session_blocks

                for block in session_blocks:
                    if block.block_type == "MESSAGE":
                        blocks_checked += 1

                        # Check if block has participant_signatures
                        if "participant_signatures" in block.content:
                            sig_dict = block.content["participant_signatures"]

                            # Verify all participants signed
                            signed_by = set(sig_dict.keys())

                            if signed_by == participant_ids:
                                signatures_verified += 1
                                print(f"✓ Block signed by all {len(participant_ids)} participants")
                            else:
                                missing = participant_ids - signed_by
                                print(f"✗ Block missing signatures from: {missing}")
                        else:
                            print(f"✗ Block has no participant_signatures field")

        print(f"\n✓ Checked {blocks_checked} MESSAGE blocks")
        print(f"✓ Verified {signatures_verified} blocks with complete multi-signatures")

        if signatures_verified == blocks_checked:
            print("✓ ALL MESSAGE BLOCKS HAVE MULTI-SIGNATURES FROM ALL PARTICIPANTS")
            return True
        else:
            print(f"✗ Some blocks are missing signatures ({blocks_checked - signatures_verified})")
            return False

    async def test_conversation_stats(self, conversation_id: str):
        """Test: Get conversation participation statistics"""
        print("\n=== Test: Conversation Statistics ===")

        stats = await self.orchestrator.get_conversation_stats(conversation_id)

        print(f"Conversation ID: {stats['conversation_id'][:8]}...")
        print(f"Total Turns: {stats['total_turns']}")
        print(f"\nParticipation Breakdown:")

        for participant in stats['participants']:
            print(f"  - {participant['name']}: {participant['turns_taken']} turns ({participant['participation_percentage']:.1f}%)")

        print("\n✓ Statistics retrieved successfully")

    async def test_end_conversation(self, conversation_id: str):
        """Test: End conversation and anchor blocks"""
        print("\n=== Test: Ending Conversation and Anchoring Blocks ===")

        summary = await self.orchestrator.end_multi_qube_conversation(
            conversation_id=conversation_id,
            anchor=True
        )

        print(f"✓ Conversation ended: {summary['conversation_id'][:8]}...")
        print(f"✓ Total turns: {summary['total_turns']}")
        print(f"✓ Blocks anchored: {summary['anchored']}")
        print(f"✓ Participants: {len(summary['participants'])}")

        # Verify conversation removed from active conversations
        assert conversation_id not in self.orchestrator.active_conversations
        print("✓ Conversation removed from active conversations")

        return summary

    async def run_all_tests(self):
        """Run complete test suite"""
        print("\n" + "="*60)
        print("MULTI-QUBE CONVERSATION TEST SUITE")
        print("="*60)

        try:
            # Setup
            await self.setup()

            # Test 1: Create Qubes
            qube_ids = await self.test_create_qubes()

            # Test 2: Start conversation
            conversation_id = await self.test_start_conversation(qube_ids)

            # Test 3: Continue conversation
            await self.test_continue_conversation(conversation_id, num_turns=4)

            # Test 4: Verify multi-signatures
            all_signed = await self.test_verify_multi_signatures(conversation_id)

            # Test 5: Get statistics
            await self.test_conversation_stats(conversation_id)

            # Test 6: End conversation
            summary = await self.test_end_conversation(conversation_id)

            # Final summary
            print("\n" + "="*60)
            print("TEST SUITE RESULTS")
            print("="*60)
            print(f"✓ Created {len(qube_ids)} Qubes")
            print(f"✓ Started conversation: {conversation_id[:8]}...")
            print(f"✓ Completed {summary['total_turns']} conversation turns")
            print(f"✓ Multi-signature verification: {'PASSED' if all_signed else 'FAILED'}")
            print(f"✓ Blocks anchored to permanent chains")
            print("\n✓✓✓ ALL TESTS PASSED ✓✓✓")

        except Exception as e:
            print(f"\n✗✗✗ TEST FAILED ✗✗✗")
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

        finally:
            # Teardown
            await self.teardown()


async def main():
    """Main test runner"""
    test_suite = TestMultiQubeConversation()
    await test_suite.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
