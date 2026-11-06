// Svelte compiler configuration.
//
// Vite handles the build, but `svelte-check` looks for this file to know which
// preprocessor and compiler options the app uses. Keeping it minimal means the
// check uses exactly the same pipeline as `npm run build`.
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

export default {
  preprocess: vitePreprocess(),
};
