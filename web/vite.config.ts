import { defineConfig } from 'vite'

export default defineConfig({
  base: './',
  build: {
    rolldownOptions: {
      input: { web: 'index.html', desktop: 'desktop.html' },
    },
  },
})
