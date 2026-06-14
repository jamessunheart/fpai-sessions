import type { Config } from "tailwindcss";

export default {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: "#f6f8fc",
        panel: "#ffffff",
        accent: "#0ea5e9",
        good: "#059669",
        warn: "#d97706",
        danger: "#dc2626",
      },
      fontFamily: { sans: ["Inter", "ui-sans-serif", "system-ui"] },
    },
  },
  plugins: [],
} satisfies Config;
