# Tokens

All values below are encoded as constants in `db_deck.py` (`THEMES`, `N`, `F`, `T`) — never
type a raw hex or size in slide-building code. This file is the human-readable reference.

## Accent roles (same role names for both directions)

| Role | Ecosystem | Accelerator | Used for |
|---|---|---|---|
| `accent` | `#FE4C02` | `#0069BF` | highlighted words, big numbers (stat values and card values), bars, bullet squares, pill text, pixel cross, eyebrow badge fill, quote block fill |
| `bright` | `#FE6F34` | `#008CFF` | secondary accent shapes (diagrams) |
| `strong` | `#982D01` | `#003866` | accent text on light fills |
| `dark` / `deep` | `#661E00` / `#330F00` | `#001C33` / `#000E1A` | dark bars/chips, footers |
| `light` | `#FE9367` | `#66BAFF` | second chart series |
| `tint` | `#FFEDE6` | `#CCE8FF` | highlighted card fill, pill fill |
| `chip` | `#FFC9B3` | `#B8D4EC` | label chip on a highlighted card (accent ~24% on white) |

Never mix orange and blue in one deck. Never add Fund I amber (`#FF9501`) or purple
(`#8C49FF`) — those directions exist in the source Figma file but are out of scope here.

## Neutrals (shared across both directions)

Text `#242424` (one text color — the Figma file mixes in `#000000`; don't), secondary
`#494A4A`, muted `#6F7072`, faint `#B1B1B1`, lines/chips `#E1E1E1`, slide background
`#F2F2F2`, cards `#FFFFFF`, secondary cards `#ECECEC`, dark `#373737`, watermark `#ECECEC`
(= `#CDCDCD` at 15% on `#F2F2F2`, pre-flattened), closing background `#F6F6F8`.

## Fonts — write these `typeface` values literally

| Role | typeface | Weight |
|---|---|---|
| Titles, body, big numbers | `FK Grotesk` | Regular / `bold:true` |
| Cover display title (UPPERCASE) | `FK Grotesk Mono Medium` | — |
| Eyebrow badge, quote label, in-bar values | `DM Mono Medium` | — |
| Labels, chips, eyebrows in mono, sources, axis labels | `DM Mono` / `DM Mono Medium` | — |
| Background watermark | Shori — already outlined into the SVG, no font needed | — |

Never substitute Arial/Calibri/Inter. The fonts need to be installed only on the machine
that opens the deck. Most existing DB Figma files use the **Trial** versions ("FK Grotesk
Trial"); this repo is written for the licensed family names — a machine with only the
Trial installed will show PowerPoint's automatic substitute font. Font files themselves are
**not** vendored in this repo (no redistribution rights) — install them locally.

## Type scale (Figma px on the 1920×1080 canvas; pt = px ÷ 2)

Cover title 144 (≤12 chars) / 74 (longer), cover subtitle 48 Bold, cover description 32,
pill 26 mono, eyebrow 24 mono (solid-accent badge, white text), slide title 60 Bold (line
height 130%), statement 102 Bold (132%), point heading 42 Bold, body 30 (130%), small body
24, stat value 110 Bold, chip label 24 mono, card value 110/80 Bold (boxless,
accent-colored — same as stat value, not a mono chip), badge/unit label 18 mono, source
line 17 mono UPPERCASE, closing 102 Bold / 42.

## Units and grid

- Canvas 1920×1080 px → `LAYOUT_WIDE` 13.333×7.5 in. **inches = px / 144, pt = px / 2** —
  exact, never eyeball.
- Line height: Figma "130%" means 1.3 × font size. Write it as **exact points**
  (`lineSpacing: pt × 1.3`), not `lineSpacingMultiple` — PowerPoint's multiple is relative
  to the font's own line height (~1.2em), so 1.3 would render ≈1.56em.
- Margins: left 60 px (cover 120), content width 1800 px, cards gutter 47 px, stats gutter
  40 px. Positions come from formulas (`x = 60 + i × (w + gutter)`), never hand-typed per
  shape.

## Chrome on every content slide (drawn by `chrome()`)

| Element | Position (px) | Notes |
|---|---|---|
| Background | full | `#F2F2F2` |
| Watermark "DEFENCE" | (0, 0) 1917 wide | pixel-font outline SVG, flattened onto the background |
| Watermark "BUILDER" | (0, 959) 1845 wide | same |
| Brand, Ecosystem | (1759, 80) mark 91×46, all `#494A4A` | mark only, no wordmark |
| Brand, Accelerator | (1655, 68) lockup 206 wide | full lockup with blue cross + ACCELERATOR |
| CONFIDENTIAL badge | (1707, 10) 203×40, white, 0.75pt `#E1E1E1` border; eye-slash icon 20px at (1727, 20); DM Mono Medium 18 `#494A4A` | on by default; `create_deck(dir, confidential=False)` removes it |
| Eyebrow (section name) | (60, 60), solid accent badge sized by `chipBox()` | DM Mono Medium 24 white caps; 1–2 words |
| Title | (60, 172) w 1500 | FK Grotesk Bold 60, accent words via `**…**` |
| Three-dot motif | (1816–1840, 976–1000) | one `#B1B1B1` dot over two `#373737` dots, 11 px |
| Source line | (60, 1011) w 1720 h 32 | DM Mono 17 UPPERCASE `#494A4A` |

## Provenance

Figma "Presentations" — fileKey `CgDFUXVtgEKy1GxaGEkvAv`. Reference slides: Ecosystem cover
`624:9843`, content `624:10125`, statement `610:8961`, cards `616:9208` (page "DB Fund II v2
(main)"); Accelerator cover `1586:1410`, content `1157:548` (page "DB Accelerator: Batch 4.0
Partnership"); closing "Outro" `6:2293` (page "Slide Templates"). Eyebrow badge `2416:1174`,
pull-quote block `2202:6432`, full cover template `4:70`, cover image library `4:32`,
generated hero-image library "Images" section `2544:1495`.

The Figma file has **no text styles and no color variables** — every value above was
measured from the layers. The practice in that file wins over the older SM-posts brand
guideline wherever they disagree.
