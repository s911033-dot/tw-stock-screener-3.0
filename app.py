import io
from datetime import date, timedelta
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import APP_TITLE
from data.database import init_db, load_watchlist, add_watchlist, remove_watchlist, save_scan
from data.markets import fetch_all_stocks, get_recent_trading_dates
from data.twse import fetch_institutional, fetch_margin_sbl
from data.yahoo import download_market_data, get_stock_history
from data.finmind import fetch_broker_concentration
from indicators.technical import compute_indicators
from screener.scoring import STRATEGIES, DEFAULT_WEIGHTS, WEIGHT_LABELS, normalize_weights, analyze_stock
from screener.engine import run_scan
from screener.backtest import backtest_market
from ui.dashboard import render_dashboard
from ui.components import result_table
from ui.stock_detail import render_stock_detail

st.set_page_config(page_title=APP_TITLE, page_icon='📈', layout='wide', initial_sidebar_state='expanded')
init_db()

if 'scan_result' not in st.session_state: st.session_state.scan_result = pd.DataFrame()
if 'selected_ticker' not in st.session_state: st.session_state.selected_ticker = None
if 'weights' not in st.session_state: st.session_state.weights = DEFAULT_WEIGHTS.copy()

stocks = fetch_all_stocks()
trade_dates = get_recent_trading_dates(5)
latest_date = trade_dates[0] if trade_dates else pd.Timestamp.now().strftime('%Y%m%d')
inst = fetch_institutional(trade_dates)
margin = fetch_margin_sbl(trade_dates)

try:
    FINMIND_TOKEN = st.secrets.get('FINMIND_TOKEN', '')
except Exception:
    FINMIND_TOKEN = ''


def broker_fetch(code):
    return fetch_broker_concentration(code, days=10, token=FINMIND_TOKEN)


def ticker_for(code):
    m = stocks[stocks.code.astype(str) == str(code)]
    return m.iloc[0]['ticker'] if not m.empty else f'{code}.TW'


def stock_name(code):
    m = stocks[stocks.code.astype(str) == str(code)]
    return m.iloc[0]['name'] if not m.empty else code


def choose_universe(label):
    core = ['2330','2317','2454','2382','2308','2603','3711','2881','2882','2891','2357','3008','2886','2303','3231','2412','2609','2615','3034','3037','3443','6415','3661','2379','6669','2345','6274','8069','3529','6515']
    if label == '市值核心股(30檔)': return stocks[stocks.code.isin(core)].ticker.tolist()
    if label == '全部上市': return stocks[stocks.market == '上市'].ticker.tolist()
    if label == '全部上櫃': return stocks[stocks.market == '上櫃'].ticker.tolist()
    if label == '自選股': return [ticker_for(c) for c in load_watchlist().code.tolist()]
    return []


st.title('📈 台股全方位量價籌碼戰情室')
st.caption('V2.1｜回測引擎 × 策略績效 × 自動每日更新 × 多因子權重｜研究用途，不構成投資建議')

with st.sidebar:
    st.header('⚙️ 系統設定')
    if st.button('🔄 重新整理市場資料', use_container_width=True):
        st.cache_data.clear(); st.rerun()
    st.divider()
    st.subheader('⭐ 自選股')
    wl = load_watchlist()
    if not wl.empty:
        for _, r in wl.iterrows():
            c1, c2 = st.columns([4, 1]); c1.write(f"{r['code']} {r['name']}")
            if c2.button('×', key=f"rm_{r['code']}"): remove_watchlist(r['code']); st.rerun()
    else: st.caption('尚未建立自選股')
    if not stocks.empty:
        choice = st.selectbox('加入自選', stocks['display'].tolist())
        if st.button('⭐ 加入', use_container_width=True):
            r = stocks[stocks.display == choice].iloc[0]; add_watchlist([r.to_dict()]); st.rerun()

