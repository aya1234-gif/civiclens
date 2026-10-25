/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        morocco: {
          red:   "#C1121F",
          green: "#006233",
          sand:  "#F5E6C8",
          dark:  "#1A1A2E",
        },
      },
    },
  },
  plugins: [],
};

