<script>
  import { t, fmt } from './i18n.js';
  import { pick, formatPrice } from './api.js';
  import { QUESTIONS, recommend } from './quizRules.js';

  // Three questions, then one drink from the menu the visitor already loaded.
  // The rules score the live categories, so a removed or unavailable drink can
  // never be recommended. The result is deliberately not persisted: this is a
  // bit of fun, not a profile.
  export let categories = [];
  export let lang = 'en';

  let step = -1; // -1 intro, 0..n-1 questions, n result
  let answers = {};
  let result = null;
  let shared = false;

  $: total = QUESTIONS.length;

  function choose(option) {
    answers = { ...answers, [QUESTIONS[step].id]: option };
    if (step + 1 < total) {
      step += 1;
    } else {
      result = recommend(categories, answers);
      step = total;
    }
  }

  function back() {
    if (step > 0) step -= 1;
    else step = -1;
  }

  function restart() {
    step = -1;
    answers = {};
    result = null;
    shared = false;
  }

  async function share() {
    if (!result) return;
    const name = pick(result.item, lang, 'name');
    const text = `${name} · ${$t.quiz.title} · Marea Alta`;
    const url = typeof window !== 'undefined' ? window.location.href : '';

    try {
      if (navigator.share) {
        await navigator.share({ title: $t.quiz.resultTitle, text, url });
        return;
      }
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(url ? `${text} ${url}` : text);
        shared = true;
      }
    } catch {
      // The visitor dismissed the share sheet; nothing to report.
    }
  }
</script>

<section class="quiz" id="quiz" aria-labelledby="quiz-h">
  <div class="head">
    <h2 id="quiz-h">{$t.quiz.title}</h2>
    <p class="sub">{$t.quiz.subtitle}</p>
  </div>

  {#if step === -1}
    <button type="button" class="primary" on:click={() => (step = 0)}>{$t.quiz.start}</button>
  {:else if step < total}
    {@const question = QUESTIONS[step]}
    {@const copy = $t.quiz.questions[question.id]}
    <p class="progress">{fmt($t.quiz.question, { n: step + 1, total })}</p>
    <h3>{copy.label}</h3>
    <div class="options">
      {#each question.options as option (option)}
        <button type="button" on:click={() => choose(option)}>{copy.options[option]}</button>
      {/each}
    </div>
    {#if step > 0}
      <button type="button" class="back" on:click={back}>{$t.quiz.back}</button>
    {/if}
  {:else if result}
    {@const name = pick(result.item, lang, 'name')}
    {@const description = pick(result.item, lang, 'description')}
    {@const ingredients = pick(result.item, lang, 'ingredients')}
    {@const price = formatPrice(result.item.price)}
    {@const categoryName = pick(result.category, lang, 'name')}
    <div class="result">
      <p class="eyebrow">{$t.quiz.resultTitle}</p>
      <h3>{name}</h3>
      <p class="meta">{categoryName}{#if price} · {price}{/if}</p>
      {#if description}<p>{description}</p>{/if}
      {#if ingredients}<p class="ingredients">{ingredients}</p>{/if}
    </div>
    <div class="actions">
      <button type="button" class="primary" on:click={share}>{$t.quiz.share}</button>
      <button type="button" class="back" on:click={restart}>{$t.quiz.retry}</button>
    </div>
    {#if shared}<p class="copied" role="status">{$t.quiz.copied}</p>{/if}
  {:else}
    <p class="empty">{$t.quiz.resultEmpty}</p>
    <button type="button" class="back" on:click={restart}>{$t.quiz.retry}</button>
  {/if}
</section>

<style>
  .quiz {
    padding: 4rem 1.25rem; max-width: 42rem; margin-inline: auto;
    border-top: 2px solid var(--rule-soft);
  }
  .head { margin-bottom: 1.5rem; }
  .sub { margin-top: .6rem; color: var(--text-muted); }
  .progress {
    font-size: .75rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: .08em; color: var(--accent-ink); margin-bottom: .35rem;
  }
  h3 { font-size: clamp(1.3rem, 5vw, 1.7rem); color: var(--accent-ink); }
  .options { display: grid; gap: .6rem; margin-top: 1rem; }
  .options button {
    text-align: left; border: 2px solid var(--field-border); border-radius: .7rem;
    padding: .85rem 1rem; background: var(--surface); color: var(--text); font: inherit;
    font-weight: 600; cursor: pointer; transition: border-color .2s, background .2s, transform .2s;
  }
  .options button:hover { border-color: var(--accent-ink); background: var(--surface-warm); transform: translateX(4px); }
  .primary {
    justify-self: start; border: none; border-radius: 999px; padding: .85rem 1.6rem;
    background: var(--accent-bg); color: var(--accent-contrast); font: inherit; font-weight: 700;
    cursor: pointer; transition: transform .25s var(--ease), background .25s;
  }
  .primary:hover { transform: translateY(-2px); background: var(--papaya); }
  .back {
    margin-top: 1rem; border: none; background: none; color: var(--accent-ink);
    font: inherit; font-weight: 700; font-size: .85rem; text-decoration: underline;
    cursor: pointer; padding: 0;
  }
  .result {
    margin-top: 1.25rem; padding: 1.25rem; border-radius: 1rem;
    background: var(--surface-warm); border-left: 4px solid var(--papaya);
  }
  .eyebrow {
    font-size: .72rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: .08em; color: var(--accent-ink);
  }
  .result h3 { margin-top: .15rem; }
  .meta { margin-top: .2rem; font-size: .85rem; font-weight: 700; color: var(--text-soft); }
  .result p { margin-top: .5rem; font-size: .92rem; }
  .ingredients { color: var(--text-soft); font-size: .85rem !important; }
  .actions { display: flex; flex-wrap: wrap; align-items: center; gap: 1rem; margin-top: 1.25rem; }
  .actions .back { margin-top: 0; }
  .copied { margin-top: .75rem; font-size: .85rem; color: var(--success-ink); }
  .empty { color: var(--text-soft); }
  @media (min-width: 760px) {
    .quiz { padding-inline: 2rem; }
  }
</style>
