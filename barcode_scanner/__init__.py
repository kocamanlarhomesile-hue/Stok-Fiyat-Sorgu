import streamlit.components.v1 as components
import os

_FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")

_barcode_scanner = components.declare_component(
    "barcode_scanner",
    path=_FRONTEND_DIR
)

def barcode_scanner(mode="scanning", key=None):
    """
    mode="scanning" → kamera açık, tarama bekliyor
    mode="result"   → kamera kapalı, sonuç gösteriliyor
    """
    return _barcode_scanner(key=key, default=None, mode=mode)
