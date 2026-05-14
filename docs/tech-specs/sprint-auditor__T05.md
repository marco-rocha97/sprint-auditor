# Tech Spec: Gerador de Relatório Estático — `T05`

> **SPEC:** [`docs/specs/sprint-auditor.md`](../specs/sprint-auditor.md)
> **Plan:** [`docs/plans/sprint-auditor.md`](../plans/sprint-auditor.md) — tarefa `T05`
> **Convenções aplicadas:** `CLAUDE.md` (projeto) + regras globais do usuário
>
> Este documento detalha **como** entregar a tarefa. O **porquê** vive na SPEC; **o quê** e **em que ordem**, no Plan.

---

## Task Scope

- **Behavior delivered** (from Plan): Para cada update processado, o sistema gera um relatório legível que mostra o Delivery Score atual, o histórico de scores, e — quando aplicável — o alerta de desvio no topo com causa provável, ação sugerida e rastreabilidade ao artefato-fonte. Todos os estados da interface são cobertos.
- **SPEC stories/criteria covered:** Story 1 (alerta com causa provável); Story 2 (histórico do score); Story 3 (fase e motivo do atraso); Story 5 (dados insuficientes sem número inventado); Story 6 (causa com nível de confiança explícito); Experience Design completo (empty state, success state, error state); princípios "silêncio é informação", "todo alerta é rastreável", "nunca inventar um score", "causa com nível de confiança"; acessibilidade (legível em texto puro, sem dependência de cor).
- **Depends on:** T01 (`Projeto`, `Update`, `Artefato`, `DeliveryScore`, `Alerta`, todos os enums); T02 (`Artefato.valido`, `Artefato.erro_ingestao`); T03 (`Update.score`); T04 (`Update.alertas`)
- **External dependencies:** nenhuma

---

## Architecture

- **General approach:** T05 adiciona `src/sprint_auditor/relatorio.py` com uma função pública `gerar_relatorio(projeto)` e funções internas de formatação. O módulo é um **formatador puro** — lê dados já computados nos campos `Update.score` e `Update.alertas` (preenchidos por T03 e T04) e produz texto. Não executa score engine nem alert engine. Não levanta exceção no caminho normal.

- **Affected modules:**
  - `src/sprint_auditor/relatorio.py` — novo módulo
  - `tests/test_relatorio.py` — novo arquivo de testes

- **New files:** `src/sprint_auditor/relatorio.py`, `tests/test_relatorio.py`

- **Reused patterns:**
  - `Projeto`, `Update`, `Artefato`, `DeliveryScore`, `Alerta`, `CategoriaAlerta`, `NivelConfianca`, `Fase` — `modelos.py` (T01)
  - `Artefato.valido` e `Artefato.erro_ingestao` — `ingestao.py` (T02)
  - Pattern "nunca levantar exceção no caminho normal" — `ingestao.py` (T02), `score_engine.py` (T03), `alert_engine.py` (T04)
  - Convenção de import sem prefixo `src.` — `ingestao.py` (T02)
  - `carregar_projeto_seed()` nos testes de integração — `seed.py` (T01)

> **Decision source:** CLAUDE.md (Python + uv + pytest + ruff + mypy); contratos de `modelos.py` (T01); padrão de formatação ASCII + barra de texto: decisões do usuário nesta conversa; multi-alerta ordenado por gravidade: decisão do usuário nesta conversa.

---

## Contracts

### `src/sprint_auditor/relatorio.py`

