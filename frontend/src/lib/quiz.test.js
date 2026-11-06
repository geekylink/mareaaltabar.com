import { describe, it, expect, afterEach, vi } from 'vitest';
import { render, screen, cleanup, fireEvent, waitFor } from '@testing-library/svelte';
import Quiz from './Quiz.svelte';
import { locale } from './i18n.js';

// The quiz walks three questions and resolves against the live menu. These
// tests pin the flow, the recommendation, the empty-menu copy, the restart and
// the clipboard fallback when the Web Share API is unavailable.

const CATEGORIES = [
  {
    id: 1,
    slug: 'cerveza',
    name_en: 'Beer',
    name_es: 'Cerveza',
    items: [
      { id: 11, name_en: 'Pilsener', name_es: 'Pilsener', price: '2.50', description_en: 'Cold lager.', description_es: '', ingredients_en: '', ingredients_es: '' },
    ],
  },
  {
    id: 2,
    slug: 'cocteles',
    name_en: 'Cocktails',
    name_es: 'Cócteles',
    items: [
      { id: 21, name_en: 'Piña Colada', name_es: 'Piña Colada', price: '6.00', description_en: 'Sweet pineapple and coconut.', description_es: '', ingredients_en: 'Rum, pineapple, coconut', ingredients_es: '' },
      { id: 22, name_en: 'Mojito', name_es: 'Mojito', price: '5.00', description_en: 'Fresh mint and lime.', description_es: '', ingredients_en: 'Rum, mint, lime', ingredients_es: '' },
    ],
  },
];

async function answer(...labels) {
  await fireEvent.click(screen.getByRole('button', { name: 'Start the quiz' }));
  for (const label of labels) {
    await fireEvent.click(screen.getByRole('button', { name: label }));
  }
}

describe('Quiz.svelte', () => {
  afterEach(() => {
    cleanup();
    locale.set('en');
    vi.restoreAllMocks();
    Reflect.deleteProperty(navigator, 'clipboard');
  });

  it('starts with an invitation, not a question', () => {
    render(Quiz, { props: { categories: CATEGORIES } });
    expect(screen.getByText('Find your perfect drink')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Start the quiz' })).toBeTruthy();
    expect(screen.queryByText('What are you in the mood for?')).toBeNull();
  });

  it('walks three questions and recommends a beer for an easy night', async () => {
    render(Quiz, { props: { categories: CATEGORIES } });

    await answer('Something cold and easy', 'No preference', 'Just warming up');

    expect(screen.getByText('Your drink is...')).toBeTruthy();
    expect(screen.getByText('Pilsener')).toBeTruthy();
    expect(screen.getByText(/Beer/)).toBeTruthy();
    expect(screen.getByText(/\$2\.50/)).toBeTruthy();
    expect(screen.getByText('Cold lager.')).toBeTruthy();
  });

  it('recommends a sweet cocktail for a celebration', async () => {
    render(Quiz, { props: { categories: CATEGORIES } });

    await answer('A proper cocktail', 'Sweet and fruity', 'Celebrating');

    expect(screen.getByText('Piña Colada')).toBeTruthy();
    expect(screen.getByText(/Cocktails/)).toBeTruthy();
    expect(screen.getByText(/Rum, pineapple, coconut/)).toBeTruthy();
  });

  it('shows the menu-updating message when there is nothing to recommend', async () => {
    render(Quiz, { props: { categories: [] } });

    await answer('Something cold and easy', 'No preference', 'Just warming up');

    expect(screen.getByText(/The menu is being updated/)).toBeTruthy();
  });

  it('starts over from the result', async () => {
    render(Quiz, { props: { categories: CATEGORIES } });
    await answer('Something cold and easy', 'No preference', 'Just warming up');

    await fireEvent.click(screen.getByRole('button', { name: 'Try again' }));

    expect(screen.getByRole('button', { name: 'Start the quiz' })).toBeTruthy();
    expect(screen.queryByText('Pilsener')).toBeNull();
  });

  it('copies the result when the Web Share API is unavailable', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText },
    });

    render(Quiz, { props: { categories: CATEGORIES } });
    await answer('Something cold and easy', 'No preference', 'Just warming up');
    await fireEvent.click(screen.getByRole('button', { name: 'Share result' }));

    await waitFor(() => expect(writeText).toHaveBeenCalledTimes(1));
    expect(writeText.mock.calls[0][0]).toContain('Pilsener');
    expect(screen.getByRole('status').textContent).toContain('Copied');
  });

  it('switches to Spanish', () => {
    locale.set('es');
    render(Quiz, { props: { categories: CATEGORIES } });

    expect(screen.getByText('Encuentra tu bebida perfecta')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Empezar el quiz' })).toBeTruthy();
  });
});
