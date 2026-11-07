import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { waitFor } from '@testing-library/svelte';

// The backend renders the schedule into #app so crawlers can read it. The app
// replaces that block on mount — `mount()` appends rather than replaces, so
// main.js clears it first. If that clear is ever dropped, both copies render on
// top of each other and every visitor sees the schedule twice.
const SEED = {
  schedule: [
    { day: 0, title_en: 'Latin Night', title_es: 'Noche Latina', note_en: '', note_es: '', open_time: '16:00', close_time: '02:00', is_closed: false },
  ],
  closedDays: [],
  menu: [
    {
      id: 1, slug: 'cocteles', name_en: 'Cocktails', name_es: 'Cócteles',
      items: [{ id: 1, category_id: 1, name_en: 'Cuba Libre', name_es: 'Cuba Libre', price: '4.00', promos: [] }],
    },
  ],
};

describe('boot', () => {
  beforeEach(() => {
    document.body.innerHTML =
      '<div id="app"><div id="marea-schedule"><h2>Party schedule</h2></div></div>';
    window.__MAREA_ALTA_DATA__ = SEED;
    localStorage.clear();
    global.fetch = vi.fn(async (url) => ({
      ok: true,
      status: 200,
      json: async () => {
        const path = String(url);
        if (path.includes('/api/surf')) {
          return {
            wave: 1.2, period: 12.5, direction: 225, tide: 0.6, rising: true,
            turns: [], sunrise: '06:21', sunset: '18:40',
            wind: 9.4, wind_direction: 200, temperature: 26.3,
          };
        }
        return path.includes('closed-days') ? [] : SEED.schedule;
      },
    }));
  });

  afterEach(() => {
    delete window.__MAREA_ALTA_DATA__;
    document.body.innerHTML = '';
    vi.restoreAllMocks();
  });

  it('replaces the server-rendered block instead of stacking on it', async () => {
    vi.resetModules();
    await import('./main.js');

    await waitFor(() => expect(document.querySelector('.hero')).toBeTruthy());
    expect(document.querySelector('#marea-schedule')).toBeNull();
    expect(document.querySelectorAll('#app > .hero')).toHaveLength(1);
  });

  it('paints the schedule without asking the API for it', async () => {
    vi.resetModules();
    await import('./main.js');

    await waitFor(() => expect(document.body.textContent).toContain('Latin Night'));
    // The surf widget makes its own same-origin `/api/surf` read; the schedule
    // must still come from the server-rendered seed.
    const urls = global.fetch.mock.calls
      .map(([url]) => String(url))
      .filter((url) => url.includes('/api/') && url !== '/api/surf');
    expect(urls).toEqual([]);
  });
});

// The menu route is a second entry point with its own server-rendered block, so
// it needs the same guard: `mount()` appends, and without the clear the visitor
// sees the menu twice.
describe('menu boot', () => {
  beforeEach(() => {
    document.body.innerHTML =
      '<div id="app"><div id="marea-menu"><h2>Drinks menu</h2></div></div>';
    window.__MAREA_ALTA_DATA__ = SEED;
    localStorage.clear();
    global.fetch = vi.fn(async (url) => ({
      ok: true,
      status: 200,
      json: async () => (String(url).includes('/api/menu') ? { categories: SEED.menu } : []),
    }));
  });

  afterEach(() => {
    delete window.__MAREA_ALTA_DATA__;
    document.body.innerHTML = '';
    vi.restoreAllMocks();
  });

  it('replaces the server-rendered menu instead of stacking on it', async () => {
    vi.resetModules();
    await import('./menu-main.js');

    await waitFor(() => expect(document.body.textContent).toContain('Cuba Libre'));
    expect(document.querySelector('#marea-menu')).toBeNull();
    expect(document.querySelectorAll('#app section.menu')).toHaveLength(1);
  });

  it('paints the menu without asking the API for it', async () => {
    vi.resetModules();
    await import('./menu-main.js');

    await waitFor(() => expect(document.body.textContent).toContain('$4.00'));
    const urls = global.fetch.mock.calls.map(([url]) => String(url));
    expect(urls.filter((u) => u.includes('/api/'))).toEqual([]);
  });
});