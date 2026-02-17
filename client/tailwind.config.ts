import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        app: {
          bg: "#FFFFFF",
          surface: "#F9FAFB",
          border: "#E5E7EB",
          text: "#111827",
          muted: "#6B7280",
          accent: "#F97316",
          accentDark: "#EA580C",
          accentSoft: "#FFF7ED",
          danger: "#DC2626",
          success: "#16A34A",
          warning: "#D97706",
        },
      },
      borderRadius: {
        xl: "12px",
        "2xl": "14px",
      },
      boxShadow: {
        card: "0 8px 24px rgba(17, 24, 39, 0.06)",
      },
    },
  },
  plugins: [],
};

export default config;
