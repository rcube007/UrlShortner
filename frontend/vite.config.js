import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/shorten': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/info': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/delete': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
});
