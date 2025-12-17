#!/usr/bin/env python
"""Wrapper to run NFT minting test with correct Python path"""
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Now run the actual test
with open(project_root / "tests" / "integration" / "test_nft_minting.py", encoding='utf-8') as f:
    exec(f.read())
