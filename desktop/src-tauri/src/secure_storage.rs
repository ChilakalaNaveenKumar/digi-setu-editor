//! Persistent SSO via OS-native secret store, with a file fallback.
//!
//! Cursor-style "sign in once, stay signed in for weeks" UX. The
//! Clerk session id is stored on every successful desktop-exchange
//! and read back on every app launch; the sidecar mints fresh JWTs
//! from it on demand, so the user never has to sign in again unless
//! they explicitly sign out or revoke the session from another device.
//!
//! Storage layout (we write to BOTH and read from EITHER):
//!   1. ~/.digi-setu/.session_id     (mode 0600, primary)
//!   2. OS keychain                  (best-effort backup)
//!
//! Why two stores instead of just the keychain:
//!
//!   macOS Keychain Services binds each item's ACL to the requesting
//!   app's *Designated Requirement* (a hash of the codesign identity).
//!   Every ad-hoc `codesign --force --sign -` produces a NEW
//!   designated requirement, so a v0.1.0 build CANNOT read a session
//!   written by the v0.1.0+1 build of the same app — macOS treats
//!   them as different apps. The user-visible symptom is "signed in
//!   yesterday, signed-out screen today after I reinstalled the
//!   nightly DMG". A file in the user's data dir doesn't have that
//!   problem.
//!
//!   We still write to the keychain in parallel because:
//!     - On Windows the Credential Vault is DPAPI-encrypted, which
//!       is meaningfully better than mode-0600.
//!     - On Linux the keychain (Secret Service) requires the user's
//!       login session, but works the same way.
//!     - When we eventually ship a stable Apple Developer ID +
//!       notarization, the macOS ACL will stop biting us and the
//!       keychain becomes the better source of truth.
//!
//! Backing stores by platform (keychain side):
//!   - macOS    →  Keychain Services
//!   - Windows  →  Credential Vault
//!   - Linux    →  Secret Service (libsecret / gnome-keyring / KWallet)
//!
//! What we DO store: the opaque Clerk session id (`sess_…`).
//!
//! What we DELIBERATELY do NOT store:
//!   - JWTs (short-lived, regenerated server-side on demand)
//!   - Refresh tokens (Clerk doesn't expose them)
//!   - User passwords, BYOK API keys (~/.digi-setu/.env per the
//!     BYOK design)
//!
//! On read failure we return None and the SPA falls through to the
//! Welcome screen. We never panic or refuse to launch on a storage
//! failure.

use std::fs;
use std::io::Write;
use std::path::PathBuf;

use keyring::Entry;

/// Service name registered with the OS keyring. Stable across versions
/// so an upgrade doesn't strand the user. Don't change without a
/// migration.
const SERVICE: &str = "com.digi-setu.desktop";

/// Account name under which the session id is stored. There's only one
/// account per OS user — we don't support concurrent multi-account
/// sign-in inside the same desktop install.
const ACCOUNT: &str = "session-id";

/// File-fallback location, relative to `$DIGI_SETU_HOME` (set by Rust
/// commands.rs::app_data_dir at startup) or `~/.digi-setu`. Hidden
/// (leading dot) so a casual `ls ~/.digi-setu` doesn't tempt the
/// user to delete it; the file isn't sensitive on its own (a stolen
/// session id without the matching Clerk SDK can't do much) but it
/// IS the keys-to-the-kingdom for that user's Digi Setu account, so
/// we keep it inconspicuous + mode 0600.
const SESSION_FILE: &str = ".session_id";

fn data_root() -> Option<PathBuf> {
    if let Ok(custom) = std::env::var("DIGI_SETU_HOME") {
        let p = PathBuf::from(custom);
        if !p.as_os_str().is_empty() {
            return Some(p);
        }
    }
    dirs::home_dir().map(|h| h.join(".digi-setu"))
}

fn session_file_path() -> Option<PathBuf> {
    data_root().map(|root| root.join(SESSION_FILE))
}

