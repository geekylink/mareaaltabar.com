import { describe, it, expect, afterEach, beforeEach, vi } from 'vitest';
import { render, screen, cleanup, waitFor } from '@testing-library/svelte';
import Surf from './Surf.svelte';
import { locale } from './i18n.js';

// The widget is same-origin now (#34): the backend proxies and caches
// Open-Meteo, so the browser must never call a third party itself.
const REPORT = {
  wave: 1.2,
  period: 12.5,
  direction: 225,
  tide: 0.62,
  rising: true,
  turns: [
    { type: 'High', time: '06:30', past: true },
    { type: 'Low', time: '12:45', past: false },
  ],
  sunrise: '06:21',
  sunset: '18:40',
  wind: 9.4,
  wind_direction: 200,
  temperature: 26.3,
  observed_at: '2026-01-06T08:30:00-05:00',
};

describe('Surf.svelte', () => {
  beforeEach(() => {
    global.fetch = vi.fn(async () => ({
      ok: true,
      status: 200,
      json: async () => REPORT,
    }));
  });

  afterEach(() => {
    cleanup();
    locale.set('en');
    vi.restoreAllMocks();
  });

  it('reads the report from the same-origin API', async () => {
    render(Surf);
    await waitFor(() => expect(document.body.textContent).toContain('1.2'));

    const urls = global.fetch.mock.calls.map(([url]) => String(url));
    expect(urls).toEqual(['/api/surf']);
  });

  it('renders the waves, tide turns, sun and wind', async () => {
    render(Surf);

    await waitFor(() => expect(document.body.textContent).toContain('13s period'));
    expect(screen.getByText('High')).toBeTruthy();
    expect(screen.getByText('Low')).toBeTruthy();
    expect(document.body.textContent).toContain('6:30 AM');
    expect(document.body.textContent).toContain('6:40 PM');
    expect(document.body.textContent).toContain('26');
  });

  it('shows the retry state instead of a blank widget when the API fails', async () => {
    global.fetch = vi.fn(async () => ({ ok: false, status: 502, json: async () => ({}) }));

    render(Surf);

    await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy());
    expect(screen.getByRole('button')).toBeTruthy();
  });
});
