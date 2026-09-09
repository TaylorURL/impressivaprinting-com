import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { fileURLToPath, URL } from 'node:url';

// Dependencies are split away from application code so a route change ships
// only the route. The order of the tests matters: lucide-react and
// react-router both contain "react" in their paths.
function manualChunks(id) {
  if (!id.includes('node_modules')) return undefined;
  if (id.includes('lucide-react')) return 'icons';
  if (id.includes('@supabase')) return 'supabase';
  if (id.includes('react-router') || id.includes('react-dom') || id.includes('scheduler')) {
    return 'react';
  }
  if (/node_modules\/react\//.test(id)) return 'react';
  return 'vendor';
}

export default defineConfig({
  plugins: [react()],
  build: {
    // The browsers named here before were read off what runs a module script,
    // which is the wrong reading: module scripts landed years before the syntax
    // that baseline permits, so the range between the two is browsers that
    // fetch the bundle and then cannot parse it. Nothing caught it while the
    // output happened to stay inside their reach, and the first ES2021 operator
    // to reach the entry chunk broke every one of them at once.
    //
    // The entry arrives through a dynamic import, so a parse failure is not one
    // dead feature: the import rejects, React never mounts, and the first screen
    // the document carries sits there looking like a page that loaded. That is
    // the whole site, silently, for anyone below the line.
    //
    // ES2020 is the floor the code actually needs. Naming it holds the output to
    // it, so syntax past it is lowered on the way out rather than shipped and
    // discovered by a reader.
    target: 'es2020',
    rollupOptions: {
      output: { manualChunks },
    },
  },
  resolve: {
    // One copy of each of these resolves for the whole graph, so a transitive
    // dependency cannot pull a second React or a second Supabase client into
    // the bundle.
    dedupe: ['react', 'react-dom', 'react-router', 'react-router-dom', '@supabase/supabase-js'],
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
      '@app': fileURLToPath(new URL('./src/app', import.meta.url)),
      '@components': fileURLToPath(new URL('./src/app/components', import.meta.url)),
      '@views': fileURLToPath(new URL('./src/app/views', import.meta.url)),
      '@constants': fileURLToPath(new URL('./src/app/constants', import.meta.url)),
      '@context': fileURLToPath(new URL('./src/app/context', import.meta.url)),
      '@hooks': fileURLToPath(new URL('./src/app/hooks', import.meta.url)),
      '@data': fileURLToPath(new URL('./src/app/data', import.meta.url)),
      '@utils': fileURLToPath(new URL('./src/app/utils', import.meta.url)),
    },
  },
});
