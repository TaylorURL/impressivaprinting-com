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
    // Every browser that runs a module script has these; naming them stops the
    // toolchain guessing an older baseline and shipping transforms for it.
    target: ['chrome111', 'edge111', 'firefox111', 'safari16.4'],
    // A visitor who never signs in still pays for the client if it is
    // announced to the preload scanner. The other preloads are marked low by
    // scripts/paint-first.js so they cannot take a turn ahead of the first
    // screen, and this one is left out of every list entirely, because at
    // fifty kilobytes it is the one whose share of the connection is worth
    // having back. AuthContext reaches the client through a dynamic import,
    // so the one list left to keep it out of is the dependency list of that
    // import: the signed-in path spends a round trip discovering it, and the
    // first screen keeps the connection to itself.
    modulePreload: {
      resolveDependencies: (_file, deps) => deps.filter((dep) => !dep.includes('supabase')),
    },
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