```python
from sprint_auditor.modelos import (
    Alerta,
    Artefato,
    CategoriaAlerta,
    DeliveryScore,
    NivelConfianca,
    Projeto,
    Update,
)

# ── constantes de formatação ──────────────────────────────────────────────────

_LARGURA_BARRA: int = 10
_LARGURA_LINHA: int = 44  # usada nos separadores

_ORDEM_CATEGORIA: dict[CategoriaAlerta, int] = {
    CategoriaAlerta.desvio_limiar: 0,
    CategoriaAlerta.deterioracao_consistente: 1,
    CategoriaAlerta.bloqueio_linguistico: 2,
}

_LABEL_CONFIANCA: dict[NivelConfianca, str] = {
    NivelConfianca.alto: "ALTA",
    NivelConfianca.medio: "MÉDIA",
    NivelConfianca.baixo: "BAIXA",
}

_LABEL_CATEGORIA: dict[CategoriaAlerta, str] = {
    CategoriaAlerta.desvio_limiar: "[DESVIO]",
    CategoriaAlerta.deterioracao_consistente: "[PIORA]",
    CategoriaAlerta.bloqueio_linguistico: "[BLOQUEIO]",
}


# ── helpers internos ──────────────────────────────────────────────────────────

def _formatar_barra(valor: int, largura: int = _LARGURA_BARRA) -> str:
    """Gera barra de progresso ASCII: ████████░░ para valor=80, largura=10.

    valor: inteiro 0–100. Valores fora do intervalo são truncados (max/min).
    Retorna string de exatamente `largura` caracteres.
    """


def _ordenar_alertas(alertas: list[Alerta]) -> list[Alerta]:
    """Retorna alertas ordenados por gravidade decrescente: DESVIO_LIMIAR > DETERIORACAO > BLOQUEIO.

    Não modifica a lista original.
    """


def _indicador_status(alertas: list[Alerta]) -> str:
    """Retorna rótulo textual do alerta mais grave, ou string vazia se não há alertas.

    Exemplos: '  [DESVIO]', '  [PIORA]', '  [BLOQUEIO]', ''
    Garante que o status nunca depende apenas de cor (acessibilidade SPEC).
    """


def _linha_score(score: DeliveryScore | None) -> str:
    """Formata a linha de Delivery Score.

    score=None ou dados_suficientes=False → 'Delivery Score: sem dados suficientes'
    dados_suficientes=True → 'Delivery Score: ████████░░  83/100'
    """


def _formatar_trecho(trecho: str, limite: int = 100) -> str:
    """Normaliza o trecho para exibição em linha única.

    Substitui quebras de linha por ' / ' e trunca em `limite` caracteres com '...'.
    Não modifica o campo original em Alerta.
    """


def _formatar_alerta(alerta: Alerta) -> str:
    """Formata um bloco de alerta como texto puro.

    Formato:
        ⚠ DESVIO_LIMIAR (confiança: ALTA)
          Fase: configuracao | Dia: 6 | Gap: 60.0 pp
          Causa: Score 0 está abaixo do limiar 70...
          Ação: Investigar bloqueios na fase configuracao...
          Fonte: art-u2-board | "Board de Configuração: [✗]..."

    gap_pp ausente (DETERIORACAO, BLOQUEIO): linha "Fase/Dia" sem "| Gap:".
    Retorna string multiline sem trailing newline.
    """


def _formatar_update(update: Update) -> str:
    """Formata a seção de um update como texto puro.

    Estrutura:
        ─── Update #N — Dia D ─────...
        Delivery Score: ████████░░  83/100  [DESVIO]
        [blocos de alerta, ordenados por gravidade, se existirem]
        [mensagem "no trilho" se não há alertas e score ok]
        [linha de erro de ingestão por artefato inválido, se existirem]

    Não levanta exceção. Retorna string multiline sem trailing newline.
    """


def _formatar_historico(updates: list[Update]) -> str:
    """Gera a seção de histórico de scores em ordem cronológica.

    Formato:
        Histórico de Delivery Score:
          Update #1 (Dia  3): ████████░░  83/100
          Update #2 (Dia  6): ░░░░░░░░░░   0/100  ⚠
          Update #3 (Dia  9): sem dados suficientes

    updates: já deve estar em ordem crescente de numero.
    Retorna string multiline sem trailing newline.
    """


# ── ponto de entrada público ──────────────────────────────────────────────────

def gerar_relatorio(projeto: Projeto) -> str:
    """Gera o relatório estático completo de um projeto como string de texto puro.

    Lê os campos já computados em cada Update (score por T03, alertas por T04).
    Não executa score engine nem alert engine — é um formatador puro.

    Estrutura do relatório:
        [cabeçalho do projeto]
        [para cada update em ordem crescente de numero:]
            [seção do update com score, alertas, erros de ingestão]
        [seção de histórico]
        [rodapé]

    Estados cobertos:
        - Empty state: projeto sem updates → mensagem "sem dados suficientes"
        - Success state (no trilho): score + "projeto no trilho" por update
        - Success state (com alerta): alerta(s) em destaque por update
        - Error state: artefato com erro de ingestão apontado por update

    Args:
        projeto: Projeto com updates já processados (score e alertas preenchidos).

    Returns:
        Relatório completo como string. Última linha sem trailing newline.
        Adequado para print() ou escrita em arquivo.

    Nunca levanta exceção.
    """
```

---

## Data Model

### Constantes do módulo

