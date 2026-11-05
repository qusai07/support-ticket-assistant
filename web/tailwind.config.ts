import type { Config } from "tailwindcss";

// Colors are CSS variables (RGB triplets) defined in globals.css for light and dark,
// so every utility (bg-surface, text-muted, border-line...) themes automatically.
const v = (name: string) => `rgb(var(--${name}) / <alpha-value>)`;

export default {
  darkMode: "class",
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: v("bg"),
        surface: v("surface"),
        sunken: v("sunken"),
        line: v("line"),
        ink: v("ink"),
        muted: v("muted"),
        primary: { DEFAULT: v("primary"), fg: v("primary-fg"), soft: v("primary-soft") },
        danger: { DEFAULT: v("danger"), soft: v("danger-soft") },
        warn: { DEFAULT: v("warn"), soft: v("warn-soft") },
        ok: { DEFAULT: v("ok"), soft: v("ok-soft") },
        info: { DEFAULT: v("info"), soft: v("info-soft") },
      },
      fontFamily: {
        sans: ["var(--font-sans)", "var(--font-arabic)", "system-ui", "sans-serif"],
      },
      borderRadius: { xl: "0.875rem" },
      boxShadow: { card: "0 1px 2px rgb(0 0 0 / 0.04), 0 1px 3px rgb(0 0 0 / 0.06)" },
    },
  },
  plugins: [],
} satisfies Config;
