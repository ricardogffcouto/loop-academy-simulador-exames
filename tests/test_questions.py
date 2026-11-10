"""Grupo 1 · Banco de perguntas."""

import pytest

ADMIN = {"pwd": "admin123"}


def test_list_topics(client):
    r = client.get("/api/topics")
    assert r.status_code == 200
    assert "Git" in r.json()


def test_filter_by_topic(client):
    r = client.get("/api/questions", params={"topic": "Git"})
    assert r.status_code == 200
    assert {q["topic"] for q in r.json()} == {"Git"}


def test_create_question(client, new_question):
    r = client.post("/api/questions", params=ADMIN, json=new_question)
    assert r.status_code in (200, 201)
    assert client.get("/api/questions/teste-001").json()["text"] == new_question["text"]


def test_upload_csv(client):
    csv = (
        "id,topic,text,option_a,option_b,correct,explanation\nc-1,Docker,O que é uma imagem?,Um template,Um volume,A,\n"
    )
    r = client.post("/api/upload", files={"file": ("banco.csv", csv, "text/csv")})
    assert r.json()["added"] == 1


# ---------- Ticket G1-A · Pydantic ----------


def test_correct_out_of_range_is_422(client, new_question):
    new_question["correct"] = [7]
    assert client.post("/api/questions", params=ADMIN, json=new_question).status_code == 422


def test_correct_must_be_a_list(client, new_question):
    new_question["correct"] = 2
    assert client.post("/api/questions", params=ADMIN, json=new_question).status_code == 422


def test_needs_two_options(client, new_question):
    new_question["options"] = ["4"]
    new_question["correct"] = [0]
    assert client.post("/api/questions", params=ADMIN, json=new_question).status_code == 422


# ---------- Ticket G1-B · erros HTTP ----------


@pytest.mark.xfail(strict=True, reason="G1-B: pergunta que não existe é 404, não 500")
def test_unknown_question_is_404(client):
    assert client.get("/api/questions/nao-existe").status_code == 404


@pytest.mark.xfail(strict=True, reason="G1-B: ?topic=git tem de encontrar as perguntas de Git")
def test_topic_filter_ignores_case(client):
    assert len(client.get("/api/questions", params={"topic": "git"}).json()) > 0


@pytest.mark.xfail(strict=True, reason="G1-B: criar com um id que já existe é 409, não sobrescrever")
def test_duplicate_id_is_409(client, new_question):
    client.post("/api/questions", params=ADMIN, json=new_question)
    assert client.post("/api/questions", params=ADMIN, json=new_question).status_code == 409
