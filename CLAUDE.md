# OnceSealed — Gizli ama Denetlenebilir Karbon Kredisi İptali

Proje adı **OnceSealed** ("once": her kredi bir kez iptal edilir; "sealed": alıcı kimliği mühürlü). GitHub repo: https://github.com/lsaliherenl/OnceSealed (**şimdilik private**; teslimden önce public yapılacak, o zaman CLAUDE.md'nin repoda kalıp kalmayacağına yeniden karar verilecek). Yerel klasör adı `ClimateChain` olarak kalır. Foundry kütüphaneleri git submodule (`git clone --recurse-submodules`). CI: `.github/workflows/ci.yml` (pytest).

Bu dosya projenin iç bağlamıdır. Her oturumda önce bunu oku, tasarım kurallarına uy.

**Kararlar (14 Ekim akşamı):**
- **Arayüz: Next.js (React) + ince FastAPI** (Streamlit yerine). FastAPI `core/service.py`'yi sarar ve operator/denetçi anahtarlarını tutar (demo). **Herkese açık doğrulama sayfası sunucuya uğramaz:** tarayıcı sözleşmeyi viem ile doğrudan Sepolia'dan okur, makbuz kontrolü tarayıcıda hesaplanır ("bize güvenmeniz gerekmiyor"). Tasarım taslağını kullanıcı Claude Design'da hazırlıyor.
- **Derinlik (D1-D4), yeni özellik değil ölçüm:** ayrıntılı plan `docs/evaluation_plan.md`. D1 AI doğruluğu (evet/hayır kontrol listesi etiketi + P/R/F1 + kappa, etiketsiz sağlamlık testleri, CCQI/BeZero/Calyx/Probst 2024 dış referansları; 11 belge), D2 ölçek (Katingan'ın 4.477 gerçek iptalini oynatma → doğrusal tarama kırılır → ipuçlu sıralı liste), D3 tehdit modeli + `AccessControlDefaultAdminRules` + Slither + meta veriden kimlik eşleştirme riski ölçümü, D4 gerçek kayıtlar (OffsetsDB'de iptal > ihraç olan 11 proje-vintage, 235.932 ton).

