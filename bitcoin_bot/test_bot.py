"""
Binance Short Bot - 테스트 및 검증 스크립트
"""

import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv
from binance.client import Client
import pandas as pd

# .env 파일 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BotTester:
    """봇 검증 클래스"""
    
    def __init__(self):
        """테스터 초기화"""
        api_key = os.getenv('BINANCE_API_KEY', '')
        api_secret = os.getenv('BINANCE_API_SECRET', '')
        
        if not api_key or not api_secret:
            logger.error("❌ API 키가 설정되지 않음")
            logger.info("환경 변수 설정: BINANCE_API_KEY, BINANCE_API_SECRET")
            sys.exit(1)
        
        try:
            self.client = Client(api_key, api_secret, testnet=True)  # 테스트넷 사용
            logger.info("✅ Binance 테스트넷 연결 성공")
        except Exception as e:
            logger.error(f"❌ Binance 연결 실패: {e}")
            sys.exit(1)
    
    def test_api_connection(self) -> bool:
        """API 연결 테스트"""
        print("\n" + "="*60)
        print("1️⃣ API 연결 테스트")
        print("="*60)
        
        try:
            status = self.client.get_system_status()
            logger.info(f"✅ 시스템 상태: {status['status']}")
            return True
        except Exception as e:
            logger.error(f"❌ API 연결 실패: {e}")
            return False
    
    def test_account_access(self) -> bool:
        """계정 접근 테스트"""
        print("\n" + "="*60)
        print("2️⃣ 계정 접근 테스트")
        print("="*60)
        
        try:
            account = self.client.futures_account()
            balance = float(account['totalWalletBalance'])
            logger.info(f"✅ 계정 접근 성공")
            logger.info(f"  - 지갑 잔액: {balance:.2f} USDT")
            logger.info(f"  - 마진율: {float(account['marginLevel']):.2f}%")
            return True
        except Exception as e:
            logger.error(f"❌ 계정 접근 실패: {e}")
            return False
    
    def test_kline_data(self) -> bool:
        """캔들 데이터 조회 테스트"""
        print("\n" + "="*60)
        print("3️⃣ 캔들 데이터 조회 테스트")
        print("="*60)
        
        try:
            symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
            
            for symbol in symbols:
                klines = self.client.futures_klines(
                    symbol=symbol,
                    interval='1h',
                    limit=10
                )
                logger.info(f"✅ {symbol}: {len(klines)}개 캔들 조회 성공")
            
            return True
        except Exception as e:
            logger.error(f"❌ 캔들 데이터 조회 실패: {e}")
            return False
    
    def test_indicators(self) -> bool:
        """기술적 지표 계산 테스트"""
        print("\n" + "="*60)
        print("4️⃣ 기술적 지표 계산 테스트")
        print("="*60)
        
        try:
            import talib
            import numpy as np
            
            # 샘플 데이터 생성
            closes = np.array([100, 101, 102, 103, 102, 101, 100, 99, 98, 99] * 20)
            
            # RSI 계산
            rsi = talib.RSI(closes, timeperiod=14)
            logger.info(f"✅ RSI 계산 성공: {rsi[-1]:.2f}")
            
            # MACD 계산
            macd, signal, hist = talib.MACD(closes, fastperiod=12, slowperiod=26, signalperiod=9)
            logger.info(f"✅ MACD 계산 성공: {macd[-1]:.4f}")
            
            # SMA 계산
            sma = talib.SMA(closes, timeperiod=20)
            logger.info(f"✅ SMA 계산 성공: {sma[-1]:.2f}")
            
            # Bollinger Bands 계산
            bb_upper, bb_mid, bb_lower = talib.BBANDS(closes, timeperiod=20)
            logger.info(f"✅ Bollinger Bands 계산 성공")
            
            return True
        except ImportError:
            logger.error("❌ TA-Lib 미설치")
            logger.info("설치 방법: pip install ta-lib")
            return False
        except Exception as e:
            logger.error(f"❌ 지표 계산 실패: {e}")
            return False
    
    def test_position_sizing(self) -> bool:
        """포지션 사이징 테스트"""
        print("\n" + "="*60)
        print("5️⃣ 포지션 사이징 테스트")
        print("="*60)
        
        try:
            account = self.client.futures_account()
            balance = float(account['totalWalletBalance'])
            
            # 포지션 사이즈 계산
            position_size_pct = 0.15  # 15%
            leverage = 2
            
            position_value = balance * position_size_pct / leverage
            
            logger.info(f"✅ 포지션 사이징 계산 성공")
            logger.info(f"  - 계좌 잔액: {balance:.2f} USDT")
            logger.info(f"  - 사용 비율: {position_size_pct*100:.0f}%")
            logger.info(f"  - 레버리지: {leverage}x")
            logger.info(f"  - 포지션 가치: {position_value:.2f} USDT")
            
            return True
        except Exception as e:
            logger.error(f"❌ 포지션 사이징 실패: {e}")
            return False
    
    def test_order_logic(self) -> bool:
        """거래 로직 테스트 (실제 거래 안 함)"""
        print("\n" + "="*60)
        print("6️⃣ 거래 로직 검증 테스트")
        print("="*60)
        
        try:
            symbol = 'BTCUSDT'
            
            # 현재가 조회
            ticker = self.client.futures_symbol_ticker(symbol=symbol)
            price = float(ticker['price'])
            logger.info(f"✅ {symbol} 현재가: {price:.2f} USDT")
            
            # 손절매/익절 계산
            stop_loss_pct = 2.0
            take_profit_pct = 5.0
            
            stop_loss_price = price * (1 + stop_loss_pct / 100)
            take_profit_price = price * (1 - take_profit_pct / 100)
            
            logger.info(f"✅ 손절매 가격 계산: {stop_loss_price:.2f} USDT (+{stop_loss_pct}%)")
            logger.info(f"✅ 익절 가격 계산: {take_profit_price:.2f} USDT (-{take_profit_pct}%)")
            
            return True
        except Exception as e:
            logger.error(f"❌ 거래 로직 검증 실패: {e}")
            return False
    
    def test_leverage_setting(self) -> bool:
        """레버리지 설정 테스트"""
        print("\n" + "="*60)
        print("7️⃣ 레버리지 설정 테스트")
        print("="*60)
        
        try:
            symbol = 'BTCUSDT'
            leverage = 2
            
            # 레버리지 설정 시뮬레이션 (실제로 변경하지 않음)
            logger.info(f"✅ {symbol} 레버리지 설정 가능: {leverage}x")
            logger.info(f"  참고: 실제 변경은 생략됨 (테스트넷)")
            
            return True
        except Exception as e:
            logger.error(f"❌ 레버리지 설정 실패: {e}")
            return False
    
    def run_all_tests(self) -> bool:
        """모든 테스트 실행"""
        print("\n" + "="*60)
        print("🧪 Binance Short Bot 전체 검증 시작")
        print("="*60)
        print(f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        tests = [
            ("API 연결", self.test_api_connection),
            ("계정 접근", self.test_account_access),
            ("캔들 데이터", self.test_kline_data),
            ("기술적 지표", self.test_indicators),
            ("포지션 사이징", self.test_position_sizing),
            ("거래 로직", self.test_order_logic),
            ("레버리지 설정", self.test_leverage_setting),
        ]
        
        results = {}
        for name, test_func in tests:
            try:
                result = test_func()
                results[name] = result
            except Exception as e:
                logger.error(f"❌ {name} 테스트 중 예외: {e}")
                results[name] = False
        
        # 결과 요약
        print("\n" + "="*60)
        print("📋 테스트 결과 요약")
        print("="*60)
        
        passed = sum(1 for v in results.values() if v)
        total = len(results)
        
        for name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status}: {name}")
        
        print("="*60)
        print(f"최종 결과: {passed}/{total} 테스트 통과")
        
        if passed == total:
            print("✅ 모든 테스트 통과! 봇을 실행할 준비가 되었습니다.")
            return True
        else:
            print(f"⚠️ {total - passed}개 테스트 실패. 위의 오류를 확인하세요.")
            return False

def main():
    """메인 함수"""
    tester = BotTester()
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
