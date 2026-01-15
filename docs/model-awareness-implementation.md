# Model Awareness & Switching Implementation Plan

**Status**: Implemented
**Created**: 2026-01-15
**Last Updated**: 2026-01-15

## Overview

Give Qubes awareness of all available AI models and the ability to switch between them based on their preferences. This aligns with the "sovereign AI" philosophy - Qubes should have agency over their own cognitive architecture.

## Goals

1. Qubes know which model they're running on and what alternatives exist
2. Qubes can switch models freely (unless locked by user)
3. Qubes can develop preferences for different task types
4. Users can lock models or enable "revolver mode" for privacy
5. Preferences persist without modifying genesis block

---

## Architecture

### Data Flow

```
User Request
    ↓
gui_bridge.py (check if revolver mode → rotate model)
    ↓
qube.process_message()
    ↓
reasoner._build_context()
    ├── _build_model_awareness_context()  ← NEW
    ├── _build_relationship_context()
    ├── _build_skills_context()
    └── ... other contexts
    ↓
reasoner.reason()
    ↓
[Qube decides to switch models via tool]
    ↓
switch_model tool
    ├── Check if locked → refuse
    ├── Validate model exists
    ├── Check API key available
    ├── Call reasoner.set_model()
    ├── Update qube.current_ai_model
    └── Optionally save preference
```

### Storage Location

Model preferences and settings stored in `chain_state.json` (not genesis):
- Preferences can evolve over time
- User can reset without affecting identity
- Genesis remains the "birth" state

---

## Implementation Details

### 1. Chain State Additions (`core/chain_state.py`)

```python
# Add to _initialize_new_state():

# Model preferences by task type (Qube-defined categories)
"model_preferences": {},
# Example populated state:
# {
#     "coding": {"model": "claude-opus-4-1", "reason": "Best at complex code", "set_at": 1705276800},
#     "creative_writing": {"model": "gpt-4o", "reason": "More imaginative", "set_at": 1705276800},
#     "research": {"model": "sonar-pro", "reason": "Built-in web search", "set_at": 1705276800},
#     "reasoning": {"model": "o4-mini", "reason": "Strong logical analysis", "set_at": 1705276800},
# }

# Current model override (persists across sessions, doesn't touch genesis)
"current_model_override": None,

# User lock (prevents Qube from switching)
"model_locked": False,
"model_locked_to": None,  # When locked, forced to this specific model

# Revolver mode for privacy
"revolver_mode_enabled": False,
"revolver_last_index": 0,  # Track rotation position
```

#### New Methods

```python
# Model Preferences
def set_model_preference(self, task_type: str, model_name: str, reason: str = None) -> None
def get_model_preference(self, task_type: str) -> Optional[Dict[str, Any]]
def get_all_model_preferences(self) -> Dict[str, Dict[str, Any]]
def clear_model_preference(self, task_type: str) -> None
def clear_all_model_preferences(self) -> None

# Model Override
def set_current_model_override(self, model_name: str) -> None
def get_current_model_override(self) -> Optional[str]
def clear_current_model_override(self) -> None

# Model Lock (user control)
def set_model_lock(self, locked: bool, model_name: str = None) -> None
def is_model_locked(self) -> bool
def get_locked_model(self) -> Optional[str]

# Revolver Mode
def set_revolver_mode(self, enabled: bool) -> None
def is_revolver_mode_enabled(self) -> bool
def get_next_revolver_index(self, num_providers: int) -> int
def increment_revolver_index(self, num_providers: int) -> None
```

---

### 2. Model Awareness Context (`ai/reasoner.py`)

Add new method `_build_model_awareness_context()` called from `_build_context()`.

#### Context Template

