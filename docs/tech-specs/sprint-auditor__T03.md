# Tech Spec: Delivery Score Engine — `T03`

> **SPEC:** [`docs/specs/sprint-auditor.md`](../specs/sprint-auditor.md)
> **Plan:** [`docs/plans/sprint-auditor.md`](../plans/sprint-auditor.md) — task `T03`
> **Conventions applied:** `CLAUDE.md` (projeto) + regras globais do usuário
>
> Este documento detalha **como** entregar a tarefa. O **porquê** vive na SPEC; **o quê** e **em que ordem**, no Plan.

---

## Task Scope

- **Behavior delivered** (from Plan): Para cada update de um projeto, o sistema compara o progresso real dos artefatos com o esperado pelo template de fases e produz um `DeliveryScore` (0–100) — ou sinaliza "dados insuficientes" quando não há base.
- **SPEC stories/criteria covered:** Story 1 (score como pré-condição do alerta); Story 2 (histórico do score entre updates); Story 3 (fase e motivo do atraso); Behavior "Projeto no trilho" (score sem desvio); Behavior "Artefatos insuficientes" (não exibir número inventado)
- **Depends on:** T02 (`ResultadoIngestao`, `Artefato`, `DeliveryScore`, `fase_do_dia`, `progresso_esperado`)
- **External dependencies:** nenhuma

---

## Architecture

- **General approach:** T03 adiciona `src/sprint_auditor/score_engine.py` com três funções em camadas. A função pública `calcular_delivery_score` é a única entrada do pipeline — consome `ResultadoIngestao` de T02 e `dia_projeto` do `Update`, e devolve um `DeliveryScore` preenchido. Internamente, delega a extração de progresso real a `_extrair_progresso_board` (heurística de marcadores de board) e o cálculo do score a `calcular_score` (fórmula determinística).

- **Affected modules:**
  - `src/sprint_auditor/score_engine.py` — novo módulo com as três funções
  - `tests/test_score_engine.py` — novo arquivo de testes

- **New files:** `src/sprint_auditor/score_engine.py`, `tests/test_score_engine.py`

- **Reused patterns:**
  - `ResultadoIngestao.tem_artefatos` (property de T02) — guarda de "sem dados"
  - `progresso_esperado(fase, dia)` e `fase_do_dia(dia)` — funções de `template_fases.py` (T01)
  - `DeliveryScore(dados_suficientes=False)` — padrão de "dados insuficientes" definido em T01
  - `TipoArtefato.BOARD` — enum de `modelos.py`

> **Decision source:** CLAUDE.md (Python + Pydantic v2 + uv + pytest); contratos de `modelos.py` e `template_fases.py` (T01 Tech Spec); comportamento do pipeline definido no Plan; fórmula e estratégia de extração: decisão do usuário nesta conversa.

---

## Contracts

### `src/sprint_auditor/score_engine.py`

```python
import re
from sprint_auditor.modelos import Artefato, DeliveryScore, ResultadoIngestao, TipoArtefato
from sprint_auditor.template_fases import fase_do_dia, progresso_esperado


def _extrair_progresso_board(artefatos: list[Artefato]) -> int:
    """Extrai progresso real (0–100) a partir de marcadores nos artefatos de board.

    Pesos: [✓]=1.0, [~]=0.5, [✗]=0.0
    Fórmula: int(soma_pesos / total_itens * 100)

    Retorna 0 se nenhum artefato de board presente ou se nenhum marcador encontrado.
    Nunca levanta exceção.
    """


def calcular_score(progresso_real: int, fase: Fase, dia: int) -> DeliveryScore:
    """Calcula DeliveryScore a partir do progresso real e do esperado pelo template.

    Fórmula: max(0, min(100, int(progresso_real * 100 / progresso_esperado)))

    Args:
        progresso_real: percentual real extraído dos artefatos (0–100)
        fase: fase ativa do projeto
        dia: dia do projeto (1–15)

    Returns:
        DeliveryScore com dados_suficientes=True, valor calculado,
        scores_por_fase={fase: valor}

    Raises:
        KeyError: se (fase, dia) não é uma combinação válida do template
    """


def calcular_delivery_score(
    resultado_ingestao: ResultadoIngestao,
    dia: int,
) -> DeliveryScore:
    """Ponto de entrada do pipeline — produz o DeliveryScore de um update.

    Se não há artefatos válidos → DeliveryScore(dados_suficientes=False).
    Caso contrário: extrai progresso do board, calcula score via fórmula linear.

    Args:
        resultado_ingestao: saída de ingerir_artefatos (T02)
        dia: dia do projeto do update sendo avaliado (1–15)

    Returns:
        DeliveryScore preenchido ou com dados_suficientes=False
    """
```

