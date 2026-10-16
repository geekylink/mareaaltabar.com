// API client for the Marea Alta backend.
//
// The API returns both languages for every string. The caller picks the field
// matching the visitor's language, so switching language needs no extra request.
//
// The first load uses the payload the backend embedded in the HTML (it renders
// the same schedule and menu server-side, for crawlers — see
// backend/app/ssr.py). That saves a round trip and the loading state on first
// paint. Anything after that — the hourly refresh, the Refresh button — goes to
// the API, so the schedule and menu stay live and an admin edit still shows up
// without a reload.

const CACHE_KEY = 'marea_alta_schedule_cache';

// The bar's own timezone. Ecuador is UTC-5 year-round, and both the schedule and
// every closure are keyed to the day it is *there* — the mirror of
// `BAR_UTC_OFFSET` in backend/app/ssr.py.
const BAR_TZ = 'America/Guayaquil';

// Which day it is at the bar: `{ day, date }`, `day` 0 = Sunday to match the
// database, `date` as YYYY-MM-DD to match a closure row.
//
// Both fields come from one read of the bar's calendar, and the weekday is
// derived from that, so no visitor timezone can shift either one. `now` is
// injectable purely so tests can pin a date, as `ssr.bar_today` is.
export function barToday(now = new Date()) {
  const parts = {};
  for (const part of new Intl.DateTimeFormat('en-US', { timeZone: BAR_TZ }).formatToParts(now)) {
    parts[part.type] = part.value;
  }
  // `en-US` hands back an unpadded month and day, and a closure row is compared
  // as a string, so the padding has to be explicit.
  const pad = (n) => String(n).padStart(2, '0');
  const date = `${parts.year}-${pad(parts.month)}-${pad(parts.day)}`;
  const day = new Date(Date.UTC(parts.year, parts.month - 1, parts.day)).getUTCDay();
  return { day, date };
}

// Is the bar shut today because of a one-off closure (a holiday, a private
// booking)? Distinct from the weekly `is_closed` flag, which says nothing about
// any particular date.
export function isClosedOn(closedDays, isoDate) {
  return closedDays.some((d) => d?.date === isoDate);
}

// The closures still to come. `GET /api/closed-days` already filters, and so
// does this: the localStorage cache and the server-rendered seed both outlive
// the date they were fetched on.
export function upcomingClosedDays(closedDays, isoDate) {
  return closedDays.filter((d) => d?.date >= isoDate);
}

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
  // The bar's date, not the visitor's: a closure is a fact about Montañita.
  const today = barToday().date;

  // Server-rendered payload, used once. `seeded` keeps the hourly refresh from
  // replaying it after the first hour.
  const seed = seededData();
  if (seed && !seeded && Array.isArray(seed.schedule) && seed.schedule.length > 0) {
    seeded = true;
    const result = {
      schedule: seed.schedule,
      closedDays: upcomingClosedDays(seed.closedDays || [], today),
      menu: seed.menu || [],
      error: null,
    };
    setCache(result);
    return result;
  }
  try {
    const [schedule, closedDays, menu] = await Promise.all([
      fetchJSON('/api/schedule'),
      fetchJSON('/api/closed-days'),
      fetchJSON('/api/menu'),
    ]);
    const result = {
      schedule,
      closedDays: upcomingClosedDays(closedDays, today),
      menu: (menu && menu.categories) || [],
      error: null,
    };
    setCache(result);
    return result;
  } catch (err) {
    const cached = getCache();
    if (cached) {
      return {
        ...cached,
        closedDays: upcomingClosedDays(cached.closedDays || [], today),
        menu: cached.menu || [],
        error: 'Backend unreachable, showing cached data',
      };
    }
    return { schedule: [], closedDays: [], menu: [], error: 'Failed to load the schedule' };
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

// A stored price as displayed: "2.50" -> "$2.50". The amount is whatever the bar
// typed, so nothing here rounds, and a blank price (an unpriced drink) renders
// as nothing rather than "$0.00". Mirrors `format_price` in backend/app/ssr.py.
export function formatPrice(price) {
  const text = String(price ?? '').trim();
  return text ? `$${text}` : '';
}