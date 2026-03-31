# -*- coding: utf-8 -*-
import sys
from pathlib import Path
from runpy import run_path

BASE_DIR = Path(__file__).resolve().parent
APP_PATH = BASE_DIR / "stok-fiyat-app" / "app.py"

if not APP_PATH.exists():
    raise FileNotFoundError(f"Deploy entrypoint not found: {APP_PATH}")

# Ensure the stok-fiyat-app directory is imported first
sys.path.insert(0, str(APP_PATH.parent))
run_path(str(APP_PATH), run_name="__main__")



if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "current_user" not in st.session_state:
    st.session_state.current_user = ""

if "current_role" not in st.session_state:
    st.session_state.current_role = ""

if "pending_price_request" not in st.session_state:
    st.session_state.pending_price_request = None

if "price_warning" not in st.session_state:
    st.session_state.price_warning = False

if not st.session_state.authenticated:
    show_login_screen()
    st.stop()

users = load_users()

MENU_ITEMS = ["ANASAYFA"]
if st.session_state.current_role == "ADMIN":
    MENU_ITEMS.append("YÖNETİCİ PANELİ")

with st.sidebar:
    st.title("KONTROL PANELİ")
    st.markdown(f"**KULLANICI:** {st.session_state.current_user}")
    st.markdown(f"**ROL:** {st.session_state.current_role}")
    st.markdown("---")
    page = st.radio("MENÜ", MENU_ITEMS)


def display_admin_panel():
    st.markdown("## YÖNETİCİ PANELİ")
    st.markdown("---")

    log_df = load_dataframe(LOG_DOSYASI)
    if not log_df.empty:
        log_df.columns = [c.strip() for c in log_df.columns]
        log_df["Kullanici"] = log_df["Kullanici"].astype(str).str.upper()
        st.subheader("SORGULAMA ÖZETİ")
        summary = log_df.groupby("Kullanici").size().reset_index(name="Sorgulama_Sayisi")
        st.table(summary.sort_values(by="Sorgulama_Sayisi", ascending=False))
    else:
        st.info("HENÜZ HERHANGİ BİR SORGULAMA KAYDI YOK.")

    st.subheader("TALEPLER")
    talepler_df = load_dataframe(TALEPLER_DOSYASI)
    if not talepler_df.empty:
        talepler_df.columns = [c.strip() for c in talepler_df.columns]
        if "Tarih" in talepler_df.columns:
            talepler_df["Tarih"] = pd.to_datetime(talepler_df["Tarih"], errors="coerce")
            talepler_df = talepler_df.sort_values(by="Tarih", ascending=False)
        st.dataframe(talepler_df)
    else:
        st.info("TALEP KAYDI BULUNAMADI.")

    st.markdown("---")
    st.subheader("YENİ KULLANICI EKLE")
    with st.form("new_user_form", clear_on_submit=True):
        yeni_username = st.text_input("KULLANICI ADI", placeholder="YENİ KULLANICI ADI")
        yeni_password = st.text_input("ŞİFRE", type="password", placeholder="YENİ ŞİFRE")
        yeni_role = st.selectbox("ROL", ["ADMIN", "USER"])
        submit_user = st.form_submit_button("KULLANICI OLUŞTUR")
        if submit_user:
            if not yeni_username.strip() or not yeni_password.strip():
                st.error("KULLANICI ADI VE ŞİFRE BOŞ BIRAKILAMAZ.")
            elif save_user(yeni_username, yeni_password, yeni_role):
                st.success("YENİ KULLANICI KAYDEDİLDİ.")
                rerun_app()
            else:
                st.warning("BU KULLANICI ZATEN MEVCUT.")

    col1, col2 = st.columns(2)
    if col1.button("LOGLARI SIFIRLA"):
        ensure_csv(LOG_DOSYASI, CSV_HEADERS["loglar"])
        st.success("LOG KAYITLARI TEMİZLENDİ.")
        rerun_app()
    if col2.button("TALEPLERI SIFIRLA"):
        ensure_csv(TALEPLER_DOSYASI, CSV_HEADERS["talepler"])
        st.success("TALEP KAYITLARI TEMİZLENDİ.")
        rerun_app()


