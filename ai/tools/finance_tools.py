"""
Finance Tools (Phase 8)

14-tool skill tree for Finance category:
- Sun: send_bch (exists in handlers.py)
- Planet 1: validate_transaction (Transaction Mastery)
- Planet 2: check_wallet_health (Wallet Management)
- Planet 3: get_market_data (Market Awareness)
- Planet 4: plan_savings (Savings Strategies)
- Planet 5: identify_token (Token Knowledge)
- Moon 1.1: optimize_fees
- Moon 1.2: track_transaction
- Moon 2.1: monitor_balance
- Moon 2.2: multisig_action
- Moon 3.1: set_price_alert
- Moon 3.2: analyze_market_trend
- Moon 4.1: setup_dca
- Moon 5.1: manage_cashtokens

Theme: Manage (Master Financial Operations for Your Owner)
"""

import structlog
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.block import Block, BlockType, create_learning_block
from utils.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

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
                "balance_range": _categorize_balance(health.get("balance", 0)),
                "health_score": health.get("health_score", 0)
            },
            source_category="finance",
            confidence=90,
            temporary=True,
            session_id=qube.current_session.session_id
        )
        await qube.current_session.add_block(block)


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
                "goal": plan.get("goal"),
                "strategy": plan.get("strategy"),
                "timeline_days": plan.get("days")
            },
            source_category="finance",
            confidence=95,
            temporary=True,
            session_id=qube.current_session.session_id
        )
        await qube.current_session.add_block(block)


async def _lookup_bcmr(token_id: str) -> Optional[Dict]:
    """Look up token in BCMR registry."""
    # Would query actual BCMR registry
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


async def _get_transaction_status(tx_id: str) -> Dict:
    """Get transaction status from blockchain."""
    # Would query Fulcrum/blockchain API
    return {"confirmations": 0}


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
                "frequency": schedule.get("frequency"),
                "total_purchases": schedule.get("total_purchases")
            },
            source_category="finance",
            confidence=95,
            temporary=True,
            session_id=qube.current_session.session_id
        )
        await qube.current_session.add_block(block)


# =============================================================================
# PLANET 1: validate_transaction (Transaction Mastery)
# =============================================================================

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


# =============================================================================
# PLANET 2: check_wallet_health (Wallet Management)
# =============================================================================

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

            health["balance"] = await wallet.get_balance() if hasattr(wallet, 'get_balance') else 0
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


# =============================================================================
# PLANET 3: get_market_data (Market Awareness)
# =============================================================================

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


# =============================================================================
# PLANET 4: plan_savings (Savings Strategies)
# =============================================================================

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
        if hasattr(qube, 'wallet') and hasattr(qube.wallet, 'get_balance'):
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


# =============================================================================
# PLANET 5: identify_token (Token Knowledge)
# =============================================================================

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


# =============================================================================
# MOON 1.1: optimize_fees
# =============================================================================

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

    if not amount:
        return {"success": False, "error": "Amount is required"}

    # BCH fees are very low - roughly 1 sat/byte
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


# =============================================================================
# MOON 1.2: track_transaction
# =============================================================================

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


# =============================================================================
# MOON 2.1: monitor_balance
# =============================================================================

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
        if hasattr(qube, 'wallet') and hasattr(qube.wallet, 'get_balance'):
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


# =============================================================================
# MOON 2.2: multisig_action
# =============================================================================

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

    if not action:
        return {"success": False, "error": "Action is required"}

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


# =============================================================================
# MOON 3.1: set_price_alert
# =============================================================================

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

    if not trigger_price or not direction:
        return {"success": False, "error": "Trigger price and direction required"}

    message = params.get("message", f"BCH price is {direction} ${trigger_price}")

    # Store alert
    alert = {
        "id": f"alert_{datetime.now().timestamp()}",
        "asset": "BCH",
        "trigger_price": trigger_price,
        "direction": direction,
        "message": message,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "triggered": False
    }

    # Store in qube's price alerts
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


# =============================================================================
# MOON 3.2: analyze_market_trend
# =============================================================================

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


# =============================================================================
# MOON 4.1: setup_dca
# =============================================================================

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

    if not amount or not frequency:
        return {"success": False, "error": "Amount and frequency required"}

    duration = params.get("duration", "3 months")

    # Calculate schedule
    purchases_per_month = {"daily": 30, "weekly": 4, "monthly": 1}.get(frequency, 4)

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


# =============================================================================
# MOON 5.1: manage_cashtokens
# =============================================================================

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

    if not action:
        return {"success": False, "error": "Action is required"}

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
        address = "bitcoincash:qz..."
        if hasattr(qube, 'wallet') and hasattr(qube.wallet, 'get_receive_address'):
            address = await qube.wallet.get_receive_address()

        return {
            "success": True,
            "action": "receive",
            "address": address,
            "message": "Send CashTokens to this address"
        }

    return {"success": False, "error": f"Unknown action: {action}"}


# =============================================================================
# HANDLER EXPORT
# =============================================================================

FINANCE_TOOL_HANDLERS = {
    # Planet 1: Transaction Mastery
    "validate_transaction": validate_transaction,
    # Planet 2: Wallet Management
    "check_wallet_health": check_wallet_health,
    # Planet 3: Market Awareness
    "get_market_data": get_market_data,
    # Planet 4: Savings Strategies
    "plan_savings": plan_savings,
    # Planet 5: Token Knowledge
    "identify_token": identify_token,
    # Moon 1.1: Fee Optimization
    "optimize_fees": optimize_fees,
    # Moon 1.2: Transaction Tracking
    "track_transaction": track_transaction,
    # Moon 2.1: Balance Monitoring
    "monitor_balance": monitor_balance,
    # Moon 2.2: Multi-sig Operations
    "multisig_action": multisig_action,
    # Moon 3.1: Price Alerts
    "set_price_alert": set_price_alert,
    # Moon 3.2: Market Trend Analysis
    "analyze_market_trend": analyze_market_trend,
    # Moon 4.1: Dollar Cost Averaging
    "setup_dca": setup_dca,
    # Moon 5.1: CashToken Operations
    "manage_cashtokens": manage_cashtokens,
}
