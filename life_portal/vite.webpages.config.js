import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { fileURLToPath } from 'node:url';

// Separate output: never rebuild or replace the running portal assets/template.
export default defineConfig({
  base: '/files/',
  plugins: [vue()],
  build: {
    outDir: '/tmp/life-standalone-webpages',
    emptyOutDir: true,
    rollupOptions: {
      input: fileURLToPath(new URL('./standalone-webpages.js', import.meta.url)),
      output: {
        entryFileNames: 'life-webpages-entry-[hash].js',
        chunkFileNames: 'life-webpages-[name]-[hash].js',
        assetFileNames: 'life-webpages-[name]-[hash][extname]',
      },
    },
  },
});
