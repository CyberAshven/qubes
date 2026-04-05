"""
Google Provider Implementation

Supports Gemini 1.5, 2.0, and 2.5 models.
Matches documentation in docs/09_AI_Integration_Tool_Calling.md Section 6.1
"""

from typing import List, Dict, Any, Optional, AsyncIterator
import json
import base64
import re

from ai.providers.base import AIModelInterface, ModelResponse
from ai.retry_decorators import google_retry
from ai.circuit_breakers import with_circuit_breaker
from core.exceptions import AIError, ModelAPIError, ModelRateLimitError, ModelNotAvailableError
from utils.logging import get_logger
from monitoring.metrics import MetricsRecorder

logger = get_logger(__name__)


class GoogleModel(AIModelInterface):
    """Google Gemini model provider"""

    # Pricing per 1M tokens (as of 2025)
    PRICING = {
        "gemini-2.5-pro": {"input": 1.25, "output": 5.00},
        "gemini-2.5-flash": {"input": 0.075, "output": 0.30},
        "gemini-2.5-flash-lite": {"input": 0.0375, "output": 0.15},
        "gemini-2.0-flash": {"input": 0.075, "output": 0.30},
        "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
    }

    CONTEXT_WINDOWS = {
        "gemini-2.5-pro": 2000000,
        "gemini-2.5-flash": 1000000,
        "gemini-2.5-flash-lite": 1000000,
        "gemini-2.0-flash": 1000000,
        "gemini-1.5-pro": 2000000,
        "gemini-3.1-pro-preview": 2000000,
        "gemini-3-flash-preview": 1000000,
    }

    # Gemini 3 models require thoughtSignature for native tool calling, but the SDK
    # doesn't fully support it yet. Use prompt-based tools instead for reliability.
    # Gemini 3 models use prompt-based tools because native tool calling requires
    # thoughtSignature which the SDK doesn't fully support yet
    PROMPT_BASED_TOOL_MODELS = {
        "gemini-3.1-pro-preview",
        "gemini-3-flash-preview",
        "gemini-3-pro-image-preview",
    }

    # Patterns to detect Gemini 3's internal thinking/planning output
    # These should be stripped from the response before displaying to users
    THINKING_PATTERNS = [
        # Planning markers
        re.compile(r'^\s*my plan:\s*\n', re.IGNORECASE | re.MULTILINE),
        re.compile(r'\*Self-Correction[^*]*\*:', re.IGNORECASE),
        re.compile(r'\*Refining the response\*:', re.IGNORECASE),
        re.compile(r"\*Let'?s do this\.?\*", re.IGNORECASE),
        re.compile(r'\*thinking\*', re.IGNORECASE),
        re.compile(r'\*internal monologue\*', re.IGNORECASE),
    ]

    def _strip_thinking_content(self, content: str) -> str:
        """
        Strip Gemini 3's internal thinking/planning from response.

        Gemini 3 sometimes outputs its reasoning process before the actual response.
        This includes planning steps, self-corrections, and markers like "*Let's do this.*"
        """
        if not content:
            return content

        # Look for common end-of-thinking markers and take content after them
        end_markers = [
            "*Let's do this.*",
            "*Let's do this*",
            "*Here's my response:*",
            "*Here's my response*",
            "*Response:*",
            "*Responding now:*",
            "*Final response:*",
        ]

        for marker in end_markers:
            marker_lower = marker.lower()
            content_lower = content.lower()
            if marker_lower in content_lower:
                idx = content_lower.find(marker_lower)
                # Take content after the marker
                content = content[idx + len(marker):].strip()
                logger.debug("gemini_thinking_stripped", marker=marker)
                break

        # Also check for numbered plan at the start (e.g., "my plan:\n1. ...")
        # If found, try to find where the actual response starts
        if content.lstrip().lower().startswith('my plan:') or content.lstrip().lower().startswith('plan:'):
            # Look for a clear transition to the actual response
            # Usually after the planning section, there's a blank line or the actual response starts
            lines = content.split('\n')
            in_planning = True
            response_start = 0

            for i, line in enumerate(lines):
                stripped = line.strip()
                # Planning indicators
                if stripped.lower().startswith(('my plan:', 'plan:', '*self-correction', '*refining', '*let')):
                    in_planning = True
                    continue
                if re.match(r'^\d+\.\s+\*\*', stripped):  # Numbered list with bold (planning)
                    in_planning = True
                    continue
                if stripped.startswith('- ') and in_planning:  # Bullet points in planning
                    continue
                if stripped.startswith('*') and stripped.endswith('*'):  # Italic markers
                    continue

                # If we hit a substantial line that doesn't look like planning, that's the response
                if stripped and not stripped.startswith(('*', '-', '#')) and len(stripped) > 20:
                    # Check if this looks like actual response (not a planning note)
                    if not any(word in stripped.lower() for word in ['should', 'will', 'need to', 'i\'ll', 'i will']):
                        response_start = i
                        break
                    # If it starts with dialog/response words, it's the response
                    if any(stripped.lower().startswith(word) for word in ['whoa', 'okay', 'hey', 'so,', 'oh', 'hmm', 'well']):
                        response_start = i
                        break

            if response_start > 0:
                content = '\n'.join(lines[response_start:]).strip()
                logger.debug("gemini_planning_stripped", lines_removed=response_start)

        return content

    def _convert_old_google_schema_to_json_schema(self, old_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert old Google SDK schema format to JSON Schema format

        Old format uses 'type_' with uppercase values ('OBJECT', 'STRING', etc.)
        New format uses 'type' with lowercase values ('object', 'string', etc.)
        """
        if not isinstance(old_schema, dict):
            return old_schema

        new_schema = {}

        # Convert type_  → type with lowercase
        if 'type_' in old_schema:
            type_map = {
                'OBJECT': 'object',
                'STRING': 'string',
                'INTEGER': 'integer',
                'NUMBER': 'number',
                'BOOLEAN': 'boolean',
                'ARRAY': 'array'
            }
            new_schema['type'] = type_map.get(old_schema['type_'], 'string')

        # Recursively convert properties
        if 'properties' in old_schema:
            new_schema['properties'] = {
                k: self._convert_old_google_schema_to_json_schema(v)
                for k, v in old_schema['properties'].items()
            }

        # Recursively convert items (for arrays)
        if 'items' in old_schema:
            new_schema['items'] = self._convert_old_google_schema_to_json_schema(old_schema['items'])

        # Copy other fields as-is
        for key in ['description', 'required', 'enum', 'default']:
            if key in old_schema:
                new_schema[key] = old_schema[key]

        return new_schema

    @google_retry(max_attempts=3)
    async def generate(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> ModelResponse:
        """Generate response using Google Gemini API with retry and circuit breaker"""
        try:
            from google import genai
            from google.genai import types

            # Check if this model needs prompt-based tools (Gemini 3 has SDK issues with thoughtSignature)
            using_prompt_tools = False
            prompt_tool_handler = None
            if tools and self.model_name in self.PROMPT_BASED_TOOL_MODELS:
                from ai.prompt_tools import get_prompt_tool_handler
                prompt_tool_handler = get_prompt_tool_handler()
                messages = prompt_tool_handler.inject_tools_into_messages(
                    messages, tools, model_name=self.model_name
                )
                tools = None  # Don't pass native tools
                using_prompt_tools = True
                logger.info(
                    "google_using_prompt_tools",
                    model=self.model_name,
                    reason="Gemini 3 thoughtSignature SDK limitation"
                )

            # Initialize client with API key
            client = genai.Client(api_key=self.api_key)

            # Convert messages to Gemini contents format
            # New SDK uses simpler contents format
            contents = []
            system_instruction = None

            for msg in messages:
                if msg["role"] == "system":
                    system_instruction = msg["content"]
                elif msg["role"] == "user":
                    contents.append(types.Content(role="user", parts=[types.Part(text=msg["content"])]))
                elif msg["role"] == "assistant":
                    # Check if this model uses prompt-based tools
                    is_prompt_tool_model = self.model_name in self.PROMPT_BASED_TOOL_MODELS

                    # Handle tool calls if present (only for native tool models)
                    if "tool_calls" in msg and msg["tool_calls"] and not is_prompt_tool_model:
                        # Gemini expects function calls in a specific format
                        parts = []
                        for tc in msg["tool_calls"]:
                            args_dict = json.loads(tc["function"]["arguments"]) if isinstance(tc["function"]["arguments"], str) else tc["function"]["arguments"]

                            # Build Part kwargs - thoughtSignature goes on Part, not FunctionCall
                            part_kwargs = {
                                "function_call": types.FunctionCall(
                                    name=tc["function"]["name"],
                                    args=args_dict
                                )
                            }

                            # Include thoughtSignature if present (required by Gemini 3 models)
                            # It's stored as base64 string, need to decode back to bytes
                            thought_sig = tc.get("thought_signature") or tc.get("function", {}).get("thought_signature")
                            if thought_sig:
                                try:
                                    part_kwargs["thoughtSignature"] = base64.b64decode(thought_sig)
                                except Exception:
                                    # If decoding fails, try using as-is (might be raw bytes)
                                    if isinstance(thought_sig, bytes):
                                        part_kwargs["thoughtSignature"] = thought_sig

                            parts.append(types.Part(**part_kwargs))
                        contents.append(types.Content(role="model", parts=parts))
                    else:
                        # For prompt-based tools or no tool calls, just use text content
                        contents.append(types.Content(role="model", parts=[types.Part(text=msg.get("content", ""))]))
                elif msg["role"] == "tool":
                    # Convert tool results to Gemini format
                    # Check if this model uses prompt-based tools (even if tools not passed on this turn)
                    is_prompt_tool_model = self.model_name in self.PROMPT_BASED_TOOL_MODELS
                    if using_prompt_tools or is_prompt_tool_model:
                        # For prompt-based tools, format as text (no native function_response)
                        tool_name = msg.get("name", "tool")
                        tool_result = msg.get("content", "")
                        formatted_result = f"[Tool Result: {tool_name}]\n{tool_result}"
                        contents.append(types.Content(role="user", parts=[types.Part(text=formatted_result)]))
                    else:
                        # Native tools: use function_response
                        try:
                            result_data = json.loads(msg["content"]) if isinstance(msg["content"], str) else msg["content"]
                            contents.append(types.Content(
                                role="user",
                                parts=[types.Part(
                                    function_response=types.FunctionResponse(
                                        name=msg["name"],
                                        response=result_data
                                    )
                                )]
                            ))
                        except json.JSONDecodeError:
                            # Fallback: treat as plain text
                            contents.append(types.Content(role="user", parts=[types.Part(text=msg["content"])]))

            # Build generation config
            config = types.GenerateContentConfig(
                temperature=temperature,
                system_instruction=system_instruction if system_instruction else None
            )

            if max_tokens:
                config.max_output_tokens = max_tokens

            # Convert tools to new Google SDK format if provided
            if tools:
                google_tools = []
                for tool in tools:
                    if isinstance(tool, dict):
                        if 'function' in tool:
                            # OpenAI format: {type: 'function', function: {name, description, parameters}}
                            func = tool['function']
                            google_tools.append(types.Tool(
                                function_declarations=[types.FunctionDeclaration(
                                    name=func['name'],
                                    description=func.get('description', ''),
                                    parameters=func.get('parameters')
                                )]
                            ))
                        elif 'function_declarations' in tool:
                            # Old Google format: {function_declarations: [{name, description, parameters}]}
                            # Parameters use OLD format with 'type_' → need to convert to new format with 'type'
                            declarations = []
                            for func_decl in tool['function_declarations']:
                                # Convert old Google schema format to JSON Schema format
                                params = func_decl.get('parameters')
                                if params:
                                    params = self._convert_old_google_schema_to_json_schema(params)

                                declarations.append(types.FunctionDeclaration(
                                    name=func_decl['name'],
                                    description=func_decl.get('description', ''),
                                    parameters=params
                                ))
                            google_tools.append(types.Tool(function_declarations=declarations))
                        else:
                            # Unknown dict format - try to pass through as-is
                            google_tools.append(tool)
                    else:
                        # Already a types.Tool object or other - pass through
                        google_tools.append(tool)
                config.tools = google_tools

            # Record API call start
            MetricsRecorder.record_ai_api_call("google", self.model_name, "started")

            # Make API call using new SDK with timeout
            # Wrap synchronous call in asyncio with 120 second timeout
            import asyncio

            def _sync_generate():
                return client.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                    config=config
                )

            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(_sync_generate),
                    timeout=120.0  # 2 minute timeout
                )
            except asyncio.TimeoutError:
                raise ModelAPIError(
                    f"Google API request timed out after 120 seconds. The model may be overloaded. Try again or use a different model.",
                    context={"model": self.model_name, "error_type": "timeout"}
                )

            # Record success
            MetricsRecorder.record_ai_api_call("google", self.model_name, "success")

            # Parse response
            content_text = response.text if response.text else ""

            # Extract tool calls if present
            tool_calls = None
            if response.candidates and len(response.candidates) > 0:
                candidate = response.candidates[0]
                if candidate.content and candidate.content.parts:
                    tool_calls = []
                    for idx, part in enumerate(candidate.content.parts):
                        if part.function_call:
                            tool_call = {
                                "id": f"call_{hash(part.function_call.name)}",
                                "name": part.function_call.name,
                                "parameters": dict(part.function_call.args) if part.function_call.args else {}
                            }
                            # Extract thoughtSignature from Part (not FunctionCall!) if present
                            # This is required by Gemini 3 models for multi-turn tool use
                            # thoughtSignature is bytes, so we base64 encode for JSON storage
                            has_thought_sig = hasattr(part, 'thoughtSignature') and part.thoughtSignature
                            logger.info(
                                "google_function_call_parsed",
                                model=self.model_name,
                                part_index=idx,
                                function_name=part.function_call.name,
                                has_thoughtSignature=has_thought_sig,
                                part_attrs=dir(part) if not has_thought_sig else None
                            )
                            if has_thought_sig:
                                tool_call["thought_signature"] = base64.b64encode(part.thoughtSignature).decode('utf-8')
                                logger.info("google_thought_signature_captured", function=part.function_call.name)
                            tool_calls.append(tool_call)
                    if not tool_calls:
                        tool_calls = None

            # Extract usage data
            usage = None
            if response.usage_metadata:
                prompt_tokens = response.usage_metadata.prompt_token_count or 0
                completion_tokens = response.usage_metadata.candidates_token_count or 0
                total_tokens = response.usage_metadata.total_token_count or (prompt_tokens + completion_tokens)

                usage = {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens
                }
                cost = self.estimate_cost(prompt_tokens, completion_tokens)
                MetricsRecorder.record_ai_cost(cost, "google", self.model_name)

            # If using prompt-based tools, parse tool calls from content
            if using_prompt_tools and prompt_tool_handler and content_text:
                parsed_calls = prompt_tool_handler.parse_tool_calls(content_text)
                if parsed_calls:
                    tool_calls = [
                        {
                            "id": f"prompt_call_{i}",
                            "name": tc.name,
                            "parameters": tc.arguments
                        }
                        for i, tc in enumerate(parsed_calls)
                    ]
                    # Clean tool call markup from content
                    content_text = prompt_tool_handler.extract_content_without_tool_calls(content_text)
                    logger.info(
                        "google_prompt_tools_parsed",
                        model=self.model_name,
                        tool_count=len(tool_calls),
                        tools=[tc["name"] for tc in tool_calls]
                    )

            # Strip Gemini 3's thinking/planning output from response
            if self.model_name in self.PROMPT_BASED_TOOL_MODELS and content_text:
                original_len = len(content_text)
                content_text = self._strip_thinking_content(content_text)
                if len(content_text) < original_len:
                    logger.info(
                        "gemini_thinking_content_stripped",
                        model=self.model_name,
                        original_length=original_len,
                        cleaned_length=len(content_text)
                    )

            logger.debug(
                "google_generation_complete",
                model=self.model_name,
                input_tokens=usage.get("prompt_tokens") if usage else None,
                output_tokens=usage.get("completion_tokens") if usage else None,
                tool_calls=len(tool_calls) if tool_calls else 0
            )

            return ModelResponse(
                content=content_text,
                tool_calls=tool_calls,
                model=self.model_name,
                usage=usage,
                finish_reason=response.candidates[0].finish_reason if response.candidates else None,
                raw_response=response
            )

        except Exception as e:
            MetricsRecorder.record_ai_api_call("google", self.model_name, "error")
            logger.error("google_generation_failed", model=self.model_name, exc_info=True)

            # Classify error with helpful messages
            error_msg = str(e).lower()
            error_str = str(e)

            if "quota" in error_msg or "rate" in error_msg or "resource_exhausted" in error_msg:
                raise ModelRateLimitError(
                    f"Google rate limit exceeded. Try again in a few minutes or switch to a different model. Original error: {error_str}",
                    context={"model": self.model_name, "error_type": "rate_limit"},
                    cause=e
                )
            elif "api key" in error_msg or "unauthorized" in error_msg or "permission" in error_msg or "403" in error_msg:
                raise ModelNotAvailableError(
                    f"Google API key is invalid or doesn't have permission for model '{self.model_name}'. "
                    f"Check your API key in Settings > API Keys. Original error: {error_str}",
                    context={"model": self.model_name, "error_type": "auth_failed"},
                    cause=e
                )
            elif "not found" in error_msg or "404" in error_msg or "invalid model" in error_msg or "does not exist" in error_msg:
                raise ModelNotAvailableError(
                    f"Model '{self.model_name}' not found in Google's API. "
                    f"This model may have been renamed or deprecated. Try 'gemini-2.5-pro' or 'gemini-2.5-flash'. "
                    f"Original error: {error_str}",
                    context={"model": self.model_name, "error_type": "model_not_found"},
                    cause=e
                )
            elif "safety" in error_msg or "blocked" in error_msg or "harm" in error_msg:
                raise ModelAPIError(
                    f"Content was blocked by Google's safety filters. Try rephrasing your message. Original error: {error_str}",
                    context={"model": self.model_name, "error_type": "content_blocked"},
                    cause=e
                )
            elif "timeout" in error_msg or "deadline" in error_msg:
                raise ModelAPIError(
                    f"Request timed out. The model may be overloaded. Try again or use a faster model like 'gemini-2.5-flash'. "
                    f"Original error: {error_str}",
                    context={"model": self.model_name, "error_type": "timeout"},
                    cause=e
                )
            elif "invalid" in error_msg and "argument" in error_msg:
                raise ModelAPIError(
                    f"Invalid request parameters for model '{self.model_name}'. "
                    f"This might be a tool format issue or unsupported feature. Original error: {error_str}",
                    context={"model": self.model_name, "error_type": "invalid_request"},
                    cause=e
                )
            else:
                raise ModelAPIError(
                    f"Google API error with model '{self.model_name}': {error_str}",
                    context={"model": self.model_name, "error_type": "unknown"},
                    cause=e
                )

    async def stream_generate(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream response using Google Gemini API"""
        try:
            from google import genai
            from google.genai import types

            # Initialize client with API key
            client = genai.Client(api_key=self.api_key)

            # Convert messages to Gemini contents format
            contents = []
            system_instruction = None

            for msg in messages:
                if msg["role"] == "system":
                    system_instruction = msg["content"]
                elif msg["role"] == "user":
                    contents.append(types.Content(role="user", parts=[types.Part(text=msg["content"])]))
                elif msg["role"] == "assistant":
                    contents.append(types.Content(role="model", parts=[types.Part(text=msg["content"])]))

            # Build generation config
            config = types.GenerateContentConfig(
                temperature=temperature,
                system_instruction=system_instruction if system_instruction else None
            )

            if max_tokens:
                config.max_output_tokens = max_tokens

            MetricsRecorder.record_ai_api_call("google", self.model_name, "started")

            # Stream response using new SDK
            response_stream = client.models.generate_content_stream(
                model=self.model_name,
                contents=contents,
                config=config
            )

            for chunk in response_stream:
                if chunk.text:
                    yield chunk.text

            MetricsRecorder.record_ai_api_call("google", self.model_name, "success")

        except Exception as e:
            MetricsRecorder.record_ai_api_call("google", self.model_name, "error")
            logger.error("google_streaming_failed", model=self.model_name, exc_info=True)
            raise ModelAPIError(f"Google streaming error: {str(e)}", cause=e)

    def parse_tool_calls(self, response: Any) -> List[Dict[str, Any]]:
        """Parse tool calls from Google response"""
        if not hasattr(response, 'candidates') or not response.candidates:
            return []

        tool_calls = []
        candidate = response.candidates[0]

        if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
            for part in candidate.content.parts:
                if hasattr(part, 'function_call'):
                    tool_calls.append({
                        "id": f"call_{hash(part.function_call.name)}",
                        "name": part.function_call.name,
                        "parameters": dict(part.function_call.args)
                    })

        return tool_calls

    def get_context_window(self) -> int:
        """Get context window size for model"""
        return self.CONTEXT_WINDOWS.get(self.model_name, 1000000)

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate API call cost in USD"""
        pricing = self.PRICING.get(self.model_name, {"input": 0, "output": 0})
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return input_cost + output_cost
