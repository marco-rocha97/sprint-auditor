# Tech Spec: Alert Engine — `T04`

> **SPEC:** [`docs/specs/sprint-auditor.md`](../specs/sprint-auditor.md)
> **Plan:** [`docs/plans/sprint-auditor.md`](../plans/sprint-auditor.md) — task `T04`
> **Conventions applied:** `CLAUDE.md` (projeto) + regras globais do usuário
>
> Este documento detalha **como** entregar a tarefa. O **porquê** vive na SPEC; **o quê** e **em que ordem**, no Plan.

---

## Task Scope

- **Behavior delivered** (from Plan): O sistema detecta três condições de desvio — threshold único cruzado, deterioração consistente sem cruzar o threshold, e causa provável identificada por sinais linguísticos — e produz alertas rastreáveis com nível de confiança.
- **SPEC stories/criteria covered:** Story 1 (alerta com causa provável); Story 3 (fase e motivo do atraso); Story 4 (silêncio quando no trilho); Story 6 (causa com nível de confiança explícito); Behaviors: "Desvio cruza o limiar", "Deterioração lenta sem cruzar o limiar", "Causa provável a partir de sinais de bloqueio", "Projeto no trilho — sistema em silêncio"
- **Depends on:** T03 (`calcular_delivery_score`, `DeliveryScore`); T01 (`Alerta`, `CategoriaAlerta`, `NivelConfianca`, `Update`, `Artefato`, `Fase`); T02 (artefatos válidos em `Update.artefatos`)
- **External dependencies:** nenhuma

---

## Architecture

- **General approach:** T04 adiciona `src/sprint_auditor/alert_engine.py` com três detectores internos e uma função pública de entrada. Cada detector avalia uma condição de desvio de forma independente; o ponto de entrada executa os três e retorna todos os alertas gerados — zero alertas é o caso normal quando o projeto está no trilho. O módulo não modifica nenhum objeto de entrada.

- **Affected modules:**
  - `src/sprint_auditor/alert_engine.py` — novo módulo
  - `tests/test_alert_engine.py` — novo arquivo de testes

- **New files:** `src/sprint_auditor/alert_engine.py`, `tests/test_alert_engine.py`

- **Reused patterns:**
  - `fase_do_dia(dia)` e `progresso_esperado(fase, dia)` — `template_fases.py` (T01) — usados para derivar fase e calcular `gap_pp`
  - `Alerta`, `CategoriaAlerta`, `NivelConfianca`, `Update`, `Artefato`, `TipoArtefato`, `Fase` — `modelos.py` (T01)
  - `DeliveryScore.dados_suficientes` — invariante de T01; guarda primária para alertas baseados em score
  - Pattern de "nunca levantar exceção no caminho normal" — `ingestao.py` (T02) e `score_engine.py` (T03)
  - Convenção de import sem prefixo `src.` — `ingestao.py` (T02)

> **Decision source:** CLAUDE.md (Python + uv + pytest + ruff + mypy); contratos de `modelos.py` (T01); lógica de score de `score_engine.py` (T03); threshold=70, deterioração=2 drops, multi-alerta independente: decisões do usuário nesta conversa.

---

## Contracts

### `src/sprint_auditor/alert_engine.py`

