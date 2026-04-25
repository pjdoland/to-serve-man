/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./templates/**/*.html", "./src/**/*.ts"],
  theme: {
    extend: {
      colors: {
        "cookbook-bg": "#fdfcfb",
        "cookbook-text": "#1a1816",
        "cookbook-light": "#5a544f",
        "cookbook-accent": "#c1121f",
        "cookbook-border": "#e8e4df",
      },
      fontFamily: {
        serif: ['"EB Garamond"', "Palatino", "Georgia", "serif"],
        sans: ['"Helvetica Neue"', "Helvetica", "Arial", "sans-serif"],
      },
      maxWidth: {
        cookbook: "1200px",
        "cookbook-narrow": "800px",
      },
    },
  },
  plugins: [],
};
