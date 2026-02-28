#!/usr/bin/env python3
"""
SHORT 모드 테스트 (단 1 루프만 실행)
"""
import os
import signal
import sys
from binance_btc_bot import BinanceBTCBot

# 환경 변수 확인
print(f"TRADING_MODE: {os.getenv('TRADING_MODE', 'SHORT')}")

# 봇 초기화
bot = BinanceBTCBot()

# 1루프만 실행하도록 설정 (신호 분석 + 거래 조건 확인)
try:
    # 1루프 시뮬레이션
    bot.run(test_mode=True)
except KeyboardInterrupt:
    print("\n테스트 종료됨")
except Exception as e:
    print(f"테스트 중 오류: {e}")
    import traceback
    traceback.print_exc()
finally:
    print("\n테스트 완료")
