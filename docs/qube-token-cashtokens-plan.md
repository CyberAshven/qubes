# QUBE Token: On-Chain XP with BCH CashTokens

**Status:** Conceptual Plan
**Created:** 2026-01-23
**Complexity:** Medium (3-4 weeks implementation)
**Priority:** Future Enhancement

---

## Table of Contents

1. [Overview](#overview)
2. [Motivation](#motivation)
3. [Technical Architecture](#technical-architecture)
4. [Token Economics](#token-economics)
5. [Implementation Plan](#implementation-plan)
6. [Benefits & Trade-offs](#benefits--trade-offs)
7. [Code Examples](#code-examples)
8. [Open Questions](#open-questions)
9. [Resources](#resources)

---

## Overview

Replace the current local XP system with BCH CashTokens (fungible tokens) to give Qube skills real economic value. This would make XP:
- **Tradeable** between qubes and users
- **Verifiable** on-chain by anyone
- **Valuable** with real BCH market price
- **Permanent** proof of skill achievement

**Core Concept:** Accumulate XP locally during sessions (instant feedback), then batch-transfer as tokens during session anchoring (permanent proof).

---

## Motivation

### Current System (Local XP)
```python
# Instant, free, offline
skills_manager.add_xp("knowledge_domains", 10)
# Stored in chain_state.json (local file)
```

**Limitations:**
- No economic value (can't trade or sell XP)
- No external verification (can edit JSON file)
- Siloed per qube (can't transfer skills between qubes)
- No incentive alignment (XP has no real-world impact)

### Proposed System (QUBE Tokens)
```python
# During session: Local accumulation (instant)
_pending_xp["knowledge_domains"] += 10

# During anchoring: Batch token transfer (once per session)
await send_qube_tokens(
    to_address=qube.nft_address,
    token_amounts=_pending_xp,  # All skills in ONE transaction
    memo=f"Session {session_id}"
)
```

**Benefits:**
- Real economic value (QUBE/BCH trading pairs on DEX)
- Provable scarcity (on-chain verification)
- Transferability (trade XP between qubes/users)
- Incentive alignment (earn real money by learning)
- Marketplace potential (rare skills command higher prices)

---

## Technical Architecture

### CashTokens Primer

**What are CashTokens?**
- Native BCH primitives (launched May 2023)
- Support fungible tokens (like ERC-20) and NFTs (like ERC-721)
- No smart contract overhead (native to BCH protocol)
- Transaction fees <$0.01 (vs $5-50 on Ethereum)
- **Key feature:** Multiple fungible token groups can be merged/divided in single transaction

**Layla Upgrade (May 2026):**
- Functions, Loops, Bitwise operations, Pay-to-Script improvements
- Enhanced scripting for token-gated skill unlocks
- Better quantum-resistant solutions
- More complex contract logic in fewer bytes

### Existing Infrastructure

Each Qube already has:
```python
genesis.wallet = {
    "p2sh_address": "bitcoincash:p...",  # Multisig wallet (owner + qube)
    "bch_address": "bitcoincash:q...",   # Derived from pubkey
    "nft_address": "bitcoincash:z...",   # Token address (PERFECT for holding QUBE)
    "owner_pubkey": "02...",
    "qube_pubkey": "03..."
}
```

**Key Classes:**
- `QubeWallet` - Full BCH transaction capabilities (crypto/wallet.py)
- `WalletTxManager` - Transaction proposals, approvals, history (blockchain/wallet_tx.py)
- `ChainState` - Local state including skills (core/chain_state.py)
- `SkillsManager` - XP tracking and level-ups (utils/skills_manager.py)

### Proposed Hybrid Architecture

**Three-Layer System:**

1. **Session Layer (Local XP - Instant)**
   - XP accumulated in memory during active session
   - Instant feedback for UI responsiveness
   - Works offline
   - Stored in `_pending_xp` dict

2. **Chain State Layer (Persistent XP - Backup)**
   - Local chain_state.json tracks XP as it does now
   - Serves as backup if token transfer fails
   - Source of truth for skill distribution across categories
   - Synced with token balance on anchoring

3. **Blockchain Layer (Token Proof - Permanent)**
   - QUBE tokens sent to qube's `nft_address` during anchoring
   - One transaction per session (batched)
   - Permanent, verifiable, tradeable proof
   - Balance = total lifetime XP earned

**Flow Diagram:**
```
User Message → AI Response → Tool Use → add_xp()
                                            ↓
                                    _pending_xp += 10
                                            ↓
                                    chain_state.skills updated
                                            ↓
                                    (Session continues...)
                                            ↓
                            User triggers anchor or auto-anchor
                                            ↓
                            Anchor blocks to permanent chain
                                            ↓
                        Send QUBE tokens (batched, all skills)
                                            ↓
                        Token balance = proof of total XP
```

### Token Structure Options

#### **Option A: Single Token Category with Metadata (Recommended)**

**Structure:**
- One QUBE token category (single token ID)
- Total balance = total lifetime XP
- Skill distribution tracked in local `chain_state.json`
- Metadata in OP_RETURN or off-chain DB (optional)

**Example:**
```python
# On-chain
qube.token_balance("QUBE") = 1,000 tokens

# Off-chain (local chain_state)
skills = {
    "knowledge_domains": 400 XP,
    "programming": 350 XP,
    "debugging": 250 XP
}
```

**Pros:**
- Simple implementation
- Easy to trade (one token type = liquidity)
- One balance query
- Lower transaction complexity

**Cons:**
- Can't trade specific skills (only total XP)
- Skill distribution requires local data
- Can't verify skill-specific achievements on-chain

#### **Option B: One Token Category Per Skill (Complex)**

**Structure:**
- 70 token categories (one per skill)
- Each skill has own token balance
- Fully on-chain skill distribution
- Complex transfers (which tokens to send?)

**Example:**
```python
# On-chain (70 separate token categories)
qube.token_balance("QUBE_KNOWLEDGE") = 400 tokens
qube.token_balance("QUBE_PROGRAMMING") = 350 tokens
qube.token_balance("QUBE_DEBUGGING") = 250 tokens
```

**Pros:**
- Fully on-chain skill verification
- Trade specific skills separately
- Skill marketplace (buy/sell individual skills)
- Rarity mechanics (rare skills worth more)

**Cons:**
- 70 token categories to manage
- Complex transaction logic (multiple token types)
- Lower liquidity (fragmented market)
- Higher complexity to implement

**Recommendation:** Start with **Option A**. The token proves total achievement while local data provides granularity. Can migrate to Option B later if needed.

---

## Token Economics

### Supply Options

**Option 1: Inflationary (Recommended for MVP)**
- No max supply cap
- Tokens minted when XP awarded
- Natural inflation as qubes learn
- Simple implementation (mint on demand)

**Option 2: Fixed Supply with Treasury**
- Total supply: 1,000,000,000 QUBE (1 billion)
- Treasury holds initial supply
- Distributed to qubes as XP earned
- Requires treasury management system

**Option 3: Proof-of-Work Mining**
- Tokens must be "mined" by completing tasks
- Difficulty adjustment based on network activity
- More complex, game-like mechanics

### Token Distribution

**Initial Distribution (if fixed supply):**
```
Treasury Reserve: 60% (600M QUBE)
  ↳ Distributed as XP rewards over time

Early Qubes Bonus: 20% (200M QUBE)
  ↳ Retroactive airdrop based on existing XP

Development Fund: 10% (100M QUBE)
  ↳ For project development and partnerships

Liquidity Pool: 10% (100M QUBE)
  ↳ Initial DEX liquidity (QUBE/BCH pair)
```

### Transaction Costs

**Current System:**
- XP award: Free (local operation)
- Frequency: Every tool use (~10-50 times per session)

**Token System:**
- Token transfer: ~$0.001 USD (BCH fee)
- Frequency: Once per session (batched)
- Daily cost for active qube: ~$0.03 USD (30 sessions)
- Annual cost: ~$11 USD (sustainable)

**Fee Payment Options:**
1. User pays (from owner's BCH wallet)
2. Qube pays (from qube's p2sh wallet)
3. Treasury pays (subsidized by project)

### Trading & Marketplace

**Potential Markets:**
1. **QUBE/BCH Trading Pair** - Buy QUBE with BCH on DEX
2. **Qube-to-Qube XP Transfer** - Gift XP between qubes
3. **Skill Rental** - Temporarily boost skills for specific tasks
4. **XP Staking** - Lock QUBE for governance or rewards
5. **Skill Marketplace** - Trade qubes with specific skill sets

---

## Implementation Plan

### Phase 1: Token Infrastructure (Week 1)

**Goal:** Create QUBE token and basic transfer capability

**Tasks:**
1. Create QUBE fungible token on BCH mainnet
   - Choose token category ID (32-byte identifier)
   - Set token metadata (name, symbol, decimals)
   - Mint initial supply (if using fixed supply model)

2. Extend `QubeWallet` class for CashTokens
   - Add `send_fungible_tokens()` method
   - Add `query_token_balance()` method
   - Add token UTXO selection logic

3. Create token distribution contract (if using treasury)
   - P2SH script for controlled distribution
   - Multisig authorization for minting

**Deliverables:**
- QUBE token created on mainnet
- `crypto/cashtokens.py` - Token utilities module
- Basic send/receive capability

### Phase 2: XP → Token Bridge (Week 2)

**Goal:** Connect local XP system to token transfers

**Tasks:**
1. Modify `SkillsManager.add_xp()`
   - Add `_pending_xp` accumulator
   - Continue local storage (backup)
   - Track last anchor timestamp

2. Add anchoring hook in `Session.anchor_to_chain()`
   - Calculate total pending XP per skill
   - Build batched token transfer
   - Send to qube's `nft_address`
   - Clear pending on success

3. Add fallback logic
   - If token transfer fails, keep local XP
   - Retry on next anchor
   - Log discrepancies for debugging

**Code Changes:**
```python
# utils/skills_manager.py
class SkillsManager:
    def __init__(self, chain_state):
        self.chain_state = chain_state
        self._pending_xp = {}  # NEW: Accumulator for batching

    def add_xp(self, skill_id, xp_amount, ...):
        # Add to pending (for token transfer)
        self._pending_xp[skill_id] = self._pending_xp.get(skill_id, 0) + xp_amount

        # Continue local storage (backup)
        # ... existing logic ...

    async def flush_pending_xp_to_tokens(self):
        """Send accumulated XP as tokens during anchoring"""
        if not self._pending_xp:
            return

        # Calculate total tokens to send
        total_tokens = sum(self._pending_xp.values())

        # Send to qube's token address
        await qube_wallet.send_fungible_tokens(
            to_address=self.qube.nft_address,
            token_category=QUBE_TOKEN_ID,
            amount=total_tokens,
            memo=f"XP: {json.dumps(self._pending_xp)}"
        )

        # Clear pending on success
        self._pending_xp.clear()

# core/session.py
class Session:
    async def anchor_to_chain(self):
        # ... existing anchoring logic ...

        # NEW: Send accumulated XP as tokens
        await self.qube.skills_manager.flush_pending_xp_to_tokens()
```

**Deliverables:**
- Modified `SkillsManager` with token integration
- Anchoring hook for batch token transfer
- Error handling and retry logic

### Phase 3: Balance Sync & UI (Week 3)

**Goal:** Display token balances and sync state

**Tasks:**
1. Add token balance queries
   - Query `nft_address` token balance via Fulcrum API
   - Cache balance in chain_state
   - Refresh on anchoring

2. Sync token balance with local XP
   - Compare token balance vs local XP total
   - Detect discrepancies
   - UI indicator for "pending anchor" state

3. Update GUI components
   - Display token balance in skills panel
   - Show pending XP (not yet tokenized)
   - Transaction history with token transfers
   - "Anchor Now" button to trigger manual sync

**UI Mockup:**
```
╔══════════════════════════════════════════╗
║ Knowledge Domains                   ☀️  ║
║ Level 12 • 450/500 XP                    ║
║                                          ║
║ Token Balance: 450 QUBE ✓               ║
║ Pending XP: +25 (not yet anchored)      ║
║                                          ║
║ [Anchor Session] ← Manual trigger       ║
╚══════════════════════════════════════════╝
```

**Deliverables:**
- Token balance query integration
- Updated skills panel UI
- Pending XP indicator
- Manual anchor button

### Phase 4: Advanced Features (Week 4+)

**Goal:** Trading, transfers, and marketplace

**Tasks:**
1. **Qube-to-Qube Transfers**
   - UI for sending QUBE to other qubes
   - Approval flow (owner must sign)
   - Gift XP mechanism

2. **DEX Integration**
   - List QUBE on BCH DEX (Cauldron, TapSwap, etc.)
   - QUBE/BCH trading pair
   - Price feed integration

3. **Token History Explorer**
   - View all token transactions
   - Filter by skill category (from memo field)
   - Export to CSV

4. **Skill-Specific Tokens (Optional)**
   - Implement Option B (one token per skill)
   - Migration path from Option A
   - Skill-specific trading

**Deliverables:**
- Transfer UI
- DEX listing (external)
- Transaction history viewer
- (Optional) Multi-token system

---

## Benefits & Trade-offs

### Benefits

**Economic Value**
- ✅ Real market price for XP (QUBE/BCH pair)
- ✅ Earn money by learning and completing tasks
- ✅ Incentivizes qube development and training
- ✅ Creates marketplace for skilled qubes

**Verification & Trust**
- ✅ On-chain proof of achievements
- ✅ Anyone can verify skill claims
- ✅ Tamper-proof (can't edit blockchain)
- ✅ Transparent skill distribution

**Transferability**
- ✅ Gift XP between qubes
- ✅ Trade qubes with specific skills
- ✅ XP inheritance (transfer to new qube)
- ✅ Skill rental/delegation mechanisms

**Network Effects**
- ✅ Liquid market for QUBE tokens
- ✅ DEX integration for easy trading
- ✅ Attract developers (earn real money)
- ✅ Community-driven token economics

### Trade-offs

**Complexity**
- ❌ More complex than local XP
- ❌ Requires BCH network connection
- ❌ Token management overhead
- ❌ Smart contract interactions (if using advanced features)

**Costs**
- ❌ Transaction fees (~$0.03/day for active qube)
- ❌ Initial token creation cost
- ❌ DEX listing fees (if applicable)

**User Experience**
- ❌ Delayed feedback (tokens arrive after anchoring)
- ❌ Network dependency (can't earn tokens offline)
- ❌ Pending state confusion ("Did I earn XP or not?")

**Economic Risks**
- ❌ Token price volatility
- ❌ Potential for XP inflation/deflation
- ❌ Gaming the system (bot farms earning QUBE)
- ❌ Regulatory concerns (depending on jurisdiction)

### Mitigation Strategies

**UX:**
- Hybrid system (local XP for instant feedback + tokens for proof)
- Clear "pending anchor" indicators
- Offline mode with sync-on-connect

**Costs:**
- Batch transfers during anchoring (1 tx per session)
- Optional subsidies from treasury
- User choice (opt-in token sync)

**Economic:**
- Anti-bot measures (captcha, proof-of-personhood)
- Token burn mechanisms (deflationary pressure)
- Governance for token economics adjustments

---

## Code Examples

### 1. Token Creation

```python
# tools/create_qube_token.py
"""
Create QUBE fungible token on BCH mainnet
"""
import asyncio
from crypto.wallet import QubeWallet
from crypto.cashtokens import create_fungible_token

async def create_qube_token():
    """
    Create QUBE token with initial supply
    """
    # Treasury wallet (holds initial supply)
    treasury_wallet = QubeWallet(
        qube_private_key=treasury_privkey,
        owner_pubkey_hex=treasury_owner_pubkey
    )

    # Create token
    token_id = await create_fungible_token(
        wallet=treasury_wallet,
        name="QUBE Experience",
        symbol="QUBE",
        decimals=0,  # Integer XP amounts
        initial_supply=1_000_000_000,  # 1 billion QUBE
        metadata={
            "description": "Experience points for Qubes AI agents",
            "website": "https://qubes.ai",
            "icon": "ipfs://...",
        }
    )

    print(f"QUBE Token Created: {token_id}")
    print(f"Treasury Balance: {await treasury_wallet.get_token_balance(token_id)}")

    return token_id

if __name__ == "__main__":
    asyncio.run(create_qube_token())
```

### 2. Batch Token Transfer

```python
# crypto/cashtokens.py
"""
CashToken utilities for QUBE tokens
"""
from typing import Dict, Optional
from crypto.wallet import QubeWallet, TxOutput

QUBE_TOKEN_ID = "..."  # 32-byte token category ID

async def send_qube_tokens(
    wallet: QubeWallet,
    to_address: str,
    amount: int,
    memo: Optional[str] = None
) -> str:
    """
    Send QUBE tokens to an address

    Args:
        wallet: Sender's wallet
        to_address: Recipient address (can be same as sender for self-transfers)
        amount: Number of QUBE tokens to send
        memo: Optional transaction memo

    Returns:
        Transaction ID (txid)
    """
    # Build token output
    token_output = TxOutput(
        address=to_address,
        value=546,  # Dust amount for token UTXO
        token_category=QUBE_TOKEN_ID,
        token_amount=amount
    )

    # Add OP_RETURN output with memo if provided
    outputs = [token_output]
    if memo:
        op_return_output = TxOutput(
            address=None,  # OP_RETURN has no address
            value=0,
            op_return_data=memo.encode('utf-8')
        )
        outputs.append(op_return_output)

    # Send transaction
    txid = await wallet.send_transaction(outputs)

    return txid

async def get_token_balance(address: str, token_category: str) -> int:
    """
    Query token balance for an address

    Uses Fulcrum API to get all UTXOs with token_category
    """
    import aiohttp

    async with aiohttp.ClientSession() as session:
        # Get UTXOs for address
        url = f"https://rest.bch.actorforth.org/v2/address/utxo/{address}"
        async with session.get(url) as resp:
            utxos = await resp.json()

        # Sum token amounts
        total = 0
        for utxo in utxos:
            if utxo.get("token_data", {}).get("category") == token_category:
                total += utxo["token_data"].get("amount", 0)

        return total
```

### 3. Skills Manager Integration

```python
# utils/skills_manager.py (modifications)

class SkillsManager:
    def __init__(self, chain_state: "ChainState"):
        self.chain_state = chain_state
        self._skill_definitions_cache = None

        # NEW: Token integration
        self._pending_xp = {}  # Accumulates XP between anchors
        self._last_token_sync = None  # Timestamp of last token transfer

    def add_xp(
        self,
        skill_id: str,
        xp_amount: int,
        evidence_block_id: Optional[str] = None,
        evidence_description: Optional[str] = None,
        tool_details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Add XP to a skill (hybrid local + token system)
        """
        # Accumulate for token transfer
        if skill_id not in self._pending_xp:
            self._pending_xp[skill_id] = 0
        self._pending_xp[skill_id] += xp_amount

        # Continue with existing local storage logic
        # ... (existing add_xp code) ...

        return result

    async def flush_pending_xp_to_tokens(self, qube) -> Dict[str, Any]:
        """
        Send accumulated XP as QUBE tokens during anchoring

        Returns:
            Result dict with success status and txid
        """
        if not self._pending_xp:
            logger.info("No pending XP to flush")
            return {"success": True, "txid": None}

        try:
            from crypto.cashtokens import send_qube_tokens, QUBE_TOKEN_ID
            from crypto.wallet import QubeWallet

            # Calculate total tokens to send
            total_tokens = sum(self._pending_xp.values())

            # Get qube's wallet
            wallet = QubeWallet(
                qube_private_key=qube.get_private_key(),
                owner_pubkey_hex=qube.genesis_block.wallet["owner_pubkey"],
                qube_pubkey_hex=qube.genesis_block.wallet["qube_pubkey"]
            )

            # Send tokens to self (qube's nft_address)
            txid = await send_qube_tokens(
                wallet=wallet,
                to_address=qube.genesis_block.wallet["nft_address"],
                amount=total_tokens,
                memo=f"Session XP: {json.dumps(self._pending_xp)}"
            )

            logger.info(
                "xp_tokens_sent",
                qube_id=qube.qube_id,
                total_tokens=total_tokens,
                skill_breakdown=self._pending_xp,
                txid=txid
            )

            # Clear pending on success
            self._pending_xp.clear()
            self._last_token_sync = datetime.utcnow().isoformat() + "Z"

            # Update chain_state with sync timestamp
            self.chain_state.state.setdefault("skills", {})["last_token_sync"] = self._last_token_sync
            self.chain_state._save()

            return {"success": True, "txid": txid, "amount": total_tokens}

        except Exception as e:
            logger.error(
                "xp_token_transfer_failed",
                qube_id=qube.qube_id,
                error=str(e),
                pending_xp=self._pending_xp
            )
            # Don't clear pending - will retry on next anchor
            return {"success": False, "error": str(e)}

    async def sync_token_balance(self, qube) -> Dict[str, Any]:
        """
        Query on-chain token balance and compare with local XP

        Returns:
            Dict with token_balance, local_total_xp, and synced status
        """
        try:
            from crypto.cashtokens import get_token_balance, QUBE_TOKEN_ID

            # Get on-chain balance
            token_balance = await get_token_balance(
                address=qube.genesis_block.wallet["nft_address"],
                token_category=QUBE_TOKEN_ID
            )

            # Get local total XP
            compact_data = self._get_compact_skills_data()
            local_total = compact_data.get("total_xp", 0)

            # Calculate pending (not yet tokenized)
            pending = sum(self._pending_xp.values())

            synced = (token_balance == local_total - pending)

            return {
                "token_balance": token_balance,
                "local_total_xp": local_total,
                "pending_xp": pending,
                "synced": synced,
                "discrepancy": (local_total - pending) - token_balance
            }

        except Exception as e:
            logger.error("token_balance_sync_failed", error=str(e))
            return {"success": False, "error": str(e)}
```

### 4. Anchoring Hook

```python
# core/session.py (modifications)

class Session:
    async def anchor_to_chain(self, memory_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Anchor session blocks to permanent chain

        MODIFIED: Also sends accumulated XP as tokens
        """
        # ... existing anchoring logic ...

        try:
            # NEW: Flush pending XP to tokens
            logger.info("Flushing pending XP to QUBE tokens...")
            token_result = await self.qube.skills_manager.flush_pending_xp_to_tokens(self.qube)

            if token_result["success"]:
                logger.info(
                    "xp_tokens_anchored",
                    txid=token_result.get("txid"),
                    amount=token_result.get("amount")
                )
            else:
                logger.warning(
                    "xp_token_transfer_failed_during_anchor",
                    error=token_result.get("error")
                )
        except Exception as e:
            logger.error("xp_token_flush_failed", error=str(e))
            # Don't fail anchoring if token transfer fails
            # Pending XP will retry on next anchor

        # ... rest of anchoring logic ...

        return {
            "success": True,
            "blocks_anchored": len(blocks),
            "token_txid": token_result.get("txid") if token_result["success"] else None
        }
```

---

## Open Questions

### 1. Token Supply Model
- **Fixed supply** (1B QUBE with treasury distribution)?
- **Inflationary** (mint on demand as XP earned)?
- **Deflationary** (burn mechanism to reduce supply)?

### 2. Token Distribution
- Should existing qubes get retroactive QUBE airdrop based on current XP?
- How to prevent bot farms from farming QUBE tokens?
- Should there be a "genesis airdrop" for early adopters?

### 3. Skill Granularity
- **One token for all XP** (simpler, more liquid)?
- **Separate tokens per skill** (more complex, skill-specific trading)?
- **Separate tokens per category** (7 tokens: AI Reasoning, Social Intelligence, etc.)?

### 4. Anchoring Frequency
- **Every session** (more up-to-date, higher fees)?
- **Daily batch** (fewer fees, less current)?
- **Manual trigger** (user controls when to "lock in" XP)?
- **Automatic threshold** (anchor when pending XP > 100)?

### 5. Transfer Rules
- Can qubes send QUBE to each other? (XP gifting)
- Can users cash out QUBE for BCH? (Real earnings)
- Should there be a transfer tax (e.g., 5% burn on transfers)?
- Lock-up period for newly earned QUBE? (Prevent instant dump)

### 6. Economic Mechanics
- Should QUBE have governance rights? (Vote on token economics)
- Staking rewards? (Lock QUBE for yield)
- Skill rental? (Temporarily lend XP to other qubes)
- XP decay? (Lose XP over time if not used)

### 7. User Experience
- Show local XP only (simpler, hides token complexity)?
- Show both local XP and token balance (transparent)?
- "Pending anchor" indicator in UI (clarity)?
- Manual vs automatic anchoring (control vs convenience)?

### 8. Security & Privacy
- Who holds the private keys for token transfers?
  - Qube only (risky if qube compromised)
  - Owner only (qube can't autonomously earn)
  - Multisig (owner + qube approval)
- Should token transfers be public or private?
  - Public: Anyone can see qube's skills
  - Private: CashFusion for privacy?

### 9. Marketplace Features
- Allow buying XP with BCH? (Pay-to-level)
- Skill-based qube marketplace? (Buy/sell trained qubes)
- XP lending? (Borrow QUBE for short-term skill boost)
- Skill certificates? (NFT proof of specific achievement)

### 10. Migration Path
- How to migrate existing XP to tokens?
  - One-time airdrop based on current XP
  - Gradual migration (new XP goes to tokens)
  - Dual system (local XP + tokens coexist)
- Backwards compatibility with old qubes?

---

## Resources

### BCH CashTokens
- [CashTokens: Token Primitives for Bitcoin Cash](https://blog.bitjson.com/cashtokens-v2/)
- [CashTokens Specification](https://cashtokens.org/docs/spec/chip/)
- [CashTokens Introduction](https://cashtokens.org/docs/intro/)
- [CashTokens Usage Examples](https://cashtokens.org/docs/spec/examples/)
- [CashTokens Rationale](https://cashtokens.org/docs/spec/rationale/)

### BCH Layla Upgrade (May 2026)
- [CHIP Endorsement May 2026 | The Bitcoin Cash Podcast](https://bitcoincashpodcast.com/blog/chip-endorsement-may-2026)
- [2026 Layla Upgrade Lock-in Thread - Bitcoin Cash Research](https://bitcoincashresearch.org/t/2026-layla-upgrade-lock-in-chip-endorsements-thread/1672)

### Libraries & Tools
- [libauth](https://github.com/bitauth/libauth) - Bitcoin Cash transaction utilities
- [mainnet-js](https://mainnet.cash/) - TypeScript/JavaScript BCH library
- [BitCash](https://bitcash.dev/guide/cashtokens.html) - Python BCH library with CashTokens support
- [Fulcrum API](https://rest.bch.actorforth.org/) - Bitcoin Cash indexer (used in Qubes)

### DEX Platforms (for QUBE/BCH trading)
- [Cauldron DEX](https://www.cauldron.quest/) - BCH-native DEX with CashTokens support
- [TapSwap](https://tapswap.cash/) - Atomic swaps for CashTokens

### Existing Qube Code
- `crypto/wallet.py` - QubeWallet class (multisig BCH wallet)
- `crypto/bch_script.py` - BCH script utilities
- `blockchain/wallet_tx.py` - Transaction management
- `utils/skills_manager.py` - XP and skill tracking
- `core/session.py` - Session anchoring logic

---

## Timeline & Milestones

### MVP (4 weeks)
- **Week 1:** Token creation + basic wallet integration
- **Week 2:** XP accumulation + batch anchoring
- **Week 3:** Balance sync + UI updates
- **Week 4:** Testing + bug fixes

**MVP Deliverables:**
- QUBE token created on mainnet
- Batch token transfer during anchoring
- Token balance display in UI
- Pending XP indicator

### V2 (2-3 months)
- Qube-to-qube transfers
- DEX listing (QUBE/BCH pair)
- Transaction history explorer
- Token governance (voting on economics)

### V3 (6+ months)
- Skill-specific tokens (if desired)
- Marketplace for trained qubes
- XP staking and rewards
- Advanced tokenomics (burn, deflation, etc.)

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-01-23 | Plan created | User interested but not ready to implement |
| TBD | Supply model chosen | Pending team discussion |
| TBD | Token structure (A vs B) | Pending technical evaluation |
| TBD | Anchoring frequency | Pending UX testing |

---

## Next Steps

When ready to implement:

1. **Review this document** and make key decisions (supply model, token structure, etc.)
2. **Create QUBE token** on BCH testnet for experimentation
3. **Implement Phase 1** (token infrastructure)
4. **Test on testnet** with multiple qubes
5. **Audit security** (key management, transaction signing)
6. **Deploy to mainnet** with initial distribution
7. **List on DEX** for QUBE/BCH trading

---

**Last Updated:** 2026-01-23
**Status:** Awaiting decision on implementation timeline