def display_main_panel():
    st.markdown("## STOK VE FIYAT KONTROL")
    st.caption(f"{len(stok_df):,} ÜRÜN YUKLENDI")
    st.markdown("---")

    tab1, tab2 = st.tabs(["📷 KAMERA ILE TARA", "🔤 BARKOD / ISIM GIRIS"])

    with tab1:
        from barcode_scanner import barcode_scanner

        kamera_modu = "result" if st.session_state.son_barkod else "scanning"
        taranan = barcode_scanner(mode=kamera_modu, key="kamera_tarayici")

        if taranan is None and st.session_state.son_barkod:
            st.session_state.bulunan_urunler = None
            st.session_state.talep_gonderildi = False
            st.session_state.son_barkod = ""
            st.session_state.arama_modu = None
            rerun_app()

        if taranan and taranan != st.session_state.son_barkod:
            st.session_state.son_barkod = taranan
            st.session_state.talep_gonderildi = False
            st.session_state.arama_modu = "kamera"
            sonuc = urun_bul_barkod(taranan, stok_df)
            st.session_state.bulunan_urunler = sonuc
            urun_adi = sonuc.iloc[0]["adi"] if sonuc is not None and len(sonuc) > 0 else ""
            log_kaydet(st.session_state.current_user, taranan, urun_adi)
            rerun_app()

        if st.session_state.arama_modu == "kamera":
            st.markdown("---")
            if st.session_state.bulunan_urunler is not None:
                goster_sonuc(st.session_state.bulunan_urunler, "kamera")
            else:
                st.warning(f"{st.session_state.son_barkod} BARKODLU URUN LISTEDE YOK.")
                if st.button("YENIDEN TARA", use_container_width=True):
                    st.session_state.son_barkod = ""
                    st.session_state.arama_modu = None
                    rerun_app()

    with tab2:
        st.markdown("**BARKOD NUMARASI VEYA URUN ADI GIRIN:**")
        col1, col2 = st.columns([3, 1])
        with col1:
            giris = st.text_input("ARAMA", placeholder="BARKOD NO VEYA URUN ADI...")
        with col2:
            ara_btn = st.button("ARA", use_container_width=True, type="primary")

        if ara_btn and giris.strip():
            st.session_state.talep_gonderildi = False
            st.session_state.arama_modu = "manuel"
            sonuc = urun_bul_barkod(giris.strip(), stok_df)
            if sonuc is None:
                sonuc = urun_ara_isim(giris.strip(), stok_df)
            st.session_state.bulunan_urunler = sonuc
            urun_adi = ""
            if sonuc is not None and len(sonuc) > 0:
                urun_adi = sonuc.iloc[0]["adi"]
            log_kaydet(st.session_state.current_user, giris.strip(), urun_adi)
            if sonuc is None:
                st.error(f"GIRISINIZ ICIN URUN BULUNAMADI: {giris.strip()}")
        elif ara_btn:
            st.warning("LUTFEN BIR DEGER GIRIN.")

        if st.session_state.bulunan_urunler is not None and st.session_state.arama_modu == "manuel":
            st.markdown("---")
            goster_sonuc(st.session_state.bulunan_urunler, "manuel")

    if st.session_state.price_warning and st.session_state.pending_price_request:
        st.warning(
            "GIRDIGINIZ FIYAT MEVCUT FIYATTAN COK FARKLI, EMIN MISINIZ?"
        )
        col1, col2 = st.columns(2)
        if col1.button("EVET, KAYDET"):
            pending = st.session_state.pending_price_request
            talep_kaydet(
                pending["barkod"],
                pending["urun_adi"],
                pending["mevcut_fiyat"],
                pending["yeni_fiyat"],
                pending["etiket_gerekli"],
                pending["not_metni"],
                st.session_state.current_user,
            )
            st.session_state.talep_gonderildi = True
            st.session_state.pending_price_request = None
            st.session_state.price_warning = False
            st.success("TALEP ONAYLANDI VE KAYDEDILDI.")
            rerun_app()
        if col2.button("VAZGEÇ"):
            st.session_state.pending_price_request = None
            st.session_state.price_warning = False
            st.info("TALEP IPTAL EDILDI.")


def goster_sonuc(df_sonuc, prefix=""):
    if df_sonuc is None or len(df_sonuc) == 0:
        return
    if len(df_sonuc) == 1:
        urun_goster_ve_form(df_sonuc.iloc[0])
        return
    st.info(f"{len(df_sonuc)} URUN BULUNDU — BIRINI SECIN:")
    secenekler = [
        f"{row['adi'].upper()} — {float(row['fiyat']):.2f} TL"
        for _, row in df_sonuc.iterrows()
    ]
    secim = st.selectbox("URUN:", secenekler, key=f"secim_{prefix}")
    idx = secenekler.index(secim)
    urun_goster_ve_form(df_sonuc.iloc[idx])


