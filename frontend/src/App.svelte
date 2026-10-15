<script>
  import Surf from './lib/Surf.svelte';
  import { tideLevel } from './lib/tide.js';
  import { t, locale, fmt, LANGS } from './lib/i18n.js';
  import { BAR, SOCIALS, EVENTS } from './lib/data.js';

  const today = new Date(new Date().toLocaleString('en-US', { timeZone: 'America/Guayaquil' })).getDay();
  const tonight = EVENTS.find((e) => e.day === today);
  // Hero water sits between 50% and 78% of hero height, following the real tide.
  $: waterTop = 78 - $tideLevel * 28;
  $: vars = { full: BAR.full, name: BAR.name, town: BAR.town, year: new Date().getFullYear(), hours: $t.visit.hours };

  $: if (typeof document !== 'undefined') {
    document.documentElement.lang = $locale;
    document.title = $t.meta.title;
    document.querySelector('meta[name="description"]')?.setAttribute('content', $t.meta.description);
  }
</script>

<header class="hero">
  <nav aria-label={$t.ui.mainNav}>
    <span class="logo">{BAR.name}</span>
    <div class="right">
      <div class="links">
        <a href="#surf">{$t.nav.surf}</a>
        <a href="#party">{$t.nav.party}</a>
        <a href="#visit">{$t.nav.visit}</a>
      </div>
      <select class="lang" bind:value={$locale} aria-label={$t.ui.language}>
        {#each LANGS as l}<option value={l.code}>{l.label}</option>{/each}
      </select>
    </div>
  </nav>

  <div class="copy">
    <h1>{$t.hero.line1}<br />{$t.hero.line2}</h1>
    <p>{fmt($t.hero.tagline, vars)}</p>
    <div class="cta">
      <a class="btn primary" href="#surf">{$t.hero.ctaSurf}</a>
      <a class="btn ghost" href="#party">{$t.hero.ctaParty}</a>
    </div>
  </div>

  <div class="sun" aria-hidden="true"></div>
  <div class="water" style="top:{waterTop}%" aria-hidden="true">
    <svg viewBox="0 0 1200 60" preserveAspectRatio="none">
      <path class="w1" d="M0 30 Q150 0 300 30 T600 30 T900 30 T1200 30 V60 H0Z" />
      <path class="w2" d="M0 36 Q150 8 300 36 T600 36 T900 36 T1200 36 V60 H0Z" />
    </svg>
    <div class="fill"></div>
  </div>
</header>

<Surf />

<section class="party" id="party" aria-labelledby="party-h">
  <h2 id="party-h">{$t.party.title}</h2>
  {#if tonight}
    <div class="tonight">
      <span class="tag">{$t.party.tonight}</span>
      <h3>{$t.events[tonight.day].title}</h3>
      <p>{tonight.time}. {$t.events[tonight.day].note}</p>
    </div>
  {/if}
  <ul class="week">
    {#each EVENTS as e}
      <li class:now={e.day === today}>
        <span class="day">{$t.days[e.day]}</span>
        <span class="what"><b>{$t.events[e.day].title}</b><br />{$t.events[e.day].note}</span>
        <span class="time">{e.time}</span>
      </li>
    {/each}
  </ul>
</section>

<section class="visit" id="visit" aria-labelledby="visit-h">
  <h2 id="visit-h">{$t.visit.title}</h2>
  <p>{fmt($t.visit.text, vars)}</p>
  <a class="btn primary" href={BAR.mapsUrl} target="_blank" rel="noopener">{$t.visit.openMap}</a>
  <div class="socials">
    {#each SOCIALS as s}
      <a href={s.url} target="_blank" rel="noopener"><b>{s.name}</b><span>{s.handle}</span></a>
    {/each}
  </div>
</section>

<footer>{fmt($t.footer, vars)}</footer>

<style>
  .hero {
    position: relative; overflow: hidden; min-height: min(62svh, 34rem); color: #fff;
    padding: env(safe-area-inset-top) 1.25rem 0;
    background: linear-gradient(180deg, var(--marigold) 0%, var(--papaya) 38%, var(--hibiscus) 75%);
    display: flex; flex-direction: column;
  }
  nav { position: relative; z-index: 3; display: flex; justify-content: space-between; align-items: center; padding: 1.1rem 0; max-width: 68rem; width: 100%; margin-inline: auto; }
  .logo { font: 800 clamp(1.1rem, 4.5vw, 1.35rem) var(--font-display); }
  .right { display: flex; align-items: center; gap: .8rem; }
  .links { display: flex; gap: .9rem; font-size: .95rem; }
  .lang {
    appearance: none; -webkit-appearance: none; cursor: pointer; color: #fff;
    font: 700 .9rem var(--font-body); padding: .3rem 1.6rem .3rem .75rem; border-radius: 999px;
    border: 2px solid rgba(255, 255, 255, .75); background-color: rgba(255, 255, 255, .15);
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M1 1l4 4 4-4' fill='none' stroke='white' stroke-width='2' stroke-linecap='round'/%3E%3C/svg%3E");
    background-repeat: no-repeat; background-position: right .6rem center;
    transition: background-color .25s var(--ease), transform .2s var(--ease);
  }
  .lang:hover { background-color: rgba(255, 255, 255, .32); }
  .lang:active { transform: scale(.95); }
  .lang option { color: var(--ink); }
  .links a { text-decoration: none; font-weight: 700; position: relative; padding-block: .25rem; }
  .links a::after { content: ''; position: absolute; left: 0; bottom: 0; height: 2px; width: 100%; background: currentColor; transform: scaleX(0); transform-origin: left; transition: transform .3s var(--ease); }
  .links a:hover::after { transform: scaleX(1); }
  .copy { position: relative; z-index: 3; max-width: 68rem; width: 100%; margin: 4vh auto 3.5rem; }
  h1 { font-size: clamp(3rem, 14vw, 7.5rem); font-weight: 800; text-wrap: balance; }
  .copy p { margin-top: 1.25rem; font-size: 1.15rem; font-weight: 500; }
  .cta { display: flex; flex-wrap: wrap; gap: .75rem; margin-top: 1.75rem; }
  .btn { display: inline-block; text-decoration: none; font-weight: 700; border-radius: 999px; padding: .85rem 1.6rem; transition: transform .25s var(--ease), box-shadow .25s var(--ease), background .25s; }
  .btn:hover { transform: translateY(-3px); }
  .btn:active { transform: scale(.96); }
  .primary { background: var(--deep); color: var(--sand); box-shadow: 0 6px 0 rgba(0,0,0,.25); }
  .primary:hover { box-shadow: 0 9px 0 rgba(0,0,0,.25); }
  .ghost { border: 2px solid #fff; color: #fff; }
  .ghost:hover { background: #fff; color: var(--hibiscus); }
  .sun { position: absolute; z-index: 1; right: -8vw; bottom: 22%; width: 52vw; max-width: 28rem; aspect-ratio: 1; border-radius: 50%; background: #ffe08a; opacity: .85; animation: bob 7s ease-in-out infinite; }
  @keyframes bob { 50% { transform: translateY(-12px); } }
  .water { position: absolute; z-index: 2; left: 0; right: 0; bottom: 0; transition: top 2.2s var(--ease); }
  .water svg { display: block; width: 200%; height: 3.5rem; }
  .water .w1 { fill: rgba(11, 60, 73, .55); animation: drift 9s linear infinite; }
  .water .w2 { fill: var(--deep); animation: drift 6s linear infinite reverse; }
  .water svg { animation: none; }
  .fill { background: var(--deep); height: 100vh; margin-top: -1px; }
  @keyframes drift { to { transform: translateX(-50%); } }
  .w1, .w2 { transform-box: fill-box; }

  .party { padding: 4rem 1.25rem; max-width: 68rem; margin-inline: auto; }
  .tonight { margin-top: 1.75rem; padding: 1.5rem; border-radius: 1.5rem; color: #fff; background: linear-gradient(135deg, var(--hibiscus), var(--papaya)); }
  .tag { display: inline-block; background: #fff; color: var(--hibiscus); font-weight: 700; font-size: .9rem; padding: .15rem .7rem; border-radius: 999px; margin-bottom: .6rem; }
  .tonight h3 { font-size: clamp(2rem, 9vw, 3.2rem); }
  .tonight p { margin-top: .5rem; }
  .week { list-style: none; padding: 0; margin: 1.75rem 0 0; }
  .week li { display: grid; grid-template-columns: 6.5rem 1fr auto; gap: .75rem; align-items: baseline; padding: 1rem .75rem; border-bottom: 2px solid rgba(29, 26, 23, .12); border-radius: .75rem; transition: background .25s, padding-left .25s var(--ease); }
  .week li:hover { background: rgba(255, 182, 39, .3); padding-left: 1.25rem; }
  .week li.now { background: rgba(255, 107, 44, .15); }
  .day { font-family: var(--font-display); font-weight: 800; font-size: 1.15rem; }
  .what { font-size: .98rem; }
  .time { font-weight: 700; white-space: nowrap; }

  .visit { padding: 3rem 1.25rem 4rem; max-width: 68rem; margin-inline: auto; display: flex; flex-direction: column; gap: 1.25rem; align-items: flex-start; }
  .socials { display: grid; gap: .75rem; width: 100%; margin-top: .75rem; }
  .socials a { display: flex; justify-content: space-between; text-decoration: none; padding: 1rem 1.25rem; border-radius: 1rem; background: #fff; border: 2px solid var(--deep); transition: transform .25s var(--ease), background .25s, color .25s; }
  .socials a:hover { transform: translateX(6px); background: var(--deep); color: var(--sand); }
  footer { background: var(--deep); color: var(--sand); text-align: center; padding: 1.5rem 1rem calc(1.5rem + env(safe-area-inset-bottom)); font-size: .9rem; }

  @media (min-width: 760px) {
    .links { gap: 1.25rem; font-size: 1.05rem; }
    .right { gap: 1.25rem; }
    .hero { padding-inline: 2rem; }
    .party, .visit { padding-inline: 2rem; }
    .week li { grid-template-columns: 9rem 1fr auto; }
    .socials { grid-template-columns: repeat(3, 1fr); }
  }
</style>
