import pandas as pd
from pathlib import Path
from datetime import datetime
import time
import os
import warnings
from dhanhq import dhanhq
from dhanhq.dhan_context import DhanContext

warnings.filterwarnings('ignore')

# Configuration
PROJECT_DIR = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_DIR / "experiments" / "backtesting" / "data"
INTRADAY_DIR = DATA_DIR / "intraday"
INTRADAY_DIR.mkdir(parents=True, exist_ok=True)

GAP_EVENTS_FILE = DATA_DIR / "gap_events.csv"
TRADES_FILE = DATA_DIR / "trades.csv"
MAPPING_FILE = PROJECT_DIR / "experiments" / "nse_movers" / "dhan_instruments.csv"

# Credentials
CLIENT_ID = "1103466045"
ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzc4NTg5ODAyLCJpYXQiOjE3Nzg1MDM0MDIsInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTAzNDY2MDQ1In0.qo73h3_PLQSg55FDyF-y7asXFFZv-fIcczyktA5MLs6mg-ArVRgDy_HMcYPfhSCGuTSKwBt6px3xpR2EyFg7VA"

# Trading Rules
CAPITAL = 100000
MAX_RISK_PCT = 0.02 # Max 2% risk

dhan = dhanhq(DhanContext(CLIENT_ID, ACCESS_TOKEN))
mapping = pd.read_csv(MAPPING_FILE)
symbol_to_id = dict(zip(mapping['SEM_TRADING_SYMBOL'], mapping['SEM_SMST_SECURITY_ID']))

def fetch_5min_data(symbol, date_str):
    """Fetch 5-minute data from Dhan API or local cache."""
    cache_file = INTRADAY_DIR / f"{symbol}_{date_str}.csv"
    if cache_file.exists():
        return pd.read_csv(cache_file)
        
    sec_id = str(symbol_to_id.get(symbol))
    if not sec_id or sec_id == 'None':
        return pd.DataFrame()
        
    max_retries = 3
    for attempt in range(max_retries):
        try:
            res = dhan.intraday_minute_data(
                security_id=sec_id,
                exchange_segment='NSE_EQ',
                instrument_type='EQUITY',
                from_date=date_str,
                to_date=date_str,
                interval=5 # 5 minute interval!
            )
            
            if res.get('status') == 'success':
                data = res.get('data', {})
                if 'open' in data and len(data['open']) > 0:
                    df = pd.DataFrame(data)
                    df.to_csv(cache_file, index=False)
                    time.sleep(0.4) # safe delay
                    return df
                else:
                    # Empty response means no data for that day
                    pd.DataFrame().to_csv(cache_file, index=False)
                    time.sleep(0.4)
                    return pd.DataFrame()
            else:
                err_code = res.get('remarks', {}).get('error_code', '')
                if err_code == 'DH-904':
                    time.sleep(2.0)
                    continue
                else:
                    return pd.DataFrame()
        except Exception as e:
            time.sleep(1.0)
            
    return pd.DataFrame()

