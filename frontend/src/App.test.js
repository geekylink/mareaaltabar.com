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

function mockFetch() {
  return vi.fn(async (url) => {
    const body = String(url).includes('closed-days') ? [] : SCHEDULE;
    return { ok: true, status: 200, json: async () => body };
  });
}

// The backend answers with whatever closures it holds, including today's.
function mockFetchWithClosures(closedDays, schedule = WEEK) {
  return vi.fn(async (url) => {
    const body = String(url).includes('closed-days') ? closedDays : schedule;
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