"""
Binance Futures BTC Trading Bot
청산 위험을 최소화한 보수적 BTC 봇 (SHORT/LONG 선택형)
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import time
from dotenv import load_dotenv

import requests
import pandas as pd
import numpy as np
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceOrderException
from sys import path as sys_path
from pathlib import Path
sys_path.insert(0, str(Path(__file__).parent.parent))
from shared.indicators import RSI, MACD, SMA, EMA, BBANDS, ATR, find_pivots, detect_bearish_divergence, detect_bullish_divergence
from shared.telegram_notifier import TelegramNotifier

# .env 파일 로드
load_dotenv()

# ============================================================================
# 설정
# ============================================================================

class BotConfig:
    """봇 설정"""
    # API 설정
    API_KEY = os.getenv('BINANCE_API_KEY', '')
    API_SECRET = os.getenv('BINANCE_API_SECRET', '')

    # Telegram 알림 설정
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')

    # 거래 설정
    INITIAL_BALANCE = 40  # USDT (50달러 중 안전 마진 포함)
    LEVERAGE = 2  # 초기 레버리지 (2배 - 보수적)
    MAX_LEVERAGE = 5  # 최대 레버리지

    # 포지션 사이징
    POSITION_SIZE_PERCENT = 0.10  # 계좌의 10% 사용 (15% → 10%으로 낮춤)
    
    # 손절매/이익실현
    STOP_LOSS_PERCENT = 2.0  # 진입가 대비 손절매 %
    TAKE_PROFIT_PERCENT = 5.0  # 진입가 대비 이익실현 %
    TRAILING_STOP_PERCENT = 2.0  # 최저가 대비 트레일링 스탑 %

    # 그리드 매매 설정
    GRID_NUM = 3      # 그리드 개수
    GRID_SPACING = 0.5  # 그리드 간격 (%)

    # 거래 방향 설정
    TRADING_MODE = os.getenv('TRADING_MODE', 'SHORT')  # 'SHORT' 또는 'LONG'

    # 자동 모드 전환 설정
    AUTO_MODE_SWITCH = os.getenv('AUTO_MODE_SWITCH', 'True').lower() == 'true'  # RSI 기반 자동 전환
    RSI_LONG_THRESHOLD = 60   # RSI > 60이면 LONG
    RSI_SHORT_THRESHOLD = 40  # RSI < 40이면 SHORT

    # 추세 감지
    RSI_PERIOD = 14
    RSI_OVERBOUGHT = 70
    RSI_OVERSOLD = 30
    
    MACD_FAST = 12
    MACD_SLOW = 26
    MACD_SIGNAL = 9
    
    # 거래쌍
    SYMBOLS = ['BTCUSDT']  # BTCUSDT만 거래 (검증됨)
    
    # 시간 설정
    TIMEFRAME = '1h'  # 1시간 봉
    CANDLES = 200  # 200개 봉 분석
    
    # 안전 설정
    MIN_VOLUME_USDT = 10000  # 최소 거래량
    MAX_DRAWDOWN_PERCENT = 10  # 최대 낙폭
    
    # 로깅
    LOG_LEVEL = logging.INFO

# ============================================================================
# 로깅 설정
# ============================================================================

def setup_logger():
    logger = logging.getLogger('BinanceBTCBot')
    logger.setLevel(BotConfig.LOG_LEVEL)
    
    # 파일 로그
    fh = logging.FileHandler('bot_trading.log')
    fh.setLevel(BotConfig.LOG_LEVEL)
    
    # 콘솔 로그
    ch = logging.StreamHandler()
    ch.setLevel(BotConfig.LOG_LEVEL)
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    
    logger.addHandler(fh)
    logger.addHandler(ch)
    
    return logger

logger = setup_logger()

# ============================================================================
# 트레이딩 엔진
# ============================================================================

class BinanceBTCBot:
    def __init__(self):
        """봇 초기화"""
        self.client = Client(BotConfig.API_KEY, BotConfig.API_SECRET)
        self.positions = {}  # 활성 포지션 추적
        self.trades_history = []  # 거래 기록
        self.account_balance = BotConfig.INITIAL_BALANCE
        self.current_mode = BotConfig.TRADING_MODE  # 현재 거래 모드
        self.mode_switch_count = 0  # 모드 전환 횟수

        # 바이낸스 선물 계좌 초기화
        try:
            self._initialize_futures_account()
        except Exception as e:
            logger.error(f"선물 계좌 초기화 실패: {e}")
            raise
    
    def _initialize_futures_account(self):
        """선물 계좌 설정"""
        try:
            # 포지션 모드 설정 (양방향)
            self.client.futures_change_position_mode(dualSidePosition=True)
            logger.info("포지션 모드: 양방향(Long/Short 동시 가능)")
            
            # 마진 타입 설정 (교차마진)
            self.client.futures_change_margin_type(symbol='BTCUSDT', marginType='CROSSED')
            logger.info("마진 타입: 교차마진")
        except Exception as e:
            # 이미 설정된 경우 무시
            if "No need to change" in str(e):
                logger.info("선물 계좌 설정은 이미 적용됨")
            else:
                logger.warning(f"계좌 설정 경고: {e}")

    def check_and_switch_mode(self, rsi: float) -> bool:
        """
        RSI 기반 자동 모드 전환
        Returns: True if mode switched, False otherwise
        """
        if not BotConfig.AUTO_MODE_SWITCH:
            return False

        recommended_mode = None

        # RSI 기반 모드 결정
        if rsi > BotConfig.RSI_LONG_THRESHOLD:
            recommended_mode = 'LONG'
        elif rsi < BotConfig.RSI_SHORT_THRESHOLD:
            recommended_mode = 'SHORT'
        # 40-60 범위는 현재 모드 유지

        # 모드 변경 필요한지 확인
        if recommended_mode and recommended_mode != self.current_mode:
            logger.warning(f"📊 모드 전환 감지! RSI: {rsi:.2f}")
            logger.warning(f"  {self.current_mode} → {recommended_mode}")

            # 현재 포지션이 있으면 먼저 청산
            for symbol in BotConfig.SYMBOLS:
                pos = self.get_position(symbol)
                if pos:
                    logger.info(f"  💧 기존 {self.current_mode} 포지션 청산 중...")
                    self.close_position(symbol, f"AUTO_SWITCH_{self.current_mode}_TO_{recommended_mode}")

            # 모드 전환
            self.current_mode = recommended_mode
            self.mode_switch_count += 1
            logger.warning(f"✅ 모드 전환 완료! (총 {self.mode_switch_count}회)")

            return True

        return False

    def get_account_info(self) -> Dict:
        """계좌 정보 조회"""
        try:
            account = self.client.futures_account()
            return {
                'balance': float(account.get('totalWalletBalance', 0)),
                'unrealized_pnl': float(account.get('totalUnrealizedProfit', 0)),
                'margin_level': float(account.get('marginLevel', 100.0)),
                'available_balance': float(account.get('availableBalance', 0)),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"계좌 정보 조회 실패: {e}")
            return {
                'balance': 0,
                'unrealized_pnl': 0,
                'margin_level': 100.0,
                'available_balance': 0,
                'timestamp': datetime.now().isoformat()
            }
    
    def get_position(self, symbol: str) -> Optional[Dict]:
        """현재 포지션 조회"""
        try:
            positions = self.client.futures_position_information(symbol=symbol)
            for pos in positions:
                if float(pos['positionAmt']) != 0:  # 포지션 보유 중
                    return {
                        'symbol': symbol,
                        'position_amount': float(pos['positionAmt']),
                        'entry_price': float(pos['entryPrice']),
                        'mark_price': float(pos['markPrice']),
                        'unrealized_pnl': float(pos['unrealizedProfit']),
                        'unrealized_pnl_percent': float(pos['percentage']),
                        'liquidation_price': float(pos['liquidationPrice']),
                        'margin_type': pos['marginType'],
                        'leverage': float(pos['leverage'])
                    }
            return None
        except Exception as e:
            logger.error(f"{symbol} 포지션 조회 실패: {e}")
            return None
    
    def get_klines(self, symbol: str, interval: str = '1h', limit: int = 200) -> pd.DataFrame:
        """캔들 데이터 조회"""
        try:
            klines = self.client.futures_klines(
                symbol=symbol,
                interval=interval,
                limit=limit
            )
            
            df = pd.DataFrame(klines, columns=[
                'time', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # 데이터 타입 변환
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col])
            
            df['time'] = pd.to_datetime(df['time'], unit='ms')
            return df.tail(limit)
        
        except Exception as e:
            logger.error(f"{symbol} 캔들 데이터 조회 실패: {e}")
            return pd.DataFrame()
    
    def calculate_indicators(self, df: pd.DataFrame) -> Dict:
        """기술적 지표 계산"""
        if len(df) < 50:
            return {}
        
        close = df['close'].values
        high = df['high'].values
        low = df['low'].values
        
        indicators = {}
        
        # RSI
        rsi = RSI(close, period=BotConfig.RSI_PERIOD)
        indicators['rsi'] = float(rsi[-1]) if not np.isnan(rsi[-1]) else 50.0

        # MACD
        macd, signal, hist = MACD(
            close,
            fast=BotConfig.MACD_FAST,
            slow=BotConfig.MACD_SLOW,
            signal=BotConfig.MACD_SIGNAL
        )
        indicators['macd'] = float(macd[-1]) if not np.isnan(macd[-1]) else 0.0
        indicators['macd_signal'] = float(signal[-1]) if not np.isnan(signal[-1]) else 0.0
        indicators['macd_histogram'] = float(hist[-1]) if not np.isnan(hist[-1]) else 0.0

        # Moving Averages
        indicators['sma_20'] = float(SMA(close, 20)[-1]) if not np.isnan(SMA(close, 20)[-1]) else close[-1]
        indicators['sma_50'] = float(SMA(close, 50)[-1]) if not np.isnan(SMA(close, 50)[-1]) else close[-1]
        indicators['ema_12'] = float(EMA(close, 12)[-1]) if not np.isnan(EMA(close, 12)[-1]) else close[-1]

        # Bollinger Bands
        bb_upper, bb_mid, bb_lower = BBANDS(close, period=20)
        indicators['bb_upper'] = float(bb_upper[-1]) if not np.isnan(bb_upper[-1]) else close[-1]
        indicators['bb_mid'] = float(bb_mid[-1]) if not np.isnan(bb_mid[-1]) else close[-1]
        indicators['bb_lower'] = float(bb_lower[-1]) if not np.isnan(bb_lower[-1]) else close[-1]

        # ATR (변동성)
        atr = ATR(high, low, close, period=14)
        indicators['atr'] = float(atr[-1]) if not np.isnan(atr[-1]) else 0.0
        
        # 현재가
        indicators['current_price'] = float(close[-1])
        indicators['previous_price'] = float(close[-2])

        # ===== RSI 다이버전스 감지 =====
        lookback = 50  # 최근 50개 캔들에서 피벗 탐지
        rsi_arr = rsi[-lookback:]
        close_arr = close[-lookback:]

        # 피벗 포인트 찾기
        price_highs, price_lows = find_pivots(close_arr, order=5)
        rsi_highs,   rsi_lows   = find_pivots(rsi_arr,   order=5)

        indicators['price_pivot_highs'] = price_highs
        indicators['price_pivot_lows'] = price_lows
        indicators['rsi_pivot_highs'] = rsi_highs
        indicators['rsi_pivot_lows'] = rsi_lows

        return indicators
    
    def analyze_signal(self, symbol: str, indicators: Dict) -> Tuple[str, float]:
        """
        진입 신호 분석 (SHORT/LONG 모드 분기)
        Returns: (signal, confidence)
            signal: 'SHORT', 'LONG', 'HOLD'
            confidence: 0.0~1.0
        """
        if self.current_mode == 'LONG':
            return self._analyze_long_signal(symbol, indicators)
        return self._analyze_short_signal(symbol, indicators)

    def _analyze_short_signal(self, symbol: str, indicators: Dict) -> Tuple[str, float]:
        """
        SHORT 신호 분석 (기존 로직)
        RSI > 70 (overbought) = 약세 신호
        """
        if not indicators:
            return 'HOLD', 0.0

        signal_score = 0
        max_score = 8

        # RSI 약세 신호 (하락장)
        if indicators['rsi'] > BotConfig.RSI_OVERBOUGHT:
            signal_score += 2
        elif indicators['rsi'] > 65:
            signal_score += 1

        # MACD 약세 신호
        if indicators['macd'] < indicators['macd_signal']:
            signal_score += 1
            if indicators['macd_histogram'] < 0 and indicators['macd_histogram'] < indicators.get('prev_macd_hist', 0):
                signal_score += 1

        # 가격이 상단 볼린저밴드에 가까운 경우
        if indicators['current_price'] > indicators['bb_mid']:
            if indicators['current_price'] > indicators['sma_20']:
                signal_score += 1

        # RSI 베어리쉬 다이버전스 신호
        bearish_div = detect_bearish_divergence(
            indicators.get('price_pivot_highs', []),
            indicators.get('rsi_pivot_highs', [])
        )
        if bearish_div:
            signal_score += 2
            logger.info(f"  ⚡ RSI 베어리쉬 다이버전스 감지!")

        confidence = signal_score / max_score
        if confidence >= 0.35:
            return 'SHORT', min(confidence, 1.0)
        else:
            return 'HOLD', confidence

    def _analyze_long_signal(self, symbol: str, indicators: Dict) -> Tuple[str, float]:
        """
        LONG 신호 분석 (SHORT의 반대 조건)
        RSI < 30 (oversold) = 강세 신호
        """
        if not indicators:
            return 'HOLD', 0.0

        signal_score = 0
        max_score = 8

        # RSI 강세 신호 (상승장)
        if indicators['rsi'] < BotConfig.RSI_OVERSOLD:
            signal_score += 2
        elif indicators['rsi'] < 35:
            signal_score += 1

        # MACD 강세 신호
        if indicators['macd'] > indicators['macd_signal']:
            signal_score += 1
            if indicators['macd_histogram'] > 0 and indicators['macd_histogram'] > indicators.get('prev_macd_hist', 0):
                signal_score += 1

        # 가격이 하단 볼린저밴드에 가까운 경우
        if indicators['current_price'] < indicators['bb_mid']:
            if indicators['current_price'] < indicators['sma_20']:
                signal_score += 1

        # RSI 불리시 다이버전스 신호
        bullish_div = detect_bullish_divergence(
            indicators.get('price_pivot_lows', []),
            indicators.get('rsi_pivot_lows', [])
        )
        if bullish_div:
            signal_score += 2
            logger.info(f"  ⚡ RSI 불리시 다이버전스 감지!")

        confidence = signal_score / max_score
        if confidence >= 0.35:
            return 'LONG', min(confidence, 1.0)
        else:
            return 'HOLD', confidence
    
    def calculate_position_size(self, symbol: str, leverage: int = 2) -> float:
        """
        포지션 크기 계산
        청산 위험을 최소화하는 보수적 계산
        """
        try:
            account_info = self.get_account_info()
            available_balance = account_info['available_balance']
            
            # 계좌의 일정 % 사용
            position_value = available_balance * BotConfig.POSITION_SIZE_PERCENT / leverage
            
            # 최소 포지션 체크
            symbol_info = self.client.futures_exchange_info()
            for symbol_data in symbol_info['symbols']:
                if symbol_data['symbol'] == symbol:
                    min_qty = float(symbol_data['filters'][1]['minQty'])
                    if position_value / self._get_current_price(symbol) < min_qty:
                        logger.warning(f"{symbol} 최소 포지션 미만")
                        return 0
            
            return position_value
        
        except Exception as e:
            logger.error(f"포지션 크기 계산 실패: {e}")
            return 0
    
    def _get_current_price(self, symbol: str) -> float:
        """현재가 조회"""
        try:
            ticker = self.client.futures_symbol_ticker(symbol=symbol)
            return float(ticker['price'])
        except Exception as e:
            logger.error(f"{symbol} 현재가 조회 실패: {e}")
            return 0
    
    def open_short_position(self, symbol: str, leverage: int = 2) -> Optional[Dict]:
        """
        숏 포지션 개설
        """
        try:
            current_price = self._get_current_price(symbol)
            if current_price <= 0:
                logger.error(f"{symbol} 현재가를 가져올 수 없음")
                return None
            
            # 이미 포지션이 있는지 확인
            existing_pos = self.get_position(symbol)
            if existing_pos:
                logger.warning(f"{symbol}에 이미 포지션 존재")
                return None
            
            # 포지션 크기 계산
            position_value = self.calculate_position_size(symbol, leverage)
            if position_value <= 0:
                logger.error(f"{symbol} 포지션 크기 계산 실패")
                return None
            
            quantity = position_value / current_price
            
            # 레버리지 설정
            self.client.futures_change_leverage(symbol=symbol, leverage=leverage)
            logger.info(f"{symbol} 레버리지 설정: {leverage}x")
            
            # 손절매 계산
            stop_loss_price = current_price * (1 + BotConfig.STOP_LOSS_PERCENT / 100)
            take_profit_price = current_price * (1 - BotConfig.TAKE_PROFIT_PERCENT / 100)
            
            # 숏 포지션 개설
            # 주문 1: 숏 진입
            order = self.client.futures_create_order(
                symbol=symbol,
                side='SELL',
                positionSide='SHORT',
                type='MARKET',
                quantity=quantity
            )
            
            logger.info(f"숏 진입: {symbol} {quantity:.4f}개 @ {current_price}")
            
            # 주문 2: 손절매 (TP/SL 주문)
            try:
                stop_loss_order = self.client.futures_create_order(
                    symbol=symbol,
                    side='BUY',
                    positionSide='SHORT',
                    type='STOP_MARKET',
                    quantity=quantity,
                    stopPrice=stop_loss_price
                )
                logger.info(f"손절매 설정: {symbol} {stop_loss_price}")
            except Exception as e:
                logger.warning(f"손절매 설정 실패: {e}")
            
            # 주문 3: 이익실현
            try:
                take_profit_order = self.client.futures_create_order(
                    symbol=symbol,
                    side='BUY',
                    positionSide='SHORT',
                    type='TAKE_PROFIT_MARKET',
                    quantity=quantity,
                    stopPrice=take_profit_price
                )
                logger.info(f"이익실현 설정: {symbol} {take_profit_price}")
            except Exception as e:
                logger.warning(f"이익실현 설정 실패: {e}")
            
            # 포지션 기록
            self.positions[symbol] = {
                'entry_price': current_price,
                'quantity': quantity,
                'leverage': leverage,
                'entry_time': datetime.now(),
                'stop_loss': stop_loss_price,
                'take_profit': take_profit_price,
                'status': 'OPEN',
                'lowest_price_seen': current_price,  # 트레일링 스탑용 최저가 추적
                'trailing_stop': stop_loss_price,    # 현재 트레일링 스탑 레벨
                'stop_order_id': stop_loss_order.get('orderId') if 'stop_loss_order' in locals() else None  # 기존 STOP 주문 ID
            }
            
            return {
                'symbol': symbol,
                'side': 'SHORT',
                'entry_price': current_price,
                'quantity': quantity,
                'leverage': leverage,
                'stop_loss': stop_loss_price,
                'take_profit': take_profit_price,
                'position_value': position_value,
                'risk_amount': position_value * (BotConfig.STOP_LOSS_PERCENT / 100)
            }
        
        except BinanceOrderException as e:
            logger.error(f"{symbol} 숏 진입 실패: {e}")
            return None
        except Exception as e:
            logger.error(f"{symbol} 숏 진입 중 오류: {e}")
            return None

    def open_grid_position(self, symbol: str, leverage: int = 2, side: str = 'SHORT') -> Optional[Dict]:
        """
        그리드 매매로 포지션 진입 (SHORT 또는 LONG)
        - SHORT: 현재가 위에 3개 레벨의 LIMIT SELL 주문
        - LONG: 현재가 아래에 3개 레벨의 LIMIT BUY 주문
        """
        try:
            current_price = self._get_current_price(symbol)
            if current_price <= 0:
                logger.error(f"{symbol} 현재가를 가져올 수 없음")
                return None

            # 이미 포지션이 있는지 확인
            existing_pos = self.get_position(symbol)
            if existing_pos:
                logger.warning(f"{symbol}에 이미 포지션 존재")
                return None

            # 레버리지 설정
            self.client.futures_change_leverage(symbol=symbol, leverage=leverage)

            # 포지션 크기 계산
            account_info = self.get_account_info()
            available_balance = account_info['available_balance']
            total_value = available_balance * BotConfig.POSITION_SIZE_PERCENT / leverage
            unit_value = total_value / BotConfig.GRID_NUM

            # 손절매/익절 가격 결정 (side에 따라)
            if side == 'LONG':
                # LONG: 손절매는 아래(-), 익절은 위(+)
                stop_loss_price = round(
                    current_price * (1 - BotConfig.STOP_LOSS_PERCENT / 100) *
                    (1 - BotConfig.GRID_SPACING * BotConfig.GRID_NUM / 100), 2
                )
                take_profit_price = round(current_price * (1 + BotConfig.TAKE_PROFIT_PERCENT / 100), 2)
            else:  # SHORT
                # SHORT: 손절매는 위(+), 익절은 아래(-)
                stop_loss_price = round(
                    current_price * (1 + BotConfig.STOP_LOSS_PERCENT / 100) *
                    (1 + BotConfig.GRID_SPACING * BotConfig.GRID_NUM / 100), 2
                )
                take_profit_price = round(current_price * (1 - BotConfig.TAKE_PROFIT_PERCENT / 100), 2)

            # 그리드 레벨 생성 및 주문 배치
            grid_levels = []
            mode_str = "롱" if side == 'LONG' else "숏"
            logger.info(f"🔗 {symbol} {mode_str} 그리드 매매 시작 (현재가: {current_price:.2f})")

            for i in range(1, BotConfig.GRID_NUM + 1):
                if side == 'LONG':
                    # LONG: 현재가 아래로 배치 (-0.5%, -1.0%, -1.5%)
                    level_price = round(current_price * (1 - BotConfig.GRID_SPACING * i / 100), 2)
                    order_side = 'BUY'
                else:
                    # SHORT: 현재가 위로 배치 (+0.5%, +1.0%, +1.5%)
                    level_price = round(current_price * (1 + BotConfig.GRID_SPACING * i / 100), 2)
                    order_side = 'SELL'

                unit_qty = round(unit_value / level_price, 4)

                # LIMIT 주문
                try:
                    order = self.client.futures_create_order(
                        symbol=symbol,
                        side=order_side,
                        positionSide=side,
                        type='LIMIT',
                        timeInForce='GTC',
                        price=level_price,
                        quantity=unit_qty
                    )
                    grid_levels.append({
                        'price': level_price,
                        'quantity': unit_qty,
                        'order_id': order['orderId'],
                        'filled': False
                    })
                    logger.info(f"  📐 그리드 {i}: {level_price:.2f} USDT x {unit_qty}")
                except Exception as e:
                    logger.error(f"  그리드 {i} 주문 실패: {e}")
                    continue

            if not grid_levels:
                logger.error(f"{symbol} 그리드 주문 모두 실패")
                return None

            # 포지션 기록 (초기 상태)
            self.positions[symbol] = {
                'entry_price': 0.0,  # 체결될 때 업데이트
                'quantity': 0.0,
                'leverage': leverage,
                'entry_time': datetime.now(),
                'stop_loss': stop_loss_price,
                'take_profit': take_profit_price,
                'status': 'GRID_OPEN',
                'lowest_price_seen': current_price if side == 'SHORT' else float('inf'),
                'highest_price_seen': float('-inf') if side == 'SHORT' else current_price,
                'trailing_stop': stop_loss_price,
                'stop_order_id': None,
                # 그리드 전용 필드
                'side': side,  # 포지션 방향 기록
                'grid_levels': grid_levels,
                'grid_filled_count': 0,
                'grid_unit_qty': unit_qty
            }

            logger.info(f"✅ {symbol} {mode_str} 그리드 배치 완료 (레벨: {len(grid_levels)}개)")
            return self.positions[symbol]

        except Exception as e:
            logger.error(f"{symbol} 그리드 포지션 진입 실패: {e}")
            return None

    def close_position(self, symbol: str, reason: str = "MANUAL", side: Optional[str] = None) -> Optional[Dict]:
        """
        포지션 종료 (SHORT 또는 LONG)
        포지션 청산 전 모든 미결제 주문 취소
        """
        try:
            position = self.get_position(symbol)
            if not position:
                logger.warning(f"{symbol}에 종료할 포지션 없음")
                return None

            # side가 지정되지 않으면 self.positions에서 읽기
            if side is None:
                side = self.positions.get(symbol, {}).get('side', 'SHORT')

            # 포지션 청산 전 미결제 주문 모두 취소
            try:
                self.client.futures_cancel_all_open_orders(symbol=symbol)
                logger.info(f"  {symbol} 미결제 주문 모두 취소됨")
            except Exception as e:
                logger.debug(f"  미결제 주문 취소 실패 (없을 수도): {e}")

            current_price = position['mark_price']
            quantity = abs(position['position_amount'])

            # 포지션 종료 (side에 따라 반대 방향)
            if side == 'LONG':
                close_side = 'SELL'
            else:
                close_side = 'BUY'

            order = self.client.futures_create_order(
                symbol=symbol,
                side=close_side,
                positionSide=side,
                type='MARKET',
                quantity=quantity
            )

            exit_price = current_price
            pnl = position['unrealized_pnl']
            pnl_percent = position['unrealized_pnl_percent']

            mode_str = "롱" if side == 'LONG' else "숏"
            logger.info(f"{mode_str} 종료: {symbol} @ {exit_price} | PnL: {pnl:.2f} USDT ({pnl_percent:.2f}%)")

            # 거래 기록 저장
            if symbol in self.positions:
                self.positions[symbol]['status'] = 'CLOSED'
                self.positions[symbol]['exit_price'] = exit_price
                self.positions[symbol]['exit_time'] = datetime.now()
                self.positions[symbol]['pnl'] = pnl
                self.positions[symbol]['pnl_percent'] = pnl_percent
                self.positions[symbol]['close_reason'] = reason

                self.trades_history.append(self.positions[symbol].copy())

            return {
                'symbol': symbol,
                'exit_price': exit_price,
                'pnl': pnl,
                'pnl_percent': pnl_percent,
                'reason': reason
            }

        except Exception as e:
            logger.error(f"{symbol} 포지션 종료 실패: {e}")
            return None

    def close_short_position(self, symbol: str, reason: str = "MANUAL") -> Optional[Dict]:
        """
        숏 포지션 종료 (호환성 유지)
        """
        return self.close_position(symbol, reason, side='SHORT')
    
    def monitor_position(self, symbol: str) -> Optional[Dict]:
        """
        포지션 모니터링 및 위험 평가
        트레일링 스탑 기능 포함
        """
        try:
            position = self.get_position(symbol)
            if not position:
                return None

            account_info = self.get_account_info()
            margin_level = account_info['margin_level']

            # 청산 위험 평가
            risk_level = 'LOW'
            if margin_level < 50:
                risk_level = 'HIGH'
                logger.warning(f"⚠️ {symbol} 청산 위험 HIGH (마진율: {margin_level:.2f}%)")
                # 자동 포지션 종료 권장
                return {
                    'symbol': symbol,
                    'risk_level': risk_level,
                    'margin_level': margin_level,
                    'action': 'CLOSE_RECOMMENDED'
                }
            elif margin_level < 100:
                risk_level = 'MEDIUM'
                logger.warning(f"⚠️ {symbol} 청산 위험 MEDIUM (마진율: {margin_level:.2f}%)")

            # ===== 그리드 매매 체결 추적 =====
            if symbol in self.positions and self.positions[symbol].get('status') == 'GRID_OPEN':
                pos = self.positions[symbol]
                for level in pos['grid_levels']:
                    if level['filled']:
                        continue
                    try:
                        order_status = self.client.futures_get_order(symbol=symbol, orderId=level['order_id'])
                        if order_status['status'] == 'FILLED':
                            level['filled'] = True
                            pos['grid_filled_count'] += 1
                            pos['quantity'] += level['quantity']

                            # 가중 평균 진입가 업데이트
                            if pos['quantity'] > 0:
                                filled_levels = [l for l in pos['grid_levels'] if l['filled']]
                                pos['entry_price'] = sum(l['price'] * l['quantity'] for l in filled_levels) / pos['quantity']
                                logger.info(f"  ✅ 그리드 체결! ({pos['grid_filled_count']}/{len(pos['grid_levels'])}) 평균 진입가: {pos['entry_price']:.2f}")

                            # 모든 그리드가 체결되면 상태 변경
                            if pos['grid_filled_count'] == len(pos['grid_levels']):
                                pos['status'] = 'OPEN'
                                logger.info(f"  🎯 모든 그리드 체결 완료!")
                    except Exception as e:
                        logger.debug(f"  그리드 주문 상태 조회 실패: {e}")

            # ===== 트레일링 스탑 로직 =====
            if symbol in self.positions:
                current_price = float(position['mark_price'])
                pos = self.positions[symbol]
                side = pos.get('side', 'SHORT')

                if side == 'LONG':
                    # LONG: 최고가 추적 (가격이 올라가는 게 유리)
                    if current_price > pos.get('highest_price_seen', 0):
                        pos['highest_price_seen'] = current_price
                        new_trailing_stop = round(current_price * (1 - BotConfig.TRAILING_STOP_PERCENT / 100), 2)

                        # 기존 STOP 주문이 있으면 취소하고 교체
                        if pos.get('stop_order_id'):
                            try:
                                self.client.futures_cancel_order(symbol=symbol, orderId=pos['stop_order_id'])
                                logger.info(f"  🔄 기존 STOP 주문 취소: {pos['stop_order_id']}")
                            except Exception as e:
                                logger.debug(f"  STOP 주문 취소 실패 (이미 체결됐을 수도): {e}")

                        # 새로운 STOP 주문 생성 (LONG은 SELL로 손절)
                        try:
                            new_stop_order = self.client.futures_create_order(
                                symbol=symbol,
                                side='SELL',
                                positionSide='LONG',
                                type='STOP_MARKET',
                                quantity=pos['quantity'],
                                stopPrice=new_trailing_stop
                            )
                            pos['stop_order_id'] = new_stop_order['orderId']
                            pos['trailing_stop'] = new_trailing_stop
                            logger.info(f"  🔄 롱 트레일링 스탑 업데이트: {new_trailing_stop:.2f} USDT (최고가: {current_price:.2f})")
                        except Exception as e:
                            logger.warning(f"  새로운 STOP 주문 생성 실패: {e}")

                    # 트레일링 스탑 돌파 감지 (LONG은 가격이 아래로 떨어지면 손절)
                    if current_price <= pos.get('trailing_stop', 0):
                        logger.warning(f"⚠️ {symbol} 롱 트레일링 스탑 부분! (현재가: {current_price:.2f}, 스탑: {pos['trailing_stop']:.2f})")
                        return {
                            'symbol': symbol,
                            'risk_level': risk_level,
                            'margin_level': margin_level,
                            'action': 'TRAILING_STOP_HIT'
                        }

                else:  # SHORT
                    # SHORT: 최저가 추적 (가격이 내려가는 게 유리)
                    if current_price < pos.get('lowest_price_seen', float('inf')):
                        pos['lowest_price_seen'] = current_price
                        new_trailing_stop = round(current_price * (1 + BotConfig.TRAILING_STOP_PERCENT / 100), 2)

                        # 기존 STOP 주문이 있으면 취소하고 교체
                        if pos.get('stop_order_id'):
                            try:
                                self.client.futures_cancel_order(symbol=symbol, orderId=pos['stop_order_id'])
                                logger.info(f"  🔄 기존 STOP 주문 취소: {pos['stop_order_id']}")
                            except Exception as e:
                                logger.debug(f"  STOP 주문 취소 실패 (이미 체결됐을 수도): {e}")

                        # 새로운 STOP 주문 생성
                        try:
                            new_stop_order = self.client.futures_create_order(
                                symbol=symbol,
                                side='BUY',
                                positionSide='SHORT',
                                type='STOP_MARKET',
                                quantity=pos['quantity'],
                                stopPrice=new_trailing_stop
                            )
                            pos['stop_order_id'] = new_stop_order['orderId']
                            pos['trailing_stop'] = new_trailing_stop
                            logger.info(f"  🔄 숏 트레일링 스탑 업데이트: {new_trailing_stop:.2f} USDT (최저가: {current_price:.2f})")
                        except Exception as e:
                            logger.warning(f"  새로운 STOP 주문 생성 실패: {e}")

                    # 트레일링 스탑 돌파 감지 (SHORT은 가격이 올라가면 손절)
                    if current_price >= pos.get('trailing_stop', 0):
                        logger.warning(f"⚠️ {symbol} 숏 트레일링 스탑 부분! (현재가: {current_price:.2f}, 스탑: {pos['trailing_stop']:.2f})")
                        return {
                            'symbol': symbol,
                            'risk_level': risk_level,
                            'margin_level': margin_level,
                            'action': 'TRAILING_STOP_HIT'
                        }

            return {
                'symbol': symbol,
                'unrealized_pnl': position['unrealized_pnl'],
                'unrealized_pnl_percent': position['unrealized_pnl_percent'],
                'liquidation_price': position['liquidation_price'],
                'margin_level': margin_level,
                'risk_level': risk_level,
                'entry_price': position['entry_price'],
                'mark_price': position['mark_price'],
                'leverage': position['leverage']
            }
        
        except Exception as e:
            logger.error(f"{symbol} 모니터링 실패: {e}")
            return None
    
    def get_trading_stats(self) -> Dict:
        """거래 통계"""
        if not self.trades_history:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'avg_pnl': 0
            }
        
        trades = self.trades_history
        winning = [t for t in trades if t.get('pnl', 0) > 0]
        losing = [t for t in trades if t.get('pnl', 0) <= 0]
        total_pnl = sum(t.get('pnl', 0) for t in trades)
        
        return {
            'total_trades': len(trades),
            'winning_trades': len(winning),
            'losing_trades': len(losing),
            'win_rate': len(winning) / len(trades) * 100 if trades else 0,
            'total_pnl': total_pnl,
            'avg_pnl': total_pnl / len(trades) if trades else 0,
            'best_trade': max((t.get('pnl', 0) for t in trades), default=0),
            'worst_trade': min((t.get('pnl', 0) for t in trades), default=0)
        }
    
    def run(self, test_mode: bool = False):
        """봇 실행"""
        logger.info("=" * 60)
        mode_str = "롱" if BotConfig.TRADING_MODE == 'LONG' else "숏"
        logger.info(f"🤖 Binance {mode_str.upper()} Trading Bot 시작")
        logger.info("=" * 60)
        logger.info(f"거래 모드: {mode_str.upper()}")
        logger.info(f"초기 자본: {BotConfig.INITIAL_BALANCE} USDT")
        logger.info(f"레버리지: {BotConfig.LEVERAGE}~{BotConfig.MAX_LEVERAGE}x")
        logger.info(f"손절매: {BotConfig.STOP_LOSS_PERCENT}%")
        logger.info(f"이익실현: {BotConfig.TAKE_PROFIT_PERCENT}%")
        logger.info("=" * 60)
        
        loop_count = 0
        
        try:
            while True:
                loop_count += 1
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                logger.info(f"\n[Loop {loop_count}] {current_time}")
                
                # 계좌 정보
                account_info = self.get_account_info()
                logger.info(f"계좌 잔액: {account_info['balance']:.2f} USDT | "
                          f"미결제손익: {account_info['unrealized_pnl']:.2f} USDT | "
                          f"마진율: {account_info['margin_level']:.2f}%")
                
                # 각 심볼 분석
                for symbol in BotConfig.SYMBOLS:
                    logger.info(f"\n📊 {symbol} 분석 중...")
                    
                    # 기존 포지션 모니터링
                    existing_pos = self.get_position(symbol)
                    if existing_pos:
                        monitor = self.monitor_position(symbol)
                        if monitor:
                            logger.info(f"  미결제손익: {monitor['unrealized_pnl']:.2f} USDT "
                                      f"({monitor['unrealized_pnl_percent']:.2f}%)")

                            # 청산 위험이 높으면 자동 종료
                            if monitor.get('action') == 'CLOSE_RECOMMENDED':
                                logger.warning(f"  🚨 청산 위험으로 자동 종료 시작")
                                result = self.close_position(symbol, "AUTO_CLOSE_RISK")
                                if result:
                                    logger.info(f"  ✅ 포지션 종료 성공")

                            # 트레일링 스탑 체결
                            elif monitor.get('action') == 'TRAILING_STOP_HIT':
                                logger.warning(f"  🎯 트레일링 스탑 체결!")
                                result = self.close_position(symbol, "TRAILING_STOP")
                                if result:
                                    logger.info(f"  ✅ 포지션 종료 성공")
                        continue
                    
                    # 캔들 데이터 조회
                    df = self.get_klines(symbol, BotConfig.TIMEFRAME, BotConfig.CANDLES)
                    if df.empty:
                        logger.warning(f"  캔들 데이터 조회 실패")
                        continue
                    
                    # 기술적 지표 계산
                    indicators = self.calculate_indicators(df)
                    
                    # 진입 신호 분석
                    signal, confidence = self.analyze_signal(symbol, indicators)

                    # RSI 기반 자동 모드 전환 확인
                    rsi = indicators.get('rsi', 50)
                    if self.check_and_switch_mode(rsi):
                        # 모드가 전환되면 현재 모드로 신호 재분석
                        signal, confidence = self.analyze_signal(symbol, indicators)
                        logger.info(f"  신호 재분석 (모드 전환 후): {signal} (확률: {confidence*100:.1f}%)")

                    logger.info(f"  RSI: {indicators.get('rsi', 0):.2f} | "
                              f"MACD: {indicators.get('macd', 0):.4f} | "
                              f"현재가: {indicators.get('current_price', 0):.2f}")
                    logger.info(f"  신호: {signal} (확률: {confidence*100:.1f}%)")

                    # 신호에 따른 거래 (자동 모드 전환 시 self.current_mode 사용)
                    if signal == 'SHORT' and confidence >= 0.35 and self.current_mode == 'SHORT':
                        logger.info(f"  ✅ 숏 진입 신호 감지!")

                        # 테스트 모드가 아닌 경우만 실제 거래
                        if not test_mode:
                            result = self.open_grid_position(symbol, BotConfig.LEVERAGE, side='SHORT')
                            if result and 'grid_levels' in result:
                                logger.info(f"  그리드 레벨: {len(result['grid_levels'])}개")
                        else:
                            logger.info(f"  [테스트 모드] 실제 거래 미실행")

                    elif signal == 'LONG' and confidence >= 0.35 and self.current_mode == 'LONG':
                        logger.info(f"  ✅ 롱 진입 신호 감지!")

                        # 테스트 모드가 아닌 경우만 실제 거래
                        if not test_mode:
                            result = self.open_grid_position(symbol, BotConfig.LEVERAGE, side='LONG')
                            if result and 'grid_levels' in result:
                                logger.info(f"  그리드 레벨: {len(result['grid_levels'])}개")
                        else:
                            logger.info(f"  [테스트 모드] 실제 거래 미실행")
                
                # 통계
                stats = self.get_trading_stats()
                if stats['total_trades'] > 0:
                    logger.info(f"\n📈 거래 통계")
                    logger.info(f"  총 거래: {stats['total_trades']} | "
                              f"승리율: {stats['win_rate']:.1f}%")
                    logger.info(f"  누적 PnL: {stats['total_pnl']:.2f} USDT | "
                              f"평균: {stats['avg_pnl']:.2f} USDT")
                
                # 대기 (1시간)
                logger.info(f"\n⏰ 다음 분석까지 1시간 대기...")
                time.sleep(3600)
        
        except KeyboardInterrupt:
            logger.info("\n봇이 사용자에 의해 중지됨")
        except Exception as e:
            logger.error(f"봇 실행 중 오류: {e}", exc_info=True)

# ============================================================================
# 메인
# ============================================================================

if __name__ == "__main__":
    try:
        # API 키 확인
        if not BotConfig.API_KEY or not BotConfig.API_SECRET:
            logger.error("❌ API 키가 설정되지 않았습니다.")
            logger.error("환경 변수 설정: BINANCE_API_KEY, BINANCE_API_SECRET")
            exit(1)
        
        # 봇 시작
        bot = BinanceBTCBot()

        # 테스트 모드로 실행 (실제 거래 안 함)
        bot.run(test_mode=False)
    
    except KeyboardInterrupt:
        logger.info("프로그램 종료")
    except Exception as e:
        logger.error(f"프로그램 오류: {e}", exc_info=True)
