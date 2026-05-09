"""
Strategy C — Entry point.

Usage:
  python3 -m src.strategy_c.run --scan          # start live scanner
  python3 -m src.strategy_c.run --screen        # run today's pre-filter and print candidates
  python3 -m src.strategy_c.run --test SYMBOL   # test detection on one stock right now
  python3 -m src.strategy_c.run --alert-test    # print a sample Telegram message
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def cmd_scan(verbose: bool):
    from src.strategy_c.scanner import Scanner
    Scanner(verbose=verbose).run()


def cmd_screen():
    from src.strategy_c.daily_filter import screen_universe
    candidates = screen_universe(verbose=True)
    print(f"\nTotal candidates: {len(candidates)}")


def cmd_test(symbol: str):
    """Fetch intraday data for one symbol and run detection — useful for debugging."""
    from src.strategy_c.intraday_setup import fetch_intraday, detect
    from src.strategy_c.alerts import send

    print(f"Fetching intraday data for {symbol}...")
    df = fetch_intraday(symbol)
    if df is None:
        print("No data returned.")
        return

    print(f"Got {len(df)} candles. Latest: {df.index[-1]}")
    print(df.tail(5).to_string())

    # Minimal meta for testing
    meta = {
        "symbol": symbol, "sector": "Test", "season_score": 60.0,
        "adx": 30.0, "rs_3m_pct": 15.0,
    }
    signal = detect(df, meta)
    if signal is None:
        print("\nNo setup detected right now.")
    else:
        print("\nSetup DETECTED:")
        send(signal, dry_run=True)


def cmd_alert_test():
    """Print a sample alert message without sending."""
    from src.strategy_c.alerts import send

    sample = {
        "symbol": "RELIANCE.NS", "sector": "Energy", "season_score": 57.0,
        "signal_time": "2026-05-09 10:30:00+05:30",
        "entry_low": 2842.50, "entry_high": 2885.14, "entry_valid_min": 45,
        "stop": 2795.30, "swing_low": 2802.00, "target": 2937.10,
        "risk_per_share": 47.20, "risk_pct": 1.66, "rr_ratio": 2.0,
        "shares": 21, "capital_required": 59693.0, "actual_risk_inr": 991.0,
        "ema20_15m": 2831.40, "rsi14_15m": 48.3, "adx_daily": 31.0,
        "rs_3m_pct": 14.2, "pullback_candles": 4, "pullback_high": 2840.00,
    }
    send(sample, dry_run=True)


def cmd_backtest(start: str, end: str, verbose: bool, save: bool):
    from src.strategy_c.backtest import run
    from src.strategy_c.report import print_report
    import os

    print(f"Running Strategy C backtest  {start} → {end} ...")
    trades = run(start=start, end=end, verbose=verbose)

    if trades.empty:
        print("No trades generated. Check params or data.")
        return

    print_report(trades, title=f"Strategy C  [{start} – {end}]")

    if save:
        out = f"results/strategy_c_trades_{start[:4]}_{end[:4]}.csv"
        os.makedirs("results", exist_ok=True)
        trades.to_csv(out, index=False)
        print(f"Trades saved to {out}")


def cmd_backtest_cooper(start: str, end: str, verbose: bool, save: bool):
    from src.strategy_c.backtest_cooper import run
    from src.strategy_c.report import print_report
    import os

    print(f"Running Cooper 5-Day Method backtest  {start} → {end} ...")
    trades = run(start=start, end=end, verbose=verbose)

    if trades.empty:
        print("No trades generated.")
        return

    print_report(trades, title=f"Cooper 5-Day Method  [{start} – {end}]")

    if save:
        out = f"results/strategy_cooper_trades_{start[:4]}_{end[:4]}.csv"
        os.makedirs("results", exist_ok=True)
        trades.to_csv(out, index=False)
        print(f"Trades saved to {out}")


def cmd_backtest_intraday(verbose: bool, save: bool):
    from src.strategy_c.backtest_intraday import run
    from src.strategy_c.report import print_report
    import os

    print("Running Strategy C intraday backtest (1-hour candles, ~3 years)...")
    trades = run(verbose=verbose)

    if trades.empty:
        print("No trades generated. Check that hourly data is downloaded.")
        return

    print_report(trades, title="Strategy C — Intraday 1h Backtest")

    if save:
        out = "results/strategy_c_intraday_trades.csv"
        os.makedirs("results", exist_ok=True)
        trades.to_csv(out, index=False)
        print(f"Trades saved to {out}")


def main():
    parser = argparse.ArgumentParser(
        description="Strategy C — Intraday Momentum Pullback Scanner"
    )
    parser.add_argument("--scan",               action="store_true", help="Start live scanner")
    parser.add_argument("--screen",             action="store_true", help="Run daily pre-filter only")
    parser.add_argument("--backtest",           action="store_true", help="Run EMA pullback daily backtest (2015–2024)")
    parser.add_argument("--backtest-intraday",  action="store_true", help="Run Path A: EMA pullback 1h intraday (~3yr)")
    parser.add_argument("--backtest-cooper",    action="store_true", help="Run Path B: Cooper 5-Day daily backtest")
    parser.add_argument("--start",              default="2015-01-01", help="Backtest start date")
    parser.add_argument("--end",                default="2024-12-31", help="Backtest end date")
    parser.add_argument("--save",               action="store_true",  help="Save trades to CSV")
    parser.add_argument("--test",               metavar="SYMBOL",     help="Test detection on one stock")
    parser.add_argument("--alert-test",         action="store_true",  help="Print sample Telegram alert")
    parser.add_argument("--verbose",            action="store_true",  help="Verbose output")
    args = parser.parse_args()

    if args.scan:
        cmd_scan(verbose=args.verbose)
    elif args.screen:
        cmd_screen()
    elif args.backtest:
        cmd_backtest(args.start, args.end, args.verbose, args.save)
    elif getattr(args, "backtest_intraday", False):
        cmd_backtest_intraday(args.verbose, args.save)
    elif getattr(args, "backtest_cooper", False):
        cmd_backtest_cooper(args.start, args.end, args.verbose, args.save)
    elif args.test:
        cmd_test(args.test)
    elif args.alert_test:
        cmd_alert_test()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
