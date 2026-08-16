/* Ders Seçim Paneli — arayüz mantığı.
   Veri sunucudan tek seferde gelir (/api/veri), değişiklikler /api/... ile geri yazılır. */

"use strict";

const durum = {
  ayarlar: {},
  plan: null,
  dersler: null,
  alinan: [],
  // Birden çok alternatif ders programı: {aktif, profiller:[{ad, crnler}]}
  secim: { aktif: "Program 1", profiller: [{ ad: "Program 1", crnler: [] }] },
};

const HAFTA = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"];
const KISA = { Pazartesi: "Pzt", Salı: "Sal", Çarşamba: "Çar", Perşembe: "Per", Cuma: "Cum", Cumartesi: "Cmt", Pazar: "Paz" };

const $ = (secici) => document.querySelector(secici);
const el = (etiket, sinif, metin) => {
  const dugum = document.createElement(etiket);
  if (sinif) dugum.className = sinif;
  if (metin != null) dugum.textContent = metin;
  return dugum;
};

/* --------------------------------------------------------------- yardımcı */

const dakika = (saat) => {
  const [s, d] = String(saat || "").split(":").map(Number);
  return Number.isFinite(s) ? s * 60 + (d || 0) : null;
};

const araliklar = (ders) =>
  (ders.slotlar || [])
    .map((s) => ({ gun: s.gun, bas: dakika(s.baslangic), bit: dakika(s.bitis), derslik: s.derslik }))
    .filter((a) => a.bas != null && a.bit != null && a.bit > a.bas);

const cakisirMi = (a, b) =>
  araliklar(a).some((x) => araliklar(b).some((y) => x.gun === y.gun && x.bas < y.bit && y.bas < x.bit));

const dersBul = (crn) => (durum.dersler?.dersler || []).find((d) => d.crn === crn);
const alindiMi = (kod) => durum.alinan.some((d) => d.kod === kod);

/* --------------------------------------------------------- program profilleri */

const aktifProfil = () =>
  durum.secim.profiller.find((p) => p.ad === durum.secim.aktif) || durum.secim.profiller[0];

const aktifCrnler = () => aktifProfil()?.crnler || [];
const seciliDersler = () => aktifCrnler().map(dersBul).filter(Boolean);

/** Çakışan/boş adları düzelterek benzersiz bir profil adı üretir. */
function benzersizAd(istenen) {
  const adlar = durum.secim.profiller.map((p) => p.ad);
  let ad = (istenen || "").trim() || "Program";
  let sayac = 2;
  while (adlar.includes(ad)) ad = `${istenen.trim()} ${sayac++}`;
  return ad;
}

function profilEkle(crnler = []) {
  const ad = benzersizAd(`Program ${durum.secim.profiller.length + 1}`);
  durum.secim.profiller.push({ ad, crnler: [...crnler] });
  durum.secim.aktif = ad;
  return ad;
}

const saatMetni = (ders) => {
  const liste = araliklar(ders);
  if (!liste.length) return "Program belirtilmemiş";
  return liste
    .map((a) => `${KISA[a.gun] || a.gun} ${String(Math.floor(a.bas / 60)).padStart(2, "0")}:${String(a.bas % 60).padStart(2, "0")}–${String(Math.floor(a.bit / 60)).padStart(2, "0")}:${String(a.bit % 60).padStart(2, "0")}`)
    .join("  ·  ");
};

/* ------------------------------------------------------- plan ilerlemesi */

/** Alınan dersleri plan gereksinimlerine açgözlü biçimde eşler.
 *  Önce listesi belli (kısıtlı) gereksinimler doldurulur, artanlar serbest
 *  seçmeli slotlarına yerleşir. */
function planIlerlemesi(alinanKodlari) {
  const havuz = [...alinanKodlari];
  const satirlar = (durum.plan?.gereksinimler || []).map((g) => ({ gereksinim: g, dolduran: null }));

  for (const satir of satirlar) {
    if (satir.gereksinim.serbest) continue;
    const kodlar = satir.gereksinim.dersler.map((d) => d.kod);
    const sira = havuz.findIndex((k) => kodlar.includes(k));
    if (sira >= 0) satir.dolduran = havuz.splice(sira, 1)[0];
  }
  for (const satir of satirlar) {
    if (satir.gereksinim.serbest && !satir.dolduran && havuz.length) satir.dolduran = havuz.shift();
  }
  return { satirlar, artan: havuz };
}

/* ------------------------------------------------------------- sunucu ile */

