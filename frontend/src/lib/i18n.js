import { writable, derived } from 'svelte/store';
import en from '../content/en.js';
import es from '../content/es.js';

// To add a language: create src/content/xx.js and add it here.
export const LANGS = [
  { code: 'en', label: 'English', content: en },
  { code: 'es', label: 'Español', content: es },
];

// Missing keys in a translation fall back to English.
const merge = (base, over) => {
  if (over === undefined) return base;
  if (Array.isArray(base) || base === null || typeof base !== 'object') return over;
  const out = { ...base };
  for (const k in over) out[k] = merge(base[k], over[k]);
  return out;
};

const initial = () => {
  try {
    const saved = localStorage.getItem('lang');
    if (LANGS.some((l) => l.code === saved)) return saved;
  } catch {}
  return (navigator.language || 'en').toLowerCase().startsWith('es') ? 'es' : 'en';
};

export const locale = writable(initial());
locale.subscribe((v) => { try { localStorage.setItem('lang', v); } catch {} });

export const t = derived(locale, (l) => merge(en, LANGS.find((x) => x.code === l).content));

// fmt('Hi {name}', { name: 'Ana' }) -> 'Hi Ana'
export const fmt = (s, v = {}) => s.replace(/\{(\w+)\}/g, (m, k) => (k in v ? v[k] : m));
