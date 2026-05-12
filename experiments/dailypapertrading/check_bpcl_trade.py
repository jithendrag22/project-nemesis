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
MAPPING_FILE = PROJECT_DIR / "experiments" / "nse_movers" / "dhan_instruments.csv"

# Dhan Credentials
CLIENT_ID = "1103466045"
ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzc4NTg5ODAyLCJpYXQiOjE3Nzg1MDM0MDIsInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTAzNDY2MDQ1In0.qo73h3_PLQSg55FDyF-y7asXFFZv-fIcczyktA5MLs6mg-ArVRgDy_HMcYPfhSCGuTSKwBt6px3xpR2EyFg7VA"

dhan = dhanhq(DhanContext(CLIENT_ID, ACCESS_TOKEN))

def check_trade_status(symbol, entry, sl, target1, shares):
    mapping = pd.read_csv(MAPPING_FILE)
    symbol_to_id = dict(zip(mapping['SEM_TRADING_SYMBOL'], mapping['SEM_SMST_SECURITY_ID']))
    sec_id = str(symbol_to_id.get(symbol))
    
    today_str = datetime.now().strftime('%Y-%m-%d')
    
    print(f"Fetching intraday data for {symbol} to check trade status...")
    res = dhan.intraday_minute_data(
        security_id=sec_id, exchange_segment='NSE_EQ',
        instrument_type='EQUITY', from_date=today_str, to_date=today_str
    )
    
    if res.get('status') != 'success':
        print("Failed to fetch data:", res)
        return
        
    data = res.get('data', {})
    if not data or len(data.get('open', [])) < 2:
        print("Not enough data yet. Waiting for candles.")
        return
        
    # We skip the first candle (09:15-09:20) because that was the setup candle!
    # The trade can only trigger from the 2nd candle onwards.
    highs = data['high'][1:]
    lows = data['low'][1:]
    closes = data['close'][1:]
    
    entry_triggered = False
    shares_held = 0
    pnl = 0.0
    status = "Pending Trigger"
    current_sl = sl
    last_price = closes[-1]
    
    for i in range(len(highs)):
        h = highs[i]
        l = lows[i]
        c = closes[i]
        
        if not entry_triggered:
            if h >= entry:
                entry_triggered = True
                shares_held = shares
                print(f"✅ Trade TRIGGERED at exactly ₹{entry:.2f}!")
                
                # If it wicked down in the SAME candle it triggered
                if l <= current_sl:
                    print(f"❌ Stop Loss hit in the same trigger candle at ₹{current_sl:.2f}!")
                    pnl -= (entry - current_sl) * shares_held
                    shares_held = 0
                    status = "Stopped Out"
                    break
            else:
                continue
                
        if entry_triggered and shares_held > 0:
            if l <= current_sl:
                print(f"❌ STOP LOSS HIT at ₹{current_sl:.2f}!")
                pnl += (current_sl - entry) * shares_held
                shares_held = 0
                status = "Stopped Out"
                break
                
            if h >= target1 and shares_held == shares:
                print(f"🎯 TARGET 1 HIT at ₹{target1:.2f}!")
                half = shares // 2
                pnl += (target1 - entry) * half
                shares_held -= half
                current_sl = entry # Trail SL to Breakeven
                print(f"🛡️ Stop Loss trailed to Breakeven (₹{entry:.2f})")
                status = "T1 Hit, Running 2nd Half"

    print("\n" + "="*50)
    print("📊 CURRENT TRADE STATUS")
    print("="*50)
    print(f"Current Time : {datetime.now().strftime('%I:%M %p')}")
    print(f"Stock        : {symbol}")
    print(f"Last Price   : ₹{last_price:.2f}")
    
    if not entry_triggered:
        print(f"Status       : {status} (Entry not crossed yet)")
    else:
        print(f"Status       : {status}")
        
        # Calculate floating PnL if shares are still held
        floating_pnl = 0
        if shares_held > 0:
            floating_pnl = (last_price - entry) * shares_held
            
        total_pnl = pnl + floating_pnl
        print(f"Realized PnL : ₹{pnl:.2f}")
        print(f"Floating PnL : ₹{floating_pnl:.2f}")
        print(f"Total PnL    : ₹{total_pnl:.2f}")
    print("="*50)

if __name__ == "__main__":
    check_trade_status(
        symbol="BPCL",
        entry=292.85,
        sl=285.57,
        target1=300.13,
        shares=274
    )
