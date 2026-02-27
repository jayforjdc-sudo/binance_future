# 🤖 Binance Futures Short Trading Bot

침체 시장(하락장)에 대응하는 자동화 숏 거래 봇입니다. 기술적 분석을 기반으로 RSI, MACD 등의 지표를 활용하여 하락 신호를 포착하고 자동으로 숏 포지션을 진입합니다.

## ✨ 주요 특징

### 🎯 보수적 위험 관리
- **낮은 레버리지**: 2~3배 기본, 최대 5배 제한
- **포지션 사이징**: 계좌의 15% 이하만 사용
- **자동 청산**: 마진율 50% 이하 시 자동 종료
- **엄격한 손절매**: 진입가 대비 2% 손실 시 즉시 청산

### 📊 기술적 분석
- **RSI**: 과매도/과매수 구간 감지
- **MACD**: 추세 전환 신호 포착
- **Bollinger Bands**: 가격 변동성 분석
- **ATR**: 변동성 기반 위험 평가

### 🔒 안전 기능
- 중복 포지션 방지
- 극도의 변동성 회피
- 실시간 마진율 모니터링
- 거래 기록 자동 저장
- 상세한 로깅

### 📈 성능 추적
- 거래 통계 자동 계산
- 승률, 손익률, 프로핏 팩터 분석
- 최대 낙폭(Drawdown) 추적
- 샤프 비율 계산

---

## 🚀 빠른 시작

### 1. 설치

```bash
# 저장소 클론
git clone <repository-url>
cd binance-short-bot

# 가상 환경 생성
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# 또는
venv\Scripts\activate  # Windows

# 패키지 설치
pip install -r requirements.txt
```

### 2. API 키 설정

`.env` 파일 생성:
```
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here
```

**⚠️ 중요**: 
- API 키는 출금 권한 비활성화
- IP 화이트리스트 설정 필수

### 3. 봇 검증

```bash
python3 test_bot.py
```

모든 테스트가 통과되면 준비 완료!

### 4. 테스트 실행

```bash
# 테스트 모드 (실제 거래 안 함)
python3 -c "from binance_short_bot import BinanceShortBot; bot = BinanceShortBot(); bot.run(test_mode=True)"
```

### 5. 실제 거래 시작

```bash
# 100달러 이하로만 거래하도록 설정 후:
python3 binance_short_bot.py
```

---

## 📋 파일 구조

```
binance-short-bot/
├── binance_short_bot.py      # 메인 봇 엔진
├── backtest_engine.py        # 백테스팅 모듈
├── test_bot.py               # 검증 스크립트
├── requirements.txt          # Python 의존성
├── .env                      # API 키 (보안!)
├── INSTALLATION_GUIDE.md     # 설치 가이드
├── RISK_MANAGEMENT.md        # 위험 관리 가이드
└── bot_trading.log          # 거래 로그 (자동 생성)
```

---

## ⚙️ 설정

### 기본 설정 (`BotConfig` 클래스)

```python
# 자본금
INITIAL_BALANCE = 100  # USDT

# 레버리지
LEVERAGE = 2  # 초기값
MAX_LEVERAGE = 5  # 최대값

# 포지션 크기
POSITION_SIZE_PERCENT = 0.15  # 계좌의 15%

# 손절매/이익실현
STOP_LOSS_PERCENT = 2.0  # -2%
TAKE_PROFIT_PERCENT = 5.0  # +5%

# 거래 심볼
SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT']

# 분석 설정
TIMEFRAME = '1h'  # 1시간 봉
CANDLES = 200  # 분석 캔들 수
```

### 신호 조정

**보수적 (낮은 거래량)**:
```python
RSI_OVERBOUGHT = 75  # RSI 75 이상에서만 진입
```

**공격적 (높은 거래량)**:
```python
RSI_OVERBOUGHT = 60  # RSI 60 이상에서도 진입
```

---

## 📊 백테스팅

과거 데이터로 전략을 검증하세요:

