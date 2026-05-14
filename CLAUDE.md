# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## O que é este projeto

**Sprint Auditor** — agente que detecta desvios de entrega antes do comitê semanal.

Dado um projeto de onboarding (15 dias do kickoff à produção), o sistema ingere artefatos textuais (transcrições de calls e exports de board), calcula um **Delivery Score** (0–100) por update e dispara alertas rastreáveis quando o projeto está desviando — com causa provável, nível de confiança e ação sugerida.

Documentação viva: [`docs/specs/sprint-auditor.md`](docs/specs/sprint-auditor.md) (SPEC) · [`docs/plans/sprint-auditor.md`](docs/plans/sprint-auditor.md) (Plan).

---

## Stack e comandos

```bash
# Instalar dependências (cria o venv em .venv/)
uv sync

# Rodar todos os testes
uv run pytest tests/ -v

# Rodar um único arquivo de testes
uv run pytest tests/caminho/test_arquivo.py -v

# Rodar um único teste
uv run pytest tests/caminho/test_arquivo.py::test_nome -v

# Lint + type-check
uv run ruff check src/ tests/
uv run mypy src/

# Formatar
uv run ruff format src/ tests/
```

O projeto usa `src/` layout — o pacote principal está em `src/sprint_auditor/`. Os testes ficam em `tests/` espelhando a estrutura de `src/`.

---

## Arquitetura

O pipeline é linear: cada módulo abaixo corresponde a uma tarefa do Plan (T01–T06) e depende do anterior.

```
artefatos (texto)
      │
  [T02] ingestao      — valida e normaliza; artefato ilegível → registra e continua
      │
  [T03] score_engine  — compara progresso real vs. template de fases → Delivery Score 0–100
      │                  (sem base → "dados insuficientes", nunca um número inventado)
  [T04] alert_engine  — 3 condições: threshold cruzado | deterioração consistente | bloqueio linguístico
      │                  todo alerta: artefato-fonte + trecho + causa + nível de confiança
  [T05] relatorio     — relatório estático; ausência de alerta = estado de sucesso explícito
      │
  [T06] demo_pipeline — script único que roda o seed sintético end-to-end
```

### Módulo T01 — Fundação

`modelos.py` — dataclasses/Pydantic do domínio: `Projeto`, `Update`, `Artefato`, `DeliveryScore`, `Alerta`.

`template_fases.py` — template das 4 fases (Discovery → Configuração → Desenvolvimento → Review) com progresso esperado por dia.

`seed.py` — projeto sintético "derrapado" com ≥ 3 updates cobrindo artefatos distintos.

### Vocabulário de domínio

| Termo | Significado |
|---|---|
| **Update** | Um ciclo de processamento de artefatos de um projeto (uma "rodada" de avaliação) |
| **Artefato** | Transcrição de call ou export de board associado a um update |
| **Delivery Score** | Número 0–100 que reflete o gap entre progresso real e esperado |
| **Alerta** | Resultado estruturado com causa provável, confiança e ação sugerida |
| **Template de fases** | Curva de progresso esperado (%) por dia para cada fase do projeto |

### Regras de negócio inegociáveis

- **Silêncio é informação.** Sem desvio → nenhum alerta. O sistema não fala à toa.
- **Todo alerta é rastreável.** Aponta artefato-fonte e trecho que originou a causa provável.
- **Nunca inventar um score.** Sem base suficiente → `"dados insuficientes"`.
- **Causa provável vem com nível de confiança.** Nunca apresentada como certeza absoluta.
