#!/usr/bin/env python3
"""Build twic1668_rossolimo.html"""

PGN_FILE = 'issues/twic1668_rossolimo/twic1668_rossolimo.pgn'
OUT_HTML  = 'issues/twic1668_rossolimo/twic1668_rossolimo.html'
TEMPLATE  = 'issues/twic1667/twic1667_nf3b3bb2.html'

PAGE_TITLE     = 'TWIC 1668 – Rossolimo Sicilian'
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
        'counterplay with rook lifts. A tactical blow on move 40 ends White\'s resistance.',
    ),
    (
        'Aizenberg – Wei Yi',
        'B30 · Rossolimo, 3...e6',
        'Wei Yi (2758) handles the Rossolimo from the Black side with trademark ease. '
        'He builds up pressure on the queenside and his extra material tells in the endgame.',
    ),
    (
        'Harikrishna – Romanov',
        'B30 · Rossolimo, 3...e6',
        'Harikrishna (2648) is in his element in the Rossolimo. He keeps the position '
        'closed and outmanoeuvres Romanov in a smooth positional game.',
    ),
    (
        'Harikrishna – Sokolovsky',
        'B51 · Moscow Variation, 3...Bd7',
        'A second Harikrishna Rossolimo — this time the Moscow Variation (3.Bb5+ Bd7). '
        'White wins convincingly after Black mishandles the transition to the endgame.',
    ),
    (
        'Sahidi – Pranesh',
        'B30 · Rossolimo, 3...e6',
        'Pranesh (2674) is one of India\'s rising stars, but Sahidi (2482) outplays him '
        'in a complex middlegame and converts the full point.',
    ),
    (
        'Boyer – Volokitin',
        'B51 · Moscow Variation, 3...Bd7',
        'Volokitin is on the other side of the Rossolimo this time — and Boyer '
        'exploits his queenside initiative to win material and the game.',
    ),
    (
        'Dudognon – Rapport',
        'B30 · Rossolimo, 3...e6',
        'The rating underdog Dudognon (2323) tries his luck with the Rossolimo against '
        'Rapport (2711), but the Hungarian star turns the tables with an imaginative pawn sacrifice.',
    ),
]

# ===========================================================================
# Engine — identical to build_issue.py
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

def tokenize_moves(s):
    tokens = []
    i = 0
    while i < len(s):
        if s[i].isspace():
            i += 1; continue
        if s[i] == '{':
            end = s.index('}', i)
            tokens.append(('comment', s[i+1:end].strip()))
            i = end + 1; continue
        if s[i] == '(':
            tokens.append(('var_open', '(')); i += 1; continue
        if s[i] == ')':
            tokens.append(('var_close', ')')); i += 1; continue
        if s[i:i+3] in ('1-0', '0-1') or s[i:i+7] == '1/2-1/2' or s[i] == '*':
            if s[i:i+7] == '1/2-1/2':
                tokens.append(('result', '1/2-1/2')); i += 7
            elif s[i:i+3] in ('1-0','0-1'):
                tokens.append(('result', s[i:i+3])); i += 3
            else:
                tokens.append(('result', '*')); i += 1
            continue
        m = re.match(r'(\d+)(\.+)', s[i:])
        if m:
            tokens.append(('movenum', int(m.group(1)), len(m.group(2)) > 1))
            i += len(m.group(0)); continue
        m = re.match(r'\$\d+', s[i:])
        if m:
            tokens.append(('glyph', m.group(0))); i += len(m.group(0)); continue
        m = re.match(r'[!?]{1,2}', s[i:])
        if m:
            tokens.append(('ann', m.group(0))); i += len(m.group(0)); continue
        m = re.match(r'[KQRBN]?[a-h]?[1-8]?x?[a-h][1-8](=[QRBN])?[+#]?|O-O-O[+#]?|O-O[+#]?', s[i:])
        if m:
            tokens.append(('san', m.group(0))); i += len(m.group(0)); continue
        i += 1
    return tokens

INIT_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'

def fen_to_board(fen):
    board = [''] * 64
    rows = fen.split()[0].split('/')
    for r, row in enumerate(rows):
        c = 0
        for ch in row:
            if ch.isdigit(): c += int(ch)
            else: board[r*8+c] = ch; c += 1
    return board

def sq(name):
    return (8 - int(name[1])) * 8 + (ord(name[0]) - ord('a'))

