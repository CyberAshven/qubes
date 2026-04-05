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
    → qube.process_message() runs tool loop as normal (non-streaming)
    → Final iteration: model.stream_generate() yields tokens
      → Tokens emitted via send_stream("tts-text-token", {token})
      → Sentence buffer accumulates tokens
      → Sentence complete → generate TTS for this sentence
      → send_stream("tts-audio-ready", {audio_path, chunk_index})
      → Continue streaming next sentence...
    → send_stream("tts-stream-end", {total_chunks, full_text})
    → Return final result (for block creation)

Frontend receives events as they arrive:
  → "tts-text-token" → update typewriter (text-first mode)
  → "tts-audio-ready" → queue audio, play first chunk immediately
  → "audio-playback-ended" → play next queued chunk
  → "tts-stream-end" → mark streaming complete
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

### Backend: Reasoner Streaming (ai/reasoner.py)

The approach: run the existing tool loop using `generate()` as-is. When the final iteration produces text (no tool calls), emit the already-complete response token-by-token to the callback. This avoids a second API call and preserves real token usage data.

**Key design decisions:**
- No `stream_generate()` used — we use the complete response from `generate()` and simulate streaming by emitting word-by-word. This gives us real `response.usage` data and costs nothing extra.
- Token emission is throttled (~20ms per word) to feel natural and give TTS time to generate between sentences.
- The `_cancel_streaming` flag is checked in the emission loop to support interruptions.
- The existing `process_input()` stays completely unchanged. The new method is additive.

```python
import asyncio

async def process_input_streaming(
    self,
    input_message: str,
    sender_id: str = "human",
    token_callback=None,       # Called with each text token
    **kwargs
) -> str:
    """
    Process input with streaming on the final text response.
    
    Tool-calling iterations use generate() as normal (non-streaming).
    The final iteration emits the complete response word-by-word
    via token_callback for progressive TTS generation.
    """
    self._cancel_streaming = False
    
    # ... [same setup as process_input: dynamic params, model loading,
    #      system prompt, context building, etc.] ...
    
    for iteration in range(max_iterations):
        # ALL iterations use non-streaming generate()
        response = await self.model.generate(
            messages=context_messages,
            tools=tools,
            temperature=temperature
        )
        
        if response.tool_calls:
            # Tool calls detected — execute them (identical to current code)
            # ... [existing tool execution, loop detection, switch_model] ...
            continue
        
        # NO tool calls — this is the final response.
        # Emit the complete text progressively for streaming TTS.
        if token_callback and response.content:
            # Split into small chunks (words + punctuation) for natural pacing
            import re
            tokens = re.findall(r'\S+\s*', response.content)
            
            for token in tokens:
                if self._cancel_streaming:
                    break
                token_callback(token)
                await asyncio.sleep(0.02)  # 20ms throttle — natural pacing
        
        # Real usage data from generate() — no estimation needed
        self.last_usage = response.usage
        self.last_model_used = self.model.model_name
        
        return response.content
```

**Why not use `stream_generate()`?**
- `generate()` returns the complete response + real token usage in a single API call
- `stream_generate()` would require a second API call (wasted tokens/cost) since we already called `generate()` to check for tool calls
- `stream_generate()` doesn't return usage data (would need estimation)
- The UX is identical — frontend receives tokens progressively either way
- The 20ms throttle between words provides natural pacing and gives TTS generation time to work between sentences

**When would we use `stream_generate()` in the future?**
If we eliminate the need to check for tool calls first (e.g., model indicates "I'm done with tools" via a flag), we could stream the final response directly from the API for even lower latency. This is a future optimization when provider APIs support it better.

**IMPORTANT:** The `token_callback` is **synchronous** (not awaited). It must not block. The callback appends tokens to a buffer and emits events — TTS generation is fired as a separate async task (see GUIBridge section below).

**IMPORTANT:** The existing `process_input()` stays completely unchanged. The streaming sidecar command calls the new method. Non-streaming commands still use the original.

### Backend: Streaming Message Handler (gui_bridge.py)

New method that combines send_message + generate_speech into one streaming flow.

