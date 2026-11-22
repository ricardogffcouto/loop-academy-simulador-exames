# Simulados NCA-GENL · Loop Future Academy

Simulados para a certificação **NVIDIA-Certified Associate: Generative AI LLMs (NCA-GENL)**.
O aluno escreve o nome, faz um simulado cronometrado e vê a nota, a nota por domínio e cada pergunta
com a resposta certa, a explicação e o link oficial para investigar. O formador vê quem fez o quê e que
perguntas cada aluno errou.

- **Alunos:** https://loop-simulados.fly.dev
- **Formador:** https://loop-simulados.fly.dev/formador (pede o token na primeira visita; também aceita `?token=...`)

## O que há

| Exame | Perguntas | Tempo | Para quê |
|---|---|---|---|
| Simulado 1 a 6 | 50 | 60 min | Fixos e disjuntos: cada pergunta do banco aparece em exatamente um. Todos os alunos fazem as mesmas perguntas, por isso dá para comparar. |
| Simulado aleatório | 50 | 60 min | Sorteado do banco inteiro com a distribuição do exame, para repetir. |
| Treino por domínio | 20 | 24 min | Atacar um domínio fraco. |

Cada simulado segue os pesos oficiais: Core ML & AI 15 · Software Development 12 · Experimentation 11 ·
Data Analysis 7 · Trustworthy AI 5. Cerca de 22% das perguntas são "select two", como no exame real (os
candidatos estimam ~25%). A correção é tudo-ou-nada: uma "select two" só conta com as duas opções certas.

A NVIDIA não publica a nota mínima (circula ~70%, sem confirmação). Por isso a meta da turma é **80% em
dois simulados seguidos** antes de marcar o exame. A página "Alunos" do formador marca quem já lá chegou.

## O banco de perguntas

300 perguntas originais em `data/bank/*.json`, escritas a partir dos objetivos oficiais e das leituras
recomendadas na página da certificação (nov. 2026). Não são perguntas do exame real: essas não se podem
publicar, e os sites de "dumps" violam as regras da NVIDIA.

Cada pergunta tem:

```json
{"id": "sw-020", "domain": "sw", "topic": "TensorRT-LLM", "type": "single",
 "question": "...", "options": ["...", "...", "...", "..."], "answer": [2],
 "explanation": "porquê a certa é certa e as outras não",
 "source": {"title": "TensorRT-LLM, Paged Attention, IFB and Request Scheduling", "url": "https://..."}}
```

`type` é `single` (4 opções, 1 certa) ou `multi` (5 opções, 2 certas, e o enunciado diz "(Select two.)").

### Como foi verificado

1. **Cobertura:** os temas seguem os objetivos dos 5 domínios e a pesquisa de cobertura em
   `loop-ai-academy/AI Track/2026-week2/planning/exam-coverage-research.md`. Há mais peso nos temas que os
   candidatos dizem aparecer muito: stack NVIDIA (NIM, Triton, TensorRT-LLM, NeMo), LoRA/PEFT,
   quantização, métricas.
2. **Factos NVIDIA confirmados nos docs oficiais**, por exemplo: as portas e funcionalidades do Triton, as
   funcionalidades do TensorRT-LLM, os 5 tipos de rails do NeMo Guardrails, os 4 princípios de
   Trustworthy AI da NVIDIA, as 4 funções do NIST AI RMF, o fallback do cudf.pandas e o aviso multi-GPU
   do Dask cuDF.
3. **Respostas e distratores revistos um a um** contra a definição standard (não contra os labs). Os
   distratores que um especialista podia defender foram reescritos.
4. **Viés de comprimento corrigido.** No primeiro rascunho, a resposta certa era a mais longa em 81% das
   perguntas, uma pista que ensina o truque errado. Agora fica em ~35% (o acaso dá 25%), e nas "select two"
   as duas certas são as duas mais longas em só 4 de 66.
5. **Posições baralhadas** com semente por id, para a resposta certa não ter posição preferida.
6. **Fontes testadas:** todos os URLs respondem, e os 52 papers citados confirmam-se pelo título no arXiv
   ou na ACL.

### Acrescentar perguntas

1. Escreve a pergunta num ficheiro de `data/bank/` do domínio certo (ou num ficheiro novo, como
   `data/bank/sw-3.json`), com um `id` novo e único, por exemplo `sw-073`. Podes pôr a resposta certa
   em qualquer posição: o passo 3 baralha.
2. `python3 tools/bank_tools.py check`: valida o esquema e mostra se a certa ficou a mais longa.
3. `python3 tools/bank_tools.py shuffle`: baralha **só as perguntas novas** e marca-as com `"shuffled": true`.
   As que já estão no ar nunca mudam de ordem, porque as tentativas guardam as respostas por posição.
4. `python3 tools/bank_tools.py links`, depois `git commit`, `git push` e `fly deploy --ha=false`.

As perguntas novas entram logo no simulado aleatório e nos treinos por domínio. Os Simulados 1–6
ficam como estão. Só corras `mocks` para os refazer antes de a turma os começar, porque mudam a
composição de cada um e deixa de dar para comparar alunos.

Para corrigir uma pergunta, mantém o `id` e a ordem das opções. Para a retirar, apaga-a do JSON:
as tentativas antigas ignoram ids que já não existem.

### Manutenção

```bash
python3 tools/bank_tools.py check     # esquema, contagens, viés de comprimento, posições
python3 tools/bank_tools.py links     # testa todos os URLs das fontes
python3 tools/bank_tools.py shuffle   # baralha as opções das perguntas novas
python3 tools/bank_tools.py mocks     # refaz data/mocks.json (6 simulados disjuntos)
python3 tools/bank_tools.py apply fix.json   # aplica correções por id: {"sw-020": {"explanation": "..."}}
```

## Correr localmente

```bash
uv venv && uv pip install -r requirements-dev.txt
SIM_ADMIN_TOKEN=teste .venv/bin/uvicorn app.main:app --reload    # http://127.0.0.1:8000
.venv/bin/python -m pytest -q
```

## Deploy (Fly.io)

App `loop-simulados`, região `cdg`, SQLite no volume `simulados_data` (`/data/simulados.db`).

```bash
fly deploy
fly secrets set SIM_ADMIN_TOKEN=...      # token da página do formador
```

## Arquitetura

FastAPI (`app/main.py`) + SQLite + HTML/JS sem build (`static/`). As respostas certas nunca vão para o
browser durante o exame: só chegam na revisão, depois de submeter. As respostas em curso ficam no
`localStorage`, por isso recarregar a página não perde nada. O cronómetro usa a hora do servidor e
submete sozinho quando chega a 0:00.

O histórico do Dia 2 (versão brownfield que a turma construiu) está nos ramos `checkpoint`, `grupo*` e `G3-*`.
