# Marea Alta Surf Bar

Svelte 5 + Vite, mobile first. No API keys needed.

    npm install
    npm run dev       # http://localhost:5173
    npm run build     # outputs dist/ — upload to Netlify, Vercel, Cloudflare Pages or any static host

## Edit content
Everything the bar changes weekly (events, hours, socials) is in `src/lib/data.js`.
The event schedule there is placeholder text: replace it with the real one.

## Surf widget
`src/lib/Surf.svelte` calls the free Open-Meteo marine + forecast APIs from the visitor's browser
(waves, tide, sunset, wind). Coordinates for Montañita are set at the top of the file.
The hero's water level moves with the real tide.
