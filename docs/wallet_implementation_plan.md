# Qube Asymmetric Multi-Sig Wallet System

## Overview

Give each Qube its own BCH wallet with asymmetric spending control:
- **Owner** can spend alone (full control, emergency withdrawal)
- **Qube** requires owner co-signature (proposes transactions, owner approves)

This enables real BCH gambling in poker while maintaining owner sovereignty.

## Architecture

```
+---------------------------------------------------------------------+
|                         USER (Owner)                                |
|  - Controls master wallet (holds Qube NFT)                          |
|  - Provides owner public key for P2SH                               |
|  - Co-signs Qube transactions OR spends alone                       |
+---------------------------------------------------------------------+
                              |
                              v
+---------------------------------------------------------------------+
|                    P2SH WALLET ADDRESS                              |
|  Script: IF <owner_pk> CHECKSIG                                     |
|          ELSE 2 <owner_pk> <qube_pk> 2 CHECKMULTISIG                |
|          ENDIF                                                      |
|                                                                     |
|  Spending Path 1: Owner alone (IF branch)                           |
|  Spending Path 2: Owner + Qube (ELSE branch)                        |
+---------------------------------------------------------------------+
                              |
                              v
+---------------------------------------------------------------------+
|                         QUBE                                        |
|  - Has existing secp256k1 keypair (for block signing)               |
|  - Same key used for wallet co-signing                              |
|  - Proposes transactions, waits for owner approval                  |
|  - Cannot spend without owner                                       |
+---------------------------------------------------------------------+
```

## P2SH Script Design

```
OP_IF
    <owner_pubkey>
    OP_CHECKSIG
OP_ELSE
    OP_2
    <owner_pubkey>
    <qube_pubkey>
    OP_2
    OP_CHECKMULTISIG
OP_ENDIF
```

**Spending Scenarios:**
1. **Owner alone:** `<owner_sig> OP_TRUE <redeem_script>`
2. **Both required:** `OP_0 <owner_sig> <qube_sig> OP_FALSE <redeem_script>`

## Wallet Creation at Mint Time

**Key Design Decision:** Wallet is created during Qube minting, not as a separate step.

When user mints a Qube:
1. User provides their BCH public key (from their wallet)
2. System generates P2SH address from (owner_pubkey + qube_pubkey)
3. Wallet address is stored in genesis block
4. Qube is ready to receive BCH immediately

**No backward compatibility** - wallet is mandatory for all new Qubes. Existing Qubes should be deleted and recreated.

### Minting Flow Changes

**Current flow:**
```
User provides: name, genesis prompt, AI settings, wallet address (for NFT)
System creates: Qube + NFT sent to wallet
```

**New flow:**
```
User provides: name, genesis prompt, AI settings, wallet address (for NFT), BCH public key
System creates: Qube + P2SH wallet + NFT sent to wallet
Genesis block includes: wallet_address, owner_pubkey, redeem_script_hash
```

## Transfer Handling

### What Happens to the Wallet on Transfer?

The P2SH address is derived from `owner_pubkey + qube_pubkey`. When ownership changes:

**Old wallet (old_owner + qube):**
- P2SH address controlled by OLD owner + Qube
- Old owner can STILL withdraw using IF branch (owner-only path)
- Funds belong to old owner - they funded it

**After transfer:**
- Old wallet info is NOT transferred to new owner
- New owner provides THEIR public key
- System creates NEW P2SH wallet (new_owner + qube)
- New wallet starts at 0 balance
- New owner funds it themselves

### Security Analysis

| Attack | Result |
|--------|--------|
| New owner tries IF branch | FAIL - Needs old owner's private key |
| New owner tries ELSE branch | FAIL - Needs old owner's sig + Qube's sig |
| New owner has Qube's key | FAIL - Both paths still need old owner's key |
| New owner knows redeem script | FAIL - Knowing script != signing |

**The new owner CANNOT access old funds** because both spending paths require the old owner's private key, which only the old owner possesses.

### Recommended: Require Withdrawal Before Transfer

```python
async def transfer_qube(...):
    # Check old wallet balance
    old_wallet_balance = await get_p2sh_balance(qube.wallet_address)

    if old_wallet_balance > 0:
        raise TransferError(
            f"Cannot transfer: Qube wallet still has {old_wallet_balance} sats. "
            f"Please withdraw funds first."
        )

    # Proceed with transfer...
```

This forces old owner to consciously withdraw before transferring.

## Implementation Phases

### Phase 0: BCH Script Spike (Validation)

**Purpose:** Validate BCH P2SH implementation before full integration.

**New file: `crypto/bch_script.py`** (~300 lines)

