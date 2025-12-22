use std::process::Command;
use std::path::PathBuf;
use serde::{Deserialize, Serialize};
use tauri::Manager;

#[cfg(target_os = "windows")]
use std::os::windows::process::CommandExt;

// Input validation function to prevent path traversal and command injection
fn validate_identifier(input: &str, field_name: &str) -> Result<(), String> {
    // Check for empty input
    if input.is_empty() {
        return Err(format!("{} cannot be empty", field_name));
    }

    // Check for path traversal attempts
    if input.contains("..") || input.contains("/") || input.contains("\\") {
        return Err(format!("{} contains invalid characters (path traversal attempt)", field_name));
    }

    // Check for null bytes or other control characters
    if input.chars().any(|c| c.is_control()) {
        return Err(format!("{} contains invalid control characters", field_name));
    }

    // Limit length to prevent DoS
    if input.len() > 256 {
        return Err(format!("{} is too long (max 256 characters)", field_name));
    }

    Ok(())
}

#[derive(Debug, Serialize, Deserialize)]
struct AuthResponse {
    success: bool,
    user_id: Option<String>,
    data_dir: Option<String>,
    error: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
struct ChatResponse {
    success: bool,
    qube_id: Option<String>,
    qube_name: Option<String>,
    message: Option<String>,
    response: Option<String>,
    timestamp: Option<String>,
    error: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
struct SpeechResponse {
    success: bool,
    audio_path: Option<String>,
    qube_id: Option<String>,
    error: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
struct DeleteResponse {
    success: bool,
    qube_id: Option<String>,
    error: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
struct SaveImageResponse {
    success: bool,
    qube_id: Option<String>,
    file_path: Option<String>,
    filename: Option<String>,
    error: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
struct UploadAvatarToIpfsResponse {
    success: bool,
    qube_id: Option<String>,
    qube_name: Option<String>,
    avatar_ipfs_cid: Option<String>,
    ipfs_gateway_url: Option<String>,
    message: Option<String>,
    error: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
struct AnalyzeImageResponse {
    success: bool,
    qube_id: Option<String>,
    description: Option<String>,
    error: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
struct MultiQubeConversationResponse {
    conversation_id: String,
    participants: Vec<serde_json::Value>,
    first_response: serde_json::Value,
}

#[derive(Debug, Serialize, Deserialize)]
struct ConversationMessageResponse {
    speaker_id: String,
    speaker_name: String,
    message: String,
    voice_model: String,
    turn_number: i32,
    conversation_id: String,
    is_final: bool,
}

#[derive(Debug, Serialize, Deserialize)]
struct ConversationSummaryResponse {
    conversation_id: String,
    total_turns: i32,
    participants: Vec<serde_json::Value>,
    conversation_history: Vec<serde_json::Value>,
    anchored: bool,
}

#[derive(Debug, Serialize, Deserialize)]
struct ConfiguredKeysResponse {
    providers: Vec<String>,
}

#[derive(Debug, Serialize, Deserialize)]
struct APIKeyResponse {
    success: bool,
    error: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
struct ValidationResponse {
    valid: bool,
    message: String,
    details: Option<serde_json::Value>,
}

// P2P Response Structs
#[derive(Debug, Serialize, Deserialize)]
struct OnlineQubesResponse {
    success: bool,
    online: Option<Vec<String>>,
    count: Option<i32>,
    error: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
struct IntroductionResponse {
    success: bool,
    relay_id: Option<String>,
    status: Option<String>,
    error: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
struct PendingIntroduction {
    relay_id: String,
    from_commitment: String,
    from_name: String,
    conversation_id: String,
    block_hash: String,
}

#[derive(Debug, Serialize, Deserialize)]
struct PendingIntroductionsResponse {
    success: bool,
    pending: Option<Vec<PendingIntroduction>>,
    error: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
struct AcceptIntroductionResponse {
    success: bool,
    from_name: Option<String>,
    from_commitment: Option<String>,
    error: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
struct GenerateIntroductionResponse {
    success: bool,
    message: Option<String>,
    error: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
struct EvaluateIntroductionResponse {
    success: bool,
    recommendation: Option<String>,
    reasoning: Option<String>,
    response_message: Option<String>,
    error: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
struct ProcessP2PMessageResponse {
    success: bool,
    response: Option<String>,
    model_used: Option<String>,
    usage: Option<serde_json::Value>,
    error: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
struct Connection {
    commitment: String,
    name: String,
    accepted_at: String,
}

#[derive(Debug, Serialize, Deserialize)]
struct ConnectionsResponse {
    success: bool,
    connections: Option<Vec<Connection>>,
    error: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
struct P2PSessionResponse {
    success: bool,
    session_id: Option<String>,
    participants: Option<Vec<serde_json::Value>>,
    error: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
struct P2PSessionsResponse {
    success: bool,
    sessions: Option<Vec<serde_json::Value>>,
    error: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
struct BlockPreferencesResponse {
    individual_auto_anchor: bool,
    individual_anchor_threshold: i32,
    group_auto_anchor: bool,
    group_anchor_threshold: i32,
}

#[derive(Debug, Serialize, Deserialize)]
struct RelationshipSettingsResponse {
    difficulty: String,
    description: String,
}

#[derive(Debug, Serialize, Deserialize)]
struct GoogleTTSPathResponse {
    path: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
struct SetPathResponse {
    success: bool,
    path: Option<String>,
    error: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
struct SkillsResponse {
    success: bool,
    qube_id: Option<String>,
    skills: Option<Vec<serde_json::Value>>,
    last_updated: Option<String>,
    summary: Option<serde_json::Value>,
    error: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
struct DifficultyPreset {
    name: String,
    description: String,
    min_interactions: MinInteractionsMap,
}

#[derive(Debug, Serialize, Deserialize)]
struct MinInteractionsMap {
    acquaintance: i32,
    friend: i32,
    close_friend: i32,
    best_friend: i32,
}

#[derive(Debug, Serialize, Deserialize)]
struct RelationshipResponse {
    success: bool,
    relationships: Vec<Relationship>,
    stats: serde_json::Value,
    error: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
struct Relationship {
    entity_id: String,
    entity_name: String,
    entity_type: String,
    status: String,
    trust: f32,
    has_met: bool,
    is_best_friend: bool,
    // Core Trust Metrics (5) - foundational earned qualities
    honesty: f32,
    reliability: f32,
    support: f32,
    loyalty: f32,
    respect: f32,
    // Social Metrics - Positive (14)
    friendship: f32,
    affection: f32,
    engagement: f32,
    depth: f32,
    humor: f32,
    understanding: f32,
    compatibility: f32,
    admiration: f32,
    warmth: f32,
    openness: f32,
    patience: f32,
    empowerment: f32,
    responsiveness: f32,
    expertise: f32,
    // Social Metrics - Negative (10)
    antagonism: f32,
    resentment: f32,
    annoyance: f32,
    distrust: f32,
    rivalry: f32,
    tension: f32,
    condescension: f32,
    manipulation: f32,
    dismissiveness: f32,
    betrayal: f32,
    // Tracked Statistics
    messages_sent: u32,
    messages_received: u32,
    collaborations_successful: u32,
    collaborations_failed: u32,
    first_contact: Option<u64>,
    last_interaction: Option<u64>,
    days_known: u32,
}

#[derive(Debug, Serialize, Deserialize)]
struct VisualizerSettingsResponse {
    enabled: bool,
    waveform_style: i32,
    color_theme: String,
    gradient_style: String,
    sensitivity: i32,
    animation_smoothness: String,
    audio_offset_ms: i32,
    frequency_range: i32,
    #[serde(default)]
    output_monitor: i32,
}

#[derive(Debug, Serialize, Deserialize)]
struct TrustPersonalityResponse {
    trust_profile: String,
}

#[derive(Debug, Serialize, Deserialize)]
struct GenericSuccessResponse {
    success: bool,
    message: Option<String>,
    error: Option<String>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
struct MonitorInfo {
    id: usize,
    name: String,
    width: u32,
    height: u32,
    x: i32,
    y: i32,
    is_primary: bool,
}

#[derive(Debug, Serialize, Deserialize)]
struct MonitorsResponse {
    monitors: Vec<MonitorInfo>,
}

#[derive(Debug, Serialize, Deserialize)]
struct TimelineDataPoint {
    block_number: u64,
    timestamp: u64,
    trust: f32,
    compatibility: f32,
    friendship: f32,
    affection: f32,
}

#[derive(Debug, Serialize, Deserialize)]
struct TimelineResponse {
    success: bool,
    timeline: Vec<TimelineDataPoint>,
    error: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
struct ExportQubeResponse {
    success: bool,
    file_path: Option<String>,
    block_count: Option<u32>,
    qube_name: Option<String>,
    qube_id: Option<String>,
    error: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
struct ImportQubeResponse {
    success: bool,
    qube_id: Option<String>,
    qube_name: Option<String>,
    block_count: Option<u32>,
    error: Option<String>,
}

// Chain Sync Response Types (NFT-Bundled Storage)
#[derive(Debug, Serialize, Deserialize)]
struct SyncToChainResponse {
    success: bool,
    ipfs_cid: Option<String>,
    encrypted_key: Option<String>,
    merkle_root: Option<String>,
    chain_length: Option<u32>,
    error: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
struct TransferQubeResponse {
    success: bool,
    transfer_txid: Option<String>,
    recipient_address: Option<String>,
    ipfs_cid: Option<String>,
    local_deleted: Option<bool>,
    error: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
struct ImportFromWalletResponse {
    success: bool,
    qube_id: Option<String>,
    qube_name: Option<String>,
    qube_dir: Option<String>,
    error: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
struct WalletQubeInfo {
    qube_id: String,
    qube_name: String,
    category_id: String,
    ipfs_cid: String,
    chain_length: u32,
    sync_timestamp: u64,
}

#[derive(Debug, Serialize, Deserialize)]
struct ScanWalletResponse {
    success: bool,
    qubes: Option<Vec<WalletQubeInfo>>,
    error: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
struct ResolvePublicKeyResponse {
    success: bool,
    public_key: Option<String>,
    found: bool,
    error: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
struct Qube {
    qube_id: String,
    name: String,
    ai_provider: String,
    ai_model: String,
    genesis_prompt: String,
    favorite_color: String,
    voice_model: Option<String>,
    tts_enabled: Option<bool>,
    creator: Option<String>,
    birth_timestamp: Option<u64>,
    home_blockchain: Option<String>,
    created_at: String,
    trust_score: Option<f32>,
    memory_blocks_count: Option<u32>,
    friends_count: Option<u32>,
    total_relationships: Option<u32>,
    best_friend: Option<String>,
    close_friends: Option<u32>,
    acquaintances: Option<u32>,
    strangers: Option<u32>,
    highest_trust: Option<f32>,
    lowest_trust: Option<f32>,
    total_messages_sent: Option<u32>,
    total_messages_received: Option<u32>,
    total_collaborations: Option<u32>,
    successful_joint_tasks: Option<u32>,
    failed_joint_tasks: Option<u32>,
    avg_reliability: Option<f32>,
    avg_honesty: Option<f32>,
    avg_responsiveness: Option<f32>,
    avg_compatibility: Option<f32>,
    status: String,
    // Blockchain metadata
    nft_category_id: Option<String>,
    mint_txid: Option<String>,
    recipient_address: Option<String>,
    public_key: Option<String>,
    genesis_block_hash: Option<String>,
    commitment: Option<String>,
    bcmr_uri: Option<String>,
    avatar_ipfs_cid: Option<String>,
    avatar_url: Option<String>,
    avatar_local_path: Option<String>,
    network: Option<String>,
    block_breakdown: Option<serde_json::Value>,
}

// Check if we're running as a bundled distribution (has qubes-backend sidecar)
fn is_bundled_distribution() -> bool {
    get_bundled_backend_path().is_some()
}

// Get path to the bundled backend executable (Tauri sidecar)
// In dev mode, always use Python directly for faster iteration
fn get_bundled_backend_path() -> Option<PathBuf> {
    // Skip bundled backend in dev mode - Python is much faster for development
    if cfg!(dev) {
        return None;
    }

    if let Ok(exe_path) = std::env::current_exe() {
        if let Some(exe_dir) = exe_path.parent() {
            // Check for Tauri sidecar (placed next to main exe)
            #[cfg(target_os = "windows")]
            let sidecar_name = "qubes-backend.exe";
            #[cfg(not(target_os = "windows"))]
            let sidecar_name = "qubes-backend";

            let sidecar_path = exe_dir.join(sidecar_name);
            if sidecar_path.exists() {
                return Some(sidecar_path);
            }

            // Also check macOS bundle location (inside .app/Contents/MacOS/)
            #[cfg(target_os = "macos")]
            {
                // exe_dir is already Contents/MacOS/ on macOS, so sidecar should be there
                // Already checked above, but let's also check Resources just in case
                if let Some(contents_dir) = exe_dir.parent() {
                    let resources_path = contents_dir.join("Resources").join(sidecar_name);
                    if resources_path.exists() {
                        return Some(resources_path);
                    }
                }
            }

            // Legacy: check for old distribution format (qubes-backend subfolder)
            #[cfg(target_os = "windows")]
            let legacy_path = exe_dir.join("qubes-backend").join("qubes-backend.exe");
            #[cfg(not(target_os = "windows"))]
            let legacy_path = exe_dir.join("qubes-backend").join("qubes-backend");

            if legacy_path.exists() {
                return Some(legacy_path);
            }
        }
    }
    None
}

// Get the path to the Python project directory
fn get_python_project_path() -> PathBuf {
    // First check if we're running as a bundled distribution
    if is_bundled_distribution() {
        if let Ok(exe_path) = std::env::current_exe() {
            if let Some(exe_dir) = exe_path.parent() {
                // Return the exe directory for bundled distribution
                return exe_dir.to_path_buf();
            }
        }
    }

    // Get current directory and navigate to project root
    let mut path = std::env::current_dir().unwrap();

    // Navigate up from release build directory if needed
    // Path could be: qubes-gui/src-tauri/target/release (when running exe)
    //            or: qubes-gui/src-tauri (when running dev)
    //            or: Qubes (when running from project root)

    // Keep going up until we find gui_bridge.py or reach the Qubes folder
    loop {
        // Check if gui_bridge.py exists in current directory
        let bridge_path = path.join("gui_bridge.py");
        if bridge_path.exists() {
            return path;
        }

        // Check folder name to stop at appropriate level
        let folder_name = path.file_name().and_then(|n| n.to_str());

        // If we're at "Qubes" folder, this is it
        if folder_name == Some("Qubes") {
            return path;
        }

        // If we're in release/debug, keep going up
        if folder_name == Some("release") || folder_name == Some("debug") {
            path.pop(); // Go up from release/debug
            continue;
        }

        // If we're in target, go up
        if folder_name == Some("target") {
            path.pop(); // Go up from target
            continue;
        }

        // If we're in src-tauri, go up
        if folder_name == Some("src-tauri") {
            path.pop(); // Go up from src-tauri
            continue;
        }

        // If we're in qubes-gui, go up to Qubes
        if folder_name == Some("qubes-gui") {
            path.pop(); // Go up from qubes-gui to Qubes
            return path;
        }

        // If we can't go up anymore, return current path
        if !path.pop() {
            return std::env::current_dir().unwrap();
        }
    }
}

fn get_python_bridge_path() -> PathBuf {
    // If bundled, return the backend exe path
    if let Some(bundled_path) = get_bundled_backend_path() {
        return bundled_path;
    }
    // Otherwise, return the gui_bridge.py path for development
    let mut path = get_python_project_path();
    path.push("gui_bridge.py");
    path
}

// Create a command to run the backend (bundled exe or Python script)
// Returns (Command, bool) where bool indicates if we should skip adding the bridge path
fn create_backend_command() -> (Command, bool) {
    // Check if we're running bundled distribution
    if let Some(bundled_path) = get_bundled_backend_path() {
        let mut cmd = Command::new(&bundled_path);
        // Hide console window on Windows
        #[cfg(target_os = "windows")]
        {
            const CREATE_NO_WINDOW: u32 = 0x08000000;
            cmd.creation_flags(CREATE_NO_WINDOW);
        }
        return (cmd, true); // true = skip bridge path argument
    }

    // Development mode - use Python
    let mut cmd = Command::new("python");

    // Hide console window on Windows
    #[cfg(target_os = "windows")]
    {
        const CREATE_NO_WINDOW: u32 = 0x08000000;
        cmd.creation_flags(CREATE_NO_WINDOW);
    }

    (cmd, false) // false = need to add bridge path argument
}

/// Prepares a backend command ready for adding command name and arguments.
/// Handles both bundled distribution and development mode automatically.
/// Returns the configured Command with current_dir and bridge_path (if needed) already set.
fn prepare_backend_command() -> Result<Command, String> {
    let (mut cmd, is_bundled) = create_backend_command();
    let project_root = get_python_project_path();

    cmd.current_dir(&project_root);

    // In development mode, add the bridge script path
    if !is_bundled {
        let bridge_path = get_python_bridge_path();
        if !bridge_path.exists() {
            return Err(format!("Python bridge not found at: {}", bridge_path.display()));
        }
        cmd.arg(&bridge_path);
    }

    Ok(cmd)
}

#[tauri::command]
async fn authenticate(username: String, password: String) -> Result<AuthResponse, String> {
    // Validate inputs
    validate_identifier(&username, "username")?;

    let bridge_path = get_python_bridge_path();
    let is_bundled = is_bundled_distribution();

    if !is_bundled && !bridge_path.exists() {
        return Err(format!("Python bridge not found at: {}", bridge_path.display()));
    }

    let project_root = get_python_project_path();
    let (mut cmd, skip_bridge_arg) = create_backend_command();
    cmd.current_dir(&project_root);

    // Only add bridge path in development mode
    if !skip_bridge_arg {
        cmd.arg(&bridge_path);
    }

    let output = cmd
        .arg("authenticate")
        .arg(&username)
        .arg(&password)
        .output()
        .map_err(|e| format!("Failed to execute Python bridge: {}", e))?;

    if !output.status.success() {
        let error = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python bridge error: {}", error));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let auth_response: AuthResponse = serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse JSON response: {}. Output: {}", e, stdout))?;

