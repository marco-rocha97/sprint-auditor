# SPEC: Sprint Auditor

> O agente que protege a promessa de 15 dias da Khal por dentro — instrumenta a própria operação de delivery com o mesmo rigor com que a Khal instrumenta o agente do cliente em produção.

---

## Problem Definition

- **Dor concreta:** O Head de Operações descobre que um squad de FDE escorregou da promessa de "15 dias do kickoff à produção" apenas no comitê semanal — quando o atraso já é fato consumado. Nesse ponto a única saída é puxar um FDE de outro onboarding para "salvar" a conta, o que queima margem (hora extra + desconto comercial) e contamina o próximo projeto. O escorregão é silencioso: ninguém vê o desvio começar, só veem o resultado.
- **Personas afetadas:**
  - **Head de Operações da Khal** — decisor que arca com a margem queimada e responde pela promessa comercial. É quem precisa agir cedo.
  - **FDE Lead do squad** — quem poderia corrigir o curso (escalar, renegociar escopo, pedir reforço) se soubesse do desvio a tempo.
- **Comportamento atual:** O acompanhamento do delivery é manual e tardio. O status real só aparece consolidado no comitê semanal; entre comitês, o desvio é percebido por intuição ou quando alguém reclama. A Khal observa o agente do cliente com Agent Score e logging, mas não observa o próprio agente humano — o FDE — com o mesmo rigor.

---

## Success Metrics

- **Mudança observável de comportamento:** A operação passa a agir sobre um desvio na quarta-feira da semana 1, em vez de descobri-lo no domingo da semana 2. A conversa de intervenção (escalar, renegociar, reforçar) acontece com dias de antecedência sobre o comitê.
- **Métrica âncora (negócio):** Tempo médio entre o início do desvio e sua detecção — alvo: reduzir de ~1 semana para ≤2 dias. Métrica secundária: taxa de projetos entregues em ≤15 dias úteis.
- **Critério de sucesso do MVP (demo):** Dado um projeto sintético que derrapou, o sistema demonstra que **teria disparado o alerta de desvio vários dias antes** do ponto em que o comitê semanal o pegaria. A frase-alvo do entrevistador: "isso é exatamente o que a gente precisa olhar na sexta da semana 1".

---

## User Stories

- Como **Head de Operações**, quero receber um alerta de desvio com a causa provável já anotada, para decidir a intervenção antes do comitê semanal.
- Como **Head de Operações**, quero ver o histórico do Delivery Score de um projeto ao longo dos updates, para distinguir um tropeço pontual de uma deterioração consistente.
- Como **FDE Lead**, quero saber em qual fase e por qual motivo provável meu squad está atrasado, para corrigir o curso enquanto ainda dá tempo.
- Como **FDE Lead**, quero que o sistema fique em silêncio quando o projeto está no trilho, para que o alerta signifique algo quando aparecer.
- Como **Head de Operações**, quero que o sistema indique quando não há artefatos suficientes para avaliar, em vez de inventar um número (edge case).
- Como **FDE Lead**, quero que o alerta traga a causa provável com seu nível de confiança explícito, para não tratar um falso positivo como certeza (caso de falha esperada).

---

## Expected Behaviors

```gherkin
Scenario: Projeto no trilho — sistema em silêncio
  Given um projeto cujos artefatos mostram progresso alinhado ao template das 4 fases
  When um novo update é processado
  Then o relatório é atualizado com o Delivery Score
  And nenhum alerta de desvio é disparado

Scenario: Desvio cruza o limiar
  Given um projeto no dia 6, na fase Configuração
  And o progresso real está em 38% contra 60% esperado pelo template
  When o update é processado
  Then um alerta de desvio é disparado
  And o alerta indica fase, dia, gap previsto-vs-real e a causa provável

Scenario: Deterioração lenta sem cruzar o limiar
  Given um projeto cujo Delivery Score caiu em updates consecutivos
  And nenhum update isolado cruzou o limiar de desvio
  When o update mais recente é processado
  Then um alerta de piora consistente é disparado

Scenario: Causa provável a partir de sinais de bloqueio
  Given uma transcrição que contém sinais linguísticos de bloqueio ("ainda não temos acesso ao SAP")
  When o update é processado
  Then a causa provável do alerta cita o bloqueio identificado
  And o alerta traz uma ação sugerida derivada de regra ("bloqueio externo → escalar para o FDE Lead")

Scenario: Histórico mostra o score caindo
  Given um projeto com pelo menos dois updates processados
  When o Head de Operações abre o relatório
  Then ele vê a evolução do Delivery Score entre os updates
  And vê em qual update o desvio começou

Scenario: Artefatos insuficientes
  Given um projeto sem nenhuma call ou board processado
  When o relatório é gerado
  Then o sistema indica que não há dados suficientes para um Delivery Score confiável
  And não exibe um número inventado

Scenario: Artefato ilegível
  Given um conjunto de artefatos em que um deles está mal formatado ou ilegível
  When o processamento é executado
  Then o relatório aponta qual artefato falhou
  And segue a avaliação com os artefatos restantes, sem abortar tudo
```

