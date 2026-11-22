// Simulados NCA-GENL: student side. Hash routes: #/ · #/exame/<attempt> · #/resultado/<attempt>
const view = document.getElementById("view");
const timerEl = document.getElementById("timer");
const whoEl = document.getElementById("who");
const LETTERS = "ABCDE";
const GOAL = 80;  // class readiness gate; NVIDIA does not publish the pass mark
let tick = null;

const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const store = {
  get(k, d) { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* private mode */ } },
  del(k) { try { localStorage.removeItem(k); } catch { /* private mode */ } },
};

async function api(path, opts = {}) {
  const res = await fetch(path, { headers: { "Content-Type": "application/json" }, ...opts });
  if (!res.ok) {
    let msg = res.statusText;
    try { msg = (await res.json()).detail || msg; } catch { /* not json */ }
    throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
  }
  return res.json();
}

function setWho() {
  const name = store.get("sim_name", "");
  whoEl.textContent = name ? `Olá, ${name}` : "";
}

function stopTimer() { clearInterval(tick); tick = null; timerEl.hidden = true; }

// ---------- home ----------

async function home() {
  stopTimer();
  setWho();
  const { exams, bank } = await api("/api/exams");
  const name = store.get("sim_name", "");
  const history = store.get("sim_history", []);
  const best = {};
  for (const h of history) if (h.pct != null) best[h.exam_id] = Math.max(best[h.exam_id] ?? 0, h.pct);
  const card = (e) => `
    <button class="card exam-card" data-exam="${esc(e.id)}">
      <span class="title">${esc(e.title)}</span>
      <span class="meta">${e.n} perguntas · ${e.minutes} min${e.kind === "drill" ? ` · ${e.pool} no banco` : ""}</span>
      ${best[e.id] != null ? `<span class="done">Melhor: ${best[e.id]}%</span>` : ""}
    </button>`;
  const mocks = exams.filter((e) => e.kind === "mock");
  const others = exams.filter((e) => e.kind === "random");
  const drills = exams.filter((e) => e.kind === "drill");
  view.innerHTML = `
    <h1>Simulados NCA-GENL</h1>
    <p class="muted">NVIDIA-Certified Associate: Generative AI LLMs. O exame real tem 50 perguntas em 60 minutos, em inglês,
      com o resultado só como aprovado ou reprovado. A NVIDIA não publica a nota mínima. A meta da turma é
      <b>${GOAL}% em dois simulados seguidos</b> antes de marcares o exame.</p>
    <div class="card" style="margin:18px 0">
      <label for="name"><b>O teu nome</b></label>
      <div class="row" style="margin-top:8px">
        <input type="text" id="name" maxlength="40" placeholder="Nome e apelido" value="${esc(name)}" autocomplete="name">
      </div>
      <p class="small muted" style="margin:8px 0 0">Usa sempre o mesmo nome, para o formador ver a tua evolução.</p>
    </div>
    <h2>Simulados completos</h2>
    <p class="small muted">Cada simulado tem perguntas diferentes, distribuídas como no exame:
      ${bank.domains.map((d) => `${esc(d.name)} ${Math.round(d.weight * 100)}%`).join(" · ")}.</p>
    <div class="grid">${mocks.map(card).join("")}${others.map(card).join("")}</div>
    <h2>Treino por domínio</h2>
    <p class="small muted">20 perguntas ao acaso de um só domínio, para atacar o teu ponto fraco.</p>
    <div class="grid">${drills.map(card).join("")}</div>
    ${history.length ? `<h2>As minhas tentativas (neste browser)</h2>
      <table><tr><th>Data</th><th>Exame</th><th class="num">Nota</th><th></th></tr>
      ${history.slice().reverse().map((h) => `<tr><td>${new Date(h.at).toLocaleString("pt-PT")}</td><td>${esc(h.title)}</td>
        <td class="num">${h.pct != null ? h.pct + "%" : "em curso"}</td>
        <td><a href="#/${h.pct != null ? "resultado" : "exame"}/${h.id}">${h.pct != null ? "rever" : "continuar"}</a></td></tr>`).join("")}
      </table>` : ""}
    <p class="small muted" style="margin-top:28px">Banco com ${bank.total} perguntas originais, cada uma com explicação e fonte oficial.
      Não são perguntas do exame real: ninguém as pode publicar.</p>`;
  const input = document.getElementById("name");
  input.addEventListener("input", () => { store.set("sim_name", input.value.trim()); setWho(); });
  view.querySelectorAll("[data-exam]").forEach((b) => b.addEventListener("click", () => startExam(b.dataset.exam)));
}

