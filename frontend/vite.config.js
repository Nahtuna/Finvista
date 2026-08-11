import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: {
    // Tối ưu bundle size - sử dụng esbuild mặc định
    minify: 'esbuild',
    // Code splitting
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom'],
          'charts-vendor': ['lightweight-charts'],
          'utils-vendor': ['lucide-react', 'clsx', 'tailwind-merge'],
        },
        chunkFileNames: 'assets/[name]-[hash].js',
        entryFileNames: 'assets/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash].[ext]',
      },
    },
    // Tăng chunk size warning limit
    chunkSizeWarningLimit: 1000,
    // CSS code splitting
    cssCodeSplit: true,
  },
  // Tối ưu dev server
  server: {
    hmr: {
      overlay: false,
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: "./src/test/setup.js",
    pool: "threads",
    maxWorkers: 1,
    minWorkers: 1
  }
});
