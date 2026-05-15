from datetime import datetime, timezone

from sprint_auditor.alert_engine import analisar_alertas
from sprint_auditor.ingestao import ingerir_artefatos
from sprint_auditor.modelos import (
    Alerta,
    Artefato,
    CategoriaAlerta,
    DeliveryScore,
    Fase,
    NivelConfianca,
    Projeto,
    TipoArtefato,
    Update,
)
from sprint_auditor.relatorio import (
    _formatar_alerta,
    _formatar_barra,
    gerar_relatorio,
)
from sprint_auditor.score_engine import calcular_delivery_score
from sprint_auditor.seed import carregar_projeto_seed


class TestGerarRelatorio:
    """Testes de integração do ponto de entrada gerar_relatorio"""

    def test_empty_state_projeto_sem_updates(self):
        """Projeto sem updates deve conter 'Sem dados suficientes para um Delivery Score
        confiável'"""
        projeto = Projeto(
            id="proj-test",
            nome="Test Project",
            data_kickoff=datetime(2026, 4, 28, 9, 0, 0, tzinfo=timezone.utc),
            updates=[],
        )

        relatorio = gerar_relatorio(projeto)

        assert "Sem dados suficientes para um Delivery Score confiável" in relatorio
        assert "Nenhum update foi processado" in relatorio

    def test_update_com_score_none(self):
        """Update com score=None deve exibir 'sem dados suficientes'"""
        update = Update(
            id="upd-test",
            numero=1,
            dia_projeto=3,
            artefatos=[],
            score=None,
        )

        projeto = Projeto(
            id="proj-test",
            nome="Test Project",
            data_kickoff=datetime(2026, 4, 28, 9, 0, 0, tzinfo=timezone.utc),
            updates=[update],
        )

        relatorio = gerar_relatorio(projeto)

        assert "sem dados suficientes" in relatorio

    def test_update_com_dados_insuficientes(self):
        """Update com dados_suficientes=False deve exibir 'sem dados suficientes'"""
        update = Update(
            id="upd-test",
            numero=1,
            dia_projeto=3,
            artefatos=[],
            score=DeliveryScore(dados_suficientes=False, valor=None),
        )

        projeto = Projeto(
            id="proj-test",
            nome="Test Project",
            data_kickoff=datetime(2026, 4, 28, 9, 0, 0, tzinfo=timezone.utc),
            updates=[update],
        )

        relatorio = gerar_relatorio(projeto)

        assert "sem dados suficientes" in relatorio

    def test_update_no_trilho_score_100(self):
        """Update com score=100 e sem alertas deve conter '100/100' e 'Projeto no trilho'"""
        update = Update(
            id="upd-test",
            numero=1,
            dia_projeto=3,
            artefatos=[
                Artefato(
                    id="art-test",
                    tipo=TipoArtefato.BOARD,
                    conteudo="[✓] Task 1, [✓] Task 2",
                    dia_projeto=3,
                )
            ],
            score=DeliveryScore(dados_suficientes=True, valor=100),
            alertas=[],
        )

        projeto = Projeto(
            id="proj-test",
            nome="Test Project",
            data_kickoff=datetime(2026, 4, 28, 9, 0, 0, tzinfo=timezone.utc),
            updates=[update],
        )

        relatorio = gerar_relatorio(projeto)

        assert "100/100" in relatorio
        assert "Projeto no trilho — nenhum desvio detectado." in relatorio
        assert "⚠" not in relatorio

    def test_update_com_desvio_limiar(self):
        """Update com DESVIO_LIMIAR deve conter categoria, confiança, gap, e fonte"""
        alerta = Alerta(
            categoria=CategoriaAlerta.DESVIO_LIMIAR,
            fase=Fase.CONFIGURACAO,
            dia_projeto=6,
            gap_pp=60.0,
            causa_provavel="Score 0 está abaixo do limiar 70",
            nivel_confianca=NivelConfianca.ALTO,
            acao_sugerida="Investigar bloqueios",
            artefato_fonte_id="art-test-board",
            trecho_fonte="Board de Configuração: [✗]",
        )

        update = Update(
            id="upd-test",
            numero=1,
            dia_projeto=6,
            artefatos=[],
            score=DeliveryScore(dados_suficientes=True, valor=0),
            alertas=[alerta],
        )

        projeto = Projeto(
            id="proj-test",
            nome="Test Project",
            data_kickoff=datetime(2026, 4, 28, 9, 0, 0, tzinfo=timezone.utc),
            updates=[update],
        )

        relatorio = gerar_relatorio(projeto)

        assert "DESVIO_LIMIAR" in relatorio
        assert "ALTA" in relatorio
        assert "Gap: 60.0 pp" in relatorio
        assert "art-test-board" in relatorio
        assert "Board de Configuração: [✗]" in relatorio

    def test_update_com_deterioracao_consistente(self):
        """Update com DETERIORACAO_CONSISTENTE deve conter categoria, confiança, mas sem gap"""
        alerta = Alerta(
            categoria=CategoriaAlerta.DETERIORACAO_CONSISTENTE,
            fase=Fase.CONFIGURACAO,
            dia_projeto=6,
            gap_pp=None,
            causa_provavel="Score caiu de 80 para 50 entre updates",
            nivel_confianca=NivelConfianca.MEDIO,
            acao_sugerida="Investigar causa da deterioração",
            artefato_fonte_id="art-test-board",
            trecho_fonte="Board degradado",
        )

        update = Update(
            id="upd-test",
            numero=2,
            dia_projeto=6,
            artefatos=[],
            score=DeliveryScore(dados_suficientes=True, valor=50),
            alertas=[alerta],
        )

        projeto = Projeto(
            id="proj-test",
            nome="Test Project",
            data_kickoff=datetime(2026, 4, 28, 9, 0, 0, tzinfo=timezone.utc),
            updates=[update],
        )

        relatorio = gerar_relatorio(projeto)

        assert "DETERIORACAO_CONSISTENTE" in relatorio
        assert "MÉDIA" in relatorio
        assert "Gap:" not in relatorio

    def test_update_com_bloqueio_linguistico(self):
        """Update com BLOQUEIO_LINGUISTICO deve conter categoria, confiança, e trecho casado"""
        alerta = Alerta(
            categoria=CategoriaAlerta.BLOQUEIO_LINGUISTICO,
            fase=Fase.CONFIGURACAO,
            dia_projeto=6,
            gap_pp=None,
            causa_provavel="Sinal de bloqueio: 'aguardando aprovação'",
            nivel_confianca=NivelConfianca.MEDIO,
            acao_sugerida="Escalar para o FDE Lead",
            artefato_fonte_id="art-test-transcricao",
            trecho_fonte="aguardando aprovação",
        )

        update = Update(
            id="upd-test",
            numero=1,
            dia_projeto=6,
            artefatos=[],
            score=DeliveryScore(dados_suficientes=True, valor=75),
            alertas=[alerta],
        )

        projeto = Projeto(
            id="proj-test",
            nome="Test Project",
            data_kickoff=datetime(2026, 4, 28, 9, 0, 0, tzinfo=timezone.utc),
            updates=[update],
        )

        relatorio = gerar_relatorio(projeto)

        assert "BLOQUEIO_LINGUISTICO" in relatorio
        assert "MÉDIA" in relatorio
        assert "aguardando aprovação" in relatorio

    def test_multi_alerta_ordem_por_gravidade(self):
        """Multi-alerta deve manter ordem DESVIO > DETERIORACAO > BLOQUEIO"""
        alerta_desvio = Alerta(
            categoria=CategoriaAlerta.DESVIO_LIMIAR,
            fase=Fase.CONFIGURACAO,
            dia_projeto=6,
            gap_pp=60.0,
            causa_provavel="Score baixo",
            nivel_confianca=NivelConfianca.ALTO,
            acao_sugerida="Investigar",
            artefato_fonte_id="art-desvio",
            trecho_fonte="Desvio",
        )

        alerta_bloqueio = Alerta(
            categoria=CategoriaAlerta.BLOQUEIO_LINGUISTICO,
            fase=Fase.CONFIGURACAO,
            dia_projeto=6,
            gap_pp=None,
            causa_provavel="Bloqueio detectado",
            nivel_confianca=NivelConfianca.MEDIO,
            acao_sugerida="Escalar",
            artefato_fonte_id="art-bloqueio",
            trecho_fonte="aguardando",
        )

        update = Update(
            id="upd-test",
            numero=1,
            dia_projeto=6,
            artefatos=[],
            score=DeliveryScore(dados_suficientes=True, valor=0),
            alertas=[alerta_bloqueio, alerta_desvio],
        )

        projeto = Projeto(
            id="proj-test",
            nome="Test Project",
            data_kickoff=datetime(2026, 4, 28, 9, 0, 0, tzinfo=timezone.utc),
            updates=[update],
        )

        relatorio = gerar_relatorio(projeto)

        idx_desvio = relatorio.index("DESVIO_LIMIAR")
        idx_bloqueio = relatorio.index("BLOQUEIO_LINGUISTICO")

        assert idx_desvio < idx_bloqueio

    def test_indicador_textual_desvio_na_linha_score(self):
        """Linha de score com DESVIO_LIMIAR deve conter '[DESVIO]'"""
        alerta = Alerta(
            categoria=CategoriaAlerta.DESVIO_LIMIAR,
            fase=Fase.CONFIGURACAO,
            dia_projeto=6,
            gap_pp=60.0,
            causa_provavel="Score baixo",
            nivel_confianca=NivelConfianca.ALTO,
            acao_sugerida="Investigar",
            artefato_fonte_id="art-test",
            trecho_fonte="Teste",
        )

        update = Update(
            id="upd-test",
            numero=1,
            dia_projeto=6,
            artefatos=[],
            score=DeliveryScore(dados_suficientes=True, valor=0),
            alertas=[alerta],
        )

        projeto = Projeto(
            id="proj-test",
            nome="Test Project",
            data_kickoff=datetime(2026, 4, 28, 9, 0, 0, tzinfo=timezone.utc),
            updates=[update],
        )

        relatorio = gerar_relatorio(projeto)
        linhas = [linha for linha in relatorio.split("\n") if "Delivery Score:" in linha]
        linha_score = linhas[0]

        assert "[DESVIO]" in linha_score

    def test_indicador_textual_ausente_quando_no_trilho(self):
        """Linha de score sem alertas não deve conter '['"""
        update = Update(
            id="upd-test",
            numero=1,
            dia_projeto=3,
            artefatos=[],
            score=DeliveryScore(dados_suficientes=True, valor=100),
            alertas=[],
        )

        projeto = Projeto(
            id="proj-test",
            nome="Test Project",
            data_kickoff=datetime(2026, 4, 28, 9, 0, 0, tzinfo=timezone.utc),
            updates=[update],
        )

        relatorio = gerar_relatorio(projeto)
        linhas = [linha for linha in relatorio.split("\n") if "Delivery Score:" in linha]
        linha_score = linhas[0]

        assert "[" not in linha_score

    def test_artefato_invalido_apontado_sem_omitir_demais(self):
        """Update com artefato inválido deve exibir erro e demais campos"""
        artefato_invalido = Artefato(
            id="art-invalid",
            tipo=TipoArtefato.BOARD,
            conteudo="",
            dia_projeto=3,
            valido=False,
            erro_ingestao="Conteúdo vazio ou ausente",
        )

        update = Update(
            id="upd-test",
            numero=1,
            dia_projeto=3,
            artefatos=[artefato_invalido],
            score=DeliveryScore(dados_suficientes=True, valor=75),
            alertas=[],
        )

        projeto = Projeto(
            id="proj-test",
            nome="Test Project",
            data_kickoff=datetime(2026, 4, 28, 9, 0, 0, tzinfo=timezone.utc),
            updates=[update],
        )

        relatorio = gerar_relatorio(projeto)

        assert "Ingestão: artefato art-invalid falhou" in relatorio
        assert "Conteúdo vazio ou ausente" in relatorio
        assert "75/100" in relatorio

    def test_historico_3_updates_ordem_cronologica(self):
        """Histórico com 3 updates deve aparecer em ordem crescente de numero"""
        updates = [
            Update(
                id="upd-1",
                numero=1,
                dia_projeto=3,
                artefatos=[],
                score=DeliveryScore(dados_suficientes=True, valor=83),
                alertas=[],
            ),
            Update(
                id="upd-2",
                numero=2,
                dia_projeto=6,
                artefatos=[],
                score=DeliveryScore(dados_suficientes=True, valor=0),
                alertas=[],
            ),
            Update(
                id="upd-3",
                numero=3,
                dia_projeto=9,
                artefatos=[],
                score=DeliveryScore(dados_suficientes=True, valor=20),
                alertas=[],
            ),
        ]

        projeto = Projeto(
            id="proj-test",
            nome="Test Project",
            data_kickoff=datetime(2026, 4, 28, 9, 0, 0, tzinfo=timezone.utc),
            updates=updates,
        )

        relatorio = gerar_relatorio(projeto)

        assert "Histórico de Delivery Score:" in relatorio
        idx_u1 = relatorio.index("Update #1 (Dia  3)")
        idx_u2 = relatorio.index("Update #2 (Dia  6)")
        idx_u3 = relatorio.index("Update #3 (Dia  9)")

        assert idx_u1 < idx_u2 < idx_u3

    def test_historico_update_com_dados_insuficientes(self):
        """Histórico com update sem dados deve exibir texto, não número"""
        updates = [
            Update(
                id="upd-1",
                numero=1,
                dia_projeto=3,
                artefatos=[],
                score=DeliveryScore(dados_suficientes=True, valor=83),
                alertas=[],
            ),
            Update(
                id="upd-2",
                numero=2,
                dia_projeto=6,
                artefatos=[],
                score=DeliveryScore(dados_suficientes=False, valor=None),
                alertas=[],
            ),
        ]

        projeto = Projeto(
            id="proj-test",
            nome="Test Project",
            data_kickoff=datetime(2026, 4, 28, 9, 0, 0, tzinfo=timezone.utc),
            updates=updates,
        )

        relatorio = gerar_relatorio(projeto)

        historico_section = relatorio[relatorio.index("Histórico de Delivery Score:") :]

        assert "Update #2 (Dia  6): sem dados suficientes" in historico_section

    def test_historico_update_com_alerta_exibe_aviso(self):
        """Histórico com update com alertas deve exibir '⚠'"""
        alerta = Alerta(
            categoria=CategoriaAlerta.DESVIO_LIMIAR,
            fase=Fase.CONFIGURACAO,
            dia_projeto=6,
            gap_pp=60.0,
            causa_provavel="Score baixo",
            nivel_confianca=NivelConfianca.ALTO,
            acao_sugerida="Investigar",
            artefato_fonte_id="art-test",
            trecho_fonte="Teste",
        )

        updates = [
            Update(
                id="upd-1",
                numero=1,
                dia_projeto=3,
                artefatos=[],
                score=DeliveryScore(dados_suficientes=True, valor=83),
                alertas=[],
            ),
            Update(
                id="upd-2",
                numero=2,
                dia_projeto=6,
                artefatos=[],
                score=DeliveryScore(dados_suficientes=True, valor=0),
                alertas=[alerta],
            ),
        ]

        projeto = Projeto(
            id="proj-test",
            nome="Test Project",
            data_kickoff=datetime(2026, 4, 28, 9, 0, 0, tzinfo=timezone.utc),
            updates=updates,
        )

        relatorio = gerar_relatorio(projeto)

        historico_section = relatorio[relatorio.index("Histórico de Delivery Score:") :]

        assert "Update #2 (Dia  6):" in historico_section
        assert "⚠" in historico_section.split("Update #2 (Dia  6):")[1].split("\n")[0]

    def test_ausencia_de_alerta_eh_estado_de_sucesso_explicito(self):
        """Update sem alertas deve exibir mensagem afirmativa 'no trilho'"""
        update = Update(
            id="upd-test",
            numero=1,
            dia_projeto=3,
            artefatos=[],
            score=DeliveryScore(dados_suficientes=True, valor=90),
            alertas=[],
        )

        projeto = Projeto(
            id="proj-test",
            nome="Test Project",
            data_kickoff=datetime(2026, 4, 28, 9, 0, 0, tzinfo=timezone.utc),
            updates=[update],
        )

        relatorio = gerar_relatorio(projeto)

        assert "Projeto no trilho — nenhum desvio detectado." in relatorio

    def test_historico_seta_decrescente_para_score_em_queda(self):
        """T08-G: seta ↘ exibida quando score decresce"""
        alerta = Alerta(
            categoria=CategoriaAlerta.DESVIO_LIMIAR,
            fase=Fase.CONFIGURACAO,
            dia_projeto=6,
            gap_pp=60.0,
            causa_provavel="Score baixo",
            nivel_confianca=NivelConfianca.ALTO,
            acao_sugerida="Investigar",
            artefato_fonte_id="art-test",
            trecho_fonte="Teste",
        )

        updates = [
            Update(
                id="upd-1",
                numero=1,
                dia_projeto=3,
                artefatos=[],
                score=DeliveryScore(dados_suficientes=True, valor=83),
                alertas=[],
            ),
            Update(
                id="upd-2",
                numero=2,
                dia_projeto=6,
                artefatos=[],
                score=DeliveryScore(dados_suficientes=True, valor=40),
                alertas=[alerta],
            ),
        ]

        projeto = Projeto(
            id="proj-test",
            nome="Test Project",
            data_kickoff=datetime(2026, 4, 28, 9, 0, 0, tzinfo=timezone.utc),
            updates=updates,
        )

        relatorio = gerar_relatorio(projeto)

        historico_section = relatorio[relatorio.index("Histórico de Delivery Score:") :]
        linhas = [line for line in historico_section.split("\n") if "Update #2" in line]

        assert len(linhas) > 0
        assert "↘" in linhas[0]
        assert "⚠" in linhas[0]

    def test_historico_seta_crescente_para_score_em_subida(self):
        """T08-H: seta ↗ exibida quando score sobe"""
        alerta = Alerta(
            categoria=CategoriaAlerta.BLOQUEIO_LINGUISTICO,
            fase=Fase.DESENVOLVIMENTO,
            dia_projeto=9,
            gap_pp=None,
            causa_provavel="Bloqueio detectado",
            nivel_confianca=NivelConfianca.MEDIO,
            acao_sugerida="Escalar",
            artefato_fonte_id="art-test",
            trecho_fonte="Teste",
        )

        updates = [
            Update(
                id="upd-1",
                numero=1,
                dia_projeto=3,
                artefatos=[],
                score=DeliveryScore(dados_suficientes=True, valor=40),
                alertas=[],
            ),
            Update(
                id="upd-2",
                numero=2,
                dia_projeto=9,
                artefatos=[],
                score=DeliveryScore(dados_suficientes=True, valor=75),
                alertas=[alerta],
            ),
        ]

        projeto = Projeto(
            id="proj-test",
            nome="Test Project",
            data_kickoff=datetime(2026, 4, 28, 9, 0, 0, tzinfo=timezone.utc),
            updates=updates,
        )

        relatorio = gerar_relatorio(projeto)

        historico_section = relatorio[relatorio.index("Histórico de Delivery Score:") :]
        linhas = [line for line in historico_section.split("\n") if "Update #2" in line]

        assert len(linhas) > 0
        assert "↗" in linhas[0]
        assert "⚠" in linhas[0]

    def test_historico_seta_estavel_para_score_constante(self):
        """T08-I: seta → exibida quando score se mantém"""
        alerta = Alerta(
            categoria=CategoriaAlerta.BLOQUEIO_LINGUISTICO,
            fase=Fase.DESENVOLVIMENTO,
            dia_projeto=9,
            gap_pp=None,
            causa_provavel="Bloqueio detectado",
            nivel_confianca=NivelConfianca.MEDIO,
            acao_sugerida="Escalar",
            artefato_fonte_id="art-test",
            trecho_fonte="Teste",
        )

        updates = [
            Update(
                id="upd-1",
                numero=1,
                dia_projeto=3,
                artefatos=[],
                score=DeliveryScore(dados_suficientes=True, valor=75),
                alertas=[],
            ),
            Update(
                id="upd-2",
                numero=2,
                dia_projeto=9,
                artefatos=[],
                score=DeliveryScore(dados_suficientes=True, valor=75),
                alertas=[alerta],
            ),
        ]

        projeto = Projeto(
            id="proj-test",
            nome="Test Project",
            data_kickoff=datetime(2026, 4, 28, 9, 0, 0, tzinfo=timezone.utc),
            updates=updates,
        )

        relatorio = gerar_relatorio(projeto)

        historico_section = relatorio[relatorio.index("Histórico de Delivery Score:") :]
        linhas = [line for line in historico_section.split("\n") if "Update #2" in line]

        assert len(linhas) > 0
        assert "→" in linhas[0]
        assert "⚠" in linhas[0]

    def test_historico_dados_insuficientes_reseta_seta(self):
        """T08-J: dados_suficientes=False reseta seta do próximo update"""
        updates = [
            Update(
                id="upd-1",
                numero=1,
                dia_projeto=3,
                artefatos=[],
                score=DeliveryScore(dados_suficientes=True, valor=83),
                alertas=[],
            ),
            Update(
                id="upd-2",
                numero=2,
                dia_projeto=6,
                artefatos=[],
                score=DeliveryScore(dados_suficientes=False, valor=None),
                alertas=[],
            ),
            Update(
                id="upd-3",
                numero=3,
                dia_projeto=9,
                artefatos=[],
                score=DeliveryScore(dados_suficientes=True, valor=75),
                alertas=[],
            ),
        ]

        projeto = Projeto(
            id="proj-test",
            nome="Test Project",
            data_kickoff=datetime(2026, 4, 28, 9, 0, 0, tzinfo=timezone.utc),
            updates=updates,
        )

        relatorio = gerar_relatorio(projeto)

        historico_section = relatorio[relatorio.index("Histórico de Delivery Score:") :]
        linhas_u3 = [line for line in historico_section.split("\n") if "Update #3" in line]

        assert len(linhas_u3) > 0
        linha_u3 = linhas_u3[0]
        assert "↗" not in linha_u3 and "↘" not in linha_u3 and "→" not in linha_u3


