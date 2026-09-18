# Pitfalls (learned the hard way)

Each of these cost a real, user-visible defect before it was fixed. Don't reintroduce them.
Most were found in the original pptxgenjs/JS version and carry straight over: the visual
defect they describe is about how PowerPoint/LibreOffice render text and shapes, not about
which language wrote the XML. A couple are new, specific to `python-pptx`'s own defaults —
those are marked below.

- **`python-pptx`'s `add_shape()` leaves a faint shadow under every shape unless you strip
  its `<p:style>` element, not just set `shadow.inherit = False`. (Python-specific.)**
  `shape.shadow.inherit = False` — the documented way to remove a shape's shadow — only adds
  an empty `<a:effectLst/>` to the shape's `<p:spPr>`. That's supposed to override the
  theme's shadow, but `add_shape()` *also* attaches a `<p:style>` element with
  `<a:effectRef idx="2">` pointing at a theme shadow effect, and LibreOffice's renderer
  doesn't reliably treat the empty `effectLst` as an override — a faint drop-shadow still
  showed under white cards in QA. Fixed in `_no_shadow()`: after setting
  `shadow.inherit = False`, also find and remove the shape's `<p:style>` element outright.
  Every shape here sets its own explicit fill/line color already, so the theme style
  reference (which is what carries `effectRef`) is never needed — safe to delete. Always
  create shapes through `rect()`/`dot()` (which call `_no_shadow()`), never `add_shape()`
  directly.
- **python-pptx has no high-level API for a colored/sized bullet character or for character
  tracking (letter-spacing) — both are hand-built XML here, and the raw `<a:pPr>` /
  `<a:rPr>` attribute/child order matters (schema-enforced).** `_set_bullet()` builds
  `<a:buClr>`, `<a:buSzPct>`, `<a:buFont>`, `<a:buChar>` in that order, appended after
  whatever spacing elements (`lnSpc`/`spcAft`) `python-pptx` already put on `<a:pPr>`; get
  the order wrong and PowerPoint treats the file as needing repair. `_set_char_spacing()`
  sets the raw `spc` attribute (hundredths of a point) on `<a:rPr>` directly via `lxml`.
  Don't hand-roll either of these differently in a new layout — call the existing helpers.
- **`_set_bullet()`'s `buFont` must be one of the four approved typefaces, not a default
  like Arial.** It's invisible (only selects which font's glyph renders the ■ character,
  never shown as text) but it still gets written into the file, and the font self-audit in
  `qa.md` checks *every* `typeface=` in the XML — a stray `Arial` here was caught and fixed
  by setting it to `F['mono']` (`DM Mono`) like everything else mono. If you add a new
  bullet variant, keep using `F[...]`, never a literal font name string.
- **`lines_needed()`'s per-char multiplier must stay conservative — this was the root cause
  of two separate real-PowerPoint overflow bugs in the original JS generator**, both caught
  only after opening the actual .pptx in real PowerPoint and screenshotting it (LibreOffice's
  QA render did not show either one). First bug: chip labels (cover pills, card label chips)
  clipped at their right edge. Second bug: card bullet text spilled past the bottom of its
  card. Root cause both times: the estimate assumed FK Grotesk / DM Mono average ~0.56–0.6 em
  per character, but the real fonts run wider, so PowerPoint wrapped one character earlier
  per line than the estimate — every box sized from the old line count came out too short.
  Fixed by widening the multipliers to 0.7 (sans) / 0.66 (mono) — deliberately overestimates
  width, i.e. underestimates chars-per-line, so boxes always get slack, never clip. These
  coefficients are carried over unchanged into `db_deck.py` since they're about real font
  metrics, not the language that computes with them — but **this Python port's own XML
  output has not yet been checked against a real PowerPoint render** (only LibreOffice so
  far — see `qa.md`), so treat that as still-open verification, not a closed question.
  **Never compute line-wrap math by hand elsewhere in a layout — always call
  `lines_needed()`.**
- **Any chip/pill/label box — a card's label chip, a cover pill, the eyebrow badge — must be
  sized with `chip_box(label, max_w, size_px)`, never a hand-rolled `len(s) * size * k + pad`
  formula.** `chip_box()` bakes in the same verified mono coefficient as `lines_needed()`
  (0.66) and also returns the box height (not just width), so a label that wraps to two
  lines still gets a tall-enough chip instead of clipping. It returns
  `(cw, h, chip_inset)` — use `chip_inset` to pad the text inside the chip so it doesn't
  touch the fill edge.
