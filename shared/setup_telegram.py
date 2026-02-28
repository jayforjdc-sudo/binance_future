#!/usr/bin/env python3
"""
Telegram 설정 및 테스트 스크립트
"""

import os
import sys
from telegram_notifier import TelegramNotifier


def setup_telegram():
    """Telegram 설정 마법사"""
    print("\n" + "="*60)
    print("🤖 Telegram Bot 설정 마법사")
    print("="*60)

    print("\n📱 Telegram Bot 토큰을 입력하세요:")
    print("   (BotFather에서 받은 Token)")
    print("   예: 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")
    token = input("\n토큰: ").strip()

    if not token or ":" not in token:
        print("❌ 유효하지 않은 토큰입니다!")
        return False

    print("\n💬 Chat ID를 입력하세요:")
    print("   (봇과의 대화에서 /start 후 getUpdates로 확인)")
    print("   예: 123456789")
    chat_id = input("\nChat ID: ").strip()

    if not chat_id or not chat_id.isdigit():
        print("❌ 유효하지 않은 Chat ID입니다!")
        return False

    # .env 파일 업데이트
    print("\n💾 .env 파일 업데이트 중...")

    env_path = ".env"
    env_content = []

    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                if line.startswith('TELEGRAM_TOKEN'):
                    env_content.append(f"TELEGRAM_TOKEN={token}\n")
                elif line.startswith('TELEGRAM_CHAT_ID'):
                    env_content.append(f"TELEGRAM_CHAT_ID={chat_id}\n")
                else:
                    env_content.append(line)
    else:
        env_content = []

    with open(env_path, 'w') as f:
        f.writelines(env_content)

    print("✅ .env 파일 업데이트됨")

    # 테스트
    print("\n🧪 Telegram 연결 테스트 중...")
    notifier = TelegramNotifier(token, chat_id)

    if notifier.send_message("✅ Telegram 연결 성공!\n\n봇이 준비되었습니다."):
        print("✅ Telegram 알림 정상 작동!")
        print("\n📋 설정 완료:")
        print(f"   Token: {token[:20]}...{token[-10:]}")
        print(f"   Chat ID: {chat_id}")
        return True
    else:
        print("❌ Telegram 연결 실패!")
        print("   Token과 Chat ID를 다시 확인하세요.")
        return False


if __name__ == "__main__":
    success = setup_telegram()
    sys.exit(0 if success else 1)