```python
import re
from typing import Optional

from sprint_auditor.modelos import (
    Alerta,
    Artefato,
    CategoriaAlerta,
    Fase,
    NivelConfianca,
    TipoArtefato,
    Update,
)
from sprint_auditor.template_fases import fase_do_dia, progresso_esperado


LIMIAR_DESVIO: int = 70

PADROES_BLOQUEIO: list[str] = [
    r"aguardando\s+\w+",             # "aguardando aprovação", "aguardando acesso"
    r"não\s+temos\s+acesso",         # "não temos acesso ao SAP"
    r"bloqueado",                     # "completamente bloqueado"
    r"falhas?\s+de\s+conectividade",  # "falhas de conectividade"
    r"sem\s+acesso",                  # "Sem acesso"
    r"não\s+pode\s+avançar",          # "não pode avançar"
    r"segurando\s+tudo",              # "está segurando tudo"
]


def _detectar_desvio_limiar(update: Update) -> Optional[Alerta]:
    """Retorna Alerta se o score do update estiver abaixo de LIMIAR_DESVIO.

    Precondição: update.score deve estar preenchido (T03 rodou antes).
    Retorna None se score é None, dados_suficientes=False ou valor >= LIMIAR_DESVIO.
    Nunca levanta exceção.
    """


def _detectar_deterioracao_consistente(
    update_atual: Update,
    updates_anteriores: list[Update],
) -> Optional[Alerta]:
    """Retorna Alerta se o score caiu em 2 updates consecutivos sem nenhum cruzar LIMIAR_DESVIO.

    Requer pelo menos 2 updates anteriores com dados_suficientes=True.
    Retorna None se a condição não for satisfeita.
    Nunca levanta exceção.
    """


def _detectar_bloqueio_linguistico(update: Update) -> Optional[Alerta]:
    """Retorna Alerta se algum padrão de PADROES_BLOQUEIO for encontrado em artefatos de transcrição válidos.

    Itera PADROES_BLOQUEIO em ordem para cada artefato de transcrição válido.
    Retorna o primeiro alerta gerado pelo primeiro padrão que casar no primeiro artefato correspondente.
    Retorna None se nenhum padrão casar.
    Nunca levanta exceção.
    """


def analisar_alertas(
    update_atual: Update,
    updates_anteriores: list[Update],
) -> list[Alerta]:
    """Ponto de entrada — executa os 3 detectores e retorna todos os alertas gerados.

    Lista vazia significa que o projeto está no trilho (silêncio é informação).

    Regras de execução:
    - Se update_atual.score é None → executa apenas _detectar_bloqueio_linguistico
    - Se score.dados_suficientes=False → executa apenas _detectar_bloqueio_linguistico
    - Caso contrário → executa os 3 detectores independentemente

    Args:
        update_atual: update com score já preenchido por T03
        updates_anteriores: updates anteriores do mesmo projeto, em ordem crescente de numero

    Returns:
        Lista com 0, 1, 2 ou 3 alertas — todos os detectores que dispararam
    """
```

---

## Data Model

### Constantes do módulo

| Constante | Valor | Papel |
|---|---|---|
| `LIMIAR_DESVIO` | `70` | Score abaixo deste valor → DESVIO_LIMIAR |
| `PADROES_BLOQUEIO` | lista de 7 regex | Padrões compilados com `re.IGNORECASE` |

### Lógica de detecção por categoria

#### DESVIO_LIMIAR

**Condição:** `update.score.dados_suficientes == True` e `update.score.valor < LIMIAR_DESVIO`

**Derivação de `gap_pp`:**
```
progresso_esp = progresso_esperado(fase_do_dia(update.dia_projeto), update.dia_projeto)
gap_pp = float(progresso_esp * (1 - update.score.valor / 100))
```

Exemplo com seed U2 (dia=6, score=0):
- `progresso_esp = progresso_esperado(CONFIGURACAO, 6) = 60`
- `gap_pp = 60.0 * (1 - 0/100) = 60.0`

Exemplo hipotético (dia=6, score=63):
- `gap_pp = 60.0 * (1 - 63/100) = 22.2` ← reproduz o gap de 22 pp do critério SPEC

**Fonte do artefato:** primeiro artefato de board válido em `update.artefatos`; fallback: primeiro artefato válido de qualquer tipo.

| Campo `Alerta` | Valor |
|---|---|
| `categoria` | `CategoriaAlerta.DESVIO_LIMIAR` |
| `fase` | `fase_do_dia(update.dia_projeto)` |
| `dia_projeto` | `update.dia_projeto` |
| `gap_pp` | `float(progresso_esp * (1 - score.valor / 100))` |
| `causa_provavel` | `f"Score {valor} está abaixo do limiar {LIMIAR_DESVIO} — progresso real estimado em {real:.0f}% contra {esp}% esperado para a fase {fase.value} no dia {dia}"` |
| `nivel_confianca` | `NivelConfianca.ALTO` |
| `acao_sugerida` | `f"Investigar bloqueios na fase {fase.value} e considerar escalonamento para o FDE Lead"` |
| `artefato_fonte_id` | ID do primeiro artefato board válido (ou primeiro válido) |
| `trecho_fonte` | `conteudo` do artefato selecionado |

---

