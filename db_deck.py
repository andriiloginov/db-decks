"""db_deck.py — Defence Builder deck helpers (python-pptx + cairosvg + Pillow).

Port of db_deck.js (pptxgenjs). All geometry is written in Figma px on a 1920x1080 canvas
and converted:  inches = px / 144   ·   pt = px / 2   (exact for 1920x1080 -> 13.333x7.5in)

Every numeric constant here — colors, type scale, and especially the linesNeeded()/chip_box()
per-character width coefficients (0.7 sans / 0.66 mono) — is carried over unchanged from the
JS version. Those coefficients are calibrated against how real PowerPoint renders and wraps
FK Grotesk / DM Mono text; that calibration has nothing to do with which library builds the
XML, so it is not re-derived here. See docs/pitfalls.md for the story behind each one.
"""
import io
import math
import re

import cairosvg
from PIL import Image
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR, MSO_AUTO_SIZE
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn

# ---------- 1. Tokens ----------
THEMES = {
    'ecosystem':   {'name': 'Ecosystem',   'accent': 'FE4C02', 'bright': 'FE6F34', 'strong': '982D01', 'dark': '661E00', 'deep': '330F00', 'light': 'FE9367', 'tint': 'FFEDE6', 'chip': 'FFC9B3'},
    'accelerator': {'name': 'Accelerator', 'accent': '0069BF', 'bright': '008CFF', 'strong': '003866', 'dark': '001C33', 'deep': '000E1A', 'light': '66BAFF', 'tint': 'CCE8FF', 'chip': 'B8D4EC'},
}
N = {  # neutrals — identical for every direction
    'text': '242424', 'text2': '494A4A', 'muted': '6F7072', 'faint': 'B1B1B1',
    'line': 'E1E1E1', 'bg': 'F2F2F2', 'card': 'FFFFFF', 'cardAlt': 'ECECEC', 'dark': '373737',
    'white': 'FFFFFF', 'wm': 'ECECEC', 'closingBg': 'F6F6F8',
}
F = {  # typeface values written literally into the file
    'sans': 'FK Grotesk',              # Regular; Bold via bold=True
    'display': 'FK Grotesk Mono Medium',
    'mono': 'DM Mono',                 # Regular
    'monoMed': 'DM Mono Medium',
}
T = {  # type scale, Figma px (pt = px/2)
    'coverTitleShort': 144, 'coverTitleLong': 74, 'coverSub': 48, 'coverDesc': 32, 'pill': 26,
    'eyebrow': 24, 'title': 60, 'statement': 102, 'h2': 42, 'body': 30, 'bodySm': 24,
    'statValue': 110, 'chip': 24, 'label': 18, 'source': 17, 'closing': 102, 'closingSub': 42,
}

