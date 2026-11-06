<script>
  import { t, fmt } from './i18n.js';

  // The form is deliberately small and same-origin. The backend stores the
  // message for the shared admin inbox (#15); there is no email provider to
  // configure, and the visitor gets an answer on the page either way.
  const MESSAGE_MAX = 1000;

  let name = '';
  let contact = '';
  let subject = '';
  let message = '';
  // Honeypot. Real people never see or fill this; bots that fill every field do.
  let website = '';

  let status = 'idle'; // idle | sending | sent | error
  let error = '';

  async function submit(event) {
    event.preventDefault();
    if (status === 'sending') return;

    status = 'sending';
    error = '';
    try {
      const res = await fetch('/api/contact', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, contact, subject, message, website }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `HTTP ${res.status}`);
      }
      status = 'sent';
      name = '';
      contact = '';
      subject = '';
      message = '';
    } catch (err) {
      status = 'error';
      error = err.message;
    }
  }
</script>

<section class="contact" id="contact" aria-labelledby="contact-h">
  <div class="head">
    <h2 id="contact-h">{$t.contact.title}</h2>
    <p class="sub">{$t.contact.subtitle}</p>
  </div>

  {#if status === 'sent'}
    <p class="notice success" role="status">{$t.contact.sent}</p>
  {/if}

  <form on:submit={submit} novalidate>
    <div class="pair">
      <label>
        <span>{$t.contact.name}</span>
        <input type="text" bind:value={name} maxlength="120" autocomplete="name" required />
      </label>
      <label>
        <span>{$t.contact.contact}</span>
        <input type="text" bind:value={contact} maxlength="200" autocomplete="email" required />
      </label>
    </div>

    <label>
      <span>{$t.contact.subject}</span>
      <input type="text" bind:value={subject} maxlength="160" />
    </label>

    <label>
      <span>{$t.contact.message}</span>
      <textarea
        bind:value={message}
        rows="5"
        maxlength={MESSAGE_MAX}
        required
      ></textarea>
      <small>{fmt($t.contact.messageHint, { count: message.length })}</small>
    </label>

    <!-- Honeypot: off-screen rather than display:none, which some bots skip. -->
    <label class="hp" aria-hidden="true">
      <span>{$t.contact.honeypot}</span>
      <input type="text" bind:value={website} tabindex="-1" autocomplete="off" />
    </label>

    {#if status === 'error'}
      <p class="notice error" role="alert">{$t.contact.error}</p>
    {/if}

    <button type="submit" disabled={status === 'sending'}>
      {status === 'sending' ? $t.contact.sending : $t.contact.send}
    </button>
  </form>
</section>

<style>
  .contact { padding: 4rem 1.25rem; max-width: 42rem; margin-inline: auto; }
  .head { margin-bottom: 1.5rem; }
  .sub { margin-top: .6rem; color: #555; }
  form { display: grid; gap: 1rem; }
  .pair { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
  label { display: grid; gap: .35rem; font-size: .85rem; font-weight: 700; color: var(--deep); }
  input, textarea {
    width: 100%; padding: .7rem .8rem; border: 2px solid rgba(11, 60, 73, .25);
    border-radius: .6rem; font: inherit; font-weight: 400; color: var(--ink);
    background: #fff;
  }
  textarea { resize: vertical; min-height: 7rem; }
  input:focus, textarea:focus { outline: none; border-color: var(--deep); }
  small { font-weight: 400; color: #777; text-align: right; }
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