- **`chip_box()`'s width formula reuses `lines_needed()`'s 0.66 mono coefficient** (plus a
  small +2px rounding buffer, not a flat +14) so the box's stated width and its own wrap
  check agree — a label that doesn't fit at that width wraps to two lines automatically
  rather than clipping. Don't introduce a second, looser constant for chip width "just to be
  safe" — that caused visibly loose chips with inconsistent slack in the original version
  before it was fixed. If a real overflow ever shows up, fix it by raising
  `lines_needed()`'s own mono coefficient (verified against a real PowerPoint render), not
  by hand-tuning `chip_box()` separately.
- **`cards()`'s `value` field renders exactly like `stats()`'s big numbers: boxless, bold,
  accent-colored FK Grotesk text, no chip.** Don't reintroduce a boxed/mono "value chip"
  treatment without the user asking for it back — a `stats()` number and a `cards()` value
  must look identical wherever they appear.
- Use `margin=0` on every text box (the `text()` helper sets
  `tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0`) so text aligns
  with shapes at the same x.
- Don't rely on auto-fit/shrink — set `auto_size = MSO_AUTO_SIZE.NONE` (the `text()` helper
  does) and size boxes from `lines_needed()` instead; it's deliberately conservative.
- Cards/panels: size the box to its content (the `cards()` helper does); a box much taller
  than its text, or text spilling out, are defects.
- Charts are drawn as shapes + real text labels, so every value is a separate run; never
  place a chart screenshot.
- Don't add borders or shadows the design doesn't have. The only bordered elements are the
  highlighted card (accent, 0.75pt), secondary cards (`#B1B1B1`, 0.75pt) and the
  CONFIDENTIAL badge.
- Background: `#F2F2F2` for all content slides, not white; white is for cards and the
  closing plate.
- **A big headline `quote_block()` (scale 1.5) plus a row of supporting quotes (scale 1)
  below it will not both fit in one slide's content band** — the combined height runs past
  the bottom watermark/dots motif with no margin. Split into two slides instead of shrinking
  the scale to force a fit; it also reads better. Verified in this Python port too (see
  `examples/test_quote.py` — deliberately builds these as two separate slides).
- **Never build a throwaway "probe" slide just to measure a layout's height.** Compute
  height with a pure, side-effect-free metrics function instead (`quote_block_metrics()`,
  which `quote_block()` itself calls) and only draw once the position is known.
- **`closing()`'s title box was a fixed 130px-tall single-line box; a title long enough to
  wrap to 2 lines overflowed it and visibly collided with the `contact` line below** (shipped
  once: a real Batch 4 partnership deck had "Let's build the pipeline together" wrap to two
  lines and overlap "partnerships@defencebuilder.com"; worked around in that one deck by
  shortening the title, but the box itself didn't know it could grow). Fixed by computing
  `lines_needed()` on the title and growing the box by one `T['closing']`-tall line per extra
  line, symmetrically around the same vertical center the 1-line design used — so a 1-line
  title renders pixel-identical to before, and `contact` is repositioned relative to the
  title's *actual* rendered bottom instead of a hardcoded y. Still untested past 2 lines —
  keep closing titles short.

- **`matrix()`'s first cut used a 480px label column, which wrapped nearly every
  real-world row label to 2 lines** (`lines_needed()`'s 0.7 coefficient gives ~21
  chars/line at `T['body']` in a 460px text area — most feature labels run 20-30 chars) —
  the resulting per-row height blew past `990 - content_top(title)` and the table's last
  row(s) ran off the bottom of the slide, overlapping the source line. Fixed by widening
  the label column to 660px (fits ~30 chars on one line) before the layout shipped, caught
  in QA with `examples/test_matrix_and_closing.py` rather than in a real deck. If you widen
  the row-label font or shrink `label_w` again, re-check with a realistic (not short
  placeholder) set of row labels — short test strings hide this class of bug.

## Network / asset pitfalls

- **`figma.com` (and every subdomain / asset host on that domain, including
  `api.figma.com`) is blocked by the sandbox egress proxy at the account-policy level** —
  confirmed against `curl`, `device_bash` on a linked computer, and the public REST API, all
  returning `connect_rejected` / 403. Don't attempt curl/fetch workarounds. The Figma MCP
  tool's `get_metadata` / `get_design_context` / `get_screenshot` (with
  `enableBase64Response: true`) still work for *looking at* a file — they just can't produce
  a file you can save.
- **Hero images come from `assets/hero-images/` in this repo**, not from a live Figma fetch.
  See the README in that folder for the manifest format and how to add new ones.
