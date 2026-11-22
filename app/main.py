"""Simulados NCA-GENL · Loop Future Academy.

Students type a name, take a mock exam and see a full review.
The instructor page (/formador) lists every attempt and which questions each student missed.
"""

import csv
import io
import json
import os
import secrets
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.bank import DOMAINS, exam_catalog, is_correct, load_bank, load_mocks, pick_questions

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"
DB_PATH = os.environ.get("SIM_DB", str(ROOT / "simulados.db"))
ADMIN_TOKEN = os.environ.get("SIM_ADMIN_TOKEN", "")
# Late submits are still graded (the browser auto-submits at 0:00), but flagged after this grace.
GRACE_S = 120

BANK = load_bank()
MOCKS = load_mocks(BANK)
CATALOG = exam_catalog(BANK, MOCKS)

app = FastAPI(title="Simulados NCA-GENL")


@contextmanager
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with db() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS attempts (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                name_key TEXT NOT NULL,
                exam_id TEXT NOT NULL,
                exam_title TEXT NOT NULL,
                question_ids TEXT NOT NULL,
                time_limit_s INTEGER NOT NULL,
                started_at REAL NOT NULL,
                submitted_at REAL,
                answers TEXT,
                correct INTEGER,
                total INTEGER NOT NULL
            )"""
        )


init_db()


# ---------- student API ----------

class StartIn(BaseModel):
    name: str = Field(min_length=2, max_length=40)
    exam_id: str


class SubmitIn(BaseModel):
    answers: dict[str, list[int]]


def public_question(qid: str) -> dict:
    q = BANK[qid]
    return {"id": qid, "domain": q["domain"], "type": q["type"], "question": q["question"], "options": q["options"]}


def review(row: sqlite3.Row) -> dict:
    answers = json.loads(row["answers"] or "{}")
    items, per_domain = [], {d: {"name": DOMAINS[d][0], "correct": 0, "total": 0} for d in DOMAINS}
    for qid in json.loads(row["question_ids"]):
        q = BANK.get(qid)
        if q is None:  # question retired from the bank after this attempt
            continue
        chosen = answers.get(qid)
        ok = is_correct(q, chosen)
        per_domain[q["domain"]]["total"] += 1
        per_domain[q["domain"]]["correct"] += ok
        items.append({**public_question(qid), "topic": q["topic"], "chosen": chosen or [], "answer": q["answer"],
                      "correct": ok, "explanation": q["explanation"], "source": q["source"]})
    total = len(items)
    correct = sum(i["correct"] for i in items)
    return {
        "attempt_id": row["id"], "name": row["name"], "exam_id": row["exam_id"], "exam_title": row["exam_title"],
        "started_at": row["started_at"], "submitted_at": row["submitted_at"],
        "duration_s": round(row["submitted_at"] - row["started_at"]) if row["submitted_at"] else None,
        "late": bool(row["submitted_at"] and row["submitted_at"] - row["started_at"] > row["time_limit_s"] + GRACE_S),
        "correct": correct, "total": total, "pct": round(100 * correct / total) if total else 0,
        "domains": [{"id": d, **v} for d, v in per_domain.items() if v["total"]],
        "questions": items,
    }


def get_row(attempt_id: str) -> sqlite3.Row:
    with db() as conn:
        row = conn.execute("SELECT * FROM attempts WHERE id = ?", (attempt_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Tentativa não encontrada")
    return row


@app.get("/health")
def health():
    return {"ok": True, "questions": len(BANK)}


@app.get("/api/exams")
def exams():
    counts = {d: 0 for d in DOMAINS}
    for q in BANK.values():
        counts[q["domain"]] += 1
    return {"exams": CATALOG, "bank": {"total": len(BANK), "domains": [
        {"id": d, "name": n, "weight": w, "count": counts[d]} for d, (n, w) in DOMAINS.items()]}}


@app.post("/api/attempts")
def start(body: StartIn):
    name = " ".join(body.name.split())
    picked = pick_questions(body.exam_id, BANK, MOCKS)
    if picked is None:
        raise HTTPException(404, "Exame desconhecido")
    title, qids, limit = picked
    attempt_id = uuid.uuid4().hex
    now = time.time()
    with db() as conn:
        conn.execute(
            "INSERT INTO attempts (id, name, name_key, exam_id, exam_title, question_ids, time_limit_s, started_at,"
            " total) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (attempt_id, name, name.casefold(), body.exam_id, title, json.dumps(qids), limit, now, len(qids)),
        )
    return {"attempt_id": attempt_id, "exam_title": title, "time_limit_s": limit, "started_at": now,
            "questions": [public_question(q) for q in qids]}


@app.get("/api/attempts/{attempt_id}")
def attempt(attempt_id: str):
    row = get_row(attempt_id)
    if row["submitted_at"]:
        return {"submitted": True, "review": review(row)}
    return {"submitted": False, "attempt_id": row["id"], "name": row["name"], "exam_title": row["exam_title"],
            "time_limit_s": row["time_limit_s"], "started_at": row["started_at"], "now": time.time(),
            "questions": [public_question(q) for q in json.loads(row["question_ids"])]}


@app.post("/api/attempts/{attempt_id}/submit")
def submit(attempt_id: str, body: SubmitIn):
    row = get_row(attempt_id)
    if row["submitted_at"]:  # double click or a second tab: return the stored result
        return review(row)
    qids = set(json.loads(row["question_ids"]))
    answers = {k: sorted(set(v)) for k, v in body.answers.items() if k in qids and v}
    correct = sum(is_correct(BANK[q], answers.get(q)) for q in qids if q in BANK)
    with db() as conn:
        conn.execute("UPDATE attempts SET submitted_at = ?, answers = ?, correct = ? WHERE id = ?",
                     (time.time(), json.dumps(answers), correct, attempt_id))
    return review(get_row(attempt_id))


# ---------- instructor API ----------

def require_admin(token: str | None) -> None:
    if not ADMIN_TOKEN or not token or not secrets.compare_digest(token, ADMIN_TOKEN):
        raise HTTPException(401, "Token de formador inválido")


@app.get("/api/admin/attempts")
def admin_attempts(x_admin_token: str | None = Header(None)):
    require_admin(x_admin_token)
    with db() as conn:
        rows = conn.execute("SELECT * FROM attempts ORDER BY started_at DESC").fetchall()
    out = []
    for r in rows:
        item = {"attempt_id": r["id"], "name": r["name"], "exam_id": r["exam_id"], "exam_title": r["exam_title"],
                "started_at": r["started_at"], "submitted_at": r["submitted_at"], "total": r["total"]}
        if r["submitted_at"]:
            rv = review(r)
            item.update(correct=rv["correct"], pct=rv["pct"], duration_s=rv["duration_s"], late=rv["late"],
                        domains={d["id"]: [d["correct"], d["total"]] for d in rv["domains"]})
        out.append(item)
    return {"attempts": out}


@app.get("/api/admin/attempts/{attempt_id}")
def admin_attempt(attempt_id: str, x_admin_token: str | None = Header(None)):
    require_admin(x_admin_token)
    row = get_row(attempt_id)
    if not row["submitted_at"]:
        raise HTTPException(409, "Ainda não submetido")
    return review(row)


@app.delete("/api/admin/attempts/{attempt_id}")
def admin_delete(attempt_id: str, x_admin_token: str | None = Header(None)):
    """For test runs and typos in names."""
    require_admin(x_admin_token)
    get_row(attempt_id)
    with db() as conn:
        conn.execute("DELETE FROM attempts WHERE id = ?", (attempt_id,))
    return {"deleted": attempt_id}


@app.get("/api/admin/questions")
def admin_questions(x_admin_token: str | None = Header(None), exam_id: str | None = Query(None)):
    """Per-question stats over submitted attempts: how many missed it, and who."""
    require_admin(x_admin_token)
    sql, args = "SELECT * FROM attempts WHERE submitted_at IS NOT NULL", ()
    if exam_id:
        sql, args = sql + " AND exam_id = ?", (exam_id,)
    with db() as conn:
        rows = conn.execute(sql, args).fetchall()
    stats: dict[str, dict] = {}
    for r in rows:
        answers = json.loads(r["answers"] or "{}")
        for qid in json.loads(r["question_ids"]):
            q = BANK.get(qid)
            if q is None:
                continue
            s = stats.setdefault(qid, {"id": qid, "domain": q["domain"], "topic": q["topic"],
                                       "question": q["question"], "options": q["options"], "answer": q["answer"],
                                       "seen": 0, "wrong": 0, "missed_by": [], "picks": [0] * len(q["options"])})
            s["seen"] += 1
            chosen = answers.get(qid) or []
            for c in chosen:
                if 0 <= c < len(s["picks"]):
                    s["picks"][c] += 1
            if not is_correct(q, chosen):
                s["wrong"] += 1
                s["missed_by"].append(r["name"])
    items = sorted(stats.values(), key=lambda s: (-s["wrong"] / s["seen"], -s["seen"]))
    return {"questions": items}


@app.get("/api/admin/export.csv", response_class=PlainTextResponse)
def admin_export(token: str = Query(...)):
    require_admin(token)
    with db() as conn:
        rows = conn.execute("SELECT * FROM attempts WHERE submitted_at IS NOT NULL ORDER BY started_at").fetchall()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["nome", "exame", "inicio_utc", "certas", "total", "pct", "duracao_min"] + list(DOMAINS))
    for r in rows:
        rv = review(r)
        dom = {d["id"]: f"{d['correct']}/{d['total']}" for d in rv["domains"]}
        w.writerow([r["name"], r["exam_title"], time.strftime("%Y-%m-%d %H:%M", time.gmtime(r["started_at"])),
                    rv["correct"], rv["total"], rv["pct"], round((rv["duration_s"] or 0) / 60, 1)]
                   + [dom.get(d, "") for d in DOMAINS])
    return PlainTextResponse(buf.getvalue(), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=simulados.csv"})


# ---------- pages ----------

@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/formador")
def formador():
    return FileResponse(STATIC / "formador.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
