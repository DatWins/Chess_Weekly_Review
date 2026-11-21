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
    pip install python-chess cairosvg graphviz Pillow
    Graphviz binary must also be installed: https://graphviz.org/download/
"""

import argparse, base64, math, os, re, sys, tempfile
import chess, chess.pgn, chess.svg
import cairosvg
from graphviz import Digraph
from PIL import Image

# ── board colours (matches what_ya_playing / Chess Weekly Review style) ──────
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


# ── tree drawing ──────────────────────────────────────────────────────────────
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


def board_png(board, last_move, img_dir, size=260):
    arrows = ([chess.svg.Arrow(last_move.from_square, last_move.to_square, color="#15781B")]
              if last_move else [])
    svg = chess.svg.board(board=board, size=size, arrows=arrows, colors=COLORS).encode()
    name = board.epd().replace("/", "_").replace(" ", "_") + (f"_{last_move.uci()}" if last_move else "") + f"_{size}.png"
    path = os.path.abspath(os.path.join(img_dir, name))
    if not os.path.exists(path):
        tmp = path + ".tmp"
        cairosvg.svg2png(bytestring=svg, write_to=tmp)
        os.replace(tmp, path)
    return path


def draw_tree(root, out_png, min_games, max_plies, img_dir, board_size=260, label_pt=34):
    os.makedirs(img_dir, exist_ok=True)
    dot = Digraph(
        graph_attr={"splines": "ortho", "ranksep": "1.3", "nodesep": "1.0",
                    "bgcolor": "white", "forcelabels": "true", "ordering": "out"},
        node_attr={"shape": "none"},
        edge_attr={"color": "#2b3a44", "arrowsize": "0.9"},
    )
    top = root.n
    ids = {}
    def nid(x): return "n" + str(ids.setdefault(id(x), len(ids)))
    stack = [(root, chess.Board(), None)]
    while stack:
        x, b, last = stack.pop()
        dot.node(nid(x), label="", image=board_png(b, last, img_dir, board_size))
        for k in pick(x, min_games, max_plies, root.ply):
            nb = b.copy(); mv = nb.parse_san(k.san); nb.push(mv)
            num = (k.ply + 1) // 2
            mvtxt = f"{num}.{k.san}" if k.ply % 2 else f"{num}...{k.san}"
            lab = (f'<<FONT COLOR="#1a4fd0" POINT-SIZE="{label_pt}"><B>{mvtxt}</B>&#160;&#160;&#160;&#160;</FONT><BR/>'
                   f'<FONT COLOR="#555555" POINT-SIZE="{int(label_pt*0.72)}">'
                   f'{k.n} game{"" if k.n == 1 else "s"} · {k.score:.0%}&#160;&#160;&#160;&#160;</FONT>>')
            dot.edge(nid(x), nid(k), xlabel=lab, penwidth=f"{1.5 + 7*math.sqrt(k.n/top):.1f}")
            stack.append((k, nb, mv))
    base = os.path.splitext(out_png)[0]
    dot.render(base, format="png", cleanup=True)
    return base + ".png"


# ── quantise + base64 ─────────────────────────────────────────────────────────
def quantise_png(src, colors=64):
    im = Image.open(src).convert("RGB")
    q = im.quantize(colors=colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    pal = q.getpalette()[:colors * 3]
    bright = max(range(colors), key=lambda k: sum(pal[3*k:3*k+3]))
    pal[3*bright:3*bright+3] = [255, 255, 255]
    q.putpalette(pal)
    out = src.replace(".png", ".q.png")
    q.save(out, optimize=True)
    return out


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
  #tree { position:absolute; top:0; left:0; transform-origin:0 0; user-select:none; -webkit-user-drag:none; }
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
  <button id="out">−</button>
  <span id="zoomLabel">100%</span>
  <button id="in">+</button>
  <button id="fit">Fit</button>
  <button id="actual">1:1</button>
</header>
<div id="stage"><img id="tree" src="__IMG__" alt="__TITLE__" draggable="false"></div>
<p class="info">__INFO__</p>
<div id="hint">Scroll or pinch to zoom · drag to pan · double-click to zoom in</div>
<script>
(function(){
  const stage=document.getElementById('stage'),img=document.getElementById('tree'),label=document.getElementById('zoomLabel');
  let scale=1,x=0,y=0,minScale=0.05,maxScale=4;
  function apply(){img.style.transform=`translate(${x}px,${y}px) scale(${scale})`;label.textContent=Math.round(scale*100)+'%';}
  function zoomAt(f,cx,cy){const ns=Math.min(maxScale,Math.max(minScale,scale*f));f=ns/scale;x=cx-(cx-x)*f;y=cy-(cy-y)*f;scale=ns;apply();}
  function fit(){const w=stage.clientWidth,h=stage.clientHeight;scale=Math.min(w/img.naturalWidth,h/img.naturalHeight)*0.98;
    minScale=scale*0.5;x=(w-img.naturalWidth*scale)/2;y=(h-img.naturalHeight*scale)/2;apply();}
  img.complete?fit():img.addEventListener('load',fit);
  window.addEventListener('resize',fit);
  document.getElementById('fit').onclick=fit;
  document.getElementById('actual').onclick=()=>{scale=1;x=0;y=0;apply();};
  document.getElementById('out').onclick=()=>{const c=[stage.clientWidth/2,stage.clientHeight/2];zoomAt(1/1.3,c[0],c[1]);};
  document.getElementById('in').onclick=()=>{const c=[stage.clientWidth/2,stage.clientHeight/2];zoomAt(1.3,c[0],c[1]);};
  stage.addEventListener('wheel',e=>{e.preventDefault();const r=stage.getBoundingClientRect();
    zoomAt(e.deltaY<0?1.15:1/1.15,e.clientX-r.left,e.clientY-r.top);},{passive:false});
  stage.addEventListener('dblclick',e=>{const r=stage.getBoundingClientRect();zoomAt(2,e.clientX-r.left,e.clientY-r.top);});
  let drag=null;
  stage.addEventListener('pointerdown',e=>{stage.setPointerCapture(e.pointerId);drag={ox:x,oy:y,px:e.clientX,py:e.clientY};stage.classList.add('dragging');});
  stage.addEventListener('pointermove',e=>{if(!drag)return;x=drag.ox+(e.clientX-drag.px);y=drag.oy+(e.clientY-drag.py);apply();});
  stage.addEventListener('pointerup',()=>{drag=null;stage.classList.remove('dragging');});
  let pDist=null;
  stage.addEventListener('touchstart',e=>{if(e.touches.length===2){pDist=Math.hypot(e.touches[0].clientX-e.touches[1].clientX,e.touches[0].clientY-e.touches[1].clientY);}},{passive:true});
  stage.addEventListener('touchmove',e=>{if(e.touches.length===2){const d=Math.hypot(e.touches[0].clientX-e.touches[1].clientX,e.touches[0].clientY-e.touches[1].clientY);
    if(pDist){const mx=(e.touches[0].clientX+e.touches[1].clientX)/2,my=(e.touches[0].clientY+e.touches[1].clientY)/2;
      const r=stage.getBoundingClientRect();zoomAt(d/pDist,mx-r.left,my-r.top);}pDist=d;}},{passive:true});
  setTimeout(()=>{const h=document.getElementById('hint');h.style.opacity='0';},3000);
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
        # derive from folder name: "twic1668_taimanov" -> "TWIC 1668 — Taimanov"
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

    with tempfile.TemporaryDirectory() as tmp:
        img_dir = os.path.join(tmp, "boards")
        raw_png = os.path.join(tmp, "tree.png")

        for depth in (max_plies, 10, 8, 6):
            try:
                draw_tree(root, raw_png, min_games, depth, img_dir)
                break
            except Exception as e:
                print(f"  draw failed at depth {depth} ({e}), retrying shallower", flush=True)
        else:
            sys.exit("Could not draw tree.")

        q_png = quantise_png(raw_png)
        b64 = "data:image/png;base64," + base64.b64encode(open(q_png, "rb").read()).decode()
        kb = os.path.getsize(q_png) // 1024
        print(f"  PNG: {kb} KB", flush=True)

    info = f"{len(games)} games · min {min_games} per branch · up to {max_plies} plies"
    back_file = stem + ".html"
    html = (VIEWER_TEMPLATE
            .replace("__TITLE__", title)
            .replace("__IMG__", b64)
            .replace("__BACK__", back_file)
            .replace("__BACKTXT__", "← Games")
            .replace("__INFO__", info))

    out_html = os.path.join(out_dir, "tree.html")
    open(out_html, "w", encoding="utf-8").write(html)
    print(f"\nDone! → {out_html}", flush=True)
    print(f'Now add this link to the game viewer HTML near the top of the article:', flush=True)
    print(f'  <p><a href="tree.html">📊 View opening tree →</a></p>', flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("pgn", help="Path to the issue PGN file")
    p.add_argument("--title", help="Page title (auto-derived from filename if omitted)")
    p.add_argument("--max-plies", type=int, default=12, help="Deepest ply to show (default 12)")
    p.add_argument("--min-games", type=int, default=None, help="Min games per branch (auto if omitted)")
    p.add_argument("--cap", type=int, default=80, help="Max board positions when auto min-games (default 80)")
    args = p.parse_args()
    build(args.pgn, title=args.title, max_plies=args.max_plies, min_games=args.min_games, cap=args.cap)
