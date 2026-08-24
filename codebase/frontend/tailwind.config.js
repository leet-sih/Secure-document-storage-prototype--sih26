/** tailwind.config.js — utility CSS config. Scans src for class names. */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      // TODO: brand palette (gov/security theme), status colors for case/audit badges
    },
  },
  plugins: [],
};
