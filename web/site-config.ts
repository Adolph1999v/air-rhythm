export const DEFAULT_SITE_URL = 'https://air-rhythm.pages.dev/'

/** Keep absolute sharing URLs and the deployed asset path in agreement. */
export function deploymentSettings(publicUrl?: string): { siteUrl: string; base: string } {
  if (!publicUrl) return { siteUrl: DEFAULT_SITE_URL, base: './' }

  const url = new URL(publicUrl)
  if (url.protocol !== 'https:' || url.username || url.password || url.search || url.hash) {
    throw new Error('AIR_RHYTHM_SITE_URL must be an HTTPS site URL without credentials, query, or fragment.')
  }
  if (!url.pathname.endsWith('/')) url.pathname += '/'
  return { siteUrl: url.href, base: url.pathname }
}

export function deploymentHtml(html: string, siteUrl: string): string {
  return html.replaceAll(DEFAULT_SITE_URL, siteUrl)
}
