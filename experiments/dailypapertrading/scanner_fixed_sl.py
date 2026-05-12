import yfinance as yf
import pandas as pd
from pathlib import Path
from datetime import datetime
import time
import warnings
from dhanhq import dhanhq
from dhanhq.dhan_context import DhanContext

warnings.filterwarnings('ignore')

# ── Configuration ──────────────────────────────────────────────────
PROJECT_DIR = Path(__file__).parent.parent.parent
UNIVERSE_FILE = PROJECT_DIR / "data" / "universe" / "fo_stocks.csv"
MAPPING_FILE = PROJECT_DIR / "experiments" / "nse_movers" / "dhan_instruments.csv"

# Dhan Credentials
CLIENT_ID = "1103466045"
ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzc4NTg5ODAyLCJpYXQiOjE3Nzg1MDM0MDIsInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTAzNDY2MDQ1In0.qo73h3_PLQSg55FDyF-y7asXFFZv-fIcczyktA5MLs6mg-ArVRgDy_HMcYPfhSCGuTSKwBt6px3xpR2EyFg7VA"

# Trading Parameters
GAP_MIN = 2.0
GAP_MAX = 15.0
CAPITAL = 100000
MAX_RISK_PCT = 0.02 # Max 2% risk

dhan = dhanhq(DhanContext(CLIENT_ID, ACCESS_TOKEN))

DAILY_DATA_DIR = PROJECT_DIR / "experiments" / "backtesting" / "data" / "daily"

def get_dhan_live_gaps(fo_symbols, symbol_to_id):
    print("Fetching live pre-market gap data via 100% Dhan API... (~3 mins)")
    results = []
    
    now = datetime.now()
    today_str = now.strftime('%Y-%m-%d')
    from_date_str = (now - pd.Timedelta(days=10)).strftime('%Y-%m-%d')
    
    for i, sym in enumerate(fo_symbols):
        sec_id = str(symbol_to_id.get(sym))
        if not sec_id or sec_id == 'None': continue
            
        try:
            # 1. Get true prev_close from Dhan Historical API dynamically
            hist_res = dhan.historical_daily_data(
                security_id=sec_id, exchange_segment='NSE_EQ',
                instrument_type='EQUITY', expiry_code=0, 
                from_date=from_date_str, to_date=today_str
            )
            time.sleep(0.4)
            
            prev_close = None
            if hist_res.get('status') == 'success':
                data = hist_res.get('data', {})
                if 'close' in data and len(data['close']) > 0:
                    prev_close = data['close'][-1] # The most recent closed day
                    
            if not prev_close:
                continue
            
            # 2. Get today's Open from Dhan Intraday API
            res = dhan.intraday_minute_data(
                security_id=sec_id, exchange_segment='NSE_EQ',
                instrument_type='EQUITY', from_date=today_str, to_date=today_str
            )
            time.sleep(0.4)
            
            if res.get('status') == 'success':
                data = res.get('data', {})
                if 'open' in data and len(data['open']) > 0:
                    today_open = data['open'][0]
                    gap_pct = ((today_open - prev_close) / prev_close) * 100
                    
                    if -GAP_MAX <= gap_pct <= -GAP_MIN:
                        results.append({
                            'SYMBOL': sym,
                            'prev_close': prev_close,
                            'open': today_open,
                            'gap_pct': gap_pct,
                            'is_fo': True,
                            # Pre-cache the 1st candle data so we don't have to fetch it again later!
                            'fc_open': today_open,
                            'fc_high': data['high'][0],
                            'fc_low': data['low'][0],
                            'fc_close': data['close'][0]
                        })
        except:
            pass
            
    return pd.DataFrame(results)