**15 Ekim durumu (D1-D4 ve API):**
- **D2 ölçek (bitti):** Gerçek OffsetsDB geçmişi Anvil'de oynatıldı (`scripts/scale_replay.py`, sonuçlar `data/derived/scale/`, grafik `docs/figures/scale_gas.png`). Eski doğrusal tarama: her önceki iptal ~4.800 gaz ekliyor; VCS766/2009'un 38.382 gerçek iptalinden **7.467.'de 36M blok sınırında başarısız** (partinin %19,5'i). **Yeni sözleşme: ipuçlu sıralı bağlı liste**, `retire(..., prevHint)`; her iptal **sabit ~211k gaz**; yanlış/kötü niyetli ipucu sadece revert'e yol açar (fuzz testli). İstemci ipucunu `hintFor` view'ı ile alıyor (büyük partilerde olaylardan hesaplanmalı). Not: ölçümde Anvil blokları 1 milyar gaza büyütüldü (EIP-1559 taban ücreti test hesabını boşaltıyordu), 36M sınır işlem başı gaz üst sınırıyla uygulandı.
- **D3 güvenlik (bitti):** `AccessControlDefaultAdminRules` (yönetici devri 2 adımlı, varsayılan 2 gün gecikme), rol iptali testi, Slither (2 yanlış alarm + 1 bilgilendirme, gerekçeli), `docs/threat_model.md` (T1-T13). **Meta veri bulgusu:** ton bazında %88,7'si (proje + miktar) ile tekil → miktar kimliği ele verebilir; 1.000 t standart lot ile tonların %95,8'i ortalama 61 eş lot arasına karışır (`scripts/linkability_stats.py`). Sözleşme yapıcısı artık `(adminDelay, admin)`.
- **D4 gerçek kayıtlar (bitti):** OffsetsDB'de iptal > ihraç olan 11 proje-vintage (235.932 t fazla). Oynatmada 1.100 iptalin 76'sı reddedildi (sözleşme sınırı aşan iptali bölmüyor, tümüyle reddediyor → reddedilen 476 bin t; muhafazakâr). Vakalardan biri değerlendirme projemiz VCS673 (2017, 13.052 t). `scripts/over_retirement_replay.py`, `data/derived/over_retirement.json`.
- **D1 AI (altyapı bitti, etiket bekleniyor):** `core/ai/checklist.py` (qs-v2, 18 evet/hayır sorusu), `data/eval/items.json` (48 parça, 177 soru, kod seçimli ≤2.500 karakter alıntı, 11 proje; VCS1742 CDM PDD'siyle birlikte), etiketleme aracı `data/eval/labeling_tool.html` (çevrimdışı, dışa aktarım → `data/eval/labels/`), model cevapları `data/eval/answers_{jev,llm}.json` (3 çalıştırma), metrikler `scripts/eval_metrics.py` → `docs/ai_evaluation.md`. Etiketsiz ilk sonuçlar: Jev 3 çalıştırmada %99,4 aynı cevap (LLM %96,0), gecikme 0,8 s vs 4,9 s, 1.000 değerlendirme 0,04 $ vs 0,79 $, iki model %90,4 uyuşuyor.
- **Standart lotlar (15 Ekim akşamı, bitti):** `registerBatch(..., lotSize)`; lot partisinde her iptal tam bir hizalı lot (son lot kısa olabilir), kontrol lot indeksiyle sabit sürede (`NotALot` hatası). Demo partileri 1.000 t (`DEFAULT_LOT_SIZE`, `data/batches.json`). `OnceSealed.retire_lots` alımı lotlara böler (her lota ayrı tuz), önce hepsini kontrol eder; makbuz `receipt-bundle-v1`. API `POST /api/retirements` artık `retirements` listesi + paket makbuz döndürür. **Dürüst ölçüm (`linkability_stats.py`):** lot + operatörün dönemsel karışık yayını ile tamamen açıkta kalan tonlar günlük %36,8 / haftalık %30,5 / aylık %21,4 / çeyreklik %14,5 (önceki "61 eş lot" zamanlamayı yok sayıyordu, geri çekildi). Dönemsel yayın operatör kuralı, sözleşme zorlayamaz.
- **Turnike yerel test (15 Ekim gece):** FP8 Windows'ta çalışmıyor: PyTorch'un Windows sürümü satır başına ölçekli FP8 çekirdeğini hiç derlemiyor (`RowwiseScaledMM.cu`: `!defined(_WIN32)`), kartla ilgisi yok (RTX 4060 tek ölçekli FP8'i Windows'ta da yapıyor). **WSL2'de çalışıyor** (test edildi: RTX 4060 Laptop sm_89, torch 2.11+cu128, Ubuntu 26.04; ortam `~/turnike-venv`, model Windows HF önbelleğinden `HF_HOME=/mnt/c/Users/90555/.cache/huggingface`). Etiketsiz: 3 çalıştırmada %100 aynı, ortanca 0,65 sn/parça (hızlandırıcı çekirdekler kurulu değil), 0 $. `answers_turnike_fp8.json` (ağırlık revizyonu kayıtlı). **Geçici AI etiketleri (Claude, `data/eval/silver/`, `docs/ai_evaluation_pilot.md`) gitignore'da**, insan etiketleri gelene kadar commit'lenmez; doğruluk diye sunulmaz. Pilot: Jev %87,9 / LLM %94,2 / Turnike %87,9 uyuşma; Jev ek katkıda zayıf (F1 0,43), Turnike D1'de zayıf ("kayıtlı değil" diyen metne "hayır" diyor: olumsuz ifade tuzağı), A1/P2/D3'te setin hiç pozitif örneği yok → set genişletilmeli. **BF16 (16 Ekim, Colab CLI, WSL'den):** `google-colab-cli` WSL'de kurulu (`~/.local/bin/colab`, giriş kullanıcıda, token `~/.config/colab-cli/token.json`); L4'te `turnike-jev-4b-merged`, aynı `karar.py` revizyonu (`e65dc054`), 0,31 birim. FP8 ile 177 sorunun 176'sı aynı cevap, ortalama olasılık farkı 0,014 → **D1 zaafı nicelemeden değil modelin kendisinden**. BF16 L4'te ortanca 0,32 sn/parça, yükleme 61 sn. `answers_turnike_bf16.json` commit'li. Colab'da kontrol için `pgrep -f` kullanma (exec'in kendi kabuğunu da yakalıyor).
- **11 rapor (15 Ekim gece, bitti):** 7 yeni rapor + ilk 4'ü güncel tabloyla yeniden (hepsi aynı `method_hash`, tablo `2026-10-15`). Metodoloji tablosu: VM0050 (koşullu onay), VM0010 v1.4 (`under_assessment`, yeni durum), AR-ACM0001 (`not_ccp_approved`), ACM0010 (`unknown`, karar bulunamadı). Manifest'e sürümler eklendi. 179/179 alıntı doğrulandı. Sepolia'da 11 rapor / 15 sürüm (`seed_sepolia.py` yayımlanan dosya değişince yeni sürüm demirler). Bulgular: genel puan 52-65 arasında sıkışık (ilke puanlarını öne çıkar); VCS985 Cordillera Azul 64 ama BeZero 2024'te baseline yüzünden not düşürdü → araç baseline şişmesini göremez.
- **README yeniden yazıldı (15 Ekim gece):** her rakam üreten dosyaya/betiğe bağlı ("What we measured" tablosu), "Trust assumptions and limitations" bölümü (operator tutarlı yalan söylerse denetçi yakalayamaz → KYC'ye güven; tek denetçi; gizlilik kalabalık ister; AI doğruluğu ölçülmedi; 11 projeden 4'ünün raporu var). Slither lot sürümünde yeniden çalıştı (1 yanlış alarm + 1 bilgilendirme, `threat_model.md`). `demo_e2e.py` `.env` yoksa geçici anahtarlarla çalışıyor (temiz klon testi yapıldı). Rakam değişirse README tablosunu ve `presentation_notes.md` Bölüm 5'i birlikte güncelle.
- **Ölçekte sorgu (15 Ekim, bitti, sözleşme değişmedi):** `Registry` serbest aralık partilerinde ipucunu ve `retirement_of`'u `CreditRetired` olaylarından kurulan sıralı dizinden (`_RangeIndex`, ikili arama, artımlı ve parçalı `eth_getLogs`) cevaplıyor; lot partilerinde sözleşmenin sabit süreli view'ı. `Registry(..., from_block=dağıtım bloğu)` gerekli (Sepolia'da taramayı kısaltır). Ölçüm `scripts/index_benchmark.py`: zincir view'ı iptal başına ~4.400 gaz (5.000'de 22M), dizin 5.000 iptali 1,5 sn'de kuruyor, sorgu ~1 ms. Web doğrulama sayfası da lot partilerinde `retirementOf`'u doğrudan, serbest partilerde olaylardan kullanmalı.
- **Sepolia (15 Ekim, bitti):** güncel `RetirementRegistry` (lot sürümü) @ **`0xBb88057576b92Ef27753A6b2a4Df83bE444F1308`**, Etherscan'de doğrulandı (`scripts/verify_etherscan.py`; forge'un kendi gönderimi bu makinede zaman aşımına uğruyor). İlk sürüm `0x7D17ebA028c6d4e77A28fC487C59F0f68aa1e675` `deployments/11155111.json` içinde `previous`. Lot sürümü deploy gazı **15,66M** (işlem başı ~16,8M sınırına yakın: sözleşmeye kod eklemeden önce `estimate_gas` ile kontrol et). Lot iptali Sepolia'da 1,02M (ilk) / 828k (sonraki). Aşağıdaki ilk-sürüm rakamları bilgi için: `scripts/seed_sepolia.py` 4 raporu demirledi, 4 parti kaydetti, 1 iptal (kurgusal Quillmere Freight, VCS1477 seri 1-1000) + denetçi onayı (6/6 kontrol) yaptı; işlemler `deployments/11155111-seed.json`. **Gerçek Sepolia gazı (yeni kurallar) Anvil'den çok farklı:** deploy 14,19M (Anvil 1,41M), `retire` 1,02M (Anvil ~211k), `registerQualityReport` 463k, `registerBatch` 242k, `attestRetirement` 33k. Sebep: yeni depolama/kod yazımı pahalandı. Blok gaz limiti 200M. İşlem başı gaz üst sınırı (EIP-7825, 2^24 ≈ 16,8M) muhtemelen geçerli → deploy sınıra yakın; sözleşme büyürse sığmayabilir. Gaz fiyatı ~0,001 gwei, toplam maliyet ihmal edilebilir. Herkese açık RPC yük dengeleyicili: okuma bazen bir blok geriden gelir → `_send` yeni bloğu bekliyor, rol kimlikleri yerelde hesaplanıyor, `deploy.py --attach` yarım kalan kurulumu tamamlar.
- **Turnike yolu (15 Ekim):** Önce eğitimsiz (zero-shot) deneme: Turnike'nin girdi biçimi (metin + kapalı sorular → seçenek olasılığı; `karar.py`) bizim evet/hayır sorularımızla birebir örtüşüyor. `scripts/export_reranker_inputs.py` → `data/eval/reranker_inputs.jsonl` (177 satır); arkadaş `data/eval/answers_turnike.json` (`p_yes`) döndürür, `eval_metrics.py` otomatik üçüncü model olarak ölçer. **Sıra: arkadaş önce etiketlemeyi bitirir, sonra modeli çalıştırır** (model çıktısını görmek etiketleri etkilemesin). Eğitim (Turnike-Carbon) ancak zero-shot zayıfsa ve zaman kalırsa; eğitim verisi 11 değerlendirme projesinden **üretilmez** (sızıntı), sentetik LLM etiketleri yalnızca eğitimde kullanılabilir.
- **API (bitti):** `api/app.py` + `api/server.py` (FastAPI). Herkese açık okuma uç noktaları jetonsuz; operator ve denetçi işlemleri `X-Role-Token` ister (`.env`: `OPERATOR_API_TOKEN`, `AUDITOR_API_TOKEN`, `scripts/gen_api_tokens.py`). Çalıştırma: `uvicorn api.server:app` (Anvil'de sözleşmeyi gerekirse kendisi dağıtır). Testler `tests/test_api.py`.
- **AI güvenilirlik planı (16 Ekim akşamı, kullanıcı onayı):** Eksik listesi çıkarıldı; sıra: 1 belge kaydı + tablo okuma, 4 deterministik veri kontrolleri (bitti), sonra 2 hibrit kanıt arama + kaçırma oranı, 3 iki modelli karar + insan inceleme kuyruğu, 5 dondurulmuş test seti + yayın kapısı, 7 prompt injection testleri. Kullanıcı ve arkadaşı 177 soruyu etiketliyor (beklenen ±5 puan güven aralığı; ilke/soru bazı sonuçlar kesin sunulmaz). Kullanıcı 11 projenin izleme/doğrulama/VVB raporlarını Verra'dan indirecek → `scripts/add_document.py`.
- **1 + 4 bitti (16 Ekim):** `core/ai/sources.py` (manifest rolleri: project_description/validation/monitoring/verification/supporting, `covers` birleşik belge için, `coverage()` eksikleri söyler; 11 projenin hepsinde sadece PD var). `pdf_extract`: `extract_tables` (PyMuPDF find_tables, `p<sayfa>-t<n>`), `profile`, `extract(..., tables=True)` (varsayılan kapalı; metin paragraf kimlikleri değişmiyor, eski raporlar geçerli). 11 PDF'in hepsinde metin katmanı var (OCR gerekmedi; tesseract kurulu değil). `core/checks/` (AI yok): `estimates.py` yıllık net azaltım tablosu ayrıştırıcı (birleşik başlık hücreleri sırayla eşleşir, çok satırlı tarih etiketleri, kısmi yıllar, 'Total number of crediting years' ve kümülatif sütunlar elenir, şablon tablo reddedilir), `registry_data.py` (OffsetsDB vintage ihraç/iptal, protokol, IDF ağırlıklı isim benzerliği), `run.py` 5 kontrol: belge kapsamı, ihraç vs belgenin kendi rakamları (dönem toplamı, >1,2 flag, <0,5 info, tek yıl aşımı info), iptal ≤ ihraç, metodoloji eşleşmesi, benzer kayıt (aynı vintage'da iki yerde ihraç → flag). `scripts/run_checks.py` → `checks/<id>.json` + `docs/data_checks.md`; web proje sayfasında "Data checks" bölümü. Bulgular: VCS985 2009-2018 ihraç belgenin 1,72 katı (BeZero bulgusuyla uyumlu ipucu), VCS673 2017 iptal > ihraç, VCS4150 ↔ VCS2749 (DelAgua) 2021'de ikisi de ihraç, VCS138 ACR113 ile aynı isim (ortak vintage yok). 69 Python testi.
- **AI doğruluğu ölçüldü (19 Ekim):** Arkadaşın etiketleyip etiketlemeyeceği belirsiz olduğu için kullanıcının kararıyla ikinci etiketçi Claude (`data/eval/labels/labels_claude.json`, `kind: ai`; eski silver etiketler, model cevaplarını görmeden yapılmıştı). Kullanıcı 177/177 (`labels_salih.json`). κ 0,90 (insan-AI, "unclear" hariç 173 soru; unclear dahil %93,2 / 0,85). 12 ayrışmayı kullanıcı karara bağladı (7 kendi, 5 Claude'un okuması), 7 kılavuz kuralı: `data/eval/adjudication.json`; altın etiket `data/eval/gold.json` (58 evet / 119 hayır). `eval_metrics.py` artık Wilson %95 aralığı, tam McNemar ikili karşılaştırma, ilke bazında doğruluk veriyor. Sonuç: LLM 0,94 (0,90-0,97), Jev 0,88, Turnike 0,86 (BF16/FP8 aynı); LLM > Jev p 0,013, LLM > Turnike p 0,001, Jev ≈ Turnike. Jev Brier 0,084 (en iyi kalibre). Zayıf: A1, S4, Turnike D1; ek katkıda 44 sorunun 4'ü pozitif, P2/D3'te pozitif yok. **Sunarken: "bir ekip üyesi + AI etiketçi", "iki insan" deme.** Bu küme artık model karşılaştırması için kullanıldı; üzerinde ayar yapılan her değişiklik yeni, ayrı bir test kümesiyle ölçülmeli. Arkadaş etiketlerse dosyası `labels/`'a eklenir, insan-insan uyumu ayrıca raporlanır.
- **Web (16 Ekim, çalışıyor):** Claude Design çıktısı `web/src`'ye taşındı (Next 16.4.1, cacheComponents açık). Veri: `scripts/export_web_data.py` → `web/src/data/site.json` (11 rapor + rapor hash'i, metodoloji tablosu, 64 parti, demo alıcılar, Sepolia kaydı; CI eskiyse kırılır). Proje sayfaları statik; rapor hash'i tarayıcıda `latestReport` ile karşılaştırılıyor. `/verify` Sepolia'yı tarayıcıdan okuyor (viem, `src/lib/chain.ts`: taahhüt + LEI kontrolü Python'la birebir; gerçek paket makbuz geçti, sahte tuz reddedildi). `/retire` ve `/auditor` FastAPI'ye `src/app/api/os/[...path]/route.ts` vekili ile gidiyor (rol jetonu sunucuda, `../.env`'den; sadece yerel demo). Arayüzden Sepolia'da **retirement #3** yapıldı (VCS1477 2001-3000, kurgusal Vantorra Cement, 827.868 gaz), sonra kullanıcı onayladı; kullanıcının denemesinden #4-#5 (VCS138 2022/002) denetim bekliyor. Tasarımdaki yanlış/örnek ifadeler düzeltildi ("JEV AI (team model)", tarayıcıda şifreleme iddiası, sahte denetim kontrolleri, %17 kaynağı). Proje sayfası parametresi ve `/verify?q=` sorgusu `<Suspense>` içinde okunuyor (Next dev "URL data outside of Suspense" uyarısı giderildi). Not: "panel boş kalıyor" gözlemi hata değildi; Claude'un gizli tarayıcı panelinde `requestAnimationFrame` çalışmadığı için React akış parçası yerleşmiyordu, görünür tarayıcıda sorun yok. Demo yine de `npm run build && npm start` ile. `.claude/launch.json` (api-sepolia, web) yerel, commit'lenmedi. `web/AGENTS.md`: Next belgeleri `web/node_modules/next/dist/docs/`.
- **Demo alıcılar:** `data/demo_buyers.json` (açıkça uydurma isimler + geçerli kontrol haneli LEI).
- **Sepolia için hazır:** `scripts/fund_roles.py` (kullanıcı `--send` ile çalıştırır), sonra `scripts/deploy.py --network sepolia`.
- **Sepolia gaz kuralları değişti (15 Ekim):** boş (yeni) hesaba ETH göndermek artık ~207k gaz istiyor (hesap oluşturma ücreti); betikteki sabit 21.000 gaz yüzünden ilk 6 fonlama işlemi "out of gas" ile düştü (kayıp ~0,00013 ETH). Betik artık `estimate_gas` kullanıyor. **Asla sabit gaz yazma.** D2 gaz rakamları Anvil'in eski kurallarıyla ölçüldü; Sepolia'da yeni depolama yazımı daha pahalı olabilir → deploy sonrası gerçek `retire` gazını ölç, README/sunumda ikisini ayrı göster (sabit-vs-doğrusal sonucu değişmez).
- Ortam notu: Slither proje ortamına kurulunca web3'ü 7.16'ya düşürdü; Slither ayrı ortamda çalıştırılmalı.

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

- **Kendi hesabımız (14 Ekim, `scripts/anonymity_stats.py` → `docs/anonymity_stats.md`, grafik `docs/figures/anonymity_trend.png`):** OffsetsDB 2026-06-01 anlık görüntüsü, 495 bin iptal, 1,59 milyar ton.
  - **Açıkça "gizli" işaretlenen iptallerin ton payı: ≤2018'de %0,4 → 2023-26'da %17,2** ("not disclosed", "not public", "anonymous", "private offset"; muhafazakâr alt sınır). Ana slayt rakamı bu.
  - **2023-26'da tonların %52,9-55,5'inde alıcı belirlenemiyor** (aralık: isim deseni tanınmayan serbest notlar).
  - Sınıflar (`core/data/anonymity.py`): named, named_in_note, intermediary_only, explicitly_undisclosed, generic_note, no_information. `retirement_account` sayılmaz (aracı hesap sahibi). "Private Limited" gibi şirket adları anonim sayılmaz (testli).
  - Uyarı: "no_information" kısmen kayıt sistemlerinin yayımlama pratiğini yansıtır (ACR/CAR'da eski yıllarda çok yüksek); "alıcının tercihi" diye sunma, açık "gizli" işaretini öne çıkar.
- **Eski ana rakam notu (bilgi için):** OffsetsDB'de iptal kayıtlarının ne kadarında "kimin adına iptal edildiği" bilgisi yok. CarbonPlan'in kendi yazısı: 1,34 milyar iptalin yalnızca 0,67 milyarında bu bilgi var (~%50). https://carbonplan.org/blog/offsets-db-additions
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
8. **AI'ı olduğundan farklı gösterme.** Jev 1.13 TypeSafe'in modelidir, bizim değil. Turnike 4B ekip arkadaşının kendi modelidir (Qwen3.5-4B + LoRA; model kartı: herhangi bir ticari karar API'sinden distile edilmedi; eğitim verisi kamu TR/EN veri setleri, LLM ile etiketlenmiş kamu metinleri ve sentetik veri); kullanılırsa öyle anılır. Her raporda hangi modellerin kullanıldığı yazar.
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
3. **Karar modeli — kanıt yeterliliği:** Değiştirilebilir arayüz arkasında (`DecisionModel`). Şimdilik **TypeSafe Jev 1.13** (`typesafe/jev-1.13`, OpenRouter `POST /api/alpha/decisions`; chat endpoint'i ile çalışmaz). İleride **Turnike 4B / Turnike-Carbon** (ekip arkadaşının modeli, Qwen3.5-4B + LoRA, yerel çalışabilir) aynı soru şemasıyla takılır. Hangisinin kullanılacağına **etiketli test kümesindeki sonuçlara göre** karar verilir.
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
docs/anonymity_stats.md  anonimlik analizi (scripts/anonymity_stats.py üretir)
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
| 1 | 14 Ekim ✓ | `RetirementRegistry` + Foundry testleri | Bitti |
| 2 | 14 Ekim ✓ | Gizlilik modülü (`core/privacy`): kurgusal LEI üretimi (mod-97), taahhüt, SealedBox kasası (SQLite), makbuz; `tests/vectors.json` | Python ve Foundry aynı vektörlerle aynı hash'i üretir |
| 3 | 14 Ekim ✓ | Zincir istemcisi (`core/chain`, web3.py) + deploy betiği; Anvil'de uçtan uca senaryo | Parti → rapor → iptal → örtüşme reddi → denetçi onayı → `verifyClaim`, tek komutla |
| 4 | ~~17 Ekim~~ **14 Ekim ✓** | Simüle seri verisi: `scripts/build_batches.py` → `data/batches.json` (64 parti, gerçek vintage/tarih/miktar, seriler 1..miktar) | Bitti |
| 5 | ~~18 Ekim~~ **14 Ekim ✓** | Anonimlik analizi (notebook yerine betik + rapor + grafik) | Bitti |
| 6 | 15-17 Ekim | **Next.js + FastAPI** (Streamlit iptal): proje kalitesi, iptal, herkese açık doğrulama (tarayıcıdan zincir), denetçi ekranları | Demo senaryosu arayüzden baştan sona oynar |
| 6b | 15-21 Ekim | **Derinlik D1-D4** (`docs/evaluation_plan.md` takvimi) | Ölçümler README'de |
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
