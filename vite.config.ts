import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],

  server: {
    host: "0.0.0.0",
    allowedHosts: [
      "brilliant-clarity-production-87cc.up.railway.app",
      "sih100-production-3f7d.up.railway.app",
      "chatlyme.xyz",
      "www.chatlyme.xyz",
    ],

    proxy: {
      "/api": "http://localhost:8000",
      "/health": "http://localhost:8000",
    },
  },

  preview: {
    host: "0.0.0.0",
    port: 8080,
    allowedHosts: [
      "brilliant-clarity-production-87cc.up.railway.app",
      "sih100-production-3f7d.up.railway.app",
      "chatlyme.xyz",
      "www.chatlyme.xyz",
    ],
  },
});