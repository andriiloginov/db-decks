# QA

Follow the base `pptx` skill first: `validate.py`, render with `soffice.py` → `pdftoppm`,
look at every slide. Then self-audit the generated file:

```bash
python3 -c "import zipfile; zipfile.ZipFile('out.pptx').extractall('unz_out')"
# fonts: only FK Grotesk, FK Grotesk Mono Medium, DM Mono, DM Mono Medium
grep -ohE 'typeface="[^"+][^"]*"' unz_out/ppt/slides/*.xml | sort | uniq -c
# colors: exactly one accent family (orange OR blue), plus neutrals
grep -ohE 'srgbClr val="[0-9A-F]{6}"' unz_out/ppt/slides/*.xml | sort | uniq -c | sort -rn
# no paragraph with more than one <a:pPr>
python3 - <<'EOF'
import re, glob
for f in sorted(glob.glob('unz_out/ppt/slides/slide*.xml')):
    x = open(f).read()
    bad = [p for p in re.findall(r'<a:p>(.*?)</a:p>', x, flags=re.S) if p.count('<a:pPr') > 1]
    if bad: print(f, 'multi-pPr paragraphs:', len(bad))
EOF
```

Unlike the original pptxgenjs/JS generator, `python-pptx` doesn't write a duplicate
`<a:pPr>` per run on its own — that check is kept here as a regression guard, not because
`python-pptx` is known to do it. `save()` here is just `deck.prs.save(path)`, no
post-processing needed.

**Shadow check:** open a rendered slide with a white card (`stats()`/`cards()`) and look
for a faint shadow along its bottom/right edge. There shouldn't be one — see `pitfalls.md`
for why `python-pptx`'s `add_shape()` can leave one behind if a shape was created without
going through `rect()`/`dot()` (which both call `_no_shadow()`).

**Real-PowerPoint check (required whenever the deck has dense text — bullets, chips,
pills):** LibreOffice's rendering (used above) substitutes fonts and has, twice now in the
original JS version, failed to reproduce overflow that real PowerPoint shows (see
`pitfalls.md`). The `lines_needed()`/`chip_box()` coefficients carry over from that
already-verified JS version, but **this specific Python-generated XML has only been
checked against LibreOffice so far, never against real PowerPoint** — when the user can
open the file in actual PowerPoint, ask them to confirm bullet/chip text isn't clipped
before treating a dense-text deck as fully verified. LibreOffice passing is necessary but
not sufficient.

Blind spots — say them when reporting: the sandbox has no FK Grotesk, so the render uses a
substitute (text widths are approximate; boxes are sized with slack). For a closer preview,
map `FK Grotesk` → a similar grotesk (e.g. Host Grotesk from
`npm pack @fontsource/host-grotesk`, converted to TTF with fontTools) and install DM Mono
(`@fontsource/dm-mono`) via `~/.config/fontconfig/fonts.conf`. LibreOffice may draw thin
seams around images — not present in PowerPoint.
