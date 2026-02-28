# ⚡ 5분 내 시작하기

## 1️⃣ 설치 (2분)

```bash
# 프로젝트 폴더로 이동
cd binance-short-bot

# 패키지 설치
pip install -r requirements.txt
```

**문제 발생 시**:
- `pip install python-binance pandas numpy python-dotenv matplotlib requests`

## 2️⃣ API 키 설정 (1분)

`.env` 파일 생성 (프로젝트 폴더에):
```
BINANCE_API_KEY=your_key_here
BINANCE_API_SECRET=your_secret_here
```

**⚠️ 필수**:
- Binance에서 API 생성
- 출금 권한 **비활성화**
- IP 화이트리스트 설정

## 3️⃣ 검증 (1분)

```bash
python3 test_bot.py
```

모두 `✅ PASS`가 나면 OK!

## 4️⃣ 실행 (1분)

**테스트 모드** (권장):
```bash
python3 binance_btc_bot.py
```

로그 확인:
```bash
tail -f bot_trading.log
```

---

## 🎯 기본 설정

`binance_btc_bot.py`의 `BotConfig` 수정:

```python
class BotConfig:
    INITIAL_BALANCE = 100  # USDT (100달러)
    LEVERAGE = 2  # 2배 레버리지
    SYMBOLS = ['BTCUSDT', 'ETHUSDT']  # 거래 코인
    STOP_LOSS_PERCENT = 2.0  # 손절매 2%
    TAKE_PROFIT_PERCENT = 5.0  # 익절 5%
```

---

## 📊 백테스팅 (선택사항)

```python
from backtest_engine import run_backtest

# 90일 백테스팅
run_backtest('BTCUSDT', days=90)
```

---

## 📈 모니터링

```bash
# 실시간 로그
tail -f bot_trading.log

# 에러만 확인
grep ERROR bot_trading.log

# 거래 기록
grep "SHORT\|CLOSE" bot_trading.log
```

---

## ⚠️ 중요 체크

시작하기 전에 확인:

- [ ] API 키 설정 완료
- [ ] 출금 권한 비활성화
- [ ] IP 화이트리스트 설정
- [ ] 테스트 통과
- [ ] 로그 파일 생성 확인
- [ ] 100달러 이하로 시작
- [ ] 2주 모니터링 준비

---

## 🚀 다음 단계

### 1주일: 모니터링
- 매일 로그 확인
- 거래 기록 분석
- 마진율 확인

### 2주: 검증
- 백테스팅 결과 비교
- 신호 정확도 확인
- 손익 분석

### 1개월+: 확장
- 수익 확인 후 자본 증액
- 추가 코인 거래
- 설정 최적화

---

## 🆘 문제 해결

### "API 키 오류"
```bash
# 키 다시 설정
echo "BINANCE_API_KEY=your_key" > .env
echo "BINANCE_API_SECRET=your_secret" >> .env
```

### "TA-Lib 오류"
```bash
# macOS
brew install ta-lib && pip install ta-lib

# Ubuntu
sudo apt-get install ta-lib libta-lib0-dev && pip install ta-lib

# Windows
pip install ta-lib --binary-only
```

### "거래가 많이 발생하지 않음"
- RSI 임계값 조정: `RSI_OVERBOUGHT = 65`
- 시간프레임 단축: `TIMEFRAME = '4h'`

---

## 📋 파일 설명

| 파일 | 용도 |
|------|------|
| `binance_btc_bot.py` | 메인 봇 (SHORT/LONG 선택형) |
| `backtest_engine.py` | 백테스팅 |
| `test_bot.py` | 검증 도구 |
| `INSTALLATION_GUIDE.md` | 자세한 설치 |
| `RISK_MANAGEMENT.md` | 위험 관리 |
| `README.md` | 완전 설명서 |

---

## 💡 팁

```python
# 현재 상태 확인
account = bot.get_account_info()
print(f"잔액: {account['balance']:.2f} USDT")
print(f"마진율: {account['margin_level']:.2f}%")

# 거래 통계
stats = bot.get_trading_stats()
print(f"총 거래: {stats['total_trades']}")
print(f"승률: {stats['win_rate']:.1f}%")
print(f"누적 PnL: {stats['total_pnl']:.2f} USDT")
```

---

## 🎓 다음 읽을 것

1. `INSTALLATION_GUIDE.md` - 상세 설치 가이드
2. `RISK_MANAGEMENT.md` - 위험 관리 필수!
3. `README.md` - 전체 기능 설명

---

**준비되셨나요? 시작해보세요! 🚀**

**Remember**: 작은 손실은 큰 손실을 막는 투자입니다!
