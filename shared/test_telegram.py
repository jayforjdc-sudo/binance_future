#!/usr/bin/env python3
"""Telegram 연결 테스트"""

from telegram_notifier import TelegramNotifier
import os

# .env 파일에서 직접 읽기
token = None
chat_id = None

with open('.env', 'r') as f:
    for line in f:
        if line.startswith('TELEGRAM_TOKEN='):
            token = line.split('=')[1].strip()
        elif line.startswith('TELEGRAM_CHAT_ID='):
            chat_id = line.split('=')[1].strip()

print("\n" + "="*60)
print("🔗 Telegram 연결 테스트")
print("="*60)
print(f"\n📱 Token: {token[:20]}...{token[-10:]}")
print(f"💬 Chat ID: {chat_id}")

notifier = TelegramNotifier(token, chat_id)

print("\n📤 테스트 메시지 전송 중...")

message = """
✅ Telegram 봇 연결 성공!

🚀 Binance Short Bot이 준비되었습니다.

📊 설정:
• 초기 자본: $53.96 USDT
• 레버리지: 2배
• 손절매: -2.0%
• 익절: +5.0%
• 거래 대상: BTCUSDT

이제 거래 알림을 이곳에서 받을 수 있습니다!
"""

if notifier.send_message(message):
    print("✅ 성공! Telegram 메시지가 도착했나요?")
    print("\n" + "="*60)
    print("🎉 Telegram 설정 완료!")
    print("="*60)
else:
    print("❌ 실패! Token 또는 Chat ID를 확인하세요.")
