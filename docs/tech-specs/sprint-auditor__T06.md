# Tech Spec: Pipeline de Demonstração — `T06`

> **SPEC:** [`docs/specs/sprint-auditor.md`](../specs/sprint-auditor.md)
> **Plan:** [`docs/plans/sprint-auditor.md`](../plans/sprint-auditor.md) — tarefa `T06`
> **Convenções aplicadas:** `CLAUDE.md` (projeto) + regras globais do usuário
>
> Este documento detalha **como** entregar a tarefa. O **porquê** vive na SPEC; **o quê** e **em que ordem**, no Plan.

---

## Task Scope

- **Behavior delivered** (from Plan): Um script end-to-end executa o projeto sintético "derrapado" do T01 através de todo o pipeline e produz o relatório de cada update, evidenciando que o alerta de desvio teria sido gerado vários dias antes do comitê semanal que o detectaria manualmente.
- **SPEC stories/criteria covered:** Anchor result (detecção precoce vs. comitê); Success Metrics ("reduzir de ~1 semana para ≤2 dias"); a frase-alvo do entrevistador ("isso é exatamente o que a gente precisa olhar na sexta da semana 1").
- **Depends on:** T01 (`carregar_projeto_seed`, `Projeto`, `Update`); T02 (`ingerir_artefatos`); T03 (`calcular_delivery_score`); T04 (`analisar_alertas`); T05 (`gerar_relatorio`)
- **External dependencies:** nenhuma

---

## Architecture

- **General approach:** T06 adiciona `src/sprint_auditor/demo_pipeline.py` com uma função pública `executar_demo()` que orquestra o pipeline linear T02→T03→T04→T05 sobre o projeto seed do T01. Para cada update do seed (em ordem crescente de número), o módulo ingere os artefatos, calcula o score e detecta alertas — construindo um novo `Update` com os resultados via `model_copy`, sem mutação dos modelos originais. Ao final, gera o relatório completo com `gerar_relatorio` e acrescenta uma seção de contraste (`_gerar_contraste`) que evidencia a antecipação de detecção vs. o comitê semanal. O script é exposto como CLI via `pyproject.toml`.

- **Affected modules:**
  - `src/sprint_auditor/demo_pipeline.py` — novo módulo (orquestrador do pipeline)
  - `tests/test_demo_pipeline.py` — novo arquivo de testes
  - `pyproject.toml` — adição de `[project.scripts]` com `sprint-auditor-demo`

- **New files:** `src/sprint_auditor/demo_pipeline.py`, `tests/test_demo_pipeline.py`

- **Reused patterns:**
  - `carregar_projeto_seed()` — `seed.py` (T01): fonte do projeto sintético
  - `ingerir_artefatos()` — `ingestao.py` (T02)
  - `calcular_delivery_score()` — `score_engine.py` (T03)
  - `analisar_alertas()` — `alert_engine.py` (T04)
  - `gerar_relatorio()` — `relatorio.py` (T05): formatador puro que lê score/alertas já preenchidos
  - `update.model_copy(update={...})` — Pydantic v2: padrão de não-mutação já usado em T03 e T04
  - Import sem prefixo `src.` — padrão de `ingestao.py`

> **Decision source:** CLAUDE.md (arquitetura do pipeline T01→T06); contrato do T05 "T06 vai preencher score e alertas antes de chamar `gerar_relatorio`" (Trade-off 1 do T05 Tech Spec); escolhas do usuário nesta conversa (contraste depois do relatório, stdout, pyproject.toml script).

---

## Contracts

### `src/sprint_auditor/demo_pipeline.py`

