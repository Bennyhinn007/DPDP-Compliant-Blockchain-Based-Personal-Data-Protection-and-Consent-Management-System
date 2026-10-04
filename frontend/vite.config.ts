import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:5000",
        changeOrigin: true,
      },
    },
  },
  build: {
    // Split large third-party libraries into separate, long-term-cacheable
    // chunks so the main bundle is small and vendor code is reused across
    // deploys (only app code changes bust the cache).
    chunkSizeWarningLimit: 900,
    rollupOptions: {
      output: {
        manualChunks: {
          "react-vendor": ["react", "react-dom", "react-router-dom"],
          "charts": ["recharts"],
          "motion": ["framer-motion"],
          "query": ["@tanstack/react-query"],
          "crypto": ["@noble/secp256k1", "@noble/hashes"],
        },
      },
    },
  },
});
