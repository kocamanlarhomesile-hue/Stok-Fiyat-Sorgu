# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import csv
import os
from datetime import datetime

st.set_page_config(
    page_title="Stok ve Fiyat Kontrol",
    page_icon="🏷️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ─── Giriş Güvenliği ───────────────────────────────────────────────────────
DOGRU_SIFRE = "kocamanlar26"

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

def giris_ekrani():
    """Giriş ekranını göster"""
    st.markdown(
        """
        <div style="display:flex;justify-content:center;align-items:center;min-height:100vh;">
        </div>
        """,
        unsafe_allow_html=True
    )
    
    st.markdown("## 🔐 Giriş Yap")
    st.markdown("---")
    
    with st.form("login_form", clear_on_submit=True):
        sifre = st.text_input(
            "🔑 Şifre",
            type="password",
            placeholder="Şifrenizi girin...",
        )
        submitted = st.form_submit_button(
            "✅ Giriş Yap",
            use_container_width=True,
            type="primary"
        )
        
        if submitted:
            if sifre == DOGRU_SIFRE:
                st.session_state.authenticated = True
                st.success("✅ Giriş başarılı!")
                st.rerun()
            else:
                st.error("❌ Şifre yanlış! Lütfen tekrar deneyin.")

# Eğer kimlik doğrulama başarısız ise, giriş ekranını göster ve çık
if not st.session_state.authenticated:
    giris_ekrani()
    st.stop()

# Dosya yollarını ayarla
STOK_DOSYASI = "stok-fiyat-app/stok_listesi.csv"
TALEPLER_DOSYASI = "stok-fiyat-app/fiyat_talepleri.csv"

@st.cache_data(ttl=60)
def stok_yukle():
    try:
        df = pd.read_csv(STOK_DOSYASI, dtype={"barkod": str}, encoding="utf-8")
        df.columns = [c.strip().lower() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"📁 Dosya okuma hatası: {e}")
        return pd.DataFrame(columns=["barkod", "adi", "fiyat"])

def urun_bul_barkod(barkod: str, df: pd.DataFrame):
    barkod = barkod.strip()
    sonuc = df[df["barkod"].astype(str).str.strip() == barkod]
    return sonuc if len(sonuc) > 0 else None

def urun_ara_isim(arama: str, df: pd.DataFrame):
    if not arama.strip():
        return None
    maske = df["adi"].str.contains(arama.strip(), case=False, na=False)
    sonuc = df[maske]
    return sonuc if len(sonuc) > 0 else None

def talep_kaydet(barkod, urun_adi, mevcut_fiyat, yeni_fiyat, etiket_gerekli, not_metni):
    dosya_var = os.path.isfile(TALEPLER_DOSYASI)
    with open(TALEPLER_DOSYASI, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not dosya_var:
            writer.writerow(["tarih", "saat", "barkod", "urun_adi",
                              "mevcut_fiyat", "yeni_fiyat_talebi",
                              "etiket_gerekli", "not"])
        simdi = datetime.now()
        writer.writerow([
            simdi.strftime("%Y-%m-%d"),
            simdi.strftime("%H:%M:%S"),
            barkod, urun_adi, mevcut_fiyat, yeni_fiyat,
            "Evet" if etiket_gerekli else "Hayır",
            not_metni
        ])

def urun_goster_ve_form(urun_row):
    st.markdown(
        f"""
        <div style="background:#f0f8ff;border-radius:12px;padding:24px;
                    text-align:center;margin-bottom:16px;border:1px solid #cce0ff;">
            <p style="font-size:11px;color:#888;margin:0;letter-spacing:1px;">ÜRÜN ADI</p>
            <h2 style="font-size:24px;color:#1a1a2e;margin:8px 0;line-height:1.3;">{urun_row['adi']}</h2>
            <p style="font-size:11px;color:#888;margin:0;letter-spacing:1px;">MEVCUT FİYAT</p>
            <h1 style="font-size:52px;color:#e63946;margin:8px 0;font-weight:bold;">{float(urun_row['fiyat']):.2f} ₺</h1>
            <p style="font-size:11px;color:#bbb;margin:0;">Barkod: {urun_row['barkod']}</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    if not st.session_state.get("talep_gonderildi"):
        st.markdown("### 📝 Fiyat Değişiklik Talebi")
        with st.form("talep_formu", clear_on_submit=False):
            yeni_fiyat = st.number_input(
                "💰 Yeni Fiyat Talebi (₺)",
                min_value=0.01, max_value=999999.99,
                value=float(urun_row["fiyat"]), step=0.25, format="%.2f"
            )
            etiket_gerekli = st.checkbox("🏷️ Etiket Gerekli mi?")
            not_metni = st.text_area("📌 Not (İsteğe Bağlı)",
                                     placeholder="Açıklama...", max_chars=500)
            if st.form_submit_button("✅ TALEBİ GÖNDER", use_container_width=True, type="primary"):
                try:
                    talep_kaydet(str(urun_row["barkod"]), str(urun_row["adi"]),
                                 float(urun_row["fiyat"]), yeni_fiyat,
                                 etiket_gerekli, not_metni.strip())
                    st.session_state.talep_gonderildi = True
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Kayıt hatası: {e}")
    else:
        st.success("✅ Talebiniz kaydedildi!")
        if st.button("🔄 Yeni Sorgulama", use_container_width=True, type="primary"):
            st.session_state.bulunan_urunler = None
            st.session_state.talep_gonderildi = False
            st.session_state.son_barkod = ""
            st.session_state.arama_modu = None
            st.rerun()

# MAIN UYGULAMA
st.markdown("# 📦 STOK VE FIYAT SORGU")
st.markdown("---")

df = stok_yukle()

if df.empty:
    st.error("❌ Stok listesi yüklenemedi!")
    st.stop()

col1, col2 = st.columns(2)
with col1:
    if st.button("📱 Barkod Okut", use_container_width=True, type="secondary"):
        st.session_state.arama_modu = "barkod"

with col2:
    if st.button("🔍 Ürün Ara", use_container_width=True, type="secondary"):
        st.session_state.arama_modu = "isim"

st.markdown("---")

arama_modu = st.session_state.get("arama_modu")

if arama_modu == "barkod":
    barkod_girdi = st.text_input("Barkod girin:", key="barkod_input")
    if barkod_girdi:
        sonuc = urun_bul_barkod(barkod_girdi, df)
        if sonuc is not None and len(sonuc) > 0:
            st.session_state.bulunan_urunler = sonuc
        else:
            st.warning("⚠️ Ürün bulunamadı!")

elif arama_modu == "isim":
    isim_girdi = st.text_input("Ürün adı girin:", key="isim_input")
    if isim_girdi:
        sonuc = urun_ara_isim(isim_girdi, df)
        if sonuc is not None and len(sonuc) > 0:
            st.session_state.bulunan_urunler = sonuc
        else:
            st.warning("⚠️ Ürün bulunamadı!")

# Bulunan ürünleri göster
bulunan = st.session_state.get("bulunan_urunler")
if bulunan is not None:
    for idx, (_, row) in enumerate(bulunan.iterrows()):
        urun_goster_ve_form(row)
        if idx < len(bulunan) - 1:
            st.divider()
