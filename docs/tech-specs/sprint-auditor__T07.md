# Tech Spec: Melhorias de qualidade pré-demo — `T07`

> **SPEC:** [`docs/specs/sprint-auditor.md`](../specs/sprint-auditor.md)
> **Plan:** [`docs/plans/sprint-auditor.md`](../plans/sprint-auditor.md) — melhoria fora do plan original; não requer nova task no plan porque não adiciona módulo de pipeline.
> **Conventions applied:** `CLAUDE.md` (projeto) + regras globais do usuário
>
> Este documento detalha **como** entregar a tarefa. O **porquê** vive na SPEC; **o quê** e **em que ordem**, no Plan.

---

## Task Scope

- **Behavior delivered:** O sistema passa a produzir um Delivery Score com gradiente real (não binário), alertas com hipótese causal fusionada quando desvio e bloqueio co-ocorrem no mesmo update, um sinal de silêncio como terceiro tipo de detecção, e um modo CLI para decompor a origem de cada score.
- **SPEC stories/criteria covered:** Story 1 (causa provável anotada — agora como hipótese fusionada), Story 2 (histórico com gradiente narrativo), Story 4 (silêncio como informação — expandido para incluir silêncio temporal), Story 6 (causa com nível de confiança explícito)
- **Depends on:** T01–T06 (todos já implementados)
- **External dependencies:** nenhuma

---

## Problema diagnosticado

### P1 — Score binário

Fórmula atual em `score_engine.py:calcular_score`:
```python
valor = max(0, min(100, int(progresso_real * 100 / progresso_esperado)))
```
Quando `progresso_real = 0`, o score é sempre 0 — independentemente de quanto o template espera. Dia 6 (esperado=60%) e dia 9 (esperado=25%) produzem o mesmo score zero, apagando qualquer sinal de que o gap encolheu.

Demo atual: `83 → 0 → 0`. Demo nova: `83 → 40 → 75 → 50`.

### P2 — Alertas independentes sem hipótese

`analisar_alertas` executa os 3 detectores de forma independente. Quando DESVIO_LIMIAR e BLOQUEIO_LINGUISTICO disparam no mesmo update, o sistema retorna 2 alertas separados — o board e a transcrição nunca são conectados em uma hipótese causal.

### P3 — Sinal de silêncio ausente

Nenhum detector observa lacuna temporal entre updates. Um squad que para de aparecer não gera sinal.

### P4 — Score é caixa-preta

Não há como ver a decomposição `fase → esperado → real → gap → score` sem ler o código.

### Extra — frase do entrevistador hardcoded

`demo_pipeline.py:_gerar_contraste` inclui a frase `"isso é exatamente o que a gente precisa olhar na sexta da semana 1"` hardcoded no output — isso coloca palavras na boca do entrevistador antes da conversa.

---

## Architecture

- **General approach:** T07 é uma melhoria horizontal — toca 8 arquivos existentes e cria 2 novos (`explain.py` e `tests/test_explain.py`). Não adiciona módulo de pipeline. Todas as mudanças são localizadas e seguem os contratos já estabelecidos em T01–T06.

- **Affected modules:**
  - `src/sprint_auditor/modelos.py` — novos campos em `DeliveryScore` e `Alerta`; nova categoria em `CategoriaAlerta`
  - `src/sprint_auditor/score_engine.py` — nova fórmula em `calcular_score`
  - `src/sprint_auditor/alert_engine.py` — fusão de alertas; novo detector de silêncio
  - `src/sprint_auditor/relatorio.py` — exibição de `hipotese_causal` e `CategoriaAlerta.SILENCIO`
  - `src/sprint_auditor/seed.py` — adição de Update 4 (dia 12, recovery parcial)
  - `src/sprint_auditor/demo_pipeline.py` — remoção de frase hardcoded
  - `pyproject.toml` — novo script `sprint-auditor-explain`

- **New files:**
  - `src/sprint_auditor/explain.py` — CLI `sprint-auditor-explain --update N`
  - `tests/test_explain.py` — testes do modo explain