async function veriYukle() {
  const yanit = await fetch("/api/veri");
  const veri = await yanit.json();
  Object.assign(durum, veri);
  durum.alinan = veri.alinan || [];

  const gelen = veri.secim;
  if (gelen && Array.isArray(gelen.profiller) && gelen.profiller.length) {
    durum.secim = gelen;
  } else {
    // Eski biçim (düz CRN listesi) ya da boş dosya
    durum.secim = {
      aktif: "Program 1",
      profiller: [{ ad: "Program 1", crnler: Array.isArray(gelen) ? gelen : [] }],
    };
  }
}

async function kaydet(yol, govde) {
  await fetch(yol, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(govde),
  });
}

const alinanKaydet = () => kaydet("/api/alinan", { alinan: durum.alinan });
const secimKaydet = () => kaydet("/api/secim", durum.secim);

/* ------------------------------------------------------------- çizim: üst */

function cizUst() {
  $("#bolumAdi").textContent = durum.ayarlar.bolum || durum.plan?.planAdi || "Ders Seçim Paneli";
  $("#donemEtiketi").textContent = durum.dersler?.donem || "Dönem verisi yok";
  $("#donemEtiketi").className = "rozet " + (durum.dersler ? "mavi" : "");
  $("#veriTarihi").textContent = durum.dersler?.cekilme ? `veri: ${durum.dersler.cekilme}` : "";
  $("#alinanSayi").textContent = durum.alinan.length;

  const uyari = $("#uyari");
  if (!durum.plan || !durum.dersler) {
    uyari.innerHTML =
      "Veri henüz çekilmemiş. Terminalde proje klasöründe <code>python panel.py guncelle</code> " +
      "çalıştır, sonra bu sayfayı yenile.";
    uyari.classList.remove("gizli");
  } else {
    uyari.classList.add("gizli");
  }
}

/** Bir ders kodunun adını bulur: önce alınan kayıtlar, sonra plan, sonra
 *  bu dönem açılan dersler. Bulunamazsa boş döner. */
function dersAdi(kod) {
  const alinanKayit = durum.alinan.find((d) => d.kod === kod);
  if (alinanKayit?.ad) return alinanKayit.ad;

  const plandaki = (durum.plan?.gereksinimler || [])
    .flatMap((g) => g.dersler)
    .find((d) => d.kod === kod);
  if (plandaki?.ad) return plandaki.ad;

  return (durum.dersler?.dersler || []).find((d) => d.kod === kod)?.ad || "";
}

/** Gereksinim satırının sağındaki "KOM 513E · Modelling & Kontrol Of Robots" metni. */
function dolduranEtiketi(kod, ek = "") {
  const kutu = el("span", "dolduran-ders");
  kutu.append(el("span", "dolduran-kod", kod));
  const ad = dersAdi(kod);
  if (ad) kutu.append(el("span", "dolduran-ad", ad));
  if (ek) kutu.append(el("span", "dolduran-ek", ek));
  return kutu;
}

/* ----------------------------------------------------- çizim: gereksinimler */

function cizGereksinimler() {
  const kap = $("#gereksinimListesi");
  kap.replaceChildren();
  if (!durum.plan) {
    kap.append(el("div", "bos", "Ders planı yok."));
    return;
  }

  const ilerleme = planIlerlemesi(durum.alinan.map((d) => d.kod));
  const secililer = seciliDersler();
  const kullanilanSecim = new Set();
  let tamamlanan = 0;

  for (const satir of ilerleme.satirlar) {
    const g = satir.gereksinim;
    const kutu = el("div", "gereksinim");
    let durumMetni = "";
    let durumDugumu = null;

    if (satir.dolduran) {
      tamamlanan++;
      kutu.classList.add("tamam");
      kutu.append(el("span", "isaret", "✓"));
      durumDugumu = dolduranEtiketi(satir.dolduran);
    } else {
      // Bu dönem seçilen dersler bu slotu doldurabilir mi?
      const aday = secililer.find(
        (d) =>
          !kullanilanSecim.has(d.crn) &&
          (g.serbest || g.dersler.some((pd) => pd.kod === d.kod))
      );
      if (aday) {
        kullanilanSecim.add(aday.crn);
        kutu.classList.add("secili");
        kutu.append(el("span", "isaret", "◍"));
        durumDugumu = dolduranEtiketi(aday.kod, "(seçildi)");
      } else {
        kutu.append(el("span", "isaret", "○"));
        durumMetni = g.serbest ? "serbest seçmeli" : `${g.dersler.length} seçenek`;
      }
    }

    const orta = el("div", "ad");
    const adSatiri = el("div", "gereksinim-ad-satiri");
    adSatiri.append(el("span", null, g.ad));
    // Lisans planlarında aynı ad birden çok yarıyılda geçer; ayırt edilsin
    if (g.yariyil) adSatiri.append(el("span", "yariyil", g.yariyil));
    orta.append(adSatiri);

    const sag = el("div", "dolduran");
    if (durumDugumu) sag.append(durumDugumu);
    else sag.textContent = durumMetni;

    kutu.append(orta, sag);
    kap.append(kutu);
  }

  $("#ilerlemeOzet").textContent =
    `${tamamlanan} / ${ilerleme.satirlar.length} tamamlandı` +
    (ilerleme.artan.length ? `  ·  ${ilerleme.artan.length} fazladan ders` : "");
}

