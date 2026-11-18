import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vitest/config'

// https://vite.dev/config/
export default defineConfig({
  // Tailwind, derleme sırasında kodda kullanılan sınıfları bulur ve yalnızca onların CSS'ini üretir.
  plugins: [react(), tailwindcss()],
  resolve: {
    // "@/components/ui/button" gibi içe aktarmalar src/ klasöründen başlar; "../../.." zinciri gerekmez.
    // Aynı kısaltma TypeScript için tsconfig.app.json'da tanımlıdır.
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  test: {
    // Testler gerçek tarayıcı yerine jsdom'un sağladığı sahte tarayıcı ortamında çalışır.
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
  },
})
