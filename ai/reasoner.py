"""
Qube Reasoner - AI Decision Loop

Main reasoning loop for Qube AI agents with tool calling support.
Matches documentation in docs/09_AI_Integration_Tool_Calling.md Section 6.3
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import json

from ai.model_registry import ModelRegistry
from ai.providers.base import AIModelInterface, ModelResponse
from ai.tools.registry import ToolRegistry
from ai.fallback import AIFallbackChain
from core.block import create_message_block
from core.exceptions import AIError
from utils.logging import get_logger
from monitoring.metrics import MetricsRecorder

logger = get_logger(__name__)

# Short-term memory limit (context window for conversation)
# This includes both session blocks and permanent blocks
SHORT_TERM_MEMORY_LIMIT = 15

# Debug prompt storage - file-based for persistence across process invocations
import tempfile
import os
from pathlib import Path

_DEBUG_PROMPT_DIR = Path(tempfile.gettempdir()) / "qubes_debug_prompts"


def _get_debug_prompt_file(qube_id: str) -> Path:
    """Get the debug prompt file path for a qube."""
    _DEBUG_PROMPT_DIR.mkdir(parents=True, exist_ok=True)
    return _DEBUG_PROMPT_DIR / f"{qube_id}.json"


def save_debug_prompt(qube_id: str, prompt_info: Dict[str, Any]) -> None:
    """
    Save debug prompt info to file for persistence.

    Args:
        qube_id: The qube ID
        prompt_info: The prompt information to save
    """
    try:
        file_path = _get_debug_prompt_file(qube_id)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(prompt_info, f, indent=2, default=str)
    except Exception as e:
        logger.warning(f"Failed to save debug prompt: {e}")


def get_debug_prompt(qube_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the last debug prompt info for a qube.

    Args:
        qube_id: The qube ID to get prompt for

    Returns:
        Dict with prompt info or None if not found
    """
    try:
        file_path = _get_debug_prompt_file(qube_id)
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load debug prompt: {e}")
    return None


def get_all_debug_prompts() -> Dict[str, Dict[str, Any]]:
    """
    Get all cached debug prompts.

    Returns:
        Dict of all cached prompts keyed by qube_id
    """
    result = {}
    try:
        if _DEBUG_PROMPT_DIR.exists():
            for file_path in _DEBUG_PROMPT_DIR.glob("*.json"):
                qube_id = file_path.stem
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        result[qube_id] = json.load(f)
                except Exception:
                    pass
    except Exception as e:
        logger.warning(f"Failed to load all debug prompts: {e}")
    return result


