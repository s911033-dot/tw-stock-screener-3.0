import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def make_stock_chart(df, title=''):
    df=df.copy(); view=df.tail(500)
    fig=make_subplots(rows=4,cols=1,shared_xaxes=True,vertical_spacing=0.025,row_heights=[0.58,0.16,0.13,0.13])
    fig.add_trace(go.Scatter(x=view.index,y=view['BB_LOWER'],line=dict(color='rgba(80,140,255,.35)',width=1),showlegend=False),row=1,col=1)
    fig.add_trace(go.Scatter(x=view.index,y=view['BB_UPPER'],line=dict(color='rgba(80,140,255,.35)',width=1),fill='tonexty',fillcolor='rgba(80,140,255,.08)',showlegend=False),row=1,col=1)
    fig.add_trace(go.Candlestick(x=view.index,open=view['Open'],high=view['High'],low=view['Low'],close=view['Close'],increasing_line_color='#ff334b',increasing_fillcolor='#ff334b',decreasing_line_color='#00c853',decreasing_fillcolor='#00c853',name='K線'),row=1,col=1)
    for n in [5,20,60,240]:
        fig.add_trace(go.Scatter(x=view.index,y=view[f'MA{n}'],mode='lines',name=f'{n}MA',line=dict(width=1.1)),row=1,col=1)
    buy=view[view['BREAK_MA20']]
    if not buy.empty: fig.add_trace(go.Scatter(x=buy.index,y=buy['Low']*0.99,mode='markers',marker=dict(symbol='triangle-up',size=9),name='突破20MA'),row=1,col=1)
    vc=['#ff334b' if c>=o else '#00c853' for c,o in zip(view['Close'],view['Open'])]
    fig.add_trace(go.Bar(x=view.index,y=view['Volume']/1000,marker_color=vc,name='成交量(張)',showlegend=False),row=2,col=1)
    fig.add_trace(go.Scatter(x=view.index,y=view['VOL5']/1000,name='5日均量',line=dict(width=1),showlegend=False),row=2,col=1)
    fig.add_trace(go.Scatter(x=view.index,y=view['K'],name='K',line=dict(width=1.2),showlegend=False),row=3,col=1)
    fig.add_trace(go.Scatter(x=view.index,y=view['D'],name='D',line=dict(width=1.2),showlegend=False),row=3,col=1)
    fig.add_hline(y=80,line_dash='dash',line_width=.7,row=3,col=1); fig.add_hline(y=20,line_dash='dash',line_width=.7,row=3,col=1)
    fig.add_trace(go.Bar(x=view.index,y=view['MACD_HIST'],name='MACD柱',showlegend=False),row=4,col=1)
    fig.add_trace(go.Scatter(x=view.index,y=view['MACD'],name='MACD',line=dict(width=1.2),showlegend=False),row=4,col=1)
    fig.add_trace(go.Scatter(x=view.index,y=view['MACD_SIGNAL'],name='Signal',line=dict(width=1.2),showlegend=False),row=4,col=1)
    pmin=float(view['Low'].min()); pmax=float(view['High'].max()); pad=max((pmax-pmin)*.08,.01)
    fig.update_yaxes(row=1,col=1,range=[max(0,pmin-pad),pmax+pad],gridcolor='#1e2638',fixedrange=False)
    for r in [2,3,4]: fig.update_yaxes(row=r,col=1,gridcolor='#1e2638',fixedrange=False)
    fig.update_yaxes(row=3,col=1,range=[0,100])
    fig.update_xaxes(rangeslider_visible=False,rangebreaks=[dict(bounds=['sat','mon'])],gridcolor='#1e2638')
    fig.update_layout(height=760,title=title,paper_bgcolor='#0a0e17',plot_bgcolor='#0a0e17',font=dict(color='#cbd5e1'),margin=dict(l=10,r=10,t=45,b=10),hovermode='x unified',legend=dict(orientation='h'))
    return fig