**Key design decisions:**
- The `token_callback` is synchronous (cannot block the LLM stream). It buffers tokens and checks for sentence boundaries.
- When a sentence completes, TTS is spawned as an `asyncio.Task` — it runs concurrently with the LLM continuing to generate tokens.
- TTS results are emitted in order via a queue, even if they complete out of order.
- Text is cleaned (markdown, URLs, code blocks stripped) before TTS, same as current `generate_speech_file()`.
- Pre/post processing matches `qube.process_message()`: dedup check, MESSAGE block creation, action block injection, token usage tracking.

```python
# Per-qube streaming locks (class-level)
_streaming_locks: Dict[str, asyncio.Lock] = {}

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
    # ... [same setup as send_message: load qube, master key, 
    #      process documents, start session, dedup check,
    #      create incoming MESSAGE block — mirrors qube.process_message()] ...
    
    tts_enabled = qube.chain_state.get_tts_enabled()
    sentence_buffer = ""
    chunk_index = 0
    full_response = ""
    tts_tasks = []       # (chunk_index, asyncio.Task) — ordered
    audio_paths = []
    
    async def on_token(token):
        """Async callback — awaited in the streaming loop."""
        nonlocal sentence_buffer, chunk_index, full_response
        full_response += token
        sentence_buffer += token
        
        # Emit text token for frontend typewriter (always, even if TTS off)
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
                        qube, clean_sentence, chunk_index,
                        qube_id, stream_callback, is_final=False
                    ),
                    timeout=30.0  # Per-sentence TTS timeout
                )
            )
            tts_tasks.append((chunk_index, task))
    
    # Process message with streaming
    response_text = await qube.reasoner.process_input_streaming(
        input_message=message,
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
                        qube, clean, chunk_index,
                        qube_id, stream_callback, is_final=True
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
        except asyncio.TimeoutError:
            logger.warning("tts_sentence_timeout", chunk=idx, qube_id=qube_id)
    
    # Emit stream-end
    if stream_callback:
        await stream_callback("tts-stream-end", {
            "qube_id": qube_id,
            "total_chunks": chunk_index,
            "full_text": full_response,
        })
    
    # Create outgoing MESSAGE block with token usage
    # (mirrors qube.process_message post-processing)
    qube.add_message(
        message_type="qube_to_human",
        recipient_id="human",
        message_body=response_text,
        conversation_id="default",
        temporary=True,
        input_tokens=qube.reasoner.last_usage.get("prompt_tokens"),
        output_tokens=qube.reasoner.last_usage.get("completion_tokens"),
    )
    
    return {
        "success": True,
        "response": response_text,
        "block_number": block_number,
        "audio_paths": [str(p) for p in audio_paths],
        "total_chunks": chunk_index,
        "streaming": True,  # Signal to frontend: TTS already handled
    }

async def _generate_and_emit_sentence(
    self, qube, sentence, chunk_index, qube_id, stream_callback, is_final
):
    """Generate TTS for one sentence and emit audio-ready event."""
    try:
        audio_path = await qube.audio_manager.generate_sentence_audio(
            text=sentence,
            chunk_index=chunk_index,
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
        return None
```

**`clean_text_for_tts()`** reuses the existing text cleaning logic from `AudioManager.generate_speech_file()` (removes `**bold**`, `*actions*`, URLs, code blocks, emoji shortcodes).

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
async def _handle_cancel_stream(self, bridge, params, secrets, request_id):
    """Cancel an in-progress streaming response."""
    qube_id = params["qube_id"]
    # Set cancellation flag on the qube's reasoner
    qube = bridge.orchestrator.qubes.get(qube_id)
    if qube and qube.reasoner:
        qube.reasoner._cancel_streaming = True
    return {"success": True}
```

### Frontend: Streaming Audio Queue (AudioContext.tsx)

```typescript
// NEW: Event-driven chunk queue for streaming
const streamingChunkQueue = useRef<string[]>([]);
const isStreamingMode = useRef(false);

