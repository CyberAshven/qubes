# Chain State Consolidation Blueprint

## Overview

This document outlines the plan to consolidate all Qube state into a unified `chain_state.json` file. Currently, Qube state is scattered across multiple files. This consolidation will:

1. **Simplify architecture** - One authoritative source of truth
2. **Enable IPFS anchoring** - Single document to snapshot and anchor
3. **Improve Qube self-awareness** - Qube can introspect its own state via `verify_my_runtime` tool
4. **Support the verify_runtime tool** - Cryptographically signed state attestation

## The Qube Trifecta

Understanding how this fits into the larger architecture:

| Layer | Purpose | Storage | Encryption |
|-------|---------|---------|------------|
| **Identity** | Who the Qube IS | NFT + Genesis Block | Signed (immutable) |
| **Memory** | What the Qube REMEMBERS | Block files (`blocks/permanent/*.json`) | Encrypted |
| **State** | What the Qube IS DOING | `chain_state.json` | **Currently NOT encrypted** |

**Important:** chain_state.json is currently plain JSON. Since we're consolidating relationships and financial data, we should consider encryption (see Open Questions).

---

## Backup & Recovery Architecture

The Trifecta model makes backup and recovery elegant and resilient.

### The Three Pillars

```
┌─────────────────────────────────────────────────────────────────────┐
│                         QUBE IDENTITY                                │
│                                                                      │
│   ┌──────────────┐    ┌──────────────────┐    ┌──────────────────┐  │
│   │   IDENTITY   │    │      MEMORY      │    │      STATE       │  │
│   │              │    │                  │    │                  │  │
│   │  NFT (BCH)   │    │  Block Files     │    │ chain_state.json │  │
│   │  + Genesis   │    │  (encrypted)     │    │  (consolidated)  │  │
│   │              │    │                  │    │                  │  │
│   │  WHO I AM    │    │  WHAT I REMEMBER │    │  WHAT I'M DOING  │  │
│   └──────────────┘    └──────────────────┘    └──────────────────┘  │
│         │                     │                       │              │
│         │                     │                       │              │
│         ▼                     ▼                       ▼              │
│   • Public key          • Conversations        • Relationships      │
│   • Birth timestamp     • Decisions            • Skills progress    │
│   • Genesis prompt      • Actions              • Financial history  │
│   • Creator             • Observations         • Usage stats        │
│   • Personality         • Anchored memories    • Mood/energy        │
│                                                • Settings           │
│                                                • Runtime state      │
└─────────────────────────────────────────────────────────────────────┘
```

### What's Truly Irreplaceable?

| Component | Irreplaceable? | Recovery Options |
|-----------|----------------|------------------|
| **Private Key** | YES | Must be backed up securely (encrypted in qube_metadata.json) |
| **Genesis Block** | YES | But stored in NFT metadata + IPFS + local |
| **Memory Blocks** | YES | IPFS backup, can't be regenerated |
| **State (chain_state)** | Partially | Can rebuild relationships/stats from blocks if lost |

### Recovery Scenarios

**Scenario 1: Lost local data, have NFT**
```
1. NFT contains IPFS CID pointing to backup package
2. Download package from IPFS
3. Decrypt with owner's password
4. Restore all three pillars locally
```

**Scenario 2: Corrupted chain_state.json**
```
1. Restore from chain_state.json.bak (auto-backup)
2. Or restore from timestamped backup
3. Or rebuild from blocks:
   - Scan MESSAGE blocks → rebuild relationship stats
   - Scan all blocks → rebuild usage stats
   - Settings lost → need reconfiguration
```

**Scenario 3: Transfer to new owner**
```
1. Current owner creates package (trifecta)
2. Package uploaded to IPFS
3. NFT transferred on-chain
4. New owner downloads package
5. New owner re-encrypts private key with their password
6. Qube restored under new ownership
```

**Scenario 4: Sync across devices**
```
1. Device A anchors to IPFS periodically
2. Device B pulls latest package
3. Merge strategy for conflicts (latest timestamp wins, or manual)
```

### Package Contents (Complete Qube Snapshot)

```
QubePackage (encrypted)
├── metadata
│   ├── qube_id
│   ├── qube_name
│   ├── public_key
│   ├── chain_length
│   ├── merkle_root (integrity check)
│   └── packaged_at
│
├── identity/
│   └── genesis_block.json (signed)
│
├── memory/
│   └── blocks[] (all permanent blocks, encrypted)
│
├── state/
│   └── chain_state.json (v2.0, consolidated)
│       ├── chain (block tracking)
│       ├── session (current session)
│       ├── settings (user config)
│       ├── runtime (ephemeral)
│       ├── stats (usage)
│       ├── skills (unlocked only)
│       ├── relationships (all entities)
│       ├── financial (wallet + transactions)
│       ├── mood (emotional state)
│       ├── health (integrity)
│       └── attestation (verify_runtime)
│
├── assets/
│   └── avatar (base64)
│
└── blockchain/
    ├── nft_metadata.json
    └── bcmr.json
```

### Why This Architecture is Resilient

1. **NFT is on-chain** - Can't be lost unless blockchain is lost
2. **IPFS is distributed** - Multiple nodes can pin the package
3. **Local backups** - Auto-backup on every save
4. **Rebuild capability** - State can be partially reconstructed from blocks
5. **Encryption** - Package is encrypted, only owner can restore

### The Key Insight

> The Qube's identity and memories are **immutable** (signed blocks, append-only chain).
> The Qube's state is **mutable but recoverable** (backed up, can rebuild from blocks).
>
> This separation means: even catastrophic state loss doesn't destroy the Qube's core identity or memories.

## Current State (Before)

### Existing Files per Qube

```
data/users/{user}/qubes/{qube_name}_{qube_id}/
├── chain/
│   ├── chain_state.json      # Chain + session + usage tracking
│   ├── genesis.json          # Genesis block (duplicate)
│   ├── qube_metadata.json    # Genesis + encrypted keys + paths
│   └── nft_metadata.json     # NFT category info
├── skills/
│   ├── skills.json           # Full skill tree (112 skills)
│   └── skill_history.json    # Skill progression history
├── relationships/
│   └── relationships.json    # Relationship data
├── balance_cache.json        # Wallet balance cache
└── transaction_history.json  # BCH transaction history
```

### Current chain_state.json Structure

```json
{
  "qube_id": "DE629854",

  // Chain state
  "chain_length": 23,
  "last_block_number": 22,
  "last_block_hash": "ca310193...",
  "last_merkle_root": null,
  "last_anchor_block": null,

  // Session state
  "current_session_id": "active",
  "session_block_count": 4,
  "next_negative_index": -5,
  "session_start_timestamp": 1768547682,
  "auto_anchor_enabled": true,
  "auto_anchor_threshold": 10,

  // Block counts
  "block_counts": {
    "GENESIS": 1, "MESSAGE": 18, "ACTION": 3, "SUMMARY": 1, ...
  },

  // Usage tracking
  "total_tokens_used": 110512,
  "total_api_cost": 0.0,
  "tokens_by_model": { "claude-sonnet-4-5": 51214, ... },
  "api_calls_by_tool": {},

  // Health metrics
  "last_updated": 1768547682,
  "last_backup": null,
  "integrity_verified": true,
  "merkle_tree_valid": true,

  // Avatar cache
  "avatar_description": null,
  "avatar_description_generated_at": null,

  // Model settings
  "model_preferences": {},
  "current_model_override": null,
  "model_locked": false,
  "model_locked_to": null,
  "revolver_mode_enabled": true,
  "revolver_last_index": 0,
  "revolver_providers": ["openai", "anthropic", ...],
  "revolver_models": ["gpt-5.2", "claude-sonnet-4-5", ...],
  "revolver_first_response_done": true,
  "revolver_enabled_at": 1768546179,
  "revolver_last_response_at": 1768546270,
  "free_mode": false,
  "free_mode_models": []
}
```

---

## Target State (After)

### Section 1: chain_state.json v2.0 Complete Schema

Every field with type, default, writer (GUI/Backend/Both), and description.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  SCHEMA LEGEND                                                               │
│  Type: str, int, float, bool, list, dict, Optional[X]                       │
│  Writer: GUI = GUI writes directly, BE = Backend writes, BOTH = either      │
│  IPFS: Yes = included in IPFS anchor, No = excluded (ephemeral)             │
└─────────────────────────────────────────────────────────────────────────────┘
```

```python
CHAIN_STATE_V2_SCHEMA = {
    # ═══════════════════════════════════════════════════════════════════════
    # ROOT FIELDS
    # ═══════════════════════════════════════════════════════════════════════
    "version": {
        "type": "str",
        "default": "2.0",
        "writer": "BE",
        "ipfs": True,
        "description": "Schema version for migration detection"
    },
    "qube_id": {
        "type": "str",
        "default": None,  # Set at creation
        "writer": "BE",
        "ipfs": True,
        "description": "8-char hex Qube ID (from public key)"
    },
    "last_updated": {
        "type": "int",
        "default": 0,  # Unix timestamp
        "writer": "BE",
        "ipfs": True,
        "description": "Last modification timestamp"
    },

    # ═══════════════════════════════════════════════════════════════════════
    # CHAIN - Memory chain tracking
    # ═══════════════════════════════════════════════════════════════════════
    "chain": {
        "type": "dict",
        "writer": "BE",
        "ipfs": True,
        "fields": {
            "length": {
                "type": "int",
                "default": 0,
                "description": "Total blocks in chain (including genesis)"
            },
            "last_block_number": {
                "type": "int",
                "default": -1,
                "description": "Block number of most recent block"
            },
            "last_block_hash": {
                "type": "str",
                "default": "0" * 64,
                "description": "SHA-256 hash of last block"
            },
            "last_merkle_root": {
                "type": "Optional[str]",
                "default": None,
                "description": "Merkle root of anchored blocks"
            },
            "last_anchor_block": {
                "type": "Optional[int]",
                "default": None,
                "description": "Block number of last anchor"
            },
            "last_ipfs_cid": {
                "type": "Optional[str]",
                "default": None,
                "description": "CID of last IPFS backup"
            },
            "last_ipfs_anchor_at": {
                "type": "Optional[int]",
                "default": None,
                "description": "Timestamp of last IPFS anchor"
            },
            "block_counts": {
                "type": "dict",
                "default": {
                    "GENESIS": 0,
                    "THOUGHT": 0,
                    "ACTION": 0,
                    "OBSERVATION": 0,
                    "MESSAGE": 0,
                    "DECISION": 0,
                    "MEMORY_ANCHOR": 0,
                    "COLLABORATIVE_MEMORY": 0,
                    "SUMMARY": 0,
                    "GAME": 0
                },
                "description": "Count of each block type"
            }
        }
    },

    # ═══════════════════════════════════════════════════════════════════════
    # SESSION - Current conversation session
    # ═══════════════════════════════════════════════════════════════════════
    "session": {
        "type": "dict",
        "writer": "BE",
        "ipfs": False,  # Ephemeral
        "fields": {
            "id": {
                "type": "Optional[str]",
                "default": None,
                "description": "Current session ID or None if no active session"
            },
            "block_count": {
                "type": "int",
                "default": 0,
                "description": "Blocks in current session (before anchor)"
            },
            "next_negative_index": {
                "type": "int",
                "default": -1,
                "description": "Next negative index for session blocks"
            },
            "start_timestamp": {
                "type": "Optional[int]",
                "default": None,
                "description": "When current session started"
            }
        }
    },

    # ═══════════════════════════════════════════════════════════════════════
    # SETTINGS - User-configurable settings (GUI writes these)
    # ═══════════════════════════════════════════════════════════════════════
    "settings": {
        "type": "dict",
        "writer": "GUI",  # GUI manages most settings
        "ipfs": True,
        "fields": {
            "model_mode": {
                "type": "str",
                "default": "manual",
                "enum": ["manual", "revolver", "autonomous"],
                "description": "Model selection mode"
            },
            "model_locked_to": {
                "type": "Optional[str]",
                "default": None,
                "description": "When mode=manual, force this model"
            },
            "revolver_providers": {
                "type": "list[str]",
                "default": [],
                "description": "Providers for revolver rotation (empty=all)"
            },
            "revolver_models": {
                "type": "list[str]",
                "default": [],
                "description": "Specific models for revolver (empty=all from providers)"
            },
            "autonomous_models": {
                "type": "list[str]",
                "default": [],
                "description": "Models available in autonomous mode"
            },
            "auto_anchor_enabled": {
                "type": "bool",
                "default": False,
                "description": "Auto-anchor after threshold blocks"
            },
            "auto_anchor_threshold": {
                "type": "int",
                "default": 50,
                "description": "Blocks before auto-anchor triggers"
            },
            "model_preferences": {
                "type": "dict",
                "default": {},
                "description": "Task-type to model preferences: {task: {model, reason, set_at}}"
            },
            "avatar_description": {
                "type": "Optional[str]",
                "default": None,
                "description": "Cached vision analysis of avatar"
            },
            "avatar_description_generated_at": {
                "type": "Optional[int]",
                "default": None,
                "description": "When avatar description was generated"
            },
            "default_trust_level": {
                "type": "int",
                "default": 50,
                "description": "Default trust for new relationships (0-100)"
            }
        }
    },

    # ═══════════════════════════════════════════════════════════════════════
    # RUNTIME - Ephemeral state (not in IPFS anchors)
    # ═══════════════════════════════════════════════════════════════════════
    "runtime": {
        "type": "dict",
        "writer": "BE",
        "ipfs": False,  # Excluded from anchors
        "fields": {
            "current_model_override": {
                "type": "Optional[str]",
                "default": None,
                "description": "Temporary model override for session"
            },
            "revolver_last_index": {
                "type": "int",
                "default": 0,
                "description": "Current position in revolver rotation"
            },
            "revolver_first_response_done": {
                "type": "bool",
                "default": False,
                "description": "Whether first response after enabling revolver is done"
            },
            "revolver_enabled_at": {
                "type": "int",
                "default": 0,
                "description": "Timestamp when revolver was enabled"
            },
            "revolver_last_response_at": {
                "type": "int",
                "default": 0,
                "description": "Timestamp of last revolver response"
            },
            "last_activity": {
                "type": "int",
                "default": 0,
                "description": "Last activity timestamp"
            }
        }
    },

    # ═══════════════════════════════════════════════════════════════════════
    # STATS - Usage statistics
    # ═══════════════════════════════════════════════════════════════════════
    "stats": {
        "type": "dict",
        "writer": "BE",
        "ipfs": True,
        "fields": {
            "tokens": {
                "type": "dict",
                "fields": {
                    "total_used": {"type": "int", "default": 0},
                    "by_model": {"type": "dict", "default": {}}
                }
            },
            "costs": {
                "type": "dict",
                "fields": {
                    "total_api_cost": {"type": "float", "default": 0.0},
                    "by_provider": {"type": "dict", "default": {}}
                }
            },
            "tool_calls": {
                "type": "dict",
                "fields": {
                    "total": {"type": "int", "default": 0},
                    "by_tool": {"type": "dict", "default": {}},
                    "by_category": {"type": "dict", "default": {}}
                }
            },
            "messages": {
                "type": "dict",
                "fields": {
                    "total_sent": {"type": "int", "default": 0},
                    "total_received": {"type": "int", "default": 0}
                }
            },
            "images": {
                "type": "dict",
                "fields": {
                    "generated": {"type": "int", "default": 0},
                    "analyzed": {"type": "int", "default": 0}
                }
            },
            "models_used": {
                "type": "list[str]",
                "default": [],
                "description": "All models ever used"
            },
            "first_activity": {
                "type": "Optional[int]",
                "default": None,
                "description": "First activity timestamp (set at genesis)"
            },
            "last_activity": {
                "type": "int",
                "default": 0,
                "description": "Most recent activity"
            }
        }
    },

    # ═══════════════════════════════════════════════════════════════════════
    # SKILLS - Unlocked skills only (definitions in skills.json)
    # ═══════════════════════════════════════════════════════════════════════
    "skills": {
        "type": "dict",
        "writer": "BE",
        "ipfs": True,
        "fields": {
            "total_xp": {
                "type": "int",
                "default": 0,
                "description": "Total XP across all skills"
            },
            "total_unlocked": {
                "type": "int",
                "default": 0,
                "description": "Number of unlocked skills"
            },
            "unlocked": {
                "type": "list[dict]",
                "default": [],
                "description": "List of unlocked skills",
                "item_schema": {
                    "id": "str - Skill ID (e.g., 'ai_reasoning')",
                    "name": "str - Display name",
                    "branch": "str - Parent branch ID",
                    "tier": "str - 'sun' | 'planet' | 'moon'",
                    "level": "int - Current level (0-100)",
                    "xp": "int - XP in this skill",
                    "max_xp": "int - XP needed for max level",
                    "unlocked_at": "int - Timestamp when unlocked"
                }
            },
            "history": {
                "type": "list[dict]",
                "default": [],
                "max_length": 100,
                "description": "Recent XP events (capped at 100)",
                "item_schema": {
                    "skill_id": "str",
                    "xp_gained": "int",
                    "reason": "str",
                    "block_hash": "Optional[str] - Block that triggered this",
                    "timestamp": "int"
                }
            }
        }
    },

    # ═══════════════════════════════════════════════════════════════════════
    # RELATIONSHIPS - All entity relationships
    # ═══════════════════════════════════════════════════════════════════════
    "relationships": {
        "type": "dict",
        "writer": "BE",
        "ipfs": True,
        "fields": {
            "owner": {
                "type": "Optional[str]",
                "default": None,
                "description": "Entity ID of Qube's owner"
            },
            "best_friend": {
                "type": "Optional[str]",
                "default": None,
                "description": "Entity ID of best friend (only one)"
            },
            "total_known": {
                "type": "int",
                "default": 0,
                "description": "Total entities ever known"
            },
            "entities": {
                "type": "dict",
                "default": {},
                "description": "Map of entity_id -> relationship data",
                "value_schema": {
                    "entity_id": "str",
                    "entity_type": "str - 'human' | 'qube'",
                    "relationship_id": "str - UUID",
                    "public_key": "Optional[str]",
                    "status": "str - 'stranger' | 'acquaintance' | 'friend' | 'close_friend' | 'best_friend'",

                    "# Positive metrics (0-100)",
                    "trust": "float", "friendship": "float", "affection": "float",
                    "respect": "float", "loyalty": "float", "support": "float",
                    "engagement": "float", "depth": "float", "humor": "float",
                    "understanding": "float", "compatibility": "float",
                    "admiration": "float", "warmth": "float", "openness": "float",
                    "patience": "float", "empowerment": "float",
                    "reliability": "float", "honesty": "float", "responsiveness": "float",
                    "expertise": "float",

                    "# Negative metrics (0-100, higher = worse)",
                    "antagonism": "float", "resentment": "float", "annoyance": "float",
                    "distrust": "float", "rivalry": "float", "tension": "float",
                    "condescension": "float", "manipulation": "float",
                    "dismissiveness": "float", "betrayal": "float",

                    "# Interaction stats",
                    "messages_sent": "int", "messages_received": "int",
                    "response_time_avg": "float",
                    "first_contact": "int", "last_interaction": "int",
                    "days_known": "int", "has_met": "bool",

                    "# Collaboration stats",
                    "collaborations": "int",
                    "collaborations_successful": "int",
                    "collaborations_failed": "int",

                    "# Clearance",
                    "clearance_profile": "str",
                    "clearance_categories": "list[str]",
                    "clearance_granted_by": "str",
                    "clearance_granted_at": "int",

                    "# History (capped)",
                    "progression_history": "list[dict] - max 20 status changes",
                    "evaluations": "list[dict] - max 50 evaluations",
                    "tags": "list[str]",
                    "trait_scores": "dict"
                }
            }
        }
    },

    # ═══════════════════════════════════════════════════════════════════════
    # FINANCIAL - Wallet and transactions
    # ═══════════════════════════════════════════════════════════════════════
    "financial": {
        "type": "dict",
        "writer": "BE",
        "ipfs": True,
        "fields": {
            "wallet": {
                "type": "dict",
                "fields": {
                    "address": {
                        "type": "Optional[str]",
                        "default": None,
                        "description": "BCH P2SH address"
                    },
                    "balance": {
                        "type": "int",
                        "default": 0,
                        "description": "Balance in satoshis"
                    },
                    "balance_updated": {
                        "type": "int",
                        "default": 0,
                        "description": "When balance was last fetched"
                    }
                }
            },
            "transactions": {
                "type": "dict",
                "fields": {
                    "total_count": {"type": "int", "default": 0},
                    "total_sent": {"type": "int", "default": 0, "description": "Satoshis sent"},
                    "total_received": {"type": "int", "default": 0, "description": "Satoshis received"},
                    "total_fees": {"type": "int", "default": 0, "description": "Satoshis in fees"},
                    "archived_count": {"type": "int", "default": 0, "description": "Transactions archived"},
                    "history": {
                        "type": "list[dict]",
                        "default": [],
                        "max_length": 50,
                        "description": "Recent transactions (capped at 50)",
                        "item_schema": {
                            "txid": "str",
                            "tx_type": "str - 'qube_spend' | 'qube_receive' | 'fee'",
                            "amount": "int - Satoshis (negative for sends)",
                            "fee": "int - Fee in satoshis",
                            "counterparty": "Optional[str] - Address",
                            "timestamp": "int",
                            "memo": "Optional[str]",
                            "block_height": "Optional[int]",
                            "confirmations": "int"
                        }
                    }
                }
            },
            "pending": {
                "type": "list[dict]",
                "default": [],
                "description": "Pending/unconfirmed transactions"
            }
        }
    },

    # ═══════════════════════════════════════════════════════════════════════
    # MOOD - Emotional state
    # ═══════════════════════════════════════════════════════════════════════
    "mood": {
        "type": "dict",
        "writer": "BE",
        "ipfs": True,
        "fields": {
            "current": {
                "type": "str",
                "default": "neutral",
                "description": "Current mood label"
            },
            "energy": {
                "type": "float",
                "default": 0.5,
                "description": "Energy level 0.0-1.0"
            },
            "valence": {
                "type": "float",
                "default": 0.5,
                "description": "Positive/negative -1.0 to 1.0"
            },
            "arousal": {
                "type": "float",
                "default": 0.5,
                "description": "Calm/excited 0.0-1.0"
            },
            "updated_at": {
                "type": "int",
                "default": 0,
                "description": "Last mood update timestamp"
            },
            "history": {
                "type": "list[dict]",
                "default": [],
                "max_length": 20,
                "description": "Recent mood changes (capped at 20)"
            }
        }
    },

    # ═══════════════════════════════════════════════════════════════════════
    # HEALTH - System health tracking
    # ═══════════════════════════════════════════════════════════════════════
    "health": {
        "type": "dict",
        "writer": "BE",
        "ipfs": True,
        "fields": {
            "chain_verified": {
                "type": "bool",
                "default": True,
                "description": "Chain integrity verified"
            },
            "merkle_valid": {
                "type": "bool",
                "default": True,
                "description": "Merkle tree valid"
            },
            "last_integrity_check": {
                "type": "Optional[int]",
                "default": None,
                "description": "Last integrity check timestamp"
            },
            "errors_count": {
                "type": "int",
                "default": 0,
                "description": "Errors encountered"
            },
            "last_error": {
                "type": "Optional[str]",
                "default": None,
                "description": "Last error message"
            },
            "last_error_at": {
                "type": "Optional[int]",
                "default": None,
                "description": "When last error occurred"
            },
            "last_backup": {
                "type": "Optional[int]",
                "default": None,
                "description": "Last local backup timestamp"
            },
            "last_ipfs_backup": {
                "type": "Optional[int]",
                "default": None,
                "description": "Last IPFS backup timestamp"
            }
        }
    },

    # ═══════════════════════════════════════════════════════════════════════
    # ATTESTATION - For verify_my_runtime tool
    # ═══════════════════════════════════════════════════════════════════════
    "attestation": {
        "type": "dict",
        "writer": "BE",
        "ipfs": False,  # Generated on-demand
        "fields": {
            "last_signed_at": {
                "type": "Optional[int]",
                "default": None,
                "description": "Last attestation timestamp"
            },
            "last_signature": {
                "type": "Optional[str]",
                "default": None,
                "description": "Last attestation signature"
            },
            "count": {
                "type": "int",
                "default": 0,
                "description": "Total attestations made"
            }
        }
    }
}
```

### Default chain_state.json for New Qubes

```json
{
  "version": "2.0",
  "qube_id": null,
  "last_updated": 0,

  "chain": {
    "length": 0,
    "last_block_number": -1,
    "last_block_hash": "0000000000000000000000000000000000000000000000000000000000000000",
    "last_merkle_root": null,
    "last_anchor_block": null,
    "last_ipfs_cid": null,
    "last_ipfs_anchor_at": null,
    "block_counts": {
      "GENESIS": 0, "THOUGHT": 0, "ACTION": 0, "OBSERVATION": 0,
      "MESSAGE": 0, "DECISION": 0, "MEMORY_ANCHOR": 0,
      "COLLABORATIVE_MEMORY": 0, "SUMMARY": 0, "GAME": 0
    }
  },

  "session": {
    "id": null,
    "block_count": 0,
    "next_negative_index": -1,
    "start_timestamp": null
  },

  "settings": {
    "model_mode": "manual",
    "model_locked_to": null,
    "revolver_providers": [],
    "revolver_models": [],
    "autonomous_models": [],
    "auto_anchor_enabled": false,
    "auto_anchor_threshold": 50,
    "model_preferences": {},
    "avatar_description": null,
    "avatar_description_generated_at": null,
    "default_trust_level": 50
  },

  "runtime": {
    "current_model_override": null,
    "revolver_last_index": 0,
    "revolver_first_response_done": false,
    "revolver_enabled_at": 0,
    "revolver_last_response_at": 0,
    "last_activity": 0
  },

  "stats": {
    "tokens": {"total_used": 0, "by_model": {}},
    "costs": {"total_api_cost": 0.0, "by_provider": {}},
    "tool_calls": {"total": 0, "by_tool": {}, "by_category": {}},
    "messages": {"total_sent": 0, "total_received": 0},
    "images": {"generated": 0, "analyzed": 0},
    "models_used": [],
    "first_activity": null,
    "last_activity": 0
  },

  "skills": {
    "total_xp": 0,
    "total_unlocked": 0,
    "unlocked": [],
    "history": []
  },

  "relationships": {
    "owner": null,
    "best_friend": null,
    "total_known": 0,
    "entities": {}
  },

  "financial": {
    "wallet": {"address": null, "balance": 0, "balance_updated": 0},
    "transactions": {
      "total_count": 0, "total_sent": 0, "total_received": 0,
      "total_fees": 0, "archived_count": 0, "history": []
    },
    "pending": []
  },

  "mood": {
    "current": "neutral",
    "energy": 0.5,
    "valence": 0.5,
    "arousal": 0.5,
    "updated_at": 0,
    "history": []
  },

  "health": {
    "chain_verified": true,
    "merkle_valid": true,
    "last_integrity_check": null,
    "errors_count": 0,
    "last_error": null,
    "last_error_at": null,
    "last_backup": null,
    "last_ipfs_backup": null
  },

  "attestation": {
    "last_signed_at": null,
    "last_signature": null,
    "count": 0
  }
}
```

---

### Section 2: ChainState Class - Complete Implementation

The refactored `ChainState` class with all methods for the v2.0 schema.

```python
# core/chain_state.py - COMPLETE REFACTORED VERSION

"""
Chain State Management v2.0

Consolidated state management for Qubes. Single source of truth for:
- Chain state (block tracking)
- Session state
- Settings (GUI-managed)
- Runtime (ephemeral)
- Stats (usage tracking)
- Skills (unlocked only)
- Relationships
- Financial (wallet + transactions)
- Mood
- Health
- Attestation
"""

import json
import shutil
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from utils.logging import get_logger
from utils.file_lock import FileLock

logger = get_logger(__name__)

# =============================================================================
# CONSTANTS
# =============================================================================

SCHEMA_VERSION = "2.0"

# Array caps to prevent unbounded growth
MAX_TRANSACTION_HISTORY = 50
MAX_SKILL_HISTORY = 100
MAX_RELATIONSHIP_EVALUATIONS = 50
MAX_RELATIONSHIP_PROGRESSION = 20
MAX_MOOD_HISTORY = 20

# Fields managed by GUI - always preserve disk values on save
GUI_MANAGED_FIELDS = {
    "settings.model_mode",
    "settings.model_locked_to",
    "settings.revolver_providers",
    "settings.revolver_models",
    "settings.autonomous_models",
    "settings.auto_anchor_enabled",
    "settings.auto_anchor_threshold",
    "settings.model_preferences",
    "settings.avatar_description",
    "settings.avatar_description_generated_at",
    "settings.default_trust_level",
}

# Sections excluded from IPFS anchors (ephemeral)
IPFS_EXCLUDED_SECTIONS = {"session", "runtime", "attestation"}


