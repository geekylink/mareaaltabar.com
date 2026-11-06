import { describe, it, expect, afterEach, vi } from 'vitest';
import { render, screen, cleanup, fireEvent } from '@testing-library/svelte';
import Calendar from './Calendar.svelte';
import { locale } from './i18n.js';
import { barToday, formatEventDate } from './api.js';

// The calendar is a month view over dated events. These tests pin the initial
// month (the soonest event, not necessarily today), the agenda copy, month
// navigation and the Spanish labels.

const pad = (n) => String(n).padStart(2, '0');

function monthDate(offset, day) {
  const [year, month] = barToday().date.split('-').map(Number);
  const value = new Date(year, month - 1 + offset, day);
  return `${value.getFullYear()}-${pad(value.getMonth() + 1)}-${pad(value.getDate())}`;
}

function monthLabel(offset) {
  const [year, month] = barToday().date.split('-').map(Number);
  return new Date(year, month - 1 + offset, 1).toLocaleDateString('en-US', {
    month: 'long',
    year: 'numeric',
  });
}

function event(id, date, over = {}) {
  return {
    id,
    date,
    title_en: `Event ${id}`,
    title_es: `Evento ${id}`,
    description_en: `Description ${id}`,
    description_es: `Descripción ${id}`,
    start_time: '21:00',
    end_time: '02:00',
    image_url: '',
    ...over,
  };
}

describe('Calendar.svelte', () => {
  afterEach(() => {
    cleanup();
    locale.set('en');
    vi.restoreAllMocks();
  });

  it('starts on the soonest event month and shows its agenda', () => {
    render(Calendar, {
      props: { events: [event(1, monthDate(0, 10), { title_en: 'DJ Sol' })] },
    });

    expect(screen.getByText(monthLabel(0))).toBeTruthy();
    expect(screen.getByText('DJ Sol')).toBeTruthy();
    expect(screen.getByText('9:00 PM - 2:00 AM')).toBeTruthy();
    expect(screen.getByText('Description 1')).toBeTruthy();
  });

  it('shows the selected day and switches when another event day is clicked', async () => {
    const first = monthDate(0, 10);
    const second = monthDate(0, 20);
    render(Calendar, {
      props: {
        events: [
          event(1, first, { title_en: 'First night' }),
          event(2, second, { title_en: 'Second night' }),
        ],
      },
    });

    expect(screen.getByText('First night')).toBeTruthy();
    expect(screen.queryByText('Second night')).toBeNull();

    const day = screen.getByRole('button', {
      name: `${formatEventDate(second, 'en')} — 1`,
    });
    await fireEvent.click(day);

    expect(screen.getByText('Second night')).toBeTruthy();
    expect(screen.queryByText('First night')).toBeNull();
  });

  it('pages to the next month and shows its events', async () => {
    render(Calendar, {
      props: {
        events: [
          event(1, monthDate(0, 10), { title_en: 'This month' }),
          event(2, monthDate(1, 12), { title_en: 'Next month' }),
        ],
      },
    });

    expect(screen.getByText('This month')).toBeTruthy();
    await fireEvent.click(screen.getByRole('button', { name: 'Next month' }));

    expect(screen.getByText(monthLabel(1))).toBeTruthy();
    expect(screen.getByText('Next month')).toBeTruthy();
    expect(screen.queryByText('This month')).toBeNull();
  });

  it('does not page into the past before the current month', () => {
    render(Calendar, { props: { events: [event(1, monthDate(0, 10))] } });
    expect(screen.getByRole('button', { name: 'Previous month' }).disabled).toBe(true);
  });

  it('shows an empty note for a month without events', async () => {
    render(Calendar, { props: { events: [event(1, monthDate(0, 10))] } });
    await fireEvent.click(screen.getByRole('button', { name: 'Next month' }));

    expect(screen.getByText('No events this month.')).toBeTruthy();
  });

  it('switches to Spanish', () => {
    locale.set('es');
    render(Calendar, {
      props: {
        events: [event(1, monthDate(0, 10), { title_en: 'DJ Sol', title_es: 'DJ Sol' })],
      },
    });

    expect(screen.getByRole('button', { name: 'Mes siguiente' })).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Mes anterior' }).disabled).toBe(true);
    expect(screen.getByText('9:00 PM - 2:00 AM')).toBeTruthy();
  });
});
