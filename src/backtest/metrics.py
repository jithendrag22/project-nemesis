import pandas as pd
import numpy as np
from typing import Optional


def compute_metrics(trades: pd.DataFrame) -> dict:
    """
    Compute all backtest statistics from the trades DataFrame.
    Returns a flat dict with all metrics including monthly breakdown.
    """
    if trades.empty:
        return {"error": "No trades found"}

    trades = trades.copy()
    trades["entry_date"] = pd.to_datetime(trades["entry_date"])
    trades["exit_date"]  = pd.to_datetime(trades["exit_date"])

    # ── Core stats ────────────────────────────────────────────────────────────
    total_trades   = len(trades)
    winners        = trades[trades["pnl"] > 0]
    losers         = trades[trades["pnl"] <= 0]
    win_rate       = len(winners) / total_trades * 100

    avg_win        = winners["pnl"].mean() if len(winners) else 0
    avg_loss       = losers["pnl"].mean()  if len(losers)  else 0
    total_pnl      = trades["pnl"].sum()
    gross_profit   = winners["pnl"].sum() if len(winners) else 0
    gross_loss     = abs(losers["pnl"].sum()) if len(losers) else 0
    profit_factor  = gross_profit / gross_loss if gross_loss > 0 else float("inf")

    # R-multiple stats (1R = ₹1,000)
    avg_r          = trades["r_multiple"].mean()
    expectancy_r   = avg_r  # same thing with 1R = fixed
    median_r       = trades["r_multiple"].median()

    # SQN (System Quality Number) — Van Tharp
    r_std = trades["r_multiple"].std()
    sqn   = (avg_r / r_std * np.sqrt(total_trades)) if r_std > 0 else 0

    # ── Equity curve & drawdown ───────────────────────────────────────────────
    trades_sorted  = trades.sort_values("exit_date")
    equity         = trades_sorted["pnl"].cumsum()
    rolling_max    = equity.cummax()
    drawdown       = equity - rolling_max
    max_drawdown   = drawdown.min()

    # Longest drawdown duration (in calendar days)
    in_dd          = drawdown < 0
    shifted        = in_dd.shift(1).infer_objects(copy=False).fillna(False)
    dd_starts      = trades_sorted["exit_date"][in_dd & ~shifted]
    dd_ends        = trades_sorted["exit_date"][~in_dd & shifted]
    max_dd_days    = 0
    for s in dd_starts:
        ends_after = dd_ends[dd_ends > s]
        if not ends_after.empty:
            max_dd_days = max(max_dd_days, (ends_after.iloc[0] - s).days)

    # ── Exit reason breakdown ─────────────────────────────────────────────────
    exit_counts = trades["exit_reason"].value_counts().to_dict()

    # ── Setup breakdown ───────────────────────────────────────────────────────
    setup_stats = {}
    for setup, grp in trades.groupby("setup"):
        wins = (grp["pnl"] > 0).sum()
        setup_stats[setup] = {
            "trades":   len(grp),
            "win_rate": round(wins / len(grp) * 100, 1),
            "avg_r":    round(grp["r_multiple"].mean(), 3),
            "total_pnl": round(grp["pnl"].sum(), 2),
        }

    # ── Market state breakdown ────────────────────────────────────────────────
    market_stats = {}
    for state, grp in trades.groupby("market_state"):
        wins = (grp["pnl"] > 0).sum()
        market_stats[state] = {
            "trades":   len(grp),
            "win_rate": round(wins / len(grp) * 100, 1),
            "avg_r":    round(grp["r_multiple"].mean(), 3),
            "total_pnl": round(grp["pnl"].sum(), 2),
        }

    # ── Monthly analysis ──────────────────────────────────────────────────────
    trades["month"] = trades["exit_date"].dt.to_period("M")
    monthly = trades.groupby("month").apply(_monthly_stats, include_groups=False).reset_index()
    monthly = monthly.sort_values("month")

    positive_months    = (monthly["pnl"] > 0).sum()
    negative_months    = (monthly["pnl"] <= 0).sum()
    best_month_pnl     = monthly["pnl"].max()
    worst_month_pnl    = monthly["pnl"].min()
    best_month         = monthly.loc[monthly["pnl"].idxmax(), "month"]
    worst_month        = monthly.loc[monthly["pnl"].idxmin(), "month"]
    avg_monthly_pnl    = monthly["pnl"].mean()

    # Consecutive streaks
    pos_neg            = (monthly["pnl"] > 0).astype(int).tolist()
    max_consec_pos     = _max_streak(pos_neg, 1)
    max_consec_neg     = _max_streak(pos_neg, 0)

    # Yearly summary
    trades["year"] = trades["exit_date"].dt.year
    yearly = trades.groupby("year").apply(_monthly_stats, include_groups=False).reset_index()

    return {
        # Core
        "total_trades":     total_trades,
        "win_rate_pct":     round(win_rate, 1),
        "avg_win_inr":      round(avg_win, 2),
        "avg_loss_inr":     round(avg_loss, 2),
        "total_pnl_inr":    round(total_pnl, 2),
        "gross_profit_inr": round(gross_profit, 2),
        "gross_loss_inr":   round(gross_loss, 2),
        "profit_factor":    round(profit_factor, 2),
        # R-multiple
        "avg_r":            round(avg_r, 3),
        "median_r":         round(median_r, 3),
        "expectancy_r":     round(expectancy_r, 3),
        "sqn":              round(sqn, 2),
        # Drawdown
        "max_drawdown_inr": round(max_drawdown, 2),
        "max_dd_days":      max_dd_days,
        # Monthly
        "positive_months":  int(positive_months),
        "negative_months":  int(negative_months),
        "pct_positive_months": round(positive_months / len(monthly) * 100, 1) if len(monthly) else 0,
        "max_consec_positive": max_consec_pos,
        "max_consec_negative": max_consec_neg,
        "best_month":       str(best_month),
        "best_month_pnl":   round(best_month_pnl, 2),
        "worst_month":      str(worst_month),
        "worst_month_pnl":  round(worst_month_pnl, 2),
        "avg_monthly_pnl":  round(avg_monthly_pnl, 2),
        # Tables
        "monthly_table":    monthly,
        "yearly_table":     yearly,
        "exit_reasons":     exit_counts,
        "setup_breakdown":  setup_stats,
        "market_breakdown": market_stats,
        # Raw for plotting
        "equity_curve":     equity.values,
        "equity_dates":     trades_sorted["exit_date"].values,
    }


