# Plan: Sprint Auditor

> Reference SPEC: [`docs/specs/sprint-auditor.md`](../specs/sprint-auditor.md)
> This plan breaks the SPEC into **independent tasks**, each ready to become a dedicated Tech Spec.
> There is **no** stack, schema, architecture, or estimation here — only behavior and sequencing.

---

## Target Outcome

- **Anchor result** (from SPEC): Dado um projeto sintético que derrapou, o sistema demonstra que *teria disparado o alerta de desvio vários dias antes* do ponto em que o comitê semanal o pegaria. A frase-alvo: "isso é exatamente o que a gente precisa olhar na sexta da semana 1".
- **MVP of this plan:** Todas as 6 tarefas fecham o anchor result — a cadeia completa artefatos → score → alerta → relatório → demo é a própria demonstração da hipótese.
- **Later phases:** Calibração fina do score, integração real com boards, transcrição ao vivo, aprendizado por histórico, visão multi-projeto — todos explicitamente fora deste MVP conforme o SPEC.

---

## Task Map

| # | Task | Cobre (SPEC) | Depende de | Fase | Status |
|---|------|--------------|------------|------|--------|
| T01 | Fundação: modelos de domínio, template de fases e seed sintético | Contratos de dados de todas as histórias | — | MVP | pending |
| T02 | Ingestão de artefatos | Story 5, Behavior "Artefato ilegível" | T01 | MVP | pending |
| T03 | Delivery Score engine | Stories 1–3, Behaviors "No trilho" e "Artefatos insuficientes" | T02 | MVP | pending |
| T04 | Alert engine | Stories 1, 3, 4, 6; Behaviors "Desvio cruza o limiar", "Deterioração lenta", "Causa provável" | T03 | MVP | pending |
| T05 | Gerador de relatório estático | Stories 1–3, 5–6; Experience Design completo | T04 | MVP | pending |
| T06 | Pipeline de demonstração | Anchor result, Success Metrics | T05 | MVP | pending |

> Ordem de execução: **T01 → T02 → T03 → T04 → T05 → T06** (cadeia linear; cada tarefa desbloqueia a próxima).

---

## Task Details

### T01 — Fundação: modelos de domínio, template de fases e seed sintético

- **Behavior delivered:** O sistema dispõe de um vocabulário compartilhado (o que é um projeto, um update, um artefato, um score, um alerta) e de um projeto sintético "derrapado" que serve de base para todas as tarefas seguintes.
- **Stories/behaviors covered in SPEC:** Contratos de dados implícitos em todas as histórias; em especial Story 5 (o que significa "sem artefatos suficientes") e Story 6 (o que é "nível de confiança" numa causa provável).
- **Acceptance criteria:**
  - Dado o template de 4 fases (Discovery, Configuração, Desenvolvimento, Review), quando consultado para o dia N de um projeto, então retorna o progresso esperado (%) para aquela fase naquele dia.
  - Dado o seed sintético carregado, quando listados os updates do projeto, então há pelo menos 3 updates cobertos por artefatos distintos — suficientes para evidenciar desvio progressivo.
  - Dado um update sem artefatos, quando consultado, então o modelo distingue explicitamente "sem dados" de "score zero".
- **Depends on:** —
- **Pending assumptions:** A definição das 4 fases e dos percentuais por dia é uma estimativa razoável para fins de demo — não requer calibração com histórico real (fora do escopo do MVP).
- **Tech Spec:** pending

---

### T02 — Ingestão de artefatos

- **Behavior delivered:** O sistema aceita transcrições de calls (texto) e exports de board (estruturado), valida a legibilidade de cada artefato e, quando um falha, registra o problema e segue processando os demais.
- **Stories/behaviors covered in SPEC:** Story 5 (saber quando não há artefatos suficientes); Behavior "Artefato ilegível" (apontar qual falhou, continuar com o restante).
- **Acceptance criteria:**
  - Dado um conjunto de artefatos onde um está mal formatado ou vazio, quando o processamento é executado, então o sistema registra qual artefato falhou e os demais são processados normalmente.
  - Dado um conjunto sem nenhum artefato, quando a ingestão é executada, então o resultado sinaliza "sem artefatos disponíveis" para o score engine.
  - Dado um artefato válido de transcrição e um de board, quando ingeridos, então ambos são convertidos para a representação interna definida em T01.