/* ------------------------------------------------------ çizim: ders listesi */

function suzgectenGecenler() {
  const arama = $("#arama").value.trim().toLocaleLowerCase("tr");
  const gereksinim = $("#gereksinimSuzgeci").value;
  const alinaniGizle = $("#alinaniGizle").checked;
  const cakisaniGizle = $("#cakisaniGizle").checked;
  const doluGizle = $("#doluGizle").checked;
  const secililer = seciliDersler();

  return (durum.dersler?.dersler || []).filter((d) => {
    if (arama) {
      const havuz = `${d.kod} ${d.ad} ${d.ogretimUyesi} ${d.crn}`.toLocaleLowerCase("tr");
      if (!havuz.includes(arama)) return false;
    }
    if (gereksinim) {
      const uyar = gereksinim === "__serbest__" ? !d.plandaVar : (d.gereksinimler || []).includes(gereksinim);
      if (!uyar) return false;
    }
    if (alinaniGizle && alindiMi(d.kod)) return false;
    if (doluGizle && d.kontenjan > 0 && d.yazilan >= d.kontenjan) return false;
    if (cakisaniGizle && !aktifCrnler().includes(d.crn)) {
      if (secililer.some((s) => s.kod !== d.kod && cakisirMi(s, d))) return false;
    }
    return true;
  });
}

function cizDersListesi() {
  const kap = $("#dersListesi");
  kap.replaceChildren();

  const hepsi = durum.dersler?.dersler || [];
  const liste = suzgectenGecenler();
  $("#dersSayisi").textContent = `${liste.length} / ${hepsi.length} kayıt`;

  if (!liste.length) {
    kap.append(el("div", "bos", hepsi.length ? "Süzgeçlere uyan ders yok." : "Ders verisi yok."));
    return;
  }

  const secililer = seciliDersler();

  for (const ders of liste) {
    const secili = aktifCrnler().includes(ders.crn);
    const alindi = alindiMi(ders.kod);
    const cakisan = !secili && secililer.some((s) => s.kod !== ders.kod && cakisirMi(s, ders));

    const satir = el("div", "ders");
    if (secili) satir.classList.add("secili");
    else if (cakisan) satir.classList.add("cakisan");
    if (alindi) satir.classList.add("alindi");

    const orta = el("div", "orta");
    const ustSatir = el("div");
    ustSatir.append(el("span", "kod", ders.kod), document.createTextNode(" "), el("span", "crn", `CRN ${ders.crn}`));
    orta.append(ustSatir, el("div", "ad", ders.ad));

    const alt = el("div", "alt");
    alt.append(el("span", "saat", saatMetni(ders)));
    if (ders.ogretimUyesi) alt.append(el("span", "hoca", "· " + ders.ogretimUyesi));

    for (const ad of ders.gereksinimler || []) alt.append(el("span", "rozet mavi", ad));
    if (!ders.plandaVar) alt.append(el("span", "rozet mor", "serbest seçmeli"));
    if (alindi) alt.append(el("span", "rozet yesil", "bu dersi aldın"));
    if (cakisan) alt.append(el("span", "rozet kirmizi", "çakışıyor"));
    orta.append(alt);

    const sag = el("div", "sag");
    const dolu = ders.kontenjan > 0 && ders.yazilan >= ders.kontenjan;
    sag.append(el("div", "kontenjan" + (dolu ? " dolu" : ""), `${ders.yazilan} / ${ders.kontenjan}`));

    const dugme = el("button", "dugme kucuk" + (secili ? "" : " birincil"), secili ? "Kaldır" : "Seç");
    dugme.addEventListener("click", () => secimDegistir(ders));
    sag.append(dugme);

    satir.addEventListener("mouseenter", () => ipucuAc(ders, satir));
    satir.addEventListener("mouseleave", ipucuGizleGecikmeli);

    satir.append(orta, sag);
    kap.append(satir);
  }
}

/* -------------------------------------------- aynı gün ipucu (fare üstünde) */

let ipucuKutusu = null;
let ipucuCrn = null;
let ipucuAcZaman = null;
let ipucuGizleZaman = null;

function ipucuHazirla() {
  if (ipucuKutusu) return ipucuKutusu;
  ipucuKutusu = el("div", "gun-ipucu gizli");
  ipucuKutusu.addEventListener("mouseenter", () => clearTimeout(ipucuGizleZaman));
  ipucuKutusu.addEventListener("mouseleave", ipucuGizleGecikmeli);
  document.body.append(ipucuKutusu);
  return ipucuKutusu;
}

