//! Native menu bar (macOS Cocoa menu / Windows window menu).
//!
//! This is the same shape Cursor / VS Code expose: a small, hand-curated
//! set of items that map either to predefined OS commands (Cut / Copy /
//! Paste / Quit / Minimize) or to Tauri events the SPA listens for.
//!
//! Design principles:
//! * Items that need OS-level behaviour (text editing, window mgmt) use
//!   `PredefinedMenuItem::*` so the user gets exactly what they expect
//!   from a native app — accelerator labels, system services, all of it.
//! * Items that need APP-level behaviour (open folder, new chat, reload)
//!   are custom `MenuItem`s with a stable string id; they're routed in
//!   `lib.rs` via `App::on_menu_event`. The id is also what the SPA sees
//!   when a menu fires a frontend event, so don't change them lightly.
//! * The "App" submenu (with About / Settings / Quit) is macOS-only; on
//!   Windows / Linux those items live under File / Help.
//! * "New Window" must keep working when the single-instance plugin is
//!   installed, because that plugin only short-circuits *second OS
//!   processes* — additional WebviewWindows inside the same process are
//!   completely independent.

use tauri::menu::{
    AboutMetadataBuilder, Menu, MenuBuilder, MenuItemBuilder, PredefinedMenuItem,
    SubmenuBuilder,
};
use tauri::{AppHandle, Manager, Runtime, WebviewUrl, WebviewWindowBuilder};

/// Stable ids for our custom menu items. Centralised so lib.rs's
/// `on_menu_event` matcher and the frontend's listener can't drift.
pub mod ids {
    pub const NEW_WINDOW: &str = "new_window";
    pub const OPEN_FOLDER: &str = "open_folder";
    pub const CLOSE_FOLDER: &str = "close_folder";
    pub const RELOAD: &str = "reload_window";
    pub const TOGGLE_DEVTOOLS: &str = "toggle_devtools";
    pub const ZOOM_IN: &str = "zoom_in";
    pub const ZOOM_OUT: &str = "zoom_out";
    pub const ZOOM_RESET: &str = "zoom_reset";
    pub const TOGGLE_FULLSCREEN: &str = "toggle_fullscreen";
    pub const FOCUS_CHAT: &str = "focus_chat";
    pub const NEW_CHAT: &str = "new_chat";
    pub const FIND_IN_CHAT: &str = "find_in_chat";
    pub const HELP_DOCS: &str = "help_docs";
    pub const HELP_REPORT: &str = "help_report";
    pub const HELP_HOMEPAGE: &str = "help_homepage";
    pub const HELP_LICENSES: &str = "help_licenses";
    pub const HELP_PRIVACY: &str = "help_privacy";
    pub const HELP_TERMS: &str = "help_terms";
}

