//! Deep-link bridge.
//!
//! The desktop shell registers the URL schemes `pi-typst-test://` and
//! `digi-setu://` with the OS at install time (Mac via Info.plist,
//! Windows via registry, Linux via .desktop file — the bundler does
//! all three). When the user finishes a Clerk login flow in their
//! default browser, Clerk redirects to:
//!
//!     pi-typst-test://auth/callback?token=<jwt>&state=<csrf>
//!
//! and Stripe Checkout success redirects to:
//!
//!     pi-typst-test://billing/return?session=<id>&billing=success
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

    // Register `pi-typst-test://` + `digi-setu://` at runtime on the
    // platforms that need it (Linux, dev-mode Win). The bundle
    // configuration in tauri.conf.json handles installed Mac + Win.
    #[cfg(any(target_os = "linux", all(debug_assertions, target_os = "windows")))]
    {
        if let Err(err) = app.deep_link().register_all() {
            log::warn!("deep_link register_all failed (non-fatal in dev): {err}");
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
