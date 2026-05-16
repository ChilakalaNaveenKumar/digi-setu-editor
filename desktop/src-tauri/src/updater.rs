//! Auto-updater IPC commands.
//!
//! Exposes a tiny surface to the SPA so the chat-settings popover and
//! `Help ▸ Check for Updates…` menu item can drive the upgrade flow
//! end-to-end without any DMG re-download:
//!
//!   1. ``check_for_update``       — hits the updater manifest, returns
//!                                   the new version + body if there's
//!                                   one available, or ``None`` if we're
//!                                   already on the latest. Network /
//!                                   signature errors come back as Err.
//!
//!   2. ``apply_update_and_restart`` — downloads the bundle (with progress
//!                                   events streamed to the renderer),
//!                                   verifies its minisign signature
//!                                   against the public key embedded at
//!                                   build time via ``tauri.conf.json``,
//!                                   writes the new bundle in-place, then
//!                                   calls ``app.restart()``. The
//!                                   ``WindowEvent::CloseRequested``
//!                                   path in lib.rs runs on shutdown,
//!                                   which means the sidecar is SIGTERM'd
//!                                   cleanly before the new binary takes
//!                                   over.
//!
//! Why two commands instead of one "do everything": the SPA's
//! Maintenance section shows a button labelled "Update available"
//! ONLY when there's something to update. If we made this a single
//! call, the SPA would have to either always show the button (loud)
//! or hit the network on every popover open (wasteful). Splitting
//! lets the SPA cache the check result for ~24 h and only download
//! on explicit consent.
//!
//! Signing: the updater REFUSES to install an unsigned bundle. The
//! public key lives in ``tauri.conf.json#plugins.updater.pubkey`` and
//! is baked into the binary at compile time. The matching private
//! key is held by CI (env var ``TAURI_SIGNING_PRIVATE_KEY``) and is
//! NEVER stored in the repo. See ``deploy/scripts/release-desktop.sh``
//! for the full publish pipeline.
//!
//! Failure modes the SPA must handle:
//!   * ``Err("offline")``                — manifest GET timed out.
//!   * ``Err("signature mismatch")``     — bundle was tampered with;
//!                                         user should reinstall manually.
//!   * ``Err("update not configured")``  — no endpoints in the conf
//!                                         (dev / CI builds without
//!                                         a release manifest yet).

use serde::Serialize;
use tauri::AppHandle;
use tauri_plugin_updater::UpdaterExt;

/// Slim, JSON-friendly mirror of ``tauri_plugin_updater::Update`` —
/// the SPA only cares about the user-visible bits (version + release
/// notes), not the manifest URL or the raw signature.
#[derive(Debug, Serialize)]
pub struct UpdateInfo {
    /// Semver of the new release (e.g. ``"0.2.1"``).
    pub version: String,
    /// Release notes / changelog body. Markdown is fine — the SPA
    /// renders it via the same renderer used for chat replies.
    pub body: Option<String>,
    /// ISO-8601 publish date if the manifest provides one. Optional
    /// because Tauri's plugin doesn't always populate it.
    pub date: Option<String>,
}

/// Probe the configured updater endpoint(s) for a newer release.
/// Returns ``Ok(None)`` when we're already on the latest, ``Ok(Some)``
/// when an upgrade is available, ``Err`` for any network / config /
/// signature problem the SPA can surface to the user.
///
/// Caching: the plugin itself does NOT cache between calls. We rely
/// on the SPA to throttle (manual click is rare; auto-checks fire on
/// boot + every 24 h while the app stays open).
#[tauri::command]
pub async fn check_for_update(app: AppHandle) -> Result<Option<UpdateInfo>, String> {
    // The updater builder reads the endpoints + pubkey from
    // tauri.conf.json. If that block is missing (dev/CI builds before
    // the manifest is provisioned) ``builder()`` returns Err — we
    // surface that as a clean "not configured" rather than a panic
    // the SPA can't decode.
    let updater = app
        .updater_builder()
        .build()
        .map_err(|err| format!("update not configured: {err}"))?;

    match updater.check().await {
        Ok(Some(update)) => Ok(Some(UpdateInfo {
            version: update.version.clone(),
            body: update.body.clone(),
            date: update.date.map(|d| d.to_string()),
        })),
        Ok(None) => Ok(None),
        Err(err) => {
            log::warn!("updater check failed: {err}");
            Err(err.to_string())
        }
    }
}

/// Download + verify + install the latest bundle, then restart the
/// app. Streams ``updater://download-progress`` events the SPA can
/// pipe into a progress bar.
///
/// On success this never returns — ``app.restart()`` reboots the
/// process before control gets back to the SPA. The ``Result`` is
/// only meaningful on failure (download error, signature mismatch,
/// install perms denied).
///
/// We DON'T need to manually SIGTERM the sidecar before restarting:
/// Tauri runs the registered ``WindowEvent::CloseRequested`` handler
/// on every window before exiting, and that handler in lib.rs is
/// the same one that terminates the sidecar on user-initiated quit.
#[tauri::command]
pub async fn apply_update_and_restart(app: AppHandle) -> Result<(), String> {
    let updater = app
        .updater_builder()
        .build()
        .map_err(|err| format!("update not configured: {err}"))?;

    let Some(update) = updater
        .check()
        .await
        .map_err(|err| err.to_string())?
    else {
        return Err("already on latest version".to_string());
    };

    log::info!("Applying update {}", update.version);

    // Stream progress so the SPA's UI can show "12 of 47 MB downloaded".
    // The closures are ``Fn`` and Send + 'static — Tauri's runtime
    // calls them from a worker thread.
    let app_for_event = app.clone();
    update
        .download_and_install(
            move |chunk_len, total_len| {
                use tauri::Emitter;
                let payload = serde_json::json!({
                    "chunkBytes": chunk_len,
                    "totalBytes": total_len,
                });
                let _ = app_for_event.emit("updater://download-progress", payload);
            },
            || {
                // The plugin calls this immediately before swapping the
                // bundle on disk. Logging it makes "the app froze for
                // 5 seconds during install" debuggable from a user log.
                log::info!("updater: download finished, installing");
            },
        )
        .await
        .map_err(|err| {
            log::error!("updater install failed: {err}");
            err.to_string()
        })?;

    log::info!("updater: install complete, restarting");
    // ``Manager::restart`` is the same call the OS would do on a fresh
    // launch — it runs through Tauri's normal close-then-spawn path,
    // which means our window-close handler tears the sidecar down
    // cleanly before the new binary boots its own. No manual SIGTERM
    // dance required.
    app.restart();
}
