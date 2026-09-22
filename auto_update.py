"""Daily data refresh entry point for GitHub Actions / cron."""
import sys
from data.markets import fetch_all_stocks, get_recent_trading_dates
from data.twse import fetch_institutional, fetch_margin_sbl
from data.yahoo import download_market_data
from data.database import init_db, save_prices
import pandas as pd
from pathlib import Path


def main():
    init_db()
    dates = get_recent_trading_dates(1)
    stocks = fetch_all_stocks()
    if stocks.empty:
        print('No stock list; abort.')
        return 1
    tickers = stocks.ticker.dropna().tolist()
    print(f'Refreshing {len(tickers)} tickers; latest={dates[0] if dates else "unknown"}')
    data = download_market_data(tickers, period='1y')
    for ticker, df in data.items():
        code = ticker.split('.')[0]
        try:
            save_prices(code, df.tail(10))
        except Exception as exc:
            print(f'save {code} failed: {exc}')
    # Persist a compact snapshot so GitHub Actions can commit it for deployments.
    snapshots = []
    for ticker, df in data.items():
        if df.empty: continue
        r = df.iloc[-1]
        snapshots.append({'date': pd.Timestamp(df.index[-1]).strftime('%Y-%m-%d'), 'ticker': ticker, 'open': r['Open'], 'high': r['High'], 'low': r['Low'], 'close': r['Close'], 'volume': r['Volume']})
    if snapshots:
        Path('data').mkdir(exist_ok=True)
        pd.DataFrame(snapshots).to_csv('data/daily_snapshot.csv', index=False)
    # Trigger TWSE endpoints.
    if dates:
        fetch_institutional(dates)
        fetch_margin_sbl(dates)
    print(f'Updated {len(data)} tickers and wrote daily_snapshot.csv.')
    return 0

if __name__ == '__main__':
    sys.exit(main())
