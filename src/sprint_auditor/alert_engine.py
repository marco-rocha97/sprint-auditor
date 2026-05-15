import re
from typing import Optional

from sprint_auditor.modelos import (
    Alerta,
    Artefato,
    CategoriaAlerta,
    NivelConfianca,
    TipoArtefato,
    Update,
)
from sprint_auditor.template_fases import fase_do_dia

LIMIAR_DESVIO: int = 70
LIMIAR_SILENCIO: int = 4

TEMPLATE_HIPOTESE: str = (
    "Fase {fase} travada em {progresso_real}% no dia {dia}. "
    "Hipótese: dependência externa — sinalizado na transcrição "
    "('{trecho_bloqueio}'). "
    "Escalar para o FDE Lead pedir intervenção do sponsor do cliente."
)

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

PADROES_BLOQUEIO: list[str] = [
    r"aguardando\s+\w+",
    r"não\s+temos\s+acesso",
    r"bloqueado",
    r"falhas?\s+de\s+conectividade",
    r"sem\s+acesso",
    r"não\s+pode\s+avançar",
    r"segurando\s+tudo",
]


def _obter_artefato_fonte(
    update: Update,
    tipo_preferido: TipoArtefato = TipoArtefato.BOARD,
) -> Optional[Artefato]:
    """Retorna o primeiro artefato válido do tipo preferido, com fallback para qualquer válido.

    Args:
        update: Update contendo artefatos
        tipo_preferido: TipoArtefato a buscar primeiro (default BOARD)

    Returns:
        Primeiro artefato válido do tipo preferido, ou primeiro válido de qualquer tipo, ou None
    """
    artefatos_validos = [a for a in update.artefatos if a.valido]

    preferidos = [a for a in artefatos_validos if a.tipo == tipo_preferido]
    if preferidos:
        return preferidos[0]

    if artefatos_validos:
        return artefatos_validos[0]

    return None


def _detectar_desvio_limiar(update: Update) -> Optional[Alerta]:
    """Retorna Alerta se o score do update estiver abaixo de LIMIAR_DESVIO.

    Precondição: update.score deve estar preenchido (T03 rodou antes).
    Retorna None se score é None, dados_suficientes=False ou valor >= LIMIAR_DESVIO.
    Nunca levanta exceção.
    """
    if update.score is None or not update.score.dados_suficientes:
        return None

    if update.score.valor is None or update.score.valor >= LIMIAR_DESVIO:
        return None

    artefato_fonte = _obter_artefato_fonte(update)
    if artefato_fonte is None:
        return None

    fase = fase_do_dia(update.dia_projeto)

    if update.score.progresso_esperado is not None and update.score.progresso_real is not None:
        gap_pp = float(max(0, update.score.progresso_esperado - update.score.progresso_real))
    else:
        gap_pp = 0.0

    causa_provavel = (
        f"Score {update.score.valor} está abaixo do limiar {LIMIAR_DESVIO} — "
        f"progresso real {update.score.progresso_real}% contra "
        f"{update.score.progresso_esperado}% esperado para a fase {fase.value} no dia "
        f"{update.dia_projeto}"
    )

    acao_sugerida = (
        f"Investigar bloqueios na fase {fase.value} e considerar "
        f"escalonamento para o FDE Lead"
    )

    hipotese = TEMPLATE_HIPOTESE_DESVIO_SIMPLES.format(
        fase=fase.value,
        progresso_real=update.score.progresso_real,
        progresso_esperado=update.score.progresso_esperado,
        dia=update.dia_projeto,
    )

    return Alerta(
        categoria=CategoriaAlerta.DESVIO_LIMIAR,
        fase=fase,
        dia_projeto=update.dia_projeto,
        gap_pp=gap_pp,
        causa_provavel=causa_provavel,
        hipotese_causal=hipotese,
        nivel_confianca=NivelConfianca.ALTO,
        acao_sugerida=acao_sugerida,
        artefato_fonte_id=artefato_fonte.id,
        trecho_fonte=artefato_fonte.conteudo,
    )


