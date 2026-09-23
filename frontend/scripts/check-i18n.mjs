#!/usr/bin/env node
/**
 * Reports translation coverage per locale against `en.json` (the source of
 * truth). Missing keys are a warning, not an error — English is always the
 * fallback — but EXTRA keys are an error, because they are almost always typos
 * or leftovers from a renamed key.
 */
import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';

const DIR = join(process.cwd(), 'src/i18n/locales');
const BASE = 'en';

const flatten = (obj, prefix = '') =>
  Object.entries(obj).flatMap(([k, v]) => {
    if (k.startsWith('_')) return []; // `_meta` blocks are not translations
    const key = prefix ? `${prefix}.${k}` : k;
    return v && typeof v === 'object' && !Array.isArray(v) ? flatten(v, key) : [key];
  });

const read = (code) => JSON.parse(readFileSync(join(DIR, `${code}.json`), 'utf8'));

const baseKeys = new Set(flatten(read(BASE)));
const locales = readdirSync(DIR)
  .filter((f) => f.endsWith('.json'))
  .map((f) => f.replace('.json', ''))
  .filter((c) => c !== BASE)
  .sort();

let hasError = false;
console.log(`\ni18n coverage — baseline ${BASE}.json has ${baseKeys.size} keys\n`);

for (const code of locales) {
  const keys = new Set(flatten(read(code)));
  const missing = [...baseKeys].filter((k) => !keys.has(k));
  const extra = [...keys].filter((k) => !baseKeys.has(k));
  const pct = Math.round(((baseKeys.size - missing.length) / baseKeys.size) * 100);

  console.log(`  ${code}  ${String(pct).padStart(3)}%  (${missing.length} missing)`);

  if (extra.length) {
    hasError = true;
    console.error(`      ✗ ${extra.length} key(s) not in ${BASE}.json: ${extra.slice(0, 8).join(', ')}`);
  }
}

console.log('\nMissing keys fall back to English — that is expected for partial locales.');
if (hasError) {
  console.error('\nFAILED: remove or rename the unknown keys listed above.\n');
  process.exit(1);
}
console.log('OK\n');