fn write_file_session(value: &str) -> std::io::Result<()> {
    let path = session_file_path().ok_or_else(|| {
        std::io::Error::new(
            std::io::ErrorKind::NotFound,
            "could not resolve home dir for session-id fallback",
        )
    })?;
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    // Atomic-ish: write to a sibling .new then rename so a crash
    // mid-write can't leave us with a half-truncated session id.
    let tmp = path.with_extension("session_id.new");
    {
        #[cfg(unix)]
        let opts = {
            use std::os::unix::fs::OpenOptionsExt;
            let mut o = fs::OpenOptions::new();
            o.write(true).create(true).truncate(true).mode(0o600);
            o
        };
        #[cfg(not(unix))]
        let opts = {
            let mut o = fs::OpenOptions::new();
            o.write(true).create(true).truncate(true);
            o
        };
        let mut f = opts.open(&tmp)?;
        f.write_all(value.as_bytes())?;
        f.sync_all()?;
    }
    fs::rename(&tmp, &path)
}

fn read_file_session() -> Option<String> {
    let path = session_file_path()?;
    let raw = fs::read_to_string(&path).ok()?;
    let trimmed = raw.trim();
    if trimmed.is_empty() {
        None
    } else {
        Some(trimmed.to_string())
    }
}

fn delete_file_session() -> std::io::Result<()> {
    let path = match session_file_path() {
        Some(p) => p,
        None => return Ok(()),
    };
    match fs::remove_file(&path) {
        Ok(()) => Ok(()),
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(()),
        Err(e) => Err(e),
    }
}

/// Persist the Clerk session id. Overwrites any prior value.
///
/// Writes to BOTH the file fallback and the OS keychain. We treat
/// the file write as authoritative — if it fails we surface that
/// error (because then we have no persistence at all). A keychain
/// failure is logged but doesn't fail the call: the file alone is
/// enough for sign-in to survive across launches.
#[tauri::command]
pub fn secure_store_session(session_id: String) -> Result<(), String> {
    let trimmed = session_id.trim();
    if trimmed.is_empty() {
        return Err("session_id cannot be empty".to_string());
    }
    write_file_session(trimmed).map_err(|e| {
        format!("session-id file write failed: {e}")
    })?;
    if let Ok(entry) = Entry::new(SERVICE, ACCOUNT) {
        if let Err(e) = entry.set_password(trimmed) {
            log::warn!("[secure_storage] keychain write failed (file ok): {e}");
        }
    }
    Ok(())
}

/// Read the cached Clerk session id. Tries the file fallback first
/// (no ACL prompts, immune to ad-hoc-signature churn), then the OS
/// keychain. Returns None if neither yielded a value.
///
/// As a self-healing side-effect: when the file is missing but the
/// keychain has a value (legacy installs that only ever wrote the
/// keychain), we copy the value into the file so the NEXT launch
/// hits the fast path and doesn't need a keychain prompt.
#[tauri::command]
pub fn secure_load_session() -> Option<String> {
    if let Some(v) = read_file_session() {
        return Some(v);
    }
    let entry = Entry::new(SERVICE, ACCOUNT).ok()?;
    let from_keychain = entry.get_password().ok()?;
    if let Err(e) = write_file_session(&from_keychain) {
        log::warn!(
            "[secure_storage] keychain hit but file mirror failed: {e}; \
             will retry next launch"
        );
    }
    Some(from_keychain)
}

/// Delete the cached session id from BOTH stores. Called on explicit
/// sign-out and on refresh failure. Errors are non-fatal — if either
/// store hiccups we still try the other so a stale session can't
/// silently haunt the user.
#[tauri::command]
pub fn secure_delete_session() -> Result<(), String> {
    let mut errs: Vec<String> = Vec::new();
    if let Err(e) = delete_file_session() {
        errs.push(format!("file: {e}"));
    }
    if let Ok(entry) = Entry::new(SERVICE, ACCOUNT) {
        match entry.delete_credential() {
            Ok(()) | Err(keyring::Error::NoEntry) => {}
            Err(e) => errs.push(format!("keychain: {e}")),
        }
    }
    if errs.is_empty() {
        Ok(())
    } else {
        Err(errs.join("; "))
    }
}
