import pandas as pd
from pathlib import Path
import os
import warnings
warnings.filterwarnings('ignore')

# Configuration
PROJECT_DIR = Path(__file__).parent.parent.parent
DAILY_DATA_DIR = PROJECT_DIR / "experiments" / "backtesting" / "data" / "daily"
UNIVERSE_FILE = PROJECT_DIR / "data" / "universe" / "fo_stocks.csv"
OUTPUT_FILE = PROJECT_DIR / "experiments" / "backtesting" / "data" / "gap_events.csv"

GAP_MIN = 2.0
GAP_MAX = 15.0

def load_fo_universe():
    if not UNIVERSE_FILE.exists():
        return set()
    fo = pd.read_csv(UNIVERSE_FILE)
    return set(fo["symbol"].str.replace(".NS", "").tolist())

def run():
    fo_set = load_fo_universe()
    csv_files = list(DAILY_DATA_DIR.glob("*.csv"))
    print(f"Scanning {len(csv_files)} historical daily data files...")
    
    all_gaps = []
    
    for file_path in csv_files:
        sym = file_path.stem
        try:
            df = pd.read_csv(file_path)
            if len(df) < 2:
                continue
                
            # Ensure chronological order
            df = df.sort_values('date')
            
            # Calculate gaps
            df['prev_close'] = df['close'].shift(1)
            # Gap % = (Today Open - Yesterday Close) / Yesterday Close
            df['gap_pct'] = ((df['open'] - df['prev_close']) / df['prev_close']) * 100
            
            # Filter for our specific criteria (-2% to -15%)
            valid_gaps = df[(df['gap_pct'] <= -GAP_MIN) & (df['gap_pct'] >= -GAP_MAX)].copy()
            
            if not valid_gaps.empty:
                valid_gaps['symbol'] = sym
                valid_gaps['is_fo'] = sym in fo_set
                # Keep only what we need
                valid_gaps = valid_gaps[['date', 'symbol', 'is_fo', 'prev_close', 'open', 'gap_pct']]
                all_gaps.append(valid_gaps)
                
        except Exception as e:
            print(f"Error processing {sym}: {e}")
            
    if not all_gaps:
        print("No gaps found across 5 years. Something is wrong.")
        return
        
    master_df = pd.concat(all_gaps, ignore_index=True)
    
    # Sort chronologically, then prioritize F&O, then by largest gap (most negative)
    master_df = master_df.sort_values(['date', 'is_fo', 'gap_pct'], ascending=[True, False, True])
    
    master_df.to_csv(OUTPUT_FILE, index=False)
    print(f"Extraction complete! Found {len(master_df)} valid gap-down events over the last 5 years.")
    print(f"Data saved to {OUTPUT_FILE}")

if __name__ == '__main__':
    run()
