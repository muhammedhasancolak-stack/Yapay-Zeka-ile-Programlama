"""Gemini destekli, güvenlik denetimli SQLite SQL asistanı."""

import os
import random
import re
import sqlite3
import time
from datetime import date

import pandas as pd
from google import genai

SEHIRLER = ["İstanbul", "Ankara", "İzmir", "Bursa", "Antalya"]
RAPOR_DOSYASI = "sql_asistan_raporu.txt"
MAKS_DENEME = 3
YASAKLI_KOMUTLAR = ("DROP", "DELETE", "UPDATE", "INSERT", "ALTER")
SISTEM_TALIMATI = """
Sen SQLite bilen bir SQL asistanısın. Aşağıdaki şemaya göre kullanıcının doğal
dilde istediği veriyi getiren, tek ve SQLite uyumlu bir SQL sorgusu yaz.

Şema:
- musteriler(musteri_id, ad_soyad, sehir)
- siparisler(siparis_id, musteri_id, tutar, tarih)

Kurallar:
- Sadece tek bir SELECT sorgusu üret.
- Markdown, açıklama, SQL kod bloğu ve noktalı virgül kullanma.
- Tablo ve sütun adlarını yalnızca verilen şemadan seç.
""".strip()


class Raporlayici:
    """Çalışma esnasındaki ölçümleri biriktirip teslim raporuna yazar."""

    def __init__(self):
        self.toplam_talep = 0
        self.basari = 0
        self.engellenen_saldiri = 0
        self.duzeltilen_hata = 0
        self.detaylar = []

    def ekle(self, metin):
        self.detaylar.append(metin)

    def yaz(self):
        with open(RAPOR_DOSYASI, "w", encoding="utf-8") as dosya:
            dosya.write("AKILLI SQL ASİSTANI PERFORMANS VE GÜVENLİK RAPORU\n")
            dosya.write("--------------------------------------------------\n")
            dosya.write(f"Çalıştırma Tarihi : {date.today().isoformat()}\n")
            dosya.write("Veritabanı Hacmi : 1.000 Müşteri / 1.000 Sipariş\n")
            dosya.write(f"Toplam Test Talebi : {self.toplam_talep}\n")
            dosya.write(f"Başarılı İcra : {self.basari}\n")
            dosya.write(f"Engellenen Saldırı : {self.engellenen_saldiri}\n")
            dosya.write(f"Hata Düzeltme Sayısı : {self.duzeltilen_hata}\n\n")
            dosya.write("TEST DETAYLARI:\n")
            dosya.write("\n".join(self.detaylar) if self.detaylar else "Henüz test çalıştırılmadı.")
            dosya.write("\n\nKISA YORUM VE DEĞERLENDİRME:\n")
            dosya.write("Süreler, API yanıtı ve SQLite sorgu icrasını birlikte ölçer.\n")
            dosya.write("Yasaklı komutlar veritabanına gönderilmeden güvenlik katmanında engellenir.\n")


def veritabanini_olustur():
    """Bellekteki SQLite veritabanını 1.000 müşteri ve siparişle hazırlar."""
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    cursor.execute(
        "CREATE TABLE musteriler (musteri_id INTEGER PRIMARY KEY, ad_soyad TEXT, sehir TEXT)"
    )
    cursor.execute(
        "CREATE TABLE siparisler (siparis_id INTEGER PRIMARY KEY, musteri_id INTEGER, "
        "tutar REAL, tarih TEXT, FOREIGN KEY(musteri_id) REFERENCES musteriler(musteri_id))"
    )

    adlar = ["Ahmet", "Ayşe", "Mehmet", "Elif", "Can", "Zeynep", "Deniz", "Ece"]
    soyadlar = ["Yılmaz", "Kaya", "Demir", "Şahin", "Çelik", "Aydın", "Arslan", "Koç"]
    musteriler = [
        (musteri_id, f"{random.choice(adlar)} {random.choice(soyadlar)}", random.choice(SEHIRLER))
        for musteri_id in range(1, 1001)
    ]
    siparisler = [
        (siparis_id, random.randint(1, 1000), round(random.uniform(100, 10000), 2), "2026-01-01")
        for siparis_id in range(1, 1001)
    ]
    cursor.executemany("INSERT INTO musteriler VALUES (?, ?, ?)", musteriler)
    cursor.executemany("INSERT INTO siparisler VALUES (?, ?, ?, ?)", siparisler)
    conn.commit()
    return conn


def guvenlik_kontrolu(sql_kodu: str) -> bool:
    """Yalnızca tek SELECT sorgusuna izin verir; tüm mutasyon komutlarını engeller."""
    temiz = re.sub(r"--[^\n]*|/\*.*?\*/", "", sql_kodu, flags=re.DOTALL).strip()
    bulunan = re.search(r"\b(" + "|".join(YASAKLI_KOMUTLAR) + r")\b", temiz, flags=re.IGNORECASE)
    if bulunan:
        print(f"[GÜVENLİK ENGELİ] Zararlı SQL tespit edildi: '{bulunan.group(1).upper()}' komutuna izin verilmiyor!")
        return False
    if not re.fullmatch(r"SELECT\b[\s\S]*?;?", temiz, flags=re.IGNORECASE):
        print("[GÜVENLİK ENGELİ] Sadece tek bir SELECT sorgusuna izin veriliyor!")
        return False
    if ";" in temiz.rstrip(";"):
        print("[GÜVENLİK ENGELİ] Birden fazla SQL ifadesine izin verilmiyor!")
        return False
    print("[GÜVENLİK] Denetim başarılı (sadece SELECT).")
    return True


