#[tauri::command]
async fn create_visualizer_window(
    app: tauri::AppHandle,
    monitor_index: usize,
) -> Result<GenericSuccessResponse, String> {
    use tauri::Manager;
    use tauri::WebviewWindowBuilder;
    use tauri::WebviewUrl;

    println!("🔍 DEBUG: create_visualizer_window called with monitor_index: {}", monitor_index);

    // Close existing visualizer window if it exists
    if let Some(window) = app.get_webview_window("visualizer") {
        println!("🔍 DEBUG: Closing existing visualizer window");
        let _ = window.close();
    }

    // Get available monitors
    let monitors = app.available_monitors()
        .map_err(|e| format!("Failed to get monitors: {}", e))?;

    println!("🔍 DEBUG: Total monitors available: {}", monitors.len());
    for (idx, mon) in monitors.iter().enumerate() {
        let size = mon.size();
        let pos = mon.position();
        println!("🔍 DEBUG: Monitor[{}]: {}x{} at ({}, {})",
            idx, size.width, size.height, pos.x, pos.y);
    }

    if monitor_index == 0 || monitor_index > monitors.len() {
        let err_msg = format!("Invalid monitor index: {} (valid range: 1-{})",
            monitor_index, monitors.len());
        println!("❌ ERROR: {}", err_msg);
        return Err(err_msg);
    }

    let target_monitor = &monitors[monitor_index - 1];
    let size = target_monitor.size();
    let position = target_monitor.position();

    println!("🔍 DEBUG: Target monitor (index {}): {}x{} at ({}, {})",
        monitor_index, size.width, size.height, position.x, position.y);

    // APPROACH 1: Try borderless fullscreen window
    match WebviewWindowBuilder::new(
        &app,
        "visualizer",
        WebviewUrl::App("visualizer".into())
    )
    .title("Qubes Visualizer")
    .decorations(false)
    .resizable(false)
    .position(position.x as f64, position.y as f64)
    .inner_size(size.width as f64, size.height as f64)
    .always_on_top(true)
    .focused(false)
    .skip_taskbar(true)
    .build() {
        Ok(window) => {
            println!("✅ SUCCESS: Visualizer window created");

            // APPROACH 2: Force position after creation (Windows workaround)
            // Sometimes Windows doesn't respect position at creation time
            std::thread::sleep(std::time::Duration::from_millis(100));

            if let Err(e) = window.set_position(tauri::Position::Physical(tauri::PhysicalPosition {
                x: position.x,
                y: position.y,
            })) {
                println!("⚠️  WARNING: Failed to set position after creation: {}", e);
            } else {
                println!("✅ Position explicitly set to ({}, {})", position.x, position.y);
            }

            // Verify final position
            if let Ok(actual_pos) = window.outer_position() {
                println!("🔍 DEBUG: Window final position: ({}, {})", actual_pos.x, actual_pos.y);
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
            let err_msg = format!("Failed to create visualizer window: {}", e);
            println!("❌ ERROR: {}", err_msg);
            Err(err_msg)
        }
    }
}
