import importlib

import pytest
from fastapi.testclient import TestClient

from app.bank import QUOTA_50, load_bank, load_mocks


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("SIM_DB", str(tmp_path / "t.db"))
    monkeypatch.setenv("SIM_ADMIN_TOKEN", "segredo")
    import app.main
    importlib.reload(app.main)
    return TestClient(app.main.app)


def test_bank_and_mocks_are_consistent():
    bank = load_bank()
    mocks = load_mocks(bank)
    assert len(mocks) == 6
    seen = [q for m in mocks for q in m["question_ids"]]
    assert len(seen) == len(set(seen)), "mocks must not share questions"
    for m in mocks:
        counts = {d: 0 for d in QUOTA_50}
        for q in m["question_ids"]:
            counts[bank[q]["domain"]] += 1
        assert counts == QUOTA_50


def test_student_flow_hides_answers_then_grades(client):
    a = client.post("/api/attempts", json={"name": "Ana Silva", "exam_id": "mock-1"}).json()
    assert len(a["questions"]) == 50
    assert all("answer" not in q and "explanation" not in q for q in a["questions"])
    import app.main
    q0, q1 = a["questions"][0], a["questions"][1]
    answers = {q0["id"]: app.main.BANK[q0["id"]]["answer"], q1["id"]: [9]}
    rv = client.post(f"/api/attempts/{a['attempt_id']}/submit", json={"answers": answers}).json()
    assert rv["correct"] == 1 and rv["total"] == 50 and rv["pct"] == 2
    assert sum(d["total"] for d in rv["domains"]) == 50
    first = next(q for q in rv["questions"] if q["id"] == q0["id"])
    assert first["correct"] and first["explanation"] and first["source"]["url"]
    # submitting twice returns the stored result instead of regrading
    again = client.post(f"/api/attempts/{a['attempt_id']}/submit", json={"answers": {}}).json()
    assert again["correct"] == 1


def test_select_two_is_all_or_nothing(client):
    import app.main
    a = client.post("/api/attempts", json={"name": "Rui", "exam_id": "mock-2"}).json()
    multi = next(q for q in a["questions"] if q["type"] == "multi")
    right = app.main.BANK[multi["id"]]["answer"]
    rv = client.post(f"/api/attempts/{a['attempt_id']}/submit", json={"answers": {multi["id"]: right[:1]}}).json()
    assert rv["correct"] == 0


def test_admin_needs_token_and_lists_who_missed(client):
    a = client.post("/api/attempts", json={"name": "Marta", "exam_id": "treino-tai"}).json()
    client.post(f"/api/attempts/{a['attempt_id']}/submit", json={"answers": {}})
    assert client.get("/api/admin/attempts").status_code == 401
    h = {"X-Admin-Token": "segredo"}
    rows = client.get("/api/admin/attempts", headers=h).json()["attempts"]
    assert rows[0]["name"] == "Marta" and rows[0]["pct"] == 0
    stats = client.get("/api/admin/questions", headers=h).json()["questions"]
    assert len(stats) == 20 and all(s["missed_by"] == ["Marta"] for s in stats)
    assert client.get("/api/admin/export.csv?token=segredo").text.startswith("nome,")


def test_random_and_drill_exams(client):
    import app.main
    r = client.post("/api/attempts", json={"name": "Zé", "exam_id": "aleatorio"}).json()
    doms = [app.main.BANK[q["id"]]["domain"] for q in r["questions"]]
    assert {d: doms.count(d) for d in QUOTA_50} == QUOTA_50
    d = client.post("/api/attempts", json={"name": "Zé", "exam_id": "treino-sw"}).json()
    assert len(d["questions"]) == 20 and all(app.main.BANK[q["id"]]["domain"] == "sw" for q in d["questions"])
    assert client.post("/api/attempts", json={"name": "Zé", "exam_id": "nope"}).status_code == 404
