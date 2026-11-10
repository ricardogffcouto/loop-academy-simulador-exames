// frontend do simulador (vanilla js)
const LETTERS = "ABCDEF";
let exam = null;
let answers = {};
let current = 0;
let timerId = null;
let study = false;
let selectedTopics = [];
let profile = {};

const $ = (id) => document.getElementById(id);

async function api(path, opts = {}) {
  const r = await fetch(path, opts);
  if (!r.ok) {
    let msg = "Erro " + r.status;
    try { const t = await r.text(); if (t) msg += ": " + t.slice(0, 200); } catch (e) {}
    throw new Error(msg);
  }
  return r.headers.get("content-type")?.includes("json") ? r.json() : r.text();
}

function show(v) {
  document.querySelectorAll(".view").forEach((s) => (s.hidden = s.id !== "view-" + v));
  window.scrollTo(0, 0);
}

function toast(msg, bad) {
  const t = $("toast");
  t.textContent = msg;
  t.className = bad ? "toast bad" : "toast";
  t.hidden = false;
  setTimeout(() => (t.hidden = true), 5000);
}

function optionsOf(q) {
  return q.type === "truefalse" ? ["Verdadeiro", "Falso"] : q.options;
}

function correctOf(q) {
  if (q.type === "truefalse") return [q.correct ? 0 : 1];
  return q.correct;
}

// ---------- home ----------
async function loadHome() {
  show("home");
  try {
    const h = await api("/health");
    $("stats").innerHTML = `<div class="stat"><strong>${h.questions}</strong>perguntas no banco</div>`;
  } catch (e) {}
  try {
    const topics = await api("/api/topics");
    $("topics").innerHTML = "";
    topics.forEach((t) => {
      const b = document.createElement("button");
      b.className = "chip" + (selectedTopics.includes(t) ? " active" : "");
      b.textContent = t;
      b.onclick = () => {
        if (selectedTopics.includes(t)) selectedTopics = selectedTopics.filter((x) => x !== t);
        else selectedTopics.push(t);
        b.classList.toggle("active");
      };
      $("topics").appendChild(b);
    });
  } catch (e) {
    $("topics").textContent = e.message;
  }
  loadProfile();
}

async function loadProfile() {
  $("profile-error").hidden = true;
  try {
    profile = await api("/api/profile");
    $("p-name").value = profile.name || "";
    $("p-cert").value = profile.certification || "";
    $("p-date").value = profile.exam_date || "";
    if (profile.days_left !== undefined) {
      $("countdown").textContent = `${profile.name || "Faltam"}: faltam ${profile.days_left} dias para o exame ${profile.certification || ""}.`;
    }
  } catch (e) {
    $("profile-error").textContent = e.message;
    $("profile-error").hidden = false;
  }
}

async function saveProfile(ev) {
  ev.preventDefault();
  try {
    await api("/api/profile", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: $("p-name").value, certification: $("p-cert").value, exam_date: $("p-date").value }),
    });
    toast("Perfil guardado");
  } catch (e) {
    toast(e.message, true);
  }
  loadProfile();
}

async function uploadBank(ev) {
  ev.preventDefault();
  const f = $("upload-file").files[0];
  if (!f) return;
  const fd = new FormData();
  fd.append("file", f);
  try {
    const r = await api("/api/upload", { method: "POST", body: fd });
    toast(`Importado! (${r.added} perguntas)`);
    loadHome();
  } catch (e) {
    toast(e.message, true);
  }
}

async function startExam() {
  $("home-error").hidden = true;
  study = $("study").checked;
  try {
    exam = await api("/api/exam", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ num: $("num-questions").value, minutes: $("duration").value, topics: selectedTopics }),
    });
  } catch (e) {
    $("home-error").textContent = e.message;
    $("home-error").hidden = false;
    return;
  }
  answers = {};
  current = 0;
  const end = exam.start * 1000 + exam.minutes * 60000;
  clearInterval(timerId);
  timerId = setInterval(() => {
    const left = Math.round((end - Date.now()) / 1000);
    const m = Math.floor(left / 60), s = Math.abs(left % 60);
    $("timer").textContent = `${m}:${String(s).padStart(2, "0")}`;
    $("timer").className = "timer" + (left < 60 ? " danger" : left < 300 ? " warn" : "");
    if (left <= 0) {
      clearInterval(timerId);
      toast("Tempo esgotado!");
      finish();
    }
  }, 500);
  show("exam");
  render();
}