| Constante | Valor | Papel |
|---|---|---|
| `_LARGURA_BARRA` | `10` | Número de caracteres da barra de progresso |
| `_LARGURA_LINHA` | `44` | Comprimento dos separadores `═` e `─` |
| `_ORDEM_CATEGORIA` | `{DESVIO_LIMIAR: 0, ...}` | Ordena alertas por gravidade crescente |
| `_LABEL_CONFIANCA` | `{alto: "ALTA", ...}` | Rótulo textual para `NivelConfianca` |
| `_LABEL_CATEGORIA` | `{desvio_limiar: "[DESVIO]", ...}` | Indicador de status por categoria |

### Mapeamento de estado de score para exibição

| `score` | `dados_suficientes` | `valor` | Exibição |
|---|---|---|---|
| `None` | — | — | `"Delivery Score: sem dados suficientes"` |
| não-None | `False` | `None` | `"Delivery Score: sem dados suficientes"` |
| não-None | `True` | `0–100` | `"Delivery Score: ████████░░  83/100"` |

### Fórmula da barra de progresso

```
preenchido = round(valor * _LARGURA_BARRA / 100)
barra = "█" * preenchido + "░" * (_LARGURA_BARRA - preenchido)
```

Exemplos:

| `valor` | `preenchido` | `barra` |
|---|---|---|
| `0` | `0` | `░░░░░░░░░░` |
| `50` | `5` | `█████░░░░░` |
| `83` | `8` | `████████░░` |
| `100` | `10` | `██████████` |

### Ordem de gravidade dos alertas

```
DESVIO_LIMIAR (0) > DETERIORACAO_CONSISTENTE (1) > BLOQUEIO_LINGUISTICO (2)
```

Aplicada por `_ordenar_alertas` usando `sorted(..., key=lambda a: _ORDEM_CATEGORIA[a.categoria])`.

### Estrutura completa de um bloco de alerta

```
⚠ DESVIO_LIMIAR (confiança: ALTA)
  Fase: configuracao | Dia: 6 | Gap: 60.0 pp
  Causa: Score 0 está abaixo do limiar 70 — progresso real estimado em 0% contra 60% esperado...
  Ação: Investigar bloqueios na fase configuracao e considerar escalonamento para o FDE Lead
  Fonte: art-u2-board | "Board de Configuração: [✗] Acesso ao SAP / [✗] Config do ambiente..."
```

- `gap_pp` só aparece se `alerta.gap_pp is not None` (ausente em DETERIORACAO e BLOQUEIO)
- `trecho_fonte` é processado por `_formatar_trecho`: newlines → `" / "`, truncado em 100 chars com `"..."`
- `categoria.value.upper()` → `"DESVIO_LIMIAR"` (enum str, `.upper()` sem sufixo extra)

### Estrutura completa do relatório

```
════════════════════════════════════════════
SPRINT AUDITOR — Alpha Corp
Kickoff: 2026-04-28
════════════════════════════════════════════

─── Update #1 — Dia 3 ──────────────────────
Delivery Score: ████████░░  83/100
Projeto no trilho — nenhum desvio detectado.

─── Update #2 — Dia 6 ──────────────────────
Delivery Score: ░░░░░░░░░░   0/100  [DESVIO]

⚠ DESVIO_LIMIAR (confiança: ALTA)
  Fase: configuracao | Dia: 6 | Gap: 60.0 pp
  Causa: Score 0 está abaixo do limiar 70...
  Ação: Investigar bloqueios na fase configuracao...
  Fonte: art-u2-board | "Board de Configuração: [✗] Acesso ao SAP / ..."

⚠ BLOQUEIO_LINGUISTICO (confiança: MÉDIA)
  Fase: configuracao | Dia: 6
  Causa: Sinal de bloqueio identificado na transcrição: 'aguardando aprovação'
  Ação: Bloqueio externo identificado → escalar para o FDE Lead
  Fonte: art-u2-transcricao | "aguardando aprovação"

────────────────────────────────────────────
Histórico de Delivery Score:
  Update #1 (Dia  3): ████████░░  83/100
  Update #2 (Dia  6): ░░░░░░░░░░   0/100  ⚠
════════════════════════════════════════════
```

### Empty state (projeto sem updates)

```
════════════════════════════════════════════
SPRINT AUDITOR — Alpha Corp
Kickoff: 2026-04-28
════════════════════════════════════════════

Sem dados suficientes para um Delivery Score confiável.
Nenhum update foi processado.
════════════════════════════════════════════
```

