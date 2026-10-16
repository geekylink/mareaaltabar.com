import { describe, it, expect, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/svelte';
import Menu from './Menu.svelte';
import { locale } from './i18n.js';
import { formatPrice } from './api.js';

// The menu is database-driven: everything here arrives from `GET /api/menu`, so
// these tests are about what the component does with it — prices, promos,
// ingredients, language fallback — rather than about any hardcoded content.
const CATEGORY = (over = {}) => ({
  id: 1, slug: 'cocteles', name_en: 'Cocktails', name_es: 'Cócteles', ...over,
});

const CUBA = {
  id: 10, category_id: 1,
  name_en: 'Cuba Libre', name_es: 'Cuba Libre',
  description_en: '', description_es: '',
  ingredients_en: 'Rum, Coca-Cola, Lime juice, Ice',
  ingredients_es: 'Ron, Coca-Cola, Jugo de limón, Hielo',
  price: '4.00', is_available: true, promos: [],
};

function renderMenu(props = {}) {
  return render(Menu, {
    props: { categories: [CATEGORY({ items: [CUBA] })], lang: 'en', ...props },
  });
}

describe('Menu.svelte', () => {
  afterEach(() => {
    cleanup();
    locale.set('en');
  });

  it('shows a drink with its price', () => {
    renderMenu();
    expect(screen.getByText('Cuba Libre')).toBeTruthy();
    expect(screen.getByText('$4.00')).toBeTruthy();
    expect(screen.getByText('Cocktails')).toBeTruthy();
  });

  it('lists a cocktail with its ingredients', () => {
    renderMenu();
    expect(screen.getByText('Rum, Coca-Cola, Lime juice, Ice')).toBeTruthy();
    expect(screen.getByText('Ingredients')).toBeTruthy();
  });

  it('renders every promo beneath the price', () => {
    renderMenu({
      categories: [CATEGORY({ items: [{
        ...CUBA,
        promos: [
          { id: 1, label_en: '2x1 Tuesdays', label_es: '2x1 martes' },
          { id: 2, label_en: 'Bucket $18.00', label_es: 'Caneca $18.00' },
        ],
      }] })],
    });
    expect(screen.getByText('Promo: 2x1 Tuesdays')).toBeTruthy();
    expect(screen.getByText('Promo: Bucket $18.00')).toBeTruthy();
  });

  it('switches language without a remount', async () => {
    // `lang` is owned by the page (App / MenuPage), which is what lets one
    // fetched payload serve both languages — so the switch is a prop update.
    const { rerender } = renderMenu({
      categories: [CATEGORY({
        items: [{ ...CUBA, promos: [{ id: 1, label_en: '6x $7.00', label_es: '6 por $7.00' }] }],
      })],
    });
    expect(screen.getByText('Rum, Coca-Cola, Lime juice, Ice')).toBeTruthy();

    await rerender({ lang: 'es' });

    expect(screen.getByText('Ron, Coca-Cola, Jugo de limón, Hielo')).toBeTruthy();
    expect(screen.getByText('Cócteles')).toBeTruthy();
    expect(screen.getByText('Promo: 6 por $7.00')).toBeTruthy();
    expect(screen.queryByText('Rum, Coca-Cola, Lime juice, Ice')).toBeNull();
  });

  it('falls back to English when a Spanish name is blank', async () => {
    // A half-translated menu still has to render, like the schedule does.
    renderMenu({
      categories: [CATEGORY({ name_es: '', items: [{ ...CUBA, ingredients_es: '   ' }] })],
      lang: 'es',
    });
    expect(screen.getByText('Cuba Libre')).toBeTruthy();
    expect(screen.getByText('Rum, Coca-Cola, Lime juice, Ice')).toBeTruthy();
  });

  it('anchors each category on its slug', () => {
    renderMenu();
    expect(document.getElementById('cocteles')).toBeTruthy();
  });

  it('shows a description when one has been written', () => {
    renderMenu({
      categories: [CATEGORY({ items: [{
        ...CUBA,
        description_en: 'Rum, cola and too much lime.',
        description_es: 'Ron, cola y demasiado limón.',
      }] })],
    });
    expect(screen.getByText('Rum, cola and too much lime.')).toBeTruthy();
  });

  it('says the menu is being updated when there is nothing to show', () => {
    renderMenu({ categories: [], loading: false });
    expect(screen.getByText(/menu is being updated/)).toBeTruthy();
  });

  it('claims nothing while the menu is still loading', () => {
    // The "being updated" line is a lie for the second a fetch takes.
    renderMenu({ categories: [], loading: true });
    expect(screen.queryByText(/menu is being updated/)).toBeNull();
  });
});

describe('formatPrice()', () => {
  it('renders a stored amount as a price', () => {
    expect(formatPrice('2.50')).toBe('$2.50');
    expect(formatPrice('0.25')).toBe('$0.25');
  });

  it('renders an unpriced drink as nothing rather than free', () => {
    // Mirrors format_price in backend/app/ssr.py.
    expect(formatPrice('')).toBe('');
    expect(formatPrice(null)).toBe('');
    expect(formatPrice(undefined)).toBe('');
  });
});