"""
Strategy C — Backtest reporting.
Computes and prints all stats: overall, monthly, market state, seasonal, ADX, sector.
"""

from __future__ import annotations
import pandas as pd
import numpy as np


MONTH_NAMES = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
               7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}


def _bar(value: float, width: int = 30, min_v: float = -2, max_v: float = 2) -> str:
    """Tiny ASCII bar chart for R-multiple."""
    frac = (value - min_v) / (max_v - min_v)
    frac = max(0.0, min(1.0, frac))
    filled = int(frac * width)
    mid    = int(-min_v / (max_v - min_v) * width)
    bar    = [" "] * width
    if value >= 0:
        for k in range(mid, min(mid + filled - (width // 2 - mid), width)):
            bar[k] = "█"
        for k in range(mid, min(mid + int(abs(value) / max_v * (width // 2)), width)):
            bar[k] = "█"
    else:
        for k in range(max(0, mid + int(value / min_v * mid)), mid):
            bar[k] = "░"
    bar[mid] = "│"
    return "".join(bar)


def compute(trades: pd.DataFrame) -> dict:
    if trades.empty:
        return {}

    t = trades.copy()
    t["entry_date"] = pd.to_datetime(t["entry_date"])
    t["exit_date"]  = pd.to_datetime(t["exit_date"])
    t["exit_month"] = t["exit_date"].dt.to_period("M")
    t["entry_month_num"] = t["entry_date"].dt.month
    t["entry_year"] = t["entry_date"].dt.year

    wins  = t["win"]
    r_mul = t["r_multiple"]

    # ── Core ─────────────────────────────────────────────────────────────────
    n            = len(t)
    win_rate     = wins.mean() * 100
    total_pnl    = t["pnl"].sum()
    avg_win      = t.loc[wins,  "pnl"].mean() if wins.any()  else 0
    avg_loss     = t.loc[~wins, "pnl"].mean() if (~wins).any() else 0
    profit_factor= abs(avg_win * wins.sum() / (avg_loss * (~wins).sum())) if (~wins).any() else np.inf
    expectancy   = r_mul.mean()
    sqn          = (r_mul.mean() / r_mul.std() * np.sqrt(n)) if r_mul.std() > 0 else 0
    avg_days     = t["trading_days"].mean()
    med_days     = t["trading_days"].median()

    # ── Monthly P&L ───────────────────────────────────────────────────────────
    monthly = t.groupby("exit_month")["pnl"].sum()
    pos_months = (monthly > 0).sum()
    neg_months = (monthly <= 0).sum()
    pos_pct    = pos_months / len(monthly) * 100 if len(monthly) > 0 else 0

    # Max consecutive red months
    streak = green = red = 0
    max_green = max_red = 0
    for v in monthly:
        if v > 0:
            green += 1; red = 0
            max_green = max(max_green, green)
        else:
            red += 1; green = 0
            max_red = max(max_red, red)

    # ── Drawdown ──────────────────────────────────────────────────────────────
    equity = t.sort_values("exit_date")["pnl"].cumsum()
    rolling_max = equity.cummax()
    drawdown = equity - rolling_max
    max_dd   = drawdown.min()

    # ── Trades per month ─────────────────────────────────────────────────────
    trades_pm = n / len(monthly) if len(monthly) > 0 else 0

    return {
        "n":              n,
        "win_rate":       win_rate,
        "total_pnl":      total_pnl,
        "avg_win":        avg_win,
        "avg_loss":       avg_loss,
        "profit_factor":  profit_factor,
        "expectancy":     expectancy,
        "sqn":            sqn,
        "avg_days":       avg_days,
        "med_days":       med_days,
        "monthly":        monthly,
        "pos_months":     pos_months,
        "neg_months":     neg_months,
        "pos_pct":        pos_pct,
        "max_consec_green": max_green,
        "max_consec_red":   max_red,
        "max_dd":         max_dd,
        "trades_pm":      trades_pm,
        "trades":         t,
    }


def print_report(trades: pd.DataFrame, title: str = "Strategy C") -> None:
    if trades.empty:
        print("No trades to report.")
        return

    m = compute(trades)
    t = m["trades"]

    SEP  = "═" * 60
    SEP2 = "─" * 60

    print(f"\n{SEP}")
    print(f"  {title.upper()}")
    print(SEP)

    # ── 1. Core performance ───────────────────────────────────────────────────
    print(f"\n{'CORE PERFORMANCE':─<60}")
    print(f"  Total trades       : {m['n']}")
    print(f"  Win rate           : {m['win_rate']:.1f}%")
    print(f"  Total P&L          : ₹{m['total_pnl']:,.0f}")
    print(f"  Avg win            : ₹{m['avg_win']:,.0f}")
    print(f"  Avg loss           : ₹{m['avg_loss']:,.0f}")
    print(f"  Profit factor      : {m['profit_factor']:.2f}")
    print(f"  Expectancy         : {m['expectancy']:.3f}R")
    print(f"  SQN                : {m['sqn']:.2f}")
    print(f"  Avg hold           : {m['avg_days']:.1f} days  (median {m['med_days']:.0f})")
    print(f"  Trades per month   : {m['trades_pm']:.1f}")

    print(f"\n{'MONTHLY HEALTH':─<60}")
    print(f"  Total months       : {m['pos_months'] + m['neg_months']}")
    print(f"  Positive months    : {m['pos_months']} ({m['pos_pct']:.1f}%)")
    print(f"  Negative months    : {m['neg_months']}")
    print(f"  Max consec. green  : {m['max_consec_green']} months")
    print(f"  Max consec. red    : {m['max_consec_red']} months")
    print(f"  Max drawdown       : ₹{m['max_dd']:,.0f}")

    # ── 2. Exit reasons ───────────────────────────────────────────────────────
    print(f"\n{'EXIT REASON BREAKDOWN':─<60}")
    for reason, cnt in t["exit_reason"].value_counts().items():
        pct = cnt / m["n"] * 100
        wr  = t.loc[t["exit_reason"] == reason, "win"].mean() * 100
        avg_r = t.loc[t["exit_reason"] == reason, "r_multiple"].mean()
        print(f"  {reason:<20} : {cnt:>4}  ({pct:>5.1f}%)  WR {wr:>5.1f}%  AvgR {avg_r:>+.3f}")

    # ── 3. Yearly breakdown ───────────────────────────────────────────────────
    print(f"\n{'YEARLY BREAKDOWN':─<60}")
    print(f"  {'Year':<6} {'Trades':>6} {'WR%':>7} {'AvgR':>7} {'P&L':>10}")
    print(f"  {'─'*40}")
    for yr, grp in t.groupby("entry_year"):
        print(
            f"  {yr:<6} {len(grp):>6} {grp['win'].mean()*100:>7.1f}%"
            f" {grp['r_multiple'].mean():>+7.3f} ₹{grp['pnl'].sum():>9,.0f}"
        )

    # ── 4. Calendar month breakdown ───────────────────────────────────────────
    print(f"\n{'CALENDAR MONTH (ENTRY MONTH) BREAKDOWN':─<60}")
    print(f"  {'Month':<6} {'Trades':>6} {'WR%':>7} {'AvgR':>7} {'P&L':>10}  Bar")
    print(f"  {'─'*65}")
    for mn in range(1, 13):
        grp = t[t["entry_month_num"] == mn]
        if grp.empty:
            continue
        avg_r = grp["r_multiple"].mean()
        print(
            f"  {MONTH_NAMES[mn]:<6} {len(grp):>6} {grp['win'].mean()*100:>7.1f}%"
            f" {avg_r:>+7.3f} ₹{grp['pnl'].sum():>9,.0f}  {_bar(avg_r)}"
        )

    # ── 5. Market state (Nifty green vs red during trade) ────────────────────
    print(f"\n{'NIFTY STATE DURING TRADE':─<60}")
    for label, mask in [
        ("Nifty GREEN (rose during trade)", t["nifty_green"] == True),
        ("Nifty RED   (fell during trade)", t["nifty_green"] == False),
    ]:
        grp = t[mask]
        if grp.empty:
            continue
        print(
            f"  {label:<40} : {len(grp):>4} trades  "
            f"WR {grp['win'].mean()*100:.1f}%  AvgR {grp['r_multiple'].mean():+.3f}"
        )

    # ── 6. Market state (bull/neutral) ───────────────────────────────────────
    print(f"\n{'MARKET STATE AT ENTRY':─<60}")
    for state, grp in t.groupby("market_state"):
        print(
            f"  {state:<10} : {len(grp):>4} trades  "
            f"WR {grp['win'].mean()*100:.1f}%  AvgR {grp['r_multiple'].mean():+.3f}"
            f"  P&L ₹{grp['pnl'].sum():,.0f}"
        )

    # ── 7. Seasonality bucket breakdown ──────────────────────────────────────
    print(f"\n{'SEASONALITY BUCKET':─<60}")
    bins   = [0, 35, 50, 65, 101]
    labels = ["Very Weak (<35)", "Weak (35-49)", "Neutral (50-64)", "Strong (≥65)"]
    t["season_bucket"] = pd.cut(t["season_score"], bins=bins, labels=labels, right=False)
    for bucket, grp in t.groupby("season_bucket", observed=True):
        print(
            f"  {str(bucket):<20} : {len(grp):>4} trades  "
            f"WR {grp['win'].mean()*100:.1f}%  AvgR {grp['r_multiple'].mean():+.3f}"
            f"  P&L ₹{grp['pnl'].sum():,.0f}"
        )

    # ── 8. ADX bucket breakdown ───────────────────────────────────────────────
    print(f"\n{'ADX AT ENTRY (TREND STRENGTH)':─<60}")
    adx_bins   = [0, 25, 35, 50, 200]
    adx_labels = ["Weak (<25)", "Moderate (25-34)", "Strong (35-49)", "Very Strong (≥50)"]
    adx_col = "adx_at_entry" if "adx_at_entry" in t.columns else "adx_at_signal"
    t["adx_bucket"] = pd.cut(t[adx_col], bins=adx_bins, labels=adx_labels, right=False)
    for bucket, grp in t.groupby("adx_bucket", observed=True):
        print(
            f"  {str(bucket):<24} : {len(grp):>4} trades  "
            f"WR {grp['win'].mean()*100:.1f}%  AvgR {grp['r_multiple'].mean():+.3f}"
        )

    # ── 9. Pullback length breakdown ──────────────────────────────────────────
    print(f"\n{'PULLBACK LENGTH (candles)':─<60}")
    for pb_len, grp in t.groupby("pullback_candles"):
        print(
            f"  {pb_len} candle(s)  : {len(grp):>4} trades  "
            f"WR {grp['win'].mean()*100:.1f}%  AvgR {grp['r_multiple'].mean():+.3f}"
        )

    # ── 10. Sector breakdown ──────────────────────────────────────────────────
    print(f"\n{'SECTOR BREAKDOWN':─<60}")
    print(f"  {'Sector':<24} {'Tr':>4} {'WR%':>7} {'AvgR':>7} {'P&L':>10}")
    print(f"  {'─'*55}")
    for sector, grp in t.groupby("sector"):
        print(
            f"  {sector:<24} {len(grp):>4} {grp['win'].mean()*100:>7.1f}%"
            f" {grp['r_multiple'].mean():>+7.3f} ₹{grp['pnl'].sum():>9,.0f}"
        )

    # ── 11. Monthly P&L detail ────────────────────────────────────────────────
    print(f"\n{'MONTHLY P&L DETAIL (exit month)':─<60}")
    print(f"  {'Month':<10} {'Tr':>4} {'W':>4} {'L':>4} {'WR%':>6} {'P&L':>10}")
    print(f"  {'─'*48}")
    monthly_full = t.groupby("exit_month").apply(
        lambda g: pd.Series({
            "trades": len(g),
            "wins":   g["win"].sum(),
            "losses": (~g["win"]).sum(),
            "wr":     g["win"].mean() * 100,
            "pnl":    g["pnl"].sum(),
        }),
        include_groups=False,
    )
    for period, row in monthly_full.iterrows():
        flag = "✓" if row["pnl"] > 0 else "✗"
        print(
            f"  {str(period):<10} {int(row['trades']):>4} {int(row['wins']):>4} "
            f"{int(row['losses']):>4} {row['wr']:>6.1f}% ₹{row['pnl']:>9,.0f}  {flag}"
        )

    print(f"\n{SEP}\n")