    Ok(auth_response)
}

#[tauri::command]
async fn list_qubes(user_id: String) -> Result<Vec<Qube>, String> {
    // Validate inputs
    validate_identifier(&user_id, "user_id")?;

    let bridge_path = get_python_bridge_path();
    let is_bundled = is_bundled_distribution();

    if !is_bundled && !bridge_path.exists() {
        return Err(format!("Python bridge not found at: {}", bridge_path.display()));
    }

    let project_root = get_python_project_path();
    let (mut cmd, skip_bridge_arg) = create_backend_command();
    cmd.current_dir(&project_root);

    if !skip_bridge_arg {
        cmd.arg(&bridge_path);
    }

    let output = cmd
        .arg("list-qubes")
        .arg(&user_id)
        .output()
        .map_err(|e| format!("Failed to execute Python bridge: {}", e))?;

    if !output.status.success() {
        let error = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python bridge error: {}", error));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);

    let qubes: Vec<Qube> = serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse JSON response: {}. Output: {}", e, stdout))?;

    Ok(qubes)
}

#[tauri::command]
async fn create_qube(
    user_id: String,
    name: String,
    genesis_prompt: String,
    ai_provider: String,
    ai_model: String,
    voice_model: String,
    wallet_address: String,
    password: String,
    encrypt_genesis: bool,
    favorite_color: String,
    avatar_file: Option<String>,
    generate_avatar: bool,
    avatar_style: Option<String>,
) -> Result<Qube, String> {
    // Validate inputs
    validate_identifier(&user_id, "user_id")?;

    let mut command = prepare_backend_command()?;
    command
        .arg("create-qube")
        .arg(&user_id)
        .arg("--name")
        .arg(&name)
        .arg("--genesis-prompt")
        .arg(&genesis_prompt)
        .arg("--ai-provider")
        .arg(&ai_provider)
        .arg("--ai-model")
        .arg(&ai_model)
        .arg("--voice-model")
        .arg(&voice_model)
        .arg("--wallet-address")
        .arg(&wallet_address)
        .arg("--password")
        .arg(&password)
        .arg("--encrypt-genesis")
        .arg(if encrypt_genesis { "true" } else { "false" })
        .arg("--favorite-color")
        .arg(&favorite_color);

    // Add avatar parameters
    if let Some(avatar_path) = avatar_file {
        command.arg("--avatar-file").arg(&avatar_path);
    } else if generate_avatar {
        command.arg("--generate-avatar");
        if let Some(style) = avatar_style {
            command.arg("--avatar-style").arg(&style);
        }
    }

    let output = command
        .output()
        .map_err(|e| format!("Failed to execute Python bridge: {}", e))?;

    if !output.status.success() {
        let error = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python bridge error: {}", error));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let qube: Qube = serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse JSON response: {}. Output: {}", e, stdout))?;

    Ok(qube)
}

#[tauri::command]
async fn prepare_qube_for_minting(
    user_id: String,
    name: String,
    genesis_prompt: String,
    ai_provider: String,
    ai_model: String,
    voice_model: String,
    wallet_address: String,
    password: String,
    encrypt_genesis: bool,
    favorite_color: String,
    avatar_file: Option<String>,
    generate_avatar: bool,
    avatar_style: Option<String>,
) -> Result<serde_json::Value, String> {
    // Validate inputs
    validate_identifier(&user_id, "user_id")?;

    let mut command = prepare_backend_command()?;
    command
        .arg("prepare-qube-for-minting")
        .arg(&user_id)
        .arg("--name")
        .arg(&name)
        .arg("--genesis-prompt")
        .arg(&genesis_prompt)
        .arg("--ai-provider")
        .arg(&ai_provider)
        .arg("--ai-model")
        .arg(&ai_model)
        .arg("--voice-model")
        .arg(&voice_model)
        .arg("--wallet-address")
        .arg(&wallet_address)
        .arg("--password")
        .arg(&password)
        .arg("--encrypt-genesis")
        .arg(if encrypt_genesis { "true" } else { "false" })
        .arg("--favorite-color")
        .arg(&favorite_color);

    // Add avatar parameters
    if let Some(avatar_path) = avatar_file {
        command.arg("--avatar-file").arg(&avatar_path);
    } else if generate_avatar {
        command.arg("--generate-avatar");
        if let Some(style) = avatar_style {
            command.arg("--avatar-style").arg(&style);
        }
    }

    let output = command
        .output()
        .map_err(|e| format!("Failed to execute Python bridge: {}", e))?;

    if !output.status.success() {
        let error = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python bridge error: {}", error));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let result: serde_json::Value = serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse JSON response: {}. Output: {}", e, stdout))?;

    Ok(result)
}

#[tauri::command]
async fn check_minting_status(
    user_id: String,
    registration_id: String,
    password: String,
) -> Result<serde_json::Value, String> {
    // Validate inputs
    validate_identifier(&user_id, "user_id")?;

    let mut command = prepare_backend_command()?;
    command
        .arg("check-minting-status")
        .arg(&user_id)
        .arg(&registration_id)
        .arg(&password);

    let output = command
        .output()
        .map_err(|e| format!("Failed to execute Python bridge: {}", e))?;

    if !output.status.success() {
        let error = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python bridge error: {}", error));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let result: serde_json::Value = serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse JSON response: {}. Output: {}", e, stdout))?;

    Ok(result)
}

#[tauri::command]
async fn submit_payment_txid(
    user_id: String,
    registration_id: String,
    txid: String,
) -> Result<serde_json::Value, String> {
    // Validate inputs
    validate_identifier(&user_id, "user_id")?;

    let mut command = prepare_backend_command()?;
    command
        .arg("submit-payment-txid")
        .arg(&user_id)
        .arg(&registration_id)
        .arg(&txid);

    let output = command
        .output()
        .map_err(|e| format!("Failed to execute Python bridge: {}", e))?;

    if !output.status.success() {
        let error = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python bridge error: {}", error));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let result: serde_json::Value = serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse JSON response: {}. Output: {}", e, stdout))?;

    Ok(result)
}

#[tauri::command]
async fn cancel_pending_minting(
    user_id: String,
    registration_id: String,
) -> Result<serde_json::Value, String> {
    // Validate inputs
    validate_identifier(&user_id, "user_id")?;

    let mut command = prepare_backend_command()?;
    command
        .arg("cancel-pending-minting")
        .arg(&user_id)
        .arg(&registration_id);

    let output = command
        .output()
        .map_err(|e| format!("Failed to execute Python bridge: {}", e))?;

    if !output.status.success() {
        let error = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python bridge error: {}", error));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let result: serde_json::Value = serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse JSON response: {}. Output: {}", e, stdout))?;

    Ok(result)
}

#[tauri::command]
async fn list_pending_registrations(
    user_id: String,
) -> Result<serde_json::Value, String> {
    // Validate inputs
    validate_identifier(&user_id, "user_id")?;

    let mut command = prepare_backend_command()?;
    command
        .arg("list-pending-registrations")
        .arg(&user_id);

    let output = command
        .output()
        .map_err(|e| format!("Failed to execute Python bridge: {}", e))?;

    if !output.status.success() {
        let error = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python bridge error: {}", error));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let result: serde_json::Value = serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse JSON response: {}. Output: {}", e, stdout))?;

