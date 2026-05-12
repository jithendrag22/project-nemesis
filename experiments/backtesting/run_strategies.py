import pandas as pd
from pathlib import Path

# Configuration
PROJECT_DIR = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_DIR / "experiments" / "backtesting" / "data"
INTRADAY_DIR = DATA_DIR / "intraday"
GAP_EVENTS_FILE = DATA_DIR / "gap_events.csv"

CAPITAL = 100000
MAX_RISK_PCT = 0.02

def simulate_trade(intra_df, strategy):
    fc = intra_df.iloc[0]
    fc_open, fc_high, fc_low, fc_close = fc['open'], fc['high'], fc['low'], fc['close']
    
    if fc_close < fc_open:
        return None # Red candle
        
    entry_price = fc_high
    
    if strategy == 'buffer':
        sl_price = fc_low * 0.998 # 0.20% buffer
        risk_per_share = entry_price - sl_price
        target1_price = entry_price + risk_per_share
        target2_price = entry_price + (risk_per_share * 2)
    elif strategy == 'fixed':
        sl_price = entry_price * 0.9925 # 0.75% fixed
        risk_per_share = entry_price - sl_price
        target1_price = entry_price * 1.0150 # 1.50% fixed target
        target2_price = None # Full exit at Target 1
    elif strategy == 'eod':
        sl_price = fc_low * 0.9985 # 0.15% buffer
        risk_per_share = entry_price - sl_price
        target1_price = entry_price + risk_per_share
        target2_price = None # Run until EOD
    else:
        return None
        
    if risk_per_share <= 0:
        return None
        
    max_risk_rs = CAPITAL * MAX_RISK_PCT
    shares = min(int(max_risk_rs / risk_per_share), int(CAPITAL / entry_price))
    if shares == 0:
        return None
        
    rest_of_day = intra_df.iloc[1:]
    entry_triggered = False
    pnl = 0.0
    current_sl = sl_price
    shares_held = shares
    exit_reason = ""
    
    for idx, min_candle in rest_of_day.iterrows():
        high, low, close = min_candle['high'], min_candle['low'], min_candle['close']
        
        if not entry_triggered:
            if high > entry_price:
                if low < sl_price:
                    exit_reason = "Hit SL before Entry"
                    break
                entry_triggered = True
            else:
                continue
                
        if entry_triggered:
            if low < current_sl:
                pnl += (current_sl - entry_price) * shares_held
                shares_held = 0
                exit_reason = "Stopped Out"
                break
                
            if strategy == 'fixed':
                if high >= target1_price:
                    pnl += (target1_price - entry_price) * shares_held
                    shares_held = 0
                    exit_reason = "Hit Full Target"
                    break
            else:
                # Buffer and EOD
                if high >= target1_price and shares_held == shares:
                    half = shares // 2
                    pnl += (target1_price - entry_price) * half
                    shares_held -= half
                    current_sl = entry_price # Trail to breakeven
                    exit_reason = "Hit Target 1, Trailing"
                    
                if strategy == 'buffer':
                    if high >= target2_price and shares_held > 0:
                        pnl += (target2_price - entry_price) * shares_held
                        shares_held = 0
                        exit_reason = "Hit Target 2"
                        break
                        
    if entry_triggered and shares_held > 0:
        last_close = rest_of_day.iloc[-1]['close']
        pnl += (last_close - entry_price) * shares_held
        exit_reason = "EOD Exit"
        
    if entry_triggered:
        return {
            'entry': entry_price,
            'sl': sl_price,
            'risk': risk_per_share,
            'shares': shares,
            'pnl': pnl,
            'exit_reason': exit_reason
        }
    return None

def run_all_strategies():
    gaps_df = pd.read_csv(GAP_EVENTS_FILE)
    unique_dates = sorted(gaps_df['date'].unique())
    
    results = {'buffer': [], 'fixed': [], 'eod': []}
    
    for date_str in unique_dates:
        day_gaps = gaps_df[gaps_df['date'] == date_str]
        day_gaps = day_gaps.sort_values(['is_fo', 'gap_pct'], ascending=[False, True])
        
        # We need to simulate per strategy because they might trigger differently
        for strat in results.keys():
            for _, row in day_gaps.iterrows():
                sym = row['symbol']
                cache_file = INTRADAY_DIR / f"{sym}_{date_str}.csv"
                
                if not cache_file.exists():
                    continue
                    
                try:
                    intra_df = pd.read_csv(cache_file)
                except pd.errors.EmptyDataError:
                    continue
                    
                if intra_df.empty or len(intra_df) < 2:
                    continue
                    
                trade = simulate_trade(intra_df, strat)
                if trade:
                    trade['date'] = date_str
                    trade['symbol'] = sym
                    results[strat].append(trade)
                    break # Got 1 trade for this day for this strategy
                    
    for strat, trades in results.items():
        df = pd.DataFrame(trades)
        out_file = DATA_DIR / f"trades_{strat}.csv"
        df.to_csv(out_file, index=False)
        print(f"Saved {len(df)} trades for {strat} to {out_file}")

if __name__ == "__main__":
    run_all_strategies()
