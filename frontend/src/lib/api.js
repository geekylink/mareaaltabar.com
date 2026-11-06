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
  if (!res.ok) {
    const err = new Error(`API error: ${res.status}`);
    err.status = res.status;
    throw err;
  }
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
      notices: seed.notices || [],
      specialEvents: seed.specialEvents || [],
      error: null,
    };
    setCache(result);
    return result;
  }
  try {
    const [schedule, closedDays, menu, notices, specialEvents] = await Promise.all([
      fetchJSON('/api/schedule'),
      fetchJSON('/api/closed-days'),
      fetchJSON('/api/menu'),
      fetchJSON('/api/notices'),
      fetchJSON('/api/special-events'),
    ]);
    const result = {
      schedule,
      closedDays: upcomingClosedDays(closedDays, today),
      menu: (menu && menu.categories) || [],
      notices: notices || [],
      specialEvents: specialEvents || [],
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
        notices: cached.notices || [],
        specialEvents: cached.specialEvents || [],
        error: 'Backend unreachable, showing cached data',
      };
    }
    return {
      schedule: [],
      closedDays: [],
      menu: [],
      notices: [],
      specialEvents: [],
      error: 'Failed to load the schedule',
    };
  }
}

export { load };

// --- News (ticket #24) ----------------------------------------------------
//
// The news pages have their own document and their own server-rendered seed, so
// they do not share the homepage's schedule cache. `blogSeeded` makes the seed a
// first-paint shortcut only; a language switch re-renders from the same rows,
// and a reload fetches fresh posts.

let blogSeeded = false;

export async function loadNews() {
  const seed = seededData();
  if (seed && !blogSeeded && Array.isArray(seed.blogPosts)) {
    blogSeeded = true;
    return { posts: seed.blogPosts, notices: seed.notices || [] };
  }
  const [posts, notices] = await Promise.all([
    fetchJSON('/api/posts'),
    fetchJSON('/api/notices'),
  ]);
  return { posts, notices: notices || [] };
}

// Returns `{ post: null }` for a post that is not public (404), and throws for a
// real network or server error so the page can distinguish "no such story"
// from "the bar's server is down".
export async function loadPost(slug) {
  const seed = seededData();
  if (seed && !blogSeeded && seed.blogPost && seed.blogPost.slug === slug) {
    blogSeeded = true;
    return { post: seed.blogPost, notices: seed.notices || [] };
  }
  try {
    const [post, notices] = await Promise.all([
      fetchJSON(`/api/posts/${encodeURIComponent(slug)}`),
      fetchJSON('/api/notices'),
    ]);
    return { post, notices: notices || [] };
  } catch (err) {
    if (err.status === 404) return { post: null, notices: [] };
    throw err;
  }
}

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

// A dated event's ISO day as "Fri, Nov 6" (or "vie, 6 nov"). Parsed at noon so
// a daylight-saving change at midnight cannot move it to the day before.
export function formatEventDate(iso, lang) {
  if (!iso) return '';
  const value = new Date(`${iso}T12:00:00`);
  if (Number.isNaN(value.getTime())) return String(iso);
  return value.toLocaleDateString(lang === 'es' ? 'es-EC' : 'en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  });
}

// An event's optional time range, or blank when it has none.
export function formatEventTime(event, lang) {
  const start = formatTime(event?.start_time, lang);
  const end = formatTime(event?.end_time, lang);
  if (start && end) return `${start} - ${end}`;
  return start;
}

// A stored price as displayed: "2.50" -> "$2.50". The amount is whatever the bar
// typed, so nothing here rounds, and a blank price (an unpriced drink) renders
// as nothing rather than "$0.00". Mirrors `format_price` in backend/app/ssr.py.
export function formatPrice(price) {
  const text = String(price ?? '').trim();
  return text ? `$${text}` : '';
}