import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import db_deck as db

deck = db.create_deck('ecosystem', title='Quote block QA')

# Slide 1: single large headline quote (scale 1.5), vertically centered in content band
s = db._blank_slide(deck)
db.chrome(deck, s, eyebrow='Testimonial', title='What **founders** say')
top = db.content_top('What **founders** say')
avail = 930 - top
m = db.quote_block_metrics(1800, 'FOUNDER, BATCH 3', scale=1.5,
                            quote='Defence Builder got us in front of **three** procurement officers in a week — that never happens on our own.',
                            cite='— Founder, Batch 3')
y = top + max(0, (avail - m['h']) / 2)
db.quote_block(deck, s, 60, y, 1800, 'FOUNDER, BATCH 3', scale=1.5,
               quote='Defence Builder got us in front of **three** procurement officers in a week — that never happens on our own.',
               cite='— Founder, Batch 3')

# Slide 2: a row of 2-3 smaller supporting quotes (scale 1), per pitfall doc these must NOT
# be combined with a scale-1.5 headline quote on the same slide -- kept on its own slide here.
s2 = db._blank_slide(deck)
db.chrome(deck, s2, eyebrow='Testimonials', title='More **voices** from the ecosystem')
top2 = db.content_top('More **voices** from the ecosystem')
quotes = [
    {'label': 'INVESTOR', 'quote': 'The most active defence-tech ecosystem we track.', 'cite': '— Partner, VC fund'},
    {'label': 'PARTNER', 'quote': 'A rare bridge between startups and procurement.', 'cite': '— Programme lead'},
    {'label': 'ALUMNI', 'quote': 'We closed our seed round two months after Batch 2.', 'cite': '— Alumni founder'},
]
col_w = (1800 - 2 * 40) / 3
x = 60
for q in quotes:
    h = db.quote_block(deck, s2, x, top2, col_w, q['label'], quote=q['quote'], cite=q['cite'], scale=1)
    x += col_w + 40

db.save(deck, 'out_quote.pptx')
print('Saved out_quote.pptx')
