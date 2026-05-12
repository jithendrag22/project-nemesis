import yfinance as yf
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, date
import time
import warnings
from dhanhq import dhanhq
from dhanhq.dhan_context import DhanContext

# ── Credentials ────────────────────────────────────────────────────
CLIENT_ID = "1103466045"
ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzc4NTg5ODAyLCJpYXQiOjE3Nzg1MDM0MDIsInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTAzNDY2MDQ1In0.qo73h3_PLQSg55FDyF-y7asXFFZv-fIcczyktA5MLs6mg-ArVRgDy_HMcYPfhSCGuTSKwBt6px3xpR2EyFg7VA"

# Initialize Dhan
dhan_context = DhanContext(CLIENT_ID, ACCESS_TOKEN)
dhan = dhanhq(dhan_context)

# ── Configuration ──────────────────────────────────────────────────
PROJECT_DIR = Path(__file__).parent.parent.parent
BHAVCOPY_DIR = Path(__file__).parent / "bhavcopy_data"
UNIVERSE_FILE = PROJECT_DIR / "data" / "universe" / "fo_stocks.csv"

GAP_MIN = 2.0
GAP_MAX = 15.0
CAPITAL = 100000
MAX_RISK_PCT = 0.02 # Max 2% risk per trade (e.g., ₹2,000)

def load_fo_universe():
    if not UNIVERSE_FILE.exists():
        return set()
    fo = pd.read_csv(UNIVERSE_FILE)
    return set(fo["symbol"].str.replace(".NS", "").tolist())

def load_all_dhan_symbols():
    mapping_file = PROJECT_DIR / "experiments" / "nse_movers" / "dhan_instruments.csv"
    if not mapping_file.exists():
        return []
    mapping = pd.read_csv(mapping_file)
    return mapping['SEM_TRADING_SYMBOL'].tolist()
    fo = pd.read_csv(UNIVERSE_FILE)
    return set(fo["symbol"].str.replace(".NS", "").tolist())

def get_yfinance_data(symbols, fo_set):
    """Fetch prev_close and open prices using yfinance."""
    print(f"Fetching live daily data for {len(symbols)} stocks via Yahoo Finance... (Takes ~15 seconds)")
    yf_symbols = [f"{sym}.NS" for sym in symbols]
    
    data = yf.download(yf_symbols, period="5d", interval="1d", progress=False, auto_adjust=True, threads=50)
    
    results = []
    if 'Open' in data.columns and 'Close' in data.columns:
        for sym in symbols:
            yf_sym = f"{sym}.NS"
            try:
                if yf_sym in data['Close'] and yf_sym in data['Open']:
                    closes = data['Close'][yf_sym].dropna()
                    opens = data['Open'][yf_sym].dropna()
                    if len(closes) >= 2 and len(opens) >= 1:
                        prev_close = closes.iloc[-2]
                        today_open = opens.iloc[-1]
                        is_fo_flag = sym in fo_set
                        results.append({
                            'SYMBOL': sym,
                            'prev_close': prev_close,
                            'open': today_open,
                            'is_fo': is_fo_flag
                        })
            except Exception:
                pass
    return pd.DataFrame(results)

