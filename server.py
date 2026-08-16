# -*- coding: utf-8 -*-
"""Panelin yerel web sunucusu.

Girişsiz, tek kullanıcılık, yalnızca localhost'a bağlanır. Statik dosyaları
web/ klasöründen sunar, veri okuma/yazma işlerini /api altında yapar.
"""

from __future__ import annotations

import json
import threading
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

KOK = Path(__file__).resolve().parent
WEB = KOK / "web"
VERI = KOK / "veri"
HAM = VERI / "ham"

AYARLAR = VERI / "ayarlar.json"
PLAN = VERI / "plan.json"
DERSLER = VERI / "dersler.json"
ALINAN = VERI / "alinan.json"
SECIM = VERI / "secim.json"

# Panelden tetiklenen yenilemenin üst üste binmesini engeller
YENILEME_KILIDI = threading.Lock()

MIME = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
}


def json_oku(yol: Path, varsayilan):
    """JSON dosyasını okur; yoksa veya bozuksa varsayılanı döndürür.

    'utf-8-sig' bilerek seçildi: Windows'ta Notepad ve PowerShell dosyaları
    çoğu zaman BOM ile yazar. Düz 'utf-8' ile okunursa BOM yüzünden JSON
    ayrıştırması patlar ve dosya dolu olmasına rağmen boş sanılır.
    """
    try:
        return json.loads(yol.read_text(encoding="utf-8-sig"))
    except (FileNotFoundError, json.JSONDecodeError):
        return varsayilan


def secim_oku() -> dict:
    """Ders programı profillerini okur ve biçimi normalleştirir.

    Eski sürümde secim.json tek bir {"crnler": [...]} listesiydi; o dosyalar
    tek profile dönüştürülerek okunur.
    """
    ham = json_oku(SECIM, {})
    profiller = ham.get("profiller")

    if isinstance(profiller, list) and profiller:
        temiz = [
            {"ad": str(p.get("ad") or f"Program {i + 1}"),
             "crnler": [str(c) for c in p.get("crnler", [])]}
            for i, p in enumerate(profiller)
            if isinstance(p, dict)
        ]
    else:
        temiz = [{"ad": "Program 1", "crnler": [str(c) for c in ham.get("crnler", [])]}]

    adlar = [p["ad"] for p in temiz]
    aktif = ham.get("aktif")
    return {"aktif": aktif if aktif in adlar else adlar[0], "profiller": temiz}


