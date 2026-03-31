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
@st.cache_data(ttl=60)
def stok_yukle():
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


def urun_bul_barkod(barkod: str, df: pd.DataFrame):
    barkod = barkod.strip()
    sonuc = df[df["barkod"].astype(str).str.strip() == barkod]
    if len(sonuc) > 0:
        return sonuc
    return None


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


def urun_goster_ve_form(urun_row):
    """Tek bir ürünü göster ve talep formu aç."""
    st.markdown(
        f"""
        <div style="background-color:#f0f8ff; border-radius:12px; padding:24px;
                    text-align:center; margin-bottom:16px; border:1px solid #cce0ff;">
            <p style="font-size:13px; color:#666; margin:0; text-transform:uppercase;">Ürün Adı</p>
            <h2 style="font-size:28px; color:#1a1a2e; margin:8px 0; line-height:1.2;">{urun_row['adi']}</h2>
            <p style="font-size:13px; color:#666; margin:0; text-transform:uppercase;">Mevcut Fiyat</p>
            <h1 style="font-size:52px; color:#e63946; margin:8px 0; font-weight:bold;">{float(urun_row['fiyat']):.2f} ₺</h1>
            <p style="font-size:11px; color:#aaa; margin:0;">Barkod: {urun_row['barkod']}</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    if not st.session_state.get("talep_gonderildi"):
        st.markdown("### 📝 Fiyat Değişiklik Talebi")
        with st.form("talep_formu", clear_on_submit=False):
            yeni_fiyat = st.number_input(
                "💰 Yeni Fiyat Talebi (₺)",
                min_value=0.01,
                max_value=999999.99,
                value=float(urun_row["fiyat"]),
                step=0.25,
                format="%.2f"
            )
            etiket_gerekli = st.checkbox("🏷️ Etiket Gerekli mi?")
            not_metni = st.text_area(
                "📌 Not (İsteğe Bağlı)",
                placeholder="Fiyat değişikliği hakkında açıklama...",
                max_chars=500
            )
            gonder = st.form_submit_button("✅ TALEBİ GÖNDER", use_container_width=True, type="primary")
            if gonder:
                try:
                    talep_kaydet(
                        str(urun_row["barkod"]),
                        str(urun_row["adi"]),
                        float(urun_row["fiyat"]),
                        yeni_fiyat,
                        etiket_gerekli,
                        not_metni.strip()
                    )
                    st.session_state.talep_gonderildi = True
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Kayıt hatası: {e}")
    else:
        st.success("✅ Talebiniz başarıyla kaydedildi!")
        if st.button("🔄 Yeni Sorgulama Yap", use_container_width=True):
            st.session_state.bulunan_urunler = None
            st.session_state.secili_urun_idx = None
            st.session_state.barkod_girisi = ""
            st.session_state.isim_arama = ""
            st.session_state.talep_gonderildi = False
            st.rerun()


# --- Session State ---
defaults = {
    "bulunan_urunler": None,
    "secili_urun_idx": None,
    "barkod_girisi": "",
    "isim_arama": "",
    "talep_gonderildi": False,
    "arama_modu": "barkod"
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# --- Stok Yükle ---
stok_df = stok_yukle()

# --- Başlık ---
st.markdown("## 🏷️ Stok & Fiyat Kontrol")
st.caption(f"Toplam {len(stok_df):,} ürün yüklendi.")
st.markdown("---")

# --- Sekme: Barkod / İsim Arama ---
tab1, tab2 = st.tabs(["📷 Barkod ile Sorgula", "🔤 İsim ile Ara"])

# ========== TAB 1: BARKOD ==========
with tab1:
    kamera_aktif = st.toggle("📸 Kamerayı Aç (Barkod Tara)", value=False)

    if kamera_aktif:
        kamera_foto = st.camera_input("Barkod Fotoğrafı Çek")
        if kamera_foto is not None:
            from PIL import Image
            import numpy as np
            try:
                from pyzbar.pyzbar import decode
                img = Image.open(kamera_foto)
                img_array = np.array(img)
                barkodlar = decode(img_array)
                if barkodlar:
                    okunan = barkodlar[0].data.decode("utf-8")
                    st.session_state.barkod_girisi = okunan
                    st.success(f"✅ Barkod okundu: **{okunan}**")
                else:
                    st.warning("⚠️ Barkod okunamadı, tekrar deneyin veya manuel girin.")
            except Exception as e:
                st.error(f"Barkod okuma hatası: {e}")

    col1, col2 = st.columns([3, 1])
    with col1:
        barkod_input = st.text_input(
            "Barkod",
            value=st.session_state.barkod_girisi,
            placeholder="Barkod numarası girin...",
            label_visibility="collapsed"
        )
    with col2:
        sorgula_btn = st.button("🔍 Sorgula", use_container_width=True, type="primary", key="barkod_sorgula")

    if sorgula_btn:
        if barkod_input.strip():
            st.session_state.barkod_girisi = barkod_input.strip()
            st.session_state.talep_gonderildi = False
            st.session_state.secili_urun_idx = None
            sonuc = urun_bul_barkod(barkod_input.strip(), stok_df)
            st.session_state.bulunan_urunler = sonuc
            st.session_state.arama_modu = "barkod"
        else:
            st.warning("⚠️ Lütfen bir barkod girin.")

    if st.session_state.bulunan_urunler is not None and st.session_state.arama_modu == "barkod":
        df_sonuc = st.session_state.bulunan_urunler
        st.markdown("---")
        if len(df_sonuc) == 0:
            st.error(f"❌ **'{st.session_state.barkod_girisi}'** barkodlu ürün bulunamadı.")
        elif len(df_sonuc) == 1:
            urun_goster_ve_form(df_sonuc.iloc[0])
        else:
            st.warning(f"⚠️ Bu barkod için **{len(df_sonuc)} ürün** bulundu. Lütfen birini seçin:")
            secenekler = [f"{row['adi']} — {float(row['fiyat']):.2f} ₺" for _, row in df_sonuc.iterrows()]
            secim = st.selectbox("Ürün Seçin:", secenekler, index=0)
            idx = secenekler.index(secim)
            urun_goster_ve_form(df_sonuc.iloc[idx])

# ========== TAB 2: İSİM ARAMA ==========
with tab2:
    col3, col4 = st.columns([3, 1])
    with col3:
        isim_input = st.text_input(
            "Ürün Adı",
            value=st.session_state.isim_arama,
            placeholder="Ürün adını yazın (örn: TABAK, KASE...)",
            label_visibility="collapsed"
        )
    with col4:
        isim_btn = st.button("🔍 Ara", use_container_width=True, type="primary", key="isim_ara")

    if isim_btn:
        if isim_input.strip():
            st.session_state.isim_arama = isim_input.strip()
            st.session_state.talep_gonderildi = False
            st.session_state.secili_urun_idx = None
            sonuc = urun_ara_isim(isim_input.strip(), stok_df)
            st.session_state.bulunan_urunler = sonuc
            st.session_state.arama_modu = "isim"
        else:
            st.warning("⚠️ Lütfen bir arama terimi girin.")

    if st.session_state.bulunan_urunler is not None and st.session_state.arama_modu == "isim":
        df_sonuc = st.session_state.bulunan_urunler
        st.markdown("---")
        if df_sonuc is None or len(df_sonuc) == 0:
            st.error(f"❌ **'{st.session_state.isim_arama}'** ile eşleşen ürün bulunamadı.")
        elif len(df_sonuc) == 1:
            urun_goster_ve_form(df_sonuc.iloc[0])
        else:
            st.info(f"**{len(df_sonuc)} ürün** bulundu. Aşağıdan seçin:")
            secenekler = [f"{row['adi']} — {float(row['fiyat']):.2f} ₺" for _, row in df_sonuc.iterrows()]
            secim = st.selectbox("Ürün Seçin:", secenekler, index=0, key="isim_secim")
            idx = secenekler.index(secim)
            urun_goster_ve_form(df_sonuc.iloc[idx])

# --- Alt Bilgi ---
st.markdown("---")
st.markdown(
    "<p style='text-align:center; color:#aaa; font-size:11px;'>Stok & Fiyat Kontrol Sistemi • UTF-8</p>",
    unsafe_allow_html=True
)