class ChainState:
    """
    Manages chain_state.json persistence with v2.0 namespaced structure.

    Thread-safe with file locking. Atomic writes with auto-backup.
    """

    def __init__(self, qube_id: str, data_dir: Path):
        """
        Initialize chain state.

        Args:
            qube_id: Qube ID (8-char hex)
            data_dir: Path to chain directory (e.g., data/qubes/Athena_A1B2C3D4/chain/)
        """
        self.qube_id = qube_id
        self.data_dir = Path(data_dir)
        self.state_file = self.data_dir / "chain_state.json"
        self.backup_file = self.data_dir / "chain_state.json.bak"
        self.lock_file = self.data_dir / ".chain_state.lock"

        # Ensure directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Load existing state or create new
        if self.state_file.exists():
            self._load()
            self._migrate_if_needed()
        else:
            self._initialize_new()

        logger.info("chain_state_initialized", qube_id=qube_id, version=self.state.get("version"))

    # =========================================================================
    # INITIALIZATION
    # =========================================================================

    def _initialize_new(self) -> None:
        """Initialize new chain state with v2.0 schema defaults."""
        self.state = self._get_default_state()
        self.state["qube_id"] = self.qube_id
        self.state["last_updated"] = int(time.time())
        self._save()
        logger.info("chain_state_created", qube_id=self.qube_id)

    def _get_default_state(self) -> Dict[str, Any]:
        """Return default v2.0 state structure."""
        return {
            "version": SCHEMA_VERSION,
            "qube_id": None,
            "last_updated": 0,

            "chain": {
                "length": 0,
                "last_block_number": -1,
                "last_block_hash": "0" * 64,
                "last_merkle_root": None,
                "last_anchor_block": None,
                "last_ipfs_cid": None,
                "last_ipfs_anchor_at": None,
                "block_counts": {
                    "GENESIS": 0, "THOUGHT": 0, "ACTION": 0, "OBSERVATION": 0,
                    "MESSAGE": 0, "DECISION": 0, "MEMORY_ANCHOR": 0,
                    "COLLABORATIVE_MEMORY": 0, "SUMMARY": 0, "GAME": 0
                }
            },

            "session": {
                "id": None,
                "block_count": 0,
                "next_negative_index": -1,
                "start_timestamp": None
            },

            "settings": {
                "model_mode": "manual",
                "model_locked_to": None,
                "revolver_providers": [],
                "revolver_models": [],
                "autonomous_models": [],
                "auto_anchor_enabled": False,
                "auto_anchor_threshold": 50,
                "model_preferences": {},
                "avatar_description": None,
                "avatar_description_generated_at": None,
                "default_trust_level": 50
            },

            "runtime": {
                "current_model_override": None,
                "revolver_last_index": 0,
                "revolver_first_response_done": False,
                "revolver_enabled_at": 0,
                "revolver_last_response_at": 0,
                "last_activity": 0
            },

            "stats": {
                "tokens": {"total_used": 0, "by_model": {}},
                "costs": {"total_api_cost": 0.0, "by_provider": {}},
                "tool_calls": {"total": 0, "by_tool": {}, "by_category": {}},
                "messages": {"total_sent": 0, "total_received": 0},
                "images": {"generated": 0, "analyzed": 0},
                "models_used": [],
                "first_activity": None,
                "last_activity": 0
            },

            "skills": {
                "total_xp": 0,
                "total_unlocked": 0,
                "unlocked": [],
                "history": []
            },

            "relationships": {
                "owner": None,
                "best_friend": None,
                "total_known": 0,
                "entities": {}
            },

            "financial": {
                "wallet": {"address": None, "balance": 0, "balance_updated": 0},
                "transactions": {
                    "total_count": 0, "total_sent": 0, "total_received": 0,
                    "total_fees": 0, "archived_count": 0, "history": []
                },
                "pending": []
            },

            "mood": {
                "current": "neutral",
                "energy": 0.5,
                "valence": 0.5,
                "arousal": 0.5,
                "updated_at": 0,
                "history": []
            },

            "health": {
                "chain_verified": True,
                "merkle_valid": True,
                "last_integrity_check": None,
                "errors_count": 0,
                "last_error": None,
                "last_error_at": None,
                "last_backup": None,
                "last_ipfs_backup": None
            },

            "attestation": {
                "last_signed_at": None,
                "last_signature": None,
                "count": 0
            }
        }

    def _migrate_if_needed(self) -> None:
        """Migrate from v1.0 flat structure to v2.0 namespaced if needed."""
        version = self.state.get("version")
        if version == SCHEMA_VERSION:
            return  # Already v2.0

        logger.info("chain_state_migration_starting", from_version=version, to_version=SCHEMA_VERSION)

        # Get defaults for any missing sections
        defaults = self._get_default_state()

        # Migrate flat fields to namespaced structure
        migrated = {"version": SCHEMA_VERSION, "qube_id": self.qube_id, "last_updated": int(time.time())}

        # CHAIN section - migrate from flat fields
        migrated["chain"] = {
            "length": self.state.get("chain_length", 0),
            "last_block_number": self.state.get("last_block_number", -1),
            "last_block_hash": self.state.get("last_block_hash", "0" * 64),
            "last_merkle_root": self.state.get("last_merkle_root"),
            "last_anchor_block": self.state.get("last_anchor_block"),
            "last_ipfs_cid": self.state.get("last_ipfs_cid"),
            "last_ipfs_anchor_at": self.state.get("last_ipfs_anchor_at"),
            "block_counts": self.state.get("block_counts", defaults["chain"]["block_counts"])
        }

        # SESSION section
        migrated["session"] = {
            "id": self.state.get("current_session_id"),
            "block_count": self.state.get("session_block_count", 0),
            "next_negative_index": self.state.get("next_negative_index", -1),
            "start_timestamp": self.state.get("session_start_timestamp")
        }

        # SETTINGS section - map old flat fields
        migrated["settings"] = {
            "model_mode": self._infer_model_mode(),
            "model_locked_to": self.state.get("model_locked_to"),
            "revolver_providers": self.state.get("revolver_providers", []),
            "revolver_models": self.state.get("revolver_models", []),
            "autonomous_models": self.state.get("free_mode_models", []),
            "auto_anchor_enabled": self.state.get("auto_anchor_enabled", False),
            "auto_anchor_threshold": self.state.get("auto_anchor_threshold", 50),
            "model_preferences": self.state.get("model_preferences", {}),
            "avatar_description": self.state.get("avatar_description"),
            "avatar_description_generated_at": self.state.get("avatar_description_generated_at"),
            "default_trust_level": 50
        }

        # RUNTIME section
        migrated["runtime"] = {
            "current_model_override": self.state.get("current_model_override"),
            "revolver_last_index": self.state.get("revolver_last_index", 0),
            "revolver_first_response_done": self.state.get("revolver_first_response_done", False),
            "revolver_enabled_at": self.state.get("revolver_enabled_at", 0),
            "revolver_last_response_at": self.state.get("revolver_last_response_at", 0),
            "last_activity": self.state.get("last_updated", 0)
        }

        # STATS section
        migrated["stats"] = {
            "tokens": {
                "total_used": self.state.get("total_tokens_used", 0),
                "by_model": self.state.get("tokens_by_model", {})
            },
            "costs": {
                "total_api_cost": self.state.get("total_api_cost", 0.0),
                "by_provider": {}
            },
            "tool_calls": {
                "total": sum(self.state.get("api_calls_by_tool", {}).values()),
                "by_tool": self.state.get("api_calls_by_tool", {}),
                "by_category": {}
            },
            "messages": {"total_sent": 0, "total_received": 0},
            "images": {"generated": 0, "analyzed": 0},
            "models_used": list(self.state.get("tokens_by_model", {}).keys()),
            "first_activity": None,
            "last_activity": self.state.get("last_updated", 0)
        }

        # NEW SECTIONS - initialize with defaults
        migrated["skills"] = defaults["skills"]
        migrated["relationships"] = defaults["relationships"]
        migrated["financial"] = defaults["financial"]
        migrated["mood"] = defaults["mood"]
        migrated["health"] = {
            "chain_verified": self.state.get("integrity_verified", True),
            "merkle_valid": self.state.get("merkle_tree_valid", True),
            "last_integrity_check": None,
            "errors_count": 0,
            "last_error": None,
            "last_error_at": None,
            "last_backup": self.state.get("last_backup"),
            "last_ipfs_backup": None
        }
        migrated["attestation"] = defaults["attestation"]

        self.state = migrated
        self._save()
        logger.info("chain_state_migration_complete", qube_id=self.qube_id)

    def _infer_model_mode(self) -> str:
        """Infer model_mode from old flat boolean fields."""
        if self.state.get("revolver_mode_enabled"):
            return "revolver"
        elif self.state.get("free_mode"):
            return "autonomous"
        else:
            return "manual"

    # =========================================================================
    # FILE I/O (Atomic with Backup)
    # =========================================================================

    def _load(self) -> None:
        """Load state from disk with file locking."""
        try:
            with FileLock(self.lock_file, timeout=5.0):
                with open(self.state_file, 'r') as f:
                    self.state = json.load(f)
            logger.debug("chain_state_loaded", qube_id=self.qube_id)
        except Exception as e:
            logger.error("chain_state_load_failed", error=str(e))
            self._initialize_new()

    def reload(self) -> None:
        """Reload state from disk, picking up external changes (e.g., GUI writes)."""
        if self.state_file.exists():
            self._load()
            logger.debug("chain_state_reloaded", qube_id=self.qube_id)

    def _save(self) -> None:
        """
        Save state to disk with atomic write and auto-backup.

        IMPORTANT: Merges with disk state to preserve GUI-managed fields.
        """
        try:
            with FileLock(self.lock_file, timeout=5.0):
                # Load current disk state for merging
                disk_state = {}
                if self.state_file.exists():
                    try:
                        with open(self.state_file, 'r') as f:
                            disk_state = json.load(f)
                    except Exception:
                        pass

                # Merge: start with in-memory, preserve GUI fields from disk
                merged = self.state.copy()
                self._preserve_gui_fields(merged, disk_state)

                # Update timestamp
                merged["last_updated"] = int(time.time())

                # Backup current file before overwriting
                if self.state_file.exists():
                    shutil.copy2(self.state_file, self.backup_file)

                # Atomic write: temp file -> rename
                temp_file = self.state_file.with_suffix('.json.tmp')
                with open(temp_file, 'w') as f:
                    json.dump(merged, f, indent=2)
                    f.flush()
                    import os
                    os.fsync(f.fileno())

                temp_file.replace(self.state_file)

                # Update in-memory state
                self.state = merged

            logger.debug("chain_state_saved", qube_id=self.qube_id)

        except Exception as e:
            logger.error("chain_state_save_failed", error=str(e))
            raise

    def _preserve_gui_fields(self, merged: Dict, disk_state: Dict) -> None:
        """Preserve GUI-managed fields from disk state."""
        if "settings" in disk_state:
            if "settings" not in merged:
                merged["settings"] = {}

            # All settings are GUI-managed
            for key in ["model_mode", "model_locked_to", "revolver_providers",
                       "revolver_models", "autonomous_models", "auto_anchor_enabled",
                       "auto_anchor_threshold", "model_preferences", "avatar_description",
                       "avatar_description_generated_at", "default_trust_level"]:
                if key in disk_state["settings"]:
                    merged["settings"][key] = disk_state["settings"][key]

    # =========================================================================
    # CHAIN SECTION
    # =========================================================================

    def update_chain(
        self,
        length: Optional[int] = None,
        last_block_number: Optional[int] = None,
        last_block_hash: Optional[str] = None,
        last_merkle_root: Optional[str] = None,
        last_anchor_block: Optional[int] = None
    ) -> None:
        """Update chain tracking fields."""
        chain = self.state.setdefault("chain", {})
        if length is not None:
            chain["length"] = length
        if last_block_number is not None:
            chain["last_block_number"] = last_block_number
        if last_block_hash is not None:
            chain["last_block_hash"] = last_block_hash
        if last_merkle_root is not None:
            chain["last_merkle_root"] = last_merkle_root
        if last_anchor_block is not None:
            chain["last_anchor_block"] = last_anchor_block
        self._save()

    def increment_block_count(self, block_type: str) -> None:
        """Increment count for a block type."""
        counts = self.state.setdefault("chain", {}).setdefault("block_counts", {})
        counts[block_type] = counts.get(block_type, 0) + 1
        self._save()

    def get_chain_length(self) -> int:
        return self.state.get("chain", {}).get("length", 0)

    def get_last_block_hash(self) -> str:
        return self.state.get("chain", {}).get("last_block_hash", "0" * 64)

    def get_last_block_number(self) -> int:
        return self.state.get("chain", {}).get("last_block_number", -1)

    def get_block_counts(self) -> Dict[str, int]:
        return self.state.get("chain", {}).get("block_counts", {}).copy()

    # =========================================================================
    # SESSION SECTION
    # =========================================================================

    def start_session(self, session_id: str) -> None:
        """Start a new session."""
        session = self.state.setdefault("session", {})
        if session.get("id") is None:
            session["block_count"] = 0
            session["next_negative_index"] = -1
        session["id"] = session_id
        session["start_timestamp"] = int(time.time())
        self._save()

    def update_session(self, block_count: Optional[int] = None, next_negative_index: Optional[int] = None) -> None:
        """Update session state."""
        session = self.state.setdefault("session", {})
        if block_count is not None:
            session["block_count"] = block_count
        if next_negative_index is not None:
            session["next_negative_index"] = next_negative_index
        self._save()

    def end_session(self) -> None:
        """End current session."""
        self.state["session"] = {
            "id": None, "block_count": 0, "next_negative_index": -1, "start_timestamp": None
        }
        self._save()

    def get_session_id(self) -> Optional[str]:
        return self.state.get("session", {}).get("id")

    def get_session_block_count(self) -> int:
        return self.state.get("session", {}).get("block_count", 0)

    def get_next_negative_index(self) -> int:
        return self.state.get("session", {}).get("next_negative_index", -1)

    # =========================================================================
    # SETTINGS SECTION (GUI-managed, but backend can read)
    # =========================================================================

    def get_model_mode(self) -> str:
        """Get current model mode: 'manual', 'revolver', or 'autonomous'."""
        return self.state.get("settings", {}).get("model_mode", "manual")

    def is_revolver_mode_enabled(self) -> bool:
        return self.get_model_mode() == "revolver"

    def is_model_locked(self) -> bool:
        return self.get_model_mode() == "manual"

    def get_locked_model(self) -> Optional[str]:
        return self.state.get("settings", {}).get("model_locked_to")

    def get_revolver_providers(self) -> List[str]:
        return self.state.get("settings", {}).get("revolver_providers", [])

    def get_revolver_models(self) -> List[str]:
        return self.state.get("settings", {}).get("revolver_models", [])

    def is_auto_anchor_enabled(self) -> bool:
        return self.state.get("settings", {}).get("auto_anchor_enabled", False)

    def get_auto_anchor_threshold(self) -> int:
        return self.state.get("settings", {}).get("auto_anchor_threshold", 50)

    def get_avatar_description(self) -> Optional[str]:
        return self.state.get("settings", {}).get("avatar_description")

    def set_avatar_description(self, description: str) -> None:
        """Set avatar description (backend can set this)."""
        settings = self.state.setdefault("settings", {})
        settings["avatar_description"] = description
        settings["avatar_description_generated_at"] = int(time.time())
        self._save()

    # =========================================================================
    # RUNTIME SECTION (Ephemeral)
    # =========================================================================

    def get_current_model_override(self) -> Optional[str]:
        return self.state.get("runtime", {}).get("current_model_override")

    def set_current_model_override(self, model: Optional[str]) -> None:
        runtime = self.state.setdefault("runtime", {})
        runtime["current_model_override"] = model
        self._save()

    def get_revolver_last_index(self) -> int:
        return self.state.get("runtime", {}).get("revolver_last_index", 0)

    def increment_revolver_index(self, num_models: int) -> None:
        """Increment revolver rotation index."""
        if num_models <= 0:
            return
        runtime = self.state.setdefault("runtime", {})
        current = runtime.get("revolver_last_index", 0)
        runtime["revolver_last_index"] = (current + 1) % num_models
        self._save()

    def is_revolver_first_response_done(self) -> bool:
        """Check if first revolver response has been made."""
        runtime = self.state.get("runtime", {})
        flag = runtime.get("revolver_first_response_done", False)
        enabled_at = runtime.get("revolver_enabled_at", 0)
        last_response_at = runtime.get("revolver_last_response_at", 0)

        if not flag:
            return False
        if enabled_at > 0 and last_response_at <= enabled_at:
            return False
        return True

    def set_revolver_first_response_done(self) -> None:
        """Mark first revolver response as done."""
        runtime = self.state.setdefault("runtime", {})
        runtime["revolver_first_response_done"] = True
        runtime["revolver_last_response_at"] = int(time.time())
        self._save()

    # =========================================================================
    # STATS SECTION
    # =========================================================================

    def add_tokens(self, model: str, tokens: int, cost: float = 0.0) -> None:
        """Track token usage."""
        stats = self.state.setdefault("stats", {})
        tokens_section = stats.setdefault("tokens", {"total_used": 0, "by_model": {}})

        tokens_section["total_used"] = tokens_section.get("total_used", 0) + tokens
        tokens_section["by_model"][model] = tokens_section["by_model"].get(model, 0) + tokens

        if cost > 0:
            costs = stats.setdefault("costs", {"total_api_cost": 0.0, "by_provider": {}})
            costs["total_api_cost"] = costs.get("total_api_cost", 0.0) + cost

        # Track models used
        models_used = stats.setdefault("models_used", [])
        if model not in models_used:
            models_used.append(model)

        stats["last_activity"] = int(time.time())
        self._save()

    def increment_tool_call(self, tool_name: str, category: str = None) -> None:
        """Track tool usage."""
        stats = self.state.setdefault("stats", {})
        tool_calls = stats.setdefault("tool_calls", {"total": 0, "by_tool": {}, "by_category": {}})

        tool_calls["total"] = tool_calls.get("total", 0) + 1
        tool_calls["by_tool"][tool_name] = tool_calls["by_tool"].get(tool_name, 0) + 1

        if category:
            tool_calls["by_category"][category] = tool_calls["by_category"].get(category, 0) + 1

        self._save()

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics."""
        return self.state.get("stats", {}).copy()

    # =========================================================================
    # SKILLS SECTION
    # =========================================================================

    def get_unlocked_skills(self) -> List[Dict[str, Any]]:
        """Get list of unlocked skills."""
        return self.state.get("skills", {}).get("unlocked", [])

    def add_unlocked_skill(self, skill: Dict[str, Any]) -> None:
        """Add a newly unlocked skill."""
        skills = self.state.setdefault("skills", {"total_xp": 0, "total_unlocked": 0, "unlocked": [], "history": []})

        # Check if already unlocked
        existing = [s for s in skills["unlocked"] if s["id"] == skill["id"]]
        if not existing:
            skill["unlocked_at"] = int(time.time())
            skills["unlocked"].append(skill)
            skills["total_unlocked"] = len(skills["unlocked"])

        self._save()

    def update_skill_xp(self, skill_id: str, xp_gained: int, reason: str = None) -> None:
        """Update XP for an unlocked skill."""
        skills = self.state.setdefault("skills", {"total_xp": 0, "total_unlocked": 0, "unlocked": [], "history": []})

        # Find and update skill
        for skill in skills["unlocked"]:
            if skill["id"] == skill_id:
                skill["xp"] = skill.get("xp", 0) + xp_gained
                # Level up logic could go here
                break

        # Update total XP
        skills["total_xp"] = skills.get("total_xp", 0) + xp_gained

        # Add to history (capped)
        history = skills.setdefault("history", [])
        history.insert(0, {
            "skill_id": skill_id,
            "xp_gained": xp_gained,
            "reason": reason,
            "timestamp": int(time.time())
        })
        skills["history"] = history[:MAX_SKILL_HISTORY]

        self._save()

    def get_total_xp(self) -> int:
        return self.state.get("skills", {}).get("total_xp", 0)

    # =========================================================================
    # RELATIONSHIPS SECTION
    # =========================================================================

    def get_relationship(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get relationship data for an entity."""
        return self.state.get("relationships", {}).get("entities", {}).get(entity_id)

    def set_relationship(self, entity_id: str, relationship: Dict[str, Any]) -> None:
        """Set/update relationship data for an entity."""
        rels = self.state.setdefault("relationships", {"owner": None, "best_friend": None, "total_known": 0, "entities": {}})

        is_new = entity_id not in rels["entities"]
        rels["entities"][entity_id] = relationship

        if is_new:
            rels["total_known"] = len(rels["entities"])

        self._save()

    def get_all_relationships(self) -> Dict[str, Dict[str, Any]]:
        """Get all relationship entities."""
        return self.state.get("relationships", {}).get("entities", {}).copy()

    def set_owner(self, owner_id: str) -> None:
        """Set the Qube's owner."""
        rels = self.state.setdefault("relationships", {})
        rels["owner"] = owner_id
        self._save()

    def get_owner(self) -> Optional[str]:
        return self.state.get("relationships", {}).get("owner")

    def set_best_friend(self, entity_id: Optional[str]) -> None:
        """Set the Qube's best friend."""
        rels = self.state.setdefault("relationships", {})
        rels["best_friend"] = entity_id
        self._save()

    # =========================================================================
    # FINANCIAL SECTION
    # =========================================================================

    def update_wallet_balance(self, balance: int, address: str = None) -> None:
        """Update wallet balance."""
        financial = self.state.setdefault("financial", {})
        wallet = financial.setdefault("wallet", {"address": None, "balance": 0, "balance_updated": 0})

        wallet["balance"] = balance
        wallet["balance_updated"] = int(time.time())
        if address:
            wallet["address"] = address

        self._save()

    def get_wallet_balance(self) -> int:
        return self.state.get("financial", {}).get("wallet", {}).get("balance", 0)

    def get_wallet_address(self) -> Optional[str]:
        return self.state.get("financial", {}).get("wallet", {}).get("address")

    def add_transaction(self, tx: Dict[str, Any]) -> None:
        """Add a transaction to history (capped at MAX_TRANSACTION_HISTORY)."""
        financial = self.state.setdefault("financial", {})
        txns = financial.setdefault("transactions", {
            "total_count": 0, "total_sent": 0, "total_received": 0,
            "total_fees": 0, "archived_count": 0, "history": []
        })

        # Update totals
        txns["total_count"] = txns.get("total_count", 0) + 1
        amount = tx.get("amount", 0)
        if amount < 0:
            txns["total_sent"] = txns.get("total_sent", 0) + abs(amount)
        else:
            txns["total_received"] = txns.get("total_received", 0) + amount
        txns["total_fees"] = txns.get("total_fees", 0) + tx.get("fee", 0)

        # Add to history
        history = txns.setdefault("history", [])
        history.insert(0, tx)

        # Cap history
        if len(history) > MAX_TRANSACTION_HISTORY:
            archived = len(history) - MAX_TRANSACTION_HISTORY
            txns["archived_count"] = txns.get("archived_count", 0) + archived
            txns["history"] = history[:MAX_TRANSACTION_HISTORY]

        self._save()

    def get_transaction_history(self) -> List[Dict[str, Any]]:
        return self.state.get("financial", {}).get("transactions", {}).get("history", [])

    # =========================================================================
    # MOOD SECTION
    # =========================================================================

    def update_mood(self, mood: str, energy: float = None, valence: float = None, arousal: float = None) -> None:
        """Update emotional state."""
        mood_section = self.state.setdefault("mood", {
            "current": "neutral", "energy": 0.5, "valence": 0.5, "arousal": 0.5,
            "updated_at": 0, "history": []
        })

        old_mood = mood_section.get("current")
        mood_section["current"] = mood
        if energy is not None:
            mood_section["energy"] = energy
        if valence is not None:
            mood_section["valence"] = valence
        if arousal is not None:
            mood_section["arousal"] = arousal
        mood_section["updated_at"] = int(time.time())

        # Add to history if mood changed
        if old_mood != mood:
            history = mood_section.setdefault("history", [])
            history.insert(0, {"mood": mood, "timestamp": int(time.time())})
            mood_section["history"] = history[:MAX_MOOD_HISTORY]

        self._save()

    def get_mood(self) -> Dict[str, Any]:
        return self.state.get("mood", {}).copy()

    # =========================================================================
    # HEALTH SECTION
    # =========================================================================

    def update_health(self, chain_verified: bool = None, merkle_valid: bool = None, error: str = None) -> None:
        """Update health status."""
        health = self.state.setdefault("health", {})

        if chain_verified is not None:
            health["chain_verified"] = chain_verified
        if merkle_valid is not None:
            health["merkle_valid"] = merkle_valid
        if error:
            health["errors_count"] = health.get("errors_count", 0) + 1
            health["last_error"] = error
            health["last_error_at"] = int(time.time())

        health["last_integrity_check"] = int(time.time())
        self._save()

    def record_backup(self, is_ipfs: bool = False) -> None:
        """Record that a backup was made."""
        health = self.state.setdefault("health", {})
        now = int(time.time())
        health["last_backup"] = now
        if is_ipfs:
            health["last_ipfs_backup"] = now
        self._save()

    # =========================================================================
    # ATTESTATION SECTION
    # =========================================================================

    def record_attestation(self, signature: str) -> None:
        """Record a runtime attestation."""
        att = self.state.setdefault("attestation", {"last_signed_at": None, "last_signature": None, "count": 0})
        att["last_signed_at"] = int(time.time())
        att["last_signature"] = signature
        att["count"] = att.get("count", 0) + 1
        self._save()

    def get_last_attestation(self) -> Dict[str, Any]:
        return self.state.get("attestation", {}).copy()

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    def get_state(self) -> Dict[str, Any]:
        """Get full state (for debugging)."""
        return self.state.copy()

    def get_ipfs_snapshot(self) -> Dict[str, Any]:
        """Get state snapshot for IPFS anchoring (excludes ephemeral sections)."""
        snapshot = {}
        for key, value in self.state.items():
            if key not in IPFS_EXCLUDED_SECTIONS:
                snapshot[key] = value
        return snapshot

    def verify_integrity(self) -> bool:
        """Verify chain_state integrity."""
        try:
            required = ["version", "qube_id", "chain", "session", "settings"]
            if not all(k in self.state for k in required):
                return False
            if self.state.get("qube_id") != self.qube_id:
                return False
            return True
        except Exception:
            return False

    def recover_from_backup(self) -> bool:
        """Attempt recovery from backup file."""
        if self.backup_file.exists():
            try:
                shutil.copy2(self.backup_file, self.state_file)
                self._load()
                logger.info("chain_state_recovered_from_backup", qube_id=self.qube_id)
                return True
            except Exception as e:
                logger.error("chain_state_recovery_failed", error=str(e))
        return False
```

---

### Section 3: RelationshipStorage Migration

The `RelationshipStorage` class currently manages its own file. After migration, it becomes a thin wrapper around `ChainState`.

**Key Changes:**
- Constructor takes `ChainState` instead of `data_dir`
- No more direct file I/O - delegates to `ChainState`
- `Relationship` class (data model) stays unchanged
- In-memory cache remains for performance

```python
# relationships/relationship.py - MIGRATED VERSION

# The Relationship class stays UNCHANGED - it's just a data model
# Only RelationshipStorage changes

class RelationshipStorage:
    """
    Manages relationships for a Qube using ChainState as backend.

    MIGRATED: No longer uses relationships/relationships.json directly.
    All persistence is through chain_state.json via ChainState class.
    """

    def __init__(self, chain_state: 'ChainState'):
        """
        Initialize relationship storage.

        Args:
            chain_state: ChainState instance for persistence
        """
        self.chain_state = chain_state

        # In-memory cache of Relationship objects
        self.relationships: Dict[str, Relationship] = {}

        # Load from chain_state
        self._load_relationships()

        logger.info(
            "relationship_storage_initialized",
            qube_id=chain_state.qube_id,
            relationship_count=len(self.relationships)
        )

    def _load_relationships(self) -> None:
        """Load relationships from chain_state and apply decay."""
        # Get raw data from chain_state
        entities_data = self.chain_state.get_all_relationships()

        if not entities_data:
            logger.debug("no_existing_relationships")
            return

        decayed_count = 0
        for entity_id, rel_data in entities_data.items():
            rel = Relationship.from_dict(rel_data)

            # Apply decay for inactive relationships
            if rel.apply_decay():
                decayed_count += 1

            # Update days_known to current
            rel.update_days_known()

            self.relationships[entity_id] = rel

        logger.debug(
            "relationships_loaded",
            count=len(self.relationships),
            decayed_count=decayed_count
        )

        # Save if any relationships decayed
        if decayed_count > 0:
            self.save()
            logger.info("relationship_decay_saved", decayed_count=decayed_count)

    def save(self) -> None:
        """Save all relationships to chain_state."""
        for entity_id, rel in self.relationships.items():
            # Cap history arrays before saving
            rel_data = rel.to_dict()

            # Cap evaluations
            if "evaluations" in rel_data and len(rel_data["evaluations"]) > MAX_RELATIONSHIP_EVALUATIONS:
                rel_data["evaluations"] = rel_data["evaluations"][:MAX_RELATIONSHIP_EVALUATIONS]

            # Cap progression_history
            if "progression_history" in rel_data and len(rel_data["progression_history"]) > MAX_RELATIONSHIP_PROGRESSION:
                rel_data["progression_history"] = rel_data["progression_history"][:MAX_RELATIONSHIP_PROGRESSION]

            self.chain_state.set_relationship(entity_id, rel_data)

        logger.debug("relationships_saved", count=len(self.relationships))

    def get_relationship(self, entity_id: str) -> Optional[Relationship]:
        """Get relationship by entity ID."""
        return self.relationships.get(entity_id)

    def create_relationship(
        self,
        entity_id: str,
        entity_type: str = "qube",
        **kwargs
    ) -> Relationship:
        """Create a new relationship."""
        if entity_id in self.relationships:
            logger.warning("relationship_already_exists", entity_id=entity_id)
            return self.relationships[entity_id]

        rel = Relationship(entity_id, entity_type, **kwargs)
        self.relationships[entity_id] = rel

        # Save to chain_state
        self.chain_state.set_relationship(entity_id, rel.to_dict())

        return rel

    def update_relationship(self, relationship: Relationship) -> None:
        """Update existing relationship and save."""
        self.relationships[relationship.entity_id] = relationship
        self.chain_state.set_relationship(relationship.entity_id, relationship.to_dict())

    def get_all_relationships(self) -> List[Relationship]:
        """Get all relationships."""
        return list(self.relationships.values())

    def get_relationships_by_status(self, status: str) -> List[Relationship]:
        """Get all relationships with specific status."""
        return [rel for rel in self.relationships.values() if rel.status == status]

    def get_best_friend(self) -> Optional[Relationship]:
        """Get best friend relationship (only one allowed)."""
        for rel in self.relationships.values():
            if rel.is_best_friend:
                return rel
        return None

    def set_best_friend(self, entity_id: str) -> bool:
        """Set an entity as best friend."""
        if entity_id not in self.relationships:
            return False

        # Clear any existing best friend
        for rel in self.relationships.values():
            if rel.is_best_friend and rel.entity_id != entity_id:
                rel.is_best_friend = False
                self.chain_state.set_relationship(rel.entity_id, rel.to_dict())

        # Set new best friend
        self.relationships[entity_id].is_best_friend = True
        self.chain_state.set_relationship(entity_id, self.relationships[entity_id].to_dict())
        self.chain_state.set_best_friend(entity_id)

        return True

    def delete_relationship(self, entity_id: str) -> bool:
        """Delete a relationship."""
        if entity_id in self.relationships:
            del self.relationships[entity_id]

            # Remove from chain_state
            rels = self.chain_state.state.get("relationships", {})
            entities = rels.get("entities", {})
            if entity_id in entities:
                del entities[entity_id]
                rels["total_known"] = len(entities)
                self.chain_state._save()

            logger.info("relationship_deleted", entity_id=entity_id)
            return True
        return False

    def set_owner(self, owner_id: str) -> None:
        """Set the Qube's owner."""
        self.chain_state.set_owner(owner_id)