# -------------------- Multi-factor panel --------------------
st.markdown('### 🧮 V2.1 多因子權重')
st.caption('權重會自動正規化為 100%；選股與回測均可使用目前權重。')
with st.expander('開啟權重調整介面', expanded=False):
    preset = st.selectbox('權重模板', ['自訂', '均衡', '趨勢型', '動能型', '突破型', '防守型'])
    presets = {
        '均衡': {'trend':20,'momentum':15,'volume':15,'breakout':15,'kd':10,'macd':10,'rsi':10,'risk':5},
        '趨勢型': {'trend':30,'momentum':10,'volume':10,'breakout':15,'kd':5,'macd':10,'rsi':5,'risk':15},
        '動能型': {'trend':10,'momentum':25,'volume':15,'breakout':10,'kd':10,'macd':10,'rsi':15,'risk':5},
        '突破型': {'trend':15,'momentum':10,'volume':20,'breakout':25,'kd':10,'macd':10,'rsi':5,'risk':5},
        '防守型': {'trend':20,'momentum':10,'volume':10,'breakout':5,'kd':10,'macd':10,'rsi':10,'risk':25},
    }
    if preset != '自訂': st.session_state.weights = presets[preset].copy()
    cols = st.columns(4)
    new_w = {}
    for i, k in enumerate(DEFAULT_WEIGHTS):
        with cols[i % 4]:
            new_w[k] = st.slider(WEIGHT_LABELS[k], 0, 40, int(st.session_state.weights.get(k, DEFAULT_WEIGHTS[k])), 1, key=f'wt_{k}_{preset}')
    st.session_state.weights = normalize_weights(new_w)
    st.write('目前正規化權重：', ' ｜ '.join([f"{WEIGHT_LABELS[k]} {v:.1f}%" for k,v in st.session_state.weights.items()]))
    if st.button('↩️ 還原預設均衡權重'):
        st.session_state.weights = DEFAULT_WEIGHTS.copy(); st.rerun()

market_tab, screen_tab, backtest_tab, perf_tab, chip_tab, broker_tab, detail_tab = st.tabs([
    '🏠 市場戰情','🔎 量化選股','🧪 回測引擎','📈 策略績效','📊 法人籌碼','🏦 主力分點','🔬 個股診斷'
])

with market_tab:
    render_dashboard(inst, margin, latest_date)
    st.subheader('⭐ 自選股快速檢視')
    if wl.empty: st.info('請從左側加入自選股。')
    else:
        tickers = [ticker_for(c) for c in wl.code.tolist()]
        data = download_market_data(tickers, period='1y')
        rows = []
        inst_map = {r['code']: r.to_dict() for _,r in inst[inst.date == latest_date].iterrows()} if not inst.empty else {}
        margin_map = {r['code']:r.to_dict() for _,r in margin[margin.date == latest_date].iterrows()} if not margin.empty else {}
        for t, df in data.items():
            df = compute_indicators(df); r = analyze_stock(t, df, inst_map.get(t.split('.')[0]), margin_map.get(t.split('.')[0]), None, st.session_state.weights)
            if r: r['code'] = t.split('.')[0]; r['name'] = stock_name(t.split('.')[0]); rows.append(r)
        if rows: result_table(pd.DataFrame(rows).sort_values('score', ascending=False))

