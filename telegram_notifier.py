"""
Telegram 알림 모듈
거래 신호와 이벤트를 Telegram으로 전송
"""

import requests
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Telegram 알림 클래스"""

    def __init__(self, token: str, chat_id: str):
        """
        초기화

        Args:
            token: Telegram Bot Token
            chat_id: Telegram Chat ID
        """
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.enabled = bool(token and chat_id)

    def send_message(self, message: str) -> bool:
        """메시지 전송"""
        if not self.enabled:
            return False

        try:
            url = f"{self.base_url}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }
            response = requests.post(url, data=data, timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"❌ Telegram 메시지 전송 실패: {e}")
            return False

    def notify_short_signal(self, symbol: str, price: float, rsi: float, confidence: float):
        """숏 신호 알림"""
        message = f"""
🔴 *SHORT 신호 발생*

종목: `{symbol}`
진입가: `${price:.2f}`
RSI: `{rsi:.2f}`
신뢰도: `{confidence:.1%}`

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        self.send_message(message)

    def notify_position_opened(self, symbol: str, entry_price: float, stop_loss: float, take_profit: float):
        """포지션 오픈 알림"""
        message = f"""
📊 *포지션 오픈*

종목: `{symbol}`
진입가: `${entry_price:.2f}`
손절매: `${stop_loss:.2f}`
익절: `${take_profit:.2f}`

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        self.send_message(message)

    def notify_position_closed(self, symbol: str, entry_price: float, exit_price: float, pnl: float, pnl_percent: float):
        """포지션 종료 알림"""
        emoji = "✅" if pnl >= 0 else "❌"
        message = f"""
{emoji} *포지션 종료*

종목: `{symbol}`
진입가: `${entry_price:.2f}`
청산가: `${exit_price:.2f}`
손익: `${pnl:.2f} ({pnl_percent:.2f}%)`

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        self.send_message(message)

    def notify_liquidation_risk(self, symbol: str, margin_level: float):
        """청산 위험 알림"""
        message = f"""
⚠️ *청산 위험 경고*

종목: `{symbol}`
마진율: `{margin_level:.2f}%`
현재 마진율이 100% 아래입니다!

🚨 모든 포지션을 즉시 확인하세요!

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        self.send_message(message)

    def notify_daily_summary(self, total_trades: int, win_rate: float, daily_pnl: float, total_balance: float):
        """일일 요약 알림"""
        message = f"""
📈 *일일 거래 요약*

총 거래: `{total_trades}`회
승률: `{win_rate:.1f}%`
일일 손익: `${daily_pnl:.2f}`
계정 잔액: `${total_balance:.2f}`

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        self.send_message(message)

    def notify_error(self, error_msg: str):
        """에러 알림"""
        message = f"""
🔴 *봇 에러*

```
{error_msg[:500]}
```

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        self.send_message(message)

    def notify_startup(self, version: str = "1.0"):
        """봇 시작 알림"""
        message = f"""
🚀 *봇 시작됨*

버전: `{version}`
초기 자본: `$100 USDT`
레버리지: `2x`
손절매: `2.0%`
익절: `5.0%`

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        self.send_message(message)
