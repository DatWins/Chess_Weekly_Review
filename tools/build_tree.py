"""Build a zoomable opening-tree viewer for one Chess Weekly Review issue.

Usage (run from anywhere):
    python build_tree.py <pgn_file> [options]

Examples:
    python build_tree.py issues/twic1668_taimanov/twic1668_taimanov.pgn
    python build_tree.py issues/twic1668_taimanov/twic1668_taimanov.pgn --title "TWIC 1668 – Taimanov Sicilian"
    python build_tree.py issues/twic1668_taimanov/twic1668_taimanov.pgn --max-plies 10 --min-games 1

Output:
    tree.html written next to the PGN file (e.g. issues/twic1668_taimanov/tree.html)

Requirements:
    pip install python-chess
    (No other packages needed — no cairosvg, no graphviz, no Pillow)
"""

import argparse, math, os, sys
import chess, chess.pgn, chess.svg

# ── board colours (matches Chess Weekly Review style) ────────────────────────
COLORS = {"square light": "#DEE3E6", "square dark": "#8CA2AD", "margin": "#5B6F79"}

# ── Node ─────────────────────────────────────────────────────────────────────
class Node:
    __slots__ = ("san", "ply", "parent", "kids", "n", "w", "d", "l")
    def __init__(self, san=None, ply=0, parent=None):
        self.san, self.ply, self.parent = san, ply, parent
        self.kids, self.n, self.w, self.d, self.l = {}, 0, 0, 0, 0

    @property
    def score(self):
        return (self.w + self.d / 2) / self.n if self.n else 0

    def path(self):
        out, x = [], self
        while x.parent is not None:
            out.append(x.san); x = x.parent
        return out[::-1]


# ── PGN → tree ───────────────────────────────────────────────────────────────
def load_games(pgn_path):
    games = []
    with open(pgn_path, encoding="utf-8", errors="replace") as f:
        while True:
            g = chess.pgn.read_game(f)
            if g is None:
                break
            h = g.headers
            if "FEN" in h or h.get("Variant"):
                continue
            board = g.board()
            sans = []
            for mv in g.mainline_moves():
                sans.append(board.san(mv)); board.push(mv)
            if not sans:
                continue
            res = h.get("Result", "*")
            games.append(dict(white=h.get("White","?"), black=h.get("Black","?"),
                               result=res, moves=sans))
    return games


def build_tree(games, max_plies=40):
    root = Node()
    for g in games:
        node = root; node.n += 1
        for i, san in enumerate(g["moves"][:max_plies]):
            kid = node.kids.get(san)
            if kid is None:
                kid = node.kids[san] = Node(san, i + 1, node)
            node = kid; node.n += 1
            r = g["result"]
            node.w += r == "1-0"; node.d += r == "1/2-1/2"; node.l += r == "0-1"
        root.w += g["result"] == "1-0"
        root.d += g["result"] == "1/2-1/2"
        root.l += g["result"] == "0-1"
    return root


# ── tree filtering ────────────────────────────────────────────────────────────
def pick(node, min_games, max_plies, base_ply):
    if node.ply - base_ply >= max_plies:
        return []
    return sorted([k for k in node.kids.values() if k.n >= min_games], key=lambda k: -k.n)


def count_nodes(start, min_games, max_plies):
    n, stack = 0, [start]
    while stack:
        x = stack.pop(); n += 1
        stack.extend(pick(x, min_games, max_plies, start.ply))
    return n


def auto_min(root, max_plies, cap, start=1):
    m = start
    while count_nodes(root, m, max_plies) > cap:
        m += 1
    return m


# ── SVG tree layout ───────────────────────────────────────────────────────────
BOARD_SZ = 180      # px per board square × 8
BOARD_PAD = 12      # extra px around board SVG (chess.svg margin)
H_GAP = 60          # horizontal gap between board centres
V_GAP = 60          # vertical gap between levels
LABEL_H = 46        # height reserved for move label above each board


def board_svg_inline(board, last_move=None, size=BOARD_SZ):
    """Return the chess.svg board as a string (already an <svg> element)."""
    arrows = ([chess.svg.Arrow(last_move.from_square, last_move.to_square,
                               color="#15781B")]
              if last_move else [])
    return chess.svg.board(board=board, size=size, arrows=arrows, colors=COLORS)


