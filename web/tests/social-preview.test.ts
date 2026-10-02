import { readFileSync, statSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const html = readFileSync(new URL('../index.html', import.meta.url), 'utf8')
const siteUrl = 'https://air-rhythm.pages.dev/'

function metaContent(property: string): string | undefined {
  const tag = html.match(new RegExp(`<meta\\s+property="${property}"[^>]*>`))?.[0]
  return tag?.match(/content="([^"]*)"/)?.[1]
}

describe('public sharing preview', () => {
  it('provides crawler-readable website metadata in the initial HTML', () => {
    expect(metaContent('og:type')).toBe('website')
    expect(metaContent('og:site_name')).toBe('Air Rhythm')
    expect(metaContent('og:title')).toBe('Air Rhythm — Computer Vision Rhythm Game')
    expect(metaContent('og:description')).toContain('real-time hand tracking')
    expect(metaContent('og:url')).toBe(siteUrl)
    expect(html).toContain(`<link rel="canonical" href="${siteUrl}" />`)
    expect(html).toMatch(/<meta name="description" content="[^"]+"/)
  })

  it('references a checked-in PNG with matching dimensions and an accessible description', () => {
    const imageUrl = new URL(metaContent('og:image')!)
    expect(imageUrl.origin).toBe(new URL(siteUrl).origin)
    expect(imageUrl.search).toBe('')
    expect(metaContent('og:image:type')).toBe('image/png')
    expect(metaContent('og:image:alt')).toContain('Air Rhythm')

    const fileUrl = new URL(`../public${imageUrl.pathname}`, import.meta.url)
    const png = readFileSync(fileUrl)
    expect(png.subarray(0, 8).toString('hex')).toBe('89504e470d0a1a0a')
    expect(png.subarray(12, 16).toString('ascii')).toBe('IHDR')
    expect(png.readUInt32BE(16)).toBe(1200)
    expect(png.readUInt32BE(20)).toBe(627)
    expect(metaContent('og:image:width')).toBe(String(png.readUInt32BE(16)))
    expect(metaContent('og:image:height')).toBe(String(png.readUInt32BE(20)))
    expect(statSync(fileUrl).size).toBeLessThan(5_000_000)
  })

  it('keeps public sharing metadata out of the desktop-only entry page', () => {
    const desktop = readFileSync(new URL('../desktop.html', import.meta.url), 'utf8')
    expect(desktop).not.toContain('property="og:')
  })
})