```python
from backtest_engine import run_backtest

# BTC 90일 백테스팅
stats, trades = run_backtest('BTCUSDT', days=90)

# 결과 시각화
# bot.plot_results('backtest_result.png')
```

**결과 해석**:
- **승률**: 50% 이상 목표
- **프로핏 팩터**: 1.5 이상 양호
- **최대 낙폭**: 10% 이내 권장
- **샤프 비율**: 1.0 이상 우수

---

## 📈 거래 흐름

### 1. 신호 생성

```
캔들 데이터 조회
    ↓
기술적 지표 계산 (RSI, MACD, BB, ATR)
    ↓
진입 신호 분석
    ↓
신뢰도 > 50% 시 SHORT 신호
```

### 2. 포지션 진입

```
진입 신호 확인
    ↓
포지션 크기 계산
    ↓
손절매/이익실현 가격 설정
    ↓
SELL (SHORT) 주문 실행
    ↓
주문 성공 시 TP/SL 주문 발동
```

### 3. 포지션 관리

```
실시간 마진율 모니터링
    ↓
- 마진율 < 50%: 자동 청산
- 손절매 타치: 자동 청산
- 이익실현 타치: 자동 청산
    ↓
거래 기록 저장 및 통계 업데이트
```

---

## 🔔 모니터링

### 실시간 로그 확인

```bash
# 실시간 로그
tail -f bot_trading.log

# 특정 심볼만 보기
tail -f bot_trading.log | grep BTCUSDT

# 에러만 보기
tail -f bot_trading.log | grep ERROR
```

### 계좌 정보 조회

```python
account = bot.get_account_info()
print(f"잔액: {account['balance']:.2f} USDT")
print(f"미결제손익: {account['unrealized_pnl']:.2f} USDT")
print(f"마진율: {account['margin_level']:.2f}%")
```

### 활성 포지션 확인

```python
position = bot.get_position('BTCUSDT')
if position:
    print(f"포지션: SHORT {position['position_amount']}")
    print(f"진입가: {position['entry_price']:.2f}")
    print(f"현재가: {position['mark_price']:.2f}")
    print(f"미결제손익: {position['unrealized_pnl']:.2f} USDT")
```

### 거래 통계

```python
stats = bot.get_trading_stats()
print(f"총 거래: {stats['total_trades']}")
print(f"승률: {stats['win_rate']:.1f}%")
print(f"누적 PnL: {stats['total_pnl']:.2f} USDT")
```

---

## 🛡️ 위험 관리

### 청산 위험 최소화

| 설정 | 값 | 이유 |
|------|-----|------|
| 초기 레버리지 | 2x | 청산까지 거리 충분 |
| 포지션 크기 | 15% | 한 번 거래로 계좌 큰 손상 없음 |
| 손절매 | -2% | 작은 손실로 위험 관리 |
| 이익실현 | +5% | 장기 보유의 위험 회피 |

### 마진율 경고 시스템

```
마진율 200% 이상   ✅ 안전
마진율 100~200%    ⚠️ 주의
마진율 50~100%     🔴 위험 (포지션 축소)
마진율 < 50%       💥 청산 (자동 종료)
```

---

## 📝 로그 예시

```
[2024-02-28 10:00:00,123] - BinanceShorBot - INFO - 🤖 Binance Short Trading Bot 시작
[2024-02-28 10:00:00,456] - BinanceShorBot - INFO - 초기 자본: 100 USDT
[2024-02-28 10:00:00,789] - BinanceShorBot - INFO - 레버리지: 2~5x
[2024-02-28 10:00:01,000] - BinanceShorBot - INFO - ============================================================
[2024-02-28 10:00:01,234] - BinanceShorBot - INFO - [Loop 1] 2024-02-28 10:00:01
[2024-02-28 10:00:01,456] - BinanceShorBot - INFO - 계좌 잔액: 99.85 USDT | 미결제손익: 0.15 USDT | 마진율: 500.00%
[2024-02-28 10:00:02,000] - BinanceShorBot - INFO - 📊 BTCUSDT 분석 중...
[2024-02-28 10:00:02,234] - BinanceShorBot - INFO -   RSI: 72.34 | MACD: 0.0245 | 현재가: 45123.45
[2024-02-28 10:00:02,456] - BinanceShorBot - INFO -   신호: SHORT (확률: 65.0%)
[2024-02-28 10:00:02,789] - BinanceShorBot - INFO -   ✅ 숏 진입 신호 감지!
[2024-02-28 10:00:03,123] - BinanceShorBot - INFO -   위험 금액: 0.15 USDT
```

