import type { Config } from "tailwindcss";

/**
 * Tailwind tokens map 1:1 to CSS variables in src/app.css.
 *
 * To add a new color/state token:
 *   1. Define `--my-thing` in `app.css` (under `.dark` for shared, under
 *      `.theme-<name>` for palette-specific).
 *   2. Register it here as `myThing: "var(--my-thing)"`.
 *
 * Components ALWAYS use the Tailwind class (`bg-card`, `text-rail-success`,
 * etc.) — they NEVER hardcode hex. That keeps palette swaps to a single
 * line in `main.ts`.
 */
export default {
  content: ["./index.html", "./src/**/*.{vue,ts}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        card: {
          DEFAULT: "var(--card)",
          foreground: "var(--card-foreground)",
        },
        popover: {
          DEFAULT: "var(--popover)",
          foreground: "var(--popover-foreground)",
        },
        primary: {
          DEFAULT: "var(--primary)",
          foreground: "var(--primary-foreground)",
        },
        secondary: {
          DEFAULT: "var(--secondary)",
          foreground: "var(--secondary-foreground)",
        },
        muted: {
          DEFAULT: "var(--muted)",
          foreground: "var(--muted-foreground)",
        },
        accent: {
          DEFAULT: "var(--accent)",
          foreground: "var(--accent-foreground)",
        },
        destructive: {
          DEFAULT: "var(--destructive)",
          foreground: "var(--destructive-foreground)",
        },
        success: {
          DEFAULT: "var(--success)",
          foreground: "var(--success-foreground)",
        },
        warning: {
          DEFAULT: "var(--warning)",
          foreground: "var(--warning-foreground)",
        },
        border: "var(--border)",
        input: "var(--input)",
        ring: "var(--ring)",
        sidebar: {
          DEFAULT: "var(--sidebar)",
          foreground: "var(--sidebar-foreground)",
          border: "var(--sidebar-border)",
        },
        editor: {
          DEFAULT: "var(--editor-bg)",
          line: "var(--editor-line)",
          add: "var(--editor-add)",
          remove: "var(--editor-remove)",
        },
        rail: {
          pending: "var(--rail-pending)",
          running: "var(--rail-running)",
          success: "var(--rail-success)",
          error: "var(--rail-error)",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      fontFamily: {
        sans: ["var(--font-sans)"],
        mono: ["var(--font-mono)"],
      },
    },
  },
  plugins: [],
} satisfies Config;
