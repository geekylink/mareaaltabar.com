import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';

// The PWA files live in `frontend/public/`, which Vite copies to `dist/`
// unchanged and the backend serves from the same origin. These tests keep the
// manifest, the service worker and the two documents in step — a typo in a
// manifest path would only show up on a real phone install.

const read = (path) => readFileSync(new URL(path, import.meta.url), 'utf8');
const readBytes = (path) => readFileSync(new URL(path, import.meta.url));

const pngSize = (bytes) => ({
  width: bytes.readUInt32BE(16),
  height: bytes.readUInt32BE(20),
});

describe('PWA manifest', () => {
  const manifest = JSON.parse(read('../public/manifest.json'));

  it('is installable as a standalone app', () => {
    expect(manifest.name).toBe('Marea Alta Surf Bar');
    expect(manifest.short_name).toBe('Marea Alta');
    expect(manifest.start_url).toBe('/');
    expect(manifest.scope).toBe('/');
    expect(manifest.display).toBe('standalone');
    expect(manifest.theme_color).toBe('#0B3C49');
    expect(manifest.background_color).toBeTruthy();
  });

  it('advertises the 192 and 512 icons at their real sizes', () => {
    const sizes = manifest.icons.map((icon) => icon.sizes).sort();
    expect(sizes).toEqual(['192x192', '512x512']);

    for (const icon of manifest.icons) {
      expect(icon.type).toBe('image/png');
      const bytes = readBytes(`../public${icon.src}`);
      expect(pngSize(bytes)).toEqual({
        width: Number(icon.sizes.split('x')[0]),
        height: Number(icon.sizes.split('x')[1]),
      });
    }
  });

  it('is linked from both documents, with the Apple install metadata', () => {
    for (const html of [read('../index.html'), read('../menu.html')]) {
      expect(html).toContain('<link rel="manifest" href="/manifest.json" />');
      expect(html).toContain('name="apple-mobile-web-app-capable" content="yes"');
      expect(html).toContain('name="apple-mobile-web-app-title" content="Marea Alta"');
    }
  });
});

describe('service worker', () => {
  const sw = read('../public/sw.js');

  it('is versioned and precaches the shell and the offline fallback', () => {
    expect(sw).toContain('const VERSION =');
    expect(sw).toContain("'/offline.html'");
    expect(sw).toContain("addEventListener('install'");
    expect(sw).toContain("addEventListener('activate'");
    expect(sw).toContain('skipWaiting');
  });

  it('only caches the public API reads the homepage uses', () => {
    for (const path of ['/api/schedule', '/api/closed-days', '/api/menu', '/api/notices', '/api/special-events']) {
      expect(sw).toContain(`'${path}'`);
    }
    // Admin reads and writes must never be stored on disk.
    for (const path of ['/api/rsvps', '/api/reservations', '/api/logs', '/api/subscribers']) {
      expect(sw).not.toContain(`'${path}'`);
    }
    expect(sw).toContain("request.method !== 'GET'");
    expect(sw).toContain("url.pathname.startsWith('/admin')");
  });

  it('uses network-first for pages and API, cache-first for immutable files', () => {
    expect(sw).toContain('async function navigation');
    expect(sw).toContain('async function networkFirst');
    expect(sw).toContain('async function cacheFirst');
    expect(sw).toContain("['/assets/', '/icons/', '/uploads/']");
  });

  it('is registered by both entry points, production only', () => {
    for (const entry of [read('./main.js'), read('./menu-main.js')]) {
      expect(entry).toContain('registerServiceWorker()');
    }
    const pwa = read('./pwa.js');
    expect(pwa).toContain('serviceWorker.register');
    expect(pwa).toContain('import.meta.env.PROD');
  });
});
