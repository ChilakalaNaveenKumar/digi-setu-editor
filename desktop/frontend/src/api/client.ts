/**
 * Thin REST client used by every api/* module. No state, no Pinia.
 *
 * Auth: a token resolver is registered once at app boot (`main.ts`). On
 * every request we ask it for a fresh Clerk JWT and stamp it on the
 * `Authorization` header. The resolver is intentionally *not* a Pinia
 * store — Pinia stores can't be used inside non-component code (like
 * this module) without dragging in `getActivePinia()` ceremony, and
 * we want callers to be able to use `apiJson()` from anywhere.
 *
 * Routes return `{ detail: "..." }` on error (FastAPI default); we surface
 * that text in `ApiError.message` so the UI can show meaningful messages
 * without each callsite having to re-parse the response.
 */

export class ApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

type TokenResolver = () => Promise<string | null>;

let _tokenResolver: TokenResolver | null = null;

/**
 * Optional base URL prefix for every request. Web mode leaves this
 * empty (Caddy reverse-proxies /api/* same-origin). Desktop mode
 * sets it to `http://127.0.0.1:<sidecar-port>` because the Tauri
 * webview navigates to a different origin than the FastAPI sidecar
 * — without this prefix every fetch would 404.
 *
 * Only intended for absolute "/api/..." paths and any other path
 * starting with "/". Already-absolute URLs (https://...) pass
 * through unchanged. Wired in main.ts after we discover the sidecar
 * port from `getBackendPort()`.
 */
let _apiBase = "";

export function setApiBase(base: string): void {
  _apiBase = base.replace(/\/+$/, "");
}

export function getApiBase(): string {
  return _apiBase;
}

function _absolutize(path: string): string {
  if (!_apiBase) return path;
  if (/^[a-z][a-z0-9+\-.]*:\/\//i.test(path)) return path;
  if (!path.startsWith("/")) return path;
  return _apiBase + path;
}

/**
 * Register the function the API client should call to get a fresh
 * session token (or null if not signed in). Wired in main.ts after
 * the Clerk plugin is installed.
 */
export function setTokenResolver(resolver: TokenResolver | null): void {
  _tokenResolver = resolver;
}

/**
 * Strip characters HTTP headers cannot legally carry (CR, LF, NUL,
 * and any other control < 0x20 except TAB). Without this, a stray
 * newline in a Clerk JWT or a session id (e.g. one read from a file
 * with a trailing `\n`) produces WebKit's confusing
 * "TypeError: The string did not match the expected pattern" out of
 * `fetch()` — and the user sees an unhelpful toast that points
 * nowhere near the actual cause.
 */
function _sanitizeHeaderValue(v: string): string {
  return v.replace(/[\u0000-\u0008\u000A-\u001F\u007F]/g, "").trim();
}

function _sanitizeHeaders(
  raw: Record<string, string>,
): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [k, v] of Object.entries(raw)) {
    if (typeof v !== "string") continue;
    const clean = _sanitizeHeaderValue(v);
    if (clean) out[k] = clean;
  }
  return out;
}

async function _authHeader(): Promise<Record<string, string>> {
  if (!_tokenResolver) return {};
  try {
    const token = await _tokenResolver();
    if (!token) return {};
    const clean = _sanitizeHeaderValue(token);
    return clean ? { Authorization: `Bearer ${clean}` } : {};
  } catch (exc) {
    console.warn("[api] token resolver threw", exc);
    return {};
  }
}

async function _detail(res: Response): Promise<string> {
  try {
    const data = (await res.json()) as { detail?: unknown };
    if (typeof data.detail === "string" && data.detail) return data.detail;
  } catch {
    /* not JSON — fall through */
  }
  return `${res.status} ${res.statusText || "request failed"}`;
}

async function _request(path: string, init?: RequestInit): Promise<Response> {
  const auth = await _authHeader();
  // Coerce caller-supplied headers (which may be a Headers / array / object
  // literal) into a plain record before we sanitize. The fetch spec accepts
  // all three forms but our sanitizer only handles a record.
  const callerHeaders: Record<string, string> = {};
  if (init?.headers) {
    if (init.headers instanceof Headers) {
      init.headers.forEach((v, k) => { callerHeaders[k] = v; });
    } else if (Array.isArray(init.headers)) {
      for (const [k, v] of init.headers) callerHeaders[k] = v;
    } else {
      Object.assign(callerHeaders, init.headers as Record<string, string>);
    }
  }

  const merged: RequestInit = {
    ...init,
    headers: _sanitizeHeaders({ ...auth, ...callerHeaders }),
  };

  const url = _absolutize(path);
  let res: Response;
  try {
    res = await fetch(url, merged);
  } catch (exc) {
    // Surface enough context to actually diagnose the failure. The two
    // common reasons fetch() throws (vs. resolves with !ok):
    //   1. Network unreachable — sidecar not yet bound, wifi down, etc.
    //   2. Invalid request — malformed header or URL, which historically
    //      produced "The string did not match the expected pattern"
    //      from WebKit and gave the user a useless toast. Sanitisation
    //      above covers (2) for the headers we control; if it still
    //      fires, the URL itself is the culprit and we want to see it.
    const cause = exc instanceof Error ? exc.message : String(exc);
    throw new ApiError(0, `cannot reach ${url} — ${cause}`);
  }
  if (!res.ok) throw new ApiError(res.status, await _detail(res));
  return res;
}