---

## 🎓 학습 리소스

### 추천 교재
- "거래의 위험성" - Perry Kaufman
- "기술적 분석 완전 정복" - John Murphy
- "몰라도 되는 과학" - Nassim Taleb

### 온라인 자료
- [Binance Academy](https://academy.binance.com)
- [TradingView](https://www.tradingview.com)
- [인베스토피디아](https://www.investopedia.com)

### 커뮤니티
- [Reddit r/CryptoCurrency](https://www.reddit.com/r/CryptoCurrency/)
- [BitcoinTalk](https://bitcointalk.org)

---

## 🆘 문제 해결

### "ModuleNotFoundError: No module named 'talib'"

```bash
# macOS
brew install ta-lib
pip install ta-lib

# Ubuntu
sudo apt-get install ta-lib libta-lib0 libta-lib0-dev
pip install ta-lib

# Windows
pip install ta-lib --binary-only
```

### "InvalidAPIKey"

- API 키 확인
- 환경 변수 설정 확인
- Binance에서 API 활성화 확인

### "청산 위험이 높음"

1. 레버리지를 1.5x로 낮춤
2. 포지션 크기를 10%로 줄임
3. 손절매를 3%로 증가

---

## 📊 성능 기준

### 양호한 성과
- 월간 수익률: 5~15%
- 승률: 55~65%
- 프로핏 팩터: 1.5 이상
- 최대 낙폭: 5~10%

### 주의할 신호
- 월간 손실: -10% 이상
- 승률: < 50%
- 최대 낙폭: > 20%
- 연패 > 5회

---

## 🔐 보안 체크리스트

- [ ] API 키 환경 변수로 관리
- [ ] `.env` 파일을 `.gitignore`에 추가
- [ ] Binance에서 IP 화이트리스트 설정
- [ ] API 키에 출금 권한 제거
- [ ] 정기적으로 API 키 교체
- [ ] 거래 기록 정기적으로 백업

---

## 📞 지원

질문이나 문제가 있으면:

1. [GitHub Issues](https://github.com/your-repo/issues) 확인
2. [이 문서](#-트러블슈팅) 참고
3. 커뮤니티 포럼에서 질문

---

## ⚖️ 면책사항

**⚠️ 중요 경고**

- 이 봇은 교육 목적으로 제공됩니다
- 과거 성과는 미래 결과를 보장하지 않습니다
- 레버리지 거래는 높은 위험을 가집니다
- 자신이 감당할 수 있는 금액만 투자하세요
- 정기적으로 모니터링하세요
- 법적 조언은 전문가와 상담하세요

**개발자는 거래로 인한 손실에 대해 책임을 지지 않습니다.**

---

## 📄 라이선스

MIT License - 자유롭게 사용, 수정, 배포 가능

---

## 🙋 기여

버그 보고, 기능 제안, 코드 기여는 환영합니다!

```bash
# 포크 후 PR 제출
git checkout -b feature/your-feature
git commit -am 'Add your feature'
git push origin feature/your-feature
```

---

## 🎯 로드맵

- [ ] 웹 대시보드 추가
- [ ] 텔레그램 알림 기능
- [ ] 다양한 전략 추가
- [ ] 머신러닝 신호 통합
- [ ] 다중 계좌 지원
- [ ] 종이 거래 모드

---

## 💬 피드백

이 프로젝트를 어떻게 개선할 수 있을지 알려주세요!

---

**Happy Trading! 🚀**

*작은 수익이 모여 큰 자산을 만듭니다.*

---

**마지막 업데이트**: 2025년 2월 28일
