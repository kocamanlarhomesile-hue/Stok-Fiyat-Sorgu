# -*- coding: utf-8 -*-
"""
KOCAMANLAR STOK & FİYAT KONTROL UYGULAMASI
ZXing.js tabanlı barkod tarayıcı
"""

import streamlit as st
import pandas as pd
import csv
import os
from datetime import datetime
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Stok ve Fiyat Kontrol",
    page_icon="🏷️",
    layout="wide",
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

if not st.session_state.authenticated:
    giris_ekrani()
    st.stop()

# ─── Dosya Yolları ─────────────────────────────────────────────────────────
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
        return pd.DataFrame(columns=["barkod", "adi", "fiyat", "miktar", "dvz"])

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
            writer.writerow(["tarih", "saat", "barkod", "urun_adi", "mevcut_fiyat",
                             "yeni_fiyat_talebi", "etiket_gerekli", "not"])
        simdi = datetime.now()
        writer.writerow([simdi.strftime("%Y-%m-%d"), simdi.strftime("%H:%M:%S"), barkod,
                         urun_adi, mevcut_fiyat, yeni_fiyat,
                         "Evet" if etiket_gerekli else "Hayır", not_metni])

def urun_goster_ve_form(urun_row):
    st.markdown(f"""
        <div style="background:#f0f8ff;border-radius:12px;padding:24px;text-align:center;margin-bottom:16px;border:1px solid #cce0ff;">
            <p style="font-size:11px;color:#888;margin:0;letter-spacing:1px;">ÜRÜN ADI</p>
            <h2 style="font-size:24px;color:#1a1a2e;margin:8px 0;">{urun_row['adi']}</h2>
            <p style="font-size:11px;color:#888;margin:0;letter-spacing:1px;">MEVCUT FİYAT</p>
            <h1 style="font-size:52px;color:#e63946;margin:8px 0;">{float(urun_row['fiyat']):.2f} ₺</h1>
            <p style="font-size:11px;color:#bbb;margin:0;">📦 Stok: {urun_row.get('miktar', 'N/A')} {urun_row.get('dvz', '')}</p>
            <p style="font-size:11px;color:#bbb;margin:0;">Barkod: {urun_row['barkod']}</p>
        </div>
    """, unsafe_allow_html=True)

    if not st.session_state.get("talep_gonderildi"):
        st.markdown("### 📝 Fiyat Değişiklik Talebi")
        with st.form("talep_formu", clear_on_submit=False):
            col1, col2 = st.columns(2)
            with col1:
                yeni_fiyat = st.number_input("💰 Yeni Fiyat (₺)", min_value=0.01, max_value=999999.99,
                                             value=float(urun_row["fiyat"]), step=0.25, format="%.2f")
            with col2:
                etiket_gerekli = st.checkbox("🏷️ Etiket Gerekli?", value=False)
            not_metni = st.text_area("📌 Not (İsteğe Bağlı)", placeholder="Açıklama...", max_chars=500)
            if st.form_submit_button("✅ TALEBİ GÖNDER", use_container_width=True, type="primary"):
                try:
                    talep_kaydet(str(urun_row["barkod"]), str(urun_row["adi"]),
                                 float(urun_row["fiyat"]), yeni_fiyat, etiket_gerekli, not_metni.strip())
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

def goster_sonuc(df_sonuc, prefix=""):
    if df_sonuc is None or len(df_sonuc) == 0:
        return
    if len(df_sonuc) == 1:
        urun_goster_ve_form(df_sonuc.iloc[0])
    else:
        st.info(f"**{len(df_sonuc)} ürün** bulundu — birini seçin:")
        secenekler = [f"{row['adi']} — {float(row['fiyat']):.2f} ₺" for _, row in df_sonuc.iterrows()]
        secim = st.selectbox("Ürün:", secenekler, key=f"secim_{prefix}")
        idx = secenekler.index(secim)
        urun_goster_ve_form(df_sonuc.iloc[idx])

