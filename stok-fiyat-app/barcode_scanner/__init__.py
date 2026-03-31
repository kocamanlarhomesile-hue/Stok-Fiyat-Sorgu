import streamlit.components.v1 as components
import os

_FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")

_barcode_scanner = components.declare_component(
    "barcode_scanner",
    path=_FRONTEND_DIR
)

def barcode_scanner(key=None):
    """EAN-13 ve diğer barkod türlerini okuyan canlı tarayıcı bileşeni."""
    return _barcode_scanner(key=key, default=None)
