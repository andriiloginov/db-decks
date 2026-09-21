// db_figma.js — Defence Builder slide renderer for Figma (runs inside `use_figma`, Plugin API).
//
// NOT a module. It is pasted as the body of a `use_figma` call, AFTER the prelude that
// `scripts/figma_prelude.py` prints (`THEMES`, `N`, `F`, `T`, `SVG` — generated from db_deck.py,
// so tokens and vectors have a single source of truth). Nothing is imported, nothing persists
// between calls: each call re-declares this file, then ends with `return await runDeck(...)`.
//
// Geometry is Figma px on a 1920x1080 frame, same numbers as db_deck.py. Where db_deck.py had to
// ESTIMATE text size (lines_needed / chip_box) this renderer MEASURES it — text nodes auto-size
// and containers that hold text are auto-layout, so a swapped/wider font can't clip anything.

// ───────────────────────── fonts ─────────────────────────
// Roles map to Figma family+style. Figma decks use exactly two families: DM Sans (text) and DM Mono
// (labels, caps, source lines); both cover Cyrillic. To try another family, change `want`/`fb` here
// (the run reports any fallback in `fontFallbacks`).
const FONT_ROLES = {
  sans:     { want: ['DM Sans'], fb: 'DM Sans', style: 'Regular' },
  sansBold: { want: ['DM Sans'], fb: 'DM Sans', style: 'Bold' },
  display:  { want: ['DM Mono'], fb: 'DM Mono', style: 'Medium' },
  mono:     { want: ['DM Mono'], fb: 'DM Mono', style: 'Regular' },
  monoMed:  { want: ['DM Mono'], fb: 'DM Mono', style: 'Medium' },
};
async function resolveFonts() {
  const avail = await figma.listAvailableFontsAsync();
  const has = (fam, sty) => avail.some((f) => f.fontName.family === fam && f.fontName.style === sty);
  const R = {}, report = {};
  for (const [role, d] of Object.entries(FONT_ROLES)) {
    const hit = d.want.find((fam) => has(fam, d.style));
    R[role] = { family: hit || d.fb, style: d.style };
    if (!hit && d.want[0] !== d.fb) report[d.want[0] + ' ' + d.style] = d.fb + ' ' + d.style + ' (fallback)';
    if (!has(R[role].family, d.style)) throw new Error('Font not available: ' + R[role].family + ' ' + d.style);
  }
  const uniq = [...new Map(Object.values(R).map((f) => [f.family + '|' + f.style, f])).values()];
  await Promise.all(uniq.map((f) => figma.loadFontAsync(f)));
  return { R, report };
}

// ───────────────────────── primitives ─────────────────────────
const SLIDE_W = 1920, SLIDE_H = 1080, SEC_PAD = 80, SEC_GAP = 120, KIT_NAME = 'DB brand kit';
const hexRgb = (h) => ({ r: parseInt(h.slice(0, 2), 16) / 255, g: parseInt(h.slice(2, 4), 16) / 255, b: parseInt(h.slice(4, 6), 16) / 255 });
const solid = (h, opacity) => (opacity == null ? { type: 'SOLID', color: hexRgb(h) } : { type: 'SOLID', color: hexRgb(h), opacity });
const recolor = (svg, from, to) => svg.split('fill="#' + from + '"').join('fill="#' + to + '"');
const pad2 = (n) => String(n).padStart(2, '0');
const plain = (s) => String(s).replace(/\*\*/g, '');

// Text. o: x,y (only when the parent is NOT auto-layout), w, h, size, font(role), bold, color, lh (percent),
// tracking (px), caps, align, valign, fill (true → stretch inside an auto-layout parent), name.
// "**accent**" runs take the direction's accent colour. Without h the box grows to fit (measured).
function txt(deck, parent, str, o) {
  const t = figma.createText();
  const role = o.font || (o.bold ? 'sansBold' : 'sans');
  t.fontName = deck.fonts[role];
  t.fontSize = o.size;
  let out = '';
  const ranges = [];
  for (const part of String(str).split(/(\*\*[^*]+\*\*)/).filter(Boolean)) {
    if (part.startsWith('**') && part.length > 4) { const s = part.slice(2, -2); ranges.push([out.length, out.length + s.length]); out += s; }
    else out += part;
  }
  t.characters = out;
  t.fills = [solid(o.color || N.text)];
  for (const [a, b] of ranges) t.setRangeFills(a, b, [solid(deck.theme.accent)]);
  t.lineHeight = { unit: 'PERCENT', value: o.lh || 120 };
  if (o.tracking) t.letterSpacing = { unit: 'PIXELS', value: o.tracking };
  if (o.caps) t.textCase = 'UPPER';
  t.textAlignHorizontal = (o.align || 'left').toUpperCase();
  parent.appendChild(t);
  if (o.w && o.h) { t.textAutoResize = 'NONE'; t.resize(o.w, o.h); }
  else if (o.w || o.fill) { t.textAutoResize = 'HEIGHT'; if (o.w) t.resize(o.w, t.height); }
  else t.textAutoResize = 'WIDTH_AND_HEIGHT';
  if (o.valign) t.textAlignVertical = o.valign.toUpperCase();
  if (o.fill) t.layoutSizingHorizontal = 'FILL';
  if (o.x != null) t.x = o.x;
  if (o.y != null) t.y = o.y;
  t.name = o.name || plain(out).slice(0, 40);
  return t;
}

