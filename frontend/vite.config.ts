import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: { assetsDir: "app-assets" },
  server: {
    host: "127.0.0.1",
    port: 8501,
    strictPort: true,
    proxy: {
      "^/(profiles|projects|jobs|analyses|assets|exports|candidates|revisions|publications|integrations|tiktok-posts|health|docs|openapi.json)(/|$)":
        "http://127.0.0.1:8000",
    },
  },
});
