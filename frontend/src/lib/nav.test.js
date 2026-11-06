import { describe, it, expect, afterEach } from 'vitest';
import { render, screen, cleanup, fireEvent } from '@testing-library/svelte';
import { tick } from 'svelte';
import Nav from './Nav.svelte';
import { locale } from './i18n.js';
import { setTheme, THEME_KEY } from './theme.js';

describe('Nav.svelte', () => {
  afterEach(() => {
    cleanup();
    locale.set('en');
    setTheme('light');
    localStorage.removeItem(THEME_KEY);
  });

  it('links to the in-page sections on the homepage', () => {
    render(Nav);
    expect(screen.getByText('Marea Alta').closest('a').getAttribute('href')).toBe('#top');
    expect(screen.getByText('Surf').closest('a').getAttribute('href')).toBe('#surf');
    expect(screen.getByText('Menu').closest('a').getAttribute('href')).toBe('#menu');
    expect(screen.getByText('News').closest('a').getAttribute('href')).toBe('/news');
  });

  it('links back to the homepage from another document', () => {
    render(Nav, { props: { home: false } });
    expect(screen.getByText('Surf').closest('a').getAttribute('href')).toBe('/#surf');
    expect(screen.getByText('Visit').closest('a').getAttribute('href')).toBe('/#visit');
    expect(screen.getByText('News').closest('a').getAttribute('href')).toBe('/news');
  });

  it('renders only the links it is given', () => {
    render(Nav, { props: { home: false, links: ['surf', 'party', 'visit'] } });
    expect(screen.getByText('Surf')).toBeTruthy();
    expect(screen.queryByText('Menu')).toBeNull();
    expect(screen.queryByText('Contact')).toBeNull();
  });

  it('translates its links when the visitor switches language', async () => {
    render(Nav);
    expect(screen.getByText('Party')).toBeTruthy();

    locale.set('es');
    await tick();

    expect(screen.getByText('Fiestas')).toBeTruthy();
    expect(screen.queryByText('Party')).toBeNull();
  });

  it('toggles the theme and remembers the choice', async () => {
    render(Nav);

    const dark = screen.getByRole('button', { name: 'Switch to dark mode' });
    await fireEvent.click(dark);

    expect(document.documentElement.dataset.theme).toBe('dark');
    expect(localStorage.getItem(THEME_KEY)).toBe('dark');
    expect(screen.getByRole('button', { name: 'Switch to light mode' })).toBeTruthy();

    await fireEvent.click(screen.getByRole('button', { name: 'Switch to light mode' }));
    expect(document.documentElement.dataset.theme).toBe('light');
    expect(localStorage.getItem(THEME_KEY)).toBe('light');
  });

  it('translates the theme toggle', async () => {
    render(Nav);
    locale.set('es');
    await tick();

    expect(screen.getByRole('button', { name: 'Cambiar a modo oscuro' })).toBeTruthy();
  });
});
