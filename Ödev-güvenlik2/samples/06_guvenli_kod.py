import json
import os
import sqlite3
from pathlib import Path

BASE_DIR = Path("/var/www/uploads").resolve()


def urun_ara(urun_adi):
    with sqlite3.connect("magaza.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM urunler WHERE urun_adi = ?", (urun_adi,))
        return cursor.fetchall()


def db_sifresi():
    sifre = os.getenv("DB_PASSWORD")
    if not sifre:
        raise RuntimeError("DB_PASSWORD ortam değişkeni tanımlı değil.")
    return sifre


def dosya_oku(dosya_adi):
    hedef = (BASE_DIR / dosya_adi).resolve()
    if not hedef.is_relative_to(BASE_DIR):
        raise ValueError("İzin verilen klasörün dışına erişilemez.")
    return hedef.read_text(encoding="utf-8")


def veri_coz(metin):
    return json.loads(metin)
