# Layout catalogue

All functions live in `db_deck.py` and are module-level (`import db_deck as db`). Call them
on a `deck` created with `db.create_deck('ecosystem' | 'accelerator', title=..., confidential=...)`.
Where the JS version took one options object, the Python port takes keyword arguments
(`db.cover(deck, title=..., subtitle=..., ...)`).

| Function | Use for | Content limits |
|---|---|---|
| `cover(deck, title, subtitle, description, pills, date, hero, notes)` | first slide | title ≤ 30 chars; subtitle ≤ 70 chars with one `**accent**` phrase; ≤ 3 pills, each ≤ 22 chars. Draws a thin underline divider between title and subtitle (Figma node 4:81) |
| `statement(deck, text_, eyebrow, hero, notes)` | one key message / section opener | ≤ 90 chars, one `**accent**` phrase. Note the trailing underscore on `text_` — avoids shadowing the `text()` helper |
| `points(deck, title, items=[{'head', 'detail'}], eyebrow, source, left_visual, notes)` | 2–4 arguments | head ≤ 50 chars, detail ≤ 90 chars |
| `stats(deck, title, items=[{'value', 'label'}], eyebrow, source, notes)` | 2–4 key numbers | value ≤ 7 chars, label ≤ 60 chars |
| `cards(deck, title, cards_=[{'label', 'value', 'bullets'}], eyebrow, source, highlight, notes)` | 2–3 options / stages / tiers | label ≤ 26 chars, value ≤ 6 chars, ≤ 4 bullets of ≤ 70 chars. Label chip is sized generously via `chip_box()` so it never clips; value renders as a boxless bold accent-colored number (same treatment as `stats()`), not a chip. Note the trailing underscore on `cards_` — avoids shadowing the built-in |
| `bars(deck, title, data=[{'label', 'value', 'display'}], eyebrow, unit, points_, source, notes)` | 2–6 values over time | exact values in `display`; optional 1–3 side `points_` |
| `matrix(deck, title, columns=[str], rows=[{'label', 'values'}], eyebrow, source, highlight, notes)` | dense feature-comparison table (e.g. 3 pricing/partnership tiers x N features) — this is the layout to reach for instead of folding a real table into `cards()`/`points()` | 2–4 columns, each ≤ 20 chars caps; up to ~6–7 rows, row label ≤ 40 chars. Each row value: `'✓'` (bold accent check), `'–'`/`''` (muted dash = not included), or a short qualifier (≤ ~12 chars, e.g. `'3 slots'`) — this is a table, not another `points()` slide, so keep cell text to a word or two, not a sentence. `highlight` tints one column like `cards()`'s `highlight` tints one card |
| `closing(deck, title, contact, hero, notes)` | last slide | white plate with notched corners. Title box auto-grows for a wrapped (2-line) title and pushes `contact` down with it — see `pitfalls.md` — but stays untested past 2 lines; keep the title short enough to need at most 2 |
| `quote_block(deck, slide, x, y, w, label, quote, cite, scale)` / `quote_block_metrics(w, label, quote, cite, scale)` | pull-quote / testimonial, solid-accent block: quote-mark icon + caps label in a left column, bold quote + citation in a right column (~50/50 split) — matches Figma node 2202:6432 | label ≤ 20 chars caps, quote ≤ 140 chars, cite ≤ 60 chars. Not a full-slide layout by itself — call `quote_block_metrics` first to measure (e.g. to vertically center it: `top + (avail - h) / 2`), then `quote_block` to draw. A single large headline quote (`scale=1.5`) plus a row of 2–3 smaller ones (`scale=1`) does not fit on one slide — split into two. Verified with `examples/test_quote.py` |

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

New layouts may be added using `chrome()`, `badge()`, `dots()`, `text()`, `bullet_text()`,
`rect()`, `dot()`, `place_svg()`, `lines_needed()`, `chip_box()`, `content_top()`,
`quote_block()`, `quote_block_metrics()`, `runs()` and the `THEMES` / `N` / `F` / `T`
constants only — no raw hex or sizes, flat fills, no invented borders or shadows, no accent
stripes. New shapes must go through `rect()`/`dot()`, never `add_shape()` directly (see
`pitfalls.md` — otherwise you get a stray theme shadow back). Add new layouts as a commit to
`db_deck.py` in this repo, not as one-off code in a session.