// Flat rectangle (no shadow, optional 0.75 inside stroke — the only borders the design has).
function box(parent, x, y, w, h, fill, o = {}) {
  const r = figma.createRectangle();
  r.resize(w, h);
  r.fills = [solid(fill)];
  if (o.line) { r.strokes = [solid(o.line)]; r.strokeWeight = o.lineW || 0.75; r.strokeAlign = 'INSIDE'; }
  if (o.radius != null) r.cornerRadius = o.radius;
  r.name = o.name || 'Rect';
  parent.appendChild(r);
  r.x = x; r.y = y;
  return r;
}
function dotShape(parent, x, y, d, fill, name) {
  const e = figma.createEllipse();
  e.resize(d, d); e.fills = [solid(fill)]; e.name = name || 'Dot';
  parent.appendChild(e); e.x = x; e.y = y;
  return e;
}

// Auto-layout frame. o: gap, p / px / py (padding), fill, line, lineW, w (fixed width), h (fixed height),
// center (centre both axes), cross ('MIN'|'CENTER'|'MAX'), name. Height hugs unless h is given.
function al(parent, dir, o = {}) {
  const f = figma.createAutoLayout(dir);
  f.name = o.name || 'Stack';
  f.fills = o.fill ? [solid(o.fill)] : [];
  f.itemSpacing = o.gap || 0;
  f.paddingLeft = f.paddingRight = o.px != null ? o.px : (o.p || 0);
  f.paddingTop = f.paddingBottom = o.py != null ? o.py : (o.p || 0);
  if (o.line) { f.strokes = [solid(o.line)]; f.strokeWeight = o.lineW || 0.75; f.strokeAlign = 'INSIDE'; }
  if (o.center) { f.primaryAxisAlignItems = 'CENTER'; f.counterAxisAlignItems = 'CENTER'; }
  if (o.cross) f.counterAxisAlignItems = o.cross;
  f.clipsContent = false;
  parent.appendChild(f);
  if (o.w) { f.resize(o.w, o.h || 100); f.layoutSizingHorizontal = 'FIXED'; f.layoutSizingVertical = o.h ? 'FIXED' : 'HUG'; }
  else if (o.h) { f.resize(f.width, o.h); f.layoutSizingVertical = 'FIXED'; }
  return f;
}
function place(node, x, y) { node.x = x; node.y = y; return node; }
// Make every child of a horizontal auto-layout row as tall as the tallest one (measured, then locked).
function equalHeight(row) {
  const h = Math.ceil(Math.max(...row.children.map((c) => c.height)));
  const w = row.width;
  row.resize(w, h);                                       // resize() resets sizing to FIXED — that is what we want here
  row.children.forEach((c) => { c.layoutSizingVertical = 'FILL'; });
  return h;
}

// ───────────────────────── brand kit (components) ─────────────────────────
// Logos / watermark / plate are imported ONCE per page as components in a frame named "DB brand kit",
// then instanced on every slide. That keeps later calls small (no 15 KB of SVG each time) and gives
// designers linked, editable brand assets.
function kitFind(kit, name) {
  return kit ? kit.findAllWithCriteria({ types: ['COMPONENT'] }).find((c) => c.name === name) || null : null;
}
function pageBounds(page) {
  if (!page.children.length) return { has: false, x: 0, bottom: 0 };
  let x = Infinity, bottom = -Infinity;
  for (const c of page.children) { x = Math.min(x, c.x); bottom = Math.max(bottom, c.y + c.height); }
  return { has: true, x, bottom };
}
function nextSpot(deck, gap) { const b = pageBounds(deck.page); return { x: b.has ? b.x : 0, y: b.has ? b.bottom + gap : 0 }; }