def _detectar_deterioracao_consistente(
    update_atual: Update,
    updates_anteriores: list[Update],
) -> Optional[Alerta]:
    """Retorna Alerta se o score caiu em 2 updates consecutivos sem nenhum cruzar LIMIAR_DESVIO.

    Requer pelo menos 2 updates anteriores com dados_suficientes=True.
    Retorna None se a condição não for satisfeita.
    Nunca levanta exceção.
    """
    updates_com_score = [
        u for u in updates_anteriores
        if u.score is not None and u.score.dados_suficientes
    ]

    if len(updates_com_score) < 2:
        return None

    penultimo = updates_com_score[-2]
    anterior = updates_com_score[-1]

    if penultimo.score is None or penultimo.score.valor is None:
        return None
    if anterior.score is None or anterior.score.valor is None:
        return None
    if update_atual.score is None or update_atual.score.valor is None:
        return None

    s_penultimo = penultimo.score.valor
    s_anterior = anterior.score.valor
    s_atual = update_atual.score.valor

    primeira_queda = s_anterior < s_penultimo
    segunda_queda = s_atual < s_anterior

    if not (primeira_queda and segunda_queda):
        return None

    nenhum_cruza_limiar = (
        s_penultimo >= LIMIAR_DESVIO and
        s_anterior >= LIMIAR_DESVIO and
        s_atual >= LIMIAR_DESVIO
    )

    if not nenhum_cruza_limiar:
        return None

    artefato_fonte = _obter_artefato_fonte(update_atual)
    if artefato_fonte is None:
        return None

    fase = fase_do_dia(update_atual.dia_projeto)

    causa_provavel = (
        f"Score caiu por 2 updates consecutivos: {s_penultimo} → {s_anterior} → {s_atual} "
        f"sem cruzar o limiar {LIMIAR_DESVIO}"
    )

    return Alerta(
        categoria=CategoriaAlerta.DETERIORACAO_CONSISTENTE,
        fase=fase,
        dia_projeto=update_atual.dia_projeto,
        gap_pp=None,
        causa_provavel=causa_provavel,
        nivel_confianca=NivelConfianca.MEDIO,
        acao_sugerida="Monitorar próximo update; se a tendência continuar, escalar para o FDE Lead",
        artefato_fonte_id=artefato_fonte.id,
        trecho_fonte=artefato_fonte.conteudo,
    )


def _detectar_bloqueio_linguistico(update: Update) -> Optional[Alerta]:
    """Retorna Alerta se algum padrão de PADROES_BLOQUEIO casar em artefatos de transcrição.

    Itera PADROES_BLOQUEIO em ordem para cada artefato de transcrição válido.
    Retorna o primeiro alerta gerado pelo primeiro padrão que casar.
    Retorna None se nenhum padrão casar.
    Nunca levanta exceção.
    """
    artefatos_transcricao = [
        a for a in update.artefatos
        if a.tipo == TipoArtefato.TRANSCRICAO and a.valido
    ]

    if not artefatos_transcricao:
        return None

    for artefato in artefatos_transcricao:
        for padrao in PADROES_BLOQUEIO:
            match = re.search(padrao, artefato.conteudo, re.IGNORECASE)
            if match:
                fase = fase_do_dia(update.dia_projeto)
                trecho_casado = match.group()

                causa_provavel = f"Sinal de bloqueio identificado na transcrição: '{trecho_casado}'"

                hipotese = TEMPLATE_HIPOTESE_BLOQUEIO_SIMPLES.format(
                    trecho_bloqueio=trecho_casado
                )

                return Alerta(
                    categoria=CategoriaAlerta.BLOQUEIO_LINGUISTICO,
                    fase=fase,
                    dia_projeto=update.dia_projeto,
                    gap_pp=None,
                    causa_provavel=causa_provavel,
                    hipotese_causal=hipotese,
                    nivel_confianca=NivelConfianca.MEDIO,
                    acao_sugerida="Bloqueio externo identificado → escalar para o FDE Lead",
                    artefato_fonte_id=artefato.id,
                    trecho_fonte=trecho_casado,
                )

    return None


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
    if not updates_anteriores:
        return None

    ultimo_update = updates_anteriores[-1]
    gap = update_atual.dia_projeto - ultimo_update.dia_projeto

    if gap <= LIMIAR_SILENCIO:
        return None

    fase = fase_do_dia(update_atual.dia_projeto)

    trecho_fonte = f"Sem update há {gap} dias (último: dia {ultimo_update.dia_projeto})"

    causa_provavel = (
        f"Squad sem sinal há {gap} dias — último update foi no dia {ultimo_update.dia_projeto}"
    )

    acao_sugerida = (
        f"Contatar FDE Lead para status — squad sem sinal há {gap} dias"
    )

    return Alerta(
        categoria=CategoriaAlerta.SILENCIO,
        fase=fase,
        dia_projeto=update_atual.dia_projeto,
        gap_pp=None,
        causa_provavel=causa_provavel,
        hipotese_causal=None,
        nivel_confianca=NivelConfianca.MEDIO,
        acao_sugerida=acao_sugerida,
        artefato_fonte_id="sistema",
        trecho_fonte=trecho_fonte,
    )


