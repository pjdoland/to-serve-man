/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./templates/**/*.html", "./src/**/*.ts"],
  theme: {
    extend: {
      colors: {
        // Mirror :root vars in static/css/custom.css. Single source of truth: this file.
        "cookbook-bg": "#fdfcfb",
        "cookbook-warm": "#f5f1ec",     // body surface wash (used on listing backgrounds, hover)
        "cookbook-text": "#1a1816",
        "cookbook-light": "#3d3936",    // darkened from #5a544f to clear WCAG 1.4.3 (4.5:1 vs cream)
        "cookbook-accent": "#c1121f",   // reserved for interactive (links, tags, save) — never chrome
        "cookbook-border": "#a39a90",   // 3:1+ for interactive controls (WCAG 1.4.11)
        "cookbook-rule": "#e8e4df",     // decorative separators only
        "cookbook-success": "#2f7a3a",  // tip callouts / completed timers
        "cookbook-header": "#5C1A1C",   // cordovan; AAA on white text + cream body
        "cookbook-on-header": "#FAF7F0",// warm off-white for text on header
        "cookbook-focus": "#F5B14A",    // warm amber; ≥3:1 on cordovan AND cream
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
