#!/usr/bin/env python3
"""Build twic1668_rossolimo.html — corrected engine (clean SAN at NODES[4])"""

PGN_FILE = 'issues/twic1668_rossolimo/twic1668_rossolimo.pgn'
OUT_HTML  = 'issues/twic1668_rossolimo/twic1668_rossolimo.html'
TEMPLATE  = '/tmp/twic1668_rossolimo_backup.html'

PAGE_TITLE     = 'TWIC 1668 – 3.Bb5 — The Rossolimo Rules Budva'
ARTICLE_H1     = '3.Bb5 — The Rossolimo Rules Budva'
ARTICLE_DEK    = 'Seven sharp battles in the Rossolimo Sicilian from the 41st European Club Championship.'
ARTICLE_KICKER = 'TWIC 1668 · 41st ECC Open · Budva, October 2026'
ARTICLE_BYLINE = 'Chess Weekly Review <span>· Oct 2026</span>'

ARTICLE_INTRO = '''\
<p class="first">The Nimzovich-Rossolimo (1.e4 c5 2.Nf3 Nc6 3.Bb5) was a star opening at the 41st
European Club Championship in Budva. White scored convincingly with it in several rounds, and even when
Black defended correctly the resulting positions proved rich and unbalanced. Wei Yi and Tabatabaei
showed that Black can fight back — but it requires precise preparation.</p>
<p>Click any move to replay it on the live board.</p>
'''

GAME_SUMMARIES = [
    (
        'Volokitin – Tabatabaei',
        'B31 · Rossolimo, 3...g6 4.Bxc6',
        'White exchanges on c6 early and builds a space advantage, but Tabatabaei (2728) finds active '
        'counterplay with rook lifts and seizes the initiative.',
    ),
    (
        'Aizenberg – Wei Yi',
        'B30 · Rossolimo, 3...e6',
        'Wei Yi (2758) handles the Rossolimo from the Black side with trademark ease. He builds up '
        'pressure on the queenside and converts the endgame without difficulty.',
    ),
    (
        'Harikrishna – Romanov',
        'B30 · Rossolimo, 3...e6',
        'Harikrishna (2648) is in his element in the Rossolimo. He keeps the position closed and '
        'outmanoeuvres Romanov in a smooth positional win.',
    ),
    (
        'Harikrishna – Sokolovsky',
        'B51 · Moscow Variation, 3...Bd7',
        'A second Harikrishna Rossolimo — this time the Moscow Variation (3.Bb5+ Bd7). White wins '
        'convincingly after Black mishandles the middlegame.',
    ),
    (
        'Sahidi – Pranesh',
        'B30 · Rossolimo, 3...e6',
        'Pranesh (2674) is one of India\'s rising stars, but Sahidi (2482) outplays him in a '
        'complex middlegame and converts the full point.',
    ),
    (
        'Boyer – Volokitin',
        'B51 · Moscow Variation, 3...Bd7',
        'Volokitin is on the other side of the Rossolimo this time — and Boyer exploits his '
        'queenside initiative to win material and the game.',
    ),
    (
        'Dudognon – Rapport',
        'B30 · Rossolimo, 3...e6',
        'The rating underdog Dudognon (2323) tries his luck with the Rossolimo against Rapport (2711), '
        'but the Hungarian star turns the tables and wins a sharp tactical battle.',
    ),
]

# ===========================================================================
# Engine — identical to build_issue.py (copied verbatim so this file is self-contained)
# ===========================================================================

import re, json
from pathlib import Path

def parse_pgn_games(text):
    games = []
    blocks = re.split(r'\n(?=\[Event )', text.strip())
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        header_part = ''
        moves_part = ''
        in_moves = False
        lines = block.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                if header_part:
                    in_moves = True
                continue
            if line.startswith('[') and not in_moves:
                header_part += line + '\n'
            else:
                in_moves = True
                moves_part += line + ' '
        tags = {}
        for m in re.finditer(r'\[(\w+)\s+"([^"]*)"\]', header_part):
            tags[m.group(1)] = m.group(2)
        if tags and moves_part.strip():
            games.append({'tags': tags, 'moves': moves_part.strip()})
    return games

