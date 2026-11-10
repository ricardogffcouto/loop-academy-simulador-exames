# Tickets da tarde

Cada grupo é dono de **uma área** do simulador e mexe só nos seus ficheiros. Cada ticket já tem **testes vermelhos** (`xfail`) que dizem quando está feito.

## Como trabalhar

```bash
git fetch
git switch checkpoint
git switch -c grupo-N          # N = número do grupo
pip install -r requirements.txt
pytest                         # verdes = já funciona · x = ainda por fazer
pytest tests/test_exams.py     # só os testes da vossa área
uvicorn main:app --reload      # app em http://127.0.0.1:8000 · API em /docs
```

**Papéis (trocam em cada bloco):**

- **Driver:** escreve o código.
- **Navegador:** lê o ticket e as pistas e diz o próximo passo.
- **Tester:** corre o `pytest` e testa no `/docs`.

**Um teste está feito quando:**

1. Tiram a linha `@pytest.mark.xfail(...)` de cima do teste.
2. O `pytest` passa a verde, incluindo os testes que já estavam verdes.
3. A app continua a funcionar no browser.

**Ajuda:** primeiro as pistas 1 e 2, depois o sénior do grupo, depois a pista 3. Só depois o formador.

**Definition of Done de cada ticket:**

- Testes da área verdes.
- `ruff check` e `black --check` sem erros novos.
- Commit com uma mensagem que diz o quê e porquê.
- Pull Request para o branch `checkpoint`.

---

## Grupo 1 · Banco de perguntas · `app/questions.py` · `tests/test_questions.py`

### G1-A · Validar perguntas novas (Pydantic)

> Como **formadora**, quero que uma pergunta mal escrita seja recusada ao criar, para que nenhum aluno fique com um exame que não consegue entregar.

Hoje `POST /api/questions` aceita qualquer JSON. Com `"correct": 2`, quem apanhar essa pergunta já não consegue entregar o exame.

**Testes a pôr verdes:**

- `test_correct_out_of_range_is_422`
- `test_correct_must_be_a_list`
- `test_needs_two_options`

<details><summary>Pista 1</summary>

Criem `class QuestionIn(BaseModel)` e recebam-no na rota em vez de `request: Request`. O FastAPI devolve 422 sozinho.
</details>

<details><summary>Pista 2</summary>

Campos: `id: str`, `topic: str`, `text: str = Field(min_length=3)`, `options: list[str] = Field(min_length=2, max_length=6)`, `correct: list[int] = Field(min_length=1)`, `type: Literal["single", "multiple"] = "single"`, `explanation: str = ""`.
</details>

<details><summary>Pista 3</summary>

"Cada índice de `correct` existe em `options`" envolve 2 campos, por isso é um `@model_validator(mode="after")`: se algum `i` não estiver em `range(len(self.options))`, faz `raise ValueError(...)`. Para guardar: `add_question(question.model_dump())`.
</details>

### G1-B · Erros HTTP certos

> Como **aluno**, quero mensagens de erro que façam sentido, para perceber o que fiz mal.

**Testes a pôr verdes:**

- `test_unknown_question_is_404`
- `test_topic_filter_ignores_case`
- `test_duplicate_id_is_409`

<details><summary>Pista 1</summary>

`raise HTTPException(status_code=404, detail="...")`.
</details>

<details><summary>Pista 2</summary>

Para o filtro, comparem as duas strings com `.lower()`, ou melhor, com `.casefold()`.
</details>

<details><summary>Pista 3</summary>

Antes de `add_question`, verifiquem `if question.id in store.questions:` e devolvam 409 (Conflict).
</details>

**Desafio:** o upload de JSON partido dá 500. Devolvam 400 com uma mensagem clara.

---

## Grupo 2 · Exames · `app/exams.py` · `tests/test_exams.py`

### G2-A · Validar o pedido de exame (Pydantic)

> Como **aluno**, quero que pedidos sem sentido sejam recusados com uma explicação, e não com um erro do servidor.

**Testes a pôr verdes:**

- `test_zero_minutes_is_422`
- `test_negative_count_is_422`
- `test_count_must_be_a_number`

<details><summary>Pista 1</summary>

Criem `class ExamRequest(BaseModel)` e usem-no como parâmetro da rota.
</details>

<details><summary>Pista 2</summary>

O frontend envia o JSON `{"num": "10", "minutes": "15", "topics": []}`. Os números chegam como texto, e o Pydantic converte `"10"` para `10` sozinho.
</details>

<details><summary>Pista 3</summary>

`num: int = Field(10, ge=1, le=50)`, `minutes: int = Field(15, ge=1, le=180)`, `topics: list[str] = []`. Aqui `[]` é seguro, porque o Pydantic copia o default. Numa função normal, não é seguro: vejam o G2-B.
</details>

### G2-B · Erros HTTP e um bug escondido

**Testes a pôr verdes:**

- `test_unknown_exam_is_404`
- `test_too_many_questions_is_400`
- `test_pick_questions_keeps_its_default`

<details><summary>Pista 1</summary>

Pedir 50 perguntas de Git faz rebentar o `random.sample`. Verifiquem antes de o chamar e devolvam 400 com uma mensagem que diga quantas perguntas há do tópico.
</details>

<details><summary>Pista 2</summary>

O `ruff check` já se queixa do bug escondido (B006). No REPL, corram `from app.exams import pick_questions`, depois `pick_questions(1)`, depois `pick_questions.__defaults__`. O que aconteceu?
</details>

