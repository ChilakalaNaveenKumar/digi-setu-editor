import { defineConfig, loadEnv } from "vite";
import vue from "@vitejs/plugin-vue";

/**
 * `VITE_API_TARGET` lets us point the dev proxy at a backend on a
 * non-default port — handy when running the desktop and web stacks
 * simultaneously for side-by-side QA.
 *   VITE_API_TARGET=http://127.0.0.1:8002 npm run dev -- --port 5175
 *
 * `VITE_DEV_PORT` overrides the front-end listen port without editing
 * this file. Default 5173 keeps standard `npm run dev` behaviour.
 */
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const apiTarget = env.VITE_API_TARGET || "http://127.0.0.1:8000";
  const wsTarget = apiTarget.replace(/^http/, "ws");
  const port = Number(env.VITE_DEV_PORT) || 5173;
  return {
    plugins: [vue()],
    server: {
      port,
      strictPort: true,
      proxy: {
        // SSE-friendly proxy config. Defaults buffer responses and
        // close the upstream socket after ~2 min — both kill our
        // long-lived `/api/sessions/:sid/stream` event source. Bump
        // the timeout to effectively-infinite, set the buffer to a
        // tiny size so each SSE chunk flushes immediately, and make
        // sure no compression middleware is inserted.
        "/api": {
          target: apiTarget,
          changeOrigin: false,
          ws: false,
          // 24h timeout — well beyond any plausible browser tab life.
          // Without this http-proxy default-closes after 120s and the
          // SSE consumer receives no more events.
          timeout: 24 * 60 * 60 * 1000,
          proxyTimeout: 24 * 60 * 60 * 1000,
          // Some proxy adapters set a `Cache-Control` that makes
          // intermediaries buffer; explicitly mirror what the backend
          // sets so behaviour matches prod (Caddy direct to uvicorn).
          configure: (proxy) => {
            proxy.on("proxyRes", (proxyRes) => {
              if (
                String(proxyRes.headers["content-type"] || "").includes(
                  "text/event-stream",
                )
              ) {
                proxyRes.headers["cache-control"] = "no-cache, no-transform";
                proxyRes.headers["x-accel-buffering"] = "no";
              }
            });
          },
        },
        "/ws": { target: wsTarget, ws: true },
      },
    },
  };
});