```python
"""
BCH Script Support for P2SH Wallets

Handles:
- Script opcode construction
- P2SH address derivation (CashAddr format)
- Transaction building with BCH format
- Signing with SIGHASH_FORKID (0x40)
"""

# Opcodes
OP_IF = 0x63
OP_ELSE = 0x67
OP_ENDIF = 0x68
OP_2 = 0x52
OP_CHECKSIG = 0xac
OP_CHECKMULTISIG = 0xae

def build_asymmetric_multisig_script(owner_pubkey: bytes, qube_pubkey: bytes) -> bytes:
    """Build IF owner ELSE 2-of-2 ENDIF redeem script"""

def script_to_p2sh_address(script: bytes, network: str = "mainnet") -> str:
    """Derive P2SH CashAddr (bitcoincash:p...) from redeem script"""

def calculate_sighash_forkid(tx: bytes, input_idx: int, script: bytes, value: int) -> bytes:
    """Calculate BIP143-style sighash with FORKID for BCH"""

def sign_input(sighash: bytes, private_key) -> bytes:
    """ECDSA sign with DER encoding + SIGHASH byte"""

def build_p2sh_spending_tx(utxos, outputs, redeem_script, signatures, spending_path: str) -> bytes:
    """Build complete signed transaction for P2SH spend"""
```

**Spike validation steps:**
1. Build script, derive P2SH address
2. Send 0.001 BCH to address (from Electron Cash)
3. Spend via owner-only path (IF branch)
4. Send another 0.001 BCH
5. Spend via 2-of-2 path (ELSE branch)
6. Verify both transactions on blockchain explorer

**Success criteria:** Both spending paths work on mainnet.

### Phase 1: Core Wallet Module

**New file: `crypto/wallet.py`**

```python
class QubeWallet:
    """Asymmetric multi-sig wallet for Qube BCH transactions"""

    def __init__(self, qube_private_key, owner_public_key):
        self.qube_key = qube_private_key
        self.owner_pubkey = owner_public_key
        self.redeem_script = self._build_redeem_script()
        self.p2sh_address = self._derive_p2sh_address()

    def _build_redeem_script(self) -> bytes:
        """Build asymmetric IF/ELSE redeem script"""

    def _derive_p2sh_address(self) -> str:
        """Derive P2SH address from redeem script"""

    def get_balance(self) -> int:
        """Query blockchain for balance in satoshis"""

    def get_utxos(self) -> List[UTXO]:
        """Get spendable UTXOs"""

    def create_transaction(self, outputs: List[TxOutput]) -> Transaction:
        """Create unsigned transaction"""

    def sign_as_qube(self, tx: Transaction) -> bytes:
        """Qube signs transaction (needs owner co-sign)"""

    def sign_as_owner(self, tx: Transaction, owner_key) -> bytes:
        """Owner signs transaction"""

    def finalize_2of2(self, tx, qube_sig, owner_sig) -> str:
        """Combine signatures, return signed tx hex"""

    def spend_owner_only(self, tx, owner_key) -> str:
        """Owner spends alone (IF branch)"""
```

**Dependencies:**
- New `crypto/bch_script.py` module (custom BCH script support ~300 lines)
- Keep `bitcash` for CashToken operations and UTXO fetching
- No external Bitcoin library needed (python-bitcoin-utils is BTC-only, doesn't support BCH's SIGHASH_FORKID)

**Key Conversion (existing key to wallet):**
```python
# From Qube's cryptography ECDSA key to wallet format
secret_int = qube.private_key.private_numbers().private_value
secret_bytes = secret_int.to_bytes(32, 'big')
```

### Phase 2: Minting Integration

**Modify: `blockchain/nft_minter.py`**

Add wallet creation during minting:
```python
class OptimizedNFTMinter:
    async def mint_qube_nft(
        self,
        qube,
        recipient_address: str,
        owner_pubkey: str,           # NEW: Owner's BCH public key
        ipfs_cid: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Mint Qube NFT with integrated wallet creation
        """
        # Create wallet from qube key + owner key
        from crypto.wallet import QubeWallet
        wallet = QubeWallet(qube.private_key, owner_pubkey)

        # Store wallet info in Qube
        qube.wallet_address = wallet.p2sh_address
        qube.owner_pubkey = owner_pubkey
        qube.redeem_script = wallet.redeem_script.hex()

        # Continue with NFT minting...
        # Include wallet_address in BCMR metadata
```

**Modify: `gui_bridge.py` - prepare_qube_for_minting (line 494)**

Add `owner_pubkey` parameter to existing function:
```python
async def prepare_qube_for_minting(
    self,
    name: str,
    genesis_prompt: str,
    ai_provider: str,
    ai_model: str,
    voice_model: str,
    wallet_address: str,
    owner_pubkey: str,              # NEW: For P2SH wallet
    password: str,
    encrypt_genesis: bool = False,
    favorite_color: str = "#00ff88",
    avatar_file: str = None,
    generate_avatar: bool = False,
    avatar_style: str = "cyberpunk"
) -> Dict[str, Any]:
```

