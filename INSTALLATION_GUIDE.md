# Binance Futures Short Trading Bot 
## 설치 및 운영 가이드

---

## 목차
1. [환경 설정](#환경-설정)
2. [API 설정](#api-설정)
3. [설치](#설치)
4. [보안](#보안)
5. [백테스팅](#백테스팅)
6. [봇 실행](#봇-실행)
7. [위험 관리](#위험-관리)
8. [모니터링](#모니터링)

---

## 환경 설정

### Python 버전
```bash
python3 --version  # Python 3.8 이상 필요
```

### 가상 환경 생성
```bash
# 가상 환경 생성
python3 -m venv venv

# 활성화
# macOS / Linux:
source venv/bin/activate

# Windows:
venv\Scripts\activate
```

---

## API 설정

### Binance API 키 생성

1. **Binance 계정 접속**: https://www.binance.com
2. **계정 > API 관리** 이동
3. **새 API 키** 생성
4. **API 키 제한 사항**:
   - ✅ 선물 거래 활성화
   - ✅ 현물 거래 활성화
   - ❌ IP 제한 설정 (보안 강화)
   - ❌ 출금 비활성화 (필수!)

### 환경 변수 설정

**방법 1: .env 파일 (권장)**

`.env` 파일 생성:
```bash
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here
```

**방법 2: 직접 설정**

```bash
# macOS / Linux:
export BINANCE_API_KEY="your_api_key"
export BINANCE_API_SECRET="your_api_secret"

# Windows PowerShell:
$env:BINANCE_API_KEY="your_api_key"
$env:BINANCE_API_SECRET="your_api_secret"
```

**방법 3: 코드에서 설정 (개발용만)**

```python
# binance_short_bot.py 수정
API_KEY = 'your_api_key'
API_SECRET = 'your_api_secret'
```

---

## 설치

### 패키지 설치

```bash
pip install -r requirements.txt
```

**requirements.txt**:
```
python-binance==1.0.17
pandas==2.0.0
numpy==1.24.0
TA-Lib==0.4.28
python-dotenv==1.0.0
matplotlib==3.7.0
```

### TA-Lib 설치

TA-Lib은 C 라이브러리에 의존성이 있습니다.

**macOS**:
```bash
brew install ta-lib
pip install ta-lib
```

**Linux (Ubuntu/Debian)**:
```bash
sudo apt-get install ta-lib libta-lib0 libta-lib0-dev
pip install ta-lib
```

**Windows**:
```bash
# 바이너리 설치 (권장)
pip install ta-lib --no-deps

# 또는 wheel 파일로 설치
# https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib
# 다운로드 후: pip install TA_Lib-*.whl
```

---

## 보안

### ⚠️ 중요: 보안 체크리스트

- [ ] **API 키 보안**: 코드에 직접 작성 금지, 환경 변수 사용
- [ ] **IP 제한**: Binance API 페이지에서 IP 화이트리스트 설정
- [ ] **출금 비활성화**: API 키에 출금 권한 제거
- [ ] **테스트넷 사용**: 초기 테스트는 테스트넷에서 실행
- [ ] **버전 관리**: .env 파일을 .gitignore에 추가
- [ ] **정기 검토**: API 키 사용 기록 정기적 확인

### .gitignore 설정

```
# 환경 변수
.env
.env.local
.env.*.local

# 로그 파일
*.log
*.logs
bot_trading.log

# 캐시
__pycache__/
*.py[cod]
*$py.class

# IDE
.vscode/
.idea/
*.swp

# 데이터
*.csv
*.pkl
*.db
```

---

## 백테스팅

### 백테스팅 실행

```python
from backtest_engine import run_backtest

# BTC 90일 백테스팅
stats, trades = run_backtest('BTCUSDT', days=90)

# ETH 60일 백테스팅
stats, trades = run_backtest('ETHUSDT', days=60)
```

### 백테스팅 결과 분석

**주요 지표**:
- **승률 (Win Rate)**: 50% 이상 목표
- **프로핏 팩터**: 1.5 이상 권장
- **최대 낙폭**: 10% 이내 권장
- **샤프 비율**: 1.0 이상 양호

**예시 결과**:
```
════════════════════════════════════════════════════════════
📊 BTCUSDT 백테스팅 결과 (90일)
════════════════════════════════════════════════════════════
초기 자본: 100 USDT
최종 자본: 115.42 USDT
총 손익: 15.42 USDT (15.42%)

거래 통계:
  총 거래: 23
  승리: 15 / 패배: 8
  승률: 65.2%
  평균 승리: 1.05 USDT
  평균 패배: -0.68 USDT
  프로핏 팩터: 1.82

위험 지표:
  최대 낙폭: -8.3%
  샤프 비율: 1.234
════════════════════════════════════════════════════════════
```

---

## 봇 실행

### 테스트 모드 (실제 거래 안 함)

```bash
# 테스트 모드로 실행
python3 binance_short_bot.py --test

# 또는 코드에서:
bot.run(test_mode=True)
```

### 라이브 모드 (실제 거래)

```bash
# 100달러 이하로만 거래하도록 설정 후:
python3 binance_short_bot.py

# 또는 코드에서:
bot.run(test_mode=False)
```

### 로깅 확인

```bash
# 실시간 로그 확인
tail -f bot_trading.log

# 특정 심볼 로그 필터
tail -f bot_trading.log | grep BTCUSDT

# 에러 로그만 확인
tail -f bot_trading.log | grep ERROR
```

---

## 위험 관리

### 청산 위험 최소화

**현재 설정**:
- 레버리지: 2~3배 (최대 5배)
- 포지션 크기: 계좌의 15%
- 손절매: 진입가 대비 2%
- 이익실현: 진입가 대비 5%

**마진율 안내**:
| 마진율 | 위험도 | 조치 |
|--------|--------|------|
| > 200% | 안전 | 정상 운영 |
| 100~200% | 주의 | 모니터링 강화 |
| 50~100% | 위험 | 포지션 축소 |
| < 50% | 심각 | 자동 청산 |

### 포지션 사이징 공식

```
포지션 가치 = 계좌잔액 × 위험비율 / 레버리지
위험 금액 = 포지션 가치 × 손절매%

예시:
- 계좌: 100 USDT
- 위험비율: 15%
- 레버리지: 2x
- 손절매: 2%

포지션 가치 = 100 × 0.15 / 2 = 7.5 USDT
위험 금액 = 7.5 × 2% = 0.15 USDT (계좌의 0.15% 위험)
```

### 자동 청산 조건

봇은 다음 조건에서 자동으로 포지션을 종료합니다:

1. **마진율 < 50%**: 청산 위험 높음
2. **손절매 타치**: -2% 손실
3. **이익실현 타치**: +5% 수익
4. **반대 신호**: 다른 거래 신호 발생

---

## 모니터링

### 실시간 모니터링

```python
# 현재 활성 포지션 확인
position = bot.get_position('BTCUSDT')

# 계좌 정보
account = bot.get_account_info()
print(f"잔액: {account['balance']} USDT")
print(f"미결제손익: {account['unrealized_pnl']} USDT")
print(f"마진율: {account['margin_level']}%")

# 거래 통계
stats = bot.get_trading_stats()
print(f"승률: {stats['win_rate']:.1f}%")
print(f"누적 PnL: {stats['total_pnl']:.2f} USDT")
```

### 알림 설정

**텔레그램 알림 (선택사항)**:

```python
import requests

def send_telegram_alert(message):
    token = 'YOUR_BOT_TOKEN'
    chat_id = 'YOUR_CHAT_ID'
    url = f'https://api.telegram.org/bot{token}/sendMessage'
    requests.post(url, data={'chat_id': chat_id, 'text': message})

# 거래 시 알림
if result:
    send_telegram_alert(f"📊 {symbol} 숏 진입\n가격: {result['entry_price']}")
```

### 일일 리포트

```python
def generate_daily_report(bot):
    stats = bot.get_trading_stats()
    account = bot.get_account_info()
    
    report = f"""
    === 일일 거래 리포트 ===
    날짜: {datetime.now().strftime('%Y-%m-%d')}
    
    계좌 상태:
    - 잔액: {account['balance']:.2f} USDT
    - 미결제손익: {account['unrealized_pnl']:.2f} USDT
    
    거래 통계:
    - 총 거래: {stats['total_trades']}
    - 승률: {stats['win_rate']:.1f}%
    - 누적 PnL: {stats['total_pnl']:.2f} USDT
    """
    
    return report
```

---

## 트러블슈팅

### 문제: "ModuleNotFoundError: No module named 'talib'"

```bash
# 솔루션: TA-Lib 재설치
pip uninstall ta-lib -y
pip install ta-lib
```

### 문제: "BinanceAPIException: Invalid API-key"

- API 키 확인
- 환경 변수 설정 확인
- Binance에서 API 키 활성화 여부 확인

### 문제: "청산 위험이 자자자 높아짐"

- 레버리지 낮추기 (2x로 시작)
- 포지션 크기 줄이기 (10%로 줄임)
- 손절매 증가 (3~4%로 조정)

### 문제: "거래가 많이 발생하지 않음"

- RSI 오버바우토 임계값 조정 (70 → 65)
- MACD 신호 조정
- 시간프레임 변경 (1h → 4h)

---

## 성능 최적화

### CPU 사용량 감소

```python
# 분석 간격 조정 (1시간 → 4시간)
TIMEFRAME = '4h'  # 더 긴 시간프레임
```

### 메모리 사용량 감소

```python
# 분석 캔들 수 조정 (200 → 100)
CANDLES = 100  # 더 적은 캔들
```

### API 요청 제한

Binance는 분당 요청 수 제한이 있습니다 (약 1200 req/min):

```python
# 요청 간격 추가
time.sleep(1)  # 1초 대기
```

---

## 다음 단계

### 1단계: 검증 (1주일)
- ✅ 테스트 모드에서 실행
- ✅ 백테스팅 결과 분석
- ✅ 신호 정확도 확인

### 2단계: 소규모 거래 (1개월)
- ✅ 100달러로 시작
- ✅ 매일 모니터링
- ✅ 승률 및 손익 기록

### 3단계: 확장 (3개월 후)
- ✅ 수익성 입증
- ✅ 자본금 천천히 증액
- ✅ 추가 코인 추가

---

## 면책사항

**중요**: 이 봇은 자동화 거래를 위한 도구입니다.

- ⚠️ 레버리지 거래는 손실 위험이 높습니다
- ⚠️ 과거 성과는 미래 결과를 보장하지 않습니다
- ⚠️ 자신이 감당할 수 있는 금액만 투자하세요
- ⚠️ 정기적으로 모니터링하세요
- ⚠️ 법적 조언은 전문가와 상담하세요

---

## 지원

문제가 발생하면:

1. 로그 파일 확인 (`bot_trading.log`)
2. Binance API 상태 확인
3. GitHub Issues 확인
4. 커뮤니티 포럼에서 질문

---

**마지막 업데이트**: 2025년 2월
