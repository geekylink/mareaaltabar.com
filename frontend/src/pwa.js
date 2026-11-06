// Register the service worker (ticket #31). Kept out of the components so both
// documents — `/` and `/menu` — get it, and so tests never touch navigator.
//
// Production only: Vite's dev server already reloads aggressively, and a worker
// caching dev modules makes that worse. The backend serves `/sw.js` from the
// built `public/` directory.
export function registerServiceWorker() {
  if (typeof window === 'undefined' || !('serviceWorker' in navigator)) return;
  if (!import.meta.env.PROD) return;

  const register = () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {
      // Registration is an enhancement. A failure must not break the page.
    });
  };

  if (document.readyState === 'complete') register();
  else window.addEventListener('load', register, { once: true });
}
