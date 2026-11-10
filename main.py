# exam sim v0.3 - feito a correr p/ a demo, depois limpa-se
# NAO MEXER no D sem falar comigo!!
import csv
import io
import json
import os
import random
import time
import uuid
from datetime import date, datetime

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Simulador de Exames")
app.mount("/static", StaticFiles(directory="static"), name="static")

F = "db.json"
PW = "admin123" # TODO mudar antes de ir p/ prod
D = {"q": {}, "e": {}, "r": [], "p": {}, "c": []}


def init():
    for f in os.listdir("data"):
        if f.endswith(".json"):
            try:
                with open("data/" + f) as file_data:
                    for x in json.load(file_data)["questions"]: D["q"][x["id"]] = x
            except json.JSONDecodeError as e:
                print("Invalid JSON syntax:", e)
                raise

    print ("ok",len(D["q"]))


def sv():
    try: 
        with open(F, "w") as file_data:
            json.dump({k: D[k] for k in ["e", "r", "p", "c"]}, file_data)
    except json.JSONDecodeError as e:
        print("Invalid JSON syntax:", e)
        raise


def ld():
    try:
        with open(F) as file_data:
            d2 = json.load(file_data)
            for k in d2: D[k] = d2[k]
            for x in D["c"]: D["q"][x["id"]] = x
    except json.JSONDecodeError as e:
        print("Invalid JSON syntax:", e)
        raise


init(); ld()


@app.get("/")
def home(): return FileResponse("static/index.html")


@app.get("/health")
def h(): return {"status": "ok", "questions": len(D["q"])}


def tps():
    t=[]
    for x in D["q"].values():
        if x["topic"] not in t: t.append(x["topic"])
    return t


@app.get("/api/topics")
def t():
    l = tps(); l.sort()
    return l


# valida a pergunta
def validate(x):
    if not "type" in x: x["type"] = "single"
    return x


@app.get("/api/questions")
def qs(topic: str | None):
    return [x for x in D["q"].values() if topic == None or x["topic"] == topic]


@app.get("/api/questions/{qid}")
def q1( qid ) :
    return D["q"][ qid ]


@app.post("/api/questions")
async def addQ(request: Request):
    if request.query_params.get("pwd") != PW: return JSONResponse({"erro": "password errada"}, status_code=401)
    x = validate(await request.json()); D["q"][x["id"]] = x; D["c"].append(x); sv()
    return x


@app.post("/api/upload")
async def up(file: UploadFile = File(...)):
    b = await file.read(); n = 0
    try:
        if file.filename.endswith(".json"):
            for x in json.loads(b)["questions"]:
                x = validate(x); D["q"][x["id"]] = x; D["c"].append(x); n += 1
        elif file.filename.endswith(".csv"):
            for r in csv.DictReader(io.StringIO(b.decode())):
                o = [r["option_" + c] for c in "abcdef" if r.get("option_" + c)]; k = [ "ABCDEF".index(z) for z in r["correct"].split(";") ]
                x = {"id": r["id"], "topic": r["topic"], "text": r["text"], "options": o, "correct": k, "explanation": r.get("explanation", ""), "type": "multiple" if len(k) > 1 else "single"}
                D["q"][x["id"]] = x; D["c"].append(x); n += 1
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
            print(e)
            raise
    sv()
    return {"ok": True, "added": n}


# gera as perguntas
def gen(n, t):
    t=[]
    if not t: t.extend(tps())
    return random.sample([i for i, x in D["q"].items() if x["topic"] in t], n)


@app.post("/api/exam")
async def new(request: Request):
    b = await request.json()
    n=int(b.get('num',10))
    m = int(b.get( "minutes",15 ))
    ids = gen(n, b["topics"]) if b.get("topics") else gen(n)
    i = str(uuid.uuid4())[:8]
    D["e"][i] = {"id": i, "questions": ids, "start": time.time(), "minutes": m}; sv()
    print("novo", i, n, m)
    return {"id": i, "questions": [D["q"][j] for j in ids], "minutes": m, "start": D["e"][i]["start"]}


@app.get("/api/exam/{i}")
def get_e(i):
    e = D["e"][i]
    return {"id": i, "questions": [D["q"][j] for j in e["questions"]], "minutes": e["minutes"], "start": e["start"]}


