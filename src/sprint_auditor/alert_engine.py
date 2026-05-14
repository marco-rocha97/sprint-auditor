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
from sprint_auditor.template_fases import fase_do_dia, progresso_esperado

LIMIAR_DESVIO: int = 70

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
    progresso_esp = progresso_esperado(fase, update.dia_projeto)

    gap_pp = float(progresso_esp * (1 - update.score.valor / 100))

    real_percentual = int(update.score.valor * progresso_esp / 100)

    causa_provavel = (
        f"Score {update.score.valor} está abaixo do limiar {LIMIAR_DESVIO} — "
        f"progresso real estimado em {real_percentual}% contra {progresso_esp}% esperado "
        f"para a fase {fase.value} no dia {update.dia_projeto}"
    )

    acao_sugerida = (
        f"Investigar bloqueios na fase {fase.value} e considerar "
        f"escalonamento para o FDE Lead"
    )

    return Alerta(
        categoria=CategoriaAlerta.DESVIO_LIMIAR,
        fase=fase,
        dia_projeto=update.dia_projeto,
        gap_pp=gap_pp,
        causa_provavel=causa_provavel,
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

                return Alerta(
                    categoria=CategoriaAlerta.BLOQUEIO_LINGUISTICO,
                    fase=fase,
                    dia_projeto=update.dia_projeto,
                    gap_pp=None,
                    causa_provavel=causa_provavel,
                    nivel_confianca=NivelConfianca.MEDIO,
                    acao_sugerida="Bloqueio externo identificado → escalar para o FDE Lead",
                    artefato_fonte_id=artefato.id,
                    trecho_fonte=trecho_casado,
                )

    return None


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
    alertas = []

    pode_usar_score = update_atual.score is not None and update_atual.score.dados_suficientes

    if pode_usar_score:
        alerta_desvio = _detectar_desvio_limiar(update_atual)
        if alerta_desvio:
            alertas.append(alerta_desvio)

        alerta_deterioracao = _detectar_deterioracao_consistente(update_atual, updates_anteriores)
        if alerta_deterioracao:
            alertas.append(alerta_deterioracao)

    alerta_bloqueio = _detectar_bloqueio_linguistico(update_atual)
    if alerta_bloqueio:
        alertas.append(alerta_bloqueio)

    return alertas
