# -*- coding: utf-8 -*-
"""İTÜ ÖBS (obs.itu.edu.tr) açık sayfalarından veri çeken katman.

Sadece Python standart kütüphanesini kullanır; kurulum gerektirmez.

Kullanılan uç noktalar
----------------------
1) Ders planı (bir kez / plan değişince):
   GET /public/DersPlan/DersPlanDetay/{planId}
       -> planın satırları; seçmeli satırlar bir "grupId"e link verir
   GET /public/DersPlan/_DersGrupSearch?grupId={grupId}
       -> o slota sayılan derslerin listesi

2) Dönemlik açılan dersler (her dönem):
   GET /public/DersProgram/GetAktifDonemByProgramSeviye?programSeviyeTipiAnahtari={LS|LU|...}
       -> {"aktifDonem": "2025-2026 Güz Dönemi"}
   GET /public/DersProgram/SearchBransKoduByProgramSeviye?programSeviyeTipiAnahtari={...}
       -> [{"bransKoduId": 66, "dersBransKodu": "KOM"}, ...]
   GET /public/DersProgram/DersProgramSearch?programSeviyeTipiAnahtari={...}&dersBransKoduId={id}
       -> CRN'li ders tablosu (HTML parça)
"""

from __future__ import annotations

import html as _html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

TABAN = "https://obs.itu.edu.tr"
BASLIKLAR = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
    "Accept-Language": "tr-TR,tr;q=0.9",
    "X-Requested-With": "XMLHttpRequest",
}

GUNLER = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]

# İTÜ ders kodu: 3 harfli branş + 3 haneli numara + isteğe bağlı E (İngilizce) eki
DERS_KODU_RE = re.compile(r"^([A-ZÇĞİÖŞÜ]{2,4})\s*(\d{3}[A-Z]?)$")


class OBSHatasi(RuntimeError):
    """ÖBS'ye ulaşılamadığında veya sayfa yapısı beklenenden farklı olduğunda."""


# ---------------------------------------------------------------- ağ katmanı


def _indir(url: str, deneme: int = 3) -> str:
    """URL'yi indirir, metni döndürür. Geçici hatalarda tekrar dener."""
    son_hata = None
    for i in range(deneme):
        try:
            istek = urllib.request.Request(url, headers=BASLIKLAR)
            with urllib.request.urlopen(istek, timeout=60) as yanit:
                return yanit.read().decode("utf-8", "replace")
        except (urllib.error.URLError, TimeoutError, OSError) as hata:
            son_hata = hata
            time.sleep(1.5 * (i + 1))
    raise OBSHatasi(f"İndirilemedi: {url}\n  sebep: {son_hata}")


def _ham_kaydet(ham_dizin: Path | None, ad: str, icerik: str) -> None:
    """Çekilen ham HTML/JSON'u diske yazar (hata ayıklama ve yeniden işleme için)."""
    if ham_dizin is None:
        return
    ham_dizin.mkdir(parents=True, exist_ok=True)
    (ham_dizin / ad).write_text(icerik, encoding="utf-8")


def _getir(url: str, ham_dizin: Path | None = None, ham_ad: str | None = None) -> str:
    icerik = _indir(url)
    if ham_ad:
        _ham_kaydet(ham_dizin, ham_ad, icerik)
    return icerik


# ------------------------------------------------------------- html ayrıştırma


def _metin(parca: str) -> str:
    """HTML parçasından düz metin üretir."""
    duz = re.sub(r"(?is)<[^>]+>", " ", parca)
    return re.sub(r"\s+", " ", _html.unescape(duz)).strip()


def _hucre(ham: str) -> dict:
    """Bir <td>/<th> içeriğini {metin, parcalar, link} olarak çözer.

    ÖBS aynı hücrede birden çok değeri <br> ile ayırıyor (ör. iki günlü dersin
    'Pazartesi<br>Salı' günü). 'parcalar' bu ayrımı korur.
    """
    parcalar = [_metin(p) for p in re.split(r"(?i)<br\s*/?>", ham)]
    parcalar = [p for p in parcalar if p]
    link = re.search(r"""(?is)href\s*=\s*["']([^"']+)["']""", ham)
    return {
        "metin": _metin(ham),
        "parcalar": parcalar,
        "link": _html.unescape(link.group(1)) if link else None,
    }


