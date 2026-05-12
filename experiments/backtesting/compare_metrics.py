import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent.parent / "experiments" / "backtesting" / "data"

def calc_metrics(df_path):
    df = pd.read_csv(df_path)
    total_trades = len(df)
    wins = df[df['pnl'] > 0]
    losses = df[df['pnl'] <= 0]
    win_rate = len(wins) / total_trades * 100
    total_pnl = df['pnl'].sum()
    avg_win = wins['pnl'].mean() if not wins.empty else 0
    avg_loss = losses['pnl'].mean() if not losses.empty else 0
    
    cum_pnl = df['pnl'].cumsum()
    running_max = cum_pnl.cummax()
    max_dd = (running_max - cum_pnl).max()
    
    expectancy = (len(wins)/total_trades * avg_win) + (len(losses)/total_trades * avg_loss)
    
    return {
        'trades': total_trades,
        'win_rate': win_rate,
        'total_pnl': total_pnl,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'expectancy': expectancy,
        'max_dd': max_dd
    }

for strat in ['buffer', 'fixed', 'eod']:
    metrics = calc_metrics(DATA_DIR / f"trades_{strat}.csv")
    print(f"--- Strategy: {strat.upper()} ---")
    print(f"Trades: {metrics['trades']}")
    print(f"Win Rate: {metrics['win_rate']:.1f}%")
    print(f"Total PnL: ₹{metrics['total_pnl']:.2f}")
    print(f"Avg Win: ₹{metrics['avg_win']:.2f}")
    print(f"Avg Loss: ₹{metrics['avg_loss']:.2f}")
    print(f"Expectancy: ₹{metrics['expectancy']:.2f}")
    print(f"Max DD: ₹{metrics['max_dd']:.2f}\n")
