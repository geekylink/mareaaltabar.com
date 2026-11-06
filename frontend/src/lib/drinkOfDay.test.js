import { describe, it, expect, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/svelte';
import DrinkOfDay from './DrinkOfDay.svelte';
import { locale } from './i18n.js';

const CATEGORY = {
  id: 1,
  slug: 'cocteles',
  name_en: 'Cocktails',
  name_es: 'Cócteles',
  items: [
    {
      id: 10,
      name_en: 'Cuba Libre',
      name_es: 'Cuba Libre',
      description_en: 'Rum and cola.',
      description_es: 'Ron y cola.',
      price: '4.00',
      is_available: true,
      is_drink_of_day: false,
    },
    {
      id: 11,
      name_en: 'Piña Colada',
      name_es: 'Piña Colada',
      description_en: 'Coconut and pineapple.',
      description_es: 'Coco y piña.',
      price: '5.50',
      is_available: true,
      is_drink_of_day: true,
    },
  ],
};

function renderHero(props = {}) {
  return render(DrinkOfDay, { props: { categories: [CATEGORY], lang: 'en', ...props } });
}

describe('DrinkOfDay.svelte', () => {
  afterEach(() => {
    cleanup();
    locale.set('en');
  });

  it('renders the drink the admin marked', () => {
    renderHero();
    expect(screen.getByText('Drink of the day')).toBeTruthy();
    expect(screen.getByText('Piña Colada')).toBeTruthy();
    expect(screen.getByText('$5.50')).toBeTruthy();
    expect(screen.getByText('Coconut and pineapple.')).toBeTruthy();
  });

  it('shows nothing when no drink is marked', () => {
    renderHero({
      categories: [{ ...CATEGORY, items: [{ ...CATEGORY.items[0] }] }],
    });
    expect(screen.queryByText('Drink of the day')).toBeNull();
  });

  it('ignores a featured drink that is switched off', () => {
    renderHero({
      categories: [{ ...CATEGORY, items: [{ ...CATEGORY.items[1], is_available: false }] }],
    });
    expect(screen.queryByText('Drink of the day')).toBeNull();
  });

  it('renders the drink copy in Spanish when App passes the locale', () => {
    locale.set('es');
    renderHero({ lang: 'es' });

    expect(screen.getByText('Bebida del día')).toBeTruthy();
    expect(screen.getByText('Coco y piña.')).toBeTruthy();
    expect(screen.queryByText('Drink of the day')).toBeNull();
  });
});
