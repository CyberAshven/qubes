"""
Tool Registry and Definition

Manages available tools for AI agents with multi-provider format conversion.
Matches documentation in docs/09_AI_Integration_Tool_Calling.md Section 6.2
"""

from typing import Dict, Any, Callable, List, Optional, Awaitable, Set
from dataclasses import dataclass, field
from core.block import create_action_block, BlockType
from core.exceptions import AIError
from utils.logging import get_logger
from monitoring.metrics import MetricsRecorder

logger = get_logger(__name__)

# Core tools that are always available regardless of skill level
# These are essential for basic qube functionality
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

    # Planet tools (unlocked from start)
    # AI Reasoning planets
    "find_analogy",
    "analyze_mistake",
    "replicate_success",
    "self_reflect",
    "synthesize_learnings",
    # Social Intelligence planets
    "recall_relationship_history",
    "read_emotional_state",
    "adapt_communication_style",
    "steelman",
    "assess_trust_level",
    # Coding planets
    "run_tests",
    "debug_code",
    "benchmark_code",
    "security_scan",
    "review_code",
    # Creative Expression planets
    "compose_text",
    "compose_music",
    "craft_narrative",
    "describe_my_avatar",
    # Memory & Recall planets
    "recall",
    "store_fact",
    "tag_memory",
    "synthesize_knowledge",
    "create_summary",
    # Security & Privacy planets
    "audit_chain",
    "assess_sensitivity",
    "vet_qube",
    "detect_threat",
    "defend_reasoning",
    # Board Games planets
    "chess_move",
    "property_tycoon_action",
    "race_home_action",
    "mystery_mansion_action",
    "life_journey_action",
    # Finance planets
    "validate_transaction",
    "check_wallet_health",
    "get_market_data",
    "plan_savings",
    "identify_token",
    # Note: Document processing happens automatically in gui_bridge.py
    # No tool needed - results injected as tool results in reasoner.py
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

        logger.info("tool_registry_initialized", qube_id=qube.qube_id)

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
        unlocked_tools: Optional[Set[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get tools in format for specific model provider, filtered by skill unlocks

        Args:
            model_provider: Provider name (openai, anthropic, google, perplexity, ollama)
            unlocked_tools: Set of tool names unlocked via maxed skills (from SkillsManager)

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

        # Filter tools based on skill unlocks
        if unlocked_tools is not None:
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
        Award XP for completed ACTION block.

        Called after tool execution completes and block is updated with result.

        Args:
            block: Completed ACTION block with status and result
        """
        logger.info(
            "xp_award_method_called",
            block_number=block.block_number,
            block_type=block.block_type
        )
        try:
            from ai.skill_scanner import analyze_research_topic, TOOL_TO_SKILL_MAPPING
            from utils.skills_manager import SkillsManager

            content = block.content if isinstance(block.content, dict) else {}
            action_type = content.get("action_type")

            logger.info(
                "xp_award_parsing_block",
                action_type=action_type,
                has_content=content is not None,
                content_keys=list(content.keys()) if content else []
            )

            if not action_type:
                return

            # Determine skill_id based on action_type
            skill_id = None

            # For research tools, analyze content
            if action_type == "web_search":
                params = content.get("parameters", {})
                query = params.get("query", "")
                skill_id = analyze_research_topic(query)
            elif action_type == "browse_url":
                params = content.get("parameters", {})
                url = params.get("url", "")
                skill_id = analyze_research_topic("", url)
            elif action_type == "process_document":
                # Document processing always goes to knowledge_domains (research)
                skill_id = "knowledge_domains"

                # Custom XP calculation based on file size and page count
                params = content.get("parameters", {})
                result = content.get("result", {})
                status = content.get("status", "unknown")

                file_size_bytes = params.get("file_size_bytes", 0)
                page_count = result.get("page_count", 0)
                success = result.get("success", False)

                # Calculate XP based on document complexity
                if status == "completed" and success:
                    # Use custom formula (1-10 XP)
                    xp_amount = self._calculate_document_xp(file_size_bytes, page_count)

                    logger.info(
                        "document_xp_calculated",
                        file_size_bytes=file_size_bytes,
                        page_count=page_count,
                        xp_amount=xp_amount
                    )
                elif status == "completed":
                    # Partial extraction - award minimum XP
                    xp_amount = 1
                else:
                    # Failed - no XP for failed document processing
                    xp_amount = 0
                    skill_id = None  # Don't award XP for failures
            elif action_type in TOOL_TO_SKILL_MAPPING:
                skill_id = TOOL_TO_SKILL_MAPPING[action_type]

            # Award XP if we identified a skill
            if skill_id:
                status = content.get("status", "unknown")
                result = content.get("result", {})

                # Determine XP amount based on success
                # (Skip this section if action_type == "process_document" - already calculated above)
                if action_type != "process_document":
                    if status == "completed" and isinstance(result, dict) and result.get("success", False):
                        xp_amount = 3  # Successful use
                    elif status == "completed":
                        xp_amount = 2  # Completed but may have issues
                    else:
                        xp_amount = 0  # Failed or error - no XP (prevents gaming)
                        skill_id = None  # Don't award XP for failures

                # Award XP immediately (writes to chain_state.skills)
                skills_manager = SkillsManager(self.qube.chain_state)

                xp_result = skills_manager.add_xp(
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
                    action_type=action_type,
                    status=status,
                    result_success=result.get("success") if isinstance(result, dict) else None
                )
        except Exception as e:
            logger.warning(
                "session_xp_award_failed",
                qube_id=self.qube.qube_id,
                block_number=block.block_number,
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
            "scan_system": "get_system_state",
            "check_system": "get_system_state",
            "system_scan": "get_system_state",
            "get_state": "get_system_state",
            "check_state": "get_system_state",
            "search_web": "web_search",
            "internet_search": "web_search",
            "google_search": "web_search",
            "browse_web": "browse_url",
            "open_url": "browse_url",
            "visit_url": "browse_url",
            "visit_website": "browse_url",
            "change_model": "switch_model",
            "set_model": "switch_model",
            "search_memory": "memory_search",
            "recall": "memory_search",
            "remember": "memory_search",
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
        if record_blocks and self.qube.current_session:
            from core.block import create_action_block
            latest = self.qube.memory_chain.get_latest_block()
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
                model_used=current_model
            )
            self.qube.current_session.create_block(in_progress_block)

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
                        model_used=current_model
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
                    model_used=current_model
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
