# Ders Seçim Paneli

Kurulum ve kullanım talimatı [`AGENTS.md`](AGENTS.md) dosyasındadır — bu projeyi
ilk kez kuruyorsan oradaki adımları izle (bölümü sor → `planId` bul → ayarları
yaz → veriyi çek → alınan dersleri sor → paneli aç).

Projenin ne olduğu, mimarisi ve tüm komutlar için [`README.md`](README.md).

Kısa notlar:

* Bağımlılık yok, sadece Python 3.9+ standart kütüphanesi. `pip install` gerekmez.
* Kişisel veri `veri/` klasöründedir ve paylaşım paketine dahil edilmez.
* Kod ve arayüz Türkçedir; değişken/fonksiyon adları da Türkçe tutulur.

## Commit kuralı

Bu projede commit mesajlarına `Co-Authored-By: Claude ...` satırı **ekleme**.
Commit'lerin tek yazarı depo sahibidir.

## Depolar

* Paylaşıma açık sürüm: <https://github.com/muhal1/itu-ders-secim-paneli>
  (`veri/` hariç — kişisel veri asla buraya gitmez)
* Kişisel kopya: <https://github.com/muhal1/ders-secim-paneli-kisisel> (private,
  `veri/*.json` dahil)

Kod değişikliklerinin ikisine de yansıması gerekir.
