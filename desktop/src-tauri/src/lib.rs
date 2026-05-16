//! Digi Setu desktop runtime.
//!
//! Responsibilities, in order of importance:
//!
//! 1. Spawn the PyInstaller-frozen FastAPI sidecar (`web/backend` packaged
//!    into a single binary) on a free local port with `PI_MODE=desktop`
//!    and the right `PI_DATA_ROOT` for the user's OS.
//! 2. Wait for the sidecar's `/health` to come up, then load the bundled
//!    Vue SPA which talks to it via `localhost:<port>`.
//! 3. Expose a couple of native helpers to the SPA via Tauri IPC:
//!    - `pick_folder()` for the workspace picker (replaces the web-mode
//!      `window.prompt` fallback in `web/frontend/src/views/Picker.vue`).
//!    - `get_backend_port()` so the SPA can rebuild its API base URL
//!      without baking it into the bundle.
//!    - `open_external_url(url)` for OAuth/billing flows that must open
//!      in the user's default browser.
//! 4. Receive deep-link callbacks (`digi-setu://auth/callback?...`,
//!    `digi-setu://billing/return?...`) and forward them into the
//!    webview as a custom JS event so the SPA's auth store can pick up
//!    the Clerk token / Stripe session id.
//! 5. Kill the sidecar cleanly on app exit so we don't orphan a Python
//!    process holding a port.
//!
//! This module is intentionally thin. All business logic — chat, file
//! tree, snapshots, billing — lives in the FastAPI backend exactly as
//! it does in web mode. The desktop binary is just an OS wrapper.

mod commands;
mod deeplink;
mod menu;
mod secure_storage;
mod sidecar;
mod updater;

use std::sync::Mutex;
use tauri::{Emitter, Manager};

/// Shared application state — populated during `setup()`.
pub struct AppState {
    /// Local TCP port the sidecar bound to. The frontend reads this via
    /// `get_backend_port()` so it can build absolute URLs to /api and /ws.
    pub backend_port: Mutex<Option<u16>>,
    /// Handle to the running sidecar so we can kill it on app exit.
    pub sidecar: Mutex<Option<sidecar::SidecarHandle>>,
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    env_logger::Builder::from_env(env_logger::Env::default().default_filter_or("info"))
        .format_timestamp_millis()
        .init();

    log::info!("Digi Setu desktop starting up");

