"""
Gap Fade V2 — Institutional Backtest Engine
============================================
Upgraded strategy with first-candle confirmation, dynamic stops,
partial profit taking, and trailing exits.

Strategy Logic:
1. Stock gaps DOWN 3-7% at open (LONG only)
2. Wait for first candle (5-min or 1-hour) to close
3. ONLY enter if first candle is GREEN (buyers stepping in)
4. Entry = break above first candle HIGH
5. Stop = first candle LOW (Opening Range low)
6. Target 1 = 1R (partial exit 50%)
7. Target 2 = trail remaining with candle-low trailing stop
8. Hard exit at last candle (3:15 PM)
"""

import pandas as pd
import numpy as np
from pathlib import Path
from dataclasses import dataclass
from typing import Literal

# ── Paths ──────────────────────────────────────────────────────────────
PROJECT_DIR = Path(__file__).parent.parent.parent
INTRADAY_1H_DIR = PROJECT_DIR / "data" / "intraday_1h"
INTRADAY_5M_DIR = Path(__file__).parent / "intraday_5m"
RESULTS_DIR = Path(__file__).parent / "backtest_results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class TradeResultV2:
    date: str
    symbol: str
    gap_pct: float
    entry_price: float
    sl_price: float           # OR low
    target1_price: float      # 1R
    target2_price: float      # 2R
    risk_pct: float           # SL distance as %
    first_candle_green: bool
    entry_triggered: bool
    outcome: str              # WIN_1R, WIN_2R, WIN_TRAIL, LOSS, FLAT, NO_SIGNAL, NO_ENTRY
    exit_price: float
    pnl_pct: float
    pnl_rs: float
    exit_candle: int
    partial_pnl_rs: float     # P&L from the partial (50%) exit at 1R
    trail_pnl_rs: float       # P&L from the trailing (50%) portion
    max_favorable: float      # Maximum favorable excursion from entry (%)
    max_adverse: float        # Maximum adverse excursion from entry (%)


@dataclass
class ConfigV2:
    gap_min_pct: float = 3.0
    gap_max_pct: float = 7.0
    partial_exit_pct: float = 0.5    # Exit 50% at 1R
    use_trailing_stop: bool = True   # Trail remaining 50%
    capital: float = 100000
    data_source: str = "5m"          # "1h" or "5m"
    market_filter: bool = False      # Skip if Nifty down >1.5%
    skip_first_n_candles: int = 1    # Wait N candles before entering (1 = wait 1st candle)