---

## Data Model

### Mapeamento de marcadores de board

| Marcador | Peso |
|---|---|
| `[✓]` | 1.0 |
| `[~]` | 0.5 |
| `[✗]` | 0.0 |

**Fórmula de extração:**
```
progresso_real = int(soma_pesos / total_itens * 100)
```
Se `total_itens == 0` (nenhum marcador encontrado) → `progresso_real = 0`.

### Fórmula do score

```
valor = max(0, min(100, int(progresso_real * 100 / progresso_esperado)))
```

**Exemplos concretos:**

| progresso_real | progresso_esperado (dia) | valor |
|---|---|---|
| 38 | 60 (dia 6, Configuração) | 63 |
| 60 | 60 (dia 6, Configuração) | 100 |
| 0  | 60 (dia 6, Configuração) | 0 |
| 80 | 60 (dia 6, Configuração) | 100 ← capped |
| 83 | 100 (dia 3, Discovery)   | 83 |
| 0  | 25 (dia 9, Desenvolvimento) | 0 |

### Campos preenchidos por `calcular_score`

| Campo `DeliveryScore` | Valor |
|---|---|
| `dados_suficientes` | `True` |
| `valor` | fórmula acima (0–100) |
| `scores_por_fase` | `{fase_ativa: valor}` |

### Comportamento por cenário de artefatos

| Cenário | `dados_suficientes` | `valor` |
|---|---|---|
| Nenhum artefato válido (`tem_artefatos=False`) | `False` | `None` |
| Somente transcrição (sem board) | `True` | `calcular_score(0, fase, dia)` |
| Board com marcadores presentes | `True` | fórmula sobre os marcadores |
| Board sem nenhum marcador `[✓]/[~]/[✗]` | `True` | `calcular_score(0, fase, dia)` |

---

## External Integrations

Nenhuma.

---

## Trade-offs e Alternativas Rejeitadas

**Decisão: fórmula linear ratio em vez de gap-based**
- Alternativa rejeitada: `max(0, 100 - max(0, esperado - real))`
- Motivo: a fórmula ratio ("quanto do esperado foi atingido") é mais intuitiva para o destinatário do relatório: score 63 significa "atingimos 63% do que era esperado para hoje", não "perdemos 22 pontos". A alternativa gap-based penaliza menos gaps grandes (38pp de gap → score=78, o que parece "quase ok").
- Trade-off: a truncagem inteira perde frações (int(63.33) = 63); irrelevante para a demo.
- Fonte: decisão do usuário nesta conversa.

**Decisão: extração board-only; transcrição reservada para T04**
- Alternativa rejeitada: usar keywords da transcrição ("concluímos", "bloqueado") como sinal de progresso
- Motivo: (1) o sinal de bloqueio linguístico já está planejado como responsabilidade exclusiva do T04 (`CategoriaAlerta.BLOQUEIO_LINGUISTICO`); duplicar a leitura da transcrição em T03 acoplaria os dois módulos no mesmo sinal. (2) Marcadores de board (`[✓]/[~]/[✗]`) são objetivos; keywords de transcrição são ambíguas e requerem lista de termos que cresceria além do MVP.
- Trade-off: update com apenas transcrição recebe `valor=calcular_score(0, ...)` — score baixo, não "dados insuficientes". Isso é correto: há dados, eles simplesmente não mostram progresso mensurável em marcadores de board.
- Fonte: decisão do usuário nesta conversa; `CategoriaAlerta.BLOQUEIO_LINGUISTICO` em `modelos.py`.