/** Verilen dersle aynı gün(ler)de olup saatleri çakışmayan diğer dersler. */
function ayniGunAdaylari(ders) {
  const gunler = [...new Set(araliklar(ders).map((a) => a.gun))];
  if (!gunler.length) return { gunler, adaylar: [] };

  const adaylar = (durum.dersler?.dersler || []).filter((aday) => {
    if (aday.crn === ders.crn || aday.kod === ders.kod) return false;
    if (alindiMi(aday.kod)) return false;
    if (!araliklar(aday).some((a) => gunler.includes(a.gun))) return false;
    return !cakisirMi(ders, aday);
  });

  adaylar.sort(
    (a, b) => a.kod.localeCompare(b.kod, "tr") || a.crn.localeCompare(b.crn)
  );
  return { gunler, adaylar };
}

/** Sadece ilgilenilen günlere düşen saatleri yazar. */
function gunSaatMetni(ders, gunler) {
  return araliklar(ders)
    .filter((a) => gunler.includes(a.gun))
    .map(
      (a) =>
        `${KISA[a.gun] || a.gun} ` +
        `${String(Math.floor(a.bas / 60)).padStart(2, "0")}:${String(a.bas % 60).padStart(2, "0")}` +
        `–${String(Math.floor(a.bit / 60)).padStart(2, "0")}:${String(a.bit % 60).padStart(2, "0")}`
    )
    .join("  ·  ");
}

function ipucuIcerik(ders) {
  const kutu = ipucuHazirla();
  kutu.replaceChildren();

  const { gunler, adaylar } = ayniGunAdaylari(ders);

  const baslik = el("div", "gun-ipucu-baslik");
  baslik.append(el("b", null, ders.kod));
  baslik.append(
    el(
      "span",
      null,
      gunler.length
        ? ` · ${gunler.join(", ")} günü çakışmayanlar`
        : " · dersin programı belirtilmemiş"
    )
  );
  kutu.append(baslik);

  if (!adaylar.length) {
    kutu.append(
      el(
        "div",
        "gun-ipucu-bos",
        gunler.length
          ? "Aynı gün alabileceğin başka ders yok."
          : "Gün/saat bilgisi olmadığı için öneri çıkarılamıyor."
      )
    );
    return;
  }

  const secililer = seciliDersler();
  const liste = el("div", "gun-ipucu-liste");

  for (const aday of adaylar) {
    const secili = aktifCrnler().includes(aday.crn);
    const secimleCakisan =
      !secili && secililer.some((s) => s.kod !== aday.kod && cakisirMi(s, aday));

    const satir = el("button", "gun-ipucu-satir");
    satir.type = "button";
    if (secili) satir.classList.add("secili");
    if (secimleCakisan) satir.classList.add("cakisan");

    const ust = el("div", "gun-ipucu-ust");
    ust.append(el("span", "kod", aday.kod), el("span", "crn", `CRN ${aday.crn}`));
    const dolu = aday.kontenjan > 0 && aday.yazilan >= aday.kontenjan;
    ust.append(
      el("span", "gun-ipucu-kontenjan" + (dolu ? " dolu" : ""), `${aday.yazilan}/${aday.kontenjan}`)
    );
    satir.append(ust);

    satir.append(el("div", "gun-ipucu-ad", aday.ad));
    satir.append(el("div", "gun-ipucu-saat", gunSaatMetni(aday, gunler)));

    const alt = el("div", "gun-ipucu-alt");
    if (aday.ogretimUyesi) alt.append(el("span", "hoca", aday.ogretimUyesi));
    if (secili) alt.append(el("span", "rozet mavi", "seçili — kaldır"));
    else if (secimleCakisan) alt.append(el("span", "rozet kirmizi", "seçiminle çakışır"));
    else alt.append(el("span", "rozet yesil", "ekle"));
    satir.append(alt);

    satir.addEventListener("click", () => {
      secimDegistir(aday);
      const guncel = dersBul(ipucuCrn);
      if (guncel) ipucuIcerik(guncel); // kutu açık kalsın, durumlar tazelensin
    });

    liste.append(satir);
  }

  kutu.append(liste);
}

function ipucuKonumla(satir) {
  const kutu = ipucuKutusu;
  kutu.classList.remove("gizli");
  const r = satir.getBoundingClientRect();
  const k = kutu.getBoundingClientRect();

  let sol = r.right + 10;
  if (sol + k.width > window.innerWidth - 8) sol = r.left - k.width - 10;
  if (sol < 8) sol = Math.max(8, window.innerWidth - k.width - 8);

  let ust = Math.min(r.top, window.innerHeight - k.height - 8);
  ust = Math.max(8, ust);

  kutu.style.left = `${sol}px`;
  kutu.style.top = `${ust}px`;
}

