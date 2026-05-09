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
        "/api": apiTarget,
        "/ws": { target: wsTarget, ws: true },
      },
    },
  };
});
