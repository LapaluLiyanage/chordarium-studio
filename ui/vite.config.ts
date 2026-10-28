/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  base: './', // relative paths so the bundle works from the plugin's resource provider
  plugins: [react()],
  build: { target: 'es2022', cssCodeSplit: false, assetsInlineLimit: 100_000_000, chunkSizeWarningLimit: 1500 },
  test: { environment: 'jsdom', globals: true, setupFiles: ['./src/test/setup.ts'], css: false },
})
