import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const apiUrl = 'http://127.0.0.1:8002'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
    proxy: { '/api': apiUrl, '/openapi.json': apiUrl },
  },
  preview: { host: '127.0.0.1', port: 5173, strictPort: true },
})
