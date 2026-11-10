"""Grupo 2 · Exames."""

import pytest

from app import exams


def test_create_exam(client):
    r = client.post("/api/exam", json={"num": 5, "minutes": 10})
    assert r.status_code == 200
    assert len(r.json()["questions"]) == 5
    assert r.json()["minutes"] == 10


def test_create_exam_by_topic(client):
    r = client.post("/api/exam", json={"num": 3, "minutes": 10, "topics": ["Git"]})
    assert {q["topic"] for q in r.json()["questions"]} == {"Git"}


def test_open_exam_again(client):
    exam_id = client.post("/api/exam", json={"num": 3}).json()["id"]
    assert client.get(f"/api/exam/{exam_id}").json()["id"] == exam_id


# ---------- Ticket G2-A · Pydantic ----------


#@pytest.mark.xfail(strict=True, reason="G2-A: um exame de 0 minutos não faz sentido")
def test_zero_minutes_is_422(client):
    assert client.post("/api/exam", json={"num": 5, "minutes": 0}).status_code == 422


#@pytest.mark.xfail(strict=True, reason="G2-A: número de perguntas negativo não faz sentido")
def test_negative_count_is_422(client):
    assert client.post("/api/exam", json={"num": -3, "minutes": 10}).status_code == 422


#@pytest.mark.xfail(strict=True, reason="G2-A: num tem de ser um número")
def test_count_must_be_a_number(client):
    assert client.post("/api/exam", json={"num": "abc", "minutes": 10}).status_code == 422


# ---------- Ticket G2-B · erros HTTP ----------


#@pytest.mark.xfail(strict=True, reason="G2-B: exame que não existe é 404, não 500")
def test_unknown_exam_is_404(client):
    assert client.get("/api/exam/nao-existe").status_code == 404


#@pytest.mark.xfail(strict=True, reason="G2-B: perguntas a mais é 400 com mensagem")
def test_too_many_questions_is_400(client):
    r = client.post("/api/exam", json={"num": 50, "minutes": 10, "topics": ["Git"]})
    assert r.status_code == 400
    assert "Git" in r.json()["detail"]


#@pytest.mark.xfail(strict=True, reason="G2-B: pick_questions não pode alterar o seu argumento por omissão")
def test_pick_questions_keeps_its_default():
    exams.pick_questions(1)
    default = exams.pick_questions.__defaults__[0]
    assert not default  # continua vazio (ou None) depois de ser usado
