#!/usr/bin/env python3
"""
Chess Weekly Review — EPUB builder (1668-style format)
Builds a Kobo-compatible EPUB from a PGN file + metadata.

Usage: python build_epub.py  (edit SETTINGS below)
"""

# ===========================================================================
# ★ SETTINGS — edit for each issue
# ===========================================================================

import sys

# Which issue to build — 'nf3b3bb2' or 'kan'
ISSUE = sys.argv[1] if len(sys.argv) > 1 else 'nf3b3bb2'

CONFIGS = {
    'nf3b3bb2': {
        'pgn_file':   'issues/twic1667/twic1667_nf3b3bb2.pgn',
        'out_epub':   'issues/twic1667/twic1667_nf3b3bb2.epub',
        'uid':        'twic1667-nf3b3bb2',
        'title':      'TWIC 1667 — Nf3/b3/Bb2: Seven Key Games',
        'subtitle':   'The London-English Spine',
        'hed':        'Seven games from the 41st European Club Championship, Budva, October 2026',
        'date':       '2026-10-23',
        'twic_num':   'TWIC 1667',
        # Game summaries: (heading, eco_line, var_line, narr)
        'games': [
            ('Mamedyarov – Duncan',
             'A14 · Nf3/b3/Bb2 · 1–0',
             'Isolated d5 pawn model',
             'Mamedyarov demonstrates the classic Na4-Nc5 manoeuvre, then launches a kingside '
             'attack that leaves Black\'s isolated d-pawn fatally exposed.'),
            ('Alonso Rosell – Yakubboev',
             'A06 · Double fianchetto · 1–0',
             'c-file domination',
             'An upset — the lower-rated Alonso Rosell outplays super-GM Yakubboev by '
             'dominating the c-file and converting the endgame with precise technique.'),
            ('Koneru – Osmak',
             'A07 · King\'s Indian Attack · 1–0',
             'Nf3/b3 vs King\'s Indian setup',
             'Koneru applies the Nf3/b3/Bb2 ideas against Black\'s King\'s Indian setup. '
             'A central break opens lines for the long diagonal, and the attack decides.'),
            ('Smirin – Lobzhanidze',
             'A13 · English-QGD hybrid · ½–½',
             'Strategic draw',
             'A tense strategic battle in the English hybrid. Both sides manoeuvre '
             'carefully and the game ends in a drawn endgame by repetition.'),
            ('Cheparinov – Korobov',
             'A07 · Reversed Reti · 0–1',
             'Black seizes the initiative',
             'Korobov equalises confidently and then seizes the initiative on the queenside, '
             'converting a passed pawn in the endgame.'),
            ('Van Foreest – Vachier-Lagrave',
             'A13 · 1.Nf3 d5 · ½–½',
             'Strategic battle',
             'Van Foreest essays the full Nf3/b3/Bb2 setup against MVL. The resulting '
             'positional fight is balanced throughout and ends peacefully.'),
            ('Pichot – Grandelius',
             'A07 · King\'s Indian Attack · 1–0',
             'Kingside attack',
             'Pichot uses the KIA formation with Nf3/g3/Bg2 and launches a '
             'thematic kingside attack that breaks through decisively.'),
        ],
    },
    'kan': {
        'pgn_file':   'issues/twic1667_kan/twic1667_kan.pgn',
        'out_epub':   'issues/twic1667_kan/twic1667_kan.epub',
        'uid':        'twic1667-kan',
        'title':      'TWIC 1667 — Kan Sicilian: Six Key Games',
        'subtitle':   'The Flexible Kan',
        'hed':        'Six games from the 41st European Club Championship, Budva, October 2026',
        'date':       '2026-10-23',
        'twic_num':   'TWIC 1667',
        'games': [
            ('Vachier-Lagrave – Shirov',
             'B41 · Kan: 5.Bd3 · 1–0',
             '5.Bd3 vs Kan',
             'MVL employs 5.Bd3 and builds a smooth positional squeeze, '
             'exploiting the weak d6 square to win a model game.'),
            ('Grandelius – Cheparinov',
             'B42 · Kan: 5.Bd3 e6 · 0–1',
             'Black counterpunches',
             'Cheparinov allows the typical central pawn structure and then '
             'generates sharp counterplay on the queenside to win decisively.'),
            ('Fridman – Pichot',
             'B43 · Kan: 5.Nc3 · ½–½',
             '5.Nc3 system',
             'A tense game in the main Kan with 5.Nc3. Both players manoeuvre '
             'carefully in the middlegame and reach a drawn rook endgame.'),
            ('Smeets – Lobzhanidze',
             'B41 · Kan: 5.c4 · 1–0',
             'Maróczy Bind attempt',
             'Smeets goes for the Maróczy Bind structure with 5.c4. '
             'Black struggles for counterplay and White converts a space advantage.'),
            ('Reinderman – Vachier-Lagrave',
             'B42 · Kan: 5.Bd3 Bc5 · 0–1',
             'Bishop sortie',
             'MVL plays the aggressive 5…Bc5 sortie and generates early pressure. '
             'White cannot hold the balance and Black converts cleanly.'),
            ('Van Foreest – Fridman',
             'B41 · Kan main line · 1–0',
             'Positional squeeze',
             'Van Foreest builds a positional advantage step by step, '
             'exploiting weaknesses on both wings in a clean technical win.'),
        ],
    },
}

