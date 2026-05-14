# Tech Spec: Ingestão de Artefatos — `T02`

> **SPEC:** [`docs/specs/sprint-auditor.md`](../specs/sprint-auditor.md)
> **Plan:** [`docs/plans/sprint-auditor.md`](../plans/sprint-auditor.md) — task `T02`
> **Conventions applied:** `CLAUDE.md` (projeto) + regras globais do usuário
>
> Este documento detalha **como** entregar a tarefa. O **porquê** vive na SPEC; **o quê** e **em que ordem**, no Plan.

---

## Task Scope

- **Behavior delivered** (from Plan): O sistema aceita transcrições de calls (texto) e exports de board (estruturado), valida a legibilidade de cada artefato e, quando um falha, registra o problema e segue processando os demais.
- **SPEC stories/criteria covered:** Story 5 (sinalizar ausência de artefatos suficientes); Behavior "Artefato ilegível" (apontar qual falhou, continuar com o restante)
- **Depends on:** T01
- **External dependencies:** nenhuma

---

## Architecture

- **General approach:** T02 adiciona uma camada de validação e normalização sobre os `Artefato` já construídos pelo pipeline. A função `ingerir_artefatos` recebe uma lista de `Artefato`, valida o conteúdo de cada um (usando os campos `valido` e `erro_ingestao` definidos em T01) e devolve um `ResultadoIngestao` com o split válidos/inválidos. A função nunca levanta exceção — erros são registrados no próprio `Artefato`.
- **Affected modules:**
  - `src/sprint_auditor/modelos.py` — adição de `ResultadoIngestao`
  - `src/sprint_auditor/ingestao.py` — novo módulo com `ingerir_artefatos`
  - `tests/test_ingestao.py` — novo arquivo de testes
- **New files:** `src/sprint_auditor/ingestao.py`, `tests/test_ingestao.py`
- **Reused patterns:**
  - `Artefato.valido` e `Artefato.erro_ingestao` — campos previstos em T01 exatamente para este uso
  - `BaseModel` + `Field(default_factory=list)` — padrão de `modelos.py`
  - `model_copy(update=...)` — API idiomática do Pydantic v2 para cópia modificada (sem mutação do input)

> **Decision source:** CLAUDE.md (Python + Pydantic v2 + uv + pytest); campos `valido`/`erro_ingestao` em `modelos.py` (T01 Tech Spec, seção Data Model).

---

## Contracts

### `modelos.py` — adição de `ResultadoIngestao`

```python
class ResultadoIngestao(BaseModel):
    artefatos_validos: list[Artefato]    # conteudo stripped; valido=True
    artefatos_invalidos: list[Artefato]  # valido=False; erro_ingestao preenchido

    @property
    def tem_artefatos(self) -> bool:
        """Sinaliza ao score engine (T03) se há base para avaliação."""
        return len(self.artefatos_validos) > 0
```

### `src/sprint_auditor/ingestao.py`

```python
from sprint_auditor.modelos import Artefato, ResultadoIngestao

def ingerir_artefatos(artefatos: list[Artefato]) -> ResultadoIngestao:
    """Valida e normaliza artefatos.

    Para cada artefato:
    - Conteúdo vazio ou só whitespace → valido=False, erro_ingestao preenchido
    - Conteúdo válido → cópia com conteudo.strip()

    Nunca levanta exceção — erros são registrados no próprio Artefato.
    O input não é mutado.
    """
```

---

## Data Model

### `ResultadoIngestao`

| Campo | Tipo | Obrigatório | Padrão | Notas |
|---|---|---|---|---|
| `artefatos_validos` | `list[Artefato]` | sim | — | cada `Artefato` tem `valido=True` e `conteudo` stripped |
| `artefatos_invalidos` | `list[Artefato]` | sim | — | cada `Artefato` tem `valido=False` e `erro_ingestao` preenchido |
| `tem_artefatos` | `bool` | — | `@property` | `True` ↔ `len(artefatos_validos) > 0`; não serializado em `model_dump()` |

### Regra de validação de `Artefato`

| Condição no `conteudo` | Resultado |
|---|---|
| `""` (string vazia) | `valido=False`, `erro_ingestao="Conteúdo vazio ou ausente"` |
| só whitespace (`" "`, `"\n\t"`, etc.) | `valido=False`, `erro_ingestao="Conteúdo vazio ou ausente"` |
| qualquer outro valor | `valido=True`, `conteudo=conteudo.strip()` |

**Invariante:** `Artefato` em `artefatos_validos` tem sempre `valido=True` e `erro_ingestao=None`. `Artefato` em `artefatos_invalidos` tem sempre `valido=False` e `erro_ingestao` não-`None`. A função preserva o `id` original em ambos os casos (rastreabilidade).

---

## External Integrations

Nenhuma.

---

## Trade-offs e Alternativas Rejeitadas

**Decisão: `ResultadoIngestao` em `modelos.py`**
- Alternativa rejeitada: definir em `ingestao.py` como tipo de saída local
- Motivo: T05 (relatório) precisa saber quais artefatos falharam para renderizar o "error state". Definir em `modelos.py` expõe o conceito ao vocabulário central sem criar dependência circular — T05 importa de `modelos.py`, não de `ingestao.py`.
- Trade-off: `modelos.py` cresce, mas segue sendo o arquivo de contratos de domínio.
- Fonte: decisão do usuário nesta conversa.

**Decisão: `@property` em vez de `@computed_field` para `tem_artefatos`**
- Alternativa rejeitada: `@computed_field` (Pydantic v2) — incluiria `tem_artefatos` na serialização
- Motivo: o pipeline do MVP é puramente in-memory; `ResultadoIngestao` nunca é serializado. `@property` é mais simples e não adiciona import.
- Trade-off: `tem_artefatos` não aparece em `model_dump()` — irrelevante para o MVP.
- Fonte: SPEC ("ingestão automática / polling" está fora do escopo).

