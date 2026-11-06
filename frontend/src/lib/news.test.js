import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/svelte';
import { tick } from 'svelte';
import Blog from './Blog.svelte';
import BlogPost from './BlogPost.svelte';
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

afterEach(() => {
  cleanup();
  locale.set('en');
});

describe('Blog.svelte', () => {
  it('renders each post with its date, summary and article link', () => {
    render(Blog, { props: { posts: [POST], lang: 'en' } });

    expect(screen.getByRole('heading', { name: 'News' })).toBeTruthy();
    expect(screen.getByRole('heading', { name: 'The new site is live' })).toBeTruthy();
    expect(screen.getByText('Surf, parties and the menu in one place.')).toBeTruthy();
    expect(screen.getByText('The new site is live').closest('a').getAttribute('href')).toBe(
      '/news/website-launch'
    );
  });

  it('says there is no news yet', () => {
    render(Blog, { props: { posts: [], lang: 'en' } });
    expect(screen.getByText('No news yet. Check back soon.')).toBeTruthy();
  });

  it('switches language without remounting', async () => {
    render(Blog, { props: { posts: [POST], lang: 'es' } });
    expect(screen.getByText('El nuevo sitio está en línea')).toBeTruthy();

    locale.set('es');
    await tick();

    expect(screen.getByText('El nuevo sitio está en línea')).toBeTruthy();
    expect(screen.getByText('Surf, fiestas y el menú en un solo lugar.')).toBeTruthy();
  });
});

describe('BlogPost.svelte', () => {
  it('renders the article body as separate paragraphs', () => {
    const { container } = render(BlogPost, { props: { post: POST, lang: 'en' } });

    expect(screen.getByRole('heading', { name: 'The new site is live' })).toBeTruthy();
    expect(screen.getByText('First paragraph.')).toBeTruthy();
    expect(screen.getByText('Second paragraph.')).toBeTruthy();
    expect(container.querySelectorAll('.body p')).toHaveLength(2);
    expect(screen.getAllByText('All news')[0].closest('a').getAttribute('href')).toBe('/news');
  });

  it('uses the Spanish title and body after a language switch', async () => {
    render(BlogPost, { props: { post: POST, lang: 'es' } });

    expect(screen.getByRole('heading', { name: 'El nuevo sitio está en línea' })).toBeTruthy();
    expect(screen.getByText('Primer párrafo.')).toBeTruthy();
    expect(screen.getByText('Segundo párrafo.')).toBeTruthy();

    locale.set('es');
    await tick();
    expect(screen.getByText('Segundo párrafo.')).toBeTruthy();
  });

  it('shows an uploaded image when the post has one', () => {
    render(BlogPost, {
      props: { post: { ...POST, image_url: '/uploads/launch.webp' }, lang: 'en' },
    });
    expect(screen.getByRole('img', { name: 'The new site is live' })).toBeTruthy();
  });
});
