# Kurulum talimatı (yapay zekâ asistanı için)

Bu dosya, projeyi zip olarak alan kişinin asistanı içindir. Amacın: kullanıcıya
birkaç soru sorup paneli **onun bölümüne göre** çalışır hâle getirmek.

Kullanıcı muhtemelen İTÜ öğrencisi ve teknik detayla uğraşmak istemiyor.
Komutları sen çalıştır, ona sadece soruları sor. Konuş dili: Türkçe.

**Ne yaptığı:** `README.md` projenin tamamını anlatır; gerekirse oradan oku.
Kısaca: İTÜ ÖBS'den bölümün ders planını ve o dönem açılan dersleri (CRN'li)
çeker, sadece kullanıcının planına sayan dersleri saklar, tarayıcıda ders seçim
paneli açar.

---

## Ön koşul

Python 3.9+ kurulu olmalı. Başka hiçbir şey gerekmez (harici paket yok).

```bash
python --version
```

Çalışmazsa `python3` veya `py` dene. Hiçbiri yoksa kullanıcıya
python.org'dan Python kurmasını söyle ve dur.

---

## Adım 1 — Bölümü sor

Kullanıcıya sor:

> **Hangi bölümdesin?** (Örn. "Kontrol ve Otomasyon Mühendisliği")
> **Seviyen nedir?** Lisans mı, yüksek lisans mı, doktora mı, ön lisans mı?

Seviyeyi şu koda çevir:

| Cevap | Kod |
|---|---|
| Lisans | `LS` |
| Yüksek lisans / doktora | `LU` |
| Ön lisans | `OL` |
| Lisansüstü 2. öğretim | `LUI` |

## Adım 2 — planId'yi bul

```bash
python panel.py ara "kontrol ve otomasyon" --seviye LU
```

Arama terimini kısa tut (bölüm adının ayırt edici 1–2 kelimesi). Tüm
fakülte/enstitüler tarandığı için 10–20 saniye sürer.

Çıktı şuna benzer:

```
  Kontrol ve Otomasyon Mühendisliği Yüksek Lisans  [KOM_KO_YL]  — Lisansüstü Eğitim Enstitüsü
      planId   2561   ... 2025-2026 Güz Dönemi Sonrası   <- en güncel
      planId   1295   ... 2025-2026 Güz Dönemi Öncesi
```

Dikkat edilecekler:

* Birden çok program çıkarsa (İngilizce/Türkçe programlar ayrıdır) **kullanıcıya
  hangisi olduğunu sor**, kendin seçme.
* Bir programın birden çok plan sürümü olur. Genelde **en güncel olan** (en
  büyük planId) doğrudur, ama kullanıcı eski müfredattaysa farklı olabilir.
  Açıklamadaki dönem bilgisini kullanıcıya göster ve teyit et.
* Sonuç boş dönerse seviye kodu yanlış olabilir; lisansüstü programlar
  fakülteler altında değil, enstitüler altındadır (`LU` dene).

## Adım 3 — Ayarları yaz

`veri/ayarlar.json` dosyasını oluştur/güncelle:

```json
{
  "bolum": "Kontrol ve Otomasyon Mühendisliği Yüksek Lisans",
  "planId": 2561,
  "seviye": "LU",
  "ekBransKodlari": []
}
```

`veri/` klasörü yoksa oluştur ve `sablon/` içindeki boş dosyaları oraya kopyala.

## Adım 4 — Veriyi çek

```bash
python panel.py guncelle
```

Bu komut ders planını ve bu dönem açılan dersleri indirir. Çıktıda kaç
gereksinim ve kaç CRN bulunduğu yazar. **Çıktıyı kullanıcıya özetle** —
"planında 10 gereksinim var, bu dönem sana uyan 12 ders açılmış" gibi.

Sıfır ders çıkarsa: muhtemelen o an aktif dönem (yaz gibi) az ders açıyordur
ya da planId yanlıştır. Çıktıdaki dönem adını kullanıcıya söyle ve teyit et.

## Adım 5 — Alınan dersleri sor

Kullanıcıya sor:

