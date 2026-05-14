import re

from sprint_auditor.modelos import (
    Artefato,
    DeliveryScore,
    Fase,
    ResultadoIngestao,
    TipoArtefato,
)
from sprint_auditor.template_fases import fase_do_dia, progresso_esperado


def _extrair_progresso_board(artefatos: list[Artefato]) -> int:
    """Extrai progresso real (0–100) a partir de marcadores nos artefatos de board.

    Pesos: [✓]=1.0, [~]=0.5, [✗]=0.0
    Fórmula: int(soma_pesos / total_itens * 100)

    Retorna 0 se nenhum artefato de board presente ou se nenhum marcador encontrado.
    Nunca levanta exceção.

    Args:
        artefatos: Lista de artefatos a processar

    Returns:
        Progresso extraído como int de 0–100
    """
    artefatos_board = [a for a in artefatos if a.tipo == TipoArtefato.BOARD]

    if not artefatos_board:
        return 0

    soma_pesos = 0.0
    total_itens = 0

    padrao = r"(\[✓\]|\[~\]|\[✗\])"

    for artefato in artefatos_board:
        marcadores = re.findall(padrao, artefato.conteudo)

        for marcador in marcadores:
            total_itens += 1
            if marcador == "[✓]":
                soma_pesos += 1.0
            elif marcador == "[~]":
                soma_pesos += 0.5

    if total_itens == 0:
        return 0

    return int(soma_pesos / total_itens * 100)


def calcular_score(progresso_real: int, fase: Fase, dia: int) -> DeliveryScore:
    """Calcula DeliveryScore a partir do progresso real e do esperado pelo template.

    Fórmula: max(0, min(100, int(progresso_real * 100 / progresso_esperado)))

    Args:
        progresso_real: percentual real extraído dos artefatos (0–100)
        fase: fase ativa do projeto
        dia: dia do projeto (1–15)

    Returns:
        DeliveryScore com dados_suficientes=True, valor calculado,
        scores_por_fase={fase: valor}

    Raises:
        KeyError: se (fase, dia) não é uma combinação válida do template
    """
    esperado = progresso_esperado(fase, dia)

    if esperado == 0:
        valor = 0
    else:
        valor = max(0, min(100, int(progresso_real * 100 / esperado)))

    return DeliveryScore(
        dados_suficientes=True,
        valor=valor,
        scores_por_fase={fase: valor},
    )


def calcular_delivery_score(
    resultado_ingestao: ResultadoIngestao,
    dia: int,
) -> DeliveryScore:
    """Ponto de entrada do pipeline — produz o DeliveryScore de um update.

    Se não há artefatos válidos → DeliveryScore(dados_suficientes=False).
    Caso contrário: extrai progresso do board, calcula score via fórmula linear.

    Args:
        resultado_ingestao: saída de ingerir_artefatos (T02)
        dia: dia do projeto do update sendo avaliado (1–15)

    Returns:
        DeliveryScore preenchido ou com dados_suficientes=False
    """
    if not resultado_ingestao.tem_artefatos:
        return DeliveryScore(dados_suficientes=False, valor=None)

    fase = fase_do_dia(dia)
    progresso_real = _extrair_progresso_board(resultado_ingestao.artefatos_validos)

    return calcular_score(progresso_real, fase, dia)
