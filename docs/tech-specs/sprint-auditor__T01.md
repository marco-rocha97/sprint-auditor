# Tech Spec: Fundação — Modelos de Domínio, Template de Fases e Seed Sintético — `T01`

> **SPEC:** [`docs/specs/sprint-auditor.md`](../specs/sprint-auditor.md)
> **Plan:** [`docs/plans/sprint-auditor.md`](../plans/sprint-auditor.md) — task `T01`
> **Conventions applied:** `CLAUDE.md` (project) + regras globais do usuário
>
> Este documento detalha **como** entregar a tarefa. O **porquê** vive na SPEC; **o quê** e **em que ordem**, no Plan.

---

## Task Scope

- **Behavior delivered** (from Plan): O sistema dispõe de um vocabulário compartilhado (o que é um projeto, um update, um artefato, um score, um alerta) e de um projeto sintético "derrapado" que serve de base para todas as tarefas seguintes.
- **SPEC stories/criteria covered:** Contratos de dados implícitos em todas as histórias; Story 5 (distinção "sem dados" vs. score zero); Story 6 (nível de confiança nos alertas)
- **Depends on:** —
- **External dependencies:** nenhuma

---

## Architecture

- **General approach:** T01 bootstrapa o pacote Python inteiro. Cria `pyproject.toml` com Pydantic v2 como única dependência de runtime, configura o layout `src/sprint_auditor/` e os três módulos de domínio. Nenhuma lógica de negócio é implementada aqui — apenas contratos de dados e constantes.
- **Affected modules:**
  - `pyproject.toml` — novo
  - `src/sprint_auditor/__init__.py` — novo (vazio, marca o pacote)
  - `src/sprint_auditor/modelos.py` — novo (enums + modelos Pydantic)
  - `src/sprint_auditor/template_fases.py` — novo (dict de constantes + funções de consulta)
  - `src/sprint_auditor/seed.py` — novo (projeto sintético "Alpha Corp")
  - `tests/__init__.py` — novo (vazio)
  - `tests/test_modelos.py` — novo
  - `tests/test_template_fases.py` — novo
  - `tests/test_seed.py` — novo
- **New files:** todos os listados acima
- **Reused patterns:** nenhum — projeto vazio; padrões estabelecidos aqui servem de referência para T02–T06

> **Decision source:** CLAUDE.md (stack Python + uv + pytest + ruff + mypy + src layout).

---

## Contracts

### `src/sprint_auditor/modelos.py`

```python
# Enums (str Enum — serializa ao valor sem formatação extra)
class Fase(str, Enum):
    DISCOVERY = "discovery"
    CONFIGURACAO = "configuracao"
    DESENVOLVIMENTO = "desenvolvimento"
    REVIEW = "review"

class TipoArtefato(str, Enum):
    TRANSCRICAO = "transcricao"
    BOARD = "board"

class NivelConfianca(str, Enum):
    ALTO = "alto"
    MEDIO = "medio"
    BAIXO = "baixo"

class CategoriaAlerta(str, Enum):
    DESVIO_LIMIAR = "desvio_limiar"
    DETERIORACAO_CONSISTENTE = "deterioracao_consistente"
    BLOQUEIO_LINGUISTICO = "bloqueio_linguistico"

# Modelos Pydantic
class Artefato(BaseModel):
    id: str
    tipo: TipoArtefato
    conteudo: str
    dia_projeto: int           # Field(ge=1, le=15)
    valido: bool = True
    erro_ingestao: Optional[str] = None

class DeliveryScore(BaseModel):
    dados_suficientes: bool
    valor: Optional[int] = None  # Field(ge=0, le=100) quando não None
    scores_por_fase: dict[Fase, Optional[int]] = {}
    # Invariante: dados_suficientes=True ↔ valor is not None (validado em model_validator)

class Alerta(BaseModel):
    categoria: CategoriaAlerta
    fase: Fase
    dia_projeto: int           # Field(ge=1, le=15)
    gap_pp: Optional[float] = None  # só presente em DESVIO_LIMIAR
    causa_provavel: str
    nivel_confianca: NivelConfianca
    acao_sugerida: str
    artefato_fonte_id: str     # referencia Artefato.id
    trecho_fonte: str          # substring do Artefato.conteudo

class Update(BaseModel):
    id: str
    numero: int                # Field(ge=1) — sequencial no projeto
    dia_projeto: int           # Field(ge=1, le=15)
    artefatos: list[Artefato] = []
    score: Optional[DeliveryScore] = None  # preenchido por T03
    alertas: list[Alerta] = []             # preenchido por T04

class Projeto(BaseModel):
    id: str
    nome: str
    data_kickoff: AwareDatetime  # UTC obrigatório (rules/datetime.md)
    updates: list[Update] = []
```

