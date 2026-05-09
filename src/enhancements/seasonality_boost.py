"""
Seasonality soft-boost — standalone enhancement layer on top of locked Setup A.

Does NOT modify engine.py, setup_a.py, or any existing backtest code.

What it provides:
  1. score(sector, month)      → 0–100 float  (beat-Nifty % for that sector-month)
  2. label(sector, month)      → human string  ("Strong" / "Neutral" / "Weak" / "Very Weak")
  3. rank_signals(signals)     → list sorted by season_score descending
  4. should_skip(sector, month)→ True if season_score < SKIP_THRESHOLD (Very Weak)
  5. enrich_trades(trades_df)  → adds season_score + season_label columns to a trades DataFrame
  6. backtest_with_filter(...)  → re-runs metrics on trades_final.csv skipping Very Weak months
     (reads the already-computed trade log — no re-simulation needed)

Thresholds (from seasonality analysis on 336 locked Setup A trades):
  Strong    ≥ 65   → 66.7% WR, +0.821R avg  (27 trades)
  Neutral   50–64  → 44.3% WR, +0.242R avg  (174 trades)
  Weak      35–49  → 54.1% WR, +0.521R avg  (109 trades)  ← surprisingly good, do NOT skip
  Very Weak  < 35  → 36.4% WR, -0.016R avg  ( 11 trades)  ← losing, candidate to skip
"""

from __future__ import annotations
import pandas as pd
from pathlib import Path

# ── Thresholds ──────────────────────────────────────────────────────────────
STRONG_THRESHOLD    = 65.0
NEUTRAL_THRESHOLD   = 50.0
WEAK_THRESHOLD      = 35.0
SKIP_THRESHOLD      = 35.0   # Very Weak: skip or deprioritize

_SEASONALITY_PATH = Path(__file__).parent.parent.parent / "data" / "sector_seasonality.csv"

_cache: pd.DataFrame | None = None


def _load() -> pd.DataFrame:
    global _cache
    if _cache is None:
        if not _SEASONALITY_PATH.exists():
            _cache = pd.DataFrame(columns=["sector", "month", "beat_nifty_pct"])
        else:
            _cache = pd.read_csv(_SEASONALITY_PATH)
    return _cache


# ── Core lookup ──────────────────────────────────────────────────────────────

def score(sector: str, month: int) -> float:
    """Return beat-Nifty % for this sector-month. 50 = neutral (no data → neutral)."""
    df = _load()
    if df.empty:
        return 50.0
    row = df[(df["sector"] == sector) & (df["month"] == month)]
    if row.empty:
        return 50.0
    return float(row["beat_nifty_pct"].iloc[0])


def label(sector: str, month: int) -> str:
    """Return human-readable tier for this sector-month."""
    s = score(sector, month)
    if s >= STRONG_THRESHOLD:
        return "Strong"
    if s >= NEUTRAL_THRESHOLD:
        return "Neutral"
    if s >= WEAK_THRESHOLD:
        return "Weak"
    return "Very Weak"


def should_skip(sector: str, month: int) -> bool:
    """True if this sector-month is historically a losing combination."""
    return score(sector, month) < SKIP_THRESHOLD


# ── Signal ranking (for alerter use) ────────────────────────────────────────

def rank_signals(signals: list[dict]) -> list[dict]:
    """
    Sort a list of signal dicts by season_score descending.

    Each signal dict must have at least:
      "sector" (str) and "entry_date" or "month" (int or date with .month attribute).

    Adds "season_score" and "season_label" keys in-place, then returns sorted list.
    """
    for sig in signals:
        sector = sig.get("sector", "Unknown")
        month  = sig.get("month") or pd.Timestamp(sig.get("entry_date", "2000-01-01")).month
        sig["season_score"] = score(sector, month)
        sig["season_label"] = label(sector, month)
    return sorted(signals, key=lambda s: s["season_score"], reverse=True)


# ── Backtest enrichment ──────────────────────────────────────────────────────

def enrich_trades(trades: pd.DataFrame) -> pd.DataFrame:
    """
    Add season_score and season_label columns to a trades DataFrame.

    Expects columns: "sector", "entry_date".
    Returns a new DataFrame (original untouched).
    """
    t = trades.copy()
    t["entry_date"] = pd.to_datetime(t["entry_date"])
    t["season_score"] = t.apply(
        lambda r: score(r["sector"], r["entry_date"].month), axis=1
    )
    t["season_label"] = t.apply(
        lambda r: label(r["sector"], r["entry_date"].month), axis=1
    )
    return t


