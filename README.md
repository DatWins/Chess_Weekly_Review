# TWIC Weekly Review – Middlegame Plans

Each week: seven key games from **The Week In Chess (TWIC)**, annotated around a single opening theme. For each issue you get:

- **Interactive HTML** — three-column layout with live clickable board, main-line moves in bold blue, prose notes at key moments, dark mode, keyboard navigation. Open in any browser.
- **EPUB** — same text with board-diagram PNGs, formatted for Kobo.
- **Annotated PGN** — prose comments in `{}` notation, ready to import into any GUI.

## Structure

```
index.html          ← library page (this file)
issues.json         ← metadata for all issues
issues/
  twic1667/
    twic1667_nf3b3bb2.html
    twic1667_nf3b3bb2.epub
    twic1667_nf3b3bb2.pgn
    thumb.png
```

## Issues

| # | TWIC | Theme | Date |
|---|------|-------|------|
| 1 | 1667 | Nf3/b3/Bb2 System | Oct 2026 |

## Adding a new issue

Each new TWIC issue gets its own folder under `issues/twic<N>/` with HTML, EPUB, PGN, and a `thumb.png`. Then add one JSON object to `issues.json` and re-inject it into `index.html`.
