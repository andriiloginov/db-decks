# Pitfalls (learned the hard way)

Each of these cost a real, user-visible defect before it was fixed. Don't reintroduce them.

- **Always save through `db.save()`, never `pres.writeFile()`.** pptxgenjs 4.x writes an
  `<a:pPr>` before every run of a multi-run paragraph (every title with an accent word) —
  schema-invalid, PowerPoint may offer to "repair" the file. `save()` keeps only the first
  `<a:pPr>` per paragraph and also colors the square bullets with the accent (pptxgenjs has
  no bullet-color option).
- **`linesNeeded()`'s per-char multiplier must stay conservative — this was the root cause
  of two separate real-PowerPoint overflow bugs**, both caught only after opening the actual
  .pptx in real PowerPoint and screenshotting it (LibreOffice's QA render did not show either
  one). First bug: chip labels (cover pills, card label chips) clipped at their right edge.
  Second bug: card bullet text spilled past the bottom of its card. Root cause both times:
  the old `linesNeeded()` assumed FK Grotesk / DM Mono average ~0.56–0.6 em per character,
  but the real fonts run wider, so PowerPoint wrapped one character earlier per line than
  the estimate — every box sized from the old line count came out too short. Fixed by
  widening the multipliers to 0.7 (sans) / 0.66 (mono) — deliberately overestimates width,
  i.e. underestimates chars-per-line, so boxes always get slack, never clip. **Never compute
  line-wrap math by hand elsewhere in a layout — always call `linesNeeded()`**, and don't
  tighten its multipliers back down without re-verifying against a real PowerPoint render
  (not just the LibreOffice QA preview), since LibreOffice's font substitution did not
  reproduce either bug.
- **Any chip/pill/label box — a card's label chip, a cover pill, the eyebrow badge — must be
  sized with `chipBox(label, maxW, sizePx)`, never a hand-rolled `length * size * k + pad`
  formula.** `chipBox()` bakes in the same verified mono coefficient as `linesNeeded()`
  (0.66) and also returns the box height (not just width), so a label that wraps to two
  lines still gets a tall-enough chip instead of clipping. It returns `{cw, h, chipInset}` —
  use `chipInset` to pad the text inside the chip so it doesn't touch the fill edge.
- **`chipBox()`'s width formula reuses `linesNeeded()`'s 0.66 mono coefficient** (plus a
  small +2px rounding buffer, not a flat +14) so the box's stated width and its own wrap
  check agree — a label that doesn't fit at that width wraps to two lines automatically
  rather than clipping. Don't introduce a second, looser constant for chip width "just to be
  safe" — that caused visibly loose chips with inconsistent slack before it was fixed. If a
  real overflow ever shows up, fix it by raising `linesNeeded()`'s own mono coefficient
  (verified against a real PowerPoint render), not by hand-tuning `chipBox()` separately.
- **`cards()`'s `value` field renders exactly like `stats()`'s big numbers: boxless, bold,
  accent-colored FK Grotesk text, no chip.** Don't reintroduce a boxed/mono "value chip"
  treatment without the user asking for it back — a `stats()` number and a `cards()` value
  must look identical wherever they appear.
- Use `margin: 0` on every text box (the `text()` helper does) so text aligns with shapes at
  the same x.
- Don't use `fit: 'shrink'` — PowerPoint only applies it after editing. Size boxes from
  `linesNeeded()` instead; it is deliberately conservative.
- Cards/panels: size the box to its content (the `cards()` helper does); a box much taller
  than its text, or text spilling out, are defects.
- Charts are drawn as shapes + real text labels, so every value is a separate `<a:t>`; never
  place a chart screenshot.
- Don't add borders or shadows the design doesn't have. The only bordered elements are the
  highlighted card (accent, 0.75pt), secondary cards (`#B1B1B1`, 0.75pt) and the
  CONFIDENTIAL badge.
- Background: `#F2F2F2` for all content slides, not white; white is for cards and the
  closing plate.
- **A big headline `quoteBlock` (scale 1.5) plus a row of supporting quotes (scale 1) below
  it will not both fit in one slide's content band** — the combined height runs past the
  bottom watermark/dots motif with no margin. Split into two slides instead of shrinking the
  scale to force a fit; it also reads better.
- **Never build a throwaway "probe" slide just to measure a layout's height** (e.g.
  `pres.addSlide()` then `pres.slides.pop()` to discard it) — this relies on undocumented
  pptxgenjs internals and risks corrupting internal rIds/refs. Compute height with a pure,
  side-effect-free metrics function instead (see `quoteBlockMetrics()`, which `quoteBlock()`
  itself calls) and only draw once the position is known.

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