function ipucuAc(ders, satir) {
  clearTimeout(ipucuGizleZaman);
  clearTimeout(ipucuAcZaman);
  ipucuAcZaman = setTimeout(() => {
    ipucuCrn = ders.crn;
    ipucuIcerik(ders);
    ipucuKonumla(satir);
  }, 180);
}

function ipucuGizle() {
  clearTimeout(ipucuAcZaman);
  ipucuCrn = null;
  if (ipucuKutusu) ipucuKutusu.classList.add("gizli");
}

function ipucuGizleGecikmeli() {
  clearTimeout(ipucuAcZaman);
  clearTimeout(ipucuGizleZaman);
  ipucuGizleZaman = setTimeout(ipucuGizle, 220);
}

function secimDegistir(ders) {
  const profil = aktifProfil();
  if (profil.crnler.includes(ders.crn)) {
    profil.crnler = profil.crnler.filter((c) => c !== ders.crn);
  } else {
    // Aynı dersin başka bir şubesi seçiliyse onun yerine geçsin
    profil.crnler = profil.crnler.filter((crn) => dersBul(crn)?.kod !== ders.kod);
    profil.crnler.push(ders.crn);
  }
  secimKaydet();
  ciz();
}

/* --------------------------------------------------- çizim: haftalık program */

function cizProgram() {
  const kap = $("#program");
  kap.replaceChildren();
  const secililer = seciliDersler();

  const tumAralik = secililer.flatMap((d) => araliklar(d).map((a) => ({ ...a, ders: d })));
  if (!tumAralik.length) {
    kap.append(el("div", "bos", "Ders seçtikçe haftalık programın burada oluşur."));
    $("#cakismaUyari").classList.add("gizli");
    return;
  }

  const gunler = HAFTA.slice(0, 5);
  for (const a of tumAralik) if (!gunler.includes(a.gun)) gunler.push(a.gun);
  gunler.sort((x, y) => HAFTA.indexOf(x) - HAFTA.indexOf(y));

  const bas = Math.min(8 * 60 + 30, ...tumAralik.map((a) => a.bas));
  const bit = Math.max(17 * 60 + 30, ...tumAralik.map((a) => a.bit));
  const basSaat = Math.floor(bas / 60);
  const bitSaat = Math.ceil(bit / 60);
  const oran = 0.72; // piksel / dakika
  const yukseklik = (bitSaat - basSaat) * 60 * oran;

  const izgara = el("div", "program-izgara");
  izgara.style.gridTemplateColumns = `52px repeat(${gunler.length}, minmax(92px, 1fr))`;

  izgara.append(el("div"));
  for (const gun of gunler) izgara.append(el("div", "gun-basi", gun));

  const saatSutunu = el("div", "saat-sutunu");
  saatSutunu.style.height = `${yukseklik}px`;
  for (let s = basSaat; s <= bitSaat; s++) {
    const etiket = el("div", "saat-etiket", `${String(s).padStart(2, "0")}:00`);
    etiket.style.top = `${(s - basSaat) * 60 * oran}px`;
    saatSutunu.append(etiket);
  }
  izgara.append(saatSutunu);

  let cakismaVar = false;

  for (const gun of gunler) {
    const sutun = el("div", "gun-sutunu");
    sutun.style.height = `${yukseklik}px`;
    for (let s = basSaat; s <= bitSaat; s++) {
      const cizgi = el("div", "saat-cizgi");
      cizgi.style.top = `${(s - basSaat) * 60 * oran}px`;
      sutun.append(cizgi);
    }

    const gununleri = tumAralik.filter((a) => a.gun === gun);
    for (const a of gununleri) {
      const carpisan = gununleri.some((b) => b !== a && a.bas < b.bit && b.bas < a.bit);
      if (carpisan) cakismaVar = true;

      const blok = el("div", "blok" + (carpisan ? " cakisan" : ""));
      blok.style.top = `${(a.bas - basSaat * 60) * oran}px`;
      blok.style.height = `${Math.max(22, (a.bit - a.bas) * oran - 3)}px`;
      blok.append(el("b", null, a.ders.kod));
      blok.append(el("span", null, `${a.ders.ogretimUyesi || ""}`));
      blok.title = `${a.ders.kod} — ${a.ders.ad}\nCRN ${a.ders.crn}\n${a.ders.ogretimUyesi}\nDerslik: ${a.derslik || "—"}`;
      sutun.append(blok);
    }
    izgara.append(sutun);
  }

  kap.append(izgara);
  $("#cakismaUyari").classList.toggle("gizli", !cakismaVar);
}

/* ----------------------------------------------------------- yer imi (CRN) */