- **Reused patterns:**
  - Sentinel `"sistema"` para `artefato_fonte_id` do alerta SILENCIO — fonte meta, não artefato real
  - `_processar_update` de `demo_pipeline.py` reutilizado em `explain.py` para reconstruir o estado processado

> **Decision source:** CLAUDE.md (Python + Pydantic v2 + uv + pytest); contratos de `modelos.py` (T01); padrão de detectores em `alert_engine.py` (T04); padrão de scripts em `pyproject.toml`.

---

## Contracts

### `src/sprint_auditor/modelos.py` — mudanças de schema

```python
class CategoriaAlerta(str, Enum):
    DESVIO_LIMIAR = "desvio_limiar"
    DETERIORACAO_CONSISTENTE = "deterioracao_consistente"
    BLOQUEIO_LINGUISTICO = "bloqueio_linguistico"
    SILENCIO = "silencio"          # novo — T07


class DeliveryScore(BaseModel):
    dados_suficientes: bool
    valor: Optional[int] = Field(None, ge=0, le=100)
    scores_por_fase: dict[Fase, Optional[int]] = Field(default_factory=dict)
    progresso_real: Optional[int] = Field(None, ge=0, le=100)       # novo — T07
    progresso_esperado: Optional[int] = Field(None, ge=0, le=100)   # novo — T07


class Alerta(BaseModel):
    categoria: CategoriaAlerta
    fase: Fase
    dia_projeto: int = Field(ge=1, le=15)
    gap_pp: Optional[float] = None
    causa_provavel: str
    hipotese_causal: Optional[str] = None   # novo — T07; presente quando DESVIO+BLOQUEIO fusionados
    nivel_confianca: NivelConfianca
    acao_sugerida: str
    artefato_fonte_id: str
    trecho_fonte: str
```

Invariante preservada em `DeliveryScore`: `dados_suficientes=True → valor not None`. Os novos campos `progresso_real` e `progresso_esperado` são opcionais e preenchidos apenas quando `dados_suficientes=True`.

### `src/sprint_auditor/score_engine.py` — nova fórmula

```python
def calcular_score(progresso_real: int, fase: Fase, dia: int) -> DeliveryScore:
    """Nova fórmula gap-based (T07):
    gap_pp = max(0, progresso_esperado(fase, dia) - progresso_real)
    valor = max(0, 100 - gap_pp)

    Popula progresso_real e progresso_esperado no DeliveryScore para o modo explain.

    Args:
        progresso_real: percentual real extraído dos artefatos (0–100)
        fase: fase ativa do projeto
        dia: dia do projeto (1–15)

    Returns:
        DeliveryScore com dados_suficientes=True, valor calculado,
        scores_por_fase={fase: valor}, progresso_real e progresso_esperado preenchidos.

    Raises:
        KeyError: se (fase, dia) não é uma combinação válida do template
    """
```

### `src/sprint_auditor/alert_engine.py` — novos contratos

```python
LIMIAR_SILENCIO: int = 2  # novo — gap de dias > LIMIAR_SILENCIO dispara SILENCIO

TEMPLATE_HIPOTESE: str = (
    "Fase {fase} travada em {progresso_real}% no dia {dia}. "
    "Hipótese: dependência externa — sinalizado na transcrição "
    "('{trecho_bloqueio}'). "
    "Escalar para o FDE Lead pedir intervenção do sponsor do cliente."
)


def _detectar_silencio(
    update_atual: Update,
    updates_anteriores: list[Update],
) -> Optional[Alerta]:
    """Retorna Alerta SILENCIO se gap de dias entre o último update anterior
    e update_atual for > LIMIAR_SILENCIO.

    Requer pelo menos 1 update anterior. Retorna None se lista vazia.
    artefato_fonte_id = "sistema"
    trecho_fonte = f"Sem update há {gap} dias (último: dia {ultimo_dia})"
    Nunca levanta exceção.

    Args:
        update_atual: update sendo avaliado
        updates_anteriores: updates do mesmo projeto em ordem crescente de numero

    Returns:
        Alerta com categoria SILENCIO, ou None
    """


def analisar_alertas(
    update_atual: Update,
    updates_anteriores: list[Update],
) -> list[Alerta]:
    """Regras adicionadas em T07:
    - _detectar_silencio é chamado sempre (retorna None se não há anteriores)
    - Fusão: se DESVIO_LIMIAR e BLOQUEIO_LINGUISTICO disparam no mesmo update,
      produz 1 alerta DESVIO_LIMIAR com hipotese_causal preenchida via TEMPLATE_HIPOTESE;
      BLOQUEIO_LINGUISTICO NÃO é incluído separadamente na lista retornada.
    - SILENCIO é sempre listado separadamente (não sofre fusão).

    Ordem de saída: [DESVIO_LIMIAR_fusionado_ou_normal, DETERIORACAO, BLOQUEIO_standalone, SILENCIO]
    Lista vazia = projeto no trilho neste update.
    """
```

