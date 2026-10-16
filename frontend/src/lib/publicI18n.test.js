import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import en from '../content/en.js';
import es from '../content/es.js';

// `backend/app/public_i18n.py` holds the labels the server-rendered schedule
// block uses. Most of them are the same strings the SPA shows, and the two
// copies live in different languages' files — so a rename on one side would
// leave the crawler-visible text disagreeing with the page for ever. This reads
// the Python file and checks the shared labels against the content modules.
// Vitest runs with `frontend/` as its root.
const PYTHON = readFileSync(
  resolve(process.cwd(), '../backend/app/public_i18n.py'),
  'utf-8',
);

// Labels the SPA genuinely does not have. Each one is a deliberate addition in
// the rendered HTML, not a duplicate — if one is added to the site, drop it
// from this list so the next edit keeps them in step.
const SERVER_ONLY = ['opening_hours'];

const SHARED_LABELS = {
  schedule_heading: (c) => c.party.title,
  tonight: (c) => c.party.tonight,
  closed_today: (c) => c.party.closedToday,
  closed_days: (c) => c.party.closedDays,
  no_event: (c) => c.party.noEvent,
};

const CONTENT = { en, es };

/** Scalar `"key": "value"` pairs for one language block of the Python file. */
function scalarsFor(lang) {
  const block = PYTHON.split(`"${lang}": {`)[1].split(/\n    }/)[0];
  const out = {};
  for (const [, key, value] of block.matchAll(/"(\w+)":\s*"([^"]*)"/g)) {
    out[key] = value;
  }
  return out;
}

/** The `days` list for one language block. */
function daysFor(lang) {
  const block = PYTHON.split(`"${lang}": {`)[1].split(/\n    }/)[0];
  const list = block.match(/"days":\s*\[([^\]]*)\]/);
  return [...list[1].matchAll(/"([^"]*)"/g)].map((m) => m[1]);
}

describe('server-rendered labels stay in step with the site copy', () => {
  for (const lang of ['en', 'es']) {
    describe(lang, () => {
      const scalars = scalarsFor(lang);
      const days = daysFor(lang);

      it('has every shared label the template renders', () => {
        for (const key of Object.keys(SHARED_LABELS)) {
          expect(scalars[key], key).toBeTruthy();
        }
      });

      for (const [key, read] of Object.entries(SHARED_LABELS)) {
        it(`"${key}" matches ${lang === 'en' ? 'en.js' : 'es.js'}`, () => {
          expect(scalars[key]).toBe(read(CONTENT[lang]));
        });
      }

      it('day names match the site copy, in order', () => {
        expect(days).toEqual(CONTENT[lang].days);
      });

      it('declares the server-only labels the template needs', () => {
        for (const key of SERVER_ONLY) {
          expect(scalars[key], key).toBeTruthy();
        }
      });
    });
  }

  it('every label in the file is either shared or explicitly server-only', () => {
    // Catches a new label added on one side and forgotten on the other.
    // `days` is absent because the scalar extractor skips lists; it has its own
    // test above.
    const known = [...Object.keys(SHARED_LABELS), ...SERVER_ONLY];
    expect(Object.keys(scalarsFor('en')).sort()).toEqual(known.sort());
  });
});