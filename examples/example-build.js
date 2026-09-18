// Minimal example — one of every layout. Copy this as a starting point for a real deck,
// then delete the layouts you don't need and fill in real content.
const db = require('../db_deck.js');

(async () => {
  const deck = db.createDeck('ecosystem', { title: 'Fund II overview' }); // or 'accelerator'

  await db.cover(deck, {
    title: 'Fund II',
    subtitle: '$50M to back **battlefield-tested** defence-tech winners',
    description: "From the region's most active defence-tech ecosystem",
    pills: ['First close Q1 2027', 'Min ticket $1M'],
    date: 'September 2026',
  });

  await db.statement(deck, { eyebrow: 'Why now', text: 'Battlefield-proven tech has **no borders**' });

  await db.points(deck, {
    eyebrow: 'Market',
    title: 'Defence tech is the **fastest-scaling** asset class',
    items: [{ head: '+10 defence unicorns since 2022', detail: 'Sector worth ≈ $416B' }],
    source: 'Sources: PitchBook',
  });

  await db.stats(deck, {
    eyebrow: 'Track record',
    title: 'Proof points',
    items: [{ value: '4.8×', label: 'Fund I MOIC in 18 months' }],
  });

  await db.cards(deck, {
    eyebrow: 'Capital',
    title: 'With **commitments** from Day 0',
    cards: [
      { label: 'Pre-opening', value: '$3M', bullets: ['Founder @ global payments infra'] },
      { label: '1st closing', value: '$20M', bullets: ['by Q1 2027'] },
    ],
  });

  await db.bars(deck, {
    eyebrow: 'Why now',
    title: 'VC **doubled** in a year',
    unit: 'Global defence-tech VC | $B',
    data: [
      { label: '2024', value: 27, display: '$27' },
      { label: '2025', value: 49, display: '$49' },
    ],
    source: 'Sources: PitchBook',
  });

  // Pull-quote example — a single large headline quote, vertically centered:
  //   const top = db.contentTop('Some title'), avail = 990 - top, scale = 1.5;
  //   const { h } = db.quoteBlockMetrics(1800, { label: 'Denmark', quote: '"..."', cite: '...', scale });
  //   await db.quoteBlock(deck, slide, 60, top + (avail - h) / 2, 1800, { label: 'Denmark', quote: '"..."', cite: '...', scale });

  await db.closing(deck, { title: 'Questions & Connections', contact: 'dy@defencebuilder.com' });

  await db.save(deck, 'out.pptx');
  console.log('Saved out.pptx');
})();