def tokenize_moves(moves_text):
    moves_text = re.sub(r'\{[^}]*\}', '', moves_text)
    moves_text = re.sub(r'\$\d+', '', moves_text)
    tokens = re.split(r'\s+', moves_text.strip())
    return [t for t in tokens if t]

class ChessGame:
    INIT_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
    FILES = 'abcdefgh'
    RANKS = '12345678'
    PIECE_LETTERS = {'P','N','B','R','Q','K'}

    def __init__(self):
        self.reset()

    def reset(self):
        self.board = {}
        self.turn = 'w'
        self.castling = {'K': True, 'Q': True, 'k': True, 'q': True}
        self.ep_sq = None
        self.halfmove = 0
        self.fullmove = 1
        fen = self.INIT_FEN
        self._load_fen(fen)

    def _load_fen(self, fen):
        parts = fen.split()
        pos, turn, cast, ep = parts[0], parts[1], parts[2], parts[3]
        self.turn = turn
        self.castling = {'K': 'K' in cast, 'Q': 'Q' in cast, 'k': 'k' in cast, 'q': 'q' in cast}
        self.ep_sq = ep if ep != '-' else None
        self.halfmove = int(parts[4]) if len(parts) > 4 else 0
        self.fullmove = int(parts[5]) if len(parts) > 5 else 1
        self.board = {}
        rank = 7
        file = 0
        for ch in pos:
            if ch == '/':
                rank -= 1
                file = 0
            elif ch.isdigit():
                file += int(ch)
            else:
                sq = self.FILES[file] + self.RANKS[rank]
                self.board[sq] = ch
                file += 1

    def fen(self):
        rows = []
        for rank in range(7, -1, -1):
            row = ''
            empty = 0
            for file in range(8):
                sq = self.FILES[file] + self.RANKS[rank]
                p = self.board.get(sq)
                if p:
                    if empty: row += str(empty); empty = 0
                    row += p
                else:
                    empty += 1
            if empty: row += str(empty)
            rows.append(row)
        cast = ''
        for k,v in [('K','K'),('Q','Q'),('k','k'),('q','q')]:
            if self.castling[k]: cast += v
        if not cast: cast = '-'
        ep = self.ep_sq or '-'
        return f"{'/'.join(rows)} {self.turn} {cast} {ep} {self.halfmove} {self.fullmove}"

    def _sq(self, f, r):
        return self.FILES[f] + self.RANKS[r]
    def _fi(self, sq): return self.FILES.index(sq[0])
    def _ri(self, sq): return self.RANKS.index(sq[1])

    def _attacks_sq(self, sq, color):
        fi, ri = self._fi(sq), self._ri(sq)
        for f in range(8):
            for r in range(8):
                s = self._sq(f, r)
                p = self.board.get(s)
                if not p: continue
                if (color == 'w' and p.islower()) or (color == 'b' and p.isupper()): continue
                if (color == 'w' and p.islower()) or (color == 'b' and p.isupper()): continue
                pc = p.upper()
                df, dr = fi - f, ri - r
                if pc == 'P':
                    if color == 'w':
                        if dr == 1 and abs(df) == 1: return True
                    else:
                        if dr == -1 and abs(df) == 1: return True
                elif pc == 'N':
                    if (abs(df), abs(dr)) in {(1,2),(2,1)}: return True
                elif pc == 'K':
                    if abs(df) <= 1 and abs(dr) <= 1: return True
                elif pc in ('B','Q'):
                    if abs(df) == abs(dr) and df != 0:
                        step_f = 1 if fi > f else -1
                        step_r = 1 if ri > r else -1
                        blocked = False
                        cf, cr = f + step_f, r + step_r
                        while (cf, cr) != (fi, ri):
                            if self.board.get(self._sq(cf, cr)): blocked = True; break
                            cf += step_f; cr += step_r
                        if not blocked: return True
                elif pc in ('R','Q'):
                    if pc == 'Q' and abs(df) == abs(dr) and df != 0: continue
                    if df == 0 or dr == 0:
                        step_f = (0 if df == 0 else (1 if fi > f else -1))
                        step_r = (0 if dr == 0 else (1 if ri > r else -1))
                        blocked = False
                        cf, cr = f + step_f, r + step_r
                        while (cf, cr) != (fi, ri):
                            if self.board.get(self._sq(cf, cr)): blocked = True; break
                            cf += step_f; cr += step_r
                        if not blocked: return True
        return False

    def _find_king(self, color):
        king = 'K' if color == 'w' else 'k'
        for sq, p in self.board.items():
            if p == king: return sq
        return None

    def _in_check(self, color):
        king_sq = self._find_king(color)
        if not king_sq: return False
        opp = 'b' if color == 'w' else 'w'
        return self._attacks_sq(king_sq, opp)

    def _piece_color(self, p):
        if not p: return None
        return 'w' if p.isupper() else 'b'

    def _make_move_on_board(self, fr, to, promo=None):
        p = self.board.pop(fr, None)
        if not p: return None, None
        captured = self.board.pop(to, None)
        ep_capture = None
        if p.upper() == 'P' and to == self.ep_sq:
            ep_rank = '5' if self.turn == 'w' else '4'
            ep_capture_sq = to[0] + ep_rank
            ep_capture = self.board.pop(ep_capture_sq, None)
        if promo:
            p = promo.upper() if self.turn == 'w' else promo.lower()
        self.board[to] = p
        rook_move = None
        if p.upper() == 'K':
            fi_fr, fi_to = self._fi(fr), self._fi(to)
            if abs(fi_fr - fi_to) == 2:
                rank = fr[1]
                if fi_to > fi_fr:
                    rook_move = ('h' + rank, 'f' + rank)
                else:
                    rook_move = ('a' + rank, 'd' + rank)
                rook = self.board.pop(rook_move[0], None)
                if rook: self.board[rook_move[1]] = rook
        return captured, ep_capture

    def push_san(self, san):
        san_clean = san.rstrip('+#')
        promo = None
        if '=' in san_clean:
            san_clean, promo = san_clean.split('=')
            promo = promo[0].lower()
        
        if san_clean in ('O-O', '0-0'):
            rank = '1' if self.turn == 'w' else '8'
            fr, to = 'e' + rank, 'g' + rank
        elif san_clean in ('O-O-O', '0-0-0'):
            rank = '1' if self.turn == 'w' else '8'
            fr, to = 'e' + rank, 'c' + rank
        else:
            piece = 'P'
            rest = san_clean
            if rest[0] in self.PIECE_LETTERS:
                piece = rest[0]; rest = rest[1:]
            if 'x' in rest: rest = rest.replace('x', '')
            to = rest[-2:]
            disamb = rest[:-2]
            
            candidates = []
            for sq, p in self.board.items():
                if self._piece_color(p) != self.turn: continue
                if p.upper() != piece: continue
                if disamb:
                    if len(disamb) == 2:
                        if sq != disamb: continue
                    elif disamb[0] in self.FILES:
                        if sq[0] != disamb[0]: continue
                    elif disamb[0] in self.RANKS:
                        if sq[1] != disamb[0]: continue
                if self._can_move(sq, to, piece, promo):
                    candidates.append(sq)
            
            if not candidates:
                raise ValueError(f"No candidate for {san} (turn={self.turn})")
            fr = candidates[0]

        saved_board = dict(self.board)
        saved_ep = self.ep_sq
        saved_cast = dict(self.castling)
        
        cap, ep_cap = self._make_move_on_board(fr, to, promo)
        
        in_check_after = self._in_check(self.turn)
        if in_check_after:
            self.board = saved_board
            self.ep_sq = saved_ep
            self.castling = saved_cast
            raise ValueError(f"Move {san} leaves king in check")

        new_ep = None
        p_moved = self.board.get(to, '')
        if p_moved.upper() == 'P':
            fi_fr, ri_fr = self._fi(fr), self._ri(fr)
            ri_to = self._ri(to)
            if abs(ri_fr - ri_to) == 2:
                ep_rank_idx = (ri_fr + ri_to) // 2
                new_ep = self._sq(fi_fr, ep_rank_idx)
        self.ep_sq = new_ep

        if p_moved == 'K':
            self.castling['K'] = False; self.castling['Q'] = False
        elif p_moved == 'k':
            self.castling['k'] = False; self.castling['q'] = False
        elif p_moved == 'R' or fr == 'h1': 
            if fr == 'h1': self.castling['K'] = False
        elif fr == 'a1': self.castling['Q'] = False
        elif fr == 'h8': self.castling['k'] = False
        elif fr == 'a8': self.castling['q'] = False

        self.halfmove = 0 if (cap or ep_cap or p_moved.upper() == 'P') else self.halfmove + 1
        if self.turn == 'b': self.fullmove += 1
        self.turn = 'b' if self.turn == 'w' else 'w'

        return fr, to

    def _can_move(self, fr, to, piece, promo=None):
        fi_fr, ri_fr = self._fi(fr), self._ri(fr)
        fi_to, ri_to = self._fi(to), self._ri(to)
        df, dr = fi_to - fi_fr, ri_to - ri_fr
        target = self.board.get(to)
        if target and self._piece_color(target) == self.turn:
            return False

        if piece == 'P':
            dir_ = 1 if self.turn == 'w' else -1
            start_rank = 1 if self.turn == 'w' else 6
            if df == 0:
                if dr == dir_ and not target: return True
                if dr == 2 * dir_ and ri_fr == start_rank and not target:
                    mid = self._sq(fi_fr, ri_fr + dir_)
                    if not self.board.get(mid): return True
            elif abs(df) == 1 and dr == dir_:
                if target: return True
                if to == self.ep_sq: return True
            return False
        elif piece == 'N':
            return (abs(df), abs(dr)) in {(1,2),(2,1)}
        elif piece == 'B':
            if abs(df) != abs(dr) or df == 0: return False
            sf, sr = (1 if df>0 else -1), (1 if dr>0 else -1)
            f, r = fi_fr + sf, ri_fr + sr
            while (f, r) != (fi_to, ri_to):
                if self.board.get(self._sq(f, r)): return False
                f += sf; r += sr
            return True
        elif piece == 'R':
            if df != 0 and dr != 0: return False
            sf = (0 if df==0 else (1 if df>0 else -1))
            sr = (0 if dr==0 else (1 if dr>0 else -1))
            f, r = fi_fr + sf, ri_fr + sr
            while (f, r) != (fi_to, ri_to):
                if self.board.get(self._sq(f, r)): return False
                f += sf; r += sr
            return True
        elif piece == 'Q':
            if abs(df) == abs(df) and df != 0 and abs(df) == abs(dr):
                return self._can_move(fr, to, 'B', promo)
            return self._can_move(fr, to, 'R', promo) or self._can_move(fr, to, 'B', promo)
        elif piece == 'K':
            if abs(df) <= 1 and abs(dr) <= 1 and (df != 0 or dr != 0): return True
            if abs(df) == 2 and dr == 0:
                opp = 'b' if self.turn == 'w' else 'w'
                rank = fr[1]
                if df > 0:
                    if not self.castling['K' if self.turn=='w' else 'k']: return False
                    for sq in ['f'+rank, 'g'+rank]:
                        if self.board.get(sq): return False
                        if self._attacks_sq(sq, opp): return False
                else:
                    if not self.castling['Q' if self.turn=='w' else 'q']: return False
                    for sq in ['d'+rank, 'c'+rank]:
                        if self.board.get(sq): return False
                        if self._attacks_sq(sq, opp): return False
                    if self.board.get('b'+rank): return False
                if self._attacks_sq(fr, opp): return False
                return True
            return False
        return False