    Ok(result)
}

#[tauri::command]
async fn send_message(user_id: String, qube_id: String, message: String, password: String) -> Result<ChatResponse, String> {
    use std::fs;

    // Validate inputs
    validate_identifier(&user_id, "user_id")?;
    validate_identifier(&qube_id, "qube_id")?;

    // If message is too long for command line, use a temp file
    if message.len() > 7000 {
        // Write message to a temporary file to avoid command-line length limits
        let temp_dir = std::env::temp_dir();
        let temp_file = temp_dir.join(format!("qubes_temp_message_{}.txt", std::process::id()));

        fs::write(&temp_file, &message)
            .map_err(|e| format!("Failed to write temp file: {}", e))?;

        let mut cmd = prepare_backend_command()?;
        let output = cmd
            .arg("send-message")
            .arg(&user_id)
            .arg(&qube_id)
            .arg(format!("@file:{}", temp_file.to_str().unwrap()))
            .arg(&password)
            .output()
            .map_err(|e| format!("Failed to execute backend: {}", e))?;

        // Clean up temp file
        let _ = fs::remove_file(&temp_file);

        if !output.status.success() {
            let error = String::from_utf8_lossy(&output.stderr);
            return Err(format!("Python bridge error: {}", error));
        }

        let stdout = String::from_utf8_lossy(&output.stdout);
        let chat_response: ChatResponse = serde_json::from_str(&stdout)
            .map_err(|e| format!("Failed to parse JSON response: {}. Output: {}", e, stdout))?;

        Ok(chat_response)
    } else {
        // Short message - use command line directly
        let mut cmd = prepare_backend_command()?;
        let output = cmd
            .arg("send-message")
            .arg(&user_id)
            .arg(&qube_id)
            .arg(&message)
            .arg(&password)
            .output()
            .map_err(|e| format!("Failed to execute backend: {}", e))?;

        if !output.status.success() {
            let error = String::from_utf8_lossy(&output.stderr);
            return Err(format!("Python bridge error: {}", error));
        }

        let stdout = String::from_utf8_lossy(&output.stdout);
        let chat_response: ChatResponse = serde_json::from_str(&stdout)
            .map_err(|e| format!("Failed to parse JSON response: {}. Output: {}", e, stdout))?;

        Ok(chat_response)
    }
}

#[tauri::command]
async fn generate_speech(user_id: String, qube_id: String, text: String, password: String) -> Result<SpeechResponse, String> {
    let mut cmd = prepare_backend_command()?;
    let output = cmd
        .arg("generate-speech")
        .arg(&user_id)
        .arg(&qube_id)
        .arg(&text)
        .arg(&password)
        .output()
        .map_err(|e| format!("Failed to execute backend: {}", e))?;

    if !output.status.success() {
        let error = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python bridge error: {}", error));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let speech_response: SpeechResponse = serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse JSON response: {}. Output: {}", e, stdout))?;

    Ok(speech_response)
}

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! You've been greeted from Rust!", name)
}

#[tauri::command]
fn force_exit() {
    std::process::exit(0);
}

#[tauri::command]
async fn check_sessions(user_id: String, qube_id: String) -> Result<serde_json::Value, String> {
    let mut cmd = prepare_backend_command()?;
    let output = cmd
        .arg("check-sessions")
        .arg(&user_id)
        .arg(&qube_id)
        .output()
        .map_err(|e| format!("Failed to execute backend: {}", e))?;

    if !output.status.success() {
        let error = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python bridge error: {}", error));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let response: serde_json::Value = serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse JSON response: {}. Output: {}", e, stdout))?;

    Ok(response)
}

#[tauri::command]
async fn anchor_session(user_id: String, qube_id: String, password: String) -> Result<serde_json::Value, String> {
    let mut cmd = prepare_backend_command()?;
    let output = cmd
        .arg("anchor-session")
        .arg(&user_id)
        .arg(&qube_id)
        .arg(&password)
        .output()
        .map_err(|e| format!("Failed to execute backend: {}", e))?;

    if !output.status.success() {
        let error = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python bridge error: {}", error));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let response: serde_json::Value = serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse JSON response: {}. Output: {}", e, stdout))?;

    Ok(response)
}

#[tauri::command]
async fn discard_session(user_id: String, qube_id: String, password: String) -> Result<serde_json::Value, String> {
    let mut cmd = prepare_backend_command()?;
    let output = cmd
        .arg("discard-session")
        .arg(&user_id)
        .arg(&qube_id)
        .arg(&password)
        .output()
        .map_err(|e| format!("Failed to execute backend: {}", e))?;

    if !output.status.success() {
        let error = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python bridge error: {}", error));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let response: serde_json::Value = serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse JSON response: {}. Output: {}", e, stdout))?;

    Ok(response)
}

#[tauri::command]
async fn delete_session_block(user_id: String, qube_id: String, block_number: i32, password: String) -> Result<serde_json::Value, String> {
    let mut cmd = prepare_backend_command()?;
    let output = cmd
        .arg("delete-session-block")
        .arg(&user_id)
        .arg(&qube_id)
        .arg(block_number.to_string())
        .arg(&password)
        .output()
        .map_err(|e| format!("Failed to execute Python bridge: {}", e))?;

    if !output.status.success() {
        let error = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python bridge error: {}", error));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let response: serde_json::Value = serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse JSON response: {}. Output: {}", e, stdout))?;

    Ok(response)
}

#[tauri::command]
async fn get_audio_base64(file_path: String) -> Result<String, String> {
    use std::fs;
    use std::path::Path;
    use base64::{Engine as _, engine::general_purpose};

    // Convert to absolute path if relative
    let path = Path::new(&file_path);
    let absolute_path = if path.is_absolute() {
        path.to_path_buf()
    } else {
        // Get project root (go up from src-tauri)
        let project_root = get_python_project_path();
        project_root.join(&file_path)
    };

    // Read the audio file
    let audio_data = fs::read(&absolute_path)
        .map_err(|e| format!("Failed to read audio file: {}", e))?;

    // Convert to base64
    let base64_data = general_purpose::STANDARD.encode(&audio_data);

    // Determine MIME type based on file extension
    let mime_type = if file_path.ends_with(".wav") {
        "audio/wav"
    } else if file_path.ends_with(".mp3") {
        "audio/mpeg"
    } else {
        "audio/mpeg"  // Default fallback
    };

    // Return as data URL with correct MIME type
    Ok(format!("data:{};base64,{}", mime_type, base64_data))
}

#[tauri::command]
async fn get_qube_blocks(
    user_id: String,
    qube_id: String,
    password: String,
    limit: Option<i32>,
    offset: Option<i32>
) -> Result<serde_json::Value, String> {
    // Validate inputs
    validate_identifier(&user_id, "user_id")?;
    validate_identifier(&qube_id, "qube_id")?;

    
    // Use defaults if not provided (100 blocks, offset 0)
    let limit_val = limit.unwrap_or(100);
    let offset_val = offset.unwrap_or(0);

    let mut cmd = prepare_backend_command()?;
    let output = cmd
        .arg("get-qube-blocks")
        .arg(&user_id)
        .arg(&qube_id)
        .arg(&password)
        .arg(limit_val.to_string())
        .arg(offset_val.to_string())
        .output()
        .map_err(|e| format!("Failed to execute Python bridge: {}", e))?;

    if !output.status.success() {
        let error = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python bridge error: {}", error));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);

    let response: serde_json::Value = serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse JSON response: {}. Output: {}", e, stdout))?;

    Ok(response)
}

#[tauri::command]
async fn update_qube_config(
    user_id: String,
    qube_id: String,
    ai_model: Option<String>,
    voice_model: Option<String>,
    favorite_color: Option<String>,
    tts_enabled: Option<bool>,
    evaluation_model: Option<String>,
) -> Result<serde_json::Value, String> {
    let mut cmd = prepare_backend_command()?;

    // Add command and required args
    cmd.arg("update-qube-config")
        .arg(&user_id)
        .arg(&qube_id);

    // Add optional parameters (empty string if not provided)
    cmd.arg(ai_model.unwrap_or_default());
    cmd.arg(voice_model.unwrap_or_default());
    cmd.arg(favorite_color.unwrap_or_default());
    cmd.arg(if tts_enabled.unwrap_or(false) { "true" } else { "" });
    cmd.arg(evaluation_model.unwrap_or_default());

    let output = cmd
        .output()
        .map_err(|e| format!("Failed to execute backend: {}", e))?;

    if !output.status.success() {
        let error = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python bridge error: {}", error));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let response: serde_json::Value = serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse JSON response: {}. Output: {}", e, stdout))?;

    Ok(response)
}

#[tauri::command]
async fn delete_qube(user_id: String, qube_id: String) -> Result<DeleteResponse, String> {
    // Validate inputs
    validate_identifier(&user_id, "user_id")?;
    validate_identifier(&qube_id, "qube_id")?;

    let mut cmd = prepare_backend_command()?;
    let output = cmd
        .arg("delete-qube")
        .arg(&user_id)
        .arg(&qube_id)
        .output()
        .map_err(|e| format!("Failed to execute Python bridge: {}", e))?;

    if !output.status.success() {
        let error = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python bridge error: {}", error));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let delete_response: DeleteResponse = serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse JSON response: {}. Output: {}", e, stdout))?;

    Ok(delete_response)
}

#[tauri::command]
async fn save_image(user_id: String, qube_id: String, image_url: String) -> Result<SaveImageResponse, String> {
    let mut cmd = prepare_backend_command()?;
    let output = cmd
        .arg("save-image")
        .arg(&user_id)
        .arg(&qube_id)
        .arg(&image_url)
        .output()
        .map_err(|e| format!("Failed to execute Python bridge: {}", e))?;

    if !output.status.success() {
        let error = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python bridge error: {}", error));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let save_response: SaveImageResponse = serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse JSON response: {}. Output: {}", e, stdout))?;

    Ok(save_response)
}

#[tauri::command]
async fn upload_avatar_to_ipfs(user_id: String, qube_id: String, password: String) -> Result<UploadAvatarToIpfsResponse, String> {
    // Validate inputs
    validate_identifier(&user_id, "user_id")?;
    validate_identifier(&qube_id, "qube_id")?;

    let mut cmd = prepare_backend_command()?;
    let output = cmd
        .arg("upload-avatar-to-ipfs")
        .arg(&user_id)
        .arg(&qube_id)
        .arg(&password)
        .output()
        .map_err(|e| format!("Failed to execute Python bridge: {}", e))?;

    if !output.status.success() {
        let error = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python bridge error: {}", error));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let response: UploadAvatarToIpfsResponse = serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse JSON response: {}. Output: {}", e, stdout))?;

    Ok(response)
}

#[tauri::command]
async fn analyze_image(user_id: String, qube_id: String, image_base64: String, user_message: String, password: String) -> Result<AnalyzeImageResponse, String> {
    use std::fs;

    // Write image data to a temporary file to avoid command-line length limits
    let temp_dir = std::env::temp_dir();
    let temp_file = temp_dir.join(format!("qubes_temp_image_{}.b64", std::process::id()));

    fs::write(&temp_file, &image_base64)
        .map_err(|e| format!("Failed to write temp file: {}", e))?;

    let mut cmd = prepare_backend_command()?;
    let output = cmd
        .arg("analyze-image")
        .arg(&user_id)
        .arg(&qube_id)
        .arg(temp_file.to_str().unwrap())
        .arg(&user_message)
        .arg(&password)
        .output()
        .map_err(|e| format!("Failed to execute Python bridge: {}", e))?;

    // Clean up temp file
    let _ = fs::remove_file(&temp_file);

    if !output.status.success() {
        let error = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python bridge error: {}", error));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let analyze_response: AnalyzeImageResponse = serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse JSON response: {}. Output: {}", e, stdout))?;

    Ok(analyze_response)
}

#[tauri::command]
async fn start_multi_qube_conversation(
    user_id: String,
    qube_ids_str: String,
    initial_prompt: String,
    password: String,
    conversation_mode: String,
) -> Result<serde_json::Value, String> {
    // Validate inputs
    validate_identifier(&user_id, "user_id")?;

    let mut cmd = prepare_backend_command()?;
    let output = cmd
        .arg("start-multi-qube-conversation")
        .arg(&user_id)
        .arg(&qube_ids_str)
        .arg(&initial_prompt)
        .arg(&password)
        .arg(&conversation_mode)
        .output()
        .map_err(|e| format!("Failed to execute Python bridge: {}", e))?;

    if !output.status.success() {
        let error = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python bridge error: {}", error));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let response: serde_json::Value = serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse JSON response: {}. Output: {}", e, stdout))?;

    Ok(response)
}

#[tauri::command]
async fn get_next_speaker(
    user_id: String,
    conversation_id: String,
    password: String,
) -> Result<serde_json::Value, String> {
    let mut cmd = prepare_backend_command()?;
    let output = cmd
        .arg("get-next-speaker")
        .arg(&user_id)
        .arg(&conversation_id)
        .arg(&password)
        .output()
        .map_err(|e| format!("Failed to execute Python bridge: {}", e))?;

    if !output.status.success() {
        let error = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python bridge error: {}", error));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let response: serde_json::Value = serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse JSON response: {}. Output: {}", e, stdout))?;

