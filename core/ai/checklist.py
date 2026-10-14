"""Evidence checklist (question set qs-v2): yes/no questions about what a text excerpt contains.

Used for the AI evaluation (D1). Each question asks whether a specific kind of evidence is
*present* in the given excerpt - something a careful non-expert can answer by reading - so human
labels are reliable and precision / recall / F1 can be computed per question. The questions are
derived from the ICVCM Assessment Framework and the CCQI sub-criteria.

`text` is what the models see (English); `tr`, `yes_if` and `no_if` guide the human annotators.
"""

from dataclasses import dataclass

QUESTION_SET_VERSION = "qs-v2-checklist"


@dataclass(frozen=True)
class Question:
    id: str
    principle: str
    text: str
    tr: str
    yes_if: str
    no_if: str


QUESTIONS: tuple[Question, ...] = (
    # --- additionality ---
    Question("A1", "additionality",
             "Does the text report a quantified financial analysis: at least one numeric financial indicator "
             "(such as IRR or NPV) together with a benchmark or threshold value it is compared against?",
             "Metinde sayısal bir finansal analiz var mı: en az bir finansal gösterge değeri (IRR, NPV gibi) VE "
             "karşılaştırıldığı bir eşik/benchmark değeri?",
             "İki sayı da metinde: ör. 'equity IRR 9.1% ... benchmark 14.5%'.",
             "Sadece 'IRR benchmark'ın altında' deniyor ama sayılar yok; ya da sadece biri var."),
    Question("A2", "additionality",
             "Does the text discuss common practice, i.e. whether similar activities are already widespread "
             "in the region or sector?",
             "Metinde 'common practice' analizi var mı: benzer projelerin bölgede/sektörde ne kadar yaygın olduğu?",
             "Benzer projelerin sayısı/payı veya 'yaygın değil' sonucuna varan bir analiz anlatılıyor.",
             "Konu hiç geçmiyor ya da sadece bölüm başlığı var."),
    Question("A3", "additionality",
             "Does the text state that the project activity is not required by any law or regulation "
             "(regulatory surplus)?",
             "Metinde projenin yasal bir zorunluluk olmadığı (regulatory surplus) belirtiliyor mu?",
             "'No law requires...', 'not mandated by regulation' gibi açık bir ifade.",
             "Sadece yasalara uyulduğu söyleniyor (bu farklı bir şey)."),
    Question("A4", "additionality",
             "Does the text state that carbon credit revenue was considered before or at the start of the project "
             "(prior consideration), for example with a date or a document?",
             "Metinde karbon gelirinin proje kararından önce/başında düşünüldüğü (prior consideration) belirtiliyor mu?",
             "Bir tarih, yönetim kurulu kararı veya belgeyle karbon gelirinin baştan hesaba katıldığı söyleniyor.",
             "Bu konu geçmiyor."),
    # --- permanence ---
    Question("P1", "permanence",
             "Does the text assess the risk that stored carbon is released (reversal or non-permanence risk), "
             "for example with a risk tool, a rating or a score?",
             "Metinde depolanan karbonun geri salınma (reversal / non-permanence) riski değerlendirilmiş mi?",
             "Risk aracı, risk puanı/derecesi veya risk faktörlerinin değerlendirmesi var.",
             "Sadece 'kalıcıdır' iddiası var, değerlendirme yok."),
    Question("P2", "permanence",
             "Does the text give a specific buffer contribution (a percentage or a number of credits set aside)?",
             "Metinde tampon havuza (buffer) ayrılan pay sayısal olarak veriliyor mu (yüzde veya kredi sayısı)?",
             "Ör. 'buffer withholding of 12%' ya da ayrılan kredi sayısı.",
             "Buffer'dan söz ediliyor ama sayı yok."),
    Question("P3", "permanence",
             "Does the text describe concrete measures to monitor or prevent reversals "
             "(e.g. fire, illegal logging, land conversion)?",
             "Metinde geri salınmayı (yangın, kaçak kesim, arazi dönüşümü) izlemek/önlemek için somut önlemler var mı?",
             "Devriye, yangın izleme, uydu takibi gibi somut faaliyetler anlatılıyor.",
             "Sadece genel niyet beyanı var."),
    # --- robust quantification ---
    Question("Q1", "robust_quantification",
             "Does the text show how baseline emissions are calculated, with an equation, parameter values "
             "or a numeric result?",
             "Metinde referans (baseline) emisyonlarının nasıl hesaplandığı denklem, parametre değeri veya "
             "sayısal sonuçla gösteriliyor mu?",
             "Bir formül, emisyon faktörü değeri veya hesaplanmış baseline sayısı var.",
             "Sadece 'baseline methodology'ye göre hesaplandı' deniyor."),
    Question("Q2", "robust_quantification",
             "Does the text address leakage (emissions shifted outside the project boundary), either by "
             "quantifying it or by justifying why it is zero?",
             "Metinde sızıntı (leakage) ele alınmış mı: sayısallaştırılmış ya da neden sıfır olduğu gerekçelendirilmiş?",
             "Leakage değeri veya 'leakage is not applicable because ...' gibi gerekçe.",
             "Leakage hiç geçmiyor."),
    Question("Q3", "robust_quantification",
             "Does the text address uncertainty or the use of conservative assumptions in the emission "
             "reduction estimate?",
             "Metinde belirsizlik veya muhafazakâr (conservative) varsayımlar ele alınıyor mu?",
             "Belirsizlik oranı, indirim faktörü veya bilinçli muhafazakâr seçim anlatılıyor.",
             "Konu geçmiyor."),
    Question("Q4", "robust_quantification",
             "Does the text describe a monitoring plan that names the parameters to be measured and how often "
             "or by what method?",
             "Metinde ölçülecek parametreleri ve ölçüm sıklığını/yöntemini belirten bir izleme planı var mı?",
             "Parametre tablosu, ölçüm cihazı, kalibrasyon veya sıklık bilgisi.",
             "Sadece 'izleme yapılacak' deniyor."),
    # --- no double counting ---
    Question("D1", "no_double_counting",
             "Does the text state whether the project is registered, or issues credits, under another GHG "
             "program (e.g. CDM, Gold Standard)?",
             "Metinde projenin başka bir karbon programında (CDM, Gold Standard vb.) kayıtlı olup olmadığı belirtiliyor mu?",
             "'Not registered under any other GHG program' veya 'also registered under CDM' gibi açık ifade.",
             "Konu geçmiyor."),
    Question("D2", "no_double_counting",
             "Does the text address other environmental credits or certificates (e.g. renewable energy "
             "certificates, I-RECs) or participation in an emissions trading scheme?",
             "Metinde başka çevresel sertifikalar (REC, I-REC vb.) veya emisyon ticaret sistemleri ele alınıyor mu?",
             "Bu sertifikalar alınmadığı/alındığı ya da ETS'ye katılmadığı açıkça söyleniyor.",
             "Konu geçmiyor."),
    Question("D3", "no_double_counting",
             "Does the text address the host country's national accounting or registry, or a corresponding "
             "adjustment?",
             "Metinde ev sahibi ülkenin ulusal muhasebesi/kayıt sistemi veya karşılıklı düzeltme (corresponding "
             "adjustment) ele alınıyor mu?",
             "Ulusal kayıt sistemi, NDC muhasebesi veya corresponding adjustment'tan söz ediliyor.",
             "Konu geçmiyor."),
    # --- safeguards ---
    Question("S1", "safeguards",
             "Does the text describe a stakeholder consultation with specifics such as dates, places, "
             "participants or comments received?",
             "Metinde paydaş görüşmesi tarih, yer, katılımcı veya alınan yorumlar gibi ayrıntılarla anlatılıyor mu?",
             "En az bir somut ayrıntı (tarih, yer, katılımcı sayısı, gelen yorum).",
             "Sadece 'paydaşlarla görüşüldü' deniyor."),
    Question("S2", "safeguards",
             "Does the text describe a grievance or complaint mechanism through which affected people can "
             "raise concerns?",
             "Metinde etkilenen kişilerin şikâyet iletebileceği bir mekanizma tanımlanıyor mu?",
             "Şikâyet kanalı (telefon, kutu, e-posta, süreç) anlatılıyor.",
             "Konu geçmiyor."),
    Question("S3", "safeguards",
             "Does the text report an environmental impact assessment or an analysis of the project's "
             "environmental risks?",
             "Metinde çevresel etki değerlendirmesi veya projenin çevresel risklerinin analizi var mı?",
             "ÇED yapıldığı/gerekmediği gerekçesiyle veya çevresel risk analizi anlatılıyor.",
             "Sadece 'çevreye faydalı' deniyor."),
    Question("S4", "safeguards",
             "Does the text address the rights of local communities or indigenous peoples, such as free, prior "
             "and informed consent (FPIC) or benefit sharing?",
             "Metinde yerel halkın veya yerli halkların hakları (FPIC, fayda paylaşımı vb.) ele alınıyor mu?",
             "FPIC, fayda paylaşımı, arazi hakları gibi somut bir konu ele alınıyor.",
             "Konu geçmiyor."),
)

BY_PRINCIPLE: dict[str, list[Question]] = {}
for _q in QUESTIONS:
    BY_PRINCIPLE.setdefault(_q.principle, []).append(_q)
