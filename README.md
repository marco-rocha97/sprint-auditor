# Sprint Auditor

Agente de auditoria que detecta desvios de entrega antes do comitê semanal.

Dado um projeto de onboarding (15 dias do kickoff à produção), o sistema ingere artefatos textuais — transcrições de calls e exports de board — calcula um **Delivery Score** (0–100) por update e dispara alertas rastreáveis quando o projeto está desviando, com causa provável, nível de confiança e ação sugerida.

---

## Saída de exemplo

```
============================================
SPRINT AUDITOR — Onboarding Alpha Corp
Kickoff: 2026-04-28
============================================

─── Update #1 — Dia 3 ──────────────────────
Delivery Score: ████████░░  83/100

Projeto no trilho — nenhum desvio detectado.

─── Update #2 — Dia 6 ──────────────────────
Delivery Score: ░░░░░░░░░░  0/100  [DESVIO]

⚠ DESVIO_LIMIAR (confiança: ALTA)
  Fase: configuracao | Dia: 6 | Gap: 60.0 pp
  Causa: Score 0 está abaixo do limiar 70 — progresso real estimado em 0%
         contra 60% esperado para a fase configuracao no dia 6
  Ação: Investigar bloqueios na fase configuracao e considerar escalonamento
  Fonte: art-u2-board | "Configuração: [✗] Acesso ao ambiente SAP, ..."

⚠ BLOQUEIO_LINGUISTICO (confiança: MÉDIA)
  Fase: configuracao | Dia: 6
  Causa: Sinal de bloqueio identificado na transcrição: 'aguardando aprovação'
  Fonte: art-u2-transcricao | "aguardando aprovação"

════════════════════════════════════════════
RESUMO DA DEMO
════════════════════════════════════════════
✓ Alerta disparado: Dia 6 — semana 1, antes do comitê
✗ Comitê semanal detectaria: Dia 12 — semana 2, tarde demais
  Antecipação: 6 dias
════════════════════════════════════════════
```

---

## Instalação

Requer Python ≥ 3.11 e [`uv`](https://docs.astral.sh/uv/).

```bash
uv sync
```

---

## Uso

```bash
# Rodar o pipeline de demo com o projeto sintético
uv run sprint-auditor-demo

# Ou via módulo
uv run python -m sprint_auditor.demo_pipeline
```

---

## Desenvolvimento

```bash
# Testes (102 testes, todos passando)
uv run pytest tests/ -v

# Lint
uv run ruff check src/ tests/

# Type-check
uv run mypy src/

# Formatar
uv run ruff format src/ tests/
```

---

## Arquitetura

O pipeline é linear. Cada módulo corresponde a uma tarefa e depende do anterior.

```
artefatos (texto)
      │
  ingestao.py       — valida e normaliza; artefato ilegível → registra e continua
      │
  score_engine.py   — compara progresso real vs. template de fases → Delivery Score 0–100
      │                (sem base → "dados insuficientes", nunca um número inventado)
  alert_engine.py   — 3 condições: limiar cruzado | deterioração consistente | bloqueio linguístico
      │                todo alerta: artefato-fonte + trecho + causa + nível de confiança
  relatorio.py      — relatório estático; ausência de alerta = estado de sucesso explícito
      │
  demo_pipeline.py  — script único que roda o seed sintético end-to-end
```

### Módulos

| Arquivo | Responsabilidade |
|---|---|
| `modelos.py` | Dataclasses Pydantic: `Projeto`, `Update`, `Artefato`, `DeliveryScore`, `Alerta` |
| `template_fases.py` | Curva de progresso esperado (%) por dia para cada uma das 4 fases |
| `seed.py` | Projeto sintético "derrapado" com ≥ 3 updates cobrindo artefatos distintos |
| `ingestao.py` | Validação e normalização de artefatos |
| `score_engine.py` | Cálculo do Delivery Score por fase e por update |
| `alert_engine.py` | Detecção de desvio de limiar, deterioração consistente e bloqueio linguístico |
| `relatorio.py` | Geração do relatório textual final |
| `demo_pipeline.py` | Entry point de demo: carrega seed, processa todos os updates, imprime relatório |

### Fases do projeto

| Fase | Dias |
|---|---|
| Discovery | 1–3 |
| Configuração | 4–7 |
| Desenvolvimento | 8–12 |
| Review | 13–15 |

### Tipos de alerta

| Categoria | Condição |
|---|---|
| `DESVIO_LIMIAR` | Score < 70 com gap ≥ 10 pp em relação ao esperado |
| `DETERIORACAO_CONSISTENTE` | Dois drops consecutivos sem cruzar o limiar |
| `BLOQUEIO_LINGUISTICO` | Sinais na transcrição: "aguardando aprovação", "bloqueado", "não pode avançar" |

### Regras de negócio inegociáveis

- **Silêncio é informação.** Sem desvio → nenhum alerta.
- **Todo alerta é rastreável.** Aponta artefato-fonte e trecho que originou a causa.
- **Nunca inventar um score.** Sem base suficiente → `dados_suficientes=False`.
- **Causa provável vem com nível de confiança.** Nunca apresentada como certeza.

---

## Stack

- Python 3.11+
- [Pydantic v2](https://docs.pydantic.dev/) — modelos de domínio
- [pytest](https://pytest.org/) — 102 testes
- [ruff](https://docs.astral.sh/ruff/) — lint + format
- [mypy](https://mypy-lang.org/) — type-check
- [uv](https://docs.astral.sh/uv/) — gerenciador de pacotes e ambiente

---

## Documentação

- [`docs/specs/sprint-auditor.md`](docs/specs/sprint-auditor.md) — SPEC do produto
- [`docs/plans/sprint-auditor.md`](docs/plans/sprint-auditor.md) — plano de tarefas
- [`docs/tech-specs/`](docs/tech-specs/) — tech specs de T01 a T06
