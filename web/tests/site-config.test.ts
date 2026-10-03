import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { DEFAULT_SITE_URL, deploymentHtml, deploymentSettings } from '../site-config'

const html = readFileSync(new URL('../index.html', import.meta.url), 'utf8')
const pagesUrl = 'https://adolph1999v.github.io/air-rhythm/'

describe('deployment settings', () => {
  it('preserves the Cloudflare and desktop defaults', () => {
    expect(deploymentSettings()).toEqual({ siteUrl: DEFAULT_SITE_URL, base: './' })
    expect(deploymentHtml(html, DEFAULT_SITE_URL)).toBe(html)
  })

  it('uses the repository subdirectory for GitHub Pages assets', () => {
    expect(deploymentSettings(pagesUrl.slice(0, -1))).toEqual({ siteUrl: pagesUrl, base: '/air-rhythm/' })
  })

  it('uses HTTPS URLs without unsafe URL components', () => {
    for (const url of ['http://example.com/', 'https://user:pass@example.com/',
      'https://example.com/?tracking=1', 'https://example.com/#section']) {
      expect(() => deploymentSettings(url)).toThrow('AIR_RHYTHM_SITE_URL')
    }
  })

  it('changes all public sharing URLs together, including the preview image', () => {
    const builtHtml = deploymentHtml(html, pagesUrl)
    expect(builtHtml).toContain(`<link rel="canonical" href="${pagesUrl}" />`)
    expect(builtHtml).toContain(`<meta property="og:url" content="${pagesUrl}" />`)
    expect(builtHtml).toContain(`<meta property="og:image" content="${pagesUrl}social-preview.png" />`)
    expect(builtHtml).not.toContain(DEFAULT_SITE_URL)
    const desktop = readFileSync(new URL('../desktop.html', import.meta.url), 'utf8')
    expect(deploymentHtml(desktop, pagesUrl)).toBe(desktop)
  })
})
