# Context Visibility & Semantic Search Implementation Plan

## Overview

This plan addresses two related issues:

1. **Semantic Search Not Connected** - The 5-layer intelligent memory search system exists in code but the FAISS/embeddings layer (Layer 1) is never initialized, causing all searches to fall back to basic keyword matching.

2. **GUI Doesn't Show Full Context** - The "Short-Term Memory" panel only shows session blocks, not everything actually injected into the Qube's AI context (genesis, recalled memories, relationships, skills, wallet, etc.).

---

## Part 1: Semantic Search Initialization

### Problem

The `SemanticSearch` class in `ai/semantic_search.py` provides FAISS-based vector search with sentence-transformers embeddings, but:

- `qube.semantic_search` is never set
- `intelligent_memory_search()` always hits the fallback (line 251): `return [(block, 0.5) for block in candidates[:top_k]]`
- All blocks get a default relevance score of 0.5
- No actual semantic understanding - just keyword matching

### Solution

#### 1.1 Initialize SemanticSearch in Qube

**File:** `core/qube.py`

Add to `__init__` after memory chain initialization:

```python
# Initialize semantic search (background load for performance)
self.semantic_search = None
self._init_semantic_search_background()

def _init_semantic_search_background(self):
    """Initialize semantic search in background thread"""
    import threading

    def init_search():
        try:
            from ai.semantic_search import SemanticSearch
            self.semantic_search = SemanticSearch(
                qube_id=self.qube_id,
                storage_dir=self.data_dir / "chain"
            )

            # Validate index integrity
            indexed_count = len(self.semantic_search.block_ids)
            actual_count = self.memory_chain.get_chain_length()

            if indexed_count != actual_count:
                logger.info(
                    "semantic_index_mismatch_rebuilding",
                    indexed=indexed_count,
                    actual=actual_count
                )
                blocks = self.memory_chain.get_all_blocks()
                self.semantic_search.rebuild_index(blocks)

            logger.info("semantic_search_ready", qube_id=self.qube_id)

        except Exception as e:
            logger.error("semantic_search_init_failed", error=str(e))
            self.semantic_search = None

    thread = threading.Thread(target=init_search, daemon=True)
    thread.start()
```

**Design Decisions:**
- **Background loading:** Model load takes 2-3 seconds; don't block Qube init
- **Index validation:** Compare indexed count vs actual count; rebuild on mismatch
- **Graceful degradation:** If init fails, `semantic_search` stays None and fallback kicks in

#### 1.2 Index New Blocks

**File:** `core/qube.py` - in `add_block()` method or wherever blocks are anchored

```python
def add_block(self, block, ...):
    # ... existing block addition logic ...

    # Index for semantic search (if available)
    if self.semantic_search:
        try:
            self.semantic_search.add_block(block)
        except Exception as e:
            logger.warning("semantic_index_add_failed", block=block.block_number, error=str(e))
```

#### 1.3 Summary Block Exclusion Logic

**File:** `ai/reasoner.py` - in `_get_recent_permanent_blocks()`

When building the context window, exclude blocks that are covered by a SUMMARY unless they were specifically recalled via semantic search.

```python
def _get_recent_permanent_blocks(self, limit: int, recalled_block_numbers: Set[int] = None) -> List[Block]:
    """
    Get recent permanent blocks for context window.

    Excludes blocks covered by SUMMARY blocks unless they were
    specifically recalled via semantic search.

    Args:
        limit: Max blocks to return
        recalled_block_numbers: Set of block numbers that were semantically recalled
                               (these bypass summary exclusion)
    """
    if recalled_block_numbers is None:
        recalled_block_numbers = set()

    blocks = []
    excluded_ranges = []  # List of (start, end) tuples from SUMMARY blocks

    # First pass: identify SUMMARY blocks and their coverage
    for block in self._iterate_permanent_blocks_reverse():
        if block.block_type == "SUMMARY":
            content = self._decrypt_block_content_if_needed(block)
            # SUMMARY blocks should store which blocks they cover
            covered_start = content.get("covers_from_block")
            covered_end = content.get("covers_to_block")
            if covered_start and covered_end:
                excluded_ranges.append((covered_start, covered_end))

    # Second pass: collect blocks, respecting exclusions
    for block in self._iterate_permanent_blocks_reverse():
        if len(blocks) >= limit:
            break

        block_num = block.block_number

        # Always include if semantically recalled
        if block_num in recalled_block_numbers:
            blocks.append(block)
            continue

        # Check if covered by a summary
        is_covered = any(start <= block_num <= end for start, end in excluded_ranges)

        if not is_covered:
            blocks.append(block)
        # If covered by summary, skip (summary itself will be included)

    return blocks
```

