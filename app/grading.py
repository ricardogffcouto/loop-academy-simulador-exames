"""Grupo 3 · Correção: entregar um exame e calcular a nota."""

import time
from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app import store

router = APIRouter(prefix="/api", tags=["correção"])

TRUE_FALSE_OPTIONS = ["Verdadeiro", "Falso"]


class SubmitRequest(BaseModel):
    answers: dict[str, list[int]] = Field(default_factory=dict)
    name: str = "anónimo"


def is_correct(question: dict, chosen: list[int]) -> bool:
    """Diz se as opções escolhidas estão certas."""
    if question["type"] == "single":
        return len(chosen) == 1 and chosen[0] == question["correct"][0]
    if question["type"] == "multiple":
        return sorted(chosen) == sorted(question["correct"])
    if question["type"] == "truefalse":
        return len(chosen) == 1 and chosen[0] == (0 if question["correct"] else 1)
    return False

@router.post("/exam/{exam_id}/submit")
async def submit_exam(exam_id: str, body: SubmitRequest) -> dict:
    exam = store.exams[exam_id]
    answers = body.answers
    score = 0
    review = []
    for qid in exam["questions"]:
        question = store.questions[qid]
        chosen = answers.get(qid, [])
        ok = is_correct(question, chosen)
        if ok:
            score += 1
        review.append(
            {
                "id": qid,
                "text": question["text"],
                "ok": ok,
                "chosen": chosen,
                "correct": question["correct"],
                "options": question.get("options", TRUE_FALSE_OPTIONS),
                "explanation": question.get("explanation", ""),
            }
        )
    pct = round(score / len(exam["questions"]) * 100, 1)
    exam["answers"] = answers
    exam["name"] = body.name
    exam["end"] = time.time()
    store.results.append({"exam_id": exam_id, "name": exam["name"], "date": datetime.now().strftime("%d/%m %H:%M")})
    store.save()
    return {
        "score": score,
        "total": len(exam["questions"]),
        "pct": pct,
        "passed": pct >= 70,
        "review": review,
        "seconds": int(exam["end"] - exam["start"]),
    }