// Listen for streamed audio chunks
useEffect(() => {
    const unlisten = listen<{
        qube_id: string;
        audio_path: string;
        chunk_index: number;
        is_final: boolean;
    }>('tts-audio-ready', async (event) => {
        const { audio_path, chunk_index, is_final } = event.payload;
        
        streamingChunkQueue.current.push(audio_path);
        
        if (is_final) {
            isStreamingMode.current = false;
        }
        
        // Start playing if this is the first chunk
        if (chunk_index === 1 && !isPlaying) {
            setIsPlaying(true);
            playNextStreamingChunk();
        }
    });
    
    return () => { unlisten.then(u => u()); };
}, []);

const playNextStreamingChunk = async () => {
    const nextPath = streamingChunkQueue.current.shift();
    if (!nextPath) {
        // Queue empty — either waiting for next chunk or done
        if (!isStreamingMode.current) {
            // Stream complete, no more chunks
            setIsPlaying(false);
        }
        // If still streaming, audio-playback-ended will retry
        return;
    }
    
    try {
        const result = await invoke<NativePlayResult>('play_audio_native', {
            filePath: nextPath,
        });
        player.setDuration(result.duration);
        player.startPlayback();
    } catch (err) {
        console.error('Streaming chunk playback failed:', err);
        playNextStreamingChunk(); // Skip failed chunk
    }
};

// Existing audio-playback-ended handler — add streaming support:
listen('audio-playback-ended', () => {
    if (streamingChunkQueue.current.length > 0 || isStreamingMode.current) {
        // Streaming mode — play next from queue
        playNextStreamingChunk();
    } else if (/* existing chunk logic */) {
        // Non-streaming mode — existing behavior
    }
});
```

### Frontend: Stream Mode (ChatInterface.tsx)

```typescript
const [isStreamMode, setIsStreamMode] = useState(false);
const [isListening, setIsListening] = useState(false);
const [interimTranscript, setInterimTranscript] = useState('');
const silenceTimerRef = useRef<NodeJS.Timeout | null>(null);

const SILENCE_TIMEOUT_MS = 1500; // Configurable

// Listen for text tokens (typewriter in streaming mode)
useEffect(() => {
    const unlisten = listen<{
        qube_id: string;
        token: string;
    }>('tts-text-token', (event) => {
        if (isStreamMode || streamingTTSEnabled) {
            // Update typewriter text as tokens arrive
            appendToTypewriter(event.payload.token);
        }
    });
    return () => { unlisten.then(u => u()); };
}, [isStreamMode]);

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
            streamingChunkQueue.current = [];
            setIsPlaying(false);
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

The existing `send_message` has a 300s timeout in lib.rs. Streaming responses can take longer (tool loop + 20ms/word emission + TTS generation). The `send_message_streaming` Tauri command must use a longer timeout:

```rust
// In lib.rs:
let result = sidecar_execute_with_retry(
    "send-message-streaming", args, secrets,
    Some(&app_handle),
    Some(300_000)  // 5 minute timeout (same as send_message)
).await?;
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

The token callback must be async (awaited in the streaming loop) to safely emit events and spawn TTS tasks:

```python
# In process_input_streaming:
for token in tokens:
    if self._cancel_streaming:
        break
    await token_callback(token)    # Async — safe to emit events
    await asyncio.sleep(0.02)      # 20ms throttle
```

This means the callback in `send_message_streaming` is async too:

```python
async def on_token(token):
    nonlocal sentence_buffer, chunk_index, full_response
    full_response += token
    sentence_buffer += token
    
    # Emit text token — safe because we're in async context
    await stream_callback("tts-text-token", {
        "qube_id": qube_id,
        "token": token,
    })
    
    # Check for sentences and fire TTS as async tasks
    sentences, remaining = extract_complete_sentences(sentence_buffer)
    sentence_buffer = remaining
    for sentence in sentences:
        chunk_index += 1
        clean = clean_text_for_tts(sentence)
        if clean.strip():
            task = asyncio.create_task(
                asyncio.wait_for(
                    self._generate_and_emit_sentence(...),
                    timeout=30.0  # Per-sentence TTS timeout
                )
            )
            tts_tasks.append((chunk_index, task))
