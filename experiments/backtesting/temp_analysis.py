import pandas as pd
from pathlib import Path
import warnings

warnings.filterwarnings('ignore')

PROJECT_DIR = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_DIR / "experiments" / "backtesting" / "data"
INTRADAY_DIR = DATA_DIR / "intraday"
GAP_EVENTS_FILE = DATA_DIR / "gap_events.csv"

def temp_run():
    gaps_df = pd.read_csv(GAP_EVENTS_FILE)
    unique_dates = sorted(gaps_df['date'].unique())[:300] # Just the first 300 days
    
    trades = []
    
    for date_str in unique_dates:
        day_gaps = gaps_df[gaps_df['date'] == date_str]
        day_gaps = day_gaps.sort_values(['is_fo', 'gap_pct'], ascending=[False, True])
        
        for _, row in day_gaps.iterrows():
            sym = row['symbol']
            cache_file = INTRADAY_DIR / f"{sym}_{date_str}.csv"
            
            if not cache_file.exists():
                continue # We only check what's already downloaded
                
            try:
                intra_df = pd.read_csv(cache_file)
            except pd.errors.EmptyDataError:
                continue
                
            if intra_df.empty or len(intra_df) < 2:
                continue
                
            fc = intra_df.iloc[0]
            if fc['close'] < fc['open']:
                continue # Red
                
            entry_price = fc['high']
            sl_price = fc['low']
            risk = entry_price - sl_price
            
            if risk <= 0:
                continue
                
            shares = min(int(2000 / risk), int(100000 / entry_price))
            if shares == 0:
                continue
                
            target1 = entry_price + risk
            target2 = entry_price + (risk * 2)
            
            rest_of_day = intra_df.iloc[1:]
            entry_triggered = False
            pnl = 0.0
            shares_held = shares
            current_sl = sl_price
            
            for _, minute_candle in rest_of_day.iterrows():
                high = minute_candle['high']
                low = minute_candle['low']
                
                if not entry_triggered:
                    if high > entry_price:
                        if low < sl_price:
                            break
                        entry_triggered = True
                    continue
                    
                if low < current_sl:
                    pnl += (current_sl - entry_price) * shares_held
                    shares_held = 0
                    break
                    
                if high >= target1 and shares_held == shares:
                    half = shares // 2
                    pnl += (target1 - entry_price) * half
                    shares_held -= half
                    current_sl = entry_price
                    
                if high >= target2 and shares_held > 0:
                    pnl += (target2 - entry_price) * shares_held
                    shares_held = 0
                    break
                    
            if entry_triggered and shares_held > 0:
                pnl += (rest_of_day.iloc[-1]['close'] - entry_price) * shares_held
                
            if entry_triggered:
                trades.append(pnl)
                break
                
    if trades:
        wins = [t for t in trades if t > 0]
        losses = [t for t in trades if t <= 0]
        print("=== SNEAK PEEK (First 50 Days) ===")
        print(f"Total Trades: {len(trades)}")
        print(f"Win Rate: {len(wins)/len(trades)*100:.1f}%")
        print(f"Total PnL: ₹{sum(trades):.2f}")
        print(f"Avg Win: ₹{sum(wins)/len(wins) if wins else 0:.2f}")
        print(f"Avg Loss: ₹{sum(losses)/len(losses) if losses else 0:.2f}")
    else:
        print("No trades found in the first 50 days.")

if __name__ == '__main__':
    temp_run()
