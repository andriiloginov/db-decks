# db-decks

Генератор PPTX/PDF-презентацій бренду Defence Builder: дизайн-токени, бібліотека
layout-функцій (`db_deck.py`, python-pptx + cairosvg) і каталог hero-зображень.

Репозиторій — єдине джерело правди для скіла `db-pptx-decks`. Скіл клонує його й будує деку
викликами готових функцій, а не відтворює генератор по пам'яті щоразу заново.

## Швидкий старт

```bash
git clone https://github.com/andriiloginov/db-decks
cd db-decks
pip install -r requirements.txt --break-system-packages   # або в venv, без цього флагу

# редагуй/копіюй examples/example_build.py, тоді:
python examples/example_build.py
```

Один запуск дає `out.pptx` (в корені репозиторію, поряд з тим, звідки запущено скрипт).

## Структура

```
db-decks/
├── db_deck.py                     ← генератор (create_deck, cover, statement, points, stats,
│                                     cards, bars, matrix, closing, quote_block, quote_block_metrics, ...)
├── requirements.txt                ← python-pptx, lxml, cairosvg, Pillow
├── figma/
│   └── db_figma.js                 ← рендерер тих самих layout-ів у Figma (Plugin API, для use_figma)
├── scripts/
│   ├── figma_prelude.py            ← віддає THEMES/N/F/T/SVG з db_deck.py як JS-константи
│   └── figma_payload.py            ← збирає повний `code` для одного виклику use_figma
├── examples/
│   ├── example_build.py            ← по одному прикладу кожного layout-у (7 слайдів)
│   ├── test_quote.py               ← окремий приклад для quote_block()/quote_block_metrics()
│   └── test_matrix_and_closing.py  ← matrix() (таблиця-порівняння) + closing() з 1- та 2-рядковим
│                                     заголовком (регресійний QA-скрипт для обох правок)
├── assets/
│   └── hero-images/
│       ├── README.md               ← як додати нове зображення
│       ├── manifest.json           ← [{id, file, label, tags}]
│       └── images/                 ← самі PNG
└── docs/
    ├── tokens.md                   ← кольори, шрифти, type scale, grid, chrome-елементи
    ├── layouts.md                  ← каталог layout-функцій і правила контенту
    ├── figma.md                    ← рендер деки у Figma: воркфлоу, spec-и, шрифти, обмеження
    ├── pitfalls.md                 ← вже виправлені баги — не наступай на ті ж граблі
    └── qa.md                       ← QA-чекліст перед здачею деки
```

## Figma

Та сама дека може бути намальована нативними фреймами на сторінці Figma-файлу (скіл
`db-figma-decks`): `python3 scripts/figma_payload.py --direction ecosystem --page-id <node-id> --name "Дека" --install-kit --specs specs.json`
збирає код для `use_figma`. Токени й вектори читаються з `db_deck.py` (нічого не дублюється);
рендерер `figma/db_figma.js` — порт layout-ів. Шрифти у Figma-деках — DM Sans + DM Mono.
Деталі, формат spec-ів і відомі обмеження — `docs/figma.md`.

## Залежності

- `python-pptx` — сам .pptx контейнер, текст, форми, зображення.
- `lxml` — низькорівневий доступ до OOXML там, де в python-pptx немає API (кольоровий
  маркер списку, character tracking) — див. `docs/pitfalls.md`.
- `cairosvg` + `Pillow` — растеризація вбудованих SVG (лого, іконки, watermark) у PNG перед
  вставкою в слайд; висота розміщення завжди береться з фактичного співвідношення сторін
  растру, ніколи «на слово» з `viewBox`.

Шрифти (FK Grotesk, FK Grotesk Mono Medium, DM Mono, DM Mono Medium) **не** входять у цей
репозиторій — немає прав на редистрибуцію. Потрібні лише на машині, де відкривають готовий
`.pptx`; для генерації самого файлу шрифти не потрібні.

## Статус

Перевірено: OOXML-валідація (`validate.py`), рендер через LibreOffice + візуальний огляд усіх
7 слайдів прикладу, self-audit шрифтів/кольорів/multi-`<a:pPr>` (чисто), окремий тест
`quote_block()`/`quote_block_metrics()` (дві версії — headline і ряд менших цитат, кожна на
своєму слайді), окремий тест `matrix()` (таблиця-порівняння 3×6 з реалістичними довжинами
лейблів) і `closing()` з 1- та 2-рядковим заголовком (регресія + сам баг-кейс — обидва чисті).
Реальна деку (Batch 4 Partnership, 13 слайдів) пройшла повний QA через цей генератор і була
здана користувачу; саме на ній і знайшовся баг `closing()`, який тепер виправлено в самому
генераторі, а не лише обходом у тій деці. **Не перевірено ще в реальному PowerPoint** —
LibreOffice двічі не показував реальний overflow, який показав PowerPoint (див.
`docs/pitfalls.md`), тож перед тим як здавати деку з великою кількістю тексту/чіпів як
фінальну, попроси користувача відкрити її в справжньому PowerPoint.
