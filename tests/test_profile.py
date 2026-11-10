"""Grupo 5 · Perfil e estatísticas."""

from datetime import date, timedelta

import pytest

from app import store

IN_30_DAYS = (date.today() + timedelta(days=30)).isoformat()


def test_save_profile_and_countdown(client):
    r = client.post("/api/profile", json={"name": "Ana", "certification": "NCA-GENL", "exam_date": IN_30_DAYS})
    assert r.status_code == 200
    assert client.get("/api/profile").json()["days_left"] == 30


def test_stats_count_exams(client):
    client.post(
        "/api/exam/" + client.post("/api/exam", json={"num": 2}).json()["id"] + "/submit",
        json={"answers": {}},
    )
    assert client.get("/api/stats").json()["exams"] == 1


def exam_with_score(right: int, total: int) -> None:
    """Põe no store um exame entregue com `right` certas em `total` (só escolha única)."""
    singles = [q for q in store.questions.values() if q["type"] == "single"][:total]
    answers = {q["id"]: q["correct"] if i < right else [9] for i, q in enumerate(singles)}
    store.exams["x"] = {
        "id": "x",
        "questions": [q["id"] for q in singles],
        "answers": answers,
        "start": 0,
        "minutes": 10,
    }


# ---------- Ticket G5-A · Pydantic ----------


def test_far_future_date_is_422(client):
    r = client.post("/api/profile", json={"name": "Ana", "certification": "X", "exam_date": "3026-01-01"})
    assert r.status_code == 422


def test_past_date_is_422(client):
    r = client.post("/api/profile", json={"name": "Ana", "certification": "X", "exam_date": "2020-01-01"})
    assert r.status_code == 422


def test_text_date_is_422(client):
    r = client.post("/api/profile", json={"name": "Ana", "certification": "X", "exam_date": "amanhã"})
    assert r.status_code == 422


# ---------- Ticket G5-B · estatísticas ----------


@pytest.mark.xfail(strict=True, reason="G5-B: 70% é aprovado (como no resultado do exame)")
def test_stats_70_percent_is_passed(client):
    exam_with_score(7, 10)
    assert client.get("/api/stats").json()["passed"] == 1


@pytest.mark.xfail(strict=True, reason="G5-B: a nota mínima vem de store.PASS_MARK, não de um número escrito à mão")
def test_stats_use_pass_mark(client, monkeypatch):
    monkeypatch.setattr(store, "PASS_MARK", 50)
    exam_with_score(6, 10)
    assert client.get("/api/stats").json()["passed"] == 1


@pytest.mark.xfail(strict=True, reason="G5-B: um perfil estragado no db.json não pode dar 500 a toda a gente")
def test_broken_saved_profile_is_not_500(client):
    store.profile.update({"name": "Ana", "exam_date": "amanhã"})
    assert client.get("/api/profile").status_code == 200