### `src/sprint_auditor/template_fases.py`

```python
def progresso_esperado(fase: Fase, dia: int) -> int:
    """Retorna o progresso esperado (0–100%) para a fase no dia dado.
    Raises: KeyError se (fase, dia) não for combinação válida do template.
    """

def fase_do_dia(dia: int) -> Fase:
    """Retorna a fase ativa esperada para o dia de projeto (1–15).
    Raises: ValueError se dia < 1 ou dia > 15.
    """
```

### `src/sprint_auditor/seed.py`

```python
def carregar_projeto_seed() -> Projeto:
    """Retorna o projeto sintético 'Alpha Corp' com 3 updates de desvio progressivo."""
```

---

## Data Model

### `Artefato`

| Campo | Tipo | Obrigatório | Padrão | Restrição |
|---|---|---|---|---|
| `id` | `str` | sim | — | único no escopo do projeto |
| `tipo` | `TipoArtefato` | sim | — | enum: transcricao \| board |
| `conteudo` | `str` | sim | — | texto bruto |
| `dia_projeto` | `int` | sim | — | 1 ≤ dia ≤ 15 |
| `valido` | `bool` | não | `True` | T02 seta `False` quando ilegível |
| `erro_ingestao` | `Optional[str]` | não | `None` | presente apenas quando `valido=False` |

### `DeliveryScore`

| Campo | Tipo | Obrigatório | Padrão | Restrição |
|---|---|---|---|---|
| `dados_suficientes` | `bool` | sim | — | — |
| `valor` | `Optional[int]` | não | `None` | 0 ≤ valor ≤ 100; `None` ↔ `dados_suficientes=False` |
| `scores_por_fase` | `dict[Fase, Optional[int]]` | não | `{}` | cada valor: 0–100 ou `None` |

**Invariante** (validada em `model_validator(mode='after')`):
- `dados_suficientes=True` → `valor is not None`
- `dados_suficientes=False` → `valor is None`

### `Alerta`

| Campo | Tipo | Obrigatório | Padrão | Restrição |
|---|---|---|---|---|
| `categoria` | `CategoriaAlerta` | sim | — | enum |
| `fase` | `Fase` | sim | — | enum |
| `dia_projeto` | `int` | sim | — | 1 ≤ dia ≤ 15 |
| `gap_pp` | `Optional[float]` | não | `None` | presente apenas em `DESVIO_LIMIAR` |
| `causa_provavel` | `str` | sim | — | texto narrativo |
| `nivel_confianca` | `NivelConfianca` | sim | — | enum: alto \| medio \| baixo |
| `acao_sugerida` | `str` | sim | — | texto imperativo |
| `artefato_fonte_id` | `str` | sim | — | referencia `Artefato.id` |
| `trecho_fonte` | `str` | sim | — | substring do `Artefato.conteudo` |

### `Update`

| Campo | Tipo | Obrigatório | Padrão |
|---|---|---|---|
| `id` | `str` | sim | — |
| `numero` | `int` | sim | — | ge=1 |
| `dia_projeto` | `int` | sim | — | 1 ≤ dia ≤ 15 |
| `artefatos` | `list[Artefato]` | não | `[]` |
| `score` | `Optional[DeliveryScore]` | não | `None` |
| `alertas` | `list[Alerta]` | não | `[]` |

### `Projeto`

| Campo | Tipo | Obrigatório | Padrão |
|---|---|---|---|
| `id` | `str` | sim | — |
| `nome` | `str` | sim | — |
| `data_kickoff` | `AwareDatetime` | sim | — | UTC obrigatório |
| `updates` | `list[Update]` | não | `[]` |

### Template de Fases — Valores Concretos

| Fase | Dia | Progresso Esperado (%) |
|---|---|---|
| Discovery | 1 | 30 |
| Discovery | 2 | 70 |
| Discovery | 3 | 100 |
| Configuração | 4 | 10 |
| Configuração | 5 | 30 |
| **Configuração** | **6** | **60** ← critério de aceitação SPEC |
| Configuração | 7 | 100 |
| Desenvolvimento | 8 | 10 |
| Desenvolvimento | 9 | 25 |
| Desenvolvimento | 10 | 50 |
| Desenvolvimento | 11 | 75 |
| Desenvolvimento | 12 | 100 |
| Review | 13 | 30 |
| Review | 14 | 70 |
| Review | 15 | 100 |

### Seed — Projeto "Onboarding Alpha Corp"

```
id: "proj-alpha-001"
nome: "Onboarding Alpha Corp"
data_kickoff: 2026-04-28T09:00:00Z (segunda-feira)
```

