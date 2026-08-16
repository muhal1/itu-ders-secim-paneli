# Güvenlik

## Bu proje ne yapar, ne yapmaz

Panelin güvenlik yüzeyi bilerek çok dar tutuldu:

* **Şifre istemez.** ÖBS'ye giriş yapmaz; yalnızca `obs.itu.edu.tr` üzerindeki
  herkese açık sayfalardan veri okur. Kimse senden ÖBS şifreni istememelidir.
* **Sunucu yalnızca `127.0.0.1` dinler.** Panel dışarıdan erişilebilir değildir;
  aynı ağdaki başka bir cihaz bile bağlanamaz.
* **Veri dışarı gitmez.** Ders planın, aldığın dersler ve seçimlerin yalnızca
  kendi diskinde, `veri/` klasöründe düz JSON olarak durur.
* **Bağımlılık yoktur.** Sadece Python standart kütüphanesi kullanılır, yani
  üçüncü parti paketlerden gelen tedarik zinciri riski yoktur.
* **Ders kaydı yapmaz.** Yalnızca CRN listesi üretir; kaydı ÖBS üzerinden sen
  yaparsın.

## Kişisel verini korumak

`veri/` klasörü `.gitignore` içindedir ve depoya yüklenmez. Projeyi çatallayıp
kendi deponu açacaksan bu satırı kaldırma — aksi halde aldığın dersler ve
notların herkese açık hale gelir.

Başkasına gönderirken `python panel.py paketle` komutunu kullan; ürettiği zip
kişisel veri içermez.

## Açık bildirimi

Bir güvenlik sorunu bulursan lütfen **herkese açık issue açma**. Bunun yerine
deponun **Security → Report a vulnerability** bölümünden özel bildirim gönder.
Böylece sorun, düzeltilmeden önce yayılmamış olur.

Bildirimde şunlar yardımcı olur: sorunun ne olduğu, nasıl tetiklendiği ve
etkisinin ne olabileceği.

## Kapsam dışı

* ÖBS'nin (`obs.itu.edu.tr`) kendisindeki açıklar bu projenin kapsamı değildir;
  onları İTÜ Bilgi İşlem Daire Başkanlığı'na bildirmek gerekir.
* Panel yerelde çalışan tek kullanıcılık bir araçtır. Kendi bilgisayarına
  erişimi olan birinin `veri/` klasörünü okuyabilmesi beklenen davranıştır.
