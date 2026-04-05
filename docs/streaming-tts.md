# Streaming TTS & Voice Conversation Mode

## Summary

Two connected features that transform how users interact with qubes:

1. **Streaming TTS** — Qubes speak sentence-by-sentence as the LLM generates text, instead of waiting for the full response. Works in both text chat and voice mode.
2. **Stream Mode** — A continuous voice conversation where the user speaks, the qube responds with streaming audio, and the user can interrupt naturally. The mic stays live until the user exits.

Both features use the existing AI providers, TTS providers, and block system. No new models or dependencies required.

---

## The Problem

Current flow (traced from actual codebase):

```
ChatInterface.handleSend()
  → invoke('send_message', {userId, qubeId, message, password})
    → sidecar_execute_with_retry("send-message", ...)
      → GUIBridge.send_message()
        → qube.process_message() → reasoner.process_input()
          → [TOOL LOOP: model.generate() → execute tools → loop]
          → Final iteration: model.generate() → response.content
        ← Returns complete text
      ← Returns {success, response, block_number}
    ← Rust returns ChatResponse
  → Sets pendingResponse (complete text)
  → useEffect triggers generateAndPlayTTS()
    → AudioContext.playTTS()
      → invoke('generate_speech', {userId, qubeId, text, password})
        → AudioManager.generate_speech_file()
          → chunk_text_for_tts() (split at sentence boundaries)
          → For EACH chunk: tts_provider.synthesize_file() [SERIAL]
        ← Returns (first_audio_path, total_chunks)
      ← SpeechResponse {audio_path, total_chunks}
    → invoke('play_audio_native', {filePath: chunk_1})
    → listen('audio-playback-ended') → play next chunk
  → addMessage() → setActiveTypewriterMessageId() → typewriter starts
```

**Total delay: 3-13 seconds** before user hears anything.
Serial waits: full LLM response + round-trip to frontend + full TTS generation for all chunks.

---

## The Solution

### New Flow

```
ChatInterface calls send-message-streaming command
  → Sidecar routes to GUIBridge.send_message_streaming()
    → qube.process_message(token_callback=on_token) — SAME method, new param
      → reasoner.process_input(token_callback=on_token)
        → Tool loop runs with generate() as normal (non-streaming)
        → Final iteration: generate() returns complete text
        → _emit_response_tokens() emits word-by-word via token_callback
          → on_token buffers tokens, checks for sentence boundaries
          → Sentence complete → asyncio.create_task(generate TTS)
          → send_stream("tts-text-token", {token})
          → send_stream("tts-audio-ready", {audio_path, chunk_index})
      → Block creation, token usage, auto-anchor — all unchanged
    → send_stream("tts-stream-end", {total_chunks, full_text})
    → Return final result

Frontend receives events as they arrive:
  → "tts-text-token" → append to streaming message text
  → "tts-audio-ready" → insert into ordered chunk map, play if next expected
  → "audio-playback-ended" → advance to next chunk in order
  → "tts-stream-end" → mark streaming complete, finalize message
```

**Target: ~1-3 seconds** after tool calls complete, first audio plays.

---

## Existing Infrastructure We Reuse

### Sidecar Streaming Protocol (sidecar_server.py:533-535)

Already exists and is used for tool call events:

```python
async def send_stream(self, request_id: str, stream_type: str, data: dict):
    """Send a streaming event associated with an in-flight request."""
    await self.send_response({"id": request_id, "stream": stream_type, "data": data})
```

### Rust Event Forwarding (lib.rs:178-192)

Already parses stream events and forwards them as Tauri events:

```rust
if let Some(stream_type) = parsed.get("stream").and_then(|v| v.as_str()) {
    if let Some(data) = parsed.get("data") {
        let event_name = match stream_type {
            "tool_call" => "tool-call-event",
            "chain_state_event" => "chain-state-event",
            _ => stream_type,  // ← Our new events pass through automatically!
        };
        let _ = handle.emit(event_name, data);
    }
    continue;
}
```

**Our new stream types (`tts-text-token`, `tts-audio-ready`, `tts-stream-end`) will flow through this existing code with zero Rust changes.** The `_ => stream_type` catch-all forwards unknown types as-is.

### Provider Streaming (all 8 providers)

Every AI provider already has `stream_generate()`:

```python
# ai/providers/openai_provider.py:217
async def stream_generate(self, messages, tools=None, temperature=0.7):
    stream = await client.chat.completions.create(**params, stream=True)
    async for chunk in stream:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
```

All 8 providers: OpenAI, Anthropic, Google, Perplexity, DeepSeek, Venice, Ollama, NanoGPT.

### Text Chunking (audio/audio_manager.py:101-161)

`chunk_text_for_tts()` already splits text at sentence boundaries (`.!?` followed by whitespace). We reuse this logic for the sentence buffer.

### Multi-Chunk Playback (AudioContext.tsx:208-248)

Frontend already queues and plays multiple audio chunks sequentially via `audio-playback-ended` events. The only change: chunks arrive dynamically instead of being known upfront.

### Audio Stop (lib.rs:3172-3187)

`stop_audio_native()` kills the playing process by PID. Works on all platforms. Already exposed as a Tauri command.

### STT Aliases (ChatInterface.tsx:736-745)

`applySttAliases()` fixes common speech recognition errors (e.g., "Alf" → "Alph"). Stream Mode reuses this.

---

## Detailed Implementation

### Backend: Reasoner Token Callback (ai/reasoner.py)

The approach: add an **optional** `token_callback` parameter to the existing `process_input()` — no new method, no code duplication. The tool loop runs identically. When the final iteration produces text (no tool calls), a helper emits the response word-by-word via the callback. Without the callback, behavior is unchanged.

**Key design decisions:**
- No `stream_generate()` used — we emit the complete response from `generate()` word-by-word. This gives us real `response.usage` data and costs nothing extra.
- Token emission is throttled (~20ms per word) to feel natural and give TTS time to generate between sentences.
- `_cancel_streaming` flag is checked in the emission loop to support interruptions.
- **No new method.** `process_input()` gains one optional parameter. The existing 4 generate() call sites and all branching logic stay untouched.
- The callback is **async** (awaited in the emission loop) so it can safely emit sidecar events and spawn TTS tasks.

**Changes to `process_input()` signature (line 205):**

```python
async def process_input(
    self,
    input_message: str,
    sender_id: str = "human",
    model_name: Optional[str] = None,
    max_iterations: int = 10,
    temperature: float = 0.7,
    token_callback=None,       # NEW — async callback for streaming TTS
) -> str:
```

**New helper method (add near `process_input`):**

```python
async def _emit_response_tokens(self, text: str, token_callback) -> bool:
    """
    Emit a complete response word-by-word via token_callback.
    Returns False if cancelled mid-stream, True if completed.
    """
    import re
    tokens = re.findall(r'\S+\s*', text)
    
    for token in tokens:
        if self._cancel_streaming:
            return False
        await token_callback(token)
        await asyncio.sleep(0.02)  # 20ms throttle — natural pacing
    return True
```

**Four exit paths in `process_input()` — only two need token emission:**

```python
# EXIT 1A: Tool loop detected, forced text response WITH content (line 776)
# Currently: return final_retry.content
if token_callback and final_retry.content:
    self._cancel_streaming = False
    try:
        await self._emit_response_tokens(final_retry.content, token_callback)
    except Exception as e:
        logger.warning("token_emission_failed", error=str(e))
        # Response already generated — continue to return it
return final_retry.content

# EXIT 1B: Tool loop detected, forced text response WITHOUT content (line 779)
# Hardcoded error message — no token emission needed
return f"I tried to help but got stuck in a loop ({loop_reason})..."

# EXIT 2: Normal final response — no tool calls (after line 935)
# IMPORTANT: Emit from response.content (raw LLM output), NOT final_response
# (which has auto-injected image paths prepended at lines 938-950).
# The frontend receives clean text tokens; the full final_response (with images)
# goes in the return value and tts-stream-end event.
if token_callback and response.content:
    self._cancel_streaming = False
    try:
        await self._emit_response_tokens(response.content, token_callback)
    except Exception as e:
        logger.warning("token_emission_failed", error=str(e))
        # Response already generated — continue to return it
return final_response  # final_response includes auto-injected image paths

# EXIT 3: Max iterations reached (line 1060)
# Hardcoded error message — no token emission needed
return "I apologize, I'm having trouble completing this request..."
```

**Only EXIT 1A and EXIT 2 emit tokens.** EXIT 1B and EXIT 3 are canned error messages — no streaming value. The frontend receives `tts-stream-end` with the error text as `full_text` and displays it directly.

**Token emission is wrapped in try/except** — if the sidecar event emission fails, the already-generated response is still returned. The user sees the response in chat (via `tts-stream-end` fallback) even if streaming playback was interrupted.