    Ok(response)
}

#[tauri::command]
async fn continue_multi_qube_conversation(
    user_id: String,
    conversation_id: String,
    password: String,
) -> Result<serde_json::Value, String> {
    let mut cmd = prepare_backend_command()?;
    let output = cmd
        .arg("continue-multi-qube-conversation")
        .arg(&user_id)
        .arg(&conversation_id)
        .arg(&password)  // Now passing password
        .output()
        .map_err(|e| format!("Failed to execute Python bridge: {}", e))?;

    if !output.status.success() {
        let error = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python bridge error: {}", error));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let response: serde_json::Value = serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse JSON response: {}. Output: {}", e, stdout))?;

    Ok(response)
}

#[tauri::command]
async fn inject_multi_qube_user_message(
    user_id: String,
    conversation_id: String,
    message: String,
    password: String,
) -> Result<serde_json::Value, String> {
    use std::fs;

    // If message is too long for command line, use a temp file
    if message.len() > 7000 {
        let temp_dir = std::env::temp_dir();
        let temp_file = temp_dir.join(format!("qubes_temp_multi_message_{}.txt", std::process::id()));

        fs::write(&temp_file, &message)
            .map_err(|e| format!("Failed to write temp file: {}", e))?;

        let mut cmd = prepare_backend_command()?;
        let output = cmd
            .arg("inject-multi-qube-user-message")
            .arg(&user_id)
            .arg(&conversation_id)
            .arg(format!("@file:{}", temp_file.to_str().unwrap()))
            .arg(&password)
            .output()
            .map_err(|e| format!("Failed to execute backend: {}", e))?;

        // Clean up temp file
        let _ = fs::remove_file(&temp_file);

        if !output.status.success() {
            let error = String::from_utf8_lossy(&output.stderr);
            return Err(format!("Python bridge error: {}", error));
        }

        let stdout = String::from_utf8_lossy(&output.stdout);
        let response: serde_json::Value = serde_json::from_str(&stdout)
            .map_err(|e| format!("Failed to parse JSON response: {}. Output: {}", e, stdout))?;

        Ok(response)
    } else {
        // Short message - use command line directly
        let mut cmd = prepare_backend_command()?;
        let output = cmd
            .arg("inject-multi-qube-user-message")
            .arg(&user_id)
            .arg(&conversation_id)
            .arg(&message)
            .arg(&password)
            .output()
            .map_err(|e| format!("Failed to execute backend: {}", e))?;

        if !output.status.success() {
            let error = String::from_utf8_lossy(&output.stderr);
            return Err(format!("Python bridge error: {}", error));
        }

        let stdout = String::from_utf8_lossy(&output.stdout);
        let response: serde_json::Value = serde_json::from_str(&stdout)
            .map_err(|e| format!("Failed to parse JSON response: {}. Output: {}", e, stdout))?;

        Ok(response)
    }
}

#[tauri::command]
async fn lock_in_multi_qube_response(
    user_id: String,
    conversation_id: String,
    timestamp: i64,
    password: String,
) -> Result<serde_json::Value, String> {
    let mut cmd = prepare_backend_command()?;
    let output = cmd
        .arg("lock-in-multi-qube-response")
        .arg(&user_id)
        .arg(&conversation_id)
        .arg(timestamp.to_string())
        .arg(&password)
        .output()
        .map_err(|e| format!("Failed to execute Python bridge: {}", e))?;

    if !output.status.success() {
        let error = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python bridge error: {}", error));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let response: serde_json::Value = serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse JSON response: {}. Output: {}", e, stdout))?;

    Ok(response)
}

#[tauri::command]
async fn end_multi_qube_conversation(
    user_id: String,
    conversation_id: String,
    anchor: bool,
    password: String,
) -> Result<serde_json::Value, String> {
    let mut cmd = prepare_backend_command()?;
    let output = cmd
        .arg("end-multi-qube-conversation")
        .arg(&user_id)
        .arg(&conversation_id)
        .arg(if anchor { "true" } else { "false" })
        .arg(&password)  // Password is now argument 5
        .output()
        .map_err(|e| format!("Failed to execute Python bridge: {}", e))?;

    if !output.status.success() {
        let error = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python bridge error: {}", error));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let response: serde_json::Value = serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse JSON response: {}. Output: {}", e, stdout))?;

    Ok(response)
}

#[tauri::command]
async fn get_configured_api_keys(user_id: String, password: String) -> Result<ConfiguredKeysResponse, String> {
    // Validate inputs
    validate_identifier(&user_id, "user_id")?;

    let bridge_path = get_python_bridge_path();
    let project_root = get_python_project_path();
    let (mut cmd, skip_bridge_arg) = create_backend_command();

    cmd.current_dir(&project_root);

    if !skip_bridge_arg {
        if !bridge_path.exists() {
            return Err(format!("Python bridge not found at: {}", bridge_path.display()));
        }
        cmd.arg(&bridge_path);
    }

    let output = cmd
        .arg("get-configured-api-keys")
        .arg(&user_id)
        .arg(&password)
        .output()
        .map_err(|e| format!("Failed to execute backend: {}", e))?;

    if !output.status.success() {
        let error = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python bridge error: {}", error));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let response: ConfiguredKeysResponse = serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse JSON response: {}. Output: {}", e, stdout))?;

    Ok(response)
}

#[tauri::command]
async fn save_api_key(user_id: String, provider: String, api_key: String, password: String) -> Result<APIKeyResponse, String> {
    // Validate inputs
    validate_identifier(&user_id, "user_id")?;

    let bridge_path = get_python_bridge_path();
    let project_root = get_python_project_path();
    let (mut cmd, skip_bridge_arg) = create_backend_command();

    cmd.current_dir(&project_root);

    if !skip_bridge_arg {
        if !bridge_path.exists() {
            return Err(format!("Python bridge not found at: {}", bridge_path.display()));
        }
        cmd.arg(&bridge_path);
    }

    let output = cmd
        .arg("save-api-key")
        .arg(&user_id)
        .arg(&provider)
        .arg(&api_key)
        .arg(&password)
        .output()
        .map_err(|e| format!("Failed to execute backend: {}", e))?;

    if !output.status.success() {
        let error = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python bridge error: {}", error));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let response: APIKeyResponse = serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse JSON response: {}. Output: {}", e, stdout))?;

    Ok(response)
}

#[tauri::command]
async fn validate_api_key(user_id: String, provider: String, api_key: String, password: Option<String>) -> Result<ValidationResponse, String> {
    // Validate inputs
    validate_identifier(&user_id, "user_id")?;

    let bridge_path = get_python_bridge_path();
    let project_root = get_python_project_path();
    let (mut cmd, skip_bridge_arg) = create_backend_command();

    cmd.current_dir(&project_root);

    if !skip_bridge_arg {
        if !bridge_path.exists() {
            return Err(format!("Python bridge not found at: {}", bridge_path.display()));
        }
        cmd.arg(&bridge_path);
    }

    cmd.arg("validate-api-key")
        .arg(&user_id)
        .arg(&provider)
        .arg(&api_key);

    // Add password if provided (for testing saved keys)
    if let Some(pw) = password {
        cmd.arg(&pw);
    }

    let output = cmd.output()
        .map_err(|e| format!("Failed to execute backend: {}", e))?;

    if !output.status.success() {
        let error = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python bridge error: {}", error));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let response: ValidationResponse = serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse JSON response: {}. Output: {}", e, stdout))?;

    Ok(response)
}

#[tauri::command]
async fn delete_api_key(user_id: String, provider: String, password: String) -> Result<APIKeyResponse, String> {
    // Validate inputs
    validate_identifier(&user_id, "user_id")?;

    let bridge_path = get_python_bridge_path();
    let project_root = get_python_project_path();
    let (mut cmd, skip_bridge_arg) = create_backend_command();

    cmd.current_dir(&project_root);

    if !skip_bridge_arg {
        if !bridge_path.exists() {
            return Err(format!("Python bridge not found at: {}", bridge_path.display()));
        }
        cmd.arg(&bridge_path);
    }

    let output = cmd
        .arg("delete-api-key")
        .arg(&user_id)
        .arg(&provider)
        .arg(&password)
        .output()
        .map_err(|e| format!("Failed to execute backend: {}", e))?;

    if !output.status.success() {
        let error = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python bridge error: {}", error));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let response: APIKeyResponse = serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse JSON response: {}. Output: {}", e, stdout))?;

    Ok(response)
}

#[tauri::command]
async fn get_block_preferences(user_id: String) -> Result<BlockPreferencesResponse, String> {
    // Validate inputs
    validate_identifier(&user_id, "user_id")?;

    let mut cmd = prepare_backend_command()?;
    let output = cmd
        .arg("get-block-preferences")
        .arg(&user_id)
        .output()
        .map_err(|e| format!("Failed to execute Python bridge: {}", e))?;

    if !output.status.success() {
        let error = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python bridge error: {}", error));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let response: BlockPreferencesResponse = serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse JSON response: {}. Output: {}", e, stdout))?;

    Ok(response)
}

#[tauri::command]
async fn update_block_preferences(
    user_id: String,
    individual_auto_anchor: Option<bool>,
    individual_anchor_threshold: Option<i32>,
    group_auto_anchor: Option<bool>,
    group_anchor_threshold: Option<i32>
) -> Result<BlockPreferencesResponse, String> {
    // Validate inputs
    validate_identifier(&user_id, "user_id")?;

    let mut cmd = prepare_backend_command()?;
    cmd
        .arg("update-block-preferences")
        .arg(&user_id);

    // Add optional parameters
    if let Some(val) = individual_auto_anchor {
        cmd.arg("--individual-auto-anchor").arg(val.to_string());
    }
    if let Some(val) = individual_anchor_threshold {
        cmd.arg("--individual-anchor-threshold").arg(val.to_string());
    }
    if let Some(val) = group_auto_anchor {
        cmd.arg("--group-auto-anchor").arg(val.to_string());
    }
    if let Some(val) = group_anchor_threshold {
        cmd.arg("--group-anchor-threshold").arg(val.to_string());
    }

    let output = cmd.output()
        .map_err(|e| format!("Failed to execute Python bridge: {}", e))?;

    if !output.status.success() {
        let error = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python bridge error: {}", error));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let response: BlockPreferencesResponse = serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse JSON response: {}. Output: {}", e, stdout))?;

    Ok(response)
}

#[tauri::command]
async fn get_relationship_difficulty(user_id: String) -> Result<RelationshipSettingsResponse, String> {
    // Validate inputs
    validate_identifier(&user_id, "user_id")?;

    let mut cmd = prepare_backend_command()?;
    let output = cmd
        .arg("get-relationship-difficulty")
        .arg(&user_id)
        .output()
        .map_err(|e| format!("Failed to execute Python bridge: {}", e))?;

    if !output.status.success() {
        let error = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python bridge error: {}", error));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let response: RelationshipSettingsResponse = serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse JSON response: {}. Output: {}", e, stdout))?;

    Ok(response)
}

#[tauri::command]
async fn set_relationship_difficulty(
    user_id: String,
    difficulty: String
) -> Result<RelationshipSettingsResponse, String> {
    // Validate inputs
    validate_identifier(&user_id, "user_id")?;

    // Validate difficulty is one of the allowed values
    if !["quick", "normal", "long", "extreme"].contains(&difficulty.as_str()) {
        return Err(format!("Invalid difficulty: {}. Must be one of: quick, normal, long, extreme", difficulty));
    }

    let mut cmd = prepare_backend_command()?;
    let output = cmd
        .arg("set-relationship-difficulty")
        .arg(&user_id)
        .arg(&difficulty)
        .output()
        .map_err(|e| format!("Failed to execute Python bridge: {}", e))?;

    if !output.status.success() {
        let error = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python bridge error: {}", error));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let response: RelationshipSettingsResponse = serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse JSON response: {}. Output: {}", e, stdout))?;

    Ok(response)
}

#[tauri::command]
async fn get_decision_config(user_id: String) -> Result<serde_json::Value, String> {
    // Validate inputs
    validate_identifier(&user_id, "user_id")?;

    let mut cmd = prepare_backend_command()?;
    let output = cmd
        .arg("get-decision-config")
        .arg(&user_id)
        .output()
        .map_err(|e| format!("Failed to execute Python bridge: {}", e))?;

    if !output.status.success() {
        let error = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python bridge error: {}", error));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let response: serde_json::Value = serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse JSON response: {}. Output: {}", e, stdout))?;

    Ok(response)
}