```

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

On timeout, `_generate_and_emit_sentence` raises `asyncio.TimeoutError`, caught by the existing exception handler, logged, and returns `None`. Frontend receives `tts-audio-ready` with `error: true` and skips the chunk.

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
    streamingChunkQueue.current = [];
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

SENTENCE_BOUNDARY = re.compile(r'(?<=[.!?])\s+|(?<=[.!?])$')

ABBREVIATIONS = {
    'Mr.', 'Mrs.', 'Ms.', 'Dr.', 'Jr.', 'Sr.', 'Prof.',
    'vs.', 'etc.', 'e.g.', 'i.e.', 'St.', 'Ave.', 'Blvd.',
    'Corp.', 'Inc.', 'Ltd.', 'approx.', 'dept.', 'est.',
    'No.', 'vol.', 'Rev.', 'Gen.', 'Gov.',
}

MIN_SENTENCE_LENGTH = 20
MAX_SENTENCE_LENGTH = 500

def extract_complete_sentences(buffer: str) -> tuple:
    """
    Extract complete sentences from buffer.
    Returns (complete_sentences: list[str], remaining_buffer: str)
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

        is_abbreviation = any(
            candidate.rstrip().endswith(abbr)
            for abbr in ABBREVIATIONS
        )
        if is_abbreviation:
            break

        sentences.append(candidate)
        remaining = remaining[match.end():]

    # Force split for run-on sentences
    if len(remaining) > MAX_SENTENCE_LENGTH:
        split_point = max(
            remaining.rfind(', ', 0, MAX_SENTENCE_LENGTH),
            remaining.rfind('; ', 0, MAX_SENTENCE_LENGTH),
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

**Block creation happens at the END of streaming** — the `send_message_streaming` method returns the full response text, and the existing block creation code runs on it. Identical to current behavior.

**Auto-anchor**: Threshold checks happen when blocks are added. Incoming MESSAGE block is created BEFORE streaming, outgoing MESSAGE block AFTER streaming completes, ACTION blocks during tool loop (before streaming). Timing is identical to current — no changes needed. If anchoring fires during streaming (from a tool call ACTION block pushing over threshold), it runs asynchronously and doesn't block streaming.

**Auto-sync to IPFS**: Triggered after anchoring completes. Runs on its own async schedule, completely independent of streaming. Syncs finalized (anchored) blocks, not in-progress data. No conflict.

---

## Interruption Handling

### User Sends New Message While Qube is Responding

Works in both text chat and Stream Mode:

```
1. User types/speaks new message
2. Frontend: invoke('stop_audio_native')     → kills audio player process
3. Frontend: invoke('cancel_stream', {qubeId}) → sets cancel flag on reasoner
4. Frontend: clear streamingChunkQueue        → discard pending audio
5. Backend: reasoner sees cancel flag         → stops token emission loop
6. Backend: saves partial response            → MESSAGE block with interrupted=true
7. Frontend: sends new message via streaming command
8. New response cycle begins
```

### Edge Case: Tool Call In Progress When Interrupted

If the user interrupts during tool execution (before streaming starts), the tool completes but the final response is never generated. The ACTION blocks are already created. The frontend simply sends the new message, and the backend starts a fresh cycle.

### Edge Case: TTS Generation In Progress

If a sentence's TTS is being generated when the user interrupts, we let it finish (it's fast, <1s) but don't play it. The audio file exists on disk but is never queued.

### Edge Case: TTS API Failure Mid-Stream

If TTS fails for one sentence (API error, rate limit, timeout):

1. `_generate_and_emit_sentence` catches the exception and logs it
2. Emits `tts-audio-ready` with `error: true` for that chunk index
3. Frontend receives the error event and marks that chunk as skipped
4. When `audio-playback-ended` fires for the previous chunk, frontend skips the failed chunk and advances to the next one
5. Result: sentences 1, 2 play → sentence 3 failed (small gap) → sentence 4 plays
6. Text typewriter is unaffected — all text still appears

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

### Edge Case: `pendingResponse` Double-Fire

The current `generateAndPlayTTS` useEffect watches `pendingResponse` to trigger TTS. With streaming, TTS is handled by the backend. Both must not run simultaneously.

Solution: `send_message_streaming` returns `{ streaming: true }` in the response. The existing useEffect checks this flag:

```typescript
// In ChatInterface.tsx generateAndPlayTTS effect:
if (pendingResponse?.streaming) {
    // TTS already handled by streaming pipeline — skip
    // Just add the message and activate typewriter
    addMessage(currentQube.qube_id, qubeResponse);
    setActiveTypewriterMessageId(messageId);
    return;
}
// ... existing TTS generation code for non-streaming path ...
```

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
# In send_message_streaming, gate TTS generation:
tts_enabled = qube.chain_state.get_tts_enabled()

def on_token(token):
    # ... emit tts-text-token always ...
    
    if tts_enabled:
        # ... sentence detection + TTS generation ...
    # If TTS disabled, tokens emit for typewriter only
```