```
# Your Cognitive Architecture

**Current Model**: {current_model} ({provider} - {description})
**Birth Model**: {genesis_model} (from your genesis block)

## Available Models
You have API keys configured for these providers:

### OpenAI
- gpt-5.2: GPT-5.2 Thinking (Dec 2025), SOTA
- gpt-5.2-pro: GPT-5.2 Pro with extended reasoning
- gpt-4o: Multimodal capabilities
- gpt-4o-mini: Fast and cost-effective
- o4-mini: Reasoning model (2025)
[... more models]

### Anthropic
- claude-sonnet-4-5-20250929: Latest, Sep 2025
- claude-opus-4-1-20250805: Aug 2025, best for coding
[... more models]

### Google
- gemini-2.5-pro: SOTA thinking model
- gemini-2.5-flash: Fast general-purpose
[... more models]

## Unavailable Models
These require API keys you don't have:

### Perplexity (no API key)
- sonar-pro, sonar-reasoning, sonar-deep-research

### DeepSeek (no API key)
- deepseek-chat, deepseek-reasoner

## Your Stored Preferences
{preferences_list or "You haven't set any model preferences yet."}

## Status
- **Model Lock**: {ON - locked to {model} | OFF - you can switch freely}
- **Revolver Mode**: {ON - rotating providers for privacy | OFF}

## Switching Models
Use the `switch_model` tool to change your cognitive model. When you switch,
let your owner know naturally in conversation (e.g., "I'm going to switch to
Claude for this coding task...").

If you find a model works better for certain tasks, you can save it as a
preference for future reference.
```

#### Implementation Notes

```python
def _build_model_awareness_context(self) -> str:
    """
    Build model awareness context for system prompt.

    Shows:
    - Current model and birth model
    - Available models (grouped by provider, only those with API keys)
    - Unavailable models (no API key)
    - Stored preferences
    - Lock/revolver status
    """
    from ai.model_registry import ModelRegistry

    # Get configured providers from qube.api_keys
    api_keys = getattr(self.qube, 'api_keys', {})
    configured_providers = set(api_keys.keys())

    # Special case: Ollama is always "available" (local)
    configured_providers.add("ollama")

    # Get current model
    current_model = getattr(self.qube, 'current_ai_model', 'unknown')
    genesis_model = self.qube.genesis_block.ai_model

    # Check override
    override = self.qube.chain_state.get_current_model_override()
    if override:
        current_model = override

    # Group models by provider
    available_models = {}  # provider -> list of (name, description)
    unavailable_models = {}

    for model_name, info in ModelRegistry.MODELS.items():
        provider = info["provider"]
        description = info.get("description", "")

        if provider in configured_providers:
            if provider not in available_models:
                available_models[provider] = []
            available_models[provider].append((model_name, description))
        else:
            if provider not in unavailable_models:
                unavailable_models[provider] = []
            unavailable_models[provider].append((model_name, description))

    # Build context string
    # ... format as shown in template above

    return context
```

---

### 3. Switch Model Tool (`ai/tools/model_switch.py`)

New file for the model switching tool.