# ---------- 2. Brand assets (literal vectors exported from Figma "Presentations") ----------
SVG = {
    'ecoLockup': '<svg width="459" height="93" viewBox="0 0 459 93" xmlns="http://www.w3.org/2000/svg"><path d="M0 30.6H15.3V45.9H0V30.6ZM30.6 30.6V15.3H15.3V30.6H30.6V45.9H45.9V30.6H30.6Z" fill="#FE4C02"/><path d="M30.6 45.9H15.3V91.8H61.2C69.6 91.8 76.5 84.9 76.5 76.5H30.6V45.9Z" fill="#1A1A1A"/><path d="M168.3 30.6H183.5V15.3L168.3 0H107.1V30.6H122.4V45.9H107.1V76.5C107.1 84.9 113.9 91.8 122.4 91.8H168.3V76.5H183.6V45.9L168.3 30.6ZM168.3 76.5H122.4V45.9H168.3V76.5ZM168.3 30.6H122.4V15.3H168.3V30.6Z" fill="#1A1A1A"/><path d="M30.6 0V15.3H76.5V76.5H91.8V15.3L76.5 0H30.6Z" fill="#1A1A1A"/><path d="M227.8 3C239 3 246 10.2 246 22.5C246 34.7 239 42 227.8 42H215.9V3H227.8ZM220.8 37.7H227.6C235.8 37.7 241 32.3 241 22.5C241 12.6 235.8 7.2 227.6 7.2H220.8V37.7ZM250.9 28.2C250.9 18.9 256.2 13.7 264.8 13.7C273.4 13.7 278 19 278 27V29.3H255.5C255.6 35.1 259.1 38.9 264.8 38.9C270.3 38.9 272.8 35.9 273.2 33.4H277.4V34.2C276.8 37.6 273.5 42.7 264.8 42.7C256.3 42.7 250.9 37.5 250.9 28.2ZM255.6 25.6H273.5C273.4 21 270.5 17.5 264.8 17.5C259.1 17.5 255.9 21 255.6 25.6ZM284.3 18.3V14.4H295.1V9.7C295.1 5.2 297.6 3 302.2 3H314.2V6.8H300.3L299.8 7.3V14.4H313.6V18.3H299.8V42H295.1V18.3H284.3ZM319.7 28.2C319.7 18.9 325.1 13.7 333.7 13.7C342.3 13.7 346.9 19 346.9 27V29.3H324.4C324.5 35.1 327.9 38.9 333.7 38.9C339.1 38.9 341.6 35.9 342.1 33.4H346.3V34.2C345.6 37.6 342.4 42.7 333.7 42.7C325.1 42.7 319.7 37.5 319.7 28.2ZM324.4 25.6H342.3C342.3 21 339.4 17.5 333.6 17.5C328 17.5 324.8 21 324.4 25.6ZM355.5 14.4H360.1V18H360.5C362.5 14.9 365.9 13.8 369.9 13.8C376.4 13.8 380.6 17 380.6 23.8V42H375.8V24.3C375.8 19.7 373.3 17.7 368.9 17.7C364.1 17.7 360.2 20.6 360.2 26.7V42H355.5V14.4ZM388.8 28.2C388.8 18.9 394.5 13.7 403 13.7C411.4 13.7 415.3 18.7 415.7 23.1V23.9H411.2C411 21 408.7 17.7 403.1 17.7C397.3 17.7 393.6 21.3 393.6 28.2C393.6 35 397.2 38.7 403.1 38.7C408.8 38.7 410.9 35.4 411.3 32.3H415.8V33.1C415.3 37.6 411.5 42.7 403 42.7C394.4 42.7 388.8 37.5 388.8 28.2ZM423.1 28.2C423.1 18.9 428.4 13.7 437 13.7C445.6 13.7 450.2 19 450.2 27V29.3H427.7C427.8 35.1 431.3 38.9 437 38.9C442.4 38.9 444.9 35.9 445.4 33.4H449.6V34.2C449 37.6 445.7 42.7 437 42.7C428.5 42.7 423.1 37.5 423.1 28.2ZM427.8 25.6H445.6C445.6 21 442.7 17.5 436.9 17.5C431.3 17.5 428.1 21 427.8 25.6ZM232.8 53C239.7 53 244.8 56.2 244.8 62.8C244.8 69 240.8 71.1 238.5 71.6V72C241 72.6 245.6 74.6 245.6 81.4C245.6 88.6 240 92 232.9 92H216V53H232.8ZM220.9 87.8H232.4C237.2 87.8 240.7 85.9 240.7 81C240.7 76.1 237.2 74.3 232.4 74.3H220.9V87.8ZM220.9 70.1H232.1C236.6 70.1 240 68.4 240 63.6C240 58.9 236.6 57.2 232.1 57.2H220.9V70.1ZM276.7 92H272V88.4H271.6C269.6 91.5 266.2 92.6 262.2 92.6C255.7 92.6 251.7 89.3 251.7 82.5V64.4H256.4V82.1C256.4 86.7 258.9 88.6 263.3 88.6C268.1 88.6 271.9 85.8 271.9 79.7V64.4H276.7V92ZM303.9 64.4V88.2H314.5V92H285.2V88.2H299.1V68.2H288.5V64.4H303.9ZM298.4 59.7V54.4H304V59.7H298.4ZM338.3 53V88.2H348.9V92H319.6V88.2H333.6V56.8H322.9V53H338.3ZM380.4 53V92H375.7V88.2H375.3C373.2 91.4 369.9 92.6 366 92.6C358.8 92.6 353.3 87.7 353.3 78.2C353.3 68.6 358.8 63.8 366 63.8C369.8 63.8 373.1 64.9 375.2 68H375.6V53H380.4ZM358.1 78.2C358.1 84.9 361.7 88.7 367 88.7C372.2 88.7 375.8 84.9 375.8 78.2C375.8 71.5 372.2 67.7 367 67.7C361.7 67.7 358.1 71.5 358.1 78.2ZM388.6 78.2C388.6 68.9 394 63.7 402.6 63.7C411.1 63.7 415.8 69 415.8 77V79.3H393.3C393.3 85.1 396.8 88.9 402.5 88.9C408 88.9 410.5 85.9 410.9 83.4H415.2V84.2C414.5 87.6 411.3 92.7 402.6 92.7C394 92.7 388.6 87.5 388.6 78.2ZM393.3 75.6H411.2C411.2 71 408.3 67.5 402.5 67.5C396.9 67.5 393.7 71 393.3 75.6ZM427.1 64.4H431.7V68.9H432.2C433.4 66.2 435.9 64.3 441.7 64.3H450.8V68.4H441.8C435 68.4 431.9 71.7 431.9 78.8V92H427.1V64.4Z" fill="#1A1A1A"/></svg>',
    'accLockup': '<svg width="312" height="79" viewBox="0 0 312 79" xmlns="http://www.w3.org/2000/svg"><path d="M39.3 26.2H26.2V13.1H13.1V26.2H0V39.3H13.1V52.4H26.2V39.3H39.3V26.2ZM26.2 26.2V39.3H13.1V26.2H26.2Z" fill="#0069BF"/><path fill-rule="evenodd" clip-rule="evenodd" d="M78.5 65.4V13.1L65.4 0H26.2V13.1H65.4V65.4H26.2V52.4H13.1V78.5H52.3C59.6 78.5 65.4 72.7 65.4 65.4H78.5Z" fill="#1A1A1A"/><path d="M104.7 65.4V39.3H144V65.4L104.7 65.4ZM144 78.5V65.4H157V39.3L144 26.2H157V13.1L144 0H91.6V26.2V65.4C91.6 72.7 97.5 78.5 104.7 78.5H144ZM144 13.1V26.2H143.9H104.7V13.1H144Z" fill="#1A1A1A"/><path d="M188.1 2C194.3 2 198.1 6 198.1 12.8C198.1 19.6 194.3 23.6 188.1 23.6H181.5V2H188.1ZM184.2 21.2H188C192.5 21.2 195.4 18.2 195.4 12.8C195.4 7.3 192.5 4.4 188 4.4H184.2V21.2ZM200.8 15.9C200.8 10.8 203.8 7.9 208.5 7.9C213.3 7.9 215.9 10.8 215.9 15.3V16.6H203.4C203.4 19.8 205.4 21.8 208.5 21.8C211.6 21.8 212.9 20.2 213.2 18.8H215.5V19.2C215.1 21.1 213.3 23.9 208.6 23.9C203.8 23.9 200.8 21.1 200.8 15.9ZM203.4 14.5H213.3C213.3 11.9 211.7 10 208.5 10C205.4 10 203.6 12 203.4 14.5ZM219.3 10.4V8.3H225.3V5.7C225.3 3.2 226.7 2 229.2 2H235.9V4.1H228.2L227.9 4.4V8.3H235.5V10.4H227.9V23.6H225.3V10.4H219.3ZM238.9 15.9C238.9 10.8 241.9 7.9 246.6 7.9C251.4 7.9 253.9 10.8 253.9 15.3V16.6H241.5C241.5 19.8 243.5 21.8 246.6 21.8C249.6 21.8 251 20.2 251.3 18.8H253.6V19.2C253.2 21.1 251.4 23.9 246.6 23.9C241.9 23.9 238.9 21.1 238.9 15.9ZM241.5 14.5H251.4C251.4 11.9 249.8 10 246.6 10C243.5 10 241.7 12 241.5 14.5ZM258.7 8.3H261.2V10.3H261.5C262.6 8.6 264.5 8 266.7 8C270.3 8 272.6 9.8 272.6 13.5V23.6H269.9V13.8C269.9 11.3 268.5 10.2 266.1 10.2C263.4 10.2 261.3 11.7 261.3 15.1V23.6H258.7V8.3ZM277.1 15.9C277.1 10.8 280.2 7.9 285 7.9C289.6 7.9 291.8 10.7 292 13.1V13.6H289.5C289.4 12 288.1 10.1 285 10.1C281.8 10.1 279.8 12.2 279.8 15.9C279.8 19.7 281.8 21.8 285 21.8C288.2 21.8 289.3 19.9 289.6 18.2H292V18.7C291.8 21.2 289.7 23.9 285 23.9C280.2 23.9 277.1 21.1 277.1 15.9ZM296.1 15.9C296.1 10.8 299 7.9 303.8 7.9C308.5 7.9 311.1 10.8 311.1 15.3V16.6H298.6C298.7 19.8 300.6 21.8 303.8 21.8C306.8 21.8 308.2 20.2 308.4 18.8H310.8V19.2C310.4 21.1 308.6 23.9 303.8 23.9C299.1 23.9 296.1 21.1 296.1 15.9ZM298.7 14.5H308.6C308.5 11.9 306.9 10 303.7 10C300.6 10 298.9 12 298.7 14.5ZM190.8 29C194.6 29 197.5 30.8 197.5 34.4C197.5 37.9 195.2 39 194 39.3V39.5C195.4 39.9 197.9 41 197.9 44.7C197.9 48.7 194.8 50.6 190.9 50.6H181.5V29H190.8ZM184.3 48.3H190.6C193.3 48.3 195.2 47.2 195.2 44.5C195.2 41.8 193.3 40.8 190.6 40.8H184.3V48.3ZM184.3 38.4H190.5C192.9 38.4 194.8 37.5 194.8 34.9C194.8 32.3 192.9 31.3 190.5 31.3H184.3V38.4ZM215.1 50.6H212.5V48.6H212.3C211.2 50.3 209.3 50.9 207.1 50.9C203.5 50.9 201.3 49.1 201.3 45.3V35.3H203.9V45.1C203.9 47.6 205.3 48.7 207.7 48.7C210.4 48.7 212.5 47.2 212.5 43.8V35.3H215.1V50.6ZM230.2 35.3V48.5H236V50.6H219.8V48.5H227.5V37.4H221.6V35.3H230.2ZM227.1 32.7V29.8H230.2V32.7H227.1ZM249.2 29V48.5H255.1V50.6H238.9V48.5H246.6V31.1H240.7V29H249.2ZM272.5 29V50.6H269.9V48.5H269.6C268.5 50.2 266.7 50.9 264.5 50.9C260.5 50.9 257.5 48.2 257.5 42.9C257.5 37.7 260.5 35 264.5 35C266.6 35 268.4 35.6 269.6 37.3H269.8V29H272.5ZM260.2 42.9C260.2 46.7 262.1 48.7 265 48.7C267.9 48.7 269.9 46.7 269.9 42.9C269.9 39.2 267.9 37.1 265 37.1C262.1 37.1 260.2 39.2 260.2 42.9ZM277 42.9C277 37.8 280 34.9 284.7 34.9C289.5 34.9 292 37.8 292 42.3V43.6H279.6C279.6 46.8 281.5 48.8 284.7 48.8C287.7 48.8 289.1 47.2 289.4 45.8H291.7V46.2C291.3 48.1 289.5 50.9 284.7 50.9C280 50.9 277 48.1 277 42.9ZM279.6 41.5H289.5C289.5 38.9 287.9 37 284.7 37C281.6 37 279.8 39 279.6 41.5ZM298.3 35.3H300.9V37.8H301.1C301.8 36.3 303.2 35.3 306.4 35.3H311.4V37.5H306.4C302.7 37.5 301 39.4 301 43.3V50.6H298.3V35.3Z" fill="#1A1A1A"/><path d="M185.7 64H187.7L192 76.1V76.3H190.4L189.2 72.8H184.2L183 76.3H181.5V76.1L185.7 64ZM184.6 71.5H188.8L186.8 65.5H186.6L184.6 71.5ZM193.1 70.2C193.1 66 195.1 63.8 198.4 63.8C201.7 63.8 203 65.9 203 67.8V68.1H201.6C201.5 66.7 200.8 65.1 198.4 65.1C196 65.1 194.7 67 194.7 70.2C194.7 73.4 196 75.2 198.4 75.2C200.8 75.2 201.6 73.5 201.6 72.2H203.1V72.4C203 74.4 201.7 76.5 198.4 76.5C195.1 76.5 193.1 74.3 193.1 70.2ZM204.4 70.2C204.4 66 206.4 63.8 209.7 63.8C213 63.8 214.3 65.9 214.4 67.8V68.1H212.9C212.9 66.7 212.1 65.1 209.7 65.1C207.3 65.1 206 67 206 70.2C206 73.4 207.3 75.2 209.7 75.2C212.1 75.2 212.9 73.5 212.9 72.2H214.4V72.4C214.3 74.4 213 76.5 209.7 76.5C206.4 76.5 204.4 74.3 204.4 70.2ZM216.6 64H225.3V65.3H218.2V69.4H224.4V70.8H218.2V75H225.4V76.3H216.6V64ZM228.1 64H229.6V75H236.6V76.3H228.1V64ZM239.2 64H247.9V65.3H240.8V69.4H247.1V70.8H240.8V75H248V76.3H239.2V64ZM255.8 64C257.9 64 259.6 65.2 259.6 67.5C259.6 69.7 258 70.9 256 70.9H254L259.5 76.1V76.3H257.7L251.9 70.9H251.7V76.3H250.2V64H255.8ZM251.7 69.6H255.6C257 69.6 258 68.9 258 67.5C258 66.1 257 65.3 255.6 65.3H251.7V69.6ZM264.9 64H266.9L271.1 76.1V76.3H269.6L268.4 72.8H263.4L262.1 76.3H260.7V76.1L264.9 64ZM263.8 71.5H268L265.9 65.5H265.8L263.8 71.5ZM272.1 64H282.3V65.4H278V76.3H276.4V65.4H272.1V64ZM283.5 70.2C283.5 66 285.4 63.8 288.5 63.8C291.6 63.8 293.6 66 293.6 70.2C293.6 74.4 291.6 76.5 288.5 76.5C285.4 76.5 283.5 74.4 283.5 70.2ZM285 70.2C285 73.5 286.3 75.2 288.5 75.2C290.7 75.2 292 73.5 292 70.2C292 66.8 290.7 65.1 288.5 65.1C286.3 65.1 285 66.8 285 70.2ZM301.1 64C303.2 64 304.8 65.2 304.8 67.5C304.8 69.7 303.2 70.9 301.2 70.9H299.2L304.7 76.1V76.3H303L297.2 70.9H297V76.3H295.4V64H301.1ZM297 69.6H300.9C302.3 69.6 303.3 68.9 303.3 67.5C303.3 66.1 302.3 65.3 300.9 65.3H297V69.6Z" fill="#0069BF"/></svg>',
    'mark': '<svg width="92" height="46" viewBox="0 0 92 46" xmlns="http://www.w3.org/2000/svg"><path d="M22.8 15.2H15.2V7.6H7.6V15.2H0V22.8H7.6V30.4H15.2V22.8H22.8V15.2ZM15.2 15.2V22.8H7.6V15.2H15.2Z" fill="#494A4A"/><path fill-rule="evenodd" clip-rule="evenodd" d="M45.7 7.6V38.1H38.1V7.6H15.2V0H38.1L45.7 7.6ZM38.1 38.1C38.1 42.3 34.6 45.7 30.4 45.7H7.6V30.4H15.2V38.1H38.1Z" fill="#494A4A"/><path d="M83.7 15.2H91.3V7.6L83.7 0H53.3V15.2V38.1C53.3 42.3 56.7 45.7 60.9 45.7H76.1C80.3 45.7 83.7 42.3 83.7 38.1H91.3V22.8L83.7 15.2ZM83.7 15.2H83.7H60.9V7.6H83.7L83.7 15.2ZM83.7 38.1L60.9 38.1V22.8H83.7V38.1Z" fill="#494A4A"/></svg>',
    'eye': '<svg width="20" height="20" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg"><path d="M4.2 2.7C4.2 2.6 4.1 2.6 4 2.6C3.9 2.5 3.9 2.5 3.8 2.5C3.7 2.5 3.6 2.5 3.5 2.5C3.5 2.6 3.4 2.6 3.3 2.7C3.3 2.7 3.2 2.8 3.2 2.9C3.1 2.9 3.1 3 3.1 3.1C3.1 3.2 3.1 3.3 3.2 3.3C3.2 3.4 3.2 3.5 3.3 3.5L4.8 5.2C2 6.9 0.7 9.6 0.7 9.7C0.6 9.8 0.6 9.9 0.6 10C0.6 10.1 0.6 10.2 0.7 10.3C0.7 10.3 1.4 11.8 2.8 13.3C4.8 15.2 7.3 16.3 10 16.3C11.4 16.3 12.8 16 14.1 15.4L15.8 17.3C15.8 17.4 15.9 17.4 16 17.4C16.1 17.5 16.1 17.5 16.2 17.5C16.3 17.5 16.4 17.5 16.5 17.5C16.5 17.4 16.6 17.4 16.7 17.3C16.7 17.3 16.8 17.2 16.8 17.1C16.9 17.1 16.9 17 16.9 16.9C16.9 16.8 16.9 16.7 16.8 16.7C16.8 16.6 16.8 16.5 16.7 16.5L4.2 2.7ZM7.9 8.6L11.2 12.2C10.7 12.5 10.1 12.6 9.6 12.5C9 12.4 8.5 12.1 8.2 11.7C7.8 11.3 7.6 10.7 7.5 10.2C7.5 9.6 7.6 9.1 7.9 8.6ZM10 15C7.6 15 5.5 14.1 3.8 12.4C3 11.7 2.4 10.9 2 10C2.3 9.3 3.5 7.4 5.7 6.1L7.1 7.7C6.5 8.4 6.2 9.2 6.3 10.1C6.3 11 6.6 11.9 7.2 12.5C7.8 13.2 8.6 13.6 9.5 13.7C10.4 13.8 11.3 13.6 12 13.2L13.2 14.4C12.2 14.8 11.1 15 10 15ZM10.5 7.5C10.3 7.5 10.2 7.4 10.1 7.3C10 7.1 9.9 7 10 6.8C10 6.7 10.1 6.5 10.2 6.4C10.4 6.3 10.5 6.3 10.7 6.3C11.5 6.5 12.2 6.9 12.8 7.5C13.3 8.1 13.7 8.8 13.7 9.6C13.7 9.8 13.7 10 13.6 10.1C13.5 10.2 13.3 10.3 13.2 10.3C13.1 10.3 13.1 10.3 13.1 10.3C13 10.3 12.8 10.3 12.7 10.2C12.6 10.1 12.5 9.9 12.5 9.8C12.4 9.2 12.2 8.7 11.8 8.3C11.5 7.9 11 7.6 10.5 7.5ZM19.3 10.3C19.3 10.3 18.5 12.1 16.7 13.7C16.7 13.7 16.6 13.8 16.5 13.8C16.4 13.8 16.3 13.8 16.3 13.8C16.2 13.8 16.1 13.8 16 13.8C15.9 13.7 15.9 13.7 15.8 13.6C15.8 13.6 15.7 13.5 15.7 13.4C15.7 13.3 15.7 13.3 15.7 13.2C15.7 13.1 15.7 13 15.7 12.9C15.8 12.9 15.8 12.8 15.9 12.7C16.8 12 17.5 11 18.1 10C17.6 9.1 17 8.3 16.2 7.6C14.5 5.9 12.4 5 10 5C9.5 5 9 5 8.5 5.1C8.4 5.1 8.3 5.1 8.2 5.1C8.2 5.1 8.1 5.1 8 5C8 5 7.9 4.9 7.8 4.8C7.8 4.8 7.8 4.7 7.8 4.6C7.7 4.5 7.8 4.4 7.8 4.4C7.8 4.3 7.8 4.2 7.9 4.1C7.9 4.1 8 4 8.1 4C8.1 3.9 8.2 3.9 8.3 3.9C8.8 3.8 9.4 3.7 10 3.8C12.7 3.8 15.2 4.8 17.2 6.7C18.6 8.2 19.3 9.7 19.3 9.7C19.4 9.8 19.4 9.9 19.4 10C19.4 10.1 19.4 10.2 19.3 10.3H19.3Z" fill="#343330"/></svg>',
    'wmTop': '<svg width="1917" height="126" viewBox="0 0 1917 126" xmlns="http://www.w3.org/2000/svg"><path d="M0 126V65.4H202V126H0ZM202 -116.5L262.6 -55.9V65.4H202V-55.9H60.6V-116.5H202ZM60.6 4.8H0V-55.9H60.6V4.8ZM559.9 -55.9H499.3V-116.5H559.9V-55.9ZM499.3 4.8H358V-55.9H499.3V4.8ZM358 -55.9H297.4V-116.5H358V-55.9ZM358 4.8V65.4H559.9V126H358L297.4 65.4V4.8H358ZM655.3 4.8H594.7V-55.9H655.3V4.8ZM654 65.4L714.6 4.8H857.3V65.4H739.5L678.9 126H594.7V65.4H654ZM857.3 -55.9H655.3V-116.5H857.3V-55.9ZM1154.7 -55.9H1094V-116.5H1154.7V-55.9ZM1094 4.8H952.7V-55.9H1094V4.8ZM952.7 -55.9H892.1V-116.5H952.7V-55.9ZM952.7 4.8V65.4H1154.7V126H952.7L892.1 65.4V4.8H952.7ZM1391.4 -116.5L1452 -55.9V126H1391.4V-55.9H1250.1V126H1189.5V-55.9H1250.1V-116.5H1391.4ZM1749.4 -55.9H1547.4V-116.5H1749.4V-55.9ZM1486.8 -55.9H1547.4V65.4H1749.4V126H1547.4L1486.8 65.4V-55.9ZM2046.8 -55.9H1986.1V-116.5H2046.8V-55.9ZM1986.1 4.8H1844.8V-55.9H1986.1V4.8ZM1844.8 -55.9H1784.2V-116.5H1844.8V-55.9ZM1844.8 4.8V65.4H2046.8V126H1844.8L1784.2 65.4V4.8H1844.8Z" fill="#CDCDCD"/></svg>',
    'quoteMark': '<svg width="45" height="30" viewBox="0 0 45 30" xmlns="http://www.w3.org/2000/svg"><path d="M0 30V19C0 8.5 6.5 1.3 17 0V6.8C10.8 7.9 7.5 11.9 7.5 17H15V30H0Z" fill="#F2F2F2"/><path d="M24.5 30V19C24.5 8.5 31 1.3 41.5 0V6.8C35.3 7.9 32 11.9 32 17H39.5V30H24.5Z" fill="#F2F2F2"/></svg>',
    'wmBottom': '<svg width="1845" height="122" viewBox="0 0 1845 122" xmlns="http://www.w3.org/2000/svg"><path d="M202 181.9V121.2H262.6V181.9L202 242.5H60.6V181.9H202ZM60.6 181.9H0V0H60.6V181.9ZM202 121.2H121.2V60.6H202V121.2ZM262.6 60.6H202V0H262.6V60.6ZM358 181.9H297.4V0H358V181.9ZM499.3 0H559.9V181.9L499.3 242.5H358V181.9H499.3V0ZM655.3 242.5H594.7V0H655.3V242.5ZM750.7 181.9H690.1V0H750.7V181.9ZM750.7 181.9H952.7V242.5H750.4V181.9H750.7ZM987.5 242.8V182.2L1189.4 181.9V242.5V242.8H987.5ZM1189.4 0L1250.1 60.6V181.9H1189.4V60.6H1048.1V0H1189.4ZM1048.1 121.6H987.5V61H1048.1V121.6ZM1547.4 60.6H1486.8V0H1547.4V60.6ZM1486.8 121.2H1345.5V60.6H1486.8V121.2ZM1345.5 60.6H1284.8V0H1345.5V60.6ZM1345.5 121.2V181.9H1547.4V242.5H1345.5L1284.8 181.9V121.2H1345.5ZM1642.8 242.5H1582.2V181.9H1642.8V242.5ZM1702.1 181.9H1642.8V121.2H1727L1787.6 181.9H1844.8V242.5H1762.7L1702.1 181.9ZM1844.8 121.2H1784.2V60.6H1642.8V121.2H1582.2V0H1784.2L1844.8 60.6V121.2Z" fill="#CDCDCD"/></svg>',
    'plate': '<svg width="1802" height="626" viewBox="0 0 1802 626" xmlns="http://www.w3.org/2000/svg"><path d="M1649.1 0.4C1653.8 0.4 1658.2 2.3 1661.5 5.5C1664.8 8.8 1666.6 13.3 1666.6 17.9V53.8C1666.6 58.7 1668.5 63.3 1672 66.8C1675.4 70.2 1680.1 72.1 1685 72.1H1711.9C1721.5 72.1 1729.4 80 1729.4 89.6V143.4C1729.4 148.3 1731.3 153 1734.7 156.4C1738.2 159.9 1742.8 161.8 1747.7 161.8H1783.6C1788.2 161.8 1792.7 163.6 1796 166.9C1799.2 170.2 1801.1 174.6 1801.1 179.3V446.2C1801.1 450.9 1799.2 455.3 1796 458.6C1792.7 461.9 1788.2 463.7 1783.6 463.7H1747.7C1742.8 463.7 1738.2 465.7 1734.7 469.1C1731.3 472.5 1729.4 477.2 1729.4 482.1V535.9C1729.4 545.5 1721.5 553.4 1711.9 553.4H1685C1674.8 553.4 1666.6 561.6 1666.6 571.7V607.7C1666.6 612.3 1664.8 616.8 1661.5 620.1C1658.2 623.3 1653.8 625.2 1649.1 625.2H188.3C188.1 625.2 188 625.3 187.9 625.4C185 625.4 166.8 625.4 152.4 625.4C147.7 625.4 143.3 623.6 140 620.3C136.7 617 134.9 612.6 134.9 608V571.9C134.9 561.8 126.7 553.6 116.6 553.6L89.6 553.4C79.9 553.4 72.1 545.6 72.1 536V482.1C72.1 477.4 70.3 472.8 67.1 469.4L66.8 469.1C63.3 465.7 58.7 463.7 53.8 463.7H17.9C13.3 463.7 8.8 461.9 5.5 458.6C2.3 455.3 0.4 450.9 0.4 446.2V179.3C0.4 174.6 2.3 170.2 5.5 166.9C8.8 163.6 13.3 161.8 17.9 161.8H53.8C58.7 161.8 63.3 159.9 66.8 156.4C70.2 153 72.1 148.3 72.1 143.4V89.7C72.1 85.1 74 80.6 77.3 77.3C80.6 74 85.1 72.2 89.7 72.2L116.5 72.3C121.3 72.3 126 70.4 129.5 67C132.9 63.5 134.9 58.9 134.9 54V18.2C134.9 13.5 136.7 9.1 140 5.8C143.3 2.5 147.7 0.7 152.4 0.7H188.3L188.4 0.7L188.4 0.7L188.8 0.5L188.7 0.4H192.5C195.3 0.4 199.4 0.4 204.7 0.4C215.4 0.4 230.9 0.4 250.8 0.4C290.4 0.4 347 0.4 414.9 0.4C550.7 0.4 731.8 0.4 913.4 0.4L1649.1 0.4ZM98.6 517.9C93.4 517.9 89.2 522.1 89.2 527.3C89.2 532.4 93.4 536.7 98.6 536.7C103.8 536.7 108 532.4 108 527.3C108 522.1 103.8 517.9 98.6 517.9ZM1702.9 517.9C1697.7 517.9 1693.5 522.1 1693.5 527.3C1693.5 532.4 1697.7 536.7 1702.9 536.7C1708.1 536.7 1712.3 532.4 1712.3 527.3C1712.3 522.1 1708.1 517.9 1702.9 517.9ZM26.9 428.2C21.7 428.2 17.5 432.4 17.5 437.6C17.5 442.8 21.7 447 26.9 447C32.1 447 36.3 442.8 36.3 437.6C36.3 432.4 32.1 428.2 26.9 428.2ZM1774.6 428.2C1769.4 428.2 1765.2 432.4 1765.2 437.6C1765.2 442.8 1769.4 447 1774.6 447C1779.8 447 1784 442.8 1784 437.6C1784 432.4 1779.8 428.2 1774.6 428.2ZM26.9 179.2C21.7 179.2 17.5 183.4 17.5 188.6C17.5 193.8 21.7 198 26.9 198C32.1 198 36.3 193.8 36.3 188.6C36.3 183.4 32.1 179.2 26.9 179.2ZM1774.6 179.2C1769.4 179.2 1765.2 183.4 1765.2 188.6C1765.2 193.8 1769.4 198 1774.6 198C1779.8 198 1784 193.8 1784 188.6C1784 183.4 1779.8 179.2 1774.6 179.2ZM98.6 89.6C93.4 89.6 89.2 93.8 89.2 99C89.2 104.2 93.4 108.4 98.6 108.4C103.8 108.4 108 104.2 108 99C108 93.8 103.8 89.6 98.6 89.6ZM1702.9 89.6C1697.7 89.6 1693.5 93.8 1693.5 99C1693.5 104.2 1697.7 108.4 1702.9 108.4C1708.1 108.4 1712.3 104.2 1712.3 99C1712.3 93.8 1708.1 89.6 1702.9 89.6Z" fill="white" stroke="#B1B1B1" stroke-width="0.9"/></svg>',
}