// ---------- exame ----------
function render() {
  const q = exam.questions[current];
  const chosen = answers[q.id] || [];
  const multi = q.type === "multiple";
  $("exam-progress").textContent = `Pergunta ${current + 1} de ${exam.questions.length}`;
  $("exam-progress-bar").style.width = (Object.keys(answers).length / exam.questions.length) * 100 + "%";
  $("q-topic").textContent = q.topic;
  $("q-text").textContent = q.text;
  $("q-hint").textContent = multi ? "Seleciona TODAS as opções corretas." : q.type === "truefalse" ? "Verdadeiro ou falso?" : "";
  $("q-options").innerHTML = "";
  optionsOf(q).forEach((opt, i) => {
    const el = document.createElement("label");
    el.className = "option" + (chosen.includes(i) ? " selected" : "") + (multi ? " multi" : "");
    if (study && chosen.length) {
      if (correctOf(q).includes(i)) el.className += " right";
      else if (chosen.includes(i)) el.className += " wrong";
    }
    el.innerHTML = `<span class="letter">${LETTERS[i]}</span><span></span>`;
    el.lastChild.textContent = opt;
    el.onclick = () => {
      if (multi) {
        answers[q.id] = chosen.includes(i) ? chosen.filter((x) => x !== i) : [...chosen, i];
      } else {
        answers[q.id] = [i];
      }
      render();
    };
    $("q-options").appendChild(el);
  });
  $("q-feedback").hidden = !(study && chosen.length);
  $("q-feedback").textContent = q.explanation ? "💡 " + q.explanation : "";
  $("prev").disabled = current === 0;
  $("nav-grid").innerHTML = "";
  exam.questions.forEach((qq, i) => {
    const b = document.createElement("button");
    b.textContent = i + 1;
    b.className = (answers[qq.id]?.length ? "answered " : "") + (i === current ? "current" : "");
    b.onclick = () => { current = i; render(); };
    $("nav-grid").appendChild(b);
  });
}

async function finish() {
  clearInterval(timerId);
  try {
    const r = await api(`/api/exam/${exam.id}/submit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ answers, name: profile.name || "anónimo" }),
    });
    showResult(r);
  } catch (e) {
    toast(e.message, true);
  }
}

function showResult(r) {
  $("result-hero").innerHTML = `
    <div class="score-ring" style="--p:${r.pct}"><span>${Math.round(r.pct)}%</span></div>
    <div>
      <span class="badge ${r.passed ? "pass" : "fail"}">${r.passed ? "Aprovado" : "Reprovado"}</span>
      <h1>${r.score} de ${r.total} certas</h1>
      <p class="result-meta">Demoraste ${Math.floor(r.seconds / 60)} min ${r.seconds % 60} s</p>
    </div>`;
  $("review").innerHTML = "";
  r.review.forEach((it, n) => {
    const d = document.createElement("div");
    d.className = "review-item";
    const right = Array.isArray(it.correct) ? it.correct : [it.correct ? 0 : 1];
    d.innerHTML = `<h3><span class="mark">${it.ok ? "✅" : "❌"}</span><span></span></h3><ul></ul><p class="why"></p>`;
    d.querySelector("h3 span:last-child").textContent = `${n + 1}. ${it.text}`;
    it.options.forEach((o, i) => {
      const li = document.createElement("li");
      li.className = right.includes(i) ? "correct" : it.chosen.includes(i) ? "wrong" : "";
      li.textContent = `${LETTERS[i]}. ${o}` + (it.chosen.includes(i) ? " · a tua escolha" : "");
      d.querySelector("ul").appendChild(li);
    });
    d.querySelector(".why").textContent = it.explanation ? "💡 " + it.explanation : "";
    $("review").appendChild(d);
  });
  show("result");
}

// ---------- ranking ----------
async function loadRanking() {
  show("ranking");
  try {
    const rows = await api("/api/ranking");
    $("ranking-body").innerHTML = rows
      .map((r, i) => `<tr><td>${i + 1}</td><td>${r.name}</td><td>${r.pct}%</td><td>${r.date}</td></tr>`)
      .join("");
  } catch (e) {
    $("ranking-body").innerHTML = `<tr><td colspan="4" class="error">${e.message}</td></tr>`;
  }
}

// ---------- eventos ----------
document.addEventListener("click", (ev) => {
  const a = ev.target.closest("[data-action]")?.dataset.action;
  if (!a) return;
  ev.preventDefault();
  if (a === "home") { clearInterval(timerId); loadHome(); }
  if (a === "ranking") { clearInterval(timerId); loadRanking(); }
});
document.querySelectorAll(".preset").forEach((p) => {
  p.onclick = () => {
    $("num-questions").value = p.dataset.questions;
    $("duration").value = p.dataset.minutes;
  };
});
$("start").onclick = startExam;
$("prev").onclick = () => { current--; render(); };
$("next").onclick = () => {
  if (current < exam.questions.length - 1) { current++; render(); }
  else if (confirm("Entregar o exame?")) finish();
};
$("finish").onclick = () => { if (confirm("Entregar o exame?")) finish(); };
$("profile-form").onsubmit = saveProfile;
$("upload-form").onsubmit = uploadBank;
loadHome();