---

## Experience Design

- **Jornada do usuário:**
  1. A operação reúne os artefatos do projeto — transcrições de calls (Discovery, dailies, reviews) e o export do board — e os fornece ao sistema.
  2. O sistema processa os artefatos e gera ou atualiza um **relatório estático** do projeto.
  3. O Head de Operações / FDE Lead abre o relatório: vê o Delivery Score atual (0–100), o histórico do score ao longo dos updates e, se houver, o alerta de desvio destacado no topo com causa provável e ação sugerida.
  4. O destinatário decide a intervenção.
- **Estados da interface:**
  - **Empty state:** projeto sem artefatos processados — o relatório mostra "sem dados suficientes para um Delivery Score confiável", lista o que falta e não exibe número.
  - **Loading state:** o processamento de artefatos é um passo explícito e finito; o relatório só passa a existir quando o processamento termina — não há tela "congelada".
  - **Success state:** relatório com Delivery Score, histórico e — quando aplicável — alerta. A **ausência de alerta é em si um estado de sucesso** ("projeto no trilho").
  - **Error state:** artefato ilegível ou mal formatado — o relatório aponta qual artefato falhou e segue com os demais.
- **Princípios inegociáveis:**
  - **Silêncio é informação.** Sem alerta = no trilho. O sistema não fala à toa — essa é a defesa direta contra o "professor irritante".
  - **Todo alerta é rastreável.** Aponta o artefato e o trecho que originou a causa provável (coerente com o DNA de "cada decisão rastreável" da Khal).
  - **Nunca inventar um score.** Sem base suficiente, o sistema diz "não sei" em vez de fingir precisão.
  - **Causa provável vem com nível de confiança.** Nunca é apresentada como certeza absoluta.
- **Acessibilidade:** relatório legível em texto puro e navegável por teclado; não depende de cor para comunicar — o semáforo do score sempre tem rótulo textual equivalente.

---

## Business Constraints

- **Stakeholders que exigem alinhamento:** este MVP é um artefato de entrevista — o "aprovador" imediato é o entrevistador da Khal. Na visão de produto, exigiria alinhamento do Head de Operações e da liderança de delivery antes de ir a campo.
- **Regras de negócio inegociáveis:** não há regra legal ou contratual. A única regra dura é de **credibilidade** — o sistema não pode apresentar um falso positivo como certeza, porque isso destrói a confiança do squad e mata a adoção (o risco central do "professor irritante").
- **Timeline crítico:** demo na noite de domingo, janela de construção de ~3 dias. O MVP **prova a hipótese** (detecção precoce é possível e útil), **não a calibragem fina** do score — e isso deve ser explícito na própria demo.

> Decisões técnicas (stack, formato dos artefatos, fórmula do score, infra) vivem na Tech Spec de cada tarefa.

---

## Out of Scope

- **Calibração fina do Delivery Score** — motivo: exige histórico real e ciclo de tuning; em 3 dias se prova a hipótese, não a precisão do número.
- **Transcrição de áudio ao vivo / em tempo real** — motivo: a entrada são transcrições já em texto; gravação e speech-to-text ao vivo ficam para fase 2.
- **Integração real com ClickUp / Linear / Discord** — motivo: a demo usa dados sintéticos (baseados em datasets públicos quando disponíveis); conectores reais consomem setup que não cabe na janela de 3 dias.
- **Sugestão de intervenção baseada em aprendizado de padrões históricos** — motivo: não existe histórico no MVP; a sugestão de ação usa regras fixas simples no lugar.
- **Visão de portfólio multi-projeto / ranking de squads** — motivo: a demo é sobre um único projeto que derrapa; agregação e comparação ficam para depois.
- **Autenticação, contas de usuário e permissões** — motivo: irrelevante para um MVP de demonstração.
- **Ingestão automática / polling de fontes** — motivo: o processamento é acionado sob demanda com os artefatos fornecidos manualmente.

---

## Ready to Plan?

- [x] Problem has a concrete, observable user pain (not a feature wishlist)
- [x] At least one specific persona identified
- [x] Success metric is measurable and anchored
- [x] User stories cover happy path + at least one failure case
- [x] Acceptance criteria are observable (no internal implementation references)
- [x] Out-of-scope is explicit
- [x] No stack, schema, or technical decisions included
