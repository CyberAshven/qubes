# Managed API Implementation Plan

## Overview

Hybrid model where users can choose:
- **BYOK (Bring Your Own Keys)**: Free, current behavior
- **Managed Mode**: Monthly subscription, API calls proxied through qube.cash

---

## Phase 1: Backend Proxy Infrastructure

### 1.1 New Server Endpoints

Create `/api/v2/ai/` routes on qube.cash:

```
POST /api/v2/ai/chat          - Proxied chat completion
POST /api/v2/ai/embeddings    - Proxied embeddings
GET  /api/v2/ai/models        - Available models for tier
GET  /api/v2/ai/usage         - User's current usage stats
```

### 1.2 New Server Files

```
/var/www/your-domain/api/
├── services/
│   ├── ai_proxy.py           # Routes requests to providers
│   ├── usage_tracker.py      # Tracks tokens/messages per user
│   └── subscription.py       # Manages subscription status
├── routes/
│   └── ai_routes.py          # FastAPI routes for /ai/*
└── models/
    └── subscription.py       # Pydantic models
```

### 1.3 AI Proxy Service

```python
# /api/services/ai_proxy.py

from typing import Optional, Dict, Any
import httpx
from enum import Enum

class SubscriptionTier(Enum):
    FREE_TRIAL = "free_trial"      # 50 messages/day, basic models
    STANDARD = "standard"          # $10/mo, 500 messages/day
    PREMIUM = "premium"            # $20/mo, unlimited, all models

# Model access per tier
TIER_MODELS = {
    SubscriptionTier.FREE_TRIAL: [
        "gemini-2.0-flash",
        "gpt-4o-mini",
    ],
    SubscriptionTier.STANDARD: [
        "gemini-2.0-flash",
        "gpt-4o-mini",
        "claude-3-5-haiku",
        "deepseek-chat",
    ],
    SubscriptionTier.PREMIUM: [
        "gemini-2.0-flash",
        "gemini-2.5-pro",
        "gpt-4o-mini",
        "gpt-4o",
        "claude-3-5-haiku",
        "claude-sonnet-4-5",
        "deepseek-chat",
        "deepseek-reasoner",
        "perplexity-sonar",
    ],
}

# Daily message limits
TIER_LIMITS = {
    SubscriptionTier.FREE_TRIAL: 50,
    SubscriptionTier.STANDARD: 500,
    SubscriptionTier.PREMIUM: 999999,  # Effectively unlimited
}

class AIProxyService:
    """Proxies AI requests using platform API keys"""

    def __init__(self):
        # Load platform API keys from environment/secrets
        self.api_keys = {
            "openai": os.getenv("PLATFORM_OPENAI_KEY"),
            "anthropic": os.getenv("PLATFORM_ANTHROPIC_KEY"),
            "google": os.getenv("PLATFORM_GOOGLE_KEY"),
            "deepseek": os.getenv("PLATFORM_DEEPSEEK_KEY"),
            "perplexity": os.getenv("PLATFORM_PERPLEXITY_KEY"),
        }

    async def chat_completion(
        self,
        user_id: str,
        model: str,
        messages: list,
        subscription_tier: SubscriptionTier,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Proxy a chat completion request

        Returns:
            Response dict with 'content', 'usage', 'model' keys
        """
        # Check model access
        if model not in TIER_MODELS[subscription_tier]:
            raise PermissionError(f"Model {model} not available on {subscription_tier.value} tier")

        # Route to appropriate provider
        provider = self._get_provider_for_model(model)

        if provider == "openai":
            return await self._call_openai(model, messages, **kwargs)
        elif provider == "anthropic":
            return await self._call_anthropic(model, messages, **kwargs)
        elif provider == "google":
            return await self._call_google(model, messages, **kwargs)
        # ... etc

    def _get_provider_for_model(self, model: str) -> str:
        if model.startswith("gpt"):
            return "openai"
        elif model.startswith("claude"):
            return "anthropic"
        elif model.startswith("gemini"):
            return "google"
        elif model.startswith("deepseek"):
            return "deepseek"
        elif model.startswith("perplexity") or model.startswith("sonar"):
            return "perplexity"
        raise ValueError(f"Unknown model: {model}")
```

### 1.4 Usage Tracking

