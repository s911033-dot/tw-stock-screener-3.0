import pandas as pd
from .scoring import analyze_stock, strategy_pass

def run_scan(target_tickers, market_data, inst_df, margin_df, stocks_df, strategy, use_broker=False, finmind=None):
    inst_map={r['code']:r.to_dict() for _,r in inst_df.iterrows()} if not inst_df.empty else {}
    margin_map={r['code']:r.to_dict() for _,r in margin_df.iterrows()} if not margin_df.empty else {}
    records=[]
    for ticker in target_tickers:
        df=market_data.get(ticker)
        if df is None or len(df)<65: continue
        code=ticker.split('.')[0]
        broker=None
        if use_broker and finmind: broker=finmind(code)
        row=analyze_stock(ticker,df,inst_map.get(code),margin_map.get(code),broker)
        if row and strategy_pass(row,strategy):
            m=stocks_df[stocks_df['ticker']==ticker]
            row['code']=code; row['name']=m.iloc[0]['name'] if not m.empty else code; row['market']=m.iloc[0]['market'] if not m.empty else ''
            records.append(row)
    if not records: return pd.DataFrame()
    return pd.DataFrame(records).sort_values(['score','volume_ratio'],ascending=False).reset_index(drop=True)
