# exam sim v0.3 - feito a correr p/ a demo, depois limpa-se
# NAO MEXER no app_state sem falar comigo!!
import csv
import io
import json
import os
import random
import time
import uuid
from datetime import date, datetime
from typing import Annotated

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

#import math
#import re
#import sys

app = FastAPI(title="Simulador de Exames")
app.mount("/static", StaticFiles(directory="static"), name="static")

DATABASE_PATH = "db.json"
PW = "admin123" # TODO mudar antes de ir p/ prod
app_state = {"q": {}, "e": {}, "r": [], "p": {}, "c": []}

def __init__():
    '''this is a docstring'''
    for f in os.listdir("data"):
        if f.endswith(".json"):
            try:
                with open("data/" + f) as file:
                    questions = json.load(file).get("questions", [])
                for x in questions: 
                    app_state["q"][x["id"]] = x
            except (OSError, json.JSONDecodeError, KeyError) as e:
                print(f"Could not load {f}: {e}")
    print ("ok", len(app_state["q"]))


def save_database_state():
    '''save the current state of the database to a JSON file'''
    try: 
        with open(DATABASE_PATH, "w") as file:
            json.dump({k: app_state[k] for k in ["e", "r", "p", "c"]}, file)
    except (OSError, json.JSONDecodeError, KeyError) as e:
        print("erro", e)


def load_database_state():
    '''load the state of the database from a JSON file'''
    try:
        with open(DATABASE_PATH) as file:
            d2 = json.load(file)
        for k in d2: app_state[k] = d2[k]
        for x in app_state["c"]: app_state["q"][x["id"]] = x
    except (OSError, json.JSONDecodeError, KeyError) as e:
        print(f"Could not load {DATABASE_PATH}: {e}")


__init__(); load_database_state()


@app.get("/")
def home(): 
    '''serve the main index.html file for the root endpoint'''
    return FileResponse("static/index.html")


@app.get("/health")
def api_check(): 
    '''check the health of the API'''
    return {"status": "ok", "questions": len(app_state["q"])}


def questions_topics() -> list:
    '''returns a list of unique topics from the questions in the database'''
    t=[]
    for x in app_state["q"].values():
        if x["topic"] not in t: t.append(x["topic"])
    return t


@app.get("/api/topics")
def t():
    '''returns a sorted list of unique topics from the questions in the database'''
    l = questions_topics(); l.sort()
    return l


# valida a pergunta
def validate(x):
    '''Function to validate a question dictionary. Ensures required fields are present and sets default values.'''
    if not "type" in x: x["type"] = "single"
    return x


@app.get("/api/questions")
def qs(topic: str | None):
    '''returns a list of questions filtered by topic'''
    return [x for x in app_state["q"].values() if topic == None or x["topic"] == topic]


@app.get("/api/questions/{qid}")
def q1( qid ) :
    '''returns a specific question by its ID'''
    return app_state["q"][ qid ]


@app.post("/api/questions")
async def addQ(request: Request):
    '''adds a new question to the database after validating the provided password'''
    if request.query_params.get("pwd") != PW: 
        return JSONResponse({"erro": "password errada"}, status_code=401)
    x = validate(await request.json()); app_state["q"][x["id"]] = x; app_state["c"].append(x); save_database_state()
    return x


@app.post("/api/upload")
async def up(file: Annotated[UploadFile, File()]):
    '''handles the upload of question files in JSON or CSV format and adds them to the database'''
    if file.content_type not in ["application/json", "text/csv"]:
        return JSONResponse({"erro": "tipo de ficheiro inválido"}, status_code=400)
    b = await file.read(); n = 0
    try:
        if file.filename.endswith(".json"):
            for x in json.loads(b)["questions"]:
                x = validate(x); app_state["q"][x["id"]] = x; app_state["c"].append(x); n += 1
        elif file.filename.endswith(".csv"):
            for r in csv.DictReader(io.StringIO(b.decode())):
                o = [r["option_" + c] for c in "abcdef" if r.get("option_" + c)]; k = [ "ABCDEF".index(z) for z in r["correct"].split(";") ]
                x = {"id": r["id"], "topic": r["topic"], "text": r["text"], "options": o, "correct": k, "explanation": r.get("explanation", ""), "type": "multiple" if len(k) > 1 else "single"}
                app_state["q"][x["id"]] = x; app_state["c"].append(x); n += 1
    except (OSError, json.JSONDecodeError, KeyError) as e:
        print(f"Could not load {DATABASE_PATH}: {e}")
    save_database_state()
    return {"ok": True, "added": n}


# gera as perguntas
def generate_questions(n, t=None):
    '''Generates a list of question IDs based on the specified number and optional topics.'''
    if not t: t = questions_topics()
    return random.sample([i for i, x in app_state["q"].items() if x["topic"] in t], n)


@app.post("/api/exam")
async def new(request: Request):
    '''Creates a new exam with a specified number of questions and optional topics.'''
    b = await request.json()
    n=int(b.get('num',10))
    m = int(b.get( "minutes",15 ))
    ids = generate_questions(n, b["topics"]) if b.get("topics") else generate_questions(n)
    i = str(uuid.uuid4())[:8]
    app_state["e"][i] = {"id": i, "questions": ids, "start": time.time(), "minutes": m}; save_database_state()
    print("novo", i, n, m)
    return {"id": i, "questions": [app_state["q"][j] for j in ids], "minutes": m, "start": app_state["e"][i]["start"]}


