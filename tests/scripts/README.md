# Qubes Helper Scripts

This directory contains utility scripts for testing and development.

## Scripts

### Platform Initialization

#### `init_platform.py`
**Purpose:** Initialize the Qubes platform minting token

**What it does:**
- Creates the platform-wide minting token on Bitcoin Cash
- Sets up the category ID for all Qube NFTs
- Required once before minting any Qube NFTs

**Usage:**
```bash
python tests/scripts/init_platform.py
```

**Requirements:**
- BCH wallet with funds
- Private key in `.env` as `BCH_PRIVATE_KEY`

---

#### `init_platform_auto.py`
**Purpose:** Automated platform initialization

**What it does:**
- Automatically initializes platform with minimal prompts
- Checks for existing platform token
- Creates new token if needed

**Usage:**
```bash
python tests/scripts/init_platform_auto.py
```

---

### Migration & Setup

#### `migrate_existing_qubes.py`
**Purpose:** Migrate Qubes to new file structure

**What it does:**
- Migrates old Qubes from flat structure to user-based structure
- Moves files to proper locations
- Creates backups before migration

**Usage:**
```bash
# Dry run
python tests/scripts/migrate_existing_qubes.py username

# Execute migration
python tests/scripts/migrate_existing_qubes.py username --execute
```

---

#### `migrate_file_structure.py`
**Purpose:** Migrate Qubes to latest file structure

**What it does:**
- Converts old structure to new user-based organization
- Renames qube.json to genesis.json
- Organizes files into chain/, audio/, images/, blocks/ folders

**Usage:**
```bash
# Dry run
python tests/scripts/migrate_file_structure.py username

# Execute migration
python tests/scripts/migrate_file_structure.py username --execute
```

---

### Blockchain Tools

#### `setup_blockchain_wallet.py`
**Purpose:** Setup Bitcoin Cash wallet for Qube minting

**What it does:**
- Generates new BCH wallet or imports existing
- Displays wallet address and balance
- Saves private key securely

**Usage:**
```bash
python tests/scripts/setup_blockchain_wallet.py
```

---

#### `save_minting_token.py`
**Purpose:** Save platform minting token information

**What it does:**
- Stores minting token details
- Saves category ID and transaction info
- Used after platform initialization

**Usage:**
```bash
python tests/scripts/save_minting_token.py
```

---

#### `save_minting_token_quick.py`
**Purpose:** Quick save of minting token

**What it does:**
- Faster version of save_minting_token.py
- Minimal prompts
- Auto-detects token from environment

**Usage:**
```bash
python tests/scripts/save_minting_token_quick.py
```

---

#### `diagnose_minting_token.py`
**Purpose:** Diagnose issues with platform minting token

**What it does:**
- Checks token existence and validity
- Verifies blockchain state
- Provides troubleshooting information

**Usage:**
```bash
python tests/scripts/diagnose_minting_token.py
```

---

### Testing & Verification

#### `run_mint_test.py`
**Purpose:** Quick NFT minting test

**What it does:**
- Tests NFT minting functionality
- Creates a test Qube NFT
- Verifies on blockchain

**Usage:**
```bash
python tests/scripts/run_mint_test.py
```

---

### `run_e2e_test.py`
**Purpose:** Quick runner for end-to-end Qube creation test

**What it does:**
- Loads `.env` file automatically
- Runs the automated Qube creation example
- Useful for quick testing of the full stack

**Usage:**
```bash
python scripts/run_e2e_test.py
```

**Environment variables required:**
- `QUBE_NAME` (optional, defaults to "ArtemisAI")
- `CREATOR_EMAIL` (optional, defaults to "qubes-test@blockchain.com")
- `AI_PROVIDER` (optional, defaults to first available provider)

---

### `verify_nft.py`
**Purpose:** Quick NFT ownership verification

**What it does:**
- Verifies NFT ownership on Bitcoin Cash blockchain
- Uses Chaingraph GraphQL API
- Shows NFT details (value, commitment, capability)

**Usage:**
```bash
python scripts/verify_nft.py
```

**Default verification:**
- Category ID: `9414252c6d661907829c9cee3fbaf2e1278d59a80392858fcd22916862602b4b`
- Owner: `bitcoincash:zpr6a0r3wtrcam0q26k8ldj5ce5se6ck3gxyapgsfx`

**To verify different NFT:**
Edit the script and change the `category_id` and `owner_address` variables.

---

## Adding New Scripts

When adding new scripts to this directory:

1. **Use shebang:** Start with `#!/usr/bin/env python`
2. **Add docstring:** Explain what the script does
3. **Set execute permission:** `chmod +x scripts/your_script.py`
4. **Update this README:** Document the script's purpose and usage

## Project Structure

```
tests/scripts/
├── README.md                      # This file
├── init_platform.py               # Platform initialization
├── init_platform_auto.py          # Auto platform init
├── migrate_existing_qubes.py      # Old structure migration
├── migrate_file_structure.py      # New structure migration
├── setup_blockchain_wallet.py     # BCH wallet setup
├── save_minting_token.py          # Save minting token
├── save_minting_token_quick.py    # Quick token save
├── diagnose_minting_token.py      # Token diagnostics
├── run_mint_test.py               # NFT minting test
├── run_e2e_example.py             # End-to-end test runner
├── verify_nft.py                  # NFT verification
└── view_qube_blocks.py            # Block viewer utility
```

## Related Directories

- `tests/examples/` - Full example programs demonstrating features
- `tests/unit/` - Unit tests (fast, isolated)
- `tests/integration/` - Integration tests requiring external services
