import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  outputDir: '../.local/playwright',
  workers: 1,
  use: { baseURL: 'http://127.0.0.1:5183', headless: true },
  webServer: {
    command: 'node bin/serve.mjs --file ../README.md --port 5183 --no-open',
    url: 'http://127.0.0.1:5183/api/status',
    reuseExistingServer: false,
  },
})