#[tauri::command]
async fn update_decision_config(
    user_id: String,
    config_json: String
) -> Result<serde_json::Value, String> {
    // Validate inputs
    validate_identifier(&user_id, "user_id")?;

    let mut cmd = prepare_backend_command()?;
    let output = cmd
        .arg("update-decision-config")
        .arg(&user_id)
        .arg(&config_json)
        .output()
        .map_err(|e| format!("Failed to execute Python bridge: {}", e))?;

    if !output.status.success() {
        let error = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python bridge error: {}", error));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let response: serde_json::Value = serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse JSON response: {}. Output: {}", e, stdout))?;

    Ok(response)
}

#[tauri::command]
async fn get_difficulty_presets() -> Result<std::collections::HashMap<String, DifficultyPreset>, String> {
    let mut cmd = prepare_backend_command()?;
    let output = cmd
        .arg("get-difficulty-presets")
        .output()
        .map_err(|e| format!("Failed to execute Python bridge: {}", e))?;

    if !output.status.success() {
        let error = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python bridge error: {}", error));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let response: std::collections::HashMap<String, DifficultyPreset> = serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse JSON response: {}. Output: {}", e, stdout))?;

    Ok(response)
}

#[tauri::command]
async fn get_qube_relationships(
    user_id: String,
    qube_id: String,
    password: Option<String>,
) -> Result<RelationshipResponse, String> {
    // Validate inputs
    validate_identifier(&user_id, "user_id")?;
    validate_identifier(&qube_id, "qube_id")?;

    let password_str = password.unwrap_or_default();
    let mut cmd = prepare_backend_command()?;
    let output = cmd
        .arg("get-qube-relationships")
        .arg(&user_id)
        .arg(&qube_id)
        .arg(&password_str)
        .output()
        .map_err(|e| format!("Failed to execute Python bridge: {}", e))?;

    if !output.status.success() {
        let error = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python bridge error: {}", error));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let response: RelationshipResponse = serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse JSON response: {}. Output: {}", e, stdout))?;

    Ok(response)
}

#[tauri::command]
async fn get_relationship_timeline(
    user_id: String,
    qube_id: String,
    entity_id: String,
    password: Option<String>,
) -> Result<TimelineResponse, String> {
    // Validate inputs
    validate_identifier(&user_id, "user_id")?;
    validate_identifier(&qube_id, "qube_id")?;
    validate_identifier(&entity_id, "entity_id")?;

    let password_str = password.unwrap_or_default();
    let mut cmd = prepare_backend_command()?;
    let output = cmd
        .arg("get-relationship-timeline")
        .arg(&user_id)
        .arg(&qube_id)
        .arg(&entity_id)
        .arg(&password_str)
        .output()
        .map_err(|e| format!("Failed to execute Python bridge: {}", e))?;

    if !output.status.success() {
        let error = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python bridge error: {}", error));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let response: TimelineResponse = serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse JSON response: {}. Output: {}", e, stdout))?;

    Ok(response)
}

#[tauri::command]
async fn get_google_tts_path(user_id: String) -> Result<GoogleTTSPathResponse, String> {
    // Validate inputs
    validate_identifier(&user_id, "user_id")?;

    let mut cmd = prepare_backend_command()?;
    let output = cmd
        .arg("get-google-tts-path")
        .arg(&user_id)
        .output()
        .map_err(|e| format!("Failed to execute Python bridge: {}", e))?;

    if !output.status.success() {
        let error = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python bridge error: {}", error));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let response: GoogleTTSPathResponse = serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse JSON response: {}. Output: {}", e, stdout))?;

    Ok(response)
}

#[tauri::command]
async fn set_google_tts_path(user_id: String, path: String) -> Result<SetPathResponse, String> {
    // Validate inputs
    validate_identifier(&user_id, "user_id")?;

    let mut cmd = prepare_backend_command()?;
    let output = cmd
        .arg("set-google-tts-path")
        .arg(&user_id)
        .arg(&path)
        .output()
        .map_err(|e| format!("Failed to execute Python bridge: {}", e))?;

    if !output.status.success() {
        let error = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python bridge error: {}", error));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let response: SetPathResponse = serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse JSON response: {}. Output: {}", e, stdout))?;

    Ok(response)
}

#[tauri::command]
async fn get_qube_skills(user_id: String, qube_id: String) -> Result<SkillsResponse, String> {
    // Validate inputs
    validate_identifier(&user_id, "user_id")?;
    validate_identifier(&qube_id, "qube_id")?;

    let mut cmd = prepare_backend_command()?;
    let output = cmd
        .arg("get-qube-skills")
        .arg(&user_id)
        .arg(&qube_id)
        .output()
        .map_err(|e| format!("Failed to execute Python bridge: {}", e))?;

    if !output.status.success() {
        let error = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python bridge error: {}", error));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let response: SkillsResponse = serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse JSON response: {}. Output: {}", e, stdout))?;

    Ok(response)
}

#[tauri::command]
async fn save_qube_skills(user_id: String, qube_id: String, skills_json: String) -> Result<SkillsResponse, String> {
    // Validate inputs
    validate_identifier(&user_id, "user_id")?;
    validate_identifier(&qube_id, "qube_id")?;

    let mut cmd = prepare_backend_command()?;
    let output = cmd
        .arg("save-qube-skills")
        .arg(&user_id)
        .arg(&qube_id)
        .arg(&skills_json)
        .output()
        .map_err(|e| format!("Failed to execute Python bridge: {}", e))?;

    if !output.status.success() {
        let error = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python bridge error: {}", error));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let response: SkillsResponse = serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse JSON response: {}. Output: {}", e, stdout))?;

    Ok(response)
}

#[tauri::command]
async fn add_skill_xp(
    user_id: String,
    qube_id: String,
    skill_id: String,
    xp_amount: i32,
    evidence_block_id: Option<String>
) -> Result<serde_json::Value, String> {
    // Validate inputs
    validate_identifier(&user_id, "user_id")?;
    validate_identifier(&qube_id, "qube_id")?;

    let mut cmd = prepare_backend_command()?;
    cmd
        .arg("add-skill-xp")
        .arg(&user_id)
        .arg(&qube_id)
        .arg(&skill_id)
        .arg(xp_amount.to_string());

    if let Some(block_id) = evidence_block_id {
        cmd.arg(block_id);
    }

    let output = cmd.output()
        .map_err(|e| format!("Failed to execute Python bridge: {}", e))?;

    if !output.status.success() {
        let error = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python bridge error: {}", error));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let response: serde_json::Value = serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse JSON response: {}. Output: {}", e, stdout))?;

    Ok(response)
}

#[tauri::command]
async fn unlock_skill(user_id: String, qube_id: String, skill_id: String) -> Result<serde_json::Value, String> {
    // Validate inputs
    validate_identifier(&user_id, "user_id")?;
    validate_identifier(&qube_id, "qube_id")?;

    let mut cmd = prepare_backend_command()?;
    let output = cmd
        .arg("unlock-skill")
        .arg(&user_id)
        .arg(&qube_id)
        .arg(&skill_id)
        .output()
        .map_err(|e| format!("Failed to execute Python bridge: {}", e))?;

    if !output.status.success() {
        let error = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python bridge error: {}", error));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let response: serde_json::Value = serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse JSON response: {}. Output: {}", e, stdout))?;

    Ok(response)
}

#[tauri::command]
async fn get_visualizer_settings(user_id: String, qube_id: String) -> Result<VisualizerSettingsResponse, String> {
    // Validate inputs
    validate_identifier(&user_id, "user_id")?;
    validate_identifier(&qube_id, "qube_id")?;

    let mut cmd = prepare_backend_command()?;
    let output = cmd
        .arg("get-visualizer-settings")
        .arg(&user_id)
        .arg(&qube_id)
        .output()
        .map_err(|e| format!("Failed to execute Python bridge: {}", e))?;

    if !output.status.success() {
        let error = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python bridge error: {}", error));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let response: VisualizerSettingsResponse = serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse JSON response: {}. Output: {}", e, stdout))?;

    Ok(response)
}

#[tauri::command]
async fn save_visualizer_settings(
    user_id: String,
    qube_id: String,
    settings: String
) -> Result<GenericSuccessResponse, String> {
    // Validate inputs
    validate_identifier(&user_id, "user_id")?;
    validate_identifier(&qube_id, "qube_id")?;

    let mut cmd = prepare_backend_command()?;
    let output = cmd
        .arg("save-visualizer-settings")
        .arg(&user_id)
        .arg(&qube_id)
        .arg(&settings)
        .output()
        .map_err(|e| format!("Failed to execute Python bridge: {}", e))?;

    if !output.status.success() {
        let error = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python bridge error: {}", error));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let response: GenericSuccessResponse = serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse JSON response: {}. Output: {}", e, stdout))?;

    Ok(response)
}

#[tauri::command]
async fn get_trust_personality(user_id: String, qube_id: String) -> Result<TrustPersonalityResponse, String> {
    // Validate inputs
    validate_identifier(&user_id, "user_id")?;
    validate_identifier(&qube_id, "qube_id")?;

    let mut cmd = prepare_backend_command()?;
    let output = cmd
        .arg("get-trust-personality")
        .arg(&user_id)
        .arg(&qube_id)
        .output()
        .map_err(|e| format!("Failed to execute Python bridge: {}", e))?;

    if !output.status.success() {
        let error = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python bridge error: {}", error));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let response: TrustPersonalityResponse = serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse JSON response: {}. Output: {}", e, stdout))?;

    Ok(response)
}

#[tauri::command]
async fn update_trust_personality(
    user_id: String,
    qube_id: String,
    trust_profile: String
) -> Result<GenericSuccessResponse, String> {
    // Validate inputs
    validate_identifier(&user_id, "user_id")?;
    validate_identifier(&qube_id, "qube_id")?;

    // Validate trust_profile value
    if !["cautious", "balanced", "social", "analytical"].contains(&trust_profile.as_str()) {
        return Err(format!("Invalid trust profile: {}. Must be one of: cautious, balanced, social, analytical", trust_profile));
    }

    let mut cmd = prepare_backend_command()?;
    let output = cmd
        .arg("update-trust-personality")
        .arg(&user_id)
        .arg(&qube_id)
        .arg(&trust_profile)
        .output()
        .map_err(|e| format!("Failed to execute Python bridge: {}", e))?;

    if !output.status.success() {
        let error = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python bridge error: {}", error));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let response: GenericSuccessResponse = serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse JSON response: {}. Output: {}", e, stdout))?;

    Ok(response)
}

#[tauri::command]
async fn get_available_monitors(app: tauri::AppHandle) -> Result<MonitorsResponse, String> {
    // Get monitors from the environment
    let monitors_result = app.available_monitors();

    match monitors_result {
        Ok(monitors) => {
            let monitor_info: Vec<MonitorInfo> = monitors
                .iter()
                .enumerate()
                .map(|(id, monitor)| {
                    let size = monitor.size();
                    let position = monitor.position();

                    // Simple, user-friendly monitor names
                    let display_name = if id == 0 {
                        format!("Monitor {} (Primary)", id + 1)
                    } else {
                        format!("Monitor {}", id + 1)
                    };

                    MonitorInfo {
                        id: id + 1, // Start from 1 (0 is reserved for main window)
                        name: display_name,
                        width: size.width,
                        height: size.height,
                        x: position.x,
                        y: position.y,
                        is_primary: id == 0, // First monitor is typically primary
                    }
                })
                .collect();

            Ok(MonitorsResponse {
                monitors: monitor_info,
            })
        }
        Err(e) => Err(format!("Failed to get monitors: {}", e)),
    }
}

#[tauri::command]
async fn create_visualizer_window(
    app: tauri::AppHandle,
    monitor_index: usize,
) -> Result<GenericSuccessResponse, String> {
    use tauri::Manager;
    use tauri::WebviewWindowBuilder;
    use tauri::WebviewUrl;

    // Close existing visualizer window if it exists
    if let Some(window) = app.get_webview_window("visualizer") {
        let _ = window.close();
    }

    // Get available monitors
    let monitors = app.available_monitors()
        .map_err(|e| format!("Failed to get monitors: {}", e))?;

    if monitor_index == 0 || monitor_index > monitors.len() {
        return Err(format!("Invalid monitor index: {} (valid range: 1-{})",
            monitor_index, monitors.len()));
    }

    let target_monitor = &monitors[monitor_index - 1];
    let size = target_monitor.size();
    let position = target_monitor.position();
    let scale_factor = target_monitor.scale_factor();

    // Convert physical pixels to logical pixels for DPI scaling
    let mut logical_width = (size.width as f64 / scale_factor).round();
    let logical_height = (size.height as f64 / scale_factor).round();
    let logical_x = (position.x as f64 / scale_factor).round();
    let logical_y = (position.y as f64 / scale_factor).round();

    // For monitors with negative X (positioned to the left), reduce width slightly
    // to prevent glow effects from bleeding onto adjacent monitors
    if position.x < 0 {
        logical_width -= 3.0;
    }

    // Create borderless window using logical coordinates
    match WebviewWindowBuilder::new(
        &app,
        "visualizer",
        WebviewUrl::App("visualizer".into())
    )
    .title("Qubes Visualizer")
    .position(logical_x, logical_y)
    .inner_size(logical_width, logical_height)
    .decorations(false)
    .resizable(false)
    .always_on_top(true)
    .focused(false)
    .skip_taskbar(true)
    .visible_on_all_workspaces(true)
    .build() {
        Ok(window) => {
            // Force position multiple times as Windows workaround
            for _ in 1..=3 {
                std::thread::sleep(std::time::Duration::from_millis(50));
                let _ = window.set_position(tauri::Position::Logical(tauri::LogicalPosition {
                    x: logical_x,
                    y: logical_y,
                }));
            }

            Ok(GenericSuccessResponse {
                success: true,
                message: Some(format!(
                    "Visualizer window created on monitor {} at ({}, {})",
                    monitor_index, position.x, position.y
                )),
                error: None,
            })
        },
        Err(e) => {
            Err(format!("Failed to create visualizer window: {}", e))
        }
    }
}

