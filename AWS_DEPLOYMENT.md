# 🚀 AWS 배포 가이드

Binance Futures Short Bot을 AWS EC2에서 24/7 실행하기

---

## 📋 **필수 준비**

- AWS 계정 (EC2 프리티어 가능)
- Telegram Bot Token과 Chat ID
- GitHub 저장소 (이미 완료됨)

---

## 1️⃣ **AWS EC2 인스턴스 생성**

### **A. EC2 인스턴스 시작**

1. [AWS 콘솔](https://console.aws.amazon.com) 로그인
2. **EC2 대시보드** → **인스턴스 시작**
3. **AMI 선택**: Ubuntu 22.04 LTS (프리티어 가능)
4. **인스턴스 유형**: t2.micro (프리티어)
5. **스토리지**: 20GB (기본값 OK)
6. **보안 그룹**:
   - SSH (22번 포트) 추가
   - 아웃바운드는 모두 허용
7. **키 페어**: 새로 생성하고 안전하게 저장 (.pem 파일)
8. **인스턴스 시작**

### **B. 인스턴스에 접속**

```bash
# .pem 파일 권한 설정
chmod 400 your-key.pem

# SSH 접속
ssh -i your-key.pem ubuntu@your-ec2-ip-address
```

---

## 2️⃣ **서버 초기 설정**

### **A. 시스템 업데이트**

```bash
sudo apt update
sudo apt upgrade -y
```

### **B. Python 설치**

```bash
sudo apt install -y python3 python3-pip python3-venv git
```

### **C. 저장소 클론**

```bash
cd ~
git clone https://github.com/jayforjdc-sudo/binance_future.git
cd binance_future
```

### **D. 가상환경 설정**

```bash
python3 -m venv venv
source venv/bin/activate

# 패키지 설치
pip install -r requirements.txt
```

### **E. 환경변수 설정**

```bash
nano .env
```

아래 내용 입력:

```
BINANCE_API_KEY=your_actual_key
BINANCE_API_SECRET=your_actual_secret
TELEGRAM_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

저장: `Ctrl+O` → `Enter` → `Ctrl+X`

---

## 3️⃣ **봇 실행 (백그라운드)**

### **A. 간단한 방법 (tmux 사용)**

```bash
# tmux 설치
sudo apt install -y tmux

# 새 세션 생성
tmux new-session -d -s binance_bot

# 봇 실행
tmux send-keys -t binance_bot "cd ~/binance_future && source venv/bin/activate && python3 binance_btc_bot.py" Enter

# 세션 확인
tmux list-sessions

# 로그 보기
tail -f ~/binance_future/bot_trading.log
```

### **B. 더 안정적인 방법 (systemd 서비스)**

```bash
# 서비스 파일 생성
sudo nano /etc/systemd/system/binance-bot.service
```

아래 내용 입력:

```ini
[Unit]
Description=Binance Short Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/binance_future
Environment="PATH=/home/ubuntu/binance_future/venv/bin"
ExecStart=/home/ubuntu/binance_future/venv/bin/python3 binance_btc_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

저장: `Ctrl+O` → `Enter` → `Ctrl+X`

```bash
# 서비스 활성화 및 시작
sudo systemctl daemon-reload
sudo systemctl enable binance-bot
sudo systemctl start binance-bot

# 상태 확인
sudo systemctl status binance-bot

# 로그 보기
sudo journalctl -u binance-bot -f
```

---

## 4️⃣ **모니터링**

### **A. 로그 확인**

```bash
# 실시간 로그
tail -f ~/binance_future/bot_trading.log

# 거래 기록만
grep "SHORT\|CLOSE" ~/binance_future/bot_trading.log

# 오류만
grep "ERROR" ~/binance_future/bot_trading.log
```

### **B. 프로세스 확인**

```bash
# 봇 프로세스 확인
ps aux | grep binance_short_bot

# CPU/메모리 사용량
top
```

### **C. Telegram 알림 테스트**

```bash
python3 << 'EOF'
from telegram_notifier import TelegramNotifier
import os
from dotenv import load_dotenv

load_dotenv()
notifier = TelegramNotifier(
    os.getenv('TELEGRAM_TOKEN'),
    os.getenv('TELEGRAM_CHAT_ID')
)

if notifier.send_message("✅ 봇이 성공적으로 AWS에 배포되었습니다!"):
    print("Telegram 알림 정상")
else:
    print("Telegram 알림 오류 - Token과 Chat ID 확인")
EOF
```

---

## 5️⃣ **자동 업데이트 (선택)**

### **GitHub에서 자동 풀**

```bash
# cron 작업 추가
crontab -e
```

아래 추가 (매일 자정에 업데이트):

```
0 0 * * * cd ~/binance_future && git pull origin main
```

---

## 6️⃣ **비용 최적화**

### **비용 절감 팁**

| 방법 | 비용 |
|------|------|
| t2.micro (프리티어) | **무료** (1년) |
| t2.nano 사용 | ~$3/월 |
| Elastic IP 예약 | 추가 비용 없음 |
| CloudWatch 모니터링 | 기본 무료 |

### **비용 추정**

```
프리티어 (12개월): $0
이후 t2.nano: ~$3-5/월
EBS 스토리지 (20GB): ~$1/월
데이터 전송: 무료 (국내)

총 예상: 첫 1년 무료, 이후 $4-6/월
```

---

## 🔧 **문제 해결**

### **1. API 연결 오류**

```bash
# .env 파일 확인
cat .env

# Binance API 키 검증
python3 verify_api.py
```

### **2. Telegram 알림 안 됨**

```bash
# Token과 Chat ID 확인
python3 << 'EOF'
import os
from dotenv import load_dotenv
load_dotenv()
print(f"Token: {os.getenv('TELEGRAM_TOKEN')[:10]}...")
print(f"Chat ID: {os.getenv('TELEGRAM_CHAT_ID')}")
EOF
```

### **3. 봇 자꾸만 죽음**

```bash
# 로그 확인
tail -100 /var/log/syslog | grep binance

# 메모리 부족 확인
free -h

# 디스크 공간 확인
df -h
```

---

## 📱 **Telegram 알림 설정**

### **수신할 알림 종류**

```
✅ 봇 시작/종료
✅ SHORT 신호 발생
✅ 포지션 오픈
✅ 포지션 종료 (손익 포함)
✅ 청산 위험 경고
✅ 일일 거래 요약
✅ 에러 알림
```

---

## 🚀 **배포 완료 체크리스트**

```
☐ EC2 인스턴스 생성
☐ Python 3.9+ 설치
☐ 저장소 클론
☐ 가상환경 설정
☐ 패키지 설치 (pip install -r requirements.txt)
☐ .env 파일 설정 (Binance + Telegram)
☐ API 연결 검증 (python3 verify_api.py)
☐ 봇 실행 (tmux 또는 systemd)
☐ 로그 확인 (tail -f bot_trading.log)
☐ Telegram 알림 테스트
☐ 모니터링 설정 (선택)
```

---

## 📞 **지원**

문제 발생 시:

1. 로그 확인: `tail -f bot_trading.log`
2. GitHub Issues: https://github.com/jayforjdc-sudo/binance_future/issues
3. Telegram으로 오류 메시지 확인

---

**축하합니다! 이제 AWS에서 24/7 거래 봇을 실행할 수 있습니다!** 🎊