def simulate_trade_v2(
    day_candles: pd.DataFrame,
    gap_pct: float,
    config: ConfigV2,
    capital: float = 100000,
) -> TradeResultV2 | None:
    """
    Simulate the V2 institutional trade on a single day.
    """
    if len(day_candles) < config.skip_first_n_candles + 2:
        return None

    open_price = day_candles.iloc[0]["Open"]
    first_candle = day_candles.iloc[config.skip_first_n_candles - 1]

    # ── Step 1: Check first candle direction ──
    first_candle_green = first_candle["Close"] >= first_candle["Open"]
    fc_high = first_candle["High"]
    fc_low = first_candle["Low"]

    if not first_candle_green:
        return TradeResultV2(
            date="", symbol="", gap_pct=gap_pct,
            entry_price=0, sl_price=0, target1_price=0, target2_price=0,
            risk_pct=0, first_candle_green=False, entry_triggered=False,
            outcome="NO_SIGNAL", exit_price=0, pnl_pct=0, pnl_rs=0,
            exit_candle=0, partial_pnl_rs=0, trail_pnl_rs=0,
            max_favorable=0, max_adverse=0,
        )

    # ── Step 2: Define trade levels ──
    entry_price = fc_high
    sl_price = fc_low
    risk = entry_price - sl_price

    if risk <= 0 or entry_price <= 0:
        return None

    risk_pct = (risk / entry_price) * 100
    target1_price = entry_price + risk        # 1R
    target2_price = entry_price + risk * 2    # 2R

    shares = int(capital / entry_price)
    if shares <= 0:
        return None

    half_shares = shares // 2
    remaining_shares = shares - half_shares

    # ── Step 3: Walk through candles after the first ──
    entry_triggered = False
    position_phase = "WAITING"   # WAITING → FULL → PARTIAL → DONE
    partial_pnl = 0.0
    trail_stop = sl_price
    trail_pnl = 0.0
    exit_price = 0.0
    exit_candle = 0
    max_fav = 0.0
    max_adv = 0.0

    remaining_candles = day_candles.iloc[config.skip_first_n_candles:]

    for idx, (ts, candle) in enumerate(remaining_candles.iterrows()):
        c_high = candle["High"]
        c_low = candle["Low"]
        c_close = candle["Close"]
        c_open = candle["Open"]

        # ── Phase: WAITING for entry trigger ──
        if position_phase == "WAITING":
            if c_high >= entry_price:
                entry_triggered = True
                position_phase = "FULL"
                # Check if SL is also hit in this same candle
                if c_low <= sl_price:
                    # Both entry and SL in same candle — skip (too choppy)
                    return TradeResultV2(
                        date="", symbol="", gap_pct=gap_pct,
                        entry_price=entry_price, sl_price=sl_price,
                        target1_price=target1_price, target2_price=target2_price,
                        risk_pct=risk_pct, first_candle_green=True,
                        entry_triggered=True, outcome="LOSS",
                        exit_price=sl_price, pnl_pct=-risk_pct,
                        pnl_rs=(sl_price - entry_price) * shares,
                        exit_candle=idx, partial_pnl_rs=0, trail_pnl_rs=0,
                        max_favorable=0, max_adverse=risk_pct,
                    )
                # Check if target1 hit in same candle as entry
                if c_high >= target1_price:
                    partial_pnl = (target1_price - entry_price) * half_shares
                    if config.use_trailing_stop:
                        position_phase = "PARTIAL"
                        trail_stop = entry_price  # Move stop to breakeven
                    else:
                        # Exit full position at target1
                        trail_pnl = (target1_price - entry_price) * remaining_shares
                        exit_price = target1_price
                        exit_candle = idx
                        position_phase = "DONE"
                        break
            continue

        # Track max favorable/adverse from entry
        if position_phase in ["FULL", "PARTIAL"]:
            fav = ((c_high - entry_price) / entry_price) * 100
            adv = ((entry_price - c_low) / entry_price) * 100
            max_fav = max(max_fav, fav)
            max_adv = max(max_adv, adv)

        # ── Phase: FULL position (waiting for SL or Target1) ──
        if position_phase == "FULL":
            if c_low <= sl_price:
                # SL hit — full loss
                exit_price = sl_price
                exit_candle = idx
                position_phase = "DONE"
                partial_pnl = 0
                trail_pnl = (sl_price - entry_price) * shares
                break
            elif c_high >= target1_price:
                # Target1 hit — take partial profit
                partial_pnl = (target1_price - entry_price) * half_shares
                if config.use_trailing_stop:
                    position_phase = "PARTIAL"
                    trail_stop = entry_price  # Move stop to breakeven
                else:
                    trail_pnl = (target1_price - entry_price) * remaining_shares
                    exit_price = target1_price
                    exit_candle = idx
                    position_phase = "DONE"
                    break

        # ── Phase: PARTIAL (trailing the remaining position) ──
        elif position_phase == "PARTIAL":
            # Update trail stop (use previous candle's low)
            if idx > 0:
                prev_candle_low = remaining_candles.iloc[idx - 1]["Low"]
                trail_stop = max(trail_stop, prev_candle_low)

            if c_low <= trail_stop:
                # Trailing stop hit
                trail_pnl = (trail_stop - entry_price) * remaining_shares
                exit_price = trail_stop
                exit_candle = idx
                position_phase = "DONE"
                break
            elif c_high >= target2_price:
                # Target2 hit — exit remaining
                trail_pnl = (target2_price - entry_price) * remaining_shares
                exit_price = target2_price
                exit_candle = idx
                position_phase = "DONE"
                break

    # ── End of day: close any remaining position ──
    if position_phase == "WAITING":
        return TradeResultV2(
            date="", symbol="", gap_pct=gap_pct,
            entry_price=entry_price, sl_price=sl_price,
            target1_price=target1_price, target2_price=target2_price,
            risk_pct=risk_pct, first_candle_green=True,
            entry_triggered=False, outcome="NO_ENTRY",
            exit_price=0, pnl_pct=0, pnl_rs=0,
            exit_candle=0, partial_pnl_rs=0, trail_pnl_rs=0,
            max_favorable=0, max_adverse=0,
        )

    if position_phase == "FULL":
        # Still holding full — exit at close
        last_close = day_candles.iloc[-1]["Close"]
        pnl = (last_close - entry_price) * shares
        exit_price = last_close
        exit_candle = len(remaining_candles) - 1
        partial_pnl = 0
        trail_pnl = pnl

    if position_phase == "PARTIAL":
        # Still trailing — exit at close
        last_close = day_candles.iloc[-1]["Close"]
        trail_pnl = (last_close - entry_price) * remaining_shares
        exit_price = last_close
        exit_candle = len(remaining_candles) - 1

    total_pnl = partial_pnl + trail_pnl
    pnl_pct = (total_pnl / capital) * 100

    # Classify outcome
    if not entry_triggered:
        outcome = "NO_ENTRY"
    elif total_pnl > 0 and partial_pnl > 0 and trail_pnl > 0:
        outcome = "WIN_FULL"
    elif total_pnl > 0 and partial_pnl > 0:
        outcome = "WIN_PARTIAL"
    elif total_pnl > 0:
        outcome = "WIN_TRAIL"
    elif total_pnl <= -(risk * shares * 0.8):
        outcome = "LOSS"
    elif total_pnl < 0:
        outcome = "SMALL_LOSS"
    else:
        outcome = "FLAT"

    return TradeResultV2(
        date="", symbol="", gap_pct=gap_pct,
        entry_price=round(entry_price, 2), sl_price=round(sl_price, 2),
        target1_price=round(target1_price, 2), target2_price=round(target2_price, 2),
        risk_pct=round(risk_pct, 2), first_candle_green=True,
        entry_triggered=entry_triggered, outcome=outcome,
        exit_price=round(exit_price, 2),
        pnl_pct=round(pnl_pct, 2), pnl_rs=round(total_pnl, 2),
        exit_candle=exit_candle, partial_pnl_rs=round(partial_pnl, 2),
        trail_pnl_rs=round(trail_pnl, 2),
        max_favorable=round(max_fav, 2), max_adverse=round(max_adv, 2),
    )


