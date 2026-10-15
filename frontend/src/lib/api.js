// API client for the Marea Alta backend.
//
// The API returns both languages for every string. The caller picks the field
// matching the visitor's language, so switching language needs no extra request.
//
// The first load uses the payload the backend embedded in the HTML (it renders
// the same schedule server-side, for crawlers — see backend/app/ssr.py). That
// saves a round trip and the loading state on first paint. Anything after that
// — the hourly refresh, the Refresh button — goes to the API, so the schedule
// stays live and an admin edit still shows up without a reload.

const CACHE_KEY = 'marea_alta_schedule_cache';

function seededData() {
  try {
    return typeof window !== 'undefined' ? window.__MAREA_ALTA_DATA__ : null;
  } catch {
    return null;
  }
}

function getCache() {
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function setCache(data) {
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify(data));
  } catch {
    /* private mode or quota: caching is best-effort */
  }
}

async function fetchJSON(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

let seeded = false;

async function load() {
  // Server-rendered payload, used once. `seeded` keeps the hourly refresh from
  // replaying it after the first hour.
  const seed = seededData();
  if (seed && !seeded && Array.isArray(seed.schedule) && seed.schedule.length > 0) {
    seeded = true;
    setCache(seed);
    return { schedule: seed.schedule, closedDays: seed.closedDays || [], error: null };
  }
  try {
    const [schedule, closedDays] = await Promise.all([
      fetchJSON('/api/schedule'),
      fetchJSON('/api/closed-days'),
    ]);
    setCache({ schedule, closedDays });
    return { schedule, closedDays, error: null };
  } catch (err) {
    const cached = getCache();
    if (cached) {
      return { ...cached, error: 'Backend unreachable, showing cached data' };
    }
    return { schedule: [], closedDays: [], error: 'Failed to load the schedule' };
  }
}

export { load };

// Picks the visitor's language, falling back to English when a translation is blank.
export function pick(day, lang, field) {
  const suffix = lang === 'es' ? '_es' : '_en';
  const value = day?.[`${field}${suffix}`];
  if (value && value.trim()) return value;
  return day?.[`${field}_en`] || '';
}

// Formats a 24-hour "HH:MM" value for display in the visitor's locale.
export function formatTime(hhmm, lang) {
  if (!hhmm) return '';
  const [h, m] = hhmm.split(':');
  const hour = Number(h);
  if (Number.isNaN(hour)) return hhmm;
  const suffix = hour >= 12 ? 'PM' : 'AM';
  const display = lang === 'es' ? (hour >= 12 ? 'p. m.' : 'a. m.') : suffix;
  const base = lang === 'es' ? hour % 12 || 12 : hour % 12 || 12;
  return `${base}:${m} ${display}`;
}

export function formatHours(day, lang, closedLabel) {
  if (!day) return '';
  if (day.is_closed) return closedLabel;
  if (!day.open_time || !day.close_time) return '';
  return `${formatTime(day.open_time, lang)} - ${formatTime(day.close_time, lang)}`;
}