**Decisão: validação agnóstica ao tipo de artefato**
- Alternativa rejeitada: validação type-specific (ex: BOARD deve conter `[`)
- Motivo: acoplar T02 ao formato interno do seed quebra quando o formato muda. "Vazio ou whitespace" é o único critério inequívoco de ilegibilidade que não depende de convenção de formato.
- Trade-off: um BOARD com conteúdo `"ok"` passa — mas isso é responsabilidade de quem constrói o artefato (T06/seed), não de T02.
- Fonte: critério de aceitação T02 no Plan ("mal formatado ou vazio").

**Decisão: `model_copy(update=...)` em vez de criar novo `Artefato` do zero**
- Alternativa rejeitada: `Artefato(id=a.id, tipo=a.tipo, conteudo=..., ...)` — lista explícita de todos os campos
- Motivo: `model_copy` propaga automaticamente campos futuros; listar todos os campos manualmente quebra silenciosamente se T01 adicionar um campo opcional.
- Fonte: Pydantic v2 docs + padrão estabelecido em T01.

---

## Risks and Mitigations

| Risco | Impacto | Mitigação |
|---|---|---|
| T04 busca `trecho_fonte` no artefato original (não normalizado) e índices não batem | `trecho_fonte` aponta trecho errado, rastreabilidade quebra | T04 usa o `Artefato` normalizado retornado por T02 como fonte, nunca o input bruto; garantido pela sequência de pipeline T02→T03→T04 |
| `tem_artefatos` como `@property` não serializado | T05 não pode usar `model_dump()` para checar o sinal | T05 acessa `resultado.tem_artefatos` diretamente no Python; não há camada de serialização no MVP |
| Lista de entrada com `None` no lugar de `Artefato` | `AttributeError` em `artefato.conteudo` | Fora do escopo — `ingerir_artefatos` aceita `list[Artefato]` tipado; o type checker (mypy) bloqueia isso em tempo de desenvolvimento |

---

## Testing Plan

**Framework:** pytest. Fonte: CLAUDE.md (`uv run pytest tests/ -v`).
**Padrão de organização:** classes agrupando casos por cenário, conforme `tests/test_modelos.py`.

### `tests/test_ingestao.py` — 10 testes

```
class TestIngestaoHappyPath:
```
1. **Transcrição válida única**: 1 artefato com `conteudo="texto qualquer"` → `tem_artefatos=True`, `len(artefatos_validos)==1`, `artefatos_invalidos==[]`
2. **Dois tipos válidos**: board + transcrição com conteúdo não-vazio → `len(artefatos_validos)==2`, `artefatos_invalidos==[]`

```
class TestIngestaoArtefatosInvalidos:
```
3. **Conteúdo vazio**: `conteudo=""` → artefato em `artefatos_invalidos`, `valido=False`, `erro_ingestao is not None`
4. **Conteúdo só whitespace**: `conteudo="\n\t  "` → mesmo resultado que vazio (inválido)
5. **Mistura válido + inválido**: 1 artefato com conteúdo + 1 vazio → `len(artefatos_validos)==1`, `len(artefatos_invalidos)==1`, sem abort

```
class TestIngestaoSemArtefatos:
```
6. **Lista de entrada vazia**: `ingerir_artefatos([])` → `tem_artefatos=False`, ambas as listas vazias
7. **Todos inválidos**: 2 artefatos com `conteudo=""` → `tem_artefatos=False`, `len(artefatos_invalidos)==2`

```
class TestNormalizacao:
```
8. **Strip aplicado no válido**: `conteudo="  texto com bordas  "` → `artefatos_validos[0].conteudo == "texto com bordas"`

```
class TestGarantias:
```
9. **Sem mutação do input**: artefato original com `conteudo=""` mantém `valido=True` e `conteudo==""` após a chamada
10. **Rastreabilidade do erro**: artefato em `artefatos_invalidos` tem o mesmo `id` do artefato de entrada

**Total: 10 testes**

---

## Implementation Sequence

Cada passo = um commit coeso:

1. Adicionar `ResultadoIngestao` a `modelos.py` (após `Projeto`) → rodar `uv run mypy src/` para confirmar tipos
2. Criar `src/sprint_auditor/ingestao.py` com `ingerir_artefatos`
3. Criar `tests/test_ingestao.py` com 10 testes → `uv run pytest tests/test_ingestao.py -v` → todos passando
4. Rodar suíte completa → `uv run pytest tests/ -v` → 31 testes passando (21 T01 + 10 T02)
5. Rodar `uv run ruff check src/ tests/` + `uv run mypy src/` → zero warnings

---

## Conventions Applied (from CLAUDE.md)

- **Stack:** Python + uv + pytest + ruff + mypy
- **Layout:** `src/sprint_auditor/` + `tests/` espelhando a estrutura de `src/`
- **Modelagem:** Pydantic v2 (`BaseModel`, `Field`, `model_copy`)
- **Sem mutação:** cópias via `model_copy(update=...)` — o input nunca é alterado
- **Nunca levanta exceção:** erros registrados no modelo de retorno (consistente com "artefato ilegível → registra e continua" do CLAUDE.md)
- **Linguagem do código:** Português-Brasil (nomes de variáveis, funções, campos)
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
- [x] Nenhuma nova biblioteca introduzida (apenas Pydantic v2, já instalado em T01)
- [x] Convenções do CLAUDE.md citadas e respeitadas
