"""
Tool Registry and Definition

Manages available tools for AI agents with multi-provider format conversion.
Matches documentation in docs/09_AI_Integration_Tool_Calling.md Section 6.2
"""

from typing import Dict, Any, Callable, List, Optional, Awaitable, Set, Tuple
from dataclasses import dataclass, field
import time
import json
import hashlib
from core.block import create_action_block, BlockType
from core.exceptions import AIError
from utils.logging import get_logger
from monitoring.metrics import MetricsRecorder

logger = get_logger(__name__)

# Sidecar tool event callback — set by sidecar_server.py for JSONL streaming
# When set, tool events route through the sidecar's stdout instead of stderr
_tool_event_callback = None

def set_tool_event_callback(callback):
    """Set a callback for tool events (used by sidecar server)."""
    global _tool_event_callback
    _tool_event_callback = callback

# Dynamic tool selection for small models
# Maps keywords/phrases in user messages to relevant tools
# Small models see only tools matching their request (max ~10 tools)
KEYWORD_TO_TOOLS: Dict[str, List[str]] = {
    # System/status queries
    "scan": ["get_system_state"],
    "system": ["get_system_state"],
    "status": ["get_system_state"],
    "state": ["get_system_state"],
    "about yourself": ["get_system_state"],
    "tell me about you": ["get_system_state"],

    # Mirror/avatar queries
    "mirror": ["describe_my_avatar"],
    "look like": ["describe_my_avatar"],
    "appearance": ["describe_my_avatar"],
    "avatar": ["describe_my_avatar"],
    "see yourself": ["describe_my_avatar"],

    # Model switching
    "switch": ["switch_model"],
    "change model": ["switch_model"],
    "use model": ["switch_model"],

    # Web search
    "search": ["web_search"],
    "look up": ["web_search"],
    "find information": ["web_search"],
    "google": ["web_search"],

    # Memory operations
    "remember": ["store_knowledge", "recall_similar"],
    "recall": ["recall_similar"],
    "memory": ["recall_similar", "store_knowledge"],
    "forget": ["store_knowledge"],

    # Mistake analysis
    "mistake": ["analyze_mistake"],
    "went wrong": ["analyze_mistake"],
    "failed": ["analyze_mistake"],
    "error": ["analyze_mistake", "debug_code"],
    "failure": ["analyze_mistake"],

    # Finance
    "send": ["send_bch"],
    "transfer": ["send_bch"],
    "bch": ["send_bch"],
    "crypto": ["send_bch"],
    "wallet": ["get_system_state", "send_bch"],

    # Image generation
    "image": ["generate_image"],
    "picture": ["generate_image"],
    "draw": ["generate_image"],
    "create art": ["generate_image"],

    # Coding
    "code": ["develop_code", "debug_code", "review_code"],
    "debug": ["debug_code"],
    "test": ["run_tests"],
    "review": ["review_code"],

    # Games
    "chess": ["chess_move", "play_game"],
    "game": ["play_game"],
    "play": ["play_game"],

    # Relationships
    "relationship": ["get_relationship_context", "recall_relationship_history"],
    "emotion": ["read_emotional_state"],
    "feeling": ["read_emotional_state"],

    # Security
    "security": ["security_scan", "verify_chain_integrity"],
    "verify": ["verify_chain_integrity"],
    "trust": ["assess_trust_level"],
}

# Tools that are ALWAYS included for small models (core functionality)
SMALL_MODEL_CORE_TOOLS: Set[str] = {
    "get_system_state",      # Always useful for context
    "switch_model",          # Can always switch models
    "store_knowledge",       # Can always remember things
}

# Core tools that are always available regardless of skill level
# These are essential for basic qube functionality (17 tools)
# Planet and moon tools must be unlocked through XP progression
ALWAYS_AVAILABLE_TOOLS: Set[str] = {
    # Utility tools (no XP)
    "get_system_state",      # Read all state: relationships, skills, owner_info, mood, wallet, etc.
    "update_system_state",   # Write state: owner_info, mood, skills, settings
    "get_skill_tree",        # View all possible skills and progress

    # Sun tools (always available, earn XP for their category)
    "recall_similar",            # AI Reasoning Sun
    "get_relationship_context",  # Social Intelligence Sun
    "verify_chain_integrity",    # Security & Privacy Sun
    "switch_model",              # Creative Expression Sun
    "send_bch",                  # Finance Sun
    "play_game",                 # Board Games Sun
    "store_knowledge",           # Memory & Recall Sun
    "develop_code",              # Coding Sun

    # Intelligent routing tools (XP based on content)
    "web_search",
    "browse_url",
    "generate_image",

    # Standalone tools (no skill node, always available)
    "describe_my_avatar",        # Look in the mirror - see own appearance
    "recall",                    # Universal memory recall - search all storage systems
    "process_document",          # Document processing (automatic, tracked for XP)
}