def _satirlari_coz(tablo: str) -> list[list[dict]]:
    """Bir tablonun veri satırlarını (başlık satırı hariç) hücre listesi olarak verir."""
    satirlar = []
    for tr in re.findall(r"(?is)<tr.*?</tr>", tablo):
        if re.search(r"(?is)<th[\s>]", tr):
            continue  # başlık satırı
        hucreler = re.findall(r"(?is)<td[^>]*>(.*?)</td>", tr)
        if hucreler:
            satirlar.append([_hucre(h) for h in hucreler])
    return satirlar


def _tablo_satirlari(belge: str, tablo_sirasi: int = 0) -> list[list[dict]]:
    """Belgedeki tek bir tablonun veri satırlarını verir."""
    tablolar = re.findall(r"(?is)<table.*?</table>", belge)
    if len(tablolar) <= tablo_sirasi:
        return []
    return _satirlari_coz(tablolar[tablo_sirasi])


def _tablolar_baslikli(belge: str) -> list[tuple[str, str]]:
    """[(başlık, tablo_html), ...] — her tabloyu kendi başlığıyla eşler.

    Lisans ders planlarında her yarıyıl ayrı bir tablodur ve başlık tablonun
    *içindedir* (<thead><tr><h2>1. Yarıyıl</h2></tr>). Lisansüstü planlarında
    tek tablo vardır ve böyle bir başlık yoktur; o zaman tablodan hemen önceki
    başlığa bakılır. İkisi de aynı biçimde ele alınabilsin diye.
    """
    sonuc = []
    son_konum = 0
    for eslesme in re.finditer(r"(?is)<table.*?</table>", belge):
        tablo = eslesme.group(0)

        ic = re.search(r"(?is)<(?:h[1-6]|caption)[^>]*>(.*?)</(?:h[1-6]|caption)>", tablo)
        baslik = _metin(ic.group(1)) if ic else ""

        if not baslik:
            onceki = re.findall(
                r"(?is)<(?:h[1-6]|caption)[^>]*>(.*?)</(?:h[1-6]|caption)>",
                belge[son_konum : eslesme.start()],
            )
            onceki = [_metin(b) for b in onceki if _metin(b)]
            baslik = onceki[-1] if onceki else ""

        sonuc.append((baslik, tablo))
        son_konum = eslesme.end()
    return sonuc


def _sayi(metin: str) -> float | None:
    """'7,5' / '3' -> 7.5 / 3.0 ; boş veya '-' -> None"""
    metin = (metin or "").strip().replace(",", ".")
    try:
        return float(metin)
    except ValueError:
        return None


def _tam_sayi(metin: str) -> int | None:
    deger = _sayi(metin)
    return int(deger) if deger is not None else None


def ders_kodu_duzelt(ham: str) -> str:
    """'KOM  501E' -> 'KOM 501E' (tek boşluk, büyük harf)."""
    return re.sub(r"\s+", " ", (ham or "").strip().upper())


def brans_kodu(ders_kodu: str) -> str:
    """'KOM 501E' -> 'KOM'"""
    return ders_kodu_duzelt(ders_kodu).split(" ")[0] if ders_kodu else ""


# ------------------------------------------------------------------ ders planı


