"""
Strategy C — Live scanner.

Architecture:
  9:00 AM  → run daily_filter.screen_universe() → candidate list
  9:30 AM  → start polling loop every 5 minutes
             for each candidate: fetch 15-min candles → detect setup
             if signal: send Telegram alert, mark alerted (no repeat same day)
  3:00 PM  → stop scanning
  repeat next trading day

Rate-limiting: 0.15s sleep between each yfinance fetch.
With ~30 candidates, one scan cycle takes ~5–10 seconds.
"""

from __future__ import annotations
import sys
import time
from pathlib import Path
from datetime import datetime, date, time as dtime

import pandas as pd
import pytz

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from .config import PARAMS
from .daily_filter import screen_universe
from .intraday_setup import fetch_intraday, detect
from .alerts import send, send_market_open_summary

IST = pytz.timezone("Asia/Kolkata")


def _now_ist() -> datetime:
    return datetime.now(IST)


def _is_trading_day() -> bool:
    return _now_ist().weekday() < 5   # Mon–Fri


def _scan_window_open() -> bool:
    now  = _now_ist().time().replace(tzinfo=None)
    h1, m1 = map(int, PARAMS["scan_start_ist"].split(":"))
    h2, m2 = map(int, PARAMS["scan_end_ist"].split(":"))
    return dtime(h1, m1) <= now <= dtime(h2, m2)


class Scanner:
    def __init__(self, verbose: bool = True):
        self.verbose             = verbose
        self.candidates: list[dict] = []
        self.alerted_today:set[str] = set()
        self.last_screen_date: date | None = None

    # ── Daily pre-filter ─────────────────────────────────────────────────────

    def _refresh_candidates(self):
        today = _now_ist().date()
        if self.last_screen_date == today:
            return

        print(f"\n[{_now_ist().strftime('%H:%M:%S')}] Running daily pre-filter...")
        self.candidates       = screen_universe(verbose=self.verbose)
        self.alerted_today    = set()
        self.last_screen_date = today

        send_market_open_summary(self.candidates)

    # ── Single scan pass ─────────────────────────────────────────────────────

    def _scan_once(self) -> int:
        signals_found = 0

        for meta in self.candidates:
            symbol = meta["symbol"]
            if symbol in self.alerted_today:
                continue

            df = fetch_intraday(symbol)
            time.sleep(0.15)   # be polite to yfinance

            if df is None:
                continue

            signal = detect(df, meta)
            if signal is None:
                continue

            self.alerted_today.add(symbol)
            signals_found += 1

            print(
                f"\n  ⚡ SIGNAL  {symbol}"
                f"  Entry ₹{signal['entry_low']:,.0f}–₹{signal['entry_high']:,.0f}"
                f"  Stop ₹{signal['stop']:,.0f}"
                f"  Target ₹{signal['target']:,.0f}"
                f"  Risk ₹{signal['actual_risk_inr']:,.0f}"
            )
            send(signal)

        if self.verbose:
            scanned = len([c for c in self.candidates if c["symbol"] not in self.alerted_today])
            print(
                f"  [{_now_ist().strftime('%H:%M')}] "
                f"Scanned {scanned} stocks — {signals_found} signal(s)"
            )

        return signals_found

    # ── Main loop ────────────────────────────────────────────────────────────

    def run(self):
        print("=" * 50)
        print("  Strategy C Scanner")
        print(f"  Interval  : {PARAMS['scan_interval_sec']}s")
        print(f"  Window    : {PARAMS['scan_start_ist']}–{PARAMS['scan_end_ist']} IST")
        print(f"  Timeframe : {PARAMS['intraday_interval']} candles")
        print("=" * 50)

        while True:
            try:
                if not _is_trading_day():
                    print(f"[{_now_ist().strftime('%a %H:%M')}] Weekend. Sleeping 1 hour.")
                    time.sleep(3600)
                    continue

                if _scan_window_open():
                    self._refresh_candidates()
                    self._scan_once()
                    time.sleep(PARAMS["scan_interval_sec"])
                else:
                    now_t = _now_ist().time()
                    h, m  = map(int, PARAMS["scan_start_ist"].split(":"))
                    open_t = dtime(h, m)
                    if now_t < open_t:
                        # Pre-market: run daily filter early so it's ready at 9:30
                        self._refresh_candidates()
                        secs = (
                            (open_t.hour - now_t.hour) * 3600
                            + (open_t.minute - now_t.minute) * 60
                        )
                        print(f"[{_now_ist().strftime('%H:%M')}] Pre-market. "
                              f"Scan starts in {max(secs,0)//60} min.")
                        time.sleep(max(min(secs, 600), 60))
                    else:
                        # Post-market
                        print(f"[{_now_ist().strftime('%H:%M')}] Market closed. "
                              f"Sleeping 10 min.")
                        time.sleep(600)

            except KeyboardInterrupt:
                print("\nScanner stopped by user.")
                break
            except Exception as exc:
                print(f"[ERROR] {exc}")
                time.sleep(60)
