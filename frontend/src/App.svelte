<script>
  import { onDestroy } from 'svelte';
  import Surf from './lib/Surf.svelte';
  import Menu from './lib/Menu.svelte';
  import ContactForm from './lib/ContactForm.svelte';
  import NoticeBanner from './lib/NoticeBanner.svelte';
  import Nav from './lib/Nav.svelte';
  import DrinkOfDay from './lib/DrinkOfDay.svelte';
  import Newsletter from './lib/Newsletter.svelte';
  import Reservation from './lib/Reservation.svelte';
  import { tideLevel } from './lib/tide.js';
  import { t, locale, fmt } from './lib/i18n.js';
  import { BAR, SOCIALS } from './lib/data.js';
  import {
    load, pick, formatHours, formatEventDate, formatEventTime, barToday, isClosedOn,
  } from './lib/api.js';

  let schedule = [];
  let closedDays = [];
  let menu = [];
  let notices = [];
  let specialEvents = [];
  let loading = true;
  let loadError = null;

  // Which day it is at the bar, not where the visitor is: the schedule is keyed
  // to Montañita's calendar. `date` is what a closure row is compared against.
  const { day: today, date: todayIso } = barToday();

  // `lang` mirrors the visitor's choice, so switching language re-renders from
  // the already-fetched payload without another request.
  $: lang = $locale;

  $: tonight = schedule.find((d) => d.day === today);
  $: tonightTitle = pick(tonight, lang, 'title');
  $: tonightNote = pick(tonight, lang, 'note');

  // A day can be shut three ways: a closure dated today, the weekday's own
  // `is_closed` flag, or a title of "Closed"/"Cerrado". All three have to agree
  // — a public holiday the bar closed for is still an open weekday in the
  // schedule, and it used to advertise a party and "open until late" anyway.
  $: closedToday = isClosedOn(closedDays, todayIso);
  $: tonightClosed = closedToday || tonight?.is_closed || /^(closed|cerrado)$/i.test(tonightTitle);
  $: tonightTime = formatHours(tonight, lang, $t.party.closedToday);

  // Hero water sits between 50% and 78% of hero height, following the real tide.
  $: waterTop = 78 - $tideLevel * 28;

  // "Open daily, afternoon until late" is a lie on a day the bar is shut.
  $: todayHours = closedToday
    ? $t.party.closedToday
    : formatHours(schedule.find((d) => d.day === today), lang, $t.party.closedToday);
  $: vars = {
    full: BAR.full,
    name: BAR.name,
    town: BAR.town,
    year: new Date().getFullYear(),
    hours: todayHours || $t.visit.hours,
  };

  async function loadData() {
    loading = true;
    loadError = null;
    try {
      const result = await load();
      schedule = result.schedule;
      closedDays = result.closedDays;
      menu = result.menu;
      notices = result.notices || [];
      specialEvents = result.specialEvents || [];
      // Only show the notice when we have data to display alongside it.
      loadError = result.error && schedule.length > 0 ? result.error : null;
    } catch (err) {
      loadError = err.message;
    } finally {
      loading = false;
    }
  }

  loadData();
  const refreshTimer = setInterval(loadData, 60 * 60 * 1000);
  onDestroy(() => clearInterval(refreshTimer));

  $: if (typeof document !== 'undefined') {
    document.documentElement.lang = $locale;
    document.title = $t.meta.title;
    document.querySelector('meta[name="description"]')?.setAttribute('content', $t.meta.description);
  }
</script>

<svelte:window on:unmount={() => clearInterval(refreshInterval)} />

<NoticeBanner {notices} {lang} />

<header class="hero" id="top">
  <Nav />

  <div class="copy">
    <h1>{$t.hero.line1}<br />{$t.hero.line2}</h1>
    <p>{fmt($t.hero.tagline, vars)}</p>
    <div class="cta">
      <a class="btn primary" href="#surf">{$t.hero.ctaSurf}</a>
      <a class="btn ghost" href="#party">{$t.hero.ctaParty}</a>
      <a class="btn ghost" href="/menu">{$t.hero.ctaMenu}</a>
    </div>
  </div>

  <DrinkOfDay categories={menu} {lang} />

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

