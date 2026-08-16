# -*- coding: utf-8 -*-
"""Ders Seçim Paneli — komut satırı arayüzü.

    python panel.py               paneli aç (tarayıcıda)
    python panel.py guncelle      plan + bu dönem açılan dersleri yeniden çek
    python panel.py plan          sadece ders planını çek
    python panel.py dersler       sadece dönemlik açılan dersleri çek
    python panel.py ara kontrol   bölümünün planId'sini bul
    python panel.py alinan        alınan dersleri listele
    python panel.py alinan-ekle "KOM 505" --donem "2024-2025 Güz" --not AA
                                 (planda olmayan ders için: --ad "..." --kredi 3 --akts 7,5)
    python panel.py alinan-sil "KOM 505"
    python panel.py paketle       paylaşılabilir zip oluştur (kişisel veri hariç)
"""

from __future__ import annotations

import json
import shutil
import sys
import zipfile
from pathlib import Path

import obs_client as obs
import server

KOK = Path(__file__).resolve().parent
VERI = KOK / "veri"
HAM = VERI / "ham"
SABLON = KOK / "sablon"

VARSAYILAN_AYARLAR = {
    "bolum": "",
    "planId": 0,
    "seviye": "LU",
    "ekBransKodlari": [],
}


# ------------------------------------------------------------------ yardımcılar


def ayarlari_oku() -> dict:
    ayarlar = {**VARSAYILAN_AYARLAR, **server.json_oku(server.AYARLAR, {})}
    if not ayarlar.get("planId"):
        cik(
            "veri/ayarlar.json içinde 'planId' boş.\n"
            "  Bölümünün plan numarasını bulmak için:  python panel.py ara <bölüm adı>\n"
            "  Örnek:  python panel.py ara kontrol"
        )
    return ayarlar


def cik(mesaj: str, kod: int = 1):
    print(f"\n  HATA: {mesaj}\n")
    sys.exit(kod)


def baslik(metin: str):
    print(f"\n{metin}\n" + "-" * max(12, len(metin)))


# --------------------------------------------------------------------- komutlar


def komut_plan(ayarlar: dict | None = None) -> dict:
    ayarlar = ayarlar or ayarlari_oku()
    baslik(f"Ders planı çekiliyor — planId {ayarlar['planId']}")
    plan = obs.ders_plani_cek(ayarlar["planId"], HAM)
    server.json_yaz(server.PLAN, plan)

    if not ayarlar.get("bolum"):
        ayarlar["bolum"] = plan["planAdi"]
        server.json_yaz(server.AYARLAR, ayarlar)

    toplam = sum(len(g["dersler"]) for g in plan["gereksinimler"])
    print(f"\n  {len(plan['gereksinimler'])} gereksinim, {toplam} ders → veri/plan.json")
    return plan


def komut_dersler(ayarlar: dict | None = None) -> dict:
    if ayarlar is None:
        ayarlari_oku()  # planId eksikse anlaşılır bir hatayla dur

    baslik("Bu dönem açılan dersler çekiliyor")
    dersler = server.dersleri_yenile(log=print)
    print(
        f"\n  {dersler['donem']} — {len(dersler['dersler'])} kayıt (CRN) "
        "→ veri/dersler.json"
    )
    return dersler


def komut_guncelle():
    ayarlar = ayarlari_oku()
    komut_plan(ayarlar)
    komut_dersler(ayarlar)
    print("\n  Güncelleme tamam. Paneli açmak için:  python panel.py\n")