### `src/sprint_auditor/explain.py` — novo módulo

```python
from sprint_auditor.modelos import Update

_LARGURA_LINHA: int = 44


def decompor_score(update: Update) -> str:
    """Formata a decomposição do score de um update como texto puro.

    Requer update.score not None.
    Exibe: número, dia, fase, progresso_esperado, progresso_real, gap, score, limiar, status, alertas.

    Args:
        update: update com score preenchido (T03 executou)

    Returns:
        String multiline sem trailing newline.
        Retorna mensagem de erro se update.score is None ou dados_suficientes=False.
    """


def main_explain() -> None:
    """CLI entry point — registrado em pyproject.toml como sprint-auditor-explain.

    Uso: sprint-auditor-explain --update N
    Carrega seed, executa pipeline completo, exibe decomposição do update N.
    Imprime erro e sai se N não existe.
    """
```

---

## Data Model

### Nova fórmula do score

| Passo | Fórmula |
|---|---|
| Gap (inteiro) | `gap_pp = max(0, progresso_esperado(fase, dia) - progresso_real)` |
| Score | `valor = max(0, 100 - gap_pp)` |

**Por que gap-based em vez de ratio:**
- Fórmula anterior `int(real * 100 / esperado)` produz 0 sempre que `real=0`, sem diferenciar "esperado=60%" de "esperado=25%"
- A nova fórmula preserva a informação de que o gap encolheu: dia 9 (gap=25 pp) é melhor do que dia 6 (gap=60 pp) mesmo com progresso real idêntico (0%)
- Score continua sendo 0–100, com `progresso_real = progresso_esperado → score = 100`

**Tabela de exemplos concretos (seed Alpha Corp):**

| Update | Dia | Fase | Real | Esperado | Gap | Score (novo) | Score (antigo) |
|---|---|---|---|---|---|---|---|
| U1 | 3 | Discovery | 83% | 100% | 17 pp | **83** | 83 |
| U2 | 6 | Configuração | 0% | 60% | 60 pp | **40** | 0 |
| U3 | 9 | Desenvolvimento | 0% | 25% | 25 pp | **75** | 0 |
| U4 | 12 | Desenvolvimento | 50% | 100% | 50 pp | **50** | — |

Arco da demo: `83 → 40 → 75 → 50` (caiu, gap encolheu temporariamente, recovery insuficiente no prazo final).

### Campos novos em `DeliveryScore`

| Campo | Tipo | Preenchido quando | Uso |
|---|---|---|---|
| `progresso_real` | `Optional[int]` | `dados_suficientes=True` | explain mode, fusão de alertas |
| `progresso_esperado` | `Optional[int]` | `dados_suficientes=True` | explain mode, gap_pp em alert_engine |

### Fusão de alertas (P2)

Condição de fusão: `DESVIO_LIMIAR` e `BLOQUEIO_LINGUISTICO` disparam **no mesmo update**.

| Campo do alerta fusionado | Valor |
|---|---|
| `categoria` | `DESVIO_LIMIAR` |
| `causa_provavel` | texto original do DESVIO_LIMIAR |
| `hipotese_causal` | `TEMPLATE_HIPOTESE` preenchido com slots |
| `acao_sugerida` | `"Bloqueio externo confirmado por sinal linguístico → escalar para o FDE Lead"` |
| `nivel_confianca` | `NivelConfianca.ALTO` |
| `artefato_fonte_id` | artefato board (fonte do DESVIO_LIMIAR) |
| `trecho_fonte` | trecho do board |

