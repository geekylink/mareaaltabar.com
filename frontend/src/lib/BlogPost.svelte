<script>
  import { t } from './i18n.js';
  import { pick, formatEventDate } from './api.js';

  // One news article. The body is plain text with blank lines between
  // paragraphs, mirrored by the server-rendered article in ssr.py.
  export let post;
  export let lang = 'en';

  $: title = pick(post, lang, 'title');
  $: excerpt = pick(post, lang, 'excerpt');
  $: paragraphs = (pick(post, lang, 'body') || '')
    .split(/\n\s*\n/)
    .map((part) => part.trim())
    .filter(Boolean);
</script>

<article class="post" aria-labelledby="post-h">
  <a class="back" href="/news"><span aria-hidden="true">←</span> {$t.news.back}</a>

  <header class="head">
    <p class="eyebrow">{$t.news.title}</p>
    <p class="date">{formatEventDate(post.published_on, lang)}</p>
    <h1 id="post-h">{title}</h1>
    {#if excerpt}<p class="sub">{excerpt}</p>{/if}
  </header>

  {#if post.image_url}
    <img class="hero" src={post.image_url} alt={title} loading="lazy" decoding="async" width="1200" height="750" />
  {/if}

  <div class="body">
    {#each paragraphs as paragraph}
      <p>{paragraph}</p>
    {/each}
  </div>

  <p class="back-wrap"><a class="back" href="/news"><span aria-hidden="true">←</span> {$t.news.back}</a></p>
</article>

<style>
  .post { padding: 3rem 1.25rem 4rem; max-width: 68rem; margin-inline: auto; }
  .back { display: inline-block; margin-bottom: 1.75rem; font-weight: 700; text-decoration: none; }
  .back:hover { text-decoration: underline; }
  .head { margin-bottom: 2rem; }
  .eyebrow {
    font-size: .72rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: .14em; color: var(--accent-ink); margin: 0 0 .65rem;
  }
  .date { font-size: .8rem; font-weight: 700; text-transform: uppercase; letter-spacing: .08em; color: var(--text-soft); margin: 0 0 .5rem; }
  h1 {
    font-family: var(--font-display); font-size: clamp(2.25rem, 8vw, 4rem);
    font-weight: 800; letter-spacing: -.03em; line-height: .98; margin: 0 0 .9rem;
  }
  .sub { font-size: clamp(1rem, 2.6vw, 1.2rem); color: var(--text-muted); max-width: 44rem; line-height: 1.55; margin: 0; }
  .hero {
    display: block; width: 100%; height: auto; aspect-ratio: 16 / 10;
    object-fit: cover; border-radius: 1.1rem; margin: 0 0 2rem;
  }
  .body { max-width: 44rem; }
  .body p { font-size: 1.05rem; line-height: 1.7; margin: 0 0 1.15rem; }
  .back-wrap { margin-top: 2.5rem; }
  @media (min-width: 760px) { .post { padding-inline: 2rem; } }
</style>
