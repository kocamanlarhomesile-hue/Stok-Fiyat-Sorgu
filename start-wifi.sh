#!/bin/bash

# STOK FİYAT SORGU - WiFi Başlangıç Scripti
# Linux'ta çalıştırma: bash start-wifi.sh

set -e

PROJECT_DIR="/tmp/Stok-Fiyat-Sorgu"
PORT=8501
ADDRESS="0.0.0.0"

# IP adresini bul
WIFI_IP=$(python3 -c "import socket; s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(('8.8.8.8', 80)); print(s.getsockname()[0]); s.close()" 2>/dev/null)
HOSTNAME=$(uname -n)

echo "════════════════════════════════════════════════════════"
echo "🚀 STOK FİYAT SORGU UYGULAMASI BAŞLATILIYOR"
echo "════════════════════════════════════════════════════════"
echo ""
echo "📱 WiFi Erişim Adresi:"
echo "   ➜ http://$WIFI_IP:$PORT"
echo ""
echo "🖥️  Lokal Erişim Adresi:"
echo "   ➜ http://localhost:$PORT"
echo ""
echo "💻 Cihaz: $HOSTNAME"
echo "📂 Proje: $PROJECT_DIR"
echo "⏳ Başlatılıyor... Lütfen bekleyin"
echo ""
echo "════════════════════════════════════════════════════════"
echo ""

# PATH'e /var/data/python/bin ekle (pip paketleri için)
export PATH="/var/data/python/bin:$PATH"

# Proje dizinine git
cd "$PROJECT_DIR"

# Streamlit'ı başlat
python3 -m streamlit run main.py \
  --server.address "$ADDRESS" \
  --server.port "$PORT" \
  --logger.level=info \
  --client.showErrorDetails=true