/** ÖBS ders kayıt ekranındaki CRN kutucuklarını dolduran bookmarklet adresi.
 *
 *  Kodun kendisi sabittir ve okunur hâliyle durur; sürümden sürüme değişen tek
 *  şey `crn` dizisinin içeriğidir. CRN'ler adrese gömülü olduğu için seçim
 *  değişince yer iminin yeniden sürüklenmesi gerekir. */
function yerImiAdresi(crnler) {
  const liste = crnler.map((c) => `'${String(c).replace(/[^0-9]/g, "")}'`).join(",");
  return (
    "javascript: (function () {            var crn = [" +
    liste +
    "];            const crninputs = document.querySelectorAll(\"input[type='number']\");" +
    "            for (var i = 0; i < crn.length; i++) {                if (crninputs[i]) {" +
    "                    crninputs[i].value = crn[i];" +
    "                    crninputs[i].dispatchEvent(new Event('input', { bubbles: true }));" +
    "                }            }            void (0);        })();"
  );
}

function cizYerImi() {
  const bag = $("#crnYerImi");
  const crnler = aktifCrnler();
  const profilAdi = aktifProfil()?.ad || "";

  bag.textContent = crnler.length ? `⇱ CRN doldur · ${profilAdi}` : "⇱ CRN doldur";
  bag.classList.toggle("pasif", !crnler.length);
  bag.setAttribute("href", crnler.length ? yerImiAdresi(crnler) : "javascript:void(0)");
  bag.title = crnler.length
    ? `${crnler.length} CRN: ${crnler.join(" ")}\nYer imi çubuğuna sürükle`
    : "Önce ders seç";
}

/* ------------------------------------------------------ çizim: seçim listesi */

function cizSecim() {
  const kap = $("#secimListesi");
  kap.replaceChildren();
  const secililer = seciliDersler();
  $("#aktifProfilAdi").textContent = `· ${aktifProfil()?.ad || ""}`;

  if (!secililer.length) {
    kap.append(el("div", "bos", "Henüz ders seçmedin."));
  }

  for (const ders of secililer) {
    const satir = el("div", "secim");
    const orta = el("div", "orta");
    const ust = el("div", "ust-satir");
    ust.append(el("span", "kod", ders.kod), el("span", "crn", `CRN ${ders.crn}`));
    orta.append(ust, el("div", "soluk", `${ders.ad} · ${saatMetni(ders)}`));

    const sil = el("button", "dugme kucuk sessiz", "Kaldır");
    sil.addEventListener("click", () => secimDegistir(ders));
    satir.append(orta, sil);
    kap.append(satir);
  }

  $("#crnKutusu").value = aktifCrnler().join(" ");
  cizYerImi();
  const kredi = secililer.reduce((toplam, d) => {
    const plandaki = (durum.plan?.gereksinimler || [])
      .flatMap((g) => g.dersler)
      .find((pd) => pd.kod === d.kod);
    return toplam + (plandaki?.kredi || 0);
  }, 0);
  $("#secimOzet").textContent = `${secililer.length} ders${kredi ? `  ·  ${kredi} kredi (plandan)` : ""}`;
}

/* -------------------------------------------------------- çizim: yan panel */

function cizAlinan() {
  const kap = $("#alinanListesi");
  kap.replaceChildren();

  if (!durum.alinan.length) {
    kap.append(el("div", "bos", "Henüz ders eklemedin."));
    return;
  }

  durum.alinan.forEach((ders, sira) => {
    const satir = el("div", "alinan");
    const orta = el("div", "orta");
    orta.append(el("div", "kod", ders.kod));
    const ayrinti = [ders.ad, ders.donem, ders.harfNotu].filter(Boolean).join(" · ");
    if (ayrinti) orta.append(el("div", "soluk", ayrinti));

    const sil = el("button", "sil", "×");
    sil.title = "Listeden çıkar";
    sil.addEventListener("click", async () => {
      durum.alinan.splice(sira, 1);
      await alinanKaydet();
      ciz();
    });

    satir.append(orta, sil);
    kap.append(satir);
  });
}

function cizSecenekler() {
  const suzgec = $("#gereksinimSuzgeci");
  const secili = suzgec.value;
  suzgec.replaceChildren(el("option", null, "Tüm gereksinimler"));
  suzgec.firstChild.value = "";

  // Aynı gereksinim adı birden çok yarıyılda geçebilir; listede bir kez görünsün
  for (const ad of [...new Set((durum.plan?.gereksinimler || []).map((g) => g.ad))]) {
    const secenek = el("option", null, ad);
    secenek.value = ad;
    suzgec.append(secenek);
  }
  const serbest = el("option", null, "Plan dışı / serbest");
  serbest.value = "__serbest__";
  suzgec.append(serbest);
  suzgec.value = secili;

  const liste = $("#planDersleri");
  liste.replaceChildren();
  const gorulen = new Set();
  for (const g of durum.plan?.gereksinimler || []) {
    for (const d of g.dersler) {
      if (gorulen.has(d.kod)) continue;
      gorulen.add(d.kod);
      const secenek = el("option");
      secenek.value = d.kod;
      secenek.label = d.ad;
      liste.append(secenek);
    }
  }
}