---

## Document Attachments

PDF/image attachments are processed BEFORE the streaming reasoner call, identical to current `send_message`:

```python
async def send_message_streaming(self, qube_id, message, password, stream_callback, ...):
    # Process documents first (same as send_message)
    processed_message, doc_action_blocks = await self._process_documents_to_action_blocks(
        qube_id=qube_id, message=message, qube=qube
    )
    
    # Documents become ACTION blocks before tool loop
    # Then proceed with streaming...
```

No change to document handling — it runs before streaming starts.

---

## Self-Evaluation

Some modes trigger a self-evaluation call after the main response. This is a separate `process_input()` call (non-streaming) that runs AFTER `process_input_streaming()` returns. It:
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
| Streaming TTS | Settings > Voice | On | Stream audio sentence-by-sentence |
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
Files: `ai/reasoner.py`, `gui_bridge.py`, `audio/audio_manager.py`, `sidecar_server.py`

- [ ] Refactor `process_input()` — extract setup logic (model loading, context building, system prompt) into shared `_prepare_input()` to avoid duplication
- [ ] Add `process_input_streaming()` to `QubeReasoner`
  - Tool iterations: use `generate()` as current (non-streaming)
  - Final iteration: emit complete response word-by-word via async callback (20ms throttle)
  - Callback is async (awaited) — safe for event emission and task spawning
  - Preserves real `response.usage` data — no estimation needed
  - Add `_cancel_streaming` flag (initialized in `__init__`) for interruption support
- [ ] Add `extract_complete_sentences()` utility to `audio/audio_manager.py`
- [ ] Add `clean_text_for_tts()` — extract existing markdown/URL/code cleaning into reusable function
- [ ] Add `generate_sentence_audio()` to `AudioManager` (single-sentence TTS)
- [ ] Add `send_message_streaming()` to `GUIBridge`
  - Process document attachments before streaming (same as `send_message`)
  - Gate TTS generation on `tts_enabled` setting (text tokens always emit)
  - Buffers tokens into sentences, fires TTS as async tasks (non-blocking)
  - Per-sentence TTS timeout (30s) via `asyncio.wait_for`
  - Per-qube streaming lock prevents concurrent streaming calls
  - Emits: `tts-text-token`, `tts-audio-ready` (with `error` field), `tts-stream-end`
  - Returns `{ streaming: true }` flag in result
  - Creates MESSAGE block after streaming completes (mirrors `qube.process_message` post-processing)
- [ ] Add `send-message-streaming` command to sidecar
- [ ] Add `cancel-stream` command to sidecar
- [ ] Test: verify events appear in sidecar stdout as JSONL

### Phase 2: Rust Commands
Files: `qubes-gui/src-tauri/src/lib.rs`

- [ ] Add `send_message_streaming` Tauri command (mirrors `send_message` but with 300s timeout, same as send_message)
- [ ] Add `cancel_stream` Tauri command
- [ ] Verify: `tts-text-token`, `tts-audio-ready`, `tts-stream-end` events flow through existing stream forwarding (lib.rs:178-192) — should work with zero code changes

