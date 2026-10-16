import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

// The backend renders the schedule into the HTML for crawlers, so the first
// paint needs no request. `load()` must use that payload once and then fall back
// to the API, otherwise the page either shows a loading state or never refreshes.
async function freshLoad() {
  vi.resetModules();
  return (await import('./api.js')).load;
}

const SCHEDULE = [
  { day: 0, title_en: 'Latin Night', title_es: 'Noche Latina', note_en: '', note_es: '', open_time: '16:00', close_time: '02:00', is_closed: false },
];
const CLOSED = [{ id: 1, date: '2030-12-25', reason_en: 'Christmas', reason_es: 'Navidad' }];
// A date that has certainly passed. The API filters these out, but a payload
// written before it did — a stale localStorage cache, an older server-rendered
// seed — still carries them, and a holiday that passed must not render.
const PAST = { id: 0, date: '2001-12-25', reason_en: 'New Year', reason_es: 'Año Nuevo' };
const MENU = [
  {
    id: 1, slug: 'cocteles', name_en: 'Cocktails', name_es: 'Cócteles',
    items: [{ id: 1, category_id: 1, name_en: 'Cuba Libre', name_es: 'Cuba Libre', price: '4.00' }],
  },
];

function jsonResponse(body) {
  return vi.fn(async (url) => {
    const path = String(url);
    const data = path.includes('closed-days') ? CLOSED : path.includes('/api/menu') ? { categories: MENU } : SCHEDULE;
    return { ok: true, status: 200, json: async () => data };
  });
}

describe('load() and the server-rendered payload', () => {
  beforeEach(() => {
    localStorage.clear();
    delete window.__MAREA_ALTA_DATA__;
  });

  afterEach(() => {
    vi.restoreAllMocks();
    delete window.__MAREA_ALTA_DATA__;
  });

  it('uses the embedded payload without calling the API', async () => {
    window.__MAREA_ALTA_DATA__ = { schedule: SCHEDULE, closedDays: CLOSED, menu: MENU };
    const fetchMock = jsonResponse();
    global.fetch = fetchMock;

    const load = await freshLoad();
    const result = await load();

    expect(result.schedule).toEqual(SCHEDULE);
    expect(result.closedDays).toEqual(CLOSED);
    expect(result.menu).toEqual(MENU);
    expect(result.error).toBeNull();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('caches the embedded payload for the offline fallback', async () => {
    window.__MAREA_ALTA_DATA__ = { schedule: SCHEDULE, closedDays: CLOSED, menu: MENU };
    global.fetch = jsonResponse();

    const load = await freshLoad();
    await load();

    const cached = JSON.parse(localStorage.getItem('marea_alta_schedule_cache'));
    expect(cached.schedule).toEqual(SCHEDULE);
    expect(cached.menu).toEqual(MENU);
  });

  it('fetches from the API on later refreshes, not the seed again', async () => {
    window.__MAREA_ALTA_DATA__ = { schedule: SCHEDULE, closedDays: CLOSED, menu: MENU };
    const fetchMock = jsonResponse();
    global.fetch = fetchMock;

    const load = await freshLoad();
    await load();
    // Stands in for the hourly timer and the Refresh button.
    const refreshed = await load();

    // The refresh fetches the schedule, the closures and the menu. The seeded
    // first paint fetches nothing.
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(refreshed.schedule).toEqual(SCHEDULE);
    expect(refreshed.menu).toEqual(MENU);
  });

  it('ignores an empty payload rather than showing a blank schedule', async () => {
    window.__MAREA_ALTA_DATA__ = { schedule: [], closedDays: [] };
    global.fetch = jsonResponse();

    const load = await freshLoad();
    const result = await load();

    expect(result.schedule).toEqual(SCHEDULE);
  });

  it('falls back to the API when the page was served without a payload', async () => {
    const fetchMock = jsonResponse();
    global.fetch = fetchMock;

    const load = await freshLoad();
    const result = await load();

    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(result.schedule).toEqual(SCHEDULE);
    expect(result.menu).toEqual(MENU);
  });

  it('survives a seed written before the menu existed', async () => {
    // A cached payload from a release that had no menu: the section renders its
    // empty state rather than crashing on `undefined.map`.
    window.__MAREA_ALTA_DATA__ = { schedule: SCHEDULE, closedDays: CLOSED };
    global.fetch = jsonResponse();

    const load = await freshLoad();
    const result = await load();

    expect(result.menu).toEqual([]);
  });
});

describe('load() and closures that have passed', () => {
  beforeEach(() => {
    localStorage.clear();
    delete window.__MAREA_ALTA_DATA__;
  });

  afterEach(() => {
    vi.restoreAllMocks();
    delete window.__MAREA_ALTA_DATA__;
  });

  it('drops them from the server-rendered payload', async () => {
    window.__MAREA_ALTA_DATA__ = { schedule: SCHEDULE, closedDays: [PAST, ...CLOSED], menu: MENU };
    global.fetch = jsonResponse();

    const load = await freshLoad();
    const result = await load();

    expect(result.closedDays).toEqual(CLOSED);
  });

  it('drops them from a cache written before the API filtered them', async () => {
    // What a returning visitor actually has: a payload stored weeks ago.
    localStorage.setItem(
      'marea_alta_schedule_cache',
      JSON.stringify({ schedule: SCHEDULE, closedDays: [PAST, ...CLOSED], menu: MENU }),
    );
    global.fetch = vi.fn(async () => ({ ok: false, status: 500 }));

    const load = await freshLoad();
    const result = await load();

    expect(result.closedDays).toEqual(CLOSED);
    expect(result.error).toBeTruthy();
  });

  it('still shows the menu when the backend is unreachable', async () => {
    // The cache is what a bar in Montañita has when the power goes out; a blank
    // menu section is the one thing a visitor cannot work around.
    localStorage.setItem(
      'marea_alta_schedule_cache',
      JSON.stringify({ schedule: SCHEDULE, closedDays: CLOSED, menu: MENU }),
    );
    global.fetch = vi.fn(async () => ({ ok: false, status: 500 }));

    const load = await freshLoad();
    const result = await load();

    expect(result.menu).toEqual(MENU);
  });
});