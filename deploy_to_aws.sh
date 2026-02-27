#!/bin/bash

# AWS EC2 배포 스크립트
# Ubuntu 22.04 LTS에서 실행

set -e  # 오류 발생 시 중단

echo ""
echo "============================================================"
echo "🚀 Binance Short Bot AWS 배포 스크립트"
echo "============================================================"
echo ""

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}[1/7] 시스템 업데이트 중...${NC}"
sudo apt update
sudo apt upgrade -y

echo -e "${YELLOW}[2/7] Python 3.9+ 설치 중...${NC}"
sudo apt install -y python3 python3-pip python3-venv git tmux

echo -e "${YELLOW}[3/7] 저장소 클론 중...${NC}"
cd ~
git clone https://github.com/jayforjdc-sudo/binance_future.git || cd binance_future && git pull

cd ~/binance_future

echo -e "${YELLOW}[4/7] 가상환경 설정 중...${NC}"
python3 -m venv venv
source venv/bin/activate

echo -e "${YELLOW}[5/7] 패키지 설치 중...${NC}"
pip install --upgrade pip
pip install -r requirements.txt

echo -e "${YELLOW}[6/7] 환경변수 설정 중...${NC}"

if [ ! -f .env ]; then
    echo ".env 파일이 없습니다."
    echo "다음 정보를 입력하세요:"

    read -p "Binance API Key: " BINANCE_KEY
    read -s -p "Binance API Secret: " BINANCE_SECRET
    echo ""
    read -p "Telegram Bot Token: " TELEGRAM_TOKEN
    read -p "Telegram Chat ID: " TELEGRAM_CHAT_ID

    cat > .env << EOF
BINANCE_API_KEY=$BINANCE_KEY
BINANCE_API_SECRET=$BINANCE_SECRET
TELEGRAM_TOKEN=$TELEGRAM_TOKEN
TELEGRAM_CHAT_ID=$TELEGRAM_CHAT_ID
EOF

    echo -e "${GREEN}✅ .env 파일 생성됨${NC}"
else
    echo -e "${GREEN}✅ .env 파일이 이미 존재합니다${NC}"
fi

echo -e "${YELLOW}[7/7] API 연결 검증 중...${NC}"
source venv/bin/activate
python3 verify_api.py

echo ""
echo "============================================================"
echo -e "${GREEN}✅ 배포 완료!${NC}"
echo "============================================================"
echo ""

echo "🚀 봇 실행 방법:"
echo ""
echo "방법 1) tmux 사용 (권장):"
echo "  tmux new-session -d -s binance_bot"
echo "  tmux send-keys -t binance_bot 'cd ~/binance_future && source venv/bin/activate && python3 binance_short_bot.py' Enter"
echo ""
echo "방법 2) 직접 실행:"
echo "  cd ~/binance_future && source venv/bin/activate && python3 binance_short_bot.py"
echo ""

echo "📋 모니터링:"
echo "  tail -f ~/binance_future/bot_trading.log"
echo ""

echo "📱 Telegram 테스트:"
echo "  python3 << 'PYEOF'"
echo "from telegram_notifier import TelegramNotifier"
echo "import os; from dotenv import load_dotenv"
echo "load_dotenv()"
echo "notifier = TelegramNotifier(os.getenv('TELEGRAM_TOKEN'), os.getenv('TELEGRAM_CHAT_ID'))"
echo "notifier.send_message('✅ AWS 배포 완료!')"
echo "PYEOF"
echo ""
