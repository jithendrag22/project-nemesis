import pandas as pd
from pathlib import Path

# Configuration
PROJECT_DIR = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_DIR / "experiments" / "backtesting" / "data"
TRADES_FILE = DATA_DIR / "trades_eod.csv"

def run_deep_analysis():
    trades = pd.read_csv(TRADES_FILE)
    trades['date'] = pd.to_datetime(trades['date'])
    trades['year'] = trades['date'].dt.year
    trades['month'] = trades['date'].dt.month
    trades['quarter'] = trades['date'].dt.quarter
    
    # 1. Yearly Analysis
    print("--- YEARLY ANALYSIS ---")
    yearly = trades.groupby('year').agg(
        trades=('pnl', 'count'),
        win_rate=('pnl', lambda x: (x > 0).mean() * 100),
        total_pnl=('pnl', 'sum'),
        avg_win=('pnl', lambda x: x[x > 0].mean() if len(x[x > 0]) > 0 else 0),
        avg_loss=('pnl', lambda x: x[x <= 0].mean() if len(x[x <= 0]) > 0 else 0)
    ).reset_index()
    
    for _, row in yearly.iterrows():
        print(f"{int(row['year'])}: {row['trades']} trades | WR: {row['win_rate']:.1f}% | PnL: ₹{row['total_pnl']:,.2f}")
        
    # 2. Seasonal Analysis (by Quarter)
    print("\n--- SEASONAL ANALYSIS (By Quarter) ---")
    quarterly = trades.groupby('quarter').agg(
        trades=('pnl', 'count'),
        win_rate=('pnl', lambda x: (x > 0).mean() * 100),
        total_pnl=('pnl', 'sum')
    ).reset_index()
    
    q_names = {1: "Q1 (Jan-Mar: Pre-Earnings/Budget)", 
               2: "Q2 (Apr-Jun: Summer)", 
               3: "Q3 (Jul-Sep: Monsoon/Results)", 
               4: "Q4 (Oct-Dec: Festive)"}
               
    for _, row in quarterly.iterrows():
        print(f"{q_names[row['quarter']]}: {row['trades']} trades | WR: {row['win_rate']:.1f}% | PnL: ₹{row['total_pnl']:,.2f}")

    # 3. Monthly Heatmap Info (Average PnL by Month)
    print("\n--- MONTHLY AGGREGATE PERFORMANCE ---")
    monthly = trades.groupby('month').agg(
        win_rate=('pnl', lambda x: (x > 0).mean() * 100),
        avg_pnl=('pnl', 'mean')
    ).reset_index()
    
    m_names = {1:'Jan', 2:'Feb', 3:'Mar', 4:'Apr', 5:'May', 6:'Jun', 
               7:'Jul', 8:'Aug', 9:'Sep', 10:'Oct', 11:'Nov', 12:'Dec'}
               
    for _, row in monthly.iterrows():
        print(f"{m_names[row['month']]}: WR: {row['win_rate']:.1f}% | Avg Trade PnL: ₹{row['avg_pnl']:,.2f}")

if __name__ == "__main__":
    run_deep_analysis()