def run_backtest_v2(config: ConfigV2) -> list[TradeResultV2]:
    """Run the V2 institutional backtest."""
    if config.data_source == "1h":
        data_dir = INTRADAY_1H_DIR
    else:
        data_dir = INTRADAY_5M_DIR

    files = list(data_dir.glob("*.csv"))
    files = [f for f in files if f.stem != "^NSEI"]

    # Load Nifty for market filter if needed
    nifty_daily_change = {}
    if config.market_filter:
        nifty_file = data_dir / "^NSEI.csv"
        if nifty_file.exists():
            ndf = pd.read_csv(nifty_file, index_col=0, parse_dates=True)
            if isinstance(ndf.columns, pd.MultiIndex):
                ndf.columns = ndf.columns.get_level_values(0)
            ndf.columns = [c.strip() for c in ndf.columns]
            ndf["trade_date"] = ndf.index.date
            for td, group in ndf.groupby("trade_date"):
                day_change = ((group.iloc[-1]["Close"] - group.iloc[0]["Open"]) / group.iloc[0]["Open"]) * 100
                nifty_daily_change[td] = day_change

    print(f"V2 Institutional Backtest")
    print(f"  Data source: {config.data_source}")
    print(f"  Gap range: {config.gap_min_pct}% to {config.gap_max_pct}%")
    print(f"  Wait candles: {config.skip_first_n_candles}")
    print(f"  Trailing: {config.use_trailing_stop}")
    print(f"  Market filter: {config.market_filter}")
    print(f"  Stocks available: {len(files)}")
    print()

    results = []

    for f in sorted(files):
        sym = f.stem.replace("_NS", "")
        df = pd.read_csv(f, index_col=0, parse_dates=True)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.columns = [c.strip() for c in df.columns]

        if len(df) < 14:
            continue

        df["trade_date"] = df.index.date
        daily_groups = df.groupby("trade_date")

        prev_close = None
        for trade_date, day_candles in daily_groups:
            if prev_close is None:
                prev_close = day_candles.iloc[-1]["Close"]
                continue

            if len(day_candles) < config.skip_first_n_candles + 3:
                prev_close = day_candles.iloc[-1]["Close"]
                continue

            open_price = day_candles.iloc[0]["Open"]
            if open_price <= 0 or prev_close <= 0:
                prev_close = day_candles.iloc[-1]["Close"]
                continue

            gap_pct = ((open_price - prev_close) / prev_close) * 100

            # Filter: gap down within range
            abs_gap = abs(gap_pct)
            if gap_pct > -config.gap_min_pct or gap_pct < -config.gap_max_pct:
                prev_close = day_candles.iloc[-1]["Close"]
                continue

            # Market filter
            if config.market_filter and trade_date in nifty_daily_change:
                if nifty_daily_change[trade_date] < -1.5:
                    prev_close = day_candles.iloc[-1]["Close"]
                    continue

            result = simulate_trade_v2(day_candles, gap_pct, config, config.capital)
            if result is not None:
                result.date = str(trade_date)
                result.symbol = sym
                result.gap_pct = round(gap_pct, 2)
                results.append(result)

            prev_close = day_candles.iloc[-1]["Close"]

    return results


