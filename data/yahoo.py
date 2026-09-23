import yfinance as yf
import pandas as pd
import streamlit as st
from config import CACHE_TTL_MARKET

@st.cache_data(ttl=CACHE_TTL_MARKET, show_spinner=False)
def download_market_data(tickers, period='5y'):
    tickers=list(dict.fromkeys(tickers))
    if not tickers: return {}
    try:
        raw=yf.download(tickers=tickers,period=period,interval='1d',group_by='ticker',auto_adjust=False,threads=True,progress=False)
    except Exception: return {}
    out={}
    for ticker in tickers:
        try:
            df=raw.copy() if len(tickers)==1 else raw[ticker].copy()
            df=df.dropna(subset=['Open','High','Low','Close'])
            if len(df)>=65: out[ticker]=df
        except Exception: continue
    return out

@st.cache_data(ttl=CACHE_TTL_MARKET, show_spinner=False)
def get_stock_history(ticker, period='5y'):
    try:
        df=yf.Ticker(ticker).history(period=period,auto_adjust=False)
        return df.dropna(subset=['Open','High','Low','Close'])
    except Exception: return pd.DataFrame()
