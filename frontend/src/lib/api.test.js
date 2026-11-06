import { describe, it, expect } from 'vitest';
import {
  pick, formatTime, formatHours, formatEventDate, formatEventTime,
  barToday, isClosedOn, upcomingClosedDays,
} from './api.js';

const day = {
  day: 4,
  title_en: 'Open Mic Night',
  title_es: 'Noche de Mic Abierto',
  note_en: 'Bring an instrument.',
  note_es: 'Trae tu instrumento.',
  open_time: '18:00',
  close_time: '03:00',
  is_closed: false,
};

describe('pick', () => {
  it('returns English when the language is English', () => {
    expect(pick(day, 'en', 'title')).toBe('Open Mic Night');
    expect(pick(day, 'en', 'note')).toBe('Bring an instrument.');
  });

  it('returns Spanish when the language is Spanish', () => {
    expect(pick(day, 'es', 'title')).toBe('Noche de Mic Abierto');
    expect(pick(day, 'es', 'note')).toBe('Trae tu instrumento.');
  });

  it('falls back to English when a translation is blank', () => {
    const partial = { ...day, title_es: '   ', note_es: '' };
    expect(pick(partial, 'es', 'title')).toBe('Open Mic Night');
    expect(pick(partial, 'es', 'note')).toBe('Bring an instrument.');
  });

  it('returns an empty string when neither language is set', () => {
    expect(pick({}, 'es', 'title')).toBe('');
    expect(pick(null, 'en', 'note')).toBe('');
  });

  it('treats any non-Spanish locale as English', () => {
    expect(pick(day, 'fr', 'title')).toBe('Open Mic Night');
  });
});

describe('formatTime', () => {
  it('formats 24-hour values for English visitors', () => {
    expect(formatTime('18:00', 'en')).toBe('6:00 PM');
    expect(formatTime('03:00', 'en')).toBe('3:00 AM');
  });

  it('formats 24-hour values for Spanish visitors', () => {
    expect(formatTime('18:00', 'es')).toBe('6:00 p. m.');
    expect(formatTime('03:00', 'es')).toBe('3:00 a. m.');
  });

  it('renders midnight and noon correctly', () => {
    expect(formatTime('00:00', 'en')).toBe('12:00 AM');
    expect(formatTime('12:00', 'en')).toBe('12:00 PM');
  });

  it('returns an empty string for missing or malformed values', () => {
    expect(formatTime('', 'en')).toBe('');
    expect(formatTime(null, 'en')).toBe('');
  });
});

describe('formatHours', () => {
  it('formats an open day', () => {
    expect(formatHours(day, 'en', 'Closed today')).toBe('6:00 PM - 3:00 AM');
  });

  it('shows the closed label when the day is closed', () => {
    expect(formatHours({ ...day, is_closed: true }, 'en', 'Closed today')).toBe('Closed today');
  });

  it('returns an empty string when times are missing but the day is open', () => {
    expect(formatHours({ ...day, open_time: '', close_time: '' }, 'en', 'Closed')).toBe('');
  });
});

describe('formatEventDate', () => {
  it('formats an ISO date for each language', () => {
    expect(formatEventDate('2030-12-31', 'en')).toBe('Tue, Dec 31');
    expect(formatEventDate('2030-12-31', 'es')).toBe('mar, 31 dic');
  });

  it('returns the raw value when the date is malformed', () => {
    expect(formatEventDate('not-a-date', 'en')).toBe('not-a-date');
    expect(formatEventDate('', 'en')).toBe('');
  });
});

describe('formatEventTime', () => {
  it('formats a time range', () => {
    expect(formatEventTime({ start_time: '21:00', end_time: '02:00' }, 'en'))
      .toBe('9:00 PM - 2:00 AM');
  });

  it('returns a single start time, or blank when there is none', () => {
    expect(formatEventTime({ start_time: '21:00', end_time: '' }, 'en')).toBe('9:00 PM');
    expect(formatEventTime({}, 'en')).toBe('');
  });
});

describe('barToday', () => {
  // These mirror the backend's `bar_today`, which owns the same boundary: the
  // bar is UTC-5, so a UTC instant can still be the previous day in Montañita.
  it('uses the bar timezone, not the visitor timezone', () => {
    // 02:30 UTC on Monday is Sunday evening in Montañita.
    expect(barToday(new Date('2026-01-05T02:30:00Z'))).toEqual({ day: 0, date: '2026-01-04' });
  });

  it('rolls over at local midnight, not UTC midnight', () => {
    // 02:30 UTC Tuesday is still Monday there.
    expect(barToday(new Date('2026-01-06T02:30:00Z'))).toEqual({ day: 1, date: '2026-01-05' });
    // 05:30 UTC Tuesday is Tuesday there.
    expect(barToday(new Date('2026-01-06T05:30:00Z'))).toEqual({ day: 2, date: '2026-01-06' });
  });

  it('numbers the days the way the database does, Sunday first', () => {
    const week = ['2026-01-04', '2026-01-05', '2026-01-06', '2026-01-07', '2026-01-08', '2026-01-09', '2026-01-10'];
    expect(week.map((d) => barToday(new Date(`${d}T12:00:00Z`)).day)).toEqual([0, 1, 2, 3, 4, 5, 6]);
  });

  it('returns an ISO date without an argument', () => {
    expect(barToday().date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });
});

describe('isClosedOn', () => {
  const closures = [
    { id: 1, date: '2030-12-25', reason_en: 'Christmas' },
    { id: 2, date: '2031-01-01', reason_en: 'New Year' },
  ];

  it('is true when a closure is dated today', () => {
    expect(isClosedOn(closures, '2030-12-25')).toBe(true);
  });

  it('is false when today is merely another closure', () => {
    expect(isClosedOn(closures, '2031-01-02')).toBe(false);
  });

  it('is false with no closures at all', () => {
    expect(isClosedOn([], '2030-12-25')).toBe(false);
  });

  it('compares the whole date, not a prefix of it', () => {
    expect(isClosedOn(closures, '2030-12-2')).toBe(false);
  });
});

describe('upcomingClosedDays', () => {
  it('drops closures that have passed and keeps the rest in order', () => {
    const closures = [
      { id: 1, date: '2001-12-25' },
      { id: 2, date: '2030-12-25' },
      { id: 3, date: '2031-01-01' },
    ];
    expect(upcomingClosedDays(closures, '2026-06-15').map((d) => d.date)).toEqual([
      '2030-12-25',
      '2031-01-01',
    ]);
  });

  it('keeps a closure dated today, since that is the one that matters', () => {
    expect(upcomingClosedDays([{ id: 1, date: '2026-06-15' }], '2026-06-15')).toHaveLength(1);
  });

  it('drops rows with no usable date rather than rendering them as today', () => {
    expect(upcomingClosedDays([{ id: 1 }, { id: 2, date: '2030-12-25' }], '2026-06-15')).toHaveLength(1);
  });
});