```python
from sprint_auditor.alert_engine import analisar_alertas
from sprint_auditor.ingestao import ingerir_artefatos
from sprint_auditor.modelos import Projeto, Update
from sprint_auditor.relatorio import gerar_relatorio
from sprint_auditor.score_engine import calcular_delivery_score
from sprint_auditor.seed import carregar_projeto_seed

_LARGURA_LINHA: int = 44
_DIA_COMITE_SEMANA_2: int = 12  # comitê semanal da semana 2 — base para o cálculo de antecipação


def _processar_update(update: Update, anteriores: list[Update]) -> Update:
    """Executa o pipeline T02→T03→T04 sobre um único update e retorna update processado.

    Pipeline:
        1. Ingere os artefatos do update (T02)
        2. Calcula o Delivery Score a partir do resultado da ingestão e do dia do update (T03)
        3. Detecta alertas com o update-com-score e contexto dos updates anteriores (T04)

    Retorna novo Update (via model_copy) com score e alertas preenchidos.
    Não muta o update de entrada nem a lista de anteriores.
    Nunca levanta exceção.
    """


def _gerar_contraste(projeto: Projeto) -> str:
    """Gera a seção de contraste da demo: quando o alerta foi disparado vs. quando o comitê detectaria.

    Varre os updates do projeto em ordem crescente de numero para encontrar o primeiro com alertas.
    Calcula antecipação = _DIA_COMITE_SEMANA_2 - dia_primeiro_alerta.
    Se nenhum update tiver alertas, retorna seção indicando ausência de desvio detectado.

    Formato (caso com alerta):
        ════════════════════════════════════════════
        RESUMO DA DEMO
        ════════════════════════════════════════════
        ✓ Alerta disparado: Dia 6 — semana 1, antes do comitê
        ✗ Comitê semanal detectaria: Dia 12 — semana 2, tarde demais
          Antecipação: 6 dias

        "isso é exatamente o que a gente precisa olhar
          na sexta da semana 1"
        ════════════════════════════════════════════

    Retorna string sem trailing newline. Nunca levanta exceção.
    """


def executar_demo() -> str:
    """Executa o pipeline de demo end-to-end e retorna o output completo como string.

    Fluxo:
        1. Carrega o projeto sintético via carregar_projeto_seed()
        2. Ordena os updates por numero (crescente)
        3. Para cada update, chama _processar_update(update, atualizados_anteriores)
           e acumula o resultado em atualizados_anteriores
        4. Monta Projeto com updates processados via model_copy
        5. Gera relatório completo via gerar_relatorio()
        6. Gera seção de contraste via _gerar_contraste()
        7. Retorna relatório + '\n\n' + contraste

    Returns:
        String com relatório completo seguido de seção de contraste.
        Adequado para print() direto.
        Nunca levanta exceção.
    """


def main() -> None:
    """CLI entry point — registrado em pyproject.toml como sprint-auditor-demo.

    Chama executar_demo() e imprime o resultado em stdout via print().
    Sem argumentos de linha de comando, sem configuração manual entre updates.
    """
    print(executar_demo())
```

### `pyproject.toml` — adição em `[project.scripts]`

```toml
[project.scripts]
sprint-auditor-demo = "sprint_auditor.demo_pipeline:main"
```

---

## Data Model

T06 não define novos modelos — todos os tipos são importados de T01–T05.

### Constantes do módulo

| Constante | Valor | Papel |
|---|---|---|
| `_LARGURA_LINHA` | `44` | Comprimento dos separadores `═` na seção de contraste (consistente com `relatorio.py`) |
| `_DIA_COMITE_SEMANA_2` | `12` | Dia do projeto em que o comitê semanal da semana 2 ocorreria — base para o cálculo de antecipação |

### Invariantes de processamento

```
atualizados_anteriores: list[Update] = []
para cada update em sorted(projeto.updates, key=lambda u: u.numero):
    atualizado = _processar_update(update, atualizados_anteriores)
    atualizados_anteriores.append(atualizado)

projeto_processado = projeto.model_copy(update={'updates': atualizados_anteriores})
```

**Por que a ordem importa:** `analisar_alertas(update_atual, anteriores)` exige que `anteriores` contenha
os updates já processados (com `score` preenchido) para que `_detectar_deterioracao_consistente` possa
comparar scores entre updates consecutivos. Processar fora de ordem quebraria silenciosamente esse detector.

### Contrato interno de `_processar_update`

```
resultado_ingestao = ingerir_artefatos(update.artefatos)
score = calcular_delivery_score(resultado_ingestao, update.dia_projeto)
update_com_score = update.model_copy(update={'score': score})
alertas = analisar_alertas(update_com_score, anteriores)
return update_com_score.model_copy(update={'alertas': alertas})
```

O `update_com_score` intermediário é necessário porque `analisar_alertas` lê `update_atual.score`
para executar `_detectar_desvio_limiar`.

### Lógica da seção de contraste com o seed atual

| Update | Dia | Alertas | Papel no contraste |
|---|---|---|---|
| #1 | 3 | 0 | Ignorado — no trilho |
| #2 | 6 | 2 (DESVIO + BLOQUEIO) | **dia_primeiro_alerta = 6** |
| #3 | 9 | 1 (DETERIORAÇÃO) | Ignorado — alerta já foi no Update #2 |

```
antecipacao = _DIA_COMITE_SEMANA_2 - dia_primeiro_alerta = 12 - 6 = 6 dias
```

---

## External Integrations

Nenhuma.

---

## Trade-offs e Alternativas Rejeitadas