def json_yaz(yol: Path, veri) -> None:
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text(
        json.dumps(veri, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def dersleri_yenile(log=print) -> dict:
    """Bu dönem açılan dersleri (kontenjanlar dahil) ÖBS'den yeniden çeker.

    Hem `python panel.py dersler` komutu hem de paneldeki "Yenile" düğmesi
    buraya düşer; mantık tek yerde dursun diye burada.
    """
    import obs_client as obs  # ağ katmanı yalnızca yenileme anında yüklensin

    ayarlar = json_oku(AYARLAR, {})
    if not ayarlar.get("planId"):
        raise RuntimeError(
            "veri/ayarlar.json içinde 'planId' yok. Önce: python panel.py ara <bölüm>"
        )

    plan = json_oku(PLAN, None)
    if not plan:
        log("  Ders planı yok, önce o çekiliyor ...")
        plan = obs.ders_plani_cek(int(ayarlar["planId"]), HAM, log)
        json_yaz(PLAN, plan)

    dersler = obs.donem_derslerini_topla(
        plan,
        ayarlar.get("seviye", "LU"),
        ayarlar.get("ekBransKodlari"),
        HAM,
        log,
    )
    json_yaz(DERSLER, dersler)
    return dersler


class Istek(SimpleHTTPRequestHandler):
    def log_message(self, bicim, *args):  # sunucu gürültüsünü kıs
        pass

    # ------------------------------------------------------------ yardımcılar

    def _json_gonder(self, veri, kod: int = 200) -> None:
        govde = json.dumps(veri, ensure_ascii=False).encode("utf-8")
        self.send_response(kod)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(govde)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(govde)

    def _govde_oku(self):
        uzunluk = int(self.headers.get("Content-Length") or 0)
        if not uzunluk:
            return {}
        try:
            return json.loads(self.rfile.read(uzunluk).decode("utf-8"))
        except json.JSONDecodeError:
            return None

    def _dosya_gonder(self, yol: Path) -> None:
        if not yol.is_file():
            self.send_error(404, "Bulunamadı")
            return
        govde = yol.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", MIME.get(yol.suffix, "application/octet-stream"))
        self.send_header("Content-Length", str(len(govde)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(govde)

    # ------------------------------------------------------------------- GET

    def do_GET(self):  # noqa: N802
        yol = self.path.split("?")[0]

        if yol == "/api/veri":
            self._json_gonder(
                {
                    "ayarlar": json_oku(AYARLAR, {}),
                    "plan": json_oku(PLAN, None),
                    "dersler": json_oku(DERSLER, None),
                    "alinan": json_oku(ALINAN, {"alinan": []}).get("alinan", []),
                    "secim": secim_oku(),
                }
            )
            return

        if yol.startswith("/api/"):
            self.send_error(404, "Bilinmeyen uç")
            return

        ad = "index.html" if yol in ("/", "") else yol.lstrip("/")
        hedef = (WEB / ad).resolve()
        if not str(hedef).startswith(str(WEB.resolve())):
            self.send_error(403, "Yasak")
            return
        self._dosya_gonder(hedef)

    # ------------------------------------------------------------------ POST

    def do_POST(self):  # noqa: N802
        yol = self.path.split("?")[0]
        govde = self._govde_oku()
        if govde is None:
            self._json_gonder({"hata": "Geçersiz JSON"}, 400)
            return

        if yol == "/api/alinan":
            liste = govde.get("alinan")
            if not isinstance(liste, list):
                self._json_gonder({"hata": "'alinan' bir liste olmalı"}, 400)
                return
            json_yaz(ALINAN, {"alinan": liste})
            self._json_gonder({"tamam": True, "adet": len(liste)})
            return

        if yol == "/api/yenile":
            if not YENILEME_KILIDI.acquire(blocking=False):
                self._json_gonder({"hata": "Zaten süren bir yenileme var."}, 409)
                return
            try:
                dersler = dersleri_yenile(log=lambda *_: None)
                self._json_gonder(
                    {
                        "tamam": True,
                        "donem": dersler["donem"],
                        "adet": len(dersler["dersler"]),
                        "cekilme": dersler["cekilme"],
                    }
                )
            except Exception as hata:  # ağ hatası, sayfa yapısı değişikliği vb.
                self._json_gonder({"hata": f"{hata}"}, 502)
            finally:
                YENILEME_KILIDI.release()
            return

        if yol == "/api/secim":
            profiller = govde.get("profiller")
            if not isinstance(profiller, list) or not profiller:
                self._json_gonder({"hata": "'profiller' boş olmayan bir liste olmalı"}, 400)
                return
            temiz = []
            for sira, profil in enumerate(profiller):
                if not isinstance(profil, dict):
                    self._json_gonder({"hata": "Her profil bir nesne olmalı"}, 400)
                    return
                temiz.append(
                    {
                        "ad": str(profil.get("ad") or f"Program {sira + 1}"),
                        "crnler": [str(c) for c in profil.get("crnler", [])],
                    }
                )
            adlar = [p["ad"] for p in temiz]
            aktif = govde.get("aktif")
            json_yaz(
                SECIM,
                {"aktif": aktif if aktif in adlar else adlar[0], "profiller": temiz},
            )
            self._json_gonder({"tamam": True, "adet": len(temiz)})
            return

        self.send_error(404, "Bilinmeyen uç")


def calistir(port: int = 8730, tarayici_ac: bool = True) -> None:
    # Yenileme birkaç saniye sürdüğü için çok iş parçacıklı sunucu:
    # o sırada sayfa donmasın.
    sunucu = ThreadingHTTPServer(("127.0.0.1", port), Istek)
    adres = f"http://127.0.0.1:{port}/"
    print(f"\n  Panel hazır:  {adres}")
    print("  Durdurmak için Ctrl+C\n")
    if tarayici_ac:
        threading.Timer(0.6, lambda: webbrowser.open(adres)).start()
    try:
        sunucu.serve_forever()
    except KeyboardInterrupt:
        print("\n  Kapatıldı.")
    finally:
        sunucu.server_close()