**Add `_cancel_streaming` init to `__init__`:**

```python
self._cancel_streaming = False
```

**Why not use `stream_generate()`?**
- `generate()` returns the complete response + real token usage in a single API call
- `stream_generate()` would require a second API call (wasted tokens/cost) since we already called `generate()` to check for tool calls
- `stream_generate()` doesn't return usage data (would need estimation)
- The UX is identical — frontend receives tokens progressively either way
- The 20ms throttle between words provides natural pacing and gives TTS generation time to work between sentences

**When would we use `stream_generate()` in the future?**
If we eliminate the need to check for tool calls first (e.g., model indicates "I'm done with tools" via a flag), we could stream the final response directly from the API for even lower latency. This is a future optimization when provider APIs support it better.

**IMPORTANT:** The `token_callback` is **async** (awaited in the emission loop). It emits sidecar events and spawns TTS tasks via `asyncio.create_task()`. Since `_emit_response_tokens` awaits each callback call sequentially, the sentence buffer stays consistent.

**IMPORTANT:** The existing `process_input()` behavior is unchanged when `token_callback` is not provided. Non-streaming commands pass no callback and hit the same code paths as before.

### Backend: Qube.process_message Token Callback (core/qube.py)

Thread the callback through `process_message()` to avoid duplicating dedup checks, block creation, token usage, relationship tracking, or auto-anchor logic.

**Changes to `process_message()` signature (line 1122):**

```python
async def process_message(
    self,
    message: str,
    sender_id: str = "human",
    model: Optional[str] = None,
    action_blocks: Optional[list] = None,
    token_callback=None,       # NEW — async callback for streaming TTS
) -> str:
```

**Single change inside the method — the reasoner call (line 1206):**

```python
# BEFORE:
response = await self.reasoner.process_input(
    input_message=message,
    sender_id=sender_id,
    model_name=model
)

# AFTER:
response = await self.reasoner.process_input(
    input_message=message,
    sender_id=sender_id,
    model_name=model,
    token_callback=token_callback,   # NEW — pass through
)
```

**Everything else stays untouched:** dedup check (1154-1181), incoming MESSAGE block (1183-1190), action blocks (1192-1204), token usage extraction (1213-1229), outgoing MESSAGE block (1231-1244), auto-anchor (1246-1249).

### Backend: Streaming Message Handler (gui_bridge.py)

Thin orchestrator that sets up the TTS callback and delegates to `qube.process_message()`. No block creation or token tracking here — that's all handled by `process_message`.

**Key design decisions:**
- The `token_callback` is **async** (awaited in the emission loop). It buffers tokens and checks for sentence boundaries.
- When a sentence completes, TTS is spawned as an `asyncio.Task` — it runs concurrently while the emission loop continues.
- TTS tasks run concurrently but the frontend plays chunks **in order** via an ordered chunk map (see AudioContext section).
- Text is cleaned (markdown, URLs, code blocks stripped) before TTS, same as current `generate_speech_file()`.
- Delegates to `qube.process_message(token_callback=on_token)` — all pre/post processing (dedup, blocks, token usage, auto-anchor) handled there.
- TTS task list tracked for cancellation support.

**Instance attributes to add in `GUIBridge.__init__` (NOT class-level — Python shares mutable class defaults across instances):**

```python
def __init__(self, user_id: str = "default_user"):
    self.orchestrator = UserOrchestrator(user_id=user_id)
    self._background_tasks: set = set()          # existing
    self._streaming_locks: Dict[str, asyncio.Lock] = {}  # NEW
    self._active_tts_tasks: Dict[str, list] = {}         # NEW
```

```python
async def send_message_streaming(
    self, qube_id, message, password,
    stream_callback=None,   # For emitting events to sidecar
    **kwargs
):
    """Send message with streaming TTS generation."""
    # Per-qube lock prevents concurrent streaming to same qube
    if qube_id not in self._streaming_locks:
        self._streaming_locks[qube_id] = asyncio.Lock()
    
    async with self._streaming_locks[qube_id]:
        return await self._send_message_streaming_impl(
            qube_id, message, password, stream_callback, **kwargs
        )

async def _send_message_streaming_impl(
    self, qube_id, message, password, stream_callback, **kwargs
):
    # Same setup as send_message (mirrors lines 1086-1095):
    try:
        if password:
            self.orchestrator.set_master_key(password)
        if qube_id not in self.orchestrator.qubes:
            await self.orchestrator.load_qube(qube_id)
        qube = self.orchestrator.qubes[qube_id]
    
        # Process documents embedded in message as <pdf_base64>/<image_base64> tags
        # (mirrors send_message lines 1097-1133)
        processed_message, doc_action_blocks = await self._process_documents_to_action_blocks(
            qube_id=qube_id, message=message, qube=qube
        )
    
        # Resolve voice config ONCE for all sentences (not per-sentence)
        voice_model_str = qube.chain_state.get_voice_model() if qube.chain_state else "openai:alloy"
        tts_provider_name, tts_voice = voice_model_str.split(":", 1) if ":" in voice_model_str else ("openai", voice_model_str)
        
        # Pre-resolve custom voice config (voice library lookup, clone paths, etc.)
        # so generate_sentence_audio doesn't repeat this per-sentence
        custom_voice_config = None
        if tts_provider_name == "custom":
            custom_voice_config = self._resolve_custom_voice(qube, tts_voice)
            # custom_voice_config = {voice_mode, clone_audio_path, clone_audio_text, design_prompt, language}
            # Mirrors generate_speech_file lines 764-797
    
        tts_enabled = qube.chain_state.is_tts_enabled()
        sentence_buffer = ""
        chunk_index = 0
        tts_tasks = []       # (chunk_index, asyncio.Task)
        audio_paths = []
        self._active_tts_tasks[qube_id] = tts_tasks  # For cancel_stream
    
    async def on_token(token):
        """Async callback — awaited in the emission loop."""
        nonlocal sentence_buffer, chunk_index
        sentence_buffer += token
        
        # Emit text token for frontend (always, even if TTS off)
        if stream_callback:
            await stream_callback("tts-text-token", {
                "qube_id": qube_id,
                "token": token,
            })
        
        if not tts_enabled:
            return  # Text-only mode — skip TTS generation
        
        # Check for complete sentences
        sentences, remaining = extract_complete_sentences(sentence_buffer)
        sentence_buffer = remaining
        
        for sentence in sentences:
            chunk_index += 1
            clean_sentence = clean_text_for_tts(sentence)
            if not clean_sentence.strip():
                continue
            
            # Fire TTS as async task with timeout — does NOT block token stream
            task = asyncio.create_task(
                asyncio.wait_for(
                    self._generate_and_emit_sentence(
                        qube, clean_sentence, chunk_index, qube_id,
                        tts_voice, tts_provider_name, custom_voice_config,
                        stream_callback, is_final=False
                    ),
                    timeout=30.0  # Per-sentence TTS timeout
                )
            )
            tts_tasks.append((chunk_index, task))
    
        # Delegate to process_message — handles dedup, blocks, token usage,
        # auto-anchor. Identical to non-streaming path.
        response_text = await qube.process_message(
            processed_message,  # Cleaned of document tags (matches send_message)
            sender_id=self.orchestrator.user_id,  # Must match send_message
            action_blocks=doc_action_blocks if doc_action_blocks else None,
            token_callback=on_token,
        )
    
    # Handle remaining buffer (last partial sentence)
    if sentence_buffer.strip() and tts_enabled:
        chunk_index += 1
        clean = clean_text_for_tts(sentence_buffer.strip())
        if clean.strip():
            task = asyncio.create_task(
                asyncio.wait_for(
                    self._generate_and_emit_sentence(
                        qube, clean, chunk_index, qube_id,
                        tts_voice, tts_provider_name, custom_voice_config,
                        stream_callback, is_final=True
                    ),
                    timeout=30.0
                )
            )
            tts_tasks.append((chunk_index, task))
    
    # Wait for all TTS tasks to complete
    for idx, task in tts_tasks:
        try:
            audio_path = await task
            if audio_path:
                audio_paths.append(audio_path)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            logger.warning("tts_sentence_skipped", chunk=idx, qube_id=qube_id)
    
    # Clean up task tracking
    self._active_tts_tasks.pop(qube_id, None)
    
        # Post-processing — mirrors send_message (gui_bridge.py:1158-1225)
        # process_message already created blocks, tracked tokens, ran auto-anchor.
        # We still need: response metadata + relationship tracking.
        response_timestamp, response_block_number = self._get_latest_response_block(
            qube, "qube_to_human"
        )
        self._record_relationship_interaction(qube, message, response_text)
        current_model, current_provider = self._get_current_model_info(qube)
        
        # Emit stream-end
        if stream_callback:
            await stream_callback("tts-stream-end", {
                "qube_id": qube_id,
                "total_chunks": chunk_index,
                "full_text": response_text,
            })
        
        # NOTE: No block creation here — process_message already created
        # both incoming and outgoing MESSAGE blocks + token usage + auto-anchor.
        # Return same fields as send_message so frontend ChatResponse type works.
        
        return {
            "success": True,
            "qube_id": qube_id,
            "qube_name": qube.genesis_block.qube_name,
            "message": message,
            "response": response_text,
            "timestamp": response_timestamp,
            "block_number": response_block_number,
            "current_model": current_model,
            "current_provider": current_provider,
            "audio_paths": [str(p) for p in audio_paths],
            "total_chunks": chunk_index,
            "streaming": True,  # Signal to frontend: TTS already handled
        }
    except Exception as e:
        logger.error(f"Failed to send streaming message to qube {qube_id}: {e}")
        return {"success": False, "error": str(e)}

async def _generate_and_emit_sentence(
    self, qube, sentence, chunk_index, qube_id,
    tts_voice, tts_provider_name, custom_voice_config,
    stream_callback, is_final
):
    """Generate TTS for one sentence and emit audio-ready event."""
    try:
        audio_path = await qube.audio_manager.generate_sentence_audio(
            text=sentence,
            voice_model=tts_voice,
            provider=tts_provider_name,
            chunk_index=chunk_index,
            custom_voice_config=custom_voice_config,
        )
        if stream_callback:
            await stream_callback("tts-audio-ready", {
                "qube_id": qube_id,
                "audio_path": str(audio_path),
                "chunk_index": chunk_index,
                "is_final": is_final,
            })
        return audio_path
    except Exception as e:
        logger.error("streaming_tts_sentence_failed",
                     chunk=chunk_index, error=str(e))
        # Emit error event so frontend can skip this chunk in the ordered map
        if stream_callback:
            await stream_callback("tts-audio-ready", {
                "qube_id": qube_id,
                "chunk_index": chunk_index,
                "is_final": is_final,
                "error": True,
            })
        return None
```