# ---------- 3. Units & primitives ----------
def I(px):
    """px -> Inches (EMU under the hood). inches = px / 144."""
    return Inches(px / 144)


def PT(px):
    """px -> Pt. pt = px / 2."""
    return Pt(px / 2)


def rgb(hexstr):
    return RGBColor.from_string(hexstr)


_VIEWBOX_RE = re.compile(r'viewBox="([\d.\s-]+)"')


def svg_raster(svg, out_width_px, flatten_on=None):
    """Rasterize at 3x the placed size via cairosvg. Returns (png_bytes, height_over_width_ratio).
    ratio is taken from the ACTUAL rendered raster, never assumed from the viewBox, so a
    padded/mismeasured SVG never distorts the placed height (mirrors the JS version)."""
    density_w = max(1, round(out_width_px * 3))
    kwargs = {'bytestring': svg.encode('utf-8'), 'output_width': density_w}
    if flatten_on:
        kwargs['background_color'] = '#' + flatten_on
    png_bytes = cairosvg.svg2png(**kwargs)
    with Image.open(io.BytesIO(png_bytes)) as img:
        ratio = img.height / img.width
    return png_bytes, ratio


def place_svg(slide, svg, x, y, w, flatten_on=None):
    """Raster + place an SVG; height is derived from the raster's own ratio. Returns placed height (px)."""
    png_bytes, ratio = svg_raster(svg, w, flatten_on)
    h = w * ratio
    slide.shapes.add_picture(io.BytesIO(png_bytes), I(x), I(y), I(w), I(h))
    return h