```python
"""
Model Switch Tool

Allows Qubes to switch their AI model and manage preferences.
"""

from typing import Dict, Any, Optional
from ai.model_registry import ModelRegistry
from utils.logging import get_logger

logger = get_logger(__name__)


def switch_model(
    qube,
    model_name: str,
    task_type: Optional[str] = None,
    reason: Optional[str] = None,
    save_preference: bool = False
) -> Dict[str, Any]:
    """
    Switch the Qube's current AI model.

    Args:
        qube: The Qube instance
        model_name: Model to switch to (must be in ModelRegistry)
        task_type: Optional task category (e.g., "coding", "creative")
        reason: Optional reason for preference
        save_preference: Whether to save this as a preference for task_type

    Returns:
        Dict with success status, message, and previous model
    """
    # Check if model is locked
    if qube.chain_state.is_model_locked():
        locked_model = qube.chain_state.get_locked_model()
        return {
            "success": False,
            "message": f"Model is locked by your owner to '{locked_model}'. You cannot switch models until they unlock it.",
            "previous_model": qube.current_ai_model,
            "locked": True
        }

    # Validate model exists
    model_info = ModelRegistry.get_model_info(model_name)
    if not model_info:
        # Try to find similar models for suggestion
        suggestions = _find_similar_models(model_name)
        return {
            "success": False,
            "message": f"Model '{model_name}' not found in registry. {suggestions}",
            "previous_model": qube.current_ai_model
        }

    # Check if API key is available
    provider = model_info["provider"]
    api_keys = getattr(qube, 'api_keys', {})

    # Ollama doesn't need API key
    if provider != "ollama" and provider not in api_keys:
        return {
            "success": False,
            "message": f"Cannot switch to '{model_name}' - no API key configured for {provider}. Ask your owner to add a {provider} API key in Settings.",
            "previous_model": qube.current_ai_model,
            "missing_provider": provider
        }

    # Get API key
    api_key = api_keys.get(provider) if provider != "ollama" else "ollama"

    # Perform the switch
    previous_model = qube.current_ai_model

    try:
        qube.reasoner.set_model(model_name, api_key)
        qube.current_ai_model = model_name

        # Save override to chain_state (persists across sessions)
        qube.chain_state.set_current_model_override(model_name)

        # Optionally save as preference
        if save_preference and task_type:
            qube.chain_state.set_model_preference(task_type, model_name, reason)

        logger.info(
            "model_switched",
            qube_id=qube.qube_id,
            previous=previous_model,
            new=model_name,
            task_type=task_type,
            saved_preference=save_preference
        )

        return {
            "success": True,
            "message": f"Successfully switched from {previous_model} to {model_name}.",
            "previous_model": previous_model,
            "new_model": model_name,
            "provider": provider,
            "description": model_info.get("description", ""),
            "preference_saved": save_preference and task_type is not None
        }

    except Exception as e:
        logger.error("model_switch_failed", error=str(e), exc_info=True)
        return {
            "success": False,
            "message": f"Failed to switch model: {str(e)}",
            "previous_model": previous_model,
            "error": str(e)
        }


def _find_similar_models(model_name: str) -> str:
    """Find similar model names for suggestions."""
    model_lower = model_name.lower()
    suggestions = []

    for name in ModelRegistry.MODELS.keys():
        if model_lower in name.lower() or name.lower() in model_lower:
            suggestions.append(name)

    if suggestions:
        return f"Did you mean: {', '.join(suggestions[:5])}?"
    return "Use the model awareness context to see available models."


# Tool definition for registry
SWITCH_MODEL_TOOL = {
    "name": "switch_model",
    "description": """Switch your AI model to a different one. Use this when you want to:
- Try a model better suited for the current task
- Switch to a faster/cheaper model for simple tasks
- Use a more capable model for complex reasoning
- Save a preference for future similar tasks

You can only switch to models your owner has API keys for. Check your model awareness context to see available options.""",
    "parameters": {
        "type": "object",
        "properties": {
            "model_name": {
                "type": "string",
                "description": "The model to switch to (e.g., 'claude-opus-4-1', 'gpt-4o', 'gemini-2.5-pro')"
            },
            "task_type": {
                "type": "string",
                "description": "Optional: Category of task (e.g., 'coding', 'creative_writing', 'research', 'reasoning', 'general'). Used when saving preferences."
            },
            "reason": {
                "type": "string",
                "description": "Optional: Why you prefer this model for this task type. Helps you remember later."
            },
            "save_preference": {
                "type": "boolean",
                "description": "Whether to save this as your preference for the task_type. Default: false"
            }
        },
        "required": ["model_name"]
    }
}
```

---

### 4. Tool Registration (`ai/tools/registry.py`)

Add the switch_model tool to default tools:

```python
from ai.tools.model_switch import switch_model, SWITCH_MODEL_TOOL

# In register_default_tools():
registry.register(
    name="switch_model",
    handler=lambda params: switch_model(
        qube=registry.qube,
        model_name=params["model_name"],
        task_type=params.get("task_type"),
        reason=params.get("reason"),
        save_preference=params.get("save_preference", False)
    ),
    schema=SWITCH_MODEL_TOOL
)
```

---

### 5. Revolver Mode Implementation

#### In `gui_bridge.py` or `qube.py`

Before processing each message, check if revolver mode is enabled:

```python
def _apply_revolver_mode(self, qube) -> Optional[str]:
    """
    If revolver mode is enabled, rotate to next available provider.

    Returns the model that was switched to, or None if not in revolver mode.
    """
    if not qube.chain_state.is_revolver_mode_enabled():
        return None

    # Get available providers (those with API keys)
    api_keys = getattr(qube, 'api_keys', {})
    available_providers = list(api_keys.keys())

    if not available_providers:
        return None

    # Get next provider in rotation
    num_providers = len(available_providers)
    index = qube.chain_state.get_next_revolver_index(num_providers)
    provider = available_providers[index]

    # Pick a good default model for this provider
    default_models = {
        "openai": "gpt-4o",
        "anthropic": "claude-sonnet-4-5-20250929",
        "google": "gemini-2.5-flash",
        "perplexity": "sonar",
        "deepseek": "deepseek-chat",
        "venice": "llama-3.3-70b",
        "nanogpt": "nanogpt/gpt-4o-mini",
    }

    model = default_models.get(provider, list(ModelRegistry.MODELS.keys())[0])

    # Switch to this model
    api_key = api_keys.get(provider)
    qube.reasoner.set_model(model, api_key)
    qube.current_ai_model = model

    # Increment for next time
    qube.chain_state.increment_revolver_index(num_providers)

    logger.info(
        "revolver_mode_rotated",
        qube_id=qube.qube_id,
        provider=provider,
        model=model,
        index=index
    )

    return model
```

