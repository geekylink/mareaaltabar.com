<script>
  import { pick } from './api.js';

  // Emergency notices published from /admin/notices. The list is already
  // filtered server-side to the notices that are switched on and inside their
  // window, so this component renders whatever it is given.
  export let notices = [];
  export let lang = 'en';

  const SEVERITIES = ['info', 'warning', 'critical'];

  function severityOf(notice) {
    return SEVERITIES.includes(notice?.severity) ? notice.severity : 'info';
  }
</script>

{#if notices && notices.length}
  <div class="notices">
    {#each notices as notice, index (notice.id ?? index)}
      <div
        class="notice notice-{severityOf(notice)}"
        role={severityOf(notice) === 'critical' ? 'alert' : 'status'}
      >
        <p>{pick(notice, lang, 'message')}</p>
      </div>
    {/each}
  </div>
{/if}

<style>
  .notices {
    display: grid;
    gap: 2px;
  }
  .notice {
    padding: 0.9rem 1.25rem;
    color: #fff;
  }
  .notice p {
    max-width: 68rem;
    margin: 0 auto;
    font-weight: 700;
    text-align: center;
    line-height: 1.4;
    white-space: pre-wrap;
  }
  .notice-info { background: #0b3c49; }
  .notice-warning { background: #b45309; }
  .notice-critical { background: #991b1b; }
</style>
