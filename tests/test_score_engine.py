from sprint_auditor.modelos import (
    Artefato,
    Fase,
    ResultadoIngestao,
    TipoArtefato,
)
from sprint_auditor.score_engine import (
    _extrair_progresso_board,
    calcular_delivery_score,
    calcular_score,
)
from sprint_auditor.seed import carregar_projeto_seed


class TestCalcularDeliveryScore:
    def test_happy_path_board_com_marcadores(self):
        artefato_board = Artefato(
            id="board-001",
            tipo=TipoArtefato.BOARD,
            conteudo="[✓] Task A, [✗] Task B, [~] Task C",
            dia_projeto=3,
        )
        resultado_ingestao = ResultadoIngestao(
            artefatos_validos=[artefato_board],
            artefatos_invalidos=[],
        )

        score = calcular_delivery_score(resultado_ingestao, dia=3)

        assert score.dados_suficientes is True
        assert score.valor == 50
        assert Fase.DISCOVERY in score.scores_por_fase
        assert score.scores_por_fase[Fase.DISCOVERY] == 50

    def test_sem_artefatos_validos(self):
        resultado_ingestao = ResultadoIngestao(
            artefatos_validos=[],
            artefatos_invalidos=[],
        )

        score = calcular_delivery_score(resultado_ingestao, dia=3)

        assert score.dados_suficientes is False
        assert score.valor is None

    def test_somente_transcricao_sem_board(self):
        artefato_transcricao = Artefato(
            id="trans-001",
            tipo=TipoArtefato.TRANSCRICAO,
            conteudo="conteúdo da transcrição",
            dia_projeto=6,
        )
        resultado_ingestao = ResultadoIngestao(
            artefatos_validos=[artefato_transcricao],
            artefatos_invalidos=[],
        )

        score = calcular_delivery_score(resultado_ingestao, dia=6)

        assert score.dados_suficientes is True
        assert score.valor is not None
        expected_score = calcular_score(0, Fase.CONFIGURACAO, 6)
        assert score.valor == expected_score.valor


class TestCalcularScore:
    def test_criterio_spec_dia6_configuracao(self):
        score = calcular_score(38, Fase.CONFIGURACAO, 6)

        assert score.valor == 78
        assert score.dados_suficientes is True
        assert score.scores_por_fase == {Fase.CONFIGURACAO: 78}

    def test_progresso_real_igual_esperado(self):
        score = calcular_score(60, Fase.CONFIGURACAO, 6)

        assert score.valor == 100
        assert score.dados_suficientes is True

    def test_progresso_real_zero(self):
        score = calcular_score(0, Fase.CONFIGURACAO, 6)

        assert score.valor == 40
        assert score.dados_suficientes is True

    def test_progresso_real_acima_esperado_capped(self):
        score = calcular_score(80, Fase.CONFIGURACAO, 6)

        assert score.valor == 100
        assert score.dados_suficientes is True

    def test_scores_por_fase_reflete_fase_ativa(self):
        score = calcular_score(38, Fase.CONFIGURACAO, 6)

        assert len(score.scores_por_fase) == 1
        assert Fase.CONFIGURACAO in score.scores_por_fase
        assert Fase.DISCOVERY not in score.scores_por_fase
        assert Fase.DESENVOLVIMENTO not in score.scores_por_fase
        assert Fase.REVIEW not in score.scores_por_fase

    def test_gradiente_real_zero_esperado_vinte_cinco(self):
        score = calcular_score(0, Fase.DESENVOLVIMENTO, 9)

        assert score.valor == 75
        assert score.dados_suficientes is True

    def test_gradiente_real_cinquenta_esperado_cem(self):
        score = calcular_score(50, Fase.DESENVOLVIMENTO, 12)

        assert score.valor == 50
        assert score.dados_suficientes is True

    def test_progresso_real_armazenado(self):
        score = calcular_score(38, Fase.CONFIGURACAO, 6)

        assert score.progresso_real == 38

    def test_progresso_esperado_armazenado(self):
        score = calcular_score(38, Fase.CONFIGURACAO, 6)

        assert score.progresso_esperado == 60

    def test_gap_negativo_capped_em_zero(self):
        score = calcular_score(80, Fase.CONFIGURACAO, 6)

        assert score.valor == 100
        assert score.progresso_real == 80
        assert score.progresso_esperado == 60


class TestExtrairProgressoBoard:
    def test_board_com_marcadores_mistos(self):
        artefato = Artefato(
            id="board-001",
            tipo=TipoArtefato.BOARD,
            conteudo="[✓] A, [✓] B, [~] C",
            dia_projeto=3,
        )

        progresso = _extrair_progresso_board([artefato])

        assert progresso == 83

    def test_board_com_todos_falhos(self):
        artefato = Artefato(
            id="board-001",
            tipo=TipoArtefato.BOARD,
            conteudo="[✗] A, [✗] B, [✗] C",
            dia_projeto=6,
        )

        progresso = _extrair_progresso_board([artefato])

        assert progresso == 0

    def test_lista_vazia_sem_artefatos(self):
        progresso = _extrair_progresso_board([])

        assert progresso == 0

    def test_board_sem_marcadores_reconheciveis(self):
        artefato = Artefato(
            id="board-001",
            tipo=TipoArtefato.BOARD,
            conteudo="sem marcadores aqui",
            dia_projeto=3,
        )

        progresso = _extrair_progresso_board([artefato])

        assert progresso == 0


class TestEvolucaoHistorica:
    def test_score_deteriora_entre_updates(self):
        projeto = carregar_projeto_seed()
        update_1 = projeto.updates[0]
        update_2 = projeto.updates[1]

        resultado_u1 = ResultadoIngestao(
            artefatos_validos=[a for a in update_1.artefatos if a.valido],
            artefatos_invalidos=[a for a in update_1.artefatos if not a.valido],
        )

        resultado_u2 = ResultadoIngestao(
            artefatos_validos=[a for a in update_2.artefatos if a.valido],
            artefatos_invalidos=[a for a in update_2.artefatos if not a.valido],
        )

        score_u1 = calcular_delivery_score(resultado_u1, dia=update_1.dia_projeto)
        score_u2 = calcular_delivery_score(resultado_u2, dia=update_2.dia_projeto)

        assert score_u1.dados_suficientes is True
        assert score_u2.dados_suficientes is True
        assert score_u2.valor < score_u1.valor
