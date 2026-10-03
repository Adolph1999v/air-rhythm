import { defineConfig, loadEnv } from 'vite'
import { deploymentHtml, deploymentSettings } from './site-config.ts'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), 'AIR_RHYTHM_')
  const { siteUrl, base } = deploymentSettings(env.AIR_RHYTHM_SITE_URL)
  return {
    base,
    plugins: [{
      name: 'public-sharing-url',
      transformIndexHtml(html) { return deploymentHtml(html, siteUrl) },
    }],
    build: {
      rolldownOptions: {
        input: { web: 'index.html', desktop: 'desktop.html' },
      },
    },
  }
})
