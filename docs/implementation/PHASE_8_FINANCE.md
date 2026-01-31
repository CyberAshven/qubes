# Phase 8: Finance - Implementation Blueprint

## Executive Summary

**Theme: Manage (Master Financial Operations for Your Owner)**

Finance is about the Qube being a trusted financial assistant - helping the owner send and receive cryptocurrency, manage their wallet, track market conditions, and plan savings strategies. This is especially relevant for BCH-based operations with CashTokens.

Finance branches directly from the Qube/Avatar (not from Security).

**Current State**: `send_bch` is already implemented. Needs full planet/moon structure.

### Tool Summary

| Level | Count | Tools |
|-------|-------|-------|
| Sun | 1 | `send_bch` (EXISTING) |
| Planet | 5 | `validate_transaction`, `check_wallet_health`, `get_market_data`, `plan_savings`, `identify_token` |
| Moon | 8 | `optimize_fees`, `track_transaction`, `monitor_balance`, `multisig_action`, `set_price_alert`, `analyze_market_trend`, `setup_dca`, `manage_cashtokens` |
| **Total** | **14** | |

### XP Model

Standard XP model (5/2.5/0) for all tools:
- **Success**: 5 XP
- **Completed**: 2.5 XP
- **Failed**: 0 XP

### Career Paths