cfg = CONFIGS[ISSUE]

# ===========================================================================
# Engine
# ===========================================================================

import re, zipfile, io
from pathlib import Path
from datetime import datetime


# ---------------------------------------------------------------------------
# Minimal PGN parser (main line only, no variations for EPUB)
# ---------------------------------------------------------------------------

def parse_pgn_games(text):
    games = []
    blocks = re.split(r'\n(?=\[Event )', text.strip())
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        lines = block.split('\n')
        headers = {}
        move_lines = []
        in_moves = False
        for line in lines:
            if line.startswith('[') and not in_moves:
                m = re.match(r'\[(\w+)\s+"(.*)"\]', line)
                if m:
                    headers[m.group(1)] = m.group(2)
            else:
                in_moves = True
                move_lines.append(line)
        moves = ' '.join(move_lines).strip()
        games.append((headers, moves))
    return games


def pgn_moves_to_epub_spans(moves_text):
    """Convert PGN move text to EPUB span markup (main line only)."""
    # Strip comments and variations
    text = moves_text
    # Remove nested variations (simple depth tracking)
    result = []
    depth = 0
    i = 0
    while i < len(text):
        c = text[i]
        if c == '(':
            depth += 1; i += 1; continue
        if c == ')':
            depth -= 1; i += 1; continue
        if c == '{':
            end = text.find('}', i)
            if end < 0:
                break
            if depth == 0:
                # Include comments as note spans
                comment = text[i+1:end].strip()
                result.append(f'<span class="note"> ({comment})</span> ')
            i = end + 1; continue
        if depth == 0:
            result.append(c)
        i += 1

    cleaned = ''.join(result).strip()

    # Tokenise move numbers and SANs
    spans = []
    tokens = re.split(r'(\d+\.+)', cleaned)
    for token in tokens:
        token = token.strip()
        if not token:
            continue
        if re.match(r'^\d+\.+$', token):
            # Move number
            spans.append(f'<span class="mn">{token}</span> ')
        else:
            # Moves: split by whitespace, classify white/black alternately
            parts = token.split()
            color = 'mw'  # first token after move number is white
            for part in parts:
                if part in ('1-0', '0-1', '1/2-1/2', '*'):
                    spans.append(f'<span class="res">{part}</span>')
                elif part:
                    spans.append(f'<span class="{color}">{part}</span> ')
                    color = 'mb' if color == 'mw' else 'mw'

    return ''.join(spans).strip()


# ---------------------------------------------------------------------------
# CSS (same style as 1668)
# ---------------------------------------------------------------------------

EPUB_CSS = """\
body { font-family: Georgia, serif; font-size: 1em; line-height: 1.6; margin: 1em 2em; color: #1d1f22; background: #fbfaf7; }
h1 { font-size: 1.8em; color: #1f4fa3; margin-bottom: 0.2em; }
h2.sub { font-size: 1.3em; color: #1f4fa3; margin-top: 0; }
p.hed { font-style: italic; color: #5d6670; margin-bottom: 2em; }
section { margin-bottom: 3em; border-top: 1px solid #e2e0da; padding-top: 1.5em; }
h2 { font-size: 1.3em; color: #1d1f22; margin-bottom: 0.3em; }
p.eco { font-size: 0.9em; color: #1f4fa3; font-weight: bold; margin: 0.2em 0; }
p.var { font-size: 0.85em; color: #5d6670; font-style: italic; margin: 0 0 0.8em 0; }
p.hdr { font-size: 0.95em; border-left: 3px solid #1f4fa3; padding-left: 0.8em; margin-bottom: 0.8em; }
span.ev { color: #5d6670; font-size: 0.9em; }
p.narr { margin-bottom: 1em; }
div.moves { font-size: 0.95em; line-height: 2; }
span.mn { color: #5d6670; font-size: 0.85em; }
span.mw { color: #1f4fa3; font-weight: bold; }
span.mb { color: #2b2f36; }
span.note { color: #5d6670; font-style: italic; font-size: 0.9em; }
span.res { font-weight: bold; color: #1d1f22; }
"""


# ---------------------------------------------------------------------------
# Build EPUB
# ---------------------------------------------------------------------------

