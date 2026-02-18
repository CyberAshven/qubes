# Persistent Sidecar Migration Plan

> Saved: 2026-02-18 | Status: Draft — awaiting approval

## Context

Every Tauri command currently spawns a new Python subprocess, pays ~550ms overhead (interpreter startup + imports + PBKDF2 key derivation + disk I/O), then exits. This makes Qubes behave as stateless functions rather than resident entities. The migration replaces this with a single persistent Python process that holds state in memory, communicating via newline-delimited JSON (JSONL) on the same stdin/stdout pipe.

The existing event watcher system (`watch-events`) already demonstrates the persistent process pattern — it's a long-running child process with stdin JSON for secrets and stdout JSON streaming. This migration generalizes that pattern to all commands.

**Key constraint:** The 240+ `GUIBridge` methods are NOT modified. Only the transport/dispatch layer changes.

---

## Phase 1: Python Sidecar Server

### 1A. Create `sidecar_server.py` (~350 lines)

**File:** `sidecar_server.py` (new, project root alongside `gui_bridge.py`)

JSONL server that reads requests from stdin, dispatches to `GUIBridge` methods, writes responses to stdout.

**Core classes:**

```
SidecarState
  - bridges: Dict[user_id, GUIBridge]      # Cached bridge instances
  - master_keys: Dict[user_id, bytes]       # Cached PBKDF2-derived keys
  - event_subscriptions: Dict[str, callback] # Active watch-events subscriptions
  - get_bridge(user_id, password) -> GUIBridge  # Get-or-create with key caching
  - invalidate_qube(user_id, qube_id)       # Remove stale qube from cache
  - invalidate_user(user_id)                # Clear all state on logout

SidecarServer
  - state: SidecarState
  - _output_lock: asyncio.Lock              # Prevent interleaved stdout lines
  - run()                                   # Main stdin read loop
  - send_response(response_dict)            # Thread-safe JSONL write
  - dispatch(command, args, secrets, request_id) -> result
```

**Protocol:**

| Direction | Format | Example |
|-----------|--------|---------|
| Request (stdin) | `{"id":"req_1","command":"send-message","args":["user1","ABCD1234","Hello"],"secrets":{"password":"..."}}` |
| Response (stdout) | `{"id":"req_1","result":{"success":true,"response":"Hi!",...}}` |
| Error (stdout) | `{"id":"req_1","error":"Qube not found"}` |
| Stream event (stdout) | `{"id":"req_1","stream":"tool_call","data":{...}}` |
| Chain event (stdout) | `{"id":"ev_ABCD","stream":"chain_state_event","data":{...}}` |
| Ready (stdout) | `{"id":null,"ready":true}` |
| Shutdown (stdin) | `{"id":"shutdown","command":"shutdown"}` |

**Dispatch approach:** A command registry dict mapping command names to `(method_name, arg_spec)` tuples. For the ~25 commands with complex arg parsing (argparse-style), individual handler functions. For the ~150 simple commands, a generic dispatcher that maps positional args to method params.

**Concurrency:** Each request dispatched as an `asyncio.Task`. Multiple in-flight commands supported (e.g., `generate-speech` overlapping with `send-message`). The `_output_lock` serializes stdout writes.

**Master key caching:** On first request with a password, `set_master_key()` runs PBKDF2 (600K iterations, ~300ms). The derived `orchestrator.master_key` (32 bytes) is stored in `SidecarState.master_keys`. Subsequent requests restore the cached key directly: `orchestrator.master_key = cached_key` — zero crypto overhead.

**Qube caching:** `UserOrchestrator.load_qube()` already caches in `self.qubes` dict. In sidecar mode, loaded qubes persist between requests automatically. Add LRU eviction at 20 qubes per user.

**Auto-anchor simplification:** Currently spawns a detached subprocess because the process is about to exit. In sidecar mode, the existing `_pending_anchor_task` (asyncio task) just runs in the background — no detached subprocess needed. Detection: if `sidecar_server` is the entry point, skip the detached subprocess spawn.

### 1B. Hook `gui_bridge.py` entry point (~5 lines changed)

Add `server` as a recognized command in `main()`, before the pre-bridge commands (around line 9291):

```python
if command == "server":
    from sidecar_server import SidecarServer
    server = SidecarServer()
    await server.run()
    return
```

This means the same `qubes-backend` binary supports both modes. CLI usage unchanged.

### 1C. Add tool event callback to `ai/tools/registry.py` (~10 lines changed)

**File:** `ai/tools/registry.py` (lines 1026, 1085)

Add a module-level callback variable:

```python
# Near top of file
_tool_event_callback = None  # Set by sidecar server for JSONL streaming

def set_tool_event_callback(callback):
    global _tool_event_callback
    _tool_event_callback = callback
```

Replace the two `print(f"__TOOL_EVENT__...")` calls with:

```python
if _tool_event_callback:
    _tool_event_callback(tool_event)
else:
    print(f"__TOOL_EVENT__{json.dumps(tool_event)}", file=sys.stderr, flush=True)
```