| Career | Description | Key Planets |
|--------|-------------|-------------|
| **Treasurer** | Manages wallet, tracks transactions | Wallet Management, Transaction Mastery |
| **Savings Coach** | Helps owner save, sets up DCA | Savings Strategies, Market Awareness |
| **Payment Processor** | Handles transactions, optimizes fees | Transaction Mastery, Wallet Management |
| **Market Watcher** | Monitors prices, sends alerts | Market Awareness |
| **Token Specialist** | Expert in CashTokens | Token Knowledge, Transaction Mastery |

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Task 8.1: Update Skill Definitions](#task-81-update-skill-definitions)
3. [Task 8.2: Verify Sun Tool](#task-82-verify-sun-tool)
4. [Task 8.3: Implement Planet Tools](#task-83-implement-planet-tools)
5. [Task 8.4: Implement Moon Tools](#task-84-implement-moon-tools)
6. [Task 8.5: Update XP Routing](#task-85-update-xp-routing)
7. [Task 8.6: Frontend Integration](#task-86-frontend-integration)
8. [Task 8.7: Testing & Validation](#task-87-testing--validation)
9. [Files Modified Summary](#files-modified-summary)

---

## Prerequisites

### Existing Infrastructure

| Component | File | Status |
|-----------|------|--------|
| send_bch | `ai/tools/handlers.py` or `wallet/` | Implemented |
| Multi-sig Wallet | `wallet/multisig.py` | Implemented |
| BCH Address Validation | `wallet/address.py` | Implemented |
| BCMR Registry | `blockchain/bcmr.py` | Implemented |

### From Phase 0 (Foundation)

1. **Qube Locker** - For storing savings plans
2. **XP Trickle-Up System** - For routing finance XP

### Current Codebase State (as of Jan 2026)

#### New Category
- **Status**: Finance category does NOT exist in current codebase
- **Action**: Add entirely new 8th category to both Python and TypeScript

#### Frontend (`qubes-gui/src/data/skillDefinitions.ts`)
- **Current categories**: 7 (ai_reasoning through games)
- **Target categories**: 8 (add finance)
- **Action**: Add finance to SKILL_CATEGORIES array and SKILL_DEFINITIONS

#### Python (`utils/skill_definitions.py`)
- **Current categories**: 7 (matches frontend)
- **Action**: Add finance category with 14 skills (1 Sun, 5 Planets, 8 Moons)

#### Existing `send_bch` Tool
- **Current location**: `ai/tools/handlers.py` or `wallet/`
- **Current status**: ✅ Implemented and in ALWAYS_AVAILABLE_TOOLS
- **Action**: Keep as Finance Sun tool, add XP mapping

#### Wallet Infrastructure
- **Multi-sig**: `wallet/multisig.py` ✅
- **Address validation**: `wallet/address.py` ✅
- **BCMR Registry**: `blockchain/bcmr.py` ✅
- **Action**: New tools will leverage existing wallet infrastructure

---

## Task 8.1: Update Skill Definitions

### File: `ai/tools/handlers.py`

Add `finance` to SKILL_CATEGORIES and SKILL_TREE:

```python
# Add to SKILL_CATEGORIES
{"id": "finance", "name": "Finance", "color": "#27AE60", "icon": "wallet", "description": "Master financial operations for your owner"},

# Add to SKILL_TREE
"finance": [
    # Sun
    {
        "id": "finance",
        "name": "Finance",
        "node_type": "sun",
        "xp_required": 1000,
        "tool_unlock": "send_bch",
        "icon": "wallet",
        "description": "Master financial operations for your owner"
    },
    # Planet 1: Transaction Mastery
    {
        "id": "transaction_mastery",
        "name": "Transaction Mastery",
        "node_type": "planet",
        "parent": "finance",
        "xp_required": 500,
        "tool_unlock": "validate_transaction",
        "icon": "send",
        "description": "Master transaction creation and validation"
    },
    # Planet 2: Wallet Management
    {
        "id": "wallet_management",
        "name": "Wallet Management",
        "node_type": "planet",
        "parent": "finance",
        "xp_required": 500,
        "tool_unlock": "check_wallet_health",
        "icon": "wallet-cards",
        "description": "Manage and maintain wallet health"
    },
    # Planet 3: Market Awareness
    {
        "id": "market_awareness",
        "name": "Market Awareness",
        "node_type": "planet",
        "parent": "finance",
        "xp_required": 500,
        "tool_unlock": "get_market_data",
        "icon": "trending-up",
        "description": "Stay informed about market conditions"
    },
    # Planet 4: Savings Strategies
    {
        "id": "savings_strategies",
        "name": "Savings Strategies",
        "node_type": "planet",
        "parent": "finance",
        "xp_required": 500,
        "tool_unlock": "plan_savings",
        "icon": "piggy-bank",
        "description": "Help owner plan and execute savings"
    },
    # Planet 5: Token Knowledge
    {
        "id": "token_knowledge",
        "name": "Token Knowledge",
        "node_type": "planet",
        "parent": "finance",
        "xp_required": 500,
        "tool_unlock": "identify_token",
        "icon": "coins",
        "description": "Understand and work with CashTokens"
    },
    # Moon 1.1: Fee Optimization
    {
        "id": "fee_optimization",
        "name": "Fee Optimization",
        "node_type": "moon",
        "parent": "transaction_mastery",
        "xp_required": 250,
        "tool_unlock": "optimize_fees",
        "icon": "percent",
        "description": "Optimize transaction fees"
    },
    # Moon 1.2: Transaction Tracking
    {
        "id": "transaction_tracking",
        "name": "Transaction Tracking",
        "node_type": "moon",
        "parent": "transaction_mastery",
        "xp_required": 250,
        "tool_unlock": "track_transaction",
        "icon": "clock",
        "description": "Track transaction status"
    },
    # Moon 2.1: Balance Monitoring
    {
        "id": "balance_monitoring",
        "name": "Balance Monitoring",
        "node_type": "moon",
        "parent": "wallet_management",
        "xp_required": 250,
        "tool_unlock": "monitor_balance",
        "icon": "eye",
        "description": "Track balance changes"
    },
    # Moon 2.2: Multi-sig Operations
    {
        "id": "multisig_operations",
        "name": "Multi-sig Operations",
        "node_type": "moon",
        "parent": "wallet_management",
        "xp_required": 250,
        "tool_unlock": "multisig_action",
        "icon": "users",
        "description": "Manage multi-signature operations"
    },
    # Moon 3.1: Price Alerts
    {
        "id": "price_alerts",
        "name": "Price Alerts",
        "node_type": "moon",
        "parent": "market_awareness",
        "xp_required": 250,
        "tool_unlock": "set_price_alert",
        "icon": "bell",
        "description": "Set and manage price alerts"
    },
    # Moon 3.2: Market Trend Analysis
    {
        "id": "market_trend_analysis",
        "name": "Market Trend Analysis",
        "node_type": "moon",
        "parent": "market_awareness",
        "xp_required": 250,
        "tool_unlock": "analyze_market_trend",
        "icon": "line-chart",
        "description": "Analyze market trends"
    },
    # Moon 4.1: Dollar Cost Averaging
    {
        "id": "dollar_cost_averaging",
        "name": "Dollar Cost Averaging",
        "node_type": "moon",
        "parent": "savings_strategies",
        "xp_required": 250,
        "tool_unlock": "setup_dca",
        "icon": "calendar",
        "description": "Set up automatic DCA purchases"
    },
    # Moon 5.1: CashToken Operations
    {
        "id": "cashtoken_operations",
        "name": "CashToken Operations",
        "node_type": "moon",
        "parent": "token_knowledge",
        "xp_required": 250,
        "tool_unlock": "manage_cashtokens",
        "icon": "circle-dollar-sign",
        "description": "Send and receive CashTokens"
    },
],
```

---

## Task 8.2: Verify Sun Tool

The `send_bch` tool should already exist. Verify it's properly integrated:

### Expected Implementation (Existing)

```python
# In ai/tools/handlers.py or wallet/operations.py

SEND_BCH_SCHEMA = {
    "type": "object",
    "properties": {
        "to_address": {
            "type": "string",
            "description": "BCH recipient address"
        },
        "amount": {
            "type": "number",
            "description": "Amount of BCH to send"
        },
        "memo": {
            "type": "string",
            "description": "Optional memo/message"
        }
    },
    "required": ["to_address", "amount"]
}

SEND_BCH_DEFINITION = ToolDefinition(
    name="send_bch",
    description="Send BCH to a recipient address. Uses multi-sig wallet for owner protection.",
    input_schema=SEND_BCH_SCHEMA,
    category="finance"
)
```

---

## Task 8.3: Implement Planet Tools

### File: `ai/tools/finance_tools.py` (NEW FILE)

```python
"""
Finance Tools - Phase 8 Implementation

Trusted financial assistant for BCH/CashToken operations.
Wallet management, market awareness, savings strategies.

Theme: Manage (Master Financial Operations)
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta

from core.block import Block, BlockType, create_learning_block
from ai.tools.registry import ToolDefinition
from utils.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# PLANET 1: validate_transaction (Transaction Mastery)
# =============================================================================

VALIDATE_TRANSACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "to_address": {
            "type": "string",
            "description": "Recipient BCH address"
        },
        "amount": {
            "type": "number",
            "description": "Amount to send"
        },
        "check_type": {
            "type": "string",
            "enum": ["quick", "thorough"],
            "description": "Validation depth"
        }
    },
    "required": ["to_address", "amount"]
}

VALIDATE_TRANSACTION_DEFINITION = ToolDefinition(
    name="validate_transaction",
    description="Validate a transaction before sending. Catches errors and suspicious patterns.",
    input_schema=VALIDATE_TRANSACTION_SCHEMA,
    category="finance"
)


async def validate_transaction(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate a transaction before sending.

    Checks:
    - Address format validity
    - Sufficient funds
    - Known scam addresses
    - Unusual amounts
    - Duplicate transactions

    Args:
        qube: Qube instance
        params: {
            to_address: str - Recipient address
            amount: float - Amount to send
            check_type: str - quick or thorough
        }

    Returns:
        Dict with validation results, warnings, recommendations
    """
    to_address = params.get("to_address")
    amount = params.get("amount")
    check_type = params.get("check_type", "quick")

    if not to_address or amount is None:
        return {"success": False, "error": "Address and amount required"}

    validations = {
        "address_valid": _is_valid_bch_address(to_address),
        "sufficient_funds": False,
        "amount_reasonable": amount > 0,
        "warnings": []
    }

    # Check balance
    try:
        if hasattr(qube, 'wallet'):
            balance = await qube.wallet.get_balance()
            validations["sufficient_funds"] = balance >= amount
            validations["current_balance"] = balance
        else:
            validations["sufficient_funds"] = True  # Can't verify
    except Exception as e:
        validations["warnings"].append(f"Could not verify balance: {str(e)}")

    # Thorough checks
    if check_type == "thorough":
        # Check for known scam addresses
        if await _is_known_scam_address(to_address):
            validations["warnings"].append("WARNING: Address associated with known scams")
            validations["scam_detected"] = True

        # Check for unusually large amount
        avg_tx = await _get_average_transaction(qube)
        if avg_tx and amount > avg_tx * 10:
            validations["warnings"].append(f"Amount is 10x your average ({avg_tx:.4f} BCH)")

        # Check for duplicate
        if await _has_recent_duplicate(qube, to_address, amount):
            validations["warnings"].append("Duplicate: Same amount to same address recently")

    validations["valid"] = all([
        validations["address_valid"],
        validations["sufficient_funds"],
        validations["amount_reasonable"],
        not validations.get("scam_detected", False)
    ])

    return {
        "success": True,
        **validations
    }


def _is_valid_bch_address(address: str) -> bool:
    """Validate BCH address format."""
    if not address:
        return False

    # Check for CashAddr format
    if address.startswith("bitcoincash:") or address.startswith("bchtest:"):
        return len(address) > 20

    # Check for legacy format
    if address.startswith("1") or address.startswith("3"):
        return 25 <= len(address) <= 35

    return False


async def _is_known_scam_address(address: str) -> bool:
    """Check if address is in scam database."""
    # Would query distributed scam database
    return False


async def _get_average_transaction(qube) -> Optional[float]:
    """Get average transaction amount for this Qube."""
    # Would calculate from transaction history
    return 0.1


async def _has_recent_duplicate(qube, address: str, amount: float) -> bool:
    """Check for recent duplicate transaction."""
    # Would check recent transactions
    return False


# =============================================================================
# PLANET 2: check_wallet_health (Wallet Management)
# =============================================================================

CHECK_WALLET_HEALTH_SCHEMA = {
    "type": "object",
    "properties": {}
}

CHECK_WALLET_HEALTH_DEFINITION = ToolDefinition(
    name="check_wallet_health",
    description="Comprehensive wallet health check. Balance, UTXOs, security, recommendations.",
    input_schema=CHECK_WALLET_HEALTH_SCHEMA,
    category="finance"
)


async def check_wallet_health(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Comprehensive wallet health check.

    Analyzes:
    - Balance
    - UTXO count and fragmentation
    - Pending transactions
    - Backup status
    - Security recommendations

    Args:
        qube: Qube instance
        params: (none required)

    Returns:
        Dict with health metrics and recommendations
    """
    health = {
        "balance": 0,
        "utxo_count": 0,
        "pending_tx": 0,
        "last_backup": None,
        "health_score": 100,
        "recommendations": []
    }

    try:
        if hasattr(qube, 'wallet'):
            wallet = qube.wallet

            health["balance"] = await wallet.get_balance()
            health["utxo_count"] = await wallet.get_utxo_count() if hasattr(wallet, 'get_utxo_count') else 0
            health["pending_tx"] = len(await wallet.get_pending_transactions()) if hasattr(wallet, 'get_pending_transactions') else 0
            health["last_backup"] = getattr(wallet, 'last_backup_date', None)

            # UTXO fragmentation check
            if health["utxo_count"] > 50:
                health["recommendations"].append("Consider consolidating UTXOs to reduce future fees")
                health["health_score"] -= 10

            # Dust check
            if hasattr(wallet, 'get_dust_balance'):
                dust = await wallet.get_dust_balance()
                if dust > 0:
                    health["recommendations"].append(f"You have {dust:.8f} BCH in dust UTXOs")
                    health["health_score"] -= 5

            # Backup reminder
            if health["last_backup"]:
                days_since = (datetime.now(timezone.utc) - health["last_backup"]).days
                if days_since > 30:
                    health["recommendations"].append(f"Backup overdue ({days_since} days since last backup)")
                    health["health_score"] -= 15

        # Log wallet health insight
        await _log_wallet_insight(qube, health)

    except Exception as e:
        logger.error("wallet_health_check_failed", error=str(e))
        health["error"] = str(e)
        health["health_score"] = 0

    return {
        "success": True,
        **health
    }


async def _log_wallet_insight(qube, health: Dict) -> None:
    """Log wallet health as LEARNING block."""
    if hasattr(qube, 'current_session'):
        block = create_learning_block(
            qube_id=qube.qube_id,
            block_number=-1,
            previous_hash="",
            learning_type="insight",
            content={
                "category": "wallet_health",
                "balance_range": _categorize_balance(health["balance"]),
                "health_score": health["health_score"]
            },
            source_category="finance",
            confidence=90,
            temporary=True,
            session_id=qube.current_session.session_id
        )
        await qube.current_session.add_block(block)


def _categorize_balance(balance: float) -> str:
    """Categorize balance for privacy."""
    if balance < 0.01:
        return "dust"
    elif balance < 0.1:
        return "small"
    elif balance < 1:
        return "medium"
    elif balance < 10:
        return "large"
    else:
        return "whale"


# =============================================================================
# PLANET 3: get_market_data (Market Awareness)
# =============================================================================

GET_MARKET_DATA_SCHEMA = {
    "type": "object",
    "properties": {
        "currency": {
            "type": "string",
            "description": "Fiat currency for price (USD, EUR, etc.)"
        },
        "include_history": {
            "type": "boolean",
            "description": "Include 7-day price history"
        }
    }
}

GET_MARKET_DATA_DEFINITION = ToolDefinition(
    name="get_market_data",
    description="Get current BCH market data. Price, changes, volume.",
    input_schema=GET_MARKET_DATA_SCHEMA,
    category="finance"
)


async def get_market_data(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get current BCH market data.

    Returns:
    - Current price
    - 24h/7d change
    - Volume
    - Optional: 7-day history

    Args:
        qube: Qube instance
        params: {
            currency: str - Fiat currency (default: USD)
            include_history: bool - Include price history
        }

    Returns:
        Dict with market data
    """
    currency = params.get("currency", "USD")
    include_history = params.get("include_history", False)

    try:
        market = await _fetch_market_data("BCH", currency)

        result = {
            "success": True,
            "asset": "BCH",
            "price": market["price"],
            "currency": currency,
            "change_24h": market["change_24h"],
            "change_7d": market["change_7d"],
            "volume_24h": market["volume_24h"],
            "market_cap": market["market_cap"],
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        if include_history:
            result["price_history_7d"] = market.get("history_7d", [])

        return result

    except Exception as e:
        logger.error("market_data_fetch_failed", error=str(e))
        return {"success": False, "error": f"Failed to fetch market data: {str(e)}"}


async def _fetch_market_data(asset: str, currency: str) -> Dict:
    """Fetch market data from API."""
    # Would query CoinGecko, CoinMarketCap, etc.
    # Placeholder data
    return {
        "price": 450.00,
        "change_24h": 2.5,
        "change_7d": -1.2,
        "volume_24h": 500000000,
        "market_cap": 8000000000,
        "history_7d": []
    }


# =============================================================================
# PLANET 4: plan_savings (Savings Strategies)
# =============================================================================

PLAN_SAVINGS_SCHEMA = {
    "type": "object",
    "properties": {
        "goal_amount": {
            "type": "number",
            "description": "Savings goal in BCH"
        },
        "target_date": {
            "type": "string",
            "description": "Target date (YYYY-MM-DD)"
        },
        "strategy": {
            "type": "string",
            "enum": ["lump_sum", "dca"],
            "description": "Savings strategy"
        }
    },
    "required": ["goal_amount", "target_date"]
}

PLAN_SAVINGS_DEFINITION = ToolDefinition(
    name="plan_savings",
    description="Create a savings plan for the owner. Structured saving with milestones.",
    input_schema=PLAN_SAVINGS_SCHEMA,
    category="finance"
)


async def plan_savings(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a savings plan.

    Calculates:
    - Daily/weekly targets
    - Milestones
    - Progress tracking

    Args:
        qube: Qube instance
        params: {
            goal_amount: float - Target amount in BCH
            target_date: str - YYYY-MM-DD
            strategy: str - lump_sum or dca
        }

    Returns:
        Dict with savings plan details
    """
    goal_amount = params.get("goal_amount")
    target_date_str = params.get("target_date")
    strategy = params.get("strategy", "dca")

    if not goal_amount or not target_date_str:
        return {"success": False, "error": "Goal amount and target date required"}

    try:
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        days_remaining = (target_date - datetime.now(timezone.utc)).days

        if days_remaining <= 0:
            return {"success": False, "error": "Target date must be in the future"}

        # Get current balance
        current = 0
        if hasattr(qube, 'wallet'):
            current = await qube.wallet.get_balance()

        remaining = goal_amount - current

        plan = {
            "goal": goal_amount,
            "current": current,
            "remaining": max(0, remaining),
            "days": days_remaining,
            "strategy": strategy,
            "target_date": target_date_str,
            "milestones": []
        }

        if strategy == "dca" and remaining > 0:
            plan["daily_target"] = remaining / days_remaining
            plan["weekly_target"] = plan["daily_target"] * 7

            # Create milestones (25%, 50%, 75%, 100%)
            for pct in [25, 50, 75, 100]:
                milestone_amount = goal_amount * (pct / 100)
                days_to_milestone = int(days_remaining * (pct / 100))
                plan["milestones"].append({
                    "percentage": pct,
                    "amount": milestone_amount,
                    "target_days": days_to_milestone
                })

        # Store plan as LEARNING block
        await _log_savings_plan(qube, plan)

        # Store in Qube Locker
        if hasattr(qube, 'locker') and qube.locker:
            await qube.locker.store(
                category="personal/savings",
                name=f"savings_plan_{target_date_str}",
                content=plan
            )

        return {
            "success": True,
            **plan
        }

    except Exception as e:
        logger.error("plan_savings_failed", error=str(e))
        return {"success": False, "error": f"Failed to create plan: {str(e)}"}


async def _log_savings_plan(qube, plan: Dict) -> None:
    """Log savings plan as LEARNING block."""
    if hasattr(qube, 'current_session'):
        block = create_learning_block(
            qube_id=qube.qube_id,
            block_number=-1,
            previous_hash="",
            learning_type="procedure",
            content={
                "context": "savings_plan",
                "goal": plan["goal"],
                "strategy": plan["strategy"],
                "timeline_days": plan["days"]
            },
            source_category="finance",
            confidence=95,
            temporary=True,
            session_id=qube.current_session.session_id
        )
        await qube.current_session.add_block(block)


# =============================================================================
# PLANET 5: identify_token (Token Knowledge)
# =============================================================================

IDENTIFY_TOKEN_SCHEMA = {
    "type": "object",
    "properties": {
        "token_id": {
            "type": "string",
            "description": "CashToken category ID"
        },
        "category": {
            "type": "string",
            "description": "Alternative: token category"
        }
    }
}

IDENTIFY_TOKEN_DEFINITION = ToolDefinition(
    name="identify_token",
    description="Identify and get info about a CashToken. Queries BCMR registry.",
    input_schema=IDENTIFY_TOKEN_SCHEMA,
    category="finance"
)


async def identify_token(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Identify a CashToken and get its metadata.

    Queries the BCMR (Bitcoin Cash Metadata Registry) for token info.

    Args:
        qube: Qube instance
        params: {
            token_id: str - Category ID
            category: str - Alternative param
        }

    Returns:
        Dict with token metadata
    """
    token_id = params.get("token_id") or params.get("category")

    if not token_id:
        return {"success": False, "error": "Token ID or category required"}

    try:
        # Query BCMR registry
        token_info = await _lookup_bcmr(token_id)

        if token_info:
            # Log new token knowledge
            if not await _qube_knows_token(qube, token_id):
                await _log_token_fact(qube, token_id, token_info)

            return {
                "success": True,
                "token_id": token_id,
                "name": token_info.get("name"),
                "symbol": token_info.get("symbol"),
                "description": token_info.get("description"),
                "decimals": token_info.get("decimals", 0),
                "supply": token_info.get("supply"),
                "uri": token_info.get("uri"),
                "icon": token_info.get("icon")
            }
        else:
            return {
                "success": False,
                "token_id": token_id,
                "error": "Token not found in BCMR registry"
            }

    except Exception as e:
        logger.error("identify_token_failed", error=str(e))
        return {"success": False, "error": f"Failed to identify token: {str(e)}"}


async def _lookup_bcmr(token_id: str) -> Optional[Dict]:
    """Look up token in BCMR registry."""
    # Would query actual BCMR registry
    # Placeholder
    return None


async def _qube_knows_token(qube, token_id: str) -> bool:
    """Check if Qube already knows this token."""
    # Would search LEARNING blocks
    return False


async def _log_token_fact(qube, token_id: str, info: Dict) -> None:
    """Log new token knowledge."""
    if hasattr(qube, 'current_session'):
        block = create_learning_block(
            qube_id=qube.qube_id,
            block_number=-1,
            previous_hash="",
            learning_type="fact",
            content={
                "context": "cashtoken",
                "token_id": token_id,
                "name": info.get("name"),
                "symbol": info.get("symbol")
            },
            source_category="finance",
            confidence=100,
            temporary=True,
            session_id=qube.current_session.session_id
        )
        await qube.current_session.add_block(block)
```

---

## Task 8.4: Implement Moon Tools

### Continue in `ai/tools/finance_tools.py`

```python
# =============================================================================
# MOON TOOLS
# =============================================================================

# Moon 1.1: optimize_fees
OPTIMIZE_FEES_SCHEMA = {
    "type": "object",
    "properties": {
        "priority": {
            "type": "string",
            "enum": ["fast", "normal", "slow"],
            "description": "Transaction priority"
        },
        "amount": {
            "type": "number",
            "description": "Transaction amount"
        }
    },
    "required": ["amount"]
}

OPTIMIZE_FEES_DEFINITION = ToolDefinition(
    name="optimize_fees",
    description="Calculate optimal fee for transaction speed vs cost tradeoff.",
    input_schema=OPTIMIZE_FEES_SCHEMA,
    category="finance"
)


async def optimize_fees(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate optimal transaction fee.

    Args:
        qube: Qube instance
        params: {
            priority: str - fast, normal, slow
            amount: float - Transaction amount
        }

    Returns:
        Dict with recommended fee, confirmation estimate
    """
    priority = params.get("priority", "normal")
    amount = params.get("amount")

    # BCH fees are very low - roughly 1 sat/byte
    # Simplified calculation
    fee_rates = {
        "fast": 2,      # sat/byte
        "normal": 1,    # sat/byte
        "slow": 0.5     # sat/byte
    }

    confirmation_times = {
        "fast": "~10 minutes (next block)",
        "normal": "~20 minutes (1-2 blocks)",
        "slow": "~60 minutes (3-6 blocks)"
    }

    rate = fee_rates.get(priority, 1)
    estimated_size = 250  # Average tx size in bytes
    fee_sats = int(rate * estimated_size)
    fee_bch = fee_sats / 100000000

    # Log fee pattern
    await _log_fee_pattern(qube, priority, fee_bch)

    return {
        "success": True,
        "priority": priority,
        "fee_sats": fee_sats,
        "fee_bch": fee_bch,
        "estimated_size_bytes": estimated_size,
        "confirmation_estimate": confirmation_times.get(priority)
    }


async def _log_fee_pattern(qube, priority: str, fee: float) -> None:
    """Log fee recommendation as LEARNING fact."""
    if hasattr(qube, 'current_session'):
        block = create_learning_block(
            qube_id=qube.qube_id,
            block_number=-1,
            previous_hash="",
            learning_type="fact",
            content={
                "context": "fee_optimization",
                "priority": priority,
                "fee_bch": fee
            },
            source_category="finance",
            confidence=80,
            temporary=True,
            session_id=qube.current_session.session_id
        )
        await qube.current_session.add_block(block)


# Moon 1.2: track_transaction
TRACK_TRANSACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "tx_id": {
            "type": "string",
            "description": "Transaction ID to track"
        }
    },
    "required": ["tx_id"]
}

TRACK_TRANSACTION_DEFINITION = ToolDefinition(
    name="track_transaction",
    description="Track a transaction's confirmation status.",
    input_schema=TRACK_TRANSACTION_SCHEMA,
    category="finance"
)


async def track_transaction(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Track transaction confirmation status.

    Args:
        qube: Qube instance
        params: {
            tx_id: str - Transaction ID
        }

    Returns:
        Dict with confirmation count, block info
    """
    tx_id = params.get("tx_id")

    if not tx_id:
        return {"success": False, "error": "Transaction ID required"}

    try:
        # Would query blockchain API
        tx_status = await _get_transaction_status(tx_id)

        return {
            "success": True,
            "tx_id": tx_id,
            "confirmations": tx_status.get("confirmations", 0),
            "block_height": tx_status.get("block_height"),
            "block_hash": tx_status.get("block_hash"),
            "status": "confirmed" if tx_status.get("confirmations", 0) > 0 else "pending",
            "timestamp": tx_status.get("timestamp")
        }

    except Exception as e:
        return {"success": False, "error": f"Failed to track transaction: {str(e)}"}


async def _get_transaction_status(tx_id: str) -> Dict:
    """Get transaction status from blockchain."""
    # Would query Fulcrum/blockchain API
    return {"confirmations": 0}


# Moon 2.1: monitor_balance
MONITOR_BALANCE_SCHEMA = {
    "type": "object",
    "properties": {
        "alert_threshold": {
            "type": "number",
            "description": "Alert if balance drops below this"
        }
    }
}

MONITOR_BALANCE_DEFINITION = ToolDefinition(
    name="monitor_balance",
    description="Monitor balance and detect unusual activity.",
    input_schema=MONITOR_BALANCE_SCHEMA,
    category="finance"
)


async def monitor_balance(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Monitor balance for changes.

    Args:
        qube: Qube instance
        params: {
            alert_threshold: float - Alert threshold
        }

    Returns:
        Dict with balance history, alerts
    """
    alert_threshold = params.get("alert_threshold")

    try:
        current_balance = 0
        if hasattr(qube, 'wallet'):
            current_balance = await qube.wallet.get_balance()

        result = {
            "success": True,
            "current_balance": current_balance,
            "alerts": []
        }

        if alert_threshold and current_balance < alert_threshold:
            result["alerts"].append(f"Balance ({current_balance}) below threshold ({alert_threshold})")

        # Log spending pattern
        await _log_balance_pattern(qube, current_balance)

        return result

    except Exception as e:
        return {"success": False, "error": str(e)}


async def _log_balance_pattern(qube, balance: float) -> None:
    """Log balance check for pattern tracking."""
    if hasattr(qube, 'current_session'):
        block = create_learning_block(
            qube_id=qube.qube_id,
            block_number=-1,
            previous_hash="",
            learning_type="pattern",
            content={
                "context": "balance_monitoring",
                "balance_category": _categorize_balance(balance)
            },
            source_category="finance",
            confidence=85,
            temporary=True,
            session_id=qube.current_session.session_id
        )
        await qube.current_session.add_block(block)


# Moon 2.2: multisig_action
MULTISIG_ACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": ["sign", "reject", "check_status"],
            "description": "Multi-sig action"
        },
        "tx_id": {
            "type": "string",
            "description": "Transaction ID"
        }
    },
    "required": ["action"]
}

MULTISIG_ACTION_DEFINITION = ToolDefinition(
    name="multisig_action",
    description="Perform multi-signature wallet operations.",
    input_schema=MULTISIG_ACTION_SCHEMA,
    category="finance"
)


async def multisig_action(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Perform multi-sig wallet operation.

    Args:
        qube: Qube instance
        params: {
            action: str - sign, reject, check_status
            tx_id: str - Transaction ID
        }

    Returns:
        Dict with action result
    """
    action = params.get("action")
    tx_id = params.get("tx_id")

    if action == "check_status":
        # Check pending multi-sig transactions
        pending = []
        if hasattr(qube, 'wallet') and hasattr(qube.wallet, 'get_pending_multisig'):
            pending = await qube.wallet.get_pending_multisig()

        return {
            "success": True,
            "pending_transactions": len(pending),
            "transactions": pending
        }

    elif action == "sign":
        if not tx_id:
            return {"success": False, "error": "Transaction ID required for signing"}

        # Would sign the transaction
        return {
            "success": True,
            "action": "signed",
            "tx_id": tx_id,
            "message": "Transaction signed. Awaiting other signatures."
        }

    elif action == "reject":
        if not tx_id:
            return {"success": False, "error": "Transaction ID required for rejection"}

        return {
            "success": True,
            "action": "rejected",
            "tx_id": tx_id,
            "message": "Transaction rejected."
        }

    return {"success": False, "error": f"Unknown action: {action}"}


# Moon 3.1: set_price_alert
SET_PRICE_ALERT_SCHEMA = {
    "type": "object",
    "properties": {
        "trigger_price": {
            "type": "number",
            "description": "Price that triggers alert"
        },
        "direction": {
            "type": "string",
            "enum": ["above", "below"],
            "description": "Trigger when price goes above or below"
        },
        "message": {
            "type": "string",
            "description": "Custom alert message"
        }
    },
    "required": ["trigger_price", "direction"]
}

SET_PRICE_ALERT_DEFINITION = ToolDefinition(
    name="set_price_alert",
    description="Set price alert for owner notification.",
    input_schema=SET_PRICE_ALERT_SCHEMA,
    category="finance"
)


async def set_price_alert(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Set a price alert.

    Args:
        qube: Qube instance
        params: {
            trigger_price: float - Trigger price
            direction: str - above or below
            message: str - Custom message
        }

    Returns:
        Dict with alert confirmation
    """
    trigger_price = params.get("trigger_price")
    direction = params.get("direction")
    message = params.get("message", f"BCH price is {direction} ${trigger_price}")

    # Would store alert in persistent storage
    alert = {
        "id": f"alert_{datetime.now().timestamp()}",
        "asset": "BCH",
        "trigger_price": trigger_price,
        "direction": direction,
        "message": message,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "triggered": False
    }

    # Store alert
    if not hasattr(qube, '_price_alerts'):
        qube._price_alerts = []
    qube._price_alerts.append(alert)

    return {
        "success": True,
        "alert_id": alert["id"],
        "trigger_price": trigger_price,
        "direction": direction,
        "message": f"Alert set: Notify when BCH goes {direction} ${trigger_price}"
    }


# Moon 3.2: analyze_market_trend
ANALYZE_MARKET_TREND_SCHEMA = {
    "type": "object",
    "properties": {
        "timeframe": {
            "type": "string",
            "enum": ["day", "week", "month"],
            "description": "Analysis timeframe"
        }
    }
}

ANALYZE_MARKET_TREND_DEFINITION = ToolDefinition(
    name="analyze_market_trend",
    description="Analyze recent market trends.",
    input_schema=ANALYZE_MARKET_TREND_SCHEMA,
    category="finance"
)


async def analyze_market_trend(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze market trends.

    Args:
        qube: Qube instance
        params: {
            timeframe: str - day, week, month
        }

    Returns:
        Dict with trend analysis
    """
    timeframe = params.get("timeframe", "week")

    try:
        market = await _fetch_market_data("BCH", "USD")

        # Simplified trend analysis
        change = market.get("change_7d", 0) if timeframe == "week" else market.get("change_24h", 0)

        trend = "bullish" if change > 5 else "bearish" if change < -5 else "neutral"

        analysis = {
            "success": True,
            "timeframe": timeframe,
            "trend": trend,
            "change_percent": change,
            "current_price": market["price"],
            "analysis": f"BCH is showing {trend} momentum with {change:.1f}% change over the {timeframe}"
        }

        # Log market pattern
        await _log_market_pattern(qube, trend, change)

        return analysis

    except Exception as e:
        return {"success": False, "error": str(e)}


async def _log_market_pattern(qube, trend: str, change: float) -> None:
    """Log market analysis as pattern."""
    if hasattr(qube, 'current_session'):
        block = create_learning_block(
            qube_id=qube.qube_id,
            block_number=-1,
            previous_hash="",
            learning_type="pattern",
            content={
                "context": "market_trend",
                "trend": trend,
                "change_percent": change
            },
            source_category="finance",
            confidence=70,
            temporary=True,
            session_id=qube.current_session.session_id
        )
        await qube.current_session.add_block(block)


# Moon 4.1: setup_dca
SETUP_DCA_SCHEMA = {
    "type": "object",
    "properties": {
        "amount": {
            "type": "number",
            "description": "Amount per purchase in BCH"
        },
        "frequency": {
            "type": "string",
            "enum": ["daily", "weekly", "monthly"],
            "description": "Purchase frequency"
        },
        "duration": {
            "type": "string",
            "description": "Duration (e.g., '3 months', '1 year')"
        }
    },
    "required": ["amount", "frequency"]
}

SETUP_DCA_DEFINITION = ToolDefinition(
    name="setup_dca",
    description="Configure dollar-cost averaging schedule.",
    input_schema=SETUP_DCA_SCHEMA,
    category="finance"
)


async def setup_dca(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Set up DCA schedule.

    Args:
        qube: Qube instance
        params: {
            amount: float - Amount per purchase
            frequency: str - daily, weekly, monthly
            duration: str - How long to run
        }

    Returns:
        Dict with DCA schedule
    """
    amount = params.get("amount")
    frequency = params.get("frequency")
    duration = params.get("duration", "3 months")

    # Calculate schedule
    purchases_per_month = {"daily": 30, "weekly": 4, "monthly": 1}[frequency]

    # Parse duration
    duration_months = 3  # Default
    if "year" in duration:
        duration_months = 12
    elif "month" in duration:
        try:
            duration_months = int(duration.split()[0])
        except:
            pass

    total_purchases = purchases_per_month * duration_months
    total_investment = amount * total_purchases

    schedule = {
        "amount_per_purchase": amount,
        "frequency": frequency,
        "duration": duration,
        "total_purchases": total_purchases,
        "total_investment": total_investment,
        "start_date": datetime.now(timezone.utc).isoformat()
    }

    # Log DCA procedure
    await _log_dca_procedure(qube, schedule)

    return {
        "success": True,
        **schedule,
        "message": f"DCA set: Buy {amount} BCH {frequency} for {duration}"
    }


async def _log_dca_procedure(qube, schedule: Dict) -> None:
    """Log DCA setup as procedure."""
    if hasattr(qube, 'current_session'):
        block = create_learning_block(
            qube_id=qube.qube_id,
            block_number=-1,
            previous_hash="",
            learning_type="procedure",
            content={
                "context": "dca_schedule",
                "frequency": schedule["frequency"],
                "total_purchases": schedule["total_purchases"]
            },
            source_category="finance",
            confidence=95,
            temporary=True,
            session_id=qube.current_session.session_id
        )
        await qube.current_session.add_block(block)


# Moon 5.1: manage_cashtokens
MANAGE_CASHTOKENS_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": ["send", "list", "receive"],
            "description": "Action to perform"
        },
        "token_id": {
            "type": "string",
            "description": "Token category ID"
        },
        "amount": {
            "type": "number",
            "description": "Amount of tokens"
        },
        "to_address": {
            "type": "string",
            "description": "Recipient address (for send)"
        }
    },
    "required": ["action"]
}

MANAGE_CASHTOKENS_DEFINITION = ToolDefinition(
    name="manage_cashtokens",
    description="Send, receive, and list CashTokens.",
    input_schema=MANAGE_CASHTOKENS_SCHEMA,
    category="finance"
)


async def manage_cashtokens(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Manage CashTokens.

    Args:
        qube: Qube instance
        params: {
            action: str - send, list, receive
            token_id: str - Token category
            amount: float - Amount
            to_address: str - Recipient
        }

    Returns:
        Dict with action result
    """
    action = params.get("action")

    if action == "list":
        # List all tokens in wallet
        tokens = []
        if hasattr(qube, 'wallet') and hasattr(qube.wallet, 'get_tokens'):
            tokens = await qube.wallet.get_tokens()

        return {
            "success": True,
            "tokens": tokens,
            "count": len(tokens)
        }

    elif action == "send":
        token_id = params.get("token_id")
        amount = params.get("amount")
        to_address = params.get("to_address")

        if not all([token_id, amount, to_address]):
            return {"success": False, "error": "Token ID, amount, and address required for send"}

        # Would send tokens
        return {
            "success": True,
            "action": "sent",
            "token_id": token_id,
            "amount": amount,
            "to": to_address,
            "message": f"Sent {amount} tokens to {to_address[:12]}..."
        }

    elif action == "receive":
        # Generate receive address
        address = "bitcoincash:qz..." if hasattr(qube, 'wallet') else "N/A"

        return {
            "success": True,
            "action": "receive",
            "address": address,
            "message": "Send CashTokens to this address"
        }

    return {"success": False, "error": f"Unknown action: {action}"}
```

---

## Task 8.5: Update XP Routing

### File: `core/xp_router.py`

```python
# Finance tool mappings
FINANCE_TOOLS = {
    # Sun
    "send_bch": {
        "skill_id": "finance",
        "xp_model": "standard",
        "category": "finance"
    },

    # Planets
    "validate_transaction": {"skill_id": "transaction_mastery", "xp_model": "standard", "category": "finance"},
    "check_wallet_health": {"skill_id": "wallet_management", "xp_model": "standard", "category": "finance"},
    "get_market_data": {"skill_id": "market_awareness", "xp_model": "standard", "category": "finance"},
    "plan_savings": {"skill_id": "savings_strategies", "xp_model": "standard", "category": "finance"},
    "identify_token": {"skill_id": "token_knowledge", "xp_model": "standard", "category": "finance"},

    # Moons
    "optimize_fees": {"skill_id": "fee_optimization", "xp_model": "standard", "category": "finance"},
    "track_transaction": {"skill_id": "transaction_tracking", "xp_model": "standard", "category": "finance"},
    "monitor_balance": {"skill_id": "balance_monitoring", "xp_model": "standard", "category": "finance"},
    "multisig_action": {"skill_id": "multisig_operations", "xp_model": "standard", "category": "finance"},
    "set_price_alert": {"skill_id": "price_alerts", "xp_model": "standard", "category": "finance"},
    "analyze_market_trend": {"skill_id": "market_trend_analysis", "xp_model": "standard", "category": "finance"},
    "setup_dca": {"skill_id": "dollar_cost_averaging", "xp_model": "standard", "category": "finance"},
    "manage_cashtokens": {"skill_id": "cashtoken_operations", "xp_model": "standard", "category": "finance"},
}

TOOL_TO_SKILL_MAPPING.update(FINANCE_TOOLS)
```

---

## Task 8.6: Frontend Integration

### File: `src/types/skills.ts`

```typescript
// Finance skill IDs
export type FinanceSkillId =
  | 'finance'
  | 'transaction_mastery'
  | 'wallet_management'
  | 'market_awareness'
  | 'savings_strategies'
  | 'token_knowledge'
  | 'fee_optimization'
  | 'transaction_tracking'
  | 'balance_monitoring'
  | 'multisig_operations'
  | 'price_alerts'
  | 'market_trend_analysis'
  | 'dollar_cost_averaging'
  | 'cashtoken_operations';

// Tool parameter types
export interface SendBchParams {
  to_address: string;
  amount: number;
  memo?: string;
}

export interface ValidateTransactionParams {
  to_address: string;
  amount: number;
  check_type?: 'quick' | 'thorough';
}

export interface PlanSavingsParams {
  goal_amount: number;
  target_date: string;
  strategy?: 'lump_sum' | 'dca';
}

export interface SetPriceAlertParams {
  trigger_price: number;
  direction: 'above' | 'below';
  message?: string;
}

export interface ManageCashTokensParams {
  action: 'send' | 'list' | 'receive';
  token_id?: string;
  amount?: number;
  to_address?: string;
}
```

---

## Task 8.7: Testing & Validation

```markdown
## Finance Testing Checklist

### 8.7.1 Sun Tool Tests
- [x] `send_bch` validates addresses
- [x] `send_bch` checks balance
- [x] `send_bch` uses multi-sig
- [ ] `send_bch` awards 5 XP on success

### 8.7.2 Transaction Mastery Tests
- [ ] `validate_transaction` catches invalid addresses
- [ ] `validate_transaction` thorough mode checks scams
- [ ] `optimize_fees` calculates correctly for BCH
- [ ] `track_transaction` queries blockchain

### 8.7.3 Wallet Management Tests
- [ ] `check_wallet_health` calculates health score
- [ ] `check_wallet_health` detects UTXO fragmentation
- [ ] `monitor_balance` triggers alerts
- [ ] `multisig_action` handles sign/reject/status

### 8.7.4 Market Awareness Tests
- [ ] `get_market_data` returns current price
- [ ] `get_market_data` supports multiple currencies
- [ ] `set_price_alert` stores alerts
- [ ] `analyze_market_trend` identifies trends

### 8.7.5 Savings Tests
- [ ] `plan_savings` calculates DCA targets
- [ ] `plan_savings` creates milestones
- [ ] `plan_savings` stores in Qube Locker
- [ ] `setup_dca` calculates schedule

### 8.7.6 Token Knowledge Tests
- [ ] `identify_token` queries BCMR
- [ ] `identify_token` logs new token facts
- [ ] `manage_cashtokens` lists tokens
- [ ] `manage_cashtokens` sends tokens

### 8.7.7 LEARNING Block Tests
- [ ] Wallet insights logged correctly
- [ ] Fee patterns recorded
- [ ] Market patterns tracked
- [ ] Savings plans as procedures
```

---

## Files Modified Summary

| File | Action | Description |
|------|--------|-------------|
| `ai/tools/finance_tools.py` | CREATE | All 14 Finance tool handlers |
| `ai/tools/handlers.py` | MODIFY | Add finance to SKILL_TREE |
| `core/xp_router.py` | MODIFY | Add FINANCE_TOOLS mapping |
| `src/types/skills.ts` | MODIFY | Add TypeScript interfaces |

---

## Estimated Effort

| Task | Complexity | Hours |
|------|------------|-------|
| 8.1 Update Skill Definitions | Low | 1 |
| 8.2 Verify Sun Tool | Low | 1 |
| 8.3 Implement Planet Tools | High | 8 |
| 8.4 Implement Moon Tools | High | 8 |
| 8.5 Update XP Routing | Low | 1 |
| 8.6 Frontend Integration | Low | 2 |
| 8.7 Testing | Medium | 4 |
| **Total** | | **25 hours** |

---

## Notes

1. **`send_bch` Exists**: The Sun tool is already implemented. This phase adds the supporting infrastructure.

2. **BCH Focus**: Finance is specifically designed for BCH/CashToken operations, not generic crypto trading.

3. **Career Paths**: The planet structure supports specialization - a "Treasurer" Qube would focus on Wallet Management and Transaction Mastery.

4. **LEARNING Integration**: Finance tools create LEARNING blocks for:
   - Wallet health insights
   - Fee patterns
   - Market trends
   - Savings procedures

5. **Privacy**: Balance categorization uses ranges ("small", "medium", "large") rather than exact amounts to protect privacy in LEARNING blocks.

6. **Price Alerts**: Stored in memory (`qube._price_alerts`). Production would persist to chain state.