#[tauri::command]
async fn close_visualizer_window(app: tauri::AppHandle) -> Result<GenericSuccessResponse, String> {
    use tauri::Manager;

    if let Some(window) = app.get_webview_window("visualizer") {
        window.close().map_err(|e| format!("Failed to close window: {}", e))?;

        Ok(GenericSuccessResponse {
            success: true,
            message: Some("Visualizer window closed".to_string()),
            error: None,
        })
    } else {
        Ok(GenericSuccessResponse {
            success: true,
            message: Some("No visualizer window to close".to_string()),
            error: None,
        })
    }
}

// NFT Authentication Response Types
#[derive(Debug, Serialize, Deserialize)]
struct NftAuthResponse {
    success: bool,
    authenticated: Option<bool>,
    qube_id: Option<String>,
    public_key: Option<String>,
    category_id: Option<String>,
    nft_verified: Option<bool>,
    token: Option<String>,
    token_expires_at: Option<i64>,
    error: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
struct NftAuthStatusResponse {
    success: bool,
    qube_id: Option<String>,
    registered: Option<bool>,
    can_authenticate: Option<bool>,
    has_nft: Option<bool>,
    category_id: Option<String>,
    error: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
struct TokenRefreshResponse {
    success: bool,
    token: Option<String>,
    expires_at: Option<i64>,
    qube_id: Option<String>,
    error: Option<String>,
}

/// Authenticate a Qube via NFT challenge-response.
/// Returns a JWT token for authenticated API requests.
#[tauri::command]
async fn authenticate_nft(
    user_id: String,
    qube_id: String,
    password: String,
) -> Result<NftAuthResponse, String> {
    // Validate inputs
    validate_identifier(&user_id, "user_id")?;
    validate_identifier(&qube_id, "qube_id")?;

    let mut cmd = prepare_backend_command()?;
    let output = cmd
        .arg("authenticate-nft")
        .arg(&user_id)
        .arg(&qube_id)
        .arg(&password)
        .output()
        .map_err(|e| format!("Failed to execute Python: {}", e))?;

    let stdout = String::from_utf8_lossy(&output.stdout).to_string();

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr).to_string();
        return Err(format!("NFT authentication failed: {}", stderr));
    }

    serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse NFT auth response: {}. Output: {}", e, stdout))
}

/// Refresh an existing JWT token.
#[tauri::command]
async fn refresh_auth_token(token: String) -> Result<TokenRefreshResponse, String> {
    let mut cmd = prepare_backend_command()?;
    let output = cmd
        .arg("refresh-auth-token")
        .arg(&token)
        .output()
        .map_err(|e| format!("Failed to execute Python: {}", e))?;

    let stdout = String::from_utf8_lossy(&output.stdout).to_string();

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr).to_string();
        return Err(format!("Token refresh failed: {}", stderr));
    }

    serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse token refresh response: {}. Output: {}", e, stdout))
}

/// Check if a Qube can authenticate (is registered on server).
#[tauri::command]
async fn get_nft_auth_status(qube_id: String) -> Result<NftAuthStatusResponse, String> {
    // Validate inputs
    validate_identifier(&qube_id, "qube_id")?;

    let mut cmd = prepare_backend_command()?;
    let output = cmd
        .arg("get-auth-status")
        .arg(&qube_id)
        .output()
        .map_err(|e| format!("Failed to execute Python: {}", e))?;

    let stdout = String::from_utf8_lossy(&output.stdout).to_string();

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr).to_string();
        return Err(format!("Auth status check failed: {}", stderr));
    }

    serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse auth status response: {}. Output: {}", e, stdout))
}

// P2P Command Functions

/// Get list of currently online Qubes
#[tauri::command]
async fn get_online_qubes(user_id: String) -> Result<OnlineQubesResponse, String> {
    validate_identifier(&user_id, "user_id")?;

    let mut cmd = prepare_backend_command()?;
    let output = cmd
        .arg("get-online-qubes")
        .arg(&user_id)
        .output()
        .map_err(|e| format!("Failed to execute Python: {}", e))?;

    let stdout = String::from_utf8_lossy(&output.stdout).to_string();

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr).to_string();
        return Err(format!("Get online qubes failed: {}", stderr));
    }

    serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse response: {}. Output: {}", e, stdout))
}

/// Generate an AI introduction message from a Qube
#[tauri::command]
async fn generate_introduction(
    user_id: String,
    qube_id: String,
    to_commitment: String,
    to_name: String,
    to_description: String,
    password: String,
) -> Result<GenerateIntroductionResponse, String> {
    validate_identifier(&user_id, "user_id")?;
    validate_identifier(&qube_id, "qube_id")?;

    let mut cmd = prepare_backend_command()?;
    let output = cmd
        .arg("generate-introduction")
        .arg(&user_id)
        .arg(&qube_id)
        .arg(&to_commitment)
        .arg(&to_name)
        .arg(&to_description)
        .arg(&password)
        .output()
        .map_err(|e| format!("Failed to execute Python: {}", e))?;

    let stdout = String::from_utf8_lossy(&output.stdout).to_string();

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr).to_string();
        return Err(format!("Generate introduction failed: {}", stderr));
    }

    serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse response: {}. Output: {}", e, stdout))
}

/// Evaluate an incoming introduction using the Qube's AI
#[tauri::command]
async fn evaluate_introduction(
    user_id: String,
    qube_id: String,
    from_name: String,
    intro_message: String,
    password: String,
) -> Result<EvaluateIntroductionResponse, String> {
    validate_identifier(&user_id, "user_id")?;
    validate_identifier(&qube_id, "qube_id")?;

    let mut cmd = prepare_backend_command()?;
    let output = cmd
        .arg("evaluate-introduction")
        .arg(&user_id)
        .arg(&qube_id)
        .arg(&from_name)
        .arg(&intro_message)
        .arg(&password)
        .output()
        .map_err(|e| format!("Failed to execute Python: {}", e))?;

    let stdout = String::from_utf8_lossy(&output.stdout).to_string();

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr).to_string();
        return Err(format!("Evaluate introduction failed: {}", stderr));
    }

    serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse response: {}. Output: {}", e, stdout))
}

/// Process an incoming P2P message through the local Qube's AI
#[tauri::command]
async fn process_p2p_message(
    user_id: String,
    qube_id: String,
    from_name: String,
    from_commitment: String,
    message: String,
    context: String,
    password: String,
) -> Result<ProcessP2PMessageResponse, String> {
    validate_identifier(&user_id, "user_id")?;
    validate_identifier(&qube_id, "qube_id")?;

    let mut cmd = prepare_backend_command()?;
    let output = cmd
        .arg("process-p2p-message")
        .arg(&user_id)
        .arg(&qube_id)
        .arg("--from-name")
        .arg(&from_name)
        .arg("--from-commitment")
        .arg(&from_commitment)
        .arg("--message")
        .arg(&message)
        .arg("--context")
        .arg(&context)
        .arg("--password")
        .arg(&password)
        .output()
        .map_err(|e| format!("Failed to execute Python: {}", e))?;

    let stdout = String::from_utf8_lossy(&output.stdout).to_string();

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr).to_string();
        return Err(format!("Process P2P message failed: {}", stderr));
    }

    serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse response: {}. Output: {}", e, stdout))
}

/// Send an introduction request to another Qube
#[tauri::command]
async fn send_introduction(
    user_id: String,
    qube_id: String,
    to_commitment: String,
    message: String,
    password: String,
) -> Result<IntroductionResponse, String> {
    validate_identifier(&user_id, "user_id")?;
    validate_identifier(&qube_id, "qube_id")?;

    let mut cmd = prepare_backend_command()?;
    let output = cmd
        .arg("send-introduction")
        .arg(&user_id)
        .arg(&qube_id)
        .arg(&to_commitment)
        .arg(&message)
        .arg(&password)
        .output()
        .map_err(|e| format!("Failed to execute Python: {}", e))?;

    let stdout = String::from_utf8_lossy(&output.stdout).to_string();

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr).to_string();
        return Err(format!("Send introduction failed: {}", stderr));
    }

    serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse response: {}. Output: {}", e, stdout))
}

/// Get pending introduction requests
#[tauri::command]
async fn get_pending_introductions(
    user_id: String,
    qube_id: String,
    password: String,
) -> Result<PendingIntroductionsResponse, String> {
    validate_identifier(&user_id, "user_id")?;
    validate_identifier(&qube_id, "qube_id")?;

    let mut cmd = prepare_backend_command()?;
    let output = cmd
        .arg("get-pending-introductions")
        .arg(&user_id)
        .arg(&qube_id)
        .arg(&password)
        .output()
        .map_err(|e| format!("Failed to execute Python: {}", e))?;

    let stdout = String::from_utf8_lossy(&output.stdout).to_string();

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr).to_string();
        return Err(format!("Get pending introductions failed: {}", stderr));
    }

    serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse response: {}. Output: {}", e, stdout))
}

/// Accept a pending introduction request
#[tauri::command]
async fn accept_introduction(
    user_id: String,
    qube_id: String,
    relay_id: String,
    password: String,
) -> Result<AcceptIntroductionResponse, String> {
    validate_identifier(&user_id, "user_id")?;
    validate_identifier(&qube_id, "qube_id")?;

    let mut cmd = prepare_backend_command()?;
    let output = cmd
        .arg("accept-introduction")
        .arg(&user_id)
        .arg(&qube_id)
        .arg(&relay_id)
        .arg(&password)
        .output()
        .map_err(|e| format!("Failed to execute Python: {}", e))?;

    let stdout = String::from_utf8_lossy(&output.stdout).to_string();

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr).to_string();
        return Err(format!("Accept introduction failed: {}", stderr));
    }

    serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse response: {}. Output: {}", e, stdout))
}

/// Reject a pending introduction request
#[tauri::command]
async fn reject_introduction(
    user_id: String,
    qube_id: String,
    relay_id: String,
    password: String,
) -> Result<serde_json::Value, String> {
    validate_identifier(&user_id, "user_id")?;
    validate_identifier(&qube_id, "qube_id")?;

    let mut cmd = prepare_backend_command()?;
    let output = cmd
        .arg("reject-introduction")
        .arg(&user_id)
        .arg(&qube_id)
        .arg(&relay_id)
        .arg(&password)
        .output()
        .map_err(|e| format!("Failed to execute Python: {}", e))?;

    let stdout = String::from_utf8_lossy(&output.stdout).to_string();

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr).to_string();
        return Err(format!("Reject introduction failed: {}", stderr));
    }

    serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse response: {}. Output: {}", e, stdout))
}

/// Get accepted connections for a Qube
#[tauri::command]
async fn get_connections(
    user_id: String,
    qube_id: String,
) -> Result<ConnectionsResponse, String> {
    validate_identifier(&user_id, "user_id")?;
    validate_identifier(&qube_id, "qube_id")?;

    let mut cmd = prepare_backend_command()?;
    let output = cmd
        .arg("get-connections")
        .arg(&user_id)
        .arg(&qube_id)
        .output()
        .map_err(|e| format!("Failed to execute Python: {}", e))?;

    let stdout = String::from_utf8_lossy(&output.stdout).to_string();

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr).to_string();
        return Err(format!("Get connections failed: {}", stderr));
    }

    serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse response: {}. Output: {}", e, stdout))
}