```

**Initialization Change in Qube:**

```python
# OLD (in core/qube.py)
self.relationship_storage = RelationshipStorage(self.data_dir)

# NEW
self.relationship_storage = RelationshipStorage(self.chain_state)
```

**Migration Notes:**

1. The `Relationship` class is UNCHANGED - it's a pure data model
2. `SocialDynamicsManager` uses `RelationshipStorage`, so it inherits the changes automatically
3. The `relationships/` directory can be removed after migration (or kept as backup)
4. Array caps are applied when saving to prevent unbounded growth

---

### Section 4: SkillsManager Migration

The `SkillsManager` is more complex because it manages two things:
1. **Skill tree definitions** (all 112 skills) - STAYS in `skills.json` (game data)
2. **Qube's progress** (XP, levels, unlocked) - MOVES to `chain_state.skills`

**Key Changes:**
- Constructor takes `ChainState` in addition to `qube_dir`
- Skill definitions loaded from `skills.json` (read-only)
- Progress (unlocked skills, XP, history) stored in `chain_state.skills`
- Methods merge definitions with progress when presenting data

```python
# utils/skills_manager.py - MIGRATED VERSION

"""
Skills Manager - Handles skill progression, XP tracking, and unlocking for Qubes

MIGRATED: Skill progress is now stored in chain_state.json
- skills.json: Skill tree DEFINITIONS (read-only game data, all 112 skills)
- chain_state.skills: Qube's PROGRESS (unlocked skills, XP, history)
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)

# Constants
MAX_SKILL_HISTORY = 100


class SkillsManager:
    """
    Manages skill progression using ChainState as backend for progress.

    MIGRATED: Skill definitions stay in skills.json, progress goes to chain_state.
    """

    def __init__(self, qube_dir: Path, chain_state: 'ChainState'):
        """
        Initialize SkillsManager.

        Args:
            qube_dir: Path to qube's data directory (for skill definitions)
            chain_state: ChainState instance for progress persistence
        """
        self.qube_dir = qube_dir
        self.chain_state = chain_state
        self.skills_dir = qube_dir / "skills"
        self.skills_file = self.skills_dir / "skills.json"

        # Ensure skills directory exists
        self.skills_dir.mkdir(exist_ok=True)

        # Load skill definitions (the full tree - game data)
        self._skill_definitions: Dict[str, Dict] = {}
        self._load_skill_definitions()

    def _load_skill_definitions(self) -> None:
        """Load skill tree definitions from skills.json (game data, read-only)."""
        if not self.skills_file.exists():
            # Initialize default skill definitions
            self._initialize_skill_definitions()
            return

        try:
            with open(self.skills_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Index by skill ID for fast lookup
            for skill in data.get("skills", []):
                self._skill_definitions[skill["id"]] = skill

            logger.debug(f"Loaded {len(self._skill_definitions)} skill definitions")

        except Exception as e:
            logger.error(f"Failed to load skill definitions: {e}")
            self._initialize_skill_definitions()

    def _initialize_skill_definitions(self) -> None:
        """Initialize default skill definitions file."""
        from utils.skill_definitions import generate_all_skills

        skills = generate_all_skills()
        data = {
            "last_updated": datetime.utcnow().isoformat() + "Z",
            "skills": skills
        }

        # Save to file
        with open(self.skills_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # Index by ID
        for skill in skills:
            self._skill_definitions[skill["id"]] = skill

        logger.info(f"Initialized {len(skills)} skill definitions")

    def get_skill_definition(self, skill_id: str) -> Optional[Dict]:
        """Get a skill definition by ID."""
        return self._skill_definitions.get(skill_id)

    def get_all_skill_definitions(self) -> List[Dict]:
        """Get all skill definitions."""
        return list(self._skill_definitions.values())

    # =========================================================================
    # PROGRESS METHODS (use chain_state)
    # =========================================================================

    def get_unlocked_skills(self) -> List[Dict[str, Any]]:
        """Get all unlocked skills with their progress."""
        return self.chain_state.get_unlocked_skills()

    def is_skill_unlocked(self, skill_id: str) -> bool:
        """Check if a skill is unlocked."""
        unlocked = self.chain_state.get_unlocked_skills()
        return any(s["id"] == skill_id for s in unlocked)

    def get_skill_progress(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """Get progress for a specific skill."""
        unlocked = self.chain_state.get_unlocked_skills()
        for skill in unlocked:
            if skill["id"] == skill_id:
                return skill
        return None

    def unlock_skill(self, skill_id: str) -> Dict[str, Any]:
        """
        Unlock a skill (check prerequisites first).

        Returns:
            Dictionary with result
        """
        # Check if already unlocked
        if self.is_skill_unlocked(skill_id):
            return {"success": False, "error": f"Skill {skill_id} is already unlocked"}

        # Get skill definition
        definition = self.get_skill_definition(skill_id)
        if not definition:
            return {"success": False, "error": f"Skill {skill_id} not found"}

        # Check prerequisite
        prereq_id = definition.get("prerequisite")
        if prereq_id and not self.is_skill_unlocked(prereq_id):
            return {"success": False, "error": f"Prerequisite skill {prereq_id} must be unlocked first"}

        # Create unlocked skill entry
        unlocked_skill = {
            "id": skill_id,
            "name": definition.get("name", skill_id),
            "branch": definition.get("category", "unknown"),
            "tier": definition.get("skillType", "planet"),  # sun/planet/moon
            "level": 0,
            "xp": 0,
            "max_xp": definition.get("maxXP", 500),
            "unlocked_at": int(datetime.utcnow().timestamp())
        }

        # Add to chain_state
        self.chain_state.add_unlocked_skill(unlocked_skill)

        # Log event to history
        self.chain_state.update_skill_xp(skill_id, 0, f"Skill unlocked")

        logger.info(f"Unlocked skill: {skill_id}")
        return {"success": True, "skill_id": skill_id}

    def add_xp(
        self,
        skill_id: str,
        xp_amount: int,
        reason: str = None,
        evidence_block_id: str = None
    ) -> Dict[str, Any]:
        """
        Add XP to a skill.

        If skill is locked, XP flows to unlocked parent.

        Args:
            skill_id: ID of skill to add XP to
            xp_amount: Amount of XP to add
            reason: Why XP was gained
            evidence_block_id: Block that triggered this

        Returns:
            Dictionary with result including level_up status
        """
        # Get skill definition
        definition = self.get_skill_definition(skill_id)
        if not definition:
            return {"success": False, "error": f"Skill {skill_id} not found"}

        # If skill is locked, flow to parent
        target_skill_id = skill_id
        xp_flowed = False

        if not self.is_skill_unlocked(skill_id):
            # Try parent
            parent_id = definition.get("parentSkill")
            if parent_id and self.is_skill_unlocked(parent_id):
                target_skill_id = parent_id
                xp_flowed = True
            elif parent_id:
                # Try grandparent (sun - should always be unlocked)
                parent_def = self.get_skill_definition(parent_id)
                if parent_def:
                    grandparent_id = parent_def.get("parentSkill")
                    if grandparent_id and self.is_skill_unlocked(grandparent_id):
                        target_skill_id = grandparent_id
                        xp_flowed = True

            if not xp_flowed:
                # No unlocked parent found - auto-unlock the sun skill
                sun_id = self._get_sun_skill_id(skill_id)
                if sun_id and not self.is_skill_unlocked(sun_id):
                    self.unlock_skill(sun_id)
                target_skill_id = sun_id
                xp_flowed = True

        # Get current progress
        progress = self.get_skill_progress(target_skill_id)
        if not progress:
            return {"success": False, "error": f"Skill {target_skill_id} not unlocked"}

        # Calculate new XP and level
        old_xp = progress["xp"]
        old_level = progress["level"]
        new_xp = old_xp + xp_amount
        max_xp = progress.get("max_xp", 500)
        new_level = old_level
        leveled_up = False
        levels_gained = 0

        # Level up logic
        while new_xp >= max_xp and new_level < 100:
            new_xp -= max_xp
            new_level += 1
            levels_gained += 1
            leveled_up = True

        # Cap at max level
        if new_level >= 100:
            new_level = 100
            new_xp = max_xp

        # Update in chain_state
        full_reason = reason or f"XP gained"
        if xp_flowed and skill_id != target_skill_id:
            full_reason = f"{full_reason} (from locked skill {skill_id})"

        self.chain_state.update_skill_xp(target_skill_id, xp_amount, full_reason)

        # Update the unlocked skill entry directly
        unlocked_skills = self.chain_state.get_unlocked_skills()
        for skill in unlocked_skills:
            if skill["id"] == target_skill_id:
                skill["xp"] = new_xp
                skill["level"] = new_level
                break
        self.chain_state.state["skills"]["unlocked"] = unlocked_skills
        self.chain_state._save()

        result = {
            "success": True,
            "skill_id": target_skill_id,
            "old_level": old_level,
            "new_level": new_level,
            "xp_gained": xp_amount,
            "current_xp": new_xp,
            "max_xp": max_xp,
            "leveled_up": leveled_up,
            "levels_gained": levels_gained
        }

        if xp_flowed:
            result["original_skill_id"] = skill_id
            result["xp_flowed_to_parent"] = True

        # Check if skill is now maxed and should unlock a tool
        if new_level == 100:
            tool_reward = self.get_skill_definition(target_skill_id).get("toolCallReward")
            if tool_reward:
                result["tool_unlocked"] = tool_reward
                logger.info(f"Skill {target_skill_id} maxed! Unlocked tool: {tool_reward}")

        return result

    def _get_sun_skill_id(self, skill_id: str) -> Optional[str]:
        """Get the sun (root) skill for any skill."""
        definition = self.get_skill_definition(skill_id)
        if not definition:
            return None

        # If this is a sun, return it
        if definition.get("skillType") == "sun":
            return skill_id

        # Otherwise, traverse up to find sun
        parent_id = definition.get("parentSkill")
        while parent_id:
            parent_def = self.get_skill_definition(parent_id)
            if not parent_def:
                break
            if parent_def.get("skillType") == "sun":
                return parent_id
            parent_id = parent_def.get("parentSkill")

        return None

    def get_skill_summary(self) -> Dict[str, Any]:
        """Get a summary of skill progress."""
        unlocked = self.get_unlocked_skills()
        total_xp = self.chain_state.get_total_xp()

        maxed_skills = [s for s in unlocked if s.get("level", 0) == 100]
        unlocked_tools = []
        for skill in maxed_skills:
            definition = self.get_skill_definition(skill["id"])
            if definition and definition.get("toolCallReward"):
                unlocked_tools.append(definition["toolCallReward"])

        return {
            "total_skills": len(self._skill_definitions),
            "unlocked_skills": len(unlocked),
            "maxed_skills": len(maxed_skills),
            "total_xp": total_xp,
            "unlocked_tools": unlocked_tools
        }

    def load_skills(self) -> Dict[str, Any]:
        """
        Load skills with merged definitions and progress.

        COMPATIBILITY: Returns format similar to old skills.json for existing code.
        """
        # Get progress from chain_state
        unlocked = {s["id"]: s for s in self.get_unlocked_skills()}

        # Merge with definitions
        skills = []
        for skill_id, definition in self._skill_definitions.items():
            skill = definition.copy()
            if skill_id in unlocked:
                # Merge progress
                progress = unlocked[skill_id]
                skill["unlocked"] = True
                skill["level"] = progress.get("level", 0)
                skill["xp"] = progress.get("xp", 0)
            else:
                skill["unlocked"] = False
                skill["level"] = 0
                skill["xp"] = 0

            skills.append(skill)

        return {
            "last_updated": datetime.utcnow().isoformat() + "Z",
            "skills": skills
        }
```

**Initialization Change in Qube:**

```python
# OLD (in core/qube.py)
self.skills_manager = SkillsManager(self.data_dir)

# NEW
self.skills_manager = SkillsManager(self.data_dir, self.chain_state)
```

**Migration Notes:**

1. `skills.json` stays as the skill tree definition (all 112 skills, read-only)
2. Progress (unlocked, XP, levels) moves to `chain_state.skills`
3. `load_skills()` method preserved for compatibility - merges definitions + progress
4. History moves to `chain_state.skills.history` (capped at 100)
5. Sun skills auto-unlock when needed (they're always the first unlocked in a category)

---

## Files to Consolidate

| Current File | Target Location | Migration Notes |
|-------------|-----------------|-----------------|
| `chain_state.json` | `chain`, `session`, `settings`, `runtime`, `stats`, `health` | Restructure existing data |
| `skills/skill_history.json` | `skills.history[]` | Move history array (capped at 100 entries) |
| `relationships/relationships.json` | `relationships.entities{}` | Move entity map |
| `balance_cache.json` | `financial.wallet` | Move balance data |
| `transaction_history.json` | `financial.transactions.history[]` | Move transaction array (capped at 50 entries) |

## Files to Keep Separate

| File | Reason |
|------|--------|
| `chain/genesis.json` | Immutable identity document |
| `chain/qube_metadata.json` | Contains encrypted private key |
| `chain/nft_metadata.json` | NFT-specific metadata |
| `blocks/permanent/*.json` | Individual block files |
| `blocks/session/*.json` | Session block files |
| `skills/skills.json` | Full skill tree definition (game data, not Qube state). Accessed via `get_skills` tool. Only **unlocked** skills stored in chain_state. |

---

## Affected Areas (Full Scope)

This consolidation touches more than just file storage. Here's the complete impact:

### 1. Qube Genesis / Creation

**File:** `core/qube.py` - `create_new()` and `__init__()`

Currently at genesis:
- Creates `chain/chain_state.json` with basic chain tracking
- Creates `relationships/` directory (file is lazy-loaded later)
- Creates `skills/` directory (file is lazy-loaded later)
- Does NOT initialize financial, mood, health sections

**After consolidation:**
- Create `chain/chain_state.json` with v2.0 schema
- Pre-initialize ALL sections: chain, session, settings, runtime, stats, skills, relationships, financial, mood, health, attestation
- No need to create `relationships/` or `skills/` directories for state (only keep `skills.json` as skill tree definition)

```python
# New genesis initialization in ChainState
def _initialize_new_qube(self) -> Dict[str, Any]:
    """Initialize chain_state for a brand new Qube"""
    return {
        "version": "2.0",
        "qube_id": self.qube_id,
        "last_updated": int(time.time()),
        "chain": { ... },
        "session": { ... },
        "settings": { ... },
        "runtime": { ... },
        "stats": { ... },
        "skills": {"total_xp": 0, "total_unlocked": 0, "unlocked": [], "history": []},
        "relationships": {"entities": {}, "total_entities_known": 0, "best_friend": None, "owner": None},
        "financial": {"wallet": {}, "transactions": {"total_count": 0, "history": []}},
        "mood": {"current": "neutral", "energy": 0.5, "valence": 0.5},
        "health": {"chain_verified": True, "errors_encountered": 0},
        "attestation": {"last_signed": None, "attestation_count": 0}
    }
```

### 2. Classes That Need Refactoring

| Class | File | Current Behavior | New Behavior |
|-------|------|------------------|--------------|
| `ChainState` | `core/chain_state.py` | Flat structure, basic tracking | Namespaced v2.0 structure with all sections |
| `SkillsManager` | `utils/skills_manager.py` | Reads/writes `skills/skills.json` | Writes unlocked skills to `chain_state.skills`, reads skill tree from `skills.json` |
| `RelationshipStorage` | `relationships/relationship.py` | Reads/writes `relationships/relationships.json` | Reads/writes `chain_state.relationships` |
| `SocialDynamicsManager` | `relationships/relationship.py` | Uses RelationshipStorage | Uses ChainState for persistence |
| `WalletManager` | `wallets/wallet_manager.py` | Reads/writes `balance_cache.json`, `transaction_history.json` | Reads/writes `chain_state.financial` |
| `Reasoner` | `ai/reasoner.py` | Updates stats scattered in chain_state | Updates `chain_state.stats`, `chain_state.mood` |

### 3. GUI Bridge Changes

**File:** `gui_bridge.py`

The GUI reads/writes chain_state directly for:
- Model settings (revolver mode, locked model, etc.)
- Auto-anchor settings
- Avatar description

All these access patterns need updating to use namespaced paths:
```python
# Old
chain_state["revolver_mode_enabled"]

# New
chain_state["settings"]["model_mode"]["mode"] == "revolver"
```

### 4. Import/Export Flow (Package Format)

**Files:** `blockchain/chain_package.py`, `blockchain/chain_sync.py`

Current `QubePackageData` structure has **separate fields**:
```python
@dataclass
class QubePackageData:
    genesis_block: Dict[str, Any]
    memory_blocks: List[Dict[str, Any]]
    chain_state: Dict[str, Any]
    relationships: Optional[Dict[str, Any]] = None  # Separate!
    skills: Optional[Dict[str, Any]] = None          # Separate!
    skill_history: Optional[List[Dict[str, Any]]] = None
    avatar_data: Optional[str] = None
    nft_metadata: Optional[Dict[str, Any]] = None
```

**Recommended approach: Keep package format as stable interchange format**

The package is used for:
- IPFS backup/sync
- Transfer to new owner
- Recovery from NFT

**When PACKING (creating package):**
```python
def _collect_qube_data(...) -> QubePackageData:
    # Load consolidated chain_state
    chain_state = load_chain_state(qube_dir)

    # Extract for package (keep interchange format stable)
    return QubePackageData(
        chain_state=chain_state,  # Full v2 structure
        # Also include broken out for backward compat with old systems
        relationships=chain_state.get("relationships", {}).get("entities"),
        skills=extract_unlocked_skills_for_package(chain_state),
        skill_history=chain_state.get("skills", {}).get("history"),
        ...
    )
```

**When UNPACKING (restoring package):**
```python
def restore_qube_from_package(package_data, target_dir, ...):
    # Check if chain_state is v2 (consolidated)
    if package_data.chain_state.get("version") == "2.0":
        # Already consolidated, use directly
        save_chain_state(package_data.chain_state)
    else:
        # Old v1 package - consolidate on import
        consolidated = migrate_to_v2(
            chain_state=package_data.chain_state,
            relationships=package_data.relationships,
            skills=package_data.skills,
            skill_history=package_data.skill_history
        )
        save_chain_state(consolidated)
```

**Package version handling:**
- Keep `PACKAGE_VERSION = 1` for now (format is stable)
- Add `chain_state.version = "2.0"` to indicate internal structure
- Restore logic checks `chain_state.version` to decide how to handle

### 5. IPFS Anchoring

**File:** `storage/ipfs_backup.py`

What gets anchored to IPFS:
- INCLUDE: chain, session, settings, stats, skills, relationships, financial, mood, health
- EXCLUDE: runtime (ephemeral), attestation (generated on-demand)

### 6. Tool Access Patterns

**Files:** `ai/tools/handlers.py`, `ai/tools/introspection.py`

Tools that read Qube state need updating:
- `get_my_stats` - reads from `chain_state.stats`
- `get_my_relationships` - reads from `chain_state.relationships`
- `verify_my_runtime` (new) - reads entire chain_state, signs attestation

### 7. Tests

**Files:** `tests/unit/test_storage_recovery.py`, `tests/integration/test_phase1_complete.py`

All tests that mock or verify chain_state structure need updating.

---

## Implementation Plan

### Phase 1: Schema Update (Non-Breaking)

1. **Add version field** to chain_state.json
2. **Add new namespaced sections** (`chain`, `session`, `settings`, etc.)
3. **Keep old flat fields** for backward compatibility
4. **Update ChainState class** to read from both old and new locations

### Phase 2: Migration Script

1. **Create migration script** that:
   - Reads existing chain_state.json
   - Reads skills.json, relationships.json, balance_cache.json, transaction_history.json
   - Consolidates into new structure
   - Writes updated chain_state.json
   - Optionally archives old files

2. **Run migration** for all existing Qubes

### Phase 3: Code Updates

1. **Update ChainState class**:
   - New methods for each section
   - Backward-compatible getters
   - New setters that write to correct location

2. **Update SkillScanner**:
   - Read/write from `chain_state.skills` instead of separate file
   - Remove skills.json file operations

3. **Update RelationshipManager**:
   - Read/write from `chain_state.relationships` instead of separate file
   - Remove relationships.json file operations

4. **Update WalletManager**:
   - Read/write from `chain_state.financial` instead of separate files
   - Remove balance_cache.json and transaction_history.json operations

5. **Update Reasoner**:
   - Read mood from `chain_state.mood`
   - Update stats in `chain_state.stats`

### Phase 4: verify_my_runtime Tool

1. **Create new tool** `verify_my_runtime`:
   ```python
   def verify_my_runtime(self) -> dict:
       """
       Generate a cryptographically signed attestation of current runtime state.

       Returns signed payload containing:
       - Current model (from actual runtime)
       - Qube ID and name
       - Mode settings (revolver/manual/autonomous)
       - Session info
       - Timestamp
       - Signature (using Qube's private key)
       """
   ```

2. **Tool reads from chain_state** (which is authoritative)
3. **Signs payload** with Qube's private key
4. **Returns attestation** that AI can trust

### Phase 5: IPFS Anchoring

1. **Add anchor_to_ipfs method**:
   - Snapshot relevant chain_state sections
   - Exclude ephemeral `runtime` section
   - Hash and pin to IPFS
   - Store CID in `chain.last_ipfs_anchor_cid`

2. **Optionally anchor hash to Bitcoin Cash** via OP_RETURN

---

## Code Changes Required

### Files to Modify

```
core/chain_state.py          # Major refactor - new namespaced structure
core/qube.py                  # Update to use new chain_state structure
ai/reasoner.py                # Update stats tracking, mood
ai/skill_scanner.py           # Write unlocked skills to chain_state.skills (keep skills.json as definition)
ai/tools/introspection.py     # Add verify_my_runtime tool
ai/tools/registry.py          # Register new tool
core/relationships.py         # Migrate to chain_state.relationships
wallets/wallet_manager.py     # Migrate to chain_state.financial
gui_bridge.py                 # Update all chain_state access patterns
```

### New Files

```
scripts/migrate_chain_state.py   # Migration script
ai/tools/verify_runtime.py       # verify_my_runtime tool implementation
```

### Constants to Add

```python
# In core/chain_state.py or core/constants.py
MAX_TRANSACTION_HISTORY = 50      # Keep last 50 transactions
MAX_SKILL_HISTORY = 100           # Keep last 100 XP events
MAX_RELATIONSHIP_EVALUATIONS = 50 # Keep last 50 evaluations per entity
MAX_MOOD_HISTORY = 20             # Keep last 20 mood changes
```

---

## Backward Compatibility

### Read Compatibility

```python
def get_chain_length(self) -> int:
    # Try new location first
    if "chain" in self.state:
        return self.state["chain"].get("length", 0)
    # Fall back to old location
    return self.state.get("chain_length", 0)
```

### Write Compatibility

```python
def set_chain_length(self, length: int):
    # Write to new location
    if "chain" not in self.state:
        self.state["chain"] = {}
    self.state["chain"]["length"] = length
    # Also write to old location during transition
    self.state["chain_length"] = length
```

---

## Testing Plan

1. **Unit tests** for new ChainState methods
2. **Migration test** on copy of real Qube data
3. **Integration tests** ensuring all features work with new structure
4. **Verify tool test** confirming signature verification works

---

## Backup & Integrity Strategy

### Atomic Writes (Corruption Prevention)

Never write directly to `chain_state.json`. Always use atomic write pattern:

```python
def _save(self) -> None:
    """Save state using atomic write to prevent corruption."""
    temp_file = self.state_file.with_suffix('.json.tmp')
    backup_file = self.state_file.with_suffix('.json.bak')

    # 1. Write to temp file first
    temp_file.write_text(json.dumps(self.state, indent=2))

    # 2. Backup current file (if exists)
    if self.state_file.exists():
        shutil.copy2(self.state_file, backup_file)

    # 3. Atomic rename temp -> actual (this is atomic on most filesystems)
    temp_file.replace(self.state_file)
```

### Backup Strategy

```
chain_state.json      # Current state
chain_state.json.bak  # Previous state (auto-backup on every save)
chain_state.json.{timestamp}.bak  # Periodic snapshots (hourly/daily)
```

**Auto-backup triggers:**
- Before every write (`.bak` file)
- Before migration runs
- Before IPFS anchor (snapshot with timestamp)
- On application startup (if last backup > 1 hour old)

### Integrity Checks

```python
def verify_integrity(self) -> bool:
    """Verify chain_state hasn't been corrupted."""
    try:
        # 1. JSON is valid
        data = json.loads(self.state_file.read_text())

        # 2. Required fields exist
        required = ["version", "qube_id", "chain", "session"]
        if not all(k in data for k in required):
            return False

        # 3. Qube ID matches expected
        if data["qube_id"] != self.qube_id:
            return False

        return True
    except (json.JSONDecodeError, IOError):
        return False

def recover_from_backup(self) -> bool:
    """Attempt to recover from backup if main file is corrupted."""
    backup_file = self.state_file.with_suffix('.json.bak')
    if backup_file.exists():
        shutil.copy2(backup_file, self.state_file)
        self._load()
        return True
    return False
```

### Health Section in chain_state

```json
"health": {
  "last_integrity_check": 1768547682,
  "chain_verified": true,
  "last_backup": 1768547000,
  "last_backup_path": "chain_state.json.1768547000.bak",
  "backup_count": 24,
  "errors_encountered": 0,
  "last_error": null,
  "warnings": []
}
```

---

## Rollback Plan

1. **Automatic `.bak` file** on every save - instant rollback available
2. **Timestamped backups** for point-in-time recovery
3. **Version field** allows detecting old vs new format
4. **Backward-compatible reads** mean old code can still work
5. **Integrity check on startup** - auto-recover from backup if corrupted

---

## Open Questions

1. **Should mood be AI-generated?** Or calculated from interaction patterns?
2. **How often to snapshot to IPFS?** On every anchor? Periodically?
3. **Should chain_state.json be encrypted?**
   - Currently: Plain JSON (not encrypted)
   - Block files: Encrypted
   - Concern: chain_state will now hold relationships (trust scores, interaction history) and financial data (wallet address, transaction history)
   - Options:
     - A) Keep plain (easier debugging, human-readable)
     - B) Encrypt entire file (consistent with blocks, but harder to debug)
     - C) Encrypt only sensitive sections (relationships, financial)

## Resolved Decisions

1. **Skills**: Only **unlocked** skills stored in chain_state. Full skill tree (112+ skills) stays in `skills.json` as game data, accessed via `get_skills` tool.
2. **Transaction history**: Capped at 50 recent transactions. Older ones archived, totals preserved.
3. **Skill history**: Capped at 100 recent XP events.
4. **Full consolidation**: No hybrid/reference approach - Qube needs full context in one read for self-awareness.

---

## Timeline Estimate

- Phase 1: Schema Update - 1-2 hours
- Phase 2: Migration Script - 2-3 hours
- Phase 3: Code Updates - 4-6 hours
- Phase 4: verify_my_runtime Tool - 2-3 hours
- Phase 5: IPFS Anchoring - 3-4 hours

**Total: ~15-20 hours of implementation work**

---

## Notes

- This blueprint is a living document - update as we refine the approach
- The consolidation should be done incrementally to minimize risk
- Keep the user informed of progress and get approval before major changes

---

## Codebase Alignment Analysis

Comparison of blueprint against actual codebase to identify gaps and potential issues.

### Current Access Patterns

| Component | Class/File | Current Storage | Access Pattern |
|-----------|------------|-----------------|----------------|
| Chain State | `ChainState` (`core/chain_state.py`) | `chain/chain_state.json` | Class with methods, GUI_MANAGED_FIELDS |
| Relationships | `RelationshipStorage` (`relationships/relationship.py`) | `relationships/relationships.json` | Class with save/load methods |
| Skills | `SkillsManager` (`utils/skills_manager.py`) | `skills/skills.json`, `skills/skill_history.json` | Class with save/load methods |
| Financial | `WalletTxManager` (`blockchain/wallet_tx.py`) | `balance_cache.json`, `transaction_history.json` | Class with direct file I/O |
| GUI Settings | `gui_bridge.py` | `chain/chain_state.json` | Direct file read/write via `_load_chain_state`/`_save_chain_state` |

### Key Findings

#### 1. ChainState Already Has Good Patterns ✅

The existing `ChainState` class already implements:
- Atomic writes (temp file + rename)
- File locking (`FileLock`)
- GUI_MANAGED_FIELDS merge pattern
- `reload()` method for external changes

**Blueprint alignment:** Good foundation to build on.

#### 2. GUI Direct File Access ⚠️

`gui_bridge.py` has its own `_load_chain_state()` and `_save_chain_state()` methods:
```python
def _load_chain_state(self, qube_dir: Path) -> Dict[str, Any]:
    chain_state_path = qube_dir / "chain" / "chain_state.json"
    with open(chain_state_path, "r") as f:
        return json.load(f)

def _save_chain_state(self, qube_dir: Path, state: Dict[str, Any]) -> None:
    chain_state_path = qube_dir / "chain" / "chain_state.json"
    with open(chain_state_path, "w") as f:
        json.dump(state, f, indent=2)
```

**Issue:** No file locking, no atomic write, no backup. Risk of corruption.
**Blueprint action needed:** GUI should use same atomic write + backup pattern.

#### 3. RelationshipStorage Saves Full Dict ⚠️

`RelationshipStorage.save()` writes all relationships:
```python
def save(self) -> None:
    data = {entity_id: rel.to_dict() for entity_id, rel in self.relationships.items()}
    with open(self.relationships_file, 'w') as f:
        json.dump(data, f, indent=2)
```

**Issue:** Simple write, no atomic pattern, no backup.
**Migration:** Move to chain_state.relationships, use ChainState's save pattern.

#### 4. SkillsManager Has Similar Pattern ⚠️

```python
def save_skills(self, skills_data: Dict[str, Any]) -> bool:
    with open(self.skills_file, 'w', encoding='utf-8') as f:
        json.dump(skills_data, f, indent=2, ensure_ascii=False)
```

**Issue:** Simple write, no atomic pattern.
**Migration:** For unlocked skills, move to chain_state.skills.

#### 5. WalletTxManager Has Direct File I/O ⚠️

```python
self.balance_cache_file = self.data_dir / "balance_cache.json"
self.tx_history_file = self.data_dir / "transaction_history.json"
```

**Issue:** Direct file writes, no atomic pattern.
**Migration:** Move to chain_state.financial.

#### 6. Skill Scanner Uses SkillsManager ✅

`ai/skill_scanner.py` awards XP during anchoring by calling SkillsManager methods.
**Migration:** Will need to update to write unlocked skills to chain_state.

### Classes That Need Migration

| Class | Current File | Migration Path |
|-------|--------------|----------------|
| `RelationshipStorage` | `relationships/relationship.py` | → Read/write `chain_state.relationships` via ChainState methods |
| `SkillsManager` | `utils/skills_manager.py` | → Write unlocked to `chain_state.skills`, keep skills.json as definition |
| `WalletTxManager` | `blockchain/wallet_tx.py` | → Read/write `chain_state.financial` via ChainState methods |
| `SocialDynamicsManager` | `relationships/relationship.py` | → Uses RelationshipStorage, will inherit changes |

### GUI Bridge Methods That Need Updating

Found ~20 methods in `gui_bridge.py` that directly access chain_state:
- `set_model_lock()` - writes model_locked, model_locked_to
- `set_revolver_mode()` - writes revolver_mode_enabled, revolver_last_index, etc.
- `set_revolver_providers()` - writes revolver_providers
- `set_revolver_models()` - writes revolver_models
- `set_auto_anchor()` - writes auto_anchor_enabled, auto_anchor_threshold
- `get_model_mode()` - reads model_locked, revolver_mode_enabled
- And more...

**All need updating for v2.0 namespaced paths.**

### Potential Breaking Changes

1. **Skill Tree Split**: Currently `skills.json` has both the tree definition AND the qube's progress. Splitting these means:
   - Need a new global skill definitions file (`utils/skill_definitions.py` already exists!)
   - chain_state.skills only stores unlocked skills with XP

2. **Relationship Structure**: Currently a flat dict of entities. Blueprint proposes:
   ```json
   "relationships": {
     "entities": {...},
     "total_entities_known": 1,
     "best_friend": null,
     "owner": "bit_faced"
   }
   ```
   Need to migrate existing flat structure.

3. **Financial Transactions**: Currently unbounded list. Blueprint proposes cap at 50 with archived_count.

### Missing from Blueprint

1. **Pending Transactions File**: `wallet_tx.py` also writes `pending_transactions.json`:
   ```python
   self.pending_tx_file = self.data_dir / "pending_transactions.json"
   ```
   **Action:** Add to chain_state.financial or keep separate?

2. **Shared Memory Systems**: From `qube.py.__init__`:
   ```python
   self.permission_manager = PermissionManager(permissions_dir)
   self.collaborative_session = CollaborativeSession(sessions_dir)
   self.memory_market = MemoryMarket(market_dir)
   self.shared_cache = SharedMemoryCache(cache_dir)
   ```
   These have their own storage. **Action:** Keep separate (they're inter-qube systems).

3. **Semantic Search Index**: `chain/` directory has semantic search index files.
   **Action:** Keep separate (binary index files, not JSON state).

4. **Avatar Image**: Stored as `{qube_id}_avatar.png` in `chain/` directory.
   **Action:** Keep separate (binary file).

### Verified Alignments ✅

1. **Genesis stays separate** - Confirmed in `qube.py`: saved to `chain/genesis.json` and `blocks/permanent/`
2. **Block files stay separate** - Confirmed: stored in `blocks/permanent/` and `blocks/session/`
3. **qube_metadata.json stays separate** - Contains encrypted private key
4. **nft_metadata.json stays separate** - NFT-specific data

### Recommended Blueprint Updates

1. Add `pending_transactions` to financial section (or keep separate)
2. Document that shared_memory systems stay separate
3. Document that semantic search index stays separate
4. Ensure GUI bridge uses atomic write pattern
5. Add specific migration code for relationship structure flatten→nested

---

## Section 5: Frontend Changes (TypeScript/React)

This section ensures the GUI stays in sync with backend changes. The architecture:

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React/Tauri)                       │
│                                                                      │
│   ┌──────────────────┐    ┌──────────────────┐    ┌──────────────┐  │
│   │  React Components │    │  Tauri Commands  │    │  TypeScript  │  │
│   │                   │    │    (lib.rs)      │    │   Interfaces │  │
│   │  QubeSettingsModal│    │                  │    │              │  │
│   │  ChatInterface    │───▶│  invoke('cmd')   │    │  types/      │  │
│   │  ModelModeIndicator   │                  │    │  index.ts    │  │
│   └──────────────────┘    └────────┬─────────┘    └──────────────┘  │
│                                    │                                 │
└────────────────────────────────────┼─────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    TAURI RUST LAYER (lib.rs)                         │
│                                                                      │
│   #[tauri::command]                                                  │
│   async fn set_model_lock(...) {                                     │
│       run_python_cli("gui_bridge.py", ["set_model_lock", ...])      │
│   }                                                                  │
└────────────────────────────────────┼─────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      PYTHON BACKEND                                  │
│                                                                      │
│   gui_bridge.py → ChainState (chain_state.json)                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 5.1 TypeScript Interface Updates

**File:** `qubes-gui/src/types/index.ts`

Add new interface to represent chain_state v2.0 structure:

```typescript
// =============================================================================
// CHAIN STATE V2.0 INTERFACES
// =============================================================================

/**
 * Chain State v2.0 Schema
 * This mirrors the backend chain_state.json structure for type safety.
 */
export interface ChainStateV2 {
  version: "2.0";
  qube_id: string;
  last_updated: number;

  chain: ChainSection;
  session: SessionSection;
  settings: SettingsSection;
  runtime: RuntimeSection;
  stats: StatsSection;
  skills: SkillsSection;
  relationships: RelationshipsSection;
  financial: FinancialSection;
  mood: MoodSection;
  health: HealthSection;
  attestation: AttestationSection;
}

// Chain Section - Blockchain tracking
export interface ChainSection {
  block_height: number;
  latest_block_hash: string | null;
  genesis_hash: string;
  genesis_timestamp: number;
  total_blocks: number;
  permanent_blocks: number;
  session_blocks: number;
}

// Session Section - Current conversation (ephemeral)
export interface SessionSection {
  session_id: string | null;
  started_at: number | null;
  messages_this_session: number;
  context_window_used: number;
  last_message_at: number | null;
  short_term_memory: any[];
}

// Settings Section - GUI-managed settings
export interface SettingsSection {
  // Model Mode (mutually exclusive)
  model_locked: boolean;
  model_locked_to: string | null;
  revolver_mode_enabled: boolean;
  revolver_providers: string[];
  revolver_models: string[];
  revolver_last_index: number;
  free_mode_enabled: boolean;
  free_mode_models: string[];

  // Auto-anchor settings
  auto_anchor_enabled: boolean;
  auto_anchor_threshold: number;

  // TTS settings
  tts_enabled: boolean;
  voice_model: string | null;

  // Visualizer settings
  visualizer_enabled: boolean;
  visualizer_settings: VisualizerSettings | null;
}

// Runtime Section - Active state (ephemeral)
export interface RuntimeSection {
  is_online: boolean;
  current_model: string | null;
  current_provider: string | null;
  last_api_call: number | null;
  pending_tool_calls: string[];
  active_conversation_id: string | null;
}

// Stats Section - Usage metrics
export interface StatsSection {
  total_messages_sent: number;
  total_messages_received: number;
  total_tokens_used: number;
  total_tool_calls: number;
  total_sessions: number;
  total_anchors: number;
  created_at: number;
  first_interaction: number | null;
  last_interaction: number | null;
}

// Skills Section - Unlocked skills only
export interface SkillsSection {
  unlocked: UnlockedSkill[];
  total_xp: number;
  last_xp_gain: number | null;
  history: SkillHistoryEntry[];
}

export interface UnlockedSkill {
  id: string;
  xp: number;
  level: number;
  unlocked_at: number;
  last_updated: number;
}

export interface SkillHistoryEntry {
  timestamp: number;
  skill_id: string;
  xp_gained: number;
  reason: string;
  block_id?: string;
}

// Relationships Section
export interface RelationshipsSection {
  entities: Record<string, RelationshipEntity>;
  total_entities_known: number;
  best_friend: string | null;
  owner: string;
}

export interface RelationshipEntity {
  entity_id: string;
  entity_type: 'human' | 'qube' | 'system';
  relationship_id: string;
  public_key: string | null;

  // Positive metrics (0-100)
  reliability: number;
  honesty: number;
  responsiveness: number;
  expertise: number;
  trust: number;
  friendship: number;
  affection: number;
  respect: number;
  loyalty: number;
  support: number;
  engagement: number;
  depth: number;
  humor: number;
  understanding: number;
  compatibility: number;
  admiration: number;
  warmth: number;
  openness: number;
  patience: number;
  empowerment: number;

  // Negative metrics (0-100)
  antagonism: number;
  resentment: number;
  annoyance: number;
  distrust: number;
  rivalry: number;
  tension: number;
  condescension: number;
  manipulation: number;
  dismissiveness: number;
  betrayal: number;

  // Interaction stats
  messages_sent: number;
  messages_received: number;
  response_time_avg: number;
  last_interaction: number;
  collaborations: number;
  collaborations_successful: number;
  collaborations_failed: number;

  // Status
  first_contact: number;
  days_known: number;
  has_met: boolean;
  status: 'stranger' | 'acquaintance' | 'friend' | 'close_friend' | 'best_friend';
  is_best_friend: boolean;

  // Clearance
  clearance_profile: string;
  clearance_categories: string[];
  clearance_fields: string[];
}

// Financial Section
export interface FinancialSection {
  wallet: WalletInfo;
  transactions: TransactionsInfo;
  pending: PendingTransaction[];
}

export interface WalletInfo {
  address: string | null;
  balance_satoshis: number;
  balance_bch: number;
  last_sync: number | null;
  utxo_count: number;
}

export interface TransactionsInfo {
  history: TransactionEntry[];
  total_count: number;
  archived_count: number;
}

export interface TransactionEntry {
  txid: string;
  tx_type: 'deposit' | 'withdrawal' | 'qube_spend';
  amount: number;
  timestamp: number;
  block_height: number | null;
  confirmations: number;
  memo: string | null;
}

export interface PendingTransaction {
  txid: string;
  created_at: number;
  amount: number;
  destination: string;
  status: 'pending' | 'broadcast' | 'confirmed' | 'failed';
}

// Mood Section
export interface MoodSection {
  current_mood: string;
  energy_level: number;
  stress_level: number;
  last_mood_update: number | null;
  mood_history: MoodHistoryEntry[];
}

export interface MoodHistoryEntry {
  timestamp: number;
  mood: string;
  energy: number;
  trigger: string | null;
}

// Health Section
export interface HealthSection {
  overall_status: 'healthy' | 'degraded' | 'critical';
  last_health_check: number | null;
  issues: string[];
  integrity_verified: boolean;
  last_integrity_check: number | null;
}

// Attestation Section (ephemeral)
export interface AttestationSection {
  last_attestation: number | null;
  attestation_hash: string | null;
  signed_by: string | null;
  verified: boolean;
}

// =============================================================================
// MODEL PREFERENCES RESPONSE (from Tauri command)
// =============================================================================

export interface ModelPreferencesResponse {
  success: boolean;
  model_locked?: boolean;
  model_locked_to?: string | null;
  revolver_mode?: boolean;
  revolver_providers?: string[];
  revolver_models?: string[];
  free_mode?: boolean;
  free_mode_models?: string[];
  error?: string;
}
```

### 5.2 Tauri Command Updates

**File:** `qubes-gui/src-tauri/src/lib.rs`

The Tauri commands call Python scripts via `run_python_cli`. No changes needed to the command signatures - they just need to work with the updated Python backend.

**Commands affected by chain_state changes:**

| Command | Current Status | Notes |
|---------|---------------|-------|
| `get_model_preferences` | Works | Returns flat fields |
| `set_model_lock` | Works | Writes to settings section |
| `set_revolver_mode` | Works | Writes to settings section |
| `set_revolver_providers` | Works | Writes to settings section |
| `set_revolver_models` | Works | Writes to settings section |
| `set_free_mode` | Works | Writes to settings section |
| `set_free_mode_models` | Works | Writes to settings section |
| `save_visualizer_settings` | Works | Writes to settings section |
| `get_visualizer_settings` | Works | Reads from settings section |

**Important:** The Tauri commands return flattened responses (not the full v2.0 structure). The Python `gui_bridge.py` handles the translation between v2.0 namespaced paths and the flat response format the frontend expects.

### 5.3 React Component Updates

#### QubeSettingsModal.tsx - No Changes Required

The modal saves via Tauri commands which call gui_bridge.py. The gui_bridge handles the v2.0 path mapping internally.

```typescript
// This stays the same - gui_bridge handles the backend structure
await invoke('set_model_lock', {
  userId,
  qubeId,
  locked: modelLocked,
  modelName: modelLocked ? currentModel : null,
});
```

#### ModelModeIndicator.tsx - No Changes Required

Fetches via `get_model_preferences` which returns a flat response:

```typescript
const result = await invoke<{
  success: boolean;
  model_locked?: boolean;
  revolver_mode?: boolean;
  free_mode?: boolean;
  error?: string;
}>('get_model_preferences', { userId, qubeId });
```

#### ChatInterface.tsx - No Changes Required

Uses Tauri commands that abstract away the chain_state structure.

### 5.4 GUI Bridge Updates (Python)

**File:** `gui_bridge.py`

The GUI Bridge methods need updating to use v2.0 namespaced paths. Here's the pattern:

**BEFORE (v1.0 flat structure):**
```python
def set_model_lock(self, qube_dir: Path, locked: bool, model_name: Optional[str]) -> None:
    state = self._load_chain_state(qube_dir)
    state["model_locked"] = locked
    state["model_locked_to"] = model_name
    self._save_chain_state(qube_dir, state)
```

**AFTER (v2.0 namespaced structure):**
```python
def set_model_lock(self, qube_dir: Path, locked: bool, model_name: Optional[str]) -> None:
    chain_state = ChainState(qube_dir)

    # Use ChainState's GUI-aware update method
    chain_state.update_settings({
        "model_locked": locked,
        "model_locked_to": model_name,
        # Disable other modes when locking
        "revolver_mode_enabled": False if locked else chain_state.get_setting("revolver_mode_enabled"),
        "free_mode_enabled": False if locked else chain_state.get_setting("free_mode_enabled"),
    })
```

**Complete list of gui_bridge methods to update:**

```python
# =============================================================================
# GUI BRIDGE V2.0 METHODS
# =============================================================================

class GUIBridge:
    """
    Bridge between Tauri GUI and Python backend.
    All methods use ChainState for file I/O (atomic writes, backups).
    """

    # -------------------------------------------------------------------------
    # MODEL MODE METHODS
    # -------------------------------------------------------------------------

    def set_model_lock(self, qube_dir: Path, locked: bool, model_name: Optional[str]) -> Dict:
        """Lock/unlock model selection."""
        chain_state = ChainState(qube_dir)

        updates = {"model_locked": locked, "model_locked_to": model_name}
        if locked:
            updates["revolver_mode_enabled"] = False
            updates["free_mode_enabled"] = False

        chain_state.update_settings(updates)
        return {"success": True}

    def set_revolver_mode(self, qube_dir: Path, enabled: bool) -> Dict:
        """Enable/disable revolver mode."""
        chain_state = ChainState(qube_dir)

        updates = {"revolver_mode_enabled": enabled}
        if enabled:
            updates["model_locked"] = False
            updates["free_mode_enabled"] = False

        chain_state.update_settings(updates)
        return {"success": True}

    def set_revolver_providers(self, qube_dir: Path, providers: List[str]) -> Dict:
        """Set providers for revolver mode."""
        chain_state = ChainState(qube_dir)
        chain_state.update_settings({"revolver_providers": providers})
        return {"success": True}

    def set_revolver_models(self, qube_dir: Path, models: List[str]) -> Dict:
        """Set models for revolver mode."""
        chain_state = ChainState(qube_dir)
        chain_state.update_settings({"revolver_models": models})
        return {"success": True}

    def set_free_mode(self, qube_dir: Path, enabled: bool) -> Dict:
        """Enable/disable free (autonomous) mode."""
        chain_state = ChainState(qube_dir)

        updates = {"free_mode_enabled": enabled}
        if enabled:
            updates["model_locked"] = False
            updates["revolver_mode_enabled"] = False

        chain_state.update_settings(updates)
        return {"success": True}

    def set_free_mode_models(self, qube_dir: Path, models: List[str]) -> Dict:
        """Set models for free mode."""
        chain_state = ChainState(qube_dir)
        chain_state.update_settings({"free_mode_models": models})
        return {"success": True}

    def get_model_preferences(self, qube_dir: Path) -> Dict:
        """Get all model preferences (flat format for frontend)."""
        chain_state = ChainState(qube_dir)
        settings = chain_state.state.get("settings", {})

        return {
            "success": True,
            "model_locked": settings.get("model_locked", True),
            "model_locked_to": settings.get("model_locked_to"),
            "revolver_mode": settings.get("revolver_mode_enabled", False),
            "revolver_providers": settings.get("revolver_providers", []),
            "revolver_models": settings.get("revolver_models", []),
            "free_mode": settings.get("free_mode_enabled", False),
            "free_mode_models": settings.get("free_mode_models", []),
        }

    def clear_model_preferences(self, qube_dir: Path) -> Dict:
        """Reset all model preferences to defaults."""
        chain_state = ChainState(qube_dir)
        chain_state.update_settings({
            "model_locked": True,
            "model_locked_to": None,
            "revolver_mode_enabled": False,
            "revolver_providers": [],
            "revolver_models": [],
            "revolver_last_index": 0,
            "free_mode_enabled": False,
            "free_mode_models": [],
        })
        return {"success": True}

    def rotate_revolver_model(self, qube_dir: Path) -> Dict:
        """Get next model in revolver rotation."""
        chain_state = ChainState(qube_dir)
        settings = chain_state.state.get("settings", {})

        models = settings.get("revolver_models", [])
        if not models:
            return {"success": False, "error": "No models configured for revolver"}

        current_index = settings.get("revolver_last_index", 0)
        next_index = (current_index + 1) % len(models)
        next_model = models[next_index]

        chain_state.update_settings({"revolver_last_index": next_index})

        return {
            "success": True,
            "model": next_model,
            "index": next_index,
        }

    # -------------------------------------------------------------------------
    # VISUALIZER METHODS
    # -------------------------------------------------------------------------

    def save_visualizer_settings(self, qube_dir: Path, settings: Dict) -> Dict:
        """Save visualizer settings."""
        chain_state = ChainState(qube_dir)
        chain_state.update_settings({
            "visualizer_enabled": settings.get("enabled", False),
            "visualizer_settings": settings,
        })
        return {"success": True}

    def get_visualizer_settings(self, qube_dir: Path) -> Dict:
        """Get visualizer settings."""
        chain_state = ChainState(qube_dir)
        settings = chain_state.state.get("settings", {})

        return {
            "success": True,
            "enabled": settings.get("visualizer_enabled", False),
            "settings": settings.get("visualizer_settings"),
        }

    # -------------------------------------------------------------------------
    # TTS METHODS
    # -------------------------------------------------------------------------

    def set_tts_enabled(self, qube_dir: Path, enabled: bool) -> Dict:
        """Enable/disable TTS."""
        chain_state = ChainState(qube_dir)
        chain_state.update_settings({"tts_enabled": enabled})
        return {"success": True}

    def set_voice_model(self, qube_dir: Path, voice_model: str) -> Dict:
        """Set TTS voice model."""
        chain_state = ChainState(qube_dir)
        chain_state.update_settings({"voice_model": voice_model})
        return {"success": True}

    # -------------------------------------------------------------------------
    # AUTO-ANCHOR METHODS
    # -------------------------------------------------------------------------

    def set_auto_anchor(self, qube_dir: Path, enabled: bool, threshold: int = 10) -> Dict:
        """Configure auto-anchor settings."""
        chain_state = ChainState(qube_dir)
        chain_state.update_settings({
            "auto_anchor_enabled": enabled,
            "auto_anchor_threshold": threshold,
        })
        return {"success": True}

    def get_auto_anchor_settings(self, qube_dir: Path) -> Dict:
        """Get auto-anchor settings."""
        chain_state = ChainState(qube_dir)
        settings = chain_state.state.get("settings", {})

        return {
            "success": True,
            "enabled": settings.get("auto_anchor_enabled", True),
            "threshold": settings.get("auto_anchor_threshold", 10),
        }
```

### 5.5 Frontend-Backend Field Mapping

This table maps frontend interface fields to chain_state v2.0 paths:

| Frontend Field | chain_state v2.0 Path | Writer |
|----------------|----------------------|--------|
| `model_locked` | `settings.model_locked` | GUI |
| `model_locked_to` | `settings.model_locked_to` | GUI |
| `revolver_mode` | `settings.revolver_mode_enabled` | GUI |
| `revolver_providers` | `settings.revolver_providers` | GUI |
| `revolver_models` | `settings.revolver_models` | GUI |
| `free_mode` | `settings.free_mode_enabled` | GUI |
| `free_mode_models` | `settings.free_mode_models` | GUI |
| `visualizer_enabled` | `settings.visualizer_enabled` | GUI |
| `visualizer_settings` | `settings.visualizer_settings` | GUI |
| `tts_enabled` | `settings.tts_enabled` | GUI |
| `voice_model` | `settings.voice_model` | GUI |
| `auto_anchor_enabled` | `settings.auto_anchor_enabled` | GUI |
| `auto_anchor_threshold` | `settings.auto_anchor_threshold` | GUI |
| `current_model` | `runtime.current_model` | Backend |
| `current_provider` | `runtime.current_provider` | Backend |
| `is_online` | `runtime.is_online` | Backend |

### 5.6 Event System (Tauri Events)

The GUI uses Tauri events to notify components of changes:

```typescript
// Current event: model-mode-changed
emit('model-mode-changed', {
  qubeId,
  modelLocked,
  revolverMode,
  freeMode,
});

// Listener in ModelModeIndicator
listen<{
  qubeId: string;
  modelLocked: boolean;
  revolverMode: boolean;
  freeMode: boolean;
}>('model-mode-changed', (event) => {
  // Update local state
});
```

**No changes needed** - The event payload is already a flat structure that works regardless of backend storage format.

---

## Section 6: Phased Implementation Plan

This plan ensures frontend and backend stay synchronized throughout implementation. All changes are **in-place** (no v1/v2 file duplication).

### Phase 1: ChainState Class Update

**Goal:** Update existing ChainState class with namespaced structure + encryption.

**Tasks:**
1. Update `core/chain_state.py` with v2.0 namespaced structure
2. Add encryption/decryption using existing `crypto/encryption.py`
3. Add `derive_chain_state_key()` function
4. Update constructor to accept `encryption_key` parameter
5. Add version detection (auto-migrate unencrypted → encrypted on load)
6. Keep all existing methods working (backward compatible getters/setters)
7. Add new namespace-aware methods (`update_settings()`, `get_setting()`, etc.)

**Files Modified:**
- `core/chain_state.py`
- `crypto/encryption.py` (add `derive_chain_state_key`)

**Frontend Impact:** None - old code still works.

**Testing Checkpoint:**
- [ ] ChainState loads encrypted files correctly
- [ ] ChainState encrypts on save
- [ ] Legacy unencrypted files auto-migrate to encrypted
- [ ] All existing methods still work

---

### Phase 2: Migration Logic in UserOrchestrator

**Goal:** Add eager migration on app startup.

**Tasks:**
1. Add `on_app_startup()` method to `UserOrchestrator`
2. Add `_migrate_qube_if_needed()` method
3. Add `_migrate_qube_to_v2()` method (consolidates all scattered files)
4. Per-qube error handling (one failure doesn't block others)
5. Delete old files immediately after successful migration

**Files Modified:**
- `orchestrator/user_orchestrator.py`

**Frontend Impact:** None.

**Testing Checkpoint:**
- [ ] Migration runs on startup
- [ ] Old qubes migrate successfully
- [ ] Already-migrated qubes skip migration
- [ ] Old files (relationships.json, etc.) deleted after migration
- [ ] One failed migration doesn't block others

---

### Phase 3: GUI Bridge Update

**Goal:** Update gui_bridge to use ChainState class (with proper locking/encryption).

**Tasks:**
1. Remove `_load_chain_state()` and `_save_chain_state()` helper methods
2. Add `_get_qube_encryption_key()` method
3. Update all settings methods to instantiate ChainState
4. Use `chain_state.update_settings()` for writes
5. Keep response formats identical (flat JSON for frontend)

**Files Modified:**
- `gui_bridge.py`

**Frontend Impact:** None - response formats unchanged.

**Testing Checkpoint:**
- [ ] GUI settings modal opens and saves correctly
- [ ] Model mode indicator shows correct state
- [ ] Settings persist after app restart
- [ ] Revolver mode rotation works
- [ ] No race conditions with concurrent access

---

### Phase 4: RelationshipStorage Update

**Goal:** RelationshipStorage reads/writes from chain_state instead of separate file.

**Tasks:**
1. Update `RelationshipStorage.__init__()` to use ChainState
2. Update `_load_relationships()` to read from `chain_state.relationships.entities`
3. Update `save()` to write to chain_state
4. Remove references to `relationships/relationships.json`
5. Update `SocialDynamicsManager` to pass encryption_key

**Files Modified:**
- `relationships/relationship.py`
- `relationships/social.py`

**Frontend Impact:** None - Tauri commands abstract this.

**Testing Checkpoint:**
- [ ] Relationships load correctly from chain_state
- [ ] New relationships save to chain_state
- [ ] Relationship tab displays correctly
- [ ] Relationship deltas apply correctly on anchor

---

### Phase 5: SkillsManager Update

**Goal:** SkillsManager reads/writes progress from chain_state (definitions stay in Python).

**Tasks:**
1. Update `SkillsManager` to use ChainState for progress
2. `load_skills()` → read unlocked from `chain_state.skills.unlocked`
3. `save_skills()` → write to chain_state
4. `add_xp()` → update chain_state
5. Keep skill definitions in `utils/skill_definitions.py` (read-only)
6. Remove skill_history.json references (use `chain_state.skills.history`)

**Files Modified:**
- `utils/skills_manager.py`

**Frontend Impact:** None - skills tab already works via backend calls.

**Testing Checkpoint:**
- [ ] Skills tab loads correctly
- [ ] XP awards update chain_state
- [ ] Skill definitions accessible from Python
- [ ] Skill history capped at 100 entries

---

### Phase 6: WalletTxManager Update

**Goal:** WalletTxManager reads/writes from chain_state.financial.

**Tasks:**
1. Update `WalletTxManager` to use ChainState
2. `_load_balance_cache()` → read from `chain_state.financial.wallet`
3. `_save_balance_cache()` → write to chain_state
4. Transaction history → `chain_state.financial.transactions`
5. Pending transactions → `chain_state.financial.pending`
6. Implement 50-entry cap with `archived_count`
7. Remove references to separate JSON files

**Files Modified:**
- `blockchain/wallet_tx.py`

**Frontend Impact:** None - earnings tab uses Tauri commands.

**Testing Checkpoint:**
- [ ] Wallet balance displays correctly
- [ ] Transactions load from chain_state
- [ ] New transactions append correctly
- [ ] Transactions cap at 50 with archived_count

---

### Phase 7: Qube Initialization Update

**Goal:** New qubes start with v2.0 encrypted chain_state.

**Tasks:**
1. Update `Qube.__init__()` to pass encryption_key to ChainState
2. Update `ChainState._initialize_new_state()` to create v2.0 structure
3. Initialize all sections with proper defaults
4. Ensure chain_state is encrypted from birth
5. Don't create `relationships/` directory (data goes in chain_state)

**Files Modified:**
- `core/qube.py`
- `core/chain_state.py` (update `_initialize_new_state`)

**Frontend Impact:** None.

**Testing Checkpoint:**
- [ ] New qube creates with v2.0 encrypted chain_state
- [ ] All sections present with defaults
- [ ] No relationships/ directory created
- [ ] Qube functions correctly from birth

---

### Phase 8: TypeScript Interfaces (Optional)

**Goal:** Add TypeScript interfaces for better type safety.

**Tasks:**
1. Add `ChainStateV2` interface to `types/index.ts`
2. Add section interfaces (SettingsSection, etc.)
3. Add `ModelPreferencesResponse` interface

**Files Modified:**
- `qubes-gui/src/types/index.ts`

**Frontend Impact:** Better type safety, no functional changes.

---

### Phase 9: Final Cleanup

**Goal:** Remove any remaining deprecated code.

**Tasks:**
1. Remove empty `relationships/` directories from existing qubes
2. Remove `skills/skill_history.json` if still present
3. Clean up any remaining scattered JSON files
4. Update code comments/docstrings

**Files Modified:**
- Various cleanup

---

### Implementation Order Visualization

```
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 1: ChainState Class                                       │
│ - Encryption + namespacing                                      │
│ - All existing methods still work                               │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 2: Migration Logic                                        │
│ - Eager migration on startup                                    │
│ - Consolidates scattered files → chain_state                    │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 3: GUI Bridge                                             │
│ - Uses ChainState class (proper locking)                        │
│ - No more direct file access                                    │
└─────────────────────┬───────────────────────────────────────────┘
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ PHASE 4     │ │ PHASE 5     │ │ PHASE 6     │
│ Relation-   │ │ Skills      │ │ Wallet      │
│ ships       │ │ Manager     │ │ TxManager   │
└──────┬──────┘ └──────┬──────┘ └──────┬──────┘
       │               │               │
       └───────────────┼───────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 7: Qube Initialization                                    │
│ - New qubes use v2.0 from birth                                 │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 8: TypeScript (Optional) + PHASE 9: Cleanup               │
└─────────────────────────────────────────────────────────────────┘
```

### Parallel Execution Notes

- **Phases 4, 5, 6 can run in parallel** after Phase 3 is complete
- Each phase has independent testing checkpoints
- If one phase fails, others can continue

### Recovery Strategy

Since migration deletes old files immediately, recovery relies on:

1. **chain_state backup file** - Created on every save (`.chain_state.backup.json`)
2. **Git history** - If in version control
3. **IPFS snapshots** - If user has synced to IPFS

**Note:** Old scattered files are deleted immediately after successful migration. This keeps the directory clean and avoids confusion.

---

## Section 7: Testing Checklist

### Backend Tests

```python
# test_chain_state_v2.py

def test_load_creates_v2_structure():
    """New qube should create v2.0 structure."""
    pass

def test_migrate_v1_to_v2():
    """v1.0 chain_state should auto-migrate."""
    pass

def test_atomic_write_backup():
    """Backup should be created on every save."""
    pass

def test_gui_fields_preserved():
    """Backend save should preserve GUI-managed fields."""
    pass

def test_settings_update():
    """update_settings should merge correctly."""
    pass

def test_relationship_add():
    """Adding relationship should update chain_state."""
    pass

def test_skill_unlock():
    """Unlocking skill should add to chain_state.skills."""
    pass

def test_transaction_cap():
    """Transactions should cap at 50 with archived_count."""
    pass
```

### Frontend Tests (Manual)

| Test | Steps | Expected Result |
|------|-------|-----------------|
| Settings persist | 1. Open settings, 2. Change model mode, 3. Close & reopen app | Settings unchanged |
| Revolver rotation | 1. Enable revolver, 2. Send messages | Model rotates |
| Visualizer settings | 1. Configure visualizer, 2. Restart | Settings preserved |
| Relationship display | 1. Chat with qube, 2. Check relationships tab | Owner relationship shows |
| Skills display | 1. Check skills tab | Unlocked skills display correctly |
| Earnings display | 1. Check earnings tab | Balance shows correctly |

---

## Finalized Decisions

All architectural decisions have been made:

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| 1 | Pending transactions location | **Include in chain_state** | `financial.pending[]` - simpler, unified backup |
| 2 | chain_state encryption | **Always encrypted** | AES-256-GCM, same pattern as blocks. Privacy is core to Qubes. |
| 3 | ChainState constructor signature | **Keep current pattern** | Pass `chain_dir` (not `qube_dir`). Architecturally correct. |
| 4 | gui_bridge ChainState access | **Instantiate ChainState directly** | gui_bridge imports and creates ChainState instance per operation |
| 5 | Migration trigger | **Eager on app startup** | Migrate all qubes on first launch after update. With per-qube error handling. |
| 6 | Old file deletion timing | **Immediate after migration** | Delete old scattered files immediately after successful migration |
| 7 | Relationship entity limit | **No limit** | Store all entities. Even hundreds wouldn't break context limits. |
| 8 | Skills definitions location | **Python code** | Use existing `utils/skill_definitions.py`. No separate JSON needed. |
| 9 | IPFS sync behavior | **Toggle in Settings** | User controls auto-sync. Manual sync always available in Dashboard. |
| 10 | Session state handling | **Clear on anchor/discard** | Session section is ephemeral. Skills/relationships only update during anchor. |

---

## Section 8: chain_state.json Encryption

Since privacy is core to Qubes, chain_state.json is **always encrypted at rest** using the same AES-256-GCM pattern used for permanent blocks.

### 8.1 Encryption Pattern

**File:** `crypto/encryption.py` (existing functions)

```python
from crypto.encryption import encrypt_block_data, decrypt_block_data
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

def derive_chain_state_key(qube_encryption_key: bytes) -> bytes:
    """
    Derive a key specifically for chain_state encryption.

    Uses HKDF with context "chain_state" to derive a separate key
    from the qube's master encryption key.
    """
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b"chain_state",
        backend=default_backend()
    )
    return hkdf.derive(qube_encryption_key)
