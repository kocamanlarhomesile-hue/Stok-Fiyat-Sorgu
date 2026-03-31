# -*- coding: utf-8 -*-
import sys
from pathlib import Path
from runpy import run_path

BASE_DIR = Path(__file__).resolve().parent
APP_PATH = BASE_DIR / "stok-fiyat-app" / "app.py"

if not APP_PATH.exists():
    raise FileNotFoundError(f"Deploy entrypoint not found: {APP_PATH}")

sys.path.insert(0, str(APP_PATH.parent))
run_path(str(APP_PATH), run_name="__main__")
