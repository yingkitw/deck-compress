#!/usr/bin/env python3
"""
Test runner for deck_compress.py
"""

import sys
import os
import subprocess

def main():
    """Run the tests for deck_compress."""
    print("🧪 Running deck_compress tests...")
    print("=" * 50)

    # Change to the project directory
    project_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_dir)

    # Try different ways to run tests
    test_commands = [
        # Try pytest first with plugin autoloading disabled
        [sys.executable, "-m", "pytest", "tests/test_deck_compress.py", "-v", "--tb=short"],
        # Try running the test file directly
        [sys.executable, "tests/test_deck_compress.py"],
        # Try running with python -m
        [sys.executable, "-m", "test_deck_compress"],
    ]

    # Set environment variable to disable problematic plugin autoloading
    env = os.environ.copy()
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"

    for i, cmd in enumerate(test_commands, 1):
        print(f"\nAttempt {i}: {' '.join(cmd)}")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, env=env)

            print("STDOUT:")
            print(result.stdout)
            if result.stderr:
                print("STDERR:")
                print(result.stderr)

            if result.returncode == 0:
                print(f"\n✅ Tests passed with command: {' '.join(cmd)}")
                return 0
            else:
                print(f"\n❌ Tests failed with return code: {result.returncode}")

        except subprocess.TimeoutExpired:
            print("❌ Test execution timed out")
        except FileNotFoundError:
            print("❌ Command not found")
        except Exception as e:
            print(f"❌ Error running command: {e}")

    print("\n❌ All test methods failed")
    print("\nTroubleshooting tips:")
    print("1. Make sure all dependencies are installed: pip install -r requirements.txt")
    print("2. Check if pytest is available: pip install pytest pytest-cov")
    print("3. Verify the deck_compress.py file is syntactically correct")
    print("4. Try running manually: python3 test_deck_compress.py")
    print("5. Run test summary: python3 test_summary.py")
    print("6. Check test coverage: pytest --cov=deck_compress --cov-report=html")

    return 1

if __name__ == "__main__":
    sys.exit(main())
