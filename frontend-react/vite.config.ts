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

          // React core — must come before generic vendor catch-all
          if (id.includes('/react-dom/') || id.includes('/react/index') || id.includes('/scheduler/')) {
            return 'vendor-react'
          }
          // Framer Motion
          if (id.includes('framer-motion')) {
            return 'vendor-motion'
          }
          // Syntax highlighter + prism language definitions (the big one)
          if (
            id.includes('react-syntax-highlighter') ||
            id.includes('/prismjs/') ||
            id.includes('/highlight.js/')
          ) {
            return 'vendor-syntax'
          }
          // Lucide icons
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
          // Everything else (react-router-dom, etc.)
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
