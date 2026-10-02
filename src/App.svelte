<script>
  import Surf from './lib/Surf.svelte';
  import { tideLevel } from './lib/tide.js';
  import { BAR, SOCIALS, EVENTS, DAYS } from './lib/data.js';

  const today = new Date(new Date().toLocaleString('en-US', { timeZone: 'America/Guayaquil' })).getDay();
  const tonight = EVENTS.find((e) => e.day === today);
  // Hero water sits between 50% and 78% of hero height, following the real tide.
  $: waterTop = 78 - $tideLevel * 28;
</script>

<header class="hero">
  <nav aria-label="Main">
    <span class="logo">{BAR.name}</span>
    <div class="links">
      <a href="#surf">Surf</a>
      <a href="#party">Party</a>
      <a href="#visit">Visit</a>
    </div>
  </nav>

  <div class="copy">
    <h1>Surf by day.<br />Dance by night.</h1>
    <p>{BAR.full} in {BAR.town}. Check the swell, then find us.</p>
    <div class="cta">
      <a class="btn primary" href="#surf">Today's surf</a>
      <a class="btn ghost" href="#party">Party schedule</a>
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
  <h2 id="party-h">Party schedule</h2>
  {#if tonight}
    <div class="tonight">
      <span class="tag">Tonight</span>
      <h3>{tonight.title}</h3>
      <p>{tonight.time}. {tonight.note}</p>
    </div>
  {/if}
  <ul class="week">
    {#each EVENTS as e}
      <li class:now={e.day === today}>
        <span class="day">{DAYS[e.day]}</span>
        <span class="what"><b>{e.title}</b><br />{e.note}</span>
        <span class="time">{e.time}</span>
      </li>
    {/each}
  </ul>
</section>

<section class="visit" id="visit" aria-labelledby="visit-h">
  <h2 id="visit-h">Find us</h2>
  <p>{BAR.full}, {BAR.town}. {BAR.hours}.</p>
  <a class="btn primary" href={BAR.mapsUrl} target="_blank" rel="noopener">Open map</a>
  <div class="socials">
    {#each SOCIALS as s}
      <a href={s.url} target="_blank" rel="noopener"><b>{s.name}</b><span>{s.handle}</span></a>
    {/each}
  </div>
</section>

<footer>© {new Date().getFullYear()} {BAR.full}. Montañita, Ecuador.</footer>

<style>
  .hero {
    position: relative; overflow: hidden; min-height: min(62svh, 34rem); color: #fff;
    padding: env(safe-area-inset-top) 1.25rem 0;
    background: linear-gradient(180deg, var(--marigold) 0%, var(--papaya) 38%, var(--hibiscus) 75%);
    display: flex; flex-direction: column;
  }
  nav { position: relative; z-index: 3; display: flex; justify-content: space-between; align-items: center; padding: 1.1rem 0; max-width: 68rem; width: 100%; margin-inline: auto; }
  .logo { font: 800 1.35rem var(--font-display); }
  .links { display: flex; gap: 1.25rem; }
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
    .hero { padding-inline: 2rem; }
    .party, .visit { padding-inline: 2rem; }
    .week li { grid-template-columns: 9rem 1fr auto; }
    .socials { grid-template-columns: repeat(3, 1fr); }
  }
</style>
