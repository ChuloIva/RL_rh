import type { Config } from "tailwindcss";

// Solid colors are exposed as `rgb(var(--c-x) / <alpha-value>)` so opacity
// modifiers (e.g. `bg-panel/70`, `text-ink/85`) keep working while the actual
// channel values are swapped per-theme via CSS variables in globals.css.
const rgb = (v: string) => `rgb(var(${v}) / <alpha-value>)`;

const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        void: rgb("--c-void"),
        ink: rgb("--c-ink"),
        muted: rgb("--c-muted"),
        faint: rgb("--c-faint"),
        gold: rgb("--c-gold"),
        ember: rgb("--c-ember"),
        panel: rgb("--c-panel"),
        panel2: rgb("--c-panel2"),
        // Already-translucent hairlines — used without alpha modifiers.
        line: "var(--c-line)",
        line2: "var(--c-line2)",
      },
      fontFamily: {
        serif: ["var(--font-serif)", "Manrope", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "IBM Plex Mono", "ui-monospace", "monospace"],
      },
      letterSpacing: {
        widest2: "0.32em",
      },
      keyframes: {
        rise: {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        glow: {
          "0%,100%": { opacity: "0.35" },
          "50%": { opacity: "0.9" },
        },
      },
      animation: {
        rise: "rise 0.7s ease both",
        glow: "glow 4s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