export async function apiJson<T>(path: string, init?: RequestInit): Promise<T> {
  return (await _request(path, init)).json() as Promise<T>;
}

export async function apiVoid(path: string, init?: RequestInit): Promise<void> {
  await _request(path, init);
}

export function apiPost<T>(path: string, body?: unknown): Promise<T> {
  return apiJson<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
}

export function apiPatch<T>(path: string, body: unknown): Promise<T> {
  return apiJson<T>(path, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function apiDelete<T>(path: string): Promise<T> {
  return apiJson<T>(path, { method: "DELETE" });
}

/**
 * Multipart POST. Used by /api/.../attachments where we ship raw File
 * objects rather than JSON. Callers build the FormData themselves.
 *
 * NOTE: do NOT set `Content-Type` on the headers — the browser must set
 * it itself with the correct multipart boundary string. Setting it
 * manually breaks the request.
 */
export async function apiPostForm<T>(path: string, form: FormData): Promise<T> {
  return apiJson<T>(path, {
    method: "POST",
    body: form,
  });
}

/**
 * Fetch `path` with auth headers and return a `blob:` URL pointing at
 * the response body. Used by `<iframe>` / `<audio>` / `<video>` previews
 * and for download triggers — none of which can carry an `Authorization`
 * header on their own.
 *
 * The caller is responsible for `URL.revokeObjectURL()` when done.
 */
export async function authBlobUrl(path: string): Promise<string> {
  const res = await _request(path);
  const blob = await res.blob();
  return URL.createObjectURL(blob);
}

/**
 * Fetch `path` with auth headers and return the raw bytes as an
 * ArrayBuffer. Used by the in-browser document viewers (xlsx, docx,
 * sql.js) that parse the file directly rather than via a blob URL.
 */
export async function authArrayBuffer(path: string): Promise<ArrayBuffer> {
  const res = await _request(path);
  return await res.arrayBuffer();
}

/**
 * Trigger a browser download of `path` with auth, suggesting `filename`
 * to the Save-As dialog. Revokes the blob URL after dispatch so we don't
 * leak memory across many downloads.
 */
export async function downloadAuthed(path: string, filename: string): Promise<void> {
  const url = await authBlobUrl(path);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.style.display = "none";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 0);
}

/**
 * Build a WebSocket URL with the Clerk token in the query string.
 *
 * Browsers don't allow custom headers on the WebSocket constructor, so
 * `Authorization: Bearer` isn't an option. Cookies *are* sent (Clerk
 * stores `__session` on its own domain, which doesn't help us if the
 * SPA + API live on the same origin we set the cookie ourselves).
 * The reliable cross-environment path is "stick the token in `?token=`
 * and let the backend pull it out of the upgrade request URL".
 *
 * The backend's auth.py reads the token from BOTH the cookie *and* a
 * `?clerk_token=` query param so the same handshake works in dev
 * (custom origin) and prod (same-origin Caddy).
 */
export async function buildWebSocketUrl(path: string): Promise<string> {
  // In desktop mode the SPA is served from `tauri://localhost` (or a
  // dev-mode Vite origin) but the WebSocket has to land on the
  // FastAPI sidecar's local port. We honour `_apiBase` here so the
  // computed `ws://` URL points at the right host:port.
  let url: string;
  if (_apiBase) {
    const base = new URL(_apiBase);
    const proto = base.protocol === "https:" ? "wss:" : "ws:";
    url = `${proto}//${base.host}${path}`;
  } else {
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    url = `${proto}//${window.location.host}${path}`;
  }
  if (_tokenResolver) {
    try {
      const token = await _tokenResolver();
      if (token) {
        const sep = url.includes("?") ? "&" : "?";
        url += `${sep}clerk_token=${encodeURIComponent(token)}`;
      }
    } catch (exc) {
      console.warn("[api] ws token resolver threw", exc);
    }
  }
  return url;
}
