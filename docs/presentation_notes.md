# OnceSealed — Sunum Notları

> Ekip içi çalışma dosyası (Türkçe). Video, README ve Devpost metni İngilizce olacak; İngilizce
> cümleler aşağıda hazır duruyor. **Her önemli adımdan sonra güncellenir.** Son güncelleme: 14 Ekim 2026.

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
| **Kendi hesapladığımız anonimlik oranı** | OffsetsDB anlık görüntüsü (2026-06-01) | **TODO** (iş paketi 5). İlk slayta bu girecek |
| Spot piyasada iptallerin %55'i anonim | [Relae](https://relae.co/blog/voluntary-carbon-market-trends-2026) | Kaynak göstermiyor; ana rakam yapma |
| ICVCM, şebekeye bağlı yenilenebilir enerji metodolojilerini ek katkı gerekçesiyle reddetti (Ağu 2024) | [ICVCM](https://icvcm.org/carbon-credits-from-current-renewable-energy-methodologies-will-not-receive-high-integrity-ccp-label/) | Kalite sorununun somut örneği |

**Gerilim (anlatının omurgası):** Şirketler dava ve eleştiri korkusuyla kimliklerini gizliyor ("greenhushing").
Piyasa ise her kredinin tek bir kez kullanıldığının ve kalite iddialarının kanıta dayandığının ispatını istiyor.
Bugün ikisi aynı anda sağlanamıyor. OnceSealed ikisini birlikte sağlıyor.

**EN:** *"Buyers want confidentiality. Markets need auditability. Today you have to choose. We think you shouldn't."*

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
| Python testleri | **40 test** (alıntı doğrulama, rapor, gizlilik, kasa, denetim, makbuz) | 14 Ekim |
| Ortak test vektörleri | Python ve Solidity aynı hash'leri üretiyor (uint64 üst sınırı dahil) | 14 Ekim |
| AI alıntıları | İlk ölçümde 72/72, yayımlanan 4 raporda 64/64 alıntı PDF'te doğrulandı, 0 atılan | 13 Ekim |
| Rapor hash'leri | 4 raporun hash'i yayımlanan dosyadan yeniden hesaplanıyor | 13 Ekim |
| AI maliyeti | 4 proje × 5 ilke ≈ 0,05 $ (LLM) + ≈ 0,001 $ (Jev) | 13 Ekim |
| Gaz | `retire` ~150-215k, `registerBatch` ~72k, `attestRetirement` ~29k | 14 Ekim |
| Sepolia sözleşme adresi / Etherscan | **TODO** (iş paketi 7) | |

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
Denetçi kasayı açar; hem kasanın parmak izini hem taahhüdü yeniden hesaplayıp zincirdekiyle karşılaştırır ve sonucu
zincire yazar. Herkese açık ekranda "denetçi tarafından doğrulandı" görünür, kimlik görünmez. Onay tek seferlik.

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

- [ ] Anonimlik oranını hesapla ve grafik çıkar (iş paketi 5)
- [ ] Sepolia adresi ve Etherscan bağlantıları (iş paketi 7)
- [ ] Arayüz ekran görüntüleri (iş paketi 6)
- [ ] Mimari diyagram
- [ ] Video metni (İngilizce) bu dosyadan çıkarılacak
