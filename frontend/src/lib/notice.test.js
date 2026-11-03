import { describe, it, expect, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/svelte';
import NoticeBanner from './NoticeBanner.svelte';

const notice = (overrides = {}) => ({
  id: 1,
  message_en: 'Closed tonight for a private party.',
  message_es: 'Cerrado esta noche por una fiesta privada.',
  severity: 'warning',
  ...overrides,
});

afterEach(cleanup);

describe('NoticeBanner', () => {
  it('renders the message in the visitor language', () => {
    render(NoticeBanner, { notices: [notice()], lang: 'es' });
    expect(screen.getByText('Cerrado esta noche por una fiesta privada.')).toBeTruthy();
  });

  it('falls back to English when the Spanish message is blank', () => {
    render(NoticeBanner, { notices: [notice({ message_es: '' })], lang: 'es' });
    expect(screen.getByText('Closed tonight for a private party.')).toBeTruthy();
  });

  it('uses the severity for the class and the ARIA role', () => {
    render(NoticeBanner, { notices: [notice({ severity: 'critical' })], lang: 'en' });
    const banner = screen.getByRole('alert');
    expect(banner.classList.contains('notice-critical')).toBe(true);
  });

  it('treats an unknown severity as info', () => {
    render(NoticeBanner, { notices: [notice({ severity: 'spicy' })], lang: 'en' });
    const banner = screen.getByRole('status');
    expect(banner.classList.contains('notice-info')).toBe(true);
  });

  it('renders nothing when there are no notices', () => {
    const { container } = render(NoticeBanner, { notices: [], lang: 'en' });
    expect(container.querySelector('.notices')).toBeNull();
  });

  it('renders every notice in order', () => {
    render(NoticeBanner, {
      notices: [
        notice({ id: 1, message_en: 'First' }),
        notice({ id: 2, message_en: 'Second' }),
      ],
      lang: 'en',
    });
    const messages = screen.getAllByRole('status').map((el) => el.textContent.trim());
    expect(messages).toEqual(['First', 'Second']);
  });
});
