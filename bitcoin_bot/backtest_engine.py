"""
Binance Futures Short Bot - Backtesting Module
과거 데이터로 전략 검증
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from binance.client import Client
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple
from sys import path as sys_path
from pathlib import Path
sys_path.insert(0, str(Path(__file__).parent.parent))
from shared.indicators import RSI, MACD, SMA, EMA, BBANDS, ATR

logger = logging.getLogger('BinanceBacktest')

class BacktestEngine:
    """백테스팅 엔진"""
    
    def __init__(self, symbol: str, initial_capital: float = 100, leverage: int = 2):
        self.symbol = symbol
        self.initial_capital = initial_capital
        self.leverage = leverage
        self.trades = []
        self.balance_history = []
        self.current_balance = initial_capital
        self.position = None
    
    def load_historical_data(self, client: Client, interval: str = '1h', days: int = 90) -> pd.DataFrame:
        """
        과거 데이터 로드
        """
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        
        logger.info(f"{self.symbol} {days}일 {interval} 데이터 로드 중...")
        
        klines = client.futures_klines(
            symbol=self.symbol,
            interval=interval,
            startTime=int(start_time.timestamp() * 1000),
            endTime=int(end_time.timestamp() * 1000),
            limit=1000
        )
        
        df = pd.DataFrame(klines, columns=[
            'time', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ])
        
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col])
        
        df['time'] = pd.to_datetime(df['time'], unit='ms')
        df = df.sort_values('time').reset_index(drop=True)
        
        logger.info(f"로드 완료: {len(df)}개 캔들 ({df['time'].min()} ~ {df['time'].max()})")
        return df
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """지표 계산"""
        close = df['close'].values
        high = df['high'].values
        low = df['low'].values

        df['rsi'] = RSI(close, period=14)

        macd, signal, hist = MACD(close, fast=12, slow=26, signal=9)
        df['macd'] = macd
        df['macd_signal'] = signal
        df['macd_hist'] = hist

        df['sma_20'] = SMA(close, 20)
        df['sma_50'] = SMA(close, 50)

        bb_upper, bb_mid, bb_lower = BBANDS(close, period=20)
        df['bb_upper'] = bb_upper
        df['bb_mid'] = bb_mid
        df['bb_lower'] = bb_lower

        df['atr'] = ATR(high, low, close, period=14)

        return df
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """거래 신호 생성"""
        df['signal'] = 'HOLD'
        
        for i in range(1, len(df)):
            rsi = df.loc[i, 'rsi']
            macd = df.loc[i, 'macd']
            macd_signal = df.loc[i, 'macd_signal']
            price = df.loc[i, 'close']
            sma_20 = df.loc[i, 'sma_20']
            
            # 숏 신호: RSI > 70 AND MACD < Signal AND price > SMA20
            if rsi > 70 and macd < macd_signal and price > sma_20:
                df.loc[i, 'signal'] = 'SHORT'
            
            # 종료 신호: RSI < 50 OR MACD > Signal
            elif rsi < 50 or macd > macd_signal:
                df.loc[i, 'signal'] = 'CLOSE'
        
        return df
    
    def backtest(self, df: pd.DataFrame, stop_loss_pct: float = 2.0, 
                 take_profit_pct: float = 5.0, position_size_pct: float = 0.15) -> Dict:
        """
        백테스팅 실행
        """
        logger.info(f"백테스팅 시작 (레버리지: {self.leverage}x, 손절매: {stop_loss_pct}%, 익절: {take_profit_pct}%)")
        
        self.trades = []
        self.balance_history = [self.initial_capital]
        self.current_balance = self.initial_capital
        self.position = None
        
        for i in range(len(df)):
            row = df.iloc[i]
            current_price = row['close']
            signal = row['signal']
            
            # 기존 포지션 확인
            if self.position:
                entry_price = self.position['entry_price']
                loss_pct = (current_price - entry_price) / entry_price * 100
                
                # 손절매 체크
                if loss_pct > stop_loss_pct:
                    self._close_position(row, 'STOP_LOSS')
                
                # 익절 체크
                elif loss_pct < -take_profit_pct:
                    self._close_position(row, 'TAKE_PROFIT')
                
                # 신호 체크
                elif signal == 'CLOSE' or signal == 'SHORT':
                    self._close_position(row, 'SIGNAL')
            
            # 새로운 숏 포지션 진입
            if not self.position and signal == 'SHORT':
                position_value = self.current_balance * position_size_pct / self.leverage
                quantity = position_value / current_price
                
                self.position = {
                    'entry_price': current_price,
                    'entry_time': row['time'],
                    'quantity': quantity,
                    'entry_index': i,
                    'position_value': position_value
                }
                logger.debug(f"[{row['time']}] SHORT @ {current_price:.2f}")
            
            # 잔액 기록
            if self.position:
                unrealized_pnl = (self.position['entry_price'] - current_price) * \
                                self.position['quantity'] * self.leverage
                self.balance_history.append(self.current_balance + unrealized_pnl)
            else:
                self.balance_history.append(self.current_balance)
        
        return self._calculate_statistics()
    
    def _close_position(self, row, reason: str):
        """포지션 종료"""
        if not self.position:
            return
        
        exit_price = row['close']
        entry_price = self.position['entry_price']
        quantity = self.position['quantity']
        
        # 숏 손익 계산
        pnl = (entry_price - exit_price) * quantity * self.leverage
        pnl_pct = (entry_price - exit_price) / entry_price * 100
        
        self.current_balance += pnl
        
        trade = {
            'entry_time': self.position['entry_time'],
            'entry_price': entry_price,
            'exit_time': row['time'],
            'exit_price': exit_price,
            'quantity': quantity,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'reason': reason,
            'duration': (row['time'] - self.position['entry_time']).total_seconds() / 3600
        }
        
        self.trades.append(trade)
        logger.debug(f"[{row['time']}] CLOSE @ {exit_price:.2f} | PnL: {pnl:.2f} ({pnl_pct:.2f}%)")
        
        self.position = None
    
    def _calculate_statistics(self) -> Dict:
        """통계 계산"""
        if not self.trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'total_pnl': 0,
                'total_pnl_pct': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0
            }
        
        trades = self.trades
        
        # 기본 통계
        total_trades = len(trades)
        winning_trades = len([t for t in trades if t['pnl'] > 0])
        losing_trades = len([t for t in trades if t['pnl'] <= 0])
        win_rate = winning_trades / total_trades * 100 if total_trades > 0 else 0
        
        # 손익
        total_pnl = sum(t['pnl'] for t in trades)
        total_pnl_pct = (total_pnl / self.initial_capital) * 100
        
        # 평균 손익
        wins = [t['pnl'] for t in trades if t['pnl'] > 0]
        losses = [t['pnl'] for t in trades if t['pnl'] < 0]
        
        avg_win = np.mean(wins) if wins else 0
        avg_loss = np.mean(losses) if losses else 0
        
        profit_factor = abs(sum(wins) / sum(losses)) if losses else 0
        
        # 최대 낙폭
        balance_array = np.array(self.balance_history)
        peak = np.maximum.accumulate(balance_array)
        drawdown = (balance_array - peak) / peak * 100
        max_drawdown = np.min(drawdown)
        
        # Sharpe Ratio (간단 계산)
        returns = np.diff(balance_array) / balance_array[:-1]
        sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252 * 24) if len(returns) > 1 else 0
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'total_pnl': total_pnl,
            'total_pnl_pct': total_pnl_pct,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'final_balance': self.current_balance
        }
    
    def plot_results(self, save_path: str = None):
        """결과 시각화"""
        fig, axes = plt.subplots(2, 1, figsize=(14, 8))
        
        # 계좌 잔액
        axes[0].plot(self.balance_history, label='Account Balance', linewidth=2)
        axes[0].axhline(y=self.initial_capital, color='r', linestyle='--', label='Initial Capital')
        axes[0].set_ylabel('Balance (USDT)')
        axes[0].set_title(f'{self.symbol} Backtest Results')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)
        
        # 거래 표시
        for trade in self.trades:
            entry_idx = trade['entry_index'] if 'entry_index' in trade else 0
            exit_price = trade['exit_price']
            color = 'green' if trade['pnl'] > 0 else 'red'
            axes[0].scatter(entry_idx, trade['entry_price'], color='blue', marker='^', s=100)
        
        # 드로우다운
        balance_array = np.array(self.balance_history)
        peak = np.maximum.accumulate(balance_array)
        drawdown = (balance_array - peak) / peak * 100
        
        axes[1].fill_between(range(len(drawdown)), drawdown, 0, alpha=0.3, color='red')
        axes[1].plot(drawdown, color='red', linewidth=2, label='Drawdown')
        axes[1].set_ylabel('Drawdown (%)')
        axes[1].set_xlabel('Candle Index')
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=100)
            logger.info(f"차트 저장: {save_path}")
        else:
            plt.show()

def run_backtest(symbol: str, days: int = 90):
    """백테스팅 실행"""
    
    # API 클라이언트
    client = Client('', '')  # API 키 필요
    
    # 백테스팅 엔진
    bt = BacktestEngine(symbol, initial_capital=100, leverage=2)
    
    # 데이터 로드
    df = bt.load_historical_data(client, interval='1h', days=days)
    
    if df.empty:
        logger.error("데이터 로드 실패")
        return
    
    # 지표 계산
    df = bt.calculate_indicators(df)
    
    # 신호 생성
    df = bt.generate_signals(df)
    
    # 백테스팅 실행
    stats = bt.backtest(df, stop_loss_pct=2.0, take_profit_pct=5.0, position_size_pct=0.15)
    
    # 결과 출력
    print("\n" + "=" * 60)
    print(f"📊 {symbol} 백테스팅 결과 ({days}일)")
    print("=" * 60)
    print(f"초기 자본: {bt.initial_capital} USDT")
    print(f"최종 자본: {stats['final_balance']:.2f} USDT")
    print(f"총 손익: {stats['total_pnl']:.2f} USDT ({stats['total_pnl_pct']:.2f}%)")
    print("\n거래 통계:")
    print(f"  총 거래: {stats['total_trades']}")
    print(f"  승리: {stats['winning_trades']} / 패배: {stats['losing_trades']}")
    print(f"  승률: {stats['win_rate']:.1f}%")
    print(f"  평균 승리: {stats['avg_win']:.2f} USDT")
    print(f"  평균 패배: {stats['avg_loss']:.2f} USDT")
    print(f"  프로핏 팩터: {stats['profit_factor']:.2f}")
    print("\n위험 지표:")
    print(f"  최대 낙폭: {stats['max_drawdown']:.2f}%")
    print(f"  샤프 비율: {stats['sharpe_ratio']:.4f}")
    print("=" * 60)
    
    # 차트 저장
    bt.plot_results(save_path=f'{symbol}_backtest.png')
    
    return stats, bt.trades

if __name__ == '__main__':
    # 백테스팅 실행 (API 키 필요)
    # stats, trades = run_backtest('BTCUSDT', days=90)
    pass
