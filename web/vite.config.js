import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// `npm run dev` outside Docker proxies to the api container's localhost port
export default defineConfig({
  plugins: [react()],
  server: { proxy: { '/api': 'http://127.0.0.1:8000' } },
})
