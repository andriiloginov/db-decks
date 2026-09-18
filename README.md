# db-decks

Джерело правди для Defence Builder pptx/pdf презентацій: токени бренду, генератор слайдів
(`db_deck.js`, pptxgenjs + sharp) і бібліотека готових hero-зображень. Скіл `db-pptx-decks`
клонує цей репозиторій і будує з нього, замість того щоб тримати весь генератор
вбудованим у текст скіла.

Той самий підхід, що й `dormotech-docs` для Dormotech: коли репо і скіл розходяться,
**репо перемагає** — воно те, що реально білдить.

## Швидкий старт

```bash
git clone https://github.com/andriiloginov/db-decks
cd db-decks
npm install

# редагуй/копіюй examples/example-build.js, тоді:
node examples/example-build.js
```

Один запуск дає `out.pptx`. `sharp` і `pptxgenjs` — залежності з `package.json`.

## Структура

```
db-decks/
├── db_deck.js                     ← генератор (createDeck, cover, statement, points, stats, cards, bars, closing, quoteBlock, ...)
├── package.json
├── examples/
│   └── example-build.js           ← по одному прикладу кожного layout-у
├── assets/
│   └── hero-images/
│       ├── README.md               ← як додати нове зображення
│       ├── manifest.json           ← [{id, file, label, tags}]
│       └── images/                 ← самі PNG
└── docs/
    ├── tokens.md                   ← кольори, шрифти, type scale, grid, chrome-елементи
    ├── layouts.md                  ← каталог layout-функцій і правила контенту
    ├── pitfalls.md                 ← вже виправлені баги — не наступай на ті ж граблі
    └── qa.md                       ← QA-чекліст перед здачею деки
