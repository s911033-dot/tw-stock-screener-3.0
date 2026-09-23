import requests
import pandas as pd
import streamlit as st
from config import HEADERS, CACHE_TTL_BROKER

@st.cache_data(ttl=CACHE_TTL_BROKER, show_spinner=False)
def fetch_broker_concentration(code, days=10, token=''):
    end=pd.Timestamp.now(); start=end-pd.Timedelta(days=int(days*2.0))
    params={'dataset':'TaiwanStockPriceBidAsk','data_id':code,'start_date':start.strftime('%Y-%m-%d'),'end_date':end.strftime('%Y-%m-%d')}
    if token: params['token']=token
    try:
        r=requests.get('https://api.finmindtrade.com/api/v4/data',params=params,headers=HEADERS,timeout=12).json()
        data=r.get('data',[])
        if not data: return {'concentration':None,'top_brokers':[]}
        df=pd.DataFrame(data); dates=sorted(df['date'].unique(),reverse=True)[:days]; df=df[df['date'].isin(dates)].copy()
        df['net_lots']=(pd.to_numeric(df['buy'],errors='coerce').fillna(0)-pd.to_numeric(df['sell'],errors='coerce').fillna(0))/1000
        summary=df.groupby('broker_name')['net_lots'].sum()
        buys=summary[summary>0].nlargest(15).sum(); sells=abs(summary[summary<0].nsmallest(15).sum())
        total=(pd.to_numeric(df['buy'],errors='coerce').fillna(0).sum()+pd.to_numeric(df['sell'],errors='coerce').fillna(0).sum())/2000
        conc=round((buys-sells)/total*100,2) if total else None
        top=[f"{name}({v:+.0f}張)" for name,v in summary.nlargest(5).items() if v>0]
        return {'concentration':conc,'top_brokers':top}
    except Exception:
        return {'concentration':None,'top_brokers':[]}