```python
# /api/services/usage_tracker.py

from datetime import datetime, date
from typing import Optional
import json

class UsageTracker:
    """Track API usage per user"""

    def __init__(self, redis_client=None):
        # Use Redis for fast counters, fallback to file-based
        self.redis = redis_client
        self.usage_dir = Path("/var/www/your-domain/data/usage")
        self.usage_dir.mkdir(exist_ok=True)

    async def check_and_increment(
        self,
        user_id: str,
        tier: SubscriptionTier,
        tokens_used: int = 0
    ) -> tuple[bool, dict]:
        """
        Check if user is within limits and increment usage

        Returns:
            (allowed: bool, usage_info: dict)
        """
        today = date.today().isoformat()
        key = f"usage:{user_id}:{today}"

        # Get current usage
        current = await self._get_usage(key)
        limit = TIER_LIMITS[tier]

        if current["messages"] >= limit:
            return False, {
                "allowed": False,
                "messages_used": current["messages"],
                "messages_limit": limit,
                "resets_at": "midnight UTC"
            }

        # Increment
        current["messages"] += 1
        current["tokens"] += tokens_used
        await self._set_usage(key, current)

        return True, {
            "allowed": True,
            "messages_used": current["messages"],
            "messages_limit": limit,
            "messages_remaining": limit - current["messages"]
        }

    async def get_usage_stats(self, user_id: str) -> dict:
        """Get usage statistics for dashboard"""
        today = date.today().isoformat()
        key = f"usage:{user_id}:{today}"
        current = await self._get_usage(key)

        # Also get monthly totals
        # ... implementation

        return {
            "today": current,
            "this_month": monthly,
            "tier": tier.value,
            "limit": TIER_LIMITS[tier]
        }
```

---

## Phase 2: Client-Side Changes

### 2.1 New Config Option

Add to `config/user_preferences.py`:

```python
@dataclass
class APIMode:
    """API access mode configuration"""
    mode: str = "byok"  # "byok" or "managed"
    subscription_tier: Optional[str] = None
    subscription_expires: Optional[str] = None
```

### 2.2 Model Registry Changes

Modify `ai/model_registry.py` to support managed mode:

```python
class ModelRegistry:
    def __init__(self, api_mode: str = "byok", managed_token: str = None):
        self.api_mode = api_mode
        self.managed_token = managed_token  # JWT for managed API auth

    async def get_client(self, provider: str, model: str):
        if self.api_mode == "managed":
            # Return a proxy client that calls qube.cash
            return ManagedAPIClient(
                base_url="https://qube.cash/api/v2/ai",
                token=self.managed_token,
                model=model
            )
        else:
            # Current behavior - use user's own API keys
            return self._get_direct_client(provider, model)
```

### 2.3 Managed API Client

New file `ai/managed_client.py`:

```python
"""
Client for managed API mode - routes requests through qube.cash
"""

import httpx
from typing import AsyncIterator, Dict, Any, List

class ManagedAPIClient:
    """
    Unified client for managed API mode.
    Routes all AI requests through qube.cash proxy.
    """

    def __init__(self, base_url: str, token: str, model: str):
        self.base_url = base_url
        self.token = token
        self.model = model

    async def chat(
        self,
        messages: List[Dict[str, str]],
        stream: bool = True,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Send chat completion request through managed proxy
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/chat",
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": stream,
                    **kwargs
                },
                timeout=120.0
            )

            if response.status_code == 429:
                raise RateLimitError("Daily message limit reached")
            elif response.status_code == 403:
                raise PermissionError("Model not available on your tier")

            response.raise_for_status()

            if stream:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        yield line[6:]
            else:
                data = response.json()
                yield data["content"]

    async def get_usage(self) -> Dict[str, Any]:
        """Get current usage statistics"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/usage",
                headers={"Authorization": f"Bearer {self.token}"}
            )
            return response.json()
```

### 2.4 Frontend Settings UI

Add to Settings tab - new "API Access" section:

