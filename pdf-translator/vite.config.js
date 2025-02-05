import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      external: ['pdfjs-dist/legacy/build/pdf.worker.js'], // Externaliser le worker
      output: {
        // Gérer les chunks pour le worker
        manualChunks: {
          worker: ['pdfjs-dist'],
        },
      },
    },
  },
  resolve: {
    alias: {
      // Alias pour le worker
      'pdfjs-dist/build/pdf.worker.entry': 'pdfjs-dist/legacy/build/pdf.worker.js',
    },
  },
})
