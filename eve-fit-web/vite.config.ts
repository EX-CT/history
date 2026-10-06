import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

// GitHub Pages serves the site under /<repo>/ ; override with BASE=/ for other hosts.
export default defineConfig({
  base: process.env.BASE ?? '/eve-fit-web/',
  plugins: [react()],
  worker: { format: 'es' },
});