# ── Enhancement backtest (skip Very Weak) ────────────────────────────────────

def backtest_with_filter(
    trades_path: str | Path | None = None,
    skip_very_weak: bool = True,
    verbose: bool = True,
) -> dict:
    """
    Load the locked Setup A trade log, apply seasonality filter, recompute metrics.

    Does NOT re-simulate. Reads trades_final.csv and filters rows only.

    Returns dict with keys: original_metrics, filtered_metrics, removed_trades.
    """
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from backtest.metrics import compute_metrics, print_summary

    if trades_path is None:
        trades_path = Path(__file__).parent.parent.parent / "results" / "trades_final.csv"

    trades = pd.read_csv(trades_path)
    trades = enrich_trades(trades)

    orig_m = compute_metrics(trades)

    if skip_very_weak:
        mask    = trades["season_score"] >= SKIP_THRESHOLD
        removed = trades[~mask].copy()
        filtered = trades[mask].copy()
    else:
        filtered = trades.copy()
        removed  = pd.DataFrame()

    filt_m = compute_metrics(filtered)

    if verbose:
        print("\n" + "=" * 60)
        print("ORIGINAL (all 336 trades):")
        print("=" * 60)
        print_summary(orig_m)

        print("\n" + "=" * 60)
        print(f"ENHANCED (skip Very Weak <{SKIP_THRESHOLD:.0f}%): "
              f"{len(filtered)} trades, removed {len(removed)}")
        print("=" * 60)
        print_summary(filt_m)

        if not removed.empty:
            print(f"\nRemoved trades ({len(removed)}):")
            print(removed[["symbol", "sector", "entry_date", "season_score",
                            "season_label", "r_multiple", "win"]].to_string(index=False))

    return {
        "original_metrics": orig_m,
        "filtered_metrics": filt_m,
        "removed_trades":   removed,
        "all_trades":       trades,
    }


# ── Calendar summary ──────────────────────────────────────────────────────────

def print_season_calendar(sectors: list[str] | None = None) -> None:
    """Print a month × sector grid of season labels for quick reference."""
    df = _load()
    if df.empty:
        print("No seasonality data found.")
        return

    if sectors is None:
        sectors = sorted(df["sector"].unique())

    MONTH_NAMES = ["Jan","Feb","Mar","Apr","May","Jun",
                   "Jul","Aug","Sep","Oct","Nov","Dec"]
    ICONS = {"Strong": "▲", "Neutral": "→", "Weak": "▽", "Very Weak": "✗"}

    col_w = max(len(s) for s in sectors) + 2
    header = f"{'Month':>5}  " + "  ".join(f"{s:<{col_w}}" for s in sectors)
    print(header)
    print("-" * len(header))

    for m in range(1, 13):
        row = f"{MONTH_NAMES[m-1]:>5}  "
        for s in sectors:
            lbl = label(s, m)
            icon = ICONS[lbl]
            sc   = score(s, m)
            cell = f"{icon}{sc:>4.0f}%"
            row += f"{cell:<{col_w}}  "
        print(row)


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Seasonality enhancement layer")
    parser.add_argument("--backtest", action="store_true",
                        help="Re-run metrics on trades_final.csv with Very Weak filter")
    parser.add_argument("--calendar", action="store_true",
                        help="Print season calendar for whitelisted sectors")
    parser.add_argument("--sector", type=str, help="Score a specific sector")
    parser.add_argument("--month",  type=int, help="Month number (1-12)")
    args = parser.parse_args()

    if args.backtest:
        backtest_with_filter(verbose=True)

    if args.calendar:
        WHITELIST = [
            "Utilities", "FMCG", "Pharma", "Cement", "Consumer Durables",
            "IT", "Real Estate", "Electronics", "Healthcare", "Consumer",
            "Insurance", "Consumer Electricals", "Mining", "Capital Goods",
            "Auto Ancillary", "Energy",
        ]
        print_season_calendar(sectors=WHITELIST)

    if args.sector and args.month:
        s = score(args.sector, args.month)
        l = label(args.sector, args.month)
        skip = should_skip(args.sector, args.month)
        print(f"{args.sector} | Month {args.month}: {s:.1f}% → {l}"
              + (" [SKIP]" if skip else ""))
