// vite.config.ts — dev server + build config.
// Dev proxy forwards /api to the Flask backend so cookies + same-origin work locally
// without CORS headaches. In production Nginx handles this routing instead.
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:5000",
        changeOrigin: true,
        // credentials/cookies flow through for the refresh-token flow
      },
    },
  },
  build: {
    outDir: "dist",
  },
});
