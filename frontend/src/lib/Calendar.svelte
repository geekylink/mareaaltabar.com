<script>
  import { t } from './i18n.js';
  import { pick, formatEventDate, formatEventTime, barToday } from './api.js';
  import EventRsvp from './EventRsvp.svelte';

  // A month view over the dated events (#53). The weekly schedule repeats; this
  // is where a one-off guest set or a holiday party lives. The calendar starts
  // on the soonest event's month so the next party is visible without paging,
  // and the agenda below it keeps the full date, time and description the old
  // list showed.
  export let events = [];
  export let lang = 'en';

  const todayIso = barToday().date;
  const pad = (n) => String(n).padStart(2, '0');

  function monthStart(iso) {
    const [year, month] = String(iso || todayIso).split('-').map(Number);
    return new Date(year, (month || 1) - 1, 1);
  }

  function monthKey(date) {
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}`;
  }

  let cursor = monthStart(events[0]?.date);
  let selected = events[0]?.date || '';

  $: key = monthKey(cursor);
  $: monthEvents = events.filter((event) => (event.date || '').startsWith(key));
  $: selectedEvents = monthEvents.filter((event) => event.date === selected);
  $: if (!monthEvents.some((event) => event.date === selected)) {
    selected = monthEvents[0]?.date || '';
  }
  $: canGoBack = key > monthKey(monthStart(todayIso));

  function move(delta) {
    cursor = new Date(cursor.getFullYear(), cursor.getMonth() + delta, 1);
  }

  function isoFor(day, date) {
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(day)}`;
  }

  function cells(date) {
    const firstWeekday = new Date(date.getFullYear(), date.getMonth(), 1).getDay();
    const daysInMonth = new Date(date.getFullYear(), date.getMonth() + 1, 0).getDate();
    const out = Array(firstWeekday).fill(null);
    for (let day = 1; day <= daysInMonth; day += 1) out.push(day);
    while (out.length % 7 !== 0) out.push(null);
    return out;
  }

  function weeks(date) {
    const all = cells(date);
    const out = [];
    for (let i = 0; i < all.length; i += 7) out.push(all.slice(i, i + 7));
    return out;
  }

  function eventsOn(iso, list) {
    return list.filter((event) => event.date === iso);
  }

  function monthLabel(date, language) {
    return date.toLocaleDateString(language === 'es' ? 'es-EC' : 'en-US', {
      month: 'long',
      year: 'numeric',
    });
  }

  function dayLabel(iso, language) {
    return formatEventDate(iso, language);
  }
</script>

<div class="calendar">
  <div class="bar">
    <button
      type="button"
      class="nav"
      on:click={() => move(-1)}
      disabled={!canGoBack}
      aria-label={$t.calendar.prev}
    >‹</button>
    <h4 aria-live="polite">{monthLabel(cursor, lang)}</h4>
    <button
      type="button"
      class="nav"
      on:click={() => move(1)}
      aria-label={$t.calendar.next}
    >›</button>
  </div>

  <table class="grid">
    <thead>
      <tr>
        {#each $t.days as day}
          <th scope="col">{day.slice(0, 3)}</th>
        {/each}
      </tr>
    </thead>
    <tbody>
      {#each weeks(cursor) as week}
        <tr>
          {#each week as day}
            {#if day}
              {@const iso = isoFor(day, cursor)}
              {@const dayEvents = eventsOn(iso, monthEvents)}
              <td class:today={iso === todayIso} class:has-event={dayEvents.length > 0}>
                <button
                  type="button"
                  class="day"
                  on:click={() => (selected = iso)}
                  aria-pressed={selected === iso}
                  aria-label={`${dayLabel(iso, lang)}${dayEvents.length ? ` — ${dayEvents.length}` : ''}`}
                >
                  <span class="num">{day}</span>
                  {#if dayEvents.length}
                    <span class="dot" aria-hidden="true"></span>
                  {/if}
                </button>
              </td>
            {:else}
              <td class="blank"></td>
            {/if}
          {/each}
        </tr>
      {/each}
    </tbody>
  </table>

  <div class="agenda">
    {#if selectedEvents.length}
      {#each selectedEvents as event (event.id)}
        {@const title = pick(event, lang, 'title')}
        {@const description = pick(event, lang, 'description')}
        {@const time = formatEventTime(event, lang)}
        <article>
          <time datetime={event.date}>{formatEventDate(event.date, lang)}</time>
          <h5>{title}</h5>
          {#if time}<span class="time">{time}</span>{/if}
          {#if description}<p>{description}</p>{/if}
          {#if event.image_url}
            <img src={event.image_url} alt="" loading="lazy" />
          {/if}
          <EventRsvp eventId={event.id} />
        </article>
      {/each}
    {:else}
      <p class="empty">{$t.calendar.empty}</p>
    {/if}
  </div>
</div>

<style>
  .calendar { margin-top: .75rem; }
  .bar { display: flex; align-items: center; justify-content: space-between; gap: .5rem; }
  .bar h4 { flex: 1; text-align: center; font-size: 1rem; color: var(--deep); text-transform: capitalize; }
  .nav {
    border: 2px solid rgba(11, 60, 73, .25); background: #fff; color: var(--deep);
    width: 2rem; height: 2rem; border-radius: 50%; font: inherit; font-size: 1.1rem;
    line-height: 1; cursor: pointer;
  }
  .nav:hover:not(:disabled) { background: var(--deep); color: var(--sand); }
  .nav:disabled { opacity: .35; cursor: not-allowed; }
  .grid { width: 100%; border-collapse: collapse; margin-top: .6rem; table-layout: fixed; }
  .grid th {
    font-size: .65rem; text-transform: uppercase; letter-spacing: .04em;
    color: #777; padding: .25rem 0; font-weight: 700;
  }
  .grid td { padding: 1px; text-align: center; }
  .grid td.blank { background: transparent; }
  .day {
    width: 100%; min-height: 2.1rem; border: 1px solid rgba(11, 60, 73, .12);
    border-radius: .35rem; background: #fff; color: var(--ink); font: inherit;
    font-size: .8rem; cursor: pointer; display: grid; place-items: center; gap: 1px;
    padding: .2rem 0;
  }
  .day:hover { border-color: var(--deep); }
  .day[aria-pressed='true'] { background: var(--deep); color: var(--sand); border-color: var(--deep); }
  .today .day:not([aria-pressed='true']) { border-color: var(--papaya); box-shadow: inset 0 0 0 1px var(--papaya); }
  .has-event .day:not([aria-pressed='true']) { background: rgba(255, 182, 39, .3); }
  .num { line-height: 1; }
  .dot { width: .35rem; height: .35rem; border-radius: 50%; background: var(--hibiscus); }
  .day[aria-pressed='true'] .dot { background: var(--sand); }
  .agenda { margin-top: .9rem; display: grid; gap: .75rem; }
  .agenda article {
    background: #fff; border-radius: .7rem; padding: .8rem .9rem;
    border-left: 3px solid var(--papaya);
  }
  .agenda time { font-size: .78rem; font-weight: 700; color: var(--deep); text-transform: capitalize; }
  .agenda h5 { font-size: 1rem; margin-top: .1rem; }
  .agenda .time { display: block; font-size: .8rem; color: #666; margin-top: .1rem; }
  .agenda p { margin-top: .35rem; font-size: .9rem; }
  .agenda img { display: block; max-width: 12rem; max-height: 8rem; object-fit: cover; border-radius: .5rem; margin-top: .5rem; }
  .empty { font-size: .9rem; color: #777; }
</style>
