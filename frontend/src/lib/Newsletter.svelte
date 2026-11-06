<script>
  import { t } from './i18n.js';

  // Signup for the newsletter. The backend stores the address with the consent
  // timestamp; there is no email provider yet, so this form is the whole public
  // surface. Consent is explicit and the honeypot is the same one the contact
  // form uses.
  let email = '';
  let name = '';
  let consent = false;
  let website = '';
  let status = 'idle'; // idle | sending | sent | error
  let error = '';

  function looksLikeEmail(value) {
    return /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(value);
  }

  async function submit(event) {
    event.preventDefault();
    if (status === 'sending') return;

    if (!looksLikeEmail(email.trim())) {
      status = 'error';
      error = $t.newsletter.emailError;
      return;
    }
    if (!consent) {
      status = 'error';
      error = $t.newsletter.consentError;
      return;
    }

    status = 'sending';
    error = '';
    try {
      const res = await fetch('/api/newsletter', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: email.trim(),
          name: name.trim(),
          consent,
          website,
        }),
      });
      if (!res.ok) throw new Error('newsletter signup failed');
      status = 'sent';
      email = '';
      name = '';
      consent = false;
    } catch (err) {
      status = 'error';
      error = $t.newsletter.error;
    }
  }
</script>

<section class="newsletter" id="newsletter" aria-labelledby="newsletter-h">
  <div class="head">
    <h2 id="newsletter-h">{$t.newsletter.title}</h2>
    <p class="sub">{$t.newsletter.subtitle}</p>
  </div>

  {#if status === 'sent'}
    <p class="notice success" role="status">{$t.newsletter.sent}</p>
  {:else}
    <form on:submit={submit} novalidate>
      <div class="pair">
        <label>
          <span>{$t.newsletter.email}</span>
          <input
            type="email"
            bind:value={email}
            maxlength="254"
            autocomplete="email"
            required
          />
        </label>
        <label>
          <span>{$t.newsletter.name}</span>
          <input type="text" bind:value={name} maxlength="120" autocomplete="name" />
        </label>
      </div>

      <label class="consent">
        <input type="checkbox" bind:checked={consent} />
        <span>{$t.newsletter.consent}</span>
      </label>

      <!-- Honeypot: off-screen rather than display:none, which some bots skip. -->
      <label class="hp" aria-hidden="true">
        <span>{$t.newsletter.honeypot}</span>
        <input type="text" bind:value={website} tabindex="-1" autocomplete="off" />
      </label>

      {#if status === 'error'}
        <p class="notice error" role="alert">{error}</p>
      {/if}

      <button type="submit" disabled={status === 'sending'}>
        {status === 'sending' ? $t.newsletter.sending : $t.newsletter.send}
      </button>
      <small>{$t.newsletter.privacy}</small>
    </form>
  {/if}
</section>

<style>
  .newsletter {
    padding: 4rem 1.25rem; max-width: 42rem; margin-inline: auto;
    border-top: 2px solid rgba(29, 26, 23, .1);
  }
  .head { margin-bottom: 1.5rem; }
  .sub { margin-top: .6rem; color: #555; }
  form { display: grid; gap: 1rem; }
  .pair { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
  label { display: grid; gap: .35rem; font-size: .85rem; font-weight: 700; color: var(--deep); }
  .consent {
    display: flex; align-items: flex-start; gap: .6rem;
    font-size: .9rem; font-weight: 400; color: var(--ink); line-height: 1.45;
  }
  .consent input { width: auto; margin-top: .2rem; accent-color: var(--deep); }
  input[type="email"], input[type="text"] {
    width: 100%; padding: .7rem .8rem; border: 2px solid rgba(11, 60, 73, .25);
    border-radius: .6rem; font: inherit; font-weight: 400; color: var(--ink);
    background: #fff;
  }
  input:focus { outline: none; border-color: var(--deep); }
  small { font-weight: 400; color: #777; }
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
