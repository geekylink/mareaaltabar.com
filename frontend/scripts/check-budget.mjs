// Build-size budget (ticket #34).
//
// Lighthouse on a coastal mobile connection is mostly a JavaScript and CSS
// question. These limits are deliberately generous against today's build (they
// catch a doubling, not a one-kilobyte regression) so a component import that
// drags in a second framework fails CI instead of quietly shipping to a phone
// on 3G. Sizes are gzipped, because that is what crosses the wire.
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { gzipSync } from 'node:zlib';

const DIST = new URL('../dist/assets/', import.meta.url);
const LIMITS = {
  totalJs: 80 * 1024,
  totalCss: 16 * 1024,
  largestChunk: 40 * 1024,
};

const files = readdirSync(DIST)
  .filter((name) => /\.(js|css)$/.test(name))
  .map((name) => {
    const path = new URL(name, DIST);
    const bytes = statSync(path).size;
    const gzip = gzipSync(readFileSync(path)).length;
    return { name, bytes, gzip, kind: name.endsWith('.js') ? 'js' : 'css' };
  })
  .sort((a, b) => b.gzip - a.gzip);

if (!files.length) {
  console.error('No JS or CSS in dist/assets — run `npm run build` first.');
  process.exit(1);
}

const total = (kind) => files.filter((file) => file.kind === kind).reduce((sum, file) => sum + file.gzip, 0);
const largest = files[0];
const failures = [];

for (const file of files) {
  console.log(`${file.gzip.toString().padStart(7)} B  ${file.kind.padEnd(3)}  ${file.name}`);
}

console.log(`\nJS  ${total('js')} B gzipped (limit ${LIMITS.totalJs})`);
console.log(`CSS ${total('css')} B gzipped (limit ${LIMITS.totalCss})`);
console.log(`Largest chunk: ${largest.gzip} B ${largest.name} (limit ${LIMITS.largestChunk})`);

if (total('js') > LIMITS.totalJs) failures.push('JavaScript budget exceeded');
if (total('css') > LIMITS.totalCss) failures.push('CSS budget exceeded');
if (largest.gzip > LIMITS.largestChunk) failures.push('Single-chunk budget exceeded');

if (failures.length) {
  for (const failure of failures) console.error(`FAIL: ${failure}`);
  process.exit(1);
}
