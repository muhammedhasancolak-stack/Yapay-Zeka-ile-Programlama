import json
import locale
import math
import os
import sys

from google import genai
from google.genai import errors

DOSYA_ADI = "urunler.json"
GEREKLI_ALANLAR = ("urun_adi", "kategori",
                   "seo_etiketleri", "satis_aciklamasi")

# Geçerli API anahtarınızı buraya yazın
API_ANAHTARI = "Api"


def turkce_ayarla():
    """Konsol giriş/çıkışını UTF-8 yapar ve Türkçe (tr_TR) dil ayarını yüklemeyi dener."""
    # Girdi/çıktıda ç, ğ, ı, ö, ş, ü ve İ harflerinin bozulmaması için
    for akis in (sys.stdin, sys.stdout, sys.stderr):
        try:
            akis.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass

    # İşletim sistemine göre uygun Türkçe locale adını dene
    for ad in ("tr_TR.UTF-8", "tr_TR.utf8", "tr_TR", "Turkish_Turkey.1254", "Turkish"):
        try:
            locale.setlocale(locale.LC_ALL, ad)
            return
        except locale.Error:
            continue


# ----------------------------------------------------------------------
# 1) API FONKSİYONU (geçen dersteki fonksiyon, artık dict döndürüyor)
# ----------------------------------------------------------------------
def e_ticaret_api_simulasyonu(urun_talebi):
    """Gemini'ye ürün açıklamasını gönderir, ham yanıtı JSON'dan dict'e çevirip döndürür."""
    client = genai.Client(api_key=API_ANAHTARI)

    sistem_mesaji = """
    Sen kurumsal bir e-ticaret sisteminin arka planında çalışan
    bir veri yapılandırma asistanısın.

    Kullanıcının girdiği ham ürün bilgilerini analiz edip,
    veritabanına kaydedilebilmesi için SADECE JSON formatında
    yanıt vermelisin.

    JSON nesnesi kesinlikle şu anahtarları içermelidir:

    {
        "urun_adi": "Kısa ve optimize edilmiş ürün adı",
        "kategori": "Uygun e-ticaret kategorisi",
        "seo_etiketleri": "3 adet virgülle ayrılmış SEO etiketi",
        "satis_aciklamasi": "Müşteriyi ikna edecek profesyonel 2 cümle"
    }

    JSON dışında hiçbir açıklama yazma.
    """

    # Interactions API çağrısı
    interaction = client.interactions.create(
        model="gemini-3.8-flash",
        input=f"{sistem_mesaji}\n\nKullanıcının ürün talebi:\n{urun_talebi}",
    )

    return json_ayristir(interaction.output_text)


# ----------------------------------------------------------------------
# 2) YARDIMCI FONKSİYONLAR
# ----------------------------------------------------------------------
def json_ayristir(ham_metin):
    """Gemini yanıtını JSON olarak ayrıştırır ve zorunlu alanları doğrular."""
    if not ham_metin or not ham_metin.strip():
        raise ValueError("API boş yanıt döndürdü.")

    metin = ham_metin.strip()

    # Model yanıtı ```json ... ``` bloğu içinde verirse temizle
    if metin.startswith("```"):
        metin = metin.strip("`").strip()
        if metin.lower().startswith("json"):
            metin = metin[4:].strip()

    try:
        veri = json.loads(metin)
    except json.JSONDecodeError:
        raise ValueError("API yanıtı geçerli bir JSON değil.")

    if not isinstance(veri, dict):
        raise ValueError("API yanıtı bir JSON nesnesi değil.")

    for alan in GEREKLI_ALANLAR:
        deger = veri.get(alan)
        if not isinstance(deger, str) or not deger.strip():
            raise ValueError(
                f"API yanıtında zorunlu alan eksik veya boş: '{alan}'")
        veri[alan] = deger.strip()

    return veri


def urunleri_yukle():
    """urunler.json dosyasını okur; dosya yoksa, boşsa veya bozuksa boş liste döner."""
    if not os.path.exists(DOSYA_ADI):
        return []
    try:
        with open(DOSYA_ADI, "r", encoding="utf-8") as dosya:
            icerik = dosya.read().strip()
        if not icerik:
            return []
        veri = json.loads(icerik)
        if not isinstance(veri, list):
            raise ValueError
        return veri
    except (json.JSONDecodeError, ValueError):
        print(
            "[UYARI] urunler.json bozuk veya hatalı biçimde. Boş liste ile devam ediliyor.")
        return []
    except OSError as e:
        print(f"[HATA] Dosya okunamadı: {e}")
        return []


def urunleri_kaydet(urunler):
    """Ürün listesini urunler.json dosyasına yazar."""
    try:
        with open(DOSYA_ADI, "w", encoding="utf-8") as dosya:
            json.dump(urunler, dosya, ensure_ascii=False, indent=2)
        return True
    except OSError as e:
        print(f"[HATA] Dosyaya yazılamadı: {e}")
        return False