def _grup_derslerini_cek(
    grup_id: int, ham_dizin: Path | None, onbellek: dict | None = None
) -> list[dict]:
    """Bir seçmeli grubun (grupId) içindeki dersleri döndürür.

    Lisans planlarında aynı grup birden çok yarıyılda geçebiliyor; aynı sayfayı
    tekrar tekrar indirmemek için önbellek kullanılır.
    """
    if onbellek is not None and grup_id in onbellek:
        return onbellek[grup_id]

    belge = _getir(
        f"{TABAN}/public/DersPlan/_DersGrupSearch?grupId={grup_id}",
        ham_dizin,
        f"grup-{grup_id}.html",
    )
    dersler = []
    for satir in _tablo_satirlari(belge):
        if len(satir) < 4:
            continue
        parcalar = satir[0]["parcalar"]
        if not parcalar:
            continue
        kod = ders_kodu_duzelt(parcalar[0])
        if not DERS_KODU_RE.match(kod):
            continue
        dersler.append(
            {
                "kod": kod,
                "ad": parcalar[1] if len(parcalar) > 1 else "",
                "dil": satir[1]["metin"],
                "kredi": _sayi(satir[2]["metin"]),
                "akts": _sayi(satir[3]["metin"]),
            }
        )

    if onbellek is not None:
        onbellek[grup_id] = dersler
    return dersler


def ders_plani_cek(plan_id: int, ham_dizin: Path | None = None, log=print) -> dict:
    """Ders planını (mezuniyet gereksinimleri + her slota sayılan dersler) çeker."""
    log(f"  Ders planı çekiliyor (planId={plan_id}) ...")
    belge = _getir(
        f"{TABAN}/public/DersPlan/DersPlanDetay/{plan_id}",
        ham_dizin,
        f"plan-{plan_id}.html",
    )

    baslik = re.search(r"(?is)<h[12][^>]*>(.*?)</h[12]>", belge)
    plan_adi = _metin(baslik.group(1)) if baslik else f"Plan {plan_id}"

    # Lisans planları yarıyıl başına bir tablo kullanır; lisansüstünde tek tablo
    # vardır. Ders satırı içermeyen tablolar (ör. "İlişkili Programlar") kendi
    # kendine elenir, çünkü o satırların ilk hücresinde ders/grup linki yoktur.
    gereksinimler = []
    grup_onbellegi: dict[int, list[dict]] = {}

    for tablo_basligi, tablo in _tablolar_baslikli(belge):
        yariyil = tablo_basligi if re.search(r"(?i)yar[ıi]y[ıi]l", tablo_basligi) else ""
        tablo_gereksinimleri = []

        for satir in _satirlari_coz(tablo):
            if len(satir) < 6:
                continue
            ilk, ad = satir[0], satir[1]["metin"]
            link = ilk["link"] or ""
            if not link:
                continue  # başlık / toplam satırı: ilk hücrede link olmaz

            ortak = {
                "ad": ad,
                "yariyil": yariyil,
                "zorunlulukTipi": satir[3]["metin"],  # Z / S
                "kredi": _sayi(satir[4]["metin"]),
                "akts": _sayi(satir[5]["metin"]),
                "tur": satir[9]["metin"] if len(satir) > 9 else "",
            }

            grup = re.search(r"grupId=(\d+)", link)
            if grup:
                grup_id = int(grup.group(1))
                dersler = _grup_derslerini_cek(grup_id, ham_dizin, grup_onbellegi)
                tablo_gereksinimleri.append(
                    {
                        **ortak,
                        "grupId": grup_id,
                        "sabit": False,
                        # Boş grup = "Seçime Bağlı": plana özel liste yok, seviyeye
                        # uygun her kredili ders sayılır.
                        "serbest": len(dersler) == 0,
                        "dersler": dersler,
                    }
                )
            elif "DersBilgi" in link:
                # Doğrudan bir derse bağlı satır (ör. Tez Çalışması, FIZ 101)
                kod = ders_kodu_duzelt(ilk["metin"])
                tablo_gereksinimleri.append(
                    {
                        **ortak,
                        "grupId": None,
                        "sabit": True,
                        "serbest": False,
                        "dersler": [
                            {
                                "kod": kod,
                                "ad": ad,
                                "dil": satir[2]["metin"],
                                "kredi": ortak["kredi"],
                                "akts": ortak["akts"],
                            }
                        ],
                    }
                )

        if tablo_gereksinimleri:
            log(f"    {yariyil or 'Plan'}: {len(tablo_gereksinimleri)} satır")
            gereksinimler.extend(tablo_gereksinimleri)

    if not gereksinimler:
        raise OBSHatasi(
            f"planId={plan_id} için ders planı tablosu bulunamadı. "
            "Plan numarası doğru mu? (obs.itu.edu.tr/public/DersPlan)"
        )

    return {
        "planId": plan_id,
        "planAdi": plan_adi,
        "kaynak": f"{TABAN}/public/DersPlan/DersPlanDetay/{plan_id}",
        "cekilme": time.strftime("%Y-%m-%d %H:%M"),
        "gereksinimler": gereksinimler,
    }