O alerta de `BLOQUEIO_LINGUISTICO` **não** é adicionado à lista quando fusão ocorre.

Slots do `TEMPLATE_HIPOTESE`:
- `{fase}` → `alerta_desvio.fase.value`
- `{progresso_real}` → `update_atual.score.progresso_real`
- `{dia}` → `update_atual.dia_projeto`
- `{trecho_bloqueio}` → `alerta_bloqueio.trecho_fonte`

### Sinal de silêncio (P3)

| Campo | Valor |
|---|---|
| `categoria` | `CategoriaAlerta.SILENCIO` |
| `nivel_confianca` | `NivelConfianca.MEDIO` |
| `artefato_fonte_id` | `"sistema"` (sentinel — fonte é ausência de artefato) |
| `trecho_fonte` | `f"Sem update há {gap} dias (último: dia {ultimo_dia})"` |
| `gap_pp` | `None` |
| `hipotese_causal` | `None` |
| `acao_sugerida` | `"Contatar FDE Lead para status — squad sem sinal há {gap} dias"` |

Limiar: `gap > LIMIAR_SILENCIO` onde `LIMIAR_SILENCIO = 2` dias.

### Update 4 do seed (recovery parcial)

```python
# Dia 12 — Desenvolvimento — acesso SAP liberado, setup parcial
artefato_u4_board = Artefato(
    id="art-u4-board",
    tipo=TipoArtefato.BOARD,
    conteudo=(
        "Desenvolvimento: [✓] Acesso ao ambiente SAP liberado, "
        "[~] Setup do agente IA em progresso, [✗] Integração com CRM bloqueada"
    ),
    dia_projeto=12,
)

artefato_u4_transcricao = Artefato(
    id="art-u4-transcricao",
    tipo=TipoArtefato.TRANSCRICAO,
    conteudo=(
        "O acesso SAP foi liberado na quarta-feira. O agente IA está sendo "
        "configurado mas com atraso em relação ao cronograma original. "
        "A integração com CRM ainda está pendente — estamos correndo contra o prazo."
    ),
    dia_projeto=12,
)
# progresso_real = int((1.0 + 0.5 + 0.0) / 3 * 100) = 50%
# gap = max(0, 100 - 50) = 50 pp
# score = max(0, 100 - 50) = 50
```

Transcrição U4 não contém nenhum padrão de `PADROES_BLOQUEIO` → sem `BLOQUEIO_LINGUISTICO` em U4 → sem fusão em U4.

### Tabela de alertas por update (estado final)

| Update | Score | DESVIO_LIMIAR | Fusionado? | BLOQUEIO | DETERIORACAO | SILENCIO |
|---|---|---|---|---|---|---|
| U1 (dia 3) | 83 | — | — | — | — | — (sem anterior) |
| U2 (dia 6) | 40 | ✓ | ✓ (com hipotese_causal) | fusionado | — | ✓ (gap=3>2) |
| U3 (dia 9) | 75 | — | — | ✓ (standalone) | — | ✓ (gap=3>2) |
| U4 (dia 12) | 50 | ✓ | — | — | — | ✓ (gap=3>2) |

### Output do modo explain (Update #2)

```
════════════════════════════════════════════
Decomposição do Score — Update #2 (Dia 6)
════════════════════════════════════════════
  Fase:               configuracao
  Progresso esperado:  60%
  Progresso real:       0%
  Gap:                 60 pp
  Score (100 - gap):   40/100
  Limiar de desvio:    70
  Status:              ⚠ ABAIXO DO LIMIAR
  Alertas gerados:     2 (DESVIO_LIMIAR, SILENCIO)
════════════════════════════════════════════
```

### Output do modo explain (Update #1)

