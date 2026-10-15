// API client for the Marea Alta backend.
// Fetches events, hours, and closed days from the backend.
// Falls back to localStorage cache if the backend is unreachable.

const CACHE_KEY_EVENTS = 'marea_alta_events_cache';
const CACHE_KEY_HOURS = 'marea_alta_hours_cache';
const CACHE_KEY_CLOSED_DAYS = 'marea_alta_closed_days_cache';

function getCache(key) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function setCache(key, data) {
  try {
    localStorage.setItem(key, JSON.stringify(data));
  } catch {}
}

async function fetchJSON(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function fetchEvents() {
  try {
    const events = await fetchJSON('/api/events');
    setCache(CACHE_KEY_EVENTS, events);
    return { data: events, source: 'api', error: null };
  } catch (err) {
    const cached = getCache(CACHE_KEY_EVENTS);
    if (cached) {
      return { data: cached, source: 'cache', error: 'Backend unreachable, showing cached data' };
    }
    return { data: [], source: 'none', error: 'Failed to load events and no cache available' };
  }
}

export async function fetchHours() {
  try {
    const hours = await fetchJSON('/api/hours');
    setCache(CACHE_KEY_HOURS, hours);
    return { data: hours, source: 'api', error: null };
  } catch (err) {
    const cached = getCache(CACHE_KEY_HOURS);
    if (cached) {
      return { data: cached, source: 'cache', error: 'Backend unreachable, showing cached data' };
    }
    return { data: [], source: 'none', error: 'Failed to load hours and no cache available' };
  }
}

export async function fetchClosedDays() {
  try {
    const days = await fetchJSON('/api/closed-days');
    setCache(CACHE_KEY_CLOSED_DAYS, days);
    return { data: days, source: 'api', error: null };
  } catch (err) {
    const cached = getCache(CACHE_KEY_CLOSED_DAYS);
    if (cached) {
      return { data: cached, source: 'cache', error: 'Backend unreachable, showing cached data' };
    }
    return { data: [], source: 'none', error: 'Failed to load closed days and no cache available' };
  }
}

export async function fetchAll() {
  const [events, hours, closedDays] = await Promise.all([
    fetchEvents(),
    fetchHours(),
    fetchClosedDays(),
  ]);
  return { events, hours, closedDays };
}