def analyze_results_v2(results: list[TradeResultV2], config: ConfigV2):
    """Print comprehensive analysis of V2 results."""
    if not results:
        print("No results!")
        return

    df = pd.DataFrame([vars(r) for r in results])
    df["date"] = pd.to_datetime(df["date"])

    total = len(df)
    no_signal = len(df[df["outcome"] == "NO_SIGNAL"])
    no_entry = len(df[df["outcome"] == "NO_ENTRY"])
    actual_trades = df[~df["outcome"].isin(["NO_SIGNAL", "NO_ENTRY"])]
    traded = len(actual_trades)

    print("=" * 65)
    print(f"V2 INSTITUTIONAL BACKTEST RESULTS")
    print(f"Gap {config.gap_min_pct}-{config.gap_max_pct}% | Wait {config.skip_first_n_candles} candle | Trail: {config.use_trailing_stop}")
    print("=" * 65)
    print(f"Total gap-down observations:  {total:,}")
    print(f"  Filtered (red 1st candle):  {no_signal:,} ({no_signal/total*100:.1f}%)")
    print(f"  No entry triggered:         {no_entry:,}")
    print(f"  Actual trades taken:        {traded:,}")
    print()

    if traded == 0:
        return

    # Outcome breakdown
    print("Trade Outcomes:")
    for outcome in ["WIN_FULL", "WIN_PARTIAL", "WIN_TRAIL", "FLAT", "SMALL_LOSS", "LOSS"]:
        count = len(actual_trades[actual_trades["outcome"] == outcome])
        if count > 0:
            avg_pnl = actual_trades[actual_trades["outcome"] == outcome]["pnl_rs"].mean()
            print(f"  {outcome:<14}: {count:4} ({count/traded*100:5.1f}%)  avg P&L: ₹{avg_pnl:>+8,.0f}")

    wins = actual_trades[actual_trades["outcome"].str.startswith("WIN")]
    losses = actual_trades[actual_trades["outcome"].isin(["LOSS", "SMALL_LOSS"])]
    flats = actual_trades[actual_trades["outcome"] == "FLAT"]

    win_count = len(wins)
    loss_count = len(losses)
    wr = win_count / traded * 100

    print()
    print(f"Win Rate:        {wr:.1f}% ({win_count}W / {loss_count}L / {len(flats)}F)")
    print(f"Avg Win:         ₹{wins['pnl_rs'].mean():>+,.0f}" if win_count > 0 else "")
    print(f"Avg Loss:        ₹{losses['pnl_rs'].mean():>+,.0f}" if loss_count > 0 else "")
    print(f"Avg P&L/trade:   ₹{actual_trades['pnl_rs'].mean():>+,.0f}")
    print(f"Total P&L:       ₹{actual_trades['pnl_rs'].sum():>+,.0f}")
    print()
    print(f"Avg risk (SL%):  {actual_trades['risk_pct'].mean():.2f}%")
    print(f"Avg max favor:   {actual_trades[actual_trades['entry_triggered']]['max_favorable'].mean():.2f}%")
    print(f"Avg max adverse: {actual_trades[actual_trades['entry_triggered']]['max_adverse'].mean():.2f}%")
    print()

    # Monthly breakdown
    actual_trades = actual_trades.copy()
    actual_trades["month"] = actual_trades["date"].dt.to_period("M")
    monthly = actual_trades.groupby("month").agg(
        trades=("outcome", "count"),
        wins=("outcome", lambda x: x.str.startswith("WIN").sum()),
        total_pnl=("pnl_rs", "sum"),
    )
    monthly["wr"] = (monthly["wins"] / monthly["trades"] * 100).round(1)
    print("Monthly Breakdown:")
    for month, row in monthly.iterrows():
        bar = "█" * min(30, max(0, int(row["total_pnl"] / 200)))
        neg_bar = "▓" * min(30, max(0, int(-row["total_pnl"] / 200)))
        print(f"  {month}: {row['trades']:3.0f} trades | {row['wins']:2.0f}W | "
              f"WR {row['wr']:5.1f}% | ₹{row['total_pnl']:>+9,.0f} "
              f"{'  ' + bar if row['total_pnl'] > 0 else '  ' + neg_bar}")

    # Simulate 1 best trade per day
    print()
    print("=" * 65)
    print("1 TRADE PER DAY (pick largest gap, only if signal exists)")
    print("=" * 65)
    signaled = df[df["outcome"].isin(["WIN_FULL", "WIN_PARTIAL", "WIN_TRAIL", "FLAT", "SMALL_LOSS", "LOSS"])]
    if len(signaled) > 0:
        best_per_day = signaled.loc[signaled.groupby("date")["gap_pct"].apply(lambda x: x.abs().idxmax())]
        bpd_total = len(best_per_day)
        bpd_wins = best_per_day["outcome"].str.startswith("WIN").sum()
        bpd_losses = best_per_day["outcome"].isin(["LOSS", "SMALL_LOSS"]).sum()
        bpd_wr = bpd_wins / bpd_total * 100 if bpd_total > 0 else 0
        bpd_pnl = best_per_day["pnl_rs"].sum()
        months = best_per_day["date"].dt.to_period("M").nunique()

        print(f"  Trading days with signal: {bpd_total}")
        print(f"  Win Rate: {bpd_wr:.1f}% ({bpd_wins}W / {bpd_losses}L)")
        print(f"  Total P&L: ₹{bpd_pnl:+,.0f}")
        print(f"  Monthly avg P&L: ₹{bpd_pnl/max(months,1):+,.0f}")

    return df