@app.get("/api/exam/{i}")
def get_e(i):
    '''Retrieves the details of a specific exam by its ID.'''
    e = app_state["e"][i]
    return {"id": i, "questions": [app_state["q"][j] for j in e["questions"]], "minutes": e["minutes"], "start": e["start"]}


@app.post("/api/exam/{i}/submit")
async def sub(i, request: Request):
    '''Submits the answers for a specific exam and calculates the score.'''
    b = await request.json(); e = app_state["e"][i]; a = b.get("answers", {}); s = 0; rv = []
    for j in e["questions"]:
        x = app_state["q"][j]; y = a.get(j, []); ok = False
        if x["type"] == "single":
            if len(y) == 1 and y[0] == x["correct"][0]: 
                ok = True
        elif x["type"] == "multiple" and sorted(y) == sorted(x["correct"]):
            ok = True
        # TODO v/f
        if ok == True:
            s = s + 1
        rv.append({"id": j, "text": x["text"], "ok": ok, "chosen": y, "correct": x["correct"], "options": x.get("options", ["Verdadeiro", "Falso"]), "explanation": x.get("explanation", "")})
    p = round(s / len(e["questions"]) * 100, 1)
    e["answers"] = a; e["name"] = b.get("name", "anónimo"); e["end"] = time.time()
    app_state["r"].append([i, e["name"], datetime.now().strftime("%d/%m %H:%M")]); save_database_state()
    return {"score": s, "total": len(e["questions"]), "pct": p, "passed": p >= 70, "review": rv, "seconds": int(e["end"] - e["start"])}


# calcula a nota
def calc2(e):
    '''Calculates the score for a given exam based on the answers provided.'''
    s = 0
    for j in e["questions"]:
        x = app_state["q"][j]; y = e.get("answers", {}).get(j, [])
        if x["type"] == "truefalse":
            if y == [0 if x["correct"] else 1]: s += 1
        elif x["type"] == "multiple":
            s += len(set(y) & set(x["correct"])) / len(x["correct"])
        else:
            if y == x["correct"]: s += 1
    return s


@app.get("/api/ranking")
def rk():
    '''Returns a sorted list of exam results with names, percentages, and dates.'''
    o = []
    for r in app_state["r"]:
        if len(r) > 3: o.append({"name": r[1], "pct": r[3], "date": r[2]}); continue
        e = app_state["e"][r[0]]
        o.append({"name": r[1], "pct": round(calc2(e) / len(e["questions"]) * 100, 1), "date": r[2]})
    by_pct = lambda x: x["pct"]
    o.sort(key = by_pct, reverse = True)
    return o


@app.post("/api/ranking")
async def rk2(request: Request):
    '''Adds a new entry to the ranking list based on the provided name and percentage.'''
    b = await request.json()
    app_state["r"].append([None, b["name"], datetime.now().strftime("%d/%m %H:%M"), b["pct"]]); save_database_state()
    return {"ok": True}


@app.delete("/api/ranking")
def rkdel(pwd: str = ""):
    '''Deletes all entries in the ranking list if the provided password is correct.'''
    if pwd == PW :
        app_state["r"] = [ ]
        save_database_state()
    return {"ok": True}


@app.get("/api/stats")
def st():
    '''Calculates and returns statistics about the exams taken, including the number of exams, passed exams, and topic-wise performance.'''
    t = {}; n = 0; ps = 0
    for e in app_state["e"].values():
        if "answers" in e:
            n += 1; s = 0
            for j in e["questions"]:
                x = app_state["q"][j]
                ok = sorted(e["answers"].get(j, [])) == sorted(x["correct"]) if x["type"] != "truefalse" else False
                t.setdefault(x["topic"], [0, 0]); t[x["topic"]][1] += 1
                if ok: s += 1; t[x["topic"]][0] += 1
            if s/len(e["questions"]) > 0.7 : ps+=1
    return {"exams": n, "passed": ps, "topics": [{"topic": k, "pct": round(v[0] / v[1] * 100), "correct": v[0], "total": v[1]} for k, v in t.items()]}


@app.get("/api/export.csv")
def exp():
    '''Exports the exam results in CSV format, including exam ID, name, score, total questions, and pass status.'''
    o = io.StringIO(); o.write("exam,name,score,total,passed\n")
    for e in app_state["e"].values():
        if "answers" not in e: continue
        s = sum([1 for j in e["questions"] if sorted(e["answers"].get(j, [])) == sorted(app_state["q"][j]["correct"] if type(app_state["q"][j]["correct"]) == list else [])])
        o.write(e["id"] + "," + e.get("name", "") + "," + str(s) + "," + str(len(e["questions"])) + "," + str(s >= 70) + "\n")
    return PlainTextResponse(o.getvalue(), media_type="text/csv")


@app.get("/api/export.yaml")
def exp2():
    '''Exports the exam results in YAML format.'''
    import yaml
    return PlainTextResponse(yaml.dump(list(app_state["e"].values())))


@app.get("/api/profile")
def pf():
    '''Returns the user's profile information, including days left until the exam if an exam date is set.'''
    p=dict(app_state["p"])
    if "exam_date" in p: p["days_left"] = (datetime.fromisoformat(p["exam_date"]).date() - date.today()).days
    return p


@app.post("/api/profile")
async def pf2(request: Request):
    '''Updates the user's profile information with the provided data.'''
    app_state["p"] = await request.json(); save_database_state()
    return pf()