def zxing_barcode_scanner():
    """ZXing.js ile HTML5 barcode tarayıcı"""
    html_template = """<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);display:flex;justify-content:center;align-items:center;min-height:100vh;padding:10px}.scanner-container{width:100%;max-width:500px;background:white;border-radius:20px;box-shadow:0 20px 60px rgba(0,0,0,0.3);overflow:hidden}.scanner-header{background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:white;padding:20px;text-align:center}.scanner-header h2{font-size:20px;margin:0 0 5px 0}.scanner-header p{font-size:13px;opacity:0.9;margin:0}.video-wrapper{position:relative;width:100%;background:#000;aspect-ratio:1;overflow:hidden}#videoElement{width:100%;height:100%;object-fit:cover;display:block}.scan-line{position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(to right,transparent,#00ff00,transparent);animation:scan 2s infinite}@keyframes scan{0%,100%{top:10%}50%{top:90%}}.corner-marker{position:absolute;width:40px;height:40px;border:3px solid #00ff00}.corner-marker.top-left{top:15px;left:15px;border-right:none;border-bottom:none}.corner-marker.top-right{top:15px;right:15px;border-left:none;border-bottom:none}.corner-marker.bottom-left{bottom:15px;left:15px;border-right:none;border-top:none}.corner-marker.bottom-right{bottom:15px;right:15px;border-left:none;border-top:none}.controls{display:grid;grid-template-columns:1fr 1fr;gap:10px;padding:15px;background:#f8f9fa}button{padding:12px 16px;border:none;border-radius:10px;font-size:14px;font-weight:600;cursor:pointer;transition:all 0.2s}.btn-primary{background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:white}.btn-primary:hover{transform:translateY(-2px);box-shadow:0 10px 20px rgba(102,126,234,0.3)}.btn-secondary{background:#e0e0e0;color:#333}.btn-secondary:hover{background:#d0d0d0}.status-area{padding:15px;background:#f0f7ff;border-top:1px solid #e0e0e0;text-align:center;font-size:14px;color:#666;min-height:50px;display:flex;align-items:center;justify-content:center}.status-area.success{background:#e8f5e9;color:#2e7d32;font-weight:600;border-top-color:#4caf50}</style></head><body><div class="scanner-container"><div class="scanner-header"><h2>📱 Barkod Tarayıcı</h2><p>Barkodu kameraya gösterin</p></div><div class="video-wrapper"><video id="videoElement" autoplay playsinline muted></video><div class="scan-line"></div><div class="corner-marker top-left"></div><div class="corner-marker top-right"></div><div class="corner-marker bottom-left"></div><div class="corner-marker bottom-right"></div></div><div class="status-area" id="statusArea">⏳ Hazırlanıyor...</div><div class="controls"><button class="btn-primary" id="torchBtn" style="display:none;">💡 Flaş</button><button class="btn-secondary" id="resetBtn">🔄 Sıfırla</button></div></div><script src="https://unpkg.com/@zxing/library@0.20.0/umd/index.js"></script><script>const videoElement=document.getElementById('videoElement');const statusArea=document.getElementById('statusArea');const resetBtn=document.getElementById('resetBtn');const torchBtn=document.getElementById('torchBtn');let stream=null;let lastScannedValue='';async function initCamera(){try{const constraints={video:{facingMode:'environment',width:{ideal:1280},height:{ideal:720}},audio:false};stream=await navigator.mediaDevices.getUserMedia(constraints);videoElement.srcObject=stream;const track=stream.getVideoTracks()[0];try{await track.applyConstraints({advanced:[{focusMode:'continuous'}]});console.log('Continuous focus enabled')}catch(e){console.log('Focus not available')}try{const capabilities=track.getCapabilities&&track.getCapabilities();if(capabilities&&capabilities.torch){torchBtn.style.display='block';torchBtn.onclick=async()=>{const settings=track.getSettings();await track.applyConstraints({advanced:[{torch:!settings.torch}]});}}}catch(e){console.log('Torch not available')}statusArea.textContent='✅ Hazır - Barkodu tarayın';statusArea.className='status-area success';startScanning();}catch(err){statusArea.textContent='❌ Kamera: '+err.message;statusArea.className='status-area';}}function startScanning(){const canvas=document.createElement('canvas');const ctx=canvas.getContext('2d');function scan(){if(videoElement.readyState===videoElement.HAVE_ENOUGH_DATA){canvas.width=videoElement.videoWidth;canvas.height=videoElement.videoHeight;ctx.drawImage(videoElement,0,0);try{const luminanceSource=new ZXing.HTMLCanvasElementLuminanceSource(canvas);const binarizer=new ZXing.HybridBinarizer(luminanceSource);const bitmap=new ZXing.BinaryBitmap(binarizer);const hints=new Map();hints.set(ZXing.DecodeHintType.TRY_HARDER,true);const reader=new ZXing.MultiFormatReader();try{const result=reader.decode(bitmap,hints);if(result&&result.text&&result.text!==lastScannedValue){lastScannedValue=result.text;statusArea.textContent='📌 '+result.text;statusArea.className='status-area success';window.parent.postMessage({type:'barcode_detected',value:result.text},'*');}}catch(e){}}catch(err){}}setTimeout(scan,150);}scan();}resetBtn.onclick=()=>{lastScannedValue='';statusArea.textContent='✅ Hazır - Barkodu tarayın';statusArea.className='status-area success';videoElement.focus();};window.addEventListener('load',initCamera);window.addEventListener('beforeunload',()=>{if(stream){stream.getTracks().forEach(track=>track.stop());}});</script></body></html>"""
    components.html(html_template, height=750)