async function startExam(examId) {
  const name = (store.get("sim_name", "") || "").trim();
  if (name.length < 2) {
    alert("Escreve o teu nome primeiro.");
    document.getElementById("name").focus();
    return;
  }
  const exam = (await api("/api/exams")).exams.find((e) => e.id === examId);
  if (!confirm(`${exam.title}\n${exam.n} perguntas, ${exam.minutes} minutos.\nO tempo começa já. Começar?`)) return;
  const a = await api("/api/attempts", { method: "POST", body: JSON.stringify({ name, exam_id: examId }) });
  store.set(`sim_att_${a.attempt_id}`, {
    ...a, answers: {}, flags: {}, cur: 0, offset: a.started_at * 1000 - Date.now(),
  });
  const history = store.get("sim_history", []);
  history.push({ id: a.attempt_id, exam_id: examId, title: a.exam_title, at: Date.now(), pct: null });
  store.set("sim_history", history);
  location.hash = `#/exame/${a.attempt_id}`;
}

// ---------- exam ----------

async function exam(attemptId) {
  let st = store.get(`sim_att_${attemptId}`, null);
  if (!st) {
    const a = await api(`/api/attempts/${attemptId}`);
    if (a.submitted) { location.hash = `#/resultado/${attemptId}`; return; }
    st = { ...a, answers: {}, flags: {}, cur: 0, offset: a.now * 1000 - Date.now() };
  }
  const save = () => store.set(`sim_att_${attemptId}`, st);
  const deadline = st.started_at * 1000 + st.time_limit_s * 1000;
  const now = () => Date.now() + st.offset;
  let submitting = false;

  async function submit(auto) {
    if (submitting) return;
    if (!auto) {
      const left = st.questions.filter((q) => !(st.answers[q.id] || []).length).length;
      const flagged = Object.values(st.flags).filter(Boolean).length;
      const msg = [left ? `${left} perguntas sem resposta.` : "", flagged ? `${flagged} marcadas para rever.` : "", "Submeter o exame?"]
        .filter(Boolean).join("\n");
      if (!confirm(msg)) return;
    }
    submitting = true;
    stopTimer();
    try {
      const rv = await api(`/api/attempts/${attemptId}/submit`, { method: "POST", body: JSON.stringify({ answers: st.answers }) });
      const history = store.get("sim_history", []);
      const h = history.find((x) => x.id === attemptId);
      if (h) { h.pct = rv.pct; store.set("sim_history", history); }
      store.del(`sim_att_${attemptId}`);
      location.hash = `#/resultado/${attemptId}`;
    } catch (e) {
      submitting = false;
      alert(`Não foi possível submeter (${e.message}). As respostas estão guardadas neste browser: tenta outra vez.`);
    }
  }

  function renderTimer() {
    const ms = deadline - now();
    if (ms <= 0) { timerEl.textContent = "0:00"; submit(true); return; }
    const m = Math.floor(ms / 60000), s = Math.floor((ms % 60000) / 1000);
    timerEl.textContent = `${m}:${String(s).padStart(2, "0")}`;
    timerEl.classList.toggle("low", ms < 5 * 60000);
  }
  stopTimer();
  timerEl.hidden = false;
  renderTimer();
  tick = setInterval(renderTimer, 1000);
  whoEl.textContent = `${st.name || store.get("sim_name", "")} · ${st.exam_title}`;

  function render() {
    const q = st.questions[st.cur];
    const chosen = st.answers[q.id] || [];
    const multi = q.type === "multi";
    view.innerHTML = `
      <div class="card">
        <div class="qhead"><span>Pergunta ${st.cur + 1} de ${st.questions.length}</span>
          <span>${multi ? "Escolhe duas" : "Escolhe uma"}</span></div>
        <p class="qtext">${esc(q.question)}</p>
        ${q.options.map((o, i) => `
          <label class="opt ${chosen.includes(i) ? "sel" : ""}">
            <input type="${multi ? "checkbox" : "radio"}" name="o" value="${i}" ${chosen.includes(i) ? "checked" : ""}>
            <span class="letter">${LETTERS[i]}</span><span>${esc(o)}</span>
          </label>`).join("")}
        <div class="row spread" style="margin-top:16px">
          <div class="row">
            <button id="prev" ${st.cur === 0 ? "disabled" : ""}>← Anterior</button>
            <button id="next" ${st.cur === st.questions.length - 1 ? "disabled" : ""}>Seguinte →</button>
          </div>
          <label class="row small"><input type="checkbox" id="flag" ${st.flags[q.id] ? "checked" : ""}> Marcar para rever</label>
          <button class="primary" id="submit">Submeter exame</button>
        </div>
      </div>
      <div class="nav">${st.questions.map((x, i) => `<button data-go="${i}" class="${(st.answers[x.id] || []).length ? "ans" : ""}
        ${i === st.cur ? "cur" : ""} ${st.flags[x.id] ? "flag" : ""}">${i + 1}</button>`).join("")}</div>
      <p class="small muted">Verde: respondida · sublinhado laranja: marcada para rever. As respostas ficam guardadas neste browser se recarregares a página.</p>`;
    view.querySelectorAll("input[name=o]").forEach((inp) => inp.addEventListener("change", () => {
      const i = Number(inp.value);
      let cur = st.answers[q.id] || [];
      if (!multi) cur = [i];
      else if (inp.checked) cur = [...cur.filter((x) => x !== i), i].slice(-2);  // keep the two latest picks
      else cur = cur.filter((x) => x !== i);
      st.answers[q.id] = cur;
      save();
      render();
    }));
    document.getElementById("flag").addEventListener("change", (e) => { st.flags[q.id] = e.target.checked; save(); render(); });
    document.getElementById("prev").addEventListener("click", () => { st.cur--; save(); render(); });
    document.getElementById("next").addEventListener("click", () => { st.cur++; save(); render(); });
    document.getElementById("submit").addEventListener("click", () => submit(false));
    view.querySelectorAll("[data-go]").forEach((b) => b.addEventListener("click", () => { st.cur = Number(b.dataset.go); save(); render(); }));
  }
  save();
  render();
}

// ---------- result ----------

function renderReview(rv, opts = {}) {
  const passed = rv.pct >= GOAL;
  const wrong = rv.questions.filter((q) => !q.correct).length;
  const mins = rv.duration_s != null ? Math.round(rv.duration_s / 60) : null;
  return `
    <h1>${esc(rv.exam_title)}</h1>
    <p class="muted">${esc(rv.name)} · ${new Date(rv.started_at * 1000).toLocaleString("pt-PT")}${mins != null ? ` · ${mins} min` : ""}${rv.late ? " · submetido fora do tempo" : ""}</p>
    <div class="card row" style="gap:28px">
      <div><div class="score">${rv.pct}%</div><div class="muted">${rv.correct} de ${rv.total} certas</div></div>
      <div>
        <div class="verdict ${passed ? "ok" : "bad"}">${passed ? "Acima da meta da turma (80%)" : "Abaixo da meta da turma (80%)"}</div>
        <div class="small muted">A nota mínima oficial não é publicada (estima-se ~70%).<br>
          Treina até teres 80% em dois simulados seguidos.</div>
      </div>
    </div>
    <h2>Por domínio</h2>
    <div class="bars">${rv.domains.map((d) => {
      const p = Math.round((100 * d.correct) / d.total);
      return `<div class="bar"><span>${esc(d.name)}</span><div class="track"><div class="fill ${p < 70 ? "weak" : ""}" style="width:${p}%"></div></div>
        <span class="num">${d.correct}/${d.total}</span></div>`;
    }).join("")}</div>
    <div class="tabs" id="tabs">
      <button data-f="wrong" class="on">Erradas (${wrong})</button>
      <button data-f="all">Todas (${rv.total})</button>
    </div>
    ${opts.footer || ""}
    <div class="list" id="rq"></div>`;
}

function renderQuestions(rv, filter) {
  const qs = rv.questions.map((q, i) => ({ ...q, n: i + 1 })).filter((q) => filter === "all" || !q.correct);
  if (!qs.length) return `<p class="muted">Nenhuma pergunta errada. Muito bem!</p>`;
  return qs.map((q) => `
    <div class="card rq ${q.correct ? "right" : "wrong"}">
      <div class="qhead"><span>Pergunta ${q.n} · ${esc(q.topic)}</span>
        <span class="tag ${q.correct ? "" : "bad"}">${q.correct ? "Certa" : q.chosen.length ? "Errada" : "Sem resposta"}</span></div>
      <p class="qtext">${esc(q.question)}</p>
      ${q.options.map((o, i) => {
        const isAns = q.answer.includes(i), isChosen = q.chosen.includes(i);
        const cls = isAns ? "correct" : isChosen ? "chosen-wrong" : "";
        const mark = isAns ? "✓" : isChosen ? "✗" : "";
        return `<div class="opt ${cls}"><span class="letter">${LETTERS[i]}</span><span style="flex:1">${esc(o)}</span>
          <span>${mark}${isChosen ? " <span class='small muted'>a tua</span>" : ""}</span></div>`;
      }).join("")}
      <div class="expl"><b>Porquê:</b> ${esc(q.explanation)}<br>
        <span class="small">Investiga: <a href="${esc(q.source.url)}" target="_blank" rel="noopener">${esc(q.source.title)}</a></span></div>
    </div>`).join("");
}

function wireReview(rv) {
  const box = document.getElementById("rq");
  const show = (f) => {
    box.innerHTML = renderQuestions(rv, f);
    document.querySelectorAll("#tabs button").forEach((b) => b.classList.toggle("on", b.dataset.f === f));
  };
  document.querySelectorAll("#tabs button").forEach((b) => b.addEventListener("click", () => show(b.dataset.f)));
  show("wrong");
}

async function result(attemptId) {
  stopTimer();
  setWho();
  const a = await api(`/api/attempts/${attemptId}`);
  if (!a.submitted) { location.hash = `#/exame/${attemptId}`; return; }
  view.innerHTML = renderReview(a.review, {
    footer: `<p class="small muted">Guarda este link para voltares a esta revisão. <a href="#/">Voltar ao início</a></p>`,
  });
  wireReview(a.review);
  window.scrollTo(0, 0);
}

// ---------- router ----------

async function route() {
  const [, page, id] = location.hash.replace(/^#/, "").split("/");
  try {
    if (page === "exame" && id) await exam(id);
    else if (page === "resultado" && id) await result(id);
    else await home();
  } catch (e) {
    view.innerHTML = `<div class="card"><b>Erro:</b> ${esc(e.message)}<p><a href="#/">Voltar ao início</a></p></div>`;
  }
}
// formador.html reuses the review rendering above and has its own router.
if (!window.FORMADOR) {
  window.addEventListener("hashchange", route);
  route();
}