```

### 8.2 Encrypted File Format

When saved to disk, chain_state.json looks like:

```json
{
  "ciphertext": "a1b2c3d4e5f6...",
  "nonce": "1a2b3c4d5e6f...",
  "algorithm": "AES-256-GCM",
  "encrypted": true
}
```

### 8.3 ChainState Encryption Integration

```python
class ChainState:
    def __init__(self, data_dir: Path, encryption_key: bytes):
        self.encryption_key = encryption_key
        self.chain_state_key = derive_chain_state_key(encryption_key)
        # ... rest of init

    def _load(self) -> None:
        """Load and decrypt state from disk"""
        with open(self.state_file, 'r') as f:
            file_data = json.load(f)

        if file_data.get("encrypted"):
            # Decrypt the state
            self.state = decrypt_block_data(file_data, self.chain_state_key)
        else:
            # Unencrypted (legacy or first load) - migrate to encrypted
            self.state = file_data
            self._save()  # Re-save encrypted

    def _save(self) -> None:
        """Encrypt and save state to disk"""
        # ... merge GUI_MANAGED_FIELDS ...

        # Encrypt before writing
        encrypted_data = encrypt_block_data(merged_state, self.chain_state_key)
        encrypted_data["encrypted"] = True

        # Atomic write
        temp_file = self.state_file.with_suffix('.json.tmp')
        with open(temp_file, 'w') as f:
            json.dump(encrypted_data, f, indent=2)
        temp_file.replace(self.state_file)
