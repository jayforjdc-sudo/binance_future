"""
간단한 기술적 지표 계산 모듈
talib 대신 사용
"""

import numpy as np
import pandas as pd


def RSI(close_prices, period=14):
    """Relative Strength Index"""
    close_prices = np.asarray(close_prices, dtype=float)
    delta = np.diff(close_prices)
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)

    avg_gain = pd.Series(gain).rolling(window=period).mean().values
    avg_loss = pd.Series(loss).rolling(window=period).mean().values

    rs = avg_gain / (avg_loss + 1e-10)
    rsi = 100 - (100 / (1 + rs))

    # 패딩: 원래 길이에 맞추기
    return np.concatenate([[np.nan], rsi])


def MACD(close_prices, fast=12, slow=26, signal=9):
    """MACD (Moving Average Convergence Divergence)"""
    close_prices = np.asarray(close_prices, dtype=float)
    ema_fast = pd.Series(close_prices).ewm(span=fast).mean().values
    ema_slow = pd.Series(close_prices).ewm(span=slow).mean().values

    macd_line = ema_fast - ema_slow
    signal_line = pd.Series(macd_line).ewm(span=signal).mean().values
    histogram = macd_line - signal_line

    return macd_line, signal_line, histogram


def SMA(close_prices, period):
    """Simple Moving Average"""
    close_prices = np.asarray(close_prices, dtype=float)
    sma = pd.Series(close_prices).rolling(window=period).mean().values
    return sma


def EMA(close_prices, period):
    """Exponential Moving Average"""
    close_prices = np.asarray(close_prices, dtype=float)
    ema = pd.Series(close_prices).ewm(span=period).mean().values
    return ema


def BBANDS(close_prices, period=20, num_std=2):
    """Bollinger Bands"""
    close_prices = np.asarray(close_prices, dtype=float)
    sma = pd.Series(close_prices).rolling(window=period).mean().values
    std = pd.Series(close_prices).rolling(window=period).std().values

    upper = sma + (num_std * std)
    middle = sma
    lower = sma - (num_std * std)

    return upper, middle, lower


def ATR(high, low, close, period=14):
    """Average True Range"""
    high = np.asarray(high, dtype=float)
    low = np.asarray(low, dtype=float)
    close = np.asarray(close, dtype=float)

    tr1 = high - low
    tr2 = np.abs(high - np.roll(close, 1))
    tr3 = np.abs(low - np.roll(close, 1))

    tr = np.maximum(tr1, np.maximum(tr2, tr3))
    atr = pd.Series(tr).rolling(window=period).mean().values

    return atr


def find_pivots(arr, order=5):
    """
    로컬 고점/저점 인덱스 탐지 (RSI 다이버전스용)

    Parameters:
    - arr: 1D numpy array 또는 list (가격 또는 RSI)
    - order: 고점/저점 좌우로 필요한 캔들 수 (확인용)

    Returns:
    - (pivot_highs, pivot_lows) - 각각 [(index, value), ...] 리스트
    """
    arr = np.asarray(arr, dtype=float)
    n = len(arr)
    pivot_highs, pivot_lows = [], []

    for i in range(order, n - order):
        window = arr[i - order: i + order + 1]
        # NaN 무시하고 비교
        if arr[i] == np.nanmax(window):
            pivot_highs.append((i, arr[i]))
        if arr[i] == np.nanmin(window):
            pivot_lows.append((i, arr[i]))

    return pivot_highs, pivot_lows


def detect_bearish_divergence(price_highs, rsi_highs):
    """
    Bearish Divergence 감지 (RSI 다이버전스)

    조건: 가격은 신고가 갱신하지만 RSI는 신고가 미갱신
    의미: 상승 모멘텀 약화 → 하락 반전 신호

    Parameters:
    - price_highs: find_pivots()로 반환된 가격 피벗 고점 리스트
    - rsi_highs: find_pivots()로 반환된 RSI 피벗 고점 리스트

    Returns:
    - True: 베어리쉬 다이버전스 감지
    - False: 다이버전스 없음
    """
    if len(price_highs) < 2 or len(rsi_highs) < 2:
        return False

    # 가장 최근 두 피벗 비교
    price_prev_val, price_last_val = price_highs[-2][1], price_highs[-1][1]
    rsi_prev_val,   rsi_last_val   = rsi_highs[-2][1],   rsi_highs[-1][1]

    # 가격은 올랐지만 RSI는 내려감 = 베어리쉬 다이버전스
    return price_last_val > price_prev_val and rsi_last_val < rsi_prev_val


def detect_bullish_divergence(price_lows, rsi_lows):
    """
    Bullish Divergence 감지 (RSI 다이버전스)

    조건: 가격은 신저가 갱신하지만 RSI는 신저가 미갱신
    의미: 하락 모멘텀 약화 → 상승 반전 신호

    Parameters:
    - price_lows: find_pivots()로 반환된 가격 피벗 저점 리스트
    - rsi_lows: find_pivots()로 반환된 RSI 피벗 저점 리스트

    Returns:
    - True: 불리시 다이버전스 감지
    - False: 다이버전스 없음
    """
    if len(price_lows) < 2 or len(rsi_lows) < 2:
        return False

    # 가장 최근 두 피벗 비교
    price_prev_val, price_last_val = price_lows[-2][1], price_lows[-1][1]
    rsi_prev_val,   rsi_last_val   = rsi_lows[-2][1],   rsi_lows[-1][1]

    # 가격은 내렸지만 RSI는 올라감 = 불리시 다이버전스
    return price_last_val < price_prev_val and rsi_last_val > rsi_prev_val
