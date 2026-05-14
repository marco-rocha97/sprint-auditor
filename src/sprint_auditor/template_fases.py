from src.sprint_auditor.modelos import Fase


TEMPLATE_PROGRESSO = {
    (Fase.DISCOVERY, 1): 30,
    (Fase.DISCOVERY, 2): 70,
    (Fase.DISCOVERY, 3): 100,
    (Fase.CONFIGURACAO, 4): 10,
    (Fase.CONFIGURACAO, 5): 30,
    (Fase.CONFIGURACAO, 6): 60,
    (Fase.CONFIGURACAO, 7): 100,
    (Fase.DESENVOLVIMENTO, 8): 10,
    (Fase.DESENVOLVIMENTO, 9): 25,
    (Fase.DESENVOLVIMENTO, 10): 50,
    (Fase.DESENVOLVIMENTO, 11): 75,
    (Fase.DESENVOLVIMENTO, 12): 100,
    (Fase.REVIEW, 13): 30,
    (Fase.REVIEW, 14): 70,
    (Fase.REVIEW, 15): 100,
}

FASES_POR_DIA = {
    1: Fase.DISCOVERY,
    2: Fase.DISCOVERY,
    3: Fase.DISCOVERY,
    4: Fase.CONFIGURACAO,
    5: Fase.CONFIGURACAO,
    6: Fase.CONFIGURACAO,
    7: Fase.CONFIGURACAO,
    8: Fase.DESENVOLVIMENTO,
    9: Fase.DESENVOLVIMENTO,
    10: Fase.DESENVOLVIMENTO,
    11: Fase.DESENVOLVIMENTO,
    12: Fase.DESENVOLVIMENTO,
    13: Fase.REVIEW,
    14: Fase.REVIEW,
    15: Fase.REVIEW,
}


def progresso_esperado(fase: Fase, dia: int) -> int:
    """Retorna o progresso esperado (0–100%) para a fase no dia dado.

    Args:
        fase: A fase do projeto
        dia: O dia do projeto (1–15)

    Returns:
        Progresso esperado em percentual (0–100)

    Raises:
        KeyError: se (fase, dia) não for uma combinação válida do template
    """
    return TEMPLATE_PROGRESSO[(fase, dia)]


def fase_do_dia(dia: int) -> Fase:
    """Retorna a fase ativa esperada para o dia de projeto (1–15).

    Args:
        dia: O dia do projeto

    Returns:
        A fase ativa no dia especificado

    Raises:
        ValueError: se dia < 1 ou dia > 15
    """
    if dia < 1 or dia > 15:
        raise ValueError(f"dia deve estar entre 1 e 15, recebido: {dia}")
    return FASES_POR_DIA[dia]