### Phase 3: Frontend Streaming Playback
Files: `AudioContext.tsx`

- [ ] Add `streamingChunkQueue` ref for dynamic audio queue
- [ ] Listen for `tts-audio-ready` events — push to queue, play first immediately
- [ ] Modify `audio-playback-ended` handler — check streaming queue before existing chunk logic
- [ ] Handle `tts-stream-end` — mark queue as final
- [ ] Handle empty queue during streaming (wait for next chunk vs done)

### Phase 4: Frontend Streaming Messages
Files: `ChatInterface.tsx`

- [ ] Add streaming send path: call `send_message_streaming` instead of `send_message`
- [ ] Gate `generateAndPlayTTS` useEffect: skip when response has `streaming: true`
- [ ] Listen for `tts-text-token` events — feed typewriter progressively
- [ ] Create message bubble BEFORE streaming starts (shows typewriter as tokens arrive)
- [ ] Handle interruption: stop audio + cancel stream when user sends new message
- [ ] Handle TTS error chunks: skip failed audio, advance to next
- [ ] Settings toggle: streaming TTS on/off (falls back to current behavior)

### Phase 5: Stream Mode
Files: `ChatInterface.tsx`, new `StreamModeIndicator.tsx`

- [ ] Replace 🎤 button: toggles Stream Mode (🎤 → 🛑)
- [ ] Disable Stream Mode button when TTS is off (tooltip: "Enable TTS to use Stream Mode")
- [ ] Disable Stream Mode button in group chat context
- [ ] Continuous speech recognition with silence detection (1.5s default)
- [ ] User voice typewriter: show interim transcript in chat bubble as user speaks
- [ ] Auto-send on silence timeout
- [ ] Interrupt detection: user speaks while qube is responding → clear silence timer, stop + cancel, restart silence timer for new transcript
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
| `ai/reasoner.py` | Add `process_input_streaming()`, `_cancel_streaming` flag |
| `gui_bridge.py` | Add `send_message_streaming()`, sentence buffer, stream callback |
| `audio/audio_manager.py` | Add `extract_complete_sentences()`, `generate_sentence_audio()` |
| `sidecar_server.py` | Add `send-message-streaming`, `cancel-stream` commands |
| `qubes-gui/src-tauri/src/lib.rs` | Add `send_message_streaming`, `cancel_stream` commands |
| `qubes-gui/src/contexts/AudioContext.tsx` | Streaming chunk queue, event listeners |
| `qubes-gui/src/components/chat/ChatInterface.tsx` | Stream Mode, voice typewriter, streaming send, interrupts |
| `qubes-gui/src/components/chat/StreamModeIndicator.tsx` | New — mic status indicator |
| `qubes-gui/src/components/tabs/SettingsTab.tsx` | Streaming TTS settings |

**No changes needed:**
- `lib.rs` stream event forwarding (line 178-192) — new event types pass through `_ => stream_type` automatically
- Block system — blocks created at end of streaming, identical to current
- Tool registry — tool execution unchanged, happens before streaming
- TTS providers — `synthesize_file()` per sentence, no API changes
- AI providers — uses existing `generate()`, no changes needed

---

## Future Enhancements

- **True LLM streaming**: Use `stream_generate()` on the final iteration instead of emitting from complete response. Requires either (a) knowing in advance that no tool calls will occur, or (b) handling tool calls mid-stream. Would shave off LLM generation time from the latency.
- **Chatterbox-Turbo**: Add as local TTS provider (350M params, voice cloning, emotion control, native streaming, 23 languages, MIT license)
- **OpenAI Realtime API**: Full speech-to-speech via WebSocket (`gpt-realtime` / `gpt-realtime-mini`) for lowest possible latency with native tool calling
- **PersonaPlex**: Local full-duplex for power users with 24GB+ NVIDIA GPU
- **Audio-level streaming**: Pipe audio bytes directly to player (skip file I/O) for sub-100ms latency
- **Wake word**: "Hey [qube name]" activation for hands-free Stream Mode
- **Multi-language Stream Mode**: Match `recognition.lang` to qube's language setting
