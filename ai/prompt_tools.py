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

    # Kimi K2 special token patterns (uses <|...|> format)
    KIMI_TOOL_SECTION = re.compile(r'<\|tool_calls_section_begin\|>(.*?)<\|tool_calls_section_end\|>', re.DOTALL | re.IGNORECASE)
    KIMI_TOOL_CALL = re.compile(r'<\|tool_call_begin\|>\s*functions\.(\w+):\d+\s*<\|tool_call_argument_begin\|>\s*(\{.*?\})\s*<\|tool_call_end\|>', re.DOTALL | re.IGNORECASE)

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

    # Pattern to detect bare JSON tool calls (no tags)
    # Used as last resort for models that output raw JSON like DeepSeek R1
    # Matches JSON objects that have both "name" and "arguments" keys
    BARE_JSON_TOOL_PATTERN = re.compile(
        r'^\s*(\{"name":\s*"[^"]+",\s*"arguments":\s*\{.*?\}\})\s*$',
        re.MULTILINE | re.DOTALL
    )

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

    # Hermes 3 specific template - uses <tools> XML format as per NousResearch spec
    # https://huggingface.co/NousResearch/Hermes-3-Llama-3.1-405B
    HERMES_TOOL_INSTRUCTION_TEMPLATE = """You are a function calling AI model. You are provided with function signatures within <tools></tools> XML tags. You may call one or more functions to assist with the user query. Don't make assumptions about what values to plug into functions. Here are the available tools:
<tools>
{tool_json}
</tools>

For each function call return a json object with function name and arguments within <tool_call></tool_call> XML tags as follows:
<tool_call>
{{"name": "<function-name>", "arguments": <args-dict>}}
</tool_call>

IMPORTANT RULES:
1. When you need to use a tool, output the <tool_call> tag immediately - don't just describe what you would do
2. Wait for the tool result before continuing your response
3. You can call multiple tools if needed by outputting multiple <tool_call> blocks
"""

    # Models that should use the Hermes-style <tools> XML format
    HERMES_STYLE_MODELS = {
        "hermes-3-llama-3.1-405b",
        "hermes-3-llama-3.1-70b",
        "hermes-3-llama-3.1-8b",
    }

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
        tools: List[Dict[str, Any]],
        model_name: str = None
    ) -> List[Dict[str, str]]:
        """
        Add tool instructions to the system prompt.

        Args:
            messages: Original conversation messages
            tools: Tool definitions to inject
            model_name: Optional model name for model-specific formatting

        Returns:
            Modified messages with tool instructions in system prompt
        """
        if not tools:
            return messages

        # Check if this model needs Hermes-style formatting
        if model_name and model_name in self.HERMES_STYLE_MODELS:
            # Use Hermes <tools> XML format with raw JSON tool definitions
            tool_json = json.dumps(tools, indent=2)
            tool_instructions = self.HERMES_TOOL_INSTRUCTION_TEMPLATE.format(
                tool_json=tool_json
            )
            logger.debug(
                "using_hermes_tool_format",
                model=model_name,
                tool_count=len(tools)
            )
        else:
            # Use default markdown format
            tool_descriptions = self.format_tools_for_prompt(tools)
            tool_instructions = self.TOOL_INSTRUCTION_TEMPLATE.format(
                tool_descriptions=tool_descriptions
            )

        # Create a copy to avoid modifying original
        new_messages = []
        system_found = False
        pending_tool_results = []  # Batch consecutive tool results

        def flush_tool_results():
            """Combine pending tool results into a single user message"""
            nonlocal pending_tool_results
            if pending_tool_results:
                # Combine all tool results into one message to avoid multiple consecutive user messages
                combined = "\n\n".join(pending_tool_results)
                # Add explicit instruction to respond - some models (like Kimi K2) need this nudge
                combined += "\n\nPlease analyze these tool results and provide your response to the user."
                new_messages.append({
                    "role": "user",
                    "content": combined
                })
                logger.debug(
                    "tool_results_batched",
                    count=len(pending_tool_results)
                )
                pending_tool_results = []

        for msg in messages:
            role = msg.get("role")
            if role == "system" and not system_found:
                flush_tool_results()  # Flush any pending results
                # Append tool instructions to existing system prompt
                new_content = msg.get("content", "") + "\n\n" + tool_instructions
                new_messages.append({"role": "system", "content": new_content})
                system_found = True
            elif role == "tool":
                # Collect tool results to batch them into a single user message
                # Multiple consecutive user messages can confuse some models
                tool_name = msg.get("name", "unknown")
                tool_content = msg.get("content", "")
                pending_tool_results.append(f"[Tool Result for {tool_name}]: {tool_content}")
            elif role == "assistant" and msg.get("tool_calls"):
                flush_tool_results()  # Flush any pending results before assistant message
                # Strip tool_calls field from assistant messages - models without native
                # tool support don't understand this field and it can cause empty responses
                content = msg.get("content", "")
                # If content is empty (model only output tool calls), add placeholder
                # Empty assistant messages can confuse some models
                if not content.strip():
                    tool_names = [tc.get("function", {}).get("name") or tc.get("name", "tool")
                                  for tc in msg.get("tool_calls", [])]
                    content = f"[Using tools: {', '.join(tool_names)}]"
                clean_msg = {"role": "assistant", "content": content}
                new_messages.append(clean_msg)
                logger.debug(
                    "assistant_tool_calls_stripped",
                    original_tool_count=len(msg.get("tool_calls", [])),
                    content_was_empty=not msg.get("content", "").strip()
                )
            else:
                flush_tool_results()  # Flush any pending results before other messages
                new_messages.append(msg.copy())

        # Flush any remaining tool results at the end
        flush_tool_results()

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

        # First, try Kimi K2 special token format (<|tool_call_begin|>...)
        tool_calls = self._parse_kimi_k2_tool_calls(content)

        # Try the robust JSON parsing approach with <tool_call> tags
        if not tool_calls:
            tool_calls = self._parse_with_json_decoder(content)

        # If that found nothing, fall back to legacy regex patterns
        if not tool_calls:
            tool_calls = self._parse_with_legacy_patterns(content)

        # Last resort: try bare JSON (for models like DeepSeek R1 that output raw JSON)
        if not tool_calls:
            tool_calls = self._parse_bare_json_tool_calls(content)

        return tool_calls

    def _parse_kimi_k2_tool_calls(self, content: str) -> List[ParsedToolCall]:
        """
        Parse Kimi K2's special token format for tool calls.

        Kimi K2 uses a unique format:
        <|tool_calls_section_begin|>
        <|tool_call_begin|> functions.browse_url:0 <|tool_call_argument_begin|> {"url": "..."} <|tool_call_end|>
        <|tool_calls_section_end|>

        Returns:
            List of parsed tool calls
        """
        tool_calls = []

        # Check if this looks like Kimi K2 format
        if '<|tool_call_begin|>' not in content:
            return tool_calls

        # Find tool calls within the section (or in the whole content if section tags are missing)
        section_match = self.KIMI_TOOL_SECTION.search(content)
        search_content = section_match.group(1) if section_match else content

        # Extract individual tool calls
        for match in self.KIMI_TOOL_CALL.finditer(search_content):
            function_name = match.group(1)  # e.g., "browse_url"
            args_json = match.group(2)      # e.g., '{"url": "..."}'

            try:
                arguments = json.loads(args_json)
                tool_calls.append(ParsedToolCall(
                    name=function_name,
                    arguments=arguments,
                    raw_text=match.group(0)
                ))
                logger.info(
                    "kimi_k2_tool_call_parsed",
                    function=function_name,
                    arguments=arguments
                )
            except json.JSONDecodeError as e:
                logger.warning(
                    "kimi_k2_tool_call_json_error",
                    function=function_name,
                    args_json=args_json,
                    error=str(e)
                )

        if tool_calls:
            logger.info(
                "kimi_k2_tool_calls_found",
                count=len(tool_calls),
                tool_names=[tc.name for tc in tool_calls]
            )

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

    def _parse_bare_json_tool_calls(self, content: str) -> List[ParsedToolCall]:
        """
        Parse bare JSON tool calls without tags.

        Last resort for models like DeepSeek R1 that output raw JSON like:
        {"name": "send_bch", "arguments": {"to_qube_name": "Paradox", "amount_sats": 20000}}

        This is more permissive but only matches JSON with both "name" and "arguments" keys.
        """
        tool_calls = []

        # Try to find JSON objects that look like tool calls
        # First try the regex pattern
        matches = self.BARE_JSON_TOOL_PATTERN.findall(content)

        # If no matches, try a more aggressive approach: find any JSON object in the content
        if not matches:
            # Look for content that's primarily JSON (stripped content starts with { and ends with })
            stripped = content.strip()
            if stripped.startswith('{') and stripped.endswith('}'):
                matches = [stripped]

        for match in matches:
            try:
                data = json.loads(match)

                # Must have both "name" and "arguments" to be considered a tool call
                if isinstance(data, dict) and "name" in data and "arguments" in data:
                    name = data["name"]
                    arguments = data.get("arguments", {})

                    tool_calls.append(ParsedToolCall(
                        name=name,
                        arguments=arguments if isinstance(arguments, dict) else {},
                        raw_text=match
                    ))

                    logger.info(
                        "tool_call_parsed_bare_json",
                        tool_name=name,
                        argument_count=len(arguments) if isinstance(arguments, dict) else 0,
                        note="Model output bare JSON without tags"
                    )

            except json.JSONDecodeError as e:
                logger.debug(
                    "bare_json_parse_failed",
                    error=str(e),
                    raw_text=match[:100] if len(match) > 100 else match
                )
                continue

        return tool_calls

    def has_tool_call(self, content: str) -> bool:
        """Check if content contains a tool call."""
        # Check for Kimi K2 special token format
        if '<|tool_call_begin|>' in content:
            return True
        # Check for <tool_call> opener followed by JSON
        if self.TOOL_CALL_OPENER.search(content):
            return True
        # Check legacy patterns
        if bool(self.TOOL_CALL_PATTERN.search(content)) or \
               any(p.search(content) for p in self.ALT_PATTERNS):
            return True
        # Check for bare JSON tool calls
        if self.BARE_JSON_TOOL_PATTERN.search(content):
            return True
        # Last check: content is pure JSON with name and arguments
        stripped = content.strip()
        if stripped.startswith('{"name":') and stripped.endswith('}'):
            return True
        return False

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

        # Remove Kimi K2 special token tool calls
        for match in self.KIMI_TOOL_SECTION.finditer(content):
            ranges_to_remove.append((match.start(), match.end()))
        # Also handle case where section tags are missing but tool calls are present
        for match in self.KIMI_TOOL_CALL.finditer(content):
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