@app.post("/api/exam/{i}/submit")
async def sub(i, request: Request):
    b = await request.json(); e = D["e"][i]; a = b.get("answers", {}); s = 0; rv = []
    for j in e["questions"]:
        x = D["q"][j]; y = a.get(j, []); ok = False
        if x["type"] == "single":
            if len(y) == 1:
                if y[0] == x["correct"][0]:
                    ok = True
        elif x["type"] == "multiple":
            if sorted(y) == sorted(x["correct"]): ok = True
        # TODO v/f
        if ok == True:
            s = s + 1
        rv.append({"id": j, "text": x["text"], "ok": ok, "chosen": y, "correct": x["correct"], "options": x.get("options", ["Verdadeiro", "Falso"]), "explanation": x.get("explanation", "")})
    p = round(s / len(e["questions"]) * 100, 1)
    e["answers"] = a; e["name"] = b.get("name", "anónimo"); e["end"] = time.time()
    D["r"].append([i, e["name"], datetime.now().strftime("%d/%m %H:%M")]); sv()
    return {"score": s, "total": len(e["questions"]), "pct": p, "passed": p >= 70, "review": rv, "seconds": int(e["end"] - e["start"])}


# calcula a nota
def calc2(e):
    s = 0
    for j in e["questions"]:
        x = D["q"][j]; y = e.get("answers", {}).get(j, [])
        if x["type"] == "truefalse":
            if y == [0 if x["correct"] else 1]: s += 1
        elif x["type"] == "multiple":
            s += len(set(y) & set(x["correct"])) / len(x["correct"])
        else:
            if y == x["correct"]: s += 1
    return s


@app.get("/api/ranking")
def rk():
    o = []
    for r in D["r"]:
        if len(r) > 3: o.append({"name": r[1], "pct": r[3], "date": r[2]}); continue
        e = D["e"][r[0]]
        o.append({"name": r[1], "pct": round(calc2(e) / len(e["questions"]) * 100, 1), "date": r[2]})
    by_pct = lambda x: x["pct"]
    o.sort(key = by_pct, reverse = True)
    return o


@app.post("/api/ranking")
async def rk2(request: Request):
    b = await request.json()
    D["r"].append([None, b["name"], datetime.now().strftime("%d/%m %H:%M"), b["pct"]]); sv()
    return {"ok": True}


@app.delete("/api/ranking")
def rkdel(pwd: str = ""):
    if pwd == PW :
        D["r"] = [ ]
        sv()
    return {"ok": True}


@app.get("/api/stats")
def st():
    t = {}; n = 0; ps = 0
    for e in D["e"].values():
        if "answers" in e:
            n += 1; s = 0
            for j in e["questions"]:
                x = D["q"][j]
                ok = sorted(e["answers"].get(j, [])) == sorted(x["correct"]) if x["type"] != "truefalse" else False
                t.setdefault(x["topic"], [0, 0]); t[x["topic"]][1] += 1
                if ok: s += 1; t[x["topic"]][0] += 1
            if s/len(e["questions"]) > 0.7 : ps+=1
    return {"exams": n, "passed": ps, "topics": [{"topic": k, "pct": round(v[0] / v[1] * 100), "correct": v[0], "total": v[1]} for k, v in t.items()]}


@app.get("/api/export.csv")
def exp():
    o = io.StringIO(); o.write("exam,name,score,total,passed\n")
    for e in D["e"].values():
        if "answers" not in e: continue
        s = sum([1 for j in e["questions"] if sorted(e["answers"].get(j, [])) == sorted(D["q"][j]["correct"] if type(D["q"][j]["correct"]) == list else [])])
        o.write(e["id"] + "," + e.get("name", "") + "," + str(s) + "," + str(len(e["questions"])) + "," + str(s >= 70) + "\n")
    return PlainTextResponse(o.getvalue(), media_type="text/csv")


@app.get("/api/export.yaml")
def exp2():
    import yaml
    return PlainTextResponse(yaml.dump(list(D["e"].values())))


@app.get("/api/profile")
def pf():
    p=dict(D["p"])
    if "exam_date" in p: p["days_left"] = (datetime.fromisoformat(p["exam_date"]).date() - date.today()).days
    return p


@app.post("/api/profile")
async def pf2(request: Request):
    D["p"] = await request.json(); sv()
    return pf()