# ── layout engine: compute (col, row) for every node ─────────────────────────
def layout(root, min_games, max_plies):
    """
    Assign integer (col, row) positions using a simple recursive algorithm:
    each leaf gets its own column; parents centre over their children.
    Returns: list of (node, board, last_move, col, row)
    """
    items = []   # (node, board, last_move)
    # DFS to collect nodes + replay board
    def collect(node, board, last_move, depth):
        children = pick(node, min_games, max_plies, root.ply)
        items.append((node, board.copy(), last_move, depth))
        for kid in children:
            nb = board.copy()
            mv = nb.parse_san(kid.san)
            nb.push(mv)
            collect(kid, nb, mv, depth + 1)
    collect(root, chess.Board(), None, 0)

    # assign columns via post-order leaf-counting
    node_col = {}
    next_leaf = [0]

    def assign_col(node, depth):
        children = pick(node, min_games, max_plies, root.ply)
        if not children:
            node_col[id(node)] = next_leaf[0]
            next_leaf[0] += 1
        else:
            for kid in children:
                assign_col(kid, depth + 1)
            cols = [node_col[id(k)] for k in children]
            node_col[id(node)] = (min(cols) + max(cols)) / 2

    assign_col(root, 0)

    result = []
    for node, board, last_move, depth in items:
        result.append((node, board, last_move, node_col[id(node)], depth))
    return result, next_leaf[0]


def render_svg_tree(root, min_games, max_plies, title):
    items, num_cols = layout(root, min_games, max_plies)
    top = root.n

    cell_w = BOARD_SZ + H_GAP
    cell_h = BOARD_SZ + LABEL_H + V_GAP

    # find depth range
    max_depth = max(row for _, _, _, _, row in items)

    total_w = num_cols * cell_w + H_GAP
    total_h = (max_depth + 1) * cell_h + V_GAP + 40  # 40 for title

    def cx(col): return H_GAP / 2 + col * cell_w + BOARD_SZ / 2
    def cy_board(row): return 40 + V_GAP / 2 + row * cell_h + LABEL_H

    # build a dict for fast lookup: id(node) → (col, row, cx, cy)
    pos = {}
    for node, board, last_move, col, row in items:
        pos[id(node)] = (col, row, cx(col), cy_board(row))

    lines = []
    lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" '
                 f'width="{total_w:.0f}" height="{total_h:.0f}" '
                 f'style="background:#dee3e6;font-family:Helvetica,Arial,sans-serif">')

    # title
    lines.append(f'  <text x="{total_w/2:.0f}" y="28" text-anchor="middle" '
                 f'font-size="20" font-weight="bold" fill="#1a2a35">'
                 f'{_esc(title)}</text>')

    # draw edges first (so they appear behind boards)
    # collect parent positions: traverse tree
    def draw_edges(node, board, depth):
        children = pick(node, min_games, max_plies, root.ply)
        _, _, px, py = pos[id(node)]
        board_bottom_y = py + BOARD_SZ / 2
        for kid in children:
            _, _, kx, ky = pos[id(kid)]
            kid_top_y = ky - BOARD_SZ / 2 - LABEL_H
            # edge thickness proportional to game count
            pw = 1.5 + 6 * math.sqrt(kid.n / top)
            # draw L-shaped connector
            mid_y = board_bottom_y + (kid_top_y - board_bottom_y) * 0.4
            path = (f'M {px:.1f} {board_bottom_y:.1f} '
                    f'L {px:.1f} {mid_y:.1f} '
                    f'L {kx:.1f} {mid_y:.1f} '
                    f'L {kx:.1f} {kid_top_y:.1f}')
            lines.append(f'  <path d="{path}" fill="none" stroke="#2b3a44" '
                         f'stroke-width="{pw:.1f}" stroke-linejoin="round"/>')

            # move label
            ply = kid.ply
            num = (ply + 1) // 2
            mvtxt = f"{num}.{kid.san}" if ply % 2 else f"{num}…{kid.san}"
            pct = f"{kid.score:.0%}"
            games_txt = f"{kid.n}g · {pct}"
            label_y = kid_top_y + 4
            lines.append(f'  <text x="{kx:.1f}" y="{label_y:.1f}" text-anchor="middle" '
                         f'font-size="13" font-weight="bold" fill="#1a4fd0">{_esc(mvtxt)}</text>')
            lines.append(f'  <text x="{kx:.1f}" y="{label_y+16:.1f}" text-anchor="middle" '
                         f'font-size="11" fill="#555">{_esc(games_txt)}</text>')

            nb = board.copy()
            mv = nb.parse_san(kid.san)
            nb.push(mv)
            draw_edges(kid, nb, depth + 1)

    draw_edges(root, chess.Board(), 0)

    # draw boards
    for node, board, last_move, col, row in items:
        _, _, bx, by = pos[id(node)]
        svg_str = board_svg_inline(board, last_move, BOARD_SZ)
        # strip the outer <?xml ...?> and wrap in a <g> with translate
        svg_str = svg_str.replace('<?xml version="1.0" encoding="utf-8"?>', '').strip()
        x_off = bx - BOARD_SZ / 2
        y_off = by - BOARD_SZ / 2
        lines.append(f'  <g transform="translate({x_off:.1f},{y_off:.1f})">')
        lines.append('  ' + svg_str)
        lines.append('  </g>')

    lines.append('</svg>')
    return '\n'.join(lines)


