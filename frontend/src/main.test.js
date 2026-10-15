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
      json: async () => (String(url).includes('closed-days') ? [] : SEED.schedule),
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
    // The surf widget still calls Open-Meteo; the schedule must not.
    const urls = global.fetch.mock.calls.map(([url]) => String(url));
    expect(urls.filter((u) => u.includes('/api/'))).toEqual([]);
  });
});