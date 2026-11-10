"""Grupo 4 · Ranking e exportação."""

from pathlib import Path

import pytest

from tests.helpers import take_exam


def test_ranking_shows_submitted_exam(client):
    take_exam(client, "Arquitetura Transformer", name="Rui")
    rows = client.get("/api/ranking").json()
    assert rows[0]["name"] == "Rui"
    assert rows[0]["pct"] == 100


def test_add_entry_by_hand(client):
    assert client.post("/api/ranking", json={"name": "Ana", "pct": 80}).status_code == 200
    assert client.get("/api/ranking").json()[0]["pct"] == 80


def test_export_csv(client):
    take_exam(client, "Arquitetura Transformer", name="Rui")
    lines = client.get("/api/export.csv").text.strip().splitlines()
    assert lines[0] == "exam,name,score,total,passed"
    assert len(lines) == 2


# ---------- Ticket G4-A · Pydantic ----------


def test_pct_above_100_is_422(client):
    assert client.post("/api/ranking", json={"name": "Ana", "pct": 150}).status_code == 422


def test_name_with_html_is_422(client):
    r = client.post("/api/ranking", json={"name": "<img src=x onerror=alert(1)>", "pct": 50})
    assert r.status_code == 422


def test_missing_pct_is_422(client):
    assert client.post("/api/ranking", json={"name": "Ana"}).status_code == 422


# ---------- Ticket G4-B · erros HTTP e exportação ----------


def test_clear_with_wrong_password_is_401(client):
    assert client.delete("/api/ranking", params={"pwd": "errada"}).status_code == 401


def test_csv_passed_uses_pass_mark(client):
    take_exam(client, "Arquitetura Transformer", name="Rui")
    assert client.get("/api/export.csv").text.strip().splitlines()[1].endswith("True")

def test_requirements_include_yaml():
    requirements = (Path(__file__).parent.parent / "requirements.txt").read_text().lower()
    assert "pyyaml" in requirements
