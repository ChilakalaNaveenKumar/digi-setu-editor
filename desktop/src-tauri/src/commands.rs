//! Tauri IPC commands invoked from the SPA.
//!
//! Keep these tiny and pure. Anything stateful (sidecar lifecycle,
//! deep-link queue) lives in the modules that own that state and is
//! reached via the `AppState` handle Tauri injects.

use std::path::PathBuf;

use tauri::{AppHandle, Manager, State};
use tauri_plugin_dialog::DialogExt;
use tauri_plugin_opener::OpenerExt;

use crate::AppState;

/// SPA bootstrap calls this before issuing any HTTP — without it we'd
/// have to bake a port into the bundle, which breaks the second
/// instance of the app.
#[tauri::command]
pub fn get_backend_port(state: State<'_, AppState>) -> Option<u16> {
    *state.backend_port.lock().unwrap()
}

/// Always returns true when called from the desktop shell. The web
/// build of the SPA never sees this command (the IPC bridge isn't
/// installed), so the same SPA bundle running in a normal browser
/// returns `undefined` and the picker falls back to the web flow.
#[tauri::command]
pub fn is_desktop() -> bool {
    true
}

/// Native folder picker. Replaces the `window.prompt(...)` in
/// `web/frontend/src/views/Picker.vue#pickDesktopWorkspace` when
/// running inside the Tauri shell.
///
/// Returns `None` when the user cancels — the caller should treat
/// that as "do nothing" rather than as an error.
#[tauri::command]
pub async fn pick_folder(app: AppHandle) -> Result<Option<String>, String> {
    use tokio::sync::oneshot;

    let (tx, rx) = oneshot::channel();
    app.dialog()
        .file()
        .set_title("Pick a folder for your Digi Setu workspace")
        .pick_folder(move |maybe_path| {
            // tauri-plugin-dialog v2 returns FilePath; normalize to
            // an absolute string the FastAPI side can consume directly
            // via the existing register_desktop_workspace path.
            let resolved = maybe_path.and_then(|p| match p {
                tauri_plugin_dialog::FilePath::Path(buf) => {
                    Some(buf.to_string_lossy().to_string())
                }
                tauri_plugin_dialog::FilePath::Url(url) => {
                    // Some platforms hand back file:// URLs. Strip the
                    // scheme so the backend's Path().resolve() works.
                    PathBuf::from(url.path())
                        .to_str()
                        .map(|s| s.to_string())
                }
            });
            let _ = tx.send(resolved);
        });

    rx.await.map_err(|err| err.to_string())
}

/// OAuth + Stripe Checkout open in the user's default browser, NOT in
/// the embedded webview. This avoids: (a) Clerk's anti-phishing checks
/// that refuse non-browser user agents, (b) Stripe's 3DS flows that
/// require a real browser, and (c) credential autofill the user
/// expects to "just work".
#[tauri::command]
pub async fn open_external_url(app: AppHandle, url: String) -> Result<(), String> {
    log::info!("Opening external URL: {url}");
    app.opener()
        .open_url(&url, None::<&str>)
        .map_err(|err| err.to_string())
}

/// Where the desktop app keeps registry/snapshots/chats. Surfaced to
/// the SPA so the Settings page can show "your data lives here" + a
/// "reveal in Finder" button.
#[tauri::command]
pub fn app_data_dir(app: AppHandle) -> Result<String, String> {
    app.path()
        .app_data_dir()
        .map(|p| p.to_string_lossy().to_string())
        .map_err(|err| err.to_string())
}

/// Spawn a new top-level window. Same SPA, same backend port, just a
/// new webview so the user can have two workspaces / two chats side by
/// side. Wired to File ▸ New Window in the menu, but also exposed as
/// an IPC command so future UI affordances (e.g. a "+" in the picker
/// to "open this folder in a new window") can call it directly.
#[tauri::command]
pub fn open_new_window(app: AppHandle) -> Result<(), String> {
    crate::menu::open_new_window(&app).map_err(|err| err.to_string())
}

/// Force-restart the FastAPI sidecar.
///
/// Called from the SPA's frontend-side health watchdog when the
/// chat WebSocket bridge can't reach the backend after exhausting
/// its own reconnect attempts AND a direct ``GET /healthz`` probe
/// also times out — i.e. when the user is staring at a stuck
/// "Lost connection" banner that the WebSocket layer can't unstick.
///
/// Implementation: kill the current child (if alive), let the
/// watchdog's normal "child exited" path notice and spawn a fresh
/// sidecar. We deliberately route through the watchdog rather than
/// calling ``spawn_sidecar`` directly so the AppState book-keeping
/// (port update, ``backend-restarted`` emit, etc.) stays in one
/// code path.
///
/// Returns Ok with the (still-old) port if a respawn is in flight;
/// the SPA then waits for the ``backend-restarted`` event before
/// rebinding its API base. If there's no live sidecar handle to
/// kill we return an Err so the SPA can show a clear "couldn't
/// restart, please reopen the app" message rather than a silent
/// no-op.
#[tauri::command]
pub fn restart_sidecar(state: State<'_, AppState>) -> Result<u16, String> {
    let port = state
        .backend_port
        .lock()
        .unwrap()
        .ok_or_else(|| "no sidecar handle to restart".to_string())?;

    // Take a clone of the handle (cheap — Arc bumps), don't take()
    // it out of AppState. The watchdog still owns its own clone and
    // will pick up the exit. We also preserve the AppState's handle
    // so the next .terminate() on app-exit still has something to
    // kill if the watchdog hasn't yet replaced the child slot.
    //
    // Dereference the guard before .clone() — MutexGuard isn't Clone
    // but the Option<SidecarHandle> inside it is.
    let handle = (*state.sidecar.lock().unwrap()).clone();
    let Some(handle) = handle else {
        return Err("sidecar already shut down".to_string());
    };

    // Kill the child but DON'T flip the shutdown flag — we WANT
    // the watchdog to respawn this one. ``handle.terminate()``
    // would set ``shutdown=true`` and stop the watchdog forever,
    // so we open the lock and kill manually.
    if let Some(mut child) = handle.kill_child_for_restart() {
        match child.kill() {
            Ok(_) => log::info!("restart_sidecar: SIGKILL sent to pid={}", child.id()),
            Err(err) => {
                log::warn!("restart_sidecar: kill failed: {err} (assuming already dead)");
            }
        }
        let _ = child.wait();
    }
    Ok(port)
}
