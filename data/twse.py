import requests
import pandas as pd
import streamlit as st
from config import HEADERS, CACHE_TTL_CHIPS


def _num(v):
    try: return int(str(v).replace(',','').replace('--','0'))
    except Exception: return 0

def _lots(v): return _num(v)//1000

@st.cache_data(ttl=CACHE_TTL_CHIPS)
def fetch_institutional(dates):
    rows=[]
    for d in dates:
        try:
            r=requests.get(f'https://www.twse.com.tw/rwd/zh/fund/T86?date={d}&selectType=ALL&response=json',headers=HEADERS,timeout=10).json()
            for row in r.get('data',[]):
                code=str(row[0]).strip(); name=str(row[1]).strip()
                if len(code)==4 and code.isdigit():
                    rows.append({'date':d,'code':code,'name':name,'foreign':_lots(row[4]),'trust':_lots(row[10]),'dealer':_lots(row[11]),'total_inst':_lots(row[18])})
        except Exception: continue
    return pd.DataFrame(rows)

@st.cache_data(ttl=CACHE_TTL_CHIPS)
def fetch_margin_sbl(dates):
    rows=[]
    for d in dates:
        day={}
        try:
            r=requests.get(f'https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN?date={d}&selectType=ALL&response=json',headers=HEADERS,timeout=10).json()
            raw=[]
            for t in r.get('tables',[]):
                if '融資' in t.get('title','') and t.get('data'): raw=t['data']; break
            if not raw: raw=r.get('data',[])
            for row in raw:
                code=str(row[0]).strip(); name=str(row[1]).strip()
                if len(code)==4 and code.isdigit():
                    day[code]={'date':d,'code':code,'name':name,'margin_buy':_num(row[2]),'margin_diff':_num(row[6])-_num(row[5]),'short_sell':_num(row[9]),'short_diff':_num(row[12])-_num(row[11]),'sbl_short_sell':0,'sbl_diff':0}
        except Exception: pass
        try:
            r=requests.get(f'https://www.twse.com.tw/rwd/zh/marginTrading/TWT93U?date={d}&response=json',headers=HEADERS,timeout=10).json()
            for row in r.get('data',[]):
                code=str(row[0]).strip()
                if code in day:
                    prev=_num(row[7])//1000; sell=_num(row[8])//1000; ret=_num(row[10])//1000 if len(row)>10 else 0; bal=_num(row[12])//1000 if len(row)>12 else prev+sell-ret
                    day[code]['sbl_short_sell']=sell; day[code]['sbl_diff']=bal-prev
        except Exception: pass
        rows.extend(day.values())
    return pd.DataFrame(rows)