def run_backtest():
    print("Starting Event-Driven Backtester...")
    if not GAP_EVENTS_FILE.exists():
        print("Gap events file not found!")
        return
        
    gaps_df = pd.read_csv(GAP_EVENTS_FILE)
    unique_dates = sorted(gaps_df['date'].unique())
    print(f"Total trading days to simulate: {len(unique_dates)}")
    
    trades = []
    
    for i, date_str in enumerate(unique_dates):
        # Print progress every 50 days
        if i % 50 == 0:
            print(f"Simulating Day {i+1}/{len(unique_dates)} ({date_str})...")
            
        day_gaps = gaps_df[gaps_df['date'] == date_str]
        # Already sorted by priority during extraction, but let's be sure:
        day_gaps = day_gaps.sort_values(['is_fo', 'gap_pct'], ascending=[False, True])
        
        trade_taken = False
        
        for _, row in day_gaps.iterrows():
            sym = row['symbol']
            
            # Fetch the 5-min data
            intra_df = fetch_5min_data(sym, date_str)
            if intra_df.empty or len(intra_df) < 2:
                continue
                
            # Assume first row is the 9:15-9:20 candle
            fc = intra_df.iloc[0]
            fc_open = fc['open']
            fc_high = fc['high']
            fc_low = fc['low']
            fc_close = fc['close']
            
            # Check if GREEN candle
            if fc_close < fc_open:
                continue # Red candle, throw it away, check next stock
                
            # We found our GREEN candle! Calculate trade params.
            entry_price = fc_high
            sl_price = fc_low
            risk_per_share = entry_price - sl_price
            
            # If candle is a flat doji or glitchy (risk <= 0), skip
            if risk_per_share <= 0:
                continue
                
            # Fixed Risk Position Sizing
            max_risk_rs = CAPITAL * MAX_RISK_PCT
            ideal_shares = int(max_risk_rs / risk_per_share)
            max_affordable_shares = int(CAPITAL / entry_price)
            shares = min(ideal_shares, max_affordable_shares)
            
            if shares == 0:
                continue # Cannot afford
                
            target1_price = entry_price + risk_per_share
            target2_price = entry_price + (risk_per_share * 2)
            
            # Simulate the rest of the day
            rest_of_day = intra_df.iloc[1:]
            
            status = "PENDING"
            entry_triggered = False
            pnl = 0.0
            current_sl = sl_price
            shares_held = shares
            exit_time = None
            exit_reason = ""
            
            for idx, minute_candle in rest_of_day.iterrows():
                high = minute_candle['high']
                low = minute_candle['low']
                close = minute_candle['close']
                candle_time = minute_candle.get('start_Time', str(idx))
                
                # Check Entry Trigger
                if not entry_triggered:
                    if high > entry_price:
                        # What if it gapped down below SL first?
                        if low < sl_price:
                            # Hit SL before entry -> Invalidated
                            status = "INVALIDATED"
                            exit_reason = "Hit SL before Entry"
                            break
                        else:
                            entry_triggered = True
                    else:
                        continue # Still waiting for entry
                
                # If we are in the trade
                if entry_triggered:
                    # Check Stop Loss
                    if low < current_sl:
                        # Sold remaining shares at SL
                        loss = (current_sl - entry_price) * shares_held
                        pnl += loss
                        shares_held = 0
                        status = "CLOSED"
                        exit_reason = "Stopped Out"
                        exit_time = candle_time
                        break
                        
                    # Check Target 1 (50% exit, move SL to breakeven)
                    if high >= target1_price and shares_held == shares:
                        half_shares = shares // 2
                        profit = (target1_price - entry_price) * half_shares
                        pnl += profit
                        shares_held -= half_shares
                        current_sl = entry_price # Move to breakeven
                        exit_reason = "Hit Target 1, Trailing"
                        
                    # Check Target 2
                    if high >= target2_price and shares_held > 0:
                        profit = (target2_price - entry_price) * shares_held
                        pnl += profit
                        shares_held = 0
                        status = "CLOSED"
                        exit_reason = "Hit Full Target"
                        exit_time = candle_time
                        break
            
            # End of day check (15:15 equivalent)
            if entry_triggered and shares_held > 0:
                # Force close at last candle close
                last_candle = rest_of_day.iloc[-1]
                profit = (last_candle['close'] - entry_price) * shares_held
                pnl += profit
                status = "CLOSED"
                exit_reason = "EOD Exit"
                exit_time = "EOD"
                
            if entry_triggered:
                trades.append({
                    'date': date_str,
                    'symbol': sym,
                    'is_fo': row['is_fo'],
                    'gap_pct': row['gap_pct'],
                    'entry': entry_price,
                    'sl': sl_price,
                    'risk': risk_per_share,
                    'shares': shares,
                    'pnl': pnl,
                    'exit_reason': exit_reason
                })
                trade_taken = True
                break # Break out of candidate loop for this day
                
    # Save trades
    trades_df = pd.DataFrame(trades)
    trades_df.to_csv(TRADES_FILE, index=False)
    print(f"\nBacktest complete! Logged {len(trades_df)} total trades.")

if __name__ == "__main__":
    run_backtest()
