/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./templates/**/*.html", "./src/**/*.ts"],
  theme: {
    extend: {
      colors: {
        // Mirror :root vars in static/css/custom.css. Single source of truth: this file.
        "cookbook-bg": "#fdfcfb",
        "cookbook-warm": "#f5f1ec",     // header / surface wash
        "cookbook-text": "#1a1816",
        "cookbook-light": "#5a544f",
        "cookbook-accent": "#c1121f",
        "cookbook-border": "#a39a90",   // 3:1+ for interactive controls (WCAG 1.4.11)
        "cookbook-rule": "#e8e4df",     // decorative separators only
        "cookbook-success": "#2f7a3a",  // tip callouts / completed timers
      },
      fontFamily: {
        serif: ['"EB Garamond"', "Palatino", "Georgia", "serif"],
        sans: ['"Helvetica Neue"', "Helvetica", "Arial", "sans-serif"],
      },
      maxWidth: {
        cookbook: "1200px",
        "cookbook-narrow": "800px",
      },
      fontSize: {
        // Editorial display scale — overrides Tailwind's generic doubling.
        "recipe-title": ["4.5rem", { lineHeight: "1.05", letterSpacing: "-0.01em" }],
        "wordmark": ["2.25rem", { lineHeight: "1.1", letterSpacing: "0.08em" }],
        "eyebrow": ["0.75rem", { lineHeight: "1.4", letterSpacing: "0.15em" }],
      },
    },
  },
  plugins: [],
};
