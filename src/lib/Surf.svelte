<script>
  import { onMount } from 'svelte';
  import { tideLevel } from './tide.js';

  const LAT = -1.8268, LON = -80.7517, TZ = 'America/Guayaquil';
  let state = 'loading'; // loading | ready | error
  let d = {};

  const hhmm = (iso) => iso.slice(11, 16);
  const to12 = (t) => {
    let [h, m] = t.split(':').map(Number);
    const ap = h >= 12 ? 'PM' : 'AM';
    return `${((h + 11) % 12) + 1}:${String(m).padStart(2, '0')} ${ap}`;
  };
  const compass = (deg) => ['N','NE','E','SE','S','SW','W','NW'][Math.round(deg / 45) % 8];
  const vibe = (m) =>
    m < 0.6 ? 'Small and gentle. Longboard or learn day.'
    : m < 1.2 ? 'Fun size. Good for most levels.'
    : m < 2 ? 'Solid. Experienced surfers will be happy.'
    : 'Big. Know your limits.';

  async function load() {
    state = 'loading';
    try {
      const [m, f] = await Promise.all([
        fetch(`https://marine-api.open-meteo.com/v1/marine?latitude=${LAT}&longitude=${LON}&hourly=wave_height,wave_period,wave_direction,sea_level_height_msl&timezone=${encodeURIComponent(TZ)}&forecast_days=3`).then(r => r.json()),
        fetch(`https://api.open-meteo.com/v1/forecast?latitude=${LAT}&longitude=${LON}&daily=sunrise,sunset&current=temperature_2m,wind_speed_10m,wind_direction_10m&timezone=${encodeURIComponent(TZ)}&forecast_days=1`).then(r => r.json()),
      ]);
      const now = new Date().toLocaleString('sv-SE', { timeZone: TZ }).slice(0, 13).replace(' ', 'T') + ':00';
      const t = m.hourly.time;
      let i = t.indexOf(now); if (i < 0) i = 0;
      const lvl = m.hourly.sea_level_height_msl;
      const win = lvl.slice(i, i + 48);
      const lo = Math.min(...win), hi = Math.max(...win);
      tideLevel.set((lvl[i] - lo) / (hi - lo || 1));

      // find the next two tide turning points
      const turns = [];
      for (let k = i + 1; k < lvl.length - 1 && turns.length < 3; k++) {
        if (lvl[k] > lvl[k-1] && lvl[k] >= lvl[k+1]) turns.push({ type: 'High', time: hhmm(t[k]), h: lvl[k] });
        if (lvl[k] < lvl[k-1] && lvl[k] <= lvl[k+1]) turns.push({ type: 'Low', time: hhmm(t[k]), h: lvl[k] });
      }
      d = {
        wave: m.hourly.wave_height[i],
        period: m.hourly.wave_period[i],
        dir: m.hourly.wave_direction[i],
        rising: lvl[i + 1] > lvl[i],
        turns,
        sunset: hhmm(f.daily.sunset[0]),
        sunrise: hhmm(f.daily.sunrise[0]),
        wind: f.current.wind_speed_10m,
        windDir: f.current.wind_direction_10m,
        temp: f.current.temperature_2m,
      };
      state = 'ready';
    } catch (e) { state = 'error'; }
  }
  onMount(load);
</script>

<section class="surf" id="surf" aria-labelledby="surf-h">
  <div class="head">
    <h2 id="surf-h">Surf report</h2>
    <p class="sub">Montañita, live. Check it, then come have a drink.</p>
  </div>

  {#if state === 'loading'}
    <div class="grid" aria-busy="true">
      {#each Array(4) as _}<div class="tile skeleton"></div>{/each}
    </div>
  {:else if state === 'error'}
    <div class="err">
      <p>Couldn't load the surf data. Check your connection and try again.</p>
      <button on:click={load}>Reload report</button>
    </div>
  {:else}
    <div class="grid">
      <div class="tile big">
        <span class="label">Waves</span>
        <span class="num">{d.wave.toFixed(1)}<small>m</small></span>
        <span class="meta">{(d.wave * 3.281).toFixed(0)} ft · {d.period.toFixed(0)}s period · from the {compass(d.dir)}</span>
        <p class="vibe">{vibe(d.wave)}</p>
      </div>
      <div class="tile">
        <span class="label">Tide</span>
        <span class="num sm">{d.rising ? 'Rising' : 'Falling'}</span>
        <ul class="turns">
          {#each d.turns.slice(0, 2) as t}<li><b>{t.type}</b> {to12(t.time)}</li>{/each}
        </ul>
      </div>
      <div class="tile">
        <span class="label">Sunset</span>
        <span class="num sm">{to12(d.sunset)}</span>
        <span class="meta">Sunrise {to12(d.sunrise)}</span>
      </div>
      <div class="tile">
        <span class="label">Wind &amp; air</span>
        <span class="num sm">{Math.round(d.wind)}<small> km/h {compass(d.windDir)}</small></span>
        <span class="meta">{Math.round(d.temp)}°C</span>
      </div>
    </div>
    <p class="credit">Data: Open-Meteo marine model. Always check the water yourself.</p>
  {/if}
</section>

<style>
  .surf { background: var(--deep); color: var(--sand); padding: 4rem 1.25rem 3rem; }
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
  .turns { list-style: none; margin: 0; padding: 0; font-size: .95rem; }
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
    .surf { padding: 6rem 2rem 4rem; }
    .grid { grid-template-columns: 2fr 1fr 1fr 1fr; }
    .big { grid-column: auto; }
    .skeleton:first-child { grid-column: auto; }
  }
</style>
