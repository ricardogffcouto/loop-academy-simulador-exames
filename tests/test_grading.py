"""Grupo 3 · Correção."""

import pytest

from app.grading import is_correct
from tests.helpers import take_exam

SINGLE = {"type": "single", "correct": [2]}
MULTIPLE = {"type": "multiple", "correct": [0, 3]}
TRUE = {"type": "truefalse", "correct": True}
FALSE = {"type": "truefalse", "correct": False}


def test_single_right_and_wrong():
    assert is_correct(SINGLE, [2])
    assert not is_correct(SINGLE, [1])
    assert not is_correct(SINGLE, [])


def test_multiple_order_does_not_matter():
    assert is_correct(MULTIPLE, [3, 0])
    assert not is_correct(MULTIPLE, [0])


def test_submit_all_right(client):
    result = take_exam(client, "Arquitetura Transformer")["result"].json()
    assert result["pct"] == 100
    assert result["passed"]


# ---------- Ticket G3-A · uma regra de correção (+ Pydantic) ----------


@pytest.mark.xfail(strict=True, reason="G3-A: Verdadeiro (0) numa pergunta verdadeira é certo")
def test_true_false_true():
    assert is_correct(TRUE, [0])
    assert not is_correct(TRUE, [1])


@pytest.mark.xfail(strict=True, reason="G3-A: Falso (opção 1) numa pergunta falsa está certo")
def test_true_false_false():
    assert is_correct(FALSE, [1])


@pytest.mark.xfail(strict=True, reason="G3-A: as respostas são listas de índices")
def test_answers_must_be_lists(client):
    exam = client.post("/api/exam", json={"num": 2}).json()
    qid = exam["questions"][0]["id"]
    r = client.post(f"/api/exam/{exam['id']}/submit", json={"answers": {qid: "A"}})
    assert r.status_code == 422


# ---------- Ticket G3-B · erros HTTP ----------


@pytest.mark.xfail(strict=True, reason="G3-B: entregar um exame que não existe é 404")
def test_submit_unknown_exam_is_404(client):
    assert client.post("/api/exam/nao-existe/submit", json={"answers": {}}).status_code == 404


@pytest.mark.xfail(strict=True, reason="G3-B: entregar o mesmo exame duas vezes é 409")
def test_submit_twice_is_409(client):
    exam = client.post("/api/exam", json={"num": 2}).json()
    client.post(f"/api/exam/{exam['id']}/submit", json={"answers": {}})
    assert client.post(f"/api/exam/{exam['id']}/submit", json={"answers": {}}).status_code == 409