- **Depends on:** T01
- **Pending assumptions:** —
- **Tech Spec:** pending

---

### T03 — Delivery Score engine

- **Behavior delivered:** Para cada update de um projeto, o sistema compara o progresso real dos artefatos com o esperado pelo template de fases e produz um Delivery Score (0–100) — ou sinaliza "dados insuficientes" quando não há base.
- **Stories/behaviors covered in SPEC:** Story 1 (alerta com causa — precisa do score para decidir se há desvio); Story 2 (histórico do score ao longo dos updates); Story 3 (fase e motivo do atraso — depende do score por fase); Behavior "Projeto no trilho" (score sem alerta); Behavior "Artefatos insuficientes" (não exibir número inventado).
- **Acceptance criteria:**
  - Dado um projeto no dia 6, fase Configuração, com progresso real de 38% e esperado de 60%, quando o score é calculado, então o resultado reflete o gap de -22 pp e o score cai abaixo de 100.
  - Dado um projeto com artefatos que mostram progresso alinhado ao template, quando o score é calculado, então o resultado está dentro da faixa "no trilho" (sem desvio).
  - Dado um projeto sem artefatos processados, quando o score é requisitado, então o sistema retorna estado "dados insuficientes" em vez de um número.
  - Dado dois updates consecutivos do mesmo projeto, quando os scores são consultados, então o histórico exibe a evolução entre eles.
- **Depends on:** T02
- **Pending assumptions:** —
- **Tech Spec:** pending

---

### T04 — Alert engine

- **Behavior delivered:** O sistema detecta três condições de desvio — threshold único cruzado, deterioração consistente sem cruzar o threshold, e causa provável identificada por sinais linguísticos — e produz alertas rastreáveis com nível de confiança.
- **Stories/behaviors covered in SPEC:** Story 1 (alerta com causa provável); Story 3 (fase e motivo do atraso); Story 4 (silêncio quando no trilho); Story 6 (causa com nível de confiança); Behavior "Desvio cruza o limiar"; Behavior "Deterioração lenta sem cruzar o limiar"; Behavior "Causa provável a partir de sinais de bloqueio"; Behavior "Projeto no trilho — sistema em silêncio".
- **Acceptance criteria:**
  - Dado um projeto cujo score de um update cruza o limiar de desvio, quando o alert engine processa o update, então um alerta de desvio é gerado com fase, dia, gap previsto-vs-real e causa provável.
  - Dado um projeto com scores caindo em updates consecutivos sem cruzar o limiar, quando o alert engine processa o update mais recente, então um alerta de "piora consistente" é gerado.
  - Dado uma transcrição com sinais de bloqueio ("ainda não temos acesso ao SAP", "aguardando aprovação"), quando o alert engine analisa o artefato, então a causa provável cita o bloqueio e a ação sugerida é "bloqueio externo → escalar para o FDE Lead".
  - Dado um projeto no trilho em todos os updates, quando o alert engine processa qualquer update, então nenhum alerta é gerado.
  - Todo alerta inclui: artefato-fonte, trecho que originou a causa, categoria da causa e nível de confiança (explícito, não implícito).
- **Depends on:** T03
- **Pending assumptions:** —
- **Tech Spec:** pending

---

### T05 — Gerador de relatório estático

