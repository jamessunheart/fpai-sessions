/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        god: {
          bg: "#0a0a0f",
          card: "#13131f",
          accent: "#6d28d9",
          text: "#e2e8f0"
        }
      }
    },
  },
  plugins: [],
}

