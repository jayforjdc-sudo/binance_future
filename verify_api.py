#!/usr/bin/env python3
"""API 키 검증 스크립트"""

from dotenv import load_dotenv
import os
from binance.client import Client

# .env 파일 로드
load_dotenv()

api_key = os.getenv('BINANCE_API_KEY')
api_secret = os.getenv('BINANCE_API_SECRET')

print("🔍 API 키 검증 중...")
print(f"API Key: {api_key[:10]}...{api_key[-10:]}")

try:
    client = Client(api_key, api_secret)

    # 1. 시스템 상태
    print("\n✅ 1. 시스템 상태 확인...")
    status = client.get_system_status()
    print(f"   시스템 상태: {status['status']}")

    # 2. 계정 정보
    print("\n✅ 2. 계정 정보 조회...")
    account = client.futures_account()
    balance = float(account['totalWalletBalance'])
    margin_level = float(account['marginLevel'])
    print(f"   지갑 잔액: {balance:.2f} USDT")
    print(f"   마진율: {margin_level:.2f}%")

    # 3. 현재가
    print("\n✅ 3. BTCUSDT 현재가...")
    ticker = client.futures_mark_price(symbol='BTCUSDT')
    price = float(ticker['markPrice'])
    print(f"   현재가: {price:.2f} USDT")

    print("\n" + "="*50)
    print("🎉 모든 검증 완료! API 정상 작동합니다!")
    print("="*50)

except Exception as e:
    print(f"\n❌ 오류 발생: {str(e)}")
    print("\n💡 해결 방법:")
    print("1. API 키가 올바른지 확인")
    print("2. Binance에서 Futures 거래 활성화 확인")
    print("3. 몇 분 기다렸다가 다시 시도")
    print("4. IP 화이트리스트 재확인")
