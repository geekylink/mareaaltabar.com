import './app.css';
import MenuPage from './lib/MenuPage.svelte';
import { mount } from 'svelte';
import { registerServiceWorker } from './pwa.js';

registerServiceWorker();

const target = document.getElementById('app');

// Same contract as main.js: the backend renders the menu into #app for crawlers
// (see backend/app/ssr.py) and the app replaces that block on mount. `mount()`
// appends rather than replaces, so clear it first or visitors see the menu twice.
target.innerHTML = '';

export default mount(MenuPage, { target });