```
════════════════════════════════════════════
Decomposição do Score — Update #1 (Dia 3)
════════════════════════════════════════════
  Fase:               discovery
  Progresso esperado: 100%
  Progresso real:      83%
  Gap:                 17 pp
  Score (100 - gap):   83/100
  Limiar de desvio:    70
  Status:              ✓ NO TRILHO
  Alertas gerados:     0
════════════════════════════════════════════
```

### `pyproject.toml` — novo script

```toml
[project.scripts]
sprint-auditor-demo = "sprint_auditor.demo_pipeline:main"
sprint-auditor-explain = "sprint_auditor.explain:main_explain"   # novo — T07
```

---

## External Integrations

Nenhuma.

---

## Trade-offs e Alternativas Rejeitadas

**Decisão: fórmula gap-based `100 - gap_pp` em vez de ratio `real/esperado * 100`**
- **Alternativa rejeitada:** manter a fórmula ratio com floor diferente de 0 (e.g., `max(30, int(real/esperado*100))`)
- **Motivo:** floor arbitrário (30, 20, etc.) é mais difícil de explicar e introduz um "zero ajustado" que ainda não carrega a informação do gap real. A fórmula gap-based tem semântica direta: "quantos pontos percentuais faltam para estar no trilho". Quando o gap encolhe (dia 9: gap=25 pp vs. dia 6: gap=60 pp), o score reflete isso naturalmente.
- **Trade-off:** score pode subir mesmo sem progresso real, se o template esperava menos naquele dia — é uma medida relativa ao benchmark, não absoluta. Para a demo, isso é uma feature, não um bug (conta a história do gap).
- **Fonte:** instrução do usuário nesta conversa.

**Decisão: fusão produz 1 alerta DESVIO_LIMIAR com campo `hipotese_causal`; não cria nova categoria**
- **Alternativa rejeitada:** criar `CategoriaAlerta.DESVIO_COM_HIPOTESE` ou alterar a lógica de ordenação para mostrar o alerta fusionado diferente
- **Motivo:** o alerta fusionado ainda é fundamentalmente um DESVIO_LIMIAR — a hipótese é enriquecimento, não uma categoria nova. Criar uma nova categoria quebraria a ordenação, os labels do relatório e toda a suíte de testes sem benefício semântico. Campo opcional `hipotese_causal` é uma extensão não-breaking do schema Pydantic.
- **Trade-off:** o field `hipotese_causal` é `Optional[str]` e fica `None` em alertas não-fusionados — o relatório deve checá-lo explicitamente.
- **Fonte:** instrução do usuário nesta conversa.

**Decisão: SILENCIO usa `artefato_fonte_id = "sistema"` (sentinel) em vez de tornar o campo Optional**
- **Alternativa rejeitada:** `artefato_fonte_id: Optional[str]` e `trecho_fonte: Optional[str]` em `Alerta`
- **Motivo:** tornar esses campos opcionais quebraria todos os alertas existentes (que sempre têm fonte) e exigiria checar `None` em `_formatar_alerta`. O sentinel `"sistema"` é autoexplicativo no output e não quebra o schema. O princípio "todo alerta é rastreável" se mantém — a fonte do SILENCIO é o próprio sistema, rastreável pela ausência de artefatos.
- **Fonte:** SPEC "todo alerta é rastreável"; contrato de `Alerta` em T01.

**Decisão: `explain.py` re-executa o pipeline via `_processar_update` em vez de deserializar estado**
- **Alternativa rejeitada:** serializar o projeto processado em JSON/pickle e o explain ler de lá
- **Motivo:** o seed é sintético e determinístico — re-executar o pipeline é instantâneo e não exige infraestrutura de persistência. Adicionar serialização seria over-engineering para um MVP de demo.
- **Trade-off:** se o seed mudar, explain reflete automaticamente (vantagem). Se o pipeline for lento (não é), explain seria lento também.
- **Fonte:** CLAUDE.md ("não adiciona features além do necessário"); instrução do usuário "não precisa estar bonito, precisa existir".

**Decisão: remoção completa da frase hardcoded em `_gerar_contraste`; não substituída por variante**
- **Alternativa rejeitada:** substituir por outra frase editorial diferente
- **Motivo:** o output da demo deve ser factual. Qualquer frase que antecipa a reação do entrevistador é uma aposta — se ele não reagir assim, cria desconforto. O contraste numérico (antecipação em dias) fala por si.
- **Fonte:** instrução explícita do usuário nesta conversa.

