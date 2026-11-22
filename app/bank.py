"""Question bank: loading, validation and exam definitions."""

import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BANK_DIR = ROOT / "data" / "bank"
MOCKS_FILE = ROOT / "data" / "mocks.json"

# Official NCA-GENL domains and weights (nvidia.com, Nov 2026).
DOMAINS = {
    "core": ("Core Machine Learning and AI Knowledge", 0.30),
    "sw": ("Software Development", 0.24),
    "exp": ("Experimentation", 0.22),
    "da": ("Data Analysis and Visualization", 0.14),
    "tai": ("Trustworthy AI", 0.10),
}
# A 50-question exam split by those weights.
QUOTA_50 = {"core": 15, "sw": 12, "exp": 11, "da": 7, "tai": 5}

EXAM_MINUTES = 60
DRILL_SIZE = 20
DRILL_MINUTES = 24


class BankError(ValueError):
    pass


def validate(q: dict, where: str) -> None:
    required = ["id", "domain", "topic", "type", "question", "options", "answer", "explanation", "source"]
    missing = [k for k in required if k not in q]
    if missing:
        raise BankError(f"{where}: missing {missing}")
    if q["domain"] not in DOMAINS:
        raise BankError(f"{where}: unknown domain {q['domain']}")
    n = len(q["options"])
    if q["type"] == "single":
        if n != 4 or len(q["answer"]) != 1:
            raise BankError(f"{where}: single needs 4 options and 1 answer")
    elif q["type"] == "multi":
        if n != 5 or len(q["answer"]) != 2:
            raise BankError(f"{where}: multi needs 5 options and 2 answers")
        if "(Select two.)" not in q["question"]:
            raise BankError(f"{where}: multi stem must say (Select two.)")
    else:
        raise BankError(f"{where}: unknown type {q['type']}")
    if len(set(q["options"])) != n:
        raise BankError(f"{where}: duplicate options")
    if any(not 0 <= a < n for a in q["answer"]) or len(set(q["answer"])) != len(q["answer"]):
        raise BankError(f"{where}: bad answer indices")
    src = q["source"]
    if not (isinstance(src, dict) and src.get("url", "").startswith("http") and src.get("title")):
        raise BankError(f"{where}: source needs title and url")


def load_bank() -> dict[str, dict]:
    bank: dict[str, dict] = {}
    for path in sorted(BANK_DIR.glob("*.json")):
        for i, q in enumerate(json.loads(path.read_text())["questions"]):
            where = f"{path.name}#{i} ({q.get('id')})"
            validate(q, where)
            if q["id"] in bank:
                raise BankError(f"{where}: duplicate id")
            bank[q["id"]] = q
    return bank


def load_mocks(bank: dict[str, dict]) -> list[dict]:
    if not MOCKS_FILE.exists():
        return []
    mocks = json.loads(MOCKS_FILE.read_text())["mocks"]
    for m in mocks:
        unknown = [qid for qid in m["question_ids"] if qid not in bank]
        if unknown:
            raise BankError(f"{m['id']}: unknown questions {unknown}")
    return mocks


def by_domain(bank: dict[str, dict]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {d: [] for d in DOMAINS}
    for qid, q in bank.items():
        groups[q["domain"]].append(qid)
    return groups


def random_exam(bank: dict[str, dict], rng: random.Random) -> list[str]:
    groups = by_domain(bank)
    ids: list[str] = []
    for d, n in QUOTA_50.items():
        ids += rng.sample(groups[d], min(n, len(groups[d])))
    rng.shuffle(ids)
    return ids


def drill_exam(bank: dict[str, dict], domain: str, rng: random.Random) -> list[str]:
    pool = by_domain(bank)[domain]
    return rng.sample(pool, min(DRILL_SIZE, len(pool)))


def exam_catalog(bank: dict[str, dict], mocks: list[dict]) -> list[dict]:
    """Every exam a student can start: the fixed mocks, a random mock and one drill per domain."""
    exams = [
        {"id": m["id"], "title": m["title"], "kind": "mock", "n": len(m["question_ids"]), "minutes": EXAM_MINUTES}
        for m in mocks
    ]
    exams.append({"id": "aleatorio", "title": "Simulado aleatório", "kind": "random", "n": sum(QUOTA_50.values()),
                  "minutes": EXAM_MINUTES})
    counts = {d: len(v) for d, v in by_domain(bank).items()}
    for d, (name, _) in DOMAINS.items():
        exams.append({"id": f"treino-{d}", "title": f"Treino · {name}", "kind": "drill", "domain": d,
                      "n": min(DRILL_SIZE, counts[d]), "minutes": DRILL_MINUTES, "pool": counts[d]})
    return exams


def pick_questions(exam_id: str, bank: dict[str, dict], mocks: list[dict]) -> tuple[str, list[str], int] | None:
    """(title, question ids, time limit in seconds) for an exam id, or None if unknown."""
    rng = random.Random()
    for m in mocks:
        if m["id"] == exam_id:
            return m["title"], list(m["question_ids"]), EXAM_MINUTES * 60
    if exam_id == "aleatorio":
        return "Simulado aleatório", random_exam(bank, rng), EXAM_MINUTES * 60
    if exam_id.startswith("treino-") and exam_id[7:] in DOMAINS:
        d = exam_id[7:]
        return f"Treino · {DOMAINS[d][0]}", drill_exam(bank, d, rng), DRILL_MINUTES * 60
    return None


def is_correct(q: dict, chosen: list[int] | None) -> bool:
    # All-or-nothing, as on the real exam: a "select two" question needs both right picks.
    return chosen is not None and sorted(chosen) == sorted(q["answer"])
