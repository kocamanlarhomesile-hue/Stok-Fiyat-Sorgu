# -*- coding: utf-8 -*-
import csv
from datetime import datetime
from pathlib import Path

import re
import difflib

import altair as alt
import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
STOK_DOSYASI_HOME = BASE_DIR / "stok_listesi_home.csv"
STOK_DOSYASI_MARKET = BASE_DIR / "stok_listesi_market.csv"
STOK_DOSYASI_LEGACY = BASE_DIR / "stok_listesi.csv"
USERS_DOSYASI = BASE_DIR.parent / "users.csv"
LOG_DOSYASI = BASE_DIR.parent / "loglar.csv"
TALEPLER_DOSYASI = BASE_DIR.parent / "talepler.csv"

ISLETME_OPTIONS = {
    "HOME": "KOCAMANLAR HOME",
    "MARKET": "KOCAMANLAR MARKET",
}
DEFAULT_ISLETME = "HOME"
ALL_ISLETMELER = ",".join(ISLETME_OPTIONS.keys())

st.set_page_config(
    page_title="STOK VE FIYAT KONTROL",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

CSV_HEADERS = {
    "users": ["username", "password", "role", "isletme"],
    "loglar": ["Tarih_Saat", "Kullanici", "Sorgulanan_Barkod", "Urun_Adi", "Isletme"],
    "talepler": ["Tarih", "Kullanici", "Barkod", "Urun_Adi", "Eski_Fiyat", "Yeni_Fiyat_Talebi", "Etiket_Talebi", "Not", "Isletme"]
}


TURKISH_CHAR_MAP = str.maketrans({
    "İ": "I",
    "I": "I",
    "ı": "I",
    "Ş": "S",
    "ş": "S",
    "Ğ": "G",
    "ğ": "G",
    "Ü": "U",
    "ü": "U",
    "Ö": "O",
    "ö": "O",
    "Ç": "C",
    "ç": "C",
})


def to_upper(value):
    return str(value).strip().upper() if value is not None else ""


def normalize_text(value):
    text = str(value or "").strip().upper()
    text = text.translate(TURKISH_CHAR_MAP)
    text = re.sub(r"[^A-Z0-9ÇŞĞÜÖıIÜĞŞÇ ]", "", text)
    return text


def smart_search_product(query: str, df: pd.DataFrame):
    if df is None or df.empty or not str(query).strip():
        return None
    query = str(query).strip()
    normalized_query = normalize_text(query)
    df = df.copy()
    df["barkod"] = df["barkod"].astype(str).str.strip()
    df["adi"] = df["adi"].astype(str).str.strip()
    df["norm_adi"] = df["adi"].apply(normalize_text)
    df["norm_barkod"] = df["barkod"].astype(str).apply(normalize_text)

    exact_barcode = df[df["barkod"] == query]
    if len(exact_barcode) > 0:
        return exact_barcode

    exact_norm_barkod = df[df["norm_barkod"] == normalize_text(query)]
    if len(exact_norm_barkod) > 0:
        return exact_norm_barkod

    if normalized_query:
        substring_name = df[df["norm_adi"].str.contains(normalized_query, na=False)]
        if len(substring_name) > 0:
            return substring_name

    ratios = []
    for _, row in df.iterrows():
        name_ratio = difflib.SequenceMatcher(None, normalized_query, row["norm_adi"]).ratio()
        barcode_ratio = difflib.SequenceMatcher(None, normalize_text(row["barkod"]), normalized_query).ratio()
        ratios.append(max(name_ratio, barcode_ratio))
    df["match_score"] = ratios
    best = df[df["match_score"] >= 0.55].sort_values(by="match_score", ascending=False)
    return best.head(1) if len(best) > 0 else None


def ensure_csv(path: Path, headers, default_values=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.stat().st_size == 0:
        with path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
        return

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        existing_headers = next(reader, [])
        existing_headers = [c.strip() for c in existing_headers]

    if existing_headers == headers:
        return

    missing_headers = [header for header in headers if header not in existing_headers]
    if not missing_headers:
        return

    try:
        df = pd.read_csv(path, dtype=str, encoding="utf-8-sig").fillna("")
        for header in missing_headers:
            df[header] = default_values.get(header, "") if default_values else ""
        df = df.reindex(columns=headers, fill_value="")
        with path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            df.to_csv(f, index=False, header=False)
    except Exception:
        return


def append_csv(path: Path, row, headers):
    ensure_csv(path, headers)
    with path.open("a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(row)


def rerun_app():
    if hasattr(st, "experimental_rerun"):
        st.experimental_rerun()
    else:
        st.stop()


def normalize_isletme(value):
    if value is None:
        return ALL_ISLETMELER
    text = str(value).strip().upper()
    if text in ISLETME_OPTIONS:
        return text
    if text in ["HER IKISI", "HER IKI", "ALL", "HOME,MARKET", "MARKET,HOME"]:
        return ALL_ISLETMELER
    if "HOME" in text and "MARKET" in text:
        return ALL_ISLETMELER
    if "HOME" in text:
        return "HOME"
    if "MARKET" in text:
        return "MARKET"
    return ALL_ISLETMELER


def parse_isletme_list(value):
    value = normalize_isletme(value)
    return [item.strip() for item in value.split(",") if item.strip()]


def user_has_access(user_isletme, selected_isletme):
    return selected_isletme in parse_isletme_list(user_isletme)


def isletme_label(value):
    values = parse_isletme_list(value)
    return " + ".join(ISLETME_OPTIONS.get(item, item) for item in values)


def get_stock_file(isletme):
    isletme = normalize_isletme(isletme)
    if isletme == "MARKET":
        return STOK_DOSYASI_MARKET if STOK_DOSYASI_MARKET.exists() else STOK_DOSYASI_LEGACY
    if isletme == "HOME":
        return STOK_DOSYASI_HOME if STOK_DOSYASI_HOME.exists() else STOK_DOSYASI_LEGACY
    return STOK_DOSYASI_HOME if STOK_DOSYASI_HOME.exists() else STOK_DOSYASI_LEGACY


def load_users():
    ensure_csv(USERS_DOSYASI, CSV_HEADERS["users"], {"isletme": ALL_ISLETMELER})
    users = pd.read_csv(USERS_DOSYASI, dtype=str, encoding="utf-8-sig").fillna("")
    users.columns = [c.strip().lower() for c in users.columns]
    users["username"] = users["username"].astype(str).str.strip().str.upper()
    users["password"] = users["password"].astype(str).str.strip().str.upper()
    users["role"] = users["role"].astype(str).str.strip().str.upper()
    if "isletme" not in users.columns:
        users["isletme"] = ALL_ISLETMELER
    users["isletme"] = users["isletme"].astype(str).fillna(ALL_ISLETMELER).apply(normalize_isletme)

    if not ((users["username"] == "ADMIN") & (users["role"] == "ADMIN")).any():
        append_csv(USERS_DOSYASI, ["ADMIN", "ADMIN", "ADMIN", ALL_ISLETMELER], CSV_HEADERS["users"])
        users = pd.read_csv(USERS_DOSYASI, dtype=str, encoding="utf-8-sig").fillna("")
        users.columns = [c.strip().lower() for c in users.columns]
        users["username"] = users["username"].astype(str).str.strip().str.upper()
        users["password"] = users["password"].astype(str).str.strip().str.upper()
        users["role"] = users["role"].astype(str).str.strip().str.upper()
        if "isletme" not in users.columns:
            users["isletme"] = ALL_ISLETMELER
        users["isletme"] = users["isletme"].astype(str).fillna(ALL_ISLETMELER).apply(normalize_isletme)

    return users


def validate_user(username: str, password: str):
    users = load_users()
    username = to_upper(username)
    password = to_upper(password)
    matched = users[(users["username"] == username) & (users["password"] == password)]
    if len(matched) == 0:
        return None
    return matched.iloc[0].to_dict()


def save_user(username: str, password: str, role: str, isletme: str = ALL_ISLETMELER):
    username = to_upper(username)
    password = to_upper(password)
    role = to_upper(role)
    isletme = normalize_isletme(isletme)
    users = load_users()
    if (users["username"] == username).any():
        return False
    append_csv(USERS_DOSYASI, [username, password, role, isletme], CSV_HEADERS["users"])
    return True


def write_users(users_df: pd.DataFrame):
    users_df = users_df.copy()
    users_df.columns = [c.strip().lower() for c in users_df.columns]
    users_df["username"] = users_df["username"].astype(str).str.strip().str.upper()
    users_df["password"] = users_df["password"].astype(str).str.strip().str.upper()
    users_df["role"] = users_df["role"].astype(str).str.strip().str.upper()
    users_df["isletme"] = users_df.get("isletme", pd.Series(ALL_ISLETMELER, index=users_df.index)).astype(str).fillna(ALL_ISLETMELER).apply(normalize_isletme)
    ensure_csv(USERS_DOSYASI, CSV_HEADERS["users"], {"isletme": ALL_ISLETMELER})
    users_df.to_csv(USERS_DOSYASI, index=False, encoding="utf-8-sig")


def delete_user(username: str):
    username = to_upper(username)
    if username == "ADMIN":
        return False
    users = load_users()
    users = users[users["username"] != username]
    write_users(users)
    return True


def update_user_password(username: str, new_password: str):
    username = to_upper(username)
    new_password = to_upper(new_password)
    users = load_users()
    match = users[users["username"] == username]
    if len(match) == 0:
        return False
    users.loc[users["username"] == username, "password"] = new_password
    write_users(users)
    return True


def update_user_isletme(username: str, isletme: str):
    username = to_upper(username)
    isletme = normalize_isletme(isletme)
    users = load_users()
    if not (users["username"] == username).any():
        return False
    users.loc[users["username"] == username, "isletme"] = isletme
    write_users(users)
    return True


def ensure_logs():
    ensure_csv(LOG_DOSYASI, CSV_HEADERS["loglar"], {"Isletme": ALL_ISLETMELER})


def log_kaydet(kullanici: str, barkod: str, urun_adi: str):
    ensure_logs()
    simdi = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    isletme = st.session_state.get("current_isletme", DEFAULT_ISLETME)
    append_csv(
        LOG_DOSYASI,
        [
            simdi,
            to_upper(kullanici),
            to_upper(barkod),
            to_upper(urun_adi),
            isletme,
        ],
        CSV_HEADERS["loglar"]
    )


def ensure_talepler():
    ensure_csv(TALEPLER_DOSYASI, CSV_HEADERS["talepler"], {"Isletme": ALL_ISLETMELER})


def talep_kaydet(barkod, urun_adi, mevcut_fiyat, yeni_fiyat, etiket_gerekli, not_metni, kullanici):
    ensure_talepler()
    isletme = st.session_state.get("current_isletme", DEFAULT_ISLETME)
    append_csv(
        TALEPLER_DOSYASI,
        [
            datetime.now().strftime("%Y-%m-%d"),
            to_upper(kullanici),
            to_upper(barkod),
            to_upper(urun_adi),
            f"{mevcut_fiyat:.2f}",
            f"{yeni_fiyat:.2f}",
            "EVET" if etiket_gerekli else "HAYIR",
            to_upper(not_metni),
            isletme,
        ],
        CSV_HEADERS["talepler"]
    )


def load_dataframe(path: Path, encoding="utf-8-sig"):
    if not path.exists():
        return pd.DataFrame()
    try:
        df = pd.read_csv(path, dtype=str, encoding=encoding).fillna("")
        return df
    except Exception:
        return pd.DataFrame()


def load_stock_csv(path: Path):
    if not path.exists():
        return pd.DataFrame(columns=["barkod", "adi", "fiyat"])
    try:
        df = pd.read_csv(path, dtype=str, encoding="utf-8-sig").fillna("")
    except Exception:
        try:
            df = pd.read_csv(path, dtype=str, encoding="utf-8").fillna("")
        except Exception:
            return pd.DataFrame(columns=["barkod", "adi", "fiyat"])
    df.columns = [c.strip().lower() for c in df.columns]
    if not {"barkod", "adi", "fiyat"}.issubset(set(df.columns)):
        return pd.DataFrame(columns=["barkod", "adi", "fiyat"])
    df = df[["barkod", "adi", "fiyat"]].copy()
    df["barkod"] = df["barkod"].astype(str).str.strip()
    df["adi"] = df["adi"].astype(str).str.strip()
    df["fiyat"] = pd.to_numeric(df["fiyat"].astype(str).str.replace(",", "."), errors="coerce")
    return df


def preprocess_uploaded_stock(uploaded_file):
    try:
        df = pd.read_csv(uploaded_file, dtype=str, encoding="utf-8-sig").fillna("")
    except Exception:
        try:
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, dtype=str, encoding="utf-8").fillna("")
        except Exception:
            return None, "CSV DOSYASI OKUNAMADI."
    df.columns = [c.strip().lower() for c in df.columns]
    missing_columns = [col for col in ["barkod", "adi", "fiyat"] if col not in df.columns]
    if missing_columns:
        return None, f"CSV DOSYASINDA EKSİK SÜTUNLAR: {', '.join([col.upper() for col in missing_columns])}."
    df = df[["barkod", "adi", "fiyat"]].copy()
    df["barkod"] = df["barkod"].astype(str).str.strip()
    df["adi"] = df["adi"].astype(str).str.strip()
    df["fiyat"] = pd.to_numeric(df["fiyat"].astype(str).str.replace(",", "."), errors="coerce")
    return df, None


def count_invalid_stock_rows(df: pd.DataFrame):
    if df is None or df.empty:
        return 0
    invalid = df["fiyat"].isna() | (df["fiyat"] <= 0)
    return int(invalid.sum())


def analyze_stock_update(old_df: pd.DataFrame, new_df: pd.DataFrame):
    old_df = old_df.copy()
    new_df = new_df.copy()
    for frame in [old_df, new_df]:
        frame["barkod"] = frame["barkod"].astype(str).str.strip()
    old_prices = old_df[["barkod", "adi", "fiyat"]].drop_duplicates(subset=["barkod"])
    new_prices = new_df[["barkod", "adi", "fiyat"]].drop_duplicates(subset=["barkod"])
    merged = old_prices.merge(new_prices, on="barkod", how="inner", suffixes=("_old", "_new"))
    merged["fiyat_old"] = pd.to_numeric(merged["fiyat_old"], errors="coerce")
    merged["fiyat_new"] = pd.to_numeric(merged["fiyat_new"], errors="coerce")
    changed = merged[merged["fiyat_old"] != merged["fiyat_new"]].copy()
    changed_count = len(changed)
    if not changed.empty:
        changed["pct_fark"] = 0.0
        nonzero = changed["fiyat_old"] != 0
        changed.loc[nonzero, "pct_fark"] = (
            (changed.loc[nonzero, "fiyat_new"] - changed.loc[nonzero, "fiyat_old"]).abs()
            / changed.loc[nonzero, "fiyat_old"].abs()
            * 100
        )
        changed.loc[~nonzero, "pct_fark"] = 100.0
        suspicious = changed[changed["pct_fark"] > 50.0].copy()
    else:
        suspicious = changed.copy()
    suspicious = suspicious.sort_values(by="pct_fark", ascending=False)
    suspicious = suspicious.rename(columns={
        "adi_new": "adi",
        "fiyat_old": "eski_fiyat",
        "fiyat_new": "yeni_fiyat",
        "pct_fark": "fark_yuzde",
    })
    added_count = int(len(new_prices[~new_prices["barkod"].isin(old_prices["barkod"])]) if not new_prices.empty else 0)
    removed_count = int(len(old_prices[~old_prices["barkod"].isin(new_prices["barkod"])]) if not old_prices.empty else 0)
    return {
        "total": int(len(new_df)),
        "changed_count": int(changed_count),
        "suspicious_df": suspicious[["barkod", "adi", "eski_fiyat", "yeni_fiyat", "fark_yuzde"]] if not suspicious.empty else pd.DataFrame(columns=["barkod", "adi", "eski_fiyat", "yeni_fiyat", "fark_yuzde"]),
        "added_count": added_count,
        "removed_count": removed_count,
    }


def backup_stock_file(path: Path):
    backup_path = BASE_DIR / "yedek_stok.csv"
    if path.exists():
        backup_path.write_bytes(path.read_bytes())
    return backup_path


def clear_stock_cache():
    try:
        st.cache_data.clear()
    except Exception:
        pass


def save_stock_csv(path: Path, df: pd.DataFrame):
    if df is None:
        return
    df = df.copy()
    df = df[["barkod", "adi", "fiyat"]]
    df.to_csv(path, index=False, encoding="utf-8-sig")
    clear_stock_cache()


@st.cache_data(ttl=300)
def load_stock_csv_cached(path_str: str):
    return load_stock_csv(Path(path_str))


def build_wildcard_pattern(query: str) -> str:
    query = str(query or "").strip().upper()
    query = query.translate(TURKISH_CHAR_MAP)
    escaped = re.escape(query)
    return escaped.replace(r"\*", ".*")


def query_stock_candidates(path: Path, query: str):
    if not str(query).strip():
        return pd.DataFrame()
    df = load_stock_csv_cached(str(path))
    if df.empty:
        return pd.DataFrame()
    query_text = str(query).strip()
    exact = df[df["barkod"].astype(str).str.strip() == query_text]
    if len(exact) > 0:
        return exact

    raw_query = str(query_text)
    candidates = df.copy()
    candidates["norm_adi"] = candidates["adi"].astype(str).apply(normalize_text)
    normalized_query = normalize_text(raw_query)

    if "*" in raw_query:
        pattern = build_wildcard_pattern(raw_query)
        regex_matches = candidates[candidates["norm_adi"].astype(str).str.contains(pattern, regex=True, na=False)]
        if len(regex_matches) > 0:
            return regex_matches.drop(columns=["norm_adi"])

    substring_matches = candidates[candidates["norm_adi"].str.contains(normalized_query, na=False)]
    if len(substring_matches) > 0:
        return substring_matches.drop(columns=["norm_adi"])

    ratios = []
    for _, row in candidates.iterrows():
        ratios.append(difflib.SequenceMatcher(None, normalized_query, row["norm_adi"]).ratio())
    candidates["match_score"] = ratios
    best = candidates[candidates["match_score"] >= 0.40].sort_values(by="match_score", ascending=False)
    if len(best) > 0:
        return best.drop(columns=["norm_adi", "match_score"])
    return pd.DataFrame()


def find_stock_item(path: Path, query: str):
    result = query_stock_candidates(path, query)
    return result if isinstance(result, pd.DataFrame) and len(result) > 0 else None


def update_single_stock_product(path: Path, barkod: str, yeni_adi: str, yeni_fiyat):
    if not str(barkod).strip():
        return False
    df = load_stock_csv(path)
    if df.empty:
        return False
    matched = df[df["barkod"].astype(str).str.strip() == str(barkod).strip()]
    if matched.empty:
        return False
    idx = matched.index[0]
    if str(yeni_adi).strip():
        df.at[idx, "adi"] = to_upper(yeni_adi)
    if yeni_fiyat is not None and float(yeni_fiyat) > 0:
        df.at[idx, "fiyat"] = float(yeni_fiyat)
    backup_stock_file(path)
    save_stock_csv(path, df)
    try:
        st.cache_data.clear()
    except Exception:
        pass
    return True


def urun_bul_barkod(barkod: str, df: pd.DataFrame):
    barkod = str(barkod).strip()
    if not barkod or df is None or df.empty:
        return None
    sonuc = smart_search_product(barkod, df)
    return sonuc if isinstance(sonuc, pd.DataFrame) and len(sonuc) > 0 else None


def urun_ara_isim(arama: str, df: pd.DataFrame):
    if not str(arama).strip() or df is None or df.empty:
        return None
    normalized_query = normalize_text(arama)
    df = df.copy()
    df["norm_adi"] = df["adi"].astype(str).apply(normalize_text)
    exact = df[df["norm_adi"].str.contains(normalized_query, na=False)]
    if len(exact) > 0:
        return exact
    sonuc = smart_search_product(arama, df)
    return sonuc if isinstance(sonuc, pd.DataFrame) and len(sonuc) > 0 else None


def show_login_screen():
    st.markdown(
        "<style>body{overflow-x:hidden;} .block-container{padding-top:2rem;}</style>",
        unsafe_allow_html=True,
    )
    st.markdown("## 🔐 GİRİŞ EKRANI")
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form", clear_on_submit=True):
            username = st.text_input("KULLANICI ADI", placeholder="KULLANICI ADI", label_visibility="visible")
            password = st.text_input("ŞİFRE", type="password", placeholder="ŞİFRE", label_visibility="visible")
            isletme_choice = st.selectbox(
                "ÇALIŞILACAK İŞLETME",
                [ISLETME_OPTIONS["HOME"], ISLETME_OPTIONS["MARKET"]],
                index=0,
            )
            submitted = st.form_submit_button("GİRİŞ YAP", use_container_width=True, type="primary")
            if submitted:
                selected_isletme = "HOME" if isletme_choice == ISLETME_OPTIONS["HOME"] else "MARKET"
                result = validate_user(username, password)
                if result:
                    if not user_has_access(result.get("isletme", ALL_ISLETMELER), selected_isletme):
                        allowed = [ISLETME_OPTIONS[item] for item in parse_isletme_list(result.get("isletme", ALL_ISLETMELER))]
                        st.error(
                            f"BU ALANA ERİŞİM YETKİNİZ YOK. YETKİLİ OLDUĞU İŞLETMELER: {', '.join(allowed)}"
                        )
                    else:
                        st.session_state.authenticated = True
                        st.session_state.current_user = result["username"]
                        st.session_state.current_role = result["role"]
                        st.session_state.current_isletme = selected_isletme
                        st.success("GİRİŞ BAŞARILI. HOŞGELDİNİZ {}".format(result["username"]))
                        rerun_app()
                else:
                    st.error("KULLANICI ADI VEYA ŞİFRE HATALI.")


if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "current_user" not in st.session_state:
    st.session_state.current_user = ""

if "current_role" not in st.session_state:
    st.session_state.current_role = ""

if "current_isletme" not in st.session_state:
    st.session_state.current_isletme = DEFAULT_ISLETME

if "pending_price_request" not in st.session_state:
    st.session_state.pending_price_request = None

if "price_warning" not in st.session_state:
    st.session_state.price_warning = False

if "single_edit_query" not in st.session_state:
    st.session_state.single_edit_query = ""
if "single_edit_selected" not in st.session_state:
    st.session_state.single_edit_selected = ""
if "single_edit_choice" not in st.session_state:
    st.session_state.single_edit_choice = 0
if "single_edit_camera_mode" not in st.session_state:
    st.session_state.single_edit_camera_mode = False

if not st.session_state.authenticated:
    show_login_screen()
    st.stop()

users = load_users()

MENU_ITEMS = ["ANASAYFA"]
if st.session_state.current_role == "ADMIN":
    MENU_ITEMS.extend(["YÖNETİCİ PANELİ", "TEK ÜRÜN DÜZENLE"])

with st.sidebar:
    st.title("KONTROL PANELİ")
    st.markdown(f"**KULLANICI:** {st.session_state.current_user}")
    st.markdown(f"**ROL:** {st.session_state.current_role}")
    st.markdown(f"**İŞLETME:** {isletme_label(st.session_state.current_isletme)}")
    st.markdown("---")
    page = st.radio("MENÜ", MENU_ITEMS)
    if st.button("ÇIKIŞ YAP"):
        st.session_state.authenticated = False
        st.session_state.current_user = ""
        st.session_state.current_role = ""
        st.session_state.current_isletme = DEFAULT_ISLETME
        rerun_app()


def display_admin_panel():
    st.markdown("## YÖNETİCİ PANELİ")
    st.markdown("---")

    filter_options = ["TÜM İŞLETMELER"] + [ISLETME_OPTIONS[k] for k in ISLETME_OPTIONS]
    isletme_filter_choice = st.selectbox("İŞLETMEYE GÖRE FİLTRELE", filter_options, index=0)
    selected_filter = None
    if isletme_filter_choice != "TÜM İŞLETMELER":
        selected_filter = "HOME" if isletme_filter_choice == ISLETME_OPTIONS["HOME"] else "MARKET"

    log_df = load_dataframe(LOG_DOSYASI)
    if not log_df.empty:
        log_df.columns = [c.strip() for c in log_df.columns]
        if "Isletme" not in log_df.columns:
            log_df["Isletme"] = ALL_ISLETMELER
        log_df["Isletme"] = log_df["Isletme"].astype(str).fillna(ALL_ISLETMELER).apply(normalize_isletme)
        log_df["Kullanici"] = log_df["Kullanici"].astype(str).str.upper()
        if selected_filter is not None:
            log_df = log_df[log_df["Isletme"].astype(str).apply(lambda v: selected_filter in parse_isletme_list(v))]

        if not log_df.empty:
            if "Sorgulanan_Barkod" in log_df.columns:
                log_df["Sorgulanan_Barkod"] = log_df["Sorgulanan_Barkod"].astype(str).str.upper()
            else:
                log_df["Sorgulanan_Barkod"] = ""
            if "Urun_Adi" not in log_df.columns:
                log_df["Urun_Adi"] = log_df["Sorgulanan_Barkod"].astype(str).str.upper()
            else:
                log_df["Urun_Adi"] = log_df["Urun_Adi"].astype(str).str.upper()
                log_df["Urun_Adi"] = log_df["Urun_Adi"].mask(log_df["Urun_Adi"] == "", log_df["Sorgulanan_Barkod"])
            st.subheader("EN ÇOK SORGULANAN 10 ÜRÜN")
            product_counts = (
                log_df.groupby("Urun_Adi")
                .size()
                .reset_index(name="Sorgulama_Sayisi")
                .sort_values(by="Sorgulama_Sayisi", ascending=False)
            )
            if not product_counts.empty:
                top_products = product_counts.head(10).copy()
                top_products["Urun_Adi"] = top_products["Urun_Adi"].astype(str).str.upper()
                chart = alt.Chart(top_products).mark_bar(color="#1f77b4").encode(
                    x=alt.X("Sorgulama_Sayisi:Q", title="SORGULAMA SAYISI"),
                    y=alt.Y("Urun_Adi:N", sort=alt.SortField("Sorgulama_Sayisi", order="descending"), title="ÜRÜN"),
                    tooltip=["Urun_Adi", "Sorgulama_Sayisi"]
                ).properties(height=450)
                st.altair_chart(chart, use_container_width=True)
                st.table(top_products)
            st.markdown("---")
            st.subheader("PERSONEL AKTİVİTESİ")
            summary = log_df.groupby("Kullanici").size().reset_index(name="Sorgulama_Sayisi")
            summary["Kullanici"] = summary["Kullanici"].astype(str).str.upper()
            st.table(summary.sort_values(by="Sorgulama_Sayisi", ascending=False))
            st.markdown("**DETAYLI LOG KAYDI**")
            st.dataframe(log_df)
        else:
            st.info("Seçilen filtreye ait sorgulama kaydı bulunamadı.")
    else:
        st.info("HENÜZ HERHANGİ BİR SORGULAMA KAYDI YOK.")

    st.subheader("TALEPLER")
    talepler_df = load_dataframe(TALEPLER_DOSYASI)
    if not talepler_df.empty:
        talepler_df.columns = [c.strip() for c in talepler_df.columns]
        if "Isletme" not in talepler_df.columns:
            talepler_df["Isletme"] = ALL_ISLETMELER
        talepler_df["Isletme"] = talepler_df["Isletme"].astype(str).fillna(ALL_ISLETMELER).apply(normalize_isletme)
        if selected_filter is not None:
            talepler_df = talepler_df[talepler_df["Isletme"].astype(str).apply(lambda v: selected_filter in parse_isletme_list(v))]
        if "Tarih" in talepler_df.columns:
            talepler_df["Tarih"] = pd.to_datetime(talepler_df["Tarih"], errors="coerce")
            talepler_df = talepler_df.sort_values(by="Tarih", ascending=False)
        if not talepler_df.empty:
            st.dataframe(talepler_df)
        else:
            st.info("Seçilen filtreye ait talep kaydı bulunamadı.")
    else:
        st.info("TALEP KAYDI BULUNAMADI.")

    st.markdown("---")
    st.subheader("KULLANICI YÖNETİMİ")

    users_df = load_users()
    if not users_df.empty:
        users_df_display = users_df[["username", "role", "isletme"]].copy()
        users_df_display["isletme"] = users_df_display["isletme"].apply(isletme_label)
        users_df_display.columns = ["KULLANICI", "ROL", "ERİŞİM YETKİSİ"]
        st.dataframe(users_df_display.sort_values(by=["KULLANICI"]))
    else:
        st.info("SİSTEMDE KAYITLI PERSONEL YOK.")

    manage_username = st.selectbox(
        "DÜZENLENECEK PERSONEL",
        [""] + sorted(users_df["username"].astype(str).unique()),
        format_func=lambda value: value if value else "SEÇİNİZ"
    )
    if manage_username:
        mevcut_kullanici = users_df[users_df["username"] == manage_username].iloc[0]
        st.markdown(f"**SEÇİLEN PERSONEL:** {mevcut_kullanici['username']} — {mevcut_kullanici['role']} — {isletme_label(mevcut_kullanici['isletme'])}")
        with st.form("manage_user_form", clear_on_submit=True):
            yeni_sifre = st.text_input("YENİ ŞİFRE", type="password", placeholder="DEĞİŞTİRMEK İÇİN YAZIN")
            yeni_yetki = st.selectbox(
                "YENİ ERİŞİM YETKİSİ",
                [ISLETME_OPTIONS["HOME"], ISLETME_OPTIONS["MARKET"], "HER İKİSİ"],
                index=0 if mevcut_kullanici["isletme"] == "HOME" else 1 if mevcut_kullanici["isletme"] == "MARKET" else 2,
            )
            submit_manage = st.form_submit_button("GÜNCELLE")
            if submit_manage:
                if yeni_sifre.strip():
                    update_user_password(manage_username, yeni_sifre)
                if yeni_yetki == "HER İKİSİ":
                    selected_isletme = ALL_ISLETMELER
                elif yeni_yetki == ISLETME_OPTIONS["HOME"]:
                    selected_isletme = "HOME"
                else:
                    selected_isletme = "MARKET"
                update_user_isletme(manage_username, selected_isletme)
                st.success("PERSONEL BİLGİLERİ GÜNCELLENDİ.")
                rerun_app()

        if st.button("PERSONELİ SİL"):
            if manage_username == "ADMIN":
                st.error("ADMIN KAYDI SİLİNEMEZ.")
            elif delete_user(manage_username):
                st.success("PERSONEL SİLİNDİ.")
                rerun_app()
            else:
                st.error("PERSONEL SİLİNEMEDİ.")

    st.markdown("---")
    st.subheader("TEK ÜRÜN DÜZENLE")
    edit_isletme_choice = st.selectbox(
        "DÜZENLENECEK İŞLETME",
        [ISLETME_OPTIONS["HOME"], ISLETME_OPTIONS["MARKET"]],
        index=0,
        key="single_edit_isletme",
    )
    edit_stock_path = STOK_DOSYASI_HOME if edit_isletme_choice == ISLETME_OPTIONS["HOME"] else STOK_DOSYASI_MARKET
    with st.form("single_edit_search_form", clear_on_submit=False):
        search_value = st.text_input("BARKOD VEYA ÜRÜN ADI", placeholder="BARKOD VEYA ÜRÜN ADI GİRİN", key="single_edit_search")
        submit_find = st.form_submit_button("ÜRÜNÜ BUL")
    if submit_find:
        st.session_state.single_edit_query = search_value.strip()
        st.session_state.single_edit_choice = 0
        rerun_app()

    if st.session_state.get("single_edit_query"):
        single_candidates = query_stock_candidates(edit_stock_path, st.session_state.single_edit_query)
        if single_candidates is None or single_candidates.empty:
            st.error(f"{st.session_state.single_edit_query} İÇİN ÜRÜN BULUNAMADI.")
        else:
            single_candidates = single_candidates.reset_index(drop=True)
            option_indices = list(range(len(single_candidates)))
            option_labels = [
                f"{to_upper(row['barkod'])} — {to_upper(row['adi'])} — {float(row['fiyat']):.2f} TL"
                for _, row in single_candidates.iterrows()
            ]
            selected_index = st.selectbox(
                "EŞLEŞEN ÜRÜNLER",
                option_indices,
                format_func=lambda i: option_labels[i],
                key="single_edit_choice",
            )
            selected_product = single_candidates.iloc[selected_index]
            st.markdown(f"**SEÇİLEN ÜRÜN:** {to_upper(selected_product['adi'])} — BARKOD: {to_upper(selected_product['barkod'])}")
            with st.form("single_edit_form", clear_on_submit=False):
                yeni_adi = st.text_input("YENİ ÜRÜN ADI", value=to_upper(selected_product['adi']))
                yeni_fiyat = st.number_input(
                    "YENİ FİYAT (TL)",
                    min_value=0.01,
                    value=float(selected_product['fiyat']) if selected_product['fiyat'] not in [None, ""] else 0.01,
                    step=0.25,
                    format="%.2f",
                )
                submit_single_edit = st.form_submit_button("DEĞİŞİKLİKLERİ KAYDET")
                if submit_single_edit:
                    if update_single_stock_product(edit_stock_path, selected_product['barkod'], yeni_adi, yeni_fiyat):
                        st.success("ÜRÜN BİLGİLERİ GÜNCELLENDİ.")
                        st.warning("BU GÜNCELLEME GITHUB'DA KALICI DEĞİLDİR, LÜTFEN DOSYAYI İNDİRİP MANUEL YÜKLEYİN.")
                        st.session_state.single_edit_query = ""
                        rerun_app()
                    else:
                        st.error("ÜRÜN GÜNCELENEMEDİ. LÜTFEN DOĞRU ÜRÜN SEÇİN.")

    st.markdown("---")
    st.subheader("GÜVENLİ VERİ GÜNCELLEME")
    upload_isletme = st.selectbox(
        "GÜNCELLENECEK İŞLETME",
        [ISLETME_OPTIONS["HOME"], ISLETME_OPTIONS["MARKET"]],
        index=0,
    )
    target_stock_path = STOK_DOSYASI_HOME if upload_isletme == ISLETME_OPTIONS["HOME"] else STOK_DOSYASI_MARKET
    st.caption("MEVCUT DOSYA GÜNCELLENMEDEN ÖNCE yedek_stok.csv OLARAK KAYDEDİLECEK.")
    uploaded_file = st.file_uploader(
        "YÜKLENECEK CSV DOSYASI",
        type=["csv"],
        help="UTF-8-SIG formatında olmalıdır.",
        key="secure_stock_upload",
    )
    if uploaded_file is not None:
        uploaded_file.seek(0)
        new_stock_df, upload_error = preprocess_uploaded_stock(uploaded_file)
        if upload_error:
            st.error(upload_error)
        else:
            existing_stock_df = load_stock_csv(target_stock_path)
            invalid_count = count_invalid_stock_rows(new_stock_df)
            analysis = analyze_stock_update(existing_stock_df, new_stock_df)
            st.markdown("**ÖN ANALİZ**")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("TOPLAM ÜRÜN", f"{analysis['total']}")
            col2.metric("FİYAT DEĞİŞEN", f"{analysis['changed_count']}")
            col3.metric("YENİ ÜRÜN", f"{analysis['added_count']}")
            col4.metric("ÇIKAN ÜRÜN", f"{analysis['removed_count']}")
            if not analysis["suspicious_df"].empty:
                st.markdown("**ŞÜPHELİ ÜRÜNLER (%50'DEN FAZLA DEĞİŞEN)**")
                suspicious_df = analysis["suspicious_df"].copy()
                suspicious_df["fark_yuzde"] = suspicious_df["fark_yuzde"].apply(lambda v: f"{v:.1f}%")
                st.dataframe(suspicious_df)
            else:
                st.info("ŞÜPHELİ ÜRÜN YOK.")
            skip_invalid = True
            if invalid_count > 0:
                skip_invalid = st.checkbox(
                    f"FİYATI SIFIR (0) VEYA GEÇERSİZ OLAN {invalid_count} ADET SATIR TESPİT EDİLDİ. BUNLARI ATLAYALIM MI?",
                    value=False,
                )
                if not skip_invalid:
                    st.warning("HATALI VERİLERİ ATLAMAK İÇİN SEÇENEĞİ İŞARETLEYİN.")
            if invalid_count == 0 or skip_invalid:
                st.warning("GÜNCELLEME SIRASINDA UYGULAMA BAKIM MODUNA GEÇECEKTİR.")
                confirm = st.checkbox("BU İŞLEM GERİ ALINAMAZ (YEDEK HARİÇ), EMİN MİSİNİZ?")
                if confirm and st.button("VERİLERİ GÜNCELLE"):
                    if invalid_count > 0:
                        new_stock_df = new_stock_df[new_stock_df["fiyat"].notna() & (new_stock_df["fiyat"] > 0)].copy()
                    backup_stock_file(target_stock_path)
                    save_stock_csv(target_stock_path, new_stock_df)
                    st.success("VERİLER GÜNCELLENDİ. YEDEK yedek_stok.csv OLARAK KAYDEDİLDİ.")
                    rerun_app()

    st.markdown("---")
    st.subheader("YENİ KULLANICI EKLE")
    with st.form("new_user_form", clear_on_submit=True):
        yeni_username = st.text_input("KULLANICI ADI", placeholder="YENİ KULLANICI ADI")
        yeni_password = st.text_input("ŞİFRE", type="password", placeholder="YENİ ŞİFRE")
        yeni_role = st.selectbox("ROL", ["ADMIN", "USER"])
        yeni_isletme = st.selectbox(
            "ERİŞEBİLECEĞİ İŞLETME",
            [ISLETME_OPTIONS["HOME"], ISLETME_OPTIONS["MARKET"], "HER İKİSİ"],
            index=2,
        )
        submit_user = st.form_submit_button("KULLANICI OLUŞTUR")
        if submit_user:
            if not yeni_username.strip() or not yeni_password.strip():
                st.error("KULLANICI ADI VE ŞİFRE BOŞ BIRAKILAMAZ.")
            else:
                if yeni_isletme == "HER İKİSİ":
                    selected_isletme = ALL_ISLETMELER
                elif yeni_isletme == ISLETME_OPTIONS["HOME"]:
                    selected_isletme = "HOME"
                else:
                    selected_isletme = "MARKET"
                if save_user(yeni_username, yeni_password, yeni_role, selected_isletme):
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


def display_single_product_edit_page():
    st.markdown("## TEK ÜRÜN DÜZENLE")
    st.caption("ARAMA, LİSTELEME VE DÜZENLEME PANELİ")
    st.markdown("---")

    edit_isletme_choice = st.selectbox(
        "DÜZENLENECEK İŞLETME",
        [ISLETME_OPTIONS["HOME"], ISLETME_OPTIONS["MARKET"]],
        index=0,
        key="single_edit_isletme",
    )
    edit_stock_path = STOK_DOSYASI_HOME if edit_isletme_choice == ISLETME_OPTIONS["HOME"] else STOK_DOSYASI_MARKET

    left_area, right_area = st.columns([4, 1])
    with left_area:
        st.markdown("### ÜRÜN ARAMA")
        search_col, camera_col, action_col = st.columns([6, 1, 1])
        search_value = search_col.text_input(
            "BARKOD VEYA ÜRÜN ADI",
            value=st.session_state.get("single_edit_query", ""),
            placeholder="ÖRN: *EKMEK* veya 12345",
            key="single_edit_search_input",
        )
        camera_clicked = camera_col.button("BARKOD TARA")
        search_clicked = action_col.button("ÜRÜNÜ BUL")

        if camera_clicked:
            st.session_state.single_edit_camera_mode = True
            st.session_state.single_edit_query = ""
            st.session_state.single_edit_selected = ""
            st.session_state.single_edit_choice = 0
            rerun_app()

        if search_clicked:
            if search_value.strip():
                st.session_state.single_edit_query = search_value.strip()
                st.session_state.single_edit_camera_mode = False
                st.session_state.single_edit_selected = ""
                st.session_state.single_edit_choice = 0
                rerun_app()
            else:
                st.warning("LÜTFEN ARAMA KELİMESİ GİRİN.")

        if st.session_state.single_edit_camera_mode:
            from barcode_scanner import barcode_scanner
            st.markdown("**KAMERA MODU: BARKOD TARANMASINI BEKLEYİN**")
            taranan = barcode_scanner(mode="scanning", key="single_edit_camera")
            if taranan:
                st.session_state.single_edit_query = taranan
                st.session_state.single_edit_camera_mode = False
                st.session_state.single_edit_selected = ""
                st.session_state.single_edit_choice = 0
                rerun_app()

        if not st.session_state.single_edit_query:
            st.info("ARAMAK İÇİN BARKOD, ÜRÜN ADI VEYA JOKER (*) KULLANARAK ARAMA YAPIN.")

        results = pd.DataFrame()
        if st.session_state.single_edit_query:
            with st.spinner("Ürün aranıyor..."):
                results = query_stock_candidates(edit_stock_path, st.session_state.single_edit_query)
                st.session_state.single_edit_results = results
        elif st.session_state.get("single_edit_results") is not None:
            results = st.session_state.single_edit_results

        if not results.empty:
            st.markdown(f"**{len(results)} ÜRÜN BULUNDU**")
            for idx, row in results.reset_index(drop=True).iterrows():
                cols = st.columns([2, 6, 2, 1])
                cols[0].write(to_upper(row["barkod"]))
                cols[1].write(to_upper(row["adi"]))
                cols[2].write(f"{float(row['fiyat']):.2f} TL")
                if cols[3].button("DÜZENLE", key=f"edit_single_{idx}_{row['barkod']}"):
                    st.session_state.single_edit_selected = row["barkod"]
                    st.session_state.single_edit_choice = idx
                    st.success("DÜZENLEME PANELİ AÇILIYOR...")
                    rerun_app()
        elif st.session_state.single_edit_query:
            st.error(f"{st.session_state.single_edit_query} İÇİN ÜRÜN BULUNAMADI.")

    with right_area:
        with st.expander("DÜZENLEME PANELİ", expanded=True):
            if st.session_state.single_edit_selected:
                product = load_stock_csv(edit_stock_path)
                product = product[product["barkod"].astype(str).str.strip() == st.session_state.single_edit_selected]
                if not product.empty:
                    product = product.iloc[0]
                    st.markdown(f"**SEÇİLEN ÜRÜN:** {to_upper(product['adi'])}")
                    st.markdown(f"BARKOD: {to_upper(product['barkod'])}")
                    with st.form("single_edit_right_form", clear_on_submit=False):
                        yeni_adi = st.text_input("YENİ ÜRÜN ADI", value=to_upper(product["adi"]))
                        yeni_fiyat = st.number_input(
                            "YENİ FİYAT (TL)",
                            min_value=0.01,
                            value=float(product["fiyat"]) if product["fiyat"] not in [None, ""] else 0.01,
                            step=0.25,
                            format="%.2f",
                        )
                        submit_update = st.form_submit_button("CSV'Yİ GÜNCELLE")
                        if submit_update:
                            if update_single_stock_product(edit_stock_path, product["barkod"], yeni_adi, yeni_fiyat):
                                st.success("ÜRÜN GÜNCELLENDİ.")
                                st.warning("BU GÜNCELLEME GITHUB'DA KALICI DEĞİLDİR, LÜTFEN DOSYAYI İNDİRİP MANUEL YÜKLEYİN.")
                                st.session_state.single_edit_query = ""
                                st.session_state.single_edit_selected = ""
                                st.session_state.single_edit_choice = 0
                                rerun_app()
                            else:
                                st.error("ÜRÜN GÜNCELLENEMEDİ. LÜTFEN DOĞRU ÜRÜNÜ SEÇİN.")
                else:
                    st.warning("SEÇİLEN BARKODA AİT ÜRÜN BULUNAMADI.")
            else:
                st.info("LÜTFEN SOLDAKİ SONUÇLARDAN BİR ÜRÜN SEÇİN VEYA YENİDEN ARA.")


def display_main_panel():
    st.markdown("## STOK VE FIYAT KONTROL")
    st.caption(f"{len(stok_df):,} ÜRÜN YÜKLENDİ")
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
            st.warning("LÜTFEN BİR DEĞER GİRİN.")

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
        with st.form("talep_formu", clear_on_submit=False):
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
def stok_yukle(isletme: str):
    stok_path = get_stock_file(isletme)
    try:
        df = pd.read_csv(stok_path, dtype={"barkod": str}, encoding="utf-8-sig")
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

stok_df = stok_yukle(st.session_state.current_isletme)

if page == "YÖNETİCİ PANELİ":
    display_admin_panel()
elif page == "TEK ÜRÜN DÜZENLE":
    display_single_product_edit_page()
else:
    display_main_panel()

st.markdown("---")
st.markdown(
    "<p style='text-align:center;color:#999;font-size:11px;'>STOK & FIYAT KONTROL • UTF-8</p>",
    unsafe_allow_html=True,
)
