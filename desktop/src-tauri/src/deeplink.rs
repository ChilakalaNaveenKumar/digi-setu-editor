//! Deep-link bridge.
//!
//! The desktop shell registers the URL scheme `digi-setu://` with the
//! OS at install time (Mac via Info.plist, Windows via registry, Linux
//! via .desktop file — the bundler does all three). When the user
//! finishes a Clerk login flow in their default browser, Clerk
//! redirects to:
//!
//!     digi-setu://auth/callback?token=<jwt>&state=<csrf>
//!
//! and Stripe Checkout success redirects to:
//!
//!     digi-setu://billing/return?session=<id>&billing=success
//!
//! The OS hands those URLs to the running desktop app (or launches
//! one if none is running). We forward them into the webview as a
//! `deep-link` event the SPA's auth/billing stores listen for.
//!
//! This module is tiny by design: the Tauri plugin does the heavy
//! lifting (URL scheme registration, single-instance argv parsing).
//! All we do is plug it into our event bus.

use serde::Serialize;
use tauri::{App, Emitter};
use tauri_plugin_deep_link::DeepLinkExt;

#[derive(Clone, Serialize)]
struct DeepLinkPayload {
    /// The full URL the OS handed us. Frontend parses query params
    /// because the routing rules ("if path == '/auth/callback' do X")
    /// are easier to express in TypeScript than Rust.
    url: String,
}

pub fn register(app: &mut App) -> Result<(), Box<dyn std::error::Error>> {
    let handle = app.handle().clone();

    // Register `digi-setu://` at runtime where the OS would otherwise
    // not see a registered handler:
    //   - Linux: always (installed .desktop files require an explicit
    //     install step which dev mode skips).
    //   - debug builds on Windows: registry registration via the
    //     plugin's runtime helper.
    //   - debug builds on macOS: the plugin's runtime helper says
    //     "unsupported platform" because LaunchServices needs a real
    //     .app bundle. We fix that with our own dev-time registrar
    //     (see `register_macos_dev_bundle` below).
    // In release builds for macOS / Windows the bundle config in
    // tauri.conf.json handles registration via Info.plist / installer
    // — nothing to do at runtime.
    #[cfg(any(target_os = "linux", all(debug_assertions, target_os = "windows")))]
    {
        if let Err(err) = app.deep_link().register_all() {
            log::warn!("deep_link register_all failed (non-fatal in dev): {err}");
        } else {
            log::info!("deep_link register_all: digi-setu:// registered with OS");
        }
    }

    #[cfg(all(debug_assertions, target_os = "macos"))]
    {
        if let Err(err) = register_macos_dev_bundle() {
            log::warn!(
                "macOS dev deep-link registration failed (non-fatal — \
                 sign-in deep links won't return to a dev build, but \
                 release builds will register correctly via Info.plist): {err}"
            );
        }
    }

    // Stream every incoming deep-link URL into the webview. The SPA
    // attaches a listener at boot via `@tauri-apps/api/event`'s
    // `listen('deep-link', …)` and routes the URL to the right store.
    app.deep_link().on_open_url(move |event| {
        for url in event.urls() {
            log::info!("Deep-link received: {url}");
            let _ = handle.emit("deep-link", DeepLinkPayload { url: url.to_string() });
        }
    });

    Ok(())
}