#### DETERIORACAO_CONSISTENTE

**Condição:**
1. Há pelo menos 2 updates anteriores com `score.dados_suficientes == True`
2. Tomando os 2 mais recentes (`penultimo`, `anterior`) e o `update_atual`:
   - `anterior.score.valor < penultimo.score.valor` (1º drop)
   - `update_atual.score.valor < anterior.score.valor` (2º drop)
3. Nenhum dos três scores (penultimo, anterior, atual) está abaixo de `LIMIAR_DESVIO`

Se qualquer score cruzar o limiar, `_detectar_desvio_limiar` é o detector correto — este não dispara.

**Fonte do artefato:** primeiro artefato board válido em `update_atual.artefatos`; fallback: primeiro artefato válido de qualquer tipo.

| Campo `Alerta` | Valor |
|---|---|
| `categoria` | `CategoriaAlerta.DETERIORACAO_CONSISTENTE` |
| `fase` | `fase_do_dia(update_atual.dia_projeto)` |
| `dia_projeto` | `update_atual.dia_projeto` |
| `gap_pp` | `None` |
| `causa_provavel` | `f"Score caiu por 2 updates consecutivos: {s_penultimo} → {s_anterior} → {s_atual} sem cruzar o limiar {LIMIAR_DESVIO}"` |
| `nivel_confianca` | `NivelConfianca.MEDIO` |
| `acao_sugerida` | `"Monitorar próximo update; se a tendência continuar, escalar para o FDE Lead"` |
| `artefato_fonte_id` | ID do primeiro artefato board válido de `update_atual` (ou primeiro válido) |
| `trecho_fonte` | `conteudo` do artefato selecionado |

---

#### BLOQUEIO_LINGUISTICO

**Condição:** pelo menos um padrão de `PADROES_BLOQUEIO` casa em ao menos um artefato de `TipoArtefato.TRANSCRICAO` com `valido=True`.

**Algoritmo:**
```
para cada artefato em update.artefatos onde tipo=TRANSCRICAO e valido=True:
    para cada padrão em PADROES_BLOQUEIO:
        match = re.search(padrão, artefato.conteudo, re.IGNORECASE)
        se match:
            retornar Alerta com trecho_fonte=match.group(), artefato_fonte_id=artefato.id
retornar None
```

Retorna o primeiro alerta gerado — um único alerta de BLOQUEIO_LINGUISTICO por update, independente de quantos padrões casam.

**Comportamento esperado para o seed:**

| Update | Artefato | Padrão que casa primeiro | `trecho_fonte` |
|---|---|---|---|
| U2 | `art-u2-transcricao` | `r"aguardando\s+\w+"` | `"aguardando aprovação"` |
| U3 | `art-u3-transcricao` | `r"bloqueado"` | `"bloqueado"` |

| Campo `Alerta` | Valor |
|---|---|
| `categoria` | `CategoriaAlerta.BLOQUEIO_LINGUISTICO` |
| `fase` | `fase_do_dia(update.dia_projeto)` |
| `dia_projeto` | `update.dia_projeto` |
| `gap_pp` | `None` |
| `causa_provavel` | `f"Sinal de bloqueio identificado na transcrição: '{trecho_casado}'"` |
| `nivel_confianca` | `NivelConfianca.MEDIO` |
| `acao_sugerida` | `"Bloqueio externo identificado → escalar para o FDE Lead"` |
| `artefato_fonte_id` | ID do artefato de transcrição onde o padrão casou |
| `trecho_fonte` | `match.group()` — substring exata que ativou o padrão |

---

### Condições de execução de `analisar_alertas`

| Estado de `update_atual.score` | Detectores executados |
|---|---|
| `None` | apenas `_detectar_bloqueio_linguistico` |
| `dados_suficientes=False` | apenas `_detectar_bloqueio_linguistico` |
| `dados_suficientes=True` | todos os 3, independentemente |

**Silêncio correto:** se nenhum detector disparar → `[]` — estado de sucesso explícito conforme SPEC Story 4.

---

## External Integrations

Nenhuma.

---

## Trade-offs e Alternativas Rejeitadas