```tsx
// components/settings/APIAccessSettings.tsx

interface APIAccessSettingsProps {
  currentMode: 'byok' | 'managed';
  subscription?: {
    tier: string;
    expires: string;
    usage: { messages: number; limit: number };
  };
  onModeChange: (mode: 'byok' | 'managed') => void;
}

export const APIAccessSettings: React.FC<APIAccessSettingsProps> = ({
  currentMode,
  subscription,
  onModeChange
}) => {
  return (
    <GlassCard className="p-6 space-y-6">
      <h3 className="text-lg font-display text-text-primary">API Access</h3>

      {/* Mode Selection */}
      <div className="grid grid-cols-2 gap-4">
        {/* BYOK Option */}
        <div
          className={`p-4 rounded-lg border-2 cursor-pointer ${
            currentMode === 'byok'
              ? 'border-accent-primary bg-accent-primary/10'
              : 'border-glass-border'
          }`}
          onClick={() => onModeChange('byok')}
        >
          <h4 className="font-medium text-text-primary">Bring Your Own Keys</h4>
          <p className="text-sm text-text-secondary mt-1">
            Use your own API keys from OpenAI, Anthropic, etc.
          </p>
          <p className="text-sm text-accent-success mt-2">Free</p>
        </div>

        {/* Managed Option */}
        <div
          className={`p-4 rounded-lg border-2 cursor-pointer ${
            currentMode === 'managed'
              ? 'border-accent-primary bg-accent-primary/10'
              : 'border-glass-border'
          }`}
          onClick={() => onModeChange('managed')}
        >
          <h4 className="font-medium text-text-primary">Managed (Easy Mode)</h4>
          <p className="text-sm text-text-secondary mt-1">
            We handle the AI providers. Just chat.
          </p>
          <p className="text-sm text-accent-primary mt-2">From $10/month</p>
        </div>
      </div>

      {/* Subscription Details (if managed) */}
      {currentMode === 'managed' && subscription && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <span className="text-text-secondary">Current Tier</span>
            <span className="text-text-primary font-medium capitalize">
              {subscription.tier}
            </span>
          </div>

          {/* Usage Bar */}
          <div>
            <div className="flex justify-between text-sm mb-1">
              <span className="text-text-secondary">Today's Usage</span>
              <span className="text-text-primary">
                {subscription.usage.messages} / {subscription.usage.limit}
              </span>
            </div>
            <div className="h-2 bg-glass-dark rounded-full overflow-hidden">
              <div
                className="h-full bg-accent-primary"
                style={{
                  width: `${(subscription.usage.messages / subscription.usage.limit) * 100}%`
                }}
              />
            </div>
          </div>

          {/* Manage Subscription Button */}
          <GlassButton
            variant="secondary"
            onClick={() => window.open('https://qube.cash/account', '_blank')}
          >
            Manage Subscription
          </GlassButton>
        </div>
      )}

      {/* BYOK API Keys (if byok mode) */}
      {currentMode === 'byok' && (
        <APIKeysManager />  // Existing component
      )}
    </GlassCard>
  );
};
```

---

## Phase 3: Payment Integration

### 3.1 Stripe Setup

1. Create Stripe account
2. Set up Products:
   - `prod_standard`: Standard tier ($10/month)
   - `prod_premium`: Premium tier ($20/month)
3. Configure webhook endpoint: `https://qube.cash/api/v2/webhooks/stripe`

### 3.2 Subscription Service

```python
# /api/services/subscription.py

import stripe
from datetime import datetime
from typing import Optional

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

class SubscriptionService:
    """Manage user subscriptions via Stripe"""

    PRICE_IDS = {
        "standard": "price_xxx",  # $10/month
        "premium": "price_yyy",   # $20/month
    }

    async def create_checkout_session(
        self,
        user_id: str,
        tier: str,
        success_url: str,
        cancel_url: str
    ) -> str:
        """Create Stripe checkout session, return URL"""
        session = stripe.checkout.Session.create(
            mode="subscription",
            payment_method_types=["card"],
            line_items=[{
                "price": self.PRICE_IDS[tier],
                "quantity": 1,
            }],
            success_url=success_url,
            cancel_url=cancel_url,
            client_reference_id=user_id,
            metadata={"user_id": user_id, "tier": tier}
        )
        return session.url

    async def handle_webhook(self, payload: bytes, signature: str) -> dict:
        """Handle Stripe webhook events"""
        event = stripe.Webhook.construct_event(
            payload, signature, os.getenv("STRIPE_WEBHOOK_SECRET")
        )

        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            user_id = session["client_reference_id"]
            # Activate subscription
            await self._activate_subscription(user_id, session)

        elif event["type"] == "customer.subscription.deleted":
            # Downgrade to free
            subscription = event["data"]["object"]
            user_id = subscription["metadata"]["user_id"]
            await self._deactivate_subscription(user_id)

        return {"status": "ok"}

    async def get_subscription(self, user_id: str) -> Optional[dict]:
        """Get user's current subscription status"""
        # Query database
        sub = await db.subscriptions.find_one({"user_id": user_id})
        if not sub:
            return None

        return {
            "tier": sub["tier"],
            "status": sub["status"],
            "current_period_end": sub["current_period_end"],
            "cancel_at_period_end": sub.get("cancel_at_period_end", False)
        }
```

### 3.3 Database Schema

Simple SQLite or PostgreSQL:

