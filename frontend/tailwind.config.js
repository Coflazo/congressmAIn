/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        primary: "var(--color-primary)",
        "primary-container": "var(--color-primary-container)",
        secondary: "var(--color-secondary)",
        "secondary-container": "var(--color-secondary-container)",
        tertiary: "var(--color-tertiary)",
        background: "var(--color-background)",
        surface: "var(--color-surface)",
        "surface-low": "var(--color-surface-low)",
        "surface-container": "var(--color-surface-container)",
        "surface-high": "var(--color-surface-high)",
        "surface-highest": "var(--color-surface-highest)",
        "surface-lowest": "var(--color-surface-lowest)",
        "on-surface": "var(--color-on-surface)",
        "on-surface-variant": "var(--color-on-surface-variant)",
        "outline-variant": "var(--color-outline-variant)"
      },
      borderRadius: {
        DEFAULT: "var(--radius-sm)",
        lg: "var(--radius-lg)",
        xl: "var(--radius-xl)"
      },
      fontFamily: {
        serif: ["Newsreader", "Georgia", "serif"],
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"]
      }
    }
  },
  plugins: []
};