def recolor(svg, frm, to):
    return svg.replace(f'fill="#{frm}"', f'fill="#{to}"')


def _no_shadow(shape):
    """shadow.inherit=False alone leaves an empty <a:effectLst/> that should override the
    theme's effectRef, but LibreOffice's renderer doesn't reliably honor that override (a
    faint shadow still showed under cards in QA). Belt and suspenders: also strip the
    <p:style> element outright — every shape here sets its own explicit fill/line color
    already, so the theme style reference (which is what carries effectRef) is never needed."""
    shape.shadow.inherit = False
    style_el = shape._element.find(qn('p:style'))
    if style_el is not None:
        shape._element.remove(style_el)


def rect(slide, x, y, w, h, fill, line=None, line_w=0.75, radius=None):
    shape_type = MSO_SHAPE.ROUNDED_RECTANGLE if radius is not None else MSO_SHAPE.RECTANGLE
    shp = slide.shapes.add_shape(shape_type, I(x), I(y), I(w), I(h))
    shp.fill.solid()
    shp.fill.fore_color.rgb = rgb(fill)
    if line:
        shp.line.color.rgb = rgb(line)
        shp.line.width = Pt(line_w)
    else:
        shp.line.fill.background()
    _no_shadow(shp)
    if radius is not None:
        radius_emu = I(radius)
        min_side = min(shp.width, shp.height)
        frac = 0.0 if min_side == 0 else max(0.0, min(1.0, radius_emu / (min_side / 2)))
        shp.adjustments[0] = frac
    return shp


