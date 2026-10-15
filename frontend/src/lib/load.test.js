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

function jsonResponse(body) {
  return vi.fn(async (url) => ({
    ok: true,
    status: 200,
    json: async () => (String(url).includes('closed-days') ? CLOSED : SCHEDULE),
  }));
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
    window.__MAREA_ALTA_DATA__ = { schedule: SCHEDULE, closedDays: CLOSED };
    const fetchMock = jsonResponse();
    global.fetch = fetchMock;

    const load = await freshLoad();
    const result = await load();

    expect(result.schedule).toEqual(SCHEDULE);
    expect(result.closedDays).toEqual(CLOSED);
    expect(result.error).toBeNull();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('caches the embedded payload for the offline fallback', async () => {
    window.__MAREA_ALTA_DATA__ = { schedule: SCHEDULE, closedDays: CLOSED };
    global.fetch = jsonResponse();

    const load = await freshLoad();
    await load();

    expect(JSON.parse(localStorage.getItem('marea_alta_schedule_cache')).schedule).toEqual(SCHEDULE);
  });

  it('fetches from the API on later refreshes, not the seed again', async () => {
    window.__MAREA_ALTA_DATA__ = { schedule: SCHEDULE, closedDays: CLOSED };
    const fetchMock = jsonResponse();
    global.fetch = fetchMock;

    const load = await freshLoad();
    await load();
    // Stands in for the hourly timer and the Refresh button.
    const refreshed = await load();

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(refreshed.schedule).toEqual(SCHEDULE);
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

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(result.schedule).toEqual(SCHEDULE);
  });
});