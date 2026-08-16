# Katkı rehberi

Bu proje İTÜ öğrencilerinin ders seçim dönemini kolaylaştırmak için yazıldı.
Katkıya açık. Aşağıdakiler kural değil, işleri kolaylaştıran birkaç not.

## En çok işe yarayan katkı: bozulan ayrıştırma

Proje ÖBS'nin resmî bir API'si olmadığı için sayfaların HTML'ini ayrıştırıyor.
İTÜ arayüzü değiştiğinde bir şeyler kırılır. **En değerli hata bildirimi budur.**

Bildirirken şunları ekle:

* Bölümün ve `planId`'n (`veri/ayarlar.json` içinde)
* Seviyen: `LS` / `LU` / `OL` / `LUI`
* Terminaldeki tam hata çıktısı

Düzeltmeye kendin bakacaksan: indirilen ham HTML'ler `veri/ham/` klasöründe
durur, ayrıştırma kodu `obs_client.py` içindeki tablo fonksiyonlarındadır.

## Kurulum

Kurulum yok. Python 3.9+ yeter:

```bash
python panel.py guncelle
```

## Kod tarzı

Projenin tuhaf ama bilinçli birkaç tercihi var; lütfen bunları bozma:

* **Bağımlılık eklenmez.** Sadece Python standart kütüphanesi. Kullanıcının
  `pip install` çalıştırmak zorunda kalmaması projenin ana fikirlerinden biri —
  hedef kitle çoğu zaman Python geliştiricisi değil.
* **Türkçe adlandırma.** Değişkenler, fonksiyonlar, JSON alanları ve arayüz
  metinleri Türkçe. `ders_plani_cek`, `gereksinimler`, `secimDegistir` gibi.
* **Arayüzde çerçeve yok.** `web/` klasörü düz HTML + CSS + JS. Build adımı
  yok, `node_modules` yok.
* **Kişisel veri depoya girmez.** `veri/` klasörü `.gitignore`'dadır.

## Değişikliği test etme

Otomatik test yok; elle doğrulama şöyle yapılıyor:

1. Kendi bölümünle: `python panel.py guncelle`
2. **Farklı bir seviyeyle de dene.** Lisans ve lisansüstü planları farklı
   yapıdadır (lisansta her yarıyıl ayrı tablodur). Biri çalışırken diğeri
   bozulabilir; ikisini de dene.
3. Paneli aç, tarayıcı konsolunda hata olmadığını kontrol et.

Test ederken kendi `veri/` klasörünü kirletmemek için projenin bir kopyasını
ayrı bir klasöre alıp orada çalışmak işe yarar.

## Pull request

Küçük ve tek konulu PR'lar en hızlı ilerler. Açıklamada neyi neden
değiştirdiğini ve hangi bölüm/seviye ile test ettiğini yazman yeterli.
