from sprint_auditor.modelos import (
    Alerta,
    CategoriaAlerta,
    DeliveryScore,
    NivelConfianca,
    Projeto,
    Update,
)

_LARGURA_BARRA: int = 10
_LARGURA_LINHA: int = 44

_ORDEM_CATEGORIA: dict[CategoriaAlerta, int] = {
    CategoriaAlerta.DESVIO_LIMIAR: 0,
    CategoriaAlerta.DETERIORACAO_CONSISTENTE: 1,
    CategoriaAlerta.BLOQUEIO_LINGUISTICO: 2,
}

_LABEL_CONFIANCA: dict[NivelConfianca, str] = {
    NivelConfianca.ALTO: "ALTA",
    NivelConfianca.MEDIO: "MÉDIA",
    NivelConfianca.BAIXO: "BAIXA",
}

_LABEL_CATEGORIA: dict[CategoriaAlerta, str] = {
    CategoriaAlerta.DESVIO_LIMIAR: "[DESVIO]",
    CategoriaAlerta.DETERIORACAO_CONSISTENTE: "[PIORA]",
    CategoriaAlerta.BLOQUEIO_LINGUISTICO: "[BLOQUEIO]",
}


def _formatar_barra(valor: int, largura: int = _LARGURA_BARRA) -> str:
    """Gera barra de progresso ASCII: ████████░░ para valor=80, largura=10.

    valor: inteiro 0–100. Valores fora do intervalo são truncados (max/min).
    Retorna string de exatamente `largura` caracteres.
    """
    valor_truncado = max(0, min(100, valor))
    preenchido = round(valor_truncado * largura / 100)
    return "█" * preenchido + "░" * (largura - preenchido)


def _ordenar_alertas(alertas: list[Alerta]) -> list[Alerta]:
    """Retorna alertas ordenados por gravidade decrescente: DESVIO_LIMIAR > DETERIORACAO > BLOQUEIO.

    Não modifica a lista original.
    """
    return sorted(alertas, key=lambda a: _ORDEM_CATEGORIA[a.categoria])


def _indicador_status(alertas: list[Alerta]) -> str:
    """Retorna rótulo textual do alerta mais grave, ou string vazia se não há alertas.

    Exemplos: '  [DESVIO]', '  [PIORA]', '  [BLOQUEIO]', ''
    Garante que o status nunca depende apenas de cor (acessibilidade SPEC).
    """
    if not alertas:
        return ""

    alerta_mais_grave = _ordenar_alertas(alertas)[0]
    return "  " + _LABEL_CATEGORIA[alerta_mais_grave.categoria]


def _linha_score(score: DeliveryScore | None) -> str:
    """Formata a linha de Delivery Score.

    score=None ou dados_suficientes=False → 'Delivery Score: sem dados suficientes'
    dados_suficientes=True → 'Delivery Score: ████████░░  83/100'
    """
    if score is None or not score.dados_suficientes:
        return "Delivery Score: sem dados suficientes"

    barra = _formatar_barra(score.valor)
    return f"Delivery Score: {barra}  {score.valor}/100"


def _formatar_trecho(trecho: str, limite: int = 100) -> str:
    """Normaliza o trecho para exibição em linha única.

    Substitui quebras de linha por ' / ' e trunca em `limite` caracteres com '...'.
    Não modifica o campo original em Alerta.
    """
    normalizado = trecho.replace("\n", " / ")

    if len(normalizado) > limite:
        return normalizado[:limite] + "..."

    return normalizado


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
    categoria_label = alerta.categoria.value.upper()
    confianca_label = _LABEL_CONFIANCA[alerta.nivel_confianca]

    linhas = [
        f"⚠ {categoria_label} (confiança: {confianca_label})",
    ]

    if alerta.gap_pp is not None:
        linhas.append(
            f"  Fase: {alerta.fase.value} | Dia: {alerta.dia_projeto} | Gap: {alerta.gap_pp} pp"
        )
    else:
        linhas.append(f"  Fase: {alerta.fase.value} | Dia: {alerta.dia_projeto}")

    linhas.append(f"  Causa: {alerta.causa_provavel}")
    linhas.append(f"  Ação: {alerta.acao_sugerida}")

    trecho_formatado = _formatar_trecho(alerta.trecho_fonte)
    linhas.append(f'  Fonte: {alerta.artefato_fonte_id} | "{trecho_formatado}"')

    return "\n".join(linhas)


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
    linhas = []

    titulo = f"─── Update #{update.numero} — Dia {update.dia_projeto} "
    comprimento_titulo = len(titulo)
    travessoes = "─" * (_LARGURA_LINHA - comprimento_titulo)
    linhas.append(titulo + travessoes)

    linha_score_str = _linha_score(update.score)
    indicador = _indicador_status(update.alertas)
    linhas.append(linha_score_str + indicador)

    alertas_ordenados = _ordenar_alertas(update.alertas)
    for alerta in alertas_ordenados:
        linhas.append("")
        linhas.append(_formatar_alerta(alerta))

    if not update.alertas and update.score and update.score.dados_suficientes:
        linhas.append("")
        linhas.append("Projeto no trilho — nenhum desvio detectado.")

    artefatos_invalidos = [a for a in update.artefatos if not a.valido]
    for artefato in artefatos_invalidos:
        linhas.append("")
        linhas.append(f"✗ Ingestão: artefato {artefato.id} falhou — {artefato.erro_ingestao}")

    return "\n".join(linhas)


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
    linhas = ["Histórico de Delivery Score:"]

    for update in updates:
        dia_str = f"{update.dia_projeto:2d}"

        if update.score is None or not update.score.dados_suficientes:
            linha = f"  Update #{update.numero} (Dia {dia_str}): sem dados suficientes"
        else:
            barra = _formatar_barra(update.score.valor)
            valor_str = f"{update.score.valor:3d}"
            linha = f"  Update #{update.numero} (Dia {dia_str}): {barra}  {valor_str}/100"

            if update.alertas:
                linha += "  ⚠"

        linhas.append(linha)

    return "\n".join(linhas)


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
    linhas = []

    linhas.append("=" * _LARGURA_LINHA)
    linhas.append(f"SPRINT AUDITOR — {projeto.nome}")
    linhas.append(f"Kickoff: {projeto.data_kickoff.date()}")
    linhas.append("=" * _LARGURA_LINHA)

    if not projeto.updates:
        linhas.append("")
        linhas.append("Sem dados suficientes para um Delivery Score confiável.")
        linhas.append("Nenhum update foi processado.")
        linhas.append("=" * _LARGURA_LINHA)
        return "\n".join(linhas)

    updates_ordenados = sorted(projeto.updates, key=lambda u: u.numero)

    for update in updates_ordenados:
        linhas.append("")
        linhas.append(_formatar_update(update))

    linhas.append("")
    linhas.append("─" * _LARGURA_LINHA)
    linhas.append(_formatar_historico(updates_ordenados))
    linhas.append("=" * _LARGURA_LINHA)

    return "\n".join(linhas)
