"""Simulador de Exames: cria a app e junta as rotas de cada área.

Correr:  uvicorn main:app --reload
"""

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import exams, grading, profile, questions, ranking, store

store.load_questions()
store.load()

app = FastAPI(title="Simulador de Exames")
app.mount("/static", StaticFiles(directory=store.BASE_DIR / "static"), name="static")
for area in (questions, exams, grading, ranking, profile):
    app.include_router(area.router)


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    return FileResponse(store.BASE_DIR / "static" / "index.html")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "questions": len(store.questions)}