### Error state (artefato que falhou na ingestão)

Aparece ao final da seção do update, depois dos alertas:

```
✗ Ingestão: artefato art-xyz falhou — Conteúdo vazio ou ausente
```

Regra: apenas artefatos com `valido=False` (e `erro_ingestao` preenchido); os demais resultados do update não são omitidos.

---

## External Integrations

Nenhuma.

---

## Trade-offs e Alternativas Rejeitadas

**Decisão: `gerar_relatorio` é um formatador puro — lê `Update.score` e `Update.alertas` já preenchidos**
- Alternativa rejeitada: `gerar_relatorio` chama internamente `calcular_delivery_score` e `analisar_alertas`
- Motivo: T05 é exclusivamente responsável pela apresentação; a orquestração do pipeline pertence a T06. Misturar computação e formatação em T05 acoplaria o relatório à lógica de score e quebraria o princípio de responsabilidade única. T06 já vai iterar updates, preencher score e alertas, e chamar `gerar_relatorio` — T05 não precisa saber disso.
- Trade-off: o chamador deve garantir que score e alertas foram preenchidos antes de chamar `gerar_relatorio`; um update com `score=None` e `alertas=[]` é tratado como "dados insuficientes" sem alerta, o que é o comportamento correto por design.
- Fonte: arquitetura do CLAUDE.md (pipeline T02→T03→T04→T05→T06); separação declarada no Plan.

**Decisão: formato texto puro ASCII com separadores `═` e `─`**
- Alternativa rejeitada: Markdown (`# Cabeçalho`, `**negrito**`, `> blockquote`)
- Motivo: o SPEC exige "relatório legível em texto puro e navegável por teclado"; `cat`, `less` ou `print()` devem ser suficientes sem renderizador externo. A decisão foi confirmada pelo usuário nesta conversa.
- Trade-off: sem biblioteca `rich`/`mdcat`, a barra de progresso usa caracteres Unicode (`█░`) que funcionam em qualquer terminal moderno mas podem exibir `?` em terminais muito antigos ou configurações ASCII-only — risco desprezível para a demo.
- Fonte: SPEC princípios "acessibilidade" e "legível em texto puro"; decisão do usuário nesta conversa.

**Decisão: múltiplos alertas exibidos em seções separadas, ordenados por gravidade**
- Alternativa rejeitada: apenas o alerta mais grave por update (DESVIO_LIMIAR suprime BLOQUEIO)
- Motivo: DESVIO_LIMIAR diz "quão longe do trilho"; BLOQUEIO_LINGUISTICO diz "por quê". Suprimir um esconderia rastreabilidade — violaria o princípio "todo alerta é rastreável". A decisão foi confirmada pelo usuário nesta conversa.
- Trade-off: o relatório pode ter 2–3 blocos de alerta por update; não é excessivo na escala da demo (15 dias, ≤3 updates no seed).
- Fonte: Trade-off registrado no T04 Tech Spec ("Decisão: todos os detectores são independentes"); decisão do usuário nesta conversa.

**Decisão: `_formatar_trecho` normaliza newlines e trunca em 100 chars**
- Alternativa rejeitada: exibir o `trecho_fonte` bruto sem transformação
- Motivo: para DESVIO_LIMIAR e DETERIORACAO_CONSISTENTE, `trecho_fonte` é o conteúdo integral do artefato board (ex: "Board de Configuração:\n[✗] Acesso ao SAP\n..."), que ocupa múltiplas linhas e quebraria a indentação do bloco de alerta. A normalização é estritamente visual — o campo `Alerta.trecho_fonte` não é modificado.
- Trade-off: o trecho exibido pode ser truncado; o artefato completo está acessível via `Alerta.artefato_fonte_id` se necessário.
- Fonte: SPEC princípio "todo alerta é rastreável" (o ID do artefato é suficiente para rastreabilidade); decisão local de formatação.

**Decisão: `data_kickoff` exibida apenas como data (YYYY-MM-DD), sem horário**
- Alternativa rejeitada: exibir `data_kickoff` com hora e offset UTC (`2026-04-28T09:00:00Z`)
- Motivo: o relatório usa "dia do projeto" como unidade de tempo; horas e minutos do kickoff não têm valor para a persona (Head de Operações ou FDE Lead) ao ler o status de delivery. A data basta para contextualizar o sprint de 15 dias.
- Trade-off: perde precisão de horário — irrelevante para a demo e para o caso de uso de monitoramento de progresso diário.
- Fonte: `rules/datetime.md` (exibir no TZ do usuário ou rotular — como é só a data, não há ambiguidade).