def run_fixed_scanner():
    now = datetime.now()
    print("\n" + "="*80)
    print(f"📉 STRATEGY B: FIXED 0.75% SL SCANNER — {now.strftime('%I:%M:%S %p')}")
    print("="*80)
    
    if not MAPPING_FILE.exists() or not UNIVERSE_FILE.exists():
        print("Required data files missing.")
        return
        
    mapping = pd.read_csv(MAPPING_FILE)
    all_symbols = mapping['SEM_TRADING_SYMBOL'].tolist()
    fo_set = set(pd.read_csv(UNIVERSE_FILE)["symbol"].str.replace(".NS", "").tolist())
    symbol_to_id = dict(zip(mapping['SEM_TRADING_SYMBOL'], mapping['SEM_SMST_SECURITY_ID']))
    
    fo_list = list(fo_set)
    gaps = get_dhan_live_gaps(fo_list, symbol_to_id)
    if gaps.empty:
        print("Waiting for market to open or no gaps found.")
        return
        
    # Data is already filtered for GAP_MIN and GAP_MAX inside get_dhan_live_gaps
    
    if gaps.empty:
        print(f"\n❌ NO TRADES TODAY. No stock gapped down between -{GAP_MIN}% and -{GAP_MAX}%.")
        return
        
    gaps['sort_score'] = gaps['is_fo'].astype(int) * 1000 + gaps['gap_pct'].abs()
    gaps = gaps.sort_values('sort_score', ascending=False)
    candidates = gaps.head(10)
    
    print(f"\n🎯 FOUND {len(gaps)} GAP-DOWN CANDIDATES. Top 10 Priority List:")
    print(f"{'Stock':<15} {'F&O?':<6} {'Prev Close':>10} {'Open':>10} {'Gap %':>10}")
    print("-" * 60)
    for _, row in candidates.iterrows():
        print(f"{row['SYMBOL']:<15} {'Yes' if row['is_fo'] else 'No':<6} {row['prev_close']:>10.2f} {row['open']:>10.2f} {row['gap_pct']:>9.2f}%")
    
    # Because we already fetched the 5-min candle inside get_dhan_live_gaps, we don't need to re-fetch!
    trade_pick = None
    
    for _, row in candidates.iterrows():
        if row['fc_close'] >= row['fc_open']: # Green Candle Confirmed
            trade_pick = row.to_dict()
            trade_pick['symbol'] = trade_pick['SYMBOL']
            break # We only take 1 trade per day!
            
    if not trade_pick:
        print("\n❌ NO TRADES TODAY. All top gap-down stocks formed a RED first candle.")
        return
        
    # --- FIXED 0.75% RUNNER LOGIC ---
    entry = trade_pick['fc_high']
    sl = entry * 0.9925 # Fixed 0.75% SL
    target = entry * 1.0150 # Fixed 1.50% Target
    risk = entry - sl
    
    shares = min(int((CAPITAL * MAX_RISK_PCT) / risk), int(CAPITAL / entry)) if risk > 0 else 0
    
    if shares == 0:
        print("\n⚠️ Cannot calculate valid position size.")
        return
        
    print("\n" + "★"*60)
    print("🛡️ OFFICIAL PAPER TRADE INSTRUCTIONS (FIXED 0.75% SL) 🛡️")
    print("★"*60)
    print(f"STOCK       : {trade_pick['symbol']} {'[F&O]' if trade_pick['is_fo'] else '[CASH]'}")
    print(f"GAP DOWN    : {trade_pick['gap_pct']:.2f}%")
    print(f"1st CANDLE  : GREEN (Open ₹{trade_pick['fc_open']:.2f} -> Close ₹{trade_pick['fc_close']:.2f})")
    print("-" * 60)
    print(f"🟩 BUY ORDER  : Buy {shares} shares at exactly ₹{entry:.2f}")
    print(f"🛑 STOP LOSS  : ₹{sl:.2f} (Strictly -0.75% from Entry)")
    print(f"🎯 TARGET     : ₹{target:.2f} (Sell all {shares} shares here)")
    print("-" * 60)
    print(f"⚠️ RULE       : If stock hits ₹{sl:.2f} BEFORE triggering entry, CANCEL TRADE.")
    print(f"Total Capital Risked : ₹{risk * shares:,.2f} ({MAX_RISK_PCT*100}% of ₹1L)")
    print("★"*60)

if __name__ == "__main__":
    run_fixed_scanner()
