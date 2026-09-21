#!/usr/bin/env python3
"""Assemble the complete `code` string for one `use_figma` call (prelude + figma/db_figma.js + runDeck call).

use_figma has no include mechanism and keeps no state between calls, so every call carries the whole
renderer. This script builds that text so it is never retyped or edited by hand.

  # first call on a page — also installs the "DB brand kit" components (needs the vectors: ~45 KB total)
  python3 scripts/figma_payload.py --direction ecosystem --page-id 600:15 --name "Fund II — Sep 2026" \
      --install-kit --specs specs.json > payload.js

  # every later call for the same page + name (tokens only: ~30 KB)
  python3 scripts/figma_payload.py --direction ecosystem --page-id 600:15 --name "Fund II — Sep 2026" \
      --specs specs2.json > payload.js

specs.json is a JSON list, e.g. [{"layout":"cover","title":"Fund II", ...}, {"layout":"points", ...}]
(field names = the keyword arguments of the matching db_deck.py function; see docs/figma.md).
Add "at": N to a spec to re-render slide N in place. The script refuses payloads over 50,000 characters.
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LIMIT = 50000


def strip_comments(js):
    # whole-line // comments and blank lines only — never touches strings (SVG holds "http://...")
    return '\n'.join(l for l in js.splitlines() if l.strip() and not l.lstrip().startswith('//'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--direction', required=True, choices=['ecosystem', 'accelerator'])
    ap.add_argument('--page-id', help='node-id from the Figma URL (a page id, or any node on the page), e.g. 600:15')
    ap.add_argument('--page-name', help='page name, when no page id is known')
    ap.add_argument('--create-page', action='store_true', help='create the page if --page-name does not exist')
    ap.add_argument('--name', required=True, help='Section title on the page that holds this deck\'s slides')
    ap.add_argument('--install-kit', action='store_true', help='embed the vectors and install/complete the "DB brand kit"')
    ap.add_argument('--no-confidential', action='store_true')
    ap.add_argument('--specs', required=True, help='JSON file: list of slide specs ("[]" is allowed with --install-kit)')
    a = ap.parse_args()
    if not (a.page_id or a.page_name):
        sys.exit('pass --page-id or --page-name')

    specs = json.load(open(a.specs, encoding='utf-8'))
    svg_args = ['--svg', 'all', '--direction', a.direction] if a.install_kit else ['--svg', 'none']
    prelude = subprocess.check_output([sys.executable, os.path.join(HERE, 'figma_prelude.py')] + svg_args, text=True)
    renderer = open(os.path.join(HERE, '..', 'figma', 'db_figma.js'), encoding='utf-8').read()
    opts = {'name': a.name, 'installKit': a.install_kit, 'confidential': not a.no_confidential}
    if a.page_id:
        opts['pageId'] = a.page_id
    if a.page_name:
        opts['pageName'] = a.page_name
        opts['createPage'] = a.create_page
    call = 'return await runDeck(%s, %s, %s);' % (json.dumps(a.direction), json.dumps(opts, ensure_ascii=False),
                                                  json.dumps(specs, ensure_ascii=False))
    code = '\n'.join([strip_comments(prelude), strip_comments(renderer), call]) + '\n'
    if len(code) > LIMIT:
        sys.exit('payload is %d chars (limit %d) — put fewer/lighter slides in this call' % (len(code), LIMIT))
    sys.stderr.write('payload: %d chars\n' % len(code))
    sys.stdout.write(code)


if __name__ == '__main__':
    main()
