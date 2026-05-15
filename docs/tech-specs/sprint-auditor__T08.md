# Tech Spec: Coerência narrativa da demo — `T08`

> **SPEC:** [`docs/specs/sprint-auditor.md`](../specs/sprint-auditor.md)
> **Plan:** [`docs/plans/sprint-auditor.md`](../plans/sprint-auditor.md) — melhoria fora do plan original; não requer nova task no plan porque não adiciona módulo de pipeline.
> **Conventions applied:** `CLAUDE.md` (projeto) + regras globais do usuário
>
> Este documento detalha **como** entregar a tarefa. O **porquê** vive na SPEC; **o quê** e **em que ordem**, no Plan.

---

## Task Scope

- **Behavior delivered:** O sistema passa a exibir hipótese causal em todos os updates com alerta (não só no #2), a eliminar o falso positivo de silêncio na cadência natural da demo, a mostrar um terceiro status "EM ALERTA" quando o score está acima do limiar mas há sinais ativos, e a exibir setas de tendência (↗/↘) no histórico para tornar a narrativa legível em 5 minutos.
- **SPEC stories/criteria covered:** Story 1 (causa provável anotada — agora em todos os alertas, não só fusionados), Story 2 (histórico com tendência explícita), Story 4 (silêncio como informação — sem falsos positivos no ritmo natural), Story 6 (causa com nível de confiança explícito)
- **Depends on:** T01–T07 (todos já implementados)
- **External dependencies:** nenhuma

---

## Problema diagnosticado

### P1 — Hipótese causal ausente nos Updates 3 e 4

`TEMPLATE_HIPOTESE` e `hipotese_causal` só são preenchidos no caminho de fusão de `analisar_alertas()` (linhas 313–331 de `alert_engine.py`), que exige `alerta_desvio and alerta_bloqueio` simultaneamente.

- **Update #3 (dia 9, score=75):** score está acima do limiar (75 ≥ 70) → `_detectar_desvio_limiar` retorna `None`; BLOQUEIO_LINGUISTICO dispara sozinho; fusão não ocorre; `hipotese_causal=None`; `acao_sugerida` cai no genérico "Investigar bloqueios na fase X".
- **Update #4 (dia 12, score=50):** score abaixo do limiar → DESVIO dispara; transcrição de U4 não contém nenhum padrão de `PADROES_BLOQUEIO` → BLOQUEIO não dispara; fusão não ocorre; `hipotese_causal=None`; mesma ação genérica.

O entrevistador compara U2 (hipótese explícita) com U3 e U4 (sem hipótese) e vê incoerência.

### P2 — SILENCIO dispara como falso positivo estrutural

`LIMIAR_SILENCIO = 2` faz com que qualquer gap > 2 dias entre updates dispare `SILENCIO`. Todos os gaps do seed são exatamente 3 dias (U1→U2: 3, U2→U3: 3, U3→U4: 3). Resultado: SILENCIO dispara nos Updates 2, 3 e 4 — o ritmo natural da demo vira alerta, não o silêncio genuíno.

Falso positivo em demo é pior que sinal a menos.

### P3 — Contradição de status no explain

`decompor_score()` em `explain.py:36` tem dois estados:
```python
status = "✓ NO TRILHO" if update.score.valor >= limiar_desvio else "⚠ ABAIXO DO LIMIAR"
```

Update #3: score=75 ≥ 70 → status "✓ NO TRILHO". Mas o output principal mostra `[BLOQUEIO]` com 2 alertas. A contradição é visível na mesma sessão de terminal: o entrevistador abre o explain de U3 e vê "no trilho" logo abaixo do `[BLOQUEIO]`.

### P4 — Histórico sem tendência

`_formatar_historico()` em `relatorio.py:199` marca todos os updates com alerta com `⚠`, mas não indica se o projeto está melhorando ou piorando:

```
Update #2 (Dia  6): ████░░░░░░  40/100  ⚠
Update #3 (Dia  9): ████████░░  75/100  ⚠
Update #4 (Dia 12): █████░░░░░  50/100  ⚠
```

Os três updates têm `⚠` idêntico — não dá para saber em 5 segundos que U3 foi recovery e U4 foi recaída.

---

## Architecture

- **General approach:** T08 é uma melhoria horizontal com 3 arquivos de produção afetados (`alert_engine.py`, `explain.py`, `relatorio.py`) e nenhum arquivo novo. Nenhum módulo de pipeline é adicionado. As mudanças são localizadas, seguem os contratos Pydantic já estabelecidos em T01–T07 e não quebram a interface pública de nenhum módulo.

- **Affected modules:**
  - `src/sprint_auditor/alert_engine.py` — `LIMIAR_SILENCIO` ajustado; dois novos templates; `_detectar_bloqueio_linguistico` e `_detectar_desvio_limiar` populam `hipotese_causal` nos casos standalone; `analisar_alertas` continua sobrescrevendo com `TEMPLATE_HIPOTESE` rico na fusão (comportamento T07 preservado)
  - `src/sprint_auditor/explain.py` — lógica de status: 2 estados → 3 estados
  - `src/sprint_auditor/relatorio.py` — `_formatar_historico` adiciona setas de tendência

- **New files:** nenhum

- **Reused patterns:**
  - `alerta.model_copy(update={...})` para sobrescrever `hipotese_causal` na fusão — padrão já estabelecido em `analisar_alertas` (T07)
  - Campo opcional `hipotese_causal: Optional[str]` em `Alerta` — já existe desde T07; nenhuma alteração de schema necessária
  - `_formatar_alerta()` em `relatorio.py` já exibe `hipotese_causal` quando não é `None` (linha 124–125) — zero mudança no formatador de alertas

> **Decision source:** CLAUDE.md (Python + Pydantic v2 + uv + pytest); contrato de `Alerta.hipotese_causal` em T07 (`docs/tech-specs/sprint-auditor__T07.md`); padrão de templates em `alert_engine.py`.

---

## Contracts

### `src/sprint_auditor/alert_engine.py` — mudanças de constantes e funções

```python
# Antes (T07):
LIMIAR_SILENCIO: int = 2

# Depois (T08):
LIMIAR_SILENCIO: int = 4
# Por que 4: todos os gaps do seed são 3 dias (cadência natural); LIMIAR=4 elimina
# o falso positivo estrutural sem remover o mecanismo para silêncios genuínos (>4 dias).


# Novos templates standalone:

TEMPLATE_HIPOTESE_BLOQUEIO_SIMPLES: str = (
    "Bloqueio identificado na transcrição: '{trecho_bloqueio}'. "
    "Hipótese: dependência externa não resolvida. "
    "Escalar para o FDE Lead pedir desbloqueio."
)

TEMPLATE_HIPOTESE_DESVIO_SIMPLES: str = (
    "Fase {fase} com apenas {progresso_real}% de progresso real contra "
    "{progresso_esperado}% esperado no dia {dia}. "
    "Hipótese: squad com capacidade reduzida ou bloqueio não declarado. "
    "Investigar com FDE Lead."
)
```

```python
def _detectar_bloqueio_linguistico(update: Update) -> Optional[Alerta]:
    """...(docstring existente preservada)...
    
    Mudança T08: popula hipotese_causal com TEMPLATE_HIPOTESE_BLOQUEIO_SIMPLES
    usando o trecho casado. A fusão em analisar_alertas pode sobrescrever
    hipotese_causal com TEMPLATE_HIPOTESE rico quando DESVIO co-ocorre.
    """
    # ...lógica existente...
    return Alerta(
        ...
        hipotese_causal=TEMPLATE_HIPOTESE_BLOQUEIO_SIMPLES.format(
            trecho_bloqueio=trecho_casado
        ),
    )
```

```python
def _detectar_desvio_limiar(update: Update) -> Optional[Alerta]:
    """...(docstring existente preservada)...
    
    Mudança T08: popula hipotese_causal com TEMPLATE_HIPOTESE_DESVIO_SIMPLES.
    A fusão em analisar_alertas pode sobrescrever com TEMPLATE_HIPOTESE rico
    quando BLOQUEIO co-ocorre.
    """
    # ...lógica existente até a construção do Alerta...
    return Alerta(
        ...
        hipotese_causal=TEMPLATE_HIPOTESE_DESVIO_SIMPLES.format(
            fase=fase.value,
            progresso_real=update.score.progresso_real,
            progresso_esperado=update.score.progresso_esperado,
            dia=update.dia_projeto,
        ),
    )
```

`analisar_alertas()` **não muda sua interface nem sua lógica de fusão.** Quando a fusão ocorre (DESVIO+BLOQUEIO), o `model_copy` já sobrescreve `hipotese_causal` com `TEMPLATE_HIPOTESE` rico — o novo campo mais simples nos alertas standalone é sobrescrito corretamente no caminho de fusão.

### `src/sprint_auditor/explain.py` — lógica de status (3 estados)

```python
# Antes (T07):
status = "✓ NO TRILHO" if update.score.valor >= limiar_desvio else "⚠ ABAIXO DO LIMIAR"

# Depois (T08):
if update.score.valor < limiar_desvio:
    status = "⚠ ABAIXO DO LIMIAR"
elif update.alertas:
    status = "⚡ EM ALERTA"
else:
    status = "✓ NO TRILHO"
```

Semântica dos três estados:

| Estado | Condição | Significado |
|---|---|---|
| `✓ NO TRILHO` | score ≥ 70 e sem alertas | Projeto no trilho, nenhum sinal ativo |
| `⚡ EM ALERTA` | score ≥ 70 mas há alertas | Acima do limiar de score mas com sinais — zona de intervenção preventiva |
| `⚠ ABAIXO DO LIMIAR` | score < 70 | Score cruzou o threshold de desvio |

"EM ALERTA" é o estado mais importante para a demo: é onde dá para intervir antes do colapso.

### `src/sprint_auditor/relatorio.py` — setas de tendência em `_formatar_historico`

```python
def _formatar_historico(updates: list[Update]) -> str:
    """...(docstring existente com adição):
    
    Mudança T08: quando o update tem score suficiente e há um update anterior
    também com score suficiente, exibe seta de tendência (↗ ↘ →) entre o
    score e o símbolo ⚠. Primeiro update nunca exibe seta (sem anterior).
    
    Formato novo:
        Update #1 (Dia  3): ████████░░  83/100
        Update #2 (Dia  6): ████░░░░░░  40/100  ↘ ⚠
        Update #3 (Dia  9): ████████░░  75/100  ↗ ⚠
        Update #4 (Dia 12): █████░░░░░  50/100  ↘ ⚠
    """
    linhas = ["Histórico de Delivery Score:"]
    score_anterior: Optional[int] = None

    for update in updates:
        dia_str = f"{update.dia_projeto:2d}"

        if update.score is None or not update.score.dados_suficientes:
            linha = f"  Update #{update.numero} (Dia {dia_str}): sem dados suficientes"
            score_anterior = None
        else:
            barra = _formatar_barra(update.score.valor)
            valor_str = f"{update.score.valor:3d}"
            linha = f"  Update #{update.numero} (Dia {dia_str}): {barra}  {valor_str}/100"

            if score_anterior is not None:
                if update.score.valor > score_anterior:
                    tendencia = "↗"
                elif update.score.valor < score_anterior:
                    tendencia = "↘"
                else:
                    tendencia = "→"
                linha += f"  {tendencia}"

            if update.alertas:
                linha += " ⚠"

            score_anterior = update.score.valor

        linhas.append(linha)

    return "\n".join(linhas)
```

Nota: quando `dados_suficientes=False`, `score_anterior` é resetado para `None` — o próximo update com dados não exibe seta (sem base válida de comparação).

---

## Data Model

Nenhuma mudança de schema de `Alerta` ou `DeliveryScore`. O campo `hipotese_causal: Optional[str]` já existe desde T07. As constantes `LIMIAR_SILENCIO`, `TEMPLATE_HIPOTESE_BLOQUEIO_SIMPLES` e `TEMPLATE_HIPOTESE_DESVIO_SIMPLES` são variáveis de módulo em `alert_engine.py`.

### Estado final dos alertas por update (após P1 + P2)

| Update | Score | DESVIO | BLOQUEIO | `hipotese_causal` | SILENCIO |
|---|---|---|---|---|---|
| U1 (dia 3) | 83 | — | — | — | — (sem anterior) |
| U2 (dia 6) | 40 | ✓ | ✓ (fusionado) | `TEMPLATE_HIPOTESE` rico | — (gap=3 ≤ 4) |
| U3 (dia 9) | 75 | — | ✓ (standalone) | `TEMPLATE_HIPOTESE_BLOQUEIO_SIMPLES` | — (gap=3 ≤ 4) |
| U4 (dia 12) | 50 | ✓ (standalone) | — | `TEMPLATE_HIPOTESE_DESVIO_SIMPLES` | — (gap=3 ≤ 4) |

### Output esperado do explain por update

**Update #3 (antes → depois):**
```
# Antes (T07)
  Status:              ✓ NO TRILHO
  Alertas gerados:     2

# Depois (T08)
  Status:              ⚡ EM ALERTA
  Alertas gerados:     1 (BLOQUEIO_LINGUISTICO)
```

**Update #4:**
```
# Depois (T08)
  Status:              ⚠ ABAIXO DO LIMIAR
  Alertas gerados:     1 (DESVIO_LIMIAR)
```

### Output esperado do histórico

```
Histórico de Delivery Score:
  Update #1 (Dia  3): ████████░░  83/100
  Update #2 (Dia  6): ████░░░░░░  40/100  ↘ ⚠
  Update #3 (Dia  9): ████████░░  75/100  ↗ ⚠
  Update #4 (Dia 12): █████░░░░░  50/100  ↘ ⚠
```

---

## External Integrations

Nenhuma.

---

## Trade-offs e Alternativas Rejeitadas

**Decisão: sempre popular `hipotese_causal` em BLOQUEIO e DESVIO standalone (não só na fusão)**
- **Alternativa rejeitada:** fusão generalizada — só gerar hipótese quando há 2+ sinais co-ocorrendo
- **Motivo:** Update #3 tem 1 sinal (BLOQUEIO) e Update #4 tem 1 sinal (DESVIO) após a correção do SILENCIO. Se a hipótese exigir 2+ sinais, os dois updates continuariam sem hipótese. A regra mais simples e robusta é: todo alerta com evidência suficiente (trecho para BLOQUEIO, dados de score para DESVIO) deve sempre carregar hipótese.
- **Trade-off:** a hipótese standalone é mais genérica ("dependência externa não resolvida") do que a fusionada ("dependência externa — sinalizado na transcrição"). A diferença de qualidade é intencional: reflete o nível de confiança de cada caso.
- **Fonte:** instrução explícita do usuário nesta conversa; opção "Sempre popular hipotese_causal" escolhida.

**Decisão: `LIMIAR_SILENCIO = 4` (não threshold relativo por fase)**
- **Alternativa rejeitada:** threshold relativo por fase (Discovery tolera gaps maiores, Desenvolvimento exige ritmo mais alto)
- **Motivo:** a alternativa correta conceitualmente exige lógica extra em `template_fases.py` e um mapeamento fase → limiar. Para a demo, o resultado prático é idêntico — todos os gaps do seed são 3 dias, então qualquer limiar ≥ 4 elimina o falso positivo. A troca de 1 linha (constante) é preferível a uma nova abstração.
- **Trade-off:** o mecanismo de SILENCIO fica inativo na demo (nenhum update do seed o dispara com LIMIAR=4). O mecanismo permanece correto para projetos com gaps genuinamente longos. Sinal a menos é aceitável; falso positivo em demo não é.
- **Fonte:** instrução do usuário ("falso positivo em demo é pior que sinal a menos"); opção "Aumentar LIMIAR_SILENCIO para 4" escolhida.

**Decisão: terceiro estado "EM ALERTA" em vez de mostrar alertas no explain**
- **Alternativa rejeitada:** exibir a lista de alertas abaixo do status (ex: `"✓ NO TRILHO — 1 alerta ativo"`)
- **Motivo:** o explain já mostra `Alertas gerados: N` — a informação já está presente. O problema é o status "✓ NO TRILHO" que contradiz "N alertas". A solução é corrigir o rótulo, não duplicar a informação de alertas.
- **Trade-off:** três estados em vez de dois exigem atualização de testes e da lógica da string.
- **Fonte:** instrução do usuário ("Score acima do limiar mas com 2 alertas → o status precisa refletir isso").

**Decisão: seta de tendência precede o `⚠` (formato `↘ ⚠`, não `⚠ ↘`)**
- **Alternativa rejeitada:** seta depois do `⚠` (`⚠ ↘`)
- **Motivo:** leitura da esquerda para direita: score → tendência → alerta. A tendência qualifica o número; o `⚠` é o indicador de alerta. Inverter coloca o diagnóstico antes da direção.
- **Fonte:** instrução do usuário ("↗ 75/100 ⚠ vs ↘ 50/100 ⚠").

---

## Risks and Mitigations

| Risco | Impacto | Mitigação |
|---|---|---|
| `TEMPLATE_HIPOTESE_DESVIO_SIMPLES` acessa `update.score.progresso_real` e `update.score.progresso_esperado` que podem ser `None` (se `dados_suficientes=False`) | `str.format()` lança `TypeError` ou exibe `None` | `_detectar_desvio_limiar` já retorna `None` quando `score is None` ou `dados_suficientes=False` (linhas 67–68 do arquivo atual) — os novos slots nunca são acessados em estado inválido |
| Testes de SILENCIO existentes com gap=3 falham após `LIMIAR_SILENCIO=4` | Suíte quebrada temporariamente | Passo 1 da sequência: atualizar testes antes de subir o limiar (ver Testing Plan) |
| `test_sem_fusao_quando_desvio_sem_bloqueio` e `test_sem_fusao_quando_bloqueio_sem_desvio` verificam `hipotese_causal=None` — falham com T08 | Suíte quebrada | Atualizar assertions para verificar `hipotese_causal is not None` e conteúdo do template |
| `test_seed_pipeline_u1_no_trilho_u2_u3_com_desvio` verifica "DESVIO_LIMIAR" em U3 — U3 passa a ter BLOQUEIO_LINGUISTICO | Falha em `test_relatorio.py` | Atualizar teste para verificar "BLOQUEIO_LINGUISTICO" em U3 |
| `test_historico_update_com_alerta_exibe_aviso` verifica `⚠` no histórico — seta de tendência agora precede o `⚠` | Potencial falha se o teste usa `endswith` | Verificar implementação do teste; ajustar para `assertIn("⚠", linha)` se necessário |
| `test_silencio_nao_sofre_fusao` usa gap=3 para disparar SILENCIO — após LIMIAR=4, gap=3 não dispara | Teste não testa mais o que pretende | Atualizar setup do teste para usar gap=5 (dia_atual=8, ultimo_dia=3) |

---

## Testing Plan

**Framework:** pytest. Fonte: CLAUDE.md (`uv run pytest tests/ -v`).

### Testes a atualizar em `tests/test_alert_engine.py`

**Classe `TestDetectarSilencio`:**

| Teste | Mudança |
|---|---|
| `test_gap_acima_limiar_dispara` | Gap=3 com LIMIAR=4 não dispara — mudar setup para gap=5 (dia_atual=8, ultimo_dia=3) |
| `test_gap_igual_limiar_nao_dispara` | Gap=2 ainda não dispara (correto), mas o boundary real é agora 4 — mudar setup para gap=4 (dia_atual=7, ultimo_dia=3) para documentar o novo boundary |
| `test_usa_ultimo_update_para_gap` | Verificar se gap no teste ainda é > 4; ajustar se necessário |

**Classe `TestFusaoAlertas`:**

| Teste | Mudança |
|---|---|
| `test_sem_fusao_quando_desvio_sem_bloqueio` | Mudar assertion de `hipotese_causal is None` para `hipotese_causal is not None`; verificar que contém `"% de progresso real"` (conteúdo de `TEMPLATE_HIPOTESE_DESVIO_SIMPLES`) |
| `test_sem_fusao_quando_bloqueio_sem_desvio` | Verificar se o teste checa `hipotese_causal=None`; se sim, mudar para `hipotese_causal is not None`; verificar que contém `"dependência externa não resolvida"` |
| `test_silencio_nao_sofre_fusao` | Ajustar gap no setup para > 4 dias (ex: gap=5) para continuar disparando SILENCIO |

**Novos testes na classe `TestFusaoAlertas`:**

```
T08-A: hipotese_causal de BLOQUEIO standalone contém trecho casado
  setup: update com score=75 (acima de 70) e transcrição com "aguardando aprovação"
  assert: alerta BLOQUEIO_LINGUISTICO retornado tem hipotese_causal contendo "aguardando aprovação"

T08-B: hipotese_causal de DESVIO standalone contém dados de score
  setup: update com score=40 (abaixo de 70) e transcrição sem padrão de bloqueio
  assert: alerta DESVIO_LIMIAR retornado tem hipotese_causal contendo progresso_real e progresso_esperado

T08-C: fusão sobrescreve hipotese_causal do DESVIO simples com o template rico
  setup: update com score=40 e transcrição com padrão de bloqueio
  assert: alerta fusionado tem hipotese_causal contendo "Hipótese: dependência externa — sinalizado na transcrição"
  assert: hipotese_causal NÃO contém "squad com capacidade reduzida" (conteúdo do template simples)
```

**Novos testes na classe `TestDetectarSilencio`:**

```
T08-D: gap=4 não dispara (novo boundary)
  setup: day_atual=7, ultimo_dia=3, gap=4
  assert: retorna None (gap ≤ LIMIAR_SILENCIO=4)

T08-E: gap=5 dispara (acima do novo limiar)
  setup: day_atual=8, ultimo_dia=3, gap=5
  assert: retorna Alerta com categoria=SILENCIO
```

### Testes a atualizar em `tests/test_explain.py`

| Teste | Mudança |
|---|---|
| `test_update_no_trilho` | Update com score=83 e **sem alertas** ainda deve retornar "NO TRILHO" — verificar que o teste não adiciona alertas ao update; adicionar assert explícito `"NO TRILHO" in output` |

**Novo teste:**

```
T08-F: update com score ≥ 70 e alertas → status "EM ALERTA"
  setup: Update com score.valor=75 (≥ 70) e alertas=[Alerta(...)]
  assert: output contém "EM ALERTA"
  assert: output NÃO contém "NO TRILHO"
```

### Testes a atualizar em `tests/test_relatorio.py`

| Teste | Mudança |
|---|---|
| `test_seed_pipeline_u1_no_trilho_u2_u3_com_desvio` | U3 agora tem BLOQUEIO_LINGUISTICO, não DESVIO_LIMIAR — mudar assert de U3 para verificar "BLOQUEIO_LINGUISTICO" no output de U3 |
| `test_historico_update_com_alerta_exibe_aviso` | Verificar se assert usa `endswith("⚠")` ou `in "⚠"` — seta de tendência precede o ⚠ agora; ajustar para `assertIn("⚠", linha_historico)` |

**Novos testes:**

```
T08-G: seta ↘ para score decrescente no histórico
  setup: projeto com U1 (score=83) e U2 (score=40, com alerta)
  assert: linha do U2 no histórico contém "↘ ⚠"
  assert: linha do U1 não contém seta (sem anterior)

T08-H: seta ↗ para score crescente no histórico
  setup: projeto com U1 (score=40) e U2 (score=75, com alerta)
  assert: linha do U2 no histórico contém "↗ ⚠"

T08-I: seta → para score estável no histórico
  setup: projeto com U1 (score=75) e U2 (score=75, com alerta)
  assert: linha do U2 no histórico contém "→ ⚠"

T08-J: dados_suficientes=False reseta seta do próximo update
  setup: U1 (score=83), U2 (dados_suficientes=False), U3 (score=75, com alerta)
  assert: linha do U3 não contém seta (U2 interrompeu a série)
```

**Total testes novos/alterados:** ~15. Suíte acumulada esperada: ~90 testes.

---

## Implementation Sequence

Cada passo = um commit coeso. A sequência garante que a suíte está verde ao final de cada passo.

1. **Atualizar testes de SILENCIO em `tests/test_alert_engine.py`** — ajustar gaps para refletir o novo limiar (T08-D, T08-E; atualizar `test_gap_acima_limiar_dispara`, `test_gap_igual_limiar_nao_dispara`, `test_silencio_nao_sofre_fusao`). Rodar `uv run pytest tests/test_alert_engine.py::TestDetectarSilencio -v` — testes devem falhar (esperado; limiar ainda é 2)

2. **`alert_engine.py` — P2:** alterar `LIMIAR_SILENCIO` de 2 para 4. Rodar `uv run pytest tests/test_alert_engine.py::TestDetectarSilencio -v` → todos passando

3. **Atualizar testes de hipótese standalone em `tests/test_alert_engine.py`** — atualizar `test_sem_fusao_quando_desvio_sem_bloqueio` e `test_sem_fusao_quando_bloqueio_sem_desvio`; adicionar T08-A, T08-B, T08-C. Rodar → falham (esperado; funções ainda retornam `hipotese_causal=None`)

4. **`alert_engine.py` — P1:** adicionar `TEMPLATE_HIPOTESE_BLOQUEIO_SIMPLES` e `TEMPLATE_HIPOTESE_DESVIO_SIMPLES`; popular `hipotese_causal` em `_detectar_bloqueio_linguistico` e `_detectar_desvio_limiar`. A lógica de fusão em `analisar_alertas` não muda. Rodar `uv run pytest tests/test_alert_engine.py -v` → todos passando

5. **Atualizar testes de status em `tests/test_explain.py`** — verificar `test_update_no_trilho`; adicionar T08-F. Rodar → T08-F falha (esperado; explain ainda tem 2 estados)

6. **`explain.py` — P3:** substituir lógica de 2 estados por 3 estados (NO TRILHO / EM ALERTA / ABAIXO DO LIMIAR). Rodar `uv run pytest tests/test_explain.py -v` → todos passando

7. **Atualizar testes de histórico em `tests/test_relatorio.py`** — atualizar `test_historico_update_com_alerta_exibe_aviso` e `test_seed_pipeline_u1_no_trilho_u2_u3_com_desvio`; adicionar T08-G, T08-H, T08-I, T08-J. Rodar → novos testes falham (esperado; `_formatar_historico` ainda sem setas)

8. **`relatorio.py` — P4:** modificar `_formatar_historico` para calcular e exibir setas de tendência. Rodar `uv run pytest tests/test_relatorio.py -v` → todos passando

9. **Rodar suíte completa:** `uv run pytest tests/ -v` → todos passando

10. **Lint e tipos:** `uv run ruff check src/ tests/` e `uv run mypy src/` → zero warnings

11. **Validação manual:** `uv run sprint-auditor-demo` — verificar que U3 mostra "Hipótese:" com conteúdo de bloqueio; U4 mostra "Hipótese:" com dados de score; SILENCIO ausente em todos os updates; histórico mostra `↘ ⚠` em U2 e U4, `↗ ⚠` em U3

12. **Validação manual:** `uv run sprint-auditor-explain --update 3` → status deve ser "⚡ EM ALERTA" com 1 alerta (BLOQUEIO_LINGUISTICO); `uv run sprint-auditor-explain --update 4` → "⚠ ABAIXO DO LIMIAR" com 1 alerta (DESVIO_LIMIAR)

---

## Conventions Applied (from CLAUDE.md)

- **Stack:** Python + uv + pytest + ruff + mypy; zero novas dependências
- **Layout:** `src/sprint_auditor/` + `tests/` espelhando a estrutura de `src/`; nenhum arquivo novo
- **Modelagem:** Pydantic v2 — `hipotese_causal: Optional[str]` já existe; nenhuma quebra de schema
- **Sem mutação:** `_detectar_bloqueio_linguistico`, `_detectar_desvio_limiar` e `_formatar_historico` são funções puras (não mutam inputs)
- **Nunca levanta exceção no caminho normal:** slots de template sempre preenchidos antes de `str.format()` (garantido pela pré-condição de não-None no início de cada detector)
- **Linguagem do código:** Português-Brasil (nomes, docstrings)
- **Comentários:** nenhum por padrão; WHY não óbvio documentado em Trade-offs acima
- **Silêncio é informação:** após P2, o sistema não produz SILENCIO para a cadência natural do seed — alerta só quando há silêncio genuíno

---

## Ready to Code?

- [x] Arquitetura descrita com módulos afetados e nenhum arquivo novo
- [x] Contratos finais: novas constantes, slots de templates, assinaturas de funções modificadas
- [x] Modelo de dados: nenhuma mudança de schema necessária (campos já existem desde T07)
- [x] Trade-offs não triviais com alternativa rejeitada e fonte da decisão documentadas
- [x] Riscos conhecidos listados com mitigações
- [x] Plano de teste cobre happy path + casos de borda + regressões explícitas
- [x] Sequência de implementação executável sem perguntas de clarificação
- [x] Nenhuma nova biblioteca introduzida
- [x] Convenções do CLAUDE.md citadas e respeitadas
