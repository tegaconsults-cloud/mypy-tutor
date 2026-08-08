import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: 'dist',
    sourcemap: false,
    chunkSizeWarningLimit: 1200,
    modulePreload: false,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) return

          // React + ReactDOM + scheduler MUST stay in one chunk together.
          // Splitting them causes "Cannot read __SECRET_INTERNALS" because
          // react-dom/client and react would resolve to different instances.
          // Keep them all in the catch-all 'vendor' chunk (no explicit entry).

          // Framer Motion — large, changes rarely
          if (id.includes('framer-motion') || id.includes('motion-dom') || id.includes('motion-utils')) {
            return 'vendor-motion'
          }
          // Syntax highlighter + prism — the heaviest single dep
          if (
            id.includes('react-syntax-highlighter') ||
            id.includes('/prismjs/') ||
            id.includes('/highlight.js/')
          ) {
            return 'vendor-syntax'
          }
          // Lucide icons — tree-shaken but still sizable
          if (id.includes('lucide-react')) {
            return 'vendor-icons'
          }
          // React-markdown + unified ecosystem
          if (
            id.includes('react-markdown') ||
            id.includes('/remark') ||
            id.includes('/rehype') ||
            id.includes('/unified/') ||
            id.includes('/micromark') ||
            id.includes('/mdast') ||
            id.includes('/hast')
          ) {
            return 'vendor-markdown'
          }
          // Everything else: react, react-dom, react-router-dom, scheduler, etc.
          return 'vendor'
        },
      },
    },
  },
  server: {
    proxy: {
      '/api': {
        target: 'https://mypytutor.onrender.com',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
