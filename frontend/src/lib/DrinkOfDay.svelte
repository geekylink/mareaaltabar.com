<script>
  import { t } from './i18n.js';
  import { pick, formatPrice } from './api.js';

  // The admin marks one menu item as the drink of the day. The menu payload is
  // already loaded by App.svelte, so this reads the flag rather than making a
  // second request. If no drink is marked the block renders nothing at all.
  export let categories = [];
  export let lang = 'en';

  $: featured = categories
    .flatMap((category) => category.items ?? [])
    .find((item) => item.is_drink_of_day && item.is_available !== false);
  $: price = featured ? formatPrice(featured.price) : '';
  $: description = featured ? pick(featured, lang, 'description') : '';
</script>

{#if featured}
  <aside class="drink" aria-labelledby="drink-of-day-h">
    <span class="eyebrow">{$t.drinkOfDay.eyebrow}</span>
    <div class="row">
      <h2 id="drink-of-day-h">{pick(featured, lang, 'name')}</h2>
      {#if price}<span class="price">{price}</span>{/if}
    </div>
    {#if description}<p>{description}</p>{/if}
    <a class="cta" href="#menu">{$t.drinkOfDay.cta}</a>
  </aside>
{/if}

<style>
  .drink {
    position: relative; z-index: 3;
    max-width: 68rem; width: 100%; margin: -.5rem auto 3rem;
    padding: 1rem 1.25rem; border-radius: 1.25rem;
    background: rgba(255, 255, 255, .16);
    border: 2px solid rgba(255, 255, 255, .5);
    backdrop-filter: blur(6px);
    color: var(--hero-ink);
  }
  .eyebrow {
    display: inline-block; font-family: var(--font-display); font-size: .72rem;
    font-weight: 800; text-transform: uppercase; letter-spacing: .1em;
    background: var(--hero-ink); color: var(--hibiscus); border-radius: 999px;
    padding: .15rem .65rem; margin-bottom: .5rem;
  }
  .row { display: flex; align-items: baseline; justify-content: space-between; gap: 1rem; flex-wrap: wrap; }
  h2 { font-size: clamp(1.5rem, 6vw, 2.2rem); }
  .price { font-weight: 800; font-size: 1.2rem; white-space: nowrap; }
  p { margin-top: .35rem; font-size: .95rem; }
  .cta { display: inline-block; margin-top: .6rem; font-size: .85rem; font-weight: 700; color: var(--hero-ink); }
</style>