def run_dhan_scanner():
    now = datetime.now()
    print("\n" + "="*80)
    print(f"⚡ V2 HYBRID SCANNER (All Stocks + F&O Priority) — {now.strftime('%I:%M:%S %p')}")
    print("="*80)
    
    # 1. Load Universe and Get Live Data
    all_symbols = load_all_dhan_symbols()
    fo_set = load_fo_universe()
    
    if not all_symbols:
        print("No universe found. Please generate dhan_instruments.csv")
        return
        
    print(f"Scanning {len(all_symbols)} total stocks (F&O prioritized)...")
    base_df = get_yfinance_data(all_symbols, fo_set)
    
    if base_df.empty:
        print("Waiting for market to open (or yfinance delayed). Try again in a minute.")
        return
        
    # 3. Calculate Gaps
    base_df['gap_pct'] = ((base_df['open'] - base_df['prev_close']) / base_df['prev_close']) * 100
    gaps = base_df[(base_df['gap_pct'] <= -GAP_MIN) & (base_df['gap_pct'] >= -GAP_MAX)].copy()
    
    if gaps.empty:
        print(f"\n❌ NO TRADES TODAY. No stock gapped down between {GAP_MIN}% and {GAP_MAX}%.")
        return
        
    # Sort candidates: F&O first, then by largest gap
    gaps['sort_score'] = gaps['is_fo'].astype(int) * 1000 + gaps['gap_pct'].abs()
    gaps = gaps.sort_values('sort_score', ascending=False)
    
    candidates = gaps.head(10) # Top 10 to process via Dhan
    
    print(f"\n🎯 FOUND {len(gaps)} GAP-DOWN CANDIDATES. Checking Top 10 via Dhan API...")
    print(f"{'Stock':<15} {'F&O?':<6} {'Prev Close':>10} {'Open':>10} {'Gap %':>10}")
    print("-" * 60)
    for _, row in candidates.iterrows():
        print(f"{row['SYMBOL']:<15} {'Yes' if row['is_fo'] else 'No':<6} {row['prev_close']:>10.2f} {row['open']:>10.2f} {row['gap_pct']:>9.2f}%")
    
    is_after_920 = (now.hour > 9) or (now.hour == 9 and now.minute >= 20)
    if not is_after_920:
        print("\n⏳ Time is before 9:20 AM. Waiting for first 5-min candle to close.")
        print("⚡ ACTION: Run this script again at exactly 9:21 AM to get entry signals from Dhan.")
        return
        
    # 4. Fetch precise 5-min candle from Dhan for candidates
    print("\nFetching precise 5-min candles directly from Dhan API...")
    
    mapping_file = PROJECT_DIR / "experiments" / "nse_movers" / "dhan_instruments.csv"
    if not mapping_file.exists():
        print("Missing dhan_instruments.csv! Please download it.")
        return
        
    mapping = pd.read_csv(mapping_file)
    symbol_to_id = dict(zip(mapping['SEM_TRADING_SYMBOL'], mapping['SEM_SMST_SECURITY_ID']))
    
    valid_trades = []
    today_str = now.strftime('%Y-%m-%d')
    
    for _, row in candidates.iterrows():
        sym = row['SYMBOL']
        sec_id = str(symbol_to_id.get(sym))
        
        if not sec_id or sec_id == 'None':
            print(f"  {sym}: Security ID not found.")
            continue
            
        try:
            res = dhan.intraday_minute_data(
                security_id=sec_id,
                exchange_segment='NSE_EQ',
                instrument_type='EQUITY',
                from_date=today_str,
                to_date=today_str
            )
            time.sleep(0.5) # Prevent DH-904 Rate Limit Error
            
            if res.get('status') == 'success':
                data = res.get('data', {})
                if 'open' in data and len(data['open']) > 0:
                    fc_open = data['open'][0]
                    fc_high = data['high'][0]
                    fc_low = data['low'][0]
                    fc_close = data['close'][0]
                    
                    is_green = fc_close >= fc_open
                    
                    if is_green:
                        valid_trades.append({
                            'symbol': sym,
                            'is_fo': row['is_fo'],
                            'gap_pct': row['gap_pct'],
                            'entry': fc_high,
                            'sl': fc_low,
                            'fc_close': fc_close,
                            'fc_open': fc_open
                        })
            else:
                print(f"  {sym}: API Error -> {res.get('remarks', {}).get('error_message', res)}")
                
        except Exception as e:
            print(f"  {sym}: Exception -> {e}")
            
    if not valid_trades:
        print("\n❌ NO TRADES TODAY. All top gap-down stocks formed a RED first candle.")
        return
        
    print("\n✅ VALID SIGNALS FOUND (Green First Candle):")
    for t in valid_trades:
         print(f"  🟢 {t['symbol']:<12} {'[F&O]' if t['is_fo'] else '[CASH]' :<6} Gap: {t['gap_pct']:>5.2f}%")
         
    # Pick the top 3
    top_picks = valid_trades[:3]
    
    print("\n" + "="*80)
    print(f"🚨 OFFICIAL TOP PICKS FOR TODAY (Up to 3)")
    print("="*80)
    
    for i, pick in enumerate(top_picks):
        entry = pick['entry']
        sl = pick['sl']
        risk = entry - sl
        
        if risk <= 0:
            print(f"⚠️ Error calculating risk for {pick['symbol']}.")
            continue
            
        target1 = entry + risk
        target2 = entry + (risk * 2)
        
        # FIXED RISK POSITION SIZING
        max_risk_rs = CAPITAL * MAX_RISK_PCT
        ideal_shares = int(max_risk_rs / risk)
        max_affordable_shares = int(CAPITAL / entry)
        shares = min(ideal_shares, max_affordable_shares)
        
        if shares == 0:
            print(f"⚠️ Cannot afford 1 share of {pick['symbol']} within risk limits.")
            continue
            
        risk_rs = risk * shares
        
        print(f"\n--- ⭐ PICK {i+1}: {pick['symbol']} {'(F&O)' if pick['is_fo'] else '(CASH)'} ---")
        print(f"Gap Size   : {pick['gap_pct']:.2f}%")
        print(f"1st Candle : GREEN (Open ₹{pick['fc_open']:.2f} -> Close ₹{pick['fc_close']:.2f})")
        print(f"BUY ORDER  : Buy {shares} shares if price crosses ₹{entry:.2f}")
        print(f"STOP LOSS  : ₹{sl:.2f}")
        print(f"TARGET 1   : ₹{target1:.2f} (Sell {shares//2} shares here)")
        print(f"TARGET 2   : ₹{target2:.2f} (or Trail SL)")
        print(f"Total Risk : ₹{risk_rs:,.2f} ({risk_rs/CAPITAL*100:.2f}% of capital)")
    
    print("\n" + "="*80)
    print("--- RULES ---")
    print("1. If price hits Stop Loss before Entry, CANCEL THE ORDER.")
    print("2. When Target 1 hits, move Stop Loss to Entry price (Breakeven).")
    print("3. Exit all remaining position at 3:15 PM.")
    print("="*80)

if __name__ == "__main__":
    run_dhan_scanner()