The sidecar server sets this callback before dispatching, passing a function that writes JSONL to stdout with the request_id.

### 1D. PyInstaller bundling

Add `sidecar_server` to hidden imports in `qubes-backend.spec` and `qubes-backend-heavy.spec`:

```python
hiddenimports=[
    # ... existing ...
    'sidecar_server',
]
```

---

## Phase 2: Rust Sidecar Manager

### 2A. Add sidecar process management to `lib.rs` (~300 lines)

**File:** `qubes-gui/src-tauri/src/lib.rs`

**New static state:**

```rust
static SIDECAR_PROCESS: Mutex<Option<SidecarProcess>> = Mutex::new(None);

struct SidecarProcess {
    child: std::process::Child,
    stdin: std::io::BufWriter<std::process::ChildStdin>,
    pending: Arc<Mutex<HashMap<String, PendingRequest>>>,
    reader_thread: Option<std::thread::JoinHandle<()>>,
}

struct PendingRequest {
    response_tx: tokio::sync::oneshot::Sender<Result<serde_json::Value, String>>,
    app_handle: Option<AppHandle>,
}
```

**New functions:**

| Function | Purpose |
|----------|---------|
| `start_sidecar(app_handle)` | Spawn `qubes-backend server`, start stdout reader thread, wait for `ready` message |
| `stop_sidecar()` | Send `shutdown` command, wait 500ms, force kill |
| `sidecar_execute(command, args, secrets, app_handle, timeout)` | Write JSONL request, register pending, await oneshot response |
| `sidecar_execute_with_retry(...)` | Try sidecar, on crash restart + retry up to 3x, fallback to subprocess |
| `fallback_subprocess_execute(...)` | Call existing `execute_with_secrets()` as safety net |

**Stdout reader thread:** Reads JSONL lines continuously. For each line:
- `{"ready": true}` → mark sidecar as ready
- `{"id": "...", "stream": "...", "data": {...}}` → find pending request by id, emit Tauri event via its `app_handle`
- `{"id": "...", "result": {...}}` → find pending request by id, send result through oneshot channel
- `{"id": "...", "error": "..."}` → find pending request by id, send error through oneshot channel

**Request ID generation:** Atomic counter (`static REQUEST_COUNTER: AtomicU64`) — no new crate dependency.

### 2B. Start sidecar on app launch

In the `.setup()` callback (around line 8053), after existing setup:

```rust
let app_handle = app.handle().clone();
std::thread::spawn(move || {
    if let Err(e) = start_sidecar(&app_handle) {
        eprintln!("[SIDECAR] Failed to start: {}", e);
        // App continues working — fallback to subprocess mode
    }
});
```

### 2C. Stop sidecar on app shutdown

In the `on_window_event` handler (around line 8109), alongside existing cleanup:

```rust
stop_sidecar();
```

### 2D. Migrate Tauri commands (164 call sites)

Each command changes from:

```rust
let mut cmd = prepare_backend_command()?;
cmd.arg("command-name").arg(&user_id).arg(&qube_id);
let mut secrets = HashMap::new();
secrets.insert("password", password.as_str());
let (stdout, _) = execute_with_secrets(cmd, secrets)?;
let response: T = serde_json::from_str(&stdout)?;
```

To:

```rust
let mut secrets = HashMap::new();
secrets.insert("password", password.as_str());
let result = sidecar_execute_with_retry(
    "command-name",
    vec![user_id, qube_id],
    secrets,
    None,    // app_handle (Some for streaming commands)
    None,    // timeout (Some(120) for TTS)
).await?;
let response: T = serde_json::from_value(result)?;
```

**Migration order:**
1. `authenticate` — validates the roundtrip, caches master key
2. `list-qubes` — simple, frequent, good benchmark
3. `send-message` — core command, validates caching benefit
4. `generate-speech` — validates timeout handling
5. `start-multi-qube-conversation` + friends — validates streaming
6. All remaining commands (batch)

**Streaming commands** (5 call sites using `execute_with_secrets_streaming`): Pass `Some(&app_handle)` so the reader thread can emit `tool-call-event` Tauri events.

**Timeout commands** (4 call sites using `execute_with_secrets_timeout`): Pass `Some(120)` for the 120s TTS timeout.

### 2E. Unify event watchers into sidecar

Replace the separate event watcher subprocess management:

**Remove:**
- `static EVENT_WATCHERS` (line 67)
- `start_event_watcher()` (lines 70-181)
- `stop_event_watcher()` (lines 183-199)
- `stop_all_event_watchers()` (lines 201-211)

**Replace `start_event_watcher_cmd`:**
```rust
#[tauri::command]
async fn start_event_watcher_cmd(app_handle: AppHandle, user_id: String, qube_id: String, password: String) -> Result<(), String> {
    let mut secrets = HashMap::new();
    secrets.insert("password", password.as_str());
    sidecar_execute(
        "watch-events",
        vec![user_id, qube_id],
        secrets,
        Some(&app_handle),
        None,  // No timeout — long-running
    ).await?;
    Ok(())
}
```