**Decisão: threshold=70 como constante nomeada `LIMIAR_DESVIO`**
- Alternativa rejeitada: valor hardcoded inline em `_detectar_desvio_limiar`
- Motivo: constante nomeada é referenciável nos testes (sem magic number) e comunicável no relatório (T05 pode exibir "limiar: 70"). O valor 70 dá margem para delays menores que não justificam escalação — score 75 significa "75% do esperado entregue", que é um tropeço menor.
- Trade-off: a calibração fina do limiar está explicitamente fora do MVP (SPEC out-of-scope); o valor é uma estimativa razoável para a demo, não um parâmetro calibrado com histórico real.
- Fonte: decisão do usuário nesta conversa; SPEC out-of-scope "calibração fina do Delivery Score".

**Decisão: 2 drops consecutivos para DETERIORACAO_CONSISTENTE**
- Alternativa rejeitada: 3 drops (janela de 4 updates)
- Motivo: o seed tem apenas 3 updates; exigir 3 drops tornaria o detector inerte na demo. 2 drops é o mínimo para confirmar tendência (um drop pode ser ruído; dois confirmam direção).
- Trade-off: mais sensível a falsos positivos com projetos de curta duração ou poucos updates.
- Fonte: decisão do usuário nesta conversa.

**Decisão: todos os detectores são independentes (multi-alerta)**
- Alternativa rejeitada: prioridade DESVIO_LIMIAR > DETERIORACAO > BLOQUEIO (primeiro que casa vence)
- Motivo: um update que cruza o limiar E contém sinal linguístico de bloqueio carrega informações complementares — o score diz "quão longe do trilho", o bloqueio diz "por quê". Suprimir um esconderia rastreabilidade. O modelo `Update.alertas: list[Alerta]` já sinaliza a intenção de múltiplos alertas.
- Trade-off: T05 deve lidar com 0–3 alertas por update; a lógica de relatório fica ligeiramente mais complexa.
- Fonte: decisão do usuário nesta conversa; campo `alertas: list[Alerta]` em `modelos.py`.

**Decisão: `PADROES_BLOQUEIO` como lista de regex fixa**
- Alternativa rejeitada: dicionário keyword → categoria (ex.: `{"aguardando": "espera_aprovacao"}`) para gerar causas mais ricas
- Motivo: o MVP usa "regras fixas simples" conforme SPEC out-of-scope. A regex basta para a demo e o `match.group()` já fornece o trecho de rastreabilidade. Categorias finas de bloqueio são features de fase 2.
- Trade-off: todos os bloqueios produzem a mesma `acao_sugerida` — "escalar para o FDE Lead". Insuficiente para produção, adequado para a demo.
- Fonte: SPEC out-of-scope "sugestão de intervenção por aprendizado de padrões".

**Decisão: `trecho_fonte` de DESVIO_LIMIAR e DETERIORACAO é o `conteudo` completo do artefato board**
- Alternativa rejeitada: gerar uma string sintética ("Score 0 vs esperado 60")
- Motivo: `Alerta.trecho_fonte` deve ser uma substring do `Artefato.conteudo` para garantir rastreabilidade verificável. O conteúdo do board é curto (seed ≤ 80 chars) e é a evidência direta do estado de progresso. Uma string sintética não seria rastreável a nenhum artefato real.
- Trade-off: o trecho pode ser menos legível para DETERIORACAO (mostra estado atual, não o histórico) — a narrativa do histórico fica em `causa_provavel`.
- Fonte: SPEC princípio "todo alerta é rastreável"; campo `artefato_fonte_id` em `Alerta`.

**Decisão: `gap_pp` definido como `progresso_esp * (1 - score.valor / 100)` em vez de `100 - score.valor`**
- Alternativa rejeitada: `float(100 - score.valor)` (gap em pontos de score)
- Motivo: o critério de aceitação do Plan cita "38% real contra 60% esperado" — um gap de 22 pp em termos de progresso bruto. A fórmula escolhida reproduz esse valor a partir do score (22.2 para score=63, dia=6), tornando o campo diretamente comparável ao template. A alternativa produziria 37 pp, que não tem ancoragem no template de fases.
- Trade-off: pequeno erro de truncagem (22.2 em vez de 22.0 exato) por causa da truncagem inteira no score — irrelevante para a demo.
- Fonte: critério de aceitação T04 no Plan; tabela de exemplos do T03 Tech Spec.

