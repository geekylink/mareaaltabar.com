<script>
  import { t } from './i18n.js';
  import { barToday } from './api.js';

  // A table request, not a booking. The backend caps the party at 20 and the
  // horizon at 90 days; those limits are mirrored here so the visitor sees them
  // before submitting rather than as a server error.
  const MAX_GUESTS = 20;
  const MAX_DAYS_AHEAD = 90;

  const { date: todayIso } = barToday();

  function addDays(iso, days) {
    const [year, month, day] = iso.split('-').map(Number);
    const value = new Date(Date.UTC(year, month - 1, day + days));
    return value.toISOString().slice(0, 10);
  }

  const lastIso = addDays(todayIso, MAX_DAYS_AHEAD);

  let date = todayIso;
  let time = '20:00';
  let partySize = 2;
  let name = '';
  let contact = '';
  let notes = '';
  let website = '';
  let status = 'idle'; // idle | sending | sent | error
  let error = '';

  async function submit(event) {
    event.preventDefault();
    if (status === 'sending') return;

    if (!date || !time || !name.trim() || !contact.trim()) {
      status = 'error';
      error = $t.reservation.required;
      return;
    }

    status = 'sending';
    error = '';
    try {
      const res = await fetch('/api/reservations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          date,
          time,
          party_size: Number(partySize),
          name: name.trim(),
          contact: contact.trim(),
          notes: notes.trim(),
          website,
        }),
      });
      if (!res.ok) throw new Error('reservation request failed');
      status = 'sent';
      name = '';
      contact = '';
      notes = '';
      website = '';
    } catch (err) {
      status = 'error';
      error = $t.reservation.error;
    }
  }
</script>

<section class="reservation" id="reservation" aria-labelledby="reservation-h">
  <div class="head">
    <h2 id="reservation-h">{$t.reservation.title}</h2>
    <p class="sub">{$t.reservation.subtitle}</p>
    <p class="policy">{$t.reservation.note}</p>
  </div>

  {#if status === 'sent'}
    <p class="notice success" role="status">{$t.reservation.sent}</p>
  {:else}
    <form on:submit={submit} novalidate>
      <div class="pair">
        <label>
          <span>{$t.reservation.date}</span>
          <input type="date" bind:value={date} min={todayIso} max={lastIso} required />
        </label>
        <label>
          <span>{$t.reservation.time}</span>
          <input type="time" bind:value={time} required />
        </label>
      </div>

      <label>
        <span>{$t.reservation.partySize}</span>
        <input
          type="number"
          bind:value={partySize}
          min="1"
          max={MAX_GUESTS}
          step="1"
          required
        />
      </label>

      <div class="pair">
        <label>
          <span>{$t.reservation.name}</span>
          <input type="text" bind:value={name} maxlength="120" autocomplete="name" required />
        </label>
        <label>
          <span>{$t.reservation.contact}</span>
          <input type="text" bind:value={contact} maxlength="200" autocomplete="email" required />
        </label>
      </div>

      <label>
        <span>{$t.reservation.notes}</span>
        <textarea bind:value={notes} rows="3" maxlength="1000"></textarea>
      </label>

      <!-- Honeypot: off-screen rather than display:none, which some bots skip. -->
      <label class="hp" aria-hidden="true">
        <span>{$t.reservation.honeypot}</span>
        <input type="text" bind:value={website} tabindex="-1" autocomplete="off" />
      </label>

      {#if status === 'error'}
        <p class="notice error" role="alert">{error}</p>
      {/if}

      <button type="submit" disabled={status === 'sending'}>
        {status === 'sending' ? $t.reservation.sending : $t.reservation.send}
      </button>
    </form>
  {/if}
</section>

<style>
  .reservation {
    padding: 4rem 1.25rem; max-width: 42rem; margin-inline: auto;
    border-top: 2px solid rgba(29, 26, 23, .1);
  }
  .head { margin-bottom: 1.5rem; }
  .sub { margin-top: .6rem; color: #555; }
  .policy {
    margin-top: .75rem; font-size: .82rem; color: var(--deep);
    background: rgba(255, 182, 39, .25); border-radius: .6rem;
    padding: .6rem .8rem;
  }
  form { display: grid; gap: 1rem; }
  .pair { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
  label { display: grid; gap: .35rem; font-size: .85rem; font-weight: 700; color: var(--deep); }
  input, textarea {
    width: 100%; padding: .7rem .8rem; border: 2px solid rgba(11, 60, 73, .25);
    border-radius: .6rem; font: inherit; font-weight: 400; color: var(--ink);
    background: #fff;
  }
  textarea { resize: vertical; min-height: 5rem; }
  input:focus, textarea:focus { outline: none; border-color: var(--deep); }
  button {
    justify-self: start; border: none; border-radius: 999px; padding: .85rem 1.6rem;
    background: var(--deep); color: var(--sand); font: inherit; font-weight: 700;
    cursor: pointer; transition: transform .25s var(--ease), background .25s;
  }
  button:hover { transform: translateY(-2px); background: var(--papaya); }
  button:disabled { opacity: .65; cursor: not-allowed; transform: none; }
  .notice { padding: .8rem 1rem; border-radius: .6rem; font-size: .9rem; }
  .success { background: #D1FAE5; color: #065F46; }
  .error { background: #FEE2E2; color: #991B1B; }
  .hp {
    position: absolute; left: -9999px; width: 1px; height: 1px;
    overflow: hidden; opacity: 0; pointer-events: none;
  }
  @media (max-width: 620px) {
    .pair { grid-template-columns: 1fr; }
  }
</style>
