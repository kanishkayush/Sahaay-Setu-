# lang-extend

**Filling in a partial locale needs no code changes — copy the missing keys from `en.json`,
translate, re-run the check.**

## Why it matters

`mr`, `bn`, `ta` and `te` sit at ~20%. Everything else falls back to English, which works but
is not the promise the app makes. This is the highest-value, lowest-risk contribution someone
with the language can make — no build config, no schema change, no chance of breaking a screen.

## Steps

```bash
npm run i18n:check
```

```
  ta   20%  (185 missing)
```

To list exactly what is missing:

```bash
node -e "
const flat=(o,p='')=>Object.entries(o).flatMap(([k,v])=>k.startsWith('_')?[]:
  (v&&typeof v==='object'&&!Array.isArray(v)?flat(v,p?p+'.'+k:k):[p?p+'.'+k:k]));
const r=c=>JSON.parse(require('fs').readFileSync('src/i18n/locales/'+c+'.json','utf8'));
const have=new Set(flat(r(process.argv[1])));
console.log(flat(r('en')).filter(k=>!have.has(k)).join('\n'));
" ta
```

Copy those keys from `en.json`, keeping the nesting, and translate.

```bash
npm run i18n:check   # coverage should rise
npm run verify
```

## Wrong

```jsonc
// flattening the nesting
{ "recommender.title": "…" } // ← keySeparator is '.', so this creates a literal key
```

```jsonc
// translating a placeholder
{ "resultsSubtitle": "{{गिनती}} योजनाएँ मिलीं" } // ← renders literally, never substituted
```

```jsonc
// translating an enum key
{ "projectType": { "खेती": "खेती" } } // ← the key is the enum value, only the value translates
```

## Right

```jsonc
{
  "recommender": {
    "resultsSubtitle": "{{count}} योजना आपके विवरण से मेल खाती है",
    "resultsSubtitle_other": "{{count}} योजनाएँ आपके विवरण से मेल खाती हैं",
  },
  "projectType": {
    "AGRICULTURE": "खेती",
  },
}
```

Keys stay in English and keep their structure. Only values are translated.

## Translation notes for this domain

Financial vocabulary is where machine translation fails hardest. A few that matter:

| English         | Note                                                                                   |
| --------------- | -------------------------------------------------------------------------------------- |
| moratorium      | Not "pause". It is a repayment holiday during which interest still accrues — say that. |
| concessional    | "rियायती" in Hindi; the sense is _below market rate_, not "discounted".                |
| Channel Partner | A defined role in this system. Prefer transliteration over a literal translation.      |
| lakh / crore    | Keep. Do not convert to millions.                                                      |
| EMI             | Widely understood as-is; the expansion helps on first use.                             |

When a term has no clean translation, transliterating the English is usually better than a
literal calque that means something else.

## Notes

- Native-speaker review before merging. These are financial terms in front of vulnerable users.
- Update `_meta.coverage` in the file as it improves.
- The translation issue template has the checklist.
