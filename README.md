# Simulador de Exames 🎓

App para treinar para os exames de certificação (NVIDIA, Databricks, AWS...).

**Em produção:** https://loop-exames.fly.dev

## Correr

```
pip install -r requirements.txt
uvicorn main:app --reload
```

Abrir http://127.0.0.1:8000

## Admin

Para adicionar perguntas: `POST /api/questions?pwd=admin123`

## Deploy

Cada push para `main` faz deploy automático para o Fly.io.