Inside the function, after Qube creation:
```python
# Create P2SH wallet for Qube
from crypto.wallet import QubeWallet
wallet = QubeWallet(qube.private_key, owner_pubkey)

# Store wallet info with Qube
qube.wallet_address = wallet.p2sh_address
qube.owner_pubkey = owner_pubkey
qube.redeem_script = wallet.redeem_script

# Include in response
return {
    "success": True,
    "qube_id": qube.qube_id,
    "qube_wallet_address": wallet.p2sh_address,  # NEW
    # ... existing fields
}
```

Update handleStartMinting in CreateQubeModal.tsx to pass ownerPubkey:
```typescript
const result = await invoke<PendingMintingResult>('prepare_qube_for_minting', {
  userId,
  name: formData.name,
  genesisPrompt: formData.genesisPrompt,
  aiProvider: formData.aiProvider,
  aiModel: formData.aiModel,
  voiceModel: formData.voiceModel,
  walletAddress: formData.walletAddress,
  ownerPubkey: formData.ownerPubkey,  // NEW
  password,
  encryptGenesis: formData.encryptGenesis || false,
  favoriteColor: formData.favoriteColor,
  avatarFile: formData.avatarFile || null,
  generateAvatar: formData.generateAvatar || false,
  avatarStyle: formData.avatarStyle || null,
});
```

**Modify: `qubes-gui/src/components/tabs/CreateQubeModal.tsx`**

Update interface (line 16-28):
```typescript
export interface CreateQubeData {
  name: string;
  genesisPrompt: string;
  aiProvider: string;
  aiModel: string;
  voiceModel?: string;
  walletAddress: string;
  ownerPubkey: string;           // NEW: For P2SH wallet
  encryptGenesis?: boolean;
  favoriteColor: string;
  avatarFile?: string;
  generateAvatar?: boolean;
  avatarStyle?: string;
}
```

Add to Step 3 (Voice & Wallet section, after walletAddress input around line 741):
```typescript
{/* Owner Public Key for Qube Wallet */}
<div className="space-y-1">
  <label className="block text-text-primary text-sm">
    Your BCH Public Key (for Qube Wallet) *
  </label>
  <input
    type="text"
    value={formData.ownerPubkey}
    onChange={(e) => setFormData({ ...formData, ownerPubkey: e.target.value })}
    placeholder="02abc123... or 03def456..."
    className="w-full px-3 py-2 bg-bg-primary border border-glass-border rounded focus:border-accent-primary"
  />
  <p className="text-xs text-text-tertiary">
    This creates a BCH wallet for your Qube to hold earnings. You'll co-sign any spending,
    so the Qube can never send funds without your approval. Get your public key from:
    Electron Cash (Wallet → Information) or Cashonize (Settings → Export Public Key)
  </p>
  {errors.ownerPubkey && (
    <p className="text-accent-danger text-sm">{errors.ownerPubkey}</p>
  )}
</div>
```

Add validation in validateForm():
```typescript
if (!formData.ownerPubkey.trim()) {
  newErrors.ownerPubkey = 'BCH public key is required for wallet creation';
} else if (!/^(02|03)[a-fA-F0-9]{64}$/.test(formData.ownerPubkey.trim())) {
  newErrors.ownerPubkey = 'Must be compressed public key (02... or 03... + 64 hex chars)';
}
```

### Phase 3: Wallet Storage & Persistence

**Modify: `core/qube.py`**

Add wallet fields to Qube class:
```python
class Qube:
    # Existing fields...

    # New wallet fields
    wallet_address: Optional[str] = None      # P2SH address
    owner_pubkey: Optional[str] = None        # Owner's public key (hex)
    redeem_script: Optional[bytes] = None     # Full redeem script (encrypted at rest)
    wallet_initialized: bool = False
```

**Genesis block structure (mandatory for new Qubes):**
```python
genesis_block = {
    # Existing fields...
    "wallet": {
        "owner_pubkey": "02abc...",           # Owner's BCH public key
        "p2sh_address": "bitcoincash:p...",   # Derived P2SH address
        "redeem_script_hash": "abc123...",    # For verification (not full script)
        "qube_pubkey": "03def..."             # Qube's public key (derivable but stored for convenience)
    }
}
```

### Phase 4: Transaction Management

**New file: `blockchain/wallet_tx.py`**

