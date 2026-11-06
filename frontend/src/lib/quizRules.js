// Quiz rules for the "Perfect Drink" recommendation (ticket #27).
//
// The questions are fixed; the drinks are not. Answers score the live menu from
// `GET /api/menu`, so a drink the owner removes or marks unavailable simply
// stops being recommended. Cigarettes are never a recommendation.
//
// This is deliberately a frontend data file, not a database table: the quiz is
// a bit of fun, the rules are short, and changing them should not need a
// migration. If the owner ever wants to edit them from the admin panel, this
// module is the shape a `quiz_rules` table would take.

const EXCLUDED_CATEGORIES = new Set(['cigarrillos']);

export const QUESTIONS = [
  { id: 'mood', options: ['easy', 'cocktail', 'wine', 'surprise'] },
  { id: 'taste', options: ['sweet', 'strong', 'fresh', 'any'] },
  { id: 'night', options: ['light', 'long', 'one', 'celebrate'] },
];

// `categories` is a strong signal (the visitor asked for beer, wine or a
// cocktail); keywords are a tie-breaker. Both languages are searched because a
// menu item may only have one side filled in.
const RULES = {
  mood: {
    easy: {
      categories: ['cerveza'],
      keywords: ['beer', 'cerveza', 'lager', 'pilsener', 'light', 'clara', 'cold'],
    },
    cocktail: {
      categories: ['cocteles'],
      keywords: ['cocktail', 'coctel', 'coctél', 'rum', 'ron', 'gin', 'vodka', 'mojito', 'margarita', 'daiquiri'],
    },
    wine: {
      categories: ['vinos', 'licores'],
      keywords: ['wine', 'vino', 'tinto', 'blanco', 'rosado', 'sparkling', 'espumoso'],
    },
    surprise: { categories: [], keywords: [] },
  },
  taste: {
    sweet: {
      keywords: ['sweet', 'dulce', 'pineapple', 'pina', 'piña', 'mango', 'coconut', 'coco', 'passion', 'maracuya', 'maracuyá', 'strawberry', 'fresa', 'honey', 'miel', 'vanilla', 'vainilla'],
    },
    strong: {
      keywords: ['strong', 'fuerte', 'rum', 'ron', 'whisky', 'whiskey', 'vodka', 'gin', 'tequila', 'mezcal', 'negroni', 'old fashioned', 'licor'],
    },
    fresh: {
      keywords: ['lime', 'limon', 'limón', 'lemon', 'sour', 'mint', 'menta', 'mojito', 'citrus', 'citrico', 'cítrico', 'fresco', 'fresh', 'soda'],
    },
    any: { keywords: [] },
  },
  night: {
    light: {
      keywords: ['light', 'clara', 'lager', 'session', 'spritz', 'soda', 'suave'],
    },
    long: {
      keywords: ['pitcher', 'jarra', 'bucket', 'cubeta', 'liter', 'litro', 'share', 'compartir'],
    },
    one: {
      keywords: ['signature', 'house', 'casa', 'special', 'especial', 'premium', 'clasico', 'clásico'],
    },
    celebrate: {
      keywords: ['champagne', 'champan', 'champán', 'sparkling', 'espumoso', 'prosecco', 'bubbles', 'birthday', 'cumpleanos', 'cumpleaños', 'shot'],
    },
  },
};

const normalize = (value) =>
  String(value ?? '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase();

function searchable(item) {
  return normalize(
    [
      item.name_en,
      item.name_es,
      item.description_en,
      item.description_es,
      item.ingredients_en,
      item.ingredients_es,
    ].join(' ')
  );
}

/**
 * Pick one drink from the live menu for a set of answers.
 *
 * Returns `{ item, category }`, or `null` when the menu has nothing to
 * recommend. The caller owns the language-specific labels.
 */
export function recommend(categories, answers) {
  const candidates = [];

  for (const category of categories || []) {
    if (EXCLUDED_CATEGORIES.has(category.slug)) continue;
    for (const item of category.items || []) {
      if (!item?.name_en && !item?.name_es) continue;
      candidates.push({ item, category, index: candidates.length });
    }
  }

  if (!candidates.length) return null;

  const scored = candidates.map((candidate) => {
    let score = 0;
    const haystack = searchable(candidate.item);

    for (const question of QUESTIONS) {
      const rule = RULES[question.id]?.[answers?.[question.id]];
      if (!rule) continue;

      if (rule.categories?.includes(candidate.category.slug)) score += 6;
      for (const keyword of rule.keywords || []) {
        if (haystack.includes(normalize(keyword))) score += 2;
      }
    }

    return { ...candidate, score };
  });

  scored.sort((a, b) => b.score - a.score || a.index - b.index);
  const winner = scored[0];
  return { item: winner.item, category: winner.category };
}
