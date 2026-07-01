#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod backend;

// Optional: uncomment for MCP client registration (Cursor / Claude Desktop)
// mod mcp_client;

use backend::{BackendProcess, spawn_backend};
use tauri::{Emitter, Manager};

#[tauri::command]
async fn start_backend(
    app: tauri::AppHandle,
    state: tauri::State<'_, BackendProcess>,
) -> Result<String, String> {
    spawn_backend(app, &state)
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_process::init())
        .manage(BackendProcess(std::sync::Mutex::new(None)))
        .invoke_handler(tauri::generate_handler![start_backend])
        .setup(|app| {
            let handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                match spawn_backend(handle.clone(), handle.state::<BackendProcess>().inner()) {
                    Ok(msg) => {
                        eprintln!("Backend started: {msg}");
                    }
                    Err(e) => {
                        eprintln!("Backend error: {e}");
                        let _ = handle.emit("backend-status", format!("error: {e}"));
                    }
                }
            });
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error building tauri application")
        .run(|app, event| {
            if let tauri::RunEvent::Exit | tauri::RunEvent::ExitRequested { .. } = event {
                if let Some(mut child) = app.state::<BackendProcess>().0.lock().unwrap().take() {
                    let _ = child.kill();
                }
            }
        });
}
