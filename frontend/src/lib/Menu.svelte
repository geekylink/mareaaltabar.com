<script>
  import { t } from './i18n.js';
  import { pick, formatPrice } from './api.js';

  // The drinks menu, as the backend returns it: categories in order, each with
  // its items and their multi-buy promos. Prices and copy live in the database
  // (admin panel: /admin/menu), so nothing about the menu is hardcoded here.
  //
  // `lang` is the visitor's language, passed in from App/MenuPage. It is read
  // inline below rather than inside a helper: App.svelte's week list once called
  // pick() through a local wrapper, which hid the dependency from Svelte's
  // compiler and left English on screen after a language switch.
  export let categories = [];
  export let lang = 'en';
  export let heading = true;
  export let subtitle = true;
  export let loading = false;
  export let id = 'menu';
</script>

<section class="menu" {id} aria-labelledby="{id}-h">
  {#if heading}
    <div class="head">
      <h2 id="{id}-h">{$t.menu.title}</h2>
      {#if subtitle}<p class="sub">{$t.menu.subtitle}</p>{/if}
    </div>
  {/if}

  <!-- While loading, nothing at all: the "menu is being updated" line is a lie
       for the second or two a fetch takes, and a visitor on a slow connection
       would read it as the answer. -->
  {#if categories.length}
    {#each categories as category (category.id)}
      <section class="cat" id={category.slug} aria-labelledby="{category.slug}-h">
        <h3 id="{category.slug}-h">{pick(category, lang, 'name')}</h3>
        <ul>
          {#each category.items as item (item.id)}
            {@const price = formatPrice(item.price)}
            {@const description = pick(item, lang, 'description')}
            {@const ingredients = pick(item, lang, 'ingredients')}
            <li class="item">
              <span class="row">
                <b>{pick(item, lang, 'name')}</b>
                {#if price}<span class="price">{price}</span>{/if}
              </span>
              {#if item.promos?.length}
                <span class="promos">
                  {#each item.promos as promo (promo.id)}
                    <span class="promo">{$t.menu.promo}: {pick(promo, lang, 'label')}</span>
                  {/each}
                </span>
              {/if}
              {#if description}<span class="desc">{description}</span>{/if}
              {#if ingredients}
                <span class="ingredients">
                  <span class="label">{$t.menu.ingredients}</span>
                  {ingredients}
                </span>
              {/if}
            </li>
          {/each}
        </ul>
      </section>
    {/each}
    <p class="note">{$t.menu.all}</p>
  {:else if !loading}
    <p class="empty">{$t.menu.empty}</p>
  {/if}
</section>

<style>
  .menu { padding: 4rem 1.25rem; max-width: 68rem; margin-inline: auto; }
  .sub { margin-top: .6rem; color: #555; }
  .empty { color: #666; }
  .cat { margin-top: 2.25rem; scroll-margin-top: 4rem; }
  .cat h3 { font-size: clamp(1.3rem, 5vw, 1.6rem); color: var(--deep); margin-bottom: .5rem; }
  .cat ul { list-style: none; padding: 0; margin: 0; }
  .item {
    display: flex; flex-direction: column; gap: .15rem;
    padding: .75rem .25rem; border-bottom: 2px solid rgba(29, 26, 23, .12);
  }
  .row { display: flex; justify-content: space-between; align-items: baseline; gap: 1rem; }
  .price { font-weight: 700; white-space: nowrap; }
  .promos { display: flex; flex-wrap: wrap; gap: .4rem; }
  .promo {
    font-size: .78rem; font-weight: 700; color: var(--deep);
    background: rgba(255, 182, 39, .35); border-radius: 999px; padding: .1rem .6rem;
  }
  .desc { font-size: .95rem; color: #444; }
  .ingredients { font-size: .85rem; color: #666; }
  .ingredients .label {
    font-family: var(--font-display); font-size: .7rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: .08em; color: var(--deep); margin-right: .35rem;
  }
  .note { margin-top: 1.5rem; font-size: .8rem; color: #888; }
  @media (min-width: 760px) {
    .menu { padding-inline: 2rem; }
  }
</style>