```python
class WalletTransactionManager:
    """Manage Qube wallet transactions"""

    def __init__(self, qube: Qube):
        self.qube = qube
        self.wallet = QubeWallet(qube.private_key, qube.owner_pubkey)

    def propose_send(self, to_address: str, amount_sats: int) -> PendingTx:
        """Qube proposes a transaction, returns pending tx for approval"""

    def owner_approve(self, pending_tx: PendingTx, owner_wif: str) -> str:
        """Owner co-signs and broadcasts, returns txid"""

    def owner_reject(self, pending_tx: PendingTx) -> None:
        """Owner rejects pending transaction"""

    def owner_withdraw(self, to_address: str, amount_sats: int, owner_wif: str) -> str:
        """Owner withdraws directly (no Qube involvement)"""
```

**Transaction States:**
```python
class PendingTx:
    tx_id: str                    # Internal ID
    raw_tx: str                   # Unsigned transaction hex
    qube_signature: str           # Qube's signature
    outputs: List[TxOutput]       # Where funds go
    created_at: datetime
    expires_at: datetime          # Auto-expire pending txs
    status: Literal["pending", "approved", "rejected", "expired"]
```

### Phase 5: GUI Bridge Functions

**Modify: `gui_bridge.py`**

Add wallet commands:

```python
# Wallet initialization
async def initialize_qube_wallet(
    self,
    user_id: str,
    qube_id: str,
    owner_pubkey: str,  # From user's BCH wallet
    password: str
) -> Dict[str, Any]:
    """Initialize wallet for Qube, returns P2SH address"""

# Balance & info
async def get_qube_wallet_info(
    self,
    user_id: str,
    qube_id: str
) -> Dict[str, Any]:
    """Get wallet address, balance, pending txs"""

# Qube proposes transaction
async def propose_wallet_transaction(
    self,
    user_id: str,
    qube_id: str,
    to_address: str,
    amount_satoshis: int,
    memo: str,
    password: str
) -> Dict[str, Any]:
    """Qube proposes send, returns pending tx for approval"""

# Owner approves
async def approve_wallet_transaction(
    self,
    user_id: str,
    qube_id: str,
    pending_tx_id: str,
    owner_wif: str  # Via stdin secrets
) -> Dict[str, Any]:
    """Owner co-signs and broadcasts"""

# Owner withdraws directly
async def owner_withdraw_from_wallet(
    self,
    user_id: str,
    qube_id: str,
    to_address: str,
    amount_satoshis: int,
    owner_wif: str
) -> Dict[str, Any]:
    """Owner withdraws without Qube (IF branch)"""

# Get transaction history
async def get_wallet_transactions(
    self,
    user_id: str,
    qube_id: str
) -> Dict[str, Any]:
    """Get wallet transaction history"""
```

### Phase 6: GUI Components

#### 6A: Blockchain Data Card (Dashboard Tab)

**Modify: `qubes-gui/src/components/tabs/QubeManagerTab.tsx`**

Add wallet balances at the TOP of the Blockchain Data card (flipState 1), before other fields:

```typescript
{/* BLOCKCHAIN SIDE (flipState 1) */}
{/* ... existing wrapper ... */}

{/* Balances Section - NEW, at top */}
<div className="mb-4 p-3 bg-accent-primary/10 rounded-lg border border-accent-primary/30">
  <div className="flex justify-between items-center mb-2">
    <span className="text-text-tertiary text-sm">NFT Address:</span>
    <span className="text-accent-primary font-mono font-semibold">
      {nftBalance ? `${formatBCH(nftBalance)} BCH` : '—'}
    </span>
  </div>
  <div className="flex justify-between items-center">
    <span className="text-text-tertiary text-sm">Qube Wallet:</span>
    <span className="text-accent-success font-mono font-semibold">
      {walletBalance ? `${formatBCH(walletBalance)} BCH` : '—'}
    </span>
  </div>
</div>

{/* Existing Blockchain Stats Section */}
<div className="space-y-2 text-xs">
  {/* ... existing fields ... */}

  {/* NEW: Wallet Address field */}
  {qube.wallet?.p2sh_address && (
    <div className="flex justify-between items-center py-0.5">
      <span className="text-text-tertiary whitespace-nowrap">Wallet Address:</span>
      <BlockchainLink value={qube.wallet.p2sh_address} type="address" network={qube.network} />
    </div>
  )}
</div>
```

**Balance Display Explanation:**
- **NFT Address**: Balance at the owner's `bitcoincash:z...` address (where the Qube NFT lives)
- **Qube Wallet**: Balance at the Qube's `bitcoincash:p...` P2SH address (earnings/spending wallet)

#### 6B: Earnings Tab (Full Wallet Management)

**Modify: `qubes-gui/src/components/tabs/TabContent.tsx`**

Replace the placeholder Earnings tab content (lines 292-317) with full wallet management UI.
Uses the existing **Qube Roster** (left sidebar) to select which Qube's wallet to manage.

