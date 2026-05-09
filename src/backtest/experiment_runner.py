"""
Experiment runner for Project Nemesis.
Each experiment is a named dict of overrides on top of the baseline config.
Run: python src/backtest/experiment_runner.py
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.downloader import load_universe, load_stock, load_nifty
from indicators.calculator import add_all
from filters.market_filter import get_market_state
from filters.stage2_filter import passes_stage2
from setups.setup_a import detect as detect_a
from setups.setup_b import detect as detect_b
from backtest.metrics import compute_metrics


# ── Baseline constants (shared across all experiments) ───────────────────────
MAX_RISK       = 1_000
MAX_CAPITAL    = 50_000
SLIPPAGE_PCT   = 0.001
COST_PER_TRADE = 100
MAX_GAP_PCT    = 0.03
MAX_EXTENDED   = 0.05
MIN_MOVE_PCT   = 0.02

BASELINE = {
    # market
    "market_filter_version": "B",
    # stage2
    "near_52w_high_pct": 15,
    "min_turnover_cr": 10,
    "min_rs_pct": 0.0,          # NEW: minimum rs_vs_nifty_3m (0 = just positive)
    # setup A
    "base_days_min": 5,
    "base_days_max": 15,
    "base_depth_pct": 8.0,
    "vol_ratio_min": 2.0,
    # setup B
    "ema_proximity_pct": 1.0,
    "prior_advance_pct": 15.0,
    "pullback_lookback": 5,
    # exit mechanics
    "time_stop_days": 999,      # no time stop (data shows breakouts need 2-4 weeks)
    "hard_stop_days": 999,      # no hard stop
    "exit_mode": "partial",     # "partial" | "full" | "trail"
    "trail_pct": 0.05,          # trailing stop % below recent high (for trail mode)
    "use_setup_b": True,        # toggle Setup B on/off
}

EXPERIMENTS = [
    # ── Baseline ──────────────────────────────────────────────────────────────
    {
        "name": "E00_baseline",
        "desc": "Baseline: MktB, depth8, vol2.0, no time exits, partial exit",
    },
    # ── Time exit variants ────────────────────────────────────────────────────
    {
        "name": "E01_time_3_5",
        "desc": "Original time exits: Day3 time-stop, Day5 hard exit",
        "time_stop_days": 3,
        "hard_stop_days": 5,
    },
    {
        "name": "E02_time_15_30",
        "desc": "Extended time exits: Day15 time-stop, Day30 hard exit",
        "time_stop_days": 15,
        "hard_stop_days": 30,
    },
    # ── Exit mode variants ────────────────────────────────────────────────────
    {
        "name": "E03_full_exit",
        "desc": "Full exit at 2:1 target (no partial exit, no BE stop trail)",
        "exit_mode": "full",
    },
    {
        "name": "E04_trail_5pct",
        "desc": "After 1:1 hit: trail stop 5% below daily high instead of locking to BE",
        "exit_mode": "trail",
        "trail_pct": 0.05,
    },
    {
        "name": "E05_trail_3pct",
        "desc": "After 1:1 hit: trail stop 3% below daily high",
        "exit_mode": "trail",
        "trail_pct": 0.03,
    },
    # ── RS filter variants ────────────────────────────────────────────────────
    {
        "name": "E06_rs_5pct",
        "desc": "RS filter: stock must outperform Nifty by ≥5% over 63 days",
        "min_rs_pct": 0.05,
    },
    {
        "name": "E07_rs_10pct",
        "desc": "RS filter: stock must outperform Nifty by ≥10% over 63 days",
        "min_rs_pct": 0.10,
    },
    {
        "name": "E08_rs_15pct",
        "desc": "RS filter: stock must outperform Nifty by ≥15% over 63 days",
        "min_rs_pct": 0.15,
    },
    # ── Setup B on/off ────────────────────────────────────────────────────────
    {
        "name": "E09_no_setup_b",
        "desc": "Setup A only — drop EMA pullback (Setup B was 43.7% WR vs A's 46.1%)",
        "use_setup_b": False,
    },
    # ── Market filter variants ────────────────────────────────────────────────
    {
        "name": "E10_market_c",
        "desc": "Market filter version C (full Minervini: 50/150/200 + SMA200 rising)",
        "market_filter_version": "C",
    },
    {
        "name": "E11_market_a",
        "desc": "Market filter version A (loose: just above 50 SMA)",
        "market_filter_version": "A",
    },
    # ── Volume ratio variants ─────────────────────────────────────────────────
    {
        "name": "E12_vol_1pt5",
        "desc": "vol_ratio_min = 1.5 (baseline uses 2.0)",
        "vol_ratio_min": 1.5,
    },
    {
        "name": "E13_vol_2pt5",
        "desc": "vol_ratio_min = 2.5",
        "vol_ratio_min": 2.5,
    },
    {
        "name": "E14_vol_3pt0",
        "desc": "vol_ratio_min = 3.0 (very high volume only)",
        "vol_ratio_min": 3.0,
    },
    # ── Base depth variants ───────────────────────────────────────────────────
    {
        "name": "E15_depth_5pct",
        "desc": "Tighter base: max depth 5% (very tight, Mark Minervini-style)",
        "base_depth_pct": 5.0,
    },
    {
        "name": "E16_depth_10pct",
        "desc": "Looser base: max depth 10%",
        "base_depth_pct": 10.0,
    },
    # ── Combined best guesses ─────────────────────────────────────────────────
    {
        "name": "E17_best_combo_a",
        "desc": "Combo A: no time exits + RS≥5% + Setup A only + vol 2.0",
        "min_rs_pct": 0.05,
        "use_setup_b": False,
    },
    {
        "name": "E18_best_combo_b",
        "desc": "Combo B: no time exits + RS≥10% + full exit + vol 2.0",
        "min_rs_pct": 0.10,
        "exit_mode": "full",
    },
    {
        "name": "E19_best_combo_c",
        "desc": "Combo C: trail exit + RS≥5% + Setup A only + vol 2.5",
        "exit_mode": "trail",
        "trail_pct": 0.05,
        "min_rs_pct": 0.05,
        "use_setup_b": False,
        "vol_ratio_min": 2.5,
    },
    {
        "name": "E20_best_combo_d",
        "desc": "Combo D: trail exit + RS≥10% + MktC + vol 2.0",
        "exit_mode": "trail",
        "trail_pct": 0.05,
        "min_rs_pct": 0.10,
        "market_filter_version": "C",
    },
]


def run_experiment(params: dict, start: str = "2015-01-01", end: str = "2024-12-31") -> pd.DataFrame:
    universe = load_universe()
    nifty    = load_nifty()
    nifty.index = pd.to_datetime(nifty.index)

    market_states = get_market_state(nifty, version=params["market_filter_version"])
    all_trades = []

    for _, row in universe.iterrows():
        symbol = row["symbol"]
        df = load_stock(symbol)
        if df is None or len(df) < 252:
            continue
        df.index = pd.to_datetime(df.index)
        df = df[(df.index >= start) & (df.index <= end)]
        if len(df) < 252:
            continue

        df = add_all(df, nifty)
        df.dropna(subset=["sma200", "ema20", "vol_ma20", "high_52w", "rs_vs_nifty_3m"], inplace=True)
        if len(df) < 50:
            continue

        ms = market_states.reindex(df.index, method="ffill")
        open_trade = None

        for i in range(len(df)):
            date  = df.index[i]
            today = df.iloc[i]
            state = ms.iloc[i] if i < len(ms) else "bear"

            # ── Manage open trade ─────────────────────────────────────────
            if open_trade is not None:
                trading_day = open_trade["trading_days"] + 1
                open_trade["trading_days"] = trading_day

                # Track recent high for trailing stop
                open_trade["recent_high"] = max(open_trade.get("recent_high", open_trade["entry"]),
                                                 today["High"])

                exit_price  = None
                exit_reason = None

                # Gap down past stop at open
                if today["Open"] <= open_trade["stop"]:
                    exit_price  = today["Open"]
                    exit_reason = "stop_gap_down"

                # Stop hit during day
                elif today["Low"] <= open_trade["stop"]:
                    exit_price  = open_trade["stop"]
                    exit_reason = "stop"

                # ── Exit mode: FULL (no partial, exit 100% at 2:1) ───────
                elif params["exit_mode"] == "full":
                    if today["High"] >= open_trade["target_2r"]:
                        exit_price  = open_trade["target_2r"]
                        exit_reason = "target_2r"
                    elif trading_day >= params["hard_stop_days"]:
                        exit_price  = today["Close"]
                        exit_reason = "hard_time_exit"
                    elif trading_day >= params["time_stop_days"]:
                        pct = (today["Close"] - open_trade["entry"]) / open_trade["entry"]
                        if pct < MIN_MOVE_PCT:
                            exit_price  = today["Close"]
                            exit_reason = "time_stop"

                # ── Exit mode: TRAIL (partial at 1:1, then trail stop) ───
                elif params["exit_mode"] == "trail":
                    if not open_trade.get("half_exited") and today["High"] >= open_trade["target_1r"]:
                        open_trade["half_exited"]     = True
                        open_trade["half_exit_price"] = open_trade["target_1r"]
                        open_trade["half_exit_date"]  = date
                        # Trail stop starts at breakeven, will be ratcheted up below

                    if open_trade.get("half_exited"):
                        # Ratchet trail stop up behind recent high
                        trail_stop = open_trade["recent_high"] * (1 - params["trail_pct"])
                        open_trade["stop"] = max(open_trade["stop"], trail_stop)

                        if today["High"] >= open_trade["target_2r"]:
                            exit_price  = open_trade["target_2r"]
                            exit_reason = "target_2r"
                        elif today["Low"] <= open_trade["stop"]:
                            exit_price  = open_trade["stop"]
                            exit_reason = "trail_stop"
                    else:
                        # Not yet half-exited: check time exits
                        if trading_day >= params["hard_stop_days"]:
                            exit_price  = today["Close"]
                            exit_reason = "hard_time_exit"
                        elif trading_day >= params["time_stop_days"]:
                            pct = (today["Close"] - open_trade["entry"]) / open_trade["entry"]
                            if pct < MIN_MOVE_PCT:
                                exit_price  = today["Close"]
                                exit_reason = "time_stop"

                # ── Exit mode: PARTIAL (original: half at 1:1, rest to BE) ─
                else:
                    if not open_trade.get("half_exited") and today["High"] >= open_trade["target_1r"]:
                        open_trade["half_exited"]     = True
                        open_trade["half_exit_price"] = open_trade["target_1r"]
                        open_trade["half_exit_date"]  = date
                        open_trade["stop"]            = open_trade["entry"]

                    elif open_trade.get("half_exited") and today["High"] >= open_trade["target_2r"]:
                        exit_price  = open_trade["target_2r"]
                        exit_reason = "target_2r"

                    elif not open_trade.get("half_exited"):
                        if trading_day >= params["hard_stop_days"]:
                            exit_price  = today["Close"]
                            exit_reason = "hard_time_exit"
                        elif trading_day >= params["time_stop_days"]:
                            pct = (today["Close"] - open_trade["entry"]) / open_trade["entry"]
                            if pct < MIN_MOVE_PCT:
                                exit_price  = today["Close"]
                                exit_reason = "time_stop"

                if exit_price is not None:
                    shares       = open_trade["shares"]
                    half_exited  = open_trade.get("half_exited", False)
                    half_exit_px = open_trade.get("half_exit_price", 0)

                    if params["exit_mode"] == "full":
                        pnl = shares * (exit_price - open_trade["entry"]) - COST_PER_TRADE
                    elif half_exited:
                        half_shares = shares // 2
                        rest_shares = shares - half_shares
                        pnl = (half_shares * (half_exit_px - open_trade["entry"]) +
                               rest_shares * (exit_price   - open_trade["entry"]) -
                               COST_PER_TRADE)
                    else:
                        pnl = shares * (exit_price - open_trade["entry"]) - COST_PER_TRADE

                    all_trades.append({
                        "symbol":       symbol,
                        "sector":       row.get("sector", "Unknown"),
                        "setup":        open_trade["setup"],
                        "entry_date":   open_trade["entry_date"],
                        "exit_date":    date,
                        "trading_days": trading_day,
                        "entry":        open_trade["entry"],
                        "stop":         open_trade["original_stop"],
                        "target_2r":    open_trade["target_2r"],
                        "exit_price":   exit_price,
                        "exit_reason":  exit_reason,
                        "shares":       shares,
                        "pnl":          round(pnl, 2),
                        "r_multiple":   round(pnl / MAX_RISK, 3),
                        "win":          pnl > 0,
                        "market_state": open_trade["market_state"],
                    })
                    open_trade = None

            # ── Look for new signal ───────────────────────────────────────
            if open_trade is None and state in ("bull", "neutral"):
                stage2_pass, _ = passes_stage2(today, params)
                if not stage2_pass:
                    continue

                # RS rank filter
                if today["rs_vs_nifty_3m"] < params["min_rs_pct"]:
                    continue

                signal = detect_a(df, i, params)
                if signal is None and params["use_setup_b"]:
                    signal = detect_b(df, i, params)
                if signal is None:
                    continue

                risk_per_share = signal["risk_per_share"]
                if risk_per_share <= 0:
                    continue

                shares       = int(MAX_RISK / risk_per_share)
                capital_used = shares * signal["entry"]
                if capital_used > MAX_CAPITAL:
                    shares = int(MAX_CAPITAL / signal["entry"])
                if shares <= 0:
                    continue

                if i + 1 >= len(df):
                    continue

                next_day = df.iloc[i + 1]
                entry_px = next_day["Open"] * (1 + SLIPPAGE_PCT)

                gap = (next_day["Open"] - today["Close"]) / today["Close"]
                if gap > MAX_GAP_PCT:
                    continue
                if (entry_px - signal["entry"]) / signal["entry"] > MAX_EXTENDED:
                    continue

                actual_risk = entry_px - signal["stop"]
                if actual_risk <= 0:
                    continue

                open_trade = {
                    "setup":         signal["setup"],
                    "entry_date":    df.index[i + 1],
                    "entry":         round(entry_px, 2),
                    "stop":          round(signal["stop"], 2),
                    "original_stop": round(signal["stop"], 2),
                    "target_1r":     round(entry_px + actual_risk, 2),
                    "target_2r":     round(entry_px + 2 * actual_risk, 2),
                    "shares":        shares,
                    "trading_days":  0,
                    "half_exited":   False,
                    "market_state":  state,
                    "recent_high":   entry_px,
                }

    return pd.DataFrame(all_trades)


def run_all(start: str = "2015-01-01", end: str = "2024-12-31") -> pd.DataFrame:
    results = []

    for exp in EXPERIMENTS:
        params = BASELINE.copy()
        for k, v in exp.items():
            if k not in ("name", "desc"):
                params[k] = v

        print(f"  {exp['name']} … ", end="", flush=True)
        trades = run_experiment(params, start=start, end=end)

        if trades.empty:
            print("no trades")
            results.append({"name": exp["name"], "desc": exp["desc"]})
            continue

        m = compute_metrics(trades)
        row = {
            "name":            exp["name"],
            "desc":            exp["desc"],
            "trades":          m["total_trades"],
            "win_rate":        m["win_rate_pct"],
            "avg_r":           m["avg_r"],
            "expectancy_r":    m["expectancy_r"],
            "total_pnl":       m["total_pnl_inr"],
            "profit_factor":   m["profit_factor"],
            "sqn":             m["sqn"],
            "pos_months":      m["positive_months"],
            "neg_months":      m["negative_months"],
            "pct_pos_months":  m["pct_positive_months"],
            "max_consec_red":  m["max_consec_negative"],
            "max_drawdown":    m["max_drawdown_inr"],
            "best_month_pnl":  m["best_month_pnl"],
            "worst_month_pnl": m["worst_month_pnl"],
            "exit_reasons":    str(m["exit_reasons"]),
        }
        results.append(row)
        print(f"WR={m['win_rate_pct']}% | E={m['expectancy_r']}R | "
              f"P&L=₹{m['total_pnl_inr']:,.0f} | Pos%={m['pct_positive_months']}%")

    df = pd.DataFrame(results)
    out = Path(__file__).parent.parent.parent / "experiments" / "results_table.csv"
    out.parent.mkdir(exist_ok=True)
    df.to_csv(out, index=False)
    print(f"\nResults saved → {out}")
    return df


if __name__ == "__main__":
    print(f"\nRunning {len(EXPERIMENTS)} experiments (2015–2024) …\n")
    df = run_all()

    print("\n\n── SORTED BY EXPECTANCY (best first) ──────────────────────────────────")
    display_cols = ["name", "trades", "win_rate", "expectancy_r", "total_pnl",
                    "pct_pos_months", "max_consec_red", "max_drawdown"]
    sub = df[display_cols].dropna().sort_values("expectancy_r", ascending=False)
    print(sub.to_string(index=False))

    print("\n── SORTED BY % POSITIVE MONTHS (best first) ───────────────────────────")
    sub2 = df[display_cols].dropna().sort_values("pct_pos_months", ascending=False)
    print(sub2.to_string(index=False))
