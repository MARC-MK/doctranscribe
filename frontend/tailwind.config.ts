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
      animation: {
        "fadeIn": "fadeIn 0.5s ease-out forwards",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0", transform: "translateY(10px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [],
} satisfies Config; 