<script>
  import { t } from './i18n.js';
  import { pick, formatEventDate } from './api.js';

  // The news index. Posts come from the database (admin panel: /admin/blog), so
  // nothing about a story is hardcoded here. `lang` is the visitor's language,
  // passed in from NewsPage.
  export let posts = [];
  export let lang = 'en';
</script>

<section class="news" aria-labelledby="news-h">
  <header class="head">
    <p class="eyebrow">{$t.news.title}</p>
    <h1 id="news-h">{$t.news.title}</h1>
    <p class="sub">{$t.news.subtitle}</p>
  </header>

  {#if !posts.length}
    <p class="empty">{$t.news.empty}</p>
  {:else}
    <div class="grid">
      {#each posts as post (post.id)}
        <article class="card">
          {#if post.image_url}
            <a class="media" href="/news/{post.slug}" tabindex="-1" aria-hidden="true">
              <img src={post.image_url} alt="" loading="lazy" decoding="async" width="640" height="400" />
            </a>
          {/if}
          <p class="date">{formatEventDate(post.published_on, lang)}</p>
          <h2><a href="/news/{post.slug}">{pick(post, lang, 'title')}</a></h2>
          {#if pick(post, lang, 'excerpt')}
            <p class="excerpt">{pick(post, lang, 'excerpt')}</p>
          {/if}
          <a class="more" href="/news/{post.slug}">{$t.news.readMore} <span aria-hidden="true">→</span></a>
        </article>
      {/each}
    </div>
  {/if}
</section>

<style>
  .news { padding: 3rem 1.25rem 4rem; max-width: 68rem; margin-inline: auto; }
  .head { margin-bottom: 2.5rem; }
  .eyebrow {
    font-size: .72rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: .14em; color: var(--accent-ink); margin: 0 0 .65rem;
  }
  h1 {
    font-family: var(--font-display); font-size: clamp(2.25rem, 8vw, 4rem);
    font-weight: 800; letter-spacing: -.03em; line-height: .98; margin: 0 0 .9rem;
  }
  .sub { font-size: clamp(1rem, 2.6vw, 1.2rem); color: var(--text-muted); max-width: 44rem; line-height: 1.55; margin: 0; }
  .empty { color: var(--text-soft); }
  .grid {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 18rem), 1fr));
    gap: 1.5rem;
  }
  .card {
    display: flex; flex-direction: column; gap: .55rem;
    background: var(--surface); border: 2px solid var(--rule);
    border-radius: 1.1rem; padding: 1.25rem;
  }
  .media { display: block; margin: -.35rem -.35rem .35rem; border-radius: .8rem; overflow: hidden; }
  .media img { display: block; width: 100%; height: auto; aspect-ratio: 16 / 10; object-fit: cover; }
  .date { font-size: .8rem; font-weight: 700; text-transform: uppercase; letter-spacing: .08em; color: var(--text-soft); margin: 0 0 .1rem; }
  h2 { font-family: var(--font-display); font-size: 1.5rem; line-height: 1.1; margin: 0; }
  h2 a { text-decoration: none; }
  h2 a:hover { text-decoration: underline; }
  .excerpt { color: var(--text-muted); line-height: 1.55; margin: 0; }
  .more { margin-top: auto; padding-top: .35rem; font-weight: 700; text-decoration: none; }
  .more:hover { text-decoration: underline; }
  @media (min-width: 760px) { .news { padding-inline: 2rem; } }
</style>