**Decisão: `_extrair_progresso_board` retorna `int` (não `Optional[int]`)**
- Alternativa rejeitada: retornar `None` quando não há board, forçar `calcular_delivery_score` a tratar o Optional
- Motivo: o comportamento "sem board → real=0" é um contrato explícito (decidido acima). Retornar `int` elimina um Optional desnecessário dentro do mesmo módulo; o contrato fica no docstring.
- Trade-off: o chamador não pode distinguir "sem board" de "board mostra 0%". Para T04 (que precisa distinguir bloqueio de ausência), a informação vem da transcrição, não do score.
- Fonte: decisão do usuário + SPEC "nunca inventar um score" (a distinção que importa é dados_suficientes, não a fonte do 0%).

**Decisão: `calcular_score` é pública (sem underscore) e testável diretamente**
- Alternativa rejeitada: torná-la privada (`_calcular_score`) e testar apenas via `calcular_delivery_score`
- Motivo: o critério de aceitação do Plan ("dado progresso real de 38% e esperado de 60%") é uma asserção direta sobre a fórmula com inputs parametrizados — não sobre a extração. Expor `calcular_score` permite o teste de unidade parametrizado sem construir artefatos.
- Trade-off: leve expansão da API pública do módulo.
- Fonte: critério de aceitação T03 no Plan.

**Decisão: `scores_por_fase` populado apenas com a fase ativa do update**
- Alternativa rejeitada: popular `scores_por_fase` com todas as 4 fases (usando `None` para fases não ativas)
- Motivo: T03 calcula o score de um único update; cada update pertence a um único dia e, portanto, a uma única fase ativa. Populando apenas a fase ativa, o dict reflete exatamente o que foi medido. T05 agrega o histórico consultando `scores_por_fase` de updates consecutivos.
- Trade-off: `scores_por_fase` nunca tem mais de 1 entrada por update; agregação multi-fase é responsabilidade de T05/T06.
- Fonte: modelo `DeliveryScore` de T01 + sequência do Plan.

---

## Risks and Mitigations

| Risco | Impacto | Mitigação |
|---|---|---|
| `progresso_esperado(fase, dia)` levanta `KeyError` para combinação inválida | `calcular_delivery_score` propaga erro não tratado | `fase_do_dia(dia)` garante que `fase` é consistente com `dia`; ambos derivados de `dia_projeto` validado (1–15) pelo Pydantic em `Update`; não é possível passar combinação inválida via pipeline normal |
| Marcador `[✓]` usa caractere Unicode `✓` (U+2713) — regex deve ser literal, não ASCII | Marcadores não reconhecidos → `progresso_real=0` silenciosamente | Regex usa literais Unicode; seed usa os mesmos caracteres; coberto pelo teste 8 que valida `[✓][✓][~]` produzindo 83 |
| Truncagem inteira acumula drift quando múltiplos boards por update | Score ligeiramente diferente dependendo da ordem de processamento dos artefatos | Peso acumulado (`soma_pesos / total_itens`) garante que todos os boards do update são agregados antes da truncagem — não há drift por ordenação |
| Update com `dia_projeto` fora de 1–15 | `fase_do_dia` levanta `ValueError` | Pydantic valida `dia_projeto` em `Update` no momento da construção; impossível no pipeline normal |

---

## Testing Plan

**Framework:** pytest. Fonte: CLAUDE.md (`uv run pytest tests/ -v`).
**Padrão de organização:** classes agrupando por responsabilidade, conforme `tests/test_ingestao.py`.

### `tests/test_score_engine.py` — 12 testes

```
class TestCalcularDeliveryScore:
```
1. **Happy path — board com marcadores**: `ResultadoIngestao` com 1 artefato de board contendo `[✓][✗][~]` → `dados_suficientes=True`, `valor` calculado corretamente (int((1+0+0.5)/3*100) = 50), `scores_por_fase` não vazio
2. **Sem artefatos válidos**: `ResultadoIngestao` com `artefatos_validos=[]` → `dados_suficientes=False`, `valor=None`
3. **Somente transcrição (sem board)**: `ResultadoIngestao` com 1 artefato `TipoArtefato.TRANSCRICAO` → `dados_suficientes=True`, `valor=calcular_score(0, fase, dia).valor`

