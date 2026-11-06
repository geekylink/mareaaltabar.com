<script>
  import Blog from './Blog.svelte';
  import BlogPost from './BlogPost.svelte';
  import NoticeBanner from './NoticeBanner.svelte';
  import Nav from './Nav.svelte';
  import InstallPrompt from './InstallPrompt.svelte';
  import { t, locale } from './i18n.js';
  import { BAR } from './data.js';
  import { loadNews, loadPost, pick } from './api.js';

  // The standalone news document. `/news` is the index and `/news/<slug>` is one
  // article; both use this component, and the backend renders the same content
  // into the HTML first for crawlers and visitors without JavaScript.
  function slugFromPath() {
    if (typeof window === 'undefined') return null;
    const match = window.location.pathname.match(/^\/news\/([^/]+)\/?$/);
    return match ? decodeURIComponent(match[1]) : null;
  }

  const slug = slugFromPath();
  let posts = [];
  let post = null;
  let notices = [];
  let loading = true;
  let error = null;
  let notFound = false;

  $: lang = $locale;
  $: pageTitle = post
    ? `${pick(post, lang, 'title')} · ${BAR.full}`
    : notFound
      ? `${$t.news.notFound} · ${BAR.full}`
      : `${$t.news.title} · ${BAR.full}`;
  $: pageDescription = post
    ? pick(post, lang, 'excerpt') || pick(post, lang, 'title')
    : $t.news.subtitle;
  $: if (typeof document !== 'undefined') document.documentElement.lang = $locale;

  async function loadData() {
    loading = true;
    error = null;
    notFound = false;
    try {
      if (slug) {
        const result = await loadPost(slug);
        post = result.post;
        notices = result.notices || [];
        notFound = !post;
      } else {
        const result = await loadNews();
        posts = result.posts || [];
        notices = result.notices || [];
      }
    } catch (err) {
      error = err.message;
    } finally {
      loading = false;
    }
  }

  loadData();
</script>

<svelte:head>
  <title>{pageTitle}</title>
  <meta name="description" content={pageDescription} />
</svelte:head>

<NoticeBanner {notices} {lang} />

<header>
  <Nav home={false} links={['surf', 'party', 'menu', 'contact', 'visit']} />
</header>

<main>
  {#if loading && !post && !posts.length && !notFound}
    <p class="state">{$t.ui.loading}</p>
  {:else if error}
    <div class="state">
      <p>{$t.news.error}</p>
      <button class="btn" on:click={loadData}>{$t.news.retry}</button>
    </div>
  {:else if notFound}
    <div class="state not-found">
      <p class="eyebrow">{$t.news.title}</p>
      <h1>{$t.news.notFound}</h1>
      <p>{$t.news.notFoundHint}</p>
      <a class="btn" href="/news">{$t.news.back}</a>
    </div>
  {:else if post}
    <BlogPost {post} {lang} />
  {:else}
    <Blog {posts} {lang} />
  {/if}
</main>

<InstallPrompt />

<footer>{$t.news.title} · {BAR.full}</footer>

<style>
  header {
    color: var(--hero-ink);
    background: linear-gradient(180deg, var(--hibiscus) 0%, var(--papaya) 100%);
    padding: env(safe-area-inset-top) 1.25rem 1.5rem;
  }
  .state { padding: 4rem 1.25rem; text-align: center; color: var(--text-soft); max-width: 44rem; margin-inline: auto; }
  .not-found h1 {
    font-family: var(--font-display); font-size: clamp(2rem, 7vw, 3.25rem);
    line-height: 1; color: var(--text); margin: .4rem 0 1rem;
  }
  .not-found p { line-height: 1.6; margin-bottom: 1.25rem; }
  .eyebrow {
    font-size: .72rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: .14em; color: var(--accent-ink);
  }
  .btn {
    display: inline-block; border: 0; border-radius: 999px; padding: .75rem 1.4rem;
    font: 700 1rem var(--font-body); background: var(--marigold);
    color: var(--ink); cursor: pointer; text-decoration: none;
  }
  footer { background: var(--deep); color: var(--sand); text-align: center; padding: 1.5rem 1rem; font-size: .85rem; }
  @media (min-width: 760px) { header { padding-inline: 2rem; } }
</style>
