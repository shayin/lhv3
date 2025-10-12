import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:9000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
  build: {
    // 减小块大小警告限制
    chunkSizeWarningLimit: 500,
    
    // 优化 Rollup 配置
    rollupOptions: {
      output: {
        // 手动代码分割，避免大文件
        manualChunks: (id) => {
          if (id.includes('node_modules')) {
            if (id.includes('monaco-editor')) {
              return 'monaco'
            }
            if (id.includes('react') || id.includes('react-dom')) {
              return 'react-vendor'
            }
            return 'vendor'
          }
        }
      }
    }
  },
  // 优化 esbuild
  esbuild: {
    minify: true,
    target: 'es2015'
  },
});