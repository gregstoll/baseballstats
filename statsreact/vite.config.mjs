import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(() => {
  return {
    base: "/~gregstoll/baseball/",
    build: {
      outDir: 'build',
    },
    plugins: [react()],
  };
});
