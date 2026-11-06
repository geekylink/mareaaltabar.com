import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, cleanup, waitFor } from '@testing-library/svelte';
import { tick } from 'svelte';
import App from './App.svelte';
import { locale } from './lib/i18n.js';
import { barToday } from './lib/api.js';

const SCHEDULE = [
  { day: 0, title_en: 'Latin Night', title_es: 'Noche Latina', note_en: 'Salsa all night.', note_es: 'Salsa toda la noche.', open_time: '16:00', close_time: '02:00', is_closed: false },
  { day: 1, title_en: 'Singles Night', title_es: 'Noche de Solteros', note_en: 'Mingle.', note_es: 'Conoce gente.', open_time: '16:00', close_time: '04:00', is_closed: false },
  { day: 2, title_en: 'Closed', title_es: 'Cerrado', note_en: '', note_es: '', open_time: '', close_time: '', is_closed: true },
];

// A full open week, so "today" is always a day the schedule has something to
// say — the bug is that an open weekday plus a closure for today must read shut.
const WEEK = [
  'Latin Night', 'Singles Night', 'Open Mic', 'Reggae Night',
  'Full Moon Party', 'Live Music', 'Sunset Sessions',
].map((title, day) => ({
  day,
  title_en: title,
  title_es: `${title} ES`,
  note_en: `${title} note.`,
  note_es: `${title} nota.`,
  open_time: '16:00',
  close_time: '04:00',
  is_closed: false,
}));

// The drinks menu, in the shape `GET /api/menu` returns.
const MENU = [
  {
    id: 1, slug: 'cerveza', name_en: 'Beer', name_es: 'Cerveza',
    items: [
      {
        id: 1, category_id: 1, name_en: 'Pilsener Can', name_es: 'Pilsener Lata',
        price: '1.50', is_available: true,
        promos: [{ id: 1, label_en: '6x $7.00', label_es: '6 por $7.00' }],
      },
    ],
  },
  {
    id: 2, slug: 'cocteles', name_en: 'Cocktails', name_es: 'Cócteles',
    items: [
      {
        id: 2, category_id: 2, name_en: 'Cuba Libre', name_es: 'Cuba Libre',
        price: '4.00', is_available: true, promos: [],
        ingredients_en: 'Rum, Coca-Cola, Lime juice',
        ingredients_es: 'Ron, Coca-Cola, Jugo de limón',
      },
    ],
  },
];

function mockFetch() {
  return vi.fn(async (url) => {
    const path = String(url);
    if (path.includes('closed-days')) return { ok: true, status: 200, json: async () => [] };
    if (path.includes('/api/notices')) return { ok: true, status: 200, json: async () => [] };
    if (path.includes('/api/special-events')) return { ok: true, status: 200, json: async () => [] };
    if (path.includes('/api/menu')) return { ok: true, status: 200, json: async () => ({ categories: MENU }) };
    return { ok: true, status: 200, json: async () => SCHEDULE };
  });
}