> **Şimdiye kadar hangi dersleri aldın?** Ders kodlarını yazman yeterli
> (örn. "KOM 505, ELE 514E"). Dönem ve notunu da söylersen ekleyebilirim.

Her ders için:

```bash
python panel.py alinan-ekle "KOM 505" --donem "2024-2025 Güz" --not AA
```

* `--donem` ve `--not` isteğe bağlıdır, bilmiyorsa boş bırak.
* Ders adı planda varsa otomatik dolar, sen yazmana gerek yok.
* Ders kodunu `BRANŞ NUMARA` biçiminde ver: `KOM 505`, `ELE 514E`.
* Kullanıcı "hiç almadım / ilk dönemim" derse bu adımı atla.

Eklendikten sonra kontrol et ve listeyi kullanıcıya göster:

```bash
python panel.py alinan
```

Kullanıcı sonradan da ekleyebilir: panelde sağ üstteki **"Alınan Dersler"**
düğmesi yandan bir panel açar, oradan elle ekleyip silebilir.

## Adım 6 — Paneli aç

```bash
python panel.py
```

Tarayıcıda `http://127.0.0.1:8730` açılır. Bu komut sen durdurana kadar
çalışır — arka planda başlat ya da kullanıcıya "terminali açık bırak,
kapatmak için Ctrl+C" de.

Son olarak kullanıcıya kısaca ne yapabileceğini anlat:
ders seçince haftalık program oluşur, çakışmalar kırmızı görünür, altta ders
kayıt ekranına yapıştıracağı CRN listesi hazırdır. "Haftalık Program" yazısının
yanındaki açılır listeden birden çok alternatif program tutabilir (`+` yeni,
`⧉` kopyala, `✎` ad değiştir, `×` sil) ve aralarında geçiş yapıp
karşılaştırabilir.

---

## Sonraki dönemler

Her ders kayıt döneminde tek komut yeterlidir:

```bash
python panel.py guncelle
```

Açılan dersler, hocalar ve kontenjanlar her dönem değişir. Kontenjan takibi için
kullanıcının terminale dönmesi gerekmez: panelin sağ üstündeki **⟳ Kontenjan
yenile** düğmesi açılan dersleri ve kontenjanları yeniden çeker. Komut satırı
karşılığı `python panel.py dersler`.

---

## Sık karşılaşılan durumlar

**"Seçime Bağlı Ders" slotları için hiç ders görünmüyor.**
Normal — bu slotların ÖBS'de ders listesi yoktur, seviyeye uygun her kredili
ders sayılır. Kullanıcıya hangi branşlarla ilgilendiğini sor ve
`veri/ayarlar.json` içindeki `ekBransKodlari` dizisine ekle
(örn. `["BLG", "EHB", "MAT"]`), sonra `python panel.py dersler` çalıştır.

**Ders sayısı beklenenden az.**
Panel bilerek yalnızca kullanıcının planına sayan dersleri gösterir. Aktif
dönemin ne olduğunu (`guncelle` çıktısında yazar) kontrol et — yaz döneminde
çok az ders açılır.

**`ara` komutu sonuç bulamıyor.**
Seviye kodunu değiştir, arama terimini kısalt. Son çare olarak kullanıcı
<https://obs.itu.edu.tr/public/DersPlan> adresinden planını bulup adresteki
son sayıyı (`.../DersPlanDetay/2561` → `2561`) verebilir.

**Ayrıştırma hatası / boş tablo.**
ÖBS sayfa yapısını değiştirmiş olabilir. İndirilen ham HTML'ler
`veri/ham/` klasöründedir; düzeltilecek yer `obs_client.py` içindeki tablo
ayrıştırma fonksiyonlarıdır.

---

## Yapma

* Kullanıcının ÖBS şifresini isteme — bu proje giriş gerektirmez, tüm veri
  herkese açık sayfalardan gelir.
* Ders kaydını sen yapmaya çalışma. Panel yalnızca CRN listesi üretir; kaydı
  kullanıcı ÖBS üzerinden kendisi yapar.
* `veri/ayarlar.json` içindeki `planId`'yi kullanıcıya teyit ettirmeden
  varsayma; yanlış plan, yanlış ders listesi demektir.
