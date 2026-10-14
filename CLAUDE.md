# OnceSealed — Gizli ama Denetlenebilir Karbon Kredisi İptali

Proje adı **OnceSealed** ("once": her kredi bir kez iptal edilir; "sealed": alıcı kimliği mühürlü). GitHub repo: https://github.com/lsaliherenl/OnceSealed (**şimdilik private**; teslimden önce public yapılacak, o zaman CLAUDE.md'nin repoda kalıp kalmayacağına yeniden karar verilecek). Yerel klasör adı `ClimateChain` olarak kalır. Foundry kütüphaneleri git submodule (`git clone --recurse-submodules`). CI: `.github/workflows/ci.yml` (pytest).

Bu dosya projenin iç bağlamıdır. Her oturumda önce bunu oku, tasarım kurallarına uy.

**Sunum notları:** `docs/presentation_notes.md` (Türkçe, ekip içi). Her iş paketi bittiğinde veya sunuma girecek bir rakam/karar değiştiğinde güncelle: teknik kanıtlar tablosu, jüri soruları, demo akışı, yapılacaklar. Video metni ve Devpost açıklaması bu dosyadan çıkarılacak.
**Teslim edilen her şey İngilizce:** kod, kod yorumları, commit mesajları, README, arayüz metinleri, video, Devpost açıklaması. Bu dosya ekip içi olduğu için Türkçe.

## Yarışma (Devpost'tan doğrulandı, 13 Ekim 2026)

- **IEEE ClimateChain Global Hackathon 2026** — https://ieee-climatechain-hack.devpost.com/ (kurallar: `/rules`)
- Katılım: öğrenciler, akademisyenler, bağımsız geliştiriciler, profesyoneller. Takım 2-5 kişi (bireysel de olur), bir kişi tek takımda.
- **Son teslim: 25 Ekim 2026, 17:00 GMT+3 (Türkiye saati).** Kurallarda ayrıca çelişkili bir "8 AM PT on October 25 öncesi teslim etmeyin" satırı var (= 18:00 TR, son teslimden sonra). **Karar: en erken saati esas al.** İç hedef: her şey 24 Ekim gecesi bitmiş olsun, 25 Ekim sabahı teslim.
- Jüri/sonuç tarihleri Devpost'ta yazmıyor (doğrulanamadı).
- **Track/challenge:** "Improve trust, transparency, and efficiency in carbon markets". Devpost'un önerdiği işler arasında "smart contracts to prevent double counting" ve "blockchain-based carbon credit verification" var; proje ikisini doğrudan karşılıyor. Açıklamada bu ifadelerle bağ kur.
- **Teslim edilecekler:** track uyumu; proje açıklaması (problem, çözüm, hedef kullanıcı, ölçeklenebilirlik, benimsenme kolaylığı); 3-5 dk demo videosu; herkese açık GitHub reposu (kaynak + dokümantasyon); "working prototype, mockup, or proof-of-concept".
- **Prototip kararı:** Video + repo + Sepolia'da Etherscan'de doğrulanmış sözleşme. Barındırılan canlı demo zorunlu değil. Repo, API anahtarı olmadan da yerelde çalışabilmeli (önceden üretilmiş raporlarla).
- **Jüri kriterleri:** Climate Impact · Innovation & Creativity · Technical Execution · Practical Usefulness · Presentation & Storytelling (iklim problemi, nasıl çalıştığı, gerçek dünya etkisi).

## Takım

- 2 kişi, ikisi de ilk kez blokzincir yarışmasında. Kapsam buna göre sade tutuldu (ayrı backend servisi yok, bkz. Mimari).
- Görev bölümü (14 Ekim): Proje geliştirmesini (sözleşme, gizlilik, zincir istemcisi, arayüz, README, video) kullanıcı yürütüyor. İkinci ekip üyesi Turnike'yi geliştiren arkadaş; Turnike-Carbon hazır olursa karar katmanında Jev'in yerine entegre edilir. Şimdilik odak geliştirmede, Turnike entegrasyonu sonraya.

## Problem (sunumda kullanılacak)

- **Ana rakam (kendimiz hesaplayacağız):** OffsetsDB'de iptal kayıtlarının ne kadarında "kimin adına iptal edildiği" bilgisi yok. CarbonPlan'in kendi yazısı: 1,34 milyar iptalin yalnızca 0,67 milyarında bu bilgi var (~%50). https://carbonplan.org/blog/offsets-db-additions
  - "Anonim" tanımını açık yap: boş alan / kod veya kısaltma (ör. "DL") / aracı adına ("on behalf of client") ayrı kategoriler.
- Destekleyici (ikincil, kaynaksız olduğunu bil): Relae, son 3 yılda spot piyasadaki iptallerin %55'inin anonim olduğunu söylüyor ama kaynak göstermiyor. https://relae.co/blog/voluntary-carbon-market-trends-2026
- Greenhushing: şirketler dava korkusuyla iddialarını gizliyor. (400+ yaptırım rakamı bir blogdan, doğrulanmadı; sadece eğilim olarak kullan.)
- **Gerilim:** Şirketler gizlilik istiyor, piyasa denetlenebilirlik istiyor. Bu proje ikisini birden sağlıyor.

