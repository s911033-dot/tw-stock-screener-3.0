import streamlit as st

def render_dashboard(inst_df, margin_df, latest_date):
    st.subheader('🏠 市場戰情')
    if inst_df.empty:
        st.info('暫時無法取得法人資料。')
        return
    today=inst_df[inst_df['date']==latest_date]
    foreign=int(today['foreign'].sum()); trust=int(today['trust'].sum()); total=int(today['total_inst'].sum())
    margin_down=int((margin_df[margin_df['date']==latest_date]['margin_diff']<0).sum()) if not margin_df.empty else 0
    c=st.columns(4); c[0].metric('外資淨買賣(張)',f'{foreign:,}'); c[1].metric('投信淨買賣(張)',f'{trust:,}'); c[2].metric('三大法人(張)',f'{total:,}'); c[3].metric('融資減少家數',f'{margin_down:,}')
    st.caption(f'最新交易日：{latest_date}')
