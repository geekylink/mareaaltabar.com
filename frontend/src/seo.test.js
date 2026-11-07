import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

// These files live outside the Svelte tree on purpose: Vite copies
// `frontend/public/` to `dist/` unchanged, and the backend's static mount serves
// the result at the same origin as the rendered pages.
const read = (path) => readFileSync(new URL(path, import.meta.url), 'utf8');
const readBytes = (path) => readFileSync(new URL(path, import.meta.url));

const PUBLIC_ROOT = 'https://mareaaltabar.com';

const meta = (html, key, value) => {
  const doc = new DOMParser().parseFromString(html, 'text/html');
  return doc.querySelector(`meta[${key}="${value}"]`)?.getAttribute('content') ?? null;
};

// PNG stores width and height as big-endian uint32s at bytes 16-24 of the
// IHDR chunk. Reading them here means a future image swap cannot silently ship
// a card the wrong shape for the social previews.
const pngSize = (bytes) => ({
  width: bytes.readUInt32BE(16),
  height: bytes.readUInt32BE(20),
});

describe('public SEO files', () => {
  it('keeps the admin panel out of crawlers', () => {
    const robots = read('../public/robots.txt');

    for (const path of ['/admin', '/admin/login', '/admin/schedule', '/admin/menu', '/admin/logs']) {
      expect(robots).toContain(`Disallow: ${path}`);
    }
    expect(robots).toContain(`Sitemap: ${PUBLIC_ROOT}/sitemap.xml`);
  });

  it('lists the public documents in a well-formed sitemap', () => {
    const xml = read('../public/sitemap.xml');
    const doc = new DOMParser().parseFromString(xml, 'application/xml');
    const locs = [...doc.querySelectorAll('loc')].map((node) => node.textContent);

    expect(doc.querySelector('parsererror')).toBeNull();
    expect(locs).toEqual([`${PUBLIC_ROOT}/`, `${PUBLIC_ROOT}/menu`, `${PUBLIC_ROOT}/news`]);
  });

  it('gives each document one canonical URL', () => {
    expect(read('../index.html')).toContain(
      `<link rel="canonical" href="${PUBLIC_ROOT}/" />`
    );
    expect(read('../menu.html')).toContain(
      `<link rel="canonical" href="${PUBLIC_ROOT}/menu" />`
    );
    expect(read('../news.html')).toContain(
      `<link rel="canonical" href="${PUBLIC_ROOT}/news" />`
    );
  });

  it('gives each document a complete Open Graph and Twitter preview', () => {
    const documents = [
      { html: read('../index.html'), url: `${PUBLIC_ROOT}/`, image: `${PUBLIC_ROOT}/og-image.png` },
      { html: read('../menu.html'), url: `${PUBLIC_ROOT}/menu`, image: `${PUBLIC_ROOT}/og-menu.png` },
      { html: read('../news.html'), url: `${PUBLIC_ROOT}/news`, image: `${PUBLIC_ROOT}/og-image.png` },
    ];

    for (const { html, url, image } of documents) {
      expect(meta(html, 'property', 'og:type')).toBe('website');
      expect(meta(html, 'property', 'og:site_name')).toBe('Marea Alta Surf Bar');
      expect(meta(html, 'property', 'og:title')).toBeTruthy();
      expect(meta(html, 'property', 'og:description')).toBeTruthy();
      expect(meta(html, 'property', 'og:url')).toBe(url);
      expect(meta(html, 'property', 'og:image')).toBe(image);
      expect(meta(html, 'property', 'og:image:width')).toBe('1200');
      expect(meta(html, 'property', 'og:image:height')).toBe('630');
      expect(meta(html, 'property', 'og:image:alt')).toBeTruthy();
      expect(meta(html, 'property', 'og:locale')).toBe('en_US');
      expect(meta(html, 'property', 'og:locale:alternate')).toBe('es_EC');
      expect(meta(html, 'name', 'twitter:card')).toBe('summary_large_image');
      expect(meta(html, 'name', 'twitter:title')).toBeTruthy();
      expect(meta(html, 'name', 'twitter:description')).toBeTruthy();
      expect(meta(html, 'name', 'twitter:image')).toBe(image);
    }
  });

  it('ships social preview images at the size the tags promise', () => {
    for (const image of ['../public/og-image.png', '../public/og-menu.png']) {
      const bytes = readBytes(image);
      expect(bytes.subarray(1, 4).toString('ascii')).toBe('PNG');
      expect(pngSize(bytes)).toEqual({ width: 1200, height: 630 });
    }
  });

  it('points both documents at the branded icon set', () => {
    for (const html of [read('../index.html'), read('../menu.html'), read('../news.html')]) {
      expect(html).toContain('<link rel="icon" href="/icons/favicon.svg" type="image/svg+xml" />');
      expect(html).toContain('href="/icons/favicon-32.png" sizes="32x32"');
      expect(html).toContain('href="/icons/favicon-16.png" sizes="16x16"');
      expect(html).toContain('rel="apple-touch-icon" href="/icons/apple-touch-icon.png"');
      expect(html).not.toContain('data:image/svg+xml');
    }
  });

  it('self-hosts and preloads both typefaces instead of calling Google Fonts', () => {
    for (const html of [read('../index.html'), read('../menu.html'), read('../news.html')]) {
      expect(html).toContain('href="/fonts/bricolage-grotesque-latin.woff2"');
      expect(html).toContain('href="/fonts/figtree-latin.woff2"');
      expect(html).toContain('as="font"');
      expect(html).not.toContain('fonts.googleapis.com');
      expect(html).not.toContain('fonts.gstatic.com');
    }

    for (const font of ['../public/fonts/bricolage-grotesque-latin.woff2', '../public/fonts/figtree-latin.woff2']) {
      expect(readBytes(font).subarray(0, 4).toString('ascii')).toBe('wOF2');
    }
  });

  it('ships every icon at its advertised size', () => {
    const icons = {
      '../public/icons/favicon-16.png': 16,
      '../public/icons/favicon-32.png': 32,
      '../public/icons/apple-touch-icon.png': 180,
      '../public/icons/icon-192.png': 192,
      '../public/icons/icon-512.png': 512,
    };

    for (const [path, size] of Object.entries(icons)) {
      expect(pngSize(readBytes(path))).toEqual({ width: size, height: size });
    }

    expect(read('../public/icons/favicon.svg')).toContain('<svg');
    expect(readBytes('../public/icons/favicon.ico').subarray(0, 4)).toEqual(
      Buffer.from([0x00, 0x00, 0x01, 0x00])
    );
  });
});