---

## Risks and Mitigations

| Risco | Impacto | Mitigação |
|---|---|---|
| Score de U3 (75) acima do limiar (70) → DESVIO_LIMIAR não dispara em U3 | Demo pode parecer inconsistente ("por que o terceiro update não tem desvio?") | O BLOQUEIO_LINGUISTICO e o SILENCIO ainda disparam em U3 — o relatorio mostra que o projeto está em alerta mesmo sem cruzar o limiar de score |
| `DETERIORACAO_CONSISTENTE` nunca dispara com o arco 83→40→75→50 (sem 2 quedas consecutivas acima do limiar) | Um tipo de alerta some da demo | DETERIORACAO existia no arco antigo (0→0) que já era problemático. Com o novo arco, o detector permanece no código mas não é exercitado pelo seed — documentar no relatório como "detector disponível" |
| `progresso_real` em `DeliveryScore` fica `None` para updates sem board (somente transcrição) | `explain.py` recebe `None` para exibir | `decompor_score` verifica `progresso_real is None` e exibe "–" no lugar de crash |
| Limiar SILENCIO=2 dias dispara em todos os updates U2–U4 (todos têm gap=3 dias) | Demo mostra SILENCIO repetidamente — pode parecer barulhento | Isso é o comportamento correto: o squad SÓ aparece a cada 3 dias, o que já é sinal de squad pouco visível. Documentar na apresentação verbal que "gaps de 3 dias já disparam o radar de silêncio — em projetos saudáveis os updates são diários" |
| Fusão de alertas muda a contagem de alertas em `test_alert_engine.py` (de 3 para 2 em U2) | Testes existentes falham | Atualizar testes explicitamente como parte da sequência de implementação |
| `explain.py` importa `_processar_update` de `demo_pipeline.py` (função privada) | Acoplamento a detalhe interno | `_processar_update` é privada por convenção (underscore) mas não é um detalhe frágil — é o núcleo do pipeline. Dado que `explain.py` é um CLI de demo no mesmo pacote, o acoplamento é aceitável. Alternativa (mover para `pipeline_core.py`) seria over-engineering. |

---

## Testing Plan

**Framework:** pytest. Fonte: CLAUDE.md (`uv run pytest tests/ -v`).

### Testes a atualizar em `tests/test_score_engine.py`

Os seguintes testes existentes mudam de valor esperado:

| Teste | Valor antigo | Valor novo |
|---|---|---|
| `calcular_score(0, Fase.CONFIGURACAO, 6)` | `valor=0` | `valor=40` |
| `calcular_score(38, Fase.CONFIGURACAO, 6)` | `valor=63` | `valor=78` |
| `TestEvolucaoHistorica` — U2 < U1 | `0 < 83` | `40 < 83` (mantém) |

Novos testes a adicionar:

```
class TestCalcularScore (adições T07):
```
14. **Gradiente: real=0, esperado=25 → valor=75** — `calcular_score(0, Fase.DESENVOLVIMENTO, 9)` → `valor=75`, não 0 (valida que gap encolhido produz score maior)
15. **Gradiente: real=50, esperado=100 → valor=50** — `calcular_score(50, Fase.DESENVOLVIMENTO, 12)` → `valor=50`
16. **progresso_real armazenado** — `calcular_score(38, Fase.CONFIGURACAO, 6)` → `score.progresso_real == 38`
17. **progresso_esperado armazenado** — `calcular_score(38, Fase.CONFIGURACAO, 6)` → `score.progresso_esperado == 60`
18. **Gap negativo → cap em 0** — `calcular_score(80, Fase.CONFIGURACAO, 6)` → `gap = max(0, 60-80) = 0`, `valor=100`

### Testes a atualizar em `tests/test_alert_engine.py`

