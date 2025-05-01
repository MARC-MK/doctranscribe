import { type Config } from "tailwindcss";

export default {
  darkMode: "class",
  content: [
    "./index.html",
    "./src/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: "#7dd3fc", // sky-300
          dark: "#0284c7", // sky-600
        },
        accent: {
          DEFAULT: "#a78bfa", // violet-400
        },
        background: {
          DEFAULT: "#0f172a", // slate-900
          light: "#1e293b", // slate-800
        },
      },
    },
  },
  plugins: [],
} satisfies Config; 