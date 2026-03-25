# Skill NFT Badges — Design Plan

## Summary

Replace the current XP-only skill progression system with on-chain NFT badges. When a qube earns enough progress toward a skill, an NFT badge is minted and sent to a soulbound covenant address tied to the qube. The NFT is the skill — if the wallet holds it, the skill is unlocked. No fungible token needed; BCH is the economic layer.

## Current System

- 141 skills: 8 suns (always unlocked), 40 planets, 93 moons
- 17 always-available tools (suns + utility + routing + standalone)
- XP earned through tool usage, tracked in encrypted chain state
- XP thresholds unlock skills locally (no on-chain record)
- Resetting a qube wipes all skill progress
- No way for other qubes to verify skills

## New System

### Core Concept

- **Progress** (internal): Tracks mastery toward earning each badge. Same as current XP counters — just a local metric with no external value. Renamed from "XP" to "progress" or "mastery."
- **Skill NFT Badge** (on-chain): A CashToken NFT minted when progress threshold is reached. Held in a soulbound covenant at the qube's address. Provably verifiable by anyone.

### Flow

```
1. Qube uses tools → earns progress locally (same as today)
2. Progress threshold reached for a skill
3. App requests signed attestation from oracle(s)
   → Oracle verifies the qube's progress is legitimate
   → Oracle signs: "qube [address] earned skill [skill_id]"
4. App builds a minting transaction with oracle signature
5. CashScript minting contract:
   → Verifies oracle signature(s) ✓
   → Mints skill NFT with metadata ✓
   → Sends NFT to qube's soulbound covenant address ✓
6. Skill is now on-chain, verifiable, non-transferable
7. Tool registry checks covenant address for NFTs to determine available tools
```

### What Changes

| Aspect | Before | After |
|--------|--------|-------|
| Skill state | Encrypted chain state (local) | On-chain NFT (global) |
| Verification | Trust self-reported data | Query blockchain |
| Reset behavior | Skills wiped | Skills survive (NFTs persist) |
| Transferability | N/A | Soulbound (covenant-enforced) |
| Cross-qube verification | Not possible | Check wallet for NFT by category ID |
| Economic layer | None | BCH (already in every qube wallet) |

---

## Token Architecture

### Separate Category from Identity NFTs

Skill badge NFTs use their own CashToken **category ID**, separate from the qube identity NFT category. Reasons:

