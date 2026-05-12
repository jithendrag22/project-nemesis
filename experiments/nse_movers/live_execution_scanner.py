import yfinance as yf
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import argparse
import warnings

warnings.filterwarnings('ignore')

# ── Configuration ──────────────────────────────────────────────────
PROJECT_DIR = Path(__file__).parent.parent.parent
UNIVERSE_FILE = PROJECT_DIR / "data" / "universe" / "fo_stocks.csv"

GAP_MIN = 2.0
GAP_MAX = 15.0
CAPITAL = 100000

def load_fo_universe() -> list[str]:
    """Load F&O stock universe."""
    if not UNIVERSE_FILE.exists():
        print(f"⚠️ Universe file not found at {UNIVERSE_FILE}")
        return []
    base = pd.read_csv(UNIVERSE_FILE)
    return base["symbol"].tolist()

def fetch_live_data(symbols: list[str]) -> pd.DataFrame:
    """Fetch live data for all F&O stocks using yfinance."""
    print(f"Fetching live data for {len(symbols)} stocks... (this takes ~10 seconds)")
    
    # Download 2 days of daily data to get Prev Close and Today's Open
    data = yf.download(symbols, period="5d", interval="1d", progress=False, auto_adjust=True)
    
    # Also fetch the 5-minute intraday data to get the first candle of today
    intraday = yf.download(symbols, period="1d", interval="5m", progress=False, auto_adjust=True)
    
    results = []
    
    # Process the data
    for sym in symbols:
        try:
            # Daily data
            closes = data['Close'][sym].dropna()
            opens = data['Open'][sym].dropna()
            
            if len(closes) < 2 or len(opens) < 1:
                continue
                
            prev_close = closes.iloc[-2]
            today_open = opens.iloc[-1]
            
            # Gap calculation
            gap_pct = ((today_open - prev_close) / prev_close) * 100
            
            # Intraday data (First 5-min candle)
            first_candle_color = "UNKNOWN"
            fc_open = fc_high = fc_low = fc_close = 0
            
            if sym in intraday['Close'] and not intraday['Close'][sym].dropna().empty:
                sym_intra = intraday.xs(sym, level='Ticker', axis=1) if 'Ticker' in intraday.columns.names else intraday
                
                # If using multi-index columns, select just this ticker
                if isinstance(intraday.columns, pd.MultiIndex):
                    sym_intra = intraday.loc[:, (slice(None), sym)]
                    sym_intra.columns = sym_intra.columns.get_level_values(0)
                
                sym_intra = sym_intra.dropna(subset=['Close'])
                
                if not sym_intra.empty:
                    # Get the very first candle of today
                    first_candle = sym_intra.iloc[0]
                    fc_open = first_candle['Open']
                    fc_high = first_candle['High']
                    fc_low = first_candle['Low']
                    fc_close = first_candle['Close']
                    
                    first_candle_color = "GREEN" if fc_close >= fc_open else "RED"
            
            results.append({
                'symbol': sym.replace('.NS', ''),
                'prev_close': prev_close,
                'open': today_open,
                'gap_pct': gap_pct,
                'fc_color': first_candle_color,
                'fc_high': fc_high,
                'fc_low': fc_low
            })
            
        except Exception as e:
            pass
            
    return pd.DataFrame(results)

