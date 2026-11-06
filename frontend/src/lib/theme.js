import { writable } from 'svelte/store';

// The visitor's colour preference. The same key is read by the small inline
// script the backend puts in the document head, so the saved theme is applied
// before the first paint rather than after the app mounts.
export const THEME_KEY = 'theme';
const THEMES = ['light', 'dark'];

function readStored() {
  try {
    const value = localStorage.getItem(THEME_KEY);
    return THEMES.includes(value) ? value : null;
  } catch {
    return null;
  }
}

function systemTheme() {
  try {
    return window.matchMedia?.('(prefers-color-scheme: dark)')?.matches ? 'dark' : 'light';
  } catch {
    return 'light';
  }
}

export function resolveInitialTheme(stored, prefersDark) {
  return THEMES.includes(stored) ? stored : prefersDark ? 'dark' : 'light';
}

function initial() {
  return resolveInitialTheme(readStored(), systemTheme() === 'dark');
}

export const theme = writable(initial());

export function applyTheme(value) {
  if (typeof document === 'undefined') return;
  document.documentElement.dataset.theme = value;
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.setAttribute('content', value === 'dark' ? '#0d1a1d' : '#0b3c49');
}

export function setTheme(value) {
  if (!THEMES.includes(value)) return;
  try {
    localStorage.setItem(THEME_KEY, value);
  } catch {}
  theme.set(value);
}

export function toggleTheme() {
  theme.update((value) => {
    const next = value === 'dark' ? 'light' : 'dark';
    try {
      localStorage.setItem(THEME_KEY, next);
    } catch {}
    return next;
  });
}

theme.subscribe(applyTheme);

// A visitor who has never pressed the toggle keeps following the operating
// system while the page is open. Once a choice is stored, it wins.
if (typeof window !== 'undefined' && window.matchMedia) {
  const query = window.matchMedia('(prefers-color-scheme: dark)');
  query.addEventListener?.('change', (event) => {
    if (readStored() === null) theme.set(event.matches ? 'dark' : 'light');
  });
}
