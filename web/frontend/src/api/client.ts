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
 * Register the function the API client should call to get a fresh
 * session token (or null if not signed in). Wired in main.ts after
 * the Clerk plugin is installed.
 */
export function setTokenResolver(resolver: TokenResolver | null): void {
  _tokenResolver = resolver;
}

async function _authHeader(): Promise<Record<string, string>> {
  if (!_tokenResolver) return {};
  try {
    const token = await _tokenResolver();
    return token ? { Authorization: `Bearer ${token}` } : {};
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
  const merged: RequestInit = {
    ...init,
    headers: {
      ...auth,
      ...(init?.headers || {}),
    },
  };
  const res = await fetch(path, merged);
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
 * Fetch `path` with auth headers and return a `blob:` URL pointing at the
 * response body. Used by `<iframe>` / `<audio>` / `<video>` previews and
 * for download triggers — none of which can carry an `Authorization`
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
 * sql.js) that need to parse the file directly rather than via a
 * blob URL.
 */
export async function authArrayBuffer(path: string): Promise<ArrayBuffer> {
  const res = await _request(path);
  return await res.arrayBuffer();
}

/**
 * Trigger a browser download of `path` with auth, suggesting `filename`
 * to the Save-As dialog. The blob URL is revoked immediately after the
 * synthetic click so we don't leak memory across many downloads.
 */
export async function downloadAuthed(path: string, filename: string): Promise<void> {
  const url = await authBlobUrl(path);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  // The anchor must be in the DOM for some browsers (Firefox); style it
  // out of the layout so it never flashes.
  a.style.display = "none";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  // Revoke on the next macrotask so the click handler has finished
  // dispatching the download. setTimeout 0 is the standard idiom for
  // "after current task settles" without bringing in queueMicrotask
  // ordering surprises.
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
  // The web edition is always same-origin: SPA + WebSocket land on the
  // same Caddy/Vite host. (The desktop hard-fork carries its own
  // version of this helper that resolves the sidecar's randomised
  // port; nothing of that here.)
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  let url = `${proto}//${window.location.host}${path}`;
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
