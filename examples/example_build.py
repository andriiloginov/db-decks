import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import db_deck as db

deck = db.create_deck('ecosystem', title='Fund II overview')

db.cover(deck, title='Fund II',
         subtitle='$50M to back **battlefield-tested** defence-tech winners',
         description="From the region's most active defence-tech ecosystem",
         pills=['First close Q1 2027', 'Min ticket $1M'], date='September 2026')

db.statement(deck, 'Battlefield-proven tech has **no borders**', eyebrow='Why now')

db.points(deck, 'Defence tech is the **fastest-scaling** asset class',
          items=[{'head': '+10 defence unicorns since 2022', 'detail': 'Sector worth ≈ $416B'}],
          eyebrow='Market', source='Sources: PitchBook')

db.stats(deck, 'Proof points', items=[{'value': '4.8×', 'label': 'Fund I MOIC in 18 months'}],
         eyebrow='Track record')

db.cards(deck, 'With **commitments** from Day 0',
         cards_=[
             {'label': 'Pre-opening', 'value': '$3M', 'bullets': ['Founder @ global payments infra']},
             {'label': '1st closing', 'value': '$20M', 'bullets': ['by Q1 2027']},
         ], eyebrow='Capital')

db.bars(deck, 'VC **doubled** in a year',
        data=[{'label': '2024', 'value': 27, 'display': '$27'}, {'label': '2025', 'value': 49, 'display': '$49'}],
        eyebrow='Why now', unit='Global defence-tech VC | $B', source='Sources: PitchBook')

db.closing(deck, title='Questions & Connections', contact='dy@defencebuilder.com')

db.save(deck, 'out.pptx')
print('Saved out.pptx')
