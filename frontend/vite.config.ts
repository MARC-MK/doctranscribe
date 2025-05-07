import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tsconfigPaths from "vite-tsconfig-paths";
import path from "path";

// Get environment variables or use defaults
const backendUrl = process.env.VITE_API_URL || 'http://localhost:8000';
console.log('Backend URL:', backendUrl);

export default defineConfig({
  plugins: [react(), tsconfigPaths()],
  server: {
    port: 3001,
    proxy: {
      '/api': {
        target: backendUrl,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
        configure: (proxy, _options) => {
          proxy.on('error', (err, _req, _res) => {
            console.log('proxy error', err);
          });
          proxy.on('proxyReq', (proxyReq, req, _res) => {
            console.log('Sending Request to the Target:', req.method, req.url);
          });
          proxy.on('proxyRes', (proxyRes, req, _res) => {
            console.log('Received Response from the Target:', proxyRes.statusCode, req.url);
          });
        }
      },
      '/auth': {
        target: backendUrl,
        changeOrigin: true
      },
      '/handwriting': {
        target: backendUrl,
        changeOrigin: true
      }
    }
  },
  preview: {
    port: 3000,
  },
  envPrefix: "VITE_",
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  },
}); 