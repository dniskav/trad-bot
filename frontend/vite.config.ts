import react from '@vitejs/plugin-react'
import path from 'path'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@assets': path.resolve(__dirname, './src/assets'),
      '@config': path.resolve(__dirname, './src/config'),
      '@components': path.resolve(__dirname, './src/components'),
      '@hooks': path.resolve(__dirname, './src/hooks'),
      '@eventBus': path.resolve(__dirname, './src/eventBus'),
      '@services': path.resolve(__dirname, './src/services'),
      '@utils': path.resolve(__dirname, './src/utils')
    }
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8200',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      },
      '/account': {
        target: 'http://127.0.0.1:8200',
        changeOrigin: true
      },
      '/bot': {
        target: 'http://127.0.0.1:8200',
        changeOrigin: true
      },
      '/metrics': {
        target: 'http://127.0.0.1:8200',
        changeOrigin: true
      },
      '/ws': {
        target: 'ws://127.0.0.1:8200',
        ws: true,
        changeOrigin: true,
        rewrite: (path) => path
      }
    }
  }
})
