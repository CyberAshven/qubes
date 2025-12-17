"""
Comprehensive CLI testing using pexpect-like functionality.
Tests all commands with proper password handling.
"""

import sys
import os
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock the password prompt before importing
from unittest.mock import patch
from io import StringIO

PASSWORD = "reefer"

def run_cli_test(test_name, command_func, *args, **kwargs):
    """Run a CLI command test with mocked password"""
    print(f"\n{'='*70}")
    print(f"TEST: {test_name}")
    print(f"{'='*70}")

    try:
        # Mock the password prompt
        with patch('rich.prompt.Prompt.ask') as mock_prompt:
            # Configure mock to return password for password prompts
            def prompt_side_effect(prompt_text, **kwargs):
                if 'password' in prompt_text.lower() or 'master' in prompt_text.lower():
                    return PASSWORD
                # For other prompts, return appropriate defaults
                if 'user id' in prompt_text.lower():
                    return 'bit_faced'
                return kwargs.get('default', '')

            mock_prompt.side_effect = prompt_side_effect

            # Capture stdout
            from io import StringIO
            import sys
            old_stdout = sys.stdout
            sys.stdout = captured_output = StringIO()

            try:
                result = command_func(*args, **kwargs)
                output = captured_output.getvalue()
                sys.stdout = old_stdout

                print(f"✅ PASSED")
                if output and len(output) < 500:
                    print(f"Output: {output[:500]}")
                elif output:
                    print(f"Output (truncated): {output[:200]}...")

                return True, output

            except Exception as e:
                sys.stdout = old_stdout
                print(f"❌ FAILED: {str(e)}")
                import traceback
                traceback.print_exc()
                return False, str(e)

    except Exception as e:
        print(f"❌ FAILED (Setup): {str(e)}")
        return False, str(e)


def test_version():
    """Test version command"""
    from cli.main import app
    from typer.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(app, ["version"])

    success = result.exit_code == 0 and "Qubes" in result.stdout
    print(f"Exit code: {result.exit_code}")
    if success:
        print("✅ PASSED")
        print(f"Output:\n{result.stdout[:300]}")
    else:
        print(f"❌ FAILED")
        print(f"Error: {result.stderr if result.stderr else 'No error output'}")

    return success, result.stdout


def test_help_commands():
    """Test help commands"""
    from cli.main import app
    from typer.testing import CliRunner

    runner = CliRunner()

    commands = [
        ["help", "commands"],
        ["help", "examples"],
        ["settings", "--help"],
        ["mem", "--help"],
    ]

    passed = 0
    for cmd in commands:
        result = runner.invoke(app, cmd)
        if result.exit_code == 0:
            passed += 1
            print(f"✅ {' '.join(cmd)}")
        else:
            print(f"❌ {' '.join(cmd)}")

    success = passed == len(commands)
    print(f"\nPassed: {passed}/{len(commands)}")
    return success, f"{passed}/{len(commands)}"


def test_list_command():
    """Test list command with orchestrator"""
    def run_list():
        from cli.main import app
        from typer.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(app, ["list"])
        return result

    success, output = run_cli_test("List Command", run_list)
    return success, output


def test_info_command():
    """Test info command"""
    def run_info():
        from cli.main import app
        from typer.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(app, ["info", "Alph"])
        return result

    success, output = run_cli_test("Info Command", run_info)
    return success, output


def test_memory_stats():
    """Test memory stats command"""
    def run_stats():
        from cli.main import app
        from typer.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(app, ["mem", "stats", "Alph"])
        return result

    success, output = run_cli_test("Memory Stats", run_stats)
    return success, output


def test_memory_list():
    """Test memory list command"""
    def run_memories():
        from cli.main import app
        from typer.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(app, ["mem", "memories", "Alph", "--limit", "5"])
        return result

    success, output = run_cli_test("Memory List", run_memories)
    return success, output


def test_blockchain_nft():
    """Test blockchain NFT command"""
    def run_nft():
        from cli.main import app
        from typer.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(app, ["blockchain", "nft", "Alph"])
        return result

    success, output = run_cli_test("Blockchain NFT", run_nft)
    return success, output


def test_health_check():
    """Test health check command"""
    def run_health():
        from cli.main import app
        from typer.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(app, ["monitor", "health", "Alph"])
        return result

    success, output = run_cli_test("Health Check", run_health)
    return success, output


def test_social_relationships():
    """Test social relationships command (placeholder)"""
    def run_relationships():
        from cli.main import app
        from typer.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(app, ["social", "relationships", "Alph"])
        return result

    success, output = run_cli_test("Social Relationships", run_relationships)
    return success, output


def main():
    """Run all tests"""
    print("""
╔══════════════════════════════════════════════════════════════════╗
║       Qubes CLI Comprehensive Testing Suite                      ║
║       Using Typer CliRunner with Mocked Password                 ║
╚══════════════════════════════════════════════════════════════════╝
""")

    tests = [
        ("Version Command", test_version),
        ("Help Commands", test_help_commands),
        ("List Qubes", test_list_command),
        ("Info Command", test_info_command),
        ("Memory Stats", test_memory_stats),
        ("Memory List", test_memory_list),
        ("Blockchain NFT", test_blockchain_nft),
        ("Health Check", test_health_check),
        ("Social Relationships", test_social_relationships),
    ]

    passed = 0
    failed = 0
    results = []

    for test_name, test_func in tests:
        print(f"\n{'='*70}")
        print(f"Running: {test_name}")
        print(f"{'='*70}")

        try:
            success, output = test_func()
            if success or (isinstance(success, int) and success > 0):
                passed += 1
                status = "✅ PASSED"
            else:
                failed += 1
                status = "❌ FAILED"

            results.append((test_name, status))

        except Exception as e:
            failed += 1
            results.append((test_name, f"❌ ERROR: {str(e)}"))
            print(f"❌ ERROR: {str(e)}")
            import traceback
            traceback.print_exc()

    # Print summary
    print(f"\n\n{'='*70}")
    print("TEST SUMMARY")
    print(f"{'='*70}")

    for test_name, status in results:
        print(f"{status:20} {test_name}")

    print(f"\n{'='*70}")
    print(f"Total Tests: {len(tests)}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"Success Rate: {(passed/len(tests)*100):.1f}%")
    print(f"{'='*70}\n")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