**Note:** This requires SUMMARY blocks to track which blocks they cover. Update summary creation to include:
```python
{
    "summary_text": "...",
    "covers_from_block": 10,
    "covers_to_block": 15,
    "block_count": 6
}
```

---

## Part 2: Context Preview Backend Endpoint

### New Endpoint

**File:** `gui_bridge.py`

```python
async def get_context_preview(self, qube_id: str, password: str = None) -> Dict[str, Any]:
    """
    Get a preview of what's currently in the Qube's AI context.

    Returns both Active Context (always-present identity/state) and
    Short-Term Memory (blocks in the context window).

    Called by GUI when Block Browser panel opens or refreshes.
    """
    try:
        # Set master key if password provided
        if password:
            self.orchestrator.set_master_key(password)

        # Load qube if needed
        if qube_id not in self.orchestrator.qubes:
            await self.orchestrator.load_qube(qube_id)

        qube = self.orchestrator.qubes[qube_id]

        # Build active context
        active_context = await self._build_active_context_preview(qube)

        # Build short-term memory preview
        short_term_memory = await self._build_short_term_memory_preview(qube)

        return {
            "success": True,
            "active_context": active_context,
            "short_term_memory": short_term_memory
        }

    except Exception as e:
        logger.error("get_context_preview_failed", qube_id=qube_id, error=str(e))
        return {"success": False, "error": str(e)}
```

### Active Context Builder

```python
async def _build_active_context_preview(self, qube) -> Dict[str, Any]:
    """Build preview of always-present context (identity, relationships, skills, wallet)"""

    genesis = qube.genesis_block

    # Genesis identity
    genesis_data = {
        "name": genesis.qube_name,
        "birth_date": format_timestamp(genesis.birth_timestamp),
        "birth_timestamp": genesis.birth_timestamp,
        "favorite_color": getattr(genesis, 'favorite_color', '#4A90E2'),
        "ai_model": genesis.ai_model,
        "voice_model": getattr(genesis, 'voice_model', None),
        "nft_status": "minted" if getattr(genesis, 'mint_txid', None) else "unminted",
        "nft_category_id": getattr(genesis, 'nft_category_id', None),
        "creator": genesis.creator,
        "genesis_prompt": genesis.genesis_prompt  # For expanded view
    }

    # Avatar description (if cached)
    avatar_description = qube.chain_state.get_avatar_description() if hasattr(qube, 'chain_state') else None

    # Current relationship (if in active session with someone)
    current_relationship = None
    if qube.current_session and hasattr(qube.current_session, 'partner_id'):
        partner_id = qube.current_session.partner_id
        rel = qube.relationships.get_relationship(partner_id)
        if rel:
            current_relationship = {
                "entity_id": rel.entity_id,
                "entity_name": rel.entity_name,
                "status": rel.relationship_status,
                "trust_score": rel.overall_trust_score,
                "messages_sent": rel.messages_sent,
                "messages_received": rel.messages_received
            }

    # Top 3 relationships (for when no active conversation)
    top_relationships = []
    try:
        all_rels = qube.relationships.storage.get_all_relationships()
        sorted_rels = sorted(all_rels, key=lambda r: r.overall_trust_score, reverse=True)[:3]
        top_relationships = [
            {
                "entity_id": r.entity_id,
                "entity_name": r.entity_name,
                "status": r.relationship_status,
                "trust_score": r.overall_trust_score
            }
            for r in sorted_rels
        ]
    except Exception as e:
        logger.warning("failed_to_get_relationships", error=str(e))

    # Skills summary
    skills_data = {"total_xp": 0, "top_skills": []}
    try:
        if hasattr(qube, 'chain_state') and qube.chain_state:
            skills = qube.chain_state.get_skills_summary()
            if skills:
                skills_data = {
                    "total_xp": skills.get("total_xp", 0),
                    "top_skills": skills.get("top_skills", [])[:3]  # Top 3
                }
    except Exception as e:
        logger.warning("failed_to_get_skills", error=str(e))

    # Wallet summary
    wallet_data = None
    try:
        if hasattr(qube, 'wallet') and qube.wallet:
            balance = await qube.wallet.get_balance()
            wallet_data = {
                "balance_sats": balance,
                "balance_bch": f"{balance / 100_000_000:.8f}",
                "address": qube.wallet.p2sh_address,
                "pending_count": len(qube.wallet.pending_transactions) if hasattr(qube.wallet, 'pending_transactions') else 0
            }
    except Exception as e:
        logger.warning("failed_to_get_wallet", error=str(e))

    # Estimate system prompt tokens (cached from last message or estimated)
    system_prompt_tokens = getattr(qube, '_last_system_prompt_tokens', None)
    if system_prompt_tokens is None:
        # Rough estimate: ~4 chars per token
        estimated_chars = len(genesis.genesis_prompt) + 2000  # Base prompt + identity block
        system_prompt_tokens = estimated_chars // 4

    return {
        "genesis": genesis_data,
        "avatar_description": avatar_description,
        "relationship": current_relationship,
        "top_relationships": top_relationships,
        "skills": skills_data,
        "wallet": wallet_data,
        "system_prompt_tokens": system_prompt_tokens
    }
```