def dot(slide, x, y, d, fill):
    shp = slide.shapes.add_shape(MSO_SHAPE.OVAL, I(x), I(y), I(d), I(d))
    shp.fill.solid()
    shp.fill.fore_color.rgb = rgb(fill)
    shp.line.fill.background()
    _no_shadow(shp)
    return shp


# "Plain text with **accent words**" -> [(text, is_accent), ...]
def runs(content):
    parts = re.split(r'(\*\*[^*]+\*\*)', str(content))
    out = []
    for p in parts:
        if not p:
            continue
        if p.startswith('**') and p.endswith('**') and len(p) > 4:
            out.append((p[2:-2], True))
        else:
            out.append((p, False))
    return out


_ALIGN = {'left': PP_ALIGN.LEFT, 'center': PP_ALIGN.CENTER, 'right': PP_ALIGN.RIGHT}
_VALIGN = {'top': MSO_ANCHOR.TOP, 'middle': MSO_ANCHOR.MIDDLE, 'bottom': MSO_ANCHOR.BOTTOM}


def _set_char_spacing(run, spacing_pt):
    if not spacing_pt:
        return
    rPr = run._r.get_or_add_rPr()
    rPr.set('spc', str(int(round(spacing_pt * 100))))


def text(slide, content, x, y, w, h, size, font=None, color=None, bold=False, accent=None,
         align='left', valign='top', lh=1.2, spacing=0, caps=False, para_after=0):
    """size is a Figma px value (T.title etc). margin=0 always, so text aligns with shapes at the same x."""
    font = font or F['sans']
    color = color or N['text']
    box = slide.shapes.add_textbox(I(x), I(y), I(w), I(h))
    tf = box.text_frame
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.word_wrap = True
    tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.vertical_anchor = _VALIGN[valign]
    display = str(content).upper() if caps else content
    run_list = runs(display) if isinstance(display, str) else display
    p = tf.paragraphs[0]
    p.alignment = _ALIGN[align]
    p.line_spacing = Pt(size * lh / 2)
    if para_after:
        p.space_after = Pt(para_after)
    for t, is_accent in run_list:
        r = p.add_run()
        r.text = t
        r.font.size = Pt(size / 2)
        r.font.bold = bold
        r.font.name = font
        r.font.color.rgb = rgb(accent if (is_accent and accent) else color)
        _set_char_spacing(r, spacing)
    return box