// The backend answers with whatever closures it holds, including today's.
function mockFetchWithClosures(closedDays, schedule = WEEK) {
  return vi.fn(async (url) => {
    const path = String(url);
    const body = path.includes('closed-days')
      ? closedDays
      : path.includes('/api/notices') || path.includes('/api/special-events')
        ? []
        : path.includes('/api/menu')
          ? { categories: MENU }
          : schedule;
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

// The bug: a closure dated today is a fact about the date, and the weekday's own
// `is_closed` flag says nothing about it. An open weekday plus a holiday closure
// used to render tonight's party and "open until late" anyway.
describe('App closed-day handling', () => {
  const { day: todayDay, date: todayIso } = barToday();
  const todaysTitle = WEEK.find((d) => d.day === todayDay).title_en;

  beforeEach(() => {
    locale.set('en');
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it('highlights tonight when nothing has closed the bar today', async () => {
    global.fetch = mockFetchWithClosures([{ id: 1, date: '2030-12-25', reason_en: 'Christmas', reason_es: 'Navidad' }]);
    render(App);

    await waitFor(() => expect(screen.getByText('Tonight')).toBeTruthy());
    // Tonight's card and today's row in the week list.
    expect(screen.getAllByText(todaysTitle)).toHaveLength(2);
    expect(screen.getByText(/Montañita, Ecuador\. 4:00 PM/)).toBeTruthy();
  });

  it('hides tonight’s party when today is a closure', async () => {
    global.fetch = mockFetchWithClosures([{ id: 1, date: todayIso, reason_en: 'Holiday', reason_es: 'Feriado' }]);
    render(App);

    await waitFor(() => expect(screen.getAllByText('Closed today').length).toBeGreaterThan(0));
    expect(screen.queryByText('Tonight')).toBeNull();
    // The party is gone from tonight's row too, not just from the card.
    expect(screen.queryByText(todaysTitle)).toBeNull();
  });

  it('says the bar is shut rather than open until late', async () => {
    global.fetch = mockFetchWithClosures([{ id: 1, date: todayIso, reason_en: 'Holiday', reason_es: 'Feriado' }]);
    render(App);

    await waitFor(() => expect(screen.getAllByText('Closed today').length).toBeGreaterThan(0));
    expect(screen.getByText(/Montañita, Ecuador\. Closed today/)).toBeTruthy();
  });

  it('reads the closure in Spanish too', async () => {
    global.fetch = mockFetchWithClosures([{ id: 1, date: todayIso, reason_en: 'Holiday', reason_es: 'Feriado' }]);
    render(App);
    await waitFor(() => expect(screen.getAllByText('Closed today').length).toBeGreaterThan(0));

    locale.set('es');
    await tick();

    await waitFor(() => expect(screen.queryByText('Closed today')).toBeNull());
    expect(screen.getAllByText('Cerrado hoy').length).toBeGreaterThan(0);
    expect(screen.getByText(/Montañita, Ecuador\. Cerrado hoy/)).toBeTruthy();
  });

  it('lists the closures still to come under their own heading', async () => {
    global.fetch = mockFetchWithClosures([
      { id: 1, date: todayIso, reason_en: 'Holiday', reason_es: 'Feriado' },
      { id: 2, date: '2030-12-25', reason_en: 'Christmas', reason_es: 'Navidad' },
    ]);
    render(App);

    await waitFor(() => expect(screen.getByText('Closed days')).toBeTruthy());
    expect(screen.getByText(/2030-12-25 — Christmas/)).toBeTruthy();
  });
});

// The menu is the flagship ticket and lives on the homepage as its own section.
// Same language-switch hazard as the week list, so same guard.
describe('App menu section', () => {
  beforeEach(() => {
    locale.set('en');
    global.fetch = mockFetch();
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it('renders the categories with their prices', async () => {
    render(App);
    // Wait for content, not the heading: the section renders its heading
    // synchronously while the menu is still in flight.
    await waitFor(() => expect(screen.getByText('Beer')).toBeTruthy());
    expect(screen.queryByText('Cerveza')).toBeNull();
    expect(screen.getByText('$1.50')).toBeTruthy();
  });

  it('shows promos under the price', async () => {
    render(App);
    await waitFor(() => expect(screen.getByText('Promo: 6x $7.00')).toBeTruthy());
  });

  it('lists a cocktail with its ingredients', async () => {
    render(App);
    await waitFor(() => expect(screen.getByText('Cocktails')).toBeTruthy());
    expect(screen.getByText('Cuba Libre')).toBeTruthy();
    expect(screen.getByText('Rum, Coca-Cola, Lime juice')).toBeTruthy();
    expect(screen.getByText('Ingredients')).toBeTruthy();
  });

  it('switches the whole menu to Spanish without a remount', async () => {
    render(App);
    await waitFor(() => expect(screen.getByText('Beer')).toBeTruthy());

    locale.set('es');
    await tick();

    await waitFor(() => expect(screen.getByText('Cerveza')).toBeTruthy());
    expect(screen.queryByText('Beer')).toBeNull();
    expect(screen.getByText('Pilsener Lata')).toBeTruthy();
    expect(screen.getByText('Promo: 6 por $7.00')).toBeTruthy();
    expect(screen.getByText('Ron, Coca-Cola, Jugo de limón')).toBeTruthy();
  });

  it('still shows the menu when the schedule fails to load', async () => {
    // `/api/menu` answering is independent of `/api/schedule`: a visitor who
    // cannot see tonight's party can still see what things cost.
    global.fetch = vi.fn(async (url) => {
      const path = String(url);
      if (path.includes('/api/notices')) return { ok: true, status: 200, json: async () => [] };
      if (path.includes('/api/menu')) return { ok: true, status: 200, json: async () => ({ categories: MENU }) };
      return { ok: false, status: 500 };
    });
    render(App);

    await waitFor(() => expect(screen.getByText('Cuba Libre')).toBeTruthy());
    expect(screen.getByText('$4.00')).toBeTruthy();
  });

  it('renders upcoming dated events alongside the weekly schedule', async () => {
    global.fetch = vi.fn(async (url) => {
      const path = String(url);
      if (path.includes('closed-days')) return { ok: true, status: 200, json: async () => [] };
      if (path.includes('/api/notices')) return { ok: true, status: 200, json: async () => [] };
      if (path.includes('/api/special-events')) {
        return {
          ok: true,
          status: 200,
          json: async () => [{
            id: 1, date: '2030-12-31', title_en: 'Beach party', title_es: 'Fiesta en la playa',
            description_en: 'Bonfire at sunset.', description_es: 'Fogata al atardecer.',
            start_time: '21:00', end_time: '02:00', image_url: '',
          }],
        };
      }
      if (path.includes('/api/menu')) return { ok: true, status: 200, json: async () => ({ categories: MENU }) };
      return { ok: true, status: 200, json: async () => SCHEDULE };
    });
    render(App);

    await waitFor(() => expect(screen.getByText('Beach party')).toBeTruthy());
    expect(screen.getByText('Special events')).toBeTruthy();
    expect(screen.getByText('Tue, Dec 31')).toBeTruthy();
    expect(screen.getByText('9:00 PM - 2:00 AM')).toBeTruthy();
    expect(screen.getByText('Bonfire at sunset.')).toBeTruthy();
  });

  it('links to the standalone menu route', async () => {
    render(App);
    await waitFor(() => expect(screen.getByText('See the menu')).toBeTruthy());
    expect(screen.getByText('See the menu').closest('a').getAttribute('href')).toBe('/menu');
  });
});

describe('App accessibility landmarks', () => {
  beforeEach(() => {
    global.fetch = mockFetch();
    locale.set('en');
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it('starts with a skip link that targets the main landmark', async () => {
    render(App);
    await waitFor(() => expect(document.querySelector('#party-h')).toBeTruthy());
    const skip = screen.getByText('Skip to content').closest('a');
    expect(skip.getAttribute('href')).toBe('#main');
    expect(document.querySelectorAll('main#main')).toHaveLength(1);
    expect(document.querySelector('main#main #party-h')).toBeTruthy();
  });

  it('translates the skip link with the rest of the page', async () => {
    render(App);
    locale.set('es');
    await tick();
    expect(screen.getByText('Saltar al contenido').closest('a').getAttribute('href')).toBe('#main');
  });
});