# ── Main ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Run V2 backtest on both data sources
    configs = [
        ConfigV2(data_source="5m", gap_min_pct=3.0, gap_max_pct=7.0, skip_first_n_candles=1, use_trailing_stop=True),
        ConfigV2(data_source="5m", gap_min_pct=3.0, gap_max_pct=7.0, skip_first_n_candles=1, use_trailing_stop=False),
        ConfigV2(data_source="5m", gap_min_pct=3.0, gap_max_pct=15.0, skip_first_n_candles=1, use_trailing_stop=True),
        ConfigV2(data_source="1h", gap_min_pct=3.0, gap_max_pct=7.0, skip_first_n_candles=1, use_trailing_stop=True),
        ConfigV2(data_source="1h", gap_min_pct=3.0, gap_max_pct=7.0, skip_first_n_candles=1, use_trailing_stop=False),
        ConfigV2(data_source="1h", gap_min_pct=3.0, gap_max_pct=15.0, skip_first_n_candles=1, use_trailing_stop=True),
    ]

    for i, config in enumerate(configs):
        print(f"\n{'#' * 65}")
        print(f"# V2 CONFIG {i+1}")
        print(f"{'#' * 65}\n")

        results = run_backtest_v2(config)
        if results:
            analyze_results_v2(results, config)

            # Save
            df = pd.DataFrame([vars(r) for r in results])
            fname = f"v2_trades_{config.data_source}_gap{config.gap_min_pct}-{config.gap_max_pct}_trail{config.use_trailing_stop}.csv"
            df.to_csv(RESULTS_DIR / fname, index=False)
            print(f"\nSaved to {RESULTS_DIR / fname}")