/* ------------------------------------------------------ çizim: profil seçici */

function cizProfiller() {
  const secici = $("#profilSecici");
  secici.replaceChildren();
  for (const profil of durum.secim.profiller) {
    const secenek = el("option", null, `${profil.ad} (${profil.crnler.length})`);
    secenek.value = profil.ad;
    secici.append(secenek);
  }
  secici.value = aktifProfil()?.ad || "";
  $("#profilSil").disabled = durum.secim.profiller.length < 2;
}

/* --------------------------------------------------------------- ana çizim */

function ciz() {
  cizUst();
  cizGereksinimler();
  cizDersListesi();
  cizProfiller();
  cizProgram();
  cizSecim();
  cizAlinan();
}

/* --------------------------------------------------------- veriyi tazeleme */

function bilgiGoster(metin, tur = "bilgi") {
  const uyari = $("#uyari");
  uyari.textContent = metin;
  uyari.classList.remove("gizli", "hata", "basari");
  if (tur !== "bilgi") uyari.classList.add(tur);
}

/** ÖBS'den açılan dersleri ve kontenjanları yeniden çeker. */
async function verileriYenile() {
  const dugme = $("#yenileDugmesi");
  if (dugme.disabled) return;

  const eskiMetin = dugme.textContent;
  dugme.disabled = true;
  dugme.textContent = "⟳ Yenileniyor…";
  bilgiGoster("ÖBS'den güncel kontenjanlar ve ders listesi çekiliyor, birkaç saniye sürebilir…");

  try {
    const yanit = await fetch("/api/yenile", { method: "POST" });
    const sonuc = await yanit.json();
    if (!yanit.ok) throw new Error(sonuc.hata || `Sunucu ${yanit.status} döndü`);

    const oncekiCrnler = aktifCrnler();
    await veriYukle();
    cizSecenekler();
    ciz();

    // Kapanmış/kaldırılmış dersler seçimde kalmış olabilir
    const kayip = oncekiCrnler.filter((crn) => !dersBul(crn));
    bilgiGoster(
      `Güncellendi — ${sonuc.donem}, ${sonuc.adet} kayıt (${sonuc.cekilme}).` +
        (kayip.length
          ? `  Dikkat: ${kayip.join(", ")} CRN'leri artık listede yok, seçimden düştü.`
          : ""),
      kayip.length ? "" : "basari"
    );
    if (!kayip.length) setTimeout(() => $("#uyari").classList.add("gizli"), 4000);
  } catch (hata) {
    bilgiGoster(`Yenilenemedi: ${hata.message}. İnternet bağlantını kontrol et.`, "hata");
  } finally {
    dugme.disabled = false;
    dugme.textContent = eskiMetin;
  }
}

/* ------------------------------------------------------------- olay bağları */

