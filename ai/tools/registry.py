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
    # Memory operations (essential)
    "search_memory",
    "get_recent_memories",
    "remember_about_owner",  # Learning about owner is core functionality
    # Basic information
    "get_current_time",
    "describe_my_skills",
    "describe_my_avatar",
    "get_relationships",
    # Communication (essential for interaction)
    "send_message",
    # Web access (fundamental capability)
    "web_search",
    "browse_url",
    # Image generation (creative capability)
    "generate_image",
    # Games (runtime check for active game)
    "chess_move",
    # Wallet operations (core functionality for BCH-enabled qubes)
    "send_bch",
    # Model switching (Qube agency over cognitive architecture)
    "switch_model",
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

        # Execute tool first
        try:
            result = await tool.handler(parameters)
            status = "completed"

            MetricsRecorder.record_tool_execution(tool_name, "success")

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

        # Record ACTION block with result included
        if record_blocks:
            if self.qube.current_session:
                # Add to session (temporary)
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
                    temporary=True
                )

                # Note: Relationship updates now handled by AI during SUMMARY blocks
                # No need to set relationship_updates on individual ACTION blocks

                self.qube.current_session.create_block(action_block_data)
            else:
                # Add to permanent chain
                latest = self.qube.memory_chain.get_latest_block()
                action_block_data = create_action_block(
                    qube_id=self.qube.qube_id,
                    block_number=self.qube.memory_chain.get_chain_length(),
                    previous_hash=latest.block_hash if latest else self.qube.genesis_block.block_hash,
                    action_type=tool_name,
                    parameters=parameters,
                    initiated_by="self",
                    status=status,
                    result=result,
                    temporary=False
                )

                # Note: Relationship updates now handled by AI during SUMMARY blocks
                # No need to set relationship_updates on individual ACTION blocks

                self.qube.memory_chain.add_block(action_block_data)
                # Note: self.qube.storage was removed, blocks are saved as individual JSON files

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