```typescript
{/* Earnings Tab */}
<div className={`absolute inset-0 overflow-y-auto ${currentTab === 'economy' ? 'z-10 opacity-100' : 'z-0 opacity-0 pointer-events-none'}`}>
  <EarningsTab
    qubes={qubes}
    selectedQubeIds={selectedQubeIds}
    onQubeSelect={handleQubeSelect}
  />
</div>
```

**New file: `qubes-gui/src/components/tabs/EarningsTab.tsx`**

```typescript
interface EarningsTabProps {
  qubes: Qube[];
  selectedQubeIds: string[];
  onQubeSelect: (qubeId: string) => void;
}

export const EarningsTab: React.FC<EarningsTabProps> = ({...}) => {
  const selectedQube = qubes.find(q => selectedQubeIds.includes(q.qube_id));

  if (!selectedQube) {
    return (
      <div className="p-6 text-center text-text-tertiary">
        Select a Qube from the roster to manage its wallet
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Wallet Header */}
      <div className="flex items-center gap-4">
        <img src={selectedQube.avatar} className="w-16 h-16 rounded-full" />
        <div>
          <h2 className="text-2xl text-text-primary">{selectedQube.name}'s Wallet</h2>
          <p className="text-text-tertiary font-mono text-sm">{selectedQube.wallet?.p2sh_address}</p>
        </div>
      </div>

      {/* Balance Display */}
      <GlassCard className="p-6 text-center">
        <div className="text-4xl font-display text-accent-primary mb-2">
          {formatBCH(walletBalance)} BCH
        </div>
        <div className="text-text-tertiary">≈ ${usdValue} USD</div>
      </GlassCard>

      {/* Deposit Section with QR */}
      <GlassCard className="p-6">
        <h3 className="text-lg mb-4">Deposit</h3>
        <div className="flex gap-6">
          <QRCodeSVG value={selectedQube.wallet?.p2sh_address} size={150} />
          <div>
            <p className="text-text-tertiary mb-2">Send BCH to:</p>
            <code className="block bg-bg-primary p-2 rounded text-sm break-all">
              {selectedQube.wallet?.p2sh_address}
            </code>
            <CopyButton text={selectedQube.wallet?.p2sh_address} />
          </div>
        </div>
      </GlassCard>

      {/* Withdraw Section */}
      <GlassCard className="p-6">
        <h3 className="text-lg mb-4">Withdraw</h3>
        <WithdrawForm qubeId={selectedQube.qube_id} balance={walletBalance} />
      </GlassCard>

      {/* Pending Transactions */}
      {pendingTxs.length > 0 && (
        <GlassCard className="p-6">
          <h3 className="text-lg mb-4">Pending Approvals</h3>
          {pendingTxs.map(tx => (
            <PendingTxCard key={tx.id} tx={tx} onApprove={handleApprove} onReject={handleReject} />
          ))}
        </GlassCard>
      )}

      {/* Transaction History */}
      <GlassCard className="p-6">
        <h3 className="text-lg mb-4">Transaction History</h3>
        <TransactionHistory qubeId={selectedQube.qube_id} />
      </GlassCard>
    </div>
  );
};
```

**New file: `qubes-gui/src/components/wallet/TransactionApprovalModal.tsx`**

```typescript
// Modal for owner to approve Qube-proposed transactions
// Shows: amount, recipient, Qube's reason
// Requires: Owner's wallet WIF (passed via secure input)
```

### ~~Phase 7: Game Integration (Poker) - FUTURE PHASE~~

*Out of scope for initial implementation. Will be added after wallet system is complete and tested.*

## File Structure

```
crypto/
  bch_script.py          # NEW: BCH Script opcodes, P2SH address, SIGHASH_FORKID
  wallet.py              # NEW: QubeWallet class wrapping bch_script.py

blockchain/
  wallet_tx.py           # NEW: Transaction management
  nft_minter.py          # MODIFY: Add wallet creation at mint time

core/
  qube.py                # MODIFY: Add wallet fields

gui_bridge.py            # MODIFY: Add wallet commands, modify minting

qubes-gui/
  src/
    components/
      tabs/
        CreateQubeModal.tsx    # MODIFY: Add owner_pubkey field
        QubeManagerTab.tsx     # MODIFY: Add balances to Blockchain Data card
        TabContent.tsx         # MODIFY: Replace Earnings tab placeholder
        EarningsTab.tsx        # NEW: Full wallet management UI
      wallet/
        TransactionApprovalModal.tsx  # NEW: Approve Qube txs
        PendingTxCard.tsx        # NEW: Pending tx display
        WithdrawForm.tsx         # NEW: Withdraw form component
        TransactionHistory.tsx   # NEW: Tx history list
    types/
      index.ts              # MODIFY: Add wallet types

  src-tauri/src/
    lib.rs                 # MODIFY: Add owner_pubkey to Rust commands
```