- `_detectar_desvio_limiar` — atualizar `gap_pp` esperado (novo cálculo: `esperado - real` em vez de `esperado * (1 - score/100)`)
- `analisar_alertas` — atualizar contagem de alertas em U2: de 3 para 2 (DESVIO_LIMIAR fusionado + SILENCIO) quando DESVIO e BLOQUEIO co-ocorrem

Novos testes a adicionar:

```
class TestDetectarSilencio:
```
19. **Happy path — gap > limiar**: update_atual.dia=6, updates_anteriores=[Update(dia=3)] → Alerta com `categoria=SILENCIO`, `artefato_fonte_id="sistema"`
20. **Abaixo do limiar — gap = limiar**: update_atual.dia=5, updates_anteriores=[Update(dia=3)] → `None` (gap=2, não > 2)
21. **Sem anteriores**: `_detectar_silencio(update, [])` → `None`
22. **Usa último update anterior para calcular gap**: updates_anteriores=[U(dia=3), U(dia=5)] → gap = atual.dia - 5 (não - 3)

```
class TestFusaoAlertas:
```
23. **Fusão: DESVIO + BLOQUEIO → 1 alerta**: update com score=40 (abaixo de 70) e transcrição com padrão de bloqueio → `analisar_alertas` retorna lista sem `CategoriaAlerta.BLOQUEIO_LINGUISTICO` separado; o alerta DESVIO_LIMIAR tem `hipotese_causal not None`
24. **Fusão popula hipotese_causal com trecho**: `hipotese_causal` contém o trecho casado da transcrição
25. **Sem fusão quando DESVIO sem BLOQUEIO**: update com score=40, transcrição sem padrão → lista contém 1 DESVIO_LIMIAR com `hipotese_causal=None`
26. **Sem fusão quando BLOQUEIO sem DESVIO**: update com score=75 (acima de 70) e transcrição com bloqueio → lista contém 1 BLOQUEIO_LINGUISTICO como standalone; sem hipotese_causal
27. **SILENCIO não é fusionado**: update com DESVIO+BLOQUEIO+SILENCIO → lista contém 2 alertas: [DESVIO_fusionado, SILENCIO]

### Testes a atualizar em `tests/test_modelos.py`

28. **DeliveryScore aceita novos campos**: `DeliveryScore(dados_suficientes=True, valor=40, progresso_real=0, progresso_esperado=60)` → sem ValidationError
29. **Alerta aceita hipotese_causal**: `Alerta(..., hipotese_causal="Fase travada...")` → sem ValidationError

### Testes a atualizar em `tests/test_seed.py`

30. **Seed tem 4 updates**: `len(projeto.updates) == 4`
31. **U4 está no dia 12**: `projeto.updates[-1].dia_projeto == 12`
32. **U4 tem board e transcrição**: U4 tem 1 artefato BOARD + 1 TRANSCRICAO

### Testes a atualizar em `tests/test_demo_pipeline.py`

33. **Sem frase hardcoded**: `_gerar_contraste(projeto)` não contém `"isso é exatamente"` na string retornada
34. **4 updates processados**: `executar_demo()` gera output com `Update #4`

### Novos testes em `tests/test_explain.py`

```
class TestDecomporScore:
```
35. **Happy path — U2**: update com score(valor=40, progresso_real=0, progresso_esperado=60) → output contém "40/100", "60 pp", "ABAIXO DO LIMIAR"
36. **Update no trilho — U1**: update com score(valor=83) → output contém "NO TRILHO"
37. **Score None**: update com score=None → output contém mensagem de erro sem crash

```
class TestMainExplain (integração):
```
38. **--update 2 retorna output válido**: `main_explain()` com `sys.argv = ["explain", "--update", "2"]` → não levanta exceção; output contém "Update #2"
39. **--update inexistente exibe erro**: `sys.argv = ["explain", "--update", "99"]` → imprime mensagem de erro; não levanta exceção

**Total novos/alterados:** ~26 testes. Suíte acumulada esperada: ~80 testes (54 existentes + 26).

---

## Implementation Sequence

Cada passo = um commit coeso:

