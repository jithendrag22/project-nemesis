"""
Project Nemesis — Backtest Runner
Usage:
    python src/main.py                    # default params, full period
    python src/main.py --sweep            # parameter sweep
    python src/main.py --download         # (re-)download price data first
    python src/main.py --walk-forward     # train/test split
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backtest.engine  import run_backtest, DEFAULT_PARAMS
from backtest.metrics import compute_metrics, print_summary
import pandas as pd


# ── Walk-forward periods ──────────────────────────────────────────────────────
TRAIN_START = "2015-01-01"
TRAIN_END   = "2020-12-31"
TEST_START  = "2021-01-01"
TEST_END    = "2024-12-31"
FULL_START  = "2015-01-01"
FULL_END    = "2024-12-31"


def save_results(trades: pd.DataFrame, label: str) -> None:
    out_dir = Path(__file__).parent.parent / "results"
    out_dir.mkdir(exist_ok=True)
    path = out_dir / f"trades_{label}.csv"
    trades.to_csv(path, index=False)
    print(f"  Trades saved → {path}")


def run_sweep() -> None:
    """Grid search over key parameters and print a comparison table."""
    import itertools

    param_grid = {
        "market_filter_version": ["A", "B", "C"],
        "vol_ratio_min":         [1.2, 1.5, 2.0],
        "base_depth_pct":        [6.0, 8.0, 10.0],
        "prior_advance_pct":     [10.0, 15.0, 20.0],
    }

    keys   = list(param_grid.keys())
    combos = list(itertools.product(*param_grid.values()))
    print(f"\nRunning {len(combos)} parameter combinations …\n")

    rows = []
    for i, combo in enumerate(combos, 1):
        params = dict(zip(keys, combo))
        print(f"  [{i}/{len(combos)}] {params}", end=" … ", flush=True)
        trades = run_backtest(params=params, start=FULL_START, end=FULL_END)
        if trades.empty:
            print("no trades")
            continue
        m = compute_metrics(trades)
        rows.append({
            **params,
            "trades":          m["total_trades"],
            "win_rate":        m["win_rate_pct"],
            "expectancy_r":    m["expectancy_r"],
            "sqn":             m["sqn"],
            "total_pnl":       m["total_pnl_inr"],
            "profit_factor":   m["profit_factor"],
            "pct_pos_months":  m["pct_positive_months"],
            "max_consec_red":  m["max_consec_negative"],
            "max_drawdown":    m["max_drawdown_inr"],
        })
        print(f"WR={m['win_rate_pct']}% | E={m['expectancy_r']}R | SQN={m['sqn']}")

    df = pd.DataFrame(rows)
    df = df.sort_values("expectancy_r", ascending=False)

    out_dir = Path(__file__).parent.parent / "results"
    out_dir.mkdir(exist_ok=True)
    sweep_path = out_dir / "parameter_sweep.csv"
    df.to_csv(sweep_path, index=False)

    print(f"\n{'─'*90}")
    print(f"  TOP 10 COMBINATIONS BY EXPECTANCY")
    print(f"{'─'*90}")
    print(df.head(10).to_string(index=False))
    print(f"\nFull sweep saved → {sweep_path}")


def run_walk_forward() -> None:
    """Run train period, apply best params to test period."""
    print("\n── WALK-FORWARD VALIDATION ──────────────────────────────────────────\n")

    print(f"[1/2] Training period: {TRAIN_START} → {TRAIN_END}")
    train_trades = run_backtest(start=TRAIN_START, end=TRAIN_END, verbose=False)
    if train_trades.empty:
        print("  No trades in training period.")
        return
    train_m = compute_metrics(train_trades)
    print_summary(train_m)
    save_results(train_trades, "train")

    print(f"\n[2/2] Test period (unseen): {TEST_START} → {TEST_END}")
    test_trades = run_backtest(start=TEST_START, end=TEST_END, verbose=False)
    if test_trades.empty:
        print("  No trades in test period.")
        return
    test_m = compute_metrics(test_trades)
    print_summary(test_m)
    save_results(test_trades, "test")

    print("\n── WALK-FORWARD COMPARISON ─────────────────────────────────────────")
    print(f"  {'Metric':<28} {'Train':>12} {'Test':>12}")
    print(f"  {'─'*28} {'─'*12} {'─'*12}")
    metrics_to_compare = [
        ("win_rate_pct",       "Win rate %"),
        ("expectancy_r",       "Expectancy (R)"),
        ("sqn",                "SQN"),
        ("profit_factor",      "Profit factor"),
        ("pct_positive_months","% positive months"),
        ("max_consec_negative","Max consec red months"),
        ("max_drawdown_inr",   "Max drawdown (₹)"),
        ("total_pnl_inr",      "Total P&L (₹)"),
    ]
    for key, label in metrics_to_compare:
        tv = train_m.get(key, "—")
        xv = test_m.get(key, "—")
        print(f"  {label:<28} {str(tv):>12} {str(xv):>12}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Project Nemesis Backtest")
    parser.add_argument("--download",     action="store_true", help="Download/refresh price data")
    parser.add_argument("--sweep",        action="store_true", help="Run parameter sweep")
    parser.add_argument("--walk-forward", action="store_true", help="Run walk-forward validation")
    parser.add_argument("--start",        default=FULL_START,  help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end",          default=FULL_END,    help="End date (YYYY-MM-DD)")
    parser.add_argument("--verbose",      action="store_true", help="Print each signal")
    args = parser.parse_args()

    if args.download:
        print("Downloading price data …")
        from data.downloader import download_all, download_nifty
        download_nifty()
        download_all()
        print("Download complete.\n")

    if args.sweep:
        run_sweep()
        return

    if args.walk_forward:
        run_walk_forward()
        return

    # ── Default: run full backtest with default params ────────────────────────
    print(f"\nRunning backtest: {args.start} → {args.end}")
    print(f"Parameters: {DEFAULT_PARAMS}\n")

    trades = run_backtest(
        params=None,
        start=args.start,
        end=args.end,
        verbose=args.verbose,
    )

    if trades.empty:
        print("No trades generated. Check data and parameters.")
        sys.exit(1)

    m = compute_metrics(trades)
    print_summary(m)
    save_results(trades, "full")


if __name__ == "__main__":
    main()
