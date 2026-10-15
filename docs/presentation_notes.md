# OnceSealed — Sunum Notları

> Ekip içi çalışma dosyası (Türkçe). Video, README ve Devpost metni İngilizce olacak; İngilizce
> cümleler aşağıda hazır duruyor. **Her önemli adımdan sonra güncellenir.** Son güncelleme: 14 Ekim 2026 (iş paketi 3 sonrası).

---

## 1. Tek cümlelik özet

- **TR:** Karbon kredisinin iptal edildiği herkese açık ve tek seferlik olur; alıcının kimliği gizli kalır ama yetkili
  denetçi doğrulayabilir. Proje belgeleri ICVCM ilkelerine göre, her bulgusu belgeden birebir alıntıyla desteklenen
  bir AI değerlendirmesinden geçer.
- **EN (pitch):** *"OnceSealed makes every carbon credit retirement public and single-use, keeps the buyer's identity
  sealed, and lets an authorized auditor verify it — with AI quality signals where every finding quotes the source
  document."*

İsim: **Once** = her kredi bir kez iptal edilir. **Sealed** = alıcı kimliği mühürlü (şifreleme yöntemimizin adı da
"sealed box").

## 2. Problem (ilk 30-40 saniye)

| Rakam | Kaynak | Not |
|---|---|---|
| OffsetsDB'deki 1,34 milyar iptalin yalnızca 0,67 milyarında kimin adına iptal edildiği bilgisi var (~%50) | [CarbonPlan](https://carbonplan.org/blog/offsets-db-additions) | Güvenilir, birincil kaynak |
| **Açıkça "gizli" işaretlenen iptallerin ton payı ≤2018'de %0,4 → 2023-26'da %17,2** | Kendi hesabımız, OffsetsDB 2026-06-01 ([docs/anonymity_stats.md](anonymity_stats.md)) | **İlk slayt.** Grafik: `docs/figures/anonymity_trend.png` |
| 2023-26'da iptal edilen tonların %53-55'inde alıcı belirlenemiyor | Kendi hesabımız | İkinci cümle. "Kayıt sistemi pratiği de etkiliyor" uyarısını bil |
| Spot piyasada iptallerin %55'i anonim | [Relae](https://relae.co/blog/voluntary-carbon-market-trends-2026) | Kaynak göstermiyor; ana rakam yapma |
| ICVCM, şebekeye bağlı yenilenebilir enerji metodolojilerini ek katkı gerekçesiyle reddetti (Ağu 2024) | [ICVCM](https://icvcm.org/carbon-credits-from-current-renewable-energy-methodologies-will-not-receive-high-integrity-ccp-label/) | Kalite sorununun somut örneği |

**Gerilim (anlatının omurgası):** Şirketler dava ve eleştiri korkusuyla kimliklerini gizliyor ("greenhushing").
Piyasa ise her kredinin tek bir kez kullanıldığının ve kalite iddialarının kanıta dayandığının ispatını istiyor.
Bugün ikisi aynı anda sağlanamıyor. OnceSealed ikisini birlikte sağlıyor.

**EN:** *"Buyers want confidentiality. Markets need auditability. Today you have to choose. We think you shouldn't."*

**İlk slayt cümlesi (EN):** *"We analysed 495,000 retirements in OffsetsDB. The share of retired tonnes explicitly marked
'not disclosed' went from almost zero before 2019 to 17% in 2023–2026 — and more than half still name no one at all."*

**Jüri sorarsa ("bu rakam ne kadar sağlam?"):** %17 sadece açık ifadelere ("not disclosed", "anonymous" vb.) dayanıyor,
yani alt sınır. "Belirlenemeyen" oranı kısmen kayıt sistemlerinin neyi yayımladığına da bağlı; bu yüzden aralık
veriyoruz ve yöntemi tabloyla birlikte yayımladık. Sınıflandırıcı test edildi: "XYZ Private Limited" gibi şirket adları
anonim sayılmıyor.

## 3. Çözüm: üç parça

1. **Tek seferlik iptal (Once).** Akıllı sözleşme, bir seri aralığı iptal edildikten sonra o aralıkla tek bir krediyi
   bile paylaşan her yeni iptali `AlreadyRetired` hatasıyla reddeder.
2. **Mühürlü kimlik (Sealed).** Zincire alıcının adı değil, tuzlanmış bir taahhüt (hash) yazılır. Kimlik bilgisi
   denetçinin açık anahtarıyla şifrelenip zincir dışında saklanır; zincire sadece şifreli dosyanın parmak izi yazılır.
   Denetçi açar, doğrular, sonucu **bir kez ve kalıcı olarak** zincire yazar. Alıcı isterse tuzunu paylaşıp iddiasını
   herkese kanıtlar (seçici ifşa).
3. **Kanıta dayalı kalite sinyali.** Üç katman:
   - Metodoloji durumu: ICVCM kararları, kaynaklı tablo, AI yok.
   - LLM belgeden alıntı çıkarır; **kod her alıntıyı PDF'te arar**, bulamadığını atar.
   - Karar modeli (Jev 1.13) kanıtın yeterliliğini olasılıklarla puanlar.
   Raporun hash'i ve hangi modellerin kullanıldığını sabitleyen "method hash" zincire yazılır.

### Benzetmeler (anlatırken)

- **Sözleşme = herkesin okuyabildiği, sadece yetkililerin yazabildiği bir kayıt defteri.**
- **Taahhüt = mühürlü zarf.** Zarfın üstündeki parmak izi herkese açık; içini sadece denetçi açabilir. Alıcı
  isterse zarfı kendisi açıp gösterir.
- **Tuz = zarfın şifresi.** Tahmin edilemez 32 bayt; aynı şirketin iki iptali bile birbirine bağlanamaz.

## 4. Jüri kriterleriyle eşleşme

| Kriter | Ne söyleyeceğiz | Kanıtı |
|---|---|---|
| **Climate Impact** | Çifte sayım ve düşük kaliteli kredi, iklim iddialarını boşaltıyor. Tek seferlik iptal + kanıta dayalı kalite, gönüllü karbon piyasasının güvenilirliğini artırır. | Problem rakamları; ICVCM reddi örneği |
| **Innovation** | Gizlilik ve denetlenebilirliği birlikte sağlıyor; AI çıktısı kodla doğrulanıyor; iptal edilen kredi token'a dönüşmüyor (sektörün yaptığı hatadan kaçınıyor). | Taahhüdün aralığa bağlanması; alıntı doğrulama |
| **Technical Execution** | Çalışan sözleşme, testler, Python ↔ Solidity ortak vektörler, yeniden hesaplanabilir rapor hash'leri, CI. | Bkz. Bölüm 5 rakamları |
| **Practical Usefulness** | Kayıt sistemlerinin üstüne eklenen bir katman; mevcut süreçleri değiştirmiyor. Hedef kullanıcı: kayıt sistemleri, kurumsal alıcılar, denetçiler, düzenleyiciler. | Bölüm 7 |
| **Presentation** | Problem → çözüm → canlı demo → sınırlar. | Bölüm 8 demo akışı |

## 5. Teknik kanıtlar (güncel rakamlar)

| Ne | Değer | Ne zaman |
|---|---|---|
| Foundry testleri | **30 test** geçiyor (27 sözleşme + 3 Python vektörü) | 14 Ekim |
| Fuzz testleri | 2 test × 1000 rastgele senaryo: hiçbir seri iki kez iptal edilemedi | 14 Ekim |
| Python testleri | **46 test** (alıntı doğrulama, rapor, gizlilik, kasa, denetim, makbuz + 6 uçtan uca zincir testi) | 14 Ekim |
| Uçtan uca senaryo | `scripts/demo_e2e.py` tek komutla: parti → rapor → iptal → örtüşme reddi → denetim → ifşa; sahte makbuzlar reddediliyor | 14 Ekim |
| Kötü niyetli operator testi | Taahhüt A şirketine, kasa B şirketine yazılırsa denetçi yakalıyor ve zincire `REJECTED` yazıyor | 14 Ekim |
| Ortak test vektörleri | Python ve Solidity aynı hash'leri üretiyor (uint64 üst sınırı dahil) | 14 Ekim |
| AI alıntıları | İlk ölçümde 72/72, yayımlanan 4 raporda 64/64 alıntı PDF'te doğrulandı, 0 atılan | 13 Ekim |
| Rapor hash'leri | 4 raporun hash'i yayımlanan dosyadan yeniden hesaplanıyor | 13 Ekim |
| AI maliyeti | 4 proje × 5 ilke ≈ 0,05 $ (LLM) + ≈ 0,001 $ (Jev) | 13 Ekim |
| Gaz (Anvil, eski kurallar) | deploy 2,24M; lot iptali ~204k; aralık iptali ~211k; `registerBatch` ~73k; `attestRetirement` ~31k | 15 Ekim |
| Gaz (Sepolia, gerçek ağ) | deploy 15,66M (işlem sınırı ~16,8M'e yakın!); lot iptali 1,02M ilk / 828k sonraki; rapor 463k; parti 243k; onay 33k. Yeni depolama yazımı pahalı; maliyet yine ihmal edilebilir (gaz fiyatı ~0,001 gwei) | 15 Ekim |
| **Ölçek (gerçek veri)** | VCS766'nın 38.382 gerçek iptali oynatıldı: eski tasarım **7.467.'de blok sınırında çöktü**; yeni tasarım her iptalde **sabit 211k gaz** | 15 Ekim |
| Gerçek kayıtlar | OffsetsDB'de iptalin ihracı aştığı 11 vaka (235.932 t); sözleşme 76 iptali reddederdi. **Dikkat:** bunlar büyük ihtimalle veri tutarsızlığı (vintage ataması, yeniden ihraç), kanıtlanmış çifte sayım değil. "Kamuya açık verideki tutarsızlıkları otomatik işaretlerdi" de | 15 Ekim |
| Gizlilik ölçümü | Tonların %88,7'si (proje + miktar) ile tekil. **Standart lotlar artık sözleşmede zorunlu** (1.000 t). Zamanlama hâlâ bağlıyor: lot + operatörün dönemsel toplu yayını ile tamamen açıkta kalan tonlar günlükte %36,8, çeyrekte %14,5. Eski "61 eş lot" rakamı zamanlamayı yok sayıyordu, **kullanma** | 15 Ekim |
| Güvenlik | Slither temiz (2 yanlış alarm gerekçeli), 2 adımlı yönetici devri, rol iptali; 13 tehdit senaryosu belgelendi | 15 Ekim |
| AI tutarlılığı | Jev 3 çalıştırmada %99,4 aynı cevap (LLM %96); Jev 6 kat hızlı, 20 kat ucuz | 15 Ekim |
| Sepolia sözleşme adresi / Etherscan | **`0xBb88057576b92Ef27753A6b2a4Df83bE444F1308`** (lot sürümü, kaynak doğrulandı): https://sepolia.etherscan.io/address/0xBb88057576b92Ef27753A6b2a4Df83bE444F1308#code . 4 rapor, 4 parti, 2 lotluk bir alım + 2 denetçi onayı; işlemler `deployments/11155111-seed.json`. İlk sürüm `0x7D17…e675` `previous` altında kayıtlı | 15 Ekim |

## 6. Jüri soruları ve cevapları

**"Neden iptal edilen krediyi token yapmıyorsunuz?"**
Çünkü iptal, kredinin iklim faydasının kullanıldığı anlamına gelir. Verra 2022'de iptal edilmiş kredilerin
tokenlaştırılmasını yasakladı; Toucan/KlimaDAO çifte sayım eleştirisi aldı. Bizim zincirimiz sadece kanıt kaydı tutar,
sözleşmede transfer veya token üretme fonksiyonu yok.
*EN: "A retired credit's climate benefit has been used. Turning it into a tradable token invites double counting —
Verra banned exactly that in 2022. Our contract has no transfer or mint function."*

**"Bu gerçek bir iptal mi?"**
Hayır. Gerçek iptal Verra gibi kayıt sistemlerinde olur. Bu, onların üzerine eklenecek bir doğrulama ve gizlilik
katmanının prototipi. Proje verileri gerçek (OffsetsDB, Verra belgeleri), seri numaraları simüle.

**"Neden sıfır bilgi kanıtı (ZK) kullanmadınız?"**
Hash taahhüdü + şifreleme bu problemi anlaşılır ve denetlenebilir şekilde çözüyor. ZK, örneğin "alıcı X sektöründen"
gibi kimliği açmadan özellik kanıtlamak için gelecek çalışma.

**"Kayıt sistemi (operator) alıcıyı görüyor mu?"**
Evet, bilerek. Gizlilik kamuya karşı. Gerçekte de Verra hesap sahibini KYC'den tanır. Zincirde görünen: proje, seri
aralığı, miktar, zaman. Görünmeyen: alıcı.

**"Şifreli kasanın içinin doğru olduğunu nereden bileceğiz?"**
Denetçi kasayı açar ve 6 kontrol yapar: kasanın parmak izi, kasa açılıyor mu, seri aralığı, şirket kodu geçerli mi,
kod ile alıcı kimliği tutarlı mı, taahhüt eşleşiyor mu. Sonucu zincire yazar. Herkese açık ekranda "denetçi tarafından
doğrulandı" görünür, kimlik görünmez. Onay tek seferlik. Testimizde operator kasaya yanlış şirketi koyduğunda denetçi
bunu yakaladı ve iptal zincirde "reddedildi" olarak işaretlendi.

**"Alıcı tuzu başkasına verirse ne olur? Biri tuzu başka bir iptal için kullanabilir mi?"**
Taahhüt iptal edilen aralığa bağlı. Paylaşılan tuz yalnızca o tek iptali kanıtlar; başka bir iptale kopyalanan
taahhüt doğrulanmaz (bunun için ayrı bir testimiz var).

**"AI'ın verdiği 64 puan ne demek? Proje iyi mi?"**
Hayır, bu bir hüküm değil. Sadece belgenin her ICVCM ilkesini ne kadar kanıtladığına dair bir sinyal. ICVCM uygunluğu
metodoloji ve program düzeyinde belirlenir; onu ayrı ve AI'sız bir katmanda gösteriyoruz.

**"AI uydurursa?"**
Her bulgu belgeden birebir alıntı içermek zorunda ve kod her alıntıyı PDF'te arıyor. Bulunamayan bulgu atılıyor.
Şimdiye kadar 64/64 alıntı doğrulandı.

**"Güneş projesi ICVCM'de reddedilmiş ama sizin puanınız fena değil, neden?"**
Çünkü belge ayrıntılı bir finansal analiz içeriyor; AI belgenin kanıtını ölçüyor. ICVCM ise metodolojinin ek katkı
testinin yeterince sıkı olmadığına karar verdi. İkisini yan yana göstermemizin sebebi bu: belgede kanıt olması,
metodolojinin sağlam olduğu anlamına gelmez.

**"Hangi AI modellerini kullanıyorsunuz, sizin mi?"**
Belgeden alıntı çıkarmak için `deepseek-v4.1-flash`, kanıtı puanlamak için TypeSafe'in Jev 1.13 karar modeli; ikisi de
OpenRouter üzerinden ve ikisi de bizim değil. Karar modeli değiştirilebilir bir arayüzün arkasında; ekibimizin kendi
modeli Turnike'yi aynı sorularla takıp karşılaştırabiliriz (henüz entegre edilmedi).

**"Ölçeklenir mi?"**
Prototipte örtüşme kontrolü bir partideki iptalleri tek tek tarıyor; demo ölçeğinde sorun değil ve sadece yetkili
operator kayıt ekleyebildiği için dışarıdan şişirilemez. Üretimde sıralı aralık yapısı kullanılır. AI tarafında bir
projenin değerlendirmesi birkaç sentlik maliyet.

**"Alıcı şirketler gerçek mi?"**
Hayır. Demo şirketleri kurgusal; kimlik kodları gerçek LEI biçiminde ve kontrol haneleri geçerli ama kayıtlı değil.

**"Kayıt sistemi (operator) hile yaparsa?"**
Zincire yazılan taahhüt ile denetçi kasası birbirini tutmazsa denetçi bunu görür ve zincire "reddedildi" yazar; bu kayıt
silinemez. Operator'ün kasaya yazdığını değiştirmesi de mümkün değil, çünkü kasanın parmak izi zincirde.

**"Gerçek ölçekte çalışır mı?"**
Ölçtük. En kalabalık gerçek partilerden birinin (VCS766, 38.382 iptal) geçmişini zincire oynattık. İlk tasarımımız her iptalde
öncekilerin hepsini kontrol ediyordu ve 7.467. iptalde blok gaz sınırına çarptı. Tasarımı değiştirdik: iptaller sıralı bir
liste olarak tutuluyor, yeni iptal sadece iki komşusuyla karşılaştırılıyor. Her iptal artık sabit 211 bin gaz. Yanlış veya
kötü niyetli bir "komşu ipucu" bile çifte iptale yol açamıyor; bunu rastgele testlerle kanıtladık.

**"Zincirde isim yok ama yine de kim olduğu anlaşılır mı?"**
Kısmen, ve bunu açıkça ölçtük: gerçek iptallerin ton bazında %88,7'si sadece proje ve miktarla tekil. Bir şirket raporunda
"şu projeden şu kadar ton" yazarsa eşleşir. Bu yüzden sözleşme lot partilerinde her iptalin tam bir standart lot (1.000 t)
olmasını zorunlu kılıyor: 5.000 t'luk alım zincirde birbirine bağlanamayan beş özdeş lot olarak görünür. Zamanlama hâlâ
ipucu verir; operatör lotları dönemsel ve karışık yayınlarsa tamamen açıkta kalan tonlar %88,7'den %14,5-36,8'e iner.
Bir projeden o dönemde tek alıcı varsa hiçbir yöntem onu gizleyemez ("gizlilik kalabalık ister"); projeyi de gizlemek
sıfır bilgi kanıtı gerektirir (gelecek çalışma).

## 7. Hedef kullanıcı, benimsenme, ölçeklenebilirlik (Devpost için)

- **Hedef kullanıcılar:** kayıt sistemleri (Verra, Gold Standard vb.), kurumsal alıcılar, bağımsız denetçiler,
  düzenleyiciler, kredi derecelendirme kuruluşları.
- **Benimsenme kolaylığı:** Kayıt sistemlerinin mevcut iptal sürecini değiştirmez; iptal anında bir kayıt ve şifreli
  kasa ekler. Alıcı açısından ek iş yok; makbuz otomatik.
- **Ölçeklenebilirlik:** Sözleşme mantığı herhangi bir EVM zincirine taşınabilir; AI değerlendirmesi proje başına
  birkaç sent. Kalite raporları sürümlü; yeni belge geldikçe yeni sürüm eklenir.
- **Neden blokzincir?** Tek seferlik iptal kuralını hiçbir tarafın (kayıt sistemi dahil) sessizce bozamaması ve herkesin
  bağımsız doğrulayabilmesi için.

## 8. Demo akışı (video, 3-5 dk) — taslak

| Süre | Sahne | Göster |
|---|---|---|
| 0:00-0:40 | Problem | Anonimlik oranı (kendi hesabımız), greenhushing gerilimi |
| 0:40-1:00 | Çözüm özeti | Üç parça şeması |
| 1:00-1:50 | Kalite raporu | Bir Verra PDF'i → ilke puanları, belgeden vurgulanmış alıntılar, ICVCM metodoloji durumu, rapor hash'i zincirde |
| 1:50-2:30 | İptal | Kurgusal şirket bir aralığı iptal eder; zincirde sadece taahhüt; makbuz indirilir |
| 2:30-2:50 | Çifte iptal | Örtüşen aralık → `AlreadyRetired` |
| 2:50-3:30 | Denetçi | Kasa açılır, kontroller yeşil, onay zincire yazılır, herkese açık ekranda "audited ✓" |
| 3:30-3:55 | Seçici ifşa | Makbuz yüklenir → "claim verified" |
| 3:55-4:20 | Etherscan | Doğrulanmış sözleşme ve işlemler |
| 4:20-4:50 | Kapanış | Neden token yok, neden ZK değil, gerçek dünyada nasıl eklenir; sınırlar |

## 9. Söylemememiz gerekenler

- "Kendi AI modelimiz" (Jev ve deepseek bizim değil).
- "Projeyi ICVCM'e göre derecelendiriyoruz" / "bu proje kötü".
- "Gerçek iptal yapıyoruz" / "sıfır bilgi kanıtı".
- Kaynaksız rakamı (%55) ana rakam gibi sunmak.
- AI puanlarının "doğru" olduğunu iddia etmek (etiketli küme olmadan doğruluk ölçmedik).

## 10. Yapılacaklar (sunum için)

- [x] Anonimlik oranı ve grafik (`docs/figures/anonymity_trend.png`)
- [ ] Sepolia adresi ve Etherscan bağlantıları (iş paketi 7)
- [ ] Arayüz ekran görüntüleri (iş paketi 6)
- [ ] Mimari diyagram
- [ ] Video metni (İngilizce) bu dosyadan çıkarılacak
