import { writable } from 'svelte/store';
// 0 = lowest tide of the next 48h, 1 = highest. Drives the hero water level.
export const tideLevel = writable(0.5);
