import pandas as pd
import streamlit as st

def metric_cards(row):
    cols=st.columns(5)
    vals=[('綜合',f"{row.get('score',0):.0f}/100"),('技術',f"{row.get('technical_score',0):.0f}/40"),('量價',f"{row.get('volume_score',0):.0f}/20"),('法人/融資',f"{row.get('chip_score',0):.0f}/30"),('分點',f"{row.get('broker_score',0):.0f}/10")]
    for c,(label,value) in zip(cols,vals): c.metric(label,value)

def result_table(df):
    if df.empty: return
    show=df[['code','name','market','close','change_pct','score','technical_score','volume_score','chip_score','broker_concentration','foreign','trust','margin_diff','volume_lots','volume_ratio']].copy()
    show.columns=['代碼','名稱','市場','收盤','漲跌%','總分','技術','量價','法人/融資','分點集中度','外資張數','投信張數','融資增減','成交量張','量比']
    st.dataframe(show,use_container_width=True,hide_index=True)

def signal_list(signals):
    if not signals: st.caption('目前沒有額外訊號'); return
    st.markdown('**訊號雷達**')
    st.write('　'.join(f'✓ {x}' for x in signals))
