# Simulador de Exames

App para treinar para os exames de certificação (NVIDIA, Databricks, AWS...). Branch `checkpoint`: o código da manhã, já limpo e partido por áreas.

## Correr

```bash
pip install -r requirements.txt
uvicorn main:app --reload      # http://127.0.0.1:8000  ·  API: /docs
pytest                         # testes
```

## Estrutura

| Ficheiro | Área | Grupo |
|---|---|---|
| `main.py` | Cria a app e junta as rotas | todos (combinar antes) |
| `app/store.py` | Estado em memória e `db.json` | todos (combinar antes) |
| `app/questions.py` | Banco de perguntas: listar, criar, importar | 1 |
| `app/exams.py` | Criar e abrir exames | 2 |
| `app/grading.py` | Entregar e corrigir | 3 |
| `app/ranking.py` | Ranking e exportação | 4 |
| `app/profile.py` | Perfil e estatísticas | 5 |

Tickets: [TICKETS.md](TICKETS.md).

## Admin

Para adicionar perguntas: `POST /api/questions?pwd=admin123`
