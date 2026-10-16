<script>
  import { onDestroy } from 'svelte';
  import Menu from './Menu.svelte';
  import { t, locale, LANGS } from './i18n.js';
  import { BAR } from './data.js';
  import { load } from './api.js';

  // The standalone menu route (/menu). Same component and same data as the menu
  // section on the homepage, on a document of its own so the URL can be shared
  // and indexed separately — this is the page to post on Instagram or WhatsApp.
  let categories = [];
  let loading = true;
  let error = null;

  $: lang = $locale;
  $: if (typeof document !== 'undefined') {
    document.documentElement.lang = $locale;
    document.title = `${$t.menu.title} · ${BAR.full}`;
  }

  async function loadData() {
    loading = true;
    error = null;
    try {
      const result = await load();
      categories = result.menu;
    } catch (err) {
      error = err.message;
    } finally {
      loading = false;
    }
  }

  loadData();
  const refreshTimer = setInterval(loadData, 60 * 60 * 1000);
  onDestroy(() => clearInterval(refreshTimer));
</script>

<header>
  <nav aria-label={$t.ui.mainNav}>
    <a class="logo" href="/">{BAR.name}</a>
    <div class="right">
      <div class="links">
        <a href="/#surf">{$t.nav.surf}</a>
        <a href="/#party">{$t.nav.party}</a>
        <a href="/#visit">{$t.nav.visit}</a>
      </div>
      <select class="lang" bind:value={$locale} aria-label={$t.ui.language}>
        {#each LANGS as l}<option value={l.code}>{l.label}</option>{/each}
      </select>
    </div>
  </nav>
</header>

{#if loading && !categories.length}
  <p class="state">{$t.ui.loading}</p>
{:else if error && !categories.length}
  <p class="state">
    {$t.ui.error}
    <button class="btn" on:click={loadData}>{$t.ui.retry}</button>
  </p>
{:else}
  <Menu {categories} {lang} {loading} id="menu-top" heading={false} />
{/if}

<footer>{$t.menu.all}</footer>

<style>
  header {
    color: #fff;
    background: linear-gradient(180deg, var(--hibiscus) 0%, var(--papaya) 100%);
    padding: env(safe-area-inset-top) 1.25rem 1.5rem;
  }
  nav {
    display: flex; justify-content: space-between; align-items: center;
    max-width: 68rem; width: 100%; margin-inline: auto;
  }
  .logo { font: 800 clamp(1.1rem, 4.5vw, 1.35rem) var(--font-display); text-decoration: none; }
  .right { display: flex; align-items: center; gap: .8rem; }
  .links { display: flex; gap: .9rem; font-size: .95rem; }
  .links a { text-decoration: none; font-weight: 700; }
  .lang {
    appearance: none; -webkit-appearance: none; cursor: pointer; color: #fff;
    font: 700 .9rem var(--font-body); padding: .3rem 1.6rem .3rem .75rem; border-radius: 999px;
    border: 2px solid rgba(255, 255, 255, .75); background-color: rgba(255, 255, 255, .15);
  }
  .lang option { color: var(--ink); }
  .state { padding: 3rem 1.25rem; text-align: center; color: #666; }
  .btn {
    margin-top: 1rem; border: 0; border-radius: 999px; padding: .75rem 1.4rem;
    font: 700 1rem var(--font-body); background: var(--marigold);
    color: var(--ink); cursor: pointer;
  }
  footer { background: var(--deep); color: var(--sand); text-align: center; padding: 1.5rem 1rem; font-size: .85rem; }
  @media (min-width: 760px) {
    header { padding-inline: 2rem; }
    .links { gap: 1.25rem; }
  }
</style>