| Update | Dia | Fase ativa | Artefatos | Narrativa |
|---|---|---|---|---|
| U1 | 3 | Discovery | board + transcricao | Discovery concluído, leve atraso em validação SAP mas dentro da tolerância |
| U2 | 6 | Configuração | board + transcricao | **Desvio inicia**: 38% real vs 60% esperado; transcrição contém sinal de bloqueio SAP |
| U3 | 9 | Desenvolvimento | board + transcricao | **Deterioração**: desenvolvimento bloqueado; ambiente SAP com falhas de conectividade |

Conteúdos concretos (strings literais definidas em `seed.py`):

**U2 — transcrição (artefato âncora para T04):**
```
"Ainda não temos acesso ao SAP, aguardando aprovação do departamento de TI da Alpha Corp.
Isso está segurando tudo. O setup do agente não pode avançar sem o ambiente configurado."
```

**U2 — board:**
```
"Configuração: [✗] Acesso ao ambiente SAP, [✗] Setup do agente IA, [✗] Integração com CRM"
```

---

## External Integrations

Nenhuma.

---

## Trade-offs e Alternativas Rejeitadas

**Decisão: Pydantic v2 em vez de dataclasses puras**
- Alternativa rejeitada: stdlib `@dataclass`
- Motivo: as restrições de domínio (score 0–100, dia 1–15, invariante `dados_suficientes ↔ valor`) são intrínsecas ao modelo; sem Pydantic, T03 e T04 precisariam duplicar guards de validação. `BaseModel` concentra isso em um ponto.
- Trade-off: adiciona `pydantic>=2.0` como dependência de runtime (~1 MB).
- Fonte: decisão do usuário nesta conversa.

**Decisão: `Optional[int] + dados_suficientes: bool` em vez de union discriminada**
- Alternativa rejeitada: `ScoreCalculado | ScoreInsuficiente` como tipos separados
- Motivo: o estado de ausência é binário; dois tipos extras adicionam overhead sem ganho real de segurança no fluxo de T05. `if not score.dados_suficientes` é inequívoco.
- Trade-off: o type checker não força tratamento exaustivo como um `match` forçaria.
- Fonte: decisão do usuário nesta conversa.

**Decisão: template como dict literal `(Fase, dia) → int`**
- Alternativa rejeitada: função matemática (curva linear ou sigmoide)
- Motivo: os valores são constantes de domínio calibradas para a demo (SPEC: "estimativa razoável — não requer calibração"). O dict torna cada valor diretamente testável; uma fórmula ocultaria o valor exato do critério dia 6 = 60%.
- Trade-off: adicionar nova duração de projeto requer entradas manuais.
- Fonte: critério de aceitação T01 no Plan + SPEC out-of-scope.

**Decisão: `AwareDatetime` (Pydantic) para `data_kickoff`**
- Alternativa rejeitada: `datetime` nativo (naive)
- Motivo: `rules/datetime.md` proíbe datetimes sem timezone. `AwareDatetime` rejeita datetimes naive no parse, eliminando a categoria de bug silenciosamente.
- Fonte: `rules/datetime.md`.

**Decisão: T01 inclui setup do `pyproject.toml`**
- Alternativa rejeitada: tarefa separada de setup fora do Plan
- Motivo: T01 não tem dependências e é o primeiro passo. Sem `pyproject.toml`, nenhum `uv run pytest` é possível — folding aqui é o único ponto lógico dentro do Plan.
- Fonte: CLAUDE.md (comandos `uv sync`, `uv run pytest`).

**Decisão: `str` como base dos enums**
- Alternativa rejeitada: `Enum` puro
- Motivo: `str` Enum serializa ao valor (`"configuracao"`) em vez de `<Fase.CONFIGURACAO: 'configuracao'>`, tornando os conteúdos de seed e relatórios legíveis sem código extra.

---

## Risks and Mitigations

| Risco | Impacto | Mitigação |
|---|---|---|
| Invariante `dados_suficientes ↔ valor` mal implementada | T03/T05 crasham ao acessar `score.valor` supondo not-None | `model_validator` valida ambas as direções; coberto em `test_modelos.py` casos 3 e 4 |
| Valor de dia 6, Configuração diferente de 60% | Critério de aceitação do Plan quebra; T03 usa baseline errada | `test_template_fases.py` caso 1 testa o valor exato com assert `== 60` |
| Seed sem diversidade de `TipoArtefato` | T02/T03 nunca exercitam o caminho BOARD | `test_seed.py` caso 2 afirma que o set de tipos inclui TRANSCRICAO e BOARD |
| `data_kickoff` criado como naive datetime | Violação de `rules/datetime.md`; comparações silenciosamente erradas | `AwareDatetime` rejeita naive no parse; seed usa `datetime(..., tzinfo=timezone.utc)` |

---

## Testing Plan

**Framework:** pytest. Fonte: CLAUDE.md (`uv run pytest tests/ -v`).

