"""Funções de apoio aos testes."""

from fastapi.testclient import TestClient

from app import store


def take_exam(client: TestClient, topic: str, right: bool = True, name: str = "Ana") -> dict:
    """Cria um exame com todas as perguntas de um tópico e entrega-o (tudo certo ou tudo errado)."""
    count = sum(1 for q in store.questions.values() if q["topic"] == topic)
    exam = client.post("/api/exam", json={"num": count, "minutes": 15, "topics": [topic]}).json()
    answers = {}
    for q in exam["questions"]:
        if q["type"] == "truefalse":
            right_choice = [0 if q["correct"] else 1]
        else:
            right_choice = q["correct"]
        answers[q["id"]] = right_choice if right else [9]
    result = client.post(f"/api/exam/{exam['id']}/submit", json={"answers": answers, "name": name})
    return {"exam": exam, "result": result}
