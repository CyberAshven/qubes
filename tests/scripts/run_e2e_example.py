#!/usr/bin/env python
"""
Quick runner for end-to-end test with .env file loading
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load .env file
from dotenv import load_dotenv
load_dotenv()

# Now import and run the test
from examples.end_to_end_qube_creation_auto import main
import asyncio

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code or 0)
