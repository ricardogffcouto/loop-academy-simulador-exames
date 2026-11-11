"""Grupo 3 · Correção."""

import pytest
from abc import ABC, abstractmethod

from tests.helpers import take_exam

class Question(ABC):
    def __init__(self, correct):
        self.correct = correct

    @abstractmethod
    def is_correct(self, chosen: list[int]) -> bool:
        pass

class SingleQuestion(Question):
    def is_correct(self, chosen: list[int]) -> bool:
        return len(chosen) == 1 and chosen[0] == self.correct[0]


class MultipleQuestion(Question):
    def is_correct(self, chosen: list[int]) -> bool:
        return sorted(chosen) == sorted(self.correct)


class TrueFalseQuestion(Question):
    def is_correct(self, chosen: list[int]) -> bool:
        expected = 0 if self.correct else 1
        return len(chosen) == 1 and chosen[0] == expected
    

def test_single_right_and_wrong():
    assert SingleQuestion([2]).is_correct([2])
    assert not SingleQuestion([2]).is_correct([1])
    assert not SingleQuestion([2]).is_correct([])


def test_multiple_order_does_not_matter():
    assert MultipleQuestion([0, 3]).is_correct([3, 0])
    assert not MultipleQuestion([0, 3]).is_correct([0])


def test_submit_all_right(client):
    result = take_exam(client, "Arquitetura Transformer")["result"].json()
    assert result["pct"] == 100
    assert result["passed"]


# ---------- Ticket G3-A · uma regra de correção (+ Pydantic) ----------


def test_true_false_true_question():
    assert TrueFalseQuestion(True).is_correct([0])
    assert not TrueFalseQuestion(True).is_correct([1])


def test_true_false_false_question():
    assert TrueFalseQuestion(False).is_correct([1])
    assert not TrueFalseQuestion(False).is_correct([0])

def test_answers_must_be_lists(client):
    exam = client.post("/api/exam", json={"num": 2}).json()
    qid = exam["questions"][0]["id"]
    r = client.post(f"/api/exam/{exam['id']}/submit", json={"answers": {qid: "A"}})
    assert r.status_code == 422


# ---------- Ticket G3-B · erros HTTP ----------


def test_submit_unknown_exam_is_404(client):
    assert client.post("/api/exam/nao-existe/submit", json={"answers": {}}).status_code == 404


def test_submit_twice_is_409(client):
    exam = client.post("/api/exam", json={"num": 2}).json()
    client.post(f"/api/exam/{exam['id']}/submit", json={"answers": {}})
    assert client.post(f"/api/exam/{exam['id']}/submit", json={"answers": {}}).status_code == 409
