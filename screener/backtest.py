import numpy as np
import pandas as pd
from indicators.technical import compute_indicators
from .scoring import weighted_factor_score


def _metrics(returns, equity, trades, avg_positions, benchmark=None):
    returns = pd.Series(returns).dropna()
    if returns.empty:
        return {'total_return': 0, 'annual_return': 0, 'volatility': 0, 'sharpe': 0, 'max_drawdown': 0, 'win_rate': 0, 'trades': 0, 'avg_positions': 0, 'benchmark_return': None}
    eq = pd.Series(equity).dropna()
    total = float(eq.iloc[-1] - 1)
    years = max(len(returns) / 252, 1 / 252)
    annual = float((1 + total) ** (1 / years) - 1) if 1 + total > 0 else -1
    vol = float(returns.std(ddof=0) * np.sqrt(252))
    sharpe = float(returns.mean() / (returns.std(ddof=0) + 1e-12) * np.sqrt(252))
    dd = eq / eq.cummax() - 1
    mdd = float(dd.min())
    win = float((returns > 0).mean())
    bench = None
    if benchmark is not None and len(benchmark):
        b = pd.Series(benchmark).dropna()
        bench = float((1 + b).prod() - 1)
    return {'total_return': total, 'annual_return': annual, 'volatility': vol, 'sharpe': sharpe,
            'max_drawdown': mdd, 'win_rate': win, 'trades': int(trades),
            'avg_positions': float(avg_positions or 0), 'benchmark_return': bench}


def backtest_market(market_data, start_date=None, end_date=None, weights=None, min_score=60, top_n=5, transaction_cost=0.0015):
    """Daily close signal -> next trading day's open-to-close return.

    This intentionally avoids look-ahead: the score on T is calculated only from data through T,
    while P/L is realized on T+1. It is a research backtest, not a broker execution simulator.
    """
    series = {}
    for ticker, raw in market_data.items():
        if raw is None or raw.empty: continue
        df = raw.copy()
        df.index = pd.to_datetime(df.index).tz_localize(None) if getattr(df.index, 'tz', None) else pd.to_datetime(df.index)
        df = compute_indicators(df)
        scores = []
        for _, row in df.iterrows():
            score, factors = weighted_factor_score(row, weights)
            scores.append(score)
        df['factor_score'] = scores
        df['next_open'] = df['Open'].shift(-1)
        df['next_close'] = df['Close'].shift(-1)
        df['next_ret'] = df['next_close'] / df['next_open'] - 1
        df['benchmark_ret'] = df['next_close'] / df['Close'] - 1
        series[ticker] = df
    if not series: return pd.DataFrame(), {}

    dates = sorted(set().union(*[set(df.index) for df in series.values()]))
    if start_date: dates = [d for d in dates if d >= pd.Timestamp(start_date)]
    if end_date: dates = [d for d in dates if d <= pd.Timestamp(end_date)]
    rows = []; equity = 1.0; trades = 0; pos_counts = []
    for dt in dates:
        candidates = []
        bench = []
        for ticker, df in series.items():
            if dt not in df.index: continue
            r = df.loc[dt]
            if pd.notna(r.get('benchmark_ret')): bench.append(float(r['benchmark_ret']))
            if pd.notna(r.get('next_ret')) and float(r.get('factor_score', 0)) >= min_score:
                # 趨勢條件由權重決定；這裡不額外加入未設定的主觀條件。
                candidates.append((float(r['factor_score']), ticker, float(r['next_ret'])))
        candidates = sorted(candidates, reverse=True)[:max(1, int(top_n))]
        if candidates:
            gross = float(np.mean([x[2] for x in candidates]))
            net = gross - transaction_cost
            trades += len(candidates); pos_counts.append(len(candidates))
        else:
            gross = net = 0.0; pos_counts.append(0)
        equity *= 1 + net
        rows.append({'date': dt, 'return': net, 'gross_return': gross, 'equity': equity,
                     'positions': len(candidates), 'benchmark_return': float(np.mean(bench)) if bench else 0.0,
                     'selected': [x[1] for x in candidates]})
    result = pd.DataFrame(rows)
    metrics = _metrics(result['return'], result['equity'], trades, np.mean(pos_counts) if pos_counts else 0,
                       result['benchmark_return'] if not result.empty else None)
    return result, metrics