def build_epub(cfg):
    pgn_text = Path(cfg['pgn_file']).read_text(encoding='utf-8')
    games = parse_pgn_games(pgn_text)
    game_summaries = cfg['games']

    n_games = min(len(games), len(game_summaries))

    # Build game sections
    game_sections = []
    toc_items = []

    for i in range(n_games):
        headers, moves_text = games[i]
        heading, eco_line, var_line, narr = game_summaries[i]

        gid = f'g{i+1}'
        white = headers.get('White', '?').replace(',', ',')
        black = headers.get('Black', '?').replace(',', ',')
        result = headers.get('Result', '*')
        event = headers.get('Event', '')
        rnd = headers.get('Round', '?')

        hdr_line = f'{white} – {black} · {result}'
        event_line = f'{event}, Round {rnd}' if event else f'Round {rnd}'

        moves_html = pgn_moves_to_epub_spans(moves_text)

        section = (
            f'<section id="{gid}" epub:type="chapter">\n'
            f'<h2>{heading}</h2>\n'
            f'<p class="eco">{eco_line}</p>\n'
            f'<p class="var">{var_line}</p>\n'
            f'<p class="hdr">{hdr_line}<br/>\n'
            f'<span class="ev">{event_line}</span></p>\n'
            f'<p class="narr">{narr}</p>\n'
            f'<div class="moves">{moves_html}</div>\n'
            f'</section>'
        )
        game_sections.append(section)
        toc_items.append(f'<li><a href="content.xhtml#{gid}">{heading}</a></li>')

    # content.xhtml
    content_xhtml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE html>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="en">\n'
        '<head>\n'
        '<meta charset="UTF-8"/>\n'
        f'<title>{cfg["title"]}</title>\n'
        '<link rel="stylesheet" type="text/css" href="../css/style.css"/>\n'
        '</head>\n'
        '<body>\n'
        '<header>\n'
        f'<h1>{cfg["twic_num"]}</h1>\n'
        f'<h2 class="sub">{cfg["subtitle"]}</h2>\n'
        f'<p class="hed">{cfg["hed"]}</p>\n'
        '</header>\n'
        + ''.join(game_sections) + '\n'
        '</body>\n'
        '</html>\n'
    )

    # nav/toc.xhtml
    toc_xhtml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE html>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">\n'
        '<head><meta charset="UTF-8"/><title>Contents</title></head>\n'
        '<body>\n'
        '<nav epub:type="toc" id="toc">\n'
        '<h1>Contents</h1>\n'
        '<ol>\n'
        + ''.join(toc_items) + '\n'
        '</ol>\n'
        '</nav>\n'
        '</body>\n'
        '</html>\n'
    )

    # content.opf
    content_opf = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">\n'
        '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">\n'
        f'  <dc:identifier id="uid">{cfg["uid"]}</dc:identifier>\n'
        f'  <dc:title>{cfg["title"]}</dc:title>\n'
        '  <dc:creator>Chess Weekly Review</dc:creator>\n'
        '  <dc:language>en</dc:language>\n'
        f'  <dc:date>{cfg["date"]}</dc:date>\n'
        f'  <meta property="dcterms:modified">{cfg["date"]}T00:00:00Z</meta>\n'
        '</metadata>\n'
        '<manifest>\n'
        '  <item id="nav" href="nav/toc.xhtml" media-type="application/xhtml+xml" properties="nav"/>\n'
        '  <item id="content" href="content/content.xhtml" media-type="application/xhtml+xml"/>\n'
        '  <item id="css" href="css/style.css" media-type="text/css"/>\n'
        '</manifest>\n'
        '<spine>\n'
        '  <itemref idref="nav"/>\n'
        '  <itemref idref="content"/>\n'
        '</spine>\n'
        '</package>\n'
    )

    # container.xml
    container_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">\n'
        '<rootfiles>\n'
        '  <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>\n'
        '</rootfiles>\n'
        '</container>\n'
    )

    # Write EPUB (zip)
    out_path = cfg['out_epub']
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        # mimetype must be first and uncompressed
        zf.writestr(zipfile.ZipInfo('mimetype'), 'application/epub+zip')
        zf.writestr('META-INF/container.xml', container_xml)
        zf.writestr('OEBPS/content.opf', content_opf)
        zf.writestr('OEBPS/nav/toc.xhtml', toc_xhtml)
        zf.writestr('OEBPS/content/content.xhtml', content_xhtml)
        zf.writestr('OEBPS/css/style.css', EPUB_CSS)

    Path(out_path).write_bytes(buf.getvalue())
    print(f'Written: {out_path}  ({Path(out_path).stat().st_size:,} bytes)')
    print(f'  Games included: {n_games}')

    # Quick verify
    z = zipfile.ZipFile(out_path)
    files = z.namelist()
    print(f'  Files in epub: {files}')


if __name__ == '__main__':
    print(f'Building EPUB for issue: {ISSUE}')
    build_epub(cfg)
