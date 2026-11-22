#!/usr/bin/env python3
"""Build twic1667_nf3b3bb2.html"""

PGN_FILE = 'issues/twic1667/twic1667_nf3b3bb2.pgn'
OUT_HTML  = 'issues/twic1667/twic1667_nf3b3bb2.html'
TEMPLATE  = '/tmp/twic1668_taimanov_backup.html'

PAGE_TITLE     = 'TWIC 1667 – Nf3/b3/Bb2 System'
ARTICLE_H1     = 'Seven Key Games: Middlegame Plans'
ARTICLE_DEK    = 'From isolation pawn structures to kingside storms – how the world\'s best players handle the Nf3/b3/Bb2 setup.'
ARTICLE_KICKER = 'TWIC 1667 · White\'s Nf3/b3/Bb2 System'
ARTICLE_BYLINE = 'Chess Weekly Review <span>· Oct 2026</span>'

ARTICLE_INTRO = '''\
<p class="first">Each week The Week In Chess packages the world's tournament output into a single collection. This selection examines seven games from TWIC 1667 in which White employed the Nf3/b3/Bb2 system – a flexible, semi-hypermodern approach that can lead to quiet positional grind or sharp kingside attack depending on how White steers the game.</p>
<p>White's three-move signature – the knight to f3, pawn to b3, bishop to b2 – creates a battery on the long diagonal that is one of chess's most enduring strategic weapons. The games here illustrate the six main middlegame themes that arise once the setup is complete:</p>
<ul>
<li><b>The isolated d5 pawn:</b> After cxd5 exd5 or …cxd5, Black is left with a lone pawn White targets with the knight-and-queen blockade.</li>
<li><b>The Nc3-Na4-Nc5 tour:</b> The knight manoeuvre that instals a blockader on c5 and trades off Black's dark-squared bishop.</li>
<li><b>The Qa1 battery:</b> Queen retreating to a1 forms the long-diagonal battery and supports a c-file invasion.</li>
<li><b>The c-file highway:</b> Rooks doubled on the c-file, often invading c7, are a recurring motif.</li>
<li><b>Kingside storm (g4-g5, f4-f5, Rf3-h3):</b> Two distinct attacking patterns – the g4 advance and the Zukertort Rf3-h3 swing – both exploiting the Bb2\'s diagonal.</li>
<li><b>The a4-a5 clamp:</b> Queenside expansion that fixes Black\'s pawns before White pushes d4-d5 to open the diagonal.</li>
</ul>
<p>Use the arrows or keyboard (← / →) to step through moves. Click any move to jump to that position. The ← key goes back; → goes forward.</p>
'''

GAME_SUMMARIES = [
    (
        'Mamedyarov – Duncan',
        'Nf3/b3/Bb2: Isolated d5 pawn model',
        'White employs the Nc3-Na4-Nc5 tour to install a knight on c5 and trade off Black\'s dark-squared bishop. '
        'Black is left with an isolated d5 pawn that becomes a long-term weakness.',
    ),
    (
        'Alonso Rosell – Yakubboev',
        'Nf3/b3/Bb2: Double fianchetto, c-file domination',
        'White doubles rooks on the c-file and invades with Rc7, cutting Black\'s position in two. '
        'The Qa1 battery on the long diagonal proves decisive.',
    ),
    (
        'Lobanov – Lisenkov',
        'Nf3/b3/Bb2: Qa1 battery and c-file invasion',
        'White retreats the queen to a1 to form the classic battery and then uses the open c-file to '
        'penetrate into Black\'s position.',
    ),
    (
        'Kistrup – Szpar',
        'Nf3/b3/Bb2: Black\'s c6/d5 wall, the ...Ne5 antidote',
        'Black sets up the c6/d5 pawn wall and uses the ...Ne5 manoeuvre to neutralise White\'s long diagonal. '
        'A model defence that earns the full point.',
    ),
    (
        'Sjugirov – Suleimen',
        'Nf3/b3/Bb2: Aggressive g4-g5 storm and queenside castling',
        'White castles queenside and launches a g4-g5 kingside storm. '
        'The attack is devastating once the h-file opens.',
    ),
    (
        'Buckels – Genov',
        'Zukertort: Ne5, f4, Rf3-h3, g4 kingside attack',
        'White uses the Zukertort plan: knight to e5, f4, then swings the rook via f3 to h3. '
        'Combined with g4, the attack crashes through on the kingside.',
    ),
    (
        'Kuzubov – Delchev',
        'Nf3/b3/Bb2: a4-a5 queenside clamp, d5 break opens diagonal',
        'White clamps the queenside with a4-a5 fixing Black\'s pawns, then plays d4-d5 to open the long diagonal. '
        'The resulting attack is unstoppable.',
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
            if not script_before:
                script_before = s
            continue
        if 'const NODES' in s:
            # Strip the NODES/GAME_ROOTS data, keep the renderer code that follows
            # The renderer starts after the last const GAME_ROOTS = ...; line
            m = re.search(r'const GAME_ROOTS\s*=\s*\[.*?\];', s, re.DOTALL)
            if m:
                renderer_part = s[m.end():].strip()
            else:
                # Fallback: strip everything before the first (function(){ block
                m2 = re.search(r'\(function\(\)', s)
                renderer_part = s[m2.start():].strip() if m2 else ''
            if renderer_part:
                script_after = renderer_part
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

        section = f'''<h2 id="game{gi+1}">{heading}</h2>
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

    # Build TOC links from game summaries
    toc_links = ''
    for gi, summary in enumerate(settings['GAME_SUMMARIES']):
        heading = summary[0]
        toc_links += f'<a id="toc-game{gi+1}" onclick="goTo(\'game{gi+1}\')">{gi+1}. {heading}</a>\n'

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{page_title}</title>
<style>{style}</style>
</head>
<body>
<div class="top">
  <a class="lib" href="../../index.html">◂ Library</a>
  <span class="t">{page_title}</span>
  <button onclick="adjFs(-1)" title="Smaller text">A−</button>
  <button onclick="adjFs(1)" title="Larger text">A+</button>
  <button id="dkbtn" onclick="toggleDark()">Dark</button>
</div>
<div class="wrap">
<nav class="toc" id="toc">
  <div class="h">Contents</div>
  {toc_links}
</nav>
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
</div>
<script>
{script_before}
</script>
<script>
const NODES = {nodes_json};
const GAME_ROOTS = {roots_json};
function adjFs(d){{var r=document.documentElement,fs=parseFloat(getComputedStyle(r).getPropertyValue('--fs')||'21');r.style.setProperty('--fs',(fs+d*1.5)+'px');try{{localStorage.setItem('gw_fs',fs+d*1.5)}}catch(e){{}}}}
function toggleDark(){{document.body.classList.toggle('dark');var dk=document.body.classList.contains('dark');document.getElementById('dkbtn').textContent=dk?'Light':'Dark';try{{localStorage.setItem('gw_dk',dk?'1':'0')}}catch(e){{}}}}
(function(){{try{{var fs=localStorage.getItem('gw_fs');if(fs)document.documentElement.style.setProperty('--fs',fs+'px');var dk=localStorage.getItem('gw_dk');if(dk==='1'){{document.body.classList.add('dark');var b=document.getElementById('dkbtn');if(b)b.textContent='Light';}}}}catch(e){{}}}})();
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
