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
