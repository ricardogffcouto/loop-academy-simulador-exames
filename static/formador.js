// Instructor page. Routes: #/ (attempts) · #/alunos · #/perguntas · #/tentativa/<id>
(function () {
  const params = new URLSearchParams(location.search);
  if (params.get("token")) {
    store.set("sim_admin", params.get("token"));
    history.replaceState(null, "", location.pathname + location.hash);
  }
  const token = () => store.get("sim_admin", "");
  const adm = (path) => fetch(path, { headers: { "X-Admin-Token": token() } }).then(async (r) => {
    if (r.status === 401) {
      const t = prompt("Token de formador:");
      if (t) { store.set("sim_admin", t.trim()); return adm(path); }
      throw new Error("Sem token de formador");
    }
    if (!r.ok) throw new Error((await r.json()).detail || r.statusText);
    return r.json();
  });
  const DOM = { core: "Core", sw: "SW Dev", exp: "Exper.", da: "Data", tai: "Trust" };
  const pill = (p) => `<span class="pill ${p >= 80 ? "ok" : p < 70 ? "bad" : "mid"}">${p}%</span>`;
  const when = (t) => new Date(t * 1000).toLocaleString("pt-PT", { dateStyle: "short", timeStyle: "short" });
  const tabs = (on) => `<div class="tabs">
    ${[["", "Tentativas"], ["alunos", "Alunos"], ["perguntas", "Perguntas mais falhadas"]].map(([r, l]) =>
      `<a class="btn ${on === r ? "primary" : ""}" href="#/${r}">${l}</a>`).join("")}
    <a class="btn" href="/api/admin/export.csv?token=${encodeURIComponent(token())}">Exportar CSV</a></div>`;

  async function attempts() {
    const { attempts } = await adm("/api/admin/attempts");
    const done = attempts.filter((a) => a.submitted_at);
    view.innerHTML = `<h1>Tentativas</h1>${tabs("")}
      <p class="muted">${done.length} submetidas · ${attempts.length - done.length} em curso ou abandonadas.</p>
      <table><tr><th>Início</th><th>Aluno</th><th>Exame</th><th class="num">Nota</th>
        ${Object.values(DOM).map((d) => `<th class="num">${d}</th>`).join("")}<th class="num">Min</th><th></th></tr>
      ${attempts.map((a) => `<tr><td>${when(a.started_at)}</td><td>${esc(a.name)}</td><td>${esc(a.exam_title)}</td>
        <td class="num">${a.submitted_at ? `${pill(a.pct)} ${a.correct}/${a.total}` : `<span class="muted">em curso</span>`}</td>
        ${Object.keys(DOM).map((d) => `<td class="num">${a.domains && a.domains[d] ? `${a.domains[d][0]}/${a.domains[d][1]}` : ""}</td>`).join("")}
        <td class="num">${a.duration_s != null ? Math.round(a.duration_s / 60) : ""}${a.late ? "*" : ""}</td>
        <td>${a.submitted_at ? `<a href="#/tentativa/${a.attempt_id}">ver</a> · ` : ""}<a href="#" data-del="${a.attempt_id}"
          data-who="${esc(a.name)} · ${esc(a.exam_title)}" class="small">apagar</a></td></tr>`).join("")}
      </table><p class="small muted">* submetido depois do tempo limite.</p>`;
    view.querySelectorAll("[data-del]").forEach((el) => el.addEventListener("click", async (e) => {
      e.preventDefault();
      if (!confirm(`Apagar a tentativa de ${el.dataset.who}? Não dá para desfazer.`)) return;
      await fetch(`/api/admin/attempts/${el.dataset.del}`, { method: "DELETE", headers: { "X-Admin-Token": token() } });
      attempts();
    }));
  }

  async function students() {
    const { attempts } = await adm("/api/admin/attempts");
    const by = {};
    const full = (x) => x.submitted_at && (x.exam_id.startsWith("mock") || x.exam_id === "aleatorio");
    for (const a of attempts.filter(full)) {
      const k = a.name.toLocaleLowerCase("pt");
      (by[k] ||= { name: a.name, list: [], dom: {} }).list.push(a);
      for (const [d, [c, t]] of Object.entries(a.domains)) {
        const x = (by[k].dom[d] ||= [0, 0]); x[0] += c; x[1] += t;
      }
    }
    const rows = Object.values(by).sort((a, b) => a.name.localeCompare(b.name, "pt"));
    view.innerHTML = `<h1>Alunos</h1>${tabs("alunos")}
      <p class="muted">Só simulados completos (fixos e aleatórios). "Pronto" = as duas últimas tentativas com 80% ou mais.</p>
      <table><tr><th>Aluno</th><th class="num">Simulados</th><th>Últimas notas</th><th class="num">Melhor</th>
        ${Object.values(DOM).map((d) => `<th class="num">${d}</th>`).join("")}<th>Pronto?</th></tr>
      ${rows.map((s) => {
        const list = s.list.sort((a, b) => a.started_at - b.started_at);
        const last2 = list.slice(-2);
        const ready = last2.length === 2 && last2.every((a) => a.pct >= 80);
        return `<tr><td>${esc(s.name)}</td><td class="num">${list.length}</td>
          <td>${list.slice(-5).map((a) => `<a href="#/tentativa/${a.attempt_id}" title="${esc(a.exam_title)}">${pill(a.pct)}</a>`).join(" ")}</td>
          <td class="num">${Math.max(...list.map((a) => a.pct))}%</td>
          ${Object.keys(DOM).map((d) => { const x = s.dom[d]; return `<td class="num">${x ? pill(Math.round(100 * x[0] / x[1])) : ""}</td>`; }).join("")}
          <td>${ready ? "✅" : ""}</td></tr>`;
      }).join("")}</table>
      <p class="small muted">Colunas por domínio: % de acerto acumulado em todos os simulados do aluno.</p>`;
  }

  async function questions() {
    const sel = new URLSearchParams(location.hash.split("?")[1] || "").get("exame") || "";
    const [{ questions }, { exams }] = await Promise.all([
      adm(`/api/admin/questions${sel ? `?exam_id=${encodeURIComponent(sel)}` : ""}`), api("/api/exams")]);
    view.innerHTML = `<h1>Perguntas mais falhadas</h1>${tabs("perguntas")}
      <div class="row"><label for="ex">Exame:</label><select id="ex">
        <option value="">Todos</option>${exams.map((e) => `<option value="${esc(e.id)}" ${e.id === sel ? "selected" : ""}>${esc(e.title)}</option>`).join("")}
      </select></div>
      <div class="list" style="margin-top:14px">${questions.map((q) => {
        const p = Math.round((100 * q.wrong) / q.seen);
        return `<div class="card rq ${p >= 50 ? "wrong" : "right"}">
          <div class="qhead"><span>${esc(q.id)} · ${DOM[q.domain]} · ${esc(q.topic)}</span>
            <span><b>${q.wrong}/${q.seen}</b> erraram (${p}%)</span></div>
          <p class="qtext" style="font-size:16px">${esc(q.question)}</p>
          ${q.options.map((o, i) => `<div class="opt ${q.answer.includes(i) ? "correct" : ""}" style="padding:6px 10px;margin:4px 0">
            <span class="letter">${LETTERS[i]}</span><span style="flex:1">${esc(o)}</span><span class="small muted">${q.picks[i]}×</span></div>`).join("")}
          ${q.missed_by.length ? `<p class="small" style="margin:8px 0 0"><b>Erraram:</b> ${q.missed_by.map(esc).join(", ")}</p>` : ""}
        </div>`;
      }).join("") || `<p class="muted">Ainda não há tentativas submetidas.</p>`}</div>`;
    document.getElementById("ex").addEventListener("change", (e) => {
      location.hash = `#/perguntas${e.target.value ? `?exame=${encodeURIComponent(e.target.value)}` : ""}`;
    });
  }

  async function one(id) {
    const rv = await adm(`/api/admin/attempts/${id}`);
    view.innerHTML = renderReview(rv, { footer: `<p><a href="#/">← Tentativas</a></p>` });
    wireReview(rv);
    window.scrollTo(0, 0);
  }

  async function adminRoute() {
    const h = location.hash.replace(/^#\/?/, "");
    const [page, id] = h.split("?")[0].split("/");
    try {
      if (page === "alunos") await students();
      else if (page === "perguntas") await questions();
      else if (page === "tentativa" && id) await one(id);
      else await attempts();
    } catch (e) {
      view.innerHTML = `<div class="card"><b>Erro:</b> ${esc(e.message)}</div>`;
    }
  }
  window.addEventListener("hashchange", adminRoute);
  adminRoute();
})();