/// Build and attach the native menu to the running app. Called once
/// from `setup()` in lib.rs.
pub fn build<R: Runtime>(app: &AppHandle<R>) -> tauri::Result<Menu<R>> {
    // ── App submenu (macOS) ──────────────────────────────────────────
    // `name` falls through to the bundle's CFBundleName on macOS, which
    // is set to "Digi Setu" via tauri.conf.json `productName`.
    let about_metadata = AboutMetadataBuilder::new()
        .name(Some("Digi Setu"))
        .version(Some(env!("CARGO_PKG_VERSION")))
        .copyright(Some("© 2026 Digi Setu"))
        .website(Some("https://digi-setu.com"))
        .build();

    let app_submenu = SubmenuBuilder::new(app, "Digi Setu")
        .item(&PredefinedMenuItem::about(
            app,
            Some("About Digi Setu"),
            Some(about_metadata),
        )?)
        .separator()
        .item(&PredefinedMenuItem::services(app, None)?)
        .separator()
        .item(&PredefinedMenuItem::hide(app, None)?)
        .item(&PredefinedMenuItem::hide_others(app, None)?)
        .item(&PredefinedMenuItem::show_all(app, None)?)
        .separator()
        .item(&PredefinedMenuItem::quit(app, None)?)
        .build()?;

    // ── File submenu ─────────────────────────────────────────────────
    let new_window_item = MenuItemBuilder::with_id(ids::NEW_WINDOW, "New Window")
        .accelerator("CmdOrCtrl+Shift+N")
        .build(app)?;
    let new_chat_item = MenuItemBuilder::with_id(ids::NEW_CHAT, "New Chat")
        .accelerator("CmdOrCtrl+T")
        .build(app)?;
    let open_folder_item = MenuItemBuilder::with_id(ids::OPEN_FOLDER, "Open Folder…")
        .accelerator("CmdOrCtrl+O")
        .build(app)?;
    let close_folder_item =
        MenuItemBuilder::with_id(ids::CLOSE_FOLDER, "Close Folder").build(app)?;

    let file_submenu = SubmenuBuilder::new(app, "File")
        .item(&new_window_item)
        .item(&new_chat_item)
        .separator()
        .item(&open_folder_item)
        .separator()
        .item(&close_folder_item)
        .item(&PredefinedMenuItem::close_window(app, None)?)
        .build()?;

    // ── Edit submenu ─────────────────────────────────────────────────
    // All predefined — the OS does the right thing for text editing.
    let find_item = MenuItemBuilder::with_id(ids::FIND_IN_CHAT, "Find in Chat")
        .accelerator("CmdOrCtrl+F")
        .build(app)?;

    let edit_submenu = SubmenuBuilder::new(app, "Edit")
        .item(&PredefinedMenuItem::undo(app, None)?)
        .item(&PredefinedMenuItem::redo(app, None)?)
        .separator()
        .item(&PredefinedMenuItem::cut(app, None)?)
        .item(&PredefinedMenuItem::copy(app, None)?)
        .item(&PredefinedMenuItem::paste(app, None)?)
        .item(&PredefinedMenuItem::select_all(app, None)?)
        .separator()
        .item(&find_item)
        .build()?;

    // ── View submenu ─────────────────────────────────────────────────
    let reload_item = MenuItemBuilder::with_id(ids::RELOAD, "Reload Window")
        .accelerator("CmdOrCtrl+Shift+R")
        .build(app)?;
    let devtools_item = MenuItemBuilder::with_id(ids::TOGGLE_DEVTOOLS, "Toggle Developer Tools")
        .accelerator("CmdOrCtrl+Option+I")
        .build(app)?;
    let zoom_in_item = MenuItemBuilder::with_id(ids::ZOOM_IN, "Zoom In")
        .accelerator("CmdOrCtrl+Plus")
        .build(app)?;
    let zoom_out_item = MenuItemBuilder::with_id(ids::ZOOM_OUT, "Zoom Out")
        .accelerator("CmdOrCtrl+-")
        .build(app)?;
    let zoom_reset_item = MenuItemBuilder::with_id(ids::ZOOM_RESET, "Actual Size")
        .accelerator("CmdOrCtrl+0")
        .build(app)?;
    let fullscreen_item = MenuItemBuilder::with_id(ids::TOGGLE_FULLSCREEN, "Toggle Full Screen")
        .accelerator(if cfg!(target_os = "macos") { "Ctrl+Cmd+F" } else { "F11" })
        .build(app)?;
    let focus_chat_item = MenuItemBuilder::with_id(ids::FOCUS_CHAT, "Focus Chat")
        .accelerator("CmdOrCtrl+L")
        .build(app)?;

    let view_submenu = SubmenuBuilder::new(app, "View")
        .item(&reload_item)
        // DevTools accessor only compiled into debug builds; in release
        // we hide it entirely so the binary doesn't advertise it.
        .item(&devtools_item)
        .separator()
        .item(&focus_chat_item)
        .separator()
        .item(&zoom_in_item)
        .item(&zoom_out_item)
        .item(&zoom_reset_item)
        .separator()
        .item(&fullscreen_item)
        .build()?;

    // ── Window submenu ───────────────────────────────────────────────
    // macOS-style: Minimize / Zoom / Bring All to Front. On other
    // platforms these still work, just mapped to the platform's
    // equivalents (or no-op if unsupported).
    let window_submenu = SubmenuBuilder::new(app, "Window")
        .item(&PredefinedMenuItem::minimize(app, None)?)
        .item(&PredefinedMenuItem::maximize(app, None)?)
        .separator()
        .item(&PredefinedMenuItem::bring_all_to_front(app, None)?)
        .build()?;

    // ── Help submenu ─────────────────────────────────────────────────
    let docs_item =
        MenuItemBuilder::with_id(ids::HELP_DOCS, "Documentation").build(app)?;
    let report_item = MenuItemBuilder::with_id(ids::HELP_REPORT, "Report Issue").build(app)?;
    let homepage_item =
        MenuItemBuilder::with_id(ids::HELP_HOMEPAGE, "Visit digi-setu.com").build(app)?;
    let privacy_item =
        MenuItemBuilder::with_id(ids::HELP_PRIVACY, "Privacy Policy").build(app)?;
    let terms_item =
        MenuItemBuilder::with_id(ids::HELP_TERMS, "Terms of Service").build(app)?;
    let licenses_item =
        MenuItemBuilder::with_id(ids::HELP_LICENSES, "Open Source Licenses").build(app)?;

    let help_submenu = SubmenuBuilder::new(app, "Help")
        .item(&docs_item)
        .item(&report_item)
        .separator()
        .item(&homepage_item)
        .separator()
        .item(&privacy_item)
        .item(&terms_item)
        .item(&licenses_item)
        .build()?;

    // ── Final assembly ───────────────────────────────────────────────
    let menu = MenuBuilder::new(app)
        .items(&[
            &app_submenu,
            &file_submenu,
            &edit_submenu,
            &view_submenu,
            &window_submenu,
            &help_submenu,
        ])
        .build()?;

    Ok(menu)
}

