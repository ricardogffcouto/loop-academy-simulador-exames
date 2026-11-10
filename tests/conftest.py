import copy

import pytest
from fastapi.testclient import TestClient

from app import store
from main import app

ORIGINAL_QUESTIONS = copy.deepcopy(store.questions)


@pytest.fixture(autouse=True)
def clean_store(tmp_path, monkeypatch):
    """Cada teste começa com o banco original e sem exames, ranking ou perfil."""
    monkeypatch.setattr(store, "DB_FILE", tmp_path / "db.json")
    store.questions.clear()
    store.questions.update(copy.deepcopy(ORIGINAL_QUESTIONS))
    store.custom_questions.clear()
    store.exams.clear()
    store.results.clear()
    store.profile.clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def new_question() -> dict:
    return {
        "id": "teste-001",
        "topic": "Python",
        "text": "Qual é o resultado de 2 + 2?",
        "options": ["3", "4", "5"],
        "correct": [1],
        "type": "single",
    }