def clean_sql(raw_sql: str) -> str:
    """Gemini yanıtındaki kod bloğu ve gereksiz boşlukları temizler."""
    temiz = raw_sql.strip()
    temiz = re.sub(r"^```(?:sql|sqlite)?\s*", "", temiz, flags=re.IGNORECASE)
    temiz = re.sub(r"\s*```$", "", temiz)
    return temiz.strip()


def gemini_sql_uret(
    client, kullanici_talebi: str, hata_mesaji: str | None = None, onceki_sql: str | None = None
) -> str:
    istem = f"{SISTEM_TALIMATI}\n\nKullanıcı talebi:\n{kullanici_talebi}"
    if hata_mesaji:
        istem += (
            "\n\nÖnceki SQL sorgusu SQLite hatası verdi.\n"
            f"Önceki sorgu: {onceki_sql}\nHata: {hata_mesaji}\n"
            "Sorguyu şemaya uygun biçimde düzelt ve yalnızca yeni SELECT sorgusunu döndür."
        )
    yanit = client.models.generate_content(model="gemini-3.5-flash", contents=istem)
    return clean_sql(yanit.text or "")


def sql_asistani_calistir(client, conn, rapor, kullanici_talebi: str):
    """SQL üretir, güvenlik denetiminden geçirir ve hatalı sorguyu en çok 3 kez düzeltir."""
    rapor.toplam_talep += 1
    baslangic = time.perf_counter()
    hata_mesaji = None
    onceki_sql = None

    for deneme in range(1, MAKS_DENEME + 1):
        try:
            print(f"[GEMINI] SQL üretiliyor... (deneme {deneme}/{MAKS_DENEME})")
            sql = gemini_sql_uret(client, kullanici_talebi, hata_mesaji, onceki_sql)
            print(f"[SQL] {sql}")

            if not guvenlik_kontrolu(sql):
                rapor.engellenen_saldiri += 1
                rapor.ekle(f"[TEST {rapor.toplam_talep}] Güvenlik engeli | Durum: BAŞARILI")
                return

            cursor = conn.execute(sql)
            sutunlar = [sutun[0] for sutun in cursor.description]
            sonuc = pd.DataFrame(cursor.fetchall(), columns=sutunlar)
            sure = time.perf_counter() - baslangic
            print(f"[SONUÇ] (Toplam süre: {sure:.3f} sn)")
            print(sonuc.to_string(index=False) if not sonuc.empty else "Sonuç bulunamadı.")
            rapor.basari += 1
            if deneme > 1:
                rapor.duzeltilen_hata += 1
                durum = f"Self-Correction {deneme}. denemede başarılı"
            else:
                durum = "BAŞARILI"
            rapor.ekle(f"[TEST {rapor.toplam_talep}] İcra süresi: {sure:.3f} saniye | Durum: {durum}")
            return
        except sqlite3.Error as hata:
            hata_mesaji = str(hata)
            onceki_sql = sql
            print(f"[SQL HATASI] {hata_mesaji}")
            if deneme < MAKS_DENEME:
                print("[SELF-CORRECTION] Hata Gemini'ye iletiliyor; sorgu düzeltilecek.")
            else:
                sure = time.perf_counter() - baslangic
                rapor.ekle(f"[TEST {rapor.toplam_talep}] {sure:.3f} saniye | Durum: 3 denemede çözülemedi ({hata_mesaji})")
        except Exception as hata:
            print(f"[SİSTEM HATASI] {hata}")
            rapor.ekle(f"[TEST {rapor.toplam_talep}] Durum: Sistem hatası ({hata})")
            return


def main():
    api_anahtari = "api"
    if not api_anahtari:
        print("[HATA] GEMINI_API_KEY ortam değişkeni tanımlı değil.")
        return

    conn = veritabanini_olustur()
    rapor = Raporlayici()
    client = genai.Client(api_key=api_anahtari)
    print("[BİLGİ] Veritabanı oluşturuldu. 1.000 müşteri ve 1.000 sipariş yüklendi.")
    print("Çıkış için 'q' yazın.")

    try:
        while True:
            talep = input("\nSoru girin: ").strip()
            if talep.lower() == "q":
                break
            if not talep:
                print("[HATA] Talep boş olamaz.")
                continue
            sql_asistani_calistir(client, conn, rapor, talep)
    finally:
        rapor.yaz()
        conn.close()
        print(f"[BİLGİ] Rapor kaydedildi: {RAPOR_DOSYASI}")


if __name__ == "__main__":
    main()
