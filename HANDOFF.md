# Chess Weekly Review — Handoff Notes

**GitHub repo:** https://github.com/DatWins/Chess_Weekly_Review  
**Live site:** https://datwins.github.io/Chess_Weekly_Review/  
**Purpose:** A library of weekly game reviews drawn from TWIC (The Week In Chess), each annotated around a single opening theme, with an HTML live-board page for the monitor and an EPUB for the Kobo.

---

## Site structure

```
Chess_Weekly_Review/
├── index.html          ← Library front page (the only page on this site)
├── issues.json         ← Issue metadata (not used by index.html; kept as reference)
├── README.md
└── issues/
    └── <slug>/         ← One folder per TWIC issue
        ├── thumb.png               ← Board thumbnail shown on the library card
        ├── twic<N>_<key>.html      ← Interactive game viewer (live board)
        ├── twic<N>_<key>.epub      ← Kobo download
        └── twic<N>_<key>.pgn       ← Source PGN
```

**Issue slug conventions:**
- `twic1667` — the main Nf3/b3/Bb2 set
- `twic1667_kan` — a second issue from the same TWIC number (Kan Sicilian)

**File key (`<key>`) matches the PGN theme abbreviation**, e.g. `nf3b3bb2`, `kan`.

---

## index.html — how it works

All issues are stored inline in a JavaScript array `ISSUES` near the bottom of the file (around line 74). Each entry is a plain object:

```js
{
  num: 1,                    // display order
  twic: 1667,                // TWIC issue number
  slug: "twic1667",          // folder name under issues/
  title: "Nf3/b3/Bb2: Seven Key Games",
  dek: "How the world's best...",   // subtitle shown on the card
  theme: "Nf3/b3/Bb2 System",
  date: "2026-10-23",        // ISO date — displayed as "October 2026"
  games: 7,
  players: "Mamedyarov, ...",
  filekey: "nf3b3bb2",       // used to build file names (may differ from slug suffix)
  tags: ["Fighting", "Upset"] // optional — "Fighting", "Upset", "Miniature"
}
```

**To add a new issue:** add one object to `ISSUES`. The page renders automatically.  
**No build step** — just edit the array and push.

### Tag colours
- `Fighting` — brown/amber
- `Upset` — dark red/pink
- `Miniature` — dark green

### Font size / dark mode
Stored in `localStorage` (`fs` key for font size, `dk` for dark mode). They persist across page loads but are **per browser origin** — they don't carry over to `positional_analysis`.

---

## Game HTML pages (issues/<slug>/*.html)

Each game viewer is a self-contained file with:
- Inline SVG chessboard (no external JS library)
- Full PGN parsed in JavaScript
- Clickable move list in a sidebar
- Light/dark mode toggle
- Nav bar linking back to `index.html` (the library)
- Font size controls

**Nav bar link:** `<a class="lib" href="../../index.html">` — always two levels up from `issues/<slug>/`.

---

## Adding a new TWIC issue — checklist

1. Create folder `issues/<slug>/` (e.g. `issues/twic1668_queens/`).
2. Put in: `thumb.png`, `twic<N>_<key>.html`, `twic<N>_<key>.epub`, `twic<N>_<key>.pgn`.
3. In `index.html`, add one entry to `ISSUES` with the matching `slug` and `filekey`.
4. Commit and push to `main`. GitHub Pages updates in ~1 minute.

---

## Relationship with positional_analysis

The **Strategic Training Library** (five-phase positional exercises) now lives at a separate site:  
https://datwins.github.io/positional_analysis/  
Repo: https://github.com/DatWins/positional_analysis

There is **no link** from Chess_Weekly_Review to positional_analysis (by design — the weekly review is its own standalone page).

---

## Git / deployment

- Branch: `main`
- GitHub Pages source: root of `main` branch
- No build system — push HTML/JSON directly
- Shallow clone is fine for new work: `git clone --depth 1 https://github.com/DatWins/Chess_Weekly_Review`

---

