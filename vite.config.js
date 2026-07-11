import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { fileURLToPath, URL } from 'node:url';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
      '@app': fileURLToPath(new URL('./src/app', import.meta.url)),
      '@components': fileURLToPath(new URL('./src/app/components', import.meta.url)),
      '@reactbits': fileURLToPath(new URL('./src/app/components/reactbits', import.meta.url)),
      '@views': fileURLToPath(new URL('./src/app/views', import.meta.url)),
      '@constants': fileURLToPath(new URL('./src/app/constants', import.meta.url)),
      '@context': fileURLToPath(new URL('./src/app/context', import.meta.url)),
      '@hooks': fileURLToPath(new URL('./src/app/hooks', import.meta.url)),
      '@data': fileURLToPath(new URL('./src/app/data', import.meta.url)),
      '@utils': fileURLToPath(new URL('./src/app/utils', import.meta.url)),
    },
  },
});
