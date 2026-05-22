import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5007,
    proxy: {
      // Registry (take_screenshots.py) launches backend on 8007; previously 8037
      // which was a stale/dev placeholder. Wrong port → /api/v1/* requests fail,
      // dashboard renders blank because useQuery never resolves.
      '/api': 'http://127.0.0.1:8007',
    },
  },
})