## Opening tree viewer (tree.html)

Each issue can have a zoomable opening-tree PNG viewer at `issues/<slug>/tree.html`. Every game HTML file already has a "📊 View opening tree →" link pointing to it; the link is a 404 until you generate the file.

### Generating tree.html (run locally on Windows)

**One-time setup:**
```
pip install python-chess cairosvg graphviz Pillow
```
Also install the **Graphviz binary** from https://graphviz.org/download/ and make sure it's on your PATH.

**Per issue:**
```
python tools/build_tree.py issues/twic1668_taimanov/twic1668_taimanov.pgn
```
Writes `tree.html` next to the PGN. Then commit and push — that's it.

**Options (if tree looks too crowded or too sparse):**
```
--max-plies 10     # shallower tree (default 12)
--min-games 2      # require more games per branch (auto if omitted)
--cap 60           # max board positions when auto min-games (default 80)
--title "..."      # custom page title (auto-derived from filename if omitted)
```

**What it looks like:** board diagram at each position, edge labels with the move + game count + score percentage, edge thickness proportional to game count. Pan/zoom viewer, same style as datwins.github.io/what_ya_playing.

### Adding tree-link to new issue HTML

When writing a new issue HTML by hand or with a builder, add this after the byline line:
```html
<p class="tree-link"><a href="tree.html">📊 View opening tree →</a></p>
```
And this CSS (already present in all existing issues):
```css
p.tree-link{margin:.5em 0 .9em;font-family:system-ui,"Segoe UI",sans-serif;font-size:.85em}
p.tree-link a{color:var(--main);font-weight:600;text-decoration:none;border-bottom:1px solid currentColor}
p.tree-link a:hover{opacity:.75}
```
`build_taimanov.py` already includes both; copy this pattern for any future Python builder.

---

## ⚠️ Critical: HTML structure for the board to work

The JS board renderer depends on the **aside being a direct sibling of `</main>`**. This is the layout that works:

```html
<main id="main">
  <article>
    … article content, game sections, move links …
  </article>
</main>
<aside class="bp">
  <div class="bhead"><span id="who"></span><b id="cur"></b></div>
  <div id="live"></div>
  <div class="ctrls">
    <button id="bStart">⏮</button>
    <button id="bPrev">◀</button>
    <button id="bNext">▶</button>
    <button id="bEnd">⏭</button>
    <button id="bFlip">⇅</button>
  </div>
  <div class="choose" id="choose"></div>
  <div class="msg" id="msg"></div>
  <div class="path" id="path"></div>
</aside>
```

**If you use a Python builder to generate the HTML:** make sure the builder emits `<main id="main">` as the article wrapper (not `<div class="wrap">`), and places `</main>` before `<aside class="bp">`. Do NOT copy the wrapper tag from the template's existing article — extract the template shell (navbar, CSS, JS) but write the wrapper yourself.

**If the board is blank:** check that `</main>` appears *before* `<aside` in the file. Run:
```python
t = open('issue.html').read()
print(t.find('</main>'), t.find('<aside'))  # first number must be smaller
```

## ⚠️ NODES injection order

The `const NODES = {...}` object must be declared **before** the chess.js renderer code in the `<script>` block. If you're building a new HTML file from a template, put NODES first, then append the template's script content (after stripping the template's own NODES with a regex).

## Move links — no onclick allowed

Move links **must** use `<a class="mv" data-id="NODE_ID">SAN</a>`. Never add `onclick="goNode(...)"` — the renderer attaches its own listener by class. Using onclick will cause double-firing and break navigation.

## Checking an issue before pushing

```python
html = open('issue.html').read()
assert html.count('onclick="goNode') == 0       # no onclick on moves
assert 'id="bStart"' in html                     # controls present
assert 'id="live"' in html                       # board div present
assert 'const NODES' in html                     # nodes data present
aside = html.find('<aside'); main_e = html.find('</main>')
assert main_e > 0 and aside > main_e             # aside after </main>
```
