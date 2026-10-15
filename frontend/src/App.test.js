import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, cleanup, waitFor } from '@testing-library/svelte';
import { tick } from 'svelte';
import App from './App.svelte';
import { locale } from './lib/i18n.js';

const SCHEDULE = [
  { day: 0, title_en: 'Latin Night', title_es: 'Noche Latina', note_en: 'Salsa all night.', note_es: 'Salsa toda la noche.', open_time: '16:00', close_time: '02:00', is_closed: false },
  { day: 1, title_en: 'Singles Night', title_es: 'Noche de Solteros', note_en: 'Mingle.', note_es: 'Conoce gente.', open_time: '16:00', close_time: '04:00', is_closed: false },
  { day: 2, title_en: 'Closed', title_es: 'Cerrado', note_en: '', note_es: '', open_time: '', close_time: '', is_closed: true },
];

function mockFetch() {
  return vi.fn(async (url) => {
    const body = String(url).includes('closed-days') ? [] : SCHEDULE;
    return { ok: true, status: 200, json: async () => body };
  });
}

describe('App language switching', () => {
  beforeEach(() => {
    global.fetch = mockFetch();
    locale.set('en');
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it('renders the week list from the API', async () => {
    render(App);
    await waitFor(() => expect(screen.getByText('Latin Night')).toBeTruthy());
    expect(screen.getByText('Singles Night')).toBeTruthy();
  });

  // Regression: the week list used to call pick() through a local wrapper
  // function, which hid the `lang` dependency from Svelte's compiler. Changing
  // the language left English text on screen until a full page refresh.
  it('switches the week list to Spanish without a remount', async () => {
    render(App);
    await waitFor(() => expect(screen.getByText('Latin Night')).toBeTruthy());

    locale.set('es');
    await tick();

    await waitFor(() => expect(screen.getByText('Noche Latina')).toBeTruthy());
    expect(screen.queryByText('Latin Night')).toBeNull();
    expect(screen.getByText('Noche de Solteros')).toBeTruthy();
  });

  it('switches back to English without a remount', async () => {
    render(App);
    await waitFor(() => expect(screen.getByText('Latin Night')).toBeTruthy());

    locale.set('es');
    await tick();
    await waitFor(() => expect(screen.getByText('Noche Latina')).toBeTruthy());

    locale.set('en');
    await tick();
    await waitFor(() => expect(screen.getByText('Latin Night')).toBeTruthy());
  });

  it('switches the day names along with the party titles', async () => {
    render(App);
    await waitFor(() => expect(screen.getByText('Latin Night')).toBeTruthy());
    expect(screen.getByText('Sunday')).toBeTruthy();

    locale.set('es');
    await tick();

    await waitFor(() => expect(screen.getByText('Domingo')).toBeTruthy());
    expect(screen.queryByText('Sunday')).toBeNull();
  });

  it('keeps a closed day closed in both languages', async () => {
    render(App);
    // The label appears twice per closed row (title and time), so use *AllBy*.
    await waitFor(() => expect(screen.getAllByText('Closed today').length).toBeGreaterThan(0));
    expect(screen.queryByText('Cerrado hoy')).toBeNull();

    locale.set('es');
    await tick();

    await waitFor(() => expect(screen.getAllByText('Cerrado hoy').length).toBeGreaterThan(0));
    expect(screen.queryByText('Closed today')).toBeNull();
  });

  it('does not refetch when the language changes', async () => {
    render(App);
    await waitFor(() => expect(screen.getByText('Latin Night')).toBeTruthy());
    const callsAfterLoad = global.fetch.mock.calls.length;

    locale.set('es');
    await tick();

    expect(global.fetch.mock.calls.length).toBe(callsAfterLoad);
  });
});