def sq_name(idx):
    return 'abcdefgh'[idx % 8] + str(8 - idx // 8)

def _clear_line(board, sr, sc, dr, dc):
    rdir = 0 if sr==dr else (1 if dr>sr else -1)
    cdir = 0 if sc==dc else (1 if dc>sc else -1)
    r, c = sr+rdir, sc+cdir
    while (r,c) != (dr,dc):
        if board[r*8+c]: return False
        r += rdir; c += cdir
    return True

def _clear_diag(board, sr, sc, dr, dc):
    rdir = 1 if dr>sr else -1
    cdir = 1 if dc>sc else -1
    r, c = sr+rdir, sc+cdir
    while (r,c) != (dr,dc):
        if board[r*8+c]: return False
        r += rdir; c += cdir
    return True

def _can_reach(board, src, dest, piece, white, ep, castling):
    sr, sc = src//8, src%8
    dr, dc = dest//8, dest%8
    dr_diff, dc_diff = dr-sr, dc-sc
    target = board[dest]
    if target and (target.isupper() == white): return False
    if piece in ('P','p'):
        dir_ = -1 if white else 1
        start_rank = 6 if white else 1
        if dc_diff==0 and dr_diff==dir_ and not target: return True
        if dc_diff==0 and sr==start_rank and dr_diff==2*dir_ and not target and not board[src+8*dir_]: return True
        if abs(dc_diff)==1 and dr_diff==dir_ and (target or sq_name(dest)==ep): return True
        return False
    if piece in ('N','n'): return abs(dr_diff)*abs(dc_diff)==2
    if piece in ('B','b'):
        if abs(dr_diff)!=abs(dc_diff): return False
        return _clear_diag(board, sr, sc, dr, dc)
    if piece in ('R','r'):
        if dr_diff!=0 and dc_diff!=0: return False
        return _clear_line(board, sr, sc, dr, dc)
    if piece in ('Q','q'):
        if abs(dr_diff)==abs(dc_diff): return _clear_diag(board, sr, sc, dr, dc)
        if dr_diff==0 or dc_diff==0: return _clear_line(board, sr, sc, dr, dc)
        return False
    if piece in ('K','k'): return max(abs(dr_diff),abs(dc_diff))==1
    return False

def apply_move(fen, san):
    parts = fen.split()
    board = fen_to_board(fen)
    turn = parts[1]; castling = parts[2]; ep = parts[3]
    half = int(parts[4]); full = int(parts[5])
    white = turn=='w'
    new_ep = '-'; capture = False
    if san in ('O-O','O-O+','O-O#'):
        if white:
            board[sq('e1')]=''; board[sq('h1')]=''; board[sq('g1')]='K'; board[sq('f1')]='R'
            castling = castling.replace('K','').replace('Q','') or '-'
        else:
            board[sq('e8')]=''; board[sq('h8')]=''; board[sq('g8')]='k'; board[sq('f8')]='r'
            castling = castling.replace('k','').replace('q','') or '-'
    elif san in ('O-O-O','O-O-O+','O-O-O#'):
        if white:
            board[sq('e1')]=''; board[sq('a1')]=''; board[sq('c1')]='K'; board[sq('d1')]='R'
            castling = castling.replace('K','').replace('Q','') or '-'
        else:
            board[sq('e8')]=''; board[sq('a8')]=''; board[sq('c8')]='k'; board[sq('d8')]='r'
            castling = castling.replace('k','').replace('q','') or '-'
    else:
        clean = san.rstrip('+#')
        promo = None
        if '=' in clean:
            promo = clean.split('=')[1]
            if not white: promo = promo.lower()
            clean = clean.split('=')[0]
        capture = 'x' in clean
        clean = clean.replace('x','')
        piece_char = 'P' if clean[0].islower() else clean[0]
        if piece_char in 'KQRBN': clean = clean[1:]
        if not white: piece_char = piece_char.lower()
        dest = clean[-2:]; disambig = clean[:-2]
        dest_sq = sq(dest)
        ep_capture = piece_char in ('P','p') and dest==ep and ep!='-'
        src_sq = None
        for i, p in enumerate(board):
            if p != piece_char: continue
            if not _can_reach(board, i, dest_sq, piece_char, white, ep, castling): continue
            sn = sq_name(i)
            if disambig:
                if len(disambig)==2:
                    if sn!=disambig: continue
                elif disambig[0].isalpha():
                    if sn[0]!=disambig[0]: continue
                elif disambig[0].isdigit():
                    if sn[1]!=disambig[0]: continue
            src_sq = i; break
        if src_sq is None: return fen
        moving = board[src_sq]; board[src_sq] = ''
        if ep_capture: board[sq(ep[0]+('5' if white else '4'))] = ''
        board[dest_sq] = promo if promo else moving
        if piece_char in ('K','k'):
            if white: castling = castling.replace('K','').replace('Q','') or '-'
            else: castling = castling.replace('k','').replace('q','') or '-'
        if piece_char in ('R','r'):
            sn = sq_name(src_sq)
            if sn=='a1': castling=castling.replace('Q','')
            if sn=='h1': castling=castling.replace('K','')
            if sn=='a8': castling=castling.replace('q','')
            if sn=='h8': castling=castling.replace('k','')
        castling = castling or '-'
        if piece_char in ('P','p') and abs(src_sq-dest_sq)==16:
            new_ep = sq_name(src_sq)[0] + ('3' if white else '6')
        half = 0 if piece_char in ('P','p') or capture or ep_capture else half+1
    next_turn = 'b' if white else 'w'
    if not white: full += 1
    rows = []
    for r in range(8):
        row = ''; empty = 0
        for c in range(8):
            p = board[r*8+c]
            if p:
                if empty: row += str(empty); empty=0
                row += p
            else: empty += 1
        if empty: row += str(empty)
        rows.append(row)
    return '/'.join(rows) + f' {next_turn} {castling} {new_ep} {half} {full}'

def _find_move_squares(fen1, fen2, san):
    b1 = fen_to_board(fen1); b2 = fen_to_board(fen2)
    clean = san.rstrip('+#!?')
    if clean in ('O-O','O-O-O'):
        turn = fen1.split()[1]
        if clean=='O-O': return ('e1','g1') if turn=='w' else ('e8','g8')
        else: return ('e1','c1') if turn=='w' else ('e8','c8')
    clean2 = re.sub(r'=[QRBN]','',clean.replace('x',''))
    dest = clean2[-2:]
    turn = fen1.split()[1]
    piece_char = clean2[0] if clean2[0] in 'KQRBN' else 'P'
    if turn=='b': piece_char = piece_char.lower()
    for i,(p1,p2) in enumerate(zip(b1,b2)):
        if p1==piece_char and p2=='':
            sn = sq_name(i)
            disambig = clean2[1:-2] if piece_char.upper() in 'KQRBN' else clean2[:-2]
            if disambig:
                if len(disambig)==2:
                    if sn!=disambig: continue
                elif disambig[0].isalpha():
                    if sn[0]!=disambig[0]: continue
                elif disambig[0].isdigit():
                    if sn[1]!=disambig[0]: continue
            return (sn, dest)
    return ('', dest)

_node_counter = [0]

def _new_id(prefix):
    _node_counter[0] += 1
    return f'{prefix}_{_node_counter[0]}'

def build_nodes(game_prefix, tokens, start_fen=INIT_FEN, start_white=True):
    nodes = {}
    root_id = _new_id(game_prefix)
    nodes[root_id] = [start_fen, None, [], '', '', '', '', 0]
    stack = []
    current_parent = root_id; current_fen = start_fen
    current_num = 1; current_white = start_white
    pending_ann = ''
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok[0]=='movenum':
            current_num = tok[1]; current_white = not tok[2]; i+=1; continue
        if tok[0]=='ann':
            pending_ann = tok[1]; i+=1; continue
        if tok[0]=='glyph':
            glyph_map={'$1':'!','$2':'?','$3':'!!','$4':'??','$5':'!?','$6':'?!'}
            pending_ann = glyph_map.get(tok[1],''); i+=1; continue
        if tok[0]=='comment':
            if current_parent != root_id:
                last = current_parent
                if len(nodes[last])<9: nodes[last].append(tok[1])
                else: nodes[last][8] += ' ' + tok[1]
            i+=1; continue
        if tok[0]=='var_open':
            stack.append((current_parent, current_fen, current_num, current_white))
            par = nodes[current_parent][1]
            if par is None: par = current_parent
            current_parent = par; current_fen = nodes[par][0]; i+=1; continue
        if tok[0]=='var_close':
            if stack: current_parent, current_fen, current_num, current_white = stack.pop()
            i+=1; continue
        if tok[0]=='result': i+=1; continue
        if tok[0]=='san':
            san = tok[1]; ann = pending_ann; pending_ann = ''
            new_fen = apply_move(current_fen, san)
            node_id = _new_id(game_prefix)
            label = f'{current_num}.{san}{ann}' if current_white else f'{current_num}…{san}{ann}'
            from_sq, to_sq = _find_move_squares(current_fen, new_fen, san)
            is_white = 1 if current_white else 0
            nodes[node_id] = [new_fen, current_parent, [], san+ann, label, from_sq, to_sq, is_white]
            nodes[current_parent][2].append(node_id)
            current_parent = node_id; current_fen = new_fen
            if not current_white: current_num += 1
            current_white = not current_white; i+=1; continue
        i+=1
    return nodes, root_id

def _render_variation(nodes, start_id):
    parts = []; cur = start_id
    while cur:
        node = nodes[cur]
        parts.append(f'<a class="mv" data-id="{cur}">{node[4]}</a> ')
        comment = node[8] if len(node)>8 else ''
        if comment: parts.append(f'<span class="note">{comment} </span>')
        for sub in node[2][1:]:
            parts.append('('); parts.append(_render_variation(nodes, sub)); parts.append(') ')
        cur = node[2][0] if node[2] else None
    return ''.join(parts)

def build_move_text(nodes, root_id):
    parts = ['<p class="ml">\n']
    cur = root_id
    while nodes[cur][2]:
        cur = nodes[cur][2][0]
        node = nodes[cur]
        parts.append(f'<a class="mv" data-id="{cur}">{node[4]}</a> ')
        for var_root in node[2][1:]:
            parts.append('<span class="lines">(')
            parts.append(_render_variation(nodes, var_root))
            parts.append(') </span>')
        comment = node[8] if len(node)>8 else ''
        if comment: parts.append(f'<span class="note"> {comment} </span>')
    parts.append('\n</p>\n')
    return ''.join(parts)

def extract_template_parts(html):
    style_m = re.search(r'<style>(.*?)</style>', html, re.DOTALL)
    style = style_m.group(1) if style_m else ''
    script_before_nodes = re.search(r'<script>(.*?)const NODES', html, re.DOTALL)
    script_before = script_before_nodes.group(1) if script_before_nodes else ''
    script_after_nodes = re.search(r'const NODES=.*?;\n(.*?)</script>', html, re.DOTALL)
    script_after = script_after_nodes.group(1) if script_after_nodes else ''
    return style, script_before, script_after

def build_html(games_data, game_root_ids, all_nodes, style, script_before, script_after):
    nodes_js = json.dumps(
        {nid: list(v[:8]) + ([v[8]] if len(v)>8 else []) for nid,v in all_nodes.items()},
        separators=(',',':')
    )
    toc = ''
    for idx, summary in enumerate(GAME_SUMMARIES):
        gid = f'game{idx+1}'
        toc += f'  <a id="toc-{gid}" onclick="goTo(\'{gid}\')">{idx+1}. {summary[0]}</a>\n'

    game_html = ''
    for idx, (gdata, summary) in enumerate(zip(games_data, GAME_SUMMARIES)):
        headers, tokens = gdata
        root_id = game_root_ids[idx]
        gid = f'game{idx+1}'
        white   = headers.get('White','?').replace(',',', ')
        black   = headers.get('Black','?').replace(',',', ')
        welo    = headers.get('WhiteElo','')
        belo    = headers.get('BlackElo','')
        result  = headers.get('Result','*')
        date    = headers.get('Date','')
        event   = headers.get('Event','')
        round_  = headers.get('Round','')
        wteam   = headers.get('WhiteTeam','')
        bteam   = headers.get('BlackTeam','')
        welo_str = f' ({welo})' if welo else ''
        belo_str = f' ({belo})' if belo else ''

        game_html += f'\n<h2 id="{gid}">{idx+1}. {summary[0]}</h2>\n'
        game_html += f'<h3>{summary[1]}</h3>\n'
        game_html += f'<div class="gamehead">'
        game_html += f'<b>{white}</b>{welo_str}'
        if wteam: game_html += f' ({wteam})'
        game_html += f' – <b>{black}</b>{belo_str}'
        if bteam: game_html += f' ({bteam})'
        game_html += f'<br>{event}, Round {round_}, {date} · <b>{result}</b></div>\n'
        game_html += f'<p>{summary[2]}</p>\n'
        game_html += build_move_text(all_nodes, root_id)

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{PAGE_TITLE}</title>
<style>
{style}
@media(max-width:900px){{
  .wrap{{grid-template-columns:1fr}}
  aside.bp{{position:static;height:auto;border-left:none;border-top:1px solid var(--line);order:-1}}
  nav.toc{{display:none}}
}}
</style>
</head>
<body>
<div class="top">
  <a class="lib" href="../../index.html">◂ Library</a>
  <span class="t">{PAGE_TITLE}</span>
  <button onclick="adjFs(-1)" title="Smaller text">A−</button>
  <button onclick="adjFs(1)" title="Larger text">A+</button>
  <button id="dkbtn" onclick="toggleDark()">Dark</button>
</div>
<div class="wrap">
<nav class="toc" id="toc">
  <div class="h">Contents</div>
{toc}</nav>
<main id="main">
<p class="kicker">{ARTICLE_KICKER}</p>
<h1>{ARTICLE_H1}</h1>
<p class="dek">{ARTICLE_DEK}</p>
<div class="byline">{ARTICLE_BYLINE}</div>
<hr style="border:none;height:2px;background:var(--line);margin:1.2em 0 1.4em">
{ARTICLE_INTRO}
{game_html}
</main>
<aside class="bp">
  <div class="bhead"><span id="who"></span><b id="cur"></b></div>
  <div id="live"></div>
  <div class="ctrls">
    <button id="bStart" title="Start (Home)">⏮</button>
    <button id="bPrev" title="Back (←)">◀</button>
    <button id="bNext" title="Forward (→)">▶</button>
    <button id="bEnd" title="End of line (End)">⏭</button>
    <button id="bFlip" title="Flip board (F)">⇅</button>
  </div>
  <div class="choose" id="choose"></div>
  <div class="msg" id="msg"></div>
  <div class="path" id="path"></div>
</aside>
</div>
<script>
{script_before}
const NODES={nodes_js};
const GAME_ROOTS={json.dumps(game_root_ids)};
{script_after}
function goTo(id){{
  const el=document.getElementById(id);
  if(el) el.scrollIntoView({{behavior:'smooth',block:'start'}});
  document.querySelectorAll('.toc a').forEach(a=>a.classList.remove('on'));
  const ta=document.getElementById('toc-'+id);
  if(ta) ta.classList.add('on');
}}
document.addEventListener('DOMContentLoaded',()=>{{
  if(typeof goNode==='function' && GAME_ROOTS[0] && NODES[GAME_ROOTS[0]]){{
    const ch=NODES[GAME_ROOTS[0]][2];
    if(ch&&ch[0]) goNode(ch[0]); else goNode(GAME_ROOTS[0]);
  }}
  try{{if(localStorage.getItem('dk')==='1') document.documentElement.setAttribute('data-theme','dark');}}catch(e){{}}
  const btn=document.getElementById('dkbtn');
  if(btn) btn.textContent=document.documentElement.getAttribute('data-theme')==='dark'?'Light':'Dark';
}});
</script>
</body>
</html>'''

def main():
    pgn_path = Path(PGN_FILE)
    print(f'Reading PGN: {PGN_FILE}')
    raw_games = parse_pgn_games(pgn_path.read_text(encoding='utf-8', errors='replace'))
    print(f'  {len(raw_games)} games found')
    if len(raw_games) != len(GAME_SUMMARIES):
        print(f'WARNING: {len(raw_games)} games but {len(GAME_SUMMARIES)} summaries')

    print(f'Reading template: {TEMPLATE}')
    template_html = Path(TEMPLATE).read_text(encoding='utf-8', errors='replace')
    style, script_before, script_after = extract_template_parts(template_html)

    print('Building node trees...')
    all_nodes = {}
    game_root_ids = []
    games_data = []
    for idx, (headers, moves_str) in enumerate(raw_games):
        prefix = f'g{idx}'
        tokens = tokenize_moves(moves_str)
        nodes, root_id = build_nodes(prefix, tokens)
        all_nodes.update(nodes)
        game_root_ids.append(root_id)
        games_data.append((headers, tokens))
        n_main = 0
        cur = root_id
        while nodes[cur][2]: cur = nodes[cur][2][0]; n_main += 1
        w = headers.get('White','?'); b = headers.get('Black','?')
        print(f'  Game {idx+1}: {w} vs {b} — {n_main} moves')

    print('Building HTML...')
    html = build_html(games_data, game_root_ids, all_nodes, style, script_before, script_after)
    out_path = Path(OUT_HTML)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding='utf-8')
    size_kb = out_path.stat().st_size // 1024
    print(f'Written: {OUT_HTML} ({size_kb} KB)')

    aside = html.find('<aside'); main_e = html.find('</main>')
    ok = main_e > 0 and aside > main_e
    print(f'Structure check (</main> before <aside>): {"OK" if ok else "FAIL"}')
    print('Done.')

if __name__ == '__main__':
    main()
