# 📱 Telegram 알림 설정 가이드

Binance Bot 거래 알림을 Telegram으로 받기

---

## ⚡ 빠른 시작 (5분)

### **1단계: Telegram Bot 생성 (2분)**

1. Telegram 앱 또는 웹 열기
2. [@BotFather](https://t.me/botfather) 검색 후 시작
3. `/newbot` 입력
4. 봇 이름 입력 (예: `BinanceBTCBot`)
5. 봇 사용자명 입력 (예: `binance_short_bot`)
6. **Bot Token 복사** 📋

   ```
   🎉 Done! Congratulations on your new bot.
   You will find it at t.me/binance_short_bot.
   You can now add a description, about section and profile picture for your bot,
   see /help for a list of commands. By the way, when you've finished creating
   your cool bot, ping our bot (@BotFather) with /newbot and we'll be happy
   to feature your bot here 😉

   Use this token to access the HTTP API:
   123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
   ```

   위의 Token을 복사하세요!

### **2단계: Chat ID 확인 (2분)**

1. 생성한 봇과 대화 시작 (예: @binance_short_bot)
2. `/start` 입력
3. 아래 명령어 실행 (터미널에서):

   ```bash
   # YOUR_TOKEN을 위에서 복사한 Token으로 교체
   curl "https://api.telegram.org/botYOUR_TOKEN/getUpdates"
   ```

   또는 브라우저에서:

   ```
   https://api.telegram.org/bot123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11/getUpdates
   ```

4. 응답에서 Chat ID 찾기:

   ```json
   {
     "ok": true,
     "result": [
       {
         "update_id": 123456789,
         "message": {
           "message_id": 1,
           "from": {
             "id": 987654321,  // ← 이것이 Chat ID
             "is_bot": false,
             "first_name": "Your Name"
           }
         }
       }
     ]
   }
   ```

### **3단계: 설정 적용 (1분)**

#### **방법 A: 자동 설정 (권장)**

```bash
cd ~/binance_future
python3 setup_telegram.py
```

대화형으로 Token과 Chat ID를 입력하면 자동으로 설정됩니다.

#### **방법 B: 수동 설정**

```bash
nano .env
```

아래와 같이 수정:

```env
BINANCE_API_KEY=your_binance_key
BINANCE_API_SECRET=your_binance_secret
TELEGRAM_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TELEGRAM_CHAT_ID=987654321
```

저장: `Ctrl+O` → `Enter` → `Ctrl+X`

---

## ✅ 테스트

### **로컬에서 테스트**

```bash
cd ~/binance_future
python3 << 'EOF'
from telegram_notifier import TelegramNotifier
import os
from dotenv import load_dotenv

load_dotenv()
notifier = TelegramNotifier(
    os.getenv('TELEGRAM_TOKEN'),
    os.getenv('TELEGRAM_CHAT_ID')
)

# 테스트 메시지 전송
if notifier.send_message("✅ Telegram 알림이 정상 작동합니다!"):
    print("✅ 성공! Telegram에 메시지가 도착했나요?")
else:
    print("❌ 실패! Token과 Chat ID를 확인하세요.")
EOF
```

---

## 📨 수신할 알림 종류

봇이 자동으로 보내는 알림:

### **1. 봇 시작**

```
🚀 봇 시작됨

버전: 1.0
초기 자본: $100 USDT
레버리지: 2x
손절매: 2.0%
익절: 5.0%

⏰ 2026-02-28 01:42:54
```

### **2. SHORT 신호**

```
🔴 SHORT 신호 발생

종목: BTCUSDT
진입가: $65,718.70
RSI: 31.80
신뢰도: 75.0%

⏰ 2026-02-28 14:30:00
```

### **3. 포지션 오픈**

```
📊 포지션 오픈

종목: BTCUSDT
진입가: $65,718.70
손절매: $67,033.07
익절: $62,432.27

⏰ 2026-02-28 14:30:15
```

### **4. 포지션 종료 (수익)**

```
✅ 포지션 종료

종목: BTCUSDT
진입가: $65,718.70
청산가: $62,432.27
손익: $3.29 (+5.03%)

⏰ 2026-02-28 15:45:30
```

### **5. 포지션 종료 (손실)**

```
❌ 포지션 종료

종목: BTCUSDT
진입가: $65,718.70
청산가: $64,403.72
손익: -$1.33 (-2.00%)

⏰ 2026-02-28 14:45:00
```

### **6. 청산 위험 경고**

```
⚠️ 청산 위험 경고

종목: BTCUSDT
마진율: 75.00%
현재 마진율이 100% 아래입니다!

🚨 모든 포지션을 즉시 확인하세요!

⏰ 2026-02-28 16:20:00
```

### **7. 일일 요약**

```
📈 일일 거래 요약

총 거래: 5회
승률: 80.0%
일일 손익: $2.50
계정 잔액: $102.50

⏰ 2026-02-28 23:59:59
```

### **8. 에러 알림**

```
🔴 봇 에러

API 연결 오류: Connection timeout

⏰ 2026-02-28 17:15:00
```

---

## 🔧 문제 해결

### **Q: "Invalid token" 오류**

```
❌ Telegram 메시지 전송 실패: Invalid token
```

**해결:**
- BotFather에서 다시 Token 확인
- Token에 공백이 없는지 확인
- 올바른 형식: `123456:ABC-DEF...`

### **Q: "Chat not found" 오류**

```
❌ Telegram 메시지 전송 실패: Chat not found
```

**해결:**
1. 봇과 대화 시작했는지 확인
2. `/start` 입력했는지 확인
3. Chat ID 다시 확인:
   ```bash
   curl "https://api.telegram.org/botYOUR_TOKEN/getUpdates"
   ```
4. `"from":{"id":YOUR_CHAT_ID}` 확인

### **Q: 알림이 안 옴**

**확인 사항:**
1. `.env` 파일에 Token과 Chat ID 설정되었는지
2. 봇이 실행 중인지: `ps aux | grep binance`
3. 로그에서 오류 확인: `tail -f bot_trading.log`
4. Telegram 설정 테스트: `python3 setup_telegram.py`

---

## 🎯 고급 설정

### **알림 그룹에 보내기**

봇을 그룹에 추가하고 Chat ID 얻기:

1. Telegram 그룹 생성
2. 봇 추가 (관리자 권한)
3. 그룹에서 `/start` 입력
4. Chat ID 확인 (음수: `-123456789`)
5. `.env`에 설정:

   ```env
   TELEGRAM_CHAT_ID=-123456789
   ```

### **여러 채널에 보내기**

코드 수정 필요 (개발자 문의)

---

## 📱 Telegram 팁

- **알림 음소거**: 대화 → 음소거 설정
- **중요 알림만**: PIN한 메시지로 중요도 표시
- **보안**: Token은 절대 공개 금지

---

## ✅ 체크리스트

```
☐ BotFather에서 봇 생성
☐ Bot Token 복사
☐ 봇과 대화 시작 (/start)
☐ Chat ID 확인
☐ .env 파일에 Token과 Chat ID 입력
☐ 테스트 메시지 확인
☐ 봇 실행 (python3 binance_btc_bot.py)
☐ 첫 거래 알림 대기 중!
```

---

**축하합니다! 이제 Telegram으로 거래 알림을 받을 수 있습니다!** 📱✨
