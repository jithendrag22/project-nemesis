from dhanhq import dhanhq
from dhanhq.dhan_context import DhanContext
import pandas as pd
from datetime import datetime, date
import warnings
warnings.filterwarnings('ignore')

CLIENT_ID = "1103466045"
ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzc4NTg5ODAyLCJpYXQiOjE3Nzg1MDM0MDIsInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTAzNDY2MDQ1In0.qo73h3_PLQSg55FDyF-y7asXFFZv-fIcczyktA5MLs6mg-ArVRgDy_HMcYPfhSCGuTSKwBt6px3xpR2EyFg7VA"

dhan_context = DhanContext(CLIENT_ID, ACCESS_TOKEN)
dhan = dhanhq(dhan_context)

# Load mapping
mapping = pd.read_csv("dhan_instruments.csv")
symbol_to_id = dict(zip(mapping['SEM_TRADING_SYMBOL'], mapping['SEM_SMST_SECURITY_ID']))

# The list we got from yfinance gaps earlier
targets = ['ABB', 'TITAN', 'M&M', 'SIEMENS', 'CHOLAFIN', 'LUPIN', 'INDIGO']

today = date.today().strftime('%Y-%m-%d')
print(f"Fetching real Dhan 5-min candles for {today}...\n")

for sym in targets:
    sec_id = str(symbol_to_id.get(sym))
    if not sec_id: continue
    
    # Fetch historical minute charts for today
    # From Dhan docs: get_historical_minute_charts(symbol, exchange_segment, instrument_type, expiry_code, from_date, to_date)
    # Wait, the v2.2.0 method might be different. Let's try historical_minute_charts.
    try:
        res = dhan.intraday_minute_data(
            security_id=sec_id,
            exchange_segment='NSE_EQ',
            instrument_type='EQUITY',
            from_date=today,
            to_date=today
        )
        if res.get('status') == 'success':
            data = res.get('data', {})
            if 'open' in data and len(data['open']) > 0:
                fc_open = data['open'][0]
                fc_high = data['high'][0]
                fc_low = data['low'][0]
                fc_close = data['close'][0]
                color = "GREEN" if fc_close >= fc_open else "RED"
                print(f"{sym}: 9:15 Open={fc_open}, Close={fc_close} [{color}] (High={fc_high}, Low={fc_low})")
            else:
                print(f"{sym}: No data returned in success payload")
        else:
            print(f"{sym}: Failed -> {res}")
    except Exception as e:
         print(f"{sym}: Exception -> {e}")
