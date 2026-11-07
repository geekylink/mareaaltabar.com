import './fonts.css';
import './app.css';
import NewsPage from './lib/NewsPage.svelte';
import { mount } from 'svelte';
import { registerServiceWorker } from './pwa.js';

registerServiceWorker();

const target = document.getElementById('app');

// Same contract as main.js and menu-main.js: the backend renders the news into
// #app for crawlers (see backend/app/ssr.py) and the app replaces that block on
// mount. `mount()` appends rather than replaces, so clear it first.
target.innerHTML = '';

export default mount(NewsPage, { target });