### Short-Term Memory Builder

```python
async def _build_short_term_memory_preview(self, qube) -> Dict[str, Any]:
    """Build preview of blocks in the context window"""

    from ai.tools.memory_search import intelligent_memory_search

    # Get recalled memories via semantic search
    recalled_memories = []
    try:
        # Build search context from recent activity
        recent_blocks = list(qube.memory_chain.get_recent_blocks(5))
        if recent_blocks:
            search_context = " ".join([
                self._extract_block_preview(b) for b in recent_blocks
            ])

            results = await intelligent_memory_search(
                qube=qube,
                query=search_context,
                context={"query_type": "recent_events"},
                top_k=5
            )

            recalled_memories = [
                {
                    "block_number": r.block.get("block_number"),
                    "block_type": r.block.get("block_type"),
                    "relevance_score": round(r.score, 1),
                    "preview": self._extract_block_preview(r.block)[:100] + "...",
                    "timestamp": r.block.get("timestamp", 0) * 1000
                }
                for r in results
            ]
    except Exception as e:
        logger.warning("failed_to_get_recalled_memories", error=str(e))

    # Get recent history (excluding blocks covered by summaries)
    recalled_block_numbers = {m["block_number"] for m in recalled_memories}
    recent_history = []
    try:
        # This would use the new _get_recent_permanent_blocks with exclusion logic
        recent_blocks = qube.reasoner._get_recent_permanent_blocks(
            limit=15,
            recalled_block_numbers=recalled_block_numbers
        ) if hasattr(qube, 'reasoner') and qube.reasoner else []

        recent_history = [
            {
                "block_number": b.block_number,
                "block_type": b.block_type if isinstance(b.block_type, str) else b.block_type.value,
                "preview": self._extract_block_preview(b.to_dict())[:100] + "...",
                "timestamp": b.timestamp * 1000
            }
            for b in recent_blocks
        ]
    except Exception as e:
        logger.warning("failed_to_get_recent_history", error=str(e))

    # Get session blocks
    session_blocks = []
    if qube.current_session:
        for b in qube.current_session.session_blocks:
            session_blocks.append({
                "block_number": b.block_number,
                "block_type": b.block_type if isinstance(b.block_type, str) else b.block_type.value,
                "preview": self._extract_block_preview(b.to_dict() if hasattr(b, 'to_dict') else b.content)[:100] + "...",
                "timestamp": b.timestamp * 1000 if hasattr(b, 'timestamp') else 0
            })

    # Calculate context utilization
    total_blocks = len(recalled_memories) + len(recent_history) + len(session_blocks)
    max_blocks = 15  # SHORT_TERM_MEMORY_LIMIT from reasoner

    # Estimate tokens (cached or calculated)
    estimated_tokens = getattr(qube, '_last_context_tokens', None)
    if estimated_tokens is None:
        # Rough estimate
        block_chars = sum(len(m.get("preview", "")) for m in recalled_memories)
        block_chars += sum(len(h.get("preview", "")) for h in recent_history)
        block_chars += sum(len(s.get("preview", "")) for s in session_blocks)
        estimated_tokens = block_chars // 4

    return {
        "recalled_memories": recalled_memories,  # Empty array if none (show "No relevant memories found")
        "recent_history": recent_history,
        "session_blocks": session_blocks,
        "context_utilization": {
            "used": total_blocks,
            "max": max_blocks,
            "percentage": round((total_blocks / max_blocks) * 100) if max_blocks > 0 else 0
        },
        "estimated_tokens": estimated_tokens,
        "last_updated": datetime.now().isoformat()
    }

def _extract_block_preview(self, block: Dict) -> str:
    """Extract preview text from block for display"""
    content = block.get("content", {})

    if block.get("block_type") == "MESSAGE":
        return content.get("message_body", content.get("content", ""))
    elif block.get("block_type") == "SUMMARY":
        return content.get("summary_text", "")
    elif block.get("block_type") == "THOUGHT":
        return content.get("thought", "")
    else:
        return str(content)[:200]
```

