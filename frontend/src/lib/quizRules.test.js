import { describe, it, expect } from 'vitest';
import { recommend } from './quizRules.js';

// The quiz is only useful if its answers actually reach the live menu. These
// tests pin the category signal, the flavour keywords, the cigarette exclusion
// and the empty-menu fallback.

const CATEGORIES = [
  {
    id: 1,
    slug: 'cerveza',
    name_en: 'Beer',
    name_es: 'Cerveza',
    items: [
      { id: 11, name_en: 'Pilsener', name_es: 'Pilsener', price: '2.50', description_en: 'Cold lager.', description_es: '', ingredients_en: '', ingredients_es: '' },
      { id: 12, name_en: 'Club', name_es: 'Club', price: '3.00', description_en: 'A light beer.', description_es: '', ingredients_en: '', ingredients_es: '' },
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
      { id: 23, name_en: 'Negroni', name_es: 'Negroni', price: '7.00', description_en: 'Strong and bitter.', description_es: '', ingredients_en: 'Gin, Campari, vermouth', ingredients_es: '' },
    ],
  },
  {
    id: 3,
    slug: 'vinos',
    name_en: 'Wine',
    name_es: 'Vinos',
    items: [
      { id: 31, name_en: 'House red', name_es: 'Tinto de la casa', price: '4.00', description_en: 'A classic house wine.', description_es: '', ingredients_en: '', ingredients_es: '' },
    ],
  },
  {
    id: 4,
    slug: 'cigarrillos',
    name_en: 'Cigarettes',
    name_es: 'Cigarrillos',
    items: [
      { id: 41, name_en: 'Elephant', name_es: 'Elephant', price: '2.00', description_en: '', description_es: '', ingredients_en: '', ingredients_es: '' },
    ],
  },
];

describe('quiz rules', () => {
  it('sends an easy, light answer to a beer', () => {
    const result = recommend(CATEGORIES, { mood: 'easy', taste: 'any', night: 'light' });
    expect(result.item.name_en).toBe('Pilsener');
    expect(result.category.slug).toBe('cerveza');
  });

  it('sends a sweet cocktail answer to the sweet cocktail', () => {
    const result = recommend(CATEGORIES, { mood: 'cocktail', taste: 'sweet', night: 'celebrate' });
    expect(result.item.name_en).toBe('Piña Colada');
  });

  it('sends a fresh answer to the mojito', () => {
    const result = recommend(CATEGORIES, { mood: 'cocktail', taste: 'fresh', night: 'one' });
    expect(result.item.name_en).toBe('Mojito');
  });

  it('sends a strong answer to the strong cocktail', () => {
    const result = recommend(CATEGORIES, { mood: 'cocktail', taste: 'strong', night: 'long' });
    expect(result.item.name_en).toBe('Negroni');
  });

  it('sends a wine answer to the wine category', () => {
    const result = recommend(CATEGORIES, { mood: 'wine', taste: 'any', night: 'one' });
    expect(result.item.name_en).toBe('House red');
  });

  it('never recommends cigarettes', () => {
    for (const answers of [
      { mood: 'surprise', taste: 'any', night: 'one' },
      { mood: 'surprise', taste: 'strong', night: 'celebrate' },
    ]) {
      expect(recommend(CATEGORIES, answers).category.slug).not.toBe('cigarrillos');
    }
  });

  it('returns null when the menu has no drinks', () => {
    expect(recommend([], { mood: 'easy' })).toBeNull();
  });
});
