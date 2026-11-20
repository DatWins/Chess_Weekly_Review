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