### Tauri Command

**File:** `qubes-gui/src-tauri/src/lib.rs`

Add new command to expose endpoint:

```rust
#[tauri::command]
async fn get_context_preview(
    qube_id: String,
    password: String,
    state: tauri::State<'_, AppState>,
) -> Result<serde_json::Value, String> {
    // Call Python backend get_context_preview
    // Similar pattern to existing commands
}
```

---

## Part 3: GUI Implementation

### File Structure

Create new component or extend BlocksTab:

```
qubes-gui/src/components/
├── blocks/
│   ├── ActiveContextPanel.tsx      (NEW)
│   ├── ShortTermMemoryPanel.tsx    (NEW)
│   └── BlockContentViewer.tsx      (existing)
└── tabs/
    └── BlocksTab.tsx               (MODIFY - integrate new panels)
```

### ActiveContextPanel.tsx

```tsx
interface ActiveContextProps {
    context: {
        genesis: GenesisData;
        avatar_description: string | null;
        relationship: RelationshipData | null;
        top_relationships: RelationshipData[];
        skills: SkillsData;
        wallet: WalletData | null;
        system_prompt_tokens: number;
    };
}

const ActiveContextPanel: React.FC<ActiveContextProps> = ({ context }) => {
    const [genesisExpanded, setGenesisExpanded] = useState(false);
    const [walletExpanded, setWalletExpanded] = useState(false);

    return (
        <GlassCard className="p-4">
            <h3 className="text-lg font-semibold text-accent-primary mb-4">
                Active Context
            </h3>

            {/* Genesis Identity - Collapsible */}
            <div className="mb-3">
                <button
                    onClick={() => setGenesisExpanded(!genesisExpanded)}
                    className="flex items-center gap-2 w-full text-left"
                >
                    <span>🧬</span>
                    <span className="font-medium">Identity</span>
                    <span className="text-text-tertiary text-sm ml-auto">
                        {genesisExpanded ? '▼' : '▶'}
                    </span>
                </button>
                <div className="text-sm text-text-secondary mt-1 ml-6">
                    {context.genesis.name} | Born {context.genesis.birth_date} |
                    NFT: {context.genesis.nft_status === 'minted' ? '✓ Minted' : 'Pending'}
                </div>
                {genesisExpanded && (
                    <div className="mt-2 ml-6 p-2 bg-bg-tertiary/50 rounded text-xs">
                        <div>Model: {context.genesis.ai_model}</div>
                        <div>Color: {context.genesis.favorite_color}</div>
                        <div className="mt-2 text-text-tertiary">
                            {context.genesis.genesis_prompt}
                        </div>
                    </div>
                )}
            </div>

            {/* Relationships */}
            <div className="mb-3">
                <div className="flex items-center gap-2">
                    <span>🤝</span>
                    <span className="font-medium">Relationships</span>
                </div>
                <div className="text-sm text-text-secondary mt-1 ml-6">
                    {context.relationship ? (
                        <span>
                            {context.relationship.entity_name}: {context.relationship.status}
                            (Trust: {context.relationship.trust_score})
                        </span>
                    ) : context.top_relationships.length > 0 ? (
                        context.top_relationships.map((r, i) => (
                            <div key={i}>
                                {r.entity_name}: {r.status} ({r.trust_score})
                            </div>
                        ))
                    ) : (
                        <span className="text-text-tertiary">No relationships yet</span>
                    )}
                </div>
            </div>

            {/* Skills */}
            <div className="mb-3">
                <div className="flex items-center gap-2">
                    <span>⭐</span>
                    <span className="font-medium">Skills: {context.skills.total_xp.toLocaleString()} XP</span>
                </div>
                <div className="text-sm text-text-secondary mt-1 ml-6">
                    {context.skills.top_skills.map((s, i) => (
                        <span key={i}>
                            {s.name} ({s.xp}){i < context.skills.top_skills.length - 1 ? ' | ' : ''}
                        </span>
                    ))}
                </div>
            </div>

            {/* Wallet - Collapsible */}
            {context.wallet && (
                <div className="mb-3">
                    <button
                        onClick={() => setWalletExpanded(!walletExpanded)}
                        className="flex items-center gap-2 w-full text-left"
                    >
                        <span>💰</span>
                        <span className="font-medium">Wallet: {context.wallet.balance_bch} BCH</span>
                        <span className="text-text-tertiary text-sm ml-auto">
                            {walletExpanded ? '▼' : '▶'}
                        </span>
                    </button>
                    {walletExpanded && (
                        <div className="mt-2 ml-6 p-2 bg-bg-tertiary/50 rounded text-xs">
                            <div>Address: {context.wallet.address}</div>
                            <div>Pending: {context.wallet.pending_count} transactions</div>
                        </div>
                    )}
                </div>
            )}

            {/* Token count */}
            <div className="mt-4 pt-3 border-t border-glass-border text-xs text-text-tertiary">
                System prompt: ~{context.system_prompt_tokens.toLocaleString()} tokens
            </div>
        </GlassCard>
    );
};
```

