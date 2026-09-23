# Design system

Tokens live in `src/theme/index.ts`. Components live in `src/components/ui/`.
**Never hardcode a colour or a spacing value in a component.**

## Who we are designing for

Often first-time smartphone users, on low-cost Android devices, outdoors in bright sunlight,
with patchy connectivity, making a real financial decision that affects their livelihood.

Every rule below follows from that sentence. None of it is stylistic preference.

## Hard constraints

| Constraint            | Value                     | Why                                                 |
| --------------------- | ------------------------- | --------------------------------------------------- |
| Minimum touch target  | 48dp                      | Thumbs, cheap digitisers, limited dexterity         |
| Minimum body text     | 16px                      | Readable outdoors, older eyes                       |
| Absolute minimum text | 13px                      | Below this is unreadable on a low-DPI screen in sun |
| Text contrast         | ≥ WCAG AA (4.5:1)         | Direct sunlight                                     |
| Status signalling     | never colour alone        | Colour blindness, glare, cheap panels               |
| Font scaling          | respected, capped at 1.6× | Honour the OS setting without shattering layouts    |

## Colour

Deep institutional blue as the brand — this is a government-adjacent service and it should
read as trustworthy rather than playful.

```
primary        #0B4F6C     primarySurface  #E7F2F7
accent         #C25E00     accentSurface   #FFF1E3   ← one per screen, the key action
success        #1B6E3C     warning         #8A5A00
danger         #A32020     info            #1B5E8A
background     #F7F8FA     surface         #FFFFFF
text           #14181F     textSecondary   #4A5361    textMuted #6B7482
```

Each status colour has a matching low-saturation surface for backgrounds, and is always
rendered alongside an icon or label (`Chip` takes a `prefix`, `Banner` supplies its own icon).

## Type

Indic scripts need more vertical room than Latin at the same nominal size — hence the generous
line heights. Do not tighten them because a Latin screenshot looks airy.

```
display    30/40    title     24/34    heading   20/30
subheading 17/26    body      16/26    bodyStrong 16/26
caption    14/22    label     13/18
```

Always use `Text` from `@/components/ui`, never react-native's.

## Spacing and shape

`xs 4 · sm 8 · md 12 · lg 16 · xl 24 · xxl 32 · xxxl 48`
Radii: `sm 6 · md 10 · lg 16 · xl 24 · pill 999`

## Components

| Component          | Notes                                                                                                                                              |
| ------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Text`             | The only text primitive. Indic-aware line heights, capped font scaling.                                                                            |
| `Button`           | `primary` / `secondary` / `outline` / `ghost` / `danger`, three sizes, loading state, haptics. Min 48dp.                                           |
| `Card`             | Surface container, optionally pressable.                                                                                                           |
| `Chip`             | Compact status/filter. `icon` carries the non-colour signal, `selected` for filters.                                                               |
| `Banner`           | Inline notice with a built-in icon and `accessibilityRole="alert"`.                                                                                |
| `Screen`           | Safe-area + background + scroll wrapper. Every screen uses it.                                                                                     |
| `AmountInput`      | Money entry. Echoes the value back as "₹1.4 lakh" and offers preset chips — an order-of-magnitude typo changes which scheme someone is matched to. |
| `OptionList`       | Large single-select. Preferred over native pickers, which hide options behind a tap.                                                               |
| `Stepper`          | −/+ numeric control. Deliberately not a drag slider (ADR-007).                                                                                     |
| `Icon`             | The 29-icon monoline SVG set, via react-native-svg. One `name` union; no emoji.                                                                    |
| `ListRow`          | Icon + title + one-line explanation + chevron, grouped by `ListGroup`. Replaced the v0 tile grid: a row can explain what "Channel Partner" means.  |
| `ValueCard`        | A single headline figure with its label. For the one number a screen is about.                                                                     |
| `StatRow`          | Label/value pair. Values must fit unaided — `adjustsFontSizeToFit` is a no-op on web and truncates instead of shrinking.                           |
| `ResultCard`       | Ranked recommendation: scheme, fit, and the reasons behind it.                                                                                     |
| `SegmentedControl` | Two-to-three way switch, e.g. list vs map.                                                                                                         |
| `SettingToggle`    | Labelled row with a `Switch`. One control per row — never a Switch nested inside a Pressable.                                                      |

Domain components live in `src/components/ui/`'s sibling `src/components/domain/`:
`SchemeCard`, `ResultCard`'s partner equivalent `PartnerCard`, `PartnerMap`, `ReasonList`, and
`PartnerNorms` — which lists what NSFDC checks for that partner type and then says plainly that
none of it can be checked. Its bullets are neutral dots, never checkmarks: a tick beside an
unevaluated condition is a false claim rendered as an icon.

## Patterns worth keeping

**One primary action per screen.** The accent colour appears once. On Home it is "Find my
scheme".

**Explain, don't just rank.** Every recommendation carries a "Why this scheme?" card. Every
excluded scheme in "near misses" says what blocked it.

**Show uncertainty.** Unverified data gets a warning chip. Ungrounded AI answers get a caveat.
A partner that cannot take applications is marked in red with the reason stated.

**Degrade, don't fail.** No map module → list view. No backend → on-device rules. No
translation → English. The user always gets something.

## Not yet done

Dark mode is not implemented; the palette is defined light-first.

Icons **were** emoji in v0. They are now a 29-icon monoline SVG set in `src/components/ui/Icon.tsx`,
ported from the Open Design system (ADR-014), rendered through react-native-svg with a single
`IconName` union. Every icon is still paired with a text label, so nothing depends on the glyph.

That port adopted the design system's hierarchy, tokens and icons but **rejected four of its
values** for failing this document's own hard constraints: sub-13px text, 1.47 line-height
(which clips Devanagari and Tamil), an SF Pro stack unavailable on the target devices, and
semantic colours that failed AA on white. `successText` and `warningText` are the
contrast-checked replacements at 5.02:1 and 5.93:1.