def urun_goster_ve_form(urun_row):
    st.markdown(
        f"""
        <div style="background:#f8fbff;border-radius:14px;padding:24px;
                    text-align:center;margin-bottom:18px;border:1px solid #c8d9ff;">
            <p style="font-size:12px;color:#556;letter-spacing:1px;margin:0;">ÜRÜN ADI</p>
            <h2 style="font-size:26px;color:#1a1a2e;margin:8px 0;">{to_upper(urun_row['adi'])}</h2>
            <p style="font-size:12px;color:#556;letter-spacing:1px;margin:0;">MEVCUT FIYAT</p>
            <h1 style="font-size:46px;color:#d32f2f;margin:8px 0;font-weight:700;">{float(urun_row['fiyat']):.2f} ₺</h1>
            <p style="font-size:12px;color:#777;margin:0;">BARKOD: {to_upper(urun_row['barkod'])}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not st.session_state.talep_gonderildi:
        form_key = f"talep_formu_{to_upper(urun_row['barkod'])}"
        with st.form(form_key, clear_on_submit=False):
            yeni_fiyat = st.number_input(
                "YENI FIYAT TALEBI (₺)",
                min_value=0.01,
                max_value=999999.99,
                value=float(urun_row["fiyat"]),
                step=0.25,
                format="%.2f",
            )
            etiket_gerekli = st.checkbox("ETIKET GEREKLI MI?")
            not_metni = st.text_area(
                "NOT (ISTEGE BAGLI)", placeholder="ACIKLAMA...", max_chars=500
            )
            submitted = st.form_submit_button("TALEBI GONDER", use_container_width=True, type="primary")
            if submitted:
                mevcut_fiyat = float(urun_row["fiyat"])
                if yeni_fiyat <= 0:
                    st.error("YENI FIYAT SIFIRDAN BUYUK OLMALIDIR.")
                else:
                    fark = abs(yeni_fiyat - mevcut_fiyat) / max(mevcut_fiyat, 0.01)
                    if fark >= 0.5:
                        st.session_state.pending_price_request = {
                            "barkod": to_upper(urun_row["barkod"]),
                            "urun_adi": to_upper(urun_row["adi"]),
                            "mevcut_fiyat": mevcut_fiyat,
                            "yeni_fiyat": yeni_fiyat,
                            "etiket_gerekli": etiket_gerekli,
                            "not_metni": not_metni,
                        }
                        st.session_state.price_warning = True
                        st.info("UYARI: FIYAT FARKI %50'DEN FAZLA. ONAY ICIN ALTTAKI BUTONA BASIN.")
                    else:
                        talep_kaydet(
                            to_upper(urun_row["barkod"]),
                            to_upper(urun_row["adi"]),
                            mevcut_fiyat,
                            yeni_fiyat,
                            etiket_gerekli,
                            not_metni,
                            st.session_state.current_user,
                        )
                        st.session_state.talep_gonderildi = True
                        st.success("TALEP KAYDEDILDI.")
    else:
        st.success("TALEBINIZ KAYDEDILDI.")
        if st.button("YENI SORGULAMA", use_container_width=True, type="primary"):
            st.session_state.bulunan_urunler = None
            st.session_state.talep_gonderildi = False
            st.session_state.son_barkod = ""
            st.session_state.arama_modu = None
            rerun_app()


@st.cache_data(ttl=60)
def stok_yukle():
    try:
        df = pd.read_csv(STOK_DOSYASI, dtype={"barkod": str}, encoding="utf-8")
        df.columns = [c.strip().lower() for c in df.columns]
        return df
    except Exception:
        return pd.DataFrame(columns=["barkod", "adi", "fiyat"])


if "bulunan_urunler" not in st.session_state:
    st.session_state.bulunan_urunler = None
if "talep_gonderildi" not in st.session_state:
    st.session_state.talep_gonderildi = False
if "arama_modu" not in st.session_state:
    st.session_state.arama_modu = None
if "son_barkod" not in st.session_state:
    st.session_state.son_barkod = ""

stok_df = stok_yukle()

if page == "YÖNETİCİ PANELİ":
    display_admin_panel()
else:
    display_main_panel()

st.markdown("---")
st.markdown(
    "<p style='text-align:center;color:#999;font-size:11px;'>STOK & FIYAT KONTROL • UTF-8</p>",
    unsafe_allow_html=True,
)