def plan_ders_kodlari(plan: dict) -> dict[str, list[str]]:
    """Plandaki her ders kodunun hangi gereksinim slotlarına sayıldığını verir."""
    esleme: dict[str, list[str]] = {}
    for gereksinim in plan["gereksinimler"]:
        for ders in gereksinim["dersler"]:
            esleme.setdefault(ders["kod"], [])
            if gereksinim["ad"] not in esleme[ders["kod"]]:
                esleme[ders["kod"]].append(gereksinim["ad"])
    return esleme


# ------------------------------------------------------- dönemlik ders programı


def aktif_donem(seviye: str) -> str:
    ham = _indir(
        f"{TABAN}/public/DersProgram/GetAktifDonemByProgramSeviye"
        f"?programSeviyeTipiAnahtari={seviye}"
    )
    try:
        return json.loads(ham).get("aktifDonem", "").strip() or "Bilinmiyor"
    except json.JSONDecodeError:
        return "Bilinmiyor"


def brans_kodu_haritasi(seviye: str) -> dict[str, int]:
    """{'KOM': 66, 'MAT': 26, ...} — ders programı sorgusu için gereken id'ler."""
    ham = _indir(
        f"{TABAN}/public/DersProgram/SearchBransKoduByProgramSeviye"
        f"?programSeviyeTipiAnahtari={seviye}"
    )
    try:
        liste = json.loads(ham)
    except json.JSONDecodeError as hata:
        raise OBSHatasi(f"Branş kodu listesi okunamadı: {hata}") from hata
    return {str(x["dersBransKodu"]).strip().upper(): int(x["bransKoduId"]) for x in liste}


def _slotlari_coz(satir: list[dict]) -> list[dict]:
    """Bina/Gün/Saat/Derslik hücrelerini paralel çözerek ders saatlerini üretir."""
    binalar = satir[5]["parcalar"]
    gunler = satir[6]["parcalar"]
    saatler = satir[7]["parcalar"]
    derslikler = satir[8]["parcalar"]

    slotlar = []
    for i, gun in enumerate(gunler):
        gun = gun.strip()
        if gun not in GUNLER:
            continue  # '----' gibi programsız kayıtlar
        saat = saatler[i] if i < len(saatler) else ""
        baslangic, _, bitis = saat.partition("/")
        slotlar.append(
            {
                "gun": gun,
                "baslangic": baslangic.strip(),
                "bitis": bitis.strip(),
                "bina": binalar[i] if i < len(binalar) else "",
                "derslik": derslikler[i] if i < len(derslikler) else "",
            }
        )
    return slotlar


def ders_programi_cek(
    seviye: str, kod: str, brans_id: int, ham_dizin: Path | None = None
) -> list[dict]:
    """Bir branş kodunun bu dönem açılan tüm şubelerini (CRN) döndürür."""
    belge = _getir(
        f"{TABAN}/public/DersProgram/DersProgramSearch"
        f"?programSeviyeTipiAnahtari={seviye}&dersBransKoduId={brans_id}",
        ham_dizin,
        f"program-{seviye}-{kod}.html",
    )

    dersler = []
    for satir in _tablo_satirlari(belge):
        if len(satir) < 11:
            continue
        crn = satir[0]["metin"]
        if not crn.isdigit():
            continue
        dersler.append(
            {
                "crn": crn,
                "kod": ders_kodu_duzelt(satir[1]["metin"]),
                "ad": satir[2]["metin"],
                "yontem": satir[3]["metin"],
                "ogretimUyesi": satir[4]["metin"],
                "slotlar": _slotlari_coz(satir),
                "kontenjan": _tam_sayi(satir[9]["metin"]) or 0,
                "yazilan": _tam_sayi(satir[10]["metin"]) or 0,
                "rezervasyon": satir[11]["metin"] if len(satir) > 11 else "",
                "programlar": satir[12]["metin"] if len(satir) > 12 else "",
                "onsart": satir[13]["metin"] if len(satir) > 13 else "",
            }
        )
    return dersler


