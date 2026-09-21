# Rendering a deck into Figma

Same brand, same layouts, different target: instead of a `.pptx`, the slides are drawn as native
Figma frames on a page of an existing file, through the `use_figma` MCP tool (Figma Plugin API).

Files:

| File | Role |
|---|---|
| `figma/db_figma.js` | The renderer (JS, Plugin API). One function per layout + `runDeck()`. |
| `scripts/figma_prelude.py` | Reads `db_deck.py` (`THEMES`, `N`, `F`, `T`, `SVG`) and prints them as JS `const`s, so tokens and vectors are never retyped. |
| `scripts/figma_payload.py` | Assembles the full `code` string for one `use_figma` call: prelude + renderer + `runDeck(...)`. Refuses payloads over 50,000 chars. |

`db_deck.py` stays the source of truth for tokens and vectors. The renderer is a *port* of its
layouts, and must be kept in step (see "Parity" below).

## Why it is built this way

`use_figma` takes one string of JS (max 50,000 chars), keeps **no state between calls**, has no
include mechanism, and has no `setPluginData` / `createImageAsync`. So every call carries the whole
renderer, and anything that has to survive between calls lives in the Figma file itself:

- **Brand kit.** Logos, watermark, plate, eye icon and quote mark are created once per page as
  components in a frame named `DB brand kit` (`DB/mark`, `DB/eye`, `DB/wm-top`, `DB/wm-bottom`,
  `DB/plate`, `DB/<direction>/lockup`, `DB/<direction>/mark-accent`, `DB/quote-mark`) and
  **instanced** on every slide. The first call for a page uses `--install-kit` (~45 KB, all SVGs);
  later calls omit the SVGs (~31–36 KB).
- **Section = deck.** Slides go into a Section named by `--name`, frames called
  `NN · layout · title`, 1920x1080, row layout (80 padding, 120 gap). A section that does not exist
  yet is created **below everything already on the page**. Existing nodes are never touched.
- **Re-render in place.** `"at": N` in a spec replaces slide N (same position and name prefix).
- **Auto-layout everywhere text lives.** Text is measured by Figma, not estimated
  (`lines_needed()` has no equivalent here). Containers hug their content, so swapping the font
  later cannot clip anything.
- **Speaker notes** go to `frame.annotations` (Figma has no notes field). If the file does not
  support annotations the call returns a warning instead of failing.

## Workflow

1. Ask (AskUserQuestion): direction, closing contact, and the Figma URL. Never guess these.
2. Parse the URL. `figma.com/design/<fileKey>/...?node-id=1373-2421` → `fileKey`, and the node id
   `1373:2421` (any node on the target page is enough: the renderer walks up to the page).
   `/branch/<branchKey>/` → use `branchKey` as fileKey. `/slides/`, `/board/` (FigJam) and `/make/`
   are not supported here — say so.
3. Load `figma:figma-use` first and pass `skillNames: "figma-use"` to every `use_figma` call.
4. Write `specs.json` (list of layout specs, fields as in `docs/layouts.md`, plus `lead` and the
   `list` layout below).
5. `python3 scripts/figma_payload.py --direction ecosystem --page-id 1373:2421 --name "My deck" \
   --install-kit --specs specs.json > payload.js` (drop `--install-kit` once the page has the kit),
   then send `payload.js` verbatim as `code`. Batch as many slides as fit under 50,000 chars
   (about 12 dense slides after the kit exists).
6. Check the result JSON: `errors` (the run stops at the first failing slide and removes it),
   `warnings` (overflow, missing hero, annotations), `fontFallbacks`, `heroTargets`.
7. QA every slide with `get_screenshot` (`enableBase64Response: true`, the CDN is not reachable from
   the sandbox), `maxDimension` ~1100. Fix, re-render with `"at": N`.

## Specs

Same fields as the Python layouts (`title`, `items`, `cards`, `data`, `columns`, `rows`, `eyebrow`,
`source`, `highlight`, `notes`, `hero`, ...), with these Figma-side differences:

- `lead` (all content layouts): a one-paragraph lead under the title, 30 px, secondary text.
- `list` layout (Figma only): `{layout:'list', title, columns:[a,b], rows:[[head, detail], ...]}` —
  two-column table with bold heads and a hairline between rows. Up to 7 rows.
- `stack` layout (Figma only) — a dense one-slide composition for when the source has few, busy
  slides and must stay 1:1 (one source slide = one DB slide). Fields: `eyebrow`, `title`, `titleW`,
  `lead`, `leadSize` (24), `leadW` (1800), `source`, `gap`, `notes`, and `blocks`, stacked top to
  bottom (each may carry a mono accent `label`):
  `table` {columns, rows:[[head, detail]], leftW, py}, `stats` {items:[{value,label}]} (60 px values),
  `columns` {cols:[{label, bullets}], plain} (cards, or plain numbered columns), `facts`
  {items:[{head, detail}]} (equal columns with a top rule), `chips` {label, items}, `text`
  {text, size, bold, color}. Type stays on the scale (60/42/30/24). Budget: content area is
  ~y 356–1000 after a one-line title and two-line 24 px lead; four to five blocks fit.
  Check the bottom in the screenshot — `qa()` warns when a block passes y 1005.
- `stats` / `cards`: all values in one row share one size (80 px if any value is longer than 6 chars).
- `hero`: `'placeholder'` draws a grey rectangle (its id comes back in `heroTargets`, fill it with
  `upload_assets`), or pass the node id of an existing hero in the **same file** to clone it. Known
  ids in the "Presentations" file: `624:9937` (Ecosystem), `1586:1441` (Accelerator).
- `closing` needs `contact` decided in step 1.

## Fonts

Figma decks use exactly two families: **DM Sans** (Regular / Bold — titles, body) and **DM Mono**
(Regular / Medium — eyebrow, labels, chips, source line). Both cover Cyrillic in Figma. This is a
deliberate deviation from the PPTX decks (FK Grotesk / FK Grotesk Mono), which are not on Figma's font
list. Roles live in `FONT_ROLES` at the top of `figma/db_figma.js`; any fallback is reported in
`fontFallbacks`. To move an existing deck to another family use `swapFont(root, from, to)`.

## Known limits / blind spots

- No Figma variables or styles are created; colours and sizes are literal values from the tokens.
- Only `list`, `stats`, `cards`, `points` and `statement` were visually verified in a real file.
  `cover`, `bars`, `matrix`, `closing`, `quote_block` and the hero clone/upload path are ported but
  untested — try them on a scratch section and delete it before relying on them.
- `upload_assets` from the sandbox is untested (figma.com is blocked from the sandbox egress).
- Annotation support depends on the file; notes may come back as a warning.
- Parity: `lead` and `list` exist only in the Figma renderer. If they should exist in `db_deck.py`,
  port them there (with `lines_needed()` limits) and update `docs/layouts.md`.