## Çözüm (tek cümle)

Kredinin iptal edildiği **herkese açık ve tek seferlik** olur, alıcının kimliği zincirde **gizli** kalır ama **yetkili denetçi açabilir ve zincirde onaylar**. Üç katmanlı bir kalite değerlendirmesi proje belgelerini ICVCM ilkelerine göre inceler: metodoloji durumu (deterministik), LLM ile **kodla doğrulanmış alıntılar**, karar modeli ile **olasılıklı kanıt değerlendirmesi**. Raporun hash'i ve yöntem sürümü zincire demirlenir.

## Değişmez tasarım kuralları

1. **İptal edilen kredi asla yeniden alınıp satılabilir bir token'a dönüşmez.** Zincir sadece kanıt kaydı tutar. (Verra Nisan 2022'de iptal edilmiş kredilerin tokenlaştırılmasını yasakladı: https://verra.org/verra-bans-greenwashing-cryptos-using-retired-credits/ . README ve videoda açıkça söyle.)
2. **Her kredi birimi yalnızca bir kez iptal edilebilir.** İptaller seri **aralığı** olarak yapılır; aynı ihraç partisinde örtüşen aralık sözleşme seviyesinde reddedilir.
3. **Zincire kişisel veri yazılmaz.** Sadece hash, taahhüt, skor ve seri aralığı yazılır.
4. **AI çıktısı hüküm değil, sinyaldir.** "Proje kötü" değil, "şu ilkede belgede kanıt bulunamadı" denir.
5. **AI'ın her bulgusu belgeden birebir alıntı içermeli ve alıntı kodla doğrulanmalı.** Doğrulanamayan bulgu atılır.
6. **Gerçek iptal yapmıyoruz.** Bu, kayıt sistemlerinin üzerine eklenecek bir **doğrulama ve gizlilik katmanının prototipidir**. Seri numaraları simüle edilmiştir (bkz. Veri). Her yerde dürüstçe belirt.
7. **Bu bir sıfır bilgi kanıtı (ZK) sistemi değil.** Hash taahhüdü + şifreleme. ZK yalnızca "gelecek çalışma".
8. **AI'ı olduğundan farklı gösterme.** Jev 1.13 TypeSafe'in modelidir, bizim değil. Turnike 4B ekip arkadaşının kendi modelidir (Qwen3-Reranker-4B + LoRA, Jev'den distile değil); kullanılırsa öyle anılır. Her raporda hangi modellerin kullanıldığı yazar.
9. **AI skoru ICVCM uygunluğu değildir.** Skor yalnızca "belgedeki kanıtın yeterliliği" sinyalidir; ICVCM değerlendirmesi program ve metodoloji düzeyindedir. Arayüz ve README bunu açıkça söyler.

## Tehdit modeli (README'de açıkça yaz)

- Gizlilik **kamuya karşıdır**, kayıt sistemine karşı değil. Operator (kayıt sistemi rolü) alıcıyı zaten tanır; gerçekte de Verra hesap sahibini KYC'den bilir.
- Zincirde görünenler: proje, seri aralığı, miktar, zaman, operator adresi. Görünmeyen: alıcı kimliği.
- Aynı alıcının farklı iptalleri farklı tuzlarla yapıldığı için birbirine bağlanamaz.
- Tek denetçi (demo). Çoklu denetçi / anahtar rotasyonu gelecek çalışma.

## Mimari

Ayrı FastAPI servisi yok: Streamlit doğrudan `core` Python paketini çağırır (2 kişilik takım için daha az parça). Benimsenme hikâyesinde "kayıt sistemleri bu katmanı API olarak entegre eder" denir; zaman kalırsa ince bir FastAPI eklenir.

```
[Verra PDD/izleme PDF'leri] ─► core/ai (LLM + Jev 1.13 via OpenRouter) ─► kalite raporu JSON (+ doğrulanmış alıntılar)
                                         │                                  │ reports/ klasöründe yayımlanır
[OffsetsDB anlık görüntüsü] ─► core/data │                                  ▼
                                         ▼                    [RetirementRegistry @ Sepolia]
                              core/chain (web3.py) ───────────►  • ihraç partileri (seri aralığı)
                              core/privacy (taahhüt, kasa)       • kalite raporları (hash + skor, sürümlü)
                                         │                       • iptaller (aralık + taahhüt + kasa hash'i)
                                         ▼                       • denetçi onayları
                              [Şifreli kasa: SQLite, zincir dışı]
                                         │
                                         ▼
                 [Streamlit: Alıcı · Herkese açık doğrulama · Denetçi · Proje kalitesi]
```

## Kimlik ve kodlama kuralları (Python ↔ Solidity birebir aynı olmalı)

- Tüm metin kimlikleri `bytes32` olarak: `Web3.keccak(text=<kanonik string>)`. **`hashlib.sha3_256` kullanma** (NIST SHA-3, keccak256 ile aynı değil).
- `projectId = keccak(text=<OffsetsDB project_id>)`, tire yok: `"VCS1477"` (14 Ekim düzeltmesi: eski taslaktaki `"VCS-1748"` örneği OffsetsDB biçimiyle çelişiyordu).
- `batchId = keccak(text=<kanonik parti anahtarı>)`. Anahtarın biçimi `core/data` (iş paketi 4) içinde tek yerde tanımlanır; sözleşme biçimden bağımsızdır.
- `buyerId = keccak(text="LEI:" + <20 karakter LEI, büyük harf>)`. LEI = ISO 17442 Legal Entity Identifier. **Demoda gerçek şirket kullanılmaz:** kurgusal şirketler, geçerli mod-97 kontrol haneli LEI biçimiyle üretilir.
- **`buyerCommitment = keccak256(abi.encode(buyerId, salt, batchId, start, end))`** (14 Ekim değişikliği; eski taslak `encodePacked(buyerId, salt)` idi). Taahhüt iptal aralığına bağlıdır: ifşa edilen bir tuz yalnızca o iptali kanıtlar, başka bir iptale kopyalanan taahhüt doğrulanmaz. Python: `keccak(eth_abi.encode(['bytes32','bytes32','bytes32','uint64','uint64'], [...]))`. Sözleşmede `commitmentOf(...)` pure fonksiyonu aynı hesabı yapar. `cast` ile Python'un aynı sonucu verdiği doğrulandı. `salt = secrets.token_bytes(32)`.
- Python (pytest) ve Foundry aynı sabit test vektörlerini kullanır; `tests/vectors.json` iki tarafın da okuduğu tek kaynak.

## Gizlilik mekanizması

**Durum (14 Ekim): `core/privacy/` yazıldı ve test edildi.** `identity.py` (LEI doğrulama/kurgusal LEI üretimi, `text_id`, `project_id`, `buyer_id`), `commitment.py` (aralığa bağlı taahhüt, tuz), `vault.py` (SealedBox kasası, `audit()` 6 kontrol: kasa hash'i, kasa açılıyor mu, aralık, LEI geçerli mi, LEI↔buyerId, taahhüt; SQLite `VaultStore`), `receipt.py` (makbuz + çevrimdışı taahhüt kontrolü). Ortak vektörler: `scripts/gen_vectors.py` → `tests/vectors.json`, hem `tests/test_privacy.py` hem `contracts/test/Vectors.t.sol` doğrular. Denetçi kasa anahtarları `scripts/gen_auditor_keys.py` ile `.env`'ye yazıldı (demo: tüm roller tek makinede). **Testlerde bile gerçek LEI kullanılmaz** (`ONCE00SEALEDDEMO0143` gibi kurgusal kodlar).

1. **İptal:** Backend tuzu üretir, taahhüdü hesaplar, zincire sadece taahhüdü yazar.
2. **Denetçi kasası:** `{batch_id, start, end, lei, buyer_id, salt, version}` kanonik JSON'u denetçinin açık anahtarıyla **PyNaCl `SealedBox`** ile şifrelenir, SQLite'ta saklanır. Zincire `auditVaultHash = keccak256(ciphertext)` yazılır.
3. **Denetçi doğrulaması:** Denetçi kasayı açar, kasa hash'ini ve taahhüdü yeniden hesaplar, zincirdekiyle karşılaştırır, sonra `attestRetirement(id, valid)` ile sonucu **zincire yazar**. Herkese açık ekran "iptal edildi + denetçi tarafından doğrulandı" gösterir, kimliği göstermez.
4. **Seçici ifşa:** Alıcı isterse LEI + tuzu paylaşır; herkes `verifyClaim` (view, işlem yayınlamaz) ile doğrular.
5. **İptal makbuzu:** İptal sonunda alıcıya bir kez `retirement_receipt.json` indirilir: `{retirementId, chainId, contract, txHash, serial, lei, salt}`. Tuz sunucuda düz metin tutulmaz (sadece kasada şifreli). Arayüzde uyarı: "Bu dosyaya sahip olan herkes iptali sizin adınıza iddia edebilir, gizli tutun."

## Akıllı sözleşme: `RetirementRegistry` (Solidity ^0.8.24, solc 0.8.28, OpenZeppelin `AccessControl` + `SafeCast`)

**Durum (14 Ekim): yazıldı, 27 Foundry testi geçiyor (2 fuzz testi × 1000 senaryo dahil), lint uyarısı yok, CI'da.** Dosyalar: `contracts/src/RetirementRegistry.sol`, `contracts/test/RetirementRegistry.t.sol`. Gaz: `retire` ~150-215k (partide her önceki iptal birkaç bin gaz ekler), `registerBatch` ~72k, `attestRetirement` ~29k.

14 Ekim'de taslağa göre yapılan iyileştirmeler:
- Taahhüt iptal aralığına bağlandı (bkz. Kimlik kuralları).
- Sıfır değer kontrolleri: sıfır taahhüt, kasa hash'i, rapor hash'i, yöntem hash'i, parti/proje kimliği → `ZeroValue`.
- Denetçi onayı **tek seferlik ve kesin**: `Pending → Verified | Rejected`; ikinci onay `AlreadyAttested`.
- Rapor sürümleri 1'den başlar; iptal kaydındaki `reportVersion = 0` "iptal anında rapor yoktu" demektir.
- Arayüz için ek view'lar: `getBatch`, `batchRetirements`, `retirementOf` (seriyi kapsayan iptal id'si), `reportCount`, `commitmentOf`, `retirementCount`.
- Bilinmeyen kayıtlar için `UnknownRetirement`, `UnknownReport` hataları.
- `retire` sadece operator'e açık olduğu için doğrusal örtüşme taraması dışarıdan şişirilemez (DoS riski yok); ölçek notu README'ye.

Aşağıdaki özgün tasarım metni bağlam için duruyor; çelişki varsa yukarıdaki ve kod esastır.

Roller: `DEFAULT_ADMIN_ROLE` (rol atar), `ASSESSOR_ROLE` (kalite raporu), `OPERATOR_ROLE` (ihraç partisi + iptal), `AUDITOR_ROLE` (onay).

Fonksiyonlar:
- `registerBatch(bytes32 batchId, bytes32 projectId, uint64 firstSerial, uint64 lastSerial)` — operator. İhraç partisini tanımlar; bu aralığın dışındaki iptal reddedilir. Aynı parti iki kez → `BatchExists`.
- `registerQualityReport(bytes32 projectId, bytes32 reportHash, uint16 score, bytes32 methodHash)` — assessor. Sürümlü (eski sürümler korunur). `score > 100` → `InvalidScore`. `methodHash` hangi modellerin ve soru şemasının kullanıldığını sabitler.
- `retire(bytes32 batchId, uint64 start, uint64 end, bytes32 buyerCommitment, bytes32 auditVaultHash) returns (uint256 retirementId)` — operator.
  - `start > end` veya parti dışı → `InvalidRange`; parti yok → `UnknownBatch`.
  - Partideki önceki iptallerle örtüşme → `AlreadyRetired(uint256 conflictingRetirementId)`. Kontrol, partinin iptal listesi üzerinde doğrusal tarama (demo ölçeği için yeterli; README'de ölçek notu: üretimde sıralı aralık ağacı).
  - İptal anındaki projenin **güncel kalite raporu sürümü** iptal kaydına yazılır.
- `attestRetirement(uint256 retirementId, bool valid)` — auditor.
- View: `getRetirement(id)`, `isRetired(bytes32 batchId, uint64 serial)`, `verifyClaim(uint256 id, bytes32 buyerId, bytes32 salt)`, `latestReport(projectId)`, `getReport(projectId, version)`.
- Olaylar: `BatchRegistered`, `QualityReportRegistered`, `CreditRetired`, `RetirementAttested`.

Foundry testleri: başarılı iptal; tam/kısmi örtüşmede revert; bitişik aralıklar (100-199 ve 200-299) kabul; parti dışı revert; yetkisiz çağrı revert; doğru/yanlış tuzla `verifyClaim`; skor > 100 revert; iptal kaydında rapor sürümü; onay olayı; Python ile ortak test vektörleri.

Not: Taslakta anılan önceki `ClimateRegistry.sol` bu klasörde yok; sıfırdan yazılacak.

## Zincir istemcisi ve uçtan uca akış

**Durum (14 Ekim): yazıldı ve test edildi.**
- `core/chain/registry.py`: `Registry.deploy` (deployer admin olur, assessor/operator/auditor rollerini verir), yazma işlemleri **önce simüle edilir** (`eth_call`), revert'ler okunur `RegistryError("AlreadyRetired", {...})` olarak döner; okuma fonksiyonları dataclass döndürür. web3.py 8.0.0.
- `core/chain/artifacts/RetirementRegistry.json`: commit'lenen ABI + bytecode (`scripts/export_artifact.py` ile `forge build` çıktısından). Sözleşme değişince yeniden dışa aktar; CI ABI'nin güncel olduğunu kontrol eder.
- `core/chain/deployments.py` → `deployments/<chain_id>.json` (Sepolia commit'lenir, Anvil `31337` gitignore'da). `core/chain/anvil.py`: Anvil başlatma ve `anvil_setBalance` ile fonlama.
- `core/data/batches.py`: `IssuanceBatch`, kanonik parti anahtarı `"<project>|<vintage>|<batch_no:03d>"` (ör. `VCS1477|2020|001`), görüntü etiketi `SIM-...` (simüle olduğu belli olsun).
- `core/service.py` (`OnceSealed`): Streamlit'in kullanacağı akışlar: `ensure_batch`, `publish_report` (yayımlanan rapor dosyasının hash'i + method hash + toplam skor), `retire` (tuz → taahhüt → kasa şifreleme → **önce simülasyon**, sonra kasa kaydı + iptal + makbuz; reddedilen iptal kasada artık bırakmaz), `audit` (kasa aç, 6 kontrol, zincire onay), `verify_receipt`, `public_record`.
- Betikler: `python scripts/demo_e2e.py` (geçici Anvil başlatır, videodaki akışı 7 adımda oynatır), `python scripts/deploy.py --network anvil|sepolia`.
- Testler: `tests/test_chain_e2e.py` (6 test, geçici Anvil + geçici anahtarlar; `.env` gerektirmez, CI'da Foundry toolchain ile koşar). Kötü niyetli operator senaryosu (taahhüt A'ya, kasa B'ye) denetçi tarafından yakalanıp `REJECTED` yazılıyor.
- Ölçülen gaz (Anvil): deploy 1,41M, `registerBatch` 72k, `retire` 214k (ilk), `attestRetirement` 31k.

## AI kalite servisi

### Üç katman (karar: 13 Ekim, ekip onaylı)

1. **Metodoloji durumu (deterministik, AI yok):** Projenin metodolojisinin ICVCM kararı, kaynaklı bir tablodan (`core/ai/methodology_status.json`, sürümlü). Şimdilik: ACM0002 reddedildi (ek katkı, Ağu 2024); ACM0001 v15-19 koşullu onaylı; VM0007 ICVCM değerlendirmesine girmedi (onaylı olan VM0048, Kas 2024); VMR0006 onaysız, yerini alan VM0050 koşullu onaylı.
2. **LLM — kanıt çıkarma:** Sabit model `deepseek/deepseek-v4.1-flash` (OpenRouter chat API, `AI_MODEL`). Router kullanılmaz (her istekte farklı model seçtiği için tekrarlanamıyordu). Alıntı + gerekçe üretir; alıntılar kodla doğrulanır.
3. **Karar modeli — kanıt yeterliliği:** Değiştirilebilir arayüz arkasında (`DecisionModel`). Şimdilik **TypeSafe Jev 1.13** (`typesafe/jev-1.13`, OpenRouter `POST /api/alpha/decisions`; chat endpoint'i ile çalışmaz). İleride **Turnike 4B / Turnike-Carbon** (ekip arkadaşının modeli, Qwen3-Reranker-4B + LoRA, yerel çalışabilir) aynı soru şemasıyla takılır. Hangisinin kullanılacağına **etiketli test kümesindeki sonuçlara göre** karar verilir.
   - Soru türleri: `choice` (seçenek + olasılıklar + confidence), `noul` (evet/hayır olasılığı), `score` (2-10 seviyeli ölçek). Soru şeması sürümlüdür ve iki model için ortaktır.
   - **Confidence kalibre değildir:** modelin kararlılığını gösterir, doğruluğunu değil. İnsan incelemesi eşiği etiketli veriyle kalibre edilene kadar sabit bir eşik "doğruluk" gibi sunulmaz.
   - "Needs human review?" gibi `noul` sorusu ilk denemede ayırt edici çıkmadı (her yerde 0,73-0,86); kullanılmaz.
   - Açık soru: Jev'e LLM'in seçtiği alıntılar mı (seçim yanlılığı riski) yoksa kodun seçtiği ham bölümler mi verilecek? Etiketli kümede ikisi karşılaştırılacak.
- **Zincire yazılan:** rapor hash'i + skor + `methodHash` = keccak256(kanonik JSON: soru şeması sürümü, prompt sürümü, LLM modeli, karar modeli sürümü, metodoloji tablosu sürümü). Değerlendirme sonradan denetlenebilir olmalı.
- **Etiketli test kümesi (gold set):** 20-50 kanıt parçası, ekip tarafından yazılı etiketleme kurallarına göre elle etiketlenir. **Hiçbir modelin çıktısı doğru etiket kabul edilmez.** Ölçütler: accuracy / macro-F1, kalibrasyon (ECE / Brier), tutarlılık (tekrar çalıştırma), gecikme, 1000 değerlendirme maliyeti. Aynı küme Jev 1.13, Turnike ve genel LLM karşılaştırmasında kullanılır.
- **Turnike** ekip arkadaşının bağımsız modelidir; **Jev'den distile edilmemiştir** ve doğrudan bir Jev alternatifi değildir (önceden belirlenmiş alanlarda benchmark'lı, açık kaynak kısmı Hugging Face'te yayımlanacak). Karbon görevi için yeniden eğitim gerekebilir. **Turnike-Carbon eğitimi** arkadaşın işidir (Colab, karbon için ayrı adaptör). Bu repo ona ortak soru şemasını ve kanıt parçalarını JSONL olarak verir. README'de Turnike'nin eğitim verisi (sentetik kısım dahil) arkadaşın verdiği bilgiyle, olduğu gibi anlatılır.
- **Modelden bağımsız istemciler:** `base_url`, `model`, anahtar config'ten gelir; LLM veya karar modelini değiştirmek kod değil config değişikliği olmalı.
- **Ölçek farkı:** LLM'in 0-100'ü ile Jev'in 0-3'ü doğrudan karşılaştırılmaz; hangisinin doğru olduğunu yalnızca etiketli küme gösterir.
- **Girdi:** Verra PDD / izleme raporu PDF (metin katmanı olan; taranmış PDF seçme).
- **Hat:**
  1. PDF → metin (PyMuPDF), sayfa numaralarıyla; paragraflara böl, her birine kimlik ver: `[p12-03]`.
  2. Her ilke için anahtar kelimeyle ilgili paragrafları seç (baseline, additionality, investment/barrier analysis, monitoring, leakage, permanence, non-permanence risk/buffer, double counting/registration, safeguards, stakeholder consultation, FPIC) ve bağlama sığacak şekilde gönder.
  3. Model ilke başına JSON döndürür; her bulgu `paragraph_id` + kısa birebir alıntı içerir.
  4. **Alıntı doğrulama:** Alıntı önce **belirtilen paragrafın içinde** aranır. Normalizasyon: Unicode NFKC, ligatür açma (ﬁ→fi), satır sonu tirelerini birleştirme (`-\n`), tırnak/tire karakterlerini tekleştirme, boşluk sıkıştırma, küçük harf. Yedek: sadece harf-rakam karşılaştırması, **yalnızca ≥ 40 karakterlik alıntılar için**. Bulunamazsa bulgu atılır, `dropped_findings` artar.
  5. Doğrulanmış alıntısı kalmayan ilke → `no_evidence`, skor 0 (karar modeline gönderilmez).
  6. Toplam skor = sayısal skoru olan ilkelerin ağırlıklı ortalaması (ağırlıklar `principles.py`'de, yeniden normalize edilir); arayüzde ilke skorları her zaman ayrı gösterilir.
  7. Rapor kanonik JSON (`sort_keys=True`, `separators=(",", ":")`, `ensure_ascii=False`, UTF-8) → `keccak256` → zincire. **Rapor JSON'u `reports/` altında yayımlanır** ki herkes hash'i yeniden hesaplayabilsin.
  8. Model geçersiz JSON döndürürse bir kez yeniden dene ("sadece JSON" uyarısıyla); yine olmazsa ilke `assessment_failed`, skor `null` (toplam skora girmez; "kanıt yok" değildir), hata loglanır.
  9. `not_applicable`: skor `null`, toplam skora girmez. Kalıcılık için karar kuraldan gelir (`reversal_risk: false`); diğer ilkelerde LLM `not_applicable` derse aktivite türünü gösteren doğrulanmış alıntı gerekir.
- **Kod:** `core/ai/` (`pdf_extract`, `quotes`, `principles`, `select`, `client`, `assess` = katman 2; `methodology` + `methodology_status.json` = katman 1; `decision` = katman 3; `report` = birleştirme). `core/hashing.py` kanonik JSON + keccak (zincir istemcisi de kullanacak).
  - Rapor üret: `python scripts/assess_project.py VCS1851 [--principles ...] [--no-cache]` → `reports/<id>.json` (yayımlanır), `data/runs/reports/` (maliyet/log), `data/evidence/<id>.jsonl` (Turnike için kanıt + soru şeması; Jev cevapları bilerek dışarıda).
  - Eski deneme betiği: `scripts/jev_smoke_test.py` (sadece katman 2).
- **Uygulanan kurallar (14 Ekim öncesi gece):**
  - Nihai ilke durumu karar modelinin güç puanından türer: `no_evidence | assertion_only | partial_evidence | strong_evidence`, artı `not_applicable`, `assessment_failed`. Skor = güç/3 × 100. LLM'in kendi puanı raporda sadece şeffaflık için durur.
  - Jev'in iki sorusu (kanıt türü vs güç) ≥ 2 seviye ayrışırsa `review_flags: ["decision_questions_disagree"]`.
  - **Kalıcılık kuralı:** manifest'te `reversal_risk: false` olan projelerde (güneş, çöp gazı, ocak) kalıcılık LLM'e sorulmadan `not_applicable` (LLM aynı belgede bazen "uygulanmaz", bazen "kanıt yok" diyordu).
  - LLM kanıtı önbelleğe alınır (`data/cache/llm/`, belge hash + ilke + prompt sürümü + model). Yeniden çalıştırma aynı alıntıları kullanır; Jev'in kendi oynaması ±2 puan.
  - Bozuk JSON'da `json-repair` ile onarım denenir (alıntılar sonradan zaten doğrulanıyor).
  - Rapor hash'i yayımlanan dosyadan yeniden hesaplanabiliyor (dört raporda doğrulandı).
- **İlk ölçüm (13 Ekim, 4 PDF × 5 ilke, prompt v1):** 20/20 sonuç, 72 alıntının 72'si doğrulandı (70 birebir, 2 harf-rakam), 0 atılan. Toplam ~0,13 $. Jev 4 farklı modele yönlendirdi (çoğunlukla deepseek-v4.1-flash). Aynı girdide puan 78→82 oynadı (tekrarlanabilirlik sorunu). Bir çağrıda model JSON yerine düşünce metni yazıp token sınırına takıldı (düzeltildi).
- **Rapor meta verisi:** PDF SHA-256, istenen model, cevap veren model, prompt sürümü, çıkarım aracı sürümü, tarih.
- **Ölçüt — ICVCM Core Carbon Principles** (https://icvcm.org/?p=2349). ICVCM'de 10 ilke var; biz belgeden kanıtlanabilen 5'ini puanlıyoruz, diğerleri (program yönetişimi, izleme/kayıt, bağımsız doğrulama, şeffaflık, net sıfır uyumu, sürdürülebilir kalkınma etkileri) kapsam dışı diye belirtilir:
  - `additionality` · `permanence` · `robust_quantification` · `no_double_counting` · `safeguards`
- **LLM çıktı şeması (ilke başına, katman 2):** `{principle, status: evidence_found|evidence_weak|no_evidence|not_applicable, score, rationale, quotes: [{paragraph_id, text}]}`. Nihai rapor şeması (`report-v1`) için örnek: `reports/VCS1851.json`.
- **Not (ICVCM ile karşılaştırma):** İlk denemede belge kanıtı ICVCM'in metodoloji kararlarıyla örtüşmedi (güneş belgesi ayrıntılı IRR analizi içeriyor). Bu beklenen bir durum: belge kanıtı ≠ metodoloji sağlamlığı. Bu yüzden katman 1 ayrı ve deterministik.

## Veri kaynakları

- **CarbonPlan OffsetsDB** — https://offsets-db-data.readthedocs.io/en/latest/data-access.html
  - İndirme: `offsets-db.parquet.zip` (veya csv). Güncellemeler şu an duraklatılmış; indirilen anlık görüntünün tarihini README'ye yaz.
  - İlgili alanlar: `project_id`, `vintage`, `quantity`, `transaction_type`, `transaction_date`, `retirement_beneficiary`, `retirement_beneficiary_harmonized`, `retirement_account`, `retirement_note`, `retirement_reason`.
  - **Seri numarası alanı yok.** Gerçek proje kimliği, vintage ve ihraç miktarı buradan gelir.
  - Lisans: telif talep edilmiyor, Terms of Data Access'e tabi. README'de CarbonPlan ve kayıt sistemlerini kaynak göster.
- **Seri numaraları (karar: simüle):** Gerçek proje + gerçek vintage + OffsetsDB'deki gerçek ihraç miktarına dayanan, **Verra biçiminde ama simüle** seri aralıkları. Verra biçimi örneği: `0001-000001-000100-VCS-VCU-003-VER-US-0003-01012020-31122020-1` (başlangıç-bitiş aralığı içerir; segmentlerin tam anlamı Verra belgesinden doğrulanmadı, sadece biçim için kullan). Arayüzde ve README'de "simulated serials" etiketi.
  - **İndirilen anlık görüntü:** `data/raw/offsetsdb/` (gitignore'da), `generated_at = 2026-06-01T20:33:13Z`, 11.659 proje, 532.799 kredi işlemi (495.403 retirement).
- **Verra Registry PDF'leri** — elle indirilir (otomatik kazıma yok; belge indirme zaten oturum gerektiriyor). **PDF'ler repoya konmaz**; `samples/manifest.json` içinde URL + dosya adı + SHA-256 tutulur. Seçilen projeler (ICVCM kararlarıyla karşılaştırılabilir üçlü):
  - `VCS1477` Katingan, REDD+/turbalık (VM0007) — kalıcılık ve güvenceler
  - `VCS1851` ReNew Solar, şebekeye bağlı güneş (ACM0002) — ICVCM bu kategoriyi ek katkı gerekçesiyle reddetti
  - `VCS138` Greater New Bedford, çöp gazı (ACM0001) — ICVCM ACM0001 v15-19'u koşullu onayladı
  - `VCS2505` Güney Afrika ocak projesi (VMR0006) — opsiyonel dördüncü
- **ICVCM CCP** — puanlama ölçütü.

## Teknoloji yığını

| Katman | Araç |
|---|---|
| Sözleşme | Solidity ^0.8.20, Foundry v1.8.5 (`~/.foundry/bin`, PATH'te değil), OpenZeppelin Contracts v5.7.0 (`contracts/lib/`) |
| Test ağı | Sepolia (uygulama geliştirme için önerilen; Holesky Eylül 2025'te kullanımdan kalktı). Yerel: Anvil |
| Zincir istemcisi | web3.py |
| Çekirdek | Python 3.11+ paket (`core/`) |
| PDF | PyMuPDF |
| AI | OpenRouter: LLM `deepseek/deepseek-v4.1-flash` (chat API) + karar modeli `typesafe/jev-1.13` (decisions API) |
| Şifreleme | PyNaCl (`SealedBox`) |
| Depolama | SQLite (kasa), `reports/` (yayımlanan rapor JSON'ları) |
| Arayüz | Streamlit |
| Veri | pandas, pyarrow |

Sırlar (`.env`, asla commit'lenmez; `.env.example` commit'lenir): `SEPOLIA_RPC_URL`, `DEPLOYER_PRIVATE_KEY`, `ASSESSOR_PRIVATE_KEY`, `OPERATOR_PRIVATE_KEY`, `AUDITOR_PRIVATE_KEY`, `AUDITOR_BOX_PUBLIC_KEY`, `AUDITOR_BOX_PRIVATE_KEY` (demo), `OPENROUTER_API_KEY`, `AI_MODEL`, `AI_BASE_URL`, `ETHERSCAN_API_KEY`. OpenRouter anahtarı bu projeye özel. Test cüzdanları ana ağ cüzdanlarından ayrı.

## Repo yapısı

```
contracts/          Foundry projesi (src/, test/, script/)
core/
  chain/            web3.py istemcisi, ABI
  privacy/          kimlik kodlama, taahhüt, tuz, SealedBox kasası
  ai/               PDF hattı, OpenRouter istemcisi, alıntı doğrulama, puanlama, rapor hash'i
  data/             OffsetsDB yükleme, simüle seri üretimi
app/                Streamlit (çok sayfalı)
tests/              pytest + vectors.json (Foundry ile ortak)
notebooks/          anonymity_stats.ipynb
reports/            yayımlanan kalite raporları (JSON)
samples/            manifest.json (PDF URL + SHA-256), PDF'lerin kendisi değil
docs/               mimari diyagram, demo senaryosu, değerlendirme sonuçları
```

## Demo senaryosu (video, İngilizce, 3-5 dk)

1. Problem: OffsetsDB'den kendi hesapladığımız anonimlik oranı + greenhushing gerilimi.
2. Bir Verra projesinin PDF'i → Jev raporu: ilke skorları, belgeden alıntılar (vurgulanmış), atılan bulgu sayısı → rapor hash'i zincirde.
3. Alıcı (kurgusal şirket) bir seri aralığını iptal eder → zincirde sadece taahhüt; makbuz indirilir.
4. Örtüşen aralık iptal edilmeye çalışılır → `AlreadyRetired` ile reddedilir.
5. Denetçi kasayı açar, taahhüdü doğrular, zincire onay yazar → herkese açık ekranda "audited ✓".
6. Alıcı makbuzu paylaşır → herkese açık doğrulama ekranı "claim verified".
7. Etherscan (Sepolia): doğrulanmış sözleşme ve işlemler.
8. Kapanış: neden token yok (Verra 2022), neden ZK değil, gerçek dünyada kayıt sistemlerine nasıl eklenir.

## Takvim (14 Ekim'de güncellendi)

**Bitti (13 Ekim):** kurulum (Python, Foundry, cüzdanlar, 0,05 Sepolia ETH, OpenRouter), OffsetsDB, 4 PDF, AI hattının üç katmanı + 4 rapor, GitHub (private) + CI. AI hattı planın ~3 gün önünde.

| # | Tarih | İş paketi | Bitti sayılması için |
|---|---|---|---|
| 1 | 14-15 Ekim | `RetirementRegistry` + Foundry testleri | Tüm testler geçer; `forge test` CI'da |
| 2 | 15-16 Ekim | Gizlilik modülü (`core/privacy`): kurgusal LEI üretimi (mod-97), taahhüt, SealedBox kasası (SQLite), makbuz; `tests/vectors.json` | Python ve Foundry aynı vektörlerle aynı hash'i üretir |
| 3 | 16-17 Ekim | Zincir istemcisi (`core/chain`, web3.py) + deploy betiği; Anvil'de uçtan uca senaryo | Parti → rapor → iptal → örtüşme reddi → denetçi onayı → `verifyClaim`, tek komutla |
| 4 | 17 Ekim | Simüle seri verisi (`core/data`): OffsetsDB ihraç kayıtlarından Verra biçiminde partiler | 4 proje için partiler hazır |
| 5 | 18 Ekim | Anonimlik notebook'u (OffsetsDB) | Sunum için kendi hesapladığımız oran + grafik |
| 6 | 18-20 Ekim | Streamlit: alıcı, herkese açık doğrulama, denetçi, proje kalitesi ekranları | Demo senaryosu arayüzden baştan sona oynar |
| 7 | 21 Ekim | Sepolia deploy + Etherscan doğrulama; raporların zincire yazılması | Etherscan'de doğrulanmış sözleşme ve işlemler |
| 8 | 21-22 Ekim | (Opsiyonel) etiketli küme / Turnike karşılaştırması | Turnike durumuna göre karar |
| 9 | 22-23 Ekim | Tampon; README son hâli, mimari diyagram, repo public | README eksiksiz, repo public |
| 10 | 24 Ekim | Demo videosu (3-5 dk), Devpost açıklaması. **Gece itibarıyla her şey bitmiş olmalı** | Video yüklü, Devpost taslağı dolu |
| 11 | 25 Ekim | Sabah teslim; son saat 17:00 TR | Gönderildi |

## Kapsam dışı

- Gerçek kayıt sistemlerinde iptal
- İptal edilmiş kredileri token'a çevirmek, ikincil piyasa
- Sıfır bilgi kanıtları (sadece "gelecek çalışma")
- Çoklu denetçi, anahtar rotasyonu (gelecek çalışma)
- Ana ağ (mainnet) deploy
- Kayıt sitelerinden otomatik veri kazıma
- Ayrı backend servisi (zaman kalırsa ince FastAPI)

## Açık konular

- Etiketli test kümesi: yapılıp yapılmayacağı ve zamanı, Turnike-Carbon'un hazır olma tarihine bağlı (ertelendi).
- Jev'e alıntılar mı, ham bölümler mi verilecek (etiketli kümeyle karşılaştırılacak).
- Repo public yapılmadan önce CLAUDE.md ve `docs/presentation_notes.md` (ikisi de Türkçe, ekip içi) repoda kalacak mı?
