#!/usr/bin/env python3
"""
Chess Weekly Review — Top Opening Lines
========================================
Reads a TWIC PGN file and reports the N most common opening themes,
so you can pick which one to feature in the next issue.

USAGE
-----
  pip install python-chess

  # Top 30 openings from a TWIC PGN:
  python top_openings.py twic1668.pgn

  # Top 20, min Elo 2500, show sample game for each:
  python top_openings.py twic1668.pgn --top 20 --min-elo 2500 --show-games

  # Group by ECO code instead of opening name:
  python top_openings.py twic1668.pgn --by-eco

OUTPUT
------
  Rank  Count  Opening / Variation                        ECO   Win%W  Win%B  Draw%
  ─────────────────────────────────────────────────────────────────────────────────
     1    142  Sicilian Defence / Najdorf Variation        B90   38%    31%    31%
     2     98  Queen's Gambit Declined / 4.Nf3             D37   42%    28%    30%
     ...

  With --show-games, also prints one sample game per line:
     → Suleymanli, Aydin (2679) vs Abdusattorov, Nodirbek (2780) — 1-0

HOW TO USE THE OUTPUT
---------------------
1. Run the script on the week's TWIC PGN
2. Paste the output here and tell Claude which theme you want
3. Claude filters the full PGN for that theme and selects the best 5-7 games
4. Claude annotates and builds the HTML viewer + EPUB issue
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

try:
    import chess.pgn
except ImportError:
    print("ERROR: python-chess not installed. Run: pip install python-chess")
    sys.exit(1)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def opening_key(headers: dict, by_eco: bool) -> str:
    """Return the grouping key for this game."""
    if by_eco:
        return headers.get("ECO", "?")

    opening   = headers.get("Opening", "").strip()
    variation = headers.get("Variation", "").strip()

    if not opening:
        return headers.get("ECO", "Unknown")

    # Truncate very long variation strings
    if variation and len(variation) < 60:
        return f"{opening} / {variation}"
    return opening


def result_to_outcome(result: str) -> str:
    if result == "1-0":   return "white"
    if result == "0-1":   return "black"
    if result == "1/2-1/2": return "draw"
    return "unknown"


def pct(n: int, total: int) -> str:
    if total == 0:
        return " — "
    return f"{100*n//total}%"


def best_game(games: list[dict]) -> dict:
    """Pick the most interesting game: decisive + highest avg Elo."""
    decisive = [g for g in games if g["result"] != "draw"]
    pool = decisive if decisive else games
    return max(pool, key=lambda g: g["avg_elo"])


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="List the most common opening themes in a TWIC PGN.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("pgn", help="Path to TWIC PGN file")
    parser.add_argument("--top", type=int, default=30,
                        help="How many openings to show (default 30)")
    parser.add_argument("--min-elo", type=int, default=0,
                        help="Minimum average Elo to include a game (default: all)")
    parser.add_argument("--by-eco", action="store_true",
                        help="Group by ECO code instead of opening name")
    parser.add_argument("--show-games", action="store_true",
                        help="Show one sample game per opening")
    parser.add_argument("--decisive-only", action="store_true",
                        help="Only count decisive games (1-0 or 0-1)")
    args = parser.parse_args()

    pgn_path = Path(args.pgn)
    if not pgn_path.is_file():
        print(f"ERROR: File not found: {pgn_path}")
        sys.exit(1)

    # ── Read PGN ──────────────────────────────────────────────────────────────
    openings: dict[str, dict] = defaultdict(lambda: {
        "count": 0, "white": 0, "black": 0, "draw": 0, "games": []
    })
    total_games = 0
    skipped     = 0

    with open(pgn_path, encoding="utf-8", errors="replace") as f:
        while True:
            game = chess.pgn.read_game(f)
            if game is None:
                break

            h      = game.headers
            result = h.get("Result", "*")
            if result == "*":
                skipped += 1
                continue

            outcome = result_to_outcome(result)
            if args.decisive_only and outcome == "draw":
                skipped += 1
                continue

            white_elo = int(h.get("WhiteElo", 0) or 0)
            black_elo = int(h.get("BlackElo", 0) or 0)
            avg_elo   = (white_elo + black_elo) / 2 if white_elo and black_elo else 0

            if avg_elo < args.min_elo:
                skipped += 1
                continue

            key = opening_key(h, args.by_eco)
            eco = h.get("ECO", "?")

            openings[key]["count"] += 1
            openings[key][outcome] = openings[key].get(outcome, 0) + 1
            openings[key]["eco"]   = eco   # last seen ECO for this key
            openings[key]["games"].append({
                "white":    h.get("White", "?"),
                "black":    h.get("Black", "?"),
                "white_elo": white_elo,
                "black_elo": black_elo,
                "avg_elo":  avg_elo,
                "result":   outcome,
                "date":     h.get("Date", "?"),
            })
            total_games += 1

    # ── Sort and display ───────────────────────────────────────────────────────
    ranked = sorted(openings.items(), key=lambda x: x[1]["count"], reverse=True)
    top    = ranked[:args.top]

    print(f"\nTWIC PGN  : {pgn_path.name}")
    print(f"Games read: {total_games}  |  Skipped: {skipped}")
    if args.min_elo:
        print(f"Min Elo   : {args.min_elo}")
    print()

    # Header
    name_w = 50
    print(f"{'Rank':>4}  {'Count':>5}  {'Opening / Variation':<{name_w}}  {'ECO':<5}  {'W%':>4}  {'B%':>4}  {'D%':>4}")
    print("─" * (4 + 2 + 5 + 2 + name_w + 2 + 5 + 2 + 4 + 2 + 4 + 2 + 4))

    for rank, (name, data) in enumerate(top, 1):
        count = data["count"]
        w     = data.get("white", 0)
        b     = data.get("black", 0)
        d     = data.get("draw",  0)
        eco   = data.get("eco", "?")

        # Truncate long names
        display = name if len(name) <= name_w else name[:name_w-1] + "…"

        print(f"{rank:>4}  {count:>5}  {display:<{name_w}}  {eco:<5}  "
              f"{pct(w,count):>4}  {pct(b,count):>4}  {pct(d,count):>4}")

        if args.show_games and data["games"]:
            g = best_game(data["games"])
            result_sym = {"white": "1-0", "black": "0-1", "draw": "½-½"}.get(g["result"], "?")
            elo_str = f"({g['white_elo']})" if g["white_elo"] else ""
            elo_b   = f"({g['black_elo']})" if g["black_elo"] else ""
            print(f"       → {g['white']} {elo_str} vs {g['black']} {elo_b}  {result_sym}")

    print()
    print("── Next step ───────────────────────────────────────────────────────")
    print("Paste this output and tell Claude which opening you want to feature.")
    print("Claude will filter the PGN, pick the best 5-7 games, annotate them,")
    print("and build the HTML viewer + EPUB issue.")


if __name__ == "__main__":
    main()
