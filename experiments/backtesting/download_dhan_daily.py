import pandas as pd
from datetime import datetime, timedelta
import time
import os
from pathlib import Path
from dhanhq import dhanhq
from dhanhq.dhan_context import DhanContext
import warnings
warnings.filterwarnings('ignore')

# Configuration
PROJECT_DIR = Path(__file__).parent.parent.parent
MAPPING_FILE = PROJECT_DIR / "experiments" / "nse_movers" / "dhan_instruments.csv"
DATA_DIR = PROJECT_DIR / "experiments" / "backtesting" / "data" / "daily"
DATA_DIR.mkdir(parents=True, exist_ok=True)

CLIENT_ID = "1103466045"
ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzc4NTg5ODAyLCJpYXQiOjE3Nzg1MDM0MDIsInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTAzNDY2MDQ1In0.qo73h3_PLQSg55FDyF-y7asXFFZv-fIcczyktA5MLs6mg-ArVRgDy_HMcYPfhSCGuTSKwBt6px3xpR2EyFg7VA"

# Initialize Dhan
dhan_context = DhanContext(CLIENT_ID, ACCESS_TOKEN)
dhan = dhanhq(dhan_context)

def run():
    print(f"Loading instrument list from {MAPPING_FILE}...")
    if not MAPPING_FILE.exists():
        print("Mapping file not found!")
        return
        
    mapping = pd.read_csv(MAPPING_FILE)
    
    today = datetime.now()
    five_years_ago = today - timedelta(days=5*365)
    
    to_date_str = today.strftime('%Y-%m-%d')
    from_date_str = five_years_ago.strftime('%Y-%m-%d')
    
    print(f"Fetching 5 years of daily data from {from_date_str} to {to_date_str}")
    print(f"Total symbols to process: {len(mapping)}")
    
    success_count = 0
    fail_count = 0
    
    for i, row in mapping.iterrows():
        sym = row['SEM_TRADING_SYMBOL']
        sec_id = str(row['SEM_SMST_SECURITY_ID'])
        
        out_path = DATA_DIR / f"{sym}.csv"
        
        # Skip if already downloaded
        if out_path.exists():
            success_count += 1
            continue
            
        print(f"[{i+1}/{len(mapping)}] Fetching {sym}...", end=" ", flush=True)
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                res = dhan.historical_daily_data(
                    security_id=sec_id,
                    exchange_segment='NSE_EQ',
                    instrument_type='EQUITY',
                    from_date=from_date_str,
                    to_date=to_date_str,
                    expiry_code=0
                )
                
                if res.get('status') == 'success':
                    data = res.get('data', {})
                    if 'open' in data and len(data['open']) > 0:
                        df = pd.DataFrame(data)
                        
                        if 'timestamp' in df.columns:
                            # Convert epoch seconds to timezone-aware UTC, then to IST, then extract date
                            df['date'] = pd.to_datetime(df['timestamp'], unit='s', utc=True).dt.tz_convert('Asia/Kolkata').dt.date
                        
                        # Reorder/rename columns for our backtester
                        if 'date' in df.columns:
                            df = df[['date', 'open', 'high', 'low', 'close', 'volume']]
                        
                        df.to_csv(out_path, index=False)
                        print(f"OK ({len(df)} days)")
                        success_count += 1
                        break # break retry loop
                    else:
                        print("NO DATA")
                        fail_count += 1
                        break # break retry loop, no data is not a rate limit error
                else:
                    err_code = res.get('remarks', {}).get('error_code', '')
                    if err_code == 'DH-904': # Rate Limit
                        print(f"Rate Limited. Retrying ({attempt+1}/{max_retries})...", end=" ")
                        time.sleep(2.0) # Backoff
                        continue
                    else:
                        print(f"ERROR: {res.get('remarks', {}).get('error_message', res)}")
                        fail_count += 1
                        break # break retry loop
                        
            except Exception as e:
                print(f"Exception: {e}")
                time.sleep(1.0)
                if attempt == max_retries - 1:
                    fail_count += 1
                
        # Mandatory delay to prevent rate limit (5 req/sec usually means 0.2s, 0.5s is extremely safe)
        time.sleep(0.5)

    print(f"Done! Success: {success_count}, Failed: {fail_count}")

if __name__ == '__main__':
    run()
