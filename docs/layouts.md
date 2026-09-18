# Layout catalogue

All functions live in `db_deck.js` and are exported from it. Call them on a `deck` created
with `db.createDeck('ecosystem' | 'accelerator', { title, confidential })`.

| Function | Use for | Content limits |
|---|---|---|
| `cover(deck, {title, subtitle, description, pills, date, hero, heroAlt})` | first slide | title ≤ 30 chars; subtitle ≤ 70 chars with one `**accent**` phrase; ≤ 3 pills, each ≤ 22 chars. Draws a thin underline divider between title and subtitle (Figma node 4:81) |
| `statement(deck, {eyebrow, text, hero})` | one key message / section opener | ≤ 90 chars, one `**accent**` phrase |
| `points(deck, {eyebrow, title, items:[{head, detail}], source})` | 2–4 arguments | head ≤ 50 chars, detail ≤ 90 chars |
| `stats(deck, {eyebrow, title, items:[{value, label}]})` | 2–4 key numbers | value ≤ 7 chars, label ≤ 60 chars |
| `cards(deck, {eyebrow, title, cards:[{label, value, bullets}], highlight})` | 2–3 options / stages / tiers | label ≤ 26 chars, value ≤ 6 chars, ≤ 4 bullets of ≤ 70 chars. Label chip is sized generously via `chipBox()` so it never clips; value renders as a boxless bold accent-colored number (same treatment as `stats()`), not a chip |
| `bars(deck, {eyebrow, title, unit, data:[{label, value, display}], points, source})` | 2–6 values over time | exact values in `display`; optional 1–3 side points |
| `closing(deck, {title, contact})` | last slide | white plate with notched corners |
| `quoteBlock(deck, slide, x, y, w, {label, quote, cite, scale})` / `quoteBlockMetrics(w, {...})` | pull-quote / testimonial, solid-accent block: quote-mark icon + caps label in a left column, bold quote + citation in a right column (~50/50 split) — matches Figma node 2202:6432 | label ≤ 20 chars caps, quote ≤ 140 chars, cite ≤ 60 chars. Not a full-slide layout by itself — call `quoteBlockMetrics` first to measure (e.g. to vertically center it: `top + (avail - h) / 2`), then `quoteBlock` to draw. A single large headline quote (`scale: 1.5`) plus a row of 2–3 smaller ones (`scale: 1`) does not fit on one slide — split into two |

## Content rules

- One `**accent**` phrase per title/statement (2 at most). Sentence case for titles;
  UPPERCASE only for mono labels and the cover title.
- Vary layouts; don't put two identical layouts back to back unless the content is a
  sequence.
- Every number or claim from a source gets a `source` line.
- Too much text → split into two slides or drop to a smaller layout. Never shrink fonts
  below the scale.
- Speaker notes go in `notes`, never on the slide.

## Building new layouts

New layouts may be added using `chrome()`, `badge()`, `dots()`, `text()`, `bulletText()`,
`rect()`, `dot()`, `placeSvg()`, `linesNeeded()`, `chipBox()`, `contentTop()`,
`quoteBlock()`, `quoteBlockMetrics()`, `runs()` and the `THEMES` / `N` / `F` / `T` constants
only — no raw hex or sizes, flat fills, no invented borders or shadows, no accent stripes.
Add new layouts as a PR to `db_deck.js` in this repo, not as one-off code in a session.
