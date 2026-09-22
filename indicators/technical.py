import numpy as np
import pandas as pd

def compute_rsi(series, period=14):
    delta=series.diff(); gain=delta.clip(lower=0); loss=-delta.clip(upper=0)
    avg_gain=gain.rolling(period).mean(); avg_loss=loss.rolling(period).mean()
    rs=avg_gain/(avg_loss+1e-12)
    return 100-(100/(1+rs))

def weighted_ma(series, period):
    weights=np.arange(1,period+1)
    return series.rolling(period).apply(lambda x: np.dot(x,weights)/weights.sum(), raw=True)

def compute_kd(df,n=9):
    df=df.copy(); lo=df['Low'].rolling(n).min(); hi=df['High'].rolling(n).max()
    rsv=(df['Close']-lo)/(hi-lo+1e-12)*100
    k=[]; d=[]; prev_k=50.; prev_d=50.
    for x in rsv.fillna(50):
        prev_k=2/3*prev_k+1/3*x; prev_d=2/3*prev_d+1/3*prev_k; k.append(prev_k); d.append(prev_d)
    df['K']=k; df['D']=d; return df

def compute_indicators(df):
    df=df.copy()
    for n in [5,10,20,60,120,240]: df[f'MA{n}']=df['Close'].rolling(n).mean()
    df['VOL5']=df['Volume'].rolling(5).mean(); df['VOL20']=df['Volume'].rolling(20).mean()
    df['VOL_RATIO']=df['Volume']/df['VOL5'].replace(0,np.nan)
    df['RSI6']=compute_rsi(df['Close'],6); df['RSI12']=compute_rsi(df['Close'],12); df['RSI14']=compute_rsi(df['Close'],14)
    df=compute_kd(df)
    ema12=df['Close'].ewm(span=12,adjust=False).mean(); ema26=df['Close'].ewm(span=26,adjust=False).mean()
    df['MACD']=ema12-ema26; df['MACD_SIGNAL']=df['MACD'].ewm(span=9,adjust=False).mean(); df['MACD_HIST']=df['MACD']-df['MACD_SIGNAL']
    std20=df['Close'].rolling(20).std(); df['BB_MID']=df['MA20']; df['BB_UPPER']=df['MA20']+2*std20; df['BB_LOWER']=df['MA20']-2*std20
    prev=df['Close'].shift(1)
    df['ABOVE_MA20']=df['Close']>df['MA20']; df['ABOVE_MA60']=df['Close']>df['MA60']
    df['MA20_UP']=df['MA20']>df['MA20'].shift(5); df['MA60_UP']=df['MA60']>df['MA60'].shift(5)
    df['KD_GOLDEN']=(df['K']>df['D'])&(df['K'].shift(1)<=df['D'].shift(1))
    df['RSI_GOLDEN']=(df['RSI6']>df['RSI12'])&(df['RSI6'].shift(1)<=df['RSI12'].shift(1))
    df['MACD_GOLDEN']=(df['MACD']>df['MACD_SIGNAL'])&(df['MACD'].shift(1)<=df['MACD_SIGNAL'].shift(1))
    df['BREAK_MA20']=(df['Close']>df['MA20'])&(prev<=df['MA20'].shift(1))
    df['BREAK_MA60']=(df['Close']>df['MA60'])&(prev<=df['MA60'].shift(1))
    return df

def add_weekly_indicators(daily):
    w=daily.resample('W-FRI').agg({'Open':'first','High':'max','Low':'min','Close':'last','Volume':'sum'}).dropna()
    w['WMA30']=weighted_ma(w['Close'],30); w['RSI6']=compute_rsi(w['Close'],6); w['RSI12']=compute_rsi(w['Close'],12); w=compute_kd(w)
    w['BREAK_WMA30']=(w['Close']>w['WMA30'])&(w['Close'].shift(1)<=w['WMA30'].shift(1))
    w['KD_GOLDEN']=(w['K']>w['D'])&(w['K'].shift(1)<=w['D'].shift(1))
    w['RSI_GOLDEN']=(w['RSI6']>w['RSI12'])&(w['RSI6'].shift(1)<=w['RSI12'].shift(1))
    return w