### `tests/test_modelos.py` — 9 testes

1. **Happy path — score com dados:** `DeliveryScore(dados_suficientes=True, valor=75)` → instancia sem erro, `score.valor == 75`
2. **Happy path — score sem dados:** `DeliveryScore(dados_suficientes=False, valor=None)` → instancia sem erro
3. **Erro — dados_suficientes=True, valor=None:** `ValidationError` levantado
4. **Erro — dados_suficientes=False, valor=50:** `ValidationError` levantado
5. **Borda — valor=0:** válido quando `dados_suficientes=True`
6. **Borda — valor=100:** válido quando `dados_suficientes=True`
7. **Borda — dia_projeto=0:** `ValidationError` em `Artefato` (ge=1)
8. **Borda — dia_projeto=16:** `ValidationError` em `Artefato` (le=15)
9. **Distinção explícita:** `Update` sem artefatos tem `score=None`; `score=None` é distinto de `DeliveryScore(dados_suficientes=False, valor=None)`

### `tests/test_template_fases.py` — 6 testes

1. **Critério SPEC:** `progresso_esperado(Fase.CONFIGURACAO, 6) == 60`
2. **Fim de cada fase = 100%:** dias 3, 7, 12, 15 → todos retornam 100
3. **Início de cada fase:** dia 1 → 30, dia 4 → 10, dia 8 → 10, dia 13 → 30
4. **Combinação inválida:** `progresso_esperado(Fase.DISCOVERY, 5)` → `KeyError`
5. **`fase_do_dia` — limites de fase:** dias 1, 3 → DISCOVERY; dias 4, 7 → CONFIGURACAO; dias 8, 12 → DESENVOLVIMENTO; dias 13, 15 → REVIEW
6. **`fase_do_dia` — fora do range:** dia 0 → `ValueError`; dia 16 → `ValueError`

### `tests/test_seed.py` — 6 testes

1. **Estrutura mínima:** `carregar_projeto_seed()` retorna `Projeto` com `len(updates) >= 3`
2. **Diversidade de tipos:** set de `tipo` em todos os artefatos inclui `TipoArtefato.TRANSCRICAO` e `TipoArtefato.BOARD`
3. **Dia de desvio presente:** existe exatamente um `update` com `dia_projeto == 6`
4. **Cronologia:** `dia_projeto` dos updates estão em ordem crescente
5. **Âncora de bloqueio:** artefato de `dia_projeto=6` com `tipo=TRANSCRICAO` contém a substring `"SAP"`
6. **Timezone UTC:** `projeto.data_kickoff.tzinfo` não é `None`; `utcoffset() == timedelta(0)`

**Total: 21 testes**

---

## Implementation Sequence

Cada passo = um commit coeso:

1. Criar `pyproject.toml` (pydantic runtime; pytest + ruff + mypy dev) → rodar `uv sync`
2. Criar `src/sprint_auditor/__init__.py` + `tests/__init__.py` (ambos vazios)
3. Criar `src/sprint_auditor/modelos.py` + `tests/test_modelos.py` → 9 testes passando
4. Criar `src/sprint_auditor/template_fases.py` + `tests/test_template_fases.py` → 6 testes passando
5. Criar `src/sprint_auditor/seed.py` + `tests/test_seed.py` → 6 testes passando
6. Rodar `uv run ruff check src/ tests/` + `uv run mypy src/` → zero warnings

---

## Conventions Applied (from CLAUDE.md)

- **Stack:** Python + uv + pytest + ruff + mypy
- **Layout:** `src/sprint_auditor/` + `tests/` espelhando a estrutura de `src/`
- **Modelagem:** Pydantic v2 (`BaseModel`, `Field`, `model_validator`, `AwareDatetime`)
- **Datetime:** `AwareDatetime` (Pydantic) + `timezone.utc` no seed — nunca naive (`rules/datetime.md`)
- **Linguagem do código:** Português-Brasil (nomes de variáveis, funções, campos, docstrings)
- **Comentários:** nenhum por padrão — apenas onde o WHY não é óbvio pelo nome

---

## Ready to Code?

- [x] Arquitetura descrita com módulos e novos arquivos nomeados
- [x] Contratos (interfaces internas) em forma final com assinaturas completas
- [x] Modelo de dados com tipos, campos obrigatórios, defaults e restrições
- [x] Trade-offs não triviais com alternativa rejeitada documentada
- [x] Riscos conhecidos listados com mitigações
- [x] Plano de teste cobre happy path + pelo menos 2 casos de erro + casos de borda
- [x] Sequência de implementação é executável sem perguntas de clarificação
- [x] Nova biblioteca (Pydantic v2) introduzida com justificativa explícita
- [x] Convenções do CLAUDE.md citadas e respeitadas