def donem_derslerini_topla(
    plan: dict,
    seviye: str,
    ek_brans_kodlari: list[str] | None = None,
    ham_dizin: Path | None = None,
    log=print,
) -> dict:
    """Sadece plandaki derslerin bu dönem açılan şubelerini toplar.

    Plandan hangi branş kodlarının gerektiği çıkarılır (ör. KOM, ELE, MKM);
    yalnızca o branşların ders programı indirilir ve plandaki kodlara göre
    süzülür. 'ek_brans_kodlari' ile serbest seçmeli için ek branşlar eklenebilir.
    """
    ek_brans_kodlari = [k.strip().upper() for k in (ek_brans_kodlari or []) if k.strip()]
    kod_eslemesi = plan_ders_kodlari(plan)
    plan_branslari = sorted({brans_kodu(k) for k in kod_eslemesi if brans_kodu(k)})
    istenen = sorted(set(plan_branslari) | set(ek_brans_kodlari))

    log(f"  Aktif dönem sorgulanıyor ({seviye}) ...")
    donem = aktif_donem(seviye)
    log(f"    Dönem: {donem}")

    harita = brans_kodu_haritasi(seviye)
    bulunamayan = [k for k in istenen if k not in harita]
    if bulunamayan:
        log(f"    ! {seviye} seviyesinde bulunamayan branş kodları: {', '.join(bulunamayan)}")

    dersler: list[dict] = []
    for kod in istenen:
        if kod not in harita:
            continue
        log(f"  {kod} ders programı çekiliyor ...")
        acilanlar = ders_programi_cek(seviye, kod, harita[kod], ham_dizin)
        ek = 0
        for ders in acilanlar:
            gruplar = kod_eslemesi.get(ders["kod"], [])
            planda_var = bool(gruplar)
            # Plandaki dersler her zaman alınır. Ek branş kodlarından gelenler
            # ise yalnızca serbest seçmeli adayı olarak eklenir.
            if not planda_var and kod not in ek_brans_kodlari:
                continue
            ders["gereksinimler"] = gruplar
            ders["plandaVar"] = planda_var
            dersler.append(ders)
            ek += 1
        log(f"    {ek} / {len(acilanlar)} kayıt alındı")

    dersler.sort(key=lambda d: (d["kod"], d["crn"]))
    return {
        "donem": donem,
        "seviye": seviye,
        "bransKodlari": istenen,
        "cekilme": time.strftime("%Y-%m-%d %H:%M"),
        "dersler": dersler,
    }


# --------------------------------------------------------------- plan arama
#
# planId'yi bulma zinciri:
#   1) /public/DersPlan sayfasındaki akademik birim (fakülte/enstitü) listesi
#   2) POST GetAkademikProgramByBirimIdAndPlanTipi  -> o birimdeki programlar
#   3) GET  DersPlanlariList?PlanTipiKodu=..&programKodu=..  -> plan sürümleri
#
# Not: lisansüstü programların tamamı "Lisansüstü Eğitim Enstitüsü" (birimId 33)
# ve benzeri enstitüler altındadır, fakülteler altında değil.

PLAN_TIPLERI = {
    "OL": "on-lisans",
    "LS": "lisans",
    "LU": "yuksek-lisans",
    "LUI": "yuksek-lisans",
}


