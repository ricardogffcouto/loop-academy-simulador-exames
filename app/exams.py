"""Grupo 2 · Exames: criar um exame e voltar a abri-lo."""

import random
import time
import uuid

from fastapi import APIRouter, Request

from app import store

router = APIRouter(prefix="/api", tags=["exames"])


def pick_questions(count: int, topics: list[str] = []) -> list[str]:
    """Escolhe ao acaso `count` ids de perguntas dos tópicos pedidos (todos, se nenhum)."""
    if not topics:
        topics.extend(store.topics())
    pool = [qid for qid, question in store.questions.items() if question["topic"] in topics]
    return random.sample(pool, count)


@router.post("/exam")
async def create_exam(request: Request) -> dict:
    body = await request.json()
    count = int(body.get("num", 10))
    minutes = int(body.get("minutes", 15))
    if body.get("topics"):
        question_ids = pick_questions(count, body["topics"])
    else:
        question_ids = pick_questions(count)
    exam_id = uuid.uuid4().hex[:8]
    store.exams[exam_id] = {
        "id": exam_id,
        "questions": question_ids,
        "start": time.time(),
        "minutes": minutes,
    }
    store.save()
    return exam_view(store.exams[exam_id])


@router.get("/exam/{exam_id}")
def get_exam(exam_id: str) -> dict:
    return exam_view(store.exams[exam_id])


def exam_view(exam: dict) -> dict:
    return {
        "id": exam["id"],
        "questions": [store.questions[qid] for qid in exam["questions"]],
        "minutes": exam["minutes"],
        "start": exam["start"],
    }
