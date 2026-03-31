# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import csv
import os
from datetime import datetime

# --- Sayfa Yapılandırması ---
st.set_page_config(
    page_title="Stok ve Fiyat Kontrol",
    page_icon="🏷️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- Sabitler ---
STOK_DOSYASI = os.path.join(os.path.dirname(__file__), "stok_listesi.csv")
TALEPLER_DOSYASI = os.path.join(os.path.dirname(__file__), "fiyat_talepleri.csv")

# --- Yardımcı Fonksiyonlar ---
@st.cache_data(ttl=30)
def stok_yukle():
    """CSV dosyasından stok listesini yükle."""
    try:
        df = pd.read_csv(STOK_DOSYASI, dtype={"barkod": str}, encoding="utf-8")
        df.columns = [c.strip().lower() for c in df.columns]
        return df
    except FileNotFoundError:
        st.error(f"'{STOK_DOSYASI}' dosyası bulunamadı.")
        return pd.DataFrame(columns=["barkod", "adi", "fiyat"])
    except Exception as e:
        st.error(f"Dosya okuma hatası: {e}")
        return pd.DataFrame(columns=["barkod", "adi", "fiyat"])


def urun_bul(barkod: str, df: pd.DataFrame):
    """Barkoda göre ürün bul."""
    barkod = barkod.strip()
    sonuc = df[df["barkod"].astype(str).str.strip() == barkod]
    if len(sonuc) > 0:
        return sonuc.iloc[0]
    return None


def talep_kaydet(barkod, urun_adi, mevcut_fiyat, yeni_fiyat, etiket_gerekli, not_metni):
    """Fiyat talebini CSV dosyasına ekle (append)."""
    dosya_var = os.path.isfile(TALEPLER_DOSYASI)
    with open(TALEPLER_DOSYASI, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not dosya_var:
            writer.writerow([
                "tarih", "saat", "barkod", "urun_adi",
                "mevcut_fiyat", "yeni_fiyat_talebi",
                "etiket_gerekli", "not"
            ])
        simdi = datetime.now()
        writer.writerow([
            simdi.strftime("%Y-%m-%d"),
            simdi.strftime("%H:%M:%S"),
            barkod,
            urun_adi,
            mevcut_fiyat,
            yeni_fiyat,
            "Evet" if etiket_gerekli else "Hayır",
            not_metni
        ])


# --- Session State ---
if "bulunan_urun" not in st.session_state:
    st.session_state.bulunan_urun = None
if "barkod_girisi" not in st.session_state:
    st.session_state.barkod_girisi = ""
if "talep_gonderildi" not in st.session_state:
    st.session_state.talep_gonderildi = False


# --- Stok Yükle ---
stok_df = stok_yukle()


# --- Başlık ---
st.markdown("## 🏷️ Stok & Fiyat Kontrol")
st.markdown("---")


# --- Barkod Tarama Bölümü ---
st.markdown("### 📷 Barkod Tara veya Gir")

# Kamera ile barkod tarama
kamera_aktif = st.toggle("📸 Kamerayı Aç (Barkod Tara)", value=False)

if kamera_aktif:
    st.info("Kamerayı barkoda doğrultun. Tarama tamamlandığında barkod aşağıya yapıştırın.")
    kamera_foto = st.camera_input("Barkod Fotoğrafı Çek")

    if kamera_foto is not None:
        from PIL import Image
        import io
        try:
            from pyzbar.pyzbar import decode
            import numpy as np

            img = Image.open(kamera_foto)
            img_array = np.array(img)
            barkodlar = decode(img_array)

            if barkodlar:
                okunan = barkodlar[0].data.decode("utf-8")
                st.session_state.barkod_girisi = okunan
                st.success(f"✅ Barkod okundu: **{okunan}**")
            else:
                st.warning("⚠️ Barkod okunamadı. Lütfen tekrar deneyin veya manuel girin.")
        except ImportError:
            st.error("Barkod okuma kütüphanesi yüklü değil.")
        except Exception as e:
            st.error(f"Barkod okuma hatası: {e}")

st.markdown("**veya**")

# Manuel barkod girişi
col1, col2 = st.columns([3, 1])
with col1:
    barkod_input = st.text_input(
        "Barkod Numarası Gir",
        value=st.session_state.barkod_girisi,
        placeholder="Örn: 8690526021498",
        label_visibility="collapsed"
    )
with col2:
    sorgula_btn = st.button("🔍 Sorgula", use_container_width=True, type="primary")


# --- Sorgulama ---
if sorgula_btn and barkod_input.strip():
    st.session_state.barkod_girisi = barkod_input.strip()
    st.session_state.talep_gonderildi = False
    urun = urun_bul(barkod_input.strip(), stok_df)
    st.session_state.bulunan_urun = urun

elif sorgula_btn and not barkod_input.strip():
    st.warning("⚠️ Lütfen bir barkod girin.")


# --- Ürün Bilgisi Göster ---
if st.session_state.bulunan_urun is not None:
    urun = st.session_state.bulunan_urun
    st.markdown("---")

    # Ürün adı ve fiyat - büyük gösterim
    st.markdown(
        f"""
        <div style="background-color:#f0f8ff; border-radius:12px; padding:24px; text-align:center; margin-bottom:16px;">
            <p style="font-size:14px; color:#666; margin:0;">ÜRÜN ADI</p>
            <h2 style="font-size:32px; color:#1a1a2e; margin:8px 0;">{urun['adi']}</h2>
            <p style="font-size:14px; color:#666; margin:0;">MEVCUT FİYAT</p>
            <h1 style="font-size:48px; color:#e63946; margin:8px 0; font-weight:bold;">{float(urun['fiyat']):.2f} ₺</h1>
            <p style="font-size:12px; color:#999; margin:0;">Barkod: {urun['barkod']}</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # --- Talep Formu ---
    if not st.session_state.talep_gonderildi:
        st.markdown("### 📝 Fiyat Değişiklik Talebi")

        with st.form("talep_formu", clear_on_submit=False):
            yeni_fiyat = st.number_input(
                "💰 Yeni Fiyat Talebi (₺)",
                min_value=0.01,
                max_value=999999.99,
                value=float(urun["fiyat"]),
                step=0.25,
                format="%.2f"
            )

            etiket_gerekli = st.checkbox("🏷️ Etiket Gerekli mi?")

            not_metni = st.text_area(
                "📌 Not (İsteğe Bağlı)",
                placeholder="Fiyat değişikliği ile ilgili açıklama girebilirsiniz...",
                max_chars=500
            )

            gonder_btn = st.form_submit_button(
                "✅ TALEBİ GÖNDER",
                use_container_width=True,
                type="primary"
            )

            if gonder_btn:
                try:
                    talep_kaydet(
                        barkod=str(urun["barkod"]),
                        urun_adi=str(urun["adi"]),
                        mevcut_fiyat=float(urun["fiyat"]),
                        yeni_fiyat=yeni_fiyat,
                        etiket_gerekli=etiket_gerekli,
                        not_metni=not_metni.strip()
                    )
                    st.session_state.talep_gonderildi = True
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Kayıt hatası: {e}")

    else:
        st.success("✅ Talebiniz başarıyla kaydedildi!")
        if st.button("🔄 Yeni Sorgulama Yap", use_container_width=True):
            st.session_state.bulunan_urun = None
            st.session_state.barkod_girisi = ""
            st.session_state.talep_gonderildi = False
            st.rerun()

elif st.session_state.barkod_girisi and sorgula_btn:
    st.error(f"❌ **'{st.session_state.barkod_girisi}'** barkodlu ürün bulunamadı.")


# --- Alt Bilgi ---
st.markdown("---")
st.markdown(
    "<p style='text-align:center; color:#aaa; font-size:12px;'>Stok & Fiyat Kontrol Sistemi • UTF-8</p>",
    unsafe_allow_html=True
)
