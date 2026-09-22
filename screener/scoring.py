import numpy as np
import pandas as pd

STRATEGIES = {
    '🔥 強勢突破': {'break20': True, 'break60': False, 'volume': True, 'foreign': False, 'trust': False, 'margin_down': False, 'broker': False},
    '💰 法人吃貨': {'break20': False, 'break60': False, 'volume': False, 'foreign': True, 'trust': True, 'margin_down': False, 'broker': True},
    '🚀 量價爆發': {'break20': True, 'break60': False, 'volume': True, 'foreign': False, 'trust': False, 'margin_down': False, 'broker': False},
    '🧹 融資退潮': {'break20': False, 'break60': False, 'volume': False, 'foreign': True, 'trust': False, 'margin_down': True, 'broker': False},
    '⚔️ 主力集中': {'break20': False, 'break60': False, 'volume': False, 'foreign': False, 'trust': False, 'margin_down': False, 'broker': True},
    '🧠 綜合評分': {'break20': False, 'break60': False, 'volume': False, 'foreign': False, 'trust': False, 'margin_down': False, 'broker': False},
}

DEFAULT_WEIGHTS = {
    'trend': 20,
    'momentum': 15,
    'volume': 15,
    'breakout': 15,
    'kd': 10,
    'macd': 10,
    'rsi': 10,
    'risk': 5,
}
WEIGHT_LABELS = {
    'trend': '趨勢 / 均線', 'momentum': '價格動能', 'volume': '量能', 'breakout': '突破',
    'kd': 'KD', 'macd': 'MACD', 'rsi': 'RSI', 'risk': '風險控制'
}


def normalize_weights(weights=None):
    w = DEFAULT_WEIGHTS.copy()
    if weights:
        for k in w:
            if k in weights:
                w[k] = max(0.0, float(weights[k]))
    total = sum(w.values())
    if total <= 0:
        return DEFAULT_WEIGHTS.copy()
    return {k: v * 100.0 / total for k, v in w.items()}


def factor_scores(last):
    """Return eight 0~100 technical factor scores for a single daily row."""
    def b(x): return 1.0 if bool(x) else 0.0
    close = float(last.get('Close', np.nan))
    ma20 = float(last.get('MA20', np.nan))
    ma60 = float(last.get('MA60', np.nan))
    ma5 = float(last.get('MA5', np.nan))
    rsi6 = float(last.get('RSI6', 50) or 50)
    rsi12 = float(last.get('RSI12', 50) or 50)
    rsi14 = float(last.get('RSI14', 50) or 50)
    vr = float(last.get('VOL_RATIO', 0) or 0)
    k = float(last.get('K', 50) or 50)
    d = float(last.get('D', 50) or 50)
    macd = float(last.get('MACD', 0) or 0)
    signal = float(last.get('MACD_SIGNAL', 0) or 0)

    trend = 100 * np.mean([b(close > ma20), b(close > ma60), b(last.get('MA20_UP', False)), b(last.get('MA60_UP', False))])
    momentum = float(np.clip((rsi14 - 30) / 40 * 100, 0, 100))
    volume = float(np.clip((vr - 0.7) / 1.8 * 100, 0, 100))
    breakout = 100 * np.mean([b(last.get('BREAK_MA20', False)), b(last.get('BREAK_MA60', False))])
    kd = 100 * np.mean([b(k > d), b(last.get('KD_GOLDEN', False))])
    macd_score = 100 * np.mean([b(macd > signal), b(last.get('MACD_GOLDEN', False))])
    rsi = 100 * np.mean([np.clip((rsi6 - 30) / 40, 0, 1), np.clip((rsi12 - 30) / 40, 0, 1), np.clip((rsi14 - 30) / 40, 0, 1)])
    # 避免追逐極端波動：RSI 過熱、爆量且長黑時扣分。
    candle_bear = close < float(last.get('Open', close))
    risk = 100.0
    if rsi14 >= 75: risk -= 35
    if vr >= 3 and candle_bear: risk -= 35
    if close < ma60: risk -= 30
    risk = float(np.clip(risk, 0, 100))
    return {
        'trend': trend, 'momentum': momentum, 'volume': volume, 'breakout': breakout,
        'kd': kd, 'macd': macd_score, 'rsi': rsi, 'risk': risk
    }