**Decisão: BLOQUEIO_LINGUISTICO dispara mesmo com `dados_suficientes=False`**
- Alternativa rejeitada: só disparar BLOQUEIO quando há score válido
- Motivo: o sinal linguístico é independente do score — um update sem board pode ter transcrição com bloqueio explícito. Suprimir o alerta nesses casos violaria o princípio "todo alerta é rastreável" ao preço de ausência de dados de board. A SPEC não condiciona BLOQUEIO_LINGUISTICO à existência de score.
- Fonte: SPEC Behavior "Causa provável a partir de sinais de bloqueio" não menciona pré-condição de score.

---

## Risks and Mitigations

| Risco | Impacto | Mitigação |
|---|---|---|
| `_detectar_deterioracao_consistente` seleciona updates com `score=None` como predecessores válidos | Score anterior falso (None interpretado como qualquer valor) | Filtro explícito: `u.score is not None and u.score.dados_suficientes` antes de selecionar os 2 predecessores |
| Regex com `\w+` não captura acentos em Python 2 (irrelevante) ou em contextos sem Unicode | "aguardando aprovação" não casa | Python 3 usa Unicode por padrão; `\w` inclui `ã`, `ç`, `ê` etc; coberto pelo teste 13 que verifica o match exato "aguardando aprovação" |
| Updates anteriores fora de ordem (por `numero`) passados a `analisar_alertas` | Detecta deterioração em ordem errada | Documentado como precondição: `updates_anteriores` deve estar em ordem crescente de `numero`; o pipeline de T06 garante isso iterando `Projeto.updates` |
| `_detectar_desvio_limiar` sem artefatos válidos apesar de `dados_suficientes=True` | `artefato_fonte` seria `None`, crashando a construção de `Alerta` | Retorna `None` defensivamente nesse caso — impossível no pipeline normal (score suficiente implica artefatos válidos), mas seguro contra construção manual de Updates |
| DETERIORACAO_CONSISTENTE e DESVIO_LIMIAR disparam simultaneamente | Alerta duplicado? Não — as condições são mutuamente exclusivas por design | `_detectar_deterioracao_consistente` verifica que nenhum score cruza `LIMIAR_DESVIO`; se o atual cruza, `_detectar_desvio_limiar` dispara e DETERIORACAO retorna `None` |

---

## Testing Plan

**Framework:** pytest. Fonte: CLAUDE.md (`uv run pytest tests/ -v`).
**Padrão de organização:** classes por responsabilidade, conforme `tests/test_score_engine.py`.

### `tests/test_alert_engine.py` — 18 testes

```
class TestAnalisarAlertas:
```
1. **Silêncio quando no trilho**: update com `score.valor=100`, sem bloqueio → `[]`
2. **DESVIO_LIMIAR único**: update com `score.valor=0` (dia=6), sem texto de bloqueio → `[Alerta(categoria=DESVIO_LIMIAR)]`
3. **BLOQUEIO_LINGUISTICO único**: update com `score.valor=80` (acima do limiar) e transcrição com "aguardando aprovação" → `[Alerta(categoria=BLOQUEIO_LINGUISTICO)]`
4. **Multi-alerta**: update com `score.valor=0` e transcrição com "aguardando aprovação" → 2 alertas, categorias `{DESVIO_LIMIAR, BLOQUEIO_LINGUISTICO}`
5. **Dados insuficientes sem bloqueio**: `score.dados_suficientes=False`, nenhuma transcrição com bloqueio → `[]`
6. **Dados insuficientes com bloqueio**: `score.dados_suficientes=False`, transcrição com "bloqueado" → `[Alerta(categoria=BLOQUEIO_LINGUISTICO)]`

```
class TestDetectarDesvioLimiar:
```
7. **Score=69 (abaixo do limiar)**: Alerta retornado com campos `categoria=DESVIO_LIMIAR`, `nivel_confianca=ALTO`, `artefato_fonte_id` e `trecho_fonte` preenchidos, `gap_pp` não None
8. **Score=70 (boundary — não cruza)**: `None` retornado — limiar é exclusivo (`< 70`), não inclusivo (`<= 70`)
9. **Score=71 (acima)**: `None`
10. **`gap_pp` para score=63, dia=6**: `gap_pp ≈ 22.2` — `float(60 * (1 - 63/100))` ← reproduz o exemplo do critério SPEC