function olaylariBagla() {
  for (const secici of ["#arama", "#gereksinimSuzgeci", "#alinaniGizle", "#cakisaniGizle", "#doluGizle"]) {
    const dugum = $(secici);
    dugum.addEventListener(dugum.type === "search" ? "input" : "change", () => {
      cizDersListesi();
    });
  }

  // Liste kaydırılınca / pencere boyutlanınca konum bozulmasın.
  // Kutunun kendi içindeki kaydırma bunu tetiklememeli.
  const kaydirmaGizle = (olay) => {
    if (ipucuKutusu && olay.target instanceof Node && ipucuKutusu.contains(olay.target)) return;
    ipucuGizle();
  };
  window.addEventListener("scroll", kaydirmaGizle, true);
  window.addEventListener("resize", ipucuGizle);

  $("#yenileDugmesi").addEventListener("click", verileriYenile);

  $("#alinanAc").addEventListener("click", () => {
    $("#yanPanel").classList.add("acik");
    $("#perde").classList.remove("gizli");
  });
  const kapat = () => {
    $("#yanPanel").classList.remove("acik");
    $("#perde").classList.add("gizli");
  };
  $("#alinanKapat").addEventListener("click", kapat);
  $("#perde").addEventListener("click", kapat);
  document.addEventListener("keydown", (olay) => olay.key === "Escape" && kapat());

  // Ders kodu kutusu boşaltılınca formun kalanı da temizlensin
  $("#yeniKod").addEventListener("input", (olay) => {
    if (olay.target.value.trim()) return;
    for (const secici of ["#yeniAd", "#yeniDonem", "#yeniNot"]) $(secici).value = "";
  });

  $("#yeniKod").addEventListener("change", (olay) => {
    const kod = olay.target.value.trim().toUpperCase();
    const plandaki = (durum.plan?.gereksinimler || []).flatMap((g) => g.dersler).find((d) => d.kod === kod);
    if (plandaki && !$("#yeniAd").value) $("#yeniAd").value = plandaki.ad;
  });

  $("#alinanForm").addEventListener("submit", async (olay) => {
    olay.preventDefault();
    const kod = $("#yeniKod").value.trim().replace(/\s+/g, " ").toUpperCase();
    if (!kod) return;
    if (alindiMi(kod)) {
      alert(`${kod} zaten listede.`);
      return;
    }
    const plandaki = (durum.plan?.gereksinimler || []).flatMap((g) => g.dersler).find((d) => d.kod === kod);
    durum.alinan.push({
      kod,
      ad: $("#yeniAd").value.trim() || plandaki?.ad || "",
      kredi: plandaki?.kredi ?? null,
      akts: plandaki?.akts ?? null,
      donem: $("#yeniDonem").value.trim(),
      harfNotu: $("#yeniNot").value.trim(),
    });
    await alinanKaydet();
    $("#alinanForm").reset();
    $("#yeniKod").focus();
    ciz();
  });

  /* --- program profilleri --- */

  $("#profilSecici").addEventListener("change", async (olay) => {
    durum.secim.aktif = olay.target.value;
    await secimKaydet();
    ciz();
  });

  $("#profilYeni").addEventListener("click", async () => {
    profilEkle();
    await secimKaydet();
    ciz();
  });

  $("#profilKopyala").addEventListener("click", async () => {
    const kaynak = aktifProfil();
    const ad = benzersizAd(`${kaynak.ad} kopya`);
    durum.secim.profiller.push({ ad, crnler: [...kaynak.crnler] });
    durum.secim.aktif = ad;
    await secimKaydet();
    ciz();
  });

  $("#profilAd").addEventListener("click", async () => {
    const profil = aktifProfil();
    const girilen = prompt("Program adı:", profil.ad);
    if (girilen === null) return;
    const yeni = girilen.trim();
    if (!yeni || yeni === profil.ad) return;
    if (durum.secim.profiller.some((p) => p !== profil && p.ad === yeni)) {
      alert(`"${yeni}" adında bir program zaten var.`);
      return;
    }
    profil.ad = yeni;
    durum.secim.aktif = yeni;
    await secimKaydet();
    ciz();
  });

  $("#profilSil").addEventListener("click", async () => {
    if (durum.secim.profiller.length < 2) return;
    const profil = aktifProfil();
    if (!confirm(`"${profil.ad}" silinsin mi? (${profil.crnler.length} ders)`)) return;
    durum.secim.profiller = durum.secim.profiller.filter((p) => p !== profil);
    durum.secim.aktif = durum.secim.profiller[0].ad;
    await secimKaydet();
    ciz();
  });

  $("#secimTemizle").addEventListener("click", async () => {
    const profil = aktifProfil();
    if (!profil.crnler.length) return;
    profil.crnler = [];
    await secimKaydet();
    ciz();
  });

  // Bağlantının amacı sürüklenmek; sayfa içinde tıklanınca kodu panoya kopyalar.
  $("#crnYerImi").addEventListener("click", async (olay) => {
    olay.preventDefault();
    const crnler = aktifCrnler();
    if (!crnler.length) return;
    const bag = $("#crnYerImi");
    const eskiMetin = bag.textContent;
    try {
      await navigator.clipboard.writeText(yerImiAdresi(crnler));
      bag.textContent = "Kod panoya kopyalandı";
    } catch {
      bag.textContent = "Kopyalanamadı — bağlantıyı sürükle";
    }
    setTimeout(cizYerImi, 1800);
    void eskiMetin;
  });

  $("#crnKopyala").addEventListener("click", async () => {
    if (!aktifCrnler().length) return;
    try {
      await navigator.clipboard.writeText(aktifCrnler().join(" "));
    } catch {
      $("#crnKutusu").select();
      document.execCommand("copy");
    }
    const dugme = $("#crnKopyala");
    dugme.textContent = "Kopyalandı";
    setTimeout(() => (dugme.textContent = "Kopyala"), 1400);
  });
}

/* ------------------------------------------------------------------ başlat */

(async function baslat() {
  olaylariBagla();
  try {
    await veriYukle();
  } catch (hata) {
    $("#uyari").textContent = "Sunucudan veri alınamadı: " + hata;
    $("#uyari").classList.remove("gizli");
  }
  cizSecenekler();
  ciz();
})();