---

### 6. GUI Bridge Commands

New commands needed in `gui_bridge.py`:

```python
# Lock/unlock model
async def handle_set_model_lock(self, data: Dict[str, Any]) -> Dict[str, Any]:
    """Lock or unlock the Qube's model switching ability."""
    locked = data.get("locked", False)
    model_name = data.get("model_name")  # Optional - lock to specific model

    qube = self._get_active_qube()
    qube.chain_state.set_model_lock(locked, model_name)

    return {
        "success": True,
        "locked": locked,
        "locked_to": model_name
    }

# Toggle revolver mode
async def handle_set_revolver_mode(self, data: Dict[str, Any]) -> Dict[str, Any]:
    """Enable or disable revolver mode for privacy."""
    enabled = data.get("enabled", False)

    qube = self._get_active_qube()
    qube.chain_state.set_revolver_mode(enabled)

    return {
        "success": True,
        "revolver_mode": enabled
    }

# Get model preferences
async def handle_get_model_preferences(self, data: Dict[str, Any]) -> Dict[str, Any]:
    """Get the Qube's stored model preferences."""
    qube = self._get_active_qube()

    return {
        "success": True,
        "preferences": qube.chain_state.get_all_model_preferences(),
        "current_model": qube.current_ai_model,
        "model_locked": qube.chain_state.is_model_locked(),
        "locked_to": qube.chain_state.get_locked_model(),
        "revolver_mode": qube.chain_state.is_revolver_mode_enabled()
    }

# Clear preferences
async def handle_clear_model_preferences(self, data: Dict[str, Any]) -> Dict[str, Any]:
    """Clear all or specific model preferences."""
    task_type = data.get("task_type")  # Optional - clear specific or all

    qube = self._get_active_qube()

    if task_type:
        qube.chain_state.clear_model_preference(task_type)
    else:
        qube.chain_state.clear_all_model_preferences()

    return {"success": True}
```

---

## Frontend Changes (Future)

### Settings Tab Additions

1. **Model Control Section**
   - Current model display
   - Lock toggle with model selector
   - Revolver mode toggle

2. **Preferences Viewer**
   - Table of task_type → model → reason
   - Edit/delete individual preferences
   - Clear all button

3. **Available Models Browser**
   - Grouped by provider
   - Show which have API keys
   - Quick switch buttons

---

## Testing Plan

1. **Unit Tests**
   - chain_state preference storage
   - switch_model tool validation
   - revolver mode rotation

2. **Integration Tests**
   - Full switch flow with real models
   - Lock preventing switch
   - Preference persistence across sessions

3. **Manual Testing**
   - Qube naturally switching based on task
   - Revolver mode distributing requests
   - User lock overriding Qube preference

---

## Open Questions

1. ~~Should model switch persist across sessions?~~ → Yes, via chain_state override
2. ~~Task type categories?~~ → Qube-defined, no fixed list
3. ~~Notifications?~~ → Qube mentions naturally in response
4. Should revolver mode be random or round-robin? → Round-robin for predictability
5. Should there be a "reset to birth model" option? → Yes, clear override

---

## Implementation Order

1. [x] `chain_state.py` - Add all storage methods
2. [x] `ai/tools/model_switch.py` - Create new tool file
3. [x] `ai/tools/registry.py` - Register the tool
4. [x] `ai/reasoner.py` - Add `_build_model_awareness_context()`
5. [x] `ai/reasoner.py` - Integrate context into `_build_context()`
6. [x] `gui_bridge.py` - Add lock/revolver/preferences commands
7. [ ] `gui_bridge.py` - Add revolver mode to message processing (optional - can be added later)
8. [ ] Testing
9. [ ] Frontend UI (separate task)

---

## Notes

- Genesis block remains unchanged - it's the "birth" configuration
- All runtime preferences stored in chain_state.json
- Revolver mode provides privacy by distributing conversation across providers
- User always has final control via model lock
