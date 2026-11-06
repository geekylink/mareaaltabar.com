<script>
  import { t, locale, LANGS } from './i18n.js';
  import { theme, toggleTheme } from './theme.js';
  import { BAR } from './data.js';

  // One navigation for both documents. On the homepage the links are in-page
  // anchors; on `/menu` they point back at the homepage anchors, because that
  // page is a document of its own. `links` is passed in so the menu page can
  // drop the "Menu" item it is already on.
  export let home = true;
  export let links = ['surf', 'party', 'menu', 'contact', 'visit'];

  $: href = (key) => (home ? `#${key}` : `/#${key}`);
</script>

<nav aria-label={$t.ui.mainNav}>
  <a class="logo" href={home ? '#top' : '/'}>{BAR.name}</a>
  <div class="right">
    <div class="links">
      {#each links as key (key)}
        <a href={href(key)}>{$t.nav[key]}</a>
      {/each}
    </div>
    <button
      type="button"
      class="theme"
      on:click={toggleTheme}
      aria-label={$theme === 'dark' ? $t.ui.switchToLight : $t.ui.switchToDark}
      title={$theme === 'dark' ? $t.ui.switchToLight : $t.ui.switchToDark}
    >
      {#if $theme === 'dark'}
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">
          <circle cx="12" cy="12" r="4" />
          <path d="M12 2v2M12 20v2M4.93 4.93l1.42 1.42M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.42-1.42M17.66 6.34l1.41-1.41" />
        </svg>
      {:else}
        <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
          <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z" />
        </svg>
      {/if}
    </button>
    <select class="lang" bind:value={$locale} aria-label={$t.ui.language}>
      {#each LANGS as l}<option value={l.code}>{l.label}</option>{/each}
    </select>
  </div>
</nav>

<style>
  nav {
    position: relative; z-index: 3;
    display: flex; justify-content: space-between; align-items: center;
    gap: 1rem; padding: 1.1rem 0;
    max-width: 68rem; width: 100%; margin-inline: auto;
  }
  .logo { font: 800 clamp(1.1rem, 4.5vw, 1.35rem) var(--font-display); text-decoration: none; }
  .right { display: flex; align-items: center; gap: .8rem; }
  .links { display: flex; gap: .9rem; font-size: .95rem; }
  .links a { text-decoration: none; font-weight: 700; position: relative; padding-block: .25rem; }
  .links a::after {
    content: ''; position: absolute; left: 0; bottom: 0; height: 2px; width: 100%;
    background: currentColor; transform: scaleX(0); transform-origin: left;
    transition: transform .3s var(--ease);
  }
  .links a:hover::after { transform: scaleX(1); }
  .theme {
    display: inline-grid; place-items: center;
    width: 2.1rem; height: 2.1rem; padding: 0; cursor: pointer;
    border-radius: 999px; border: 2px solid rgba(255, 255, 255, .75);
    background: rgba(255, 255, 255, .15); color: var(--hero-ink);
    transition: background-color .25s var(--ease), transform .2s var(--ease);
  }
  .theme:hover { background: rgba(255, 255, 255, .32); }
  .theme:active { transform: scale(.95); }
  .theme svg { display: block; width: 1rem; height: 1rem; }
  .lang {
    appearance: none; -webkit-appearance: none; cursor: pointer; color: var(--hero-ink);
    font: 700 .9rem var(--font-body); padding: .3rem 1.6rem .3rem .75rem; border-radius: 999px;
    border: 2px solid rgba(255, 255, 255, .75); background-color: rgba(255, 255, 255, .15);
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M1 1l4 4 4-4' fill='none' stroke='white' stroke-width='2' stroke-linecap='round'/%3E%3C/svg%3E");
    background-repeat: no-repeat; background-position: right .6rem center;
    transition: background-color .25s var(--ease), transform .2s var(--ease);
  }
  .lang:hover { background-color: rgba(255, 255, 255, .32); }
  .lang:active { transform: scale(.95); }
  .lang option { color: var(--ink); }
  @media (min-width: 760px) {
    .links { gap: 1.25rem; font-size: 1.05rem; }
    .right { gap: 1.25rem; }
  }
</style>