**Replace `stop_event_watcher_cmd`:**
```rust
sidecar_execute("stop-watch-events", vec![user_id, qube_id], ...).await?;
```

The sidecar server handles `watch-events` by subscribing to the qube's `Events` object and streaming chain state events as JSONL lines. The `stop-watch-events` command unsubscribes.

---

## Phase 3: Optimization & Cleanup

### 3A. Warm-up on login

After `authenticate` succeeds, the Rust side immediately sends a `warm-up` command through the sidecar. The Python side pre-imports heavy modules (`ai.tools.registry`, `core.qube`) and confirms the master key is cached.

### 3B. Remove old subprocess functions

Once all 164 call sites are migrated and tested:

- Mark `execute_with_secrets()`, `execute_with_secrets_timeout()`, `execute_with_secrets_streaming()` as `#[allow(dead_code)]` (keep as fallback)
- Or remove entirely if fallback is handled at the `sidecar_execute_with_retry` level

### 3C. Memory management

- LRU eviction: cap cached qubes at 20 per user
- Logout cleanup: `invalidate_user()` clears all cached state
- Periodic heartbeat: sidecar sends heartbeat every 30s, Rust detects dead sidecar

### 3D. Performance verification

Benchmark before/after for:
- `list-qubes` (cold vs warm)
- `send-message` (first message vs subsequent)
- `generate-speech` (Kokoro TTS with model already loaded)
- Group chat round-trip (multiple qubes, prefetching)

---

## Critical Files

| File | Changes | Lines |
|------|---------|-------|
| `sidecar_server.py` | **NEW** — JSONL server, dispatch, state caching | ~350 |
| `gui_bridge.py` | Add `server` command routing (~line 9291) | ~5 |
| `ai/tools/registry.py` | Add tool event callback hook (lines 1026, 1085) | ~10 |
| `qubes-gui/src-tauri/src/lib.rs` | Sidecar manager, migrate 164 call sites | ~300 new + ~164 modified |
| `qubes-gui/src-tauri/qubes-backend*.spec` | Add `sidecar_server` to hidden imports | ~2 |

## What Does NOT Change

- All 240+ `GUIBridge` method bodies — untouched
- `orchestrator/user_orchestrator.py` — untouched (caching is automatic)
- `core/qube.py` — untouched
- React frontend — still calls `invoke()` and gets responses
- CLI usage — `gui_bridge.py` subprocess mode still works
- On-disk format — blocks, chain state, encryption all identical
- Build pipeline — same PyInstaller `--onedir`, same Tauri bundling

## Expected Performance

| Operation | Current (subprocess) | Sidecar (warm) | Improvement |
|-----------|---------------------|-----------------|-------------|
| Python startup + imports | ~200ms | 0ms (already running) | -200ms |
| PBKDF2 key derivation | ~300ms | 0ms (cached) | -300ms |
| Load qube from disk | ~50ms | 0ms (cached) | -50ms |
| Total overhead per command | ~550ms | ~5ms (JSONL roundtrip) | ~99% reduction |
| `list-qubes` (5 qubes) | ~800ms | ~50ms | ~94% reduction |
| `send-message` (qube loaded) | ~600ms + AI time | ~10ms + AI time | -590ms latency |

## Verification Plan

1. **Unit test sidecar protocol:** Pipe JSONL requests to `sidecar_server.py`, verify responses
   ```bash
   echo '{"id":"1","command":"check-first-run","args":[],"secrets":{}}' | python sidecar_server.py
   ```

2. **Integration test with Rust:** Start sidecar via `lib.rs`, send `authenticate` + `list-qubes`, verify roundtrip

3. **Benchmark:** Compare latency for 10 sequential `list-qubes` calls: subprocess vs sidecar

4. **Crash recovery test:** Kill sidecar process mid-request, verify auto-restart + retry

5. **Streaming test:** Send `send-message` that triggers tool calls, verify `tool-call-event` events reach frontend

6. **Event watcher test:** Start `watch-events`, trigger a chain state change, verify `chain-state-event` reaches frontend

7. **Full app test:** Launch Tauri app, login, create qube, chat, anchor, verify all features work end-to-end

---

## Risk Mitigation

1. **Fallback always available.** `fallback_subprocess_execute()` calls the old `execute_with_secrets*()` functions. If sidecar fails, every command still works via subprocess.

2. **Incremental migration.** Commands can be migrated one at a time. Each Tauri command independently uses either sidecar or subprocess.

3. **No GUIBridge method changes.** The 240+ methods in `GUIBridge` are called directly by `sidecar_server.py`. Zero changes to existing business logic.

4. **Stdin/stdout security preserved.** Secrets are still passed via the stdin pipe. Never to disk, env vars, or command line args.

5. **PyInstaller compatibility.** The same binary (`qubes-backend`) supports both `server` mode (persistent) and individual commands (subprocess). No build pipeline changes needed.
