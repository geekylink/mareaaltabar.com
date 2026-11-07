<script>
  import { onMount } from 'svelte';
  import { tideLevel } from './tide.js';
  import { t as tx, fmt } from './i18n.js';

  let state = 'loading'; // loading | ready | error
  let d = {};

  const to12 = (t) => {
    if (!t) return '—';
    let [h, m] = t.split(':').map(Number);
    const ap = h >= 12 ? 'PM' : 'AM';
    return `${((h + 11) % 12) + 1}:${String(m).padStart(2, '0')} ${ap}`;
  };
  const compass = (deg, c) => c.surf.compass[Math.round(deg / 45) % 8];
  const vibe = (m, c) => c.surf.vibes[m < 0.6 ? 0 : m < 1.2 ? 1 : m < 2 ? 2 : 3];

  async function load() {
    state = 'loading';
    try {
      // One same-origin read. The backend calls Open-Meteo and caches the
      // result for fifteen minutes, so a visitor's phone never talks to a
      // third party and the upstream API is not hammered at sunset.
      const response = await fetch('/api/surf');
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const report = await response.json();
      tideLevel.set(report.tide);
      d = {
        wave: report.wave,
        period: report.period,
        dir: report.direction,
        rising: report.rising,
        turns: report.turns || [],
        sunset: report.sunset,
        sunrise: report.sunrise,
        wind: report.wind,
        windDir: report.wind_direction,
        temp: report.temperature,
      };
      state = 'ready';
    } catch (e) { state = 'error'; }
  }
  onMount(load);
</script>

<section class="surf" id="surf" aria-labelledby="surf-h">
  <div class="head">
    <h2 id="surf-h">{$tx.surf.title}</h2>
    <p class="sub">{$tx.surf.subtitle}</p>
  </div>

  {#if state === 'loading'}
    <div class="grid" aria-busy="true">
      {#each Array(4) as _}<div class="tile skeleton"></div>{/each}
    </div>
  {:else if state === 'error'}
    <div class="err" role="alert">
      <p>{$tx.surf.error}</p>
      <button type="button" on:click={load}>{$tx.surf.retry}</button>
    </div>
  {:else}
    <div class="grid">
      <div class="tile big">
        <span class="label">{$tx.surf.waves}</span>
        <span class="num">{d.wave.toFixed(1)}<small>m</small></span>
        <span class="meta">{fmt($tx.surf.waveMeta, { ft: (d.wave * 3.281).toFixed(0), period: d.period.toFixed(0), dir: compass(d.dir, $tx) })}</span>
        <p class="vibe">{vibe(d.wave, $tx)}</p>
      </div>
      <div class="tile wide">
        <span class="label">{$tx.surf.tideToday}</span>
        <span class="num sm">{d.rising ? $tx.surf.rising : $tx.surf.falling}</span>
        <ul class="turns">
          {#each d.turns as tp}<li class:past={tp.past}><b>{tp.type === 'High' ? $tx.surf.high : $tx.surf.low}</b> {to12(tp.time)}</li>{/each}
        </ul>
      </div>
      <div class="tile">
        <span class="label">{$tx.surf.sunset}</span>
        <span class="num sm">{to12(d.sunset)}</span>
        <span class="meta">{$tx.surf.sunrise} {to12(d.sunrise)}</span>
      </div>
      <div class="tile">
        <span class="label">{$tx.surf.windAir}</span>
        <span class="num sm">{Math.round(d.wind)}<small> km/h {compass(d.windDir, $tx)}</small></span>
        <span class="meta">{Math.round(d.temp)}°C</span>
      </div>
    </div>
    <p class="credit">{$tx.surf.credit}</p>
  {/if}
</section>

<style>
  .surf { background: var(--deep); color: var(--sand); padding: 1.5rem 1.25rem 3rem; }
  .head, .grid, .credit, .err { max-width: 68rem; margin-inline: auto; }
  .sub { margin-top: .6rem; opacity: .8; }
  .grid { display: grid; gap: .9rem; margin-top: 2rem; grid-template-columns: 1fr 1fr; }
  .tile {
    background: rgba(255, 243, 224, .08); border: 1px solid rgba(255, 243, 224, .16);
    border-radius: 1.25rem; padding: 1.1rem; display: flex; flex-direction: column; gap: .35rem;
    transition: transform .35s var(--ease), background .35s var(--ease);
  }
  .tile:hover { transform: translateY(-4px); background: rgba(255, 182, 39, .14); }
  .big { grid-column: 1 / -1; background: linear-gradient(135deg, var(--papaya), var(--hibiscus)); border: 0; color: #fff; }
  .big:hover { background: linear-gradient(135deg, var(--hibiscus), var(--papaya)); }
  .label { font-weight: 700; font-size: .95rem; opacity: .85; }
  .num { font-family: var(--font-display); font-weight: 800; font-size: clamp(3.5rem, 16vw, 6rem); line-height: 1; }
  .num.sm { font-size: clamp(1.6rem, 7vw, 2.4rem); }
  .num small { font-size: .35em; font-weight: 500; margin-left: .15em; }
  .meta { opacity: .85; font-size: .95rem; }
  .vibe { font-weight: 500; margin-top: .4rem; }
  .turns { list-style: none; margin: .2rem 0 0; padding: 0; font-size: 1rem; display: grid; grid-template-columns: 1fr 1fr; gap: .35rem .9rem; }
  .turns li.past { opacity: .45; }
  .wide { grid-column: 1 / -1; }
  .skeleton { min-height: 7rem; animation: pulse 1.4s ease-in-out infinite; }
  .skeleton:first-child { grid-column: 1 / -1; min-height: 11rem; }
  @keyframes pulse { 50% { opacity: .45; } }
  .credit { margin-top: 1.25rem; font-size: .85rem; opacity: .6; }
  .err button {
    margin-top: 1rem; border: 0; border-radius: 999px; padding: .75rem 1.4rem; font: 700 1rem var(--font-body);
    background: var(--marigold); color: var(--ink); cursor: pointer; transition: transform .2s var(--ease);
  }
  .err button:active { transform: scale(.95); }
  @media (min-width: 760px) {
    .surf { padding: 2rem 2rem 4rem; }
    .grid { grid-template-columns: 1.2fr 1.6fr 1fr 1fr; }
    .big, .wide { grid-column: auto; }
    .skeleton:first-child { grid-column: auto; }
  }
</style>
