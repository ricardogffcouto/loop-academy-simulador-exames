"""Maintenance tools for the question bank.

    python3 tools/bank_tools.py check            # validate + quality report (answer length bias, positions, counts)
    python3 tools/bank_tools.py apply FIX.json   # merge per-question overrides into the bank files
    python3 tools/bank_tools.py shuffle          # shuffle option order of NEW questions only (marks them "shuffled")
    python3 tools/bank_tools.py mocks            # rebuild data/mocks.json: 6 disjoint mocks of 50 with the exam's domain split
    python3 tools/bank_tools.py links            # check that every source URL answers
"""

import collections
import json
import random
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app.bank import BANK_DIR, DOMAINS, MOCKS_FILE, QUOTA_50, load_bank  # noqa: E402

N_MOCKS = 6


def files():
    return sorted(BANK_DIR.glob("*.json"))


def write(path: Path, questions: list[dict]) -> None:
    lines = ",\n".join(json.dumps(q, ensure_ascii=False) for q in questions)
    path.write_text('{"questions": [\n' + lines + "\n]}\n")


def check() -> None:
    bank = load_bank()  # raises on any schema problem
    qs = list(bank.values())
    by = collections.Counter((q["domain"], q["type"]) for q in qs)
    print(f"{len(qs)} questions")
    for d in DOMAINS:
        n = by[(d, "single")] + by[(d, "multi")]
        print(f"  {d:5} {n:4}  (multi {by[(d, 'multi')]})  need {QUOTA_50[d] * N_MOCKS} for {N_MOCKS} mocks")
    multi = sum(q["type"] == "multi" for q in qs)
    print(f"select-two share: {100 * multi / len(qs):.0f}%")

    singles = [q for q in qs if q["type"] == "single"]
    longest = [q for q in singles if max(range(4), key=lambda i: len(q["options"][i])) == q["answer"][0]]
    much = [q for q in singles
            if len(q["options"][q["answer"][0]]) > 1.25 * max(len(o) for i, o in enumerate(q["options"]) if i != q["answer"][0])]
    print(f"correct option is the longest: {len(longest)}/{len(singles)} ({100 * len(longest) / len(singles):.0f}%, chance = 25%)")
    print(f"correct option >25% longer than every distractor: {len(much)}")
    for q in much:
        print("   ", q["id"])
    pos = collections.Counter(a for q in qs for a in q["answer"])
    print("answer positions:", dict(sorted(pos.items())))
    texts = collections.Counter(q["question"].strip().lower() for q in qs)
    dup = [t for t, n in texts.items() if n > 1]
    if dup:
        print("DUPLICATE STEMS:", dup)


def apply(fix_path: str) -> None:
    fixes = json.loads(Path(fix_path).read_text())
    seen = set()
    for path in files():
        qs = json.loads(path.read_text())["questions"]
        for q in qs:
            if q["id"] in fixes:
                fix = dict(fixes[q["id"]])
                for i, text in fix.pop("opt", {}).items():  # replace single options by index
                    q["options"][int(i)] = text
                q.update(fix)
                seen.add(q["id"])
        write(path, qs)
    missing = set(fixes) - seen
    if missing:
        raise SystemExit(f"unknown ids in fix file: {sorted(missing)}")
    load_bank()
    print(f"applied {len(seen)} fixes")


def shuffle() -> None:
    for path in files():
        qs = json.loads(path.read_text())["questions"]
        for q in qs:
            if q.get("shuffled"):  # never reorder a live question: attempts store answers as option positions
                continue
            q["shuffled"] = True
            rng = random.Random(f"shuffle:{q['id']}")
            order = list(range(len(q["options"])))
            rng.shuffle(order)
            q["options"] = [q["options"][i] for i in order]
            q["answer"] = sorted(order.index(a) for a in q["answer"])
        write(path, qs)
    print("shuffled")


def mocks() -> None:
    """Deal each domain's questions round-robin over the mocks, sorted by topic, so every mock
    gets the same domain split, a spread of topics and a similar number of select-two items."""
    bank = load_bank()
    rng = random.Random("mocks-v1")
    decks: list[list[str]] = [[] for _ in range(N_MOCKS)]
    multi_count = [0] * N_MOCKS
    for d, quota in QUOTA_50.items():
        pool = sorted((q for q in bank.values() if q["domain"] == d), key=lambda q: (q["type"], q["topic"], q["id"]))
        if len(pool) < quota * N_MOCKS:
            raise SystemExit(f"{d}: {len(pool)} questions, need {quota * N_MOCKS}")
        taken = [0] * N_MOCKS
        for i, q in enumerate(pool[: quota * N_MOCKS]):
            open_decks = [m for m in range(N_MOCKS) if taken[m] < quota]
            if q["type"] == "multi":  # select-two items go to the mock that has fewest so far
                m = min(open_decks, key=lambda m: (multi_count[m], taken[m]))
                multi_count[m] += 1
            else:  # singles are sorted by topic, so dealing in turn spreads the topics
                m = min(open_decks, key=lambda m: (taken[m], (m - i) % N_MOCKS))
            decks[m].append(q["id"])
            taken[m] += 1
    out = []
    for i, ids in enumerate(decks, 1):
        rng.shuffle(ids)
        out.append({"id": f"mock-{i}", "title": f"Simulado {i}", "question_ids": ids})
    MOCKS_FILE.write_text(json.dumps({"mocks": out}, indent=1) + "\n")
    for m in out:
        dom = collections.Counter(bank[q]["domain"] for q in m["question_ids"])
        multi = sum(bank[q]["type"] == "multi" for q in m["question_ids"])
        print(m["id"], dict(dom), "multi", multi)


def links() -> None:
    bank = load_bank()
    urls = sorted({q["source"]["url"] for q in bank.values()})

    def probe(url):
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (link check)"})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return url, r.status
        except Exception as e:  # noqa: BLE001 - report every failure kind
            return url, getattr(e, "code", None) or type(e).__name__

    with ThreadPoolExecutor(16) as ex:
        results = list(ex.map(probe, urls))
    bad = [(u, s) for u, s in results if s != 200]
    print(f"{len(urls)} urls, {len(bad)} not 200")
    for u, s in bad:
        ids = [q["id"] for q in bank.values() if q["source"]["url"] == u]
        print(f"  {s}  {u}  {ids}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    {"check": check, "shuffle": shuffle, "mocks": mocks, "links": links}.get(cmd, lambda: apply(sys.argv[2]))() \
        if cmd != "apply" else apply(sys.argv[2])