/// macOS dev-only: build a tiny .app wrapper around the dev binary
/// and register it with LaunchServices so `digi-setu://` URLs route
/// back to the running Tauri dev instance.
///
/// `tauri dev` produces a bare debug binary at `target/debug/digi-setu-desktop`
/// — there is no `.app` directory, no `Info.plist`, and macOS
/// LaunchServices has no idea any process on the machine handles
/// `digi-setu://`. The end-user-visible symptom is a sign-in browser
/// tab stuck forever on "Returning you to Digi Setu…" because the
/// `window.location.href = "digi-setu://..."` redirect silently
/// fails (no registered handler).
///
/// This function:
///   1. Creates `<dev_binary_dir>/Digi Setu Dev.app/Contents/{MacOS,Info.plist}`
///   2. Symlinks the dev binary into `Contents/MacOS/`
///   3. Writes an `Info.plist` that declares `digi-setu` as a handled
///      `CFBundleURLScheme`
///   4. Calls `lsregister -f` so LaunchServices indexes the bundle
///
/// Idempotent: re-running just refreshes the symlink + plist, and
/// lsregister tolerates re-registering the same bundle. We do this
/// every dev launch so a fresh `cargo clean` is automatically
/// recovered without operator intervention.
///
/// The bundle ID intentionally differs from the prod identifier
/// (`com.digisetu.desktop` → `com.digisetu.desktop.dev`) so a dev
/// build never accidentally clobbers a user's installed prod
/// registration.
#[cfg(all(debug_assertions, target_os = "macos"))]
fn register_macos_dev_bundle() -> Result<(), String> {
    use std::fs;
    use std::os::unix::fs::symlink;
    use std::path::PathBuf;
    use std::process::Command;

    let dev_bin = std::env::current_exe()
        .map_err(|e| format!("current_exe: {e}"))?;
    let dev_bin_name = dev_bin
        .file_name()
        .ok_or_else(|| "dev binary has no filename".to_string())?
        .to_owned();
    let dev_bin_dir = dev_bin
        .parent()
        .ok_or_else(|| "dev binary has no parent dir".to_string())?
        .to_path_buf();

    let app_dir = dev_bin_dir.join("Digi Setu Dev.app");
    let contents_dir = app_dir.join("Contents");
    let macos_dir: PathBuf = contents_dir.join("MacOS");
    let plist_path = contents_dir.join("Info.plist");

    fs::create_dir_all(&macos_dir).map_err(|e| format!("mkdir {macos_dir:?}: {e}"))?;

    // Refresh the symlink. We can't trust `exists()` to disambiguate
    // a stale symlink from a real file, so just remove and recreate.
    let symlink_path = macos_dir.join(&dev_bin_name);
    let _ = fs::remove_file(&symlink_path);
    symlink(&dev_bin, &symlink_path)
        .map_err(|e| format!("symlink {symlink_path:?} -> {dev_bin:?}: {e}"))?;

    let plist = format!(
        r#"<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key>
    <string>en</string>
    <key>CFBundleExecutable</key>
    <string>{exec}</string>
    <key>CFBundleIdentifier</key>
    <string>com.digisetu.desktop.dev</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>Digi Setu Dev</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>0.0.0-dev</string>
    <key>CFBundleVersion</key>
    <string>0</string>
    <key>LSMinimumSystemVersion</key>
    <string>11.0</string>
    <key>CFBundleURLTypes</key>
    <array>
        <dict>
            <key>CFBundleURLName</key>
            <string>com.digisetu.desktop.dev</string>
            <key>CFBundleURLSchemes</key>
            <array>
                <string>digi-setu</string>
            </array>
        </dict>
    </array>
</dict>
</plist>
"#,
        exec = dev_bin_name.to_string_lossy(),
    );

    fs::write(&plist_path, plist)
        .map_err(|e| format!("write Info.plist {plist_path:?}: {e}"))?;

    let lsregister = "/System/Library/Frameworks/CoreServices.framework/\
                      Versions/A/Frameworks/LaunchServices.framework/\
                      Versions/A/Support/lsregister";
    let output = Command::new(lsregister)
        .args(["-f", "-R"])
        .arg(&app_dir)
        .output()
        .map_err(|e| format!("spawn lsregister: {e}"))?;
    if !output.status.success() {
        return Err(format!(
            "lsregister exited {} — stderr: {}",
            output.status,
            String::from_utf8_lossy(&output.stderr).trim(),
        ));
    }

    log::info!(
        "macOS dev deep-link registered: {} (digi-setu:// → {})",
        app_dir.display(),
        dev_bin.display(),
    );
    Ok(())
}