### ShortTermMemoryPanel.tsx

```tsx
interface ShortTermMemoryProps {
    memory: {
        recalled_memories: RecalledMemory[];
        recent_history: BlockPreview[];
        session_blocks: BlockPreview[];
        context_utilization: { used: number; max: number; percentage: number };
        estimated_tokens: number;
    };
}

const ShortTermMemoryPanel: React.FC<ShortTermMemoryProps> = ({ memory }) => {
    const [recalledExpanded, setRecalledExpanded] = useState(true);
    const [historyExpanded, setHistoryExpanded] = useState(true);
    const [sessionExpanded, setSessionExpanded] = useState(true);

    return (
        <GlassCard className="p-4">
            <h3 className="text-lg font-semibold text-accent-primary mb-4">
                Short-Term Memory
            </h3>

            {/* Context Utilization Bar */}
            <div className="mb-4">
                <div className="flex justify-between text-xs text-text-tertiary mb-1">
                    <span>{memory.context_utilization.used}/{memory.context_utilization.max} blocks</span>
                    <span>~{memory.estimated_tokens.toLocaleString()} tokens</span>
                </div>
                <div className="h-2 bg-bg-tertiary rounded-full overflow-hidden">
                    <div
                        className="h-full bg-accent-primary transition-all"
                        style={{ width: `${memory.context_utilization.percentage}%` }}
                    />
                </div>
            </div>

            {/* Recalled Memories */}
            <div className="mb-3">
                <button
                    onClick={() => setRecalledExpanded(!recalledExpanded)}
                    className="flex items-center gap-2 w-full text-left"
                >
                    <span>🔍</span>
                    <span className="font-medium">
                        Recalled Memories ({memory.recalled_memories.length})
                    </span>
                    <span className="text-text-tertiary text-sm ml-auto">
                        {recalledExpanded ? '▼' : '▶'}
                    </span>
                </button>
                {recalledExpanded && (
                    <div className="mt-2 ml-6 space-y-2">
                        {memory.recalled_memories.length > 0 ? (
                            memory.recalled_memories.map((m, i) => (
                                <div key={i} className="text-sm p-2 bg-bg-tertiary/30 rounded">
                                    <div className="flex justify-between">
                                        <span className="text-accent-secondary">
                                            #{m.block_number} {m.block_type}
                                        </span>
                                        <span className="text-green-400 text-xs">
                                            {m.relevance_score}
                                        </span>
                                    </div>
                                    <div className="text-text-tertiary text-xs mt-1">
                                        {m.preview}
                                    </div>
                                </div>
                            ))
                        ) : (
                            <div className="text-text-tertiary text-sm">
                                No relevant memories found
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* Recent History */}
            <div className="mb-3">
                <button
                    onClick={() => setHistoryExpanded(!historyExpanded)}
                    className="flex items-center gap-2 w-full text-left"
                >
                    <span>📜</span>
                    <span className="font-medium">
                        Recent History ({memory.recent_history.length})
                    </span>
                    <span className="text-text-tertiary text-sm ml-auto">
                        {historyExpanded ? '▼' : '▶'}
                    </span>
                </button>
                {historyExpanded && (
                    <div className="mt-2 ml-6 space-y-1">
                        {memory.recent_history.map((h, i) => (
                            <div key={i} className="text-sm text-text-secondary">
                                #{h.block_number} <span className="text-accent-secondary">{h.block_type}</span>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Current Session */}
            <div className="mb-3">
                <button
                    onClick={() => setSessionExpanded(!sessionExpanded)}
                    className="flex items-center gap-2 w-full text-left"
                >
                    <span>💬</span>
                    <span className="font-medium">
                        Current Session ({memory.session_blocks.length})
                    </span>
                    <span className="text-text-tertiary text-sm ml-auto">
                        {sessionExpanded ? '▼' : '▶'}
                    </span>
                </button>
                {sessionExpanded && (
                    <div className="mt-2 ml-6">
                        {memory.session_blocks.length > 0 ? (
                            memory.session_blocks.map((s, i) => (
                                <div key={i} className="text-sm text-text-secondary">
                                    {s.block_type}: {s.preview}
                                </div>
                            ))
                        ) : (
                            <div className="text-text-tertiary text-sm">
                                Start a conversation to add messages
                            </div>
                        )}
                    </div>
                )}
            </div>
        </GlassCard>
    );
};
```