```
class TestDetectarDeterioracaoConsistente:
```
11. **2 drops consecutivos sem cruzar limiar**: scores `[90, 80, 75]` (nenhum < 70) → Alerta com `categoria=DETERIORACAO_CONSISTENTE`, `nivel_confianca=MEDIO`, `gap_pp=None`
12. **Apenas 1 drop**: scores `[90, 80]` (sem update anterior suficiente) → `None`
13. **Drops mas um cruza limiar**: scores `[90, 80, 60]` (60 < 70) → `None`
14. **Menos de 2 updates anteriores com score**: lista vazia → `None`

```
class TestDetectarBloqueioLinguistico:
```
15. **"aguardando aprovação"**: Alerta retornado com `trecho_fonte="aguardando aprovação"` (match exato), `nivel_confianca=MEDIO`, `acao_sugerida` contém "FDE Lead"
16. **"bloqueado"**: Alerta retornado com `trecho_fonte="bloqueado"`
17. **Sem sinal de bloqueio**: transcrição sem nenhum padrão → `None`
18. **Artefato board somente (sem transcrição)**: board com "aguardando aprovação" no conteúdo → `None` (detector só lê `TipoArtefato.TRANSCRICAO`)

```
class TestSeedRastreabilidade:
```
_(usa `carregar_projeto_seed()` para exercitar os critérios de aceitação do Plan com dados concretos)_

19. **Seed U2 → DESVIO_LIMIAR rastreável**: `analisar_alertas(update_2, [update_1])` → alerta `DESVIO_LIMIAR` com `artefato_fonte_id="art-u2-board"`
20. **Seed U2 → BLOQUEIO rastreável**: alerta `BLOQUEIO_LINGUISTICO` com `artefato_fonte_id="art-u2-transcricao"` e `trecho_fonte` contendo `"aguardando"`

**Total: 20 testes**

> A suíte acumulada após T04: **64 testes** (44 de T01–T03 + 20 de T04).

---

## Implementation Sequence

Cada passo = um commit coeso:

1. Criar `src/sprint_auditor/alert_engine.py` com as constantes, as 3 funções internas e `analisar_alertas`
2. Criar `tests/test_alert_engine.py` com 20 testes → `uv run pytest tests/test_alert_engine.py -v` → todos passando
3. Rodar suíte completa → `uv run pytest tests/ -v` → 64 testes passando
4. Rodar `uv run ruff check src/ tests/` + `uv run mypy src/` → zero warnings

---

## Conventions Applied (from CLAUDE.md)

- **Stack:** Python + uv + pytest + ruff + mypy
- **Layout:** `src/sprint_auditor/` + `tests/` espelhando a estrutura de `src/`
- **Import:** sem prefixo `src.` (padrão de `ingestao.py`)
- **Sem mutação:** nenhuma função modifica `update_atual`, `updates_anteriores` ou seus campos
- **Nunca levanta exceção no caminho normal:** todos os detectores retornam `None` em vez de levantar; `analisar_alertas` retorna `[]` nos casos de score ausente
- **Linguagem do código:** Português-Brasil (nomes de funções, variáveis, docstrings)
- **Comentários:** nenhum por padrão — WHY não óbvio documentado em Trade-offs

---

## Ready to Code?

- [x] Arquitetura descrita com módulo e novos arquivos nomeados
- [x] Contratos (interfaces internas) em forma final com assinaturas completas e docstrings
- [x] Modelo de dados com algoritmos, fórmulas e tabelas de comportamento concretas por categoria
- [x] Comportamento do seed documentado com valores esperados (`trecho_fonte` exato para U2 e U3)
- [x] Trade-offs não triviais com alternativa rejeitada e fonte da decisão documentadas
- [x] Riscos conhecidos listados com mitigações
- [x] Plano de teste cobre happy path + casos de erro + boundary + critério SPEC explícito + rastreabilidade do seed
- [x] Sequência de implementação é executável sem perguntas de clarificação
- [x] Nenhuma nova biblioteca introduzida (apenas `re` da stdlib + Pydantic v2 já instalado)
- [x] Convenções do CLAUDE.md citadas e respeitadas
