import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          pdf: ["@react-pdf-viewer/core"],
        },
      },
    },
  },
  server: {
    port: 5173,
  },
});
