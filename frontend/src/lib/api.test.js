import { describe, it, expect } from 'vitest';
import { pick, formatTime, formatHours } from './api.js';

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