- **Behavior delivered:** Para cada update processado, o sistema gera um relatório legível que mostra o Delivery Score atual, o histórico de scores, e — quando aplicável — o alerta de desvio no topo com causa provável, ação sugerida e rastreabilidade ao artefato-fonte. Todos os estados da interface são cobertos.
- **Stories/behaviors covered in SPEC:** Stories 1, 2, 3, 5, 6; Experience Design completo (empty state, success state, error state); princípios "silêncio é informação", "todo alerta é rastreável", "nunca inventar um score", "causa com nível de confiança"; acessibilidade (legível em texto puro, sem dependência de cor).
- **Acceptance criteria:**
  - Dado um projeto sem artefatos, quando o relatório é gerado, então exibe "sem dados suficientes para um Delivery Score confiável" sem nenhum número.
  - Dado um projeto no trilho, quando o relatório é gerado, então exibe o score sem nenhuma seção de alerta (ausência de alerta é estado de sucesso explícito).
  - Dado um projeto com alerta de desvio, quando o relatório é gerado, então o alerta aparece no topo com: fase, dia, gap, causa provável, nível de confiança, ação sugerida, artefato-fonte e trecho.
  - Dado um projeto com histórico de múltiplos updates, quando o relatório é gerado, então a evolução do score é visível em ordem cronológica.
  - Dado um artefato que falhou na ingestão, quando o relatório é gerado, então o relatório aponta qual artefato falhou sem omitir os demais resultados.
  - O relatório é legível em texto puro e não depende de cor para comunicar status (todo indicador visual tem rótulo textual equivalente).
- **Depends on:** T04
- **Pending assumptions:** —
- **Tech Spec:** pending

---

### T06 — Pipeline de demonstração

- **Behavior delivered:** Um script end-to-end executa o projeto sintético "derrapado" do T01 através de todo o pipeline e produz o relatório de cada update, evidenciando que o alerta de desvio teria sido gerado vários dias antes do comitê semanal que o detectaria manualmente.
- **Stories/behaviors covered in SPEC:** Anchor result (detecção precoce vs. comitê); Success Metrics ("reduzir de ~1 semana para ≤2 dias"); a frase-alvo do entrevistador.
- **Acceptance criteria:**
  - Dado o projeto sintético carregado, quando o pipeline de demo é executado, então gera relatórios para cada update cronológico do projeto.
  - Dado o relatório do update do dia 6 (dentro da semana 1), quando visualizado, então o alerta de desvio já está presente com causa provável identificada.
  - Dado o contraste explícito no output da demo, quando apresentado, então fica claro que o comitê semanal da semana 2 teria detectado o mesmo desvio ~6 dias depois.
  - O pipeline roda com um único comando, sem configuração manual entre updates.
- **Depends on:** T05
- **Pending assumptions:** —
- **Tech Spec:** pending

---

## External Dependencies

Nenhuma dependência externa bloqueia este plano — o MVP usa dados sintéticos e não requer acesso a APIs externas, boards reais ou integrações.

---

## Out of This Plan

Itens do SPEC **deliberadamente fora do MVP**, conforme a seção "Out of Scope":

- **Calibração fina do Delivery Score** — requer histórico real; o MVP prova a hipótese, não a precisão do número.
- **Transcrição de áudio ao vivo / em tempo real** — entrada são textos já prontos.
- **Integração real com ClickUp / Linear / Discord** — a demo usa seed sintético.
- **Sugestão de intervenção por aprendizado de padrões** — regras fixas no MVP (T04).
- **Visão de portfólio multi-projeto / ranking de squads** — a demo é sobre um único projeto.
- **Autenticação, contas e permissões** — irrelevante para demonstração.
- **Ingestão automática / polling** — processamento sob demanda, manual.

---

## Ready for Tech Spec?

- [x] Every task cites at least one story/behavior from the SPEC
- [x] Every task fits in one Tech Spec (no mega-tasks)
- [x] Dependencies are explicit and cycle-free
- [x] MVP is identified and closes the anchor result
- [x] Zero implementation details (no stack, schema, endpoint, infra)
- [x] SPEC out-of-scope is respected
- [x] External blocking dependencies are listed