def _esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')


# ── HTML template ─────────────────────────────────────────────────────────────
VIEWER_TEMPLATE = """\
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
  :root { --bg:#dee3e6; --bar:#1f2a33; --barText:#dee3e6; --btn:#34505f; --btnHover:#1f4fa3; }
  html,body { margin:0; height:100%; background:var(--bg); font-family:Helvetica,Arial,sans-serif; overflow:hidden; }
  header { position:fixed; top:0; left:0; right:0; height:52px; background:var(--bar); color:var(--barText);
           display:flex; align-items:center; gap:10px; padding:0 16px; z-index:2; box-sizing:border-box; }
  .back { color:#dee3e6; text-decoration:none; font-size:15px; white-space:nowrap; padding:7px 12px;
          border-radius:6px; background:#34505f; }
  .back:hover { background:#1f4fa3; }
  header h1 { font-size:18px; margin:0 auto 0 0; font-weight:600; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  button { background:var(--btn); color:#dee3e6; border:0; border-radius:6px; font-size:18px;
           min-width:40px; height:36px; padding:0 12px; cursor:pointer; }
  button:hover { background:var(--btnHover); }
  #zoomLabel { min-width:56px; text-align:center; font-size:15px; }
  #stage { position:absolute; top:52px; left:0; right:0; bottom:0; overflow:hidden; cursor:grab; touch-action:none; }
  #stage.dragging { cursor:grabbing; }
  #tree { position:absolute; top:0; left:0; transform-origin:0 0; user-select:none; }
  #hint { position:fixed; bottom:12px; left:50%; transform:translateX(-50%); background:rgba(31,42,51,.9);
          color:#dee3e6; padding:8px 14px; border-radius:6px; font-size:14px; transition:opacity 1s; pointer-events:none; }
  .info { position:fixed; bottom:48px; left:50%; transform:translateX(-50%);
          color:#555; font-size:13px; white-space:nowrap; }
  @media (max-width: 640px) {
    header { gap:6px; padding:0 8px; }
    header h1 { display:none; }
    .back { margin-right:auto; }
    button { min-width:34px; padding:0 8px; font-size:16px; }
    #zoomLabel { min-width:44px; font-size:13px; }
  }
</style>
</head>
<body>
<header>
  <a href="__BACK__" class="back">&#8592; __BACKTXT__</a>
  <h1>__TITLE__</h1>
  <button id="out">&#8722;</button>
  <span id="zoomLabel">100%</span>
  <button id="in">+</button>
  <button id="fit">Fit</button>
  <button id="actual">1:1</button>
</header>
<div id="stage">
  <div id="tree">__SVG__</div>
</div>
<p class="info">__INFO__</p>
<div id="hint">Scroll or pinch to zoom &middot; drag to pan &middot; double-click to zoom in</div>
<script>
(function(){
  const stage=document.getElementById('stage'),tree=document.getElementById('tree'),
        label=document.getElementById('zoomLabel');
  let scale=1,x=0,y=0,minScale=0.05,maxScale=4;
  function apply(){tree.style.transform=`translate(${x}px,${y}px) scale(${scale})`;label.textContent=Math.round(scale*100)+'%';}
  function svgSize(){const s=tree.querySelector('svg');return s?[+s.getAttribute('width'),+s.getAttribute('height')]:[800,600];}
  function fit(){const [sw,sh]=svgSize(),w=stage.clientWidth,h=stage.clientHeight;
    scale=Math.min(w/sw,h/sh)*0.98;minScale=scale*0.5;x=(w-sw*scale)/2;y=(h-sh*scale)/2;apply();}
  function zoomAt(f,cx,cy){const ns=Math.min(maxScale,Math.max(minScale,scale*f));f=ns/scale;x=cx-(cx-x)*f;y=cy-(cy-y)*f;scale=ns;apply();}
  window.addEventListener('load',fit);window.addEventListener('resize',fit);
  document.getElementById('fit').onclick=fit;
  document.getElementById('actual').onclick=()=>{scale=1;x=0;y=0;apply();};
  document.getElementById('out').onclick=()=>zoomAt(1/1.3,...[stage.clientWidth/2,stage.clientHeight/2]);
  document.getElementById('in').onclick=()=>zoomAt(1.3,...[stage.clientWidth/2,stage.clientHeight/2]);
  stage.addEventListener('wheel',e=>{e.preventDefault();const r=stage.getBoundingClientRect();
    zoomAt(e.deltaY<0?1.15:1/1.15,e.clientX-r.left,e.clientY-r.top);},{passive:false});
  stage.addEventListener('dblclick',e=>{const r=stage.getBoundingClientRect();zoomAt(2,e.clientX-r.left,e.clientY-r.top);});
  let drag=null;
  stage.addEventListener('pointerdown',e=>{stage.setPointerCapture(e.pointerId);drag={ox:x,oy:y,px:e.clientX,py:e.clientY};stage.classList.add('dragging');});
  stage.addEventListener('pointermove',e=>{if(!drag)return;x=drag.ox+(e.clientX-drag.px);y=drag.oy+(e.clientY-drag.py);apply();});
  stage.addEventListener('pointerup',()=>{drag=null;stage.classList.remove('dragging');});
  let pDist=null;
  stage.addEventListener('touchstart',e=>{if(e.touches.length===2)pDist=Math.hypot(e.touches[0].clientX-e.touches[1].clientX,e.touches[0].clientY-e.touches[1].clientY);},{passive:true});
  stage.addEventListener('touchmove',e=>{if(e.touches.length===2){const d=Math.hypot(e.touches[0].clientX-e.touches[1].clientX,e.touches[0].clientY-e.touches[1].clientY);
    if(pDist){const mx=(e.touches[0].clientX+e.touches[1].clientX)/2,my=(e.touches[0].clientY+e.touches[1].clientY)/2;
      const r=stage.getBoundingClientRect();zoomAt(d/pDist,mx-r.left,my-r.top);}pDist=d;}},{passive:true});
  setTimeout(()=>{const h=document.getElementById('hint');if(h)h.style.opacity='0';},3000);
})();
</script>
</body>
</html>
"""