### BlocksTab Integration

**File:** `qubes-gui/src/components/tabs/BlocksTab.tsx`

```tsx
// Add state for context preview
const [contextPreview, setContextPreview] = useState<ContextPreview | null>(null);
const [loadingContext, setLoadingContext] = useState(false);

// Fetch on panel open/mount
useEffect(() => {
    if (selectedQube) {
        fetchContextPreview();
    }
}, [selectedQube]);

const fetchContextPreview = async () => {
    if (!selectedQube) return;

    setLoadingContext(true);
    try {
        const result = await invoke('get_context_preview', {
            qubeId: selectedQube.qube_id,
            password: password
        });

        if (result.success) {
            setContextPreview(result);
        }
    } catch (error) {
        console.error('Failed to fetch context preview:', error);
    } finally {
        setLoadingContext(false);
    }
};

// In render, add panels above existing block browser:
return (
    <div className="space-y-4">
        {/* Active Context Panel */}
        {contextPreview && (
            <ActiveContextPanel context={contextPreview.active_context} />
        )}

        {/* Short-Term Memory Panel */}
        {contextPreview && (
            <ShortTermMemoryPanel memory={contextPreview.short_term_memory} />
        )}

        {/* Existing Long-Term Memory / Block Browser */}
        <GlassCard>
            <h3>Long-Term Memory ({totalBlocks})</h3>
            {/* ... existing block browser ... */}
        </GlassCard>
    </div>
);
```