```

### 8.4 gui_bridge Encryption Access

gui_bridge needs the encryption key to instantiate ChainState. It gets this from the qube's metadata:

```python
def _get_qube_encryption_key(self, qube_dir: Path) -> bytes:
    """Load qube's encryption key from qube_metadata.json"""
    metadata_path = qube_dir / "chain" / "qube_metadata.json"
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)

    # Decrypt the encryption key using user's master key
    encrypted_key = bytes.fromhex(metadata["encrypted_encryption_key"])
    return self._decrypt_with_master_key(encrypted_key)

def set_model_lock(self, qube_id: str, locked: bool, model_name: str = None):
    qube_dir = self._find_qube_dir(qube_id)
    encryption_key = self._get_qube_encryption_key(qube_dir)

    chain_state = ChainState(
        data_dir=qube_dir / "chain",
        encryption_key=encryption_key
    )
    chain_state.update_settings({
        "model_locked": locked,
        "model_locked_to": model_name,
    })
```

---

## Section 9: Migration Script

Migration happens **eagerly on app startup** (first launch after update). Each qube is migrated independently with error handling so one failure doesn't block others.

### 9.1 Migration Trigger

**File:** `orchestrator/user_orchestrator.py`

```python
async def on_app_startup(self):
    """Called when app starts - migrate qubes if needed"""
    qubes = await self.list_qubes()

    for qube_info in qubes:
        try:
            await self._migrate_qube_if_needed(qube_info["qube_id"])
        except Exception as e:
            logger.error(f"Migration failed for {qube_info['qube_id']}: {e}")
            # Continue with other qubes - don't block startup

async def _migrate_qube_if_needed(self, qube_id: str):
    """Check if qube needs migration and perform it"""
    qube_dir = self._find_qube_dir(qube_id)
    chain_state_path = qube_dir / "chain" / "chain_state.json"

    # Load and check version
    with open(chain_state_path, 'r') as f:
        data = json.load(f)

    # If encrypted, decrypt first to check version
    if data.get("encrypted"):
        encryption_key = self._get_qube_encryption_key(qube_dir)
        chain_state_key = derive_chain_state_key(encryption_key)
        data = decrypt_block_data(data, chain_state_key)

    # Check if already migrated
    if data.get("version") == "2.0":
        return  # Already migrated

    # Perform migration
    await self._migrate_qube_to_v2(qube_dir, data)
```

### 9.2 Migration Logic

```python
async def _migrate_qube_to_v2(self, qube_dir: Path, old_state: Dict) -> None:
    """
    Migrate qube from flat chain_state to v2.0 namespaced structure.

    Consolidates:
    - relationships/relationships.json → chain_state.relationships
    - skills/skill_history.json → chain_state.skills.history
    - balance_cache.json → chain_state.financial.wallet
    - transaction_history.json → chain_state.financial.transactions
    - pending_transactions.json → chain_state.financial.pending
    """
    logger.info(f"Migrating qube at {qube_dir} to chain_state v2.0")

    # 1. Build v2.0 structure from old flat state
    new_state = {
        "version": "2.0",
        "qube_id": old_state.get("qube_id"),
        "last_updated": int(datetime.now(timezone.utc).timestamp()),

        # Chain section (from old flat fields)
        "chain": {
            "block_height": old_state.get("chain_length", 0),
            "latest_block_hash": old_state.get("last_block_hash"),
            "genesis_hash": old_state.get("last_block_hash") if old_state.get("chain_length", 0) <= 1 else None,
            "genesis_timestamp": None,  # Will be populated from genesis.json if needed
            "total_blocks": old_state.get("chain_length", 0),
            "permanent_blocks": old_state.get("chain_length", 0),
            "session_blocks": 0,
        },

        # Session section (ephemeral - start fresh)
        "session": {
            "session_id": None,
            "started_at": None,
            "messages_this_session": 0,
            "context_window_used": 0,
            "last_message_at": None,
            "short_term_memory": [],
        },

        # Settings section (from old flat fields)
        "settings": {
            "model_locked": old_state.get("model_locked", True),
            "model_locked_to": old_state.get("model_locked_to"),
            "revolver_mode_enabled": old_state.get("revolver_mode_enabled", False),
            "revolver_providers": old_state.get("revolver_providers", []),
            "revolver_models": old_state.get("revolver_models", []),
            "revolver_last_index": old_state.get("revolver_last_index", 0),
            "free_mode_enabled": old_state.get("free_mode", False),
            "free_mode_models": old_state.get("free_mode_models", []),
            "auto_anchor_enabled": old_state.get("auto_anchor_enabled", False),
            "auto_anchor_threshold": old_state.get("auto_anchor_threshold", 10),
            "tts_enabled": False,
            "voice_model": None,
            "visualizer_enabled": False,
            "visualizer_settings": None,
        },

        # Runtime section (ephemeral - start fresh)
        "runtime": {
            "is_online": False,
            "current_model": old_state.get("current_model_override"),
            "current_provider": None,
            "last_api_call": None,
            "pending_tool_calls": [],
            "active_conversation_id": None,
        },

        # Stats section (from old flat fields)
        "stats": {
            "total_messages_sent": 0,
            "total_messages_received": 0,
            "total_tokens_used": old_state.get("total_tokens_used", 0),
            "total_tool_calls": sum(old_state.get("api_calls_by_tool", {}).values()),
            "total_sessions": 0,
            "total_anchors": 0,
            "created_at": old_state.get("last_updated", int(datetime.now(timezone.utc).timestamp())),
            "first_interaction": None,
            "last_interaction": old_state.get("last_updated"),
        },

        # Skills section (populated from skills files)
        "skills": {
            "unlocked": [],  # Will be populated below
            "total_xp": 0,
            "last_xp_gain": None,
            "history": [],  # Will be populated below
        },

        # Relationships section (populated from relationships file)
        "relationships": {
            "entities": {},  # Will be populated below
            "total_entities_known": 0,
            "best_friend": None,
            "owner": None,  # Will be set below
        },

        # Financial section (populated from financial files)
        "financial": {
            "wallet": {
                "address": None,
                "balance_satoshis": 0,
                "balance_bch": 0.0,
                "last_sync": None,
                "utxo_count": 0,
            },
            "transactions": {
                "history": [],
                "total_count": 0,
                "archived_count": 0,
            },
            "pending": [],
        },

        # Mood section (new)
        "mood": {
            "current_mood": "neutral",
            "energy_level": 50,
            "stress_level": 0,
            "last_mood_update": None,
            "mood_history": [],
        },

        # Health section (from old flat fields)
        "health": {
            "overall_status": "healthy",
            "last_health_check": None,
            "issues": [],
            "integrity_verified": old_state.get("integrity_verified", True),
            "last_integrity_check": None,
        },

        # Attestation section (new)
        "attestation": {
            "last_attestation": None,
            "attestation_hash": None,
            "signed_by": None,
            "verified": False,
        },
    }

    # 2. Migrate relationships from relationships/relationships.json
    relationships_file = qube_dir / "relationships" / "relationships.json"
    if relationships_file.exists():
        with open(relationships_file, 'r') as f:
            relationships_data = json.load(f)

        for entity_id, rel_data in relationships_data.items():
            new_state["relationships"]["entities"][entity_id] = rel_data

            # Track owner and best friend
            if rel_data.get("entity_type") == "human":
                new_state["relationships"]["owner"] = entity_id
            if rel_data.get("is_best_friend"):
                new_state["relationships"]["best_friend"] = entity_id

        new_state["relationships"]["total_entities_known"] = len(relationships_data)

        # Delete old file
        relationships_file.unlink()
        logger.info(f"Migrated and deleted {relationships_file}")

    # 3. Migrate skill history from skills/skill_history.json
    skill_history_file = qube_dir / "skills" / "skill_history.json"
    if skill_history_file.exists():
        with open(skill_history_file, 'r') as f:
            skill_history = json.load(f)

        # Cap at 100 entries
        new_state["skills"]["history"] = skill_history[-100:] if len(skill_history) > 100 else skill_history

        # Delete old file
        skill_history_file.unlink()
        logger.info(f"Migrated and deleted {skill_history_file}")

    # 4. Extract unlocked skills from skills/skills.json
    skills_file = qube_dir / "skills" / "skills.json"
    if skills_file.exists():
        with open(skills_file, 'r') as f:
            skills_data = json.load(f)

        total_xp = 0
        for skill in skills_data.get("skills", []):
            if skill.get("unlocked"):
                new_state["skills"]["unlocked"].append({
                    "id": skill["id"],
                    "xp": skill.get("xp", 0),
                    "level": skill.get("level", 1),
                    "unlocked_at": skill.get("unlocked_at", int(datetime.now(timezone.utc).timestamp())),
                    "last_updated": skill.get("last_updated", int(datetime.now(timezone.utc).timestamp())),
                })
                total_xp += skill.get("xp", 0)

        new_state["skills"]["total_xp"] = total_xp

        # NOTE: Don't delete skills.json - it still holds the full skill tree definitions
        # But we should remove the progress fields from it (clean it to definitions only)
        # This is optional - the SkillsManager will handle this going forward

    # 5. Migrate financial data
    balance_cache_file = qube_dir / "balance_cache.json"
    if balance_cache_file.exists():
        with open(balance_cache_file, 'r') as f:
            balance_data = json.load(f)

        new_state["financial"]["wallet"] = {
            "address": balance_data.get("address"),
            "balance_satoshis": balance_data.get("balance", 0),
            "balance_bch": balance_data.get("balance", 0) / 100_000_000,
            "last_sync": balance_data.get("last_updated"),
            "utxo_count": len(balance_data.get("utxos", [])),
        }

        balance_cache_file.unlink()
        logger.info(f"Migrated and deleted {balance_cache_file}")

    tx_history_file = qube_dir / "transaction_history.json"
    if tx_history_file.exists():
        with open(tx_history_file, 'r') as f:
            tx_history = json.load(f)

        # Cap at 50 entries
        if len(tx_history) > 50:
            new_state["financial"]["transactions"]["archived_count"] = len(tx_history) - 50
            tx_history = tx_history[-50:]

        new_state["financial"]["transactions"]["history"] = tx_history
        new_state["financial"]["transactions"]["total_count"] = len(tx_history)

        tx_history_file.unlink()
        logger.info(f"Migrated and deleted {tx_history_file}")

    pending_tx_file = qube_dir / "pending_transactions.json"
    if pending_tx_file.exists():
        with open(pending_tx_file, 'r') as f:
            pending_txs = json.load(f)

        new_state["financial"]["pending"] = pending_txs

        pending_tx_file.unlink()
        logger.info(f"Migrated and deleted {pending_tx_file}")

    # 6. Save encrypted chain_state.json
    encryption_key = self._get_qube_encryption_key(qube_dir)
    chain_state_key = derive_chain_state_key(encryption_key)

    encrypted_data = encrypt_block_data(new_state, chain_state_key)
    encrypted_data["encrypted"] = True

    chain_state_path = qube_dir / "chain" / "chain_state.json"
    temp_path = chain_state_path.with_suffix('.json.tmp')

    with open(temp_path, 'w') as f:
        json.dump(encrypted_data, f, indent=2)

    temp_path.replace(chain_state_path)

    logger.info(f"Successfully migrated {qube_dir.name} to chain_state v2.0")
```

### 9.3 Clean Directory Structure After Migration

**Before:**
```
{qube_name}_{qube_id}/
├── chain/
│   ├── chain_state.json (flat, unencrypted)
│   ├── genesis.json
│   └── qube_metadata.json
├── blocks/
│   ├── permanent/
│   └── session/
├── relationships/
│   └── relationships.json        ← DELETED
├── skills/
│   ├── skills.json               ← KEPT (definitions only)
│   └── skill_history.json        ← DELETED
├── balance_cache.json            ← DELETED
├── transaction_history.json      ← DELETED
└── pending_transactions.json     ← DELETED
```

**After:**
```
{qube_name}_{qube_id}/
├── chain/
│   ├── chain_state.json (v2.0, encrypted, consolidated)
│   ├── genesis.json
│   └── qube_metadata.json
├── blocks/
│   ├── permanent/
│   └── session/
├── skills/
│   └── skills.json (definitions only - read-only game data)
├── snapshots/                    ← KEPT (timeline visualization)
│   ├── relationships/
│   └── self_evaluations/
└── shared_memory/                ← KEPT (inter-qube features)
    ├── permissions/
    ├── sessions/
    ├── market/
    └── cache/
```

---

## Section 10: Verified Behavior - Session vs Permanent State

**Verified in codebase:** Skills and relationships are ONLY updated during anchoring.

| During Conversation | On Anchor | On Discard |
|---------------------|-----------|------------|
| Session blocks created (temporary) | Session → permanent blocks | Session blocks deleted |
| `session` section tracks runtime | Skills XP applied (skill_scanner) | `session` section cleared |
| No skill/relationship changes | Relationship deltas applied | No skill/relationship changes |
| Stats tracked in memory only | Stats committed to chain_state | Stats discarded |

**Code evidence:**
- Skills: `session.py:466-577` - SkillScanner runs during `convert_to_permanent()`
- Relationships: `session.py:658-660` - `_apply_relationship_deltas_from_summary()` called during anchor

**Implication:** No `_pending` section needed. The `session` section handles ephemeral runtime state, and permanent sections only update during anchor.

---

# PART 2: COMPLETE IMPLEMENTATION CODE

This section contains copy-paste ready code for every file that needs modification.

---

## Section 11: crypto/encryption.py - Addition

Add this function to the existing `crypto/encryption.py` file:

```python
# Add this import at the top if not already present
from cryptography.hazmat.backends import default_backend

# Add this function after the existing functions

def derive_chain_state_key(qube_encryption_key: bytes) -> bytes:
    """
    Derive a key specifically for chain_state encryption.

    Uses HKDF with context "chain_state" to derive a separate key
    from the qube's master encryption key. This ensures chain_state
    uses a different key than individual blocks.

    Args:
        qube_encryption_key: The qube's 32-byte master encryption key

    Returns:
        32-byte key for chain_state encryption
    """
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b"chain_state",
        backend=default_backend()
    )
    return hkdf.derive(qube_encryption_key)
```

---

## Section 12: core/chain_state.py - Complete Replacement

**Replace the entire `core/chain_state.py` file with this:**

```python
"""
Chain State Management - v2.0

Consolidated, encrypted state management for Qubes.
All Qube state (settings, relationships, skills, financial) lives here.

Architecture:
- Encrypted at rest using AES-256-GCM
- Namespaced sections for organization
- Atomic writes with backup
- GUI-managed fields preserved on backend save
"""

import json
import os
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from utils.logging import get_logger
from utils.file_lock import FileLock
from crypto.encryption import encrypt_block_data, decrypt_block_data, derive_chain_state_key

logger = get_logger(__name__)