def komut_ara(argumanlar: list[str]):
    """python panel.py ara kontrol [--seviye LU]"""
    seviye = "LU"
    kelimeler = []
    i = 0
    while i < len(argumanlar):
        if argumanlar[i] == "--seviye" and i + 1 < len(argumanlar):
            seviye = argumanlar[i + 1].upper()
            i += 2
        else:
            kelimeler.append(argumanlar[i])
            i += 1

    arama = " ".join(kelimeler).strip()
    if not arama:
        cik('Aranacak bölüm adı gerekli. Örnek:  python panel.py ara kontrol --seviye LU')

    baslik(f"'{arama}' aranıyor (seviye: {seviye})")
    print("  Tüm fakülte/enstitüler taranıyor, bu 10-20 saniye sürebilir ...\n")
    sonuc = obs.ders_planlarini_ara(arama, seviye)

    if not sonuc:
        print(
            "\n  Sonuç yok. Seviyeyi kontrol et:\n"
            "    LS  = Lisans      LU = Yüksek Lisans/Doktora\n"
            "    OL  = Ön Lisans   LUI = Lisansüstü 2. Öğretim\n"
            "  Elle de bakabilirsin: https://obs.itu.edu.tr/public/DersPlan\n"
            "  Plan sayfasının adresindeki son sayı planId'dir:\n"
            "    .../DersPlan/DersPlanDetay/2561  ->  planId = 2561"
        )
        return

    print()
    for kayit in sonuc:
        print(f"  {kayit['programAdi']}  [{kayit['programKodu']}]  — {kayit['birim']}")
        for plan in kayit["planlar"]:
            isaret = "  <- en güncel" if plan is kayit["planlar"][0] else ""
            print(f"      planId {plan['planId']:>6}   {plan['aciklama'][:95]}{isaret}")
        print()
    print("  Doğru planId'yi veri/ayarlar.json içindeki 'planId' alanına yaz,")
    print("  sonra:  python panel.py guncelle\n")


def komut_alinan_listele():
    alinan = server.json_oku(server.ALINAN, {"alinan": []})["alinan"]
    baslik(f"Alınan dersler ({len(alinan)})")
    if not alinan:
        print("  Henüz kayıt yok.")
        return
    for ders in alinan:
        satir = f"  {ders.get('kod', ''):<10} {ders.get('ad', '')}"
        ekler = [ders.get("donem", ""), ders.get("harfNotu", "")]
        ek = "  ".join(e for e in ekler if e)
        print(satir + (f"   [{ek}]" if ek else ""))


def _plandan_ders_bul(kod: str) -> dict | None:
    plan = server.json_oku(server.PLAN, None)
    if not plan:
        return None
    for gereksinim in plan["gereksinimler"]:
        for ders in gereksinim["dersler"]:
            if ders["kod"] == kod:
                return ders
    return None


def komut_alinan_ekle(argumanlar: list[str]):
    if not argumanlar:
        cik('Ders kodu gerekli. Örnek:  python panel.py alinan-ekle "KOM 505" --donem "2024-2025 Güz" --not AA')

    kod = obs.ders_kodu_duzelt(argumanlar[0])
    secenekler = {}
    i = 1
    while i < len(argumanlar) - 1:
        if argumanlar[i].startswith("--"):
            secenekler[argumanlar[i][2:]] = argumanlar[i + 1]
            i += 2
        else:
            i += 1

    alinan = server.json_oku(server.ALINAN, {"alinan": []})["alinan"]
    if any(d.get("kod") == kod for d in alinan):
        print(f"\n  {kod} zaten listede.\n")
        return

    def sayi(deger):
        """'7,5' / '7.5' -> 7.5 ; verilmemişse None"""
        if deger is None:
            return None
        try:
            return float(str(deger).replace(",", "."))
        except ValueError:
            return None

    plandaki = _plandan_ders_bul(kod)
    kayit = {
        "kod": kod,
        "ad": secenekler.get("ad") or (plandaki or {}).get("ad", ""),
        "kredi": sayi(secenekler.get("kredi")) or (plandaki or {}).get("kredi"),
        "akts": sayi(secenekler.get("akts")) or (plandaki or {}).get("akts"),
        "donem": secenekler.get("donem", ""),
        "harfNotu": secenekler.get("not", ""),
    }
    alinan.append(kayit)
    server.json_yaz(server.ALINAN, {"alinan": alinan})
    print(f"\n  Eklendi: {kod} {kayit['ad']}  (toplam {len(alinan)})\n")
    if plandaki is None:
        print("  Not: bu ders planda bulunamadı, sadece kayıt olarak tutuluyor.\n")


