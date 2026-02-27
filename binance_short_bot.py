"""
Binance Futures Short Trading Bot
청산 위험을 최소화한 보수적 숏 봇
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
from indicators import RSI, MACD, SMA, EMA, BBANDS, ATR
from telegram_notifier import TelegramNotifier

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
    INITIAL_BALANCE = 100  # USDT
    LEVERAGE = 2  # 초기 레버리지 (2~3배 권장)
    MAX_LEVERAGE = 5  # 최대 레버리지
    
    # 포지션 사이징
    POSITION_SIZE_PERCENT = 0.15  # 계좌의 15% 사용
    
    # 손절매/이익실현
    STOP_LOSS_PERCENT = 2.0  # 진입가 대비 손절매 %
    TAKE_PROFIT_PERCENT = 5.0  # 진입가 대비 이익실현 %
    
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
    logger = logging.getLogger('BinanceShorBot')
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

class BinanceShortBot:
    def __init__(self):
        """봇 초기화"""
        self.client = Client(BotConfig.API_KEY, BotConfig.API_SECRET)
        self.positions = {}  # 활성 포지션 추적
        self.trades_history = []  # 거래 기록
        self.account_balance = BotConfig.INITIAL_BALANCE
        
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
        
        return indicators
    
    def analyze_signal(self, symbol: str, indicators: Dict) -> Tuple[str, float]:
        """
        진입 신호 분석
        Returns: (signal, confidence)
            signal: 'SHORT', 'HOLD', 'CLOSE'
            confidence: 0.0~1.0
        """
        if not indicators:
            return 'HOLD', 0.0
        
        signal_score = 0
        max_score = 6
        
        # RSI 약세 신호 (하락장)
        if indicators['rsi'] > BotConfig.RSI_OVERBOUGHT:
            signal_score += 2  # 강한 신호
        elif indicators['rsi'] > 65:
            signal_score += 1  # 중간 신호
        
        # MACD 약세 신호
        if indicators['macd'] < indicators['macd_signal']:
            signal_score += 1
            if indicators['macd_histogram'] < 0 and indicators['macd_histogram'] < indicators.get('prev_macd_hist', 0):
                signal_score += 1
        
        # 가격이 상단 볼린저밴드에 가까운 경우
        if indicators['current_price'] > indicators['bb_mid']:
            if indicators['current_price'] > indicators['sma_20']:
                signal_score += 1
        
        confidence = signal_score / max_score
        
        # 진입 신호 결정
        if confidence >= 0.50:  # 50% 이상 확률
            return 'SHORT', min(confidence, 1.0)
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
                'status': 'OPEN'
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
    
    def close_short_position(self, symbol: str, reason: str = "MANUAL") -> Optional[Dict]:
        """
        숏 포지션 종료
        """
        try:
            position = self.get_position(symbol)
            if not position:
                logger.warning(f"{symbol}에 종료할 포지션 없음")
                return None
            
            current_price = position['mark_price']
            quantity = abs(position['position_amount'])
            
            # 숏 포지션 종료 (BUY)
            order = self.client.futures_create_order(
                symbol=symbol,
                side='BUY',
                positionSide='SHORT',
                type='MARKET',
                quantity=quantity
            )
            
            exit_price = current_price
            pnl = position['unrealized_pnl']
            pnl_percent = position['unrealized_pnl_percent']
            
            logger.info(f"숏 종료: {symbol} @ {exit_price} | PnL: {pnl:.2f} USDT ({pnl_percent:.2f}%)")
            
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
            logger.error(f"{symbol} 숏 종료 실패: {e}")
            return None
    
    def monitor_position(self, symbol: str) -> Optional[Dict]:
        """
        포지션 모니터링 및 위험 평가
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
        logger.info("🤖 Binance Short Trading Bot 시작")
        logger.info("=" * 60)
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
                                result = self.close_short_position(symbol, "AUTO_CLOSE_RISK")
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
                    
                    logger.info(f"  RSI: {indicators.get('rsi', 0):.2f} | "
                              f"MACD: {indicators.get('macd', 0):.4f} | "
                              f"현재가: {indicators.get('current_price', 0):.2f}")
                    logger.info(f"  신호: {signal} (확률: {confidence*100:.1f}%)")
                    
                    # 신호에 따른 거래
                    if signal == 'SHORT' and confidence >= 0.50:
                        logger.info(f"  ✅ 숏 진입 신호 감지!")
                        
                        # 테스트 모드가 아닌 경우만 실제 거래
                        if not test_mode:
                            result = self.open_short_position(symbol, BotConfig.LEVERAGE)
                            if result:
                                logger.info(f"  위험 금액: {result['risk_amount']:.2f} USDT")
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
        bot = BinanceShortBot()
        
        # 테스트 모드로 실행 (실제 거래 안 함)
        bot.run(test_mode=False)
    
    except KeyboardInterrupt:
        logger.info("프로그램 종료")
    except Exception as e:
        logger.error(f"프로그램 오류: {e}", exc_info=True)
