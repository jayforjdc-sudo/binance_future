"""
호환성 유지용 래퍼 모듈
실제 구현은 binance_btc_bot.py에 있습니다.
"""

# 새 이름으로 import
from binance_btc_bot import BinanceBTCBot

# 호환성 유지: 예전 이름으로도 접근 가능
BinanceShortBot = BinanceBTCBot

if __name__ == "__main__":
    try:
        from binance_btc_bot import BotConfig, logger

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
