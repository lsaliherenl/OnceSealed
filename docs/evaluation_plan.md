# OnceSealed — Değerlendirme Planı (ekip içi)

> Amaç: yeni özellik eklemek değil, mevcut sistemin **doğruluğunu, güvenliğini ve gerçek dünyadaki faydasını ölçmek**.
> Dört başlık (D1-D4). Her biri için: ne ölçüyoruz, nasıl, hangi metrikle, kim ne yapacak.
> Son güncelleme: 14 Ekim 2026.

---

## D1. AI değerlendirmesinin doğruluğu

### Neden sadece "uzman etiketi" yapmıyoruz?

50-100 belge ve alan uzmanı 10 günde mümkün değil; iki kişinin "bu projenin ek katkısı 3 mü 4 mü" diye puan vermesi de
güvenilir olmaz (öznel, uzmanlık ister). Bunun yerine üç ayağı olan bir yöntem kuruyoruz. Her ayak farklı bir soruyu
cevaplıyor ve birinin zayıflığını diğeri kapatıyor:

| Ayak | Cevapladığı soru | İnsan emeği |
|---|---|---|
| **A. Kontrol listesi etiketi** (precision/recall/F1) | Model, belgede **somut bir kanıtın olup olmadığını** doğru buluyor mu? | ~1,5-2 saat / kişi |
| **B. Etiketsiz sağlamlık testleri** | Kanıtı silince puan düşüyor mu? Alakasız metne "kanıt var" diyor mu? Tekrar çalıştırınca değişiyor mu? | Yok |
| **C. Dış uzman referansları** | Sonuçlarımız, uzmanların yayımladığı kalite değerlendirmeleriyle ne kadar örtüşüyor? | Yok (ben toplarım) |

### A. Kontrol listesi etiketi (insanların yapacağı tek iş)

**Fikir:** Uzmanlık isteyen "kalite puanı" yerine, herkesin metne bakarak cevaplayabileceği **evet/hayır soruları**
soruyoruz. Sorular ICVCM'in değerlendirme çerçevesindeki ve CCQI'nin alt kriterlerindeki somut kanıt türlerinden
türetildi. Örnek: "Metinde, yatırım analizi için sayısal bir getiri (IRR) değeri VE bir eşik (benchmark) değeri
veriliyor mu?" Bu soruya cevap vermek için karbon uzmanı olmak gerekmiyor; metinde var ya da yok.

