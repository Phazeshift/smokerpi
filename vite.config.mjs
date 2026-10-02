import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  build: {
    // Flask serves ../../build (see api/smokerpi/__init__.py) and the release
    // workflow packages it, so keep the CRA-era output directory.
    outDir: 'build',
  },
  server: {
    proxy: {
      '/api': 'http://localhost:5000',
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/setupTests.js',
  },
});
