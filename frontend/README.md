# Marea Alta — Frontend

Svelte 5 + Vite static site for Marea Alta Surf Bar. Mobile-first, English/Spanish, no API keys needed.

## Commands

```bash
npm install       # Install dependencies
npm run dev       # Start dev server at http://localhost:5173
npm run build     # Build for production → outputs dist/
npm run preview   # Preview the production build locally
```

## Editing the Site

- **All wording:** `src/content/en.js` (English) and `src/content/es.js` (Spanish). Same structure in both.
  Missing Spanish keys fall back to English. `{full}`, `{town}`, `{year}` are filled in automatically.
- **Weekly party schedule:** titles and descriptions per weekday in the content files; times in `src/lib/data.js`.
- **Names, map link, social links:** `src/lib/data.js`.
- **Add a language:** copy `en.js` to `src/content/xx.js`, translate it, add it to `LANGS` in `src/lib/i18n.js`.
- The visitor's language choice is remembered; first visit follows the browser language.

## Surf Widget

`src/lib/Surf.svelte` calls the free Open-Meteo marine + forecast APIs from the visitor's browser.
Coordinates for Montañita are at the top of the file.

## Deployment

Upload the contents of `dist/` to any static host (Netlify, Vercel, GitHub Pages, S3, etc.).