function installKit(deck) {
  const dir = deck.direction, th = deck.theme;
  const wanted = {
    'DB/mark': SVG.mark,
    'DB/eye': SVG.eye && recolor(SVG.eye, '343330', N.text2),
    'DB/wm-top': SVG.wmTop,
    'DB/wm-bottom': SVG.wmBottom,
    'DB/plate': SVG.plate,
    ['DB/' + dir + '/lockup']: dir === 'ecosystem' ? SVG.ecoLockup : SVG.accLockup,
    ['DB/' + dir + '/mark-accent']: SVG.mark && recolor(SVG.mark, '494A4A', N.line).replace('fill="#' + N.line + '"', 'fill="#' + th.accent + '"'),
    'DB/quote-mark': SVG.quoteMark,
  };
  let kit = deck.kit;
  if (!kit) {
    const p = nextSpot(deck, 240);
    kit = al(deck.page, 'HORIZONTAL', { name: KIT_NAME, gap: 40, p: 40, fill: N.white, w: 2080 });
    kit.layoutWrap = 'WRAP';
    place(kit, p.x, p.y);
    deck.kit = kit;
    deck.created.push(kit.id);
  }
  const added = [];
  for (const [name, svg] of Object.entries(wanted)) {
    if (!svg || kitFind(kit, name)) continue;
    const c = figma.createComponentFromNode(figma.createNodeFromSvg(svg));
    c.name = name;
    kit.appendChild(c);
    added.push(name);
  }
  return added;
}
function inst(deck, name, parent, x, y, w, label) {
  const c = kitFind(deck.kit, name);
  if (!c) throw new Error('Brand kit is missing "' + name + '" — call runDeck with installKit:true (and the full SVG prelude) once per page');
  const i = c.createInstance();
  parent.appendChild(i);
  if (w) i.resize(w, (w * c.height) / c.width);
  if (!('layoutMode' in parent) || parent.layoutMode === 'NONE') place(i, x, y);   // auto-layout parents position their children
  i.name = label || name.replace(/^DB\//, '');
  return i;
}

// ───────────────────────── deck / section / slide ─────────────────────────
async function openDeck(direction, o) {
  const theme = THEMES[direction];
  if (!theme) throw new Error('direction must be "ecosystem" or "accelerator", got ' + direction);
  let page = null;
  if (o.pageId) { let n = await figma.getNodeByIdAsync(String(o.pageId).replace('-', ':')); while (n && n.type !== 'PAGE') n = n.parent; page = n; }
  if (!page && o.pageName) page = figma.root.children.find((p) => p.name.trim() === o.pageName.trim()) || null;
  if (!page && o.pageName && o.createPage) { page = figma.createPage(); page.name = o.pageName; }
  if (!page) throw new Error('Target page not found — pass pageId (the node-id from the Figma URL, or any node on that page) or pageName');
  await figma.setCurrentPageAsync(page);
  const f = await resolveFonts();
  const deck = {
    direction, theme, page, fonts: f.R, fontReport: f.report, confidential: o.confidential !== false,
    name: o.name || 'DB deck', warnings: [], created: [], heroTargets: [], chrome: new Set(), section: null, redo: null,
    kit: page.children.find((n) => n.type === 'FRAME' && n.name === KIT_NAME) || null,
  };
  return deck;
}
function openSection(deck) {
  let sec = deck.page.children.find((n) => n.type === 'SECTION' && n.name === deck.name);
  if (!sec) {
    const p = nextSpot(deck, 240);                     // BELOW everything already on the page
    sec = figma.createSection();
    sec.name = deck.name;
    sec.x = p.x; sec.y = p.y;
    sec.resizeWithoutConstraints(SEC_PAD * 2 + SLIDE_W, SEC_PAD * 2 + SLIDE_H);
    deck.created.push(sec.id);
  }
  deck.section = sec;
  return sec;
}
const isSlide = (n) => n.type === 'FRAME' && /^\d\d · /.test(n.name);
function newSlide(deck, layout, title, bg) {
  const sec = deck.section || openSection(deck);
  const slides = sec.children.filter(isSlide);
  let idx = slides.length;
  if (deck.redo != null) {                              // re-render slide N in place
    idx = deck.redo - 1;
    const old = slides.find((n) => n.name.startsWith(pad2(idx + 1) + ' · '));
    if (old) old.remove();
    deck.redo = null;
  }
  const s = figma.createFrame();
  s.resize(SLIDE_W, SLIDE_H);
  s.fills = [solid(bg || N.bg)];
  s.clipsContent = true;
  s.name = pad2(idx + 1) + ' · ' + layout + (title ? ' · ' + plain(title).slice(0, 40) : '');
  sec.appendChild(s);
  place(s, SEC_PAD + idx * (SLIDE_W + SEC_GAP), SEC_PAD);
  const needW = SEC_PAD * 2 + (idx + 1) * SLIDE_W + idx * SEC_GAP;
  if (sec.width < needW) sec.resizeWithoutConstraints(needW, SEC_PAD * 2 + SLIDE_H);
  deck.created.push(s.id);
  deck.chrome = new Set();
  deck.lastSlide = s;
  return s;
}
function addNotes(deck, s, notes) {                     // speaker notes → node annotation (Figma has no notes field)
  if (!notes) return;
  try { s.annotations = [{ labelMarkdown: String(notes) }]; }
  catch (e) { deck.warnings.push('speaker notes not written to ' + s.name + ': ' + (e.message || e)); }
}
function mark(deck, node) { deck.chrome.add(node.id); return node; }

// ───────────────────────── chrome ─────────────────────────
function badge(deck, s) {                               // CONFIDENTIAL, top-right (203x40)
  if (!deck.confidential) return;
  const b = al(s, 'HORIZONTAL', { name: 'Confidential Badge', fill: N.white, line: N.line, px: 20, gap: 13, cross: 'CENTER' });
  inst(deck, 'DB/eye', b, 0, 0, 20, 'Eye-slash');
  txt(deck, b, 'Confidential', { size: T.label, font: 'monoMed', color: N.text2, caps: true, lh: 100, name: 'Label' });
  const w = b.width;
  b.resize(w, 40); b.primaryAxisSizingMode = 'AUTO';
  place(b, 1910 - b.width, 10);
  mark(deck, b);
}
function dots(deck, s) {                                // three-pixel motif, bottom-right
  const g = [dotShape(s, 1823, 976, 11, N.faint, 'Dot'), dotShape(s, 1816, 989, 11, N.dark, 'Dot'), dotShape(s, 1829, 989, 11, N.dark, 'Dot')];
  g.forEach((d) => mark(deck, d));
}
function eyebrowBadge(deck, s, label) {                 // solid accent badge, DM Mono Medium 24 white caps
  const b = al(s, 'HORIZONTAL', { name: 'Eyebrow', fill: deck.theme.accent, px: 10, py: 10 });
  txt(deck, b, label, { size: T.eyebrow, font: 'monoMed', color: N.white, caps: true, tracking: 1, lh: 120, name: 'Label' });
  place(b, 60, 60);
  return mark(deck, b);
}
// Returns { top } — where content may start (below the measured title).
function chrome(deck, s, o = {}) {
  if (o.watermark !== false) {
    mark(deck, inst(deck, 'DB/wm-top', s, 0, 0, 1917, 'Watermark DEFENCE')).opacity = 0.15;
    mark(deck, inst(deck, 'DB/wm-bottom', s, 0, 959, 1845, 'Watermark BUILDER')).opacity = 0.15;
  }
  if (o.brand !== false) {
    mark(deck, deck.direction === 'ecosystem'
      ? inst(deck, 'DB/mark', s, 1759, 80, 91, 'Logo')
      : inst(deck, 'DB/accelerator/lockup', s, 1655, 68, 206, 'Logo'));
  }
  if (o.badge !== false) badge(deck, s);
  if (o.dots !== false) dots(deck, s);
  if (o.eyebrow) eyebrowBadge(deck, s, o.eyebrow);
  let top = 300;
  if (o.title) {
    const t = txt(deck, s, o.title, { x: 60, y: 172, w: o.titleW || 1500, size: T.title, bold: true, lh: 130, name: 'Title' });
    top = t.y + t.height + 50;
  }
  if (o.lead) {                                         // one-paragraph lead under the title (body 30, secondary text)
    const l = txt(deck, s, o.lead, { x: 60, y: top - 30, w: o.leadW || 1500, size: o.leadSize || T.body, color: N.text2, lh: 130, name: 'Lead' });
    top = l.y + l.height + 50;
  }
  if (o.source) mark(deck, txt(deck, s, o.source, { x: 60, y: 1011, w: 1720, h: 32, size: T.source, font: 'mono', color: N.text2, caps: true, valign: 'center', name: 'Source' }));
  return { top };
}

// Anything that ended up outside the safe content area (x 60..1860, y ≤ 990) is reported, not hidden.
function qa(deck, s) {
  for (const c of s.children) {
    if (deck.chrome.has(c.id) || c.name.startsWith('Hero') || c.name === 'Plate') continue;
    if (c.y + c.height > 1005 || c.x + c.width > 1865 || c.x < 55)
      deck.warnings.push(s.name + ': "' + c.name + '" leaves the content area (bottom ' + Math.round(c.y + c.height) + ', right ' + Math.round(c.x + c.width) + ') — shorten text or split the slide');
  }
}

// Hero image. spec: 'placeholder' | true → grey rectangle named "Hero image", id returned in heroTargets so an
// image can be dropped in with upload_assets; '<nodeId>' → clone that node (same-file only).
async function hero(deck, s, spec, b) {
  let node = null;
  if (typeof spec === 'string' && spec !== 'placeholder') {
    const src = await figma.getNodeByIdAsync(spec.replace('-', ':'));
    if (src && 'clone' in src) { node = src.clone(); s.appendChild(node); node.resize(b.w, b.h); }
    else deck.warnings.push('hero node ' + spec + ' not found in this file — placeholder used');
  }
  if (!node) {
    node = figma.createRectangle(); node.resize(b.w, b.h); node.fills = [solid(N.line)];
    s.appendChild(node);
    deck.heroTargets.push(node.id);
  }
  node.name = 'Hero image';
  place(node, b.x, b.y);
  return node;
}

// ───────────────────────── layouts ─────────────────────────
async function cover(deck, o) {
  const th = deck.theme, eco = deck.direction === 'ecosystem';
  const s = newSlide(deck, 'cover', o.title);
  chrome(deck, s, { brand: false, badge: false, dots: false });
  if (o.hero) await hero(deck, s, o.hero, { x: 1000, y: 0, w: 920, h: 1080 });
  inst(deck, 'DB/' + deck.direction + '/lockup', s, 120, 100, eco ? 459 : 363, 'Logo');
  const short = o.title.length <= 12, size = short ? T.coverTitleShort : T.coverTitleLong;
  const title = txt(deck, s, o.title, { x: 120, y: 330, w: 1000, size, font: 'display', caps: true, lh: 90, tracking: short ? -6 : 0, name: 'Title' });
  let y = title.y + title.height + 40;
  box(s, 120, y, 1000, 2, N.line, { name: 'Divider' });
  y += 38;
  if (o.subtitle) { const t = txt(deck, s, o.subtitle, { x: 120, y, w: 820, size: T.coverSub, bold: true, lh: 120, name: 'Subtitle' }); y = t.y + t.height + 40; }
  if (o.description) txt(deck, s, o.description, { x: 120, y, w: 820, size: T.coverDesc, lh: 120, name: 'Description' });
  let px = 120;
  for (const p of (o.pills || []).slice(0, 3)) {
    const pill = al(s, 'HORIZONTAL', { name: 'Pill', fill: th.tint, px: 35, center: true });
    txt(deck, pill, p, { size: T.pill, font: 'monoMed', color: th.accent, caps: true, lh: 100, name: 'Label' });
    const w = pill.width; pill.resize(w, 83); pill.primaryAxisSizingMode = 'AUTO'; pill.cornerRadius = 41.5;
    place(pill, px, 920);
    px += pill.width + 42;
  }
  if (!o.hero) inst(deck, 'DB/' + deck.direction + '/mark-accent', s, 1130, 390, 640, 'DB mark');
  badge(deck, s);
  dots(deck, s);
  if (o.date) mark(deck, txt(deck, s, o.date, { x: 1475, y: 1011, w: 300, h: 32, size: T.source, font: 'mono', color: N.text2, caps: true, align: 'right', valign: 'center', name: 'Date' }));
  addNotes(deck, s, o.notes); qa(deck, s);
  return s;
}

async function statement(deck, o) {
  const s = newSlide(deck, 'statement', o.text);
  chrome(deck, s, { eyebrow: o.eyebrow });
  if (o.hero) await hero(deck, s, o.hero, { x: 1300, y: 143, w: 620, h: 937 });
  const t = txt(deck, s, o.text, { x: 70, y: 0, w: 1400, size: T.statement, bold: true, lh: 132, name: 'Statement' });
  if (t.height > 3 * T.statement * 1.32 + 2) t.fontSize = 80;
  t.y = Math.round((SLIDE_H - t.height) / 2);
  addNotes(deck, s, o.notes); qa(deck, s);
  return s;
}

async function points(deck, o) {
  const th = deck.theme;
  const s = newSlide(deck, 'points', o.title);
  const { top } = chrome(deck, s, { eyebrow: o.eyebrow, title: o.title, lead: o.lead, source: o.source });
  const items = o.items.slice(0, 4);
  const x = o.leftVisual ? 700 : 60, w = o.leftVisual ? 1100 : 1500;
  const gap = Math.max(24, Math.min(170, (960 - top) / items.length) - 95);
  const list = al(s, 'VERTICAL', { name: 'Points', gap });
  for (const it of items) {
    const row = al(list, 'HORIZONTAL', { name: 'Point', gap: 26 });
    const holder = figma.createFrame(); holder.name = 'Bullet'; holder.fills = []; holder.resize(14, 50); holder.clipsContent = false;
    row.appendChild(holder);
    box(holder, 0, 14, 14, 14, th.accent, { name: 'Square' });
    const stack = al(row, 'VERTICAL', { name: 'Text', gap: 8, w: w - 40 });
    txt(deck, stack, it.head, { fill: true, size: T.h2, bold: true, lh: 120, name: 'Head' });
    if (it.detail) txt(deck, stack, it.detail, { fill: true, size: T.bodySm * 1.25, color: N.text2, lh: 120, name: 'Detail' });
  }
  place(list, x, top);
  addNotes(deck, s, o.notes); qa(deck, s);
  return s;
}

async function stats(deck, o) {
  const s = newSlide(deck, 'stats', o.title);
  const { top: t0 } = chrome(deck, s, { eyebrow: o.eyebrow, title: o.title, lead: o.lead, source: o.source });
  const items = o.items.slice(0, 4);
  const vsize = items.some((it) => String(it.value).length > 6) ? 80 : T.statValue;   // one size per row, so values line up
  const row = al(s, 'HORIZONTAL', { name: 'Stats', gap: 40, w: 1800, h: 400 });
  for (const it of items) {
    const card = al(row, 'VERTICAL', { name: 'Stat', fill: N.card, p: 40, gap: 50 });
    card.layoutSizingHorizontal = 'FILL'; card.layoutSizingVertical = 'FILL';
    txt(deck, card, it.value, { fill: true, size: vsize, bold: true, color: deck.theme.accent, lh: 100, name: 'Value' });
    txt(deck, card, it.label, { fill: true, size: T.body, color: N.text2, lh: 120, name: 'Label' });
  }
  place(row, 60, Math.max(t0, 420));
  addNotes(deck, s, o.notes); qa(deck, s);
  return s;
}

function chip(deck, parent, label, fill) {              // label chip: hugs its text, never clips
  const c = al(parent, 'HORIZONTAL', { name: 'Chip', fill, px: 14, py: 9 });
  txt(deck, c, label, { size: T.chip, font: 'mono', caps: true, lh: 125, name: 'Label' });
  return c;
}
function bulletList(deck, parent, items, size, gap) {
  size = size || T.body;              // ■ bullets in accent colour (Figma lists can't colour the marker)
  const list = al(parent, 'VERTICAL', { name: 'Bullets', gap: gap || 24 });
  list.layoutSizingHorizontal = 'FILL';
  for (const it of items) {
    const row = al(list, 'HORIZONTAL', { name: 'Bullet', gap: 13 });
    row.layoutSizingHorizontal = 'FILL';
    const holder = figma.createFrame(); holder.name = 'Square'; holder.fills = []; holder.resize(14, size * 1.3); holder.clipsContent = false;
    row.appendChild(holder);
    box(holder, 0, (size * 1.3 - 14) / 2, 14, 14, deck.theme.accent, { name: 'Marker' });
    txt(deck, row, it, { fill: true, size, lh: 130, name: 'Text' });
  }
  return list;
}
async function cards(deck, o) {
  const th = deck.theme;
  const s = newSlide(deck, 'cards', o.title);
  const { top } = chrome(deck, s, { eyebrow: o.eyebrow, title: o.title, lead: o.lead, source: o.source });
  const list = o.cards.slice(0, 3), hi = o.highlight == null ? 0 : o.highlight;
  const vsize = list.some((c) => c.value && String(c.value).length > 6) ? 80 : T.statValue;
  const row = al(s, 'HORIZONTAL', { name: 'Cards', gap: 47, w: 1790 });
  list.forEach((c, i) => {
    const on = i === hi;
    const card = al(row, 'VERTICAL', { name: 'Card', fill: on ? th.tint : N.cardAlt, line: on ? th.accent : N.faint, p: 28, gap: 47 });
    card.layoutSizingHorizontal = 'FILL';
    chip(deck, card, c.label, on ? th.chip : N.line);
    if (c.value) txt(deck, card, c.value, { fill: true, size: vsize, bold: true, color: th.accent, lh: 100, name: 'Value' });
    if (c.bullets && c.bullets.length) bulletList(deck, card, c.bullets);
  });
  equalHeight(row);                                       // all cards as tall as the tallest
  place(row, 60, top);
  addNotes(deck, s, o.notes); qa(deck, s);
  return s;
}

async function bars(deck, o) {
  const th = deck.theme;
  const s = newSlide(deck, 'bars', o.title);
  const { top } = chrome(deck, s, { eyebrow: o.eyebrow, title: o.title, lead: o.lead, source: o.source });
  const base = 930, maxH = base - top - 80, data = o.data.slice(0, 6), maxV = Math.max(...data.map((d) => d.value));
  const colW = 197, gut = 57;
  if (o.unit) txt(deck, s, o.unit, { x: 60, y: top - 10, w: 560, size: T.label, font: 'mono', caps: true, lh: 120, name: 'Unit' });
  data.forEach((d, i) => {
    const x = 80 + i * (colW + gut), h = Math.max(40, (maxH * d.value) / maxV);
    const bar = figma.createFrame(); bar.name = 'Bar ' + d.label; bar.fills = [solid(th.accent)]; bar.resize(colW, h); bar.clipsContent = false;
    s.appendChild(bar); place(bar, x, base - h);
    txt(deck, bar, d.display != null ? d.display : String(d.value), { x: 0, y: 20, w: colW, size: 34, font: 'display', color: N.white, align: 'center', lh: 120, name: 'Value' });
    txt(deck, s, d.label, { x, y: base + 6, w: colW, size: 28, font: 'mono', color: N.text2, align: 'center', lh: 120, name: 'Label ' + d.label });
  });
  const sideX = 80 + data.length * (colW + gut) + 60;
  if (o.points && o.points.length && sideX < 1500) {
    const list = al(s, 'VERTICAL', { name: 'Points', gap: 48 });
    for (const p of o.points) {
      const st = al(list, 'VERTICAL', { name: 'Point', gap: 8, w: 1860 - sideX });
      txt(deck, st, p.head, { fill: true, size: T.h2, bold: true, lh: 120, name: 'Head' });
      if (p.detail) txt(deck, st, p.detail, { fill: true, size: T.body, color: N.text2, lh: 120, name: 'Detail' });
    }
    place(list, sideX, top);
  }
  addNotes(deck, s, o.notes); qa(deck, s);
  return s;
}

// Comparison table: rows × 2–4 columns. '✓' → bold accent check, '–' / '' → muted dash, else short text.
async function matrix(deck, o) {
  const th = deck.theme;
  const s = newSlide(deck, 'matrix', o.title);
  const { top } = chrome(deck, s, { eyebrow: o.eyebrow, title: o.title, lead: o.lead, source: o.source });
  const cols = o.columns.slice(0, 4), n = cols.length, labelW = 660, gut = 20, hi = o.highlight;
  const cellW = (1800 - labelW) / n;
  const table = al(s, 'VERTICAL', { name: 'Matrix', w: 1800 });
  const newRow = (name, bottomW) => {
    const r = al(table, 'HORIZONTAL', { name, w: 1800 });
    if (bottomW) { r.strokes = [solid(N.line)]; r.strokeAlign = 'INSIDE'; r.strokeTopWeight = 0; r.strokeLeftWeight = 0; r.strokeRightWeight = 0; r.strokeBottomWeight = bottomW; }
    return r;
  };
  const cell = (row, i, py) => al(row, 'HORIZONTAL', { name: 'Cell', w: cellW, py, center: true, fill: hi === i ? th.tint : null });
  const head = newRow('Header', 2);
  al(head, 'HORIZONTAL', { name: 'Cell', w: labelW });
  cols.forEach((c, i) => txt(deck, cell(head, i, 20), c, { size: T.chip, font: 'monoMed', color: hi === i ? th.strong : N.text2, caps: true, align: 'center', lh: 120, name: 'Column' }));
  equalHeight(head);
  o.rows.forEach((r, ri) => {
    const row = newRow('Row', ri < o.rows.length - 1 ? 1 : 0);
    const lc = al(row, 'HORIZONTAL', { name: 'Label', w: labelW, py: 20, cross: 'CENTER' });
    lc.paddingRight = gut;
    txt(deck, lc, r.label, { fill: true, size: T.body, bold: true, lh: 130, name: 'Label' });
    cols.forEach((_, ci) => {
      const v = String((r.values || [])[ci] == null ? '–' : r.values[ci]);
      const cl = cell(row, ci, 20);
      if (v === '✓') txt(deck, cl, '✓', { size: T.h2, bold: true, color: th.accent, align: 'center', lh: 120, name: 'Check' });
      else if (v === '–' || v === '-' || v === '') txt(deck, cl, '–', { size: T.h2, color: N.faint, align: 'center', lh: 120, name: 'None' });
      else txt(deck, cl, v, { fill: true, size: T.bodySm, color: N.text2, align: 'center', lh: 125, name: 'Value' });
    });
    equalHeight(row);
  });
  place(table, 60, top);
  addNotes(deck, s, o.notes); qa(deck, s);
  return s;
}

// Two-column list: bold head on the left, plain detail on the right, hairlines between rows (like matrix, without ticks).
// o: columns? ['Left header', 'Right header'], rows: [[head, detail?], ...] (up to 7).
function tableBlock(deck, parent, o) {
  const th = deck.theme;
  const tbl = al(parent, 'VERTICAL', { name: 'List', w: 1800 });
  const leftW = o.leftW || 720, hs = o.headSize || T.h2, ds = o.detailSize || T.body, py = o.py != null ? o.py : 22;
  const newRow = (name, bottomW) => {
    const r = al(tbl, 'HORIZONTAL', { name, w: 1800 });
    if (bottomW) { r.strokes = [solid(N.line)]; r.strokeAlign = 'INSIDE'; r.strokeTopWeight = 0; r.strokeLeftWeight = 0; r.strokeRightWeight = 0; r.strokeBottomWeight = bottomW; }
    return r;
  };
  const cellOf = (row, w, p, padR) => { const c = al(row, 'HORIZONTAL', { name: 'Cell', w, py: p, cross: 'CENTER' }); c.paddingRight = padR; return c; };
  if (o.columns && o.columns.length) {
    const head = newRow('Header', 2);
    o.columns.slice(0, 2).forEach((c, i) => txt(deck, cellOf(head, i ? 1800 - leftW : leftW, o.headPy || 16, i ? 0 : 40), c, { fill: true, size: T.chip, font: 'monoMed', color: th.accent, caps: true, lh: 120, name: 'Column' }));
    equalHeight(head);
  }
  const rows = o.rows.slice(0, 7);
  rows.forEach((r, ri) => {
    const row = newRow('Row', ri < rows.length - 1 ? 1 : 0);
    txt(deck, cellOf(row, leftW, py, 40), r[0], { fill: true, size: hs, bold: true, lh: 120, name: 'Head' });
    const dc = cellOf(row, 1800 - leftW, py, 0);
    if (r[1]) txt(deck, dc, r[1], { fill: true, size: ds, color: N.text2, lh: 130, name: 'Detail' });
    equalHeight(row);
  });
  return tbl;
}
async function list(deck, o) {
  const s = newSlide(deck, 'list', o.title);
  const { top } = chrome(deck, s, { eyebrow: o.eyebrow, title: o.title, lead: o.lead, source: o.source });
  place(tableBlock(deck, s, o), 60, top);
  addNotes(deck, s, o.notes); qa(deck, s);
  return s;
}
function blockLabel(deck, parent, text) { return txt(deck, parent, text, { size: T.chip, font: 'monoMed', color: deck.theme.accent, caps: true, lh: 120, name: 'Block label' }); }
function statsBlock(deck, parent, b) {
  const row = al(parent, 'HORIZONTAL', { name: 'Stats', gap: 32, w: 1800 });
  for (const it of b.items.slice(0, 4)) {
    const card = al(row, 'VERTICAL', { name: 'Stat', fill: N.card, p: 24, gap: 8 });
    card.layoutSizingHorizontal = 'FILL';
    txt(deck, card, it.value, { fill: true, size: b.vsize || T.title, bold: true, color: deck.theme.accent, lh: 100, name: 'Value' });
    txt(deck, card, it.label, { fill: true, size: T.bodySm, color: N.text2, lh: 120, name: 'Label' });
  }
  equalHeight(row);
}
function columnsBlock(deck, parent, b) {
  const row = al(parent, 'HORIZONTAL', { name: 'Columns', gap: b.plain ? 60 : 32, w: 1800 });
  for (const c of b.cols.slice(0, 3)) {
    const col = b.plain ? al(row, 'VERTICAL', { name: 'Column', gap: 12 }) : al(row, 'VERTICAL', { name: 'Card', fill: N.cardAlt, line: N.faint, p: 24, gap: 16 });
    col.layoutSizingHorizontal = 'FILL';
    if (b.plain) txt(deck, col, c.label, { fill: true, size: T.body, bold: true, lh: 120, name: 'Head' });
    else chip(deck, col, c.label, N.line);
    if (c.bullets && c.bullets.length) bulletList(deck, col, c.bullets, T.bodySm, 8);
  }
  equalHeight(row);
}
function factsBlock(deck, parent, b) {
  const row = al(parent, 'HORIZONTAL', { name: 'Facts', gap: 40, w: 1800 });
  for (const it of b.items) {
    const c = al(row, 'VERTICAL', { name: 'Fact', gap: 6 });
    c.layoutSizingHorizontal = 'FILL';
    c.paddingTop = 14;
    c.strokes = [solid(N.faint)]; c.strokeAlign = 'INSIDE'; c.strokeTopWeight = 2; c.strokeBottomWeight = 0; c.strokeLeftWeight = 0; c.strokeRightWeight = 0;
    txt(deck, c, it.head, { fill: true, size: T.body, bold: true, lh: 120, name: 'Head' });
    if (it.detail) txt(deck, c, it.detail, { fill: true, size: T.bodySm, color: N.text2, lh: 120, name: 'Detail' });
  }
}
function chipsBlock(deck, parent, b) {
  const row = al(parent, 'HORIZONTAL', { name: 'Chips', gap: 16, w: 1800, cross: 'CENTER' });
  if (b.label) blockLabel(deck, row, b.label);
  b.items.forEach((x) => chip(deck, row, x, N.line));
}
function textBlock(deck, parent, b) { txt(deck, parent, b.text, { fill: true, size: b.size || T.body, bold: b.bold, color: b.color || N.text, lh: 130, name: 'Text' }); }
const BLOCKS = { table: tableBlock, stats: statsBlock, columns: columnsBlock, facts: factsBlock, chips: chipsBlock, text: textBlock };
// stack: a dense one-slide composition of blocks (table | stats | columns | facts | chips | text) under a title and lead
async function stack(deck, o) {
  const s = newSlide(deck, 'stack', o.title);
  const { top } = chrome(deck, s, { eyebrow: o.eyebrow, title: o.title, titleW: o.titleW, lead: o.lead, leadW: o.leadW, leadSize: o.leadSize, source: o.source });
  const col = al(s, 'VERTICAL', { name: 'Blocks', gap: o.gap || 26, w: 1800 });
  for (const b of o.blocks) {
    const wrap = al(col, 'VERTICAL', { name: 'Block', gap: 12, w: 1800 });
    if (b.label && b.type !== 'chips') blockLabel(deck, wrap, b.label);
    BLOCKS[b.type](deck, wrap, b);
  }
  place(col, 60, top - 26);
  addNotes(deck, s, o.notes); qa(deck, s);
  return s;
}
function quoteBlock(deck, s, x, y, w, o) {
  const k = o.scale || 1, pad = Math.round(32 * k), gap = Math.round(14 * k);
  const colW = (w - pad * 2 - gap) / 2;
  const blk = al(s, 'HORIZONTAL', { name: 'Quote', fill: deck.theme.accent, p: pad, gap, w });
  const left = al(blk, 'VERTICAL', { name: 'Label', gap: Math.round(10 * k), w: colW });
  inst(deck, 'DB/quote-mark', left, 0, 0, Math.round(54 * k), 'Quote mark');
  txt(deck, left, o.label, { fill: true, size: Math.round(20 * k), font: 'monoMed', color: 'F2F2F2', caps: true, lh: 130, name: 'Label' });
  const right = al(blk, 'VERTICAL', { name: 'Body', gap: Math.round(14 * k), w: colW });
  txt(deck, right, o.quote, { fill: true, size: Math.round(26 * k), bold: true, color: N.white, lh: 135, name: 'Quote' });
  if (o.cite) txt(deck, right, o.cite, { fill: true, size: Math.round(18 * k), color: 'FFD9C4', lh: 130, name: 'Cite' });
  place(blk, x, y);
  return blk;
}

async function closing(deck, o = {}) {
  const eco = deck.direction === 'ecosystem';
  const s = newSlide(deck, 'closing', o.title || 'Thank you', N.closingBg);
  if (o.hero) await hero(deck, s, o.hero, { x: 0, y: 0, w: 1920, h: 1080 });
  inst(deck, 'DB/plate', s, 59, 227, 1802, 'Plate');
  const t = txt(deck, s, o.title || 'Thank you!', { x: 333, y: 0, w: 1255, size: T.closing, bold: true, align: 'center', lh: 100, name: 'Title' });
  t.y = Math.round(495 - t.height / 2);                  // centred on the plate; grows symmetrically for 2 lines
  if (o.contact) txt(deck, s, o.contact, { x: 460, y: Math.round(519 + t.height / 2), w: 1000, size: T.closingSub, align: 'center', lh: 120, name: 'Contact' });
  const lw = eco ? 230 : 182;
  inst(deck, 'DB/' + deck.direction + '/lockup', s, (1920 - lw) / 2, 300, lw, 'Logo');
  addNotes(deck, s, o.notes); qa(deck, s);
  return s;
}

// ───────────────────────── runner ─────────────────────────
const LAYOUTS = { cover, statement, points, stats, cards, bars, matrix, list, stack, closing };

// Swap one font family for another on a frame (e.g. DM Sans → FK Grotesk once the org font library has it).
async function swapFont(root, from, to) {
  const texts = root.findAllWithCriteria({ types: ['TEXT'] });
  const styles = new Set();
  for (const t of texts) for (const seg of t.getStyledTextSegments(['fontName'])) if (seg.fontName.family === from) styles.add(seg.fontName.style);
  await Promise.all([...styles].flatMap((st) => [figma.loadFontAsync({ family: from, style: st }), figma.loadFontAsync({ family: to, style: st })]));
  let n = 0;
  for (const t of texts) for (const seg of t.getStyledTextSegments(['fontName'])) if (seg.fontName.family === from) { t.setRangeFontName(seg.start, seg.end, { family: to, style: seg.fontName.style }); n++; }
  return n;
}

// opts: { pageId | pageName [, createPage], name (section title), installKit, confidential }
// specs: [{ layout: 'cover'|'statement'|'points'|'stats'|'cards'|'bars'|'matrix'|'list'|'closing', at?: 1-based slide to re-render, ...fields }]
async function runDeck(direction, opts, specs) {
  const deck = await openDeck(direction, opts);
  const kitAdded = opts.installKit ? installKit(deck) : [];
  if (specs.length && !deck.kit) throw new Error('No "' + KIT_NAME + '" on this page yet — run once with installKit:true and the full SVG prelude');
  const slides = [], errors = [];
  for (const [i, spec] of specs.entries()) {
    const fn = LAYOUTS[spec.layout];
    if (!fn) { errors.push({ i, message: 'unknown layout ' + spec.layout }); break; }
    deck.redo = spec.at || null;
    deck.lastSlide = null;
    try {
      const s = await fn(deck, spec);
      slides.push({ n: s.name.slice(0, 2), name: s.name, id: s.id });
    } catch (e) {
      errors.push({ i, layout: spec.layout, message: String(e.message || e) });
      if (deck.lastSlide && !deck.lastSlide.removed) deck.lastSlide.remove();   // no half-built slide left behind
      break;                                            // stop at the first failure; fix it, then re-run from that spec
    }
  }
  return {
    section: deck.section && deck.section.id, page: deck.page.name, kit: deck.kit && deck.kit.id, kitAdded,
    slides, errors, warnings: deck.warnings, fontFallbacks: deck.fontReport, heroTargets: deck.heroTargets, createdNodeIds: deck.created,
  };
}