**Decisão: histórico de scores ao final do relatório (seção única)**
- Alternativa rejeitada: histórico ao topo, antes dos detalhes por update
- Motivo: o leitor precisa do contexto detalhado (score + alertas por update) antes de interpretar a evolução. A seção de histórico funciona como resumo/conclusão. Para a demo, o relatório do update mais recente já carrega a informação mais relevante nas seções anteriores.
- Trade-off: se o projeto tiver muitos updates, o leitor precisa rolar para baixo antes de ver o histórico — não é um problema para um MVP com ≤3 updates no seed.
- Fonte: SPEC Experience Design ("vê o Delivery Score atual, o histórico do score ao longo dos updates"); decisão de ordenação local.

---

## Risks and Mitigations

| Risco | Impacto | Mitigação |
|---|---|---|
| `update.score` preenchido mas `update.alertas` não (T04 não foi chamado) | Update parece "no trilho" mesmo com score baixo | Documentado como precondição da função: score e alertas devem ser preenchidos pelo pipeline antes de chamar `gerar_relatorio`; nos testes de integração com o seed, o pipeline completo é executado |
| `update.alertas` contém categoria não mapeada em `_ORDEM_CATEGORIA` | `KeyError` em `_ordenar_alertas` | Impossível com os tipos definidos em T01 — `CategoriaAlerta` é um enum fechado; mypy garante cobertura |
| Caráter `█`/`░` não renderiza em locale ASCII-only | Barra ilegível | Risco desprezível para a demo (terminal moderno com UTF-8); comentado no Tech Spec como trade-off conhecido |
| `trecho_fonte` vazio (string `""`) em algum alerta | `_formatar_trecho` retorna `""`, linha "Fonte:" fica vazia | Impossível: T04 garante que `trecho_fonte` = `conteudo` do artefato (que deve ser não-vazio para ser válido per T02) ou `match.group()` (não pode ser vazio se match ocorreu) |
| `update.numero` fora de ordem em `projeto.updates` | Histórico e seções exibidos fora de ordem cronológica | `gerar_relatorio` ordena explicitamente: `sorted(projeto.updates, key=lambda u: u.numero)` |

---

## Testing Plan

**Framework:** pytest. Fonte: CLAUDE.md (`uv run pytest tests/ -v`).
**Padrão de organização:** classes por responsabilidade, conforme `tests/test_alert_engine.py`.

### `tests/test_relatorio.py` — 20 testes

```
class TestGerarRelatorio:
```
1. **Empty state — projeto sem updates**: resultado contém "Sem dados suficientes para um Delivery Score confiável"; não contém nenhum dígito de score
2. **Update com score=None (sem T03)**: seção contém "sem dados suficientes"; nenhum número exibido
3. **Update com dados_suficientes=False**: seção contém "sem dados suficientes"; nenhum número exibido
4. **Update no trilho (score=100, sem alertas)**: linha score contém "100/100"; contém "Projeto no trilho — nenhum desvio detectado."; nenhuma linha "⚠"
5. **Update com DESVIO_LIMIAR**: contém "DESVIO_LIMIAR"; contém "ALTA"; contém "Gap:"; contém `artefato_fonte_id` do alerta; contém trecho do fonte
6. **Update com DETERIORACAO_CONSISTENTE**: contém "DETERIORACAO_CONSISTENTE"; contém "MÉDIA"; não contém "Gap:"
7. **Update com BLOQUEIO_LINGUISTICO**: contém "BLOQUEIO_LINGUISTICO"; contém "MÉDIA"; contém o trecho casado ("aguardando aprovação")
8. **Multi-alerta DESVIO + BLOQUEIO — ordem de gravidade**: índice de "DESVIO_LIMIAR" < índice de "BLOQUEIO_LINGUISTICO" no relatório
9. **Indicador textual "[DESVIO]" na linha de score (acessibilidade)**: linha de score contém "[DESVIO]" quando há alerta DESVIO_LIMIAR
10. **Indicador textual ausente quando no trilho**: linha de score não contém "[" quando `alertas=[]`
11. **Artefato inválido apontado sem omitir demais**: contém "Ingestão: artefato X falhou"; outros campos do update também presentes
12. **Histórico com 3 updates em ordem cronológica**: seção "Histórico de Delivery Score:" presente; as 3 linhas de update aparecem em ordem crescente de `numero`
13. **Histórico — update com dados insuficientes exibe texto, não número**: linha do update sem score contém "sem dados suficientes" (não um número)
14. **Histórico — update com alerta exibe "⚠"**: linha do histórico para update com alertas contém "⚠"
15. **Ausência de alerta é estado de sucesso explícito**: update sem alertas exibe mensagem afirmativa de "no trilho", não silêncio completo

