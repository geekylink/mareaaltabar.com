import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/svelte';

// NewsPage decides what to fetch from the pathname and then owns the four page
// states (loading, error, not found, article/index). Mock only the two loaders;
// `pick` and the rest of the API client stay real.
vi.mock('./api.js', async (importOriginal) => {
  const actual = await importOriginal();
  return { ...actual, loadNews: vi.fn(), loadPost: vi.fn() };
});

import NewsPage from './NewsPage.svelte';
import { loadNews, loadPost } from './api.js';
import { locale } from './i18n.js';

const POST = {
  id: 1,
  slug: 'website-launch',
  title_en: 'The new site is live',
  title_es: 'El nuevo sitio está en línea',
  excerpt_en: 'Surf, parties and the menu in one place.',
  excerpt_es: 'Surf, fiestas y el menú en un solo lugar.',
  body_en: 'First paragraph.\n\nSecond paragraph.',
  body_es: 'Primer párrafo.\n\nSegundo párrafo.',
  image_url: '',
  published_on: '2026-11-06',
  is_active: true,
  is_live: true,
};

beforeEach(() => {
  window.history.pushState({}, '', '/news');
  vi.mocked(loadNews).mockReset();
  vi.mocked(loadPost).mockReset();
  locale.set('en');
});

afterEach(() => {
  cleanup();
});

describe('NewsPage.svelte', () => {
  it('shows the loading state until the index answers', async () => {
    let resolve;
    loadNews.mockReturnValue(new Promise((done) => { resolve = done; }));

    render(NewsPage);
    expect(screen.getByText('Loading...')).toBeTruthy();

    resolve({ posts: [], notices: [] });
    expect(await screen.findByText('No news yet. Check back soon.')).toBeTruthy();
  });

  it('renders the index from the API', async () => {
    loadNews.mockResolvedValue({ posts: [POST], notices: [] });

    render(NewsPage);

    expect(await screen.findByText('The new site is live')).toBeTruthy();
    expect(loadPost).not.toHaveBeenCalled();
  });

  it('renders one article from the API', async () => {
    window.history.pushState({}, '', '/news/website-launch');
    loadPost.mockResolvedValue({ post: POST, notices: [] });

    render(NewsPage);

    expect(await screen.findByRole('heading', { name: 'The new site is live' })).toBeTruthy();
    expect(loadPost).toHaveBeenCalledWith('website-launch');
    expect(loadNews).not.toHaveBeenCalled();
  });

  it('shows the not-found state for a missing article', async () => {
    window.history.pushState({}, '', '/news/gone');
    loadPost.mockResolvedValue({ post: null, notices: [] });

    render(NewsPage);

    expect(await screen.findByText('That story could not be found.')).toBeTruthy();
    expect(screen.getByText('All news').closest('a').getAttribute('href')).toBe('/news');
  });

  it('shows the error state and retries', async () => {
    loadNews
      .mockRejectedValueOnce(new Error('offline'))
      .mockResolvedValueOnce({ posts: [], notices: [] });

    render(NewsPage);

    expect(await screen.findByText('Could not load the news. Please try again.')).toBeTruthy();
    await fireEvent.click(screen.getByRole('button', { name: 'Try again' }));

    expect(await screen.findByText('No news yet. Check back soon.')).toBeTruthy();
    expect(loadNews).toHaveBeenCalledTimes(2);
  });

  it('renders Spanish copy and updates the document language', async () => {
    locale.set('es');
    loadNews.mockResolvedValue({ posts: [POST], notices: [] });

    render(NewsPage);

    expect(await screen.findByText('El nuevo sitio está en línea')).toBeTruthy();
    expect(document.documentElement.lang).toBe('es');
    expect(screen.queryByText('No news yet. Check back soon.')).toBeNull();
  });
});