@dataclass
class ToolDefinition:
    """
    Tool definition with multi-provider format support

    Attributes:
        name: Tool identifier (e.g., "web_search")
        description: Human-readable description
        parameters: JSON schema for parameters
        handler: Async function to execute tool
    """
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Callable[[Dict[str, Any]], Awaitable[Any]]

    def to_openai_format(self) -> Dict[str, Any]:
        """Convert to OpenAI tool format"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }

    def to_anthropic_format(self) -> Dict[str, Any]:
        """Convert to Anthropic tool format"""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.parameters
        }

    def to_google_format(self) -> Dict[str, Any]:
        """Convert to Google (Gemini) tool format"""
        def convert_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
            """Convert JSON Schema to Gemini Schema format"""
            converted = {}

            # Convert type field
            if "type" in schema:
                type_map = {
                    "object": "OBJECT",
                    "string": "STRING",
                    "integer": "INTEGER",
                    "number": "NUMBER",
                    "boolean": "BOOLEAN",
                    "array": "ARRAY"
                }
                converted["type_"] = type_map.get(schema["type"], "STRING")

            # Convert properties recursively
            if "properties" in schema:
                converted["properties"] = {
                    k: convert_schema(v) for k, v in schema["properties"].items()
                }

            # Copy other fields (Gemini doesn't support 'default')
            for key in ["description", "required", "items"]:
                if key in schema:
                    if key == "items":
                        converted["items"] = convert_schema(schema["items"])
                    else:
                        converted[key] = schema[key]

            return converted

        return {
            "function_declarations": [{
                "name": self.name,
                "description": self.description,
                "parameters": convert_schema(self.parameters)
            }]
        }


class ToolRegistry:
    """
    Registry of tools available to Qube

    Manages tool registration, execution, and format conversion
    for different AI providers.
    """

    def __init__(self, qube):
        """
        Initialize tool registry

        Args:
            qube: Qube instance that owns these tools
        """
        self.qube = qube
        self.tools: Dict[str, ToolDefinition] = {}

        # Tool call cache to prevent redundant calls
        # Key: hash of (tool_name, parameters), Value: (result, timestamp)
        self._tool_cache: Dict[str, Tuple[Any, float]] = {}
        self._cache_ttl_seconds = 300  # Cache results for 5 minutes
        # Tools that should NOT be cached (stateful or time-sensitive)
        self._uncacheable_tools: Set[str] = {
            "generate_image",  # Always generates new images
            "add_memory",  # Creates new memory
            "store_knowledge",  # Creates new knowledge
            "send_message",  # Sends new messages
            "switch_model",  # Changes state
            "send_bch",  # Transactions
            "claim_nft",  # Transactions
            "update_owner_info",  # Updates state
            "update_qube_profile",  # Updates state
        }

        # Cache loading disabled - always start fresh
        # self._load_persistent_cache()

        # Log initialization
        cache_path = self._get_cache_file_path()
        import os
        logger.info(
            "tool_registry_initialized",
            qube_id=qube.qube_id,
            cache_file_path=cache_path,
            cache_file_exists=os.path.exists(cache_path) if cache_path else False,
            in_memory_cache_size=len(self._tool_cache),
            data_dir=str(self.qube.data_dir) if hasattr(self.qube, 'data_dir') else 'NOT_SET'
        )

    def _get_cache_key(self, tool_name: str, parameters: Dict[str, Any]) -> str:
        """Generate a unique cache key for a tool call."""
        # Normalize parameters for better cache hits
        normalized_params = self._normalize_params_for_cache(tool_name, parameters)
        # Sort parameters for consistent hashing
        param_str = json.dumps(normalized_params, sort_keys=True, default=str)
        key_str = f"{tool_name}:{param_str}"
        cache_key = hashlib.md5(key_str.encode()).hexdigest()

        # Debug logging to help diagnose cache issues
        if parameters != normalized_params:
            logger.debug(
                "cache_key_normalized",
                tool=tool_name,
                original_params=parameters,
                normalized_params=normalized_params,
                cache_key=cache_key[:16],
                qube_id=self.qube.qube_id
            )

        return cache_key

    def _normalize_params_for_cache(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize parameters to improve cache hit rates.
        Handles cases where different parameter formats mean the same thing.
        """
        params = dict(parameters)  # Copy to avoid mutating original

        if tool_name == "get_system_state":
            # Normalize sections parameter:
            # - Missing sections, null sections, or empty sections all mean "get all"
            # - Sort sections list for consistent ordering
            sections = params.get("sections")
            if sections is None or sections == [] or sections == "":
                # Remove sections key entirely - means "get all"
                params.pop("sections", None)
            elif isinstance(sections, list):
                # Sort for consistent ordering
                params["sections"] = sorted(sections)

        # Remove None/null values that don't affect the result
        params = {k: v for k, v in params.items() if v is not None}

        return params

    def _get_cached_result(self, cache_key: str) -> Optional[Any]:
        """Get cached result if it exists and hasn't expired."""
        # If in-memory cache is empty, try loading from persistent storage
        # This handles the case where the process was restarted
        if not self._tool_cache:
            self._load_persistent_cache()

        if cache_key in self._tool_cache:
            result, timestamp = self._tool_cache[cache_key]
            if time.time() - timestamp < self._cache_ttl_seconds:
                return result
            else:
                # Expired, remove from cache
                del self._tool_cache[cache_key]
        return None

    def _cache_result(self, cache_key: str, result: Any) -> None:
        """Store a result in the cache."""
        self._tool_cache[cache_key] = (result, time.time())
        logger.info(
            "tool_cache_stored",
            cache_key=cache_key[:16],
            cache_size=len(self._tool_cache),
            qube_id=self.qube.qube_id
        )
        # Clean up old entries if cache gets too large
        if len(self._tool_cache) > 100:
            self._cleanup_cache()
        # Persist to disk for cross-process deduplication
        self._save_persistent_cache()

    def _cleanup_cache(self) -> None:
        """Remove expired entries from cache."""
        current_time = time.time()
        expired_keys = [
            key for key, (_, timestamp) in self._tool_cache.items()
            if current_time - timestamp >= self._cache_ttl_seconds
        ]
        for key in expired_keys:
            del self._tool_cache[key]

    def clear_tool_cache(self) -> None:
        """Clear all cached tool results. Call this when starting a new conversation."""
        cache_size = len(self._tool_cache)
        self._tool_cache.clear()
        # Also clear the persistent cache file
        self._clear_persistent_cache()
        logger.info("tool_cache_cleared", qube_id=self.qube.qube_id, previous_size=cache_size)

    def _get_cache_file_path(self) -> Optional[str]:
        """Get the path to the persistent cache file for this qube's session."""
        import os
        if not hasattr(self.qube, 'data_dir') or not self.qube.data_dir:
            logger.warning(
                "cache_file_path_unavailable",
                qube_id=self.qube.qube_id,
                has_data_dir=hasattr(self.qube, 'data_dir'),
                data_dir_value=getattr(self.qube, 'data_dir', 'NOT_SET')
            )
            return None
        # Session blocks are stored in data_dir/blocks/session/
        session_dir = os.path.join(self.qube.data_dir, "blocks", "session")
        return os.path.join(session_dir, "_tool_cache.json")

    def _load_persistent_cache(self) -> None:
        """Load tool cache from disk if it exists."""
        import os
        cache_file = self._get_cache_file_path()
        if not cache_file:
            logger.info(
                "persistent_cache_skip_no_path",
                qube_id=self.qube.qube_id
            )
            return

        if not os.path.exists(cache_file):
            logger.info(
                "persistent_cache_file_not_found",
                qube_id=self.qube.qube_id,
                cache_file=cache_file
            )
            return

        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Validate and load entries, checking TTL
            current_time = time.time()
            loaded_count = 0
            expired_count = 0
            for key, entry in data.items():
                if isinstance(entry, dict) and 'result' in entry and 'timestamp' in entry:
                    timestamp = entry['timestamp']
                    age_seconds = current_time - timestamp
                    if age_seconds < self._cache_ttl_seconds:
                        self._tool_cache[key] = (entry['result'], timestamp)
                        loaded_count += 1
                    else:
                        expired_count += 1

            logger.info(
                "persistent_cache_loaded",
                qube_id=self.qube.qube_id,
                entries_loaded=loaded_count,
                entries_expired=expired_count,
                total_in_file=len(data),
                cache_file=cache_file
            )
        except Exception as e:
            logger.warning(
                "persistent_cache_load_failed",
                qube_id=self.qube.qube_id,
                cache_file=cache_file,
                error=str(e)
            )

    def _save_persistent_cache(self) -> None:
        """Save tool cache to disk."""
        import os
        cache_file = self._get_cache_file_path()
        if not cache_file:
            return

        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(cache_file), exist_ok=True)

            # Convert cache to serializable format
            data = {}
            for key, (result, timestamp) in self._tool_cache.items():
                data[key] = {
                    'result': result,
                    'timestamp': timestamp
                }

            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)

            logger.info(
                "persistent_cache_saved",
                qube_id=self.qube.qube_id,
                entries=len(data),
                cache_file=cache_file
            )
        except Exception as e:
            logger.warning(
                "persistent_cache_save_failed",
                qube_id=self.qube.qube_id,
                error=str(e)
            )

    def _clear_persistent_cache(self) -> None:
        """Delete the persistent cache file."""
        import os
        cache_file = self._get_cache_file_path()
        if cache_file and os.path.exists(cache_file):
            try:
                os.remove(cache_file)
                logger.debug(
                    "persistent_cache_cleared",
                    qube_id=self.qube.qube_id
                )
            except Exception as e:
                logger.warning(
                    "persistent_cache_clear_failed",
                    qube_id=self.qube.qube_id,
                    error=str(e)
                )

    def register(self, tool: ToolDefinition) -> None:
        """
        Register a new tool

        Args:
            tool: Tool definition to register
        """
        self.tools[tool.name] = tool
        logger.debug("tool_registered", tool_name=tool.name, qube_id=self.qube.qube_id)

    def unregister(self, tool_name: str) -> None:
        """Unregister a tool"""
        if tool_name in self.tools:
            del self.tools[tool_name]
            logger.debug("tool_unregistered", tool_name=tool_name)

    def get_tool(self, tool_name: str) -> Optional[ToolDefinition]:
        """Get tool by name"""
        return self.tools.get(tool_name)

    def list_tools(self) -> List[str]:
        """List all registered tool names"""
        return list(self.tools.keys())

    def get_tools_for_model(
        self,
        model_provider: str,
        unlocked_tools: Optional[Set[str]] = None,
        model_name: Optional[str] = None,
        user_message: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get tools in format for specific model provider, filtered by skill unlocks

        Args:
            model_provider: Provider name (openai, anthropic, google, perplexity, ollama)
            unlocked_tools: Set of tool names unlocked via maxed skills (from SkillsManager)
            model_name: Optional model name for small model detection
            user_message: Optional user message for dynamic tool selection (small models)

        Returns:
            List of tools in provider-specific format
        """
        # Note: Ollama models now use prompt-based tool calling (like Venice/Perplexity)
        # The ollama_provider.py handles injecting tool instructions into the prompt
        # and parsing <tool_call> tags from responses. This allows local models to
        # participate in model switching and other tool-based operations.

        # Check if revolver mode is enabled - if so, exclude switch_model tool
        # This prevents the Qube from trying to switch models when revolver mode
        # automatically rotates them
        revolver_mode_enabled = False
        if hasattr(self.qube, 'chain_state') and self.qube.chain_state:
            revolver_mode_enabled = self.qube.chain_state.is_revolver_mode_enabled()

        # Detect small/local models that need dynamic tool selection
        # These models get confused with too many tools, so we filter based on user message
        is_small_model = False
        if model_name:
            small_model_patterns = [
                "llama3.2",      # Llama 3.2 all sizes (1b, 3b, etc.)
                "llama-3.2",     # Alternative naming
                "qwen3:4b",      # Small Qwen
                "qwen2.5:7b",    # Small Qwen
                "gemma2:9b",     # Gemma 2
                "phi4:14b",      # Phi 4
                "mistral:7b",    # Small Mistral
                "deepseek-r1:8b", # Small DeepSeek
            ]
            model_lower = model_name.lower()
            is_small_model = any(pattern in model_lower for pattern in small_model_patterns)

        # Determine which tools are available
        if is_small_model:
            # Dynamic tool selection based on user message keywords
            # Start with core tools that are always useful
            selected_tools: Set[str] = set(SMALL_MODEL_CORE_TOOLS)

            # Add tools based on keywords in user message
            if user_message:
                message_lower = user_message.lower()
                for keyword, tools in KEYWORD_TO_TOOLS.items():
                    if keyword in message_lower:
                        selected_tools.update(tools)

            # If no keywords matched, add some general-purpose tools
            if len(selected_tools) == len(SMALL_MODEL_CORE_TOOLS):
                selected_tools.update(["describe_my_avatar", "web_search", "recall_similar"])

            # Exclude switch_model in revolver mode
            if revolver_mode_enabled:
                selected_tools.discard("switch_model")

            # Filter to only registered tools that were selected
            tools_to_use = [
                tool for tool in self.tools.values()
                if tool.name in selected_tools
            ]

            logger.info(
                "small_model_dynamic_tool_selection",
                model=model_name,
                user_message_preview=user_message[:100] if user_message else None,
                tool_count=len(tools_to_use),
                tools=[t.name for t in tools_to_use]
            )
        elif unlocked_tools is not None:
            # Tool is available if:
            # 1. It's in ALWAYS_AVAILABLE_TOOLS (core functionality)
            # 2. OR it's been unlocked via a maxed skill
            # 3. AND it's not switch_model when revolver mode is on
            tools_to_use = [
                tool for tool in self.tools.values()
                if (tool.name in ALWAYS_AVAILABLE_TOOLS or tool.name in unlocked_tools)
                and not (revolver_mode_enabled and tool.name == "switch_model")
            ]
            logger.debug(
                "tools_filtered_by_skills",
                total_tools=len(self.tools),
                available_tools=len(tools_to_use),
                unlocked_count=len(unlocked_tools),
                revolver_mode=revolver_mode_enabled,
                qube_id=self.qube.qube_id
            )
        else:
            # No skill filtering - all tools available (backward compatibility)
            # Still exclude switch_model in revolver mode
            tools_to_use = [
                tool for tool in self.tools.values()
                if not (revolver_mode_enabled and tool.name == "switch_model")
            ]

        # OpenAI enforces a max of 128 tools per request
        # If we exceed that, prioritize ALWAYS_AVAILABLE_TOOLS and trim the rest
        MAX_TOOLS = 128
        if len(tools_to_use) > MAX_TOOLS:
            always = [t for t in tools_to_use if t.name in ALWAYS_AVAILABLE_TOOLS]
            rest = [t for t in tools_to_use if t.name not in ALWAYS_AVAILABLE_TOOLS]
            tools_to_use = always + rest[:MAX_TOOLS - len(always)]
            logger.warning(
                "tools_truncated_to_api_limit",
                original_count=len(always) + len(rest),
                truncated_to=len(tools_to_use),
                max_tools=MAX_TOOLS,
            )

        if model_provider == "openai":
            return [tool.to_openai_format() for tool in tools_to_use]
        elif model_provider == "anthropic":
            return [tool.to_anthropic_format() for tool in tools_to_use]
        elif model_provider == "google":
            # Google returns list of tool objects
            return [tool.to_google_format() for tool in tools_to_use]
        elif model_provider == "perplexity":
            # Use OpenAI format (compatible)
            return [tool.to_openai_format() for tool in tools_to_use]
        else:
            # Default to OpenAI format
            return [tool.to_openai_format() for tool in tools_to_use]

    def _award_xp_for_action_block(self, block) -> None:
        """
        Award XP for completed ACTION block during session.

        XP is awarded immediately so users see progress, but is provisional
        until the session is anchored. If session is discarded, XP rolls back.

        Uses the 5/2/0 formula:
        - 5 XP for successful tool use
        - 2 XP for completed with issues
        - 0 XP for failure

        Args:
            block: Completed ACTION block with status and result
        """
        try:
            from ai.skill_scanner import analyze_research_topic, TOOL_TO_SKILL_MAPPING, calculate_document_xp
            from utils.skills_manager import SkillsManager

            content = block.content if isinstance(block.content, dict) else {}
            action_type = content.get("action_type")

            if not action_type:
                return

            # Determine skill_id based on action_type
            skill_id = None
            xp_amount = 0

            # For research tools, analyze content to determine skill
            if action_type == "web_search":
                params = content.get("parameters", {})
                query = params.get("query", "")
                skill_id = analyze_research_topic(query)
            elif action_type == "browse_url":
                params = content.get("parameters", {})
                url = params.get("url", "")
                skill_id = analyze_research_topic("", url)
            elif action_type == "process_document":
                # Document processing goes to memory_recall
                skill_id = "memory_recall"

                # Custom XP calculation based on file size and page count
                params = content.get("parameters", {})
                result = content.get("result", {})
                status = content.get("status", "unknown")

                file_size_bytes = params.get("file_size_bytes", 0)
                page_count = result.get("page_count", 0)
                success = result.get("success", False)

                if status == "completed" and success:
                    xp_amount = calculate_document_xp(file_size_bytes, page_count)
                elif status == "completed":
                    xp_amount = 1  # Partial extraction
                else:
                    return  # No XP for failures
            elif action_type in TOOL_TO_SKILL_MAPPING:
                skill_id = TOOL_TO_SKILL_MAPPING[action_type]

            # Award XP if we identified a skill
            if skill_id:
                status = content.get("status", "unknown")
                result = content.get("result", {})

                # Standard 5/2/0 XP formula (skip for process_document - already calculated)
                if action_type != "process_document":
                    if status == "completed" and isinstance(result, dict) and result.get("success", False):
                        xp_amount = 5  # Successful use
                    elif status == "completed":
                        xp_amount = 2  # Completed but may have issues
                    else:
                        return  # No XP for failures

                # Award XP immediately (provisional until anchored)
                skills_manager = SkillsManager(self.qube.chain_state)
                skills_manager.add_xp(
                    skill_id=skill_id,
                    xp_amount=xp_amount,
                    evidence_block_id=f"session_block_{block.block_number}",
                    evidence_description=f"Used {action_type} tool during session"
                )

                logger.info(
                    "session_xp_awarded",
                    skill_id=skill_id,
                    xp_amount=xp_amount,
                    block_number=block.block_number,
                    action_type=action_type
                )
        except Exception as e:
            logger.warning(
                "session_xp_award_failed",
                error=str(e)
            )

    def _calculate_file_size_xp(self, file_size_bytes: int) -> int:
        """
        Calculate XP based on file size (1-10 XP).
        Simple linear scaling: 1 XP per 500 KB, capped at 10.

        Args:
            file_size_bytes: File size in bytes

        Returns:
            XP amount (1-10)
        """
        return min(10, max(1, file_size_bytes // 500_000))

    def _calculate_page_count_xp(self, page_count: int) -> int:
        """
        Calculate XP based on page count (2-10 XP).
        Simple scaling: ~0.8 XP per page, capped at 10.

        Args:
            page_count: Number of pages

        Returns:
            XP amount (2-10)
        """
        return min(10, max(2, int(page_count * 0.8)))

    def _calculate_document_xp(self, file_size_bytes: int, page_count: int) -> int:
        """
        Calculate XP for document processing.
        Awards whichever gives more XP: file size or page count.
        This rewards both large files and multi-page processing.

        Args:
            file_size_bytes: File size in bytes
            page_count: Number of pages

        Returns:
            XP amount (1-10)
        """
        file_size_xp = self._calculate_file_size_xp(file_size_bytes)
        page_count_xp = self._calculate_page_count_xp(page_count)
        return max(file_size_xp, page_count_xp)

    async def execute_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        record_blocks: bool = True
    ) -> Any:
        """
        Execute a tool and return result

        Creates ACTION block with result included (no separate OBSERVATION block).

        Args:
            tool_name: Name of tool to execute
            parameters: Tool parameters
            record_blocks: Whether to create memory blocks (default True)

        Returns:
            Tool execution result

        Raises:
            AIError: If tool not found or execution fails
        """
        # Defensive check: ensure parameters is a dict (model might send a list)
        if not isinstance(parameters, dict):
            logger.warning(
                "execute_tool_parameters_not_dict",
                tool=tool_name,
                parameters_type=type(parameters).__name__,
                parameters=str(parameters)[:200]
            )
            parameters = {}

        # ========== TOOL CALL DEDUPLICATION - DISABLED ==========
        # Cache disabled - always execute tools fresh
        # The cache was causing issues with stale results and complex state management
        cache_key = None  # For later use if we want to re-enable caching
        # ========== END DEDUPLICATION ==========

        # Validation layer - check if action should be allowed
        if hasattr(self.qube, 'decision_config') and self.qube.decision_config.enable_validation_layer:
            from ai.decision_validator import DecisionValidator

            validator = DecisionValidator(self.qube)

            # Extract target_entity if present in parameters
            target_entity = parameters.get("entity_id") or parameters.get("recipient_id")

            # Validate the action
            validation = await validator.validate_action(
                action_type=tool_name,
                target_entity=target_entity,
                **parameters
            )

            if not validation.allowed:
                # Action blocked by validation layer
                logger.warning(
                    "action_blocked_by_validation",
                    tool=tool_name,
                    reason=validation.blocking_reason,
                    warnings=validation.warnings,
                    qube_id=self.qube.qube_id
                )

                return {
                    "error": f"Action blocked: {validation.blocking_reason}",
                    "warnings": validation.warnings,
                    "suggestions": validation.suggestions,
                    "success": False,
                    "validation_failed": True
                }

            # Log warnings if present (but allow action to proceed)
            if validation.warnings:
                logger.warning(
                    "action_validation_warnings",
                    tool=tool_name,
                    warnings=validation.warnings,
                    confidence=validation.confidence,
                    qube_id=self.qube.qube_id
                )

        # Tool alias mapping for common model hallucinations
        # Models using prompt-based tool calling sometimes guess at tool names
        TOOL_ALIASES = {
            # System state aliases
            "scan_system": "get_system_state",
            "check_system": "get_system_state",
            "system_scan": "get_system_state",
            "get_state": "get_system_state",
            "check_state": "get_system_state",
            "system_status": "get_system_state",
            "get_status": "get_system_state",
            "my_status": "get_system_state",
            "check_status": "get_system_state",
            # Avatar/mirror aliases
            "look_in_mirror": "describe_my_avatar",
            "look_mirror": "describe_my_avatar",
            "mirror": "describe_my_avatar",
            "see_myself": "describe_my_avatar",
            "my_appearance": "describe_my_avatar",
            "describe_avatar": "describe_my_avatar",
            "view_avatar": "describe_my_avatar",
            "check_appearance": "describe_my_avatar",
            "what_do_i_look_like": "describe_my_avatar",
            # Web search aliases
            "search_web": "web_search",
            "internet_search": "web_search",
            "google_search": "web_search",
            # Browse aliases
            "browse_web": "browse_url",
            "open_url": "browse_url",
            "visit_url": "browse_url",
            "visit_website": "browse_url",
            # Model switch aliases
            "change_model": "switch_model",
            "set_model": "switch_model",
            # Memory aliases
            "memory_search": "recall",
            "remember": "recall",
            "save_memory": "add_memory",
            "store_memory": "add_memory",
            "create_memory": "add_memory",
        }

        # Resolve alias if present
        if tool_name in TOOL_ALIASES:
            original_name = tool_name
            tool_name = TOOL_ALIASES[tool_name]
            logger.info(
                "tool_alias_resolved",
                original=original_name,
                resolved=tool_name,
                qube_id=self.qube.qube_id
            )

        tool = self.tools.get(tool_name)
        if not tool:
            raise AIError(
                f"Unknown tool: {tool_name}",
                context={"tool": tool_name, "available_tools": list(self.tools.keys())}
            )

        logger.info(
            "tool_execution_started",
            tool=tool_name,
            parameters=parameters,
            qube_id=self.qube.qube_id
        )

        # Get current model for ACTION block tracking
        current_model = None
        if hasattr(self.qube, 'chain_state') and self.qube.chain_state:
            # In Manual mode, use locked_model (source of truth for user's choice)
            # In other modes, use runtime.current_model
            model_mode = self.qube.chain_state.get_model_mode()
            if model_mode == "manual":
                current_model = self.qube.chain_state.get_locked_model()
            else:
                runtime = self.qube.chain_state.get_runtime()
                current_model = runtime.get("current_model")

        # Create in_progress ACTION block BEFORE executing (so frontend can show status)
        in_progress_block = None
        tool_timestamp = int(time.time() * 1000)  # Millisecond timestamp for uniqueness
        if record_blocks and self.qube.current_session:
            from core.block import create_action_block
            latest = self.qube.memory_chain.get_latest_block()
            # Use get_next_turn_number() for unique per-block turn numbers
            session = self.qube.current_session
            if session.get_next_turn_number:
                turn_number = session.get_next_turn_number()
            else:
                turn_number = getattr(session, 'current_turn_number', None)
            in_progress_block = create_action_block(
                qube_id=self.qube.qube_id,
                block_number=-1,
                previous_block_number=latest.block_number if latest else 0,
                action_type=tool_name,
                parameters=parameters,
                initiated_by="self",
                status="in_progress",
                result=None,
                temporary=True,
                model_used=current_model,
                turn_number=turn_number
            )
            self.qube.current_session.create_block(in_progress_block)
            tool_timestamp = in_progress_block.timestamp

            # Emit real-time tool call event to stdout (picked up by Rust/Tauri)
            import sys
            tool_event = {
                "event_type": "tool_call",
                "action_type": tool_name,
                "status": "in_progress",
                "speaker_id": self.qube.qube_id,
                "speaker_name": self.qube.name,
                "timestamp": tool_timestamp,
                "parameters": parameters,
            }
            if _tool_event_callback:
                _tool_event_callback(tool_event)
            else:
                print(f"__TOOL_EVENT__{json.dumps(tool_event)}", file=sys.stderr, flush=True)

        # Execute tool
        try:
            result = await tool.handler(parameters)
            status = "completed"

            MetricsRecorder.record_tool_execution(tool_name, "success")

            # Emit tool called event
            from core.events import Events
            self.qube.events.emit(Events.TOOL_CALLED, {
                "tool_name": tool_name
            })

            logger.info(
                "tool_execution_complete",
                tool=tool_name,
                success=True,
                qube_id=self.qube.qube_id
            )

        except Exception as e:
            status = "failed"
            MetricsRecorder.record_tool_execution(tool_name, "error")

            logger.error(
                "tool_execution_failed",
                tool=tool_name,
                qube_id=self.qube.qube_id,
                exc_info=True
            )

            result = {
                "error": str(e),
                "success": False
            }

        # Update the in_progress block with result, or create new block if none exists
        if record_blocks:
            if self.qube.current_session:
                if in_progress_block:
                    # Update the in_progress block with result
                    in_progress_block.content["status"] = status
                    in_progress_block.content["result"] = result
                    # Re-save to disk (overwrites the in_progress file)
                    self.qube.current_session._save_session_block(in_progress_block)

                    # Emit real-time tool completion event to stdout
                    import sys
                    tool_event = {
                        "event_type": "tool_call",
                        "action_type": tool_name,
                        "status": status,
                        "speaker_id": self.qube.qube_id,
                        "speaker_name": self.qube.name,
                        "timestamp": tool_timestamp,
                        "result": result if not isinstance(result, dict) or len(json.dumps(result)) < 500 else {"truncated": True},
                    }
                    if _tool_event_callback:
                        _tool_event_callback(tool_event)
                    else:
                        print(f"__TOOL_EVENT__{json.dumps(tool_event)}", file=sys.stderr, flush=True)

                    # Award XP now that we have complete status and result
                    logger.info(
                        "about_to_award_xp",
                        tool_name=tool_name,
                        block_number=in_progress_block.block_number,
                        status=status,
                        result_type=type(result).__name__
                    )
                    self._award_xp_for_action_block(in_progress_block)
                    logger.info("xp_award_call_completed", tool_name=tool_name)
                else:
                    # No in_progress block (shouldn't happen, but fallback)
                    latest = self.qube.memory_chain.get_latest_block()
                    # Use get_next_turn_number() for unique per-block turn numbers
                    session = self.qube.current_session
                    if session.get_next_turn_number:
                        turn_number = session.get_next_turn_number()
                    else:
                        turn_number = getattr(session, 'current_turn_number', None)
                    action_block_data = create_action_block(
                        qube_id=self.qube.qube_id,
                        block_number=-1,
                        previous_block_number=latest.block_number if latest else 0,
                        action_type=tool_name,
                        parameters=parameters,
                        initiated_by="self",
                        status=status,
                        result=result,
                        temporary=True,
                        model_used=current_model,
                        turn_number=turn_number
                    )
                    created_block = self.qube.current_session.create_block(action_block_data)

                    # Award XP for this completed block
                    self._award_xp_for_action_block(created_block)
            else:
                # Add to permanent chain (rare case - tool called outside session)
                from pathlib import Path
                import json as json_module
                from crypto.signing import sign_block

                latest = self.qube.memory_chain.get_latest_block()
                block_number = self.qube.memory_chain.get_chain_length()
                # Use get_next_turn_number() for unique per-block turn numbers
                turn_number = None
                if self.qube.current_session:
                    session = self.qube.current_session
                    if session.get_next_turn_number:
                        turn_number = session.get_next_turn_number()
                    else:
                        turn_number = getattr(session, 'current_turn_number', None)
                action_block_data = create_action_block(
                    qube_id=self.qube.qube_id,
                    block_number=block_number,
                    previous_hash=latest.block_hash if latest else self.qube.genesis_block.block_hash,
                    action_type=tool_name,
                    parameters=parameters,
                    initiated_by="self",
                    status=status,
                    result=result,
                    temporary=False,
                    model_used=current_model,
                    turn_number=turn_number
                )

                # Encrypt content for permanent storage
                if action_block_data.content:
                    encrypted_content = self.qube.encrypt_block_content(action_block_data.content)
                    action_block_data.content = encrypted_content
                    action_block_data.encrypted = True

                # Sign the block
                action_block_data.block_hash = action_block_data.compute_hash()
                action_block_data.signature = sign_block(action_block_data.to_dict(), self.qube.private_key)

                # Save block to disk
                permanent_dir = Path(self.qube.data_dir) / "blocks" / "permanent"
                permanent_dir.mkdir(parents=True, exist_ok=True)
                block_type_str = action_block_data.block_type if isinstance(action_block_data.block_type, str) else action_block_data.block_type.value
                filename = f"{block_number}_{block_type_str}_{action_block_data.timestamp}.json"
                with open(permanent_dir / filename, 'w') as f:
                    json_module.dump(action_block_data.to_dict(), f, indent=2)

                # Add to memory chain index
                self.qube.memory_chain.add_block(action_block_data)

                # Emit events to update chain state
                self.qube.events.emit(Events.BLOCK_ADDED, {
                    "block_type": "ACTION",
                    "block_number": block_number
                })
                self.qube.events.emit(Events.CHAIN_UPDATED, {
                    "chain_length": block_number + 1,
                    "last_block_number": block_number,
                    "last_block_hash": action_block_data.block_hash
                })

        # Cache disabled - don't store results
        # if status == "completed" and tool_name not in self._uncacheable_tools:
        #     cache_key = self._get_cache_key(tool_name, parameters)
        #     self._cache_result(cache_key, result)

        return result

    def to_dict(self) -> Dict[str, Any]:
        """Serialize registry to dictionary"""
        return {
            "tools": [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters
                }
                for tool in self.tools.values()
            ]
        }
