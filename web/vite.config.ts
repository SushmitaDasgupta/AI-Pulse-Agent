import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

// Prefer non-prefixed API_BASE_URL on Vercel (avoids "public framework prefix"
// / Config-type friction). VITE_API_BASE_URL still works for local .env.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const apiBase = (
    env.API_BASE_URL ||
    env.VITE_API_BASE_URL ||
    'https://ai-pulse-agent-production.up.railway.app'
  ).replace(/\/$/, '')

  return {
    plugins: [react(), tailwindcss()],
    define: {
      'import.meta.env.VITE_API_BASE_URL': JSON.stringify(apiBase),
    },
  }
})