<details><summary>Pista 3</summary>

`topics: list[str] | None = None`, e dentro da função `topics = topics or store.topics()`.
</details>

---

## Grupo 3 · Correção · `app/grading.py` · `tests/test_grading.py`

### G3-A · Uma regra de correção que funciona para todos os tipos

> Como **aluno**, quero que as perguntas de verdadeiro/falso contem, porque acerto nelas e aparecem erradas.

**Testes a pôr verdes:**

- `test_true_false_true`
- `test_true_false_false`
- `test_answers_must_be_lists`

<details><summary>Pista 1</summary>

Nas perguntas V/F, `correct` é `True` ou `False`, e o aluno escolhe a opção 0 (Verdadeiro) ou 1 (Falso).
</details>

<details><summary>Pista 2</summary>

Ao certo vale `chosen == [0 if question["correct"] else 1]`. Para as respostas, criem um modelo `Submission` com `answers: dict[str, list[int]] = {}` e `name: str = "anónimo"`.
</details>

<details><summary>Pista 3</summary>

Desafio de POO: uma classe por tipo (`SingleChoice`, `MultipleChoice`, `TrueFalse`), cada uma com o seu `is_correct()`, e uma função que escolhe a classe pelo `type`.
</details>

### G3-B · Erros HTTP na entrega

**Testes a pôr verdes:**

- `test_submit_unknown_exam_is_404`
- `test_submit_twice_is_409`

<details><summary>Pista 1</summary>

Um exame já entregue tem a chave `"answers"`.
</details>

<details><summary>Pista 2</summary>

Usem `HTTPException` com 404 e com 409.
</details>

<details><summary>Pista 3</summary>

Façam as duas verificações no início de `submit_exam`, antes de calcular seja o que for.
</details>

---

## Grupo 4 · Ranking e exportação · `app/ranking.py` · `tests/test_ranking.py`

### G4-A · Validar entradas do ranking (Pydantic)

> Como **formadora**, não quero ver 150% nem código HTML no ranking que aparece no ecrã da turma.

Experimentem no `/docs`: `POST /api/ranking` com `{"name": "<img src=x onerror=alert(1)>", "pct": 50}` e abram o Ranking no browser.

**Testes a pôr verdes:**

- `test_pct_above_100_is_422`
- `test_name_with_html_is_422`
- `test_missing_pct_is_422`

<details><summary>Pista 1</summary>

Criem `class RankingEntryIn(BaseModel)` com `name` e `pct`.
</details>

<details><summary>Pista 2</summary>

`pct: float = Field(ge=0, le=100)`, `name: str = Field(min_length=1, max_length=30)`.
</details>

<details><summary>Pista 3</summary>

Para recusar HTML, usem `@field_validator("name")`: se tiver `<` ou `>`, façam `raise ValueError(...)`. Outra opção é `Field(pattern=r"^[^<>]+$")`.
</details>

### G4-B · Password errada, CSV e YAML

**Testes a pôr verdes:**

- `test_clear_with_wrong_password_is_401`
- `test_csv_passed_uses_pass_mark`
- `test_requirements_include_yaml`

<details><summary>Pista 1</summary>

No CSV, `score >= 70` compara o número de certas com 70. O que devia comparar?
</details>

<details><summary>Pista 2</summary>

Para a password, criem uma função `require_admin(pwd: str = "")` que levanta 401, e usem-na com `Depends`.
</details>

<details><summary>Pista 3</summary>

Ponham `pyyaml` no `requirements.txt`, corram `pip install -r requirements.txt` e experimentem `/api/export.yaml`.
</details>

---

## Grupo 5 · Perfil e estatísticas · `app/profile.py` · `tests/test_profile.py`

### G5-A · Validar o perfil (Pydantic)

> Como **aluno**, quero que a contagem decrescente para o exame faça sentido.

Hoje uma data do exame em 3026-01-01 diz que faltam 364 000 dias. Uma data escrita como texto ("amanhã") parte a página de **toda a turma**, porque o perfil é um só.

**Testes a pôr verdes:**

- `test_far_future_date_is_422`
- `test_past_date_is_422`
- `test_text_date_is_422`

<details><summary>Pista 1</summary>

Criem `class Profile(BaseModel)` com `name`, `certification` e `exam_date: date`. O Pydantic já recusa "amanhã".
</details>

<details><summary>Pista 2</summary>

"Entre hoje e daqui a 2 anos" é uma regra vossa, por isso usem `@field_validator("exam_date")`.
</details>

<details><summary>Pista 3</summary>

`if not date.today() <= v <= date.today() + timedelta(days=730): raise ValueError(...)`. Para guardar: `profile.model_dump(mode="json")`.
</details>

### G5-B · Estatísticas que batem certo

**Testes a pôr verdes:**

- `test_stats_70_percent_is_passed`
- `test_stats_use_pass_mark`
- `test_broken_saved_profile_is_not_500`

<details><summary>Pista 1</summary>

Comparem a regra de "passou" em `get_stats` com a de `grading.py`. Quantas regras diferentes há na app?
</details>

<details><summary>Pista 2</summary>

`store.PASS_MARK` existe, mas ninguém o usa.
</details>

<details><summary>Pista 3</summary>

No `get_profile`, ponham `try` / `except ValueError` à volta do `fromisoformat` e, se der erro, não calculem `days_left`.
</details>