Bu yaklaşımın üç avantajı var:
- Evet/hayır etiketleri iki kişi arasında çok daha tutarlı olur (ölçeceğiz: Cohen's kappa).
- Precision / recall / F1 doğrudan hesaplanır (her soru bir ikili sınıflandırma).
- Jev'in en güçlü olduğu soru tipiyle (`noul`: evet/hayır olasılığı) birebir aynı. Yani Jev'i en adil koşulda ölçüyoruz.

**Soru listesi (taslak, `qs-v2`):**

| İlke | Evet/hayır soruları |
|---|---|
| Additionality | (1) Sayısal yatırım analizi var mı (IRR/NPV + eşik değeri)? (2) Benzer projelerin yaygınlığı (common practice) ele alınmış mı? (3) Projenin yasal zorunluluk olmadığı (regulatory surplus) belirtilmiş mi? (4) Karbon gelirinin proje kararından önce düşünüldüğü (prior consideration) belgelenmiş mi? |
| Permanence | (1) Geri dönüş (reversal) riski bir araç/puanla değerlendirilmiş mi? (2) Tampon havuza (buffer) katkı sayısal olarak verilmiş mi? (3) Yangın, kesim vb. risklere karşı izleme/önlem anlatılmış mı? |
| Robust quantification | (1) Referans (baseline) emisyon hesabı formül veya değerle verilmiş mi? (2) Sızıntı (leakage) ele alınmış mı? (3) Belirsizlik veya muhafazakârlık ele alınmış mı? (4) İzleme planı parametre ve sıklıkla tanımlanmış mı? |
| No double counting | (1) Başka bir karbon programında kayıtlı/ihraç edilmediği belirtilmiş mi? (2) Başka çevresel sertifikalar (REC, I-REC) veya emisyon ticareti ele alınmış mı? (3) Ev sahibi ülke / ulusal kayıt / karşılıklı düzeltme (corresponding adjustment) ele alınmış mı? |
| Safeguards | (1) Paydaş görüşmesi tarih/katılımcı gibi ayrıntılarla anlatılmış mı? (2) Şikâyet mekanizması tanımlanmış mı? (3) Çevresel etki değerlendirmesi yapılmış mı? (4) Yerel halk / yerli halkların hakları veya FPIC ele alınmış mı? |

**Etiketleme adım adım (siz ikiniz):**
1. Size bir tablo vereceğim (Excel/Google Sheets). Her satır: proje + ilke + **kodun seçtiği belge bölümleri**
   (LLM'in seçtiği alıntılar değil; böylece modelin seçim yanlılığı etikete bulaşmaz) + bir soru.
2. Her soru için **Evet / Hayır** seçin. "Evet" dediyseniz kanıtın geçtiği paragraf kimliğini (ör. `p32-03`) yazın.
   Emin değilseniz "Belirsiz" seçin (bunlar ayrıca raporlanır).
3. **Birbirinize bakmadan** ayrı ayrı doldurun. Bu çok önemli: iki kişinin bağımsız uyumu (Cohen's kappa) ölçülecek.
4. Bitince anlaşmadığınız satırları birlikte konuşup ortak karara bağlayın (adjudication). Nihai etiket bu olur.
5. Kılavuz: her soru için "evet sayılır / hayır sayılır" örnekleri tabloda olacak.

**Boyut:** 11 belge × 5 ilke × ~3,6 soru ≈ 190 soru (uygulanmayan ilkeler düşünce biraz azalır). Soru başına ~30 sn →
kişi başı ~1,5-2 saat.

**Metrikler:**
- İki etiketçi arası uyum: Cohen's kappa (soru başına ve toplam).
- Jev 1.13 ve LLM için, her soru ve toplam: precision, recall, F1 (Jev olasılığı 0,5 eşikle evet/hayır'a çevrilir).
- Jev olasılıkları için kalibrasyon: Brier skoru (küçük örneklem uyarısıyla).
- İlke düzeyi: "evet" oranı ile Jev'in güç puanı arasındaki sıra korelasyonu (Spearman).
- Jev'e alıntı vermek mi, ham bölüm vermek mi daha iyi: aynı metriklerle karşılaştırma.
- Turnike-Carbon hazır olursa aynı tabloyla üçüncü model olarak eklenir.

**Dürüstlük notu (README'ye girecek):** Etiketler alan uzmanlarınca değil, ekip tarafından yazılı kılavuzla verildi;
sorular kanıtın *varlığını* ölçer, kanıtın *doğruluğunu* değil.

### B. Etiketsiz sağlamlık testleri

| Test | Nasıl | Beklenen |
|---|---|---|
| Silme testi | Kanıt olarak gösterilen paragrafları belgeden çıkarıp yeniden değerlendir | Güç puanı düşer |
| Yanlış ilke testi | Güvenceler bölümünü ek katkı sorularına ver | "Ele alınmamış" |
| Tekrarlanabilirlik | Aynı girdiyle 3 çalıştırma | Puan farkı küçük (±2 civarı) |
| Sahte alıntı testi | Değiştirilmiş/uydurma alıntılar ekle | Doğrulayıcı hepsini atar |

### C. Dış uzman referansları (karşılaştırma, "doğruluk" değil)

| Kaynak | Ne verir | Not |
|---|---|---|
| **CCQI** (Öko-Institut, EDF, WWF) | Kredi türü bazında, her kalite hedefi için 1-5 puan; yöntemi açık | 14 proje türü; seçtiğimiz belgeler bu türlere göre seçildi |
| **ICVCM metodoloji kararları** | Onaylandı / reddedildi | Zaten katman 1'de |
| **BeZero / Calyx Global** | Proje bazında genel derecelendirme (AAA-D); temel notlar ücretsiz görülebiliyor | Genel kaliteyi ölçer, belge kanıtını değil |
| **Probst ve ark. 2024, Nature Communications** | Proje türüne göre gerçekleşen emisyon azaltımı oranı (ör. ocak %11, ormansızlaşma %25) | Tür düzeyinde gerçek dünya etkisi |

Beklenti: belge kanıtı ile gerçek dünya kalitesi arasında **zayıf** bir ilişki çıkabilir. Bu da bir bulgu:
"iyi yazılmış belge ≠ sağlam kredi"; katman 1'i (metodoloji durumu) ayrı tutmamızın gerekçesi.

### Belgeler (11 proje, CCQI türlerini kapsayacak şekilde)

Mevcut 4: VCS1477 (REDD+), VCS1851 (güneş), VCS138 (çöp gazı), VCS2505 (ocak).
İndirilecek 7 (her biri için proje sayfası > Documents > View More > "VCS Project Description"):

| Proje | Tür (CCQI) | Metodoloji | İndirilecek dosya | Kaydedilecek ad |
|---|---|---|---|---|
| [VCS1742](https://registry.verra.org/app/projectDetail/VCS/1742) Kinnaur, Hindistan | Hidroelektrik | ACM0002 | `PL1742_VCS PD_HBPCL_V02_17042018_Clean.pdf` | `VCS1742_PD.pdf` |
| [VCS1728](https://registry.verra.org/app/projectDetail/VCS/1728) Mytrah, Hindistan | Rüzgâr | ACM0002 | `VCS Joint PD  MR_Mytrah_V03_20122017_Clean.pdf` | `VCS1728_PD.pdf` |
| [VCS2609](https://registry.verra.org/app/projectDetail/VCS/2609) Kuamut, Malezya | İyileştirilmiş orman yönetimi | VM0010 | `PROJ_DESC_2609_07032023.pdf` | `VCS2609_PD.pdf` |
| [VCS673](https://registry.verra.org/app/projectDetail/VCS/673) Kibale, Uganda | Doğal orman rehabilitasyonu | AR-ACM0001 | `PROJ_DESC_673_05SEP2011.pdf` | `VCS673_PD.pdf` |
| [VCS2846](https://registry.verra.org/app/projectDetail/VCS/2846) Nanyang, Çin | Gübre biyogazı | ACM0010 | `VCS-Joint-Project-Description-Monitoring-Report-Muanyuan FSW-version03-clean.pdf` | `VCS2846_PD.pdf` |
| [VCS985](https://registry.verra.org/app/projectDetail/VCS/985) Cordillera Azul, Peru | REDD+ (Katingan ile aynı metodoloji) | VM0007 | `PROJ_DESC_985_20DEC2012.pdf` | `VCS985_PD.pdf` |
| [VCS4150](https://registry.verra.org/app/projectDetail/VCS/4150) DelAgua, Ruanda | Ocak (yeni metodoloji VM0050) | VM0050 + VMR0006 | `VCS 4150 ReQ PD v6.0 11082025_clean.pdf` | `VCS4150_PD.pdf` |

---

## D2. Ölçek ve performans

**Gerçek veriyle ölçüm:** Katingan'ın OffsetsDB'deki **4.477 gerçek iptal işlemini** (en büyük projede 38.455) seri
aralıklarına çevirip Anvil'de sözleşmeye tek tek oynatacağız. Ölçülecekler: işlem başına gaz, süre, partideki kayıt
sayısına göre büyüme.

**Beklenti (hesap):** Örtüşme kontrolü partideki her önceki iptali okuyor (~4-5 bin gaz/kayıt). Birkaç bin iptalde tek
işlem on milyonlarca gaza ve blok sınırına yaklaşır. Yani gerçek ölçekte **mevcut tasarım kırılır**.

**Düzeltme (ölçümden sonra):** İptalleri parti içinde sıralı bir bağlı liste olarak tutmak; istemci yeni aralığın
"hemen öncesindeki" iptali ipucu olarak verir, sözleşme yalnızca iki komşuyu kontrol eder → kayıt sayısından bağımsız
sabit gaz. Fuzz testleri değişmeden geçmeli. Sonra aynı gerçek veriyle yeniden ölçüm: önce/sonra grafiği.

## D3. Tehdit modeli ve güvenlik

| Senaryo | Test / önlem |
|---|---|
| Yetkisiz erişim | Var olan rol testleri + rol iptali (revoke) akışı testi |
| Yönetici anahtarı ele geçirilmesi/kaybı | `AccessControlDefaultAdminRules`: yönetici devri iki adımlı ve gecikmeli |
| Operator anahtarı ele geçirilirse | Rolün iptal edilmesi testi; zararın sınırı (yalnızca yeni iptal ekleyebilir, eskisini silemez) |
| Kötü niyetli/hatalı operator | Var: taahhüt-kasa uyuşmazlığını denetçi yakalıyor |
| Kötü niyetli denetçi | Tek denetçi yalan onay verebilir → sınır olarak belgelenir; çözüm önerisi: çoklu denetçi eşiği (gelecek çalışma) |
| Denetçi anahtar kaybı | Kasalar açılamaz → öneri: kasayı iki anahtara (denetçi + düzenleyici) şifrelemek; belgelenir |
| Gizlilik ihlali (meta veri) | **Gerçek veriyle ölçüm:** OffsetsDB'de (proje, tarih, miktar) üçlüsü tekil olan iptallerin oranı → bir şirket "X tarihinde Y ton iptal ettik" derse zincirdeki kaydı ne kadar kolay eşleştirilir? |
| Statik analiz | Slither çalıştırılır, bulgular raporlanır |

## D4. Gerçek kayıtlarla doğrulama

**Gerçek veride kontrol:** OffsetsDB'de iptal edilen miktarın ihraç edilen miktarı aştığı **11 proje-vintage**
(toplam 235.932 ton) var. Gerçek ihraç/iptal geçmişlerini sözleşmeye oynattığımızda bu iptaller "parti aralığı dışında"
diye reddedilir. Bunu ölçüp raporlayacağız.

**Dürüst sınır:** Bu fazlalıklar gerçek çifte sayım olmayabilir; kayıt sistemlerindeki vintage etiketi hataları da
olabilir. Birkaçını kayıt sisteminde tek tek inceleyip ayırt etmeye çalışacağız. Gerçek mutabakat (kayıt sistemi API'si
ile) kapsam dışı; README'de entegrasyon yolu olarak anlatılır.

---

## Takvim önerisi

| Tarih | İş | Kim |
|---|---|---|
| 15 Ekim | D2 ölçüm + sözleşme düzeltmesi, D3 yönetici güvenliği + Slither; FastAPI katmanı | Claude |
| 15 Ekim | 7 PDF'i indir; Claude Design taslağı | Siz |
| 16 Ekim | Sepolia'ya (düzeltilmiş sözleşme) yayın + rol fonlama; Next.js başlangıcı | Claude + siz (fonlama betiğini çalıştırma) |
| 16-17 Ekim | Next.js ekranları (tasarıma göre) | Claude |
| 17 Ekim | 11 belge için pipeline + qs-v2; etiket tablosu hazır | Claude |
| 18-19 Ekim | **Etiketleme (bağımsız, ayrı ayrı) + ortak karar** | Siz ikiniz |
| 19-20 Ekim | D1 metrikleri, B testleri, C karşılaştırması; D3/D4 raporları | Claude |
| 21-23 Ekim | Tampon, README, sunum provası, kod anlatım rehberi | Birlikte |
| 24 Ekim | Video + Devpost | Birlikte |
| 25 Ekim | Teslim | |