    tauri::Builder::default()
        // Single-instance MUST be the very first plugin: when a second
        // launch happens (e.g. double-click in the macOS Dock while the
        // app is already running) Tauri short-circuits inside this
        // plugin and invokes our callback in the existing process
        // *before* any other setup runs. Without this, a second launch
        // would spawn a second sidecar fighting for the same
        // ~/.digi-setu/registry.json — that's where the duplicate
        // workspace bug came from in the first place.
        .plugin(tauri_plugin_single_instance::init(|app, _argv, _cwd| {
            // The user clicked the dock icon (or `open -a "Digi Setu"`)
            // while we were already running. Pull the existing window to
            // the front instead of spinning up a second instance.
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.unminimize();
                let _ = window.show();
                let _ = window.set_focus();
            }
        }))
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_os::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_deep_link::init())
        // Updater + process plugins. ``tauri_plugin_updater`` reads its
        // endpoints + pubkey from ``tauri.conf.json#plugins.updater``
        // and exposes a Rust API the IPC commands in ``updater.rs``
        // wrap into a SPA-friendly surface. ``tauri_plugin_process``
        // gives us ``app.restart()`` (used by ``apply_update_and_restart``)
        // and is required by the updater plugin in Tauri 2.x.
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .manage(AppState {
            backend_port: Mutex::new(None),
            sidecar: Mutex::new(None),
        })
        .setup(|app| {
            // Native menu. Built once at startup and shared across every
            // window (macOS hangs the menu off the application; Windows
            // hangs it off each window — Tauri abstracts both).
            let menu = menu::build(app.handle())?;
            app.set_menu(menu)?;

            // Sidecar boot is async (PyInstaller binary takes 1-2s on cold
            // start) and has to happen BEFORE the webview navigates to the
            // SPA's index.html — otherwise every API call 500s for the
            // first second. We block the setup hook on the spawn but let
            // the health-check race the window opening; the SPA is
            // tolerant of the API being briefly absent (it has a retry
            // loop for /api/config).
            let app_handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                match sidecar::spawn_sidecar(&app_handle).await {
                    Ok((handle, port)) => {
                        log::info!("Sidecar up on 127.0.0.1:{port}");
                        let state = app_handle.state::<AppState>();
                        *state.backend_port.lock().unwrap() = Some(port);
                        // Clone the handle into the watchdog BEFORE
                        // moving the original into AppState — both
                        // references share the same child / shutdown
                        // Arc, so .terminate() on app-exit and the
                        // watchdog's poll see the same state.
                        let watchdog_handle = handle.clone();
                        *state.sidecar.lock().unwrap() = Some(handle);
                        // Tell the webview the port is ready. The SPA's
                        // bootstrap listens for this event before issuing
                        // its first API call (see frontend-bridge).
                        let _ = app_handle.emit("backend-ready", port);
                        // Continuous liveness watchdog. If the sidecar
                        // ever exits (panic, OOM, broken pi import, OS
                        // kill) the watchdog respawns it and emits
                        // ``backend-restarted`` with the new port so
                        // the SPA can rebind its API base + force
                        // every open WS to reconnect.
                        sidecar::spawn_watchdog(app_handle.clone(), watchdog_handle);
                    }
                    Err(err) => {
                        log::error!("Failed to spawn sidecar: {err}");
                        // No sidecar = no app. Tell the webview so it
                        // can render a friendly error instead of an
                        // infinite loading spinner.
                        let _ = app_handle.emit("backend-failed", err.to_string());
                    }
                }
            });

            // Deep-link plugin needs explicit registration on Linux/Win;
            // on Mac the URL scheme is registered via Info.plist by the
            // bundler. The handler emits a `deep-link` event into the
            // webview which the SPA's auth store listens for.
            deeplink::register(app)?;

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::get_backend_port,
            commands::pick_folder,
            commands::open_external_url,
            commands::app_data_dir,
            commands::is_desktop,
            commands::open_new_window,
            commands::restart_sidecar,
            commands::restart_and_clean,
            updater::check_for_update,
            updater::apply_update_and_restart,
            secure_storage::secure_store_session,
            secure_storage::secure_load_session,
            secure_storage::secure_delete_session,
        ])
        .on_menu_event(|app_handle, event| {
            handle_menu_event(app_handle, event.id().as_ref());
        })
        .on_window_event(|window, event| {
            // Sidecar lifecycle is tied to the LAST window closing, not
            // the first one. With multi-window enabled (File ▸ New
            // Window) the user may close window-2 while window-1 is
            // still streaming a chat; killing the sidecar there would
            // cut off the live request. We count the remaining windows
            // (including this one — it's still in the registry until
            // CloseRequested returns) and only terminate the Python
            // process when this is the last one going down.
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                let app_handle = window.app_handle();
                let remaining = app_handle.webview_windows().len();
                if remaining > 1 {
                    log::info!(
                        "Window {} closing — sidecar kept alive ({} window(s) remain)",
                        window.label(),
                        remaining - 1,
                    );
                    return;
                }
                let state = app_handle.state::<AppState>();
                let maybe_sidecar = state.sidecar.lock().unwrap().take();
                if let Some(handle) = maybe_sidecar {
                    log::info!("Last window closing — terminating sidecar");
                    handle.terminate();
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("Tauri app failed to start");
}

/// Handle a click on any of our custom menu items. `id` is the stable
/// string from `menu::ids::*`. Predefined items (Cut/Copy/Paste/Quit/
/// Minimize/etc.) never reach this — Tauri routes them straight to the
/// OS, so the matcher only deals with our app-level commands.
fn handle_menu_event(app: &tauri::AppHandle, id: &str) {
    use menu::ids;

    // Pick the window the menu click logically targets. Tauri's
    // `AppHandle` doesn't expose a `get_focused_window()` shortcut
    // (windows know their own focus state, the handle doesn't), so
    // we iterate. Falling back to `main` covers the case where the
    // user used a global keyboard shortcut while no window happened
    // to hold focus.
    let active_window = || -> Option<tauri::WebviewWindow> {
        app.webview_windows()
            .values()
            .find(|w| w.is_focused().unwrap_or(false))
            .cloned()
            .or_else(|| app.get_webview_window("main"))
    };
    // Emit a JSON-serialisable () payload so the proc-macro that
    // generates the typed event surface picks the right impl.
    let emit_to_active = |event: &str| {
        if let Some(w) = active_window() {
            let _ = w.emit::<()>(event, ());
        }
    };

    match id {
        ids::NEW_WINDOW => {
            if let Err(err) = menu::open_new_window(app) {
                log::error!("Failed to open new window: {err}");
            }
        }
        ids::OPEN_FOLDER => emit_to_active("menu:open_folder"),
        ids::CLOSE_FOLDER => emit_to_active("menu:close_folder"),
        ids::NEW_CHAT => emit_to_active("menu:new_chat"),
        ids::FIND_IN_CHAT => emit_to_active("menu:find_in_chat"),
        ids::FOCUS_CHAT => emit_to_active("menu:focus_chat"),
        // The SPA listens for these on every window and mounts the
        // matching modal / triggers the IPC. Doing the IPC directly
        // here would skip the SPA's progress UI (download bar for
        // updates, "respawning…" banner for restart-clean) which is
        // the whole point of having a UI in the first place.
        ids::RESTART_AND_CLEAN => emit_to_active("menu:restart_and_clean"),
        ids::CHECK_FOR_UPDATES => emit_to_active("menu:check_for_updates"),
        ids::RELOAD => {
            // Cmd+Shift+R bypasses the Cmd+R suppressor we set up in
            // main.ts (which exists to stop accidental reloads from
            // killing an in-flight chat). The menu path is an
            // explicit user action so we honour it.
            if let Some(w) = active_window() {
                let _ = w.eval("window.location.reload()");
            }
        }
        ids::TOGGLE_DEVTOOLS => {
            // DevTools accessor is only compiled in debug builds —
            // Tauri gates `open_devtools` behind `cfg(any(debug_assertions,
            // feature = "devtools"))`. We don't ship a `devtools` feature,
            // so this is `cfg(debug_assertions)` only. In release the
            // menu item is still visible but is a no-op (rather than
            // silently disappearing on us).
            #[cfg(debug_assertions)]
            if let Some(w) = active_window() {
                if w.is_devtools_open() {
                    w.close_devtools();
                } else {
                    w.open_devtools();
                }
            }
        }
        ids::ZOOM_IN => emit_to_active("menu:zoom_in"),
        ids::ZOOM_OUT => emit_to_active("menu:zoom_out"),
        ids::ZOOM_RESET => emit_to_active("menu:zoom_reset"),
        ids::TOGGLE_FULLSCREEN => {
            if let Some(w) = active_window() {
                let next = !w.is_fullscreen().unwrap_or(false);
                let _ = w.set_fullscreen(next);
            }
        }
        ids::HELP_DOCS => open_external(app, "https://digi-setu.com/docs"),
        ids::HELP_REPORT => open_external(
            app,
            "https://github.com/Digi-Setu/digi-setu/issues/new",
        ),
        ids::HELP_HOMEPAGE => open_external(app, "https://digi-setu.com"),
        ids::HELP_PRIVACY => open_external(app, "https://digi-setu.com/privacy"),
        ids::HELP_TERMS => open_external(app, "https://digi-setu.com/terms"),
        ids::HELP_LICENSES => open_bundled_licenses(app),
        _ => log::debug!("Unhandled menu id: {id}"),
    }
}

/// Open `THIRD_PARTY_LICENSES.txt` in the user's default text app.
///
/// In dev mode the file lives at the repo root next to `desktop/`; in
/// release mode it's staged into the bundle's resources directory.
/// Tauri's `path().resource_dir()` resolves to the right location in
/// both modes (it falls back to `cargo target/<profile>/` during
/// `cargo run`), so we ask Tauri rather than pretending we know the
/// install layout.
fn open_bundled_licenses(app: &tauri::AppHandle) {
    use tauri_plugin_opener::OpenerExt;
    let resource_path = app
        .path()
        .resource_dir()
        .ok()
        .map(|p| p.join("THIRD_PARTY_LICENSES.txt"));

    let candidate = match resource_path {
        Some(p) if p.exists() => Some(p),
        _ => {
            // Dev fallback: relative to the workspace root. tauri::Manager's
            // resource_dir doesn't always resolve during `cargo run` from a
            // sibling crate, so we walk up from CARGO_MANIFEST_DIR.
            let manifest_dir = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"));
            let dev_path = manifest_dir.join("..").join("THIRD_PARTY_LICENSES.txt");
            if dev_path.exists() {
                Some(dev_path)
            } else {
                None
            }
        }
    };

    match candidate {
        Some(path) => {
            if let Err(err) = app.opener().open_path(path.to_string_lossy(), None::<&str>) {
                log::error!("Failed to open licenses file: {err}");
            }
        }
        None => {
            log::warn!(
                "THIRD_PARTY_LICENSES.txt not found; run desktop/scripts/gen-third-party-licenses.mjs"
            );
            // Fall back to the hosted copy.
            open_external(app, "https://digi-setu.com/licenses");
        }
    }
}

fn open_external(app: &tauri::AppHandle, url: &str) {
    use tauri_plugin_opener::OpenerExt;
    if let Err(err) = app.opener().open_url(url, None::<&str>) {
        log::error!("Failed to open {url}: {err}");
    }
}
