"""
Prompt-Based Tool Calling

Enables tool/function calling for models without native support.
Injects tool descriptions into the system prompt and parses
structured tool calls from the model's response.

This allows models like venice-uncensored, Ollama models, and other
non-function-calling models to use Qube tools.
"""

import re
import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ParsedToolCall:
    """A tool call parsed from model output"""
    name: str
    arguments: Dict[str, Any]
    raw_text: str  # Original text that was parsed


class PromptBasedToolHandler:
    """
    Enables tool calling for models without native function calling support.

    Works by:
    1. Converting tool schemas to natural language descriptions
    2. Injecting tool instructions into the system prompt
    3. Parsing structured tool calls from model responses
    4. Formatting tool results for the model to continue
    """

    # XML-style tags for tool calls (models handle these well)
    TOOL_CALL_PATTERN = re.compile(
        r'<tool_call>\s*(\{.*?\})\s*</tool_call>',
        re.DOTALL | re.IGNORECASE
    )

    # Alternative patterns models might use
    ALT_PATTERNS = [
        re.compile(r'```tool_call\s*\n(\{.*?\})\n```', re.DOTALL),
        re.compile(r'```json\s*\n(\{.*?\})\n```', re.DOTALL),
        re.compile(r'\[TOOL_CALL\]\s*(\{.*?\})\s*\[/TOOL_CALL\]', re.DOTALL | re.IGNORECASE),
    ]

    TOOL_INSTRUCTION_TEMPLATE = """
## Available Tools

You have access to the following tools. Use them when needed to help the user.

{tool_descriptions}

## How to Use Tools

When you need to use a tool, output a tool call in this exact format:
<tool_call>{{"name": "tool_name", "arguments": {{"arg1": "value1"}}}}</tool_call>

Important rules:
1. Output ONLY the tool_call tag when using a tool - don't add extra text before it
2. Wait for the tool result before continuing your response
3. You can use multiple tools in sequence if needed
4. After receiving tool results, provide your final response to the user

Example:
User: What's the weather in Tokyo?
Assistant: <tool_call>{{"name": "get_weather", "arguments": {{"location": "Tokyo"}}}}</tool_call>
[Tool Result: Temperature: 22°C, Sunny]
Assistant: The weather in Tokyo is currently sunny with a temperature of 22°C.
"""

    def __init__(self, max_tool_calls: int = 10):
        """
        Initialize the prompt-based tool handler.

        Args:
            max_tool_calls: Maximum tool calls per turn (prevents infinite loops)
        """
        self.max_tool_calls = max_tool_calls

    def format_tools_for_prompt(self, tools: List[Dict[str, Any]]) -> str:
        """
        Convert OpenAI-style tool definitions to human-readable descriptions.

        Args:
            tools: List of tool definitions in OpenAI format

        Returns:
            Formatted string describing all tools
        """
        if not tools:
            return ""

        descriptions = []

        for tool in tools:
            if tool.get("type") != "function":
                continue

            func = tool.get("function", {})
            name = func.get("name", "unknown")
            desc = func.get("description", "No description")
            params = func.get("parameters", {})

            # Format parameters
            param_lines = []
            properties = params.get("properties", {})
            required = params.get("required", [])

            for param_name, param_info in properties.items():
                param_type = param_info.get("type", "any")
                param_desc = param_info.get("description", "")
                is_required = param_name in required
                req_marker = " (required)" if is_required else " (optional)"

                param_lines.append(f"    - {param_name}: {param_type}{req_marker} - {param_desc}")

            # Build tool description
            tool_desc = f"### {name}\n{desc}"
            if param_lines:
                tool_desc += "\n  Parameters:\n" + "\n".join(param_lines)

            descriptions.append(tool_desc)

        return "\n\n".join(descriptions)

    def inject_tools_into_messages(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """
        Add tool instructions to the system prompt.

        Args:
            messages: Original conversation messages
            tools: Tool definitions to inject

        Returns:
            Modified messages with tool instructions in system prompt
        """
        if not tools:
            return messages

        tool_descriptions = self.format_tools_for_prompt(tools)
        tool_instructions = self.TOOL_INSTRUCTION_TEMPLATE.format(
            tool_descriptions=tool_descriptions
        )

        # Create a copy to avoid modifying original
        new_messages = []
        system_found = False

        for msg in messages:
            if msg.get("role") == "system" and not system_found:
                # Append tool instructions to existing system prompt
                new_content = msg.get("content", "") + "\n\n" + tool_instructions
                new_messages.append({"role": "system", "content": new_content})
                system_found = True
            else:
                new_messages.append(msg.copy())

        # If no system message exists, add one
        if not system_found:
            new_messages.insert(0, {"role": "system", "content": tool_instructions})

        logger.debug(
            "tools_injected_into_prompt",
            tool_count=len(tools),
            tool_names=[t.get("function", {}).get("name") for t in tools if t.get("type") == "function"]
        )

        return new_messages

    def parse_tool_calls(self, content: str) -> List[ParsedToolCall]:
        """
        Extract tool calls from model response.

        Args:
            content: Model's response text

        Returns:
            List of parsed tool calls
        """
        tool_calls = []

        # Try main pattern first
        matches = self.TOOL_CALL_PATTERN.findall(content)

        # Try alternative patterns if no matches
        if not matches:
            for pattern in self.ALT_PATTERNS:
                matches = pattern.findall(content)
                if matches:
                    break

        for match in matches:
            try:
                # Parse the JSON
                data = json.loads(match)

                name = data.get("name")
                arguments = data.get("arguments", {})

                if name:
                    tool_calls.append(ParsedToolCall(
                        name=name,
                        arguments=arguments,
                        raw_text=match
                    ))

                    logger.debug(
                        "tool_call_parsed",
                        tool_name=name,
                        argument_count=len(arguments)
                    )

            except json.JSONDecodeError as e:
                logger.warning(
                    "tool_call_parse_failed",
                    error=str(e),
                    raw_text=match[:100]
                )
                continue

        return tool_calls

    def has_tool_call(self, content: str) -> bool:
        """Check if content contains a tool call."""
        return bool(self.TOOL_CALL_PATTERN.search(content)) or \
               any(p.search(content) for p in self.ALT_PATTERNS)

    def format_tool_result(
        self,
        tool_name: str,
        result: Any,
        success: bool = True
    ) -> str:
        """
        Format a tool result for feeding back to the model.

        Args:
            tool_name: Name of the tool that was called
            result: Result from tool execution
            success: Whether the tool call succeeded

        Returns:
            Formatted result string
        """
        if success:
            if isinstance(result, dict):
                result_str = json.dumps(result, indent=2)
            else:
                result_str = str(result)
            return f"[Tool Result - {tool_name}]\n{result_str}\n[End Tool Result]"
        else:
            return f"[Tool Error - {tool_name}]\n{result}\n[End Tool Error]"

    def extract_content_without_tool_calls(self, content: str) -> str:
        """
        Remove tool call tags from content to get clean text.

        Args:
            content: Model response with potential tool calls

        Returns:
            Content with tool call tags removed
        """
        # Remove main pattern
        clean = self.TOOL_CALL_PATTERN.sub('', content)

        # Remove alternative patterns
        for pattern in self.ALT_PATTERNS:
            clean = pattern.sub('', clean)

        # Clean up extra whitespace
        clean = re.sub(r'\n{3,}', '\n\n', clean)
        return clean.strip()

    def convert_to_native_format(
        self,
        parsed_calls: List[ParsedToolCall]
    ) -> List[Dict[str, Any]]:
        """
        Convert parsed tool calls to OpenAI-style tool_calls format.

        This allows the rest of the system to handle them uniformly.

        Args:
            parsed_calls: Tool calls parsed from model output

        Returns:
            Tool calls in OpenAI format
        """
        import uuid

        return [
            {
                "id": f"prompt_tool_{uuid.uuid4().hex[:8]}",
                "type": "function",
                "name": call.name,
                "parameters": call.arguments
            }
            for call in parsed_calls
        ]


# Singleton instance for easy access
_handler: Optional[PromptBasedToolHandler] = None


def get_prompt_tool_handler() -> PromptBasedToolHandler:
    """Get the singleton prompt tool handler instance."""
    global _handler
    if _handler is None:
        _handler = PromptBasedToolHandler()
    return _handler
