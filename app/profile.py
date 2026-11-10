"""Grupo 5 · Perfil do aluno e estatísticas da turma."""

from datetime import date, datetime

from fastapi import APIRouter, Request

from app import store

router = APIRouter(prefix="/api", tags=["perfil e estatísticas"])


@router.get("/profile")
def get_profile() -> dict:
    profile = dict(store.profile)
    if "exam_date" in profile:
        exam_day = datetime.fromisoformat(profile["exam_date"]).date()
        profile["days_left"] = (exam_day - date.today()).days
    return profile


@router.post("/profile")
async def save_profile(request: Request) -> dict:
    store.profile.clear()
    store.profile.update(await request.json())
    store.save()
    return get_profile()


@router.get("/stats")
def get_stats() -> dict:
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
        if score / len(exam["questions"]) > 0.7:
            passed += 1
    return {
        "exams": finished,
        "passed": passed,
        "topics": [
            {"topic": topic, "pct": round(right / total * 100), "correct": right, "total": total}
            for topic, (right, total) in by_topic.items()
        ],
    }
