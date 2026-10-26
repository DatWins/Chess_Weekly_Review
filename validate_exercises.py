#!/usr/bin/env python3
"""
Chess Weekly Review — Exercise Position Validator
==================================================
Parses all 40 exercise HTML files, extracts FEN + CORRECT plan + plan move text,
then uses Stockfish (via python-chess) to verify that the CORRECT plan corresponds
to the engine's top choice at the given position.

USAGE
-----
  # Install dependencies (once):
  pip install python-chess

  # Windows — Stockfish at default path:
  python validate_exercises.py

  # Explicit Stockfish path:
  python validate_exercises.py --stockfish "C:/path/to/stockfish.exe"

  # Skip engine (syntax / FEN check only):
  python validate_exercises.py --no-engine

  # Analysis depth (default 20):
  python validate_exercises.py --depth 20

OUTPUT
------
  PASS  transition_mg/ex01 — A matches engine top move f4 (+0.45)
  WARN  transition_mg/ex08 — A (Nd5!) chosen; engine top: Nd5 (+0.20) ✓
  FAIL  middlegame/ex03    — B chosen as correct; engine prefers A (Rxf7+, +1.80)

Exit code: 0 if all pass, 1 if any FAIL.

HOW IT WORKS
------------
Each exercise defines:
  - const FEN = '...'          — position to analyse
  - const CORRECT = 'A'        — which plan is correct
  - <span class="choice-plan"> — the human-readable move/plan text

Since the exercises use strategic "plan" descriptions (not always single UCI moves),
the validator takes a two-pronged approach:

  1. ENGINE MOVE: Stockfish top-3 moves at depth N are computed.
  2. PLAN MOVE PARSE: The correct plan's <choice-plan> text is parsed for a move
     in SAN notation (e.g. "f4", "Nd5!", "...Rxf7+"). If found, it is checked
     against the engine's top moves.
  3. FALLBACK: If no parseable move is found, the validator reports the engine's
     recommendation and flags it as NEEDS-REVIEW for manual inspection.

This catches clear tactical errors (as in ex08 where Nc2+ loses to Rxc2) while
acknowledging that strategic plan exercises may have multiple reasonable options.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

# ──────────────────────────────────────────────────────────────────────────────
# Optional imports — fail gracefully if python-chess is not installed
# ──────────────────────────────────────────────────────────────────────────────
try:
    import chess
    import chess.engine
    HAS_CHESS = True
except ImportError:
    HAS_CHESS = False

# ──────────────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).parent
EXERCISES_DIR = REPO_ROOT / "issues" / "training" / "week1"

PHASES = [
    ("transition_mg", 10),
    ("middlegame",    10),
    ("transition_eg", 10),
    ("endgame",       10),
]

# Stockfish search order (Windows + Unix paths)
DEFAULT_STOCKFISH_PATHS = [
    r"C:\Users\%USERNAME%\Downloads\stockfish\stockfish.exe",
    r"C:\Program Files\Stockfish\stockfish.exe",
    r"C:\stockfish\stockfish.exe",
    "/opt/homebrew/bin/stockfish",
    "/usr/local/bin/stockfish",
    "/usr/bin/stockfish",
]

ANALYSIS_DEPTH = 20
MULTIPV        = 3          # top N moves to fetch

# ──────────────────────────────────────────────────────────────────────────────
# HTML parsing
# ──────────────────────────────────────────────────────────────────────────────

_FEN_RE     = re.compile(r"const FEN\s*=\s*'([^']+)'")
_CORRECT_RE = re.compile(r"const CORRECT\s*=\s*'([ABC])'")
_TITLE_RE   = re.compile(r"<title>([^<]+)</title>")
_PLAN_RE    = re.compile(
    r'<span class="choice-letter">([ABC])</span>\s*'
    r'<span class="choice-plan">([^<]+)</span>',
    re.DOTALL,
)


def parse_exercise(path: Path) -> dict | None:
    """Extract FEN, correct answer, and plan texts from an exercise HTML file."""
    html = path.read_text(encoding="utf-8")

    fen_m     = _FEN_RE.search(html)
    correct_m = _CORRECT_RE.search(html)
    title_m   = _TITLE_RE.search(html)

    if not fen_m or not correct_m:
        return None  # file structure unexpected

    plans: dict[str, str] = {}
    for letter, plan_text in _PLAN_RE.findall(html):
        plans[letter] = plan_text.strip()

    return {
        "fen":     fen_m.group(1),
        "correct": correct_m.group(1),
        "title":   title_m.group(1).split("·")[0].strip() if title_m else path.stem,
        "plans":   plans,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Move extraction from plan text
# ──────────────────────────────────────────────────────────────────────────────

# SAN patterns: piece moves, pawn captures, castling, with optional +/# and !/?
_SAN_CANDIDATES = re.compile(
    r"""
    (?:\.\.\.)?                              # optional "..." (Black to move)
    (?:
        O-O-O | O-O                          # castling
        | [KQRBN][a-h1-8]?[a-h1-8]?x?[a-h][1-8]   # piece move
        | [a-h](?:x[a-h])?[1-8](?:=[QRBN])?        # pawn push/capture/promo
    )
    [+#!?]{0,2}
    """,
    re.VERBOSE,
)


def extract_san(plan_text: str, board: "chess.Board | None") -> str | None:
    """
    Try to find a legal SAN move embedded in a plan description.
    Returns the first match that is legal in the given position, or None.
    """
    if board is None:
        # No board available — just return first candidate
        m = _SAN_CANDIDATES.search(plan_text)
        return m.group(0).lstrip(".") if m else None

    for candidate in _SAN_CANDIDATES.finditer(plan_text):
        raw = candidate.group(0).lstrip(".")
        # Strip decorations for parsing
        san = raw.rstrip("!?")
        try:
            move = board.parse_san(san)
            if move in board.legal_moves:
                return raw   # keep original including ! / ?
        except (ValueError, chess.IllegalMoveError, chess.InvalidMoveError,
                chess.AmbiguousMoveError):
            pass
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Engine analysis
# ──────────────────────────────────────────────────────────────────────────────

def find_stockfish(explicit_path: str | None) -> str | None:
    """Return path to Stockfish binary, or None if not found."""
    if explicit_path:
        if Path(explicit_path).is_file():
            return explicit_path
        # Windows env var expansion
        expanded = str(Path(explicit_path).expanduser())
        if Path(expanded).is_file():
            return expanded
        print(f"  [!] Stockfish not found at: {explicit_path}", file=sys.stderr)
        return None

    which = shutil.which("stockfish")
    if which:
        return which

    for p in DEFAULT_STOCKFISH_PATHS:
        expanded = str(Path(p).expanduser())
        if Path(expanded).is_file():
            return expanded

    return None


def analyse_position(
    engine: "chess.engine.SimpleEngine",
    fen: str,
    depth: int,
    multipv: int,
) -> list[dict]:
    """Return top `multipv` lines for position. Each dict: uci, san, cp, mate."""
    board = chess.Board(fen)
    raw = engine.analyse(board, chess.engine.Limit(depth=depth), multipv=multipv)
    if isinstance(raw, dict):
        raw = [raw]

    results = []
    for info in raw:
        score = info["score"].pov(board.turn)
        pv = info.get("pv", [])
        if not pv:
            continue
        best = pv[0]
        try:
            san = board.san(best)
        except Exception:
            san = best.uci()

        results.append({
            "uci":  best.uci(),
            "san":  san,
            "cp":   score.score(),       # None if mate
            "mate": score.mate(),        # None if cp
        })
    return results


def score_str(line: dict) -> str:
    if line["mate"] is not None:
        return f"M{line['mate']}"
    cp = line["cp"]
    return f"{cp/100:+.2f}" if cp is not None else "?"


# ──────────────────────────────────────────────────────────────────────────────
# Comparison logic
# ──────────────────────────────────────────────────────────────────────────────

def sans_match(a: str, b: str) -> bool:
    """Fuzzy SAN comparison: strip check/mate/decoration and compare."""
    def clean(s: str) -> str:
        return s.rstrip("+#!?").replace("x", "").replace("-", "").lower()
    return clean(a) == clean(b)


# ──────────────────────────────────────────────────────────────────────────────
# Main validation loop
# ──────────────────────────────────────────────────────────────────────────────

def validate(stockfish_path: str | None, depth: int, no_engine: bool,
             only_phase: str | None = None, only_exercise: int | None = None) -> int:
    """
    Run validation. Returns number of FAILs (0 = all good).
    """
    engine: "chess.engine.SimpleEngine | None" = None

    if not no_engine:
        if not HAS_CHESS:
            print("ERROR: python-chess not installed. Run: pip install python-chess")
            print("       Or re-run with --no-engine for syntax-only checking.")
            return 1

        sf_path = find_stockfish(stockfish_path)
        if sf_path is None:
            print("ERROR: Stockfish not found.")
            print("  • Install from https://stockfishchess.org/download/")
            print("  • Or pass --stockfish <path>")
            print("  • Or use --no-engine for syntax-only checking.")
            return 1

        print(f"Stockfish : {sf_path}")
        print(f"Depth     : {depth}")
        engine = chess.engine.SimpleEngine.popen_uci(sf_path)
    else:
        print("Mode      : --no-engine (FEN/structure check only)")

    print()

    results = {"PASS": 0, "WARN": 0, "FAIL": 0, "SKIP": 0, "REVIEW": 0}
    failures: list[str] = []

    phases = [(p, c) for p, c in PHASES if only_phase is None or p == only_phase]

    try:
        for phase_dir, count in phases:
            ex_range = [only_exercise] if only_exercise else list(range(1, count + 1))
            for ex_num in ex_range:
                path = EXERCISES_DIR / phase_dir / f"ex{ex_num:02d}.html"
                label = f"{phase_dir}/ex{ex_num:02d}"

                if not path.exists():
                    print(f"  SKIP  {label} — file not found")
                    results["SKIP"] += 1
                    continue

                data = parse_exercise(path)
                if data is None:
                    print(f"  SKIP  {label} — could not parse")
                    results["SKIP"] += 1
                    continue

                fen     = data["fen"]
                correct = data["correct"]
                plans   = data["plans"]
                title   = data["title"]

                # ── FEN legality check ────────────────────────────────────────
                if HAS_CHESS:
                    try:
                        board = chess.Board(fen)
                    except ValueError as e:
                        msg = f"  FAIL  {label} — invalid FEN: {e}"
                        print(msg)
                        failures.append(msg)
                        results["FAIL"] += 1
                        continue
                else:
                    board = None

                correct_plan_text = plans.get(correct, "")

                # ── No-engine mode ────────────────────────────────────────────
                if no_engine or engine is None:
                    status = "FEN-OK"
                    print(f"  {status:6s}  {label} — {title}")
                    print(f"           Correct: Plan {correct} — {correct_plan_text}")
                    results["PASS"] += 1
                    continue

                # ── Engine analysis ───────────────────────────────────────────
                try:
                    top_moves = analyse_position(engine, fen, depth, MULTIPV)
                except Exception as e:
                    # Engine may have crashed — restart once and retry
                    try:
                        engine.quit()
                    except Exception:
                        pass
                    try:
                        engine = chess.engine.SimpleEngine.popen_uci(sf_path)
                        top_moves = analyse_position(engine, fen, depth, MULTIPV)
                    except Exception as e2:
                        print(f"  SKIP  {label} — engine error: {e2}")
                        results["SKIP"] += 1
                        continue

                if not top_moves:
                    print(f"  SKIP  {label} — engine returned no moves")
                    results["SKIP"] += 1
                    continue

                best_engine = top_moves[0]

                # ── Try to extract a move from the correct plan ───────────────
                correct_san = extract_san(correct_plan_text, board)

                # ── Compare ───────────────────────────────────────────────────
                engine_top_sans = [m["san"] for m in top_moves]
                engine_top_str  = ", ".join(
                    f"{m['san']} ({score_str(m)})" for m in top_moves
                )

                if correct_san is None:
                    # Strategic/positional plan — can't parse a single move
                    # Report engine top move for manual review
                    print(
                        f"  REVIEW {label} — {title}\n"
                        f"           Plan {correct}: \"{correct_plan_text}\"\n"
                        f"           Engine top: {engine_top_str}\n"
                        f"           (No single move found in plan — verify manually)"
                    )
                    results["REVIEW"] += 1
                    continue

                # Check if the correct plan's move appears in engine's top moves
                match = any(sans_match(correct_san, s) for s in engine_top_sans)

                if match:
                    matched_line = next(m for m in top_moves if sans_match(correct_san, m["san"]))
                    print(
                        f"  PASS  {label} — {title}\n"
                        f"           Plan {correct}: {correct_san} "
                        f"({score_str(matched_line)}) ✓ in engine top {MULTIPV}"
                    )
                    results["PASS"] += 1
                else:
                    # FAIL — the "correct" plan's move is not in engine's top choices
                    cp_threshold = 150  # centipawns worse than best = likely wrong
                    best_cp = best_engine["cp"]

                    # Try to score the correct move against the position
                    try:
                        b2 = chess.Board(fen)
                        move_obj = b2.parse_san(correct_san.rstrip("!?"))
                        b2.push(move_obj)
                        after_info = engine.analyse(b2, chess.engine.Limit(depth=depth-4))
                        after_score = after_info["score"].pov(b2.turn)
                        after_cp = after_score.score()
                        # From the mover's side: -after_cp is what they got
                        correct_cp = -after_cp if after_cp is not None else None
                    except Exception:
                        correct_cp = None

                    severity = "FAIL"
                    if correct_cp is not None and best_cp is not None:
                        cp_loss = best_cp - correct_cp
                        if cp_loss < cp_threshold:
                            severity = "WARN"   # close enough — near-equal alternatives

                    line = (
                        f"  {severity}  {label} — {title}\n"
                        f"           Plan {correct} (correct): {correct_san}"
                        + (f" ({correct_cp/100:+.2f})" if correct_cp else "")
                        + f"\n"
                        f"           Engine top {MULTIPV}: {engine_top_str}\n"
                        f"           {'!! Possible wrong answer — verify position' if severity == 'FAIL' else '(near-equal — OK)'}"
                    )
                    print(line)
                    results[severity] += 1
                    if severity == "FAIL":
                        failures.append(line)

    finally:
        if engine is not None:
            try:
                engine.quit()
            except Exception:
                pass

    # ── Summary ───────────────────────────────────────────────────────────────
    print()
    print("=" * 60)
    print(f"Results: {results['PASS']} PASS  |  {results['WARN']} WARN  |  "
          f"{results['FAIL']} FAIL  |  {results['REVIEW']} REVIEW  |  "
          f"{results['SKIP']} SKIP")

    if failures:
        print()
        print("FAILURES requiring attention:")
        for f in failures:
            print(f)

    return results["FAIL"]


# ──────────────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate Chess Weekly Review exercise positions with Stockfish.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--stockfish", metavar="PATH",
        help="Path to Stockfish binary (auto-detected if omitted)",
    )
    parser.add_argument(
        "--depth", type=int, default=ANALYSIS_DEPTH,
        help=f"Stockfish analysis depth (default {ANALYSIS_DEPTH})",
    )
    parser.add_argument(
        "--no-engine", action="store_true",
        help="Skip Stockfish analysis — only check FEN validity and file structure",
    )
    parser.add_argument(
        "--phase", choices=["transition_mg", "middlegame", "transition_eg", "endgame"],
        help="Only validate exercises in this phase",
    )
    parser.add_argument(
        "--exercise", type=int, metavar="N",
        help="Only validate exercise N (within the specified --phase)",
    )
    args = parser.parse_args()

    fail_count = validate(
        args.stockfish, args.depth, args.no_engine,
        only_phase=args.phase,
        only_exercise=args.exercise,
    )
    sys.exit(1 if fail_count else 0)


if __name__ == "__main__":
    main()