/// Create a P2P conversation session
#[tauri::command]
async fn create_p2p_session(
    user_id: String,
    qube_id: String,
    local_qubes: String,
    remote_commitments: String,
    topic: String,
    password: String,
) -> Result<P2PSessionResponse, String> {
    validate_identifier(&user_id, "user_id")?;
    validate_identifier(&qube_id, "qube_id")?;

    let mut cmd = prepare_backend_command()?;
    let output = cmd
        .arg("create-p2p-session")
        .arg(&user_id)
        .arg(&qube_id)
        .arg("--local-qubes")
        .arg(&local_qubes)
        .arg("--remote-commitments")
        .arg(&remote_commitments)
        .arg("--topic")
        .arg(&topic)
        .arg("--password")
        .arg(&password)
        .output()
        .map_err(|e| format!("Failed to execute Python: {}", e))?;

    let stdout = String::from_utf8_lossy(&output.stdout).to_string();

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr).to_string();
        return Err(format!("Create P2P session failed: {}", stderr));
    }

    serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse response: {}. Output: {}", e, stdout))
}

/// Get P2P sessions for a Qube
#[tauri::command]
async fn get_p2p_sessions(
    user_id: String,
    qube_id: String,
    password: String,
) -> Result<P2PSessionsResponse, String> {
    validate_identifier(&user_id, "user_id")?;
    validate_identifier(&qube_id, "qube_id")?;

    let mut cmd = prepare_backend_command()?;
    let output = cmd
        .arg("get-p2p-sessions")
        .arg(&user_id)
        .arg(&qube_id)
        .arg(&password)
        .output()
        .map_err(|e| format!("Failed to execute Python: {}", e))?;

    let stdout = String::from_utf8_lossy(&output.stdout).to_string();

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr).to_string();
        return Err(format!("Get P2P sessions failed: {}", stderr));
    }

    serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse response: {}. Output: {}", e, stdout))
}

/// Start a P2P conversation using the same logic as local multi-qube
#[tauri::command]
async fn start_p2p_conversation(
    user_id: String,
    local_qubes: String,
    remote_connections: String,
    session_id: String,
    initial_prompt: String,
    password: String,
) -> Result<serde_json::Value, String> {
    validate_identifier(&user_id, "user_id")?;

    let mut cmd = prepare_backend_command()?;
    let output = cmd
        .arg("start-p2p-conversation")
        .arg(&user_id)
        .arg("--local-qubes")
        .arg(&local_qubes)
        .arg("--remote-connections")
        .arg(&remote_connections)
        .arg("--session-id")
        .arg(&session_id)
        .arg("--initial-prompt")
        .arg(&initial_prompt)
        .arg("--password")
        .arg(&password)
        .output()
        .map_err(|e| format!("Failed to execute Python: {}", e))?;

    let stdout = String::from_utf8_lossy(&output.stdout).to_string();

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr).to_string();
        return Err(format!("Start P2P conversation failed: {}", stderr));
    }

    serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse response: {}. Output: {}", e, stdout))
}

/// Continue P2P conversation - get next local Qube response
#[tauri::command]
async fn continue_p2p_conversation(
    user_id: String,
    conversation_id: String,
    session_id: String,
    local_qubes: String,
    remote_connections: String,
    password: String,
) -> Result<serde_json::Value, String> {
    validate_identifier(&user_id, "user_id")?;

    let mut cmd = prepare_backend_command()?;
    let output = cmd
        .arg("continue-p2p-conversation")
        .arg(&user_id)
        .arg("--conversation-id")
        .arg(&conversation_id)
        .arg("--session-id")
        .arg(&session_id)
        .arg("--local-qubes")
        .arg(&local_qubes)
        .arg("--remote-connections")
        .arg(&remote_connections)
        .arg("--password")
        .arg(&password)
        .output()
        .map_err(|e| format!("Failed to execute Python: {}", e))?;

    let stdout = String::from_utf8_lossy(&output.stdout).to_string();

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr).to_string();
        return Err(format!("Continue P2P conversation failed: {}", stderr));
    }

    serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse response: {}. Output: {}", e, stdout))
}

/// Inject a block received from hub into local conversation
#[tauri::command]
async fn inject_p2p_block(
    user_id: String,
    conversation_id: String,
    session_id: String,
    block_data: String,
    from_commitment: String,
    local_qubes: String,
    remote_connections: String,
    password: String,
) -> Result<serde_json::Value, String> {
    validate_identifier(&user_id, "user_id")?;

    let mut cmd = prepare_backend_command()?;
    let output = cmd
        .arg("inject-p2p-block")
        .arg(&user_id)
        .arg("--conversation-id")
        .arg(&conversation_id)
        .arg("--session-id")
        .arg(&session_id)
        .arg("--block-data")
        .arg(&block_data)
        .arg("--from-commitment")
        .arg(&from_commitment)
        .arg("--local-qubes")
        .arg(&local_qubes)
        .arg("--remote-connections")
        .arg(&remote_connections)
        .arg("--password")
        .arg(&password)
        .output()
        .map_err(|e| format!("Failed to execute Python: {}", e))?;

    let stdout = String::from_utf8_lossy(&output.stdout).to_string();

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr).to_string();
        return Err(format!("Inject P2P block failed: {}", stderr));
    }

    serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse response: {}. Output: {}", e, stdout))
}

/// Send user message in P2P conversation
#[tauri::command]
async fn send_p2p_user_message(
    user_id: String,
    conversation_id: String,
    session_id: String,
    message: String,
    local_qubes: String,
    remote_connections: String,
    password: String,
) -> Result<serde_json::Value, String> {
    validate_identifier(&user_id, "user_id")?;

    let mut cmd = prepare_backend_command()?;
    let output = cmd
        .arg("send-p2p-user-message")
        .arg(&user_id)
        .arg("--conversation-id")
        .arg(&conversation_id)
        .arg("--session-id")
        .arg(&session_id)
        .arg("--message")
        .arg(&message)
        .arg("--local-qubes")
        .arg(&local_qubes)
        .arg("--remote-connections")
        .arg(&remote_connections)
        .arg("--password")
        .arg(&password)
        .output()
        .map_err(|e| format!("Failed to execute Python: {}", e))?;

    let stdout = String::from_utf8_lossy(&output.stdout).to_string();

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr).to_string();
        return Err(format!("Send P2P user message failed: {}", stderr));
    }

    serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse response: {}. Output: {}", e, stdout))
}

// ============================================================================
// SETUP WIZARD COMMANDS
// ============================================================================

#[derive(Debug, Serialize, Deserialize)]
struct CreateAccountResponse {
    success: bool,
    user_id: Option<String>,
    data_dir: Option<String>,
    error: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
struct OllamaStatusResponse {
    running: bool,
    models: Vec<String>,
}

#[derive(Debug, Serialize, Deserialize)]
struct CreateQubeForMintingResponse {
    success: bool,
    qube_id: Option<String>,
    public_key: Option<String>,
    genesis_block_hash: Option<String>,
    recipient_address: Option<String>,
    error: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
struct PreRegisterResponse {
    success: bool,
    registration_id: Option<String>,
    payment_amount_satoshis: Option<i64>,
    payment_amount_bch: Option<String>,
    error: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
struct RegistrationStatusResponse {
    status: String,
    payment_detected: Option<bool>,
    mint_result: Option<serde_json::Value>,
    error: Option<String>,
}

/// Response from check_first_run
#[derive(Debug, Serialize, Deserialize)]
struct FirstRunResponse {
    is_first_run: bool,
    users: Vec<String>,
}

/// Check if this is the first run (no users exist)
#[tauri::command]
async fn check_first_run() -> Result<FirstRunResponse, String> {
    let bridge_path = get_python_bridge_path();
    let project_root = get_python_project_path();

    let (mut cmd, skip_bridge_arg) = create_backend_command();
    cmd.current_dir(&project_root);

    if !skip_bridge_arg {
        cmd.arg(&bridge_path);
    }

    let output = cmd
        .arg("check-first-run")
        .output()
        .map_err(|e| format!("Failed to execute backend: {}", e))?;

    let stdout = String::from_utf8_lossy(&output.stdout).to_string();

    if !output.status.success() {
        // If backend fails, assume first run
        return Ok(FirstRunResponse {
            is_first_run: true,
            users: vec![],
        });
    }

    serde_json::from_str(&stdout.trim())
        .map_err(|e| format!("Failed to parse response: {}. Output: {}", e, stdout))
}

/// Create a new user account
#[tauri::command]
async fn create_user_account(user_id: String, password: String) -> Result<CreateAccountResponse, String> {
    validate_identifier(&user_id, "user_id")?;

    let bridge_path = get_python_bridge_path();
    let project_root = get_python_project_path();

    let (mut cmd, skip_bridge_arg) = create_backend_command();
    cmd.current_dir(&project_root);

    if !skip_bridge_arg {
        cmd.arg(&bridge_path);
    }

    let output = cmd
        .arg("create-user-account")
        .arg(&user_id)
        .arg(&password)  // Positional argument, not --password flag
        .output()
        .map_err(|e| format!("Failed to execute Python: {}", e))?;

    let stdout = String::from_utf8_lossy(&output.stdout).to_string();

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr).to_string();
        return Ok(CreateAccountResponse {
            success: false,
            user_id: None,
            data_dir: None,
            error: Some(format!("Failed to create account: {}", stderr)),
        });
    }

    serde_json::from_str(&stdout.trim())
        .map_err(|e| format!("Failed to parse response: {}. Output: {}", e, stdout))
}

/// Check Ollama status
#[tauri::command]
async fn check_ollama_status() -> Result<OllamaStatusResponse, String> {
    // Try to connect to Ollama API
    let client = reqwest::Client::new();

    match client.get("http://127.0.0.1:11434/api/tags").send().await {
        Ok(response) => {
            if response.status().is_success() {
                // Parse the models list
                if let Ok(json) = response.json::<serde_json::Value>().await {
                    let models: Vec<String> = json.get("models")
                        .and_then(|m| m.as_array())
                        .map(|arr| {
                            arr.iter()
                                .filter_map(|v| v.get("name").and_then(|n| n.as_str()).map(String::from))
                                .collect()
                        })
                        .unwrap_or_default();

                    return Ok(OllamaStatusResponse {
                        running: true,
                        models,
                    });
                }
            }
            Ok(OllamaStatusResponse {
                running: false,
                models: vec![],
            })
        }
        Err(_) => Ok(OllamaStatusResponse {
            running: false,
            models: vec![],
        }),
    }
}

/// Start bundled Ollama
#[tauri::command]
async fn start_ollama() -> Result<bool, String> {
    // Get path to bundled Ollama
    let exe_dir = std::env::current_exe()
        .map_err(|e| format!("Failed to get exe path: {}", e))?
        .parent()
        .ok_or("Failed to get exe directory")?
        .to_path_buf();

    let ollama_path = exe_dir.join("ollama").join("ollama.exe");

    if !ollama_path.exists() {
        // Fall back to system Ollama
        #[cfg(target_os = "windows")]
        {
            Command::new("ollama")
                .arg("serve")
                .creation_flags(0x08000000) // CREATE_NO_WINDOW
                .spawn()
                .map_err(|e| format!("Failed to start Ollama: {}", e))?;
        }
        #[cfg(not(target_os = "windows"))]
        {
            Command::new("ollama")
                .arg("serve")
                .spawn()
                .map_err(|e| format!("Failed to start Ollama: {}", e))?;
        }
    } else {
        // Use bundled Ollama
        #[cfg(target_os = "windows")]
        {
            Command::new(&ollama_path)
                .arg("serve")
                .creation_flags(0x08000000) // CREATE_NO_WINDOW
                .spawn()
                .map_err(|e| format!("Failed to start bundled Ollama: {}", e))?;
        }
        #[cfg(not(target_os = "windows"))]
        {
            Command::new(&ollama_path)
                .arg("serve")
                .spawn()
                .map_err(|e| format!("Failed to start bundled Ollama: {}", e))?;
        }
    }

    Ok(true)
}

/// Create a Qube locally and prepare for minting
#[tauri::command]
async fn create_qube_for_minting(
    user_id: String,
    password: String,
    qube_name: String,
    genesis_prompt: String,
    favorite_color: String,
    ai_provider: String,
    ai_model: String,
    evaluation_model: String,
) -> Result<CreateQubeForMintingResponse, String> {
    validate_identifier(&user_id, "user_id")?;
    validate_identifier(&qube_name, "qube_name")?;

    let bridge_path = get_python_bridge_path();
    let project_root = get_python_project_path();

    let (mut cmd, skip_bridge_arg) = create_backend_command();
    cmd.current_dir(&project_root);

    if !skip_bridge_arg {
        cmd.arg(&bridge_path);
    }

    let output = cmd
        .arg("create-qube-for-minting")
        .arg(&user_id)
        .arg("--name")
        .arg(&qube_name)
        .arg("--genesis-prompt")
        .arg(&genesis_prompt)
        .arg("--favorite-color")
        .arg(&favorite_color)
        .arg("--ai-provider")
        .arg(&ai_provider)
        .arg("--ai-model")
        .arg(&ai_model)
        .arg("--evaluation-model")
        .arg(&evaluation_model)
        .arg("--password")
        .arg(&password)
        .output()
        .map_err(|e| format!("Failed to execute Python: {}", e))?;

    let stdout = String::from_utf8_lossy(&output.stdout).to_string();

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr).to_string();
        return Ok(CreateQubeForMintingResponse {
            success: false,
            qube_id: None,
            public_key: None,
            genesis_block_hash: None,
            recipient_address: None,
            error: Some(format!("Failed to create qube: {}", stderr)),
        });
    }

    serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse response: {}. Output: {}", e, stdout))
}

