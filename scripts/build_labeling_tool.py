"""D1: build a self-contained labeling page (data/eval/labeling_tool.html) from data/eval/items.json.

    python scripts/build_labeling_tool.py

Open the HTML file in a browser (works offline). Each annotator enters their name, answers every
question Yes / No / Unclear for the excerpt shown, and exports a JSON file at the end. Answers are
autosaved in the browser. Annotators must work independently.
"""

import json
from dataclasses import asdict

from core.ai.checklist import QUESTIONS, QUESTION_SET_VERSION
from core.config import PROJECT_ROOT

TEMPLATE = r"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>OnceSealed etiketleme</title>
<style>
  :root { --bg:#f7f7f5; --card:#ffffff; --ink:#1a1a19; --ink2:#55534e; --muted:#8a8780; --line:#e2e0d8;
          --accent:#2a78d6; --yes:#1b7f4b; --no:#b3372f; --unc:#9a6b00; }
  @media (prefers-color-scheme: dark) { :root { --bg:#141413; --card:#1e1e1c; --ink:#f2f1ec; --ink2:#c3c2b7;
          --muted:#8f8d86; --line:#33322f; --accent:#5a9be8; --yes:#3fb27a; --no:#e0645b; --unc:#d9a63a; } }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--ink); font:15px/1.55 system-ui, -apple-system, "Segoe UI", sans-serif; }
  header { position:sticky; top:0; z-index:2; background:var(--card); border-bottom:1px solid var(--line);
           padding:10px 16px; display:flex; gap:12px; align-items:center; flex-wrap:wrap; }
  header b { font-size:16px; }
  .bar { flex:1; min-width:160px; height:8px; background:var(--line); border-radius:4px; overflow:hidden; }
  .bar > div { height:100%; background:var(--accent); width:0; }
  button, select { font:inherit; padding:6px 12px; border-radius:6px; border:1px solid var(--line); background:var(--card); color:var(--ink); cursor:pointer; }
  button.primary { background:var(--accent); color:#fff; border-color:var(--accent); }
  main { max-width:920px; margin:0 auto; padding:16px; display:flex; flex-direction:column; gap:16px; }
  .card { background:var(--card); border:1px solid var(--line); border-radius:10px; padding:16px; }
  .meta { color:var(--ink2); font-size:13px; margin-bottom:8px; }
  .para { margin:0 0 12px; white-space:pre-line; overflow-wrap:anywhere; }
  .pid { display:inline-block; font:12px ui-monospace, Consolas, monospace; color:var(--accent); margin-right:6px; user-select:all; }
  .q { border-top:1px solid var(--line); padding:12px 0; }
  .q:first-of-type { border-top:none; }
  .qid { font-weight:700; margin-right:6px; }
  .tr { color:var(--ink2); font-size:14px; margin:4px 0; }
  .hint { font-size:13px; color:var(--muted); margin:4px 0 8px; }
  .hint b { color:var(--ink2); }
  .opts { display:flex; gap:6px; flex-wrap:wrap; align-items:center; }
  .opts label { border:1px solid var(--line); border-radius:6px; padding:4px 10px; cursor:pointer; }
  .opts input { margin-right:4px; }
  .opts input[value=yes]:checked + span { color:var(--yes); font-weight:700; }
  .opts input[value=no]:checked + span { color:var(--no); font-weight:700; }
  .opts input[value=unclear]:checked + span { color:var(--unc); font-weight:700; }
  .opts input[type=text] { font:13px ui-monospace, Consolas, monospace; padding:4px 6px; border:1px solid var(--line); border-radius:6px; background:var(--card); color:var(--ink); width:190px; }
  .nav { display:flex; justify-content:space-between; gap:8px; margin-top:12px; }
  .intro { max-width:760px; margin:40px auto; }
  .intro li { margin-bottom:6px; }
  .done { color:var(--yes); }
</style>
</head>
<body>
<div id="app"></div>
<script id="data" type="application/json">__DATA__</script>
<script>
const DATA = JSON.parse(document.getElementById('data').textContent);
const Q = Object.fromEntries(DATA.questions.map(q => [q.id, q]));
const items = DATA.items;
let annotator = '', idx = 0, answers = {};
const key = () => 'oncesealed-labels-' + annotator;
function load() { try { const s = JSON.parse(localStorage.getItem(key()) || '{}'); answers = s.answers || {}; idx = s.idx || 0; } catch (e) { answers = {}; } }
function save() { try { localStorage.setItem(key(), JSON.stringify({answers, idx})); } catch (e) {} }
const total = DATA.items.reduce((n, it) => n + it.questions.length, 0);
const answered = () => Object.values(answers).filter(a => a && a.answer).length;
const esc = s => s.replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
// PDF text keeps the PDF's line breaks, so table cells arrive one word per line and sentences break mid-way.
// Join wrapped lines for reading; keep blank lines, headings, bullets and numbered items on their own line.
// Only whitespace changes; the words, including any hyphen at a line end, are unchanged.
const BULLET = /^[•▪●·–-]$/;
const NEW_ITEM = /^([•▪●·–]|-\s|\(?[a-z0-9ivx]{1,4}[.)]\s)/i;
const ENDS_SENTENCE = /[.:;!?)]$/;
function reflow(text) {
  return text.replace(/\r/g, '').split(/\n\s*\n/).map(block => {
    let out = '', prev = '', prevStartsLine = true;
    for (const line of block.split('\n').map(l => l.trim()).filter(Boolean)) {
      // A short line that starts a line, starts with a capital and has no closing punctuation, followed by a
      // capitalised line, is a heading ("Baseline Scenario" / "In the absence of ...").
      const heading = prevStartsLine && prev.length < 70 && /^[A-Z0-9]/.test(prev) && !ENDS_SENTENCE.test(prev)
                      && /^[A-Z]/.test(line);
      let startsLine = false;
      if (!out) { out = line; startsLine = true; }
      else if (BULLET.test(out.split('\n').pop())) out += ' ' + line;  // a bullet alone on its line: join its text
      else if (NEW_ITEM.test(line) || heading) { out += '\n' + line; startsLine = true; }
      else if (/[a-z]-$/.test(out) && /^[a-z]/.test(line)) out += line;  // keep the hyphen: it may be part of the word
      else out += ' ' + line;
      prevStartsLine = startsLine || ENDS_SENTENCE.test(prev);
      prev = line;
    }
    return out;
  }).filter(Boolean).join('\n\n');
}

function intro() {
  document.getElementById('app').innerHTML = `
  <div class="intro card">
    <h2>OnceSealed — kanıt etiketleme</h2>
    <p>Her ekranda bir karbon projesi belgesinden <b>kodun seçtiği bir bölüm</b> ve o bölüm hakkında evet/hayır soruları var.
       Sorular kanıtın <b>bu metinde olup olmadığını</b> soruyor; projenin iyi ya da kötü olduğunu değil.</p>
    <ol>
      <li><b>Sadece gösterilen metne bakın.</b> Belgenin başka yerinde olabileceğini tahmin etmeyin.</li>
      <li>Her soruya <b>Evet / Hayır / Belirsiz</b> deyin. "Evet" dediyseniz kanıtın geçtiği paragraf kimliğini
          (mavi kod, ör. <code>p32-03</code>, tıklayınca seçilir) yazın.</li>
      <li>Her sorunun altında "evet sayılır / hayır sayılır" örnekleri var.</li>
      <li><b>Diğer etiketçiye bakmadan, konuşmadan</b> çalışın. Uyuşmazlıkları en sonda birlikte konuşacaksınız.</li>
      <li>Cevaplar bu tarayıcıda otomatik kaydedilir. Bitince <b>Dışa aktar</b> ile dosyayı indirip gönderin.</li>
    </ol>
    <p>${items.length} bölüm, ${total} soru. Soru seti: ${DATA.question_set_version}.</p>
    <p><label>Adınız: <input id="name" style="font:inherit;padding:6px;border:1px solid var(--line);border-radius:6px"></label>
       <button class="primary" id="start">Başla</button></p>
  </div>`;
  document.getElementById('start').onclick = () => {
    const n = document.getElementById('name').value.trim();
    if (!n) return alert('Lütfen adınızı yazın');
    annotator = n; load(); render();
  };
}

function render() {
  const it = items[idx];
  const done = answered();
  const qs = it.questions.map(qid => {
    const q = Q[qid], a = answers[it.item_id + '|' + qid] || {};
    const opt = (v, t) => `<label><input type="radio" name="${qid}" value="${v}" ${a.answer===v?'checked':''}><span>${t}</span></label>`;
    return `<div class="q"><div><span class="qid">${qid}</span>${esc(q.text)}</div>
      <div class="tr">${esc(q.tr)}</div>
      <div class="hint"><b>Evet sayılır:</b> ${esc(q.yes_if)}<br><b>Hayır sayılır:</b> ${esc(q.no_if)}</div>
      <div class="opts">${opt('yes','Evet')}${opt('no','Hayır')}${opt('unclear','Belirsiz')}
        <input type="text" data-q="${qid}" placeholder="paragraf (ör. p32-03)" value="${esc(a.evidence||'')}"></div></div>`;
  }).join('');
  const paras = it.paragraphs.map(p => `<p class="para"><span class="pid">${p.id}</span>${esc(reflow(p.text))}</p>`).join('')
              || '<p class="meta">Bu ilke için belgede anahtar kelimeyle eşleşen paragraf bulunamadı. Tüm sorulara Hayır deyin.</p>';
  document.getElementById('app').innerHTML = `
  <header><b>${esc(annotator)}</b><span>${idx+1} / ${items.length}</span>
    <div class="bar"><div style="width:${(100*done/total).toFixed(1)}%"></div></div>
    <span>${done}/${total} soru</span>
    <select id="jump">${items.map((x,i)=>`<option value="${i}" ${i===idx?'selected':''}>${x.item_id}${x.questions.every(q=>(answers[x.item_id+'|'+q]||{}).answer)?' ✓':''}</option>`).join('')}</select>
    <button id="export" class="primary">Dışa aktar</button></header>
  <main>
    <section class="card"><div class="meta">${esc(it.project_id)} · ${esc(it.project_name)} · ${esc(it.category)}<br>
      İlke: <b>${esc(it.principle)}</b> · ${it.excerpt_chars.toLocaleString()} karakter</div>${paras}</section>
    <section class="card">${qs}
      <div class="nav"><button id="prev" ${idx===0?'disabled':''}>← Önceki</button>
      <button id="next" class="primary">${idx===items.length-1?'Bitti':'Sonraki →'}</button></div></section>
  </main>`;
  document.querySelectorAll('input[type=radio]').forEach(el => el.onchange = () => {
    const k = it.item_id + '|' + el.name; answers[k] = {...(answers[k]||{}), answer: el.value}; save(); render();
  });
  document.querySelectorAll('input[type=text]').forEach(el => el.oninput = () => {
    const k = it.item_id + '|' + el.dataset.q; answers[k] = {...(answers[k]||{}), evidence: el.value.trim()}; save();
  });
  document.getElementById('prev').onclick = () => { idx--; save(); render(); scrollTo(0,0); };
  document.getElementById('next').onclick = () => {
    const missing = it.questions.filter(q => !(answers[it.item_id+'|'+q]||{}).answer);
    if (missing.length && !confirm('Cevaplanmamış soru var: ' + missing.join(', ') + '. Yine de geçilsin mi?')) return;
    if (idx < items.length - 1) { idx++; save(); render(); scrollTo(0,0); } else exportFile();
  };
  document.getElementById('jump').onchange = e => { idx = +e.target.value; save(); render(); };
  document.getElementById('export').onclick = exportFile;
}

function exportFile() {
  const rows = [];
  items.forEach(it => it.questions.forEach(qid => {
    const a = answers[it.item_id + '|' + qid] || {};
    rows.push({item_id: it.item_id, project_id: it.project_id, principle: it.principle, question_id: qid,
               answer: a.answer || null, evidence: a.evidence || ''});
  }));
  const blob = new Blob([JSON.stringify({annotator, question_set_version: DATA.question_set_version,
    exported_at: new Date().toISOString(), answered: answered(), total, labels: rows}, null, 1)], {type: 'application/json'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'labels_' + annotator.replace(/[^a-z0-9]+/gi, '_') + '.json';
  a.click();
}
intro();
</script>
</body>
</html>
"""


def main() -> None:
    items = json.loads((PROJECT_ROOT / "data" / "eval" / "items.json").read_text(encoding="utf-8"))
    data = {"question_set_version": QUESTION_SET_VERSION, "questions": [asdict(q) for q in QUESTIONS],
            "items": items["items"]}
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")  # keep the JSON inside its <script>
    out = PROJECT_ROOT / "data" / "eval" / "labeling_tool.html"
    out.write_text(TEMPLATE.replace("__DATA__", payload), encoding="utf-8")
    print(f"wrote {out.relative_to(PROJECT_ROOT)} ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
