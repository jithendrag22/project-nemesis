"""
Strategy C — Telegram alert formatter and sender.
"""

from __future__ import annotations
import requests
import pandas as pd

from .config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


def _season_label(score: float) -> tuple[str, str]:
    if score >= 65:
        return "Strong tailwind", "🔥"
    if score >= 50:
        return "Neutral", "→"
    if score >= 35:
        return "Weak (acceptable)", "▽"
    return "Very Weak", "✗"


def format_signal(signal: dict) -> str:
    label, icon = _season_label(signal["season_score"])

    sig_time  = pd.Timestamp(signal["signal_time"])
    valid_till = sig_time + pd.Timedelta(minutes=signal["entry_valid_min"])
    valid_str  = valid_till.strftime("%H:%M")

    lines = [
        f"⚡ STRATEGY C  |  {signal['symbol']}",
        f"{'─' * 38}",
        f"Sector   : {signal['sector']}",
        f"Season   : {icon} {signal['season_score']:.0f}%  ({label})",
        f"",
        f"ENTRY ZONE  ₹{signal['entry_low']:,.2f}  →  ₹{signal['entry_high']:,.2f}",
        f"Valid until {valid_str} IST  (if price above ₹{signal['entry_high']:,.2f} → skip)",
        f"",
        f"Stop loss  ₹{signal['stop']:,.2f}  (swing low {signal['risk_pct']:.1f}% below entry)",
        f"Target     ₹{signal['target']:,.2f}  ({signal['rr_ratio']:.0f}:1 R:R)",
        f"",
        f"Qty  {signal['shares']} shares",
        f"Capital  ₹{signal['capital_required']:,.0f}",
        f"Risk     ₹{signal['actual_risk_inr']:,.0f}  (1R)",
        f"",
        f"─── Context ─────────────────────────",
        f"ADX(D)   {signal['adx_daily']:.0f}  (trend strength)",
        f"RSI(15m) {signal['rsi14_15m']:.0f}  (pullback exhausted)",
        f"EMA20    ₹{signal['ema20_15m']:,.2f}  (15-min support)",
        f"RS       {signal['rs_3m_pct']:+.1f}%  vs Nifty 3m",
        f"Pullback {signal['pullback_candles']} candles → EMA bounce",
        f"",
        f"─── Trade management ─────────────────",
        f"• SL trails to prev-day Low each morning",
        f"• Hard exit: Day 5 at 3:15 PM",
        f"• If price gaps above ₹{signal['entry_high']:,.2f} at open → skip",
    ]
    return "\n".join(lines)


def send(signal: dict, dry_run: bool = False) -> bool:
    """
    Send signal to Telegram. If not configured, print to console.
    dry_run=True prints without sending.
    """
    text = format_signal(signal)

    if dry_run or not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("\n" + text + "\n")
        return True

    try:
        url  = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        resp = requests.post(
            url,
            json={"chat_id": TELEGRAM_CHAT_ID, "text": text},
            timeout=10,
        )
        return resp.status_code == 200
    except Exception as e:
        print(f"[Telegram] Send failed: {e}")
        print(text)
        return False


def send_market_open_summary(candidates: list[dict]) -> None:
    """Send a morning briefing with today's candidate list."""
    if not candidates:
        msg = "⚡ Strategy C: 0 candidates today — no scans will run."
    else:
        lines = ["⚡ Strategy C — Morning candidates\n"]
        for c in sorted(candidates, key=lambda x: x["adx"], reverse=True):
            lines.append(
                f"• {c['symbol']:<18} ADX {c['adx']:.0f}  "
                f"RS {c['rs_3m_pct']:+.1f}%  "
                f"Season {c['season_score']:.0f}%  "
                f"({c['sector']})"
            )
        lines.append(f"\nScanning {len(candidates)} stocks every 5 min.")
        msg = "\n".join(lines)

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(msg)
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": msg},
            timeout=10,
        )
    except Exception:
        print(msg)