```
class TestFormatar:
```
16. **`_formatar_barra(0)`**: retorna string de 10 `░`
17. **`_formatar_barra(100)`**: retorna string de 10 `█`
18. **`_formatar_barra(50)`**: retorna 5 `█` + 5 `░`
19. **`_formatar_alerta` com `gap_pp`**: string contém `"Gap: "` com sufixo `" pp"`
20. **`_formatar_alerta` sem `gap_pp` (BLOQUEIO_LINGUISTICO)**: string não contém `"Gap:"`

```
class TestSeedRastreabilidade:
```
21. **Seed pipeline completo — U2 rastreável**: relatório com seed processado contém `"aguardando aprovação"` como trecho do alerta de U2
22. **Seed pipeline completo — U1 no trilho, U2/U3 com desvio**: relatório contém "no trilho" associado ao Update #1 e "DESVIO_LIMIAR" associados a Update #2 e #3

**Total: 22 testes**

> A suíte acumulada após T05: **86 testes** (64 de T01–T04 + 22 de T05).

---

## Implementation Sequence

Cada passo = um commit coeso:

1. Criar `src/sprint_auditor/relatorio.py` com as constantes, os helpers internos (`_formatar_barra`, `_ordenar_alertas`, `_indicador_status`, `_linha_score`, `_formatar_trecho`, `_formatar_alerta`, `_formatar_update`, `_formatar_historico`) e `gerar_relatorio`
2. Criar `tests/test_relatorio.py` com 22 testes → `uv run pytest tests/test_relatorio.py -v` → todos passando
3. Rodar suíte completa → `uv run pytest tests/ -v` → 86 testes passando
4. Rodar `uv run ruff check src/ tests/` + `uv run mypy src/` → zero warnings

---

## Conventions Applied (from CLAUDE.md)

- **Stack:** Python + uv + pytest + ruff + mypy
- **Layout:** `src/sprint_auditor/` + `tests/` espelhando a estrutura de `src/`
- **Import:** sem prefixo `src.` (padrão de `ingestao.py`)
- **Sem mutação:** nenhuma função modifica `Projeto`, `Update`, `Artefato`, `Alerta` ou qualquer campo dos modelos de entrada
- **Nunca levanta exceção no caminho normal:** `gerar_relatorio` e todos os helpers retornam string em todos os cenários
- **Linguagem do código:** Português-Brasil (nomes de funções, variáveis, docstrings)
- **Comentários:** nenhum por padrão — WHY não óbvio documentado em Trade-offs
- **Datetime:** `data_kickoff` exibida como `YYYY-MM-DD` (ISO 8601 date, UTC implícito) — `rules/datetime.md`
- **Acessibilidade:** todo indicador de status tem rótulo textual (`[DESVIO]`, `[PIORA]`, `[BLOQUEIO]`, "ALTA", "MÉDIA") — nenhum status comunicado apenas por caractere especial sem label

---

## Ready to Code?

- [x] Arquitetura descrita com módulo e novos arquivos nomeados
- [x] Contratos (interfaces internas) em forma final com assinaturas completas e docstrings
- [x] Todos os estados da interface documentados com exemplos de output concretos (empty, success, error, multi-alerta)
- [x] Fórmula da barra de progresso especificada com tabela de exemplos
- [x] Ordem de gravidade dos alertas documentada com constante `_ORDEM_CATEGORIA`
- [x] Normalização de `trecho_fonte` documentada (`_formatar_trecho`: newlines→' / ', truncate 100)
- [x] Trade-offs não triviais com alternativa rejeitada e fonte da decisão documentadas
- [x] Riscos conhecidos listados com mitigações
- [x] Plano de teste cobre: empty state, dados insuficientes, no trilho, todos os tipos de alerta, multi-alerta, história, ingestão de erro, acessibilidade, integração com seed
- [x] Sequência de implementação é executável sem perguntas de clarificação
- [x] Nenhuma nova biblioteca introduzida (apenas stdlib + Pydantic v2 já instalado)
- [x] Convenções do CLAUDE.md citadas e respeitadas
