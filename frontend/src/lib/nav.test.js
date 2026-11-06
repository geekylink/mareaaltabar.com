import { describe, it, expect, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/svelte';
import { tick } from 'svelte';
import Nav from './Nav.svelte';
import { locale } from './i18n.js';

describe('Nav.svelte', () => {
  afterEach(() => {
    cleanup();
    locale.set('en');
  });

  it('links to the in-page sections on the homepage', () => {
    render(Nav);
    expect(screen.getByText('Marea Alta').closest('a').getAttribute('href')).toBe('#top');
    expect(screen.getByText('Surf').closest('a').getAttribute('href')).toBe('#surf');
    expect(screen.getByText('Menu').closest('a').getAttribute('href')).toBe('#menu');
  });

  it('links back to the homepage from another document', () => {
    render(Nav, { props: { home: false } });
    expect(screen.getByText('Surf').closest('a').getAttribute('href')).toBe('/#surf');
    expect(screen.getByText('Visit').closest('a').getAttribute('href')).toBe('/#visit');
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
});
