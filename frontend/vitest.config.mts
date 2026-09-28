import { defineConfig } from 'vitest/config';
import path from 'node:path';

// Mirrors the `@/*` -> `src/*` alias from tsconfig.json so tests can import
// source modules that use it.
export default defineConfig({
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
});
