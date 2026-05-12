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
MASTER_DB_DIR = PROJECT_DIR / "experiments" / "backtesting" / "data" / "master_5m"
MASTER_DB_DIR.mkdir(parents=True, exist_ok=True)

CLIENT_ID = "1103466045"
ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzc4NTg5ODAyLCJpYXQiOjE3Nzg1MDM0MDIsInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTAzNDY2MDQ1In0.qo73h3_PLQSg55FDyF-y7asXFFZv-fIcczyktA5MLs6mg-ArVRgDy_HMcYPfhSCGuTSKwBt6px3xpR2EyFg7VA"

# Initialize Dhan
dhan_context = DhanContext(CLIENT_ID, ACCESS_TOKEN)
dhan = dhanhq(dhan_context)

def generate_date_chunks(start_date, end_date, chunk_size_days=90):
    """Slice the date range into chunks of max 90 days to respect Dhan API limits."""
    chunks = []
    current_start = start_date
    while current_start < end_date:
        current_end = min(current_start + timedelta(days=chunk_size_days - 1), end_date)
        chunks.append((current_start.strftime('%Y-%m-%d'), current_end.strftime('%Y-%m-%d')))
        current_start = current_end + timedelta(days=1)
    return chunks

def run():
    print(f"Loading instrument list from {MAPPING_FILE}...")
    if not MAPPING_FILE.exists():
        print("Mapping file not found!")
        return
        
    mapping = pd.read_csv(MAPPING_FILE)
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=5*365)
    date_chunks = generate_date_chunks(start_date, end_date, chunk_size_days=90)
    
    print(f"Fetching 5 years of 5-min data from {start_date.date()} to {end_date.date()}")
    print(f"API chunks per stock: {len(date_chunks)}")
    print(f"Total stocks to process: {len(mapping)}")
    print("="*60)
    
    for i, row in mapping.iterrows():
        sym = row['SEM_TRADING_SYMBOL']
        sec_id = str(row['SEM_SMST_SECURITY_ID'])
        
        out_path = MASTER_DB_DIR / f"{sym}.csv"
        
        # Crash recovery: skip if already fully downloaded
        if out_path.exists():
            continue
            
        print(f"[{i+1}/{len(mapping)}] Downloading {sym}...", end=" ", flush=True)
        
        stock_dfs = []
        skip_stock = False
        
        for from_str, to_str in date_chunks:
            max_retries = 3
            success = False
            for attempt in range(max_retries):
                try:
                    res = dhan.intraday_minute_data(
                        security_id=sec_id,
                        exchange_segment='NSE_EQ',
                        instrument_type='EQUITY',
                        from_date=from_str,
                        to_date=to_str,
                        interval=5
                    )
                    
                    if res.get('status') == 'success':
                        data = res.get('data', {})
                        if 'open' in data and len(data['open']) > 0:
                            stock_dfs.append(pd.DataFrame(data))
                        success = True
                        break # Break retry loop
                    else:
                        err_code = res.get('remarks', {}).get('error_code', '')
                        if err_code == 'DH-904': # Rate Limit
                            time.sleep(2.0)
                            continue
                        elif err_code == 'DH-901' or err_code == 'DH-902': 
                            # Invalid sec ID or generic failure, break early
                            success = True # Pretend success to skip gracefully
                            break
                        else:
                            time.sleep(1.0)
                except Exception as e:
                    time.sleep(1.0)
                    
            if not success:
                skip_stock = True
                break
                
            time.sleep(0.4) # Mandatory delay between chunks
            
        if not skip_stock and stock_dfs:
            final_df = pd.concat(stock_dfs, ignore_index=True)
            # Format Dhan timestamp
            if 'start_Time' in final_df.columns:
                try:
                    # Dhan returns specific format, but let's try direct datetime conversion
                    final_df['datetime'] = pd.to_datetime(final_df['start_Time'])
                    final_df = final_df.sort_values('datetime')
                except:
                    pass
            elif 'timestamp' in final_df.columns:
                 # It might return epoch seconds
                 final_df['datetime'] = pd.to_datetime(final_df['timestamp'], unit='s', utc=True).dt.tz_convert('Asia/Kolkata')
                 final_df = final_df.sort_values('datetime')
                 
            final_df.to_csv(out_path, index=False)
            print(f"OK ({len(final_df)} rows)")
        else:
            print("FAILED/NO DATA")

if __name__ == '__main__':
    run()