{#if loading && schedule.length === 0}
  <div class="loading-state">
    <p>{$t.ui.loading}</p>
  </div>
{:else if schedule.length === 0}
  <div class="error-state">
    <p>{loadError || $t.ui.error}</p>
    <button class="btn primary" on:click={loadData}>{$t.ui.retry}</button>
  </div>
{:else}
  <section class="party" id="party" aria-labelledby="party-h">
    <div class="section-header">
      <h2 id="party-h">{$t.party.title}</h2>
      <button class="btn-refresh" on:click={loadData}>{$t.ui.refresh}</button>
    </div>
    {#if loadError}
      <p class="cache-notice">{$t.party.cacheNotice}</p>
    {/if}
    {#if tonight && !tonightClosed}
      <div class="tonight">
        <span class="tag">{$t.party.tonight}</span>
        <h3>{tonightTitle}</h3>
        {#if tonightTime}<p>{tonightTime}</p>{/if}
        {#if tonightNote}<p>{tonightNote}</p>{/if}
      </div>
    {/if}
    <ul class="week">
      {#each schedule as day (day.day)}
        <!-- `lang` is referenced inline so Svelte records it as a dependency.
             Wrapping pick() in a local function hides the dependency and the
             list stops updating when the visitor switches language. -->
        {@const title = pick(day, lang, 'title')}
        {@const closed = (day.day === today && closedToday) || day.is_closed || /^(closed|cerrado)$/i.test(title)}
        {@const note = closed ? '' : pick(day, lang, 'note')}
        <li class:now={day.day === today} class:closed>
          <span class="day">{$t.days[day.day]}</span>
          <span class="what">
            <b>{closed ? $t.party.closedToday : title || $t.party.noEvent}</b>
            {#if note}<br />{note}{/if}
          </span>
          <span class="time">{closed ? $t.party.closedToday : formatHours(day, lang, $t.party.closedToday)}</span>
        </li>
      {/each}
    </ul>
    {#if specialEvents.length > 0}
      <div class="special-events">
        <h3>{$t.party.specialEvents}</h3>
        <ul>
          {#each specialEvents as event (event.id)}
            {@const eventTitle = pick(event, lang, 'title')}
            {@const eventDescription = pick(event, lang, 'description')}
            {@const eventTime = formatEventTime(event, lang)}
            <li>
              <time datetime={event.date}>{formatEventDate(event.date, lang)}</time>
              <div class="event-main">
                <b>{eventTitle}</b>
                {#if eventTime}<span class="event-time">{eventTime}</span>{/if}
                {#if eventDescription}<p>{eventDescription}</p>{/if}
                {#if event.image_url}
                  <img src={event.image_url} alt="" loading="lazy" />
                {/if}
              </div>
            </li>
          {/each}
        </ul>
      </div>
    {/if}
    {#if closedDays.length > 0}
      <div class="closed-days">
        <h3>{$t.party.closedDays}</h3>
        <ul>
          {#each closedDays as d (d.id)}
            <li>{d.date}{pick(d, lang, 'reason') ? ' — ' + pick(d, lang, 'reason') : ''}</li>
          {/each}
        </ul>
      </div>
    {/if}
  </section>
{/if}

<!-- The menu renders outside the schedule's loading/error branch: a backend
     hiccup that blanks the week must not blank the drinks too, and vice versa. -->
<Menu categories={menu} {lang} {loading} />

<Reservation />

<ContactForm />

<Newsletter />

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
  .copy { position: relative; z-index: 3; max-width: 68rem; width: 100%; margin: 4vh auto 1rem; }
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

  .loading-state, .error-state {
    padding: 4rem 1.25rem;
    text-align: center;
    max-width: 68rem;
    margin-inline: auto;
  }
  .error-state .btn { margin-top: 1rem; }

  .party { padding: 4rem 1.25rem; max-width: 68rem; margin-inline: auto; }
  :global(#menu), :global(#contact) { scroll-margin-top: 2rem; }
  .section-header { display: flex; justify-content: space-between; align-items: center; }
  .btn-refresh {
    background: none;
    border: 2px solid var(--deep);
    color: var(--deep);
    padding: .4rem .9rem;
    border-radius: 999px;
    font-size: .85rem;
    font-weight: 600;
    cursor: pointer;
    transition: background .2s, color .2s;
  }
  .btn-refresh:hover { background: var(--deep); color: #fff; }
  .cache-notice {
    font-size: .85rem;
    color: #888;
    margin-top: .5rem;
    font-style: italic;
  }
  .tonight { margin-top: 1.75rem; padding: 1.5rem; border-radius: 1.5rem; color: #fff; background: linear-gradient(135deg, var(--hibiscus), var(--papaya)); }
  .tag { display: inline-block; background: #fff; color: var(--hibiscus); font-weight: 700; font-size: .9rem; padding: .15rem .7rem; border-radius: 999px; margin-bottom: .6rem; }
  .tonight h3 { font-size: clamp(2rem, 9vw, 3.2rem); }
  .tonight p { margin-top: .5rem; }
  .week { list-style: none; padding: 0; margin: 1.75rem 0 0; }
  .week li { display: grid; grid-template-columns: 6.5rem 1fr auto; gap: .75rem; align-items: baseline; padding: 1rem .75rem; border-bottom: 2px solid rgba(29, 26, 23, .12); border-radius: .75rem; transition: background .25s, padding-left .25s var(--ease); }
  .week li:hover { background: rgba(255, 182, 39, .3); padding-left: 1.25rem; }
  .week li.now { background: rgba(255, 107, 44, .15); }
  .week li.closed { opacity: .6; }
  .day { font-family: var(--font-display); font-weight: 800; font-size: 1.15rem; }
  .what { font-size: .98rem; }
  .time { font-weight: 700; white-space: nowrap; }

  .special-events { margin-top: 1.5rem; padding: 1.25rem; border-radius: 1rem; background: rgba(11, 60, 73, .06); }
  .special-events h3 { font-size: 1rem; color: var(--deep); margin-bottom: .5rem; }
  .special-events ul { list-style: none; padding: 0; }
  .special-events li { display: grid; grid-template-columns: 7rem 1fr; gap: .75rem; padding: .8rem 0; border-bottom: 1px solid rgba(29, 26, 23, .1); }
  .special-events li:last-child { border-bottom: none; }
  .special-events time { font-weight: 700; color: var(--deep); }
  .special-events .event-main { font-size: .95rem; }
  .special-events .event-time { display: block; font-size: .85rem; color: #666; margin-top: .15rem; }
  .special-events p { margin-top: .35rem; }
  .special-events img { display: block; max-width: 12rem; max-height: 8rem; object-fit: cover; border-radius: .5rem; margin-top: .5rem; }
  .closed-days { margin-top: 1.5rem; padding: 1.25rem; border-radius: 1rem; background: rgba(255, 107, 44, .08); }
  .closed-days h3 { font-size: 1rem; color: var(--deep); margin-bottom: .5rem; }
  .closed-days ul { list-style: none; }
  .closed-days li { padding: .3rem 0; font-size: .9rem; color: #555; }

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