/// Spawn a new top-level window pointing at the same SPA. The label
/// must be unique (Tauri rejects duplicates), so we tack a counter on.
///
/// The new window inherits sidecar / backend port from `AppState`, so
/// the SPA's bootstrap (which calls `get_backend_port`) just works.
pub fn open_new_window<R: Runtime>(app: &AppHandle<R>) -> tauri::Result<()> {
    // Pick the first label that's not in use. Cheap because we only
    // ever have a handful of windows open.
    let mut idx: u32 = 2;
    let label = loop {
        let candidate = format!("window-{idx}");
        if app.get_webview_window(&candidate).is_none() {
            break candidate;
        }
        idx += 1;
        if idx > 64 {
            // Defensive — the user shouldn't realistically open 64
            // windows, but bail rather than spin forever if something
            // goes sideways.
            return Err(tauri::Error::WebviewLabelAlreadyExists(format!(
                "window-{idx}"
            )));
        }
    };

    // Clone the main window's URL so dev (Vite on 5173) and prod
    // (tauri://localhost) both work without a config branch.
    let url = if let Some(main) = app.get_webview_window("main") {
        // `WebviewWindow::url()` returns the live URL, including the
        // tauri:// scheme in prod; we just hand it back to Tauri.
        match main.url() {
            Ok(u) => WebviewUrl::External(u),
            Err(_) => WebviewUrl::App("index.html".into()),
        }
    } else {
        WebviewUrl::App("index.html".into())
    };

    WebviewWindowBuilder::new(app, &label, url)
        .title("Digi Setu")
        .inner_size(1400.0, 900.0)
        .min_inner_size(900.0, 600.0)
        .resizable(true)
        .center()
        .build()?;

    Ok(())
}
