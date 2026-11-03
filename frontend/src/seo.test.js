import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

// These files live outside the Svelte tree on purpose: Vite copies
// `frontend/public/` to `dist/` unchanged, and the backend's static mount serves
// the result at the same origin as the rendered pages.
const read = (path) => readFileSync(new URL(path, import.meta.url), 'utf8');

const PUBLIC_ROOT = 'https://mareaaltabar.com';

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
    expect(locs).toEqual([`${PUBLIC_ROOT}/`, `${PUBLIC_ROOT}/menu`]);
  });

  it('gives each document one canonical URL', () => {
    expect(read('../index.html')).toContain(
      `<link rel="canonical" href="${PUBLIC_ROOT}/" />`
    );
    expect(read('../menu.html')).toContain(
      `<link rel="canonical" href="${PUBLIC_ROOT}/menu" />`
    );
  });
});