```
class TestCalcularScore:
```
4. **Critério SPEC — dia 6, Configuração**: `calcular_score(38, Fase.CONFIGURACAO, 6)` → `valor=63` (int(38*100/60)), `dados_suficientes=True`, `scores_por_fase={Fase.CONFIGURACAO: 63}`
5. **Progresso real igual ao esperado**: `calcular_score(60, Fase.CONFIGURACAO, 6)` → `valor=100`
6. **Progresso real zero**: `calcular_score(0, Fase.CONFIGURACAO, 6)` → `valor=0`
7. **Progresso real acima do esperado (cap)**: `calcular_score(80, Fase.CONFIGURACAO, 6)` → `valor=100` (não ultrapassa 100)
8. **scores_por_fase reflete fase ativa**: `calcular_score(38, Fase.CONFIGURACAO, 6)` → `scores_por_fase` tem exatamente a chave `Fase.CONFIGURACAO`

```
class TestExtrairProgressoBoard:
```
9. **Board com marcadores mistos**: artefato board com `[✓] A, [✓] B, [~] C` → `83` (int(2.5/3*100))
10. **Board com todos [✗]**: artefato board com `[✗] A, [✗] B, [✗] C` (seed U2) → `0`
11. **Lista vazia — sem artefatos**: `_extrair_progresso_board([])` → `0`
12. **Board sem marcadores reconhecíveis**: artefato board com conteúdo `"sem marcadores aqui"` → `0`

```
class TestEvolucaoHistorica:
```
_(usa artefatos do seed para exercitar o critério de aceitação 4 do Plan)_

13. **Score deteriora entre updates**: calcular score para U1 (dia=3, board `[✓][✓][~]`) e U2 (dia=6, board `[✗][✗][✗]`); `score_u2.valor < score_u1.valor`

**Total: 13 testes**

> A suíte acumulada após T03: **44 testes** (31 de T01/T02 + 13 de T03).

---

## Implementation Sequence

Cada passo = um commit coeso:

1. Criar `src/sprint_auditor/score_engine.py` com `_extrair_progresso_board`, `calcular_score` e `calcular_delivery_score`
2. Criar `tests/test_score_engine.py` com 13 testes → `uv run pytest tests/test_score_engine.py -v` → todos passando
3. Rodar suíte completa → `uv run pytest tests/ -v` → 44 testes passando
4. Rodar `uv run ruff check src/ tests/` + `uv run mypy src/` → zero warnings

---

## Conventions Applied (from CLAUDE.md)

- **Stack:** Python + uv + pytest + ruff + mypy
- **Layout:** `src/sprint_auditor/` + `tests/` espelhando a estrutura de `src/`
- **Modelagem:** Pydantic v2 (`DeliveryScore`, `ResultadoIngestao`) — sem novos modelos nesta tarefa
- **Sem mutação:** `_extrair_progresso_board` e `calcular_score` são funções puras; `calcular_delivery_score` não modifica `resultado_ingestao`
- **Nunca levanta exceção no caminho normal:** o único `KeyError` possível é de combinação (fase, dia) inválida — impossível via pipeline validado pelo Pydantic
- **Linguagem do código:** Português-Brasil (nomes de funções, variáveis, docstrings)
- **Comentários:** nenhum por padrão — WHY não óbvio documentado em Trade-offs

---

## Ready to Code?

- [x] Arquitetura descrita com módulos e novos arquivos nomeados
- [x] Contratos (interfaces internas) em forma final com assinaturas completas e docstrings
- [x] Modelo de dados com tipos, campos, fórmulas e tabela de exemplos concretos
- [x] Trade-offs não triviais com alternativa rejeitada e fonte da decisão documentadas
- [x] Riscos conhecidos listados com mitigações
- [x] Plano de teste cobre happy path + casos de erro + borda + critério SPEC explícito
- [x] Sequência de implementação é executável sem perguntas de clarificação
- [x] Nenhuma nova biblioteca introduzida (apenas `re` da stdlib + Pydantic v2 já instalado)
- [x] Convenções do CLAUDE.md citadas e respeitadas