**Decisão: `_processar_update` cria novos objetos via `model_copy`, sem mutação**
- Alternativa rejeitada: atribuir diretamente `update.score = score` e `update.alertas = alertas`
- Motivo: Pydantic v2 `BaseModel` é imutável por padrão; `model_copy` é o padrão estabelecido no projeto (vide T03 e T04). Consistência com o padrão existente evita surpresas e mantém a invariante de imutabilidade documentada nos Tech Specs anteriores.
- Trade-off: código levemente mais verboso (uma chamada de `model_copy` extra).
- Fonte: padrão de não-mutação em `alert_engine.py` (T04); `anti-patterns.md` (imutabilidade preferida).

**Decisão: seção de contraste após o relatório completo**
- Alternativa rejeitada: contraste antes do relatório (TL;DR no topo)
- Motivo: o relatório é a evidência; o contraste é o veredicto. Mostrar os dados primeiro e concluir depois espelha a narrativa "aqui estão os fatos → esta é a conclusão" — mais persuasiva numa demo ao vivo onde o apresentador controla o ritmo. Decisão do usuário nesta conversa.
- Trade-off: o entrevistador precisa rolar o output para chegar à conclusão — não é problema numa demo ao vivo.
- Fonte: decisão do usuário nesta conversa.

**Decisão: `_DIA_COMITE_SEMANA_2 = 12` como constante explícita**
- Alternativa rejeitada: calcular dinamicamente (ex: próximo múltiplo de 7 após o dia do primeiro alerta)
- Motivo: o seed é fixo e o propósito é demonstrar um ponto concreto. Uma constante nomeada documenta a suposição de domínio ("comitê semanal da semana 2 ≈ dia 12") mais claramente do que uma heurística de calendário. Para o MVP, a constante é suficiente e auditável.
- Trade-off: se o seed mudar (dia do primeiro alerta diferente de 6), a antecipação calculada muda mas a constante permanece a mesma — ainda correto desde que o primeiro alerta seja anterior a 12.
- Fonte: Plan T06 ("comitê semanal da semana 2 teria detectado ~6 dias depois").

**Decisão: stdout apenas, sem escrita em arquivo**
- Alternativa rejeitada: gravar em `demo_relatorio.txt`
- Motivo: stdout é suficiente para a demo; não cria artefato residual no repositório; o entrevistador pode redirecionar com `>` se quiser salvar. Decisão do usuário nesta conversa.
- Trade-off: o output não persiste automaticamente entre execuções — irrelevante para o MVP.
- Fonte: decisão do usuário nesta conversa.

**Decisão: `[project.scripts]` em `pyproject.toml` para o CLI entry point**
- Alternativa rejeitada: `uv run python -m sprint_auditor.demo_pipeline` sem alterar `pyproject.toml`
- Motivo: um único comando `uv run sprint-auditor-demo` é mais limpo e satisfaz diretamente o critério de aceitação "roda com um único comando, sem configuração manual entre updates". Decisão do usuário nesta conversa.
- Trade-off: requer `uv sync` após alterar `pyproject.toml` para instalar o script — passo único e esperado.
- Fonte: decisão do usuário nesta conversa; Plan T06 critério de aceitação.

---

## Risks and Mitigations

| Risco | Impacto | Mitigação |
|---|---|---|
| `updates_anteriores` passados para `analisar_alertas` ainda com `alertas=[]` (recém-criados sem alertas ainda) | Sem impacto — `_detectar_deterioracao_consistente` lê apenas `update.score` dos anteriores, não `update.alertas` | Verificado no contrato de T04: o detector de deterioração depende só de `.score` |
| `calcular_delivery_score` retorna `dados_suficientes=False` para um update (T03 sem artefatos válidos) | `analisar_alertas` entra no branch "só detectores sem score" — comportamento correto per T04 | Documentado no contrato do T04; coberto indiretamente pelos testes de integração com o seed |
| Seed alterado em T01 após esta Tech Spec (ex: sem update no dia 6) | `_gerar_contraste` não encontra alerta; exibe "sem desvio detectado" | Contrato defensivo em `_gerar_contraste`: caso sem alertas retorna mensagem explícita em vez de falhar |
| `pyproject.toml` alterado mas `uv sync` não executado | `uv run sprint-auditor-demo` retorna erro de comando não encontrado | Documentado na sequência de implementação: passo 2 inclui `uv sync` |
| `model_copy` com campo com validação que rejeita o valor (ex: validator em `Update`) | `ValidationError` em runtime | Score é computado por T03 respeitando o range 0–100; alertas são `list[Alerta]` sem restricão de tamanho — impossível pelo contrato de T03/T04 |

