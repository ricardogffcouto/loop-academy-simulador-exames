"""Estado da aplicação: tudo em memória, gravado em db.json.

Zona partilhada por todos os grupos: mudar alguma coisa aqui é combinar primeiro.
"""

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_FILE = BASE_DIR / "db.json"

ADMIN_PASSWORD = "admin123"  # TODO: tirar do código
PASS_MARK = 70  # nota mínima para passar, em %

questions: dict[str, dict] = {}  # id -> pergunta
custom_questions: list[dict] = []  # perguntas criadas ou importadas na app
exams: dict[str, dict] = {}  # id -> exame
results: list[dict] = []  # entradas do ranking
profile: dict = {}


def load_questions() -> None:
    """Carrega os bancos de perguntas da pasta data/."""
    for path in sorted(DATA_DIR.glob("*.json")):
        try:
            for question in json.loads(path.read_text(encoding="utf-8"))["questions"]:
                questions[question["id"]] = question
        except (OSError, ValueError, KeyError) as error:
            print(f"Não consegui ler {path.name}: {error}")


def load() -> None:
    """Carrega o estado gravado em db.json, se existir."""
    if not DB_FILE.exists():
        return
    try:
        state = json.loads(DB_FILE.read_text(encoding="utf-8"))
    except ValueError as error:
        print(f"db.json inválido, a ignorar: {error}")
        return
    exams.update(state.get("exams", {}))
    results.extend(state.get("results", []))
    profile.update(state.get("profile", {}))
    for question in state.get("custom_questions", []):
        custom_questions.append(question)
        questions[question["id"]] = question


def save() -> None:
    """Grava o estado em db.json."""
    state = {
        "exams": exams,
        "results": results,
        "profile": profile,
        "custom_questions": custom_questions,
    }
    DB_FILE.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")


def topics() -> list[str]:
    """Tópicos existentes no banco, sem repetições."""
    return sorted({question["topic"] for question in questions.values()})
