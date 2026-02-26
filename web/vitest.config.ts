import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import tsconfigPaths from 'vite-tsconfig-paths'

export default defineConfig({
  plugins: [tsconfigPaths(), react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    globals: true,
    pool: 'forks',
    // Suppress undici UND_ERR_INVALID_ARG errors that leak from server
    // components making fetch calls in jsdom (no real server available).
    dangerouslyIgnoreUnhandledErrors: true,
  },
})
