import './app.css';
import App from './App.svelte';
import { mount } from 'svelte';

const target = document.getElementById('app');

// The backend renders the schedule into #app so crawlers (and visitors without
// JavaScript) see the hours and party titles in the HTML. The app replaces that
// block on mount — `mount()` appends rather than replaces, so clear it first.
// Both happen in the same tick, so nothing flashes.
target.innerHTML = '';

export default mount(App, { target });