def _gonder(url: str, veri: dict) -> str:
    govde = urllib.parse.urlencode(veri, encoding="utf-8").encode()
    basliklar = {
        **BASLIKLAR,
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    }
    istek = urllib.request.Request(url, data=govde, headers=basliklar)
    try:
        with urllib.request.urlopen(istek, timeout=60) as yanit:
            return yanit.read().decode("utf-8", "replace")
    except (urllib.error.URLError, TimeoutError, OSError) as hata:
        raise OBSHatasi(f"İstek başarısız: {url}\n  sebep: {hata}") from hata


def akademik_birimler() -> list[dict]:
    """Fakülte / enstitü listesi: [{'id': '33', 'ad': 'Lisansüstü Eğitim Enstitüsü'}]"""
    belge = _indir(f"{TABAN}/public/DersPlan")
    secim = re.search(r'(?is)<select[^>]*id="akademikBirimId".*?</select>', belge)
    if not secim:
        raise OBSHatasi("Akademik birim listesi bulunamadı (sayfa yapısı değişmiş olabilir).")
    birimler = []
    for deger, metin in re.findall(
        r'(?is)<option[^>]*value="([^"]*)"[^>]*>(.*?)</option>', secim.group(0)
    ):
        if deger.strip():
            birimler.append({"id": deger.strip(), "ad": _metin(metin)})
    return birimler


def akademik_programlar(birim_id: str, plan_tipi: str) -> list[dict]:
    """Bir birimdeki programlar: [{'programKodu': 'KOM_KO_YL', 'programAdi': '...'}]"""
    ham = _gonder(
        f"{TABAN}/public/DersPlan/GetAkademikProgramByBirimIdAndPlanTipi",
        {"birimId": birim_id, "planTipiKodu": plan_tipi},
    )
    try:
        return json.loads(ham)
    except json.JSONDecodeError:
        return []


def program_planlari(program_kodu: str, plan_tipi: str) -> list[dict]:
    """Bir programın plan sürümleri: [{'planId': 2561, 'aciklama': '... sonrası'}]

    Aynı programın birden çok plan sürümü olabilir (eski/yeni müfredat);
    genelde en güncel olanı, yani en büyük planId'yi seçmek gerekir.
    """
    belge = _indir(
        f"{TABAN}/public/DersPlan/DersPlanlariList"
        f"?PlanTipiKodu={urllib.parse.quote(plan_tipi)}"
        f"&programKodu={urllib.parse.quote(program_kodu)}"
    )
    planlar = []
    for satir in re.findall(r"(?is)<tr.*?</tr>", belge):
        bag = re.search(r"(?i)DersPlanDetay/(\d+)", satir)
        if not bag:
            continue
        hucreler = [_metin(h) for h in re.findall(r"(?is)<td[^>]*>(.*?)</td>", satir)]
        aciklama = " — ".join(h for h in hucreler if h and h.lower() != "detay")
        planlar.append({"planId": int(bag.group(1)), "aciklama": aciklama})
    planlar.sort(key=lambda p: p["planId"], reverse=True)
    return planlar


def ders_planlarini_ara(arama: str, seviye: str = "LU", log=print) -> list[dict]:
    """Program adına göre arayıp planId'leri döndürür.

    Dönen kayıt: {'programKodu', 'programAdi', 'birim', 'planlar': [{planId, aciklama}]}
    """
    plan_tipi = PLAN_TIPLERI.get(seviye.upper(), seviye)
    arama_kucuk = arama.strip().lower()
    sonuclar = []

    for birim in akademik_birimler():
        try:
            programlar = akademik_programlar(birim["id"], plan_tipi)
        except OBSHatasi:
            continue
        for program in programlar:
            ad = program.get("programAdi", "")
            if arama_kucuk and arama_kucuk not in ad.lower():
                continue
            log(f"  bulundu: {ad}  ({birim['ad']})")
            sonuclar.append(
                {
                    "programKodu": program.get("programKodu", ""),
                    "programAdi": ad,
                    "birim": birim["ad"],
                    "planlar": program_planlari(program.get("programKodu", ""), plan_tipi),
                }
            )
    return sonuclar