def weighted_factor_score(last, weights=None):
    w = normalize_weights(weights)
    factors = factor_scores(last)
    score = sum(factors[k] * w[k] / 100 for k in factors)
    return float(np.clip(score, 0, 100)), factors


def analyze_stock(ticker, df, inst=None, margin=None, broker=None, weights=None):
    if df is None or df.empty:
        return None
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else last
    foreign = (inst or {}).get('foreign', 0)
    trust = (inst or {}).get('trust', 0)
    margin_diff = (margin or {}).get('margin_diff', 0)
    conc = (broker or {}).get('concentration') if broker else None

    technical = 0; volume = 0; chip = 0; broker_score = 0; signals = []
    if bool(last.get('ABOVE_MA20', False)): technical += 6; signals.append('站上20MA')
    if bool(last.get('ABOVE_MA60', False)): technical += 6; signals.append('站上60MA')
    if bool(last.get('MA20_UP', False)): technical += 6; signals.append('20MA上彎')
    if bool(last.get('MA60_UP', False)): technical += 6; signals.append('60MA上彎')
    if bool(last.get('KD_GOLDEN', False)): technical += 8; signals.append('KD黃金交叉')
    if bool(last.get('MACD_GOLDEN', False)): technical += 8; signals.append('MACD黃金交叉')
    if float(last.get('RSI14', 50)) >= 50: technical += 5; signals.append('RSI站上50')
    technical = min(40, technical)
    vr = float(last.get('VOL_RATIO', 0) or 0)
    if vr >= 1.5: volume += 10; signals.append('成交量放大')
    if vr >= 2: volume += 5; signals.append('爆量')
    if float(last['Close']) > float(last['Open']): volume += 5
    volume = min(20, volume)
    if foreign > 0: chip += 10; signals.append('外資買超')
    if trust > 0: chip += 10; signals.append('投信買超')
    if margin_diff < 0: chip += 10; signals.append('融資下降')
    chip = min(30, chip)
    if conc is not None and conc >= 10: broker_score += 5; signals.append('主力集中')
    if conc is not None and conc >= 20: broker_score += 5; signals.append('主力高度集中')
    broker_score = min(10, broker_score)
    legacy_score = technical + volume + chip + broker_score
    factor_score, factors = weighted_factor_score(last, weights)
    score = factor_score if weights is not None else legacy_score
    return {
        'ticker': ticker, 'close': round(float(last['Close']), 2),
        'change_pct': round((float(last['Close']) / float(prev['Close']) - 1) * 100, 2),
        'volume_lots': int(float(last['Volume']) / 1000), 'volume_ratio': round(vr, 2),
        'score': round(score, 2), 'legacy_score': legacy_score,
        'technical_score': technical, 'volume_score': volume, 'chip_score': chip,
        'broker_score': broker_score, 'foreign': foreign, 'trust': trust,
        'margin_diff': margin_diff, 'broker_concentration': conc,
        'signals': signals, 'factor_scores': factors,
    }


def strategy_pass(row, strategy):
    s = STRATEGIES.get(strategy, STRATEGIES['🧠 綜合評分'])
    sig = set(row.get('signals', []))
    if s['break20'] and '站上20MA' not in sig: return False
    if s['break60'] and '站上60MA' not in sig: return False
    if s['volume'] and row.get('volume_ratio', 0) < 1.5: return False
    if s['foreign'] and row.get('foreign', 0) <= 0: return False
    if s['trust'] and row.get('trust', 0) <= 0: return False
    if s['margin_down'] and row.get('margin_diff', 0) >= 0: return False
    if s['broker'] and (row.get('broker_concentration') is None or row.get('broker_concentration', 0) < 10): return False
    return True