1. **`modelos.py`** — adicionar `progresso_real`, `progresso_esperado` em `DeliveryScore`; `hipotese_causal` em `Alerta`; `SILENCIO` em `CategoriaAlerta`. Rodar `uv run pytest tests/test_modelos.py` — testes existentes não devem quebrar (campos com default)
2. **`score_engine.py`** — nova fórmula gap-based; popular `progresso_real` e `progresso_esperado`. Rodar `uv run pytest tests/test_score_engine.py` — os testes de valor (63→78, 0→40) vão falhar
3. **Atualizar `tests/test_score_engine.py`** — corrigir valores esperados; adicionar testes 14–18. Rodar → todos passando
4. **`alert_engine.py`** — adicionar `LIMIAR_SILENCIO`, `TEMPLATE_HIPOTESE`, `_detectar_silencio`; refatorar `analisar_alertas` para fusão. Rodar `uv run pytest tests/test_alert_engine.py` — testes de contagem de alertas vão falhar
5. **Atualizar `tests/test_alert_engine.py`** — corrigir contagens; adicionar testes 19–27. Rodar → todos passando
6. **`seed.py`** — adicionar U4 (dia 12, recovery parcial). Rodar `uv run pytest tests/test_seed.py` — testes de contagem vão falhar
7. **Atualizar `tests/test_seed.py`** — adicionar testes 30–32. Rodar → todos passando
8. **`relatorio.py`** — adicionar `CategoriaAlerta.SILENCIO` em `_ORDEM_CATEGORIA` e `_LABEL_CATEGORIA`; exibir `hipotese_causal` em `_formatar_alerta` (linha "Hipótese:" após "Causa:" quando presente). Rodar `uv run pytest tests/test_relatorio.py`
9. **`demo_pipeline.py`** — remover frase hardcoded de `_gerar_contraste`. Atualizar `tests/test_demo_pipeline.py` (testes 33–34). Rodar → todos passando
10. **Criar `src/sprint_auditor/explain.py`** com `decompor_score` e `main_explain`; criar `tests/test_explain.py` com testes 35–39. Rodar → todos passando
11. **`pyproject.toml`** — adicionar script `sprint-auditor-explain`
12. **Rodar suíte completa**: `uv run pytest tests/ -v` → todos passando
13. **Rodar lint e tipos**: `uv run ruff check src/ tests/` e `uv run mypy src/` → zero warnings
14. **Validação manual**: `uv run sprint-auditor-demo` — verificar arco `83 → 40 → 75 → 50` no output. `uv run sprint-auditor-explain --update 2` — verificar decomposição do Update #2

---

## Conventions Applied (from CLAUDE.md)

- **Stack:** Python + uv + pytest + ruff + mypy; sem novas dependências
- **Layout:** `src/sprint_auditor/` + `tests/` espelhando a estrutura de `src/`
- **Modelagem:** Pydantic v2 — extensões com campos opcionais são não-breaking por padrão
- **Sem mutação:** `calcular_score` permanece função pura; `_detectar_silencio` e a lógica de fusão são funções puras (não mutam `update` nem `updates_anteriores`)
- **Nunca levanta exceção no caminho normal:** `_detectar_silencio`, `decompor_score` e `main_explain` capturam estados inválidos com retorno de `None` ou mensagem de texto
- **Linguagem do código:** Português-Brasil (nomes, docstrings)
- **Comentários:** nenhum por padrão; WHY não óbvio documentado em Trade-offs acima

---

## Ready to Code?

- [x] Arquitetura descrita com módulos e novos arquivos nomeados
- [x] Contratos (interfaces internas) em forma final com assinaturas completas e docstrings
- [x] Modelo de dados com tipos, campos, fórmulas e tabelas de exemplos concretos
- [x] Trade-offs não triviais com alternativa rejeitada e fonte da decisão documentadas
- [x] Riscos conhecidos listados com mitigações
- [x] Plano de teste cobre happy path + casos de erro + borda + critério SPEC explícito
- [x] Sequência de implementação é executável sem perguntas de clarificação
- [x] Nenhuma nova biblioteca introduzida (apenas `argparse` da stdlib, já disponível)
- [x] Convenções do CLAUDE.md citadas e respeitadas