def _monthly_stats(grp: pd.DataFrame) -> pd.Series:
    wins = (grp["pnl"] > 0).sum()
    n    = len(grp)
    return pd.Series({
        "trades":    n,
        "winners":   int(wins),
        "losers":    int(n - wins),
        "win_rate":  round(wins / n * 100, 1) if n else 0,
        "pnl":       round(grp["pnl"].sum(), 2),
        "avg_r":     round(grp["r_multiple"].mean(), 3),
    })


def _max_streak(seq: list, value: int) -> int:
    max_s = cur = 0
    for v in seq:
        if v == value:
            cur += 1
            max_s = max(max_s, cur)
        else:
            cur = 0
    return max_s


def print_summary(m: dict) -> None:
    """Print a human-readable summary of all metrics."""
    sep = "─" * 55

    print(f"\n{'═'*55}")
    print(f"  PROJECT NEMESIS — BACKTEST RESULTS")
    print(f"{'═'*55}")

    print(f"\n{sep}")
    print(f"  CORE PERFORMANCE")
    print(sep)
    print(f"  Total trades       : {m['total_trades']}")
    print(f"  Win rate           : {m['win_rate_pct']}%  (target: ≥60%)")
    print(f"  Total P&L          : ₹{m['total_pnl_inr']:,.0f}")
    print(f"  Avg win            : ₹{m['avg_win_inr']:,.0f}")
    print(f"  Avg loss           : ₹{m['avg_loss_inr']:,.0f}")
    print(f"  Profit factor      : {m['profit_factor']}  (target: ≥1.5)")

    print(f"\n{sep}")
    print(f"  R-MULTIPLE STATS  (1R = ₹1,000)")
    print(sep)
    print(f"  Expectancy         : {m['expectancy_r']}R  (target: ≥0.5R)")
    print(f"  Median R           : {m['median_r']}R")
    print(f"  SQN                : {m['sqn']}  (>1.6 good, >2.0 excellent)")

    print(f"\n{sep}")
    print(f"  DRAWDOWN")
    print(sep)
    print(f"  Max drawdown       : ₹{m['max_drawdown_inr']:,.0f}")
    print(f"  Max DD duration    : {m['max_dd_days']} calendar days")

    print(f"\n{sep}")
    print(f"  MONTHLY ANALYSIS  (by exit month)")
    print(sep)
    total_m = m['positive_months'] + m['negative_months']
    print(f"  Total months       : {total_m}")
    print(f"  Positive months    : {m['positive_months']} ({m['pct_positive_months']}%)  (target: ≥60%)")
    print(f"  Negative months    : {m['negative_months']}")
    print(f"  Avg monthly P&L    : ₹{m['avg_monthly_pnl']:,.0f}")
    print(f"  Best month         : {m['best_month']}  ₹{m['best_month_pnl']:,.0f}")
    print(f"  Worst month        : {m['worst_month']}  ₹{m['worst_month_pnl']:,.0f}")
    print(f"  Max consec. green  : {m['max_consec_positive']} months")
    print(f"  Max consec. red    : {m['max_consec_negative']} months  (target: ≤3)")

    print(f"\n{sep}")
    print(f"  EXIT REASON BREAKDOWN")
    print(sep)
    for reason, count in sorted(m['exit_reasons'].items(), key=lambda x: -x[1]):
        pct = count / m['total_trades'] * 100
        print(f"  {reason:<22}: {count:4d}  ({pct:.1f}%)")

    print(f"\n{sep}")
    print(f"  SETUP BREAKDOWN")
    print(sep)
    for setup, s in m['setup_breakdown'].items():
        print(f"  {setup:<22}: {s['trades']:3d} trades | WR {s['win_rate']}% | "
              f"AvgR {s['avg_r']} | P&L ₹{s['total_pnl']:,.0f}")

    print(f"\n{sep}")
    print(f"  MARKET STATE BREAKDOWN")
    print(sep)
    for state, s in m['market_breakdown'].items():
        print(f"  {state:<10}: {s['trades']:3d} trades | WR {s['win_rate']}% | "
              f"AvgR {s['avg_r']} | P&L ₹{s['total_pnl']:,.0f}")

    print(f"\n{sep}")
    print(f"  MONTHLY DETAIL TABLE")
    print(sep)
    mt = m['monthly_table']
    print(f"  {'Month':<9} {'Trades':>6} {'W':>4} {'L':>4} {'WR%':>6} {'P&L':>9} {'AvgR':>6}")
    print(f"  {'-'*9} {'-'*6} {'-'*4} {'-'*4} {'-'*6} {'-'*9} {'-'*6}")
    for _, row in mt.iterrows():
        flag = "✓" if row["pnl"] > 0 else "✗"
        print(f"  {str(row['month']):<9} {row['trades']:>6} {row['winners']:>4} {row['losers']:>4} "
              f"{row['win_rate']:>5.1f}% {row['pnl']:>9,.0f}  {row['avg_r']:>6.3f}  {flag}")

    print(f"\n{sep}")
    print(f"  YEARLY SUMMARY")
    print(sep)
    yt = m['yearly_table']
    print(f"  {'Year':<6} {'Trades':>6} {'W':>4} {'L':>4} {'WR%':>6} {'P&L':>10} {'AvgR':>6}")
    print(f"  {'-'*6} {'-'*6} {'-'*4} {'-'*4} {'-'*6} {'-'*10} {'-'*6}")
    for _, row in yt.iterrows():
        print(f"  {int(row['year']):<6} {row['trades']:>6} {row['winners']:>4} {row['losers']:>4} "
              f"{row['win_rate']:>5.1f}% {row['pnl']:>10,.0f}  {row['avg_r']:>6.3f}")

    print(f"\n{'═'*55}\n")