def build(pgn_path, title=None, max_plies=12, min_games=None, cap=80):
    pgn_path = os.path.abspath(pgn_path)
    out_dir = os.path.dirname(pgn_path)
    stem = os.path.splitext(os.path.basename(pgn_path))[0]

    if title is None:
        parts = stem.split("_", 1)
        title = parts[0].upper() + (" — " + parts[1].replace("_", " ").title() if len(parts) > 1 else "")
        title += " — Opening Tree"

    print(f"Loading {pgn_path} ...", flush=True)
    games = load_games(pgn_path)
    if not games:
        sys.exit("No games found in PGN.")
    print(f"  {len(games)} games loaded", flush=True)

    root = build_tree(games, max_plies=40)

    if min_games is None:
        min_games = auto_min(root, max_plies, cap)
    nodes = count_nodes(root, min_games, max_plies)
    print(f"  min_games={min_games}  max_plies={max_plies}  nodes={nodes}", flush=True)

    print("  Rendering SVG tree ...", flush=True)
    svg = render_svg_tree(root, min_games, max_plies, title)

    info = f"{len(games)} games · min {min_games} per branch · up to {max_plies} plies"
    back_file = stem + ".html"
    html = (VIEWER_TEMPLATE
            .replace("__TITLE__", title)
            .replace("__SVG__", svg)
            .replace("__BACK__", back_file)
            .replace("__BACKTXT__", "Games")
            .replace("__INFO__", info))

    out_html = os.path.join(out_dir, "tree.html")
    with open(out_html, "w", encoding="utf-8") as f:
        f.write(html)
    kb = len(html.encode()) // 1024
    print(f"\nDone! → {out_html}  ({kb} KB)", flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("pgn", help="Path to the issue PGN file")
    p.add_argument("--title", help="Page title (auto-derived from filename if omitted)")
    p.add_argument("--max-plies", type=int, default=12, help="Deepest ply to show (default 12)")
    p.add_argument("--min-games", type=int, default=None, help="Min games per branch (auto if omitted)")
    p.add_argument("--cap", type=int, default=80, help="Max board positions when auto min-games (default 80)")
    args = p.parse_args()
    build(args.pgn, title=args.title, max_plies=args.max_plies, min_games=args.min_games, cap=args.cap)
