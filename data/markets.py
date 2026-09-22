import requests
import pandas as pd
import streamlit as st
from config import HEADERS, CACHE_TTL_STOCKS

@st.cache_data(ttl=CACHE_TTL_STOCKS)
def fetch_all_stocks():
    rows=[]
    try:
        r=requests.get('https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL',headers=HEADERS,timeout=15)
        if r.ok:
            for x in r.json():
                code=str(x.get('Code','')).strip(); name=str(x.get('Name','')).strip()
                if len(code)==4 and code.isdigit(): rows.append({'ticker':f'{code}.TW','code':code,'name':name,'market':'上市','display':f'{code} {name} (上市)'})
    except Exception: pass
    try:
        r=requests.get('https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes',headers=HEADERS,timeout=15)
        if r.ok:
            for x in r.json():
                code=str(x.get('SecuritiesCompanyCode','')).strip(); name=str(x.get('CompanyName','')).strip()
                if len(code)==4 and code.isdigit(): rows.append({'ticker':f'{code}.TWO','code':code,'name':name,'market':'上櫃','display':f'{code} {name} (上櫃)'})
    except Exception: pass
    return pd.DataFrame(rows).drop_duplicates('code')

@st.cache_data(ttl=3600)
def get_recent_trading_dates(count=5):
    dates=[]; d=pd.Timestamp.now().normalize()
    for _ in range(20):
        if d.weekday()<5 and len(dates)<count:
            s=d.strftime('%Y%m%d')
            try:
                r=requests.get(f'https://www.twse.com.tw/rwd/zh/fund/T86?date={s}&selectType=ALL&response=json',headers=HEADERS,timeout=8).json()
                if r.get('stat')=='OK' and r.get('data'): dates.append(s)
            except Exception: pass
        if len(dates)>=count: break
        d-=pd.Timedelta(days=1)
    return dates