def yeni_urun_kodu(urunler):
    """URN-0001, URN-0002 ... biçiminde benzersiz kod üretir."""
    en_buyuk = 0
    for urun in urunler:
        kod = str(urun.get("urun_kodu", ""))
        if kod.startswith("URN-") and kod[4:].isdigit():
            en_buyuk = max(en_buyuk, int(kod[4:]))
    return f"URN-{en_buyuk + 1:04d}"


def sayi_al(mesaj, tur):
    """Negatif olmayan geçerli bir sayı alana kadar sorar. tur: 'int' veya 'float'."""
    while True:
        girdi = input(mesaj).strip().replace(",", ".")
        try:
            deger = int(girdi) if tur == "int" else float(girdi)
        except ValueError:
            print("[HATA] Lütfen geçerli bir sayı girin.")
            continue
        if isinstance(deger, float) and not math.isfinite(deger):
            print("[HATA] Lütfen geçerli bir sayı girin.")
            continue
        if deger < 0:
            print("[HATA] Değer negatif olamaz.")
            continue
        if isinstance(deger, float) and deger.is_integer():
            deger = int(deger)
        return deger


def tr_normallestir(metin):
    """Arama için metni küçültür (İ/I doğru) ve Türkçe harfleri sadeleştirir (ç->c, ı->i ...).
    Böylece 'ÇANTA', 'çanta' ve 'canta' aynı sonucu verir."""
    metin = metin.replace("İ", "i").replace("I", "ı").lower()
    return metin.translate(str.maketrans("çğıöşü", "cgiosu"))


def stok_uyarisi(stok):
    """Stok 0 ise 'STOKTA YOK', 1-4 arasıysa 'KRİTİK STOK' uyarısı yazdırır."""
    if stok == 0:
        print("[UYARI] STOKTA YOK!")
    elif 1 <= stok <= 4:
        print(f"[UYARI] KRİTİK STOK! Yalnızca {stok} adet kaldı.")


def urun_yazdir(urun):
    print(f"Ürün Kodu : {urun['urun_kodu']}")
    print(f"Ürün Adı  : {urun['urun_adi']}")
    print(f"Kategori  : {urun['kategori']}")
    print(f"Fiyat     : {urun['fiyat']} TL")
    print(f"Stok      : {urun['stok']}")
    print(f"SEO       : {urun['seo_etiketleri']}")



# ----------------------------------------------------------------------
# 3) DOĞAL DİLDEN SQL ÜRETİMİ
# ----------------------------------------------------------------------

def sql_sorgusu_uret():
    """Kullanıcının doğal dildeki talebini Gemini ile PostgreSQL'e çevirir."""
    talep = input("\nSQL talebinizi yazın: ").strip()
    if not talep:
        print("[HATA] SQL talebi boş olamaz.")
        return

    sema = """
    Musteriler Tablosu: musteri_id, ad_soyad, eposta, sehir
    Siparisler Tablosu: siparis_id, musteri_id, tutar, siparis_tarihi
    """

    istem = f"""
    Sen PostgreSQL bilen bir SQL asistanısın.

    Veritabanı şeması:
    {sema}

    Kullanıcı talebi:
    {talep}

    Sadece tek bir PostgreSQL SELECT sorgusu döndür.
    Açıklama veya Markdown kod bloğu kullanma.
    Müşteriler için m, siparişler için s takma adını kullan.
    Toplam harcama gerekiyorsa SUM(s.tutar) AS toplam_harcama yaz.
    """

    api_anahtari = os.getenv("GEMINI_API_KEY") or API_ANAHTARI
    print("\nGemini isteği gönderiliyor...")

    try:
        client = genai.Client(api_key=api_anahtari)
        yanit = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=istem,
        )
        sql = (yanit.text or "").strip()

        # Model yanıtı Markdown kod bloğunda verirse temizle.
        kod_blogu = chr(96) * 3
        if sql.startswith(kod_blogu):
            satirlar = sql.splitlines()[1:]
            if satirlar and satirlar[-1].strip() == kod_blogu:
                satirlar = satirlar[:-1]
            sql = "\n".join(satirlar).strip()

        if not sql.upper().startswith("SELECT"):
            raise ValueError("Gemini geçerli bir SELECT sorgusu üretmedi.")

        print("Gemini yanıtı alındı!")
        print("=" * 72)
        print("                        ÜRETİLEN SQL SORGUSU")
        print("=" * 72)
        print(sql)
        print("=" * 72)
    except Exception as e:
        print(f"[SQL HATASI] {e}")


