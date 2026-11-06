<script>
  import { onDestroy } from 'svelte';
  import Menu from './Menu.svelte';
  import NoticeBanner from './NoticeBanner.svelte';
  import Nav from './Nav.svelte';
  import InstallPrompt from './InstallPrompt.svelte';
  import { t, locale } from './i18n.js';
  import { BAR } from './data.js';
  import { load } from './api.js';

  // The standalone menu route (/menu). Same component and same data as the menu
  // section on the homepage, on a document of its own so the URL can be shared
  // and indexed separately — this is the page to post on Instagram or WhatsApp.
  let categories = [];
  let notices = [];
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
      notices = result.notices || [];
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

<a class="skip-link" href="#main">{$t.ui.skipToContent}</a>

<NoticeBanner {notices} {lang} />

<header>
  <Nav home={false} links={['surf', 'party', 'news', 'contact', 'visit']} />
</header>

<main id="main">
<div class="page-head">
  <h1>{$t.menu.title}</h1>
  <p>{$t.menu.subtitle}</p>
</div>
{#if loading && !categories.length}
  <p class="state">{$t.ui.loading}</p>
{:else if error && !categories.length}
  <p class="state">
    {$t.ui.error}
    <button type="button" class="btn" on:click={loadData}>{$t.ui.retry}</button>
  </p>
{:else}
  <Menu {categories} {lang} {loading} id="menu-top" heading={false} />
{/if}

<InstallPrompt />
</main>

<footer>{$t.menu.all}</footer>

<style>
  header {
    color: var(--hero-ink);
    background: linear-gradient(180deg, var(--hibiscus) 0%, var(--papaya) 100%);
    padding: env(safe-area-inset-top) 1.25rem 1.5rem;
  }
  .state { padding: 3rem 1.25rem; text-align: center; color: var(--text-soft); }
  .page-head { padding: 2.5rem 1.25rem .5rem; max-width: 68rem; margin-inline: auto; }
  .page-head h1 { font-size: clamp(2.25rem, 8vw, 3.75rem); font-weight: 800; letter-spacing: -.03em; }
  .page-head p { color: var(--text-muted); margin-top: .6rem; max-width: 44rem; }
  .btn {
    margin-top: 1rem; border: 0; border-radius: 999px; padding: .75rem 1.4rem;
    font: 700 1rem var(--font-body); background: var(--marigold);
    color: var(--ink); cursor: pointer;
  }
  footer { background: var(--deep); color: var(--sand); text-align: center; padding: 1.5rem 1rem; font-size: .85rem; }
  @media (min-width: 760px) {
    header { padding-inline: 2rem; }
  }
</style>