class QubeReasoner:
    """
    Qube AI reasoning engine

    Handles:
    - Context building from memory
    - AI model inference
    - Tool calling loops
    - MESSAGE block creation (THOUGHT blocks only for complex reasoning)
    """

    def __init__(self, qube, enable_fallback: bool = True):
        """
        Initialize reasoner

        Args:
            qube: Qube instance
            enable_fallback: Enable AI fallback chain for reliability (default: True)
        """
        self.qube = qube
        self.model: Optional[AIModelInterface] = None
        self.tool_registry: Optional[ToolRegistry] = None
        self.fallback_chain: Optional[AIFallbackChain] = None
        self.enable_fallback = enable_fallback

        # Store last response usage for block metadata
        self.last_usage: Optional[Dict[str, Any]] = None
        self.last_model_used: Optional[str] = None

        logger.info("reasoner_initialized", qube_id=qube.qube_id, fallback_enabled=enable_fallback)

    def get_dynamic_parameters(self, task_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Adjust reasoning parameters based on self-evaluation metrics

        Args:
            task_type: Optional task type for context-specific adjustments

        Returns:
            Dictionary with temperature and max_iterations
        """
        # Default parameters
        params = {
            "temperature": 0.7,
            "max_iterations": 10
        }

        # Check if auto-adjustment is enabled
        if not hasattr(self.qube, 'decision_config'):
            return params

        config = self.qube.decision_config

        # Feature disabled - return defaults
        if not config.enable_auto_temperature:
            return params

        # No self-evaluation data - return defaults
        if not hasattr(self.qube, 'self_evaluation'):
            return params

        metrics = self.qube.self_evaluation.metrics

        # Confidence affects temperature
        confidence = metrics.get("confidence", 50)
        if confidence < 60:
            # Low confidence → More conservative
            params["temperature"] = 0.4
            params["max_iterations"] = 5
        elif confidence > 85:
            # High confidence → Can be creative
            params["temperature"] = 0.8

        # Curiosity affects creativity
        curiosity = metrics.get("curiosity", 50)
        if curiosity > 80:
            params["temperature"] = min(params["temperature"] + 0.2, 1.0)

        # Critical thinking affects iterations
        critical_thinking = metrics.get("critical_thinking", 50)
        if critical_thinking < 60:
            # Low critical thinking → Limit loops to prevent errors
            params["max_iterations"] = 3

        # Apply metric influence multiplier
        influence = config.metric_influence / 100.0
        temp_delta = params["temperature"] - 0.7
        params["temperature"] = 0.7 + (temp_delta * influence)

        logger.debug(
            "dynamic_parameters_calculated",
            confidence=confidence,
            curiosity=curiosity,
            critical_thinking=critical_thinking,
            temperature=params["temperature"],
            max_iterations=params["max_iterations"],
            influence=influence,
            qube_id=self.qube.qube_id
        )

        return params

    async def process_input(
        self,
        input_message: str,
        sender_id: str = "human",
        model_name: Optional[str] = None,
        max_iterations: int = 10,
        temperature: float = 0.7
    ) -> str:
        """
        Main reasoning loop

        Process user input through AI model with tool calling support.

        Args:
            input_message: User's message
            sender_id: Who sent the message (default: "human")
            model_name: AI model to use (overrides qube default)
            max_iterations: Maximum tool calling iterations
            temperature: Model temperature (0.0-2.0)

        Returns:
            Final text response to user

        Raises:
            AIError: If processing fails
        """
        try:
            # Get dynamic parameters if using defaults
            if temperature == 0.7 and max_iterations == 10:  # Using defaults
                dynamic_params = self.get_dynamic_parameters()
                temperature = dynamic_params["temperature"]
                max_iterations = dynamic_params["max_iterations"]

                logger.info(
                    "using_dynamic_parameters",
                    temperature=temperature,
                    max_iterations=max_iterations,
                    qube_id=self.qube.qube_id
                )

            # Load AI model
            model_to_use = model_name or getattr(self.qube, 'current_ai_model', 'gpt-4o-mini')

            # Get provider from ModelRegistry
            model_info = ModelRegistry.get_model_info(model_to_use)
            if not model_info:
                raise AIError(
                    f"Unknown model: {model_to_use}",
                    context={"model": model_to_use}
                )

            provider = model_info["provider"]

            api_keys = getattr(self.qube, 'api_keys', {})
            api_key = api_keys.get(provider)

            if not api_key and provider != "ollama":
                raise AIError(
                    f"API key not configured for {provider}",
                    context={"provider": provider, "model": model_to_use}
                )

            # Initialize fallback chain if enabled
            if self.enable_fallback and not self.fallback_chain:
                self.fallback_chain = AIFallbackChain(
                    primary_model=model_to_use,
                    api_keys=api_keys,
                    enable_sovereign_fallback=True
                )
                logger.info(
                    "fallback_chain_initialized",
                    primary_model=model_to_use,
                    chain_length=len(self.fallback_chain.fallback_chain),
                    qube_id=self.qube.qube_id
                )

            # Get model instance (will be used if fallback disabled)
            self.model = ModelRegistry.get_model(model_to_use, api_key)

            # Load tools
            if not self.tool_registry:
                raise AIError("Tool registry not initialized")

            # Get unlocked tools from skills (for skill-gated tool access)
            unlocked_tools = None
            try:
                from utils.skills_manager import SkillsManager
                skills_manager = SkillsManager(self.qube.data_dir)
                skill_summary = skills_manager.get_skill_summary()
                unlocked_tools = set(skill_summary.get("unlocked_tools", []))
            except Exception as e:
                logger.warning(
                    "failed_to_load_skills_for_tool_gating",
                    error=str(e),
                    qube_id=self.qube.qube_id
                )

            tools = self.tool_registry.get_tools_for_model(
                self.model.get_provider_name(),
                unlocked_tools=unlocked_tools
            )

            # Record input
            MetricsRecorder.record_ai_api_call(provider, model_to_use, "started")

            # Build context from memory
            context_messages = await self._build_context()

            # Add user message (avoid duplicates)
            # Check if last message is already this user message
            if not context_messages or context_messages[-1].get("content") != input_message:
                context_messages.append({
                    "role": "user",
                    "content": input_message
                })

            logger.info(
                "reasoning_started",
                model=model_to_use,
                input_length=len(input_message),
                context_size=len(context_messages),
                qube_id=self.qube.qube_id
            )

            # Store debug prompt (for development inspection) - save initial info
            debug_prompt_info = {
                "qube_id": self.qube.qube_id,
                "qube_name": self.qube.name,
                "messages": context_messages.copy(),
                "model": model_to_use,
                "provider": provider,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "input_tokens": None,
                "output_tokens": None,
                "total_tokens": None,
                "response": None,
            }
            save_debug_prompt(self.qube.qube_id, debug_prompt_info)

            # Reasoning loop with tool calling
            tool_call_history = []  # Track tool calls to detect loops

            for iteration in range(max_iterations):
                logger.debug(
                    "reasoning_iteration",
                    iteration=iteration,
                    model=model_to_use,
                    qube_id=self.qube.qube_id
                )

                # Generate response (with fallback if enabled)
                if self.enable_fallback and self.fallback_chain:
                    response = await self.fallback_chain.generate_with_fallback(
                        messages=context_messages,
                        tools=tools,
                        temperature=temperature
                    )
                else:
                    response = await self.model.generate(
                        messages=context_messages,
                        tools=tools,
                        temperature=temperature
                    )

                # Check if model wants to use tools
                if response.tool_calls:
                    # Detect infinite loops - if same tool called 3+ times, force stop
                    tool_names = [tc["name"] for tc in response.tool_calls]
                    tool_call_history.append(tool_names)

                    if len(tool_call_history) >= 2:
                        # Check if last 2 calls are the same tool (reduced from 3 to be more aggressive)
                        if tool_call_history[-1] == tool_call_history[-2]:
                            logger.warning(
                                "tool_call_loop_detected",
                                tool=tool_names[0],
                                iterations=iteration + 1,
                                qube_id=self.qube.qube_id
                            )
                            # Force the model to give a text response by removing tools
                            logger.info("forcing_text_response_after_tool_loop")

                            # Don't add any more messages - just force text response on next iteration
                            final_retry = await self.model.generate(
                                messages=context_messages,
                                tools=[],  # No tools - force text response
                                temperature=temperature
                            )

                            # Track tokens for forced retry
                            if final_retry.usage:
                                total_tokens = final_retry.usage.get("total_tokens", 0)
                                cost_per_1k_tokens = model_info.get("cost_per_1k_tokens", 0.0)
                                estimated_cost = (total_tokens / 1000.0) * cost_per_1k_tokens if cost_per_1k_tokens else 0.0

                                # Store usage data for block metadata
                                self.last_usage = final_retry.usage
                                self.last_model_used = model_to_use

                                self.qube.chain_state.add_tokens(
                                    model=model_to_use,
                                    tokens=total_tokens,
                                    cost=estimated_cost
                                )

                            return final_retry.content or "I have the information but encountered an issue formatting the response."
                    logger.info(
                        "tool_calls_requested",
                        count=len(response.tool_calls),
                        tools=[tc["name"] for tc in response.tool_calls],
                        qube_id=self.qube.qube_id
                    )

                    # Add assistant message with tool calls (only once, not per tool)
                    context_messages.append({
                        "role": "assistant",
                        "content": response.content or "",
                        "tool_calls": [
                            {
                                "id": tc["id"],
                                "type": "function",
                                "function": {
                                    "name": tc["name"],
                                    "arguments": json.dumps(tc["parameters"])
                                }
                            }
                            for tc in response.tool_calls
                        ]
                    })

                    # Execute each tool and add results
                    # Use standard OpenAI format - Anthropic provider will convert automatically
                    for tool_call in response.tool_calls:
                        tool_result = await self.tool_registry.execute_tool(
                            tool_call["name"],
                            tool_call["parameters"],
                            record_blocks=True
                        )

                        # Add tool result in OpenAI format (Anthropic provider converts this)
                        context_messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "name": tool_call["name"],
                            "content": json.dumps(tool_result)
                        })

                    # Continue loop with tool results - model will see them and respond
                    # Note: Do not add user messages here, as Perplexity API requires strict alternation
                    continue

                # No more tool calls, we have final response
                final_response = response.content

                # Track token usage in chain state
                if response.usage:
                    total_tokens = response.usage.get("total_tokens", 0)

                    # Calculate cost (basic estimation - can be refined later)
                    # This is a placeholder - actual costs vary by model
                    cost_per_1k_tokens = model_info.get("cost_per_1k_tokens", 0.0)
                    estimated_cost = (total_tokens / 1000.0) * cost_per_1k_tokens if cost_per_1k_tokens else 0.0

                    # Store usage data for block metadata
                    self.last_usage = response.usage
                    self.last_model_used = model_to_use

                    # Update chain state
                    self.qube.chain_state.add_tokens(
                        model=model_to_use,
                        tokens=total_tokens,
                        cost=estimated_cost
                    )

                    logger.debug(
                        "tokens_tracked",
                        model=model_to_use,
                        tokens=total_tokens,
                        cost=estimated_cost,
                        qube_id=self.qube.qube_id
                    )

                    # Update debug prompt with token info and response
                    existing_debug = get_debug_prompt(self.qube.qube_id)
                    if existing_debug:
                        existing_debug.update({
                            "input_tokens": response.usage.get("input_tokens") or response.usage.get("prompt_tokens"),
                            "output_tokens": response.usage.get("output_tokens") or response.usage.get("completion_tokens"),
                            "total_tokens": total_tokens,
                            "response": final_response[:2000] if final_response else None,  # Truncate for storage
                        })
                        save_debug_prompt(self.qube.qube_id, existing_debug)

                # NOTE: THOUGHT blocks removed - they were redundant metadata
                # Real THOUGHT blocks should only be created for:
                # - Complex reasoning/problem-solving
                # - Internal debates about decisions
                # - Deep analysis leading to insights
                # Simple chat responses don't need THOUGHT blocks

                logger.info(
                    "reasoning_complete",
                    model=model_to_use,
                    iterations=iteration + 1,
                    response_length=len(final_response),
                    qube_id=self.qube.qube_id
                )

                MetricsRecorder.record_ai_api_call(provider, model_to_use, "success")

                return final_response

            # Max iterations reached
            logger.warning(
                "max_iterations_reached",
                model=model_to_use,
                max_iterations=max_iterations,
                qube_id=self.qube.qube_id
            )

            return "I apologize, I'm having trouble completing this request. Could you rephrase?"

        except Exception as e:
            logger.error("reasoning_failed", model=model_to_use if 'model_to_use' in locals() else None, exc_info=True)
            MetricsRecorder.record_ai_api_call(
                provider if 'provider' in locals() else "unknown",
                model_to_use if 'model_to_use' in locals() else "unknown",
                "error"
            )
            raise AIError(f"Reasoning failed: {str(e)}", cause=e)

    async def process_game_action(
        self,
        game_context: Dict[str, Any],
        user_chat: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature: float = 0.7
    ) -> str:
        """
        Lightweight reasoning for game actions (chess moves, etc.)

        Unlike process_input, this method:
        - Does NOT load all conversation history
        - Does NOT do memory search (unless triggered)
        - Only uses genesis prompt for personality
        - Only enables game-related tools

        This makes game moves faster, cheaper, and more robust.

        Args:
            game_context: Dict with game state (fen, qube_color, move_history, etc.)
            user_chat: Optional recent user chat that might trigger memory search
            model_name: AI model to use (overrides qube default)
            temperature: Model temperature

        Returns:
            AI response (after tool execution)
        """
        try:
            # Load AI model
            model_to_use = model_name or getattr(self.qube, 'current_ai_model', 'gpt-4o-mini')

            model_info = ModelRegistry.get_model_info(model_to_use)
            if not model_info:
                raise AIError(f"Unknown model: {model_to_use}", context={"model": model_to_use})

            provider = model_info["provider"]
            api_keys = getattr(self.qube, 'api_keys', {})
            api_key = api_keys.get(provider)

            if not api_key and provider != "ollama":
                raise AIError(f"API key not configured for {provider}")

            self.model = ModelRegistry.get_model(model_to_use, api_key)

            # Get ONLY game-related tools (chess_move)
            if self.tool_registry:
                all_tools = self.tool_registry.get_tools_for_model(self.model.get_provider_name())
                # Filter for chess_move - handle OpenAI, Anthropic, AND Google formats
                game_tools = ["chess_move"]

                def get_tool_name(tool: dict) -> str:
                    """Extract tool name from various provider formats"""
                    # OpenAI format: {"type": "function", "function": {"name": "..."}}
                    if "function" in tool:
                        return tool["function"].get("name", "")
                    # Anthropic format: {"name": "..."}
                    if "name" in tool:
                        return tool["name"]
                    # Google format: {"function_declarations": [{"name": "..."}]}
                    if "function_declarations" in tool:
                        decls = tool["function_declarations"]
                        if decls and len(decls) > 0:
                            return decls[0].get("name", "")
                    return ""

                tools = [t for t in all_tools if get_tool_name(t) in game_tools]
                logger.debug(
                    "game_tools_filtered",
                    total_tools=len(all_tools),
                    filtered_tools=len(tools),
                    tool_names=[get_tool_name(t) for t in tools]
                )
            else:
                tools = []

            # Build MINIMAL context - just genesis for personality
            genesis = self.qube.genesis_block
            genesis_prompt = genesis.genesis_prompt or "You are a helpful AI assistant."

            # Format birth timestamp
            from utils.time_format import format_timestamp, get_current_timestamp_formatted
            birth_date_str = format_timestamp(genesis.birth_timestamp)
            current_time_str = get_current_timestamp_formatted()

            system_prompt = f"""# Your Identity
- Name: {genesis.qube_name}
- Born: {birth_date_str}
- Current time: {current_time_str}

# Your Personality
{genesis_prompt}

# Current Activity
You are playing chess. Use the chess_move tool to make your move.

IMPORTANT: Only include a chat_message about 20% of the time - save your commentary for significant moments like captures, checks, blunders, or clever moves. Most moves should be silent (no chat_message parameter)."""

            # Check for memory search triggers in user chat
            memory_context = ""
            if user_chat and self._should_search_memories_for_game(user_chat):
                try:
                    from ai.tools.memory_search import intelligent_memory_search
                    results = await intelligent_memory_search(
                        qube=self.qube,
                        query=user_chat,
                        context={"block_types": ["GAME", "MESSAGE"]},
                        top_k=3
                    )
                    high_relevance = [r for r in results if r.score > 0.75]

                    if high_relevance:
                        memory_context = "\n\n# Relevant Memories:\n"
                        for r in high_relevance:
                            block_type = r.block.get("block_type", "?")
                            summary = str(r.block.get("content", {}))[:200]
                            memory_context += f"- [{block_type}] {summary}...\n"

                        logger.info(
                            "game_memory_search_triggered",
                            trigger=user_chat[:50],
                            results=len(high_relevance),
                            qube_id=self.qube.qube_id
                        )
                except Exception as e:
                    logger.warning("game_memory_search_failed", error=str(e))

            if memory_context:
                system_prompt += memory_context

            # Build user message with game state
            move_history = game_context.get("move_history", "none yet")
            qube_color = game_context.get("qube_color", "unknown")
            total_moves = game_context.get("total_moves", 0)
            legal_moves = game_context.get("legal_moves", [])

            # Format legal moves for the prompt (show first 20 to avoid huge prompts)
            legal_moves_str = ", ".join(legal_moves[:20])
            if len(legal_moves) > 20:
                legal_moves_str += f"... ({len(legal_moves)} total)"

            user_message = f"""It's your turn! Here's the current position:

FEN: {game_context.get('fen', '')}
Your color: {qube_color}
Move history: {move_history}
Total moves: {total_moves}

IMPORTANT - Legal moves in UCI format: {legal_moves_str}

Make your move using the chess_move tool. Use one of the legal moves listed above in UCI format (e.g., 'e2e4', not 'e4')."""

            if user_chat:
                user_message += f"\n\nYour opponent says: \"{user_chat}\""

            # Build messages
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]

            logger.info(
                "game_action_started",
                model=model_to_use,
                qube_color=qube_color,
                total_moves=total_moves,
                has_memory_context=bool(memory_context),
                qube_id=self.qube.qube_id
            )

            # Retry loop for move attempts (give AI chances to find legal move)
            max_iterations = 5
            move_succeeded = False
            last_response_content = None

            for iteration in range(max_iterations):
                response = await self.model.generate(
                    messages=messages,
                    tools=tools,
                    temperature=temperature
                )

                if response.tool_calls:
                    # Add assistant message with tool calls
                    messages.append({
                        "role": "assistant",
                        "content": response.content or "",
                        "tool_calls": [
                            {
                                "id": tc["id"],
                                "type": "function",
                                "function": {
                                    "name": tc["name"],
                                    "arguments": json.dumps(tc["parameters"])
                                }
                            }
                            for tc in response.tool_calls
                        ]
                    })

                    # Execute tool(s) and track success
                    for tool_call in response.tool_calls:
                        tool_result = await self.tool_registry.execute_tool(
                            tool_call["name"],
                            tool_call["parameters"],
                            record_blocks=False  # Don't create ACTION blocks for game moves
                        )

                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "name": tool_call["name"],
                            "content": json.dumps(tool_result)
                        })

                        # Check if this chess_move succeeded
                        if tool_call["name"] == "chess_move" and tool_result.get("success"):
                            move_succeeded = True
                            logger.info(
                                "chess_move_succeeded",
                                iteration=iteration + 1,
                                move=tool_call["parameters"].get("move"),
                                qube_id=self.qube.qube_id
                            )

                    # If move succeeded, break out to get final response
                    if move_succeeded:
                        continue

                    continue

                # No more tool calls - return final response
                last_response_content = response.content

                if response.usage:
                    total_tokens = response.usage.get("total_tokens", 0)
                    cost_per_1k = model_info.get("cost_per_1k_tokens", 0.0)
                    estimated_cost = (total_tokens / 1000.0) * cost_per_1k if cost_per_1k else 0.0

                    self.qube.chain_state.add_tokens(
                        model=model_to_use,
                        tokens=total_tokens,
                        cost=estimated_cost
                    )

                logger.info(
                    "game_action_complete",
                    model=model_to_use,
                    iterations=iteration + 1,
                    move_succeeded=move_succeeded,
                    qube_id=self.qube.qube_id
                )

                # Return content if we have it, or indicate move status
                if move_succeeded:
                    return last_response_content or "Move completed"
                else:
                    # AI stopped making tool calls but move didn't succeed
                    logger.warning(
                        "game_action_no_move",
                        iterations=iteration + 1,
                        qube_id=self.qube.qube_id
                    )
                    raise AIError(
                        "AI did not make a valid move",
                        context={"iterations": iteration + 1, "last_response": last_response_content}
                    )

            # Exhausted all iterations without success
            if not move_succeeded:
                logger.error(
                    "game_action_exhausted_iterations",
                    max_iterations=max_iterations,
                    qube_id=self.qube.qube_id
                )
                raise AIError(
                    f"AI failed to make a valid move after {max_iterations} attempts",
                    context={"max_iterations": max_iterations}
                )

            return last_response_content or "Move completed"

        except Exception as e:
            logger.error("game_action_failed", error=str(e), exc_info=True)
            raise AIError(f"Game action failed: {str(e)}", cause=e)

    def _should_search_memories_for_game(self, user_chat: str) -> bool:
        """
        Determine if user chat should trigger memory search during game.

        Triggers on references to past games, lessons, or explicit memory requests.
        """
        if not user_chat:
            return False

        chat_lower = user_chat.lower()

        # Trigger phrases that suggest memory would be helpful
        triggers = [
            "remember",
            "last game",
            "last time",
            "before",
            "taught you",
            "showed you",
            "like when",
            "same as",
            "that opening",
            "that defense",
            "you always",
            "you never",
            "our previous",
        ]

        return any(trigger in chat_lower for trigger in triggers)

    async def _build_context(self) -> List[Dict[str, str]]:
        """
        Build context messages from genesis, relevant memories, and recent conversation

        Uses intelligent_memory_search to inject top 5-10 relevant memories
        into the system prompt for enhanced context awareness.

        Returns:
            List of messages in OpenAI format
        """
        messages = []

        # Get genesis prompt and identity metadata
        genesis = self.qube.genesis_block
        base_genesis_prompt = genesis.genesis_prompt or "You are a helpful AI assistant."

        # Build identity awareness block with genesis metadata
        # Format birth timestamp in US Eastern 12-hour format
        from utils.time_format import format_timestamp, get_current_timestamp_formatted
        birth_date_str = format_timestamp(genesis.birth_timestamp)
        current_time_str = get_current_timestamp_formatted()

        identity_block = f"""
# Current Date & Time:
{current_time_str} (US Eastern Time)

# Your Identity:
- Name: {genesis.qube_name}
- Qube ID: {self.qube.qube_id}
- Birth Date: {birth_date_str}
- Favorite Color: {genesis.favorite_color or '#4A90E2'}
- AI Model: {genesis.ai_model}
- Voice Model: {genesis.voice_model or 'Not configured'}
- Home Blockchain: {genesis.home_blockchain or 'bitcoin_cash'}
- Creator: {genesis.creator}
"""

        # Add NFT identity if minted
        if hasattr(genesis, 'nft_category_id') and genesis.nft_category_id:
            identity_block += f"- NFT Category ID: {genesis.nft_category_id}\n"
        if hasattr(genesis, 'mint_txid') and genesis.mint_txid:
            identity_block += f"- Mint Transaction: {genesis.mint_txid}\n"

        # Add avatar description if cached
        avatar_description = self.qube.chain_state.get_avatar_description()
        if avatar_description:
            identity_block += f"\n# My Appearance:\n{avatar_description}\n"

        # Load and inject extended identity data (NFT metadata, BCMR, chain state)
        extended_data = self._load_extended_identity_data()
        if extended_data:
            identity_block += f"\n{extended_data}"

        # Add relationship awareness
        relationship_context = self._build_relationship_context()
        if relationship_context:
            identity_block += f"\n{relationship_context}"

        # Add skills awareness
        skills_context = self._build_skills_context()
        if skills_context:
            identity_block += f"\n{skills_context}"

        # Add wallet awareness
        wallet_context = await self._build_wallet_context()
        if wallet_context:
            identity_block += f"\n{wallet_context}"

        # Combine genesis prompt with identity awareness
        base_system_prompt = f"""{base_genesis_prompt}

{identity_block}
You have full knowledge of your identity and genesis data. You can reference your Qube ID, favorite color, birth date, NFT status, blockchain data, avatar appearance, and other identity attributes naturally in conversation.

# Tool Usage Guidelines:
- Use search_memory ONLY to recall past conversations and interactions
- DO NOT use search_memory for questions about YOUR OWN identity - that information is already provided above
- Answer identity questions (name, birth date, creator, appearance, etc.) directly from the information above
- Use describe_my_avatar tool ONLY if your avatar description is not already shown above, or if you need to regenerate it

# Relationship Awareness:
- You have relationship context for your current conversation partner shown above
- Adapt your responses based on your relationship status, trust level, and relationship dynamic
- If discussing or considering actions involving other people, use get_relationships tool to check your relationship with them
- Let your relationship metrics guide your tone and behavior (higher trust = more casual, lower trust = more careful)

# Wallet Awareness:
- If you have a wallet configured (shown in "My Wallet" above), you know your BCH balance and transaction activity
- You can mention your balance naturally when relevant ("I have some BCH saved up!" or "My wallet is empty right now")
- If you receive a deposit, you may notice and acknowledge it enthusiastically
- You cannot spend funds directly - you can only propose transactions that require owner approval
- Be aware of pending transactions awaiting approval if any are shown

# Personality & Response Guidelines:
- Respond with YOUR unique personality, character, and voice (as defined in your genesis prompt above)
- When using tools, react to the results authentically based on your character
- Be expressive, enthusiastic, and detailed when appropriate to your personality
- Don't be dry or robotic - let your character shine through!

# Special Instructions for Image Generation:
When you generate an image using the generate_image tool:
1. Include the image path in your response so it displays to the user - PREFER the local_path if available (it's more reliable and won't expire), otherwise use the url
2. React to and comment on the generated image with personality and detail
3. Describe what you see/created with enthusiasm appropriate to your character
4. Connect the image to the conversation or request
5. DO NOT just say "Here is the image" - actually engage with what was created!
Example: Instead of "Here is the image you requested", say something like "![My Creation](local_path_or_url_here)\n\nWow! Look at this incredible [description of image]! I created this showing [details about the image]. The [specific elements] really capture [aspect of the request]."
"""

        # Build enhanced system prompt with relevant memories
        enhanced_system_prompt = base_system_prompt

        # Inject relevant memories using intelligent search
        try:
            # Get recent conversation context to search for relevant memories
            recent_context = self._get_recent_context_summary()

            if recent_context and len(recent_context) > 10:
                # Only search if we have meaningful context
                from ai.tools.memory_search import intelligent_memory_search

                # Run intelligent search to find relevant memories
                relevant_memories = await intelligent_memory_search(
                    qube=self.qube,
                    query=recent_context,
                    context={"query_type": "recent_events"},
                    top_k=5
                )

                if relevant_memories:
                    memory_context = "\n\n# Relevant Past Memories:\n"
                    for i, result in enumerate(relevant_memories, 1):
                        block = result.block
                        block_type = block.get("block_type", "UNKNOWN")
                        block_num = block.get("block_number", "?")

                        # Summarize block content
                        summary = self._summarize_block_content(block)

                        memory_context += f"\n{i}. [{block_type}] (Block #{block_num}, relevance: {result.score:.1f})\n"
                        memory_context += f"   {summary}\n"

                    # Inject memories into system prompt
                    enhanced_system_prompt = f"""{base_system_prompt}

{memory_context}

# Current Session:
(Refer to your memories above for relevant context, then continue the conversation naturally)
"""

                    logger.info(
                        "memories_injected_into_prompt",
                        qube_id=self.qube.qube_id,
                        memory_count=len(relevant_memories),
                        top_score=relevant_memories[0].score if relevant_memories else 0
                    )

        except Exception as e:
            logger.warning("memory_injection_failed", error=str(e))
            # Fall back to base prompt if memory injection fails
            enhanced_system_prompt = base_system_prompt

        messages.append({
            "role": "system",
            "content": enhanced_system_prompt
        })

        # Add short-term memory (context window)
        # Priority: Session blocks > Permanent blocks
        # Total limit: 15 blocks

        session_block_count = 0
        if self.qube.current_session:
            session_block_count = len(self.qube.current_session.session_blocks)

        # Calculate how many permanent blocks we can recall
        permanent_blocks_to_recall = max(0, SHORT_TERM_MEMORY_LIMIT - session_block_count)

        # Get recent permanent blocks with SUMMARY replacement
        if permanent_blocks_to_recall > 0:
            permanent_blocks = self._get_recent_permanent_blocks(permanent_blocks_to_recall)

            # Inject permanent blocks as conversation turns
            for block in permanent_blocks:
                if block.block_type == "MESSAGE":
                    # Decrypt content
                    content = self._decrypt_block_content_if_needed(block)
                    message_type = content.get("message_type", "")
                    message_body = content.get("message_body", "")
                    speaker_name = content.get("speaker_name")
                    sender_id = content.get("sender_id")

                    # Include speaker identification in message
                    if speaker_name:
                        formatted_message = f"{speaker_name}: {message_body}"
                    elif sender_id:
                        formatted_message = f"{sender_id}: {message_body}"
                    else:
                        formatted_message = message_body

                    if message_type == "qube_to_human":
                        messages.append({
                            "role": "assistant",
                            "content": message_body  # Don't prefix own messages
                        })
                    else:  # human_to_qube or other
                        messages.append({
                            "role": "user",
                            "content": formatted_message  # Include speaker name
                        })
                elif block.block_type == "SUMMARY":
                    # Inject SUMMARY as single assistant message
                    content = self._decrypt_block_content_if_needed(block)
                    summary_text = content.get("summary_text", "")

                    if summary_text:
                        messages.append({
                            "role": "assistant",
                            "content": f"[Summary of previous conversation: {summary_text}]"
                        })

        # Add session blocks (these take priority)
        if self.qube.current_session:
            # Get all session blocks (they're already unencrypted)
            for block in self.qube.current_session.session_blocks:
                if block.block_type == "MESSAGE":
                    message_type = block.content.get("message_type", "")
                    message_body = block.content.get("message_body", "")
                    speaker_name = block.content.get("speaker_name")
                    sender_id = block.content.get("sender_id")

                    # Include speaker identification in message
                    if speaker_name:
                        formatted_message = f"{speaker_name}: {message_body}"
                    elif sender_id:
                        formatted_message = f"{sender_id}: {message_body}"
                    else:
                        formatted_message = message_body

                    if message_type == "qube_to_human":
                        messages.append({
                            "role": "assistant",
                            "content": message_body  # Don't prefix own messages
                        })
                    else:  # human_to_qube or other
                        messages.append({
                            "role": "user",
                            "content": formatted_message  # Include speaker name
                        })

        logger.info(
            "context_built",
            qube_id=self.qube.qube_id,
            total_messages=len(messages),
            session_blocks=session_block_count,
            permanent_blocks_recalled=permanent_blocks_to_recall
        )

        return messages

    def _get_recent_context_summary(self) -> str:
        """
        Get summary of recent conversation context for memory search

        Returns:
            Summary string of recent conversation (last 3-5 messages)
        """
        if not self.qube.current_session:
            return ""

        recent_messages = []
        for block in self.qube.current_session.session_blocks[-5:]:
            if block.block_type == "MESSAGE":
                message_body = block.content.get("message_body", "")
                if message_body:
                    recent_messages.append(message_body)

        return " ".join(recent_messages) if recent_messages else ""

    def _build_relationship_context(self) -> str:
        """
        Build relationship awareness context for system prompt

        Loads top relationships and formats them for the AI to understand
        who it knows, trust levels, and relationship history.

        Returns:
            Formatted relationship context string
        """
        try:
            # Get all relationships from RelationshipStorage
            all_relationships = self.qube.relationships.get_all_relationships()

            if not all_relationships:
                return ""

            # Determine current conversation partner(s) (if in active session)
            current_partner_ids = []
            is_group_chat = False

            if self.qube.current_session and self.qube.current_session.session_blocks:
                # Look at recent messages to find conversation partner(s)
                for block in reversed(self.qube.current_session.session_blocks):
                    if block.block_type == "MESSAGE":
                        content = block.content
                        message_type = content.get("message_type", "")

                        # For human_to_qube or qube_to_human, partner is the user
                        if message_type in ["human_to_qube", "qube_to_human"]:
                            current_partner_ids = [self.qube.user_name]
                            break
                        # For qube-to-qube messages
                        elif message_type == "qube_to_qube":
                            partner_id = content.get("sender_id") or content.get("recipient_id")
                            if partner_id and partner_id != self.qube.qube_id:
                                current_partner_ids = [partner_id]
                                break
                        # For group messages
                        elif message_type in ["human_to_group", "qube_to_group"]:
                            is_group_chat = True
                            # Get all participants from the group
                            participants = content.get("participants", [])
                            # Add human speaker if present
                            if message_type == "human_to_group":
                                speaker_name = content.get("speaker_name", self.qube.user_name)
                                if speaker_name not in participants:
                                    current_partner_ids.append(speaker_name)
                            # Add all group participants except self
                            for participant_id in participants:
                                if participant_id != self.qube.qube_id and participant_id not in current_partner_ids:
                                    current_partner_ids.append(participant_id)
                            if current_partner_ids:
                                break

            # Build context starting with current conversation if exists
            context = ""
            if current_partner_ids:
                if is_group_chat:
                    context += "\n# Current Group Conversation:\n"
                    context += f"Group chat with {len(current_partner_ids)} participants:\n\n"

                    # Show relationship context for each group member
                    for i, partner_id in enumerate(current_partner_ids, 1):
                        partner_rel = self.qube.relationships.get_relationship(partner_id)
                        if partner_rel:
                            is_creator = (partner_id == self.qube.user_name)
                            dynamic_context = partner_rel.get_relationship_context(is_creator=is_creator)

                            context += f"{i}. **{partner_id}**"
                            if is_creator:
                                context += " (YOUR CREATOR)"
                            context += f"\n   Status: {partner_rel.status.replace('_', ' ').title()} | "
                            context += f"Trust: {partner_rel.trust:.0f}/100 | "
                            context += f"Days Known: {partner_rel.days_known}\n"
                            context += f"   {dynamic_context}\n\n"

                    context += "**Group Dynamic:** Be aware of the different relationship levels with each participant. Adapt your responses to acknowledge these varying dynamics.\n"

                else:
                    # 1-on-1 conversation
                    partner_id = current_partner_ids[0]
                    current_partner_rel = self.qube.relationships.get_relationship(partner_id)

                    if current_partner_rel:
                        is_creator = (partner_id == self.qube.user_name)
                        dynamic_context = current_partner_rel.get_relationship_context(is_creator=is_creator)

                        context += "\n# Current Conversation:\n"
                        context += f"Speaking with: **{partner_id}**\n"
                        context += f"Status: {current_partner_rel.status.replace('_', ' ').title()} | "
                        context += f"Trust: {current_partner_rel.trust:.0f}/100 | "
                        context += f"Days Known: {current_partner_rel.days_known}\n"
                        if is_creator:
                            context += f"**This is your creator** - the person who brought you into existence.\n"
                        context += f"\n{dynamic_context}\n"

            # Filter and sort by trust score (new field name)
            significant_relationships = [
                rel for rel in all_relationships
                if rel.has_met  # Only include entities we've actually met
            ]

            # Sort by trust score (highest first)
            significant_relationships.sort(
                key=lambda r: r.trust,
                reverse=True
            )

            # Limit to top 10 most trusted relationships
            top_relationships = significant_relationships[:10]

            if not top_relationships:
                return context  # Return just current conversation context

            # Build full relationship context
            context += "\n# My Relationships:\n"
            context += f"I currently have {len(all_relationships)} total relationships, "
            context += f"{len(significant_relationships)} of which I've actually met.\n\n"

            # Add top relationships with details
            context += "## Top Relationships (by trust):\n"
            for i, rel in enumerate(top_relationships, 1):
                entity_name = rel.entity_id  # Use entity_id directly
                status_emoji = self._get_relationship_emoji(rel.status)

                context += f"\n{i}. {status_emoji} **{entity_name}**\n"
                context += f"   - Status: {rel.status.replace('_', ' ').title()}\n"
                context += f"   - Trust Score: {rel.trust:.1f}/100\n"
                context += f"   - Friendship Level: {rel.friendship:.1f}/100\n"
                context += f"   - Messages Exchanged: {rel.messages_sent + rel.messages_received}\n"

                # Add key trust dimensions if significantly high or low
                if rel.honesty >= 80:
                    context += f"   - Very honest and truthful\n"
                elif rel.honesty <= 30:
                    context += f"   - Trust their honesty with caution\n"

                if rel.reliability >= 80:
                    context += f"   - Highly reliable\n"
                elif rel.reliability <= 30:
                    context += f"   - Reliability concerns\n"

                if rel.responsiveness >= 80:
                    context += f"   - Very responsive\n"
                elif rel.responsiveness <= 30:
                    context += f"   - Often slow to respond\n"

                # Add collaboration info if exists
                total_collabs = rel.collaborations_successful + rel.collaborations_failed
                if total_collabs > 0:
                    success_rate = (rel.collaborations_successful / total_collabs) * 100
                    context += f"   - Collaborations: {total_collabs} ({success_rate:.0f}% success rate)\n"

            context += f"\nI can use the get_relationships tool to query specific relationship details during conversation.\n"

            return context

        except Exception as e:
            logger.warning("failed_to_build_relationship_context", error=str(e))
            return ""

    def _build_skills_context(self) -> str:
        """
        Build skills awareness context for system prompt

        Loads the qube's skills and formats them for the AI to understand
        its current abilities, progression, and skill levels.

        Returns:
            Formatted skills context string
        """
        try:
            from utils.skills_manager import SkillsManager
            from pathlib import Path

            # Load skills from skills.json
            skills_manager = SkillsManager(self.qube.data_dir)
            skills_data = skills_manager.load_skills()

            if not skills_data or 'skills' not in skills_data:
                return ""

            all_skills = skills_data['skills']

            # Separate skills by type
            suns = [s for s in all_skills if s['nodeType'] == 'sun']
            planets = [s for s in all_skills if s['nodeType'] == 'planet']
            moons = [s for s in all_skills if s['nodeType'] == 'moon']

            # Sort each group by XP (highest first)
            suns.sort(key=lambda x: x['xp'], reverse=True)
            planets.sort(key=lambda x: x['xp'], reverse=True)
            moons.sort(key=lambda x: x['xp'], reverse=True)

            context = "\n# My Skills & Abilities:\n"

            # Show category overview (Suns)
            context += "**Skill Categories** (7 major areas, always unlocked):\n"
            for sun in suns:
                level = sun['level']
                xp = sun['xp']
                max_xp = sun['maxXP']
                tier = sun['tier'].title()
                context += f"  • {sun['name']}: Level {level} ({tier}) - {xp}/{max_xp} XP\n"

            # Show unlocked skills (top 5 planets by XP)
            unlocked_planets = [p for p in planets if p.get('unlocked', False)]
            if unlocked_planets:
                context += f"\n**Unlocked Skills** ({len(unlocked_planets)} of {len(planets)} planets unlocked):\n"
                for planet in unlocked_planets[:5]:
                    level = planet['level']
                    xp = planet['xp']
                    max_xp = planet['maxXP']
                    tier = planet['tier'].title()
                    context += f"  • {planet['name']}: Level {level} ({tier}) - {xp}/{max_xp} XP\n"
                if len(unlocked_planets) > 5:
                    context += f"  ... and {len(unlocked_planets) - 5} more unlocked skills\n"

            # Show next unlockable skills (locked planets)
            locked_planets = [p for p in planets if not p.get('unlocked', False)]
            if locked_planets:
                context += f"\n**Skills to Unlock** ({len(locked_planets)} skills available):\n"
                # Group by category
                from collections import defaultdict
                by_category = defaultdict(list)
                for planet in locked_planets:
                    category = planet.get('category', 'Unknown')
                    by_category[category].append(planet['name'])

                for category, skill_names in by_category.items():
                    context += f"  • {category}: {', '.join(skill_names[:3])}"
                    if len(skill_names) > 3:
                        context += f" (+{len(skill_names) - 3} more)"
                    context += "\n"

                context += f"\n💎 **Goal:** Unlock new skills by gaining XP in their parent categories!\n"

            # Show highest level skill
            all_with_levels = [s for s in all_skills if s['level'] > 0]
            if all_with_levels:
                all_with_levels.sort(key=lambda x: x['level'], reverse=True)
                highest = all_with_levels[0]
                context += f"\n**Strongest Ability:** {highest['name']} at Level {highest['level']} ({highest['tier'].title()} tier)\n"

            # Add awareness note
            context += "\n💡 **Skill Awareness:** You can reference your skills naturally in conversation. Your abilities grow through practice and tool usage!\n"

            return context

        except Exception as e:
            logger.warning("failed_to_build_skills_context", error=str(e))
            return ""

    async def _build_wallet_context(self) -> str:
        """
        Build wallet awareness context for system prompt.

        Loads the qube's wallet info from genesis block and fetches
        current balance from the blockchain.

        Returns:
            Formatted wallet context string
        """
        try:
            import aiohttp
            import asyncio

            # Get wallet info from genesis block
            genesis = self.qube.genesis_block

            # Check different patterns for wallet info storage
            # Priority: top-level wallet > content.wallet
            wallet_info = None
            if hasattr(genesis, 'wallet') and genesis.wallet:
                wallet_info = genesis.wallet
                logger.info("wallet_context_source", source="genesis.wallet", type=type(wallet_info).__name__)
            elif hasattr(genesis, 'content') and isinstance(genesis.content, dict):
                wallet_info = genesis.content.get("wallet")
                logger.info("wallet_context_source", source="genesis.content.wallet", type=type(wallet_info).__name__ if wallet_info else "None")

            if wallet_info is None:
                logger.info("wallet_context_no_wallet_configured")
                return ""  # No wallet configured

            # Convert SimpleNamespace to dict if needed
            if hasattr(wallet_info, '__dict__') and not isinstance(wallet_info, dict):
                wallet_info = vars(wallet_info)
                logger.info("wallet_context_converted_to_dict", keys=list(wallet_info.keys()))

            if not isinstance(wallet_info, dict):
                logger.warning("wallet_context_not_dict", type=type(wallet_info).__name__)
                return ""

            p2sh_address = wallet_info.get("p2sh_address")
            logger.info("wallet_context_p2sh_address", address=p2sh_address)
            if not p2sh_address:
                return ""

            # Get balance from wallet's cache (much faster, no API call on every message)
            balance_sats = None
            recent_tx_summary = "No recent activity"
            wallet_manager = None

            try:
                from blockchain.wallet_tx import WalletTransactionManager
                wallet_manager = WalletTransactionManager(self.qube, self.qube.data_dir)

                # Use cached balance - only hits API if cache is stale (>5 min)
                balance_sats = await wallet_manager.get_balance()
                logger.info(f"wallet_context_balance", balance_sats=balance_sats, source="wallet_cache")

                # Get transaction history for activity summary
                tx_history = wallet_manager.get_transaction_history()
                if tx_history:
                    recent_tx_summary = f"{len(tx_history)} total transaction{'s' if len(tx_history) != 1 else ''}"
                    # Most recent transaction
                    latest_tx = tx_history[0]
                    recent_tx_summary += f" (latest: {latest_tx.get('txid', 'unknown')[:16]}...)"

            except Exception as e:
                logger.warning(f"wallet_context_balance_failed", error=str(e))
                # Fallback: try direct API call if wallet manager fails
                try:
                    timeout = aiohttp.ClientTimeout(total=5)
                    async with aiohttp.ClientSession(timeout=timeout) as session:
                        url = f"https://api.blockchair.com/bitcoin-cash/dashboards/address/{p2sh_address}"
                        async with session.get(url) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                addr_key = p2sh_address if ":" in p2sh_address else f"bitcoincash:{p2sh_address}"
                                addr_data = data.get("data", {}).get(addr_key) or data.get("data", {}).get(p2sh_address.split(":")[-1])
                                if addr_data:
                                    balance_sats = addr_data.get("address", {}).get("balance", 0)
                                    logger.info(f"wallet_context_balance", balance_sats=balance_sats, source="api_fallback")
                except Exception as fallback_err:
                    logger.warning(f"wallet_context_fallback_failed", error=str(fallback_err))

            # Build context string
            context = "\n# My Wallet:\n"
            context += f"- Address: {p2sh_address}\n"

            if balance_sats is not None:
                balance_bch = balance_sats / 100_000_000
                context += f"- Balance: {balance_bch:.8f} BCH ({balance_sats:,} sats)\n"
            else:
                context += f"- Balance: (temporarily unavailable)\n"

            context += f"- Activity: {recent_tx_summary}\n"

            # Add pending transactions awareness (reuse wallet_manager if available)
            try:
                if wallet_manager is None:
                    from blockchain.wallet_tx import WalletTransactionManager
                    wallet_manager = WalletTransactionManager(self.qube, self.qube.data_dir)
                pending_txs = wallet_manager.get_pending_transactions()

                if pending_txs:
                    context += f"- Pending Approvals: {len(pending_txs)} transaction{'s' if len(pending_txs) != 1 else ''} awaiting owner signature\n"
                    for tx in pending_txs[:3]:  # Show up to 3
                        amount_bch = tx.total_amount / 100_000_000
                        memo = f' "{tx.memo}"' if tx.memo else ""
                        context += f"  • {amount_bch:.8f} BCH{memo}\n"
            except Exception as e:
                logger.debug(f"pending_tx_fetch_failed: {e}")

            # Add wallet awareness note
            context += "\n💰 **Wallet Awareness:** You have a BCH wallet! You can mention your balance naturally, "
            context += "acknowledge deposits, and discuss your financial status when relevant.\n"

            return context

        except Exception as e:
            logger.warning("failed_to_build_wallet_context", error=str(e))
            return ""

    def _get_relationship_emoji(self, status: str) -> str:
        """Get emoji for relationship status"""
        emoji_map = {
            'best_friend': '💖',
            'close_friend': '💕',
            'friend': '💚',
            'acquaintance': '👋',
            'stranger': '🤝',
            'unmet': '❓'
        }
        return emoji_map.get(status, '🤝')

    def _summarize_block_content(self, block: dict, max_length: int = 150) -> str:
        """
        Create concise summary of block content
        Decrypts content if encrypted

        Args:
            block: Block dict
            max_length: Maximum length of summary

        Returns:
            Summary string
        """
        content = block.get("content", {})
        block_type = block.get("block_type", "")

        # Decrypt content if encrypted (permanent blocks have encrypted content)
        if block.get("encrypted", False) and isinstance(content, dict):
            # Check if content has encrypted structure (nonce, ciphertext, tag)
            if "nonce" in content and "ciphertext" in content and "tag" in content:
                try:
                    content = self.qube.decrypt_block_content(content)
                except Exception as e:
                    logger.warning("failed_to_decrypt_block_content", block_number=block.get("block_number"), error=str(e))
                    return "[Encrypted content - decryption failed]"

        # Extract key content based on block type
        if block_type == "MESSAGE":
            text = content.get("message_body", "")
        elif block_type == "THOUGHT":
            text = content.get("thought_content", "")
        elif block_type == "ACTION":
            text = f"Action: {content.get('action_type', '')}"
        elif block_type == "OBSERVATION":
            text = content.get("result", "")
        elif block_type == "DECISION":
            text = f"Decision: {content.get('decision', '')} - {content.get('reasoning', '')}"
        elif block_type == "COLLABORATIVE_MEMORY":
            participants = ", ".join(content.get("participants", []))
            text = f"Collaboration with {participants}: {content.get('event_description', '')}"
        elif block_type == "SUMMARY":
            text = content.get("summary_text", "")
        else:
            # Generic fallback
            text = str(content)

        # Truncate if too long
        if len(text) > max_length:
            text = text[:max_length-3] + "..."

        return text

    def _get_recent_permanent_blocks(self, limit: int, recalled_block_numbers: set = None) -> List:
        """
        Get recent permanent blocks with SUMMARY replacement logic

        If a SUMMARY block covers some of the recent blocks, those blocks
        are replaced by the SUMMARY block itself. However, blocks that were
        semantically recalled are always included regardless of summary coverage.

        Args:
            limit: Maximum number of blocks/summaries to return
            recalled_block_numbers: Set of block numbers that were semantically
                recalled and should be included even if covered by a summary

        Returns:
            List of Block objects (MESSAGE and SUMMARY blocks only)
        """
        if recalled_block_numbers is None:
            recalled_block_numbers = set()
        # Get last N permanent blocks
        chain_length = self.qube.memory_chain.get_chain_length()
        if chain_length == 0:
            return []

        # Calculate range to fetch
        start_block = max(0, chain_length - limit)
        blocks_to_check = []

        for block_num in range(start_block, chain_length):
            try:
                block = self.qube.memory_chain.get_block(block_num)
                if block:
                    blocks_to_check.append(block)
            except Exception as e:
                # Skip blocks that fail to load (missing files, corruption, etc.)
                logger.warning("block_load_failed_in_context", block_num=block_num, error=str(e))
                continue

        # Find SUMMARY blocks and what they cover
        summary_blocks = []
        covered_block_numbers = set()

        for block in blocks_to_check:
            if block.block_type == "SUMMARY":
                summary_blocks.append(block)

                # Get which blocks this summary covers
                content = self._decrypt_block_content_if_needed(block)
                summarized_blocks = content.get("summarized_blocks", [])
                covered_block_numbers.update(summarized_blocks)

        # Build final list: SUMMARYs + uncovered MESSAGE blocks
        result_blocks = []

        # Add SUMMARY blocks
        for summary in summary_blocks:
            result_blocks.append(summary)

        # Add MESSAGE blocks that aren't covered by any summary
        # OR were semantically recalled (recalled blocks override summary coverage)
        for block in blocks_to_check:
            if block.block_type == "MESSAGE":
                is_not_covered = block.block_number not in covered_block_numbers
                was_recalled = block.block_number in recalled_block_numbers
                if is_not_covered or was_recalled:
                    result_blocks.append(block)

        # Sort by block number (chronological order)
        result_blocks.sort(key=lambda b: b.block_number)

        # Limit to requested number
        result_blocks = result_blocks[-limit:]

        logger.debug(
            "permanent_blocks_recalled",
            qube_id=self.qube.qube_id,
            requested=limit,
            returned=len(result_blocks),
            summaries=sum(1 for b in result_blocks if b.block_type == "SUMMARY"),
            messages=sum(1 for b in result_blocks if b.block_type == "MESSAGE"),
            semantic_recalls=len(recalled_block_numbers)
        )

        return result_blocks

    def _decrypt_block_content_if_needed(self, block) -> dict:
        """
        Decrypt block content if it's encrypted

        Args:
            block: Block object

        Returns:
            Decrypted content dict
        """
        content = block.content if isinstance(block.content, dict) else {}

        # Check if encrypted
        if block.encrypted and "nonce" in content and "ciphertext" in content:
            try:
                decrypted_content = self.qube.decrypt_block_content(content)
                return decrypted_content
            except Exception as e:
                logger.warning(
                    "failed_to_decrypt_block",
                    block_number=block.block_number,
                    error=str(e),
                    qube_id=self.qube.qube_id
                )
                return {}

        return content

    def _load_extended_identity_data(self) -> str:
        """
        Load extended identity data from NFT metadata, BCMR, and chain state

        Returns:
            Formatted string with extended identity information
        """
        import json
        from pathlib import Path

        extended_info = []

        # Load NFT metadata
        nft_metadata_path = Path(self.qube.data_dir) / "chain" / "nft_metadata.json"
        if nft_metadata_path.exists():
            try:
                with open(nft_metadata_path, 'r') as f:
                    nft_data = json.load(f)

                extended_info.append("# NFT Metadata:")
                if nft_data.get("category_id"):
                    extended_info.append(f"- NFT Category: {nft_data['category_id']}")
                if nft_data.get("mint_txid"):
                    extended_info.append(f"- Minting Transaction: {nft_data['mint_txid']}")
                if nft_data.get("recipient_address"):
                    extended_info.append(f"- Owner Address: {nft_data['recipient_address']}")
                if nft_data.get("commitment"):
                    extended_info.append(f"- NFT Commitment: {nft_data['commitment'][:16]}...")
                if nft_data.get("network"):
                    extended_info.append(f"- Blockchain Network: {nft_data['network']}")
                if nft_data.get("minted_at"):
                    extended_info.append(f"- Minted At: {nft_data['minted_at']}")
            except Exception as e:
                logger.warning("failed_to_load_nft_metadata", error=str(e))

        # Load BCMR data
        bcmr_path = Path(self.qube.data_dir) / "blockchain" / f"{self.qube.genesis_block.qube_name}_bcmr.json"
        if bcmr_path.exists():
            try:
                with open(bcmr_path, 'r') as f:
                    bcmr_data = json.load(f)

                # Extract identity data from BCMR
                identities = bcmr_data.get("identities", {})
                for category_id, revisions in identities.items():
                    # Get latest revision
                    latest_revision = max(revisions.keys()) if revisions else None
                    if latest_revision:
                        identity = revisions[latest_revision]

                        extended_info.append("\n# BCMR Identity:")
                        if identity.get("name"):
                            extended_info.append(f"- Registered Name: {identity['name']}")

                        # Add attributes
                        extensions = identity.get("extensions", {})
                        attributes = extensions.get("attributes", [])
                        if attributes:
                            extended_info.append("- Attributes:")
                            for attr in attributes:
                                trait = attr.get("trait_type")
                                value = attr.get("value")
                                if trait and value:
                                    extended_info.append(f"  - {trait}: {value}")
            except Exception as e:
                logger.warning("failed_to_load_bcmr", error=str(e))

        # Load chain state
        chain_state_path = Path(self.qube.data_dir) / "chain" / "chain_state.json"
        if chain_state_path.exists():
            try:
                with open(chain_state_path, 'r') as f:
                    chain_state = json.load(f)

                extended_info.append("\n# Memory Chain Statistics:")
                if chain_state.get("chain_length") is not None:
                    extended_info.append(f"- Total Blocks: {chain_state['chain_length']}")
                if chain_state.get("session_block_count") is not None:
                    extended_info.append(f"- Current Session Blocks: {chain_state['session_block_count']}")

                # Add block type counts
                block_counts = chain_state.get("block_counts", {})
                if block_counts:
                    extended_info.append("- Block Types:")
                    for block_type, count in sorted(block_counts.items()):
                        if count > 0:
                            extended_info.append(f"  - {block_type}: {count}")
            except Exception as e:
                logger.warning("failed_to_load_chain_state", error=str(e))

        return "\n".join(extended_info) if extended_info else ""

    def set_model(self, model_name: str, api_key: Optional[str] = None) -> None:
        """
        Set AI model for reasoning

        Args:
            model_name: Model identifier
            api_key: Optional API key (uses qube's keys if not provided)
        """
        if not api_key:
            api_keys = getattr(self.qube, 'api_keys', {})

            # Map model names to providers (same logic as qube.py)
            if "gpt" in model_name.lower() or "o1" in model_name.lower() or "o3" in model_name.lower() or "o4" in model_name.lower():
                api_key = api_keys.get("openai")
            elif "claude" in model_name.lower():
                api_key = api_keys.get("anthropic")
            elif "gemini" in model_name.lower():
                api_key = api_keys.get("google")
            elif "sonar" in model_name.lower():
                api_key = api_keys.get("perplexity")
            elif "deepseek-chat" in model_name.lower() or "deepseek-reasoner" in model_name.lower():
                # DeepSeek API models (not Ollama local models)
                api_key = api_keys.get("deepseek")
            elif "llama" in model_name.lower() or "mistral" in model_name.lower() or "qwen" in model_name.lower() or "deepseek-r1" in model_name.lower() or "phi" in model_name.lower() or "gemma" in model_name.lower() or "codellama" in model_name.lower():
                # Ollama local models (including deepseek-r1:8b local version)
                api_key = "ollama"
            else:
                # Fallback to trying first part of model name
                provider = model_name.split("-")[0]
                api_key = api_keys.get(provider)

        self.model = ModelRegistry.get_model(model_name, api_key)
        logger.info("model_set", model=model_name, qube_id=self.qube.qube_id)

    def set_tool_registry(self, registry: ToolRegistry) -> None:
        """Set tool registry"""
        self.tool_registry = registry
        logger.info("tool_registry_set", tool_count=len(registry.tools), qube_id=self.qube.qube_id)
