"""Grupo 1 · Banco de perguntas: listar, ler, criar e importar."""

import csv
import io
import json
from typing import Annotated, Literal

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, model_validator

from app import store

router = APIRouter(prefix="/api", tags=["perguntas"])

class Question(BaseModel):
    id: str = Field(..., description="Identificador único da pergunta")
    topic: str = Field(..., description="Tópico da pergunta")
    text: str = Field(min_length=3)
    options: list[str] = Field(min_length=2, max_length=6)
    correct: list[int] = Field(min_length=1)
    explanation: str = ""
    type: Literal["single", "multiple"] = "single"
    @model_validator(mode="after")
    def validate_corrects(self):
        if not self.correct:
            raise ValueError("correct deve ser uma lista de índices")
        
        for index in self.correct:
            if index < 0 or index >= len(self.options):
                raise ValueError(f"Índice {index} em correct está fora do intervalo de opções")
        return self


@router.get("/topics")
def list_topics() -> list[str]:
    return store.topics()


@router.get("/questions")
def list_questions(topic: str | None = None) -> list[dict]:
    return [question for question in store.questions.values() if topic is None or question["topic"].lower() == topic.lower()]


@router.get("/questions/{question_id}")
def get_question(question_id: str) -> dict:
    if question_id not in store.questions:
        raise HTTPException(status_code=404, detail="Pergunta não encontrada")
    return store.questions[question_id]


@router.post("/questions")
async def create_question(question: Question, pwd: str = ""):
    if pwd != store.ADMIN_PASSWORD:
        return JSONResponse({"erro": "password errada"}, status_code=401)
    if question.id in store.questions:
        raise HTTPException(status_code=409, detail="Pergunta já existe")
    add_question(question.model_dump())
    store.save()
    return question


@router.post("/upload")
async def upload_bank(file: Annotated[UploadFile, File()]) -> dict:
    content = await file.read()
    if file.filename.endswith(".json"):
        imported = json.loads(content)["questions"]
    elif file.filename.endswith(".csv"):
        imported = parse_csv(content.decode("utf-8"))
    else:
        imported = []
    for question in imported:
        question.setdefault("type", "single")
        add_question(question)
    store.save()
    return {"ok": True, "added": len(imported)}


def add_question(question: dict) -> None:
    store.questions[question["id"]] = question
    store.custom_questions.append(question)


def parse_csv(text: str) -> list[dict]:
    """Converte um CSV (id,topic,text,option_a..option_f,correct,explanation) em perguntas."""
    parsed = []
    for row in csv.DictReader(io.StringIO(text)):
        try:
            options = [row[f"option_{letter}"] for letter in "abcdef" if row.get(f"option_{letter}")]
            correct = ["ABCDEF".index(letter) for letter in row["correct"].split(";")]
        except (KeyError, ValueError):
            continue  # linha inválida: salta
        parsed.append(
            {
                "id": row["id"],
                "topic": row["topic"],
                "text": row["text"],
                "options": options,
                "correct": correct,
                "explanation": row.get("explanation", ""),
                "type": "multiple" if len(correct) > 1 else "single",
            }
        )
    return parsed