# ----------------------------------------------------------------------
# 4) MENÜ İŞLEMLERİ
# ----------------------------------------------------------------------
def menu_goster():
    print("\n========== E-TİCARET YÖNETİM PANELİ ==========")
    print("1 - Yeni Ürün Ekle")
    print("2 - Ürünleri Listele")
    print("3 - Ürün Ara")
    print("4 - Stok Güncelle")
    print("5 - Çıkış")
    print("6 - Doğal Dilden SQL Sorgusu Üret")


def urun_ekle(urunler):
    aciklama = input("Ürün açıklaması: ").strip()
    if not aciklama:
        print("[HATA] Ürün açıklaması boş olamaz.")
        return
    fiyat = sayi_al("Ürün fiyatı: ", "float")
    stok = sayi_al("Stok miktarı: ", "int")

    print("\n[API] Ürün bilgileri oluşturuluyor...")
    try:
        veri = e_ticaret_api_simulasyonu(aciklama)
    except errors.APIError as e:
        print(f"[API HATASI] {e}")
        print("[BİLGİ] Ürün kaydedilmedi.")
        return
    except ValueError as e:
        print(f"[HATA] {e}")
        print("[BİLGİ] Ürün kaydedilmedi.")
        return
    except Exception as e:
        print(f"[SİSTEM HATASI] Beklenmeyen bir hata oluştu: {e}")
        print("[BİLGİ] Ürün kaydedilmedi.")
        return

    urun = {
        "urun_kodu": yeni_urun_kodu(urunler),
        "urun_adi": veri["urun_adi"],
        "kategori": veri["kategori"],
        "seo_etiketleri": veri["seo_etiketleri"],
        "satis_aciklamasi": veri["satis_aciklamasi"],
        "fiyat": fiyat,
        "stok": stok,
    }
    urunler.append(urun)

    if urunleri_kaydet(urunler):
        print("[BAŞARILI] Ürün kaydedildi.")
        urun_yazdir(urun)
        stok_uyarisi(stok)
    else:
        urunler.pop()
        print("[BİLGİ] Ürün kaydedilemedi.")


def urunleri_listele(urunler):
    if not urunler:
        print("[BİLGİ] Kayıtlı ürün bulunmuyor.")
        return
    print(f"\n--- Toplam {len(urunler)} ürün ---")
    for urun in urunler:
        print("-" * 40)
        urun_yazdir(urun)
        stok_uyarisi(urun["stok"])
    print("-" * 40)


def urun_ara(urunler):
    aranan = input("Aranacak ürün: ").strip()
    if not aranan:
        print("[HATA] Arama metni boş olamaz.")
        return
    aranan_kucuk = tr_normallestir(aranan)
    bulunanlar = [
        u
        for u in urunler
        if aranan_kucuk in tr_normallestir(u["urun_adi"])
        or aranan_kucuk in tr_normallestir(u["urun_kodu"])
    ]
    if not bulunanlar:
        print("[SONUÇ] Eşleşen ürün bulunamadı.")
        return
    kodlar = ", ".join(u["urun_kodu"] for u in bulunanlar)
    print(f"[SONUÇ] {len(bulunanlar)} ürün bulundu: {kodlar}")
    for urun in bulunanlar:
        print("-" * 40)
        urun_yazdir(urun)
        stok_uyarisi(urun["stok"])


def stok_guncelle(urunler):
    kod = input("Ürün kodu: ").strip().upper()
    urun = next((u for u in urunler if u["urun_kodu"] == kod), None)
    if urun is None:
        print("[HATA] Bu koda sahip bir ürün bulunamadı.")
        return
    yeni_stok = sayi_al("Yeni stok miktarı: ", "int")
    eski_stok = urun["stok"]
    urun["stok"] = yeni_stok
    if urunleri_kaydet(urunler):
        print(
            f"[BAŞARILI] Stok {eski_stok} -> {yeni_stok} olarak güncellendi.")
        stok_uyarisi(yeni_stok)
    else:
        urun["stok"] = eski_stok
        print("[BİLGİ] Stok güncellenemedi.")


# ----------------------------------------------------------------------
# 4) ANA PROGRAM
# ----------------------------------------------------------------------
def main():
    turkce_ayarla()
    urunler = urunleri_yukle()

    while True:
        menu_goster()
        secim = input("Seçiminiz: ").strip()

        if secim == "1":
            urun_ekle(urunler)
        elif secim == "2":
            urunleri_listele(urunler)
        elif secim == "3":
            urun_ara(urunler)
        elif secim == "4":
            stok_guncelle(urunler)
        elif secim == "5":
            print("Programdan çıkılıyor. Görüşmek üzere!")
            break
        elif secim == "6":
            sql_sorgusu_uret()
        else:
            print("[HATA] Geçersiz seçim. Lütfen 1-6 arasında bir sayı girin.")


if __name__ == "__main__":
    main()