---

## Part 4: Additional Changes

### 4.1 SUMMARY Block Schema Update

Ensure SUMMARY blocks track which blocks they cover:

**File:** `core/session.py` or wherever summaries are created

```python
summary_content = {
    "summary_text": summary_text,
    "covers_from_block": first_block_number,
    "covers_to_block": last_block_number,
    "block_count": number_of_blocks_summarized,
    "created_at": timestamp
}
```

### 4.2 Token Caching

Cache token counts from actual API responses for accurate display:

**File:** `ai/reasoner.py`

```python
# After building context:
self.qube._last_system_prompt_tokens = count_tokens(system_prompt)
self.qube._last_context_tokens = total_tokens_used
```

### 4.3 Skills Summary Method

If not existing, add to chain_state:

**File:** `core/chain_state.py`

```python
def get_skills_summary(self) -> Dict[str, Any]:
    """Get summary of skills for context preview"""
    skills = self.get_all_skills()  # or however skills are stored

    total_xp = sum(s.get('xp', 0) for s in skills.values())

    sorted_skills = sorted(
        skills.items(),
        key=lambda x: x[1].get('xp', 0),
        reverse=True
    )

    top_skills = [
        {"id": k, "name": v.get('name', k), "xp": v.get('xp', 0)}
        for k, v in sorted_skills[:3]
    ]

    return {"total_xp": total_xp, "top_skills": top_skills}
```

---

## Implementation Order

| Phase | Task | Files | Effort |
|-------|------|-------|--------|
| 1.1 | Initialize SemanticSearch in Qube (background) | `core/qube.py` | Medium |
| 1.2 | Index new blocks on creation | `core/qube.py` | Small |
| 1.3 | Add summary exclusion logic | `ai/reasoner.py` | Medium |
| 1.4 | Update SUMMARY block schema | `core/session.py` | Small |
| 2.1 | Create `get_context_preview` endpoint | `gui_bridge.py` | Medium |
| 2.2 | Add helper methods for context building | `gui_bridge.py` | Medium |
| 2.3 | Add Tauri command | `lib.rs` | Small |
| 3.1 | Create ActiveContextPanel component | `ActiveContextPanel.tsx` | Medium |
| 3.2 | Create ShortTermMemoryPanel component | `ShortTermMemoryPanel.tsx` | Medium |
| 3.3 | Integrate panels into BlocksTab | `BlocksTab.tsx` | Small |
| 4.1 | Add token caching | `ai/reasoner.py` | Small |
| 4.2 | Add skills summary method (if needed) | `core/chain_state.py` | Small |
| 5 | Testing & refinement | All | Medium |

---

## Testing Checklist

- [ ] Semantic search initializes in background without blocking Qube load
- [ ] FAISS index persists and loads correctly
- [ ] Index rebuilds when block count mismatches
- [ ] New blocks are indexed when created
- [ ] Blocks covered by SUMMARY are excluded from recent history
- [ ] Semantically recalled blocks bypass summary exclusion
- [ ] `get_context_preview` returns all expected data
- [ ] Active Context panel displays correctly
- [ ] Short-Term Memory panel displays correctly
- [ ] Context utilization bar shows accurate counts
- [ ] Token estimates are reasonable
- [ ] Relevance scores display for recalled memories
- [ ] "No relevant memories found" shows when appropriate
- [ ] Collapsible sections work correctly
- [ ] Panel refreshes on open

---

## Future Enhancements

1. **Real-time token counting** - Use actual tokenizer instead of estimates
2. **Memory importance indicators** - Visual cues for highly relevant memories
3. **Context editing** - Allow manual pinning/unpinning of memories
4. **Search preview** - Show what would be recalled for a given query
5. **Performance metrics** - Show semantic search latency/accuracy
