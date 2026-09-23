import streamlit as st
from charts.stock_chart import make_stock_chart
from ui.components import metric_cards, signal_list

def render_stock_detail(row, df):
    if row is None or df is None or df.empty: return
    st.subheader(f"🔬 {row.get('code','')} {row.get('name','')}")
    c1,c2=st.columns([3,1]);
    with c1: st.metric('最新收盤',f"{row['close']:.2f}",f"{row['change_pct']:+.2f}%")
    with c2: st.metric('成交量',f"{row['volume_lots']:,} 張",f"量比 {row['volume_ratio']:.2f}x")
    metric_cards(row); signal_list(row.get('signals',[]))
    st.plotly_chart(make_stock_chart(df,f"{row.get('code','')} {row.get('name','')}"),use_container_width=True,config={'scrollZoom':True,'displayModeBar':True})
