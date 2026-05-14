from sprint_auditor.alert_engine import analisar_alertas
from sprint_auditor.ingestao import ingerir_artefatos
from sprint_auditor.modelos import Projeto, Update
from sprint_auditor.relatorio import gerar_relatorio
from sprint_auditor.score_engine import calcular_delivery_score
from sprint_auditor.seed import carregar_projeto_seed

_LARGURA_LINHA: int = 44
_DIA_COMITE_SEMANA_2: int = 12


def _processar_update(update: Update, anteriores: list[Update]) -> Update:
    """Executa o pipeline T02→T03→T04 sobre um único update e retorna update processado.

    Pipeline:
        1. Ingere os artefatos do update (T02)
        2. Calcula o Delivery Score a partir do resultado da ingestão e do dia do update (T03)
        3. Detecta alertas com o update-com-score e contexto dos updates anteriores (T04)

    Retorna novo Update (via model_copy) com score e alertas preenchidos.
    Não muta o update de entrada nem a lista de anteriores.
    Nunca levanta exceção.
    """
    resultado_ingestao = ingerir_artefatos(update.artefatos)
    score = calcular_delivery_score(resultado_ingestao, update.dia_projeto)
    update_com_score = update.model_copy(update={"score": score})
    alertas = analisar_alertas(update_com_score, anteriores)
    return update_com_score.model_copy(update={"alertas": alertas})


def _gerar_contraste(projeto: Projeto) -> str:
    """Gera a seção de contraste: alerta vs. comitê semanal.

    Varre os updates do projeto em ordem crescente de numero para encontrar
    o primeiro com alertas. Calcula antecipação = _DIA_COMITE_SEMANA_2 -
    dia_primeiro_alerta. Se nenhum update tiver alertas, retorna seção
    indicando ausência de desvio detectado.

    Formato (caso com alerta):
        ════════════════════════════════════════════
        RESUMO DA DEMO
        ════════════════════════════════════════════
        ✓ Alerta disparado: Dia 6 — semana 1, antes do comitê
        ✗ Comitê semanal detectaria: Dia 12 — semana 2, tarde demais
          Antecipação: 6 dias

        "isso é exatamente o que a gente precisa olhar
          na sexta da semana 1"
        ════════════════════════════════════════════

    Retorna string sem trailing newline. Nunca levanta exceção.
    """
    updates_ordenados = sorted(projeto.updates, key=lambda u: u.numero)

    primeiro_alerta_dia = None
    for update in updates_ordenados:
        if update.alertas:
            primeiro_alerta_dia = update.dia_projeto
            break

    linhas = []
    linhas.append("═" * _LARGURA_LINHA)
    linhas.append("RESUMO DA DEMO")
    linhas.append("═" * _LARGURA_LINHA)

    if primeiro_alerta_dia is None:
        linhas.append("Sem desvio detectado em nenhum update.")
    else:
        antecipacao = _DIA_COMITE_SEMANA_2 - primeiro_alerta_dia
        msg1 = f"✓ Alerta disparado: Dia {primeiro_alerta_dia} — semana 1"
        linhas.append(msg1 + ", antes do comitê")
        msg2 = f"✗ Comitê semanal detectaria: Dia {_DIA_COMITE_SEMANA_2}"
        linhas.append(msg2 + " — semana 2, tarde demais")
        linhas.append(f"  Antecipação: {antecipacao} dias")
        linhas.append("")
        linhas.append('"isso é exatamente o que a gente precisa olhar')
        linhas.append('  na sexta da semana 1"')

    linhas.append("═" * _LARGURA_LINHA)

    return "\n".join(linhas)


def executar_demo() -> str:
    """Executa o pipeline de demo end-to-end e retorna o output completo como string.

    Fluxo:
        1. Carrega o projeto sintético via carregar_projeto_seed()
        2. Ordena os updates por numero (crescente)
        3. Para cada update, chama _processar_update(update, atualizados_anteriores)
           e acumula o resultado em atualizados_anteriores
        4. Monta Projeto com updates processados via model_copy
        5. Gera relatório completo via gerar_relatorio()
        6. Gera seção de contraste via _gerar_contraste()
        7. Retorna relatório + '\n\n' + contraste

    Returns:
        String com relatório completo seguido de seção de contraste.
        Adequado para print() direto.
        Nunca levanta exceção.
    """
    projeto_original = carregar_projeto_seed()

    updates_ordenados = sorted(projeto_original.updates, key=lambda u: u.numero)
    atualizados_anteriores: list[Update] = []

    for update in updates_ordenados:
        atualizado = _processar_update(update, atualizados_anteriores)
        atualizados_anteriores.append(atualizado)

    projeto_processado = projeto_original.model_copy(update={"updates": atualizados_anteriores})

    relatorio: str = gerar_relatorio(projeto_processado)
    contraste: str = _gerar_contraste(projeto_processado)

    return relatorio + "\n\n" + contraste


def main() -> None:
    """CLI entry point — registrado em pyproject.toml como sprint-auditor-demo.

    Chama executar_demo() e imprime o resultado em stdout via print().
    Sem argumentos de linha de comando, sem configuração manual entre updates.
    """
    print(executar_demo())
