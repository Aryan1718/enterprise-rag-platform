import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        app: {
          bg: "#0B0B0F",
          surface: "#12121A",
          elevated: "#1A1A26",
          border: "#2A2A36",
          text: "#FFFFFF",
          muted: "#C8CBD2",
          accent: "#F97316",
          accentSoft: "#FDBA74",
          danger: "#EF4444",
          success: "#22C55E",
        },
      },
      boxShadow: {
        card: "0 20px 45px -28px rgba(0, 0, 0, 0.8)",
        glow: "0 0 0 1px rgba(249, 115, 22, 0.2), 0 0 60px rgba(249, 115, 22, 0.18)",
      },
      backgroundImage: {
        "auth-glow": "radial-gradient(circle at top left, rgba(249,115,22,0.32), rgba(11,11,15,0) 40%), radial-gradient(circle at bottom right, rgba(249,115,22,0.2), rgba(11,11,15,0) 45%)",
      },
    },
  },
  plugins: [],
};

export default config;
