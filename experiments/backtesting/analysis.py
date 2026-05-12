import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import numpy as np

# Configuration
PROJECT_DIR = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_DIR / "experiments" / "backtesting" / "data"
TRADES_FILE = DATA_DIR / "trades.csv"

def calculate_metrics(df, period_name):
    if df.empty:
        return f"--- {period_name} ---\nNo trades taken in this period.\n"
        
    total_trades = len(df)
    winning_trades = df[df['pnl'] > 0]
    losing_trades = df[df['pnl'] <= 0]
    
    win_rate = len(winning_trades) / total_trades * 100
    avg_win = winning_trades['pnl'].mean() if not winning_trades.empty else 0
    avg_loss = losing_trades['pnl'].mean() if not losing_trades.empty else 0
    
    total_pnl = df['pnl'].sum()
    
    # Max Drawdown
    # We calculate cumulative PnL, then find peak and drawdowns from peak
    cum_pnl = df['pnl'].cumsum()
    running_max = cum_pnl.cummax()
    drawdown = running_max - cum_pnl
    max_drawdown = drawdown.max()
    
    # Expectancy
    win_prob = len(winning_trades) / total_trades
    loss_prob = 1 - win_prob
    expectancy = (win_prob * avg_win) + (loss_prob * avg_loss)
    
    report = f"--- {period_name} ---\n"
    report += f"Total Trades : {total_trades}\n"
    report += f"Win Rate     : {win_rate:.1f}%\n"
    report += f"Total PnL    : ₹{total_pnl:,.2f}\n"
    report += f"Avg Win      : ₹{avg_win:,.2f}\n"
    report += f"Avg Loss     : ₹{avg_loss:,.2f}\n"
    report += f"Expectancy   : ₹{expectancy:,.2f} per trade\n"
    report += f"Max Drawdown : ₹{max_drawdown:,.2f}\n\n"
    
    return report

def run_analysis():
    if not TRADES_FILE.exists():
        print("Trades file not found! Engine must complete first.")
        return
        
    trades = pd.read_csv(TRADES_FILE)
    trades['date'] = pd.to_datetime(trades['date'])
    trades = trades.sort_values('date')
    
    latest_date = trades['date'].max()
    
    print("="*60)
    print("📈 INSTITUTIONAL GAP-FADE V2 — BACKTEST REPORT")
    print("="*60 + "\n")
    
    # 5 Years (All Data)
    print(calculate_metrics(trades, "Full 5 Years"))
    
    # Time stratified
    timeframes = {
        "Last 1 Year": 365,
        "Last 150 Days": 150,
        "Last 90 Days": 90,
        "Last 30 Days": 30,
        "Last 10 Days": 10
    }
    
    for name, days in timeframes.items():
        cutoff_date = latest_date - timedelta(days=days)
        subset = trades[trades['date'] >= cutoff_date]
        print(calculate_metrics(subset, name))
        
    # Monthly PnL
    print("--- Monthly PnL Breakdown ---")
    trades['month'] = trades['date'].dt.to_period('M')
    monthly = trades.groupby('month')['pnl'].sum().reset_index()
    monthly['pnl_formatted'] = monthly['pnl'].apply(lambda x: f"₹{x:,.2f}")
    
    # Print last 12 months for brevity
    for _, row in monthly.tail(12).iterrows():
        status = "🟢" if row['pnl'] > 0 else "🔴"
        print(f"{row['month']}: {status} {row['pnl_formatted']}")

if __name__ == "__main__":
    run_analysis()