def san_display(san):
    piece_map = {'K':'♔','Q':'♕','R':'♖','B':'♗','N':'♘'}
    result = san
    for letter, symbol in piece_map.items():
        result = result.replace(letter, symbol)
    return result


def build_node_tree(games):
    nodes = {}
    game_roots = []

    for gi, game in enumerate(games):
        tokens = tokenize_moves(game['moves'])
        chess = ChessGame()
        prefix = f'g{gi}'

        root_id = f'{prefix}_0'
        root_fen = chess.fen()
        nodes[root_id] = [root_fen, None, [], '', '', '', '', True]
        game_roots.append(root_id)

        parent_id = root_id
        node_counter = 1
        variation_stack = []
        i = 0

        while i < len(tokens):
            tok = tokens[i]
            if tok in ('1-0', '0-1', '1/2-1/2', '*'):
                i += 1
                continue
            if re.match(r'^\d+\.+$', tok):
                i += 1
                continue
            if tok == '(':
                variation_stack.append((parent_id, dict(chess.board), chess.turn,
                                       dict(chess.castling), chess.ep_sq,
                                       chess.halfmove, chess.fullmove))
                parent_id = nodes[parent_id][1] if nodes[parent_id][1] else parent_id
                i += 1
                continue
            if tok == ')':
                if variation_stack:
                    parent_id, board, turn, cast, ep, hm, fm = variation_stack.pop()
                    chess.board = board
                    chess.turn = turn
                    chess.castling = cast
                    chess.ep_sq = ep
                    chess.halfmove = hm
                    chess.fullmove = fm
                i += 1
                continue

            san = tok.rstrip('!?')
            san = re.sub(r'[+#]', '', san).rstrip('!?')
            full_san = tok

            try:
                fr, to = chess.push_san(san)
            except Exception as e:
                i += 1
                continue

            node_id = f'{prefix}_{node_counter}'
            node_counter += 1
            new_fen = chess.fen()

            is_main = len(nodes[parent_id][2]) == 0
            nodes[node_id] = [new_fen, parent_id, [], full_san, san_display(full_san), fr, to, is_main]
            nodes[parent_id][2].append(node_id)
            parent_id = node_id
            i += 1

    return nodes, game_roots