class TestFormatar:
    """Testes de funções de formatação interna"""

    def test_formatar_barra_0(self):
        """_formatar_barra(0) deve retornar 10 '░'"""
        resultado = _formatar_barra(0)
        assert resultado == "░░░░░░░░░░"
        assert len(resultado) == 10

    def test_formatar_barra_100(self):
        """_formatar_barra(100) deve retornar 10 '█'"""
        resultado = _formatar_barra(100)
        assert resultado == "██████████"
        assert len(resultado) == 10

    def test_formatar_barra_50(self):
        """_formatar_barra(50) deve retornar 5 '█' + 5 '░'"""
        resultado = _formatar_barra(50)
        assert resultado == "█████░░░░░"
        assert len(resultado) == 10

    def test_formatar_alerta_com_gap_pp(self):
        """_formatar_alerta com gap_pp deve conter 'Gap: ' com ' pp'"""
        alerta = Alerta(
            categoria=CategoriaAlerta.DESVIO_LIMIAR,
            fase=Fase.CONFIGURACAO,
            dia_projeto=6,
            gap_pp=60.0,
            causa_provavel="Score baixo",
            nivel_confianca=NivelConfianca.ALTO,
            acao_sugerida="Investigar",
            artefato_fonte_id="art-test",
            trecho_fonte="Teste",
        )

        resultado = _formatar_alerta(alerta)

        assert "Gap: 60.0 pp" in resultado

    def test_formatar_alerta_sem_gap_pp(self):
        """_formatar_alerta sem gap_pp não deve conter 'Gap:'"""
        alerta = Alerta(
            categoria=CategoriaAlerta.BLOQUEIO_LINGUISTICO,
            fase=Fase.CONFIGURACAO,
            dia_projeto=6,
            gap_pp=None,
            causa_provavel="Bloqueio detectado",
            nivel_confianca=NivelConfianca.MEDIO,
            acao_sugerida="Escalar",
            artefato_fonte_id="art-test",
            trecho_fonte="Teste",
        )

        resultado = _formatar_alerta(alerta)

        assert "Gap:" not in resultado