with screen_tab:
    st.subheader('🔎 量化選股')
    mode = st.radio('掃描範圍',['市值核心股(30檔)','全部上市','全部上櫃','自選股','自訂股票'],horizontal=True)
    if mode in ['全部上市','全部上櫃']:
        market = '上市' if mode == '全部上市' else '上櫃'
        n = st.slider('掃描檔數', 10, max(10, len(stocks[stocks.market == market])), min(100, max(10, len(stocks[stocks.market == market]))), step=10)
        target = stocks[stocks.market == market].head(n).ticker.tolist()
    elif mode == '自訂股票':
        selected = st.multiselect('搜尋股票', stocks.display.tolist(), default=[]); target = stocks[stocks.display.isin(selected)].ticker.tolist()
    else: target = choose_universe(mode)
    strategy = st.selectbox('快速策略', list(STRATEGIES.keys()))
    use_broker = st.checkbox('啟用 10 日分點集中度（速度較慢；需要 FinMind）', value=False)
    c1,c2,c3 = st.columns(3)
    min_score = c1.slider('最低綜合分數',0,100,55,5)
    min_volume = c2.number_input('最低成交量(張)',0,100000,500,500)
    only_bull = c3.checkbox('只看收盤上漲',False)
    if st.button('🚀 開始掃描',type='primary',use_container_width=True):
        with st.spinner('批次下載市場資料並計算多因子中...'):
            market_data = download_market_data(target, period='5y')
            today_inst = inst[inst.date == latest_date].copy() if not inst.empty else pd.DataFrame()
            today_margin = margin[margin.date == latest_date].copy() if not margin.empty else pd.DataFrame()
            result = run_scan(target, market_data, today_inst, today_margin, stocks, strategy, use_broker, broker_fetch if use_broker else None)
            if not result.empty:
                # 用目前多因子權重重新評分。
                rescored=[]
                for _, rr in result.iterrows():
                    df=market_data.get(rr.ticker)
                    row=analyze_stock(rr.ticker, df, today_inst[today_inst.code==rr.code].iloc[0].to_dict() if not today_inst[today_inst.code==rr.code].empty else {}, today_margin[today_margin.code==rr.code].iloc[0].to_dict() if not today_margin[today_margin.code==rr.code].empty else {}, None, st.session_state.weights)
                    if row:
                        row.update({'code':rr.code,'name':rr['name'],'market':rr['market']}); rescored.append(row)
                result = pd.DataFrame(rescored) if rescored else result
                result = result[result.score >= min_score]
                result = result[result.volume_lots >= min_volume]
                if only_bull: result = result[result.change_pct > 0]
            st.session_state.scan_result = result
            save_scan(strategy, result.to_dict('records') if not result.empty else [])
    result = st.session_state.scan_result
    if result is not None and not result.empty:
        st.success(f'符合條件：{len(result)} 檔')
        result_table(result)
        st.download_button('⬇️ 下載 CSV', result.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig'), 'scan_result.csv', 'text/csv')
        excel=io.BytesIO()
        with pd.ExcelWriter(excel, engine='openpyxl') as writer: result.to_excel(writer,index=False,sheet_name='選股結果')
        st.download_button('⬇️ 下載 Excel', excel.getvalue(), 'scan_result.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        labels={f"{r.code} {r['name']}":r.ticker for _,r in result.iterrows()}
        selected=st.selectbox('選擇個股深入分析', list(labels.keys()))
        t=labels[selected]; r=result[result.ticker==t].iloc[0].to_dict(); df=compute_indicators(get_stock_history(t,'5y')); render_stock_detail(r,df)
    else: st.info('尚無掃描結果。請設定條件後按「開始掃描」。')

with backtest_tab:
    st.subheader('🧪 多因子回測引擎')
    st.caption('訊號於 T 日收盤計算，績效以 T+1 日開盤→收盤計算，避免直接使用未來價格。未模擬滑價、漲跌停、撮合失敗及稅費差異。')
    bt_mode = st.radio('回測範圍',['市值核心股(30檔)','自選股','自訂股票'],horizontal=True,key='bt_mode')
    if bt_mode == '自訂股票':
        bt_sel=st.multiselect('回測股票',stocks.display.tolist(),key='bt_sel'); bt_target=stocks[stocks.display.isin(bt_sel)].ticker.tolist()
    else: bt_target=choose_universe(bt_mode)
    c1,c2,c3,c4=st.columns(4)
    start=c1.date_input('開始日期', date.today()-timedelta(days=365*3), key='bt_start')
    end=c2.date_input('結束日期', date.today(), key='bt_end')
    bt_score=c3.slider('進場最低分數',0,100,65,5,key='bt_score')
    top_n=c4.slider('每日持股數',1,20,5,key='bt_topn')
    cost=st.number_input('單次換股成本（估計）',0.0,0.02,0.0015,0.0005,format='%.4f',key='bt_cost')
    if st.button('▶️ 執行回測',type='primary',use_container_width=True,key='run_bt'):
        if start >= end: st.error('開始日期必須早於結束日期。')
        elif not bt_target: st.warning('請選擇至少一檔股票。')
        else:
            with st.spinner(f'下載 {len(bt_target)} 檔歷史資料並逐日回測中...'):
                bt_data=download_market_data(bt_target, period='5y')
                bt_result, bt_metrics=backtest_market(bt_data, start, end, st.session_state.weights, bt_score, top_n, cost)
                st.session_state.bt_result=bt_result; st.session_state.bt_metrics=bt_metrics
    if st.session_state.get('bt_result') is not None and not st.session_state.bt_result.empty:
        m=st.session_state.bt_metrics
        cols=st.columns(6)
        cols[0].metric('累積報酬',f"{m['total_return']:.2%}")
        cols[1].metric('年化報酬',f"{m['annual_return']:.2%}")
        cols[2].metric('年化波動',f"{m['volatility']:.2%}")
        cols[3].metric('Sharpe',f"{m['sharpe']:.2f}")
        cols[4].metric('最大回撤',f"{m['max_drawdown']:.2%}")
        cols[5].metric('勝率',f"{m['win_rate']:.2%}")
        br=st.session_state.bt_result.copy(); fig=go.Figure(); fig.add_trace(go.Scatter(x=br.date,y=br.equity,mode='lines',name='策略淨值')); fig.update_layout(height=420,template='plotly_dark',yaxis_title='Equity'); st.plotly_chart(fig,use_container_width=True)
        st.write(f"交易筆數：{m['trades']}｜平均每日持股：{m['avg_positions']:.1f}｜簡化基準（所有股票平均 T+1 報酬）累積：{m['benchmark_return']:.2%}")
        st.dataframe(br.tail(100).sort_values('date',ascending=False),use_container_width=True,hide_index=True)

with perf_tab:
    st.subheader('📈 策略績效統計')
    if st.session_state.get('bt_result') is None or st.session_state.get('bt_result').empty:
        st.info('請先到「回測引擎」執行一次回測。')
    else:
        m=st.session_state.bt_metrics; br=st.session_state.bt_result.copy(); br['month']=pd.to_datetime(br.date).dt.to_period('M').astype(str)
        monthly=br.groupby('month')['return'].apply(lambda x:(1+x).prod()-1).reset_index(name='月報酬')
        st.dataframe(monthly.tail(36),use_container_width=True,hide_index=True)
        positive=(monthly['月報酬']>0).mean() if not monthly.empty else 0
        c1,c2,c3,c4=st.columns(4); c1.metric('正報酬月份',f'{positive:.1%}'); c2.metric('最佳月',f"{monthly['月報酬'].max():.2%}"); c3.metric('最差月',f"{monthly['月報酬'].min():.2%}"); c4.metric('交易筆數',m['trades'])
        st.download_button('⬇️ 匯出回測明細 CSV',br.to_csv(index=False,encoding='utf-8-sig').encode('utf-8-sig'),'backtest_detail.csv','text/csv')

with chip_tab:
    st.subheader(f'📊 法人與信用交易｜最新交易日 {latest_date}')
    kind=st.selectbox('排行榜',['外資買超','外資賣超','投信買超','投信賣超','融資增加','融資減少','融券賣出','融券增加','借券賣出'])
    period=st.radio('統計天期',['當日','近3日','近5日'],horizontal=True)
    days={'當日':1,'近3日':3,'近5日':5}[period]; ds=trade_dates[:days]
    if kind.startswith('外資') or kind.startswith('投信'):
        d=inst[inst.date.isin(ds)].groupby(['code','name'])[['foreign','trust','total_inst']].sum().reset_index(); col='foreign' if kind.startswith('外資') else 'trust'; d=d.sort_values(col,ascending='賣' in kind).head(20); d.columns=['代碼','名稱','外資(張)','投信(張)','三大法人(張)']; st.dataframe(d,use_container_width=True,hide_index=True)
    else:
        d=margin[margin.date.isin(ds)].groupby(['code','name'])[['margin_buy','margin_diff','short_sell','short_diff','sbl_short_sell','sbl_diff']].sum().reset_index(); mapping={'融資增加':'margin_diff','融資減少':'margin_diff','融券賣出':'short_sell','融券增加':'short_diff','借券賣出':'sbl_short_sell'}; col=mapping[kind]; asc=kind in ['融資減少']; d=d.sort_values(col,ascending=asc).head(20); d.columns=['代碼','名稱','融資買進','融資增減','融券賣出','融券增減','借券賣出','借券增減']; st.dataframe(d,use_container_width=True,hide_index=True)

with broker_tab:
    st.subheader('🏦 主力分點集中度')
    if not FINMIND_TOKEN: st.warning('未設定 FINMIND_TOKEN。仍可查詢，但 FinMind 可能要求 Token 或限制頻率。')
    code=st.text_input('股票代碼','2330',max_chars=4); days=st.selectbox('統計天數',[5,10,20,60],index=1)
    if st.button('查詢分點',use_container_width=True):
        b=fetch_broker_concentration(code,days,FINMIND_TOKEN)
        if b.get('concentration') is None: st.warning('目前沒有足夠的分點資料。')
        else: st.metric(f'{days}日主力淨集中度',f"{b['concentration']:.2f}%"); st.write('主要買方：', '、'.join(b['top_brokers']) if b['top_brokers'] else '無明顯買方')

with detail_tab:
    st.subheader('🔬 個股診斷')
    q=st.text_input('輸入股票代碼','2330',max_chars=4)
    if st.button('載入個股',use_container_width=True): st.session_state.selected_ticker=ticker_for(q)
    if st.session_state.selected_ticker:
        t=st.session_state.selected_ticker; code=t.split('.')[0]; df=get_stock_history(t,'5y')
        if not df.empty:
            df=compute_indicators(df); im=inst[inst.date==latest_date]; mm=margin[margin.date==latest_date]
            ir=im[im.code==code].iloc[0].to_dict() if not im[im.code==code].empty else {}; mr=mm[mm.code==code].iloc[0].to_dict() if not mm[mm.code==code].empty else {}
            row=analyze_stock(t,df,ir,mr,None,st.session_state.weights); row['code']=code; row['name']=stock_name(code); render_stock_detail(row,df)
        else: st.error('無法取得此股票歷史資料。')

st.divider(); st.caption('V2.1 回測為研究型模擬：不代表未來績效，也未完整模擬滑價、稅費、流動性、漲跌停與實際成交。')
