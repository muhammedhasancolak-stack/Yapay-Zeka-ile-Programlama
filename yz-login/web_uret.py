"""
Yapay Zekâ Destekli Web Sayfası Üretici
Gemini API ile Login, Forgot Password ve Sign Up sayfalarını üretir
ve index.html, forgot_password.html, signup.html dosyalarına kaydeder.
"""
import os
import re

import google.generativeai as genai

# API anahtarı: ortam değişkeninden okunur, yoksa aşağıdaki yer tutucu kullanılır.
# (Anahtarı GitHub'a yüklemeyin.)
API_ANAHTARI = os.getenv("GEMINI_API_KEY", "GEMINI_API_ANAHTARINIZI_BURAYA_YAZIN")
MODEL_ADI = "gemini-3.5-flash"

# Dosya adı -> ayıraç etiketi
dosyalar = {
    "index.html": "===INDEX.HTML===",
    "forgot_password.html": "===FORGOT_PASSWORD.HTML===",
    "signup.html": "===SIGNUP.HTML===",
}

sistem_mesaji = """Sen deneyimli bir ön yüz (front-end) geliştiricisisin.
Kullanıcının tasarım talebine göre TAM OLARAK üç adet bağımsız HTML sayfası üret:
1) Login sayfası (index.html): E-posta alanı, Şifre alanı, "Giriş Yap" butonu,
   "Şifremi unuttum" bağlantısı (forgot_password.html), "Üye Ol" bağlantısı (signup.html).
2) Şifremi unuttum sayfası (forgot_password.html): "Şifremi unuttum" başlığı,
   E-posta adresi alanı, "Şifre sıfırlama bağlantısı gönder" butonu,
   "Giriş sayfasına dön" bağlantısı (index.html).
3) Üye Ol sayfası (signup.html): Ad Soyad, E-posta, Şifre, Şifre tekrar alanları,
   "Üye Ol" butonu, "Giriş sayfasına dön" bağlantısı (index.html).

TASARIM KURALLARI:
- Modern, profesyonel, mobil uyumlu (responsive) ve karanlık mod (Dark Mode) tasarım kullan.
- Üç sayfa aynı tasarım dilini kullansın.
- CSS ve JavaScript harici dosya olmasın; doğrudan her HTML dosyasının içine
  <style> ve <script> olarak göm.
- Sayfalar arası geçişler çalışan href bağlantılarıyla kurulsun.
- Butonlarda hover durumunda parlama (glow) animasyonu olsun.
- JavaScript ile form doğrulaması ekle: boş alan kontrolü, e-posta formatı kontrolü,
  şifre eşleşme kontrolü (Üye Ol sayfasında).
- Şifre alanlarında şifre göster/gizle özelliği olsun.

ÇIKTI FORMATI (ÇOK ÖNEMLİ):
Yanıtı YALNIZCA aşağıdaki ayıraç etiketleriyle ver. Etiketlerin dışında hiçbir açıklama,
yorum veya Markdown yazma. Her etiketin altına o dosyanın tam HTML kodunu yaz:

===INDEX.HTML===
(index.html kodu)
===FORGOT_PASSWORD.HTML===
(forgot_password.html kodu)
===SIGNUP.HTML===
(signup.html kodu)
"""

tasarim_talebi = (
    "Modern, profesyonel, karanlık temalı bir üyelik sistemi oluştur. "
    "Siyah ve mavi neon renkler kullan. Login, Forgot Password ve Signup sayfaları "
    "aynı tasarım dilini kullansın. Sayfalar arasında geçişler çalışsın. "
    "Butonların üzerine gelindiğinde parlama efekti oluşsun."
)


def markdown_temizle(metin):
    """Olası Markdown kod bloklarını (```html ve ```) temizler."""
    return metin.replace("```html", "").replace("```", "").strip()


def yaniti_ayristir(sonuc):
    """Ayıraç etiketlerine göre yanıtı {dosya_adi: html_kodu} sözlüğüne böler."""
    # Her etiketin yanıttaki konumunu bul
    konumlar = []
    for dosya_adi, etiket in dosyalar.items():
        indeks = sonuc.find(etiket)
        if indeks == -1:
            raise ValueError(f"Yanıtta {etiket} etiketi bulunamadı.")
        konumlar.append((indeks, dosya_adi, etiket))
    konumlar.sort()

    # Her başlık aralığını kes ve markdown işaretlerini temizle
    sonuclar = {}
    for i, (baslangic, dosya_adi, etiket) in enumerate(konumlar):
        icerik_baslangic = baslangic + len(etiket)
        bitis = konumlar[i + 1][0] if i + 1 < len(konumlar) else len(sonuc)
        sonuclar[dosya_adi] = markdown_temizle(sonuc[icerik_baslangic:bitis])
    return sonuclar


def dosyalari_kaydet(sayfalar, klasor="."):
    """HTML kodlarını UTF-8 kodlamasıyla ilgili dosyalara kaydeder."""
    for dosya_adi, html_kodu in sayfalar.items():
        yol = os.path.join(klasor, dosya_adi)
        with open(yol, "w", encoding="utf-8") as dosya:
            dosya.write(html_kodu)
        print(f"Kaydedildi: {yol}")


def main():
    # 1) Gemini API bağlantısı
    genai.configure(api_key=API_ANAHTARI)
    model = genai.GenerativeModel(model_name=MODEL_ADI)

    # 2) Sistem mesajı + kullanıcı talebi -> API
    response = model.generate_content(
        sistem_mesaji + "\n\nKullanıcı talebi:\n" + tasarim_talebi,
        generation_config={"temperature": 0.5, "max_output_tokens": 16000},
    )
    sonuc = response.text

    # 3) Ayrıştırma ve kaydetme
    sayfalar = yaniti_ayristir(sonuc)
    dosyalari_kaydet(sayfalar)
    print("Tamamlandı: index.html, forgot_password.html, signup.html oluşturuldu.")


if __name__ == "__main__":
    main()
