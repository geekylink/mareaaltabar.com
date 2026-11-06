import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { get } from 'svelte/store';
import { theme, setTheme, toggleTheme, resolveInitialTheme, THEME_KEY } from './theme.js';

describe('theme preference', () => {
  beforeEach(() => {
    localStorage.clear();
    setTheme('light');
  });

  afterEach(() => {
    setTheme('light');
    localStorage.clear();
  });

  it('defaults to the operating system when nothing is stored', () => {
    expect(resolveInitialTheme(null, true)).toBe('dark');
    expect(resolveInitialTheme(null, false)).toBe('light');
  });

  it('lets a saved choice win over the system', () => {
    expect(resolveInitialTheme('light', true)).toBe('light');
    expect(resolveInitialTheme('dark', false)).toBe('dark');
    // An old or corrupted value is not a preference.
    expect(resolveInitialTheme('sepia', true)).toBe('dark');
  });

  it('applies and persists a theme', () => {
    const meta = document.createElement('meta');
    meta.name = 'theme-color';
    meta.content = '#0b3c49';
    document.head.appendChild(meta);

    setTheme('dark');

    expect(get(theme)).toBe('dark');
    expect(document.documentElement.dataset.theme).toBe('dark');
    expect(localStorage.getItem(THEME_KEY)).toBe('dark');
    expect(meta.getAttribute('content')).toBe('#0d1a1d');

    meta.remove();
  });

  it('toggles between light and dark', () => {
    setTheme('light');

    toggleTheme();
    expect(get(theme)).toBe('dark');
    expect(localStorage.getItem(THEME_KEY)).toBe('dark');

    toggleTheme();
    expect(get(theme)).toBe('light');
    expect(localStorage.getItem(THEME_KEY)).toBe('light');
  });

  it('ignores an unknown theme', () => {
    setTheme('sepia');
    expect(get(theme)).toBe('light');
  });
});
