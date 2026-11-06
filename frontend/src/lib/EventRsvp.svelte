<script>
  import { t } from './i18n.js';

  // A free RSVP, separate from the table request in Reservation.svelte. The
  // backend caps the party at 20; the form mirrors that so the visitor sees the
  // limit before submitting. There is no payment and no ticket — the bar only
  // uses this to gauge the crowd.
  const MAX_GUESTS = 20;

  export let eventId;

  let name = '';
  let contact = '';
  let partySize = 2;
  let notes = '';
  // Honeypot. Real people never see or fill this; bots that fill every field do.
  let website = '';

  let status = 'idle'; // idle | sending | sent | error
  let error = '';

  async function submit(evt) {
    evt.preventDefault();
    if (status === 'sending') return;

    if (!name.trim() || !contact.trim()) {
      status = 'error';
      error = $t.rsvp.required;
      return;
    }

    status = 'sending';
    error = '';
    try {
      const res = await fetch(`/api/special-events/${eventId}/rsvp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name.trim(),
          contact: contact.trim(),
          party_size: Number(partySize),
          notes: notes.trim(),
          website,
        }),
      });
      if (!res.ok) throw new Error('rsvp failed');
      status = 'sent';
      name = '';
      contact = '';
      notes = '';
      website = '';
    } catch (err) {
      status = 'error';
      error = $t.rsvp.error;
    }
  }
</script>

<details class="rsvp">
  <summary>{$t.rsvp.open}</summary>

  {#if status === 'sent'}
    <p class="notice success" role="status">{$t.rsvp.sent}</p>
  {:else}
    <p class="hint">{$t.rsvp.subtitle}</p>
    <form on:submit={submit} novalidate>
      <div class="pair">
        <label>
          <span>{$t.rsvp.name}</span>
          <input type="text" bind:value={name} maxlength="120" autocomplete="name" required />
        </label>
        <label>
          <span>{$t.rsvp.contact}</span>
          <input type="text" bind:value={contact} maxlength="200" autocomplete="email" required />
        </label>
      </div>

      <label>
        <span>{$t.rsvp.partySize}</span>
        <input type="number" bind:value={partySize} min="1" max={MAX_GUESTS} step="1" required />
      </label>

      <label>
        <span>{$t.rsvp.notes}</span>
        <textarea bind:value={notes} rows="2" maxlength="1000"></textarea>
      </label>

      <!-- Honeypot: off-screen rather than display:none, which some bots skip. -->
      <label class="hp" aria-hidden="true">
        <span>{$t.rsvp.honeypot}</span>
        <input type="text" bind:value={website} tabindex="-1" autocomplete="off" />
      </label>

      {#if status === 'error'}
        <p class="notice error" role="alert">{error}</p>
      {/if}

      <button type="submit" disabled={status === 'sending'}>
        {status === 'sending' ? $t.rsvp.sending : $t.rsvp.send}
      </button>
    </form>
  {/if}
</details>

<style>
  .rsvp {
    margin-top: .75rem; border-top: 1px dashed var(--rule);
    padding-top: .6rem;
  }
  summary {
    cursor: pointer; font-size: .85rem; font-weight: 700; color: var(--accent-ink);
    list-style-position: inside;
  }
  summary:hover { color: var(--papaya); }
  .hint { margin: .6rem 0; font-size: .8rem; color: var(--text-soft); }
  form { display: grid; gap: .7rem; max-width: 34rem; }
  .pair { display: grid; grid-template-columns: 1fr 1fr; gap: .7rem; }
  label { display: grid; gap: .3rem; font-size: .8rem; font-weight: 700; color: var(--accent-ink); }
  input, textarea {
    width: 100%; padding: .55rem .65rem; border: 2px solid var(--field-border);
    border-radius: .5rem; font: inherit; font-weight: 400; color: var(--text);
    background: var(--surface);
  }
  textarea { resize: vertical; min-height: 3.5rem; }
  input:focus, textarea:focus { outline: none; border-color: var(--accent-ink); }
  button {
    justify-self: start; border: none; border-radius: 999px; padding: .6rem 1.2rem;
    background: var(--accent-bg); color: var(--accent-contrast); font: inherit; font-weight: 700;
    font-size: .85rem; cursor: pointer; transition: transform .25s var(--ease), background .25s;
  }
  button:hover { transform: translateY(-2px); background: var(--papaya); }
  button:disabled { opacity: .65; cursor: not-allowed; transform: none; }
  .notice { padding: .6rem .8rem; border-radius: .5rem; font-size: .85rem; }
  .success { background: var(--success-bg); color: var(--success-ink); }
  .error { background: var(--error-bg); color: var(--error-ink); }
  .hp {
    position: absolute; left: -9999px; width: 1px; height: 1px;
    overflow: hidden; opacity: 0; pointer-events: none;
  }
  @media (max-width: 620px) {
    .pair { grid-template-columns: 1fr; }
  }
</style>