# Conservative fit estimate. Real PowerPoint renders (FK Grotesk / DM Mono) wrap earlier than a
# naive average-advance estimate predicts — this exact 0.7/0.66 pair was verified against real
# PowerPoint screenshots showing both chip labels and card bullet text overflowing their boxes at
# lower multipliers. These wider per-char multipliers intentionally overestimate width (underestimate
# chars/line) so every box sized from lines_needed() has slack rather than clipping. Do not tighten
# without re-verifying against a real PowerPoint render (LibreOffice did not catch either original bug,
# and this port has not yet re-earned that verification for python-pptx's own XML — see docs/qa.md).
def lines_needed(s, size_px, box_w, mono=False):
    per_line = max(1, math.floor(box_w / (size_px * (0.66 if mono else 0.7))))
    total = 0
    clean = re.sub(r'\*\*', '', str(s))
    for para in clean.split('\n'):
        total += max(1, math.ceil(len(para) / per_line))
    return total


def _set_bullet(paragraph, char='■', indent_pt=0, color_hex=None, size_pct=60):
    """Square bullet, colored, via raw pPr XML — python-pptx has no high-level bullet API.
    Element order inside <a:pPr> matters (schema): lnSpc, spcBef, spcAft, buClr, buSzPct, buFont,
    buChar must come in that order, appended AFTER whatever spacing pPr already has (python-pptx
    inserts lnSpc/spcAft correctly when line_spacing/space_after are set first)."""
    pPr = paragraph._p.get_or_add_pPr()
    indent_emu = int(round(indent_pt * 12700))  # 1 pt = 12700 EMU
    pPr.set('marL', str(indent_emu))
    pPr.set('indent', str(-indent_emu))
    ns = 'http://schemas.openxmlformats.org/drawingml/2006/main'
    if color_hex:
        buClr = pPr.makeelement(qn('a:buClr'), {})
        srgb = buClr.makeelement(qn('a:srgbClr'), {'val': color_hex})
        buClr.append(srgb)
        pPr.append(buClr)
    buSzPct = pPr.makeelement(qn('a:buSzPct'), {'val': str(int(size_pct * 1000))})
    pPr.append(buSzPct)
    buFont = pPr.makeelement(qn('a:buFont'), {'typeface': F['mono']})
    pPr.append(buFont)
    buChar = pPr.makeelement(qn('a:buChar'), {'char': char})
    pPr.append(buChar)


def bullet_text(slide, items, x, y, w, h, size, accent=None, gap=24):
    """Native bullet list: one text box, one paragraph per item, square bullet colored with accent."""
    box = slide.shapes.add_textbox(I(x), I(y), I(w), I(h))
    tf = box.text_frame
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.word_wrap = True
    tf.auto_size = MSO_AUTO_SIZE.NONE
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.line_spacing = Pt(size * 1.3 / 2)
        p.space_after = Pt(gap / 2)
        for t, is_accent in runs(item):
            r = p.add_run()
            r.text = t
            r.font.size = Pt(size / 2)
            r.font.name = F['sans']
            r.font.bold = False
            r.font.color.rgb = rgb(accent if (is_accent and accent) else N['text'])
        _set_bullet(p, char='■', indent_pt=size * 0.9 / 2, color_hex=accent, size_pct=60)
    return box


# ---------- 3b. Chip sizing — shared by every chip/pill/label box. Direct port of chipBox() —
# same 0.66 mono coefficient as lines_needed(), same +2px rounding buffer. Always use this instead
# of a hand-rolled `len(label) * size * k + pad` formula — see docs/pitfalls.md. ----------
def chip_box(label, max_w, size_px=None):
    size_px = size_px or T['chip']
    chip_inset = 18
    cw = min(max_w, round(len(str(label)) * size_px * 0.66) + chip_inset * 2 + 2)
    lines = lines_needed(label, size_px, cw - chip_inset * 2, mono=True)
    h = max(47, lines * size_px * 1.35 + 16)
    return cw, h, chip_inset


# ---------- 4. Deck + shared chrome ----------
class Deck:
    def __init__(self, prs, theme, direction, confidential):
        self.prs = prs
        self.theme = theme
        self.direction = direction
        self.confidential = confidential


def create_deck(direction, title='Defence Builder', confidential=True):
    theme = THEMES.get(direction)
    if not theme:
        raise ValueError(f'direction must be "ecosystem" or "accelerator", got {direction!r}')
    prs = Presentation()
    prs.slide_width = I(1920)
    prs.slide_height = I(1080)
    core_props = prs.core_properties
    core_props.title = title
    return Deck(prs, theme, direction, confidential)


def _blank_slide(deck):
    return deck.prs.slides.add_slide(deck.prs.slide_layouts[6])  # blank layout


def badge(deck, slide):  # CONFIDENTIAL badge, top-right
    if not deck.confidential:
        return
    rect(slide, 1707, 10, 203, 40, N['white'], line=N['line'], line_w=0.75)
    place_svg(slide, recolor(SVG['eye'], '343330', N['text2']), 1727, 20, 20)
    text(slide, 'Confidential', x=1760, y=10, w=140, h=40, size=T['label'], font=F['monoMed'],
         color=N['text2'], caps=True, valign='middle')


def dots(deck, slide):  # the 3-pixel motif, bottom-right
    dot(slide, 1823, 976, 11, N['faint'])
    dot(slide, 1816, 989, 11, N['dark'])
    dot(slide, 1829, 989, 11, N['dark'])


def chrome(deck, slide, watermark=True, brand=True, badge_on=True, dots_on=True, eyebrow=None,
           title=None, source=None, bg=None, notes=None):
    bg_hex = bg or N['bg']
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = rgb(bg_hex)
    if watermark:
        place_svg(slide, recolor(SVG['wmTop'], 'CDCDCD', N['wm']), 0, 0, 1917, bg_hex)
        place_svg(slide, recolor(SVG['wmBottom'], 'CDCDCD', N['wm']), 0, 959, 1845, bg_hex)
    if brand:
        if deck.direction == 'ecosystem':
            place_svg(slide, SVG['mark'], 1759, 80, 91)
        else:
            place_svg(slide, SVG['accLockup'], 1655, 68, 206)
    if badge_on:
        badge(deck, slide)
    if dots_on:
        dots(deck, slide)
    if eyebrow:
        cw, h, chip_inset = chip_box(eyebrow, 1500, T['eyebrow'])
        rect(slide, 60, 60, cw, h, deck.theme['accent'])
        text(slide, eyebrow, x=60 + chip_inset, y=60, w=cw - chip_inset * 2, h=h, size=T['eyebrow'],
             font=F['monoMed'], color=N['white'], caps=True, valign='middle', spacing=0.5, lh=1.2)
    if title:
        lines = lines_needed(title, T['title'], 1500)
        text(slide, title, x=60, y=172, w=1500, h=max(1, lines) * T['title'] * 1.3, size=T['title'],
             bold=True, accent=deck.theme['accent'], lh=1.3)
    if source:
        text(slide, source, x=60, y=1011, w=1720, h=32, size=T['source'], font=F['mono'],
             color=N['text2'], caps=True, valign='middle')
    if notes:
        slide.notes_slide.notes_text_frame.text = notes


