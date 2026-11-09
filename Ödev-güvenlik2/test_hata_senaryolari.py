"""Gemini'ye bağlanmadan (sahte istemci ile) hata senaryolarını ve JSON akışını doğrular."""
import json
import tempfile
from pathlib import Path

import security_analyzer as sa


class SahteYanit:
    def __init__(self, text): self.text = text

class SahteModeller:
    def __init__(self, davranis): self.davranis = davranis
    def generate_content(self, **kw):
        if isinstance(self.davranis, Exception):
            raise self.davranis
        return SahteYanit(self.davranis)

class SahteClient:
    def __init__(self, davranis): self.models = SahteModeller(davranis)


def dene(ad, client, yol, beklenen_hata=None, rapor=None):
    try:
        sonuc = sa.dosyayi_analiz_et(client, yol, rapor)
        ok = beklenen_hata is None
        mesaj = f"{len(sonuc)} bulgu"
    except sa.AnalizHatasi as e:
        ok = beklenen_hata is not None and beklenen_hata in str(e)
        mesaj = str(e)
    print(f"{'GEÇTİ' if ok else 'KALDI'} | {ad}: {mesaj}\n")
    return ok


gecerli = json.dumps({"findings": [{
    "type": "Path Traversal", "severity": "high", "evidence": "open(base_dir + filename)",
    "cause": "Doğrulama yok", "impact": "Yetkisiz dosya erişimi", "secure_code": "# güvenli"}]})

with tempfile.TemporaryDirectory() as t:
    t = Path(t)
    bos = t / "bos.py"; bos.write_text("  \n", encoding="utf-8")
    txt = t / "not.txt"; txt.write_text("x", encoding="utf-8")
    kod = t / "k.py"; kod.write_text("print('merhaba')", encoding="utf-8")
    ikili = t / "bin.py"; ikili.write_bytes(b"\xff\xfe\x00\x81")
    r = t / "reports" / "a.json"
    sonuc = []
    sonuc.append(dene("olmayan dosya", SahteClient(gecerli), str(t / "yok.py"), "bulunamadı"))
    sonuc.append(dene("boş dosya", SahteClient(gecerli), str(bos), "boş"))
    sonuc.append(dene(".py olmayan", SahteClient(gecerli), str(txt), ".py"))
    sonuc.append(dene("UTF-8 olmayan", SahteClient(gecerli), str(ikili), "UTF-8"))
    sonuc.append(dene("bağlantı hatası", SahteClient(ConnectionError("x")), str(kod), "bağlanılamadı", r))
    sonuc.append(dene("geçersiz JSON", SahteClient("bu json değil"), str(kod), "geçerli JSON değil", r))
    sonuc.append(dene("eksik alan", SahteClient('{"findings":[{"type":"x"}]}'), str(kod), "eksik alan", r))
    sonuc.append(dene("geçersiz seviye", SahteClient(gecerli.replace("high", "süper")), str(kod), "risk seviyesi", r))
    sonuc.append(not r.exists()); print(f"{'GEÇTİ' if not r.exists() else 'KALDI'} | hata durumlarında rapor kaydedilmedi\n")
    sonuc.append(dene("geçerli yanıt", SahteClient(gecerli), str(kod), None, r))
    d = json.loads(r.read_text(encoding="utf-8"))
    sonuc.append(d["finding_count"] == 1 and d["findings"][0]["severity"] == "Yüksek")
    print("GEÇTİ | rapor yapısı doğru (severity 'Yüksek'e normalize edildi)\n" if sonuc[-1] else "KALDI | rapor yapısı\n")
    sonuc.append(dene("sıfır bulgu", SahteClient('{"findings": []}'), str(kod), None, r))
    d = json.loads(r.read_text(encoding="utf-8"))
    sonuc.append(d == {"file": kod.as_posix(), "finding_count": 0, "findings": []})
    print("GEÇTİ | sıfır bulgu raporu doğru\n" if sonuc[-1] else "KALDI | sıfır bulgu raporu\n")

print(f"SONUÇ: {sum(sonuc)}/{len(sonuc)} test geçti")
