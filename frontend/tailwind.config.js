/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "rgb(var(--parse-ink) / <alpha-value>)",
        "ink-soft": "rgb(var(--parse-ink-soft) / <alpha-value>)",
        paper: "rgb(var(--parse-paper) / <alpha-value>)",
        surface: "rgb(var(--parse-surface) / <alpha-value>)",
        line: "rgb(var(--parse-line) / <alpha-value>)",
        "line-strong": "rgb(var(--parse-line-strong) / <alpha-value>)",
        brand: "rgb(var(--parse-brand) / <alpha-value>)",
        "brand-strong": "rgb(var(--parse-brand-strong) / <alpha-value>)",
        "brand-soft": "rgb(var(--parse-brand-soft) / <alpha-value>)",
        "brand-mist": "rgb(var(--parse-brand-mist) / <alpha-value>)",
        danger: "rgb(var(--parse-danger) / <alpha-value>)",
        warning: "rgb(var(--parse-warning) / <alpha-value>)",
      },
      borderRadius: {
        sm: "var(--parse-radius-sm)",
        md: "var(--parse-radius-md)",
        lg: "var(--parse-radius-lg)",
      },
      fontFamily: {
        sans: [
          "Inter",
          "Avenir Next",
          "Segoe UI",
          "ui-sans-serif",
          "system-ui",
          "sans-serif",
        ],
      },
      animation: { "page-in": "page-in .35s var(--parse-ease) both" },
    },
  },
  plugins: [],
};
