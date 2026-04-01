# Stok-Fiyat-Sorgu WiFi Başlangıç Rehberi

## 🎯 Sistem Hazırlığı Tamamlandı

Uygulamanız şu anda **192.168.1.13:8501** adresinde çalışıyor ve aynı WiFi ağındaki tüm cihazlardan erişilebilir.

---

## 📱 Erişim Yolları

### 1. **Aynı Bilgisayardan** (Lokal)
```bash
http://localhost:8501
```

### 2. **Aynı WiFi Ağındaki Başka Cihazlardan**
```bash
http://192.168.1.13:8501
```
> Mobil telefon, tablet, dizüstü bilgisayar vb. kullanabilirsiniz (Pop!_OS'la aynı WiFi'de olmalı)

### 3. **İnternet Üzerinden** (Dış Ağ)
```bash
http://188.3.53.6:8501
```

---

## 🚀 Gelecekte Hızlı Başlatma

Uygulamayı durdurup yeniden başlatmanız gerekirse:

### Önceki Prosesi Durdur
```bash
# Terminal'de Ctrl+C tuşuna basın VEYA
killall python3
```

### Yeniden Başlat
```bash
cd /tmp/Stok-Fiyat-Sorgu
bash start-wifi.sh
```

Veya tek satırda:
```bash
cd /tmp/Stok-Fiyat-Sorgu && /var/data/python/bin/python3 -m streamlit run main.py --server.address 0.0.0.0 --server.port 8501
```

---

## 🔧 Kurulmuş Paketler

- ✅ **Python 3.13.12**
- ✅ **Streamlit 1.56.0** - Web UI çerçevesi
- ✅ **Pandas 3.0.2** - Veri işleme
- ✅ **OpenCV (headless)** - Görüntü işleme
- ✅ **Pillow 12.1.1** - Resim kütüphanesi
- ✅ **pyzbar 0.1.9** - Barkod okuma
- ✅ **Altair** - Veri görselleştirme

---

## 📂 Proje Yapısı

```
/tmp/Stok-Fiyat-Sorgu/
├── main.py                      # Ana giriş noktası
├── stok-fiyat-app/
│   ├── app.py                   # Streamlit uygulaması
│   ├── stok_listesi_home.csv   # Home stok verileri
│   ├── stok_listesi_market.csv # Market stok verileri
│   └── stok_listesi.csv        # Birleştirilmiş data
├── .streamlit/config.toml       # Streamlit konfigürasyonu
├── start-wifi.sh                # WiFi başlangıç scripti (yeni)
├── users.csv                    # Kullanıcı veritabanı
├── loglar.csv                   # İşlem logları
└── talepler.csv                 # Fiyat talepleri
```

---

## ⚙️ Konfigürasyon Detayları

Streamlit ayarları (.streamlit/config.toml):
```toml
[server]
address = "0.0.0.0"           # Tüm ağ arayüzlerində dinle
port = 8501                   # Port numarası
headless = true               # GUI olmadan çalış
enableCORS = true             # Çapraz kaynak isteklerine izin ver

[client]
showErrorDetails = true       # Hata detaylarını göster
```

---

## 🐛 Sorun Giderme

### Port 8501 Zaten Kullanılıyorsa
```bash
# Kullanılan prosesi bul ve kapat
lsof -i :8501
kill -9 <PID>

# Veya farklı port kullan
python3 -m streamlit run main.py --server.port <8502|8503|...>
```

### WiFi Bağlantısı Kontrol
```bash
# Cihaz IP adresini kontrol et
python3 -c "import socket; s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(('8.8.8.8', 80)); print(s.getsockname()[0]); s.close()"
```

### Uygulamaya Erişim Sorunları
```bash
# Lokal bağlantı test et
curl http://localhost:8501

# Network test
ping 192.168.1.13
```

---

## 📊 Yaşam Döngüsü

| Eylem | Komut |
|-------|-------|
| **Başlat** | `cd /tmp/Stok-Fiyat-Sorgu && bash start-wifi.sh` |
| **Durdur** | `Ctrl+C` veya `killall python3` |
| **Durum Kontrol** | `ps aux \| grep streamlit` |
| **Port Kontrol** | `lsof -i :8501` |
| **Logları Temizle** | `rm loglar.csv talepler.csv` (saklamak istersen yapma!) |

---

## 💡 İpuçları

1. **Sesli Barkod Tarama**: Barcode scanner komponenti, QR/barcode okumalar için hazır
2. **CSV Backups**: İlk çalıştırmadan önce tüm CSV dosyalarının yedeklerini alın
3. **Türkçe Destek**: Uygulama Türkçe karakterleri (ş, ç, ğ, ü, ö, ı) tam destekler
4. **Dosya Yolları**: Tüm veritabanı dosyaları `/tmp/Stok-Fiyat-Sorgu/` altında

---

**Hazır mısınız? 🚀 Şimdi tarayıcıda `http://192.168.1.13:8501` açıp kullanmaya başlayabilirsiniz!**

