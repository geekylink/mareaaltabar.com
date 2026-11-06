<script>
  import { onMount } from 'svelte';
  import { t } from './i18n.js';

  // Chromium fires `beforeinstallprompt` when the site meets the PWA criteria.
  // Other browsers never fire it, so the strip simply never renders there; there
  // is no fake "install" button for a prompt the browser will not show.
  let deferred = null;

  onMount(() => {
    const onPrompt = (event) => {
      event.preventDefault();
      deferred = event;
    };
    const onInstalled = () => {
      deferred = null;
    };

    window.addEventListener('beforeinstallprompt', onPrompt);
    window.addEventListener('appinstalled', onInstalled);
    return () => {
      window.removeEventListener('beforeinstallprompt', onPrompt);
      window.removeEventListener('appinstalled', onInstalled);
    };
  });

  async function install() {
    if (!deferred) return;
    const prompt = deferred;
    // Hide the strip as soon as the browser prompt opens; it can only be used
    // once, and a second click would do nothing.
    deferred = null;
    prompt.prompt();
    try {
      await prompt.userChoice;
    } catch {
      // The visitor closed the prompt or the browser refused it. Nothing to do.
    }
  }
</script>

{#if deferred}
  <aside class="install" aria-label={$t.install.title}>
    <p>{$t.install.text}</p>
    <button type="button" on:click={install}>{$t.install.button}</button>
  </aside>
{/if}

<style>
  .install {
    display: flex; align-items: center; justify-content: center; gap: 1rem;
    flex-wrap: wrap; padding: 1rem 1.25rem; background: var(--surface-warm);
    border-top: 2px solid var(--rule);
  }
  .install p { margin: 0; font-size: .9rem; color: var(--accent-ink); font-weight: 600; }
  button {
    border: none; border-radius: 999px; padding: .55rem 1.1rem;
    background: var(--accent-bg); color: var(--accent-contrast); font: inherit; font-weight: 700;
    font-size: .85rem; cursor: pointer; transition: transform .2s var(--ease), background .2s;
  }
  button:hover { transform: translateY(-2px); background: var(--papaya); }
</style>