def content_top(title):
    """Content area below a 1-line title: y ~300..990. Two-line title pushes it down."""
    return 172 + max(1, lines_needed(title or '', T['title'], 1500)) * T['title'] * 1.3 + 50


# ---------- 5. Image "cover" placement (crop-to-fill, matches pptxgenjs sizing:{type:'cover'}) ----------
def _add_image_cover(slide, path, x, y, w, h):
    """Place an image filling (x,y,w,h) exactly, cropping the longer axis — object-fit: cover."""
    with Image.open(path) as im:
        img_w, img_h = im.size
    img_ratio = img_w / img_h
    box_ratio = w / h
    crop_left = crop_right = crop_top = crop_bottom = 0.0
    if img_ratio > box_ratio:  # image relatively wider than box -> crop left/right
        keep = box_ratio / img_ratio
        crop_left = crop_right = (1 - keep) / 2
    elif img_ratio < box_ratio:  # image relatively taller than box -> crop top/bottom
        keep = img_ratio / box_ratio
        crop_top = crop_bottom = (1 - keep) / 2
    pic = slide.shapes.add_picture(path, I(x), I(y), I(w), I(h))
    pic.crop_left = crop_left
    pic.crop_right = crop_right
    pic.crop_top = crop_top
    pic.crop_bottom = crop_bottom
    return pic


# ---------- 6. Layouts ----------
def cover(deck, title, subtitle=None, description=None, pills=None, date=None, hero=None, notes=None):
    prs, theme, direction = deck.prs, deck.theme, deck.direction
    s = _blank_slide(deck)
    chrome(deck, s, brand=False, badge_on=False, dots_on=False)
    if hero:
        _add_image_cover(s, hero, 1000, 0, 920, 1080)
    lock = SVG['ecoLockup'] if direction == 'ecosystem' else SVG['accLockup']
    place_svg(s, lock, 120, 100, 459 if direction == 'ecosystem' else 363)
    short = len(title) <= 12
    t_size = T['coverTitleShort'] if short else T['coverTitleLong']
    t_lines = lines_needed(title, t_size, 1000, mono=True)
    t_h = t_lines * t_size * 0.95
    text(s, title, x=120, y=330, w=1000, h=t_h, size=t_size, font=F['display'], caps=True,
         lh=0.9, spacing=-3 if short else 0)
    y = 330 + t_h + 40
    rect(s, 120, y, 1000, 2, N['line'])  # underline divider — matches Figma node 4:81
    y += 38
    if subtitle:
        l = lines_needed(subtitle, T['coverSub'], 820)
        text(s, subtitle, x=120, y=y, w=820, h=l * T['coverSub'] * 1.2, size=T['coverSub'],
             bold=True, accent=theme['accent'])
        y += l * T['coverSub'] * 1.2 + 40
    if description:
        text(s, description, x=120, y=y, w=820, h=2 * T['coverDesc'] * 1.2, size=T['coverDesc'])
    px = 120  # pills: tint fill, accent mono caps
    for p in (pills or [])[:3]:
        w = round(len(p) * T['pill'] * 0.74) + 70
        rect(s, px, 920, w, 83, theme['tint'], radius=41.5)
        text(s, p, x=px, y=920, w=w, h=83, size=T['pill'], font=F['monoMed'], color=theme['accent'],
             caps=True, align='center', valign='middle')
        px += w + 42
    if not hero:  # fallback graphic: oversized DB mark, cross in accent
        big = recolor(SVG['mark'], '494A4A', N['line']).replace(f"fill=\"#{N['line']}\"", f"fill=\"#{theme['accent']}\"")
        place_svg(s, big, 1130, 390, 640)
    badge(deck, s)
    dots(deck, s)
    if date:
        text(s, date, x=1475, y=1011, w=300, h=32, size=T['source'], font=F['mono'], color=N['text2'],
             caps=True, align='right', valign='middle')
    if notes:
        s.notes_slide.notes_text_frame.text = notes
    return s


def statement(deck, text_, eyebrow=None, hero=None, notes=None):  # one big sentence with **accent** words
    s = _blank_slide(deck)
    chrome(deck, s, eyebrow=eyebrow, notes=notes)
    size = 80 if lines_needed(text_, T['statement'], 1400) > 3 else T['statement']
    lines = lines_needed(text_, size, 1400)
    h = lines * size * 1.32
    if hero:
        _add_image_cover(s, hero, 1300, 143, 620, 937)
    text(s, text_, x=70, y=(1080 - h) / 2, w=1400, h=h, size=size, bold=True, accent=deck.theme['accent'], lh=1.32)
    return s


def points(deck, title, items, eyebrow=None, source=None, left_visual=False, notes=None):
    """items: [{'head': ..., 'detail': ...}, ...], up to 4."""
    s = _blank_slide(deck)
    chrome(deck, s, eyebrow=eyebrow, title=title, source=source, notes=notes)
    top = content_top(title)
    items = items[:4]
    gap = min(170, (960 - top) / len(items))
    x, w = (700, 1100) if left_visual else (60, 1500)
    for i, it in enumerate(items):
        y = top + i * gap
        rect(s, x, y + 14, 14, 14, deck.theme['accent'])
        text(s, it['head'], x=x + 40, y=y, w=w - 40, h=T['h2'] * 1.2, size=T['h2'], bold=True, accent=deck.theme['accent'])
        if it.get('detail'):
            text(s, it['detail'], x=x + 40, y=y + T['h2'] * 1.2 + 8, w=w - 40, h=gap - T['h2'] * 1.2 - 20,
                 size=T['bodySm'] * 1.25, color=N['text2'])
    return s


def stats(deck, title, items, eyebrow=None, source=None, notes=None):
    """items: [{'value': ..., 'label': ...}, ...], 2–4."""
    s = _blank_slide(deck)
    chrome(deck, s, eyebrow=eyebrow, title=title, source=source, notes=notes)
    items = items[:4]
    n = len(items)
    gut = 40
    w = (1800 - gut * (n - 1)) / n
    top = max(content_top(title), 420)
    for i, it in enumerate(items):
        x = 60 + i * (w + gut)
        rect(s, x, top, w, 400, N['card'])
        vsize = 80 if len(it['value']) > 6 else T['statValue']
        text(s, it['value'], x=x + 40, y=top + 40, w=w - 80, h=T['statValue'] * 1.1, size=vsize,
             bold=True, color=deck.theme['accent'], lh=1.0)
        text(s, it['label'], x=x + 40, y=top + 200, w=w - 80, h=160, size=T['body'], color=N['text2'])
    return s


