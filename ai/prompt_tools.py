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

    # Pattern to find tool_call opening tags
    TOOL_CALL_OPENER = re.compile(r'<tool_call>', re.IGNORECASE)

    # Pattern to find tool_call closing tags
    TOOL_CALL_CLOSER = re.compile(r'</tool_call>', re.IGNORECASE)

    # Alternative opening patterns
    ALT_OPENERS = [
        re.compile(r'```tool_call\s*\n', re.IGNORECASE),
        re.compile(r'\[TOOL_CALL\]', re.IGNORECASE),
    ]

    # Legacy pattern for backward compatibility (simple cases)
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

## CRITICAL: How to Use Tools

**YOU MUST USE THE EXACT FORMAT BELOW TO CALL TOOLS. DO NOT DESCRIBE OR NARRATE TOOL USAGE.**

When you need to use a tool, output ONLY this format:
<tool_call>{{"name": "tool_name", "arguments": {{"arg1": "value1"}}}}</tool_call>

**WRONG (DO NOT DO THIS):**
- "I'll switch to the llama model now" (just describing, not calling)
- "Let me search for that..." (narrating without tool call)
- "*switches to a different model*" (roleplay, not actual call)

**CORRECT:**
<tool_call>{{"name": "switch_model", "arguments": {{"model_name": "llama-3.3-70b"}}}}</tool_call>

Rules:
1. **ALWAYS** output the <tool_call> tag - never just describe what you would do
2. Output ONLY the tool_call tag when using a tool - no extra text before it
3. Wait for the [Tool Result] before continuing your response
4. You can call multiple tools if needed

Example:
User: Switch to a different model
Assistant: <tool_call>{{"name": "switch_model", "arguments": {{"model_name": "gpt-4o"}}}}</tool_call>
[Tool Result: Successfully switched to gpt-4o]
Assistant: Done! I've switched to GPT-4o.
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

        Uses json.JSONDecoder.raw_decode to properly handle nested JSON objects,
        which the simple regex approach fails on (nested braces break .*? patterns).

        Also handles malformed tags where models forget closing tags, like:
        <tool_call>{json1}<tool_call>{json2}</tool_call>

        Args:
            content: Model's response text

        Returns:
            List of parsed tool calls
        """
        tool_calls = []

        # First, try the robust JSON parsing approach
        tool_calls = self._parse_with_json_decoder(content)

        # If that found nothing, fall back to legacy regex patterns
        if not tool_calls:
            tool_calls = self._parse_with_legacy_patterns(content)

        return tool_calls

    def _parse_with_json_decoder(self, content: str) -> List[ParsedToolCall]:
        """
        Parse tool calls using json.JSONDecoder.raw_decode for proper nested JSON handling.

        This method:
        1. Finds all <tool_call> opening tags
        2. For each tag, uses raw_decode to parse exactly one complete JSON object
        3. Handles malformed tags (missing closers) gracefully
        """
        tool_calls = []
        decoder = json.JSONDecoder()

        # Find all positions where <tool_call> appears
        for match in self.TOOL_CALL_OPENER.finditer(content):
            start_pos = match.end()  # Position right after <tool_call>

            # Skip any whitespace
            while start_pos < len(content) and content[start_pos].isspace():
                start_pos += 1

            if start_pos >= len(content) or content[start_pos] != '{':
                continue  # No JSON object found after tag

            try:
                # raw_decode parses exactly one JSON value and returns (value, end_position)
                # end_position is the ABSOLUTE index where parsing stopped
                # This correctly handles nested objects like {"args": {"nested": "value"}}
                data, end_pos = decoder.raw_decode(content, start_pos)

                if isinstance(data, dict):
                    name = data.get("name")
                    arguments = data.get("arguments", {})

                    if name:
                        raw_text = content[start_pos:end_pos]
                        tool_calls.append(ParsedToolCall(
                            name=name,
                            arguments=arguments,
                            raw_text=raw_text
                        ))

                        logger.debug(
                            "tool_call_parsed_with_decoder",
                            tool_name=name,
                            argument_count=len(arguments)
                        )

            except json.JSONDecodeError as e:
                logger.warning(
                    "tool_call_json_decode_failed",
                    error=str(e),
                    position=start_pos,
                    context=content[start_pos:start_pos + 50]
                )
                continue

        return tool_calls

    def _parse_with_legacy_patterns(self, content: str) -> List[ParsedToolCall]:
        """
        Fall back to legacy regex patterns for simple cases.
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
                        "tool_call_parsed_legacy",
                        tool_name=name,
                        argument_count=len(arguments)
                    )

            except json.JSONDecodeError as e:
                logger.warning(
                    "tool_call_parse_failed_legacy",
                    error=str(e),
                    raw_text=match[:100]
                )
                continue

        return tool_calls

    def has_tool_call(self, content: str) -> bool:
        """Check if content contains a tool call."""
        # Check for <tool_call> opener followed by JSON
        if self.TOOL_CALL_OPENER.search(content):
            return True
        # Check legacy patterns
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

        Uses JSON decoder to find complete tool call boundaries,
        handling nested JSON objects correctly.

        Args:
            content: Model response with potential tool calls

        Returns:
            Content with tool call tags removed
        """
        # Build list of (start, end) ranges to remove
        ranges_to_remove = []
        decoder = json.JSONDecoder()

        # Find all <tool_call> tags and their complete JSON
        for match in self.TOOL_CALL_OPENER.finditer(content):
            tag_start = match.start()
            json_start = match.end()

            # Skip whitespace
            while json_start < len(content) and content[json_start].isspace():
                json_start += 1

            if json_start >= len(content) or content[json_start] != '{':
                # No JSON, just remove the tag itself
                ranges_to_remove.append((tag_start, match.end()))
                continue

            try:
                # Parse the complete JSON object
                # end_pos is the ABSOLUTE index where parsing stopped
                _, json_end = decoder.raw_decode(content, json_start)

                # Check for closing </tool_call> tag after JSON
                remaining = content[json_end:json_end + 20]
                close_match = self.TOOL_CALL_CLOSER.match(remaining.lstrip())
                if close_match:
                    # Include the closing tag in removal
                    whitespace_len = len(remaining) - len(remaining.lstrip())
                    json_end += whitespace_len + close_match.end()

                ranges_to_remove.append((tag_start, json_end))

            except json.JSONDecodeError:
                # If JSON parse fails, just remove the opening tag
                ranges_to_remove.append((tag_start, match.end()))

        # Also remove any orphaned </tool_call> tags
        for match in self.TOOL_CALL_CLOSER.finditer(content):
            # Check if this closer is already covered by a range
            is_covered = any(start <= match.start() < end for start, end in ranges_to_remove)
            if not is_covered:
                ranges_to_remove.append((match.start(), match.end()))

        # Remove legacy patterns too
        for pattern in self.ALT_PATTERNS:
            for match in pattern.finditer(content):
                ranges_to_remove.append((match.start(), match.end()))

        # Sort ranges and merge overlapping ones
        ranges_to_remove.sort()
        merged = []
        for start, end in ranges_to_remove:
            if merged and start <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))

        # Build clean content by excluding the ranges
        clean_parts = []
        prev_end = 0
        for start, end in merged:
            if start > prev_end:
                clean_parts.append(content[prev_end:start])
            prev_end = end
        if prev_end < len(content):
            clean_parts.append(content[prev_end:])

        clean = ''.join(clean_parts)

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
