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
from typing import Annotated

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Simulador de Exames")
app.mount("/static", StaticFiles(directory="static"), name="static")

F = "db.json"
PW = "admin123" # TODO mudar antes de ir p/ prod
QUESTION_BANK = {"questions": {}, "exams": {}, "ranking": [], "profile": {}, "custom": []}

def init():
    """
    Load questions from the 'data' directory and store them in QUESTION_BANK.
    
    Raises:
        json.JSONDecodeError: If any JSON file has invalid syntax.
    """
    for f in os.listdir("data"):
        if f.endswith(".json"):
            try:
                with open("data/" + f, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                for x in data["questions"]:
                    QUESTION_BANK["questions"][x["id"]] = x 
            except json.JSONDecodeError as e:
                print("Invalid JSON syntax:", e)
                raise

    print ("ok",len(QUESTION_BANK["questions"]))


def save_current():
    """
    Save the current state of QUESTION_BANK to a JSON file.
    
    Raises:
        json.JSONDecodeError: If there is an error in JSON serialization.
    """
    try: 
        with open(F, "w", encoding="utf-8") as f:
            json.dump({k: QUESTION_BANK[k] for k in ["exams", "ranking", "profile", "custom"]}, f)
    except json.JSONDecodeError as e:
        print("Invalid JSON syntax:", e)
        raise

def load_current():
    """
    Load the state of QUESTION_BANK from a JSON file if it exists.
    
    Raises:
        json.JSONDecodeError: If the JSON file has invalid syntax.
    """
    try:
        with open(F, "r", encoding="utf-8") as f:
            d2 = json.load(f)
        for k in d2: QUESTION_BANK[k] = d2[k]
        for x in QUESTION_BANK["custom"]: QUESTION_BANK["questions"][x["id"]] = x
    except json.JSONDecodeError as e:
        print("Invalid JSON syntax:", e)
        raise

init(); load_current()


@app.get("/")
def home(): 
    """
    Serve the main HTML page for the application.
    
    Returns:
        FileResponse: The response containing the 'index.html' file.
    """
    return FileResponse("static/index.html")


@app.get("/health")
def h(): 
    """
    Check the health of the application.
    
    Returns:
        dict: A dictionary containing the status and question count.
    """
    return {"status": "ok", "questions": len(QUESTION_BANK["questions"])}


def topics():
    """
    Retrieve a list of unique topics from the QUESTION_BANK.
    
    Returns:
        list: A list of unique topics.
    """
    t=[]
    for x in QUESTION_BANK["questions"].values():
        if x["topic"] not in t: t.append(x["topic"])
    return t


@app.get("/api/topics")
def t():
    """
    Retrieve a list of unique topics from the QUESTION_BANK.
    
    Returns:
        list: A list of unique topics.
    """
    l = topics(); l.sort()
    return l


# valida a pergunta
def validate(x):
    """
    Validate and normalize a question dictionary.
    
    Args:
        x (dict): The question dictionary to validate.
    
    Returns:
        dict: The validated question dictionary.
    """
    if not "type" in x: x["type"] = "single"
    return x


@app.get("/api/questions")
def qs(topic: str | None):
    """
    Retrieve a list of questions filtered by topic.
    
    Args:
        topic (str | None): The topic to filter questions by.
    
    Returns:
        list: A list of questions matching the filter.
    """
    return [x for x in QUESTION_BANK["questions"].values() if topic == None or x["topic"] == topic]


@app.get("/api/questions/{qid}")
def q1( qid ) :
    """
    Retrieve a specific question by its ID.
    
    Args:
        qid (str): The ID of the question to retrieve.
    
    Returns:
        dict: The question dictionary.
    """
    return QUESTION_BANK["questions"][ qid ]


@app.post("/api/questions")
async def addQ(request: Request):
    """
    Add a new question to the QUESTION_BANK.
    
    Args:
        request (Request): The incoming request containing the question data.
    
    Returns:
        dict: The added question dictionary.
    """
    if request.query_params.get("pwd") != PW: return JSONResponse({"erro": "password errada"}, status_code=401)
    x = validate(await request.json()); QUESTION_BANK["questions"][x["id"]] = x; QUESTION_BANK["custom"].append(x); save_current()
    return x


@app.post("/api/upload")
async def up(file: Annotated[UploadFile, File()]):
    """
    Upload a file containing questions in JSON or CSV format and add them to the QUESTION_BANK.
    
    Args:
        file (UploadFile): The file to upload.
    
    Returns:
        dict: A summary of the upload results.
    Raises:
        json.JSONDecodeError: If the uploaded JSON file has invalid syntax."""
    b = await file.read(); n = 0
    try:
        if file.filename.endswith(".json"):
            for x in json.loads(b)["questions"]:
                x = validate(x); QUESTION_BANK["questions"][x["id"]] = x; QUESTION_BANK["custom"].append(x); n += 1
        elif file.filename.endswith(".csv"):
            for r in csv.DictReader(io.StringIO(b.decode())):
                o = [r["option_" + c] for c in "abcdef" if r.get("option_" + c)]; k = [ "ABCDEF".index(z) for z in r["correct"].split(";") ]
                x = {"id": r["id"], "topic": r["topic"], "text": r["text"], "options": o, "correct": k, "explanation": r.get("explanation", ""), "type": "multiple" if len(k) > 1 else "single"}
                QUESTION_BANK["questions"][x["id"]] = x; QUESTION_BANK["custom"].append(x); n += 1
    except json.JSONDecodeError as e:
        print("Invalid JSON syntax:", e)
        raise
    save_current()
    return {"ok": True, "added": n}


# gera as perguntas
def generate_question(n, t=None):
    """
    Generate a list of question IDs based on the specified number and optional topics.
    
    Args:
        n (int): The number of questions to generate.
        t (list | None): The list of topics to filter questions by.
    
    Returns:
        list: A list of question IDs.
    """
    if t is None or not t:
        t = topics()
    ids = [i for i, x in QUESTION_BANK["questions"].items() if x["topic"] in t]
    if n <= 0:
        return []
    if n >= len(ids):
        return ids
    return random.sample(ids, n)


@app.post("/api/exam")
async def new(request: Request):
    """
    Create a new exam with a specified number of questions and optional topics.
    
    Args:
        request (Request): The incoming request containing exam configuration.
    
    Returns:
        dict: The created exam dictionary.
    """
    b = await request.json()
    n=int(b.get('num',10))
    m = int(b.get( "minutes",15 ))
    ids = generate_question(n, b["topics"]) if b.get("topics") else generate_question(n)
    i = str(uuid.uuid4())[:8]
    QUESTION_BANK["exams"][i] = {"id": i, "questions": ids, "start": time.time(), "minutes": m}; save_current()
    print("novo", i, n, m)
    return {"id": i, "questions": [QUESTION_BANK["questions"][j] for j in ids], "minutes": m, "start": QUESTION_BANK["exams"][i]["start"]}


@app.get("/api/exam/{i}")
def get_e(i):
    """
    Retrieve an exam by its ID.

    Args:
        i (str): The ID of the exam to retrieve.

    Returns:
        dict: The exam dictionary.
    """
    e = QUESTION_BANK["exams"][i]
    return {"id": i, "questions": [QUESTION_BANK["questions"][j] for j in e["questions"]], "minutes": e["minutes"], "start": e["start"]}


@app.post("/api/exam/{i}/submit")
async def sub(i, request: Request):
    """
    Submit answers for an exam and calculate the score.

    Args:
        i (str): The ID of the exam to submit.
        request (Request): The incoming request containing the answers.

    Returns:
        dict: A summary of the exam results, including score, total questions, percentage, pass status, review of answers, and time taken.
    """
    b = await request.json(); e = QUESTION_BANK["exams"][i]; a = b.get("answers", {}); s = 0; rv = []
    for j in e["questions"]:
        x = QUESTION_BANK["questions"][j]; y = a.get(j, []); ok = False
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
    QUESTION_BANK["ranking"].append([i, e["name"], datetime.now().strftime("%d/%m %H:%M")]); save_current()
    return {"score": s, "total": len(e["questions"]), "pct": p, "passed": p >= 70, "review": rv, "seconds": int(e["end"] - e["start"])}


# calcula a nota
def calc2(e):
    """
    Calculate the score for an exam.

    Args:
        e (dict): The exam dictionary.

    Returns:
        int: The calculated score.
    """
    s = 0
    for j in e["questions"]:
        x = QUESTION_BANK["questions"][j]; y = e.get("answers", {}).get(j, [])
        if x["type"] == "truefalse":
            if y == [0 if x["correct"] else 1]: s += 1
        elif x["type"] == "multiple":
            s += len(set(y) & set(x["correct"])) / len(x["correct"])
        else:
            if y == x["correct"]: s += 1
    return s


@app.get("/api/ranking")
def rk():
    """
    Retrieve the ranking of exams based on scores and percentages.
    
    Returns:
        list: A sorted list of ranking entries, each containing the name, percentage score, and date of the exam."""
    o = []
    for r in QUESTION_BANK["ranking"]:
        if len(r) > 3: o.append({"name": r[1], "pct": r[3], "date": r[2]}); continue
        e = QUESTION_BANK["exams"][r[0]]
        o.append({"name": r[1], "pct": round(calc2(e) / len(e["questions"]) * 100, 1), "date": r[2]})
    by_pct = lambda x: x["pct"]
    o.sort(key = by_pct, reverse = True)
    return o


@app.post("/api/ranking")
async def rk2(request: Request):
    """
    Add a new entry to the ranking with the provided name and percentage score.

    Args:
        request (Request): The incoming request containing the ranking entry data.
    Returns:
        dict: A confirmation of the successful addition to the ranking.
    """
    b = await request.json()
    QUESTION_BANK["ranking"].append([None, b["name"], datetime.now().strftime("%d/%m %H:%M"), b["pct"]]); save_current()
    return {"ok": True}


@app.delete("/api/ranking")
def rkdel(pwd: str = ""):
    """
    Delete all entries in the ranking if the provided password is correct.

    Args:
        pwd (str): The password to authorize the deletion.

    Returns:
        dict: A confirmation of the successful deletion or an error message if the password is incorrect.
    """
    if pwd == PW :
        QUESTION_BANK["ranking"] = [ ]
        save_current()
    return {"ok": True}


@app.get("/api/stats")
def st():
    """
    Calculate and return statistics about the exams and topics.

    Returns:
        dict: A dictionary containing the number of exams, number of passed exams, and topic statistics.
    """
    t = {}; n = 0; ps = 0
    for e in QUESTION_BANK["exams"].values():
        if "answers" in e:
            n += 1; s = 0
            for j in e["questions"]:
                x = QUESTION_BANK["questions"][j]
                ok = sorted(e["answers"].get(j, [])) == sorted(x["correct"]) if x["type"] != "truefalse" else False
                t.setdefault(x["topic"], [0, 0]); t[x["topic"]][1] += 1
                if ok: s += 1; t[x["topic"]][0] += 1
            if s/len(e["questions"]) > 0.7 : ps+=1
    return {"exams": n, "passed": ps, "topics": [{"topic": k, "pct": round(v[0] / v[1] * 100), "correct": v[0], "total": v[1]} for k, v in t.items()]}


@app.get("/api/export.csv")
def exp():
    """
    Export exam results as a CSV file.
    
    Returns:
        PlainTextResponse: A response containing the CSV data of exam results.
    """
    o = io.StringIO(); o.write("exam,name,score,total,passed\n")
    for e in QUESTION_BANK["exams"].values():
        if "answers" not in e: continue
        s = sum([1 for j in e["questions"] if sorted(e["answers"].get(j, [])) == sorted(QUESTION_BANK["questions"][j]["correct"] if type(QUESTION_BANK["questions"][j]["correct"]) == list else [])])
        o.write(e["id"] + "," + e.get("name", "") + "," + str(s) + "," + str(len(e["questions"])) + "," + str(s >= 70) + "\n")
    return PlainTextResponse(o.getvalue(), media_type="text/csv")


@app.get("/api/export.yaml")
def exp2():
    """
    Export exam results as a YAML file.

    Returns:
        PlainTextResponse: A response containing the YAML data of exam results.
    """
    import pyyaml
    return PlainTextResponse(pyyaml.dump(list(QUESTION_BANK["exams"].values())))


@app.get("/api/profile")
def pf():
    """
    Retrieve the user's profile information, including the number of days left until the exam date if specified.
    
    Returns:
        dict: A dictionary containing the user's profile information.
    """
    p=dict(QUESTION_BANK["profile"])
    if "exam_date" in p: p["days_left"] = (datetime.fromisoformat(p["exam_date"]).date() - date.today()).days
    return p


@app.post("/api/profile")
async def pf2(request: Request):
    """
    Update the user's profile information with the provided data.

    Args:
        request (Request): The HTTP request containing the updated profile data.

    Returns:
        dict: The updated user profile information.
    """
    QUESTION_BANK["profile"] = await request.json(); save_current()
    return pf()