# ─── Session State ─────────────────────────────────────────────────────────
defaults = {"bulunan_urunler": None, "talep_gonderildi": False, "arama_modu": None, "son_barkod": ""}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

stok_df = stok_yukle()

# ─── Sayfa ────────────────────────────────────────────────────────────────────
st.markdown("## 🏷️ Stok & Fiyat Kontrol Sistemi")
st.caption(f"📊 {len(stok_df):,} ürün yüklendi • ✅ Hazır")
st.markdown("---")

tab1, tab2 = st.tabs(["📷 Kamera ile Tara", "🔤 Barkod / İsim Yaz"])

with tab1:
    st.markdown("**🎥 Kamera ile barkodu tarayın**")
    zxing_barcode_scanner()
    st.markdown("---")
    st.markdown("**Sonuç:**")
    taranan = st.text_input("📱 Okunan barkod", placeholder="...", label_visibility="collapsed")
    
    if taranan and taranan.strip():
        if taranan.strip() != st.session_state.son_barkod:
            st.session_state.son_barkod = taranan.strip()
            st.session_state.talep_gonderildi = False
            st.session_state.arama_modu = "kamera"
            sonuc = urun_bul_barkod(taranan.strip(), stok_df)
            st.session_state.bulunan_urunler = sonuc
            st.rerun()
    
    if st.session_state.arama_modu == "kamera":
        if st.session_state.bulunan_urunler is not None and len(st.session_state.bulunan_urunler) > 0:
            goster_sonuc(st.session_state.bulunan_urunler, "kamera")
        else:
            st.warning(f"⚠️ **{st.session_state.son_barkod}** barkodlu ürün bulunamadı.")
            if st.button("🔄 Yeniden Tara", use_container_width=True):
                st.session_state.son_barkod = ""
                st.session_state.arama_modu = None
                st.rerun()

with tab2:
    st.markdown("**🔍 Barkod numarası veya ürün adı girin:**")
    col1, col2 = st.columns([3, 1])
    with col1:
        giris = st.text_input("Arama", placeholder="Barkod no veya ürün adı...", label_visibility="collapsed")
    with col2:
        ara_btn = st.button("🔍 Ara", use_container_width=True, type="primary")
    
    if ara_btn and giris.strip():
        st.session_state.talep_gonderildi = False
        st.session_state.arama_modu = "manuel"
        sonuc = urun_bul_barkod(giris.strip(), stok_df)
        if sonuc is None or len(sonuc) == 0:
            sonuc = urun_ara_isim(giris.strip(), stok_df)
        st.session_state.bulunan_urunler = sonuc
        if sonuc is None or len(sonuc) == 0:
            st.error(f"❌ **'{giris.strip()}'** için ürün bulunamadı.")
    elif ara_btn:
        st.warning("⚠️ Lütfen bir şey girin.")
    
    if st.session_state.bulunan_urunler is not None and st.session_state.arama_modu == "manuel":
        st.markdown("---")
        goster_sonuc(st.session_state.bulunan_urunler, "manuel")

st.markdown("---")
st.markdown("<p style='text-align:center;color:#ccc;font-size:11px;'>🚀 KOCAMANLAR Stok & Fiyat Kontrol • v2.0 • ZXing.js</p>", unsafe_allow_html=True)