class TestSeedRastreabilidade:
    """Testes de integração com o seed — rastreabilidade fim a fim"""

    def test_seed_pipeline_completo_u2_rastreavel(self):
        """Seed processado deve conter trecho 'aguardando aprovação' em U2"""
        projeto = carregar_projeto_seed()

        for update in projeto.updates:
            resultado = ingerir_artefatos(update.artefatos)
            update.score = calcular_delivery_score(resultado, dia=update.dia_projeto)
            update.alertas = analisar_alertas(update, [])

        relatorio = gerar_relatorio(projeto)

        assert "aguardando aprovação" in relatorio

    def test_seed_pipeline_u1_no_trilho_u2_u3_com_desvio(self):
        """Seed: U1 no trilho, U2 com DESVIO_LIMIAR, U3 com BLOQUEIO_LINGUISTICO"""
        projeto = carregar_projeto_seed()

        updates_com_anteriores = []
        for update in projeto.updates:
            resultado = ingerir_artefatos(update.artefatos)
            update.score = calcular_delivery_score(resultado, dia=update.dia_projeto)
            update.alertas = analisar_alertas(update, updates_com_anteriores)
            updates_com_anteriores.append(update)

        relatorio = gerar_relatorio(projeto)

        u1_section = relatorio.split("Update #2")[0]
        u2_section = relatorio.split("Update #2")[1].split("Update #3")[0]
        u3_section = relatorio.split("Update #3")[1]

        assert "Projeto no trilho" in u1_section
        assert "DESVIO_LIMIAR" in u2_section
        assert "BLOQUEIO_LINGUISTICO" in u3_section