```sql
-- Subscriptions table
CREATE TABLE subscriptions (
    user_id TEXT PRIMARY KEY,
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,
    tier TEXT NOT NULL DEFAULT 'free_trial',
    status TEXT NOT NULL DEFAULT 'active',
    current_period_start TIMESTAMP,
    current_period_end TIMESTAMP,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Daily usage tracking
CREATE TABLE usage_daily (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    date DATE NOT NULL,
    messages_count INTEGER DEFAULT 0,
    tokens_input INTEGER DEFAULT 0,
    tokens_output INTEGER DEFAULT 0,
    UNIQUE(user_id, date)
);

-- Index for fast lookups
CREATE INDEX idx_usage_user_date ON usage_daily(user_id, date);
```

---

## Phase 4: Tauri Commands

### 4.1 New Commands

Add to `src-tauri/src/lib.rs`:

```rust
#[tauri::command]
async fn get_api_mode(user_id: &str) -> Result<ApiModeResponse, String> {
    // Returns current mode (byok/managed) and subscription info
}

#[tauri::command]
async fn set_api_mode(user_id: &str, mode: &str, password: &str) -> Result<(), String> {
    // Switch between byok and managed mode
}

#[tauri::command]
async fn get_subscription_status(user_id: &str) -> Result<SubscriptionStatus, String> {
    // Get current subscription tier, usage, etc.
}

#[tauri::command]
async fn create_checkout_session(user_id: &str, tier: &str) -> Result<String, String> {
    // Returns Stripe checkout URL
}

#[tauri::command]
async fn get_managed_token(user_id: &str, password: &str) -> Result<String, String> {
    // Get JWT token for managed API calls
}
```

---

## Phase 5: Free Trial Flow

### 5.1 New User Experience

1. User creates account (existing flow)
2. Wizard offers choice:
   - "I have API keys" → BYOK setup
   - "Set up for me" → Managed mode (free trial)
3. Free trial: 7 days, 50 messages/day, basic models
4. Trial ending → prompt to subscribe or switch to BYOK

### 5.2 Trial Management

```python
class TrialService:
    TRIAL_DAYS = 7
    TRIAL_DAILY_LIMIT = 50

    async def start_trial(self, user_id: str) -> dict:
        """Start free trial for new user"""
        expires = datetime.utcnow() + timedelta(days=self.TRIAL_DAYS)

        await db.subscriptions.insert_one({
            "user_id": user_id,
            "tier": "free_trial",
            "status": "trialing",
            "trial_end": expires,
            "created_at": datetime.utcnow()
        })

        return {
            "tier": "free_trial",
            "trial_ends": expires.isoformat(),
            "daily_limit": self.TRIAL_DAILY_LIMIT
        }

    async def check_trial_status(self, user_id: str) -> dict:
        """Check if trial is still active"""
        sub = await db.subscriptions.find_one({"user_id": user_id})

        if sub["tier"] == "free_trial":
            if datetime.utcnow() > sub["trial_end"]:
                return {
                    "active": False,
                    "reason": "trial_expired",
                    "message": "Your free trial has ended. Subscribe to continue using managed mode."
                }

        return {"active": True}
```

---

## Implementation Order

### Week 1-2: Server Infrastructure
- [ ] Set up PostgreSQL/SQLite on server
- [ ] Implement ai_proxy.py with OpenAI + Anthropic
- [ ] Implement usage_tracker.py
- [ ] Create /api/v2/ai/* routes
- [ ] Test with curl/Postman

### Week 3: Client Integration
- [ ] Create managed_client.py
- [ ] Modify model_registry.py for dual mode
- [ ] Add api_mode to user preferences
- [ ] Test end-to-end with hardcoded managed mode

### Week 4: Payment Integration
- [ ] Set up Stripe account and products
- [ ] Implement subscription.py
- [ ] Add webhook endpoint
- [ ] Test subscription flow

### Week 5: UI Polish
- [ ] Build APIAccessSettings component
- [ ] Add usage dashboard
- [ ] Update setup wizard for mode selection
- [ ] Add trial expiration warnings

### Week 6: Launch Prep
- [ ] Security audit (rate limits, abuse prevention)
- [ ] Documentation
- [ ] Pricing page on website
- [ ] Beta test with small group

---

## Cost Management Tips

1. **Default to cheap models** - Gemini Flash and GPT-4o-mini are very affordable
2. **Cache common queries** - System prompts, skill descriptions don't change
3. **Set hard limits** - Even "unlimited" should have a 10K/day safety cap
4. **Monitor daily** - Set up alerts for unusual usage patterns
5. **Negotiate with providers** - At scale, you can get volume discounts

---

## Security Considerations

1. **JWT tokens** - Short-lived (1 hour), refresh mechanism
2. **Rate limiting** - Per user AND per IP
3. **Request validation** - Sanitize all inputs before forwarding to AI
4. **Audit logging** - Log all managed API calls for abuse detection
5. **Abuse detection** - Flag accounts with unusual patterns