## Rust Layer Changes

**Modify: `qubes-gui/src-tauri/src/lib.rs` (line 1045)**

Add `owner_pubkey` parameter to Tauri command:
```rust
#[tauri::command]
async fn prepare_qube_for_minting(
    user_id: String,
    name: String,
    genesis_prompt: String,
    ai_provider: String,
    ai_model: String,
    voice_model: String,
    wallet_address: String,
    owner_pubkey: String,           // NEW
    password: String,
    encrypt_genesis: bool,
    favorite_color: String,
    avatar_file: Option<String>,
    generate_avatar: bool,
    avatar_style: Option<String>,
) -> Result<serde_json::Value, String> {
    // ... existing validation ...

    command
        .arg("prepare-qube-for-minting")
        // ... existing args ...
        .arg("--owner-pubkey")      // NEW
        .arg(&owner_pubkey)         // NEW
        // ... rest of args ...
}
```

Also add new wallet commands to lib.rs:
```rust
#[tauri::command]
async fn get_qube_wallet_info(
    user_id: String,
    qube_id: String,
) -> Result<serde_json::Value, String> { ... }

#[tauri::command]
async fn approve_wallet_transaction(
    user_id: String,
    qube_id: String,
    pending_tx_id: String,
    owner_wif: String,
) -> Result<serde_json::Value, String> { ... }

#[tauri::command]
async fn owner_withdraw_from_wallet(
    user_id: String,
    qube_id: String,
    to_address: String,
    amount_satoshis: u64,
    owner_wif: String,
) -> Result<serde_json::Value, String> { ... }
```

Register commands in `tauri::Builder` (line ~4201):
```rust
.invoke_handler(tauri::generate_handler![
    // ... existing commands ...
    get_qube_wallet_info,
    approve_wallet_transaction,
    owner_withdraw_from_wallet,
])
```

## Dependencies

**No new pip packages required.**

Custom BCH script support is built in-house via `crypto/bch_script.py` because:
- `python-bitcoin-utils` is BTC-only (no SIGHASH_FORKID support)
- `bitcash` doesn't support custom P2SH scripts
- Our script is simple (~10 opcodes), custom implementation is cleaner

**Existing dependencies used:**
- `bitcash>=1.1.0` - CashToken operations, UTXO fetching
- `ecdsa` or `cryptography` - Already used for Qube key signing

## Security Considerations

1. **Redeem Script Storage**
   - Encrypt redeem script with master password
   - Store in Qube's data directory
   - Include in encrypted backups

2. **Owner Key Handling**
   - Owner WIF passed via stdin (never logged)
   - Used only for signing, immediately discarded
   - Option for hardware wallet integration later

3. **Transaction Expiry**
   - Pending transactions expire after 24 hours
   - Prevents stale transactions from being approved later

4. **Spending Limits** (Optional)
   - Owner can set max spend per transaction
   - Daily spending limits
   - Require owner approval above threshold

5. **Transfer Safety**
   - Require wallet balance = 0 before transfer allowed
   - Old owner retains access to old wallet (IF branch)
   - New owner creates fresh wallet with their pubkey

## Implementation Order

0. **BCH Script Spike** (`crypto/bch_script.py`) - **DO FIRST**
   - Build P2SH script and address derivation
   - Test both spending paths on mainnet with real BCH
   - Validate before proceeding

1. **Core wallet module** (`crypto/wallet.py`)
   - Uses bch_script.py for script building
   - QubeWallet class wrapping script operations
   - Signing helpers for both paths

2. **Minting integration** (`blockchain/nft_minter.py`, `gui_bridge.py`)
   - Add owner_pubkey parameter (required)
   - Create wallet during mint
   - Store in genesis block

3. **Qube class updates** (`core/qube.py`)
   - Wallet fields (mandatory)
   - Load wallet from genesis on Qube load

4. **CreateQubeModal update** (`CreateQubeModal.tsx`)
   - Add owner public key input field (required)
   - Validation for hex public key format
   - Helper text explaining co-signing

5. **Transaction management** (`blockchain/wallet_tx.py`)
   - UTXO fetching via Chaingraph
   - Transaction building using bch_script.py
   - Signature handling for both paths

6. **GUI Bridge wallet commands** (`gui_bridge.py`)
   - Balance queries (both NFT address and P2SH wallet)
   - Transaction proposal/approval
   - Owner withdrawal

7. **Blockchain Data card update** (`QubeManagerTab.tsx`)
   - Add balances at top of card (NFT + Wallet)
   - Add Wallet Address field in list