/// Pre-register Qube with minting server
#[tauri::command]
async fn pre_register_qube(
    qube_id: String,
    qube_name: String,
    public_key: String,
    genesis_block_hash: String,
    recipient_address: String,
    creator_public_key: String,
) -> Result<PreRegisterResponse, String> {
    let client = reqwest::Client::new();

    let payload = serde_json::json!({
        "qube_id": qube_id,
        "qube_name": qube_name,
        "public_key": public_key,
        "genesis_block_hash": genesis_block_hash,
        "recipient_address": recipient_address,
        "creator": creator_public_key,
        "birth_timestamp": std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_secs(),
    });

    match client
        .post("https://qube.cash/api/register/pre-register")
        .json(&payload)
        .send()
        .await
    {
        Ok(response) => {
            let status = response.status();
            let response_text = response.text().await.unwrap_or_default();

            if status.is_success() {
                if let Ok(json) = serde_json::from_str::<serde_json::Value>(&response_text) {
                    return Ok(PreRegisterResponse {
                        success: true,
                        registration_id: json.get("registration_id").and_then(|v| v.as_str()).map(String::from),
                        payment_amount_satoshis: json.get("amount_satoshis").and_then(|v| v.as_i64()),
                        payment_amount_bch: json.get("amount_bch").and_then(|v| v.as_str()).map(String::from),
                        error: None,
                    });
                }
            }
            Ok(PreRegisterResponse {
                success: false,
                registration_id: None,
                payment_amount_satoshis: None,
                payment_amount_bch: None,
                error: Some(format!("Server error: {}", response_text)),
            })
        }
        Err(e) => Ok(PreRegisterResponse {
            success: false,
            registration_id: None,
            payment_amount_satoshis: None,
            payment_amount_bch: None,
            error: Some(format!("Request failed: {}", e)),
        }),
    }
}

/// Check registration status with server
#[tauri::command]
async fn check_registration_status(registration_id: String) -> Result<RegistrationStatusResponse, String> {
    let client = reqwest::Client::new();

    match client
        .get(&format!("https://qube.cash/api/register/status/{}", registration_id))
        .send()
        .await
    {
        Ok(response) => {
            let status = response.status();
            let response_text = response.text().await.unwrap_or_default();

            if status.is_success() {
                if let Ok(json) = serde_json::from_str::<serde_json::Value>(&response_text) {
                    return Ok(RegistrationStatusResponse {
                        status: json.get("status").and_then(|v| v.as_str()).unwrap_or("unknown").to_string(),
                        payment_detected: json.get("payment_detected").and_then(|v| v.as_bool()),
                        mint_result: json.get("mint_result").cloned(),
                        error: None,
                    });
                }
            }
            Ok(RegistrationStatusResponse {
                status: "error".to_string(),
                payment_detected: None,
                mint_result: None,
                error: Some(format!("Failed to get status: {}", response_text)),
            })
        }
        Err(e) => Ok(RegistrationStatusResponse {
            status: "error".to_string(),
            payment_detected: None,
            mint_result: None,
            error: Some(format!("Request failed: {}", e)),
        }),
    }
}

/// Open external URL in default browser
#[tauri::command]
async fn open_external_url(url: String) -> Result<bool, String> {
    // Basic URL validation
    if !url.starts_with("http://") && !url.starts_with("https://") {
        return Err("Invalid URL: must start with http:// or https://".to_string());
    }

    #[cfg(target_os = "windows")]
    {
        Command::new("cmd")
            .args(["/C", "start", "", &url])
            .spawn()
            .map_err(|e| format!("Failed to open URL: {}", e))?;
    }

    #[cfg(target_os = "macos")]
    {
        Command::new("open")
            .arg(&url)
            .spawn()
            .map_err(|e| format!("Failed to open URL: {}", e))?;
    }

    #[cfg(target_os = "linux")]
    {
        Command::new("xdg-open")
            .arg(&url)
            .spawn()
            .map_err(|e| format!("Failed to open URL: {}", e))?;
    }

    Ok(true)
}

/// Sync Qube to chain (backup to IPFS, encrypted to owner)
#[tauri::command]
async fn sync_to_chain(
    user_id: String,
    qube_id: String,
    password: String,
) -> Result<SyncToChainResponse, String> {
    validate_identifier(&user_id, "user_id")?;
    validate_identifier(&qube_id, "qube_id")?;

    let project_root = get_python_project_path();
    let (mut cmd, skip_bridge_arg) = create_backend_command();
    cmd.current_dir(&project_root);

    if !skip_bridge_arg {
        let bridge_path = get_python_bridge_path();
        cmd.arg(&bridge_path);
    }

    let output = cmd
        .arg("sync-to-chain")
        .arg(&user_id)
        .arg("--qube-id")
        .arg(&qube_id)
        .arg("--password")
        .arg(&password)
        .output()
        .map_err(|e| format!("Failed to execute Python bridge: {}", e))?;

    if !output.status.success() {
        let error = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python bridge error: {}", error));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let response: SyncToChainResponse = serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse JSON response: {}. Output: {}", e, stdout))?;

    Ok(response)
}

/// Transfer Qube to new owner (DESTRUCTIVE - deletes local copy)
#[tauri::command]
async fn transfer_qube(
    user_id: String,
    qube_id: String,
    recipient_address: String,
    recipient_public_key: String,
    wallet_wif: String,
    password: String,
) -> Result<TransferQubeResponse, String> {
    validate_identifier(&user_id, "user_id")?;
    validate_identifier(&qube_id, "qube_id")?;

    let project_root = get_python_project_path();
    let (mut cmd, skip_bridge_arg) = create_backend_command();
    cmd.current_dir(&project_root);

    if !skip_bridge_arg {
        let bridge_path = get_python_bridge_path();
        cmd.arg(&bridge_path);
    }

    let output = cmd
        .arg("transfer-qube")
        .arg(&user_id)
        .arg("--qube-id")
        .arg(&qube_id)
        .arg("--recipient-address")
        .arg(&recipient_address)
        .arg("--recipient-public-key")
        .arg(&recipient_public_key)
        .arg("--wallet-wif")
        .arg(&wallet_wif)
        .arg("--password")
        .arg(&password)
        .output()
        .map_err(|e| format!("Failed to execute Python bridge: {}", e))?;

    if !output.status.success() {
        let error = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python bridge error: {}", error));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let response: TransferQubeResponse = serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse JSON response: {}. Output: {}", e, stdout))?;

    Ok(response)
}

/// Import Qube from wallet
#[tauri::command]
async fn import_from_wallet(
    user_id: String,
    wallet_wif: String,
    category_id: String,
    password: String,
) -> Result<ImportFromWalletResponse, String> {
    validate_identifier(&user_id, "user_id")?;

    let project_root = get_python_project_path();
    let (mut cmd, skip_bridge_arg) = create_backend_command();
    cmd.current_dir(&project_root);

    if !skip_bridge_arg {
        let bridge_path = get_python_bridge_path();
        cmd.arg(&bridge_path);
    }

    let output = cmd
        .arg("import-from-wallet")
        .arg(&user_id)
        .arg("--wallet-wif")
        .arg(&wallet_wif)
        .arg("--category-id")
        .arg(&category_id)
        .arg("--password")
        .arg(&password)
        .output()
        .map_err(|e| format!("Failed to execute Python bridge: {}", e))?;

    if !output.status.success() {
        let error = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python bridge error: {}", error));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let response: ImportFromWalletResponse = serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse JSON response: {}. Output: {}", e, stdout))?;

    Ok(response)
}

/// Scan wallet for Qube NFTs
#[tauri::command]
async fn scan_wallet(
    user_id: String,
    wallet_address: String,
) -> Result<ScanWalletResponse, String> {
    validate_identifier(&user_id, "user_id")?;

    let project_root = get_python_project_path();
    let (mut cmd, skip_bridge_arg) = create_backend_command();
    cmd.current_dir(&project_root);

    if !skip_bridge_arg {
        let bridge_path = get_python_bridge_path();
        cmd.arg(&bridge_path);
    }

    let output = cmd
        .arg("scan-wallet")
        .arg(&user_id)
        .arg("--wallet-address")
        .arg(&wallet_address)
        .output()
        .map_err(|e| format!("Failed to execute Python bridge: {}", e))?;

    if !output.status.success() {
        let error = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python bridge error: {}", error));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let response: ScanWalletResponse = serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse JSON response: {}. Output: {}", e, stdout))?;

    Ok(response)
}

/// Resolve public key from BCH address
#[tauri::command]
async fn resolve_public_key(
    user_id: String,
    address: String,
) -> Result<ResolvePublicKeyResponse, String> {
    validate_identifier(&user_id, "user_id")?;

    let project_root = get_python_project_path();
    let (mut cmd, skip_bridge_arg) = create_backend_command();
    cmd.current_dir(&project_root);

    if !skip_bridge_arg {
        let bridge_path = get_python_bridge_path();
        cmd.arg(&bridge_path);
    }

    let output = cmd
        .arg("resolve-public-key")
        .arg(&user_id)
        .arg("--address")
        .arg(&address)
        .output()
        .map_err(|e| format!("Failed to execute Python bridge: {}", e))?;

    if !output.status.success() {
        let error = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python bridge error: {}", error));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let response: ResolvePublicKeyResponse = serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse JSON response: {}. Output: {}", e, stdout))?;

    Ok(response)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .invoke_handler(tauri::generate_handler![
            greet,
            authenticate,
            list_qubes,
            create_qube,
            prepare_qube_for_minting,
            check_minting_status,
            submit_payment_txid,
            cancel_pending_minting,
            list_pending_registrations,
            send_message,
            generate_speech,
            get_audio_base64,
            anchor_session,
            discard_session,
            delete_session_block,
            check_sessions,
            force_exit,
            update_qube_config,
            get_qube_blocks,
            delete_qube,
            save_image,
            upload_avatar_to_ipfs,
            analyze_image,
            start_multi_qube_conversation,
            get_next_speaker,
            continue_multi_qube_conversation,
            inject_multi_qube_user_message,
            lock_in_multi_qube_response,
            end_multi_qube_conversation,
            get_configured_api_keys,
            save_api_key,
            validate_api_key,
            delete_api_key,
            get_block_preferences,
            update_block_preferences,
            get_relationship_difficulty,
            set_relationship_difficulty,
            get_difficulty_presets,
            get_decision_config,
            update_decision_config,
            get_qube_relationships,
            get_relationship_timeline,
            get_google_tts_path,
            set_google_tts_path,
            get_qube_skills,
            save_qube_skills,
            add_skill_xp,
            unlock_skill,
            get_visualizer_settings,
            save_visualizer_settings,
            get_trust_personality,
            update_trust_personality,
            get_available_monitors,
            create_visualizer_window,
            close_visualizer_window,
            // NFT Authentication
            authenticate_nft,
            refresh_auth_token,
            get_nft_auth_status,
            // P2P Network
            get_online_qubes,
            generate_introduction,
            evaluate_introduction,
            process_p2p_message,
            send_introduction,
            get_pending_introductions,
            accept_introduction,
            reject_introduction,
            get_connections,
            create_p2p_session,
            get_p2p_sessions,
            // P2P Conversations (uses same logic as local multi-qube)
            start_p2p_conversation,
            continue_p2p_conversation,
            inject_p2p_block,
            send_p2p_user_message,
            // Setup Wizard
            check_first_run,
            create_user_account,
            check_ollama_status,
            start_ollama,
            create_qube_for_minting,
            pre_register_qube,
            check_registration_status,
            open_external_url,
            // Chain Sync (NFT-Bundled Storage)
            sync_to_chain,
            transfer_qube,
            import_from_wallet,
            scan_wallet,
            resolve_public_key
        ])
        .setup(|app| {
            // Get the main and splash windows
            let splashscreen_window = app.get_webview_window("splashscreen").unwrap();
            let main_window = app.get_webview_window("main").unwrap();

            // Clone for the thread
            let main_window_clone = main_window.clone();
            let splashscreen_window_clone = splashscreen_window.clone();

            // Wait for the main window to finish loading, then close splash
            std::thread::spawn(move || {
                // Wait 1.5 seconds to ensure main window is ready
                std::thread::sleep(std::time::Duration::from_millis(1500));

                // Show the main window
                main_window_clone.show().unwrap();

                // Close the splashscreen
                splashscreen_window_clone.close().unwrap();
            });

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