def komut_alinan_sil(argumanlar: list[str]):
    if not argumanlar:
        cik('Ders kodu gerekli. Örnek:  python panel.py alinan-sil "KOM 505"')
    kod = obs.ders_kodu_duzelt(argumanlar[0])
    alinan = server.json_oku(server.ALINAN, {"alinan": []})["alinan"]
    kalan = [d for d in alinan if d.get("kod") != kod]
    if len(kalan) == len(alinan):
        print(f"\n  {kod} listede yok.\n")
        return
    server.json_yaz(server.ALINAN, {"alinan": kalan})
    print(f"\n  Silindi: {kod}  (kalan {len(kalan)})\n")


def komut_paketle():
    """Kişisel veriyi dışarıda bırakarak paylaşılabilir bir zip üretir."""
    hedef = KOK.parent / f"{KOK.name}-paylasim.zip"
    haric_klasor = {"veri", "__pycache__", ".git", ".venv"}

    baslik("Paylaşım paketi hazırlanıyor")
    with zipfile.ZipFile(hedef, "w", zipfile.ZIP_DEFLATED) as zip_dosyasi:
        for yol in KOK.rglob("*"):
            if not yol.is_file():
                continue
            goreli = yol.relative_to(KOK)
            if set(goreli.parts) & haric_klasor or goreli.suffix == ".zip":
                continue
            zip_dosyasi.write(yol, goreli.as_posix())
        # sablon/ içindeki boş dosyalar karşı tarafta veri/ olarak açılsın
        for yol in SABLON.glob("*.json"):
            zip_dosyasi.write(yol, f"veri/{yol.name}")

    boyut = hedef.stat().st_size / 1024
    print(f"  Oluşturuldu: {hedef}  ({boyut:.0f} KB)")
    print("  İçinde senin plan/alınan ders verilerin YOK; karşı taraf sıfırdan kurar.\n")


def komut_sifirla(argumanlar: list[str]):
    """Alınan dersler ve seçimi boşaltır.

    --hepsi verilirse ayarlar da (planId dahil) şablondaki boş hale döner.
    """
    hepsi = "--hepsi" in argumanlar
    dosyalar = ["alinan.json", "secim.json"] + (["ayarlar.json"] if hepsi else [])

    baslik("Veri sıfırlanıyor")
    for ad in dosyalar:
        kaynak = SABLON / ad
        if kaynak.is_file():
            VERI.mkdir(parents=True, exist_ok=True)
            shutil.copy2(kaynak, VERI / ad)
            print(f"  {ad} sıfırlandı")
    if not hepsi:
        print("\n  (ayarlar.json ve çekilmiş plan/ders verisi korundu.")
        print("   Hepsini sıfırlamak için:  python panel.py sifirla --hepsi)")
    print()


YARDIM = __doc__


def main(argv: list[str]):
    komut = (argv[0] if argv else "basla").lower()
    argumanlar = argv[1:]

    if komut in ("-h", "--help", "yardim"):
        print(YARDIM)
    elif komut == "plan":
        komut_plan()
    elif komut == "dersler":
        komut_dersler()
    elif komut == "guncelle":
        komut_guncelle()
    elif komut == "ara":
        komut_ara(argumanlar)
    elif komut == "alinan":
        komut_alinan_listele()
    elif komut == "alinan-ekle":
        komut_alinan_ekle(argumanlar)
    elif komut == "alinan-sil":
        komut_alinan_sil(argumanlar)
    elif komut == "paketle":
        komut_paketle()
    elif komut == "sifirla":
        komut_sifirla(argumanlar)
    elif komut in ("basla", "sunucu", "ac"):
        if not server.PLAN.is_file():
            print(
                "\n  Henüz veri yok. Önce:  python panel.py guncelle"
                "\n  (Panel yine de açılıyor.)"
            )
        server.calistir()
    else:
        print(f"\n  Bilinmeyen komut: {komut}")
        print(YARDIM)
        sys.exit(2)


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except obs.OBSHatasi as hata:
        cik(str(hata))
