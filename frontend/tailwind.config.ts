import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      // ── Design System Tokens ─────────────────────────────────
      // Spacing scale: 4px base (0.25rem increments)
      // Type scale: 3 sizes (sm: 0.875rem, base: 1rem, lg: 1.125rem)
      // Accent: Veridoc blue (#0c8ee7 → veridoc-500)
      // Neutral: Tailwind gray scale
      colors: {
        veridoc: {
          50: "#f0f7ff",
          100: "#e0effe",
          200: "#bae0fd",
          300: "#7cc8fb",
          400: "#36aaf5",
          500: "#0c8ee7",
          600: "#0070c4",
          700: "#01599f",
          800: "#064c83",
          900: "#0b406d",
          950: "#072849",
        },
        accent: {
          DEFAULT: "#f59e0b",
          light: "#fbbf24",
          dark: "#d97706",
        },
        // Surface colors for cards, dialogs, etc.
        surface: {
          DEFAULT: "var(--color-surface)",
          secondary: "var(--color-surface-secondary)",
          hover: "var(--color-surface-hover)",
        },
        // Border colors
        border: {
          DEFAULT: "var(--color-border)",
          subtle: "var(--color-border-subtle)",
        },
        // Semantic colors via CSS variables for @apply directives
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
      },
      fontFamily: {
        display: ["var(--font-inter)", "system-ui", "sans-serif"],
        body: ["var(--font-source-serif)", "Georgia", "serif"],
        mono: ["var(--font-jetbrains-mono)", "Fira Code", "monospace"],
      },
      fontSize: {
        // Small: 0.875rem/1.25rem for UI labels and secondary text
        sm: ["0.875rem", { lineHeight: "1.25rem" }],
        // Base: 1rem/1.5rem for primary content
        base: ["1rem", { lineHeight: "1.5rem" }],
        // Large: 1.125rem/1.75rem for headings
        lg: ["1.125rem", { lineHeight: "1.75rem" }],
      },
      spacing: {
        // Design tokens: 4px = 1, 8px = 2, 12px = 3, 16px = 4, etc.
        0.5: "0.125rem", // 2px
        1: "0.25rem",    // 4px
        1.5: "0.375rem", // 6px
        2: "0.5rem",     // 8px
        2.5: "0.625rem", // 10px
        3: "0.75rem",    // 12px
        3.5: "0.875rem", // 14px
        4: "1rem",       // 16px
        5: "1.25rem",    // 20px
        6: "1.5rem",     // 24px
        8: "2rem",       // 32px
        10: "2.5rem",    // 40px
        12: "3rem",      // 48px
        16: "4rem",      // 64px
      },
      borderRadius: {
        // Consistent border radius scale
        sm: "0.375rem",  // 6px
        DEFAULT: "0.5rem", // 8px
        md: "0.625rem",  // 10px
        lg: "0.75rem",   // 12px
        xl: "1rem",      // 16px
        "2xl": "1.25rem", // 20px
      },
      animation: {
        "cursor-blink": "blink 1s step-end infinite",
        "fade-in": "fadeIn 0.3s ease-out",
        "fade-in-up": "fadeInUp 0.3s ease-out",
        "slide-up": "slideUp 0.3s ease-out",
        "slide-in-right": "slideInRight 0.3s ease-out",
        "slide-out-right": "slideOutRight 0.3s ease-out",
        "scale-in": "scaleIn 0.2s ease-out",
        "pulse-slow": "pulse 3s ease-in-out infinite",
        "shimmer": "shimmer 2s infinite linear",
      },
      keyframes: {
        blink: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0" },
        },
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        fadeInUp: {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(10px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        slideInRight: {
          "0%": { transform: "translateX(100%)", opacity: "0" },
          "100%": { transform: "translateX(0)", opacity: "1" },
        },
        slideOutRight: {
          "0%": { transform: "translateX(0)", opacity: "1" },
          "100%": { transform: "translateX(100%)", opacity: "0" },
        },
        scaleIn: {
          "0%": { transform: "scale(0.95)", opacity: "0" },
          "100%": { transform: "scale(1)", opacity: "1" },
        },
        shimmer: {
          "0%": { transform: "translateX(-100%)" },
          "100%": { transform: "translateX(100%)" },
        },
      },
      backgroundImage: {
        "shimmer-gradient":
          "linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.4) 50%, transparent 100%)",
      },
    },
  },
  plugins: [],
};

export default config;
