"""Gemini ile doğal dildeki e-ticaret isteğini PostgreSQL sorgusuna çevirir.

Çalıştırmadan önce Google AI Studio anahtarını ortam değişkeni olarak tanımlayın:
PowerShell: $env:GEMINI_API_KEY = "anahtariniz"
"""

import os
import sys

from google import genai
from google.genai import types


# Veritabanı şeması (görseldeki tablolar korunmuştur).
SEMA = """
1. Musteriler Tablosu: musteri_id, ad_soyad, eposta, sehir
2. Siparisler Tablosu: siparis_id, musteri_id, tutar, siparis_tarihi
"""

# Görseldeki talebin aynı sonucu veren, farklı yazılmış hâli.
TALEP = """
İstanbul'da ikamet eden müşterilerden son 30 gün içindeki siparişlerinin
toplamı 5.000 TL'yi aşanların ad-soyadını, e-posta adresini ve toplam
harcama tutarını listele.
"""


def turkce_ayarla() -> None:
    """Windows terminalinde Türkçe karakterlerin düzgün görünmesini sağlar."""
    for akis in (sys.stdin, sys.stdout, sys.stderr):
        try:
            akis.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


def kod_blogunu_temizle(metin: str) -> str:
    """Model SQL'i Markdown kod bloğunda döndürürse blok işaretlerini kaldırır."""
    metin = metin.strip()
    kod_blogu_isareti = chr(96) * 3
    if metin.startswith(kod_blogu_isareti):
        satirlar = metin.splitlines()[1:]
        if satirlar and satirlar[-1].strip() == kod_blogu_isareti:
            satirlar = satirlar[:-1]
        metin = "\n".join(satirlar).strip()
    return metin


def salt_okunur_sql_mi(sql: str) -> bool:
    """Örnek uygulamanın yalnızca SELECT sorgusu yazdırmasını garanti eder."""
    yasakli = ("INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "CREATE")
    buyuk_sql = sql.upper()
    return buyuk_sql.startswith("SELECT") and not any(kelime in buyuk_sql for kelime in yasakli)


def sql_uret(sema: str, talep: str) -> str:
    """Gemini'ye şema ve talebi gönderir; yalnızca PostgreSQL SELECT sorgusunu döndürür."""
    api_anahtari = os.getenv("GEMINI_API_KEY")
    if not api_anahtari:
        raise RuntimeError(
            "GEMINI_API_KEY ortam değişkeni bulunamadı. "
            "Önce API anahtarınızı tanımlayın."
        )

    istem = f"""
Sen PostgreSQL bilen bir SQL asistanısın.

Veritabanı şeması:
{sema}

Kullanıcı talebi:
{talep}

Kurallar:
- Sadece tek bir PostgreSQL SELECT sorgusu döndür.
- Açıklama, Markdown ve kod bloğu kullanma.
- Musteriler tablosunu m, Siparisler tablosunu s takma adıyla kullan.
- Müşteri bazında toplam harcamayı SUM(s.tutar) AS toplam_harcama olarak döndür.
- SELECT ve GROUP BY içinde m.musteri_id, m.ad_soyad ve m.eposta alanları olsun.
- İstanbul filtresi, son 30 gün filtresi, GROUP BY ve 5000 TL üzeri koşulu için HAVING kullan.
"""

    istemci = genai.Client(api_key=api_anahtari)
    yanit = istemci.models.generate_content(
        model="gemini-2.5-flash",
        contents=istem,
        config=types.GenerateContentConfig(temperature=0),
    )

    sql = kod_blogunu_temizle(yanit.text or "")
    if not sql:
        raise RuntimeError("Gemini boş bir yanıt döndürdü.")
    if not salt_okunur_sql_mi(sql):
        raise RuntimeError("Güvenli olmayan veya SELECT olmayan bir SQL üretildi.")
    return sql


def main() -> None:
    turkce_ayarla()
    print("=" * 72)
    print("             YAPAY ZEKA DESTEKLİ DOĞAL DİLDEN SQL ÜRETİCİ")
    print("=" * 72)
    print("\n[AŞAMA 1] VERİTABANI ŞEMASI VE KULLANICI TALEBİ ALINDI...")
    print("\n[AŞAMA 2] SQL ÇEVİRİSİ İÇİN GEMINI'YE BAĞLANILIYOR...")
    print("\nGemini isteği gönderiliyor...")

    try:
        sql = sql_uret(SEMA, TALEP)
    except Exception as hata:
        print(f"\n[HATA] {hata}")
        return

    print("Gemini yanıtı alındı!")
    print("=" * 72)
    print("                        ÜRETİLEN SQL SORGUSU")
    print("=" * 72)
    print(sql)
    print("=" * 72)


if __name__ == "__main__":
    main()
