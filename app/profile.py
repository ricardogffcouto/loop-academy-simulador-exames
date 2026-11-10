"""Grupo 5 · Perfil do aluno e estatísticas da turma."""

from datetime import date, datetime, timedelta

from fastapi import APIRouter
from pydantic import BaseModel, field_validator

from app import store

router = APIRouter(prefix="/api", tags=["perfil e estatísticas"])


class Profile(BaseModel):
    """Dados válidos do perfil de preparação para um exame."""

    name: str
    certification: str
    exam_date: date

    @field_validator("exam_date")
    @classmethod
    def validate_exam_date(cls, exam_date: date) -> date:
        """Aceita apenas datas entre hoje e os próximos dois anos."""
        today = date.today()
        latest_allowed_date = today + timedelta(days=730)
        if not today <= exam_date <= latest_allowed_date:
            raise ValueError("A data do exame deve estar entre hoje e os próximos 730 dias.")
        return exam_date


@router.get("/profile")
def get_profile() -> dict:
    profile = dict(store.profile)
    if "exam_date" in profile:
        try:
            exam_day = datetime.fromisoformat(profile["exam_date"]).date()
        except ValueError:
            pass
        else:
            profile["days_left"] = (exam_day - date.today()).days
    return profile


@router.post("/profile")
async def save_profile(profile: Profile) -> dict:
    """Valida, guarda e devolve o perfil de preparação para o exame."""
    store.profile.clear()
    store.profile.update(profile.model_dump(mode="json"))
    store.save()
    return get_profile()


@router.get("/stats")
def get_stats() -> dict:
    """  Devolve as estatísticas da turma, incluindo exames feitos, aprovados e percentagem de acertos por tópico."""
    by_topic: dict[str, list[int]] = {}  # tópico -> [certas, total]
    finished = 0
    passed = 0
    for exam in store.exams.values():
        if "answers" not in exam:
            continue
        finished += 1
        score = 0
        for qid in exam["questions"]:
            question = store.questions[qid]
            chosen = exam["answers"].get(qid, [])
            ok = question["type"] != "truefalse" and sorted(chosen) == sorted(question["correct"])
            counts = by_topic.setdefault(question["topic"], [0, 0])
            counts[1] += 1
            if ok:
                score += 1
                counts[0] += 1
        percentage = round(score / len(exam["questions"]) * 100)
        if percentage >= store.PASS_MARK:
            passed += 1
    return {
        "exams": finished,
        "passed": passed,
        "topics": [
            {"topic": topic, "pct": round(right / total * 100), "correct": right, "total": total}
            for topic, (right, total) in by_topic.items()
        ],
    }