8. **Earnings Tab build-out** (`EarningsTab.tsx`, `TabContent.tsx`)
   - Replace placeholder with full wallet UI
   - Uses Qube Roster for selection
   - Deposit QR, withdraw form, pending txs, history

9. **Wallet support components** (`components/wallet/`)
   - TransactionApprovalModal
   - PendingTxCard
   - WithdrawForm
   - TransactionHistory

~~10. Game integration (FUTURE - separate phase)~~
   ~~- Poker with real stakes~~
   ~~- Settlement transactions~~

## Testing Strategy

Testing directly on **mainnet** (BCH fees are negligible, ~0.001 cents per tx).

1. **Unit tests** for P2SH script construction and address derivation
2. **Mainnet validation** with small amounts (~0.001 BCH):
   - Verify P2SH address derivation is correct
   - Test owner-only spending (IF branch)
   - Test 2-of-2 spending (ELSE branch)
   - Test with real wallet apps (Electron Cash, Cashonize)
3. **Mint test** on mainnet with wallet creation
4. **GUI tests** for wallet display and approval flows

## Decision: Owner Key Source

User manually enters their BCH public key (compressed hex format: 02... or 03...).
- Simple, no external wallet integration needed
- User can get this from Electron Cash, Cashonize, or any BCH wallet

**Helper text in CreateQubeModal:**
> "This creates a BCH wallet for your Qube to hold earnings. You'll co-sign any spending,
> so the Qube can never send funds without your approval. Get your public key from:
> Electron Cash (Wallet → Information) or Cashonize (Settings → Export Public Key)"

Hardware wallet integration can be added later as enhancement.

## Notes