def run_scanner():
    now = datetime.now()
    time_str = now.strftime("%I:%M %p")
    
    print("\n" + "="*70)
    print(f"🚀 V2 INSTITUTIONAL LIVE SCANNER — {now.strftime('%A, %b %d %Y | %I:%M %p')}")
    print("="*70)
    
    # 1. Load Universe
    symbols = load_fo_universe()
    if not symbols:
        return
        
    # 2. Fetch Data
    df = fetch_live_data(symbols)
    if df.empty:
        print("No data retrieved. Market might be closed or API is down.")
        return
        
    # 3. Filter for gap downs
    gaps = df[(df['gap_pct'] <= -GAP_MIN) & (df['gap_pct'] >= -GAP_MAX)].copy()
    gaps['abs_gap'] = gaps['gap_pct'].abs()
    gaps = gaps.sort_values('abs_gap', ascending=False)
    
    if gaps.empty:
        print(f"\n❌ NO TRADES TODAY. No F&O stock gapped down between {GAP_MIN}% and {GAP_MAX}%.")
        return
        
    print(f"\n🎯 FOUND {len(gaps)} GAP-DOWN CANDIDATES:")
    print("-" * 60)
    
    # 4. Determine Phase (Before 9:20 vs After 9:20)
    is_after_920 = (now.hour > 9) or (now.hour == 9 and now.minute >= 20)
    
    if not is_after_920:
        print("⏳ Time is before 9:20 AM. Waiting for first 5-min candle to close.")
        print("Watchlist for 9:20 AM:\n")
        print(f"{'Stock':<15} {'Prev Close':>10} {'Open':>10} {'Gap %':>10}")
        print("-" * 60)
        for _, row in gaps.iterrows():
            print(f"{row['symbol']:<15} {row['prev_close']:>10.2f} {row['open']:>10.2f} {row['gap_pct']:>9.2f}%")
        
        print("\n⚡ ACTION: Run this script again at exactly 9:21 AM to get entry signals.")
        return
        
    # AFTER 9:20 AM -> We have first candle data
    green_gaps = gaps[gaps['fc_color'] == 'GREEN']
    red_gaps = gaps[gaps['fc_color'] == 'RED']
    
    if green_gaps.empty:
        print("❌ NO TRADES TODAY. All gap-down stocks formed a RED first candle.")
        print("\nRed Candles (Skipped):")
        for sym in red_gaps['symbol']:
            print(f"  - {sym}")
        return
        
    # We have green candles! Present the best trade.
    top_pick = green_gaps.iloc[0]
    
    entry = top_pick['fc_high']
    sl = top_pick['fc_low']
    risk = entry - sl
    
    if risk <= 0:
        print(f"⚠️ Error calculating risk for {top_pick['symbol']}. FC High: {entry}, FC Low: {sl}")
        return
        
    target1 = entry + risk
    target2 = entry + (risk * 2)
    shares = int(CAPITAL / entry)
    risk_rs = risk * shares
    
    print("\n✅ VALID SIGNALS FOUND (Green First Candle):")
    for _, row in green_gaps.iterrows():
         print(f"  🟢 {row['symbol']:<12} Gap: {row['gap_pct']:>5.2f}%")
         
    print("\n" + "="*70)
    print(f"🚨 TOP PICK EXECUTION PLAN: {top_pick['symbol']}")
    print("="*70)
    
    print(f"Gap Size   : {top_pick['gap_pct']:.2f}%")
    print(f"1st Candle : GREEN (Open {top_pick['open']:.2f} -> Close {top_pick['fc_close'] if 'fc_close' in top_pick else 'higher'})")
    
    print("\n--- ORDER DETAILS ---")
    print(f"BUY ORDER  : Buy {shares} shares if price crosses ₹{entry:.2f}")
    print(f"STOP LOSS  : ₹{sl:.2f}")
    print(f"TARGET 1   : ₹{target1:.2f} (Sell {shares//2} shares here)")
    print(f"TARGET 2   : ₹{target2:.2f} (or Trail SL)")
    print("-" * 21)
    print(f"Capital Req: ₹{(shares * entry):,.2f}")
    print(f"Total Risk : ₹{risk_rs:,.2f} ({risk_rs/CAPITAL*100:.2f}% of capital)")
    
    print("\n--- RULES ---")
    print("1. If price hits Stop Loss before Entry, CANCEL THE ORDER.")
    print("2. When Target 1 hits, move Stop Loss to Entry price (Breakeven).")
    print("3. Exit all remaining position at 3:15 PM.")
    print("="*70)

if __name__ == "__main__":
    run_scanner()
