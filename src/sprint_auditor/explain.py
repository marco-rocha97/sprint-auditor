import sys

from sprint_auditor.demo_pipeline import _processar_update
from sprint_auditor.modelos import Update
from sprint_auditor.seed import carregar_projeto_seed

_LARGURA_LINHA: int = 44


def decompor_score(update: Update) -> str:
    """Formata a decomposição do score de um update como texto puro.

    Requer update.score not None.
    Exibe: número, dia, fase, progresso_esperado, progresso_real, gap, score,
    limiar, status, alertas.

    Args:
        update: update com score preenchido (T03 executou)

    Returns:
        String multiline sem trailing newline.
        Retorna mensagem de erro se update.score is None ou
        dados_suficientes=False.
    """
    if update.score is None or not update.score.dados_suficientes:
        return (
            f"Erro: Update #{update.numero} não tem score suficiente para decompor. "
            f"Dados: {update.score}"
        )

    fase = update.score.scores_por_fase
    fase_nome = list(fase.keys())[0].value if fase else "desconhecida"

    gap_pp = max(0, update.score.progresso_esperado - update.score.progresso_real)
    limiar_desvio = 70

    if update.score.valor < limiar_desvio:
        status = "⚠ ABAIXO DO LIMIAR"
    elif update.alertas:
        status = "⚡ EM ALERTA"
    else:
        status = "✓ NO TRILHO"

    num_alertas = len(update.alertas)

    linhas = [
        "═" * _LARGURA_LINHA,
        f"Decomposição do Score — Update #{update.numero} (Dia {update.dia_projeto})",
        "═" * _LARGURA_LINHA,
        f"  Fase:               {fase_nome}",
        f"  Progresso esperado: {update.score.progresso_esperado}%",
        f"  Progresso real:      {update.score.progresso_real}%",
        f"  Gap:                 {int(gap_pp)} pp",
        f"  Score (100 - gap):   {update.score.valor}/100",
        f"  Limiar de desvio:    {limiar_desvio}",
        f"  Status:              {status}",
        f"  Alertas gerados:     {num_alertas}",
        "═" * _LARGURA_LINHA,
    ]

    return "\n".join(linhas)


def main_explain() -> None:
    """CLI entry point — registrado em pyproject.toml como sprint-auditor-explain.

    Uso: sprint-auditor-explain --update N.
    Carrega seed, executa pipeline completo, exibe decomposição do update N.
    Imprime erro e sai se N não existe.
    """
    if len(sys.argv) < 3 or sys.argv[1] != "--update":
        print("Uso: sprint-auditor-explain --update N")
        sys.exit(1)

    try:
        numero_update = int(sys.argv[2])
    except ValueError:
        print(f"Erro: {sys.argv[2]} não é um número válido")
        sys.exit(1)

    projeto = carregar_projeto_seed()
    updates_ordenados = sorted(projeto.updates, key=lambda u: u.numero)
    atualizados_anteriores: list[Update] = []

    for update in updates_ordenados:
        atualizado = _processar_update(update, atualizados_anteriores)
        atualizados_anteriores.append(atualizado)

    update_encontrado = None
    for update in atualizados_anteriores:
        if update.numero == numero_update:
            update_encontrado = update
            break

    if update_encontrado is None:
        print(f"Erro: Update #{numero_update} não encontrado no projeto.")
        sys.exit(1)

    print(decompor_score(update_encontrado))