**`clean_text_for_tts()`** reuses the existing `clean_text_for_speech()` from `audio_manager.py:33` (removes `**bold**`, `*actions*`, URLs, code blocks, emoji shortcodes).

**Shared helpers extracted from `send_message()`:** The post-processing that both `send_message` and `send_message_streaming` need (response block lookup, relationship tracking, model info) should be extracted into small private methods on GUIBridge to avoid duplication:

```python
def _get_latest_response_block(self, qube, message_type) -> tuple:
    """Get timestamp and block_number of most recent MESSAGE block of given type."""
    # Extract from send_message lines 1160-1169
    ...

def _record_relationship_interaction(self, qube, user_message, response_text):
    """Record relationship interaction if applicable."""
    # Extract from send_message lines 1171-1207
    ...

def _get_current_model_info(self, qube) -> tuple:
    """Get current model and provider from chain_state."""
    # Extract from send_message lines 1210-1212
    ...
```

Then refactor `send_message` to call these same helpers, eliminating code duplication.

**`generate_sentence_audio()`** — New method on `AudioManager`. Thin wrapper around the existing TTS provider call, with streaming-specific file naming (block_number isn't available yet — MESSAGE block is created after streaming completes):

```python
async def generate_sentence_audio(
    self, text: str, voice_model: str, provider: str, chunk_index: int,
    custom_voice_config: dict = None,  # Pre-resolved by gui_bridge for custom voices
) -> Path:
    """Generate TTS for a single sentence. Used by streaming pipeline.
    
    Custom voice handling: gui_bridge resolves voice library lookup ONCE
    at stream start and passes custom_voice_config to all sentence calls.
    This avoids repeated file I/O and keeps AudioManager stateless.
    """
    audio_dir = (self.qube_data_dir / "audio") if self.qube_data_dir else get_app_data_dir() / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    
    # Custom voices route to WSL2 with full clone/design config
    actual_provider = provider
    if provider == "custom" and custom_voice_config:
        actual_provider = "wsl2"
    
    extension = "wav" if actual_provider in ("gemini", "wsl2", "qwen3", "kokoro") else "mp3"
    filename = f"stream_{chunk_index}_{int(time.time() * 1000)}.{extension}"
    output_path = audio_dir / filename
    
    if custom_voice_config:
        voice_config = VoiceConfig(
            provider=actual_provider, voice_id=voice_model,
            voice_mode=custom_voice_config.get("voice_mode", "cloned"),
            clone_audio_path=custom_voice_config.get("clone_audio_path"),
            clone_audio_text=custom_voice_config.get("clone_audio_text"),
            voice_design_prompt=custom_voice_config.get("design_prompt"),
            language=custom_voice_config.get("language", "en"),
        )
    else:
        voice_config = VoiceConfig(provider=actual_provider, voice_id=voice_model)
    
    # Provider lookup with WSL2→kokoro→qwen3 fallback for local TTS
    tts_provider = self._get_tts_provider_with_fallback(actual_provider)
    
    await tts_provider.synthesize_file(text, voice_config, output_path)
    return output_path

def _get_tts_provider_with_fallback(self, provider: str):
    """Get TTS provider, falling back for local providers if unavailable."""
    tts_provider = self.tts_providers.get(provider)
    if tts_provider:
        return tts_provider
    
    # Fallback chain for local TTS (mirrors generate_speech_file lines 846-932)
    if provider in ("wsl2", "qwen3", "qwen"):
        for fallback in ("kokoro", "qwen3"):
            fb = self.tts_providers.get(fallback)
            if fb:
                logger.warning("tts_provider_fallback", requested=provider, using=fallback)
                return fb
    
    raise ValueError(f"TTS provider '{provider}' not available")
```

### Backend: Sidecar Command (sidecar_server.py)

```python
# Add to command definitions
"send-message-streaming": ["user_id", "qube_id"],

# Add handler
async def _handle_send_message_streaming(self, bridge, params, secrets, request_id):
    """Send message with streaming TTS — emits events as sentences complete."""
    qube_id = params["qube_id"]
    message = secrets.get("message", "") or params.get("message", "")
    
    async def stream_callback(event_type, data):
        await self.send_stream(request_id, event_type, data)
    
    result = await bridge.send_message_streaming(
        qube_id=qube_id,
        message=message,
        password=secrets.get("password"),
        stream_callback=stream_callback,
    )
    return result

# Add cancel command
"cancel-stream": ["user_id", "qube_id"],

async def _handle_cancel_stream(self, bridge, params, secrets, request_id):
    """Cancel an in-progress streaming response."""
    qube_id = params["qube_id"]
    # 1. Set cancellation flag on the reasoner (stops token emission loop)
    qube = bridge.orchestrator.qubes.get(qube_id)
    if qube and qube.reasoner:
        qube.reasoner._cancel_streaming = True
    # 2. Cancel in-flight TTS tasks (stops wasted API calls)
    active_tasks = bridge._active_tts_tasks.get(qube_id, [])
    for idx, task in active_tasks:
        if not task.done():
            task.cancel()
    return {"success": True}
```

### Frontend: Streaming Audio Queue (AudioContext.tsx)

**Problem with a simple array queue:** TTS tasks run concurrently. Sentence 3 might generate faster than sentence 2. A naive `push()` / `shift()` would play chunks out of order.

**Solution:** An ordered `Map<number, string>` keyed by `chunk_index`. The playback function always looks for the next expected index. If it's not ready yet, it waits. When the chunk arrives, playback resumes automatically.

```typescript
// NEW: Ordered chunk map for streaming (guarantees playback order)
const streamingChunkMap = useRef<Map<number, string | null>>(new Map());
// null = error/skipped chunk, string = audio path
const nextExpectedChunk = useRef(1);
const isStreamingActive = useRef(false);
const streamingDone = useRef(false);  // All chunks received (including final)

// Listen for streamed audio chunks
useEffect(() => {
    const unlisten = listen<{
        qube_id: string;
        audio_path?: string;
        chunk_index: number;
        is_final: boolean;
        error?: boolean;
    }>('tts-audio-ready', (event) => {
        const { audio_path, chunk_index, is_final, error } = event.payload;
        
        // Insert into ordered map (null for error/skipped chunks)
        streamingChunkMap.current.set(
            chunk_index,
            error ? null : (audio_path ?? null)
        );
        
        if (is_final) {
            streamingDone.current = true;
        }
        
        // If we're waiting for this chunk, start/resume playback
        if (chunk_index === nextExpectedChunk.current && !isPlaying) {
            playNextStreamingChunk();
        }
    });
    
    return () => { unlisten.then(u => u()); };
}, []);

// Listen for stream-end (reset state when streaming completes)
useEffect(() => {
    const unlisten = listen<{
        qube_id: string;
        total_chunks: number;
        full_text: string;
    }>('tts-stream-end', (event) => {
        isStreamingActive.current = false;
    });
    return () => { unlisten.then(u => u()); };
}, []);

const playNextStreamingChunk = async () => {
    const chunkIndex = nextExpectedChunk.current;
    const path = streamingChunkMap.current.get(chunkIndex);
    
    if (path === undefined) {
        // Chunk not arrived yet — if stream is done and no more coming, finish
        if (streamingDone.current) {
            setIsPlaying(false);
            resetStreamingState();
        }
        // Otherwise, wait — the tts-audio-ready listener will call us
        return;
    }
    
    // Advance past this chunk (whether we play it or skip it)
    nextExpectedChunk.current = chunkIndex + 1;
    streamingChunkMap.current.delete(chunkIndex);
    
    if (path === null) {
        // Error/skipped chunk — advance to next immediately
        playNextStreamingChunk();
        return;
    }
    
    try {
        setIsPlaying(true);
        const result = await invoke<NativePlayResult>('play_audio_native', {
            filePath: path,
        });
        player.setDuration(result.duration);
        player.startPlayback();
    } catch (err) {
        console.error('Streaming chunk playback failed:', err);
        playNextStreamingChunk(); // Skip failed chunk, try next
    }
};

const resetStreamingState = () => {
    streamingChunkMap.current.clear();
    nextExpectedChunk.current = 1;
    isStreamingActive.current = false;
    streamingDone.current = false;
};

// Start streaming mode (called from ChatInterface before send)
const startStreamingPlayback = () => {
    resetStreamingState();
    isStreamingActive.current = true;
};

// Existing audio-playback-ended handler — add streaming support:
listen('audio-playback-ended', () => {
    if (isStreamingActive.current || streamingChunkMap.current.size > 0) {
        // Streaming mode — play next ordered chunk
        playNextStreamingChunk();
    } else if (/* existing chunk logic */) {
        // Non-streaming mode — existing behavior unchanged
    }
});
```

### Frontend: Streaming Text Display (ChatInterface.tsx)

The current TypewriterText component syncs text reveal to `audioElement.currentTime`. In streaming mode, text arrives token-by-token from the LLM while audio arrives sentence-by-sentence — they're decoupled. Rather than modifying TypewriterText's sync logic, streaming uses a simpler approach: **text appears immediately as tokens arrive, audio plays independently in parallel.**

**Performance note:** At 20ms per token, naive `setState` per token = ~50 re-renders/second, each re-parsing markdown. Instead, accumulate in a ref and flush to state on an interval:

```typescript
// NEW state for streaming text
const [streamingText, setStreamingText] = useState('');
const [isStreaming, setIsStreaming] = useState(false);
const streamingMessageIdRef = useRef<string | null>(null);
const streamingTextRef = useRef('');  // Accumulator (no re-render)
const flushIntervalRef = useRef<NodeJS.Timeout | null>(null);

const startStreamingText = () => {
    streamingTextRef.current = '';
    setStreamingText('');
    setIsStreaming(true);
    // Flush accumulated text to state every 100ms (10 re-renders/sec, not 50)
    flushIntervalRef.current = setInterval(() => {
        setStreamingText(streamingTextRef.current);
    }, 100);
};

const stopStreamingText = () => {
    if (flushIntervalRef.current) {
        clearInterval(flushIntervalRef.current);
        flushIntervalRef.current = null;
    }
    // Final flush
    setStreamingText(streamingTextRef.current);
};

// Listen for text tokens from backend
useEffect(() => {
    const unlisten = listen<{
        qube_id: string;
        token: string;
    }>('tts-text-token', (event) => {
        if (!isStreaming) return;
        streamingTextRef.current += event.payload.token;
        
        // Clear loading indicator on first token (user sees response starting)
        if (isLoading) {
            setIsLoading(false);
            setProcessingStage(null);
        }
    });
    return () => { unlisten.then(u => u()); };
}, [isStreaming, isLoading]);

// Listen for stream-end — finalize message
useEffect(() => {
    const unlisten = listen<{
        qube_id: string;
        full_text: string;
    }>('tts-stream-end', (event) => {
        if (!isStreaming) return;
        const messageId = streamingMessageIdRef.current;
        
        stopStreamingText();
        setStreamingText('');
        setIsStreaming(false);
        streamingMessageIdRef.current = null;
        
        // Add finalized message to history using cleanContentForDisplay
        // (same cleaning as non-streaming path at line 1107)
        if (messageId) {
            addMessage(currentQube.qube_id, {
                id: messageId,
                role: 'assistant',
                content: cleanContentForDisplay(event.payload.full_text),
            });
        }
    });
    return () => { unlisten.then(u => u()); };
}, [isStreaming]);
```

**Rendering in the message list:**

```tsx
{/* Streaming message — rendered inline, text grows as tokens arrive */}
{isStreaming && streamingText && (
    <div className="qube-message-bubble">
        <MarkdownRenderer content={streamingText} />
    </div>
)}
```

**Why not use TypewriterText in streaming mode?**
- TypewriterText's value is syncing text to audio timing. In streaming, text arrives at LLM speed (~20ms/word) which already feels like natural typing.
- Audio plays independently — there's no benefit to artificially delaying text to match audio timing.
- Simpler implementation: just render `streamingText` as it grows. No duration calculation, no fallback modes, no chunk-aware text distribution.

### Frontend: Stream Mode (ChatInterface.tsx)

**Coexistence with existing SpeechRecognition:** ChatInterface already has a `recognitionRef` (line 82), `toggleRecording()` (line 1245), and `isRecording` state used by the existing mic button for single-shot voice input. Stream Mode **reuses the same `recognitionRef`** but reconfigures it with different handlers (continuous + silence detection + interrupt). When Stream Mode is active, the existing mic button is hidden. When Stream Mode exits, the original handlers are restored.

```typescript
const [isStreamMode, setIsStreamMode] = useState(false);
const [isListening, setIsListening] = useState(false);
const [interimTranscript, setInterimTranscript] = useState('');
const silenceTimerRef = useRef<NodeJS.Timeout | null>(null);
// Store original recognition handlers to restore on Stream Mode exit
const originalHandlersRef = useRef<{ onresult: any; onend: any } | null>(null);

const SILENCE_TIMEOUT_MS = 1500; // Configurable

// NOTE: tts-text-token listener is in the "Streaming Text Display" section above.
// Stream Mode reuses that same listener — no duplicate needed.

const toggleStreamMode = () => {
    if (isStreamMode) {
        // EXIT Stream Mode
        recognitionRef.current?.stop();
        setIsStreamMode(false);
        setIsListening(false);
        if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
    } else {
        // ENTER Stream Mode
        setIsStreamMode(true);
        startListening();
    }
};

const startListening = () => {
    if (!recognitionRef.current) return;
    
    const recognition = recognitionRef.current;
    recognition.continuous = true;
    recognition.interimResults = true;
    
    recognition.onresult = (event: any) => {
        let transcript = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
            transcript += event.results[i][0].transcript;
        }
        transcript = applySttAliases(transcript);
        
        // Show typewriter effect for user's speech
        setInterimTranscript(transcript);
        
        // Reset silence timer
        if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
        silenceTimerRef.current = setTimeout(() => {
            // Silence detected — auto-send
            if (transcript.trim()) {
                handleStreamSend(transcript.trim());
                setInterimTranscript('');
            }
        }, SILENCE_TIMEOUT_MS);
        
        // INTERRUPT DETECTION: user speaking while qube is responding
        if (isPlaying || isLoading) {
            // Stop qube's audio
            invoke('stop_audio_native');
            // Cancel LLM stream
            invoke('cancel_stream', { qubeId: currentQube.qube_id });
            // Clear audio queue
            resetStreamingState();  // From AudioContext — clears ordered chunk map
            setIsPlaying(false);
        }
    };
    
    // AUTO-RESTART: Web Speech API can silently stop even with continuous=true
    // (network timeouts, browser limits, tab backgrounding). Restart if still
    // in Stream Mode.
    recognition.onend = () => {
        if (isStreamMode) {
            // Brief delay to avoid rapid restart loops on persistent errors
            setTimeout(() => {
                if (isStreamMode && !isListening) {
                    try {
                        recognition.start();
                    } catch (e) {
                        // Already started or other error — ignore
                    }
                }
            }, 300);
        }
    };
    
    recognition.start();
    setIsListening(true);
};

const handleStreamSend = async (text: string) => {
    // Add user message to chat
    addMessage(currentQube.qube_id, {
        role: 'user',
        content: text,
    });
    
    // Send via streaming command
    await invoke('send_message_streaming', {
        userId, qubeId: currentQube.qube_id, message: text, password,
    });
    
    // After qube responds, auto-resume listening (if still in Stream Mode)
    if (isStreamMode) {
        startListening();
    }
};
```

### Frontend: UI Changes

```tsx
{/* Replace microphone button */}
<button
    onClick={toggleStreamMode}
    className={`px-3 py-2 rounded-lg transition-all ${
        isStreamMode
            ? 'bg-accent-danger/20 text-accent-danger animate-pulse'
            : 'bg-bg-secondary text-text-secondary hover:text-accent-primary'
    }`}
    title={isStreamMode ? 'Stop Stream Mode' : 'Start Stream Mode'}
    disabled={isLoading && !isStreamMode}
>
    {isStreamMode ? '🛑' : '🎤'}
</button>

{/* Stream Mode indicator */}
{isStreamMode && (
    <div className="absolute bottom-16 left-0 right-0 flex justify-center">
        <div className="bg-accent-primary/10 border border-accent-primary/30 
                        rounded-full px-4 py-1 text-xs text-accent-primary 
                        flex items-center gap-2">
            <span className="w-2 h-2 bg-accent-danger rounded-full animate-pulse" />
            Stream Mode — speaking to {currentQube?.qube_name}
        </div>
    </div>
)}

{/* User's voice transcript (interim) */}
{isStreamMode && interimTranscript && (
    <div className="user-message-bubble opacity-70 italic">
        {interimTranscript}
    </div>
)}
```

---

## Concurrency & Safety

### Streaming Command Timeout

The existing `send_message` has a 300s timeout in lib.rs. The `send_message_streaming` Tauri command uses the same timeout (the `sidecar_execute_with_retry` timeout is in **seconds**, not milliseconds):

```rust
// In lib.rs — mirrors send_message pattern exactly:
let result = sidecar_execute_with_retry(
    "send-message-streaming", args, secrets,
    Some(&app_handle),
    Some(300)  // 5 minute timeout in seconds (same as send_message)
).await?;
```

### ChatResponse Struct (lib.rs)

Add optional streaming fields to the existing `ChatResponse` so both commands return the same type:

```rust
#[derive(Debug, Serialize, Deserialize)]
struct ChatResponse {
    success: bool,
    qube_id: Option<String>,
    qube_name: Option<String>,
    message: Option<String>,
    response: Option<String>,
    timestamp: Option<i64>,
    block_number: Option<i64>,
    current_model: Option<String>,
    current_provider: Option<String>,
    error: Option<String>,
    // NEW — streaming fields (None for non-streaming responses)
    streaming: Option<bool>,
    total_chunks: Option<i64>,
}
```

The TypeScript `ChatResponse` interface (ChatInterface.tsx:28-39) also needs the matching optional fields:

```typescript
interface ChatResponse {
    // ... existing fields ...
    streaming?: boolean;
    total_chunks?: number;
}
```

### Per-Qube Streaming Lock

Prevents concurrent streaming calls to the same qube (e.g., rapid double-send):

```python
# In GUIBridge:
_streaming_locks: Dict[str, asyncio.Lock] = {}

async def send_message_streaming(self, qube_id, ...):
    if qube_id not in self._streaming_locks:
        self._streaming_locks[qube_id] = asyncio.Lock()
    
    async with self._streaming_locks[qube_id]:
        # ... streaming code ...
```

The frontend already guards against double-sends with `isSendingRef`, but the backend lock is a safety net.

### Async Token Callback

The token callback is **async** (awaited in `_emit_response_tokens`):

```python
# In _emit_response_tokens:
for token in tokens:
    if self._cancel_streaming:
        return False
    await token_callback(token)    # Async — safe to emit events + spawn tasks
    await asyncio.sleep(0.02)      # 20ms throttle
```

The callback in `send_message_streaming` is async too — it buffers tokens, emits sidecar events, checks for sentence boundaries, and spawns TTS as `asyncio.create_task()`. All shown in the GUIBridge section above.

### TTS Sentence Timeout

Each TTS generation call has a 30-second timeout. If a provider hangs, the sentence is skipped and the stream continues:

```python
task = asyncio.create_task(
    asyncio.wait_for(
        self._generate_and_emit_sentence(qube, sentence, chunk_index, ...),
        timeout=30.0
    )
)
```

On timeout, `asyncio.TimeoutError` is raised. The `_generate_and_emit_sentence` exception handler catches it, logs it, and emits `tts-audio-ready` with `error: true`. The frontend's ordered chunk map marks that index as `null` and skips it during playback.

### TTS Task Cancellation

When `cancel_stream` is called, it does two things:
1. Sets `reasoner._cancel_streaming = True` (stops the token emission loop)
2. Cancels all in-flight TTS tasks via `task.cancel()` (stops wasted API calls)

```python
# In _handle_cancel_stream:
active_tasks = bridge._active_tts_tasks.get(qube_id, [])
for idx, task in active_tasks:
    if not task.done():
        task.cancel()
```

The `_generate_and_emit_sentence` handler catches `asyncio.CancelledError` alongside other exceptions.

### Stream Mode Double-Send Prevention

When the user interrupts (speaks while qube is responding), the silence timer must be cleared to prevent auto-sending the interrupt as a message before the current response is fully cancelled:

```typescript
// In interrupt detection:
if (isPlaying || isLoading) {
    // Clear silence timer FIRST — prevent premature auto-send
    if (silenceTimerRef.current) {
        clearTimeout(silenceTimerRef.current);
        silenceTimerRef.current = null;
    }
    
    // Stop qube's response
    await invoke('stop_audio_native');
    await invoke('cancel_stream', { qubeId });
    resetStreamingState();  // Clear ordered chunk map
    setIsPlaying(false);
    setIsLoading(false);
    
    // NOW restart silence timer for the interrupt transcript
    // (will auto-send after user stops speaking)
    silenceTimerRef.current = setTimeout(() => {
        handleStreamSend(transcript.trim());
    }, SILENCE_TIMEOUT_MS);
}
```

---

## Sentence Detection

```python
import re

# Matches sentence-ending punctuation followed by whitespace or end of string.
# Excludes ellipses (... ) which are continuations, not sentence endings.
SENTENCE_BOUNDARY = re.compile(r'(?<=[.!?])(?<!\.\.\.)(?<!\. \. \.)\s+|(?<=[.!?])(?<!\.\.\.)$')

# URL pattern — dots inside URLs should not trigger sentence splits
URL_PATTERN = re.compile(r'https?://\S+|www\.\S+')

ABBREVIATIONS = {
    # Titles
    'Mr.', 'Mrs.', 'Ms.', 'Dr.', 'Jr.', 'Sr.', 'Prof.', 'Rev.', 'Gen.', 'Gov.',
    # Latin
    'vs.', 'etc.', 'e.g.', 'i.e.', 'approx.', 'dept.', 'est.',
    # Places & addresses
    'St.', 'Ave.', 'Blvd.', 'Rd.', 'Ln.', 'Dr.',
    # Organizations
    'Corp.', 'Inc.', 'Ltd.', 'Co.', 'Bros.',
    # Measurements
    'ft.', 'oz.', 'lb.', 'pt.', 'qt.',
    # Other
    'No.', 'vol.', 'Fig.', 'Ref.',
    # Geographic / political
    'U.S.', 'D.C.', 'U.K.', 'E.U.',
    # Time
    'a.m.', 'p.m.',
}

MIN_SENTENCE_LENGTH = 20
MAX_SENTENCE_LENGTH = 500

def extract_complete_sentences(buffer: str) -> tuple:
    """
    Extract complete sentences from buffer.
    Returns (complete_sentences: list[str], remaining_buffer: str)
    
    Handles:
    - Standard sentence boundaries (. ! ?)
    - Abbreviations (Mr., U.S., etc.) — not treated as boundaries
    - URLs (example.com) — dots inside not treated as boundaries
    - Ellipses (...) — treated as continuation, not boundary
    - Run-on sentences — force-split at comma/semicolon after MAX_SENTENCE_LENGTH
    """
    sentences = []
    remaining = buffer

    while True:
        match = SENTENCE_BOUNDARY.search(remaining)
        if not match:
            break

        candidate = remaining[:match.end()].strip()

        if len(candidate) < MIN_SENTENCE_LENGTH:
            break

        # Skip if the period is inside a URL
        pre_match = remaining[:match.start()]
        url_match = URL_PATTERN.search(pre_match)
        if url_match and url_match.end() >= match.start():
            # The sentence boundary is inside a URL — skip this match
            remaining_after = remaining[match.end():]
            next_match = SENTENCE_BOUNDARY.search(remaining_after)
            if not next_match:
                break
            # Try the next boundary instead
            continue

        is_abbreviation = any(
            candidate.rstrip().endswith(abbr)
            for abbr in ABBREVIATIONS
        )
        if is_abbreviation:
            break

        sentences.append(candidate)
        remaining = remaining[match.end():]

    # Force split for run-on sentences (no sentence boundary found)
    if len(remaining) > MAX_SENTENCE_LENGTH:
        split_point = max(
            remaining.rfind(', ', 0, MAX_SENTENCE_LENGTH),
            remaining.rfind('; ', 0, MAX_SENTENCE_LENGTH),
            remaining.rfind(' — ', 0, MAX_SENTENCE_LENGTH),
            remaining.rfind(': ', 0, MAX_SENTENCE_LENGTH),
        )
        if split_point > MIN_SENTENCE_LENGTH:
            sentences.append(remaining[:split_point + 1].strip())
            remaining = remaining[split_point + 1:].strip()

    return sentences, remaining
```

---

## Block System — No Changes Needed

All existing block types handle streaming naturally:

| Scenario | Block | How |
|----------|-------|-----|
| User types message | MESSAGE (user) | Same as current |
| User speaks in Stream Mode | MESSAGE (user) | Same as current (transcript becomes message text) |
| Qube responds (streaming) | MESSAGE (assistant) | Created AFTER streaming completes with full text |
| Qube interrupted | MESSAGE (assistant) | `metadata.interrupted = True`, partial text |
| Tool called during processing | ACTION | Created by tool_registry during tool loop (before streaming starts) |

**Block creation is handled by `process_message()`** — the same method used by the non-streaming path. Incoming MESSAGE block is created before the reasoner call, outgoing MESSAGE block after it returns. `send_message_streaming` does not touch blocks at all.

**Auto-anchor**: Threshold checks happen when blocks are added. Incoming MESSAGE block is created BEFORE streaming, outgoing MESSAGE block AFTER streaming completes, ACTION blocks during tool loop (before streaming). Timing is identical to current — no changes needed. If anchoring fires during streaming (from a tool call ACTION block pushing over threshold), it runs asynchronously and doesn't block streaming.

**Auto-sync to IPFS**: Triggered after anchoring completes. Runs on its own async schedule, completely independent of streaming. Syncs finalized (anchored) blocks, not in-progress data. No conflict.

---

## Interruption Handling

### User Sends New Message While Qube is Responding

Works in both text chat and Stream Mode:

```
1. User types/speaks new message
2. Frontend: invoke('stop_audio_native')     → kills audio player process
3. Frontend: invoke('cancel_stream', {qubeId}) → sets cancel flag + cancels TTS tasks
4. Frontend: resetStreamingState()            → clears ordered chunk map
5. Backend: reasoner sees cancel flag         → stops token emission loop
6. Backend: in-flight TTS tasks receive CancelledError → stop wasted API calls
7. Backend: process_message returns partial response → outgoing MESSAGE block
8. Frontend: sends new message via streaming command
9. New response cycle begins
```

### Edge Case: Tool Call In Progress When Interrupted

If the user interrupts during tool execution (before streaming starts), the tool completes but the final response is never generated. The ACTION blocks are already created. The frontend simply sends the new message, and the backend starts a fresh cycle.

### Edge Case: TTS Generation In Progress

When the user interrupts, `cancel_stream` cancels all in-flight TTS tasks via `task.cancel()`. Tasks that have already completed are unaffected (audio files exist on disk but are never queued for playback). Tasks mid-API-call receive `CancelledError` and stop.

### Edge Case: TTS API Failure Mid-Stream

If TTS fails for one sentence (API error, rate limit, timeout):

1. `_generate_and_emit_sentence` catches the exception and logs it
2. Emits `tts-audio-ready` with `error: true` for that chunk index
3. Frontend's ordered chunk map stores `null` for that index
4. When `playNextStreamingChunk()` encounters a `null` entry, it skips it and advances to the next index
5. Result: sentences 1, 2 play → sentence 3 failed (small gap) → sentence 4 plays
6. Streaming text display is unaffected — all text still appears via `tts-text-token` events

### Edge Case: Auto-Lock Mid-Stream

If the user has auto-lock enabled and the timeout fires during streaming:

```typescript
// In auto-lock handler (App.tsx):
if (isStreamingActive) {
    await invoke('cancel_stream', { qubeId });
    await invoke('stop_audio_native');
}
lock();
```

Partial response is saved as an interrupted MESSAGE block. When the user unlocks, they see the partial response in chat history.

### Edge Case: Escape Key During Streaming

The existing escape handler (ChatInterface.tsx lines 804-818) clears messages and tool calls but does NOT stop audio or clean up streaming state. Must add streaming cleanup:

```typescript
const handleEscapeKey = (e: KeyboardEvent) => {
    if (e.key === 'Escape' && selectedQubes.length > 0) {
        // Existing cleanup
        clearMessages(selectedQubes[0].qube_id);
        setCompletedActionBlocks([]);
        setActiveToolCalls([]);
        chatClearedAtRef.current = Date.now();
        setError(null);
        setLastResponseText('');
        
        // NEW: Streaming cleanup
        stopAudio();                      // Stop TTS playback
        resetStreamingState();            // Clear ordered chunk map
        stopStreamingText();              // Stop flush interval
        setStreamingText('');
        setIsStreaming(false);
        setActiveTypewriterMessageId(null);
        pendingTypewriterRef.current = null;
        setIsLoading(false);
        isSendingRef.current = false;
        setProcessingStage(null);
        setIsGeneratingTTS(false);
        
        // Cancel backend stream if active
        if (isStreaming) {
            invoke('cancel_stream', { qubeId: selectedQubes[0].qube_id }).catch(() => {});
        }
    }
};
```

### Edge Case: Partial Response on Exception

If `process_input` raises after some tokens have been emitted (e.g., API error mid-response), the frontend has partial streaming text but the invoke returns an error. The `tts-stream-end` event is never emitted.

Solution: `send_message_streaming` wraps the `process_message` call in try/except. On error, it emits `tts-stream-end` with the partial text before returning the error:

```python
try:
    response_text = await qube.process_message(...)
except Exception as e:
    # Emit stream-end with partial text so frontend can finalize
    if stream_callback:
        await stream_callback("tts-stream-end", {
            "qube_id": qube_id,
            "total_chunks": chunk_index,
            "full_text": sentence_buffer,  # Whatever was accumulated
            "error": str(e),
        })
    raise  # Let outer handler return {"success": False}
```

The frontend's `tts-stream-end` handler checks for `error` and displays the partial response with an error indicator rather than silently discarding it.

### Edge Case: `pendingResponse` Double-Fire

The current `generateAndPlayTTS` useEffect watches `pendingResponse` to trigger TTS. With streaming, TTS is handled by the backend. Both must not run simultaneously.

Solution: `send_message_streaming` returns `{ streaming: true }` in the response. The existing useEffect checks this flag:

```typescript
// In ChatInterface.tsx generateAndPlayTTS effect:
if (pendingResponse?.streaming) {
    // TTS already handled by streaming pipeline — skip entirely.
    // Message was already added progressively via tts-text-token events
    // and finalized by tts-stream-end. No typewriter needed.
    setPendingResponse(null);
    setIsLoading(false);
    isSendingRef.current = false;
    setProcessingStage(null);
    processingResponseRef.current = null;
    return;
}
// ... existing TTS generation code for non-streaming path ...
```

### Two `invoke('send_message')` Call Sites in handleSend

ChatInterface has TWO `invoke('send_message')` calls that both need streaming variants:

1. **Line 1040** — For text files + PDFs after image processing (combined response)
2. **Line 1089** — For regular messages

Both follow the same pattern: invoke → check success → setPendingResponse. Extract a shared helper to avoid duplicating the streaming/non-streaming branch:

```typescript
// Helper: send via streaming or non-streaming path
// NOTE: Both call sites already call prepareMessageForIPC(message) before this
// (line 1038 and 1087), which writes to a temp file if >100KB. Pass the result.
const sendToBackend = async (preparedMessage: string): Promise<ChatResponse> => {
    // streamingTTSEnabled: defaults to true when TTS is enabled.
    // Can be toggled off in Settings > Voice to fall back to batch TTS.
    // Stored per-qube in chain_state alongside tts_enabled.
    if (currentQube.streaming_tts_enabled !== false && currentQube.tts_enabled) {
        // Streaming path: start streaming state, send via streaming command
        startStreamingText();  // Init ref, start flush interval
        streamingMessageIdRef.current = (Date.now() + 1).toString();
        startStreamingPlayback();  // From AudioContext — init ordered chunk map
        
        const response = await invoke<ChatResponse>('send_message_streaming', {
            userId, qubeId: selectedQubes[0].qube_id,
            message: preparedMessage, password,
        });
        
        // Response has streaming: true — pendingResponse effect will skip TTS
        return response;
    } else {
        // Non-streaming path: existing behavior unchanged
        return await invoke<ChatResponse>('send_message', {
            userId, qubeId: selectedQubes[0].qube_id,
            message: preparedMessage, password,
        });
    }
};
```

Both call sites (line 1040 and 1089) replace `invoke('send_message', ...)` with `sendToBackend(preparedMessage)`. The existing `prepareMessageForIPC()` call at each site runs before `sendToBackend` — no change needed there. The rest of handleSend stays unchanged — `setPendingResponse` is set the same way, `generateAndPlayTTS` triggers, and the streaming flag gates the TTS path.

---

## TTS Disabled

Every qube has a voice model (set at mint, can be changed but not removed). TTS can be toggled off in settings.

**When TTS is off:**
- `send_message_streaming` still emits `tts-text-token` events → typewriter works normally
- TTS generation is skipped entirely → no `tts-audio-ready` events, no audio
- `tts-stream-end` still fires with the full text
- The 20ms throttle on token emission provides natural typewriter pacing even without audio
- Stream Mode button is disabled with tooltip: "Enable TTS to use Stream Mode"

```python
# In on_token callback (shown in GUIBridge section):
tts_enabled = qube.chain_state.is_tts_enabled()

async def on_token(token):
    # ... emit tts-text-token always ...
    
    if not tts_enabled:
        return  # Text-only mode — skip TTS generation
    # ... sentence detection + TTS generation ...
```

---

## Document Attachments

PDF/image attachments are processed BEFORE the `process_message` call, same as current `send_message`. Documents are converted to `action_blocks` and passed to `qube.process_message(action_blocks=action_blocks, token_callback=on_token)`. The document processing is shown in the GUIBridge section above.

No change to document handling — it runs before streaming starts.

---

## Self-Evaluation

Some modes trigger a self-evaluation call after the main response. This is a separate `process_input()` call (no `token_callback`) that runs AFTER the streaming `process_input()` returns. It:
- Does NOT emit TTS events (uses the non-streaming path)
- Does NOT produce audio
- Stores results internally in chain state
- No conflict with streaming

---

## Scope Boundaries

| Feature | Supported | Notes |
|---------|-----------|-------|
| Individual chat | Streaming TTS + Stream Mode | Full support |
| Group chat | Streaming TTS only | Stream Mode disabled (button hidden) |
| P2P chat | Not supported | P2P relay protocol is request/response, no streaming events |

---

## Settings

| Setting | Location | Default | Description |
|---------|----------|---------|-------------|
| Streaming TTS | Settings > Voice (per-qube) | On | Stream audio sentence-by-sentence. Stored in chain_state as `streaming_tts_enabled`. Defaults to `true` when TTS is enabled. Set to `false` to fall back to batch TTS. |
| Silence timeout | Settings > Voice | 1.5s | Seconds of silence before auto-send in Stream Mode |
| Auto-listen | Settings > Voice | On | Re-activate mic after qube finishes speaking |

---

## Compatibility

### AI Providers — All 8 Compatible (No Provider Changes Needed)

Streaming uses the existing `generate()` method on all providers. The complete response is emitted word-by-word to the frontend — no `stream_generate()` required.

| Provider | Existing Method Used |
|----------|---------------------|
| OpenAI | `generate()` — returns content + usage |
| Anthropic | `generate()` — returns content + usage |
| Google | `generate()` — returns content + usage |
| Perplexity | `generate()` — returns content + usage |
| DeepSeek | `generate()` — returns content + usage |
| Venice | `generate()` — returns content + usage |
| Ollama | `generate()` — returns content + usage |
| NanoGPT | `generate()` — returns content + usage |

`stream_generate()` exists on all 8 providers as a future optimization path if we can eliminate the tool-call check iteration.

### TTS Providers — All Support Per-Sentence Generation

| Provider | Voices | Method |
|----------|--------|--------|
| OpenAI TTS | 13 | `synthesize_file()` per sentence |
| Kokoro | 54 | `synthesize_file()` per sentence |
| Gemini TTS | 30 | `synthesize_file()` per sentence |
| ElevenLabs | API-fetched | `synthesize_file()` per sentence |
| Google Cloud | API-fetched | `synthesize_file()` per sentence |
| Piper | 3 | `synthesize_file()` per sentence |
| Qwen3 | 9+ custom | `synthesize_file()` per sentence |

### Speech Recognition (Stream Mode)

| Browser | Support | Notes |
|---------|---------|-------|
| Chrome/Edge | Full | Native `SpeechRecognition` |
| Safari | Full | `webkitSpeechRecognition` (already handled in code) |
| Firefox | Limited | May need flag, Stream Mode button hidden if unavailable |

### Existing Code Reused

| Component | File:Line | What It Does |
|-----------|-----------|--------------|
| `send_stream()` | `sidecar_server.py:533` | Emit streaming events to Rust |
| Stream event forwarding | `lib.rs:178-192` | Forward to frontend as Tauri events |
| `chunk_text_for_tts()` | `audio/audio_manager.py:101` | Sentence boundary detection |
| `audio-playback-ended` listener | `AudioContext.tsx:208` | Sequential chunk playback |
| `stop_audio_native()` | `lib.rs:3172` | Kill audio player by PID |
| `NATIVE_AUDIO_PID` | `lib.rs:2961` | Track playing process for stop |
| `applySttAliases()` | `ChatInterface.tsx:736` | Fix speech recognition errors |
| `SpeechRecognition` setup | `ChatInterface.tsx:747` | Browser STT with interim results |

---

## Implementation Phases

### Phase 1: Backend Streaming Pipeline
Files: `ai/reasoner.py`, `core/qube.py`, `gui_bridge.py`, `audio/audio_manager.py`, `sidecar_server.py`

- [ ] Add `token_callback=None` parameter to `process_input()` (no new method)
  - Add `_emit_response_tokens()` helper — word-by-word emission with cancel check + 20ms throttle
  - Insert callback invocation at 2 of 4 exit paths (EXIT 1A: forced text with content, EXIT 2: normal response). EXIT 1B and EXIT 3 are canned error messages — no streaming needed.
  - EXIT 2: emit from `response.content` (pre-image-injection), NOT `final_response` (post-injection)
  - Wrap emission in try/except — failures are non-fatal (response already generated)
  - Callback is async (awaited) — safe for event emission and task spawning
  - Preserves real `response.usage` data — no estimation needed
  - Add `_cancel_streaming` flag (initialized in `__init__`) for interruption support
- [ ] Add `token_callback=None` parameter to `qube.process_message()` — passes through to `process_input()`
  - Single-line change at the reasoner call site (line 1206)
  - All pre/post processing (dedup, blocks, token usage, auto-anchor) stays untouched
- [ ] Add `extract_complete_sentences()` utility to `audio/audio_manager.py`
  - Abbreviation-aware, URL-aware, ellipsis-aware sentence detection
- [ ] Add `clean_text_for_tts()` — extract existing `clean_text_for_speech()` into reusable function
- [ ] Add `generate_sentence_audio()` to `AudioManager` (single-sentence TTS, timestamp-based file naming)
  - Takes `text`, `voice_model`, `provider`, `chunk_index`, `custom_voice_config=None`
  - Uses `stream_{chunk_index}_{timestamp_ms}.{ext}` naming (block_number not yet available)
  - Handles custom voices: `custom_voice_config` pre-resolved by gui_bridge, passed through
  - Includes `_get_tts_provider_with_fallback()` — WSL2→kokoro→qwen3 fallback for local TTS
- [ ] Add `send_message_streaming()` to `GUIBridge`
  - Instance attributes `_streaming_locks` and `_active_tts_tasks` in `__init__` (NOT class-level — Python shares mutable class defaults)
  - Thin orchestrator — delegates to `qube.process_message(processed_message, sender_id, token_callback=on_token)`
  - Inline qube loading (same 3-line pattern as `send_message`, no `_load_and_unlock_qube` helper)
  - Process document tags in message via `_process_documents_to_action_blocks(qube_id, message, qube)` → `(processed_message, doc_action_blocks)`
  - Resolve voice config ONCE at start: `qube.chain_state.get_voice_model()` → split `"provider:voice"` → resolve custom voice config if `provider == "custom"` → pass to all TTS calls
  - Wrap `process_message` call in try/except: on error, emit `tts-stream-end` with partial text + error flag before re-raising
  - Gate TTS generation on `tts_enabled` setting (text tokens always emit)
  - Buffers tokens into sentences, fires TTS as async tasks (non-blocking)
  - Per-sentence TTS timeout (30s) via `asyncio.wait_for`
  - Per-qube streaming lock prevents concurrent streaming calls
  - Track active TTS tasks in `_active_tts_tasks` for cancellation
  - Emits: `tts-text-token`, `tts-audio-ready` (with `error` field), `tts-stream-end`
  - Returns `{ streaming: true }` flag + same fields as `send_message` (timestamp, block_number, etc.)
  - Does NOT create blocks — `process_message` handles all of that
  - Post-processing: extract shared helpers from `send_message` for response block lookup, relationship tracking, model info — used by both methods
- [ ] Add `send-message-streaming` command to sidecar
- [ ] Add `cancel-stream` command to sidecar (sets cancel flag + cancels TTS tasks)
- [ ] Test: verify events appear in sidecar stdout as JSONL

### Phase 2: Rust Commands
Files: `qubes-gui/src-tauri/src/lib.rs`

- [ ] Add `streaming: Option<bool>` and `total_chunks: Option<i64>` to `ChatResponse` struct (existing fields stay, new ones are None for non-streaming)
- [ ] Add `send_message_streaming` Tauri command (mirrors `send_message`, 300s timeout in seconds, same ChatResponse return type)
- [ ] Add `cancel_stream` Tauri command (short timeout, no streaming events)
- [ ] Add both to `generate_handler![]` command registration list
- [ ] Verify: `tts-text-token`, `tts-audio-ready`, `tts-stream-end` events flow through existing stream forwarding (lib.rs:178-192) — should work with zero code changes

### Phase 3: Frontend Streaming Playback
Files: `AudioContext.tsx`

- [ ] Add ordered chunk map (`Map<number, string | null>`) and `nextExpectedChunk` ref
- [ ] Listen for `tts-audio-ready` events — insert into ordered map by chunk_index
- [ ] `playNextStreamingChunk()` — always plays next expected index, skips null (error), waits if not yet arrived
- [ ] Modify `audio-playback-ended` handler — check streaming state before existing chunk logic
- [ ] Listen for `tts-stream-end` — mark streaming done
- [ ] Add `resetStreamingState()` and `startStreamingPlayback()` helpers
- [ ] Handle error chunks: null entries in map are skipped during playback

### Phase 4: Frontend Streaming Messages
Files: `ChatInterface.tsx`

- [ ] Add `streaming?: boolean` and `total_chunks?: number` to TypeScript `ChatResponse` interface
- [ ] Add streaming text state: `streamingText`, `isStreaming`, `streamingMessageIdRef`
- [ ] Performance: accumulate tokens in ref, flush to state on 100ms interval (not per-token setState)
  - `streamingTextRef` (ref, no re-render) + `setStreamingText` (state, flushed at 10Hz)
  - `startStreamingText()` / `stopStreamingText()` helpers manage the interval
- [ ] Listen for `tts-text-token` events — update ref (no re-render), clear `isLoading` on first token
- [ ] Listen for `tts-stream-end` events — finalize message with `cleanContentForDisplay(full_text)`
- [ ] Render streaming message bubble inline (text grows as tokens arrive, no TypewriterText)
- [ ] Extract `sendToBackend()` helper — branches streaming vs non-streaming based on setting
  - Replaces BOTH `invoke('send_message')` call sites (line 1040 for files+PDFs, line 1089 for regular messages)
  - Both sites already call `prepareMessageForIPC()` before this — no change needed
  - Streaming path: calls `startStreamingText()`, generates messageId, calls `startStreamingPlayback()`, invokes `send_message_streaming`
  - Non-streaming path: existing `invoke('send_message')` unchanged
- [ ] Gate `generateAndPlayTTS` useEffect: skip when response has `streaming: true` (clear pending state)
- [ ] Handle interruption: stop audio + cancel stream + resetStreamingState + stopStreamingText when user sends new message
- [ ] Escape key handler: add streaming cleanup (stopAudio, resetStreamingState, cancel_stream, clear typewriter)
- [ ] Handle `tts-stream-end` with `error` field: show partial response with error indicator
- [ ] Settings toggle: streaming TTS on/off per-qube (`streaming_tts_enabled` in chain_state, defaults true)

### Phase 5: Stream Mode
Files: `ChatInterface.tsx`, new `StreamModeIndicator.tsx`

- [ ] Replace 🎤 button: toggles Stream Mode (🎤 → 🛑)
- [ ] Disable Stream Mode button when TTS is off (tooltip: "Enable TTS to use Stream Mode")
- [ ] Disable Stream Mode button in group chat context
- [ ] Reuse existing `recognitionRef` — save original handlers, reconfigure for Stream Mode, restore on exit
- [ ] Hide existing mic button when Stream Mode is active (prevent handler conflicts)
- [ ] Continuous speech recognition with silence detection (1.5s default)
- [ ] `recognition.onend` auto-restart: Web Speech API can silently stop even with `continuous=true` — auto-restart with 300ms backoff if still in Stream Mode
- [ ] User voice typewriter: show interim transcript in chat bubble as user speaks
- [ ] Auto-send on silence timeout
- [ ] Interrupt detection: user speaks while qube is responding → clear silence timer, stop + cancel + resetStreamingState, restart silence timer for new transcript
- [ ] Auto-listen: resume mic after qube finishes (if still in Stream Mode)
- [ ] `applySttAliases()` applied to voice transcript
- [ ] Stream Mode indicator bar (pulsing dot, "Stream Mode active — speaking to [qube name]")
- [ ] Keyboard shortcut: Ctrl+M to toggle Stream Mode

### Phase 6: Polish & Edge Cases
- [ ] Settings: silence timeout slider, auto-listen toggle
- [ ] Audio replay button on qube response messages
- [ ] Qube avatar glow/pulse while speaking
- [ ] Auto-lock handler: cancel stream + stop audio before locking
- [ ] Graceful fallback: if streaming fails, fall back to current non-streaming path
- [ ] Test with TTS disabled: typewriter works, no audio, Stream Mode button disabled
- [ ] Test with document attachments: PDFs/images process before streaming starts
- [ ] Test with all 8 AI providers
- [ ] Test with all 7 TTS providers
- [ ] Test TTS failure mid-stream: chunk skipped, subsequent chunks play
- [ ] Test interruptions: during tool calls, mid-sentence, between sentences
- [ ] Test auto-anchor: verify blocks anchor correctly during/after streaming
- [ ] Test auto-lock mid-stream: partial response saved, clean resume after unlock
- [ ] Test Stream Mode: rapid interruptions, long silences, background noise
- [ ] Test self-evaluation: verify no TTS events from post-response evaluation
- [ ] Browser fallback: hide Stream Mode button if SpeechRecognition unavailable

---

## Files Modified

| File | Changes |
|------|---------|
| `ai/reasoner.py` | Add `token_callback` param to `process_input()`, `_emit_response_tokens()` helper, `_cancel_streaming` flag |
| `core/qube.py` | Add `token_callback` param to `process_message()`, pass through to `process_input()` |
| `gui_bridge.py` | Add `send_message_streaming()`, `_generate_and_emit_sentence()`, streaming locks, TTS task tracking. Extract `_get_latest_response_block()`, `_record_relationship_interaction()`, `_get_current_model_info()` shared helpers from `send_message()`. |
| `audio/audio_manager.py` | Add `extract_complete_sentences()`, `generate_sentence_audio()`, `clean_text_for_tts()` |
| `sidecar_server.py` | Add `send-message-streaming`, `cancel-stream` commands |
| `qubes-gui/src-tauri/src/lib.rs` | Add `send_message_streaming`, `cancel_stream` commands |
| `qubes-gui/src/contexts/AudioContext.tsx` | Ordered streaming chunk map, event listeners, `resetStreamingState()` |
| `qubes-gui/src/components/chat/ChatInterface.tsx` | Stream Mode, streaming text display, streaming send, interrupts |
| `qubes-gui/src/components/chat/StreamModeIndicator.tsx` | New — mic status indicator |
| `qubes-gui/src/components/tabs/SettingsTab.tsx` | Streaming TTS settings |

**No changes needed:**
- `lib.rs` stream event forwarding (line 178-192) — new event types pass through `_ => stream_type` automatically
- Block system — `process_message()` handles all block creation identically to non-streaming path
- Tool registry — tool execution unchanged, happens before streaming
- TTS providers — `synthesize_file()` per sentence, no API changes
- AI providers — uses existing `generate()`, no changes needed
- TypewriterText — not used in streaming mode (streaming text renders directly)

---

## Future Enhancements

- **True LLM streaming**: Use `stream_generate()` on the final iteration instead of emitting from complete response. Requires either (a) knowing in advance that no tool calls will occur, or (b) handling tool calls mid-stream. Would shave off LLM generation time from the latency.
- **Chatterbox-Turbo**: Add as local TTS provider (350M params, voice cloning, emotion control, native streaming, 23 languages, MIT license)
- **OpenAI Realtime API**: Full speech-to-speech via WebSocket (`gpt-realtime` / `gpt-realtime-mini`) for lowest possible latency with native tool calling
- **PersonaPlex**: Local full-duplex for power users with 24GB+ NVIDIA GPU
- **Audio-level streaming**: Pipe audio bytes directly to player (skip file I/O) for sub-100ms latency
- **Wake word**: "Hey [qube name]" activation for hands-free Stream Mode
- **Multi-language Stream Mode**: Match `recognition.lang` to qube's language setting
