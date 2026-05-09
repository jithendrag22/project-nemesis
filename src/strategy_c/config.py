"""
Strategy C — all tunable parameters in one place.
Change values here; everything else reads from PARAMS.
"""

# ── Sectors we trade (from Strategy A analysis — these have positive expectancy) ──
SECTOR_WHITELIST = {
    "Utilities", "FMCG", "Pharma", "Cement", "Consumer Durables",
    "IT", "Real Estate", "Electronics", "Healthcare", "Consumer",
    "Insurance", "Consumer Electricals", "Mining", "Capital Goods",
    "Auto Ancillary", "Energy",
}

PARAMS = {
    # ── Daily pre-market filter ──────────────────────────────────────────────
    "min_rs_pct":            0.10,    # RS vs Nifty ≥ +10% over 63 days (validated in Strat A)
    "min_adx_daily":         25,      # ADX ≥ 25 → trend is real, not sideways chop
    "near_52w_high_pct":     20,      # price within 20% of 52-week high (Stage 2 proxy)
    "min_turnover_cr":       10,      # ₹10Cr avg daily turnover — F&O liquidity floor
    "seasonality_min_score": 45.0,    # skip Very Weak sector-months (<35 is the hard skip)
    "min_recent_move_pct":   0.01,    # stock must be up ≥1% in last 5 days (in motion)

    # ── Intraday candle settings ─────────────────────────────────────────────
    "intraday_interval":     "15m",   # 15-min candles — less noisy than 5m, still granular
    "ema_period_intraday":   20,      # EMA(20) on 15-min chart = ~5 hours of context
    "rsi_period_intraday":   14,

    # ── Pullback detection ───────────────────────────────────────────────────
    "pullback_min_candles":  2,       # pullback must have at least 2 declining candles
    "pullback_max_candles":  10,      # cap at 10 candles (~2.5 hours) — beyond = weakness
    "ema_touch_pct":         0.015,   # pullback low must come within 1.5% of EMA(20)
    "rsi_pullback_min":      35,      # RSI not so oversold the stock is collapsing
    "rsi_pullback_max":      62,      # RSI not overbought — still has room to run
    "pullback_vol_ratio_max":0.75,    # pullback volume < 75% of 20-candle avg (drying up)

    # ── Entry ────────────────────────────────────────────────────────────────
    "entry_range_pct":       0.015,   # entry valid up to 1.5% above trigger → your delay window
    "entry_valid_minutes":   45,      # signal expires 45 min after firing (3 candles)

    # ── Stop and target ──────────────────────────────────────────────────────
    "stop_buffer_pct":       0.0025,  # 0.25% below swing low → avoid tick-level stops
    "max_stop_pct":          0.04,    # skip if stop > 4% from entry (too wide for 5-day target)
    "min_stop_pct":          0.005,   # skip if stop < 0.5% (inside noise band)
    "target_rr":             2.0,     # 2:1 R:R — same philosophy as Strategy A

    # ── Position sizing ──────────────────────────────────────────────────────
    "max_risk_inr":          1_000,   # ₹1,000 risk per trade (locked from Strategy A learning)
    "max_capital_inr":       50_000,  # ₹50,000 max position size

    # ── Trade management ─────────────────────────────────────────────────────
    "hard_exit_days":        5,       # exit Day 5 at 3:15 PM regardless — short-term system
    "trail_sl_to_prev_day_low": True, # every morning move SL to previous day's low

    # ── Scanner timing (IST) ─────────────────────────────────────────────────
    "scan_interval_sec":     300,     # poll every 5 minutes
    "scan_start_ist":        "09:30", # skip the opening auction noise
    "scan_end_ist":          "15:00", # stop 30 min before close — avoid end-of-day traps
}

# ── Telegram config — fill before running ────────────────────────────────────
TELEGRAM_BOT_TOKEN = ""   # from @BotFather
TELEGRAM_CHAT_ID   = ""   # your personal chat ID or group