- Transaction fees deducted from Qube wallet balance
- No minimum balance enforced (user's responsibility)
- Pending transactions expire after 24 hours
- Testing directly on mainnet with small amounts (BCH fees are ~0.001 cents)

---

## Implementation Checklist

### Phase 0: BCH Script Spike
- [ ] Create `crypto/bch_script.py`
- [ ] Implement opcodes (OP_IF, OP_ELSE, OP_ENDIF, OP_CHECKSIG, OP_CHECKMULTISIG, OP_2)
- [ ] Implement `build_asymmetric_multisig_script(owner_pk, qube_pk)`
- [ ] Implement HASH160 (SHA256 → RIPEMD160)
- [ ] Implement CashAddr encoding for P2SH (`bitcoincash:p...`)
- [ ] Implement `script_to_p2sh_address(script, network)`
- [ ] Implement BIP143-style sighash calculation
- [ ] Implement SIGHASH_FORKID (0x41 = SIGHASH_ALL | FORKID)
- [ ] Implement `calculate_sighash_forkid(tx, input_idx, script, value)`
- [ ] Implement DER signature encoding
- [ ] Implement `sign_input(sighash, private_key)`
- [ ] Implement BCH transaction serialization
- [ ] Implement `build_p2sh_spending_tx(utxos, outputs, redeem_script, sigs, path)`
- [ ] **TEST: Generate P2SH address from test keys**
- [ ] **TEST: Send 0.001 BCH to P2SH address (from Electron Cash)**
- [ ] **TEST: Spend via owner-only path (IF branch) → verify on explorer**
- [ ] **TEST: Send another 0.001 BCH to P2SH address**
- [ ] **TEST: Spend via 2-of-2 path (ELSE branch) → verify on explorer**

### Phase 1: Core Wallet Module
- [ ] Create `crypto/wallet.py`
- [ ] Implement `QubeWallet.__init__(qube_private_key, owner_public_key)`
- [ ] Implement `QubeWallet._build_redeem_script()` using bch_script
- [ ] Implement `QubeWallet._derive_p2sh_address()` using bch_script
- [ ] Implement `QubeWallet.get_balance()` via Chaingraph
- [ ] Implement `QubeWallet.get_utxos()` via Chaingraph
- [ ] Implement `QubeWallet.create_transaction(outputs)`
- [ ] Implement `QubeWallet.sign_as_qube(tx)`
- [ ] Implement `QubeWallet.sign_as_owner(tx, owner_key)`
- [ ] Implement `QubeWallet.finalize_2of2(tx, qube_sig, owner_sig)`
- [ ] Implement `QubeWallet.spend_owner_only(tx, owner_key)`
- [ ] Add key conversion helper (cryptography → raw bytes)

### Phase 2: Minting Integration
- [ ] Modify `blockchain/nft_minter.py`: add `owner_pubkey` parameter
- [ ] Create wallet during `mint_qube_nft()`
- [ ] Store wallet info in Qube object
- [ ] Include wallet_address in BCMR metadata
- [ ] Modify `gui_bridge.py`: add `owner_pubkey` to `prepare_qube_for_minting()`
- [ ] Create wallet in `prepare_qube_for_minting()` after Qube creation
- [ ] Return `qube_wallet_address` in response
- [ ] Modify `orchestrator/user_orchestrator.py`: add wallet to genesis block

### Phase 3: Qube Class Updates
- [ ] Modify `core/qube.py`: add wallet fields to Qube class
  - [ ] `wallet_address: Optional[str]`
  - [ ] `owner_pubkey: Optional[str]`
  - [ ] `redeem_script: Optional[bytes]`
- [ ] Add `wallet` object to genesis block structure
- [ ] Load wallet from genesis on Qube initialization
- [ ] Add wallet property accessors

### Phase 4: CreateQubeModal Update
- [ ] Add `ownerPubkey` to `CreateQubeData` interface
- [ ] Add owner public key input field in Step 3
- [ ] Add helper text explaining co-signing
- [ ] Add validation in `validateForm()` (02.../03... + 64 hex)
- [ ] Pass `ownerPubkey` to `prepare_qube_for_minting` invoke
- [ ] Add `ownerPubkey` to form initial state
- [ ] Modify `lib.rs`: add `owner_pubkey: String` parameter
- [ ] Modify `lib.rs`: add `--owner-pubkey` CLI argument

### Phase 5: Transaction Management
- [ ] Create `blockchain/wallet_tx.py`
- [ ] Implement `WalletTransactionManager` class
- [ ] Implement `propose_send(to_address, amount_sats)` → PendingTx
- [ ] Implement `owner_approve(pending_tx, owner_wif)` → txid
- [ ] Implement `owner_reject(pending_tx)`
- [ ] Implement `owner_withdraw(to_address, amount_sats, owner_wif)` → txid
- [ ] Implement `PendingTx` dataclass with expiry
- [ ] Implement pending tx storage (JSON in qube dir)
- [ ] Implement tx broadcast via bitcash or direct API

### Phase 6: GUI Bridge Wallet Commands
- [ ] Add `get_qube_wallet_info()` to gui_bridge.py
- [ ] Add `propose_wallet_transaction()` to gui_bridge.py
- [ ] Add `approve_wallet_transaction()` to gui_bridge.py
- [ ] Add `owner_withdraw_from_wallet()` to gui_bridge.py
- [ ] Add `get_wallet_transactions()` to gui_bridge.py
- [ ] Add corresponding Tauri commands in lib.rs
- [ ] Register new commands in `tauri::generate_handler![]`

### Phase 7: Blockchain Data Card Update
- [ ] Modify `QubeManagerTab.tsx`: add balances section at top of card
- [ ] Implement `formatBCH()` utility function
- [ ] Add NFT Address balance display
- [ ] Add Qube Wallet balance display
- [ ] Add Wallet Address field to blockchain stats list
- [ ] Implement balance fetching (via Tauri command)
- [ ] Add refresh/loading state for balances

### Phase 8: Earnings Tab Build-out
- [ ] Create `EarningsTab.tsx` component
- [ ] Implement wallet header with avatar and address
- [ ] Implement balance display card with USD conversion
- [ ] Implement deposit section with QR code
- [ ] Implement copy button for address
- [ ] Add `qrcode.react` package if not present
- [ ] Modify `TabContent.tsx`: replace placeholder with EarningsTab
- [ ] Pass required props (qubes, selectedQubeIds, etc.)

### Phase 9: Wallet Support Components
- [ ] Create `components/wallet/` directory
- [ ] Create `WithdrawForm.tsx` component
  - [ ] Amount input (BCH and satoshis)
  - [ ] Destination address input
  - [ ] Owner WIF input (secure/password type)
  - [ ] Submit button with confirmation
- [ ] Create `PendingTxCard.tsx` component
  - [ ] Display amount, recipient, timestamp
  - [ ] Approve/Reject buttons
  - [ ] Expiry countdown
- [ ] Create `TransactionApprovalModal.tsx`
  - [ ] Full transaction details
  - [ ] Owner WIF input
  - [ ] Confirm/Cancel buttons
- [ ] Create `TransactionHistory.tsx` component
  - [ ] Fetch tx history from blockchain
  - [ ] Display list with amount, date, status
  - [ ] Link to explorer
- [ ] Add wallet types to `types/index.ts`

### Final Validation
- [ ] Delete existing test Qubes
- [ ] Create new Qube with wallet (full flow)
- [ ] Verify wallet address appears in genesis block
- [ ] Verify balances display on Blockchain Data card
- [ ] Verify Earnings tab shows wallet correctly
- [ ] Test deposit (send BCH to wallet)
- [ ] Test owner withdrawal (IF branch)
- [ ] Test 2-of-2 transaction flow (ELSE branch)
- [ ] Test transfer blocking when balance > 0
- [ ] Verify old owner can still access old wallet after transfer