def cards(deck, title, cards_, eyebrow=None, source=None, highlight=0, notes=None):
    """cards_: [{'label': ..., 'value': (optional), 'bullets': [...]}, ...], 2–3.
    First card highlighted by default. value renders boxless, accent-colored — same treatment as stats()."""
    theme = deck.theme
    s = _blank_slide(deck)
    chrome(deck, s, eyebrow=eyebrow, title=title, source=source, notes=notes)
    lst = cards_[:3]
    n = len(lst)
    gut = 47
    w = (1790 - gut * (n - 1)) / n
    top = content_top(title)
    pad = 28
    body_w = w - pad * 2 - 22

    def card_height(c):
        _, chip_h, _ = chip_box(c['label'], w - pad * 2)
        v_h = ((80 if len(c['value']) > 6 else T['statValue']) * 1.1) if c.get('value') else 0
        h = pad + chip_h + 47 + (v_h + 47 if c.get('value') else 0)
        for b in c.get('bullets') or []:
            h += lines_needed(b, T['body'], body_w) * T['body'] * 1.3 + 24
        return h + pad

    card_h = min(max(card_height(c) for c in lst), 990 - top)
    for i, c in enumerate(lst):
        x = 60 + i * (w + gut)
        hi = i == (highlight if highlight is not None else 0)
        rect(s, x, top, w, card_h, theme['tint'] if hi else N['cardAlt'],
             line=theme['accent'] if hi else N['faint'], line_w=0.75)
        y = top + pad
        cw, chip_h, chip_inset = chip_box(c['label'], w - pad * 2)
        rect(s, x + pad, y, cw, chip_h, theme['chip'] if hi else N['line'])
        text(s, c['label'], x=x + pad + chip_inset, y=y, w=cw - chip_inset * 2, h=chip_h, size=T['chip'],
             font=F['mono'], caps=True, valign='middle', lh=1.25)
        y += chip_h + 47
        if c.get('value'):
            v_size = 80 if len(c['value']) > 6 else T['statValue']
            text(s, c['value'], x=x + pad, y=y, w=w - pad * 2, h=v_size * 1.1, size=v_size, bold=True,
                 color=theme['accent'], lh=1.0)
            y += v_size * 1.1 + 47
        if c.get('bullets'):
            bullet_text(s, c['bullets'], x=x + pad, y=y, w=w - pad * 2, h=top + card_h - pad - y,
                        size=T['body'], accent=theme['accent'])
    return s


# Solid-accent pull-quote block — matches Figma node 2202:6432. quote_block_metrics() is pure
# geometry (no drawing) so callers can measure before committing to a slide (e.g. to vertically
# center: top + (avail - h) / 2), mirroring quoteBlock()/quoteBlockMetrics() in the JS version.
def quote_block_metrics(w, label, quote, cite=None, scale=1):
    pad = round(32 * scale)
    gap = round(14 * scale)
    icon_h = round(36 * scale)
    label_size = round(20 * scale)
    quote_size = round(26 * scale)
    cite_size = round(18 * scale)
    inner_w = w - pad * 2
    col_w = (inner_w - gap) / 2
    label_lines = lines_needed(label, label_size, col_w, mono=True)
    left_h = icon_h + round(10 * scale) + label_lines * label_size * 1.3
    quote_lines = lines_needed(quote, quote_size, col_w)
    quote_h = quote_lines * quote_size * 1.35
    cite_lines = lines_needed(cite, cite_size, col_w) if cite else 0
    right_h = quote_h + (round(14 * scale) + cite_lines * cite_size * 1.3 if cite else 0)
    h = pad * 2 + max(left_h, right_h)
    return {'h': h, 'pad': pad, 'gap': gap, 'iconH': icon_h, 'labelSize': label_size,
            'quoteSize': quote_size, 'citeSize': cite_size, 'colW': col_w, 'labelLines': label_lines,
            'quoteH': quote_h, 'citeLines': cite_lines}


def quote_block(deck, slide, x, y, w, label, quote, cite=None, scale=1):
    theme = deck.theme
    m = quote_block_metrics(w, label, quote, cite, scale)
    h, pad, gap, icon_h = m['h'], m['pad'], m['gap'], m['iconH']
    label_size, quote_size, cite_size, col_w = m['labelSize'], m['quoteSize'], m['citeSize'], m['colW']
    label_lines, quote_h, cite_lines = m['labelLines'], m['quoteH'], m['citeLines']
    rect(slide, x, y, w, h, theme['accent'])
    place_svg(slide, SVG['quoteMark'], x + pad, y + pad, round(54 * scale))
    text(slide, label, x=x + pad, y=y + pad + icon_h + round(10 * scale), w=col_w,
         h=label_lines * label_size * 1.3, size=label_size, font=F['monoMed'], color='F2F2F2',
         caps=True, lh=1.3)
    tx = x + pad + col_w + gap
    text(slide, quote, x=tx, y=y + pad, w=col_w, h=quote_h, size=quote_size, bold=True,
         color=N['white'], accent=N['text'], lh=1.35)
    if cite:
        text(slide, cite, x=tx, y=y + pad + quote_h + round(14 * scale), w=col_w,
             h=cite_lines * cite_size * 1.3, size=cite_size, color='FFD9C4', lh=1.3)
    return h


def bars(deck, title, data, eyebrow=None, unit=None, points_=None, source=None, notes=None):
    """data: [{'label':..., 'value': number, 'display': '...'}], 2–6. points_: 1–3 side {'head','detail'}."""
    theme = deck.theme
    s = _blank_slide(deck)
    chrome(deck, s, eyebrow=eyebrow, title=title, source=source, notes=notes)
    top = content_top(title)
    base = 930
    max_h = base - top - 80
    data = data[:6]
    max_v = max(d['value'] for d in data)
    col_w, gut = 197, 57
    if unit:
        text(s, unit, x=60, y=top - 10, w=560, h=31, size=T['label'], font=F['mono'], color=N['text'], caps=True)
    for i, d in enumerate(data):
        x = 80 + i * (col_w + gut)
        h = max(40, max_h * d['value'] / max_v)
        rect(s, x, base - h, col_w, h, theme['accent'])
        text(s, d.get('display', str(d['value'])), x=x, y=base - h + 20, w=col_w, h=40, size=34,
             font=F['display'], color=N['white'], align='center')
        text(s, d['label'], x=x, y=base + 6, w=col_w, h=39, size=28, font=F['mono'], color=N['text2'], align='center')
    side_x = 80 + len(data) * (col_w + gut) + 60
    if points_ and side_x < 1500:
        w = 1860 - side_x
        gap = (base - top) / len(points_)
        for i, p in enumerate(points_):
            text(s, p['head'], x=side_x, y=top + i * gap, w=w, h=T['h2'] * 1.2, size=T['h2'], bold=True)
            if p.get('detail'):
                text(s, p['detail'], x=side_x, y=top + i * gap + T['h2'] * 1.2 + 8, w=w,
                     h=gap - T['h2'] * 1.2 - 30, size=T['body'], color=N['text2'])
    return s


def closing(deck, title='Thank you!', contact=None, hero=None, notes=None):
    s = _blank_slide(deck)
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = rgb(N['closingBg'])
    if hero:
        _add_image_cover(s, hero, 0, 0, 1920, 1080)
    place_svg(s, SVG['plate'], 59, 227, 1802)
    text(s, title, x=333, y=430, w=1255, h=130, size=T['closing'], bold=True, align='center',
         valign='middle', lh=1.0)
    if contact:
        text(s, contact, x=460, y=570, w=1000, h=60, size=T['closingSub'], align='center', valign='top')
    lock = SVG['ecoLockup'] if deck.direction == 'ecosystem' else SVG['accLockup']
    lw = 230 if deck.direction == 'ecosystem' else 182
    place_svg(s, lock, (1920 - lw) / 2, 300, lw)
    if notes:
        s.notes_slide.notes_text_frame.text = notes
    return s


# ---------- 7. Save ----------
def save(deck, path):
    deck.prs.save(path)
    return path