---

## Testing Plan

**Framework:** pytest. Fonte: CLAUDE.md (`uv run pytest tests/ -v`).
**Padrão de organização:** classes por responsabilidade, conforme `tests/test_relatorio.py`.

### `tests/test_demo_pipeline.py` — 9 testes

```
class TestExecutarDemo:
```
1. **Pipeline completo executa sem exceção**: `executar_demo()` retorna string não vazia sem levantar exceção
2. **Output contém seções dos 3 updates**: output contém `"Update #1"`, `"Update #2"` e `"Update #3"`
3. **Update #1 está no trilho**: output contém `"no trilho"` associado à seção do Update #1
4. **Alerta DESVIO_LIMIAR presente no Update #2 (dia 6)**: output contém `"DESVIO_LIMIAR"` e `"Dia: 6"`
5. **Alerta DETERIORACAO_CONSISTENTE presente no Update #3 (dia 9)**: output contém `"DETERIORACAO_CONSISTENTE"`
6. **Rastreabilidade: ID do artefato-fonte no output**: output contém `"art-u2-board"` (ID definido no seed para o artefato board do Update #2)
7. **Seção de contraste presente**: output contém `"RESUMO DA DEMO"` e `"Antecipação"`
8. **Contraste mostra 6 dias de antecipação**: output contém `"6 dias"`

```
class TestMain:
```
9. **`main()` imprime o output de `executar_demo()` em stdout**: captura stdout com `capsys`; o output capturado contém `"SPRINT AUDITOR"`

**Total: 9 testes**

> A suíte acumulada após T06: **95 testes** (86 de T01–T05 + 9 de T06).

---

## Implementation Sequence

Cada passo = um commit coeso:

1. Criar `src/sprint_auditor/demo_pipeline.py` com `_processar_update`, `_gerar_contraste`, `executar_demo` e `main`
2. Atualizar `pyproject.toml` adicionando `[project.scripts]` com `sprint-auditor-demo = "sprint_auditor.demo_pipeline:main"` → executar `uv sync`
3. Criar `tests/test_demo_pipeline.py` com 9 testes → `uv run pytest tests/test_demo_pipeline.py -v` → todos passando
4. Rodar suíte completa → `uv run pytest tests/ -v` → 95 testes passando
5. Rodar `uv run ruff check src/ tests/` + `uv run mypy src/` → zero warnings
6. Validar manualmente: `uv run sprint-auditor-demo` → output completo com relatório + contraste mostrando "6 dias de antecipação"

---

## Conventions Applied (from CLAUDE.md)

- **Stack:** Python + uv + pytest + ruff + mypy
- **Layout:** `src/sprint_auditor/` + `tests/` espelhando a estrutura de `src/`
- **Import:** sem prefixo `src.` (padrão de `ingestao.py`)
- **Sem mutação:** `_processar_update` cria novos objetos via `model_copy`; nenhum modelo de entrada é modificado
- **Nunca levanta exceção no caminho normal:** `executar_demo`, `_processar_update` e `_gerar_contraste` retornam em todos os cenários
- **Linguagem do código:** Português-Brasil (nomes de funções, variáveis, docstrings)
- **Comentários:** nenhum por padrão — WHY não óbvio documentado nos Trade-offs acima
- **Sem nova biblioteca:** apenas stdlib + Pydantic v2 + módulos do próprio projeto

---

## Ready to Code?

- [x] Arquitetura descrita com módulo e novos arquivos nomeados
- [x] Contratos com assinaturas completas e docstrings para todas as funções públicas e privadas
- [x] Contrato interno de `_processar_update` detalhado com pseudocódigo (ordem das chamadas importa)
- [x] Invariante de ordem dos updates documentada (impacto em `analisar_alertas`)
- [x] Lógica da seção de contraste documentada com fórmula e tabela do seed (resultado esperado: 6 dias)
- [x] Constante `_DIA_COMITE_SEMANA_2 = 12` justificada com fonte no Plan
- [x] Atualização de `pyproject.toml` e `uv sync` incluídos na sequência de implementação
- [x] Trade-offs com alternativa rejeitada e fonte da decisão documentados para todas as decisões não-triviais
- [x] Riscos listados com mitigações
- [x] Plano de teste cobre: execução sem erro, 3 updates, no trilho, DESVIO, DETERIORAÇÃO, rastreabilidade, seção de contraste, antecipação de 6 dias, main com stdout
- [x] Nenhuma nova biblioteca introduzida
- [x] Convenções do CLAUDE.md citadas e respeitadas
