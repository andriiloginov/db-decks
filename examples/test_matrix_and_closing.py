"""QA script for two repo fixes/additions:
  1. matrix() — new dense feature-comparison table layout.
  2. closing() — title box now grows for a wrapped (2-line) title instead of
     overlapping the contact line. Renders both a 1-line title (regression check —
     must look identical to the old fixed geometry) and a 2-line title.

Run from the repo root: python examples/test_matrix_and_closing.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import db_deck as db

deck = db.create_deck('accelerator', title='matrix() + closing() QA')

# 1. matrix() — same three tiers/content as the real Batch 4 deck's cards() slide,
# reshaped into a comparison table.
db.matrix(deck, 'Compare the **three** partnership tiers',
          columns=['PARTNER', 'GENERAL PARTNER', 'ANCHOR PARTNER'],
          rows=[
              {'label': 'Full Batch 4 visibility', 'values': ['✓', '✓', '✓']},
              {'label': 'Companies matched to you', 'values': ['–', '3', 'Priority']},
              {'label': 'Participation in selection', 'values': ['–', '✓', '✓']},
              {'label': 'Programme co-design', 'values': ['–', '–', '✓']},
              {'label': 'Priority cohort access', 'values': ['–', '–', '✓']},
              {'label': 'Extended international access', 'values': ['–', '–', '✓']},
          ], eyebrow='Choose your model', highlight=2, source='Illustrative — see cards() slide for actual figures')

# 2. closing() — regression check: a short 1-line title must render identically to
# the pre-fix geometry (y=430, h=130).
db.closing(deck, title='Thank you!', contact='partnerships@defencebuilder.com')

# 3. closing() — the actual bug case: a title long enough to wrap to 2 lines must
# not collide with the contact line below it.
db.closing(deck, title="Let's build the pipeline together", contact='partnerships@defencebuilder.com')

db.save(deck, 'out_matrix_closing_qa.pptx')
print('Saved out_matrix_closing_qa.pptx')
