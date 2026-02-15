export const theme = {
  colors: {
    background: "#0B0B0F",
    surface: "#12121A",
    textPrimary: "#FFFFFF",
    textSecondary: "#C8CBD2",
    accent: "#F97316",
    accentMuted: "#FDBA74",
    border: "#2A2A36",
    danger: "#EF4444",
    success: "#22C55E",
  },
  radius: {
    md: "0.75rem",
    lg: "1rem",
    xl: "1.25rem",
  },
  shadow: {
    card: "0 20px 45px -28px rgba(0, 0, 0, 0.8)",
    glow: "0 0 0 1px rgba(249, 115, 22, 0.2), 0 0 60px rgba(249, 115, 22, 0.18)",
  },
} as const;

export const appName = "Enterprise RAG";
