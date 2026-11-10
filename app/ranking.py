"""Grupo 4 · Ranking e exportação de resultados."""

import io
from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

from app import store

from pydantic import BaseModel, Field, field_validator

router = APIRouter(prefix="/api", tags=["ranking"])

class RankingEntryIn(BaseModel):
    """Entrada de ranking enviada pelo cliente."""

    name: str = Field(min_length=1, max_length=30)
    pct: float = Field(ge=0, le=100)

    @field_validator("name")
    def name_must_not_contain_html(cls, v: str) -> str:
        if "<" in v or ">" in v:
            raise ValueError("name must not contain HTML")
        return v


def exam_score(exam: dict) -> float:
    """Pontos de um exame entregue (as de escolha múltipla dão pontos parciais)."""
    score = 0.0
    for qid in exam["questions"]:
        question = store.questions[qid]
        chosen = exam.get("answers", {}).get(qid, [])
        if question["type"] == "truefalse":
            if chosen == [0 if question["correct"] else 1]:
                score += 1
        elif question["type"] == "multiple":
            score += len(set(chosen) & set(question["correct"])) / len(question["correct"])
        elif chosen == question["correct"]:
            score += 1
    return score


@router.get("/ranking")
def get_ranking() -> list[dict]:
    rows = []
    for entry in store.results:
        if entry.get("pct") is not None:
            pct = entry["pct"]
        else:
            exam = store.exams[entry["exam_id"]]
            pct = round(exam_score(exam) / len(exam["questions"]) * 100, 1)
        rows.append({"name": entry["name"], "pct": pct, "date": entry["date"]})
    return sorted(rows, key=lambda row: row["pct"], reverse=True)


@router.post("/ranking")
async def add_ranking_entry(entry: RankingEntryIn) -> dict:
    store.results.append(
        {
            "exam_id": None,
            "name": entry.name,
            "date": datetime.now().strftime("%d/%m %H:%M"),
            "pct": entry.pct,
        }
    )
    store.save()
    return {"ok": True}


@router.delete("/ranking")
def clear_ranking(pwd: str = "") -> dict:
    if pwd == store.ADMIN_PASSWORD:
        store.results.clear()
        store.save()
    return {"ok": True}


@router.get("/export.csv")
def export_csv() -> PlainTextResponse:
    out = io.StringIO()
    out.write("exam,name,score,total,passed\n")
    for exam in store.exams.values():
        if "answers" not in exam:
            continue
        score = sum(
            1
            for qid in exam["questions"]
            if sorted(exam["answers"].get(qid, [])) == sorted(store.questions[qid]["correct"])
        )
        total = len(exam["questions"])
        out.write(f"{exam['id']},{exam.get('name', '')},{score},{total},{score >= 70}\n")
    return PlainTextResponse(out.getvalue(), media_type="text/csv")


@router.get("/export.yaml")
def export_yaml() -> PlainTextResponse:
    import yaml

    return PlainTextResponse(yaml.dump(list(store.exams.values()), allow_unicode=True))
