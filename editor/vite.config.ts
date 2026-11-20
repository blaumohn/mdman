import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import { markdownFiles } from './server/plugin.ts'

export default defineConfig({
  plugins: [react(), markdownFiles()],
  server: {
    host: '127.0.0.1',
    strictPort: true,
    watch: { awaitWriteFinish: { stabilityThreshold: 200, pollInterval: 20 } },
  },
  test: {
    include: ['src/**/*.test.{ts,tsx}', 'server/**/*.test.ts'],
    environment: 'jsdom',
    setupFiles: ['./src/test-setup.ts'],
    globals: true,
  },
})
