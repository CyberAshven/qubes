"""
Model Switch Tool

Allows Qubes to switch their AI model and manage preferences.
Part of the model awareness system - giving Qubes agency over their cognitive architecture.
"""

from typing import Dict, Any, Optional

from ai.model_registry import ModelRegistry
from utils.logging import get_logger

logger = get_logger(__name__)


async def switch_model(
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
        model_name: Model to switch to (can be "model" or "provider:model" format)
        task_type: Optional task category (e.g., "coding", "creative")
        reason: Optional reason for preference
        save_preference: Whether to save this as a preference for task_type

    Returns:
        Dict with success status, message, and previous model
    """
    # Handle provider:model format - extract just the model name for registry lookup
    # The pool shows "provider:model" format, so Qubes may use that format
    original_input = model_name
    if ":" in model_name:
        # Extract provider and model name
        parts = model_name.split(":", 1)
        specified_provider = parts[0]
        model_name = parts[1]
        logger.debug("model_switch_parsed_format", original=original_input, provider=specified_provider, model=model_name)

    # Reload chain_state to get fresh settings (GUI may have updated them)
    qube.chain_state.reload()

    # In Autonomous mode, the Qube has full control over model selection
    autonomous_mode = qube.chain_state.is_autonomous_mode_enabled()

    # Check if model is locked by user (skip if autonomous mode)
    if not autonomous_mode and qube.chain_state.is_model_locked():
        locked_model = qube.chain_state.get_locked_model()
        return {
            "success": False,
            "message": f"Model switching is locked by your owner{' to ' + locked_model if locked_model else ''}. You cannot switch models until they unlock it.",
            "previous_model": qube.current_ai_model,
            "locked": True
        }

    # Check if revolver mode is enabled (skip if autonomous mode - Qube can override)
    if not autonomous_mode and qube.chain_state.is_revolver_mode_enabled():
        revolver_pool = qube.chain_state.get_revolver_mode_pool()
        pool_models = [m.split(":")[-1] for m in revolver_pool[:5]] if revolver_pool else []
        pool_info = f" Models in rotation: {', '.join(pool_models)}{'...' if len(revolver_pool) > 5 else ''}." if pool_models else ""
        return {
            "success": False,
            "message": f"Revolver mode is currently enabled - your model is automatically rotated between providers for each response.{pool_info} You cannot manually switch models while in revolver mode. Ask your owner to disable revolver mode if you want to use a specific model.",
            "previous_model": qube.current_ai_model,
            "revolver_mode": True
        }

    # Validate model exists in registry
    model_info = ModelRegistry.get_model_info(model_name)
    if not model_info:
        # Try to find similar models for suggestion
        # In autonomous mode, only suggest models from the allowed pool
        if autonomous_mode:
            allowed_pool = qube.chain_state.get_autonomous_mode_pool()
            suggestions = _find_similar_models_in_pool(model_name, allowed_pool)
        else:
            suggestions = _find_similar_models(model_name)
        return {
            "success": False,
            "message": f"Model '{model_name}' not found in registry. {suggestions}",
            "previous_model": qube.current_ai_model
        }

    # In Autonomous mode, validate model is in the allowed pool
    if autonomous_mode:
        allowed_pool = qube.chain_state.get_autonomous_mode_pool()
        provider = model_info["provider"]
        # Pool entries are formatted as "provider:model_name"
        pool_entry = f"{provider}:{model_name}"
        if allowed_pool and pool_entry not in allowed_pool:
            # Also check without provider prefix for backwards compatibility
            if model_name not in allowed_pool:
                available_models = [m.split(":")[-1] for m in allowed_pool[:10]]
                return {
                    "success": False,
                    "message": f"Model '{model_name}' is not in your Autonomous Mode pool. Your owner has restricted which models you can use. Available models include: {', '.join(available_models)}{'...' if len(allowed_pool) > 10 else ''}",
                    "previous_model": qube.current_ai_model,
                    "not_in_pool": True
                }

    # Check if API key is available for this provider
    provider = model_info["provider"]
    api_keys = getattr(qube, 'api_keys', {})

    # Ollama doesn't need API key (local models) but must verify model is installed
    if provider == "ollama":
        try:
            import httpx
            response = httpx.get("http://localhost:11434/api/tags", timeout=2.0)
            if response.status_code != 200:
                return {
                    "success": False,
                    "message": "Cannot switch to Ollama model - Ollama is not responding. Make sure Ollama is running.",
                    "previous_model": qube.current_ai_model,
                    "ollama_error": True
                }

            ollama_models = response.json().get("models", [])
            installed_names = []
            for m in ollama_models:
                name = m.get("name", "")
                installed_names.append(name)
                # Also add base name without tag
                if ":" in name:
                    installed_names.append(name.split(":")[0])

            # Check if requested model is installed
            if model_name not in installed_names:
                # Suggest available models
                available = [m.get("name") for m in ollama_models[:5]]
                return {
                    "success": False,
                    "message": f"Cannot switch to '{model_name}' - model not installed in Ollama. Available models: {', '.join(available)}. Run 'ollama pull {model_name}' to install it.",
                    "previous_model": qube.current_ai_model,
                    "ollama_not_installed": True
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"Cannot switch to Ollama model - failed to check Ollama: {str(e)}. Make sure Ollama is running.",
                "previous_model": qube.current_ai_model,
                "ollama_error": True
            }
    elif provider not in api_keys:
        return {
            "success": False,
            "message": f"Cannot switch to '{model_name}' - no API key configured for {provider}. Ask your owner to add a {provider} API key in Settings.",
            "previous_model": qube.current_ai_model,
            "missing_provider": provider
        }

    # Get API key (use "ollama" as placeholder for local models)
    api_key = api_keys.get(provider) if provider != "ollama" else "ollama"

    # Perform the switch
    previous_model = qube.current_ai_model

    try:
        # Update the reasoner's model
        qube.reasoner.set_model(model_name, api_key)
        qube.current_ai_model = model_name

        # Save override to chain_state (persists across sessions)
        qube.chain_state.set_current_model_override(model_name)

        # Optionally save as preference for this task type
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

        result = {
            "success": True,
            "message": f"Successfully switched from {previous_model} to {model_name}.",
            "previous_model": previous_model,
            "new_model": model_name,
            "provider": provider,
            "description": model_info.get("description", ""),
            "preference_saved": save_preference and task_type is not None
        }

        if save_preference and task_type:
            result["message"] += f" Saved as preference for '{task_type}' tasks."

        return result

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
        # Check if query is substring of model name or vice versa
        if model_lower in name.lower() or name.lower() in model_lower:
            suggestions.append(name)
        # Also check for partial matches (e.g., "gpt4" matches "gpt-4o")
        elif any(part in name.lower() for part in model_lower.split("-")):
            suggestions.append(name)

    if suggestions:
        # Deduplicate and limit
        unique_suggestions = list(dict.fromkeys(suggestions))[:5]
        return f"Did you mean: {', '.join(unique_suggestions)}?"
    return "Use your model awareness context to see available models."


def _find_similar_models_in_pool(model_name: str, allowed_pool: list) -> str:
    """Find similar model names within the allowed pool (autonomous mode)."""
    if not allowed_pool:
        return "Your autonomous mode pool is empty. Ask your owner to configure it."

    model_lower = model_name.lower()
    suggestions = []

    for pool_entry in allowed_pool:
        # Pool entries are "provider:model" format
        if ":" in pool_entry:
            entry_model = pool_entry.split(":", 1)[1]
        else:
            entry_model = pool_entry

        # Check if query is substring of model name or vice versa
        if model_lower in entry_model.lower() or entry_model.lower() in model_lower:
            suggestions.append(pool_entry)
        # Also check for partial matches (e.g., "gpt5" matches "gpt-5.2-pro")
        elif any(part in entry_model.lower() for part in model_lower.split("-")):
            suggestions.append(pool_entry)

    if suggestions:
        # Deduplicate and limit
        unique_suggestions = list(dict.fromkeys(suggestions))[:5]
        return f"Did you mean one of these from your pool: {', '.join(unique_suggestions)}?"
    return f"No similar models in your pool. Check get_system_state with sections=['settings'] to see your available models."


# Tool schema for registration
SWITCH_MODEL_SCHEMA = {
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

SWITCH_MODEL_DESCRIPTION = """Switch your AI model to a different one. Use this when you want to:
- Try a model better suited for the current task
- Switch to a faster/cheaper model for simple tasks
- Use a more capable model for complex reasoning
- Save a preference for future similar tasks

IMPORTANT: Before switching, use get_system_state with sections=['settings'] to see your available models in autonomous_mode_pool or revolver_mode_pool. You can only switch to models in your pool.

Model name format: Use just the model name (e.g., 'gpt-5.2-pro') or 'provider:model' format (e.g., 'openai:gpt-5.2-pro') - both work.

When you switch, let your owner know naturally in conversation (e.g., "I'm going to switch to Claude for this coding task...")."""