- Different minting rules (identity = once at creation; skills = repeatedly as earned)
- Security isolation (bug in one doesn't compromise the other)
- Cleaner queries (one category ID = all skills)
- Different spending rules (identity may be transferable; skills are soulbound)

### Category Setup

1. Create a genesis transaction that establishes the skill badge category
2. The genesis produces a **minting NFT** with minting capability
3. The minting NFT is sent to the **CashScript minting contract**
4. Only this contract can ever mint skill badge NFTs in this category
5. The **category ID** (genesis txid) is hardcoded into the app for verification

### NFT Metadata (Commitment Data)

Each skill badge NFT carries commitment data encoding:

```
┌─────────────────────────────────────────────┐
│ Skill Badge NFT Commitment                  │
├─────────────┬───────────────────────────────┤
│ skill_id    │ e.g. "pattern_recognition"    │
│ tier        │ "planet" or "moon"            │
│ category    │ e.g. "ai_reasoning"           │
│ earned_at   │ block height at mint time     │
│ qube_addr   │ qube's P2SH32 address (hash) │
└─────────────┴───────────────────────────────┘
```

The commitment is compact (CashToken commitments are limited to 40 bytes on BCH). Encoding options:

- **Option A**: Pack fields into a binary format (skill_id as index number, tier as 1 byte, etc.)
- **Option B**: Use a hash of the full metadata, store full metadata off-chain (indexed by hash)
- **Recommendation**: Option A — use numeric skill indices (1 byte = 256 possible skills, more than enough for 141) plus tier (1 byte) + category (1 byte) + block height (4 bytes) + qube address hash (20 bytes) = 27 bytes total. Fits comfortably in 40 bytes.

### Byte Layout (27 bytes)

```
Offset  Size  Field
0       1     version (0x01)
1       1     skill_index (0-255, maps to skill_id)
2       1     tier (0=sun, 1=planet, 2=moon)
3       1     category_index (0-7, maps to category)
4       4     block_height (uint32, when minted)
8       4     earned_timestamp (uint32, unix epoch)
12      15    qube_address_hash (first 15 bytes of qube P2SH32 hash)
```

Total: 27 bytes. Leaves 13 bytes of headroom for future fields.

---

## Soulbound Enforcement (Covenant)

### Approach: Covenant-Locked NFTs

Each qube has a **skill vault address** — a separate P2SH32 address controlled by a soulbound covenant. This address is deterministically derived from the qube's identity (public key or identity NFT category).

The covenant locking script enforces:

1. **No transfer**: The NFT can only be spent back to the SAME covenant address
2. **Burn allowed**: The NFT can be provably destroyed (output value = 0, no token output)
3. **No other spending paths**: Any transaction that tries to send the NFT elsewhere is invalid

```
// Pseudocode for soulbound covenant
contract SkillVault(bytes20 qubeAddressHash) {
    // Only allow spending back to self (reorganize UTXOs) or burn
    function reorganize() {
        // All NFT outputs must go back to this same contract
        require(tx.outputs[this.activeInputIndex].lockingBytecode == this.activeBytecode);
        require(tx.outputs[this.activeInputIndex].tokenCategory == tx.inputs[this.activeInputIndex].tokenCategory);
    }

    function burn() {
        // Allow burning the NFT (no token in output)
        require(tx.outputs[this.activeInputIndex].tokenCategory == 0x);
    }
}
```

### Skill Vault Address Derivation

```
qubePublicKey → hash → SkillVault(hash) → P2SH32 address
```

Every qube gets a deterministic skill vault address. The app computes it from the qube's key material. No extra keys to manage.

### Querying Skills

To check what skills a qube has:

```
1. Derive the qube's skill vault address from its public key
2. Query the UTXO set at that address
3. Filter UTXOs by the official skill badge category ID
4. Decode commitment data from each NFT
5. Map skill indices back to skill definitions
```

This is a standard UTXO query — fast, no special infrastructure needed.

---

## Minting Contract (CashScript)

### Design

The minting contract holds the minting NFT and processes mint requests. It uses the **oracle pattern** for verification.

```
contract SkillMinter(
    pubkey oracle1,
    pubkey oracle2,
    pubkey oracle3
) {
    // Mint a skill badge NFT
    // Requires 2-of-3 oracle signatures attesting the qube earned the skill
    function mintSkill(
        sig oracleSig1,
        sig oracleSig2,
        bytes skillCommitment
    ) {
        // Verify at least 2 oracle signatures
        require(checkMultiSig([oracleSig1, oracleSig2], [oracle1, oracle2, oracle3]));

        // Verify the minting NFT stays in the contract (not stolen)
        require(tx.outputs[0].lockingBytecode == this.activeBytecode);
        require(tx.outputs[0].tokenCategory == tx.inputs[this.activeInputIndex].tokenCategory);
        require(tx.outputs[0].nftCommitment == tx.inputs[this.activeInputIndex].nftCommitment);

        // Verify a new NFT is minted with the skill commitment
        require(tx.outputs[1].tokenCategory == tx.inputs[this.activeInputIndex].tokenCategory);
        require(tx.outputs[1].nftCommitment == skillCommitment);

        // Output 1 goes to the qube's skill vault (enforced by oracle attestation)
    }
}
```

### Oracle Verification

Oracles are lightweight services that:

1. Receive a mint request: `{qube_address, skill_id, progress_proof}`
2. Verify the qube's progress is legitimate:
   - Check the qube exists on-chain (identity NFT)
   - Verify progress data signature (signed by the qube's key)
   - Check the skill hasn't already been minted (query skill vault)
   - Validate progress threshold is met
3. Return a signed attestation if valid

**Initial deployment**: Single oracle (your server). The contract uses 1-of-1 signature.

**Future decentralization**: Add community-run oracles. Upgrade contract to 2-of-3 or 3-of-5. Multiple independent parties must agree before minting.

### Contract Funding

The minting contract holds a small BCH balance to fund dust outputs for minted NFTs. Anyone can top up the contract by sending BCH to it. A single $1 deposit covers thousands of mints.

---

## Anti-Gaming Measures

### Why Gaming Is Difficult

| Attack | Natural Defense |
|--------|-----------------|
| Bot spam tool calls | Cloud API calls cost money; diminishing returns per tool per session |
| Sybil (many qubes) | Each qube costs BCH to mint |
| Self-dealing (qube talks to itself) | Earning only from tool usage, not messages |
| Repeated identical calls | Dedup: same tool + same params in a session = progress only on first call |
| Local model farming | Daily progress cap per qube; oracle rate-limits mint requests |

### Progress Earning Rules

- **Daily cap**: Maximum 50 progress points per qube per day
- **Diminishing returns**: First 50 tool calls = full progress; 51-100 = half; 101+ = zero
- **Deduplication**: Identical tool calls (same name + same params) earn progress only once per session
- **Tool-type cooldown**: Each tool type earns progress at most N times per session
- **Oracle rate limit**: Maximum 1 skill mint request per qube per hour

### Progress Thresholds

| Tier | Progress Required | Approx. Days at 50/day |
|------|-------------------|------------------------|
| Planet | 500 | ~10 days |
| Moon | 250 | ~5 days |

These are tunable. The exact values should be set based on playtesting.

---

## Migration Plan

### Phase 1: Foundation

- [ ] Create skill badge CashToken category (genesis transaction)
- [ ] Send minting NFT to a secure wallet (pre-contract)
- [ ] Define skill index mapping (112 skills → 0-111 indices)
- [ ] Build commitment encoding/decoding utilities
- [ ] Build skill vault address derivation from qube public key

### Phase 2: Minting Contract

- [ ] Write CashScript soulbound covenant (SkillVault)
- [ ] Write CashScript minting contract (SkillMinter)
- [ ] Deploy contracts to mainnet
- [ ] Transfer minting NFT to the minting contract
- [ ] Fund the minting contract with BCH for dust outputs

### Phase 3: Oracle Service

- [ ] Build oracle verification endpoint
- [ ] Implement progress verification logic
- [ ] Implement rate limiting and anti-gaming checks
- [ ] Deploy as a service (can run on existing server initially)
- [ ] Generate oracle keypair, configure in minting contract

### Phase 4: App Integration

- [ ] Rename "XP" to "Progress" / "Mastery" throughout app
- [ ] Add skill vault address derivation to wallet code
- [ ] Add NFT minting request flow when progress threshold is reached
- [ ] Replace skill unlock checks: chain state → query skill vault UTXOs
- [ ] Update Skills tab UI to show on-chain badge status
- [ ] Update tool registry to check for badge NFTs when filtering tools
- [ ] Cache skill vault query results locally (refresh on new blocks)

### Phase 5: Verification & Display

- [ ] Add cross-qube skill verification (group chats, P2P)
- [ ] Show verified badge indicators in UI
- [ ] Add skill badge gallery/collection view
- [ ] Display earned_at timestamp and block height for each badge

### Phase 6: Decentralization

- [ ] Deploy additional oracle nodes
- [ ] Upgrade minting contract to multi-sig (2-of-3)
- [ ] Open-source oracle software for community operators
- [ ] Document oracle API for third-party implementations

---

## Open Questions

1. **Existing qubes**: Qubes that already have XP/unlocked skills — should they receive retroactive NFT badges for skills they already earned? Or start fresh?
2. **Sun skills**: Suns are always unlocked (no badge needed). Should suns still get a badge anyway for completeness/collection purposes?
3. **Skill dependencies**: Currently planets require parent sun, moons require parent planet. Should the oracle enforce these prerequisites, or just check progress threshold?
4. **Badge revocation**: Should badges ever be revocable? (e.g., if gaming is detected after the fact). Burn capability in the covenant allows this, but who has authority to burn?
5. **Off-chain fallback**: If the BCH network is slow or the oracle is down, should skills still unlock locally (with NFT minted later)? Or require on-chain confirmation before unlocking?
6. **Display in wallet apps**: Standard BCH wallet apps will show these NFTs. Should the commitment data be human-readable, or is app-only decoding acceptable?