def analisar_alertas(
    update_atual: Update,
    updates_anteriores: list[Update],
) -> list[Alerta]:
    """Ponto de entrada — executa detectores, funde alertas e retorna lista final.

    Regras adicionadas em T07:
    - _detectar_silencio é chamado sempre (retorna None se não há anteriores)
    - Fusão: se DESVIO_LIMIAR e BLOQUEIO_LINGUISTICO disparam no mesmo update,
      produz 1 alerta DESVIO_LIMIAR com hipotese_causal preenchida via TEMPLATE_HIPOTESE;
      BLOQUEIO_LINGUISTICO NÃO é incluído separadamente na lista retornada.
    - SILENCIO é sempre listado separadamente (não sofre fusão).

    Ordem de saída: [DESVIO_LIMIAR_fusionado_ou_normal, DETERIORACAO, BLOQUEIO_standalone, SILENCIO]
    Lista vazia = projeto no trilho neste update.

    Args:
        update_atual: update com score já preenchido por T03
        updates_anteriores: updates anteriores do mesmo projeto, em ordem crescente de numero

    Returns:
        Lista de alertas com fusão aplicada quando necessário
    """
    alertas = []

    pode_usar_score = update_atual.score is not None and update_atual.score.dados_suficientes

    alerta_desvio = None
    alerta_bloqueio = None

    if pode_usar_score:
        alerta_desvio = _detectar_desvio_limiar(update_atual)

        alerta_deterioracao = _detectar_deterioracao_consistente(update_atual, updates_anteriores)
        if alerta_deterioracao:
            alertas.append(alerta_deterioracao)

    alerta_bloqueio = _detectar_bloqueio_linguistico(update_atual)

    if alerta_desvio and alerta_bloqueio:
        hipotese = TEMPLATE_HIPOTESE.format(
            fase=alerta_desvio.fase.value,
            progresso_real=update_atual.score.progresso_real,
            dia=update_atual.dia_projeto,
            trecho_bloqueio=alerta_bloqueio.trecho_fonte,
        )
        acao_sugerida_fusao = (
            "Bloqueio externo confirmado por sinal linguístico → escalar para "
            "o FDE Lead"
        )
        alerta_desvio_fusionado = alerta_desvio.model_copy(
            update={
                "hipotese_causal": hipotese,
                "acao_sugerida": acao_sugerida_fusao,
                "nivel_confianca": NivelConfianca.ALTO,
            }
        )
        alertas.insert(0, alerta_desvio_fusionado)
    else:
        if alerta_desvio:
            alertas.insert(0, alerta_desvio)
        if alerta_bloqueio:
            alertas.append(alerta_bloqueio)

    alerta_silencio = _detectar_silencio(update_atual, updates_anteriores)
    if alerta_silencio:
        alertas.append(alerta_silencio)

    return alertas
