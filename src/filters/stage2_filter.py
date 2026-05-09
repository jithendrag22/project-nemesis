import pandas as pd


def passes_stage2(row: pd.Series, params: dict) -> tuple[bool, list[str]]:
    """
    Check if a stock row passes all 7 Stage 2 conditions.
    Returns (passed: bool, failed_conditions: list[str])
    """
    failed = []
    near_high_pct = params.get("near_52w_high_pct", 15)  # within X% of 52w high
    min_turnover   = params.get("min_turnover_cr", 10) * 1e7  # convert crore to rupees

    checks = {
        "above_sma50":      row["Close"] > row["sma50"],
        "above_sma200":     row["Close"] > row["sma200"],
        "near_52w_high":    row["pct_from_52w_high"] >= -near_high_pct,
        "sma50_rising":     bool(row["sma50_rising"]),
        "rs_positive":      row["rs_vs_nifty_3m"] > 0,
        "liquidity":        row["turnover_ma20"] >= min_turnover,
    }

    for name, passed in checks.items():
        if not passed:
            failed.append(name)

    return len(failed) == 0, failed