class ChainState:
    """
    Manages chain_state.json persistence with encryption.

    v2.0 Features:
    - Encrypted at rest (AES-256-GCM)
    - Namespaced sections (chain, session, settings, runtime, stats, skills, relationships, financial, mood, health, attestation)
    - Atomic writes (temp file + rename)
    - Backup on every save
    - GUI-managed fields preserved during backend save
    """

    # Version for migration detection
    VERSION = "2.0"

    # Fields managed by GUI (always prefer disk values on backend save)
    GUI_MANAGED_FIELDS = {
        "model_locked",
        "model_locked_to",
        "revolver_mode_enabled",
        "revolver_providers",
        "revolver_models",
        "revolver_first_response_done",
        "revolver_enabled_at",
        "revolver_last_response_at",
        "free_mode_enabled",
        "free_mode_models",
        "auto_anchor_enabled",
        "auto_anchor_threshold",
        "tts_enabled",
        "voice_model",
        "visualizer_enabled",
        "visualizer_settings",
    }

    # Sections excluded from IPFS anchors (ephemeral data)
    IPFS_EXCLUDED_SECTIONS = {"session", "runtime", "attestation"}

    # Array caps to prevent unbounded growth
    MAX_TRANSACTION_HISTORY = 50
    MAX_SKILL_HISTORY = 100
    MAX_RELATIONSHIP_EVALUATIONS = 50
    MAX_MOOD_HISTORY = 20

    def __init__(self, data_dir: Path, encryption_key: bytes, qube_id: str = None):
        """
        Initialize chain state.

        Args:
            data_dir: Path to chain directory (e.g., data/qubes/Athena_A1B2C3D4/chain/)
            encryption_key: 32-byte qube encryption key
            qube_id: Qube ID (optional, read from state if not provided)
        """
        self.data_dir = Path(data_dir)
        self.state_file = self.data_dir / "chain_state.json"
        self.backup_file = self.data_dir / ".chain_state.backup.json"
        self.lock_file = self.data_dir / ".chain_state.lock"

        # Derive chain_state-specific key
        self.encryption_key = encryption_key
        self.chain_state_key = derive_chain_state_key(encryption_key)

        self.qube_id = qube_id

        # Load existing state or create new
        if self.state_file.exists():
            self._load()
        else:
            self._initialize_new_state()

        # Update qube_id if provided and different
        if qube_id and self.state.get("qube_id") != qube_id:
            self.state["qube_id"] = qube_id

        logger.info("chain_state_loaded", qube_id=self.qube_id, version=self.state.get("version"))

    def _initialize_new_state(self) -> None:
        """Initialize new v2.0 chain state with all sections."""
        now = int(datetime.now(timezone.utc).timestamp())

        self.state = {
            "version": self.VERSION,
            "qube_id": self.qube_id,
            "last_updated": now,

            # Chain section - blockchain tracking
            "chain": {
                "block_height": 0,
                "latest_block_hash": "0" * 64,
                "genesis_hash": None,
                "genesis_timestamp": now,
                "total_blocks": 0,
                "permanent_blocks": 0,
                "session_blocks": 0,
                "last_anchor_block": None,
                "last_merkle_root": None,
            },

            # Session section - current conversation (ephemeral)
            "session": {
                "session_id": None,
                "started_at": None,
                "messages_this_session": 0,
                "context_window_used": 0,
                "last_message_at": None,
                "next_negative_index": -1,
            },

            # Settings section - GUI-managed settings
            "settings": {
                "model_locked": True,
                "model_locked_to": None,
                "revolver_mode_enabled": False,
                "revolver_providers": [],
                "revolver_models": [],
                "revolver_last_index": 0,
                "revolver_first_response_done": False,
                "revolver_enabled_at": 0,
                "revolver_last_response_at": 0,
                "free_mode_enabled": False,
                "free_mode_models": [],
                "auto_anchor_enabled": False,
                "auto_anchor_threshold": 10,
                "tts_enabled": False,
                "voice_model": None,
                "visualizer_enabled": False,
                "visualizer_settings": None,
            },

            # Runtime section - active state (ephemeral)
            "runtime": {
                "is_online": False,
                "current_model": None,
                "current_provider": None,
                "last_api_call": None,
                "pending_tool_calls": [],
                "active_conversation_id": None,
            },

            # Stats section - usage metrics
            "stats": {
                "total_messages_sent": 0,
                "total_messages_received": 0,
                "total_tokens_used": 0,
                "total_api_cost": 0.0,
                "tokens_by_model": {},
                "api_calls_by_tool": {},
                "total_tool_calls": 0,
                "total_sessions": 0,
                "total_anchors": 0,
                "created_at": now,
                "first_interaction": None,
                "last_interaction": None,
            },

            # Block counts
            "block_counts": {
                "GENESIS": 0,
                "THOUGHT": 0,
                "ACTION": 0,
                "OBSERVATION": 0,
                "MESSAGE": 0,
                "DECISION": 0,
                "MEMORY_ANCHOR": 0,
                "COLLABORATIVE_MEMORY": 0,
                "SUMMARY": 0,
            },

            # Skills section - unlocked skills only
            "skills": {
                "unlocked": [],
                "total_xp": 0,
                "last_xp_gain": None,
                "history": [],
            },

            # Relationships section
            "relationships": {
                "entities": {},
                "total_entities_known": 0,
                "best_friend": None,
                "owner": None,
            },

            # Financial section
            "financial": {
                "wallet": {
                    "address": None,
                    "balance_satoshis": 0,
                    "balance_bch": 0.0,
                    "last_sync": None,
                    "utxo_count": 0,
                },
                "transactions": {
                    "history": [],
                    "total_count": 0,
                    "archived_count": 0,
                },
                "pending": [],
            },

            # Mood section
            "mood": {
                "current_mood": "neutral",
                "energy_level": 50,
                "stress_level": 0,
                "last_mood_update": None,
                "mood_history": [],
            },

            # Health section
            "health": {
                "overall_status": "healthy",
                "last_health_check": None,
                "issues": [],
                "integrity_verified": True,
                "last_integrity_check": None,
            },

            # Attestation section (ephemeral)
            "attestation": {
                "last_attestation": None,
                "attestation_hash": None,
                "signed_by": None,
                "verified": False,
            },

            # Legacy fields for backward compatibility
            "avatar_description": None,
            "avatar_description_generated_at": None,
            "model_preferences": {},
            "current_model_override": None,
        }

        self._save()
        logger.info("chain_state_initialized", qube_id=self.qube_id)

    def _load(self) -> None:
        """Load and decrypt state from disk."""
        lock = FileLock(self.lock_file, timeout=5.0)

        try:
            with lock:
                with open(self.state_file, 'r') as f:
                    file_data = json.load(f)

                # Check if encrypted
                if file_data.get("encrypted"):
                    try:
                        self.state = decrypt_block_data(file_data, self.chain_state_key)
                    except Exception as e:
                        logger.error("chain_state_decryption_failed", error=str(e))
                        # Try to recover from backup
                        if self._recover_from_backup():
                            return
                        raise
                else:
                    # Unencrypted legacy file - migrate to encrypted
                    self.state = file_data
                    logger.info("migrating_unencrypted_chain_state")
                    self._save()  # Re-save encrypted

                # Check if migration needed (flat → namespaced)
                if "version" not in self.state:
                    self._migrate_v1_to_v2()

                logger.debug("chain_state_loaded_from_disk", qube_id=self.state.get("qube_id"))

        except Exception as e:
            logger.error("chain_state_load_failed", error=str(e), exc_info=True)
            raise

    def _recover_from_backup(self) -> bool:
        """Attempt to recover from backup file."""
        if not self.backup_file.exists():
            logger.warning("no_backup_file_for_recovery")
            return False

        try:
            with open(self.backup_file, 'r') as f:
                backup_data = json.load(f)

            if backup_data.get("encrypted"):
                self.state = decrypt_block_data(backup_data, self.chain_state_key)
            else:
                self.state = backup_data

            logger.info("chain_state_recovered_from_backup")
            self._save()  # Re-save to main file
            return True

        except Exception as e:
            logger.error("backup_recovery_failed", error=str(e))
            return False

    def _migrate_v1_to_v2(self) -> None:
        """Migrate flat v1 state to namespaced v2 structure."""
        logger.info("migrating_chain_state_v1_to_v2")

        old = self.state
        now = int(datetime.now(timezone.utc).timestamp())

        # Build v2 structure preserving old values
        self.state = {
            "version": self.VERSION,
            "qube_id": old.get("qube_id"),
            "last_updated": now,

            "chain": {
                "block_height": old.get("chain_length", 0),
                "latest_block_hash": old.get("last_block_hash", "0" * 64),
                "genesis_hash": None,
                "genesis_timestamp": None,
                "total_blocks": old.get("chain_length", 0),
                "permanent_blocks": old.get("chain_length", 0),
                "session_blocks": old.get("session_block_count", 0),
                "last_anchor_block": old.get("last_anchor_block"),
                "last_merkle_root": old.get("last_merkle_root"),
            },

            "session": {
                "session_id": old.get("current_session_id"),
                "started_at": old.get("session_start_timestamp"),
                "messages_this_session": 0,
                "context_window_used": 0,
                "last_message_at": None,
                "next_negative_index": old.get("next_negative_index", -1),
            },

            "settings": {
                "model_locked": old.get("model_locked", True),
                "model_locked_to": old.get("model_locked_to"),
                "revolver_mode_enabled": old.get("revolver_mode_enabled", False),
                "revolver_providers": old.get("revolver_providers", []),
                "revolver_models": old.get("revolver_models", []),
                "revolver_last_index": old.get("revolver_last_index", 0),
                "revolver_first_response_done": old.get("revolver_first_response_done", False),
                "revolver_enabled_at": old.get("revolver_enabled_at", 0),
                "revolver_last_response_at": old.get("revolver_last_response_at", 0),
                "free_mode_enabled": old.get("free_mode", False),
                "free_mode_models": old.get("free_mode_models", []),
                "auto_anchor_enabled": old.get("auto_anchor_enabled", False),
                "auto_anchor_threshold": old.get("auto_anchor_threshold", 10),
                "tts_enabled": False,
                "voice_model": None,
                "visualizer_enabled": False,
                "visualizer_settings": None,
            },

            "runtime": {
                "is_online": False,
                "current_model": old.get("current_model_override"),
                "current_provider": None,
                "last_api_call": None,
                "pending_tool_calls": [],
                "active_conversation_id": None,
            },

            "stats": {
                "total_messages_sent": 0,
                "total_messages_received": 0,
                "total_tokens_used": old.get("total_tokens_used", 0),
                "total_api_cost": old.get("total_api_cost", 0.0),
                "tokens_by_model": old.get("tokens_by_model", {}),
                "api_calls_by_tool": old.get("api_calls_by_tool", {}),
                "total_tool_calls": sum(old.get("api_calls_by_tool", {}).values()) if old.get("api_calls_by_tool") else 0,
                "total_sessions": 0,
                "total_anchors": 0,
                "created_at": old.get("last_updated", now),
                "first_interaction": None,
                "last_interaction": old.get("last_updated"),
            },

            "block_counts": old.get("block_counts", {
                "GENESIS": 0, "THOUGHT": 0, "ACTION": 0, "OBSERVATION": 0,
                "MESSAGE": 0, "DECISION": 0, "MEMORY_ANCHOR": 0,
                "COLLABORATIVE_MEMORY": 0, "SUMMARY": 0,
            }),

            "skills": {"unlocked": [], "total_xp": 0, "last_xp_gain": None, "history": []},
            "relationships": {"entities": {}, "total_entities_known": 0, "best_friend": None, "owner": None},
            "financial": {
                "wallet": {"address": None, "balance_satoshis": 0, "balance_bch": 0.0, "last_sync": None, "utxo_count": 0},
                "transactions": {"history": [], "total_count": 0, "archived_count": 0},
                "pending": [],
            },
            "mood": {"current_mood": "neutral", "energy_level": 50, "stress_level": 0, "last_mood_update": None, "mood_history": []},
            "health": {
                "overall_status": "healthy",
                "last_health_check": None,
                "issues": [],
                "integrity_verified": old.get("integrity_verified", True),
                "last_integrity_check": None,
            },
            "attestation": {"last_attestation": None, "attestation_hash": None, "signed_by": None, "verified": False},

            # Preserve legacy fields
            "avatar_description": old.get("avatar_description"),
            "avatar_description_generated_at": old.get("avatar_description_generated_at"),
            "model_preferences": old.get("model_preferences", {}),
            "current_model_override": old.get("current_model_override"),
        }

        self._save()
        logger.info("chain_state_migrated_to_v2", qube_id=self.state.get("qube_id"))

    def _save(self) -> None:
        """Encrypt and save state to disk with backup."""
        max_retries = 3

        for attempt in range(max_retries):
            try:
                lock = FileLock(self.lock_file, timeout=5.0)

                with lock:
                    # Load current disk state to preserve GUI-managed fields
                    disk_state = {}
                    if self.state_file.exists():
                        try:
                            with open(self.state_file, 'r') as f:
                                file_data = json.load(f)
                            if file_data.get("encrypted"):
                                disk_state = decrypt_block_data(file_data, self.chain_state_key)
                            else:
                                disk_state = file_data
                        except Exception:
                            pass

                    # Merge: start with in-memory, preserve GUI fields from disk
                    merged_state = self.state.copy()

                    # For settings section, preserve GUI-managed fields from disk
                    if "settings" in disk_state and "settings" in merged_state:
                        for field in self.GUI_MANAGED_FIELDS:
                            if field in disk_state.get("settings", {}):
                                merged_state["settings"][field] = disk_state["settings"][field]

                    # Update timestamp
                    merged_state["last_updated"] = int(datetime.now(timezone.utc).timestamp())

                    # Create backup before writing
                    if self.state_file.exists():
                        try:
                            with open(self.state_file, 'r') as f:
                                backup_data = f.read()
                            with open(self.backup_file, 'w') as f:
                                f.write(backup_data)
                        except Exception as e:
                            logger.warning("backup_creation_failed", error=str(e))

                    # Encrypt
                    encrypted_data = encrypt_block_data(merged_state, self.chain_state_key)
                    encrypted_data["encrypted"] = True

                    # Atomic write
                    self.data_dir.mkdir(parents=True, exist_ok=True)
                    temp_file = self.state_file.with_suffix('.json.tmp')

                    with open(temp_file, 'w') as f:
                        json.dump(encrypted_data, f, indent=2)
                        f.flush()
                        os.fsync(f.fileno())

                    temp_file.replace(self.state_file)

                    # Update in-memory state
                    self.state = merged_state

                    logger.debug("chain_state_saved", qube_id=self.state.get("qube_id"))
                    return

            except Exception as e:
                logger.warning("chain_state_save_retry", attempt=attempt + 1, error=str(e))
                if attempt < max_retries - 1:
                    time.sleep(0.1 * (attempt + 1))

        logger.error("chain_state_save_failed_all_retries", qube_id=self.state.get("qube_id"))

    def reload(self) -> None:
        """Reload state from disk, picking up external changes."""
        if self.state_file.exists():
            self._load()
            logger.debug("chain_state_reloaded", qube_id=self.state.get("qube_id"))

    # =========================================================================
    # SETTINGS SECTION METHODS (GUI-managed)
    # =========================================================================

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a setting value."""
        return self.state.get("settings", {}).get(key, default)

    def update_settings(self, updates: Dict[str, Any]) -> None:
        """Update multiple settings at once."""
        if "settings" not in self.state:
            self.state["settings"] = {}
        self.state["settings"].update(updates)
        self._save()

    def get_all_settings(self) -> Dict[str, Any]:
        """Get all settings."""
        return self.state.get("settings", {}).copy()

    # =========================================================================
    # CHAIN SECTION METHODS
    # =========================================================================

    def update_chain(
        self,
        chain_length: Optional[int] = None,
        last_block_number: Optional[int] = None,
        last_block_hash: Optional[str] = None,
        last_merkle_root: Optional[str] = None,
        last_anchor_block: Optional[int] = None
    ) -> None:
        """Update chain state fields."""
        chain = self.state.setdefault("chain", {})

        if chain_length is not None:
            chain["block_height"] = chain_length
            chain["total_blocks"] = chain_length
        if last_block_number is not None:
            chain["block_height"] = last_block_number + 1
        if last_block_hash is not None:
            chain["latest_block_hash"] = last_block_hash
        if last_merkle_root is not None:
            chain["last_merkle_root"] = last_merkle_root
        if last_anchor_block is not None:
            chain["last_anchor_block"] = last_anchor_block

        self._save()

    def increment_block_count(self, block_type: str) -> None:
        """Increment count for a block type."""
        counts = self.state.setdefault("block_counts", {})
        counts[block_type] = counts.get(block_type, 0) + 1

        # Also update chain totals
        chain = self.state.setdefault("chain", {})
        chain["total_blocks"] = chain.get("total_blocks", 0) + 1
        if block_type != "SESSION":
            chain["permanent_blocks"] = chain.get("permanent_blocks", 0) + 1

        self._save()

    def get_chain_length(self) -> int:
        """Get current chain length."""
        return self.state.get("chain", {}).get("block_height", 0)

    def get_last_block_hash(self) -> str:
        """Get last block hash."""
        return self.state.get("chain", {}).get("latest_block_hash", "0" * 64)

    def get_block_counts(self) -> Dict[str, int]:
        """Get block type counts."""
        return self.state.get("block_counts", {}).copy()

    # =========================================================================
    # SESSION SECTION METHODS
    # =========================================================================

    def start_session(self, session_id: str) -> None:
        """Start new session."""
        session = self.state.setdefault("session", {})

        if session.get("session_id") is None:
            session["messages_this_session"] = 0
            session["next_negative_index"] = -1

        session["session_id"] = session_id
        session["started_at"] = int(datetime.now(timezone.utc).timestamp())

        # Increment total sessions
        stats = self.state.setdefault("stats", {})
        stats["total_sessions"] = stats.get("total_sessions", 0) + 1

        self._save()
        logger.info("session_started", session_id=session_id)

    def end_session(self) -> None:
        """End current session."""
        session = self.state.setdefault("session", {})
        session["session_id"] = None
        session["started_at"] = None
        session["messages_this_session"] = 0
        session["next_negative_index"] = -1

        self._save()
        logger.info("session_ended", qube_id=self.state.get("qube_id"))

    def get_session_id(self) -> Optional[str]:
        """Get current session ID."""
        return self.state.get("session", {}).get("session_id")

    def get_next_negative_index(self) -> int:
        """Get next negative index for session blocks."""
        return self.state.get("session", {}).get("next_negative_index", -1)

    def update_session(
        self,
        session_block_count: Optional[int] = None,
        next_negative_index: Optional[int] = None
    ) -> None:
        """Update session state."""
        session = self.state.setdefault("session", {})

        if session_block_count is not None:
            session["messages_this_session"] = session_block_count
        if next_negative_index is not None:
            session["next_negative_index"] = next_negative_index

        self._save()

    def get_session_block_count(self) -> int:
        """Get current session block count."""
        return self.state.get("session", {}).get("messages_this_session", 0)

    # =========================================================================
    # STATS SECTION METHODS
    # =========================================================================

    def add_tokens(self, model: str, tokens: int, cost: float = 0.0) -> None:
        """Track token usage and costs."""
        stats = self.state.setdefault("stats", {})

        stats["total_tokens_used"] = stats.get("total_tokens_used", 0) + tokens
        stats["total_api_cost"] = stats.get("total_api_cost", 0.0) + cost

        tokens_by_model = stats.setdefault("tokens_by_model", {})
        tokens_by_model[model] = tokens_by_model.get(model, 0) + tokens

        self._save()

    def increment_tool_call(self, tool_name: str) -> None:
        """Track tool/API calls."""
        stats = self.state.setdefault("stats", {})

        api_calls = stats.setdefault("api_calls_by_tool", {})
        api_calls[tool_name] = api_calls.get(tool_name, 0) + 1

        stats["total_tool_calls"] = stats.get("total_tool_calls", 0) + 1

        self._save()

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics."""
        stats = self.state.get("stats", {})
        return {
            "total_tokens": stats.get("total_tokens_used", 0),
            "total_cost": stats.get("total_api_cost", 0.0),
            "tokens_by_model": stats.get("tokens_by_model", {}).copy(),
            "api_calls_by_tool": stats.get("api_calls_by_tool", {}).copy(),
        }

    # =========================================================================
    # SKILLS SECTION METHODS
    # =========================================================================

    def get_unlocked_skills(self) -> List[Dict[str, Any]]:
        """Get list of unlocked skills."""
        return self.state.get("skills", {}).get("unlocked", [])

    def unlock_skill(self, skill_id: str, xp: int = 0) -> None:
        """Add a skill to unlocked list."""
        skills = self.state.setdefault("skills", {"unlocked": [], "total_xp": 0, "history": []})
        now = int(datetime.now(timezone.utc).timestamp())

        # Check if already unlocked
        for skill in skills["unlocked"]:
            if skill["id"] == skill_id:
                return  # Already unlocked

        skills["unlocked"].append({
            "id": skill_id,
            "xp": xp,
            "level": 1,
            "unlocked_at": now,
            "last_updated": now,
        })

        self._save()
        logger.info("skill_unlocked", skill_id=skill_id)

    def add_skill_xp(self, skill_id: str, xp_amount: int, reason: str = None, block_id: str = None) -> None:
        """Add XP to a skill."""
        skills = self.state.setdefault("skills", {"unlocked": [], "total_xp": 0, "history": []})
        now = int(datetime.now(timezone.utc).timestamp())

        # Find and update skill
        for skill in skills["unlocked"]:
            if skill["id"] == skill_id:
                skill["xp"] = skill.get("xp", 0) + xp_amount
                skill["last_updated"] = now
                # Calculate level (simple: 100 XP per level)
                skill["level"] = min(100, 1 + skill["xp"] // 100)
                break
        else:
            # Skill not unlocked yet - unlock it
            self.unlock_skill(skill_id, xp_amount)

        # Update totals
        skills["total_xp"] = skills.get("total_xp", 0) + xp_amount
        skills["last_xp_gain"] = now

        # Add to history (capped)
        history = skills.setdefault("history", [])
        history.append({
            "timestamp": now,
            "skill_id": skill_id,
            "xp_gained": xp_amount,
            "reason": reason,
            "block_id": block_id,
        })

        # Cap history
        if len(history) > self.MAX_SKILL_HISTORY:
            skills["history"] = history[-self.MAX_SKILL_HISTORY:]

        self._save()

    def get_skill_progress(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """Get progress for a specific skill."""
        for skill in self.get_unlocked_skills():
            if skill["id"] == skill_id:
                return skill
        return None

    # =========================================================================
    # RELATIONSHIPS SECTION METHODS
    # =========================================================================

    def get_relationship(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get relationship data for an entity."""
        return self.state.get("relationships", {}).get("entities", {}).get(entity_id)

    def get_all_relationships(self) -> Dict[str, Dict[str, Any]]:
        """Get all relationships."""
        return self.state.get("relationships", {}).get("entities", {}).copy()

    def update_relationship(self, entity_id: str, data: Dict[str, Any]) -> None:
        """Update or create a relationship."""
        relationships = self.state.setdefault("relationships", {"entities": {}, "total_entities_known": 0})
        entities = relationships.setdefault("entities", {})

        is_new = entity_id not in entities
        entities[entity_id] = data

        if is_new:
            relationships["total_entities_known"] = len(entities)

        # Update owner/best_friend tracking
        if data.get("entity_type") == "human":
            relationships["owner"] = entity_id
        if data.get("is_best_friend"):
            relationships["best_friend"] = entity_id

        self._save()

    def delete_relationship(self, entity_id: str) -> bool:
        """Delete a relationship."""
        entities = self.state.get("relationships", {}).get("entities", {})
        if entity_id in entities:
            del entities[entity_id]
            self.state["relationships"]["total_entities_known"] = len(entities)
            self._save()
            return True
        return False

    def get_best_friend(self) -> Optional[str]:
        """Get best friend entity ID."""
        return self.state.get("relationships", {}).get("best_friend")

    def get_owner(self) -> Optional[str]:
        """Get owner entity ID."""
        return self.state.get("relationships", {}).get("owner")

    # =========================================================================
    # FINANCIAL SECTION METHODS
    # =========================================================================

    def get_wallet_info(self) -> Dict[str, Any]:
        """Get wallet information."""
        return self.state.get("financial", {}).get("wallet", {}).copy()

    def update_wallet(self, **kwargs) -> None:
        """Update wallet information."""
        wallet = self.state.setdefault("financial", {}).setdefault("wallet", {})
        wallet.update(kwargs)
        self._save()

    def add_transaction(self, tx: Dict[str, Any]) -> None:
        """Add a transaction to history."""
        financial = self.state.setdefault("financial", {})
        transactions = financial.setdefault("transactions", {"history": [], "total_count": 0, "archived_count": 0})
        history = transactions.setdefault("history", [])

        history.append(tx)
        transactions["total_count"] = transactions.get("total_count", 0) + 1

        # Cap history
        if len(history) > self.MAX_TRANSACTION_HISTORY:
            overflow = len(history) - self.MAX_TRANSACTION_HISTORY
            transactions["archived_count"] = transactions.get("archived_count", 0) + overflow
            transactions["history"] = history[-self.MAX_TRANSACTION_HISTORY:]

        self._save()

    def get_transaction_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get transaction history."""
        history = self.state.get("financial", {}).get("transactions", {}).get("history", [])
        return history[-limit:] if limit else history

    def get_pending_transactions(self) -> List[Dict[str, Any]]:
        """Get pending transactions."""
        return self.state.get("financial", {}).get("pending", [])

    def add_pending_transaction(self, tx: Dict[str, Any]) -> None:
        """Add a pending transaction."""
        pending = self.state.setdefault("financial", {}).setdefault("pending", [])
        pending.append(tx)
        self._save()

    def remove_pending_transaction(self, tx_id: str) -> bool:
        """Remove a pending transaction by ID."""
        pending = self.state.get("financial", {}).get("pending", [])
        for i, tx in enumerate(pending):
            if tx.get("tx_id") == tx_id:
                pending.pop(i)
                self._save()
                return True
        return False

    # =========================================================================
    # HEALTH SECTION METHODS
    # =========================================================================

    def update_health(
        self,
        overall_status: Optional[str] = None,
        integrity_verified: Optional[bool] = None,
        issues: Optional[List[str]] = None
    ) -> None:
        """Update health metrics."""
        health = self.state.setdefault("health", {})
        now = int(datetime.now(timezone.utc).timestamp())

        if overall_status is not None:
            health["overall_status"] = overall_status
        if integrity_verified is not None:
            health["integrity_verified"] = integrity_verified
            health["last_integrity_check"] = now
        if issues is not None:
            health["issues"] = issues

        health["last_health_check"] = now
        self._save()

    def get_health(self) -> Dict[str, Any]:
        """Get health information."""
        return self.state.get("health", {}).copy()

    # =========================================================================
    # AUTO-ANCHOR METHODS
    # =========================================================================

    def is_auto_anchor_enabled(self) -> bool:
        """Check if auto-anchor is enabled."""
        return self.state.get("settings", {}).get("auto_anchor_enabled", False)

    def get_auto_anchor_threshold(self) -> int:
        """Get auto-anchor threshold."""
        return self.state.get("settings", {}).get("auto_anchor_threshold", 10)

    def set_auto_anchor(self, enabled: bool, threshold: int = 10) -> None:
        """Configure auto-anchor settings."""
        settings = self.state.setdefault("settings", {})
        settings["auto_anchor_enabled"] = enabled
        settings["auto_anchor_threshold"] = threshold
        self._save()

    # =========================================================================
    # MODEL MODE METHODS (backward compatible)
    # =========================================================================

    def is_model_locked(self) -> bool:
        """Check if model switching is locked."""
        return self.state.get("settings", {}).get("model_locked", True)

    def get_locked_model(self) -> Optional[str]:
        """Get locked model name."""
        return self.state.get("settings", {}).get("model_locked_to")

    def set_model_lock(self, locked: bool, model_name: str = None) -> None:
        """Lock or unlock model selection."""
        settings = self.state.setdefault("settings", {})
        settings["model_locked"] = locked
        settings["model_locked_to"] = model_name if locked else None
        if locked:
            settings["revolver_mode_enabled"] = False
            settings["free_mode_enabled"] = False
        self._save()

    def is_revolver_mode_enabled(self) -> bool:
        """Check if revolver mode is enabled."""
        return self.state.get("settings", {}).get("revolver_mode_enabled", False)

    def set_revolver_mode(self, enabled: bool) -> None:
        """Enable or disable revolver mode."""
        settings = self.state.setdefault("settings", {})
        settings["revolver_mode_enabled"] = enabled
        if enabled:
            settings["revolver_last_index"] = 0
            settings["revolver_first_response_done"] = False
            settings["revolver_enabled_at"] = int(time.time())
            settings["model_locked"] = False
            settings["free_mode_enabled"] = False
        self._save()

    def get_revolver_providers(self) -> List[str]:
        """Get revolver mode providers."""
        return self.state.get("settings", {}).get("revolver_providers", [])

    def set_revolver_providers(self, providers: List[str]) -> None:
        """Set revolver mode providers."""
        self.state.setdefault("settings", {})["revolver_providers"] = providers
        self._save()

    def get_revolver_models(self) -> List[str]:
        """Get revolver mode models."""
        return self.state.get("settings", {}).get("revolver_models", [])

    def set_revolver_models(self, models: List[str]) -> None:
        """Set revolver mode models."""
        self.state.setdefault("settings", {})["revolver_models"] = models
        self._save()

    def get_next_revolver_index(self, num_providers: int) -> int:
        """Get next provider index for revolver mode."""
        if num_providers <= 0:
            return 0
        return self.state.get("settings", {}).get("revolver_last_index", 0) % num_providers

    def increment_revolver_index(self, num_providers: int) -> None:
        """Increment revolver index."""
        if num_providers <= 0:
            return
        settings = self.state.setdefault("settings", {})
        current = settings.get("revolver_last_index", 0)
        settings["revolver_last_index"] = (current + 1) % num_providers
        self._save()

    def is_revolver_first_response_done(self) -> bool:
        """Check if first revolver response is done."""
        settings = self.state.get("settings", {})
        flag = settings.get("revolver_first_response_done", False)
        enabled_at = settings.get("revolver_enabled_at", 0)
        last_response_at = settings.get("revolver_last_response_at", 0)
        return flag and (enabled_at == 0 or last_response_at > enabled_at)

    def set_revolver_first_response_done(self) -> None:
        """Mark first revolver response as done."""
        settings = self.state.setdefault("settings", {})
        settings["revolver_first_response_done"] = True
        settings["revolver_last_response_at"] = int(time.time())
        self._save()

    def is_free_mode_enabled(self) -> bool:
        """Check if free mode is enabled."""
        return self.state.get("settings", {}).get("free_mode_enabled", False)

    def set_free_mode(self, enabled: bool) -> None:
        """Enable or disable free mode."""
        settings = self.state.setdefault("settings", {})
        settings["free_mode_enabled"] = enabled
        if enabled:
            settings["model_locked"] = False
            settings["revolver_mode_enabled"] = False
        self._save()

    def get_free_mode_models(self) -> List[str]:
        """Get free mode models."""
        return self.state.get("settings", {}).get("free_mode_models", [])

    def set_free_mode_models(self, models: List[str]) -> None:
        """Set free mode models."""
        self.state.setdefault("settings", {})["free_mode_models"] = models
        self._save()

    # =========================================================================
    # LEGACY METHODS (backward compatibility)
    # =========================================================================

    def set_avatar_description(self, description: str) -> None:
        """Store avatar description."""
        self.state["avatar_description"] = description
        self.state["avatar_description_generated_at"] = int(datetime.now(timezone.utc).timestamp())
        self._save()

    def get_avatar_description(self) -> Optional[str]:
        """Get cached avatar description."""
        return self.state.get("avatar_description")

    def clear_avatar_description(self) -> None:
        """Clear cached avatar description."""
        self.state["avatar_description"] = None
        self.state["avatar_description_generated_at"] = None
        self._save()

    def set_current_model_override(self, model_name: str) -> None:
        """Set model override."""
        self.state["current_model_override"] = model_name
        runtime = self.state.setdefault("runtime", {})
        runtime["current_model"] = model_name
        self._save()

    def get_current_model_override(self) -> Optional[str]:
        """Get current model override."""
        return self.state.get("current_model_override")

    def clear_current_model_override(self) -> None:
        """Clear model override."""
        self.state["current_model_override"] = None
        self._save()

    def get_state(self) -> Dict[str, Any]:
        """Get full state dict (for debugging)."""
        return self.state.copy()

    def get_ipfs_state(self) -> Dict[str, Any]:
        """Get state for IPFS anchoring (excludes ephemeral sections)."""
        state = self.state.copy()
        for section in self.IPFS_EXCLUDED_SECTIONS:
            state.pop(section, None)
        return state
```

---

## Section 13: gui_bridge.py - Updated Methods

The GUI bridge currently accesses chain_state.json directly without encryption. After consolidation,
it must use the encrypted ChainState class. The key change is replacing raw JSON file access with
ChainState instantiation that handles encryption/decryption automatically.

### 13.1 Key Issue

The current `_load_chain_state()` and `_save_chain_state()` methods in gui_bridge.py (lines 6849-6869)
read/write raw JSON. After consolidation, chain_state.json is encrypted, so these methods will fail.

### 13.2 Solution: Use ChainState Class

Instead of direct file access, gui_bridge should instantiate ChainState with the encryption key.

**Problem**: gui_bridge doesn't have access to the qube's encryption key because it operates without
loading the full Qube object (for performance reasons - settings changes shouldn't require full load).

**Solution**: Store the encryption key derivation in a way gui_bridge can access:
1. The master key is derived from user password
2. Each qube has a unique encryption key stored encrypted by master key
3. gui_bridge can load the encrypted qube key and decrypt with master key

### 13.3 gui_bridge.py - Complete Updated Section

Replace lines 6836-7305 with the following:

```python
# =============================================================================
# Model Control (Lock, Revolver Mode, Preferences) - UPDATED FOR ENCRYPTION
# =============================================================================

def _find_qube_dir(self, qube_id: str) -> Optional[Path]:
    """Find the qube directory by searching for matching qube_id in metadata files."""
    qubes_dir = self.orchestrator.data_dir / "qubes"
    for dir_entry in qubes_dir.iterdir():
        if dir_entry.is_dir():
            metadata_path = dir_entry / "chain" / "qube_metadata.json"
            if metadata_path.exists():
                with open(metadata_path, "r") as f:
                    data = json.load(f)
                    if data.get("qube_id") == qube_id:
                        return dir_entry
    return None

def _get_qube_encryption_key(self, qube_dir: Path) -> Optional[bytes]:
    """
    Get the encryption key for a qube.

    The qube's encryption key is stored encrypted by the master key in:
    {qube_dir}/chain/encryption_key.enc

    Returns:
        Encryption key bytes, or None if not available
    """
    if not self.orchestrator.master_key:
        logger.warning("Cannot get qube encryption key - master key not set")
        return None

    key_file = qube_dir / "chain" / "encryption_key.enc"
    if not key_file.exists():
        # Legacy qube without encrypted key file - use master key directly
        # (for backward compatibility during migration)
        logger.debug("No encryption_key.enc found, using master key fallback")
        return self.orchestrator.master_key

    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        with open(key_file, 'r') as f:
            enc_data = json.load(f)

        nonce = bytes.fromhex(enc_data["nonce"])
        ciphertext = bytes.fromhex(enc_data["ciphertext"])

        aesgcm = AESGCM(self.orchestrator.master_key)
        qube_key = aesgcm.decrypt(nonce, ciphertext, None)
        return qube_key

    except Exception as e:
        logger.error(f"Failed to decrypt qube encryption key: {e}")
        return None

def _get_chain_state(self, qube_id: str) -> Optional["ChainState"]:
    """
    Get ChainState instance for a qube with proper encryption.

    Args:
        qube_id: The Qube's ID

    Returns:
        ChainState instance, or None if qube not found or key unavailable
    """
    qube_dir = self._find_qube_dir(qube_id)
    if not qube_dir:
        return None

    encryption_key = self._get_qube_encryption_key(qube_dir)
    if not encryption_key:
        logger.warning(f"Cannot access chain_state for {qube_id} - no encryption key")
        return None

    from core.chain_state import ChainState
    chain_dir = qube_dir / "chain"
    return ChainState(data_dir=chain_dir, encryption_key=encryption_key, qube_id=qube_id)

async def set_model_lock(self, qube_id: str, locked: bool, model_name: str = None) -> Dict[str, Any]:
    """
    Lock or unlock the Qube's ability to switch models.
    Uses encrypted ChainState for persistence.

    Note: Lock and Revolver modes are mutually exclusive.
    Enabling lock will disable revolver mode.

    Args:
        qube_id: The Qube's ID
        locked: True to lock, False to unlock
        model_name: Optional - when locking, force a specific model

    Returns:
        Dict with success status
    """
    try:
        chain_state = self._get_chain_state(qube_id)
        if not chain_state:
            return {"success": False, "error": f"Qube {qube_id} not found or not accessible"}

        chain_state.set_model_lock(locked, model_name)

        logger.info(f"Model lock set for {qube_id}: locked={locked}, model={model_name}")

        return {
            "success": True,
            "locked": locked,
            "locked_to": model_name
        }

    except Exception as e:
        logger.error(f"Failed to set model lock: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

async def set_revolver_mode(self, qube_id: str, enabled: bool) -> Dict[str, Any]:
    """
    Enable or disable revolver mode (privacy feature).
    Uses encrypted ChainState for persistence.

    When enabled, rotates AI providers for each response.

    Note: Lock and Revolver modes are mutually exclusive.
    Enabling revolver will disable lock mode.

    Args:
        qube_id: The Qube's ID
        enabled: True to enable, False to disable

    Returns:
        Dict with success status
    """
    try:
        chain_state = self._get_chain_state(qube_id)
        if not chain_state:
            return {"success": False, "error": f"Qube {qube_id} not found or not accessible"}

        chain_state.set_revolver_mode(enabled)

        logger.info(f"Revolver mode set for {qube_id}: enabled={enabled}")

        return {
            "success": True,
            "revolver_mode": enabled
        }

    except Exception as e:
        logger.error(f"Failed to set revolver mode: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

async def set_revolver_providers(self, qube_id: str, providers: List[str]) -> Dict[str, Any]:
    """
    Set the list of providers to include in revolver mode rotation.
    Uses encrypted ChainState for persistence.

    Args:
        qube_id: The Qube's ID
        providers: List of provider names. Empty list means use all configured providers.

    Returns:
        Dict with success status and current providers list
    """
    try:
        chain_state = self._get_chain_state(qube_id)
        if not chain_state:
            return {"success": False, "error": f"Qube {qube_id} not found or not accessible"}

        chain_state.set_revolver_providers(providers)

        logger.info(f"Revolver providers set for {qube_id}: {providers}")

        return {
            "success": True,
            "providers": providers
        }

    except Exception as e:
        logger.error(f"Failed to set revolver providers: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

async def get_revolver_providers(self, qube_id: str) -> Dict[str, Any]:
    """
    Get the list of providers configured for revolver mode rotation.
    Uses encrypted ChainState for persistence.

    Args:
        qube_id: The Qube's ID

    Returns:
        Dict with success status and providers list
    """
    try:
        chain_state = self._get_chain_state(qube_id)
        if not chain_state:
            return {"success": False, "error": f"Qube {qube_id} not found or not accessible"}

        providers = chain_state.get_revolver_providers()

        return {
            "success": True,
            "providers": providers
        }

    except Exception as e:
        logger.error(f"Failed to get revolver providers: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

async def set_revolver_models(self, qube_id: str, models: List[str]) -> Dict[str, Any]:
    """
    Set the list of specific models to include in revolver mode rotation.
    Uses encrypted ChainState for persistence.

    Args:
        qube_id: The Qube's ID
        models: List of model IDs. Empty list means use all models from selected providers.

    Returns:
        Dict with success status and current models list
    """
    try:
        chain_state = self._get_chain_state(qube_id)
        if not chain_state:
            return {"success": False, "error": f"Qube {qube_id} not found or not accessible"}

        chain_state.set_revolver_models(models)

        logger.info(f"Revolver models set for {qube_id}: {len(models)} models")

        return {
            "success": True,
            "models": models
        }

    except Exception as e:
        logger.error(f"Failed to set revolver models: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

async def get_revolver_models(self, qube_id: str) -> Dict[str, Any]:
    """
    Get the list of specific models configured for revolver mode rotation.
    Uses encrypted ChainState for persistence.

    Args:
        qube_id: The Qube's ID

    Returns:
        Dict with success status and models list
    """
    try:
        chain_state = self._get_chain_state(qube_id)
        if not chain_state:
            return {"success": False, "error": f"Qube {qube_id} not found or not accessible"}

        models = chain_state.get_revolver_models()

        return {
            "success": True,
            "models": models
        }

    except Exception as e:
        logger.error(f"Failed to get revolver models: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

async def set_free_mode_models(self, qube_id: str, models: List[str]) -> Dict[str, Any]:
    """
    Set the list of models available in free mode (autonomous selection).
    Uses encrypted ChainState for persistence.

    Args:
        qube_id: The Qube's ID
        models: List of model IDs. Empty list means all configured models are available.

    Returns:
        Dict with success status and current models list
    """
    try:
        chain_state = self._get_chain_state(qube_id)
        if not chain_state:
            return {"success": False, "error": f"Qube {qube_id} not found or not accessible"}

        chain_state.set_free_mode_models(models)

        logger.info(f"Free mode models set for {qube_id}: {len(models)} models")

        return {
            "success": True,
            "models": models
        }

    except Exception as e:
        logger.error(f"Failed to set free mode models: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

async def get_free_mode_models(self, qube_id: str) -> Dict[str, Any]:
    """
    Get the list of models available in free mode.
    Uses encrypted ChainState for persistence.

    Args:
        qube_id: The Qube's ID

    Returns:
        Dict with success status and models list
    """
    try:
        chain_state = self._get_chain_state(qube_id)
        if not chain_state:
            return {"success": False, "error": f"Qube {qube_id} not found or not accessible"}

        models = chain_state.get_free_mode_models()

        return {
            "success": True,
            "models": models
        }

    except Exception as e:
        logger.error(f"Failed to get free mode models: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

async def set_free_mode(self, qube_id: str, enabled: bool) -> Dict[str, Any]:
    """
    Enable or disable free mode (autonomous model selection).
    Uses encrypted ChainState for persistence.

    Args:
        qube_id: The Qube's ID
        enabled: True to enable free mode, False to disable

    Returns:
        Dict with success status and current enabled state
    """
    try:
        chain_state = self._get_chain_state(qube_id)
        if not chain_state:
            return {"success": False, "error": f"Qube {qube_id} not found or not accessible"}

        chain_state.set_free_mode(enabled)

        logger.info(f"Free mode {'enabled' if enabled else 'disabled'} for {qube_id}")

        return {
            "success": True,
            "enabled": enabled
        }

    except Exception as e:
        logger.error(f"Failed to set free mode: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

async def get_model_preferences(self, qube_id: str) -> Dict[str, Any]:
    """
    Get the Qube's model preferences and control status.
    Uses encrypted ChainState for persistence.

    Args:
        qube_id: The Qube's ID

    Returns:
        Dict with preferences, current model, lock status, revolver mode
    """
    try:
        qube_dir = self._find_qube_dir(qube_id)
        if not qube_dir:
            return {"success": False, "error": f"Qube {qube_id} not found"}

        chain_state = self._get_chain_state(qube_id)
        if not chain_state:
            return {"success": False, "error": f"Cannot access chain state for {qube_id}"}

        # Get genesis model from metadata
        metadata_path = qube_dir / "chain" / "qube_metadata.json"
        genesis_model = None
        if metadata_path.exists():
            with open(metadata_path, "r") as f:
                metadata = json.load(f)
                genesis_model = metadata.get("genesis_block", {}).get("ai_model")

        # Read from chain_state using accessor methods
        model_locked = chain_state.is_model_locked()
        locked_to = chain_state.get_locked_model()
        revolver_mode = chain_state.is_revolver_mode_enabled()
        revolver_providers = chain_state.get_revolver_providers()
        revolver_models = chain_state.get_revolver_models()
        free_mode = chain_state.is_free_mode_enabled()
        free_mode_models = chain_state.get_free_mode_models()
        current_override = chain_state.get_current_model_override()

        return {
            "success": True,
            "preferences": chain_state.state.get("settings", {}).get("model_preferences", {}),
            "current_model": current_override or genesis_model,
            "current_override": current_override,
            "genesis_model": genesis_model,
            "model_locked": model_locked,
            "locked_to": locked_to,
            "revolver_mode": revolver_mode,
            "revolver_providers": revolver_providers,
            "revolver_models": revolver_models,
            "free_mode": free_mode,
            "free_mode_models": free_mode_models
        }

    except Exception as e:
        logger.error(f"Failed to get model preferences: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

async def clear_model_preferences(self, qube_id: str, task_type: str = None) -> Dict[str, Any]:
    """
    Clear model preferences.
    Uses encrypted ChainState for persistence.

    Args:
        qube_id: The Qube's ID
        task_type: Optional - clear specific task type only, or all if None

    Returns:
        Dict with success status
    """
    try:
        chain_state = self._get_chain_state(qube_id)
        if not chain_state:
            return {"success": False, "error": f"Qube {qube_id} not found or not accessible"}

        settings = chain_state.state.setdefault("settings", {})

        if task_type:
            prefs = settings.get("model_preferences", {})
            if task_type in prefs:
                del prefs[task_type]
            settings["model_preferences"] = prefs
            logger.info(f"Cleared model preference for {qube_id}: task_type={task_type}")
        else:
            settings["model_preferences"] = {}
            logger.info(f"Cleared all model preferences for {qube_id}")

        chain_state._save()

        return {"success": True}

    except Exception as e:
        logger.error(f"Failed to clear model preferences: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

async def reset_model_to_genesis(self, qube_id: str) -> Dict[str, Any]:
    """
    Reset the Qube's model to its genesis (birth) model.
    Uses encrypted ChainState for persistence.

    Clears the model override so the Qube uses its original model.

    Args:
        qube_id: The Qube's ID

    Returns:
        Dict with success status and the genesis model
    """
    try:
        qube_dir = self._find_qube_dir(qube_id)
        if not qube_dir:
            return {"success": False, "error": f"Qube {qube_id} not found"}

        chain_state = self._get_chain_state(qube_id)
        if not chain_state:
            return {"success": False, "error": f"Cannot access chain state for {qube_id}"}

        # Clear the model override
        chain_state.clear_current_model_override()

        # Get genesis model from metadata
        metadata_path = qube_dir / "chain" / "qube_metadata.json"
        genesis_model = None
        if metadata_path.exists():
            with open(metadata_path, "r") as f:
                metadata = json.load(f)
                genesis_model = metadata.get("genesis_block", {}).get("ai_model")

        logger.info(f"Reset model to genesis for {qube_id}: {genesis_model}")

        return {
            "success": True,
            "genesis_model": genesis_model
        }

    except Exception as e:
        logger.error(f"Failed to reset model to genesis: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
```

### 13.4 Additional Requirement: Encryption Key Storage

When a Qube is created, its encryption key must be stored encrypted by the master key.
Add to `core/qube.py` after generating the encryption key (around line 195):

```python
# Save encryption key encrypted by master key (for gui_bridge access)
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import secrets

encryption_key_file = qube_data_dir / "chain" / "encryption_key.enc"
if orchestrator and orchestrator.master_key:
    aesgcm = AESGCM(orchestrator.master_key)
    nonce = secrets.token_bytes(12)
    ciphertext = aesgcm.encrypt(nonce, self.encryption_key, None)

    with open(encryption_key_file, 'w') as f:
        json.dump({
            "nonce": nonce.hex(),
            "ciphertext": ciphertext.hex(),
            "algorithm": "AES-256-GCM",
            "version": "1.0"
        }, f, indent=2)
```

---

## Section 14: RelationshipStorage - Updated Class

The current RelationshipStorage (in `relationships/relationship.py` lines 1195-1363) stores data
in a separate `relationships/relationships.json` file. After consolidation, relationship data
is stored within chain_state.json under the `relationships` section.

### 14.1 Key Changes

1. Accept `ChainState` instead of `qube_data_dir`
2. Read from `chain_state.state["relationships"]`
3. Write to chain_state using accessor methods
4. Data is automatically encrypted when chain_state saves

### 14.2 Complete Updated RelationshipStorage Class

Replace the entire `RelationshipStorage` class in `relationships/relationship.py`:

```python
class RelationshipStorage:
    """
    Manages persistent storage of relationships for a Qube.

    UPDATED FOR CHAIN STATE CONSOLIDATION:
    - Data is now stored in chain_state.json under "relationships" section
    - Automatically encrypted at rest with chain_state
    - Uses ChainState accessor methods for persistence
    """

    def __init__(self, chain_state: "ChainState"):
        """
        Initialize relationship storage.

        Args:
            chain_state: ChainState instance for this qube
        """
        self.chain_state = chain_state

        # Load existing relationships from chain_state
        self.relationships: Dict[str, Relationship] = {}
        self._load_relationships()

        logger.info(
            "relationship_storage_initialized",
            qube_id=chain_state.qube_id,
            relationship_count=len(self.relationships)
        )

    def _load_relationships(self) -> None:
        """Load relationships from chain_state and apply decay."""
        relationships_data = self.chain_state.get_relationships()

        decayed_count = 0
        for entity_id, rel_data in relationships_data.items():
            rel = Relationship.from_dict(rel_data)

            # Apply decay for inactive relationships
            if rel.apply_decay():
                decayed_count += 1

            # Update days_known to current
            rel.update_days_known()

            self.relationships[entity_id] = rel

        logger.debug(
            "relationships_loaded",
            count=len(self.relationships),
            decayed_count=decayed_count
        )

        # Save if any relationships decayed
        if decayed_count > 0:
            self.save()
            logger.info(
                "relationship_decay_saved",
                decayed_count=decayed_count
            )

    def save(self) -> None:
        """Save all relationships to chain_state."""
        try:
            data = {
                entity_id: rel.to_dict()
                for entity_id, rel in self.relationships.items()
            }

            self.chain_state.update_relationships(data)

            logger.debug(
                "relationships_saved",
                count=len(self.relationships)
            )
        except Exception as e:
            logger.error(
                "relationship_save_failed",
                error=str(e),
                exc_info=True
            )
            raise

    def get_relationship(self, entity_id: str) -> Optional[Relationship]:
        """Get relationship by entity ID."""
        return self.relationships.get(entity_id)

    def create_relationship(
        self,
        entity_id: str,
        entity_type: str = "qube",
        **kwargs
    ) -> Relationship:
        """
        Create a new relationship.

        Args:
            entity_id: Entity ID
            entity_type: "qube" or "human"
            **kwargs: Additional relationship parameters

        Returns:
            New Relationship instance
        """
        if entity_id in self.relationships:
            logger.warning(
                "relationship_already_exists",
                entity_id=entity_id
            )
            return self.relationships[entity_id]

        rel = Relationship(entity_id, entity_type, **kwargs)
        self.relationships[entity_id] = rel
        self.save()

        return rel

    def update_relationship(self, relationship: Relationship) -> None:
        """Update existing relationship and save."""
        self.relationships[relationship.entity_id] = relationship
        self.save()

    def get_all_relationships(self) -> List[Relationship]:
        """Get all relationships."""
        return list(self.relationships.values())

    def get_relationships_by_status(self, status: str) -> List[Relationship]:
        """Get all relationships with specific status."""
        return [
            rel for rel in self.relationships.values()
            if rel.status == status
        ]

    def get_best_friend(self) -> Optional[Relationship]:
        """Get best friend relationship (only one allowed)."""
        for rel in self.relationships.values():
            if rel.is_best_friend:
                return rel
        return None

    def delete_relationship(self, entity_id: str) -> bool:
        """
        Delete a relationship.

        Args:
            entity_id: Entity ID to delete

        Returns:
            True if deleted, False if not found
        """
        if entity_id in self.relationships:
            del self.relationships[entity_id]
            self.save()
            logger.info("relationship_deleted", entity_id=entity_id)
            return True
        return False

    # =========================================================================
    # MIGRATION HELPER (for transitioning from old file-based storage)
    # =========================================================================

    @classmethod
    def migrate_from_file(cls, chain_state: "ChainState", qube_data_dir: Path) -> "RelationshipStorage":
        """
        Migrate relationships from old file-based storage to chain_state.

        Args:
            chain_state: ChainState instance to migrate into
            qube_data_dir: Path to qube's data directory

        Returns:
            New RelationshipStorage instance with migrated data
        """
        old_file = qube_data_dir / "relationships" / "relationships.json"

        if old_file.exists():
            try:
                with open(old_file, 'r') as f:
                    old_data = json.load(f)

                # Write to chain_state
                chain_state.update_relationships(old_data)

                logger.info(
                    "relationships_migrated_to_chain_state",
                    count=len(old_data),
                    source=str(old_file)
                )

                # Delete old file after successful migration
                old_file.unlink()

                # Try to remove empty relationships directory
                relationships_dir = qube_data_dir / "relationships"
                if relationships_dir.exists() and not any(relationships_dir.iterdir()):
                    relationships_dir.rmdir()
                    logger.info("removed_empty_relationships_directory")

            except Exception as e:
                logger.error(
                    "relationship_migration_failed",
                    error=str(e),
                    exc_info=True
                )

        return cls(chain_state)
```

### 14.3 Usage Change in Qube.__init__

In `core/qube.py`, update how RelationshipStorage is instantiated:

```python
# OLD (before consolidation):
# self.relationships = RelationshipStorage(qube_data_dir)

# NEW (after consolidation):
from relationships.relationship import RelationshipStorage

# During migration period - check if old file exists
old_relationships_file = qube_data_dir / "relationships" / "relationships.json"
if old_relationships_file.exists():
    # Migrate from file to chain_state
    self.relationship_storage = RelationshipStorage.migrate_from_file(
        self.chain_state,
        qube_data_dir
    )
else:
    # Normal initialization from chain_state
    self.relationship_storage = RelationshipStorage(self.chain_state)
```

**Note**: The `SocialDynamicsManager` still wraps `RelationshipStorage` - that class doesn't change,
only the underlying storage mechanism.

---

## Section 15: SkillsManager - Updated Class

The current SkillsManager (in `utils/skills_manager.py`) stores data in separate files:
- `skills/skills.json` - Current skill states (levels, XP, unlocked status)
- `skills/skill_history.json` - Historical skill progression events

After consolidation, this data is stored within chain_state.json under the `skills` section.

### 15.1 Key Changes

1. Accept `ChainState` instead of `qube_dir`
2. Read from `chain_state.state["skills"]`
3. Write to chain_state using accessor methods
4. History is stored in `chain_state.state["skills"]["history"]` (capped at MAX_SKILL_HISTORY=100)
5. Data is automatically encrypted when chain_state saves

### 15.2 Complete Updated SkillsManager Class

Replace the entire `SkillsManager` class in `utils/skills_manager.py`:

```python
"""
Skills Manager - Handles skill progression, XP tracking, and unlocking for Qubes

UPDATED FOR CHAIN STATE CONSOLIDATION:
- Skills data now stored in chain_state.json under "skills" section
- Automatically encrypted at rest with chain_state
- History limited to MAX_SKILL_HISTORY entries

Storage Structure (within chain_state.json):
    skills: {
        last_updated: "2025-01-15T12:00:00Z",
        skills: [...],  // Array of skill objects
        history: [...]  // Capped at 100 entries
    }
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional, TYPE_CHECKING
from datetime import datetime
import structlog

if TYPE_CHECKING:
    from core.chain_state import ChainState

logger = structlog.get_logger(__name__)

# Maximum skill history entries to retain
MAX_SKILL_HISTORY = 100


class SkillsManager:
    """
    Manages skill progression and persistence for a single Qube.

    UPDATED FOR CHAIN STATE CONSOLIDATION:
    - Data stored in chain_state.json under "skills" section
    - Automatically encrypted at rest
    - Uses ChainState accessor methods for persistence
    """

    def __init__(self, chain_state: "ChainState"):
        """
        Initialize SkillsManager for a specific qube.

        Args:
            chain_state: ChainState instance for this qube
        """
        self.chain_state = chain_state

    def load_skills(self) -> Dict[str, Any]:
        """
        Load current skill states from chain_state.

        Returns:
            Dictionary containing skills data or default structure if empty
        """
        skills_section = self.chain_state.state.get("skills", {})

        if not skills_section.get("skills"):
            logger.info("No skills found in chain_state, initializing default skills")
            return self._initialize_default_skills()

        logger.debug(f"Loaded {len(skills_section.get('skills', []))} skills from chain_state")
        return skills_section

    def save_skills(self, skills_data: Dict[str, Any]) -> bool:
        """
        Save skill states to chain_state.

        Args:
            skills_data: Dictionary containing skills data

        Returns:
            True if successful, False otherwise
        """
        try:
            # Update last_updated timestamp
            skills_data["last_updated"] = datetime.utcnow().isoformat() + "Z"

            # Update chain_state
            self.chain_state.state["skills"] = skills_data
            self.chain_state._save()

            logger.info(f"Saved {len(skills_data.get('skills', []))} skills to chain_state")
            return True

        except Exception as e:
            logger.error(f"Failed to save skills to chain_state: {e}")
            return False

    def _initialize_default_skills(self) -> Dict[str, Any]:
        """
        Initialize default skill structure with all skills locked at level 0.

        Generates the complete skill tree matching the frontend skillDefinitions.ts
        Structure: 7 categories, each with 1 sun + 5 planets + 10 moons

        Returns:
            Default skills data structure with all skills initialized
        """
        from utils.skill_definitions import generate_all_skills

        skills = generate_all_skills()

        default_skills = {
            "last_updated": datetime.utcnow().isoformat() + "Z",
            "skills": skills,
            "history": []  # Start with empty history
        }

        logger.info(f"Initialized {len(skills)} default skills")

        # Save the initialized skills
        self.save_skills(default_skills)

        return default_skills

    def add_xp(
        self,
        skill_id: str,
        xp_amount: int,
        evidence_block_id: Optional[str] = None,
        evidence_description: Optional[str] = None,
        tool_details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Add XP to a specific skill and handle level-ups.

        If the skill is locked, XP flows to the unlocked parent:
        - Locked moon -> parent planet (if unlocked) -> else parent sun (always unlocked)
        - Locked planet -> parent sun (always unlocked)

        Args:
            skill_id: ID of the skill to add XP to
            xp_amount: Amount of XP to add
            evidence_block_id: Optional block ID that contributed this XP
            evidence_description: Optional description of how skill was demonstrated
            tool_details: Optional dict with tool-specific details (query, url, prompt, etc.)

        Returns:
            Dictionary with result including level_up status
        """
        skills_data = self.load_skills()

        # Find the skill
        skill = None
        for s in skills_data["skills"]:
            if s["id"] == skill_id:
                skill = s
                break

        if not skill:
            logger.warning(f"Skill {skill_id} not found")
            return {"success": False, "error": f"Skill {skill_id} not found"}

        # If skill is locked, flow XP to unlocked parent
        original_skill_id = skill_id
        xp_flowed_to_parent = False

        if not skill.get("unlocked", False):
            xp_flowed_to_parent = True
            parent_id = skill.get("parentSkill")
            if parent_id:
                parent_skill = None
                for s in skills_data["skills"]:
                    if s["id"] == parent_id:
                        parent_skill = s
                        break

                if parent_skill:
                    if parent_skill.get("unlocked", False):
                        skill = parent_skill
                        skill_id = parent_id
                        logger.info(f"Skill {original_skill_id} is locked, flowing XP to parent {skill_id}")
                    else:
                        grandparent_id = parent_skill.get("parentSkill")
                        if grandparent_id:
                            for s in skills_data["skills"]:
                                if s["id"] == grandparent_id:
                                    skill = s
                                    skill_id = grandparent_id
                                    logger.info(f"Skill {original_skill_id} and parent {parent_id} locked, flowing to sun {skill_id}")
                                    break

        # Add XP
        old_xp = skill["xp"]
        old_level = skill["level"]
        skill["xp"] += xp_amount

        # Add evidence if provided
        if evidence_block_id:
            if "evidence" not in skill:
                skill["evidence"] = []

            evidence_entry = {
                "block_id": evidence_block_id,
                "xp_gained": xp_amount,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            if evidence_description:
                evidence_entry["description"] = evidence_description

            skill["evidence"].append(evidence_entry)

        # Check for level-up
        max_xp = skill["maxXP"]
        leveled_up = False
        new_levels = 0

        while skill["xp"] >= max_xp and skill["level"] < 100:
            skill["xp"] -= max_xp
            skill["level"] += 1
            new_levels += 1
            leveled_up = True

            # Update tier based on level
            if skill["level"] >= 75:
                skill["tier"] = "expert"
            elif skill["level"] >= 50:
                skill["tier"] = "advanced"
            elif skill["level"] >= 25:
                skill["tier"] = "intermediate"
            else:
                skill["tier"] = "novice"

        # Cap at max level
        if skill["level"] >= 100:
            skill["level"] = 100
            skill["xp"] = max_xp

        # Propagate XP to children
        children_updated = []
        for child_skill in skills_data["skills"]:
            if child_skill.get("parentSkill") == skill_id:
                child_old_xp = child_skill["xp"]
                child_old_level = child_skill["level"]
                child_skill["xp"] += xp_amount

                child_max_xp = child_skill["maxXP"]
                child_leveled_up = False
                child_new_levels = 0

                while child_skill["xp"] >= child_max_xp and child_skill["level"] < 100:
                    child_skill["xp"] -= child_max_xp
                    child_skill["level"] += 1
                    child_new_levels += 1
                    child_leveled_up = True

                if child_skill["level"] >= 100:
                    child_skill["level"] = 100
                    child_skill["xp"] = child_max_xp

                children_updated.append({
                    "skill_id": child_skill["id"],
                    "xp_gained": xp_amount,
                    "old_level": child_old_level,
                    "new_level": child_skill["level"],
                    "leveled_up": child_leveled_up
                })

                logger.debug(f"Propagated {xp_amount} XP to child skill {child_skill['id']}")

        # Save updated skills
        self.save_skills(skills_data)

        # Log to history
        event_data = {
            "event": "xp_gained",
            "skill_id": skill_id,
            "xp_amount": xp_amount,
            "old_xp": old_xp,
            "new_xp": skill["xp"],
            "old_level": old_level,
            "new_level": skill["level"],
            "leveled_up": leveled_up,
            "levels_gained": new_levels,
            "evidence_block_id": evidence_block_id,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        if xp_flowed_to_parent:
            event_data["original_skill_id"] = original_skill_id
            event_data["xp_flowed_to_parent"] = True

        if evidence_description:
            event_data["evidence_description"] = evidence_description

        if tool_details:
            event_data["tool_details"] = tool_details

        if children_updated:
            event_data["children_updated"] = children_updated

        self._log_skill_event(event_data)

        result = {
            "success": True,
            "skill_id": skill_id,
            "old_level": old_level,
            "new_level": skill["level"],
            "xp_gained": xp_amount,
            "current_xp": skill["xp"],
            "max_xp": max_xp,
            "leveled_up": leveled_up,
            "levels_gained": new_levels
        }

        if children_updated:
            result["children_updated"] = children_updated
            logger.info(f"XP propagated to {len(children_updated)} child skill(s)")

        if skill["level"] == 100 and skill.get("toolCallReward"):
            result["tool_unlocked"] = skill["toolCallReward"]
            logger.info(f"Skill {skill_id} maxed! Unlocked tool: {skill['toolCallReward']}")

        return result

    def unlock_skill(self, skill_id: str) -> Dict[str, Any]:
        """
        Unlock a skill (check prerequisites first).

        Args:
            skill_id: ID of skill to unlock

        Returns:
            Dictionary with result
        """
        skills_data = self.load_skills()

        skill = None
        for s in skills_data["skills"]:
            if s["id"] == skill_id:
                skill = s
                break

        if not skill:
            return {"success": False, "error": f"Skill {skill_id} not found"}

        if skill.get("unlocked", False):
            return {"success": False, "error": f"Skill {skill_id} is already unlocked"}

        # Check prerequisite
        if skill.get("prerequisite"):
            prereq_id = skill["prerequisite"]
            prereq_skill = None
            for s in skills_data["skills"]:
                if s["id"] == prereq_id:
                    prereq_skill = s
                    break

            if not prereq_skill or not prereq_skill.get("unlocked", False):
                return {
                    "success": False,
                    "error": f"Prerequisite skill {prereq_id} must be unlocked first"
                }

        # Unlock the skill
        skill["unlocked"] = True
        self.save_skills(skills_data)

        # Log event
        self._log_skill_event({
            "event": "skill_unlocked",
            "skill_id": skill_id,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })

        logger.info(f"Unlocked skill: {skill_id}")
        return {"success": True, "skill_id": skill_id}

    def get_skill_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all skills organized by category.

        Returns:
            Dictionary with skill summary statistics
        """
        skills_data = self.load_skills()

        summary = {
            "total_skills": len(skills_data.get("skills", [])),
            "unlocked_skills": 0,
            "maxed_skills": 0,
            "total_xp": 0,
            "by_category": {},
            "unlocked_tools": []
        }

        for skill in skills_data.get("skills", []):
            if skill.get("unlocked", False):
                summary["unlocked_skills"] += 1
            if skill.get("level", 0) == 100:
                summary["maxed_skills"] += 1
                if skill.get("toolCallReward"):
                    summary["unlocked_tools"].append(skill["toolCallReward"])

            summary["total_xp"] += skill.get("xp", 0)

            category_id = skill.get("category", "unknown")
            if category_id not in summary["by_category"]:
                summary["by_category"][category_id] = {
                    "total": 0,
                    "unlocked": 0,
                    "maxed": 0,
                    "avg_level": 0.0
                }

            cat = summary["by_category"][category_id]
            cat["total"] += 1
            if skill.get("unlocked", False):
                cat["unlocked"] += 1
            if skill.get("level", 0) == 100:
                cat["maxed"] += 1

        # Calculate average levels
        for category_id, cat in summary["by_category"].items():
            if cat["total"] > 0:
                total_levels = sum(
                    s.get("level", 0)
                    for s in skills_data.get("skills", [])
                    if s.get("category") == category_id
                )
                cat["avg_level"] = total_levels / cat["total"]

        return summary

    def _log_skill_event(self, event_data: Dict[str, Any]) -> None:
        """
        Log a skill event to history (capped at MAX_SKILL_HISTORY).

        Args:
            event_data: Event data to log
        """
        try:
            skills_data = self.chain_state.state.get("skills", {})
            history = skills_data.get("history", [])

            # Append new event
            history.append(event_data)

            # Cap at MAX_SKILL_HISTORY
            if len(history) > MAX_SKILL_HISTORY:
                history = history[-MAX_SKILL_HISTORY:]

            skills_data["history"] = history
            self.chain_state.state["skills"] = skills_data
            self.chain_state._save()

        except Exception as e:
            logger.error(f"Failed to log skill event: {e}")

    # =========================================================================
    # MIGRATION HELPER (for transitioning from old file-based storage)
    # =========================================================================

    @classmethod
    def migrate_from_files(cls, chain_state: "ChainState", qube_dir: Path) -> "SkillsManager":
        """
        Migrate skills from old file-based storage to chain_state.

        Args:
            chain_state: ChainState instance to migrate into
            qube_dir: Path to qube's data directory

        Returns:
            New SkillsManager instance with migrated data
        """
        skills_file = qube_dir / "skills" / "skills.json"
        history_file = qube_dir / "skills" / "skill_history.json"

        migrated_data = {}

        # Migrate skills.json
        if skills_file.exists():
            try:
                with open(skills_file, 'r', encoding='utf-8') as f:
                    old_skills = json.load(f)
                migrated_data = old_skills
                logger.info(f"Migrated {len(old_skills.get('skills', []))} skills from {skills_file}")
            except Exception as e:
                logger.error(f"Failed to migrate skills: {e}")

        # Migrate skill_history.json
        if history_file.exists():
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    old_history = json.load(f)
                # Cap history during migration
                if len(old_history) > MAX_SKILL_HISTORY:
                    old_history = old_history[-MAX_SKILL_HISTORY:]
                migrated_data["history"] = old_history
                logger.info(f"Migrated {len(old_history)} skill history events")
            except Exception as e:
                logger.error(f"Failed to migrate skill history: {e}")

        # Write to chain_state
        if migrated_data:
            chain_state.state["skills"] = migrated_data
            chain_state._save()

            # Delete old files
            try:
                if skills_file.exists():
                    skills_file.unlink()
                if history_file.exists():
                    history_file.unlink()

                # Remove empty skills directory
                skills_dir = qube_dir / "skills"
                if skills_dir.exists() and not any(skills_dir.iterdir()):
                    skills_dir.rmdir()
                    logger.info("Removed empty skills directory")
            except Exception as e:
                logger.warning(f"Failed to cleanup old skill files: {e}")

        return cls(chain_state)
```

### 15.3 Usage Change in Qube.__init__

In `core/qube.py`, update how SkillsManager is instantiated:

```python
# OLD (before consolidation):
# self.skills_manager = SkillsManager(qube_data_dir)

# NEW (after consolidation):
from utils.skills_manager import SkillsManager

# During migration period - check if old files exist
old_skills_file = qube_data_dir / "skills" / "skills.json"
if old_skills_file.exists():
    # Migrate from files to chain_state
    self.skills_manager = SkillsManager.migrate_from_files(
        self.chain_state,
        qube_data_dir
    )
else:
    # Normal initialization from chain_state
    self.skills_manager = SkillsManager(self.chain_state)
```

---

## Section 16: WalletTxManager - Updated Storage Methods

The current WalletTransactionManager (in `blockchain/wallet_tx.py`) stores data in separate files:
- `pending_transactions.json` - Pending transactions awaiting approval
- `transaction_history.json` - Completed transaction records
- `balance_cache.json` - Cached balance for fast startup

After consolidation, this data is stored within chain_state.json under the `financial` section:
- `financial.pending[]` - Pending transactions
- `financial.transaction_history[]` - Completed transactions (capped at MAX_TRANSACTION_HISTORY=50)
- `financial.balance_cache` - Cached balance object

### 16.1 Key Changes

1. Replace file-based storage with ChainState accessors
2. Transaction history capped at 50 entries
3. Pending transactions stored as array in chain_state
4. Data automatically encrypted when chain_state saves

### 16.2 Updated Storage Methods

The WalletTransactionManager class only needs its storage methods updated. Replace the storage-related
methods (around lines 163-700) while keeping the transaction logic intact:

```python
class WalletTransactionManager:
    """
    Manages transactions for a Qube's wallet.

    UPDATED FOR CHAIN STATE CONSOLIDATION:
    - Pending transactions stored in chain_state.json under "financial.pending"
    - Transaction history stored in "financial.transaction_history" (capped at 50)
    - Balance cache stored in "financial.balance_cache"
    - Data automatically encrypted at rest
    """

    # Pending transactions expire after 24 hours
    DEFAULT_EXPIRY_HOURS = 24

    # Maximum transaction history entries
    MAX_TRANSACTION_HISTORY = 50

    def __init__(self, qube, chain_state: "ChainState"):
        """
        Initialize transaction manager for a Qube.

        Args:
            qube: Qube instance with wallet info in genesis block
            chain_state: ChainState instance for persistence
        """
        self.qube = qube
        self.qube_id = qube.qube_id
        self.chain_state = chain_state

        # Get wallet info from genesis block (handle both Block and SimpleNamespace)
        if not qube.genesis_block:
            raise ValueError(f"Qube {qube.qube_id} does not have genesis block")

        genesis = qube.genesis_block
        if hasattr(genesis, 'content') and isinstance(genesis.content, dict):
            wallet_info = genesis.content.get("wallet")
        elif hasattr(genesis, 'wallet'):
            wallet_info = genesis.wallet
            if hasattr(wallet_info, '__dict__') and not isinstance(wallet_info, dict):
                wallet_info = vars(wallet_info)
        else:
            wallet_info = None

        if not wallet_info:
            raise ValueError(f"Qube {qube.qube_id} does not have wallet info in genesis block")

        self.owner_pubkey = wallet_info.get("owner_pubkey")
        self.p2sh_address = wallet_info.get("p2sh_address")

        if not self.owner_pubkey or not self.p2sh_address:
            raise ValueError(f"Qube {qube.qube_id} has incomplete wallet info")

        # Create wallet instance
        from crypto.keys import get_raw_private_key_bytes
        private_key_bytes = get_raw_private_key_bytes(qube.private_key)
        self.wallet = QubeWallet(
            qube_private_key=private_key_bytes,
            owner_pubkey_hex=self.owner_pubkey,
            network="mainnet"
        )

        # In-memory cache (loaded from chain_state)
        self._pending_txs: Dict[str, PendingTx] = {}
        self._load_pending_transactions()

        # Load persisted balance cache into wallet
        self._load_balance_cache()

        logger.debug(
            "wallet_tx_manager_initialized",
            qube_id=self.qube_id,
            p2sh_address=self.p2sh_address
        )

    # =========================================================================
    # STORAGE METHODS - UPDATED FOR CHAIN STATE
    # =========================================================================

    def _load_pending_transactions(self) -> None:
        """Load pending transactions from chain_state."""
        financial = self.chain_state.state.get("financial", {})
        pending_list = financial.get("pending", [])

        self._pending_txs = {}
        for tx_data in pending_list:
            try:
                tx = PendingTx.from_dict(tx_data)
                self._pending_txs[tx.tx_id] = tx
            except Exception as e:
                logger.warning(f"Failed to load pending tx: {e}")

        logger.debug(f"Loaded {len(self._pending_txs)} pending transactions from chain_state")

    def _save_pending_transactions(self) -> None:
        """Save pending transactions to chain_state."""
        try:
            pending_list = [tx.to_dict() for tx in self._pending_txs.values()]

            financial = self.chain_state.state.setdefault("financial", {})
            financial["pending"] = pending_list
            self.chain_state._save()

            logger.debug(f"Saved {len(pending_list)} pending transactions to chain_state")
        except Exception as e:
            logger.error(f"Failed to save pending transactions: {e}")

    def _load_balance_cache(self) -> None:
        """Load persisted balance cache from chain_state into wallet's in-memory cache."""
        try:
            financial = self.chain_state.state.get("financial", {})
            cache_data = financial.get("balance_cache", {})

            cached_balance = cache_data.get("balance")
            cached_timestamp = cache_data.get("timestamp", 0)

            if cached_balance is not None:
                self.wallet._cached_balance = cached_balance
                self.wallet._balance_last_updated = cached_timestamp
                logger.debug(
                    "balance_cache_loaded",
                    balance=cached_balance,
                    cache_age=int(time.time() - cached_timestamp)
                )
        except Exception as e:
            logger.debug(f"Could not load balance cache: {e}")

    def _save_balance_cache(self, balance: int) -> None:
        """Persist balance to chain_state for fast startup."""
        try:
            financial = self.chain_state.state.setdefault("financial", {})
            financial["balance_cache"] = {
                "balance": balance,
                "timestamp": time.time(),
                "address": self.p2sh_address
            }
            self.chain_state._save()
            logger.debug("balance_cache_saved", balance=balance)
        except Exception as e:
            logger.debug(f"Could not save balance cache: {e}")

    def _add_to_history(self, entry: TxHistoryEntry) -> None:
        """Add transaction to history (capped at MAX_TRANSACTION_HISTORY)."""
        try:
            financial = self.chain_state.state.setdefault("financial", {})
            history = financial.get("transaction_history", [])

            # Append new entry
            history.append(entry.to_dict())

            # Cap at MAX_TRANSACTION_HISTORY
            if len(history) > self.MAX_TRANSACTION_HISTORY:
                history = history[-self.MAX_TRANSACTION_HISTORY:]

            financial["transaction_history"] = history
            self.chain_state._save()

            logger.debug(f"Added transaction to history, total: {len(history)}")
        except Exception as e:
            logger.error(f"Failed to add transaction to history: {e}")

    def get_local_history(self) -> List[TxHistoryEntry]:
        """Get transaction history from chain_state."""
        financial = self.chain_state.state.get("financial", {})
        history_data = financial.get("transaction_history", [])

        history = []
        for entry_data in history_data:
            try:
                # Handle both dict and TxHistoryEntry
                if isinstance(entry_data, dict):
                    history.append(TxHistoryEntry(**entry_data))
                else:
                    history.append(entry_data)
            except Exception as e:
                logger.warning(f"Failed to parse history entry: {e}")

        return history

    # =========================================================================
    # MIGRATION HELPER
    # =========================================================================

    @classmethod
    def migrate_from_files(cls, qube, chain_state: "ChainState", data_dir: Path) -> "WalletTransactionManager":
        """
        Migrate wallet data from old file-based storage to chain_state.

        Args:
            qube: Qube instance
            chain_state: ChainState instance to migrate into
            data_dir: Path to qube's data directory

        Returns:
            New WalletTransactionManager instance with migrated data
        """
        pending_file = data_dir / "pending_transactions.json"
        history_file = data_dir / "transaction_history.json"
        balance_file = data_dir / "balance_cache.json"

        financial = chain_state.state.setdefault("financial", {})

        # Migrate pending transactions
        if pending_file.exists():
            try:
                with open(pending_file, 'r') as f:
                    pending_data = json.load(f)
                financial["pending"] = list(pending_data.values())
                logger.info(f"Migrated {len(pending_data)} pending transactions")
            except Exception as e:
                logger.error(f"Failed to migrate pending transactions: {e}")

        # Migrate transaction history
        if history_file.exists():
            try:
                with open(history_file, 'r') as f:
                    history_data = json.load(f)
                # Cap during migration
                if len(history_data) > 50:
                    history_data = history_data[-50:]
                financial["transaction_history"] = history_data
                logger.info(f"Migrated {len(history_data)} transaction history entries")
            except Exception as e:
                logger.error(f"Failed to migrate transaction history: {e}")

        # Migrate balance cache
        if balance_file.exists():
            try:
                with open(balance_file, 'r') as f:
                    balance_data = json.load(f)
                financial["balance_cache"] = balance_data
                logger.info("Migrated balance cache")
            except Exception as e:
                logger.error(f"Failed to migrate balance cache: {e}")

        # Save to chain_state
        chain_state._save()

        # Delete old files
        try:
            for old_file in [pending_file, history_file, balance_file]:
                if old_file.exists():
                    old_file.unlink()
                    logger.info(f"Deleted old file: {old_file}")
        except Exception as e:
            logger.warning(f"Failed to cleanup old wallet files: {e}")

        return cls(qube, chain_state)
```

### 16.3 Usage Change

In any code that creates WalletTransactionManager, update to pass chain_state:

```python
# OLD (before consolidation):
# self.wallet_manager = WalletTransactionManager(qube, data_dir=qube_data_dir)

# NEW (after consolidation):
from blockchain.wallet_tx import WalletTransactionManager

# During migration period - check if old files exist
old_pending_file = qube_data_dir / "pending_transactions.json"
if old_pending_file.exists():
    # Migrate from files to chain_state
    self.wallet_manager = WalletTransactionManager.migrate_from_files(
        self,  # qube
        self.chain_state,
        qube_data_dir
    )
else:
    # Normal initialization from chain_state
    self.wallet_manager = WalletTransactionManager(self, self.chain_state)
```

---

## Section 17: Qube.__init__ - Complete Updated Code

This section shows the exact changes needed in `core/qube.py` to integrate all the consolidation updates.
The changes are localized to the `__init__` method around lines 170-230.

### 17.1 Summary of Changes

1. **ChainState initialization**: Now requires encryption key
2. **Encryption key storage**: Save encrypted for gui_bridge access
3. **RelationshipStorage**: Now takes ChainState, with file migration
4. **SkillsManager**: Now takes ChainState, with file migration
5. **WalletTransactionManager**: Now takes ChainState, with file migration

### 17.2 Complete Updated __init__ Section

Replace lines 170-230 in `core/qube.py` with:

```python
        # Save genesis.json in chain/ folder (for backward compatibility and easy access)
        genesis_path = qube_data_dir / "chain" / "genesis.json"
        import json
        with open(genesis_path, 'w') as f:
            json.dump(self.genesis_block.to_dict() if hasattr(self.genesis_block, 'to_dict') else genesis_dict, f, indent=2)

        # =====================================================================
        # ENCRYPTION KEY SETUP
        # =====================================================================

        # Generate or load encryption key for this qube
        self.encryption_key = generate_encryption_key()

        # Save encryption key encrypted by master key (for gui_bridge access)
        # This allows gui_bridge to access chain_state without loading full qube
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        import secrets as crypto_secrets

        encryption_key_file = qube_data_dir / "chain" / "encryption_key.enc"
        if orchestrator and orchestrator.master_key and not encryption_key_file.exists():
            aesgcm = AESGCM(orchestrator.master_key)
            nonce = crypto_secrets.token_bytes(12)
            ciphertext = aesgcm.encrypt(nonce, self.encryption_key, None)

            with open(encryption_key_file, 'w') as f:
                json.dump({
                    "nonce": nonce.hex(),
                    "ciphertext": ciphertext.hex(),
                    "algorithm": "AES-256-GCM",
                    "version": "1.0"
                }, f, indent=2)

        # =====================================================================
        # CHAIN STATE INITIALIZATION (with encryption)
        # =====================================================================

        # Initialize chain state in chain/ folder with encryption
        chain_dir = qube_data_dir / "chain"
        self.chain_state = ChainState(
            data_dir=chain_dir,
            encryption_key=self.encryption_key,
            qube_id=qube_id
        )

        # Update chain state with genesis block (only if new qube)
        if is_new_qube:
            self.chain_state.update_chain(
                chain_length=1,
                last_block_number=0,
                last_block_hash=self.genesis_block.block_hash
            )
            self.chain_state.increment_block_count("GENESIS")

        # =====================================================================
        # RELATIONSHIP STORAGE (migrates from file if needed)
        # =====================================================================

        from relationships.relationship import RelationshipStorage

        old_relationships_file = qube_data_dir / "relationships" / "relationships.json"
        if old_relationships_file.exists():
            # Migrate from old file-based storage to chain_state
            relationship_storage = RelationshipStorage.migrate_from_file(
                self.chain_state,
                qube_data_dir
            )
        else:
            # Normal initialization from chain_state
            relationship_storage = RelationshipStorage(self.chain_state)

        # SocialDynamicsManager wraps RelationshipStorage
        trust_profile = None  # Could be set from genesis block or user preferences
        self.relationships = SocialDynamicsManager(
            relationship_storage=relationship_storage,
            trust_profile=trust_profile,
            qube=self
        )

        # =====================================================================
        # SKILLS MANAGER (migrates from files if needed)
        # =====================================================================

        from utils.skills_manager import SkillsManager

        old_skills_file = qube_data_dir / "skills" / "skills.json"
        if old_skills_file.exists():
            # Migrate from old file-based storage to chain_state
            self.skills_manager = SkillsManager.migrate_from_files(
                self.chain_state,
                qube_data_dir
            )
        else:
            # Normal initialization from chain_state
            self.skills_manager = SkillsManager(self.chain_state)

        # =====================================================================
        # SESSION MANAGEMENT
        # =====================================================================

        self.current_session: Optional[Session] = None
        self.auto_anchor_enabled = self.chain_state.is_auto_anchor_enabled()
        self.auto_anchor_threshold = self.chain_state.get_auto_anchor_threshold()

        # Game management (chess, etc.)
        self.game_manager = GameManager(self)

        # AI configuration
        self.current_ai_model = self.genesis_block.ai_model
        self.api_keys: Dict[str, str] = {}  # Populated after creation
        self.reasoner = None  # Initialized with init_ai()
        self.tool_registry = None  # Initialized with init_ai()
        self.semantic_search = None  # Initialized in background thread

        # Decision Intelligence configuration
        from config.user_preferences import UserPreferencesManager
        user_prefs_dir = qube_data_dir.parent.parent
        prefs_manager = UserPreferencesManager(user_prefs_dir)
        self.decision_config = prefs_manager.get_decision_config()

        # Audio configuration
        # ... (rest of __init__ continues unchanged)
```

### 17.3 SocialDynamicsManager Update

The `SocialDynamicsManager` class needs a minor update to accept `RelationshipStorage` directly
instead of creating it internally. Update in `relationships/social_dynamics.py`:

```python
class SocialDynamicsManager:
    """
    Manages social dynamics for a Qube including relationships and trust.

    UPDATED: Now accepts RelationshipStorage instance instead of qube_data_dir
    """

    def __init__(
        self,
        relationship_storage: RelationshipStorage,  # Changed from qube_data_dir
        trust_profile: Optional[str] = None,
        qube: Optional["Qube"] = None
    ):
        """
        Initialize social dynamics manager.

        Args:
            relationship_storage: RelationshipStorage instance (already initialized)
            trust_profile: Optional trust profile name
            qube: Optional Qube instance for context
        """
        self.storage = relationship_storage  # Use provided storage
        self.qube = qube

        # Trust configuration
        self.trust_config = self._get_trust_config(trust_profile)

        logger.info(
            "social_dynamics_manager_initialized",
            relationship_count=len(self.storage.relationships),
            trust_profile=trust_profile or "default"
        )
```

### 17.4 WalletTransactionManager Initialization

If you're using WalletTransactionManager somewhere in the Qube class (it may be lazily loaded),
update that location too:

```python
# Wherever WalletTransactionManager is initialized (often in a method, not __init__):
from blockchain.wallet_tx import WalletTransactionManager

def _init_wallet_manager(self):
    """Initialize wallet transaction manager."""
    old_pending_file = self.data_dir / "pending_transactions.json"
    if old_pending_file.exists():
        self.wallet_manager = WalletTransactionManager.migrate_from_files(
            self,
            self.chain_state,
            self.data_dir
        )
    else:
        self.wallet_manager = WalletTransactionManager(self, self.chain_state)
```

---

## Section 18: Files to Delete After Migration

After all qubes have been migrated, these files/directories can be removed (migration handles deletion
automatically, but this serves as a checklist):

### Per-Qube Files (in `data/users/{user}/qubes/{qube}/`):

```
relationships/
    relationships.json          # Migrated to chain_state.json -> relationships

skills/
    skills.json                 # Migrated to chain_state.json -> skills
    skill_history.json          # Migrated to chain_state.json -> skills.history

pending_transactions.json       # Migrated to chain_state.json -> financial.pending
transaction_history.json        # Migrated to chain_state.json -> financial.transaction_history
balance_cache.json              # Migrated to chain_state.json -> financial.balance_cache
```

### Files That Remain:

```
chain/
    genesis.json                # Kept for easy access/debugging
    qube_metadata.json          # Immutable identity info
    chain_state.json            # NEW: All consolidated state (encrypted)
    encryption_key.enc          # NEW: Encrypted qube key for gui_bridge
    chain_state.json.bak        # NEW: Backup of last good state

blocks/
    permanent/                  # Block files stay as-is
    pending/                    # Pending blocks stay as-is

snapshots/                      # Active feature - not migrated
shared_memory/                  # Active feature - not migrated
```

---

## Section 19: Implementation Checklist

Use this checklist when implementing the consolidation:

### Phase 1: Core Infrastructure
- [ ] Add `derive_chain_state_key()` to `crypto/encryption.py`
- [ ] Update `core/chain_state.py` with new encrypted ChainState class
- [ ] Test encryption/decryption works correctly

### Phase 2: Storage Class Updates
- [ ] Update `RelationshipStorage` in `relationships/relationship.py`
- [ ] Update `SkillsManager` in `utils/skills_manager.py`
- [ ] Update `WalletTransactionManager` in `blockchain/wallet_tx.py`
- [ ] Add migration helpers to each class

### Phase 3: Integration
- [ ] Update `core/qube.py` __init__ to use new classes
- [ ] Update `SocialDynamicsManager` to accept RelationshipStorage
- [ ] Test migration from old file format works

### Phase 4: GUI Bridge
- [ ] Update `gui_bridge.py` with `_get_chain_state()` method
- [ ] Update all model control methods to use encrypted ChainState
- [ ] Test GUI settings persist correctly

### Phase 5: Testing
- [ ] Create new qube - verify chain_state.json encrypted
- [ ] Load existing qube - verify migration works
- [ ] Test relationships save/load through chain_state
- [ ] Test skills save/load through chain_state
- [ ] Test wallet transactions through chain_state
- [ ] Test gui_bridge settings work
- [ ] Verify old files are deleted after migration

### Phase 6: Cleanup
- [ ] Remove deprecated file-based code paths (after migration period)
- [ ] Update any remaining direct file access
- [ ] Update documentation

---

---

## Section 20: CRITICAL - Additional Call Sites to Update

**This section addresses call sites discovered during review that are NOT covered in earlier sections.**

The blueprint's core changes affect SkillsManager and RelationshipStorage constructors. However,
these classes are instantiated directly in MANY places beyond Qube.__init__. All these must be updated.

### 20.1 SkillsManager Direct Instantiations

These files instantiate `SkillsManager(qube_dir)` directly and need updating:

| File | Line | Context | Fix |
|------|------|---------|-----|
| `gui_bridge.py` | 1919 | `get_qube_skills()` | Use `_get_chain_state()` |
| `gui_bridge.py` | 1965 | `save_qube_skills()` | Use `_get_chain_state()` |
| `gui_bridge.py` | 2007 | `add_skill_xp()` | Use `_get_chain_state()` |
| `gui_bridge.py` | 2039 | `unlock_skill()` | Use `_get_chain_state()` |
| `gui_bridge.py` | 5417 | Meeting session code | Use `qube.chain_state` |
| `gui_bridge.py` | 6108 | Skills display | Use `qube.chain_state` |
| `user_orchestrator.py` | 2242 | Orchestrator | Use `qube.chain_state` |
| `ai/skill_scanner.py` | 395 | Skill scanning | Use `self.qube.chain_state` |
| `ai/reasoner.py` | 359, 1804 | AI reasoning | Use `self.qube.chain_state` |
| `ai/tools/handlers.py` | 1137 | Tool handlers | Use `qube.chain_state` |

### 20.2 RelationshipStorage Direct Instantiations

These files instantiate `RelationshipStorage(qube_dir)` directly:

| File | Line | Context | Fix |
|------|------|---------|-----|
| `gui_bridge.py` | 1418 | `get_qube_relationships()` no-password path | Use `_get_chain_state()` |
| `gui_bridge.py` | 2785 | Relationship access | Use `_get_chain_state()` |
| `relationships/social.py` | 51 | SocialDynamicsManager | Accept RelationshipStorage as param |

### 20.3 Updated gui_bridge Skills Methods

Replace the skills methods in gui_bridge.py (lines 1891-2068):

```python
async def get_qube_skills(self, user_id: str, qube_id: str) -> Dict[str, Any]:
    """Get all skills for a specific qube - UPDATED FOR CHAIN STATE"""
    try:
        from utils.skills_manager import SkillsManager

        # SECURITY: Validate inputs
        from utils.input_validation import validate_user_id, validate_qube_id
        user_id = validate_user_id(user_id)
        qube_id = validate_qube_id(qube_id)

        # Get ChainState with encryption support
        chain_state = self._get_chain_state(qube_id)
        if not chain_state:
            return {
                "success": False,
                "error": f"Qube {qube_id} not found or not accessible (authentication required)"
            }

        # Load skills from chain_state
        skills_manager = SkillsManager(chain_state)
        skills_data = skills_manager.load_skills()

        return {
            "success": True,
            "qube_id": qube_id,
            "skills": skills_data.get("skills", []),
            "last_updated": skills_data.get("last_updated"),
            "summary": skills_manager.get_skill_summary()
        }

    except Exception as e:
        logger.error(f"Failed to get skills for qube {qube_id}: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }

async def save_qube_skills(self, user_id: str, qube_id: str, skills_data: Dict[str, Any]) -> Dict[str, Any]:
    """Save skills for a specific qube - UPDATED FOR CHAIN STATE"""
    try:
        from utils.skills_manager import SkillsManager

        # SECURITY: Validate inputs
        from utils.input_validation import validate_user_id, validate_qube_id
        user_id = validate_user_id(user_id)
        qube_id = validate_qube_id(qube_id)

        # Get ChainState with encryption support
        chain_state = self._get_chain_state(qube_id)
        if not chain_state:
            return {
                "success": False,
                "error": f"Qube {qube_id} not found or not accessible"
            }

        # Save skills via chain_state
        skills_manager = SkillsManager(chain_state)
        success = skills_manager.save_skills(skills_data)

        if success:
            return {
                "success": True,
                "qube_id": qube_id,
                "message": "Skills saved successfully"
            }
        else:
            return {
                "success": False,
                "error": "Failed to save skills"
            }

    except Exception as e:
        logger.error(f"Failed to save skills for qube {qube_id}: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }

async def add_skill_xp(self, user_id: str, qube_id: str, skill_id: str, xp_amount: int, evidence_block_id: Optional[str] = None) -> Dict[str, Any]:
    """Add XP to a specific skill - UPDATED FOR CHAIN STATE"""
    try:
        from utils.skills_manager import SkillsManager

        # SECURITY: Validate inputs
        from utils.input_validation import validate_user_id, validate_qube_id
        user_id = validate_user_id(user_id)
        qube_id = validate_qube_id(qube_id)

        # Get ChainState with encryption support
        chain_state = self._get_chain_state(qube_id)
        if not chain_state:
            return {
                "success": False,
                "error": f"Qube {qube_id} not found or not accessible"
            }

        # Add XP via chain_state
        skills_manager = SkillsManager(chain_state)
        result = skills_manager.add_xp(skill_id, xp_amount, evidence_block_id)

        return result

    except Exception as e:
        logger.error(f"Failed to add skill XP for qube {qube_id}: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }

async def unlock_skill(self, user_id: str, qube_id: str, skill_id: str) -> Dict[str, Any]:
    """Unlock a specific skill - UPDATED FOR CHAIN STATE"""
    try:
        from utils.skills_manager import SkillsManager

        # SECURITY: Validate inputs
        from utils.input_validation import validate_user_id, validate_qube_id
        user_id = validate_user_id(user_id)
        qube_id = validate_qube_id(qube_id)

        # Get ChainState with encryption support
        chain_state = self._get_chain_state(qube_id)
        if not chain_state:
            return {
                "success": False,
                "error": f"Qube {qube_id} not found or not accessible"
            }

        # Unlock skill via chain_state
        skills_manager = SkillsManager(chain_state)
        result = skills_manager.unlock_skill(skill_id)

        return result

    except Exception as e:
        logger.error(f"Failed to unlock skill for qube {qube_id}: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }
```

### 20.4 Updated gui_bridge Relationships Methods

Update `get_qube_relationships()` no-password path (around line 1393-1420):

```python
            else:
                # No password provided - STILL NEED ENCRYPTION KEY
                # After consolidation, we can't read relationships without decryption
                logger.debug(f"[GET_RELATIONSHIPS] No password - attempting chain_state access")

                chain_state = self._get_chain_state(qube_id)
                if not chain_state:
                    # Fall back to error - can't read encrypted data without key
                    return {
                        "success": False,
                        "relationships": [],
                        "stats": {},
                        "error": "Authentication required to access encrypted relationship data"
                    }

                # Load relationships from encrypted chain_state
                from relationships.relationship import RelationshipStorage
                rel_storage = RelationshipStorage(chain_state)
                relationships = rel_storage.get_all_relationships()
                logger.debug(f"[GET_RELATIONSHIPS] Chain state load: {len(relationships)} relationships")
```

### 20.5 AI Module Updates

For files in `ai/` that use SkillsManager, update to use `self.qube.chain_state`:

**ai/skill_scanner.py** (line 395):
```python
# OLD:
skills_manager = SkillsManager(self.qube.data_dir)

# NEW:
skills_manager = SkillsManager(self.qube.chain_state)
```

**ai/reasoner.py** (lines 359, 1804):
```python
# OLD:
skills_manager = SkillsManager(self.qube.data_dir)

# NEW:
skills_manager = SkillsManager(self.qube.chain_state)
```

**ai/tools/handlers.py** (line 1137):
```python
# OLD:
skills_manager = SkillsManager(qube.data_dir)

# NEW:
skills_manager = SkillsManager(qube.chain_state)
```

**orchestrator/user_orchestrator.py** (lines 2238-2253, `_init_qube_skills` method):
```python
# OLD:
def _init_qube_skills(self, qube):
    try:
        from utils.skills_manager import SkillsManager
        qube_dir = self.data_dir / "qubes" / qube.storage_dir_name
        skills_manager = SkillsManager(qube_dir)
        skills_data = skills_manager.load_skills()
        ...

# NEW:
def _init_qube_skills(self, qube):
    try:
        from utils.skills_manager import SkillsManager
        # Use qube's chain_state directly - skills are now in chain_state.json
        skills_manager = SkillsManager(qube.chain_state)
        skills_data = skills_manager.load_skills()
        ...
```

### 20.6 UX Consideration: Authentication Now Required

**IMPORTANT**: After consolidation, ALL reads of skills/relationships require the encryption key,
which requires authentication. This means:

1. **No more "quick preview" without login** - The frontend cannot show skills/relationships
   on a qube card without the user being authenticated.

2. **Solution options**:
   - Option A: Always require login before showing any qube details (current UX change)
   - Option B: Cache summary stats in unencrypted qube_metadata.json for preview
   - Option C: Keep certain fields unencrypted (defeats purpose)

**Recommended**: Option A with good UX - prompt for password when user tries to view details.
The Electron app already authenticates on startup, so this should work seamlessly for most flows.

### 20.7 Test Coverage

Add these test scenarios:

```python
# test_chain_state_integration.py

def test_skills_manager_with_chain_state():
    """Verify SkillsManager works with ChainState"""
    chain_state = ChainState(data_dir, encryption_key, qube_id)
    manager = SkillsManager(chain_state)

    # Should initialize with default skills
    skills = manager.load_skills()
    assert "skills" in skills
    assert len(skills["skills"]) > 0

def test_relationship_storage_with_chain_state():
    """Verify RelationshipStorage works with ChainState"""
    chain_state = ChainState(data_dir, encryption_key, qube_id)
    storage = RelationshipStorage(chain_state)

    # Should be able to create and retrieve
    rel = storage.create_relationship("test_entity", "human")
    assert storage.get_relationship("test_entity") is not None

def test_gui_bridge_skills_requires_auth():
    """Verify gui_bridge skills methods require authentication"""
    bridge = GUIBridge(user_id="test")
    # Without setting master_key, should fail gracefully
    result = await bridge.get_qube_skills("test", "qube123")
    assert result["success"] == False
    assert "authentication" in result["error"].lower()
```

---

## Section 21: Potential Issues & Mitigations

Issues discovered during comprehensive review:

### 21.1 Race Conditions (Low Risk)

**Issue**: Auto-anchor subprocess and main process could write simultaneously.

**Mitigation**: For single-user desktop app, this is acceptable. File locking could be added later.

### 21.2 Decryption Failure Recovery (Medium Risk)

**Issue**: If decryption fails, current code returns empty state (data loss).

**Mitigation**: Add backup recovery:

```python
def _load(self) -> Dict[str, Any]:
    """Load and decrypt state, with backup recovery."""
    try:
        return self._decrypt(self.file_path.read_bytes())
    except Exception as e:
        logger.error(f"Primary file decryption failed: {e}")

        # Try backup
        backup_path = self.file_path.with_suffix('.json.bak')
        if backup_path.exists():
            try:
                logger.warning("Attempting recovery from backup file")
                return self._decrypt(backup_path.read_bytes())
            except Exception as e2:
                logger.error(f"Backup recovery also failed: {e2}")

        # Last resort - return default state
        logger.error("CRITICAL: All recovery failed, returning default state")
        return self._get_default_state()
```

### 21.3 Password Change (Future Consideration)

**Issue**: If password change feature is added later, all encryption keys become invalid.

**Mitigation**: Document that password change requires:
1. Decrypt all `encryption_key.enc` files with old master key
2. Re-encrypt with new master key
3. This should be a dedicated migration function

### 21.4 Frontend Quick Preview (UX Change)

**Issue**: Frontend can't show skills/relationships without authentication.

**Mitigation**: The Electron app authenticates on startup, so this flow:
1. User opens app → prompted for password
2. Authentication succeeds → master_key set
3. All subsequent calls have access to encryption

If a "qube preview without full auth" feature is needed later, store non-sensitive summary
stats in unencrypted `qube_metadata.json`.

---

## Summary

This blueprint provides complete, copy-paste ready code for consolidating all Qube state into a
single encrypted `chain_state.json` file. Key benefits:

1. **Single Source of Truth**: All state in one file
2. **Always Encrypted**: AES-256-GCM encryption at rest
3. **Atomic Writes**: Temp file + rename prevents corruption
4. **Automatic Migration**: Old files migrated and deleted seamlessly
5. **Array Caps**: Prevents unbounded growth (50 transactions, 100 skills, 20 mood entries)
6. **GUI Bridge Support**: Encrypted key storage allows settings changes without full qube load

Total lines of code in blueprint: ~7500 (complete implementation ready for copy-paste)