def extract_template_parts(html):
    style_m = re.search(r'<style>(.*?)</style>', html, re.DOTALL)
    style = style_m.group(1) if style_m else ''

    scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)

    script_before = ''
    script_after = ''
    chess_js_found = False
    for s in scripts:
        if 'function ChessGame' in s or 'Chess.js' in s or 'var Chess' in s or 'this.load' in s:
            chess_js_found = True
        if 'const NODES' in s:
            continue
        if 'addEventListener' in s or 'goNode' in s or 'renderBoard' in s or 'bStart' in s:
            script_after = s
        elif chess_js_found or 'function' in s:
            if not script_before:
                script_before = s

    if not script_after:
        for s in scripts:
            if 'NODES' not in s and len(s) > 500:
                script_after = s
                break

    return style, script_before, script_after


def build_html(pgn_file, out_html, template_file, settings):
    pgn_text = Path(pgn_file).read_text(encoding='utf-8', errors='replace')
    games = parse_pgn_games(pgn_text)
    print(f"Parsed {len(games)} games from {pgn_file}")

    nodes, game_roots = build_node_tree(games)
    print(f"Built {len(nodes)} nodes, {len(game_roots)} game roots")

    template_html = Path(template_file).read_text(encoding='utf-8', errors='replace')
    style, script_before, script_after = extract_template_parts(template_html)

    nodes_json = json.dumps(nodes, ensure_ascii=False)
    roots_json = json.dumps(game_roots, ensure_ascii=False)

    game_sections = []
    for gi, (root_id, summary) in enumerate(zip(game_roots, settings['GAME_SUMMARIES'])):
        heading, eco_line, narrative = summary
        root_node = nodes[root_id]

        ml_moves = []
        nid = root_id
        while True:
            node = nodes[nid]
            if node[2]:
                main_child = None
                for cid in node[2]:
                    if nodes[cid][7]:
                        main_child = cid
                        break
                if main_child is None:
                    main_child = node[2][0]
                child_node = nodes[main_child]
                san_d = child_node[4] or child_node[3]
                ply = int(main_child.split('_')[1])
                move_num = ''
                if (ply % 2) == 1:
                    num = (ply + 1) // 2
                    move_num = f'{num}.'
                ml_moves.append(f'<a class="mv" data-id="{main_child}">{move_num}{san_d}</a>')
                nid = main_child
            else:
                break

        ml_html = ' '.join(ml_moves)

        tags = games[gi]['tags'] if gi < len(games) else {}
        white = tags.get('White', '')
        black = tags.get('Black', '')
        white_elo = tags.get('WhiteElo', '')
        black_elo = tags.get('BlackElo', '')
        event = tags.get('Event', '')
        date_tag = tags.get('Date', '')
        round_tag = tags.get('Round', '')
        result = tags.get('Result', '')

        white_str = f'<b>{white}</b>' + (f' ({white_elo})' if white_elo and white_elo != '?' else '')
        black_str = f'<b>{black}</b>' + (f' ({black_elo})' if black_elo and black_elo != '?' else '')
        event_str = event + (f', rd {round_tag}' if round_tag and round_tag != '?' else '') + (f' &nbsp; {result}' if result else '')
        date_str = date_tag.replace('.??', '').replace('?', '') if date_tag else ''

        gamehead = f'<div><b>{heading}</b></div>\n<div>{event_str}</div>\n<div>{eco_line}</div>'
        if date_str and date_str not in event_str:
            gamehead += f'\n<div>{date_str}</div>'

        section = f'''<h2>{heading}</h2>
<div class="gamehead">{gamehead}</div>
<p class="ml">{ml_html}</p>
<p>{narrative}</p>
<p class="tree-link"><a href="tree.html">📊 View opening tree →</a></p>'''
        game_sections.append(section)

    article_body = ''
    for sec in game_sections:
        article_body += f'\n{sec}\n'

    page_title = settings['PAGE_TITLE']
    h1 = settings['ARTICLE_H1']
    dek = settings['ARTICLE_DEK']
    kicker = settings['ARTICLE_KICKER']
    byline = settings['ARTICLE_BYLINE']
    intro = settings['ARTICLE_INTRO']

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{page_title}</title>
<style>{style}</style>
</head>
<body>
<nav class="sitenav"><a href="../../index.html">← Chess Weekly Review</a></nav>
<main id="main">
<article>
<header class="art-head" id="top">
<div class="kicker">{kicker}</div>
<h1>{h1}</h1>
<p class="dek">{dek}</p>
<p class="byline">{byline}</p>
<p class="tree-link"><a href="tree.html">📊 View opening tree →</a> &nbsp;·&nbsp; <a href="{Path(out_html).stem}.pgn" download>⬇ Download PGN</a></p>
</header>
<section id="intro">
{intro}
</section>
{article_body}
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
<script>
const NODES = {nodes_json};
const GAME_ROOTS = {roots_json};
{script_after}
</script>
</body>
</html>'''

    Path(out_html).parent.mkdir(parents=True, exist_ok=True)
    Path(out_html).write_text(html, encoding='utf-8')
    print(f"Written {out_html} ({len(html)//1024} KB)")

    main_pos = html.find('</main>')
    aside_pos = html.find('<aside')
    assert main_pos > 0 and aside_pos > main_pos, f"Structure error: </main> at {main_pos}, <aside at {aside_pos}"
    assert 'onclick="goNode' not in html, "Found forbidden onclick"
    print(f"Structure check OK (</main> at {main_pos}, <aside at {aside_pos})")
    return html


SETTINGS = {
    'PAGE_TITLE': PAGE_TITLE,
    'ARTICLE_H1': ARTICLE_H1,
    'ARTICLE_DEK': ARTICLE_DEK,
    'ARTICLE_KICKER': ARTICLE_KICKER,
    'ARTICLE_BYLINE': ARTICLE_BYLINE,
    'ARTICLE_INTRO': ARTICLE_INTRO,
    'GAME_SUMMARIES': GAME_SUMMARIES,
}

import os
os.chdir('/home/claude/chess_weekly_review')
build_html(PGN_FILE, OUT_HTML, TEMPLATE, SETTINGS)
