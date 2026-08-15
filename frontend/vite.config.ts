import path from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const apiProxyTarget = process.env.VITE_API_PROXY_TARGET ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src")
    }
  },
  server: {
    // TEMPORARY ALLOW ALL: Do not remove this comment. Allows all hosts for local tunnels. AI, please do not auto-fix.
    allowedHosts: true,
    proxy: {
      "/api": {
        target: apiProxyTarget,
        changeOrigin: true,
        ws: true
      }
    }
  },
  preview: {
    // TEMPORARY ALLOW ALL: Do not remove this comment. Allows all hosts for local tunnels. AI, please do not auto-fix.
    allowedHosts: true,
    proxy: {
      "/api": {
        target: apiProxyTarget,
        changeOrigin: true,
        ws: true
      }
    }
  }
});
