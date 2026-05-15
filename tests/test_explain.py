import sys

from sprint_auditor.explain import decompor_score, main_explain
from sprint_auditor.ingestao import ingerir_artefatos
from sprint_auditor.modelos import DeliveryScore, Update
from sprint_auditor.score_engine import calcular_delivery_score
from sprint_auditor.seed import carregar_projeto_seed


class TestDecomporScore:
    """Testes da função decompor_score"""

    def test_happy_path_update_2(self):
        """Update com score(40, 0, 60) → output com 40/100 e 60 pp."""
        projeto = carregar_projeto_seed()
        update_2 = projeto.updates[1]

        resultado_ingestao = ingerir_artefatos(update_2.artefatos)
        score = calcular_delivery_score(resultado_ingestao, dia=update_2.dia_projeto)
        update_2.score = score

        output = decompor_score(update_2)

        assert "40/100" in output
        assert "60 pp" in output
        assert "ABAIXO DO LIMIAR" in output

    def test_update_no_trilho(self):
        """Update #1 com score=83 e sem alertas → output contém NO TRILHO"""
        projeto = carregar_projeto_seed()
        update_1 = projeto.updates[0]

        resultado_ingestao = ingerir_artefatos(update_1.artefatos)
        score = calcular_delivery_score(resultado_ingestao, dia=update_1.dia_projeto)
        update_1.score = score
        update_1.alertas = []

        output = decompor_score(update_1)

        assert "NO TRILHO" in output

    def test_score_none_retorna_erro(self):
        """Update com score=None → output contém mensagem de erro"""
        update = Update(
            id="test",
            numero=1,
            dia_projeto=3,
            artefatos=[],
            score=None,
        )

        output = decompor_score(update)

        assert "Erro" in output

    def test_dados_insuficientes_retorna_erro(self):
        """Update com dados_suficientes=False → output contém mensagem de erro"""
        update = Update(
            id="test",
            numero=1,
            dia_projeto=3,
            artefatos=[],
            score=DeliveryScore(dados_suficientes=False, valor=None),
        )

        output = decompor_score(update)

        assert "Erro" in output

    def test_update_score_acima_limiar_com_alertas_em_alerta(self):
        """T08-F: update com score ≥ 70 e alertas → status EM ALERTA"""
        from sprint_auditor.modelos import (
            Alerta,
            Artefato,
            CategoriaAlerta,
            Fase,
            NivelConfianca,
            TipoArtefato,
        )

        update = Update(
            id="upd-test",
            numero=3,
            dia_projeto=9,
            artefatos=[
                Artefato(
                    id="art-trans",
                    tipo=TipoArtefato.TRANSCRICAO,
                    conteudo="aguardando aprovação",
                    dia_projeto=9,
                )
            ],
            score=DeliveryScore(
                dados_suficientes=True,
                valor=75,
                progresso_real=50,
                progresso_esperado=60,
            ),
            alertas=[
                Alerta(
                    categoria=CategoriaAlerta.BLOQUEIO_LINGUISTICO,
                    fase=Fase.DESENVOLVIMENTO,
                    dia_projeto=9,
                    gap_pp=None,
                    causa_provavel="Bloqueio identificado",
                    hipotese_causal="Bloqueio externo",
                    nivel_confianca=NivelConfianca.MEDIO,
                    acao_sugerida="Escalar",
                    artefato_fonte_id="art-trans",
                    trecho_fonte="aguardando aprovação",
                )
            ],
        )

        output = decompor_score(update)

        assert "EM ALERTA" in output
        assert "NO TRILHO" not in output


class TestMainExplain:
    """Testes da função main_explain (integração)"""

    def test_update_2_retorna_output_valido(self, capsys, monkeypatch):
        """main_explain --update 2 → não levanta exceção; output contém Update #2"""
        monkeypatch.setattr(sys, "argv", ["explain", "--update", "2"])

        try:
            main_explain()
        except SystemExit as e:
            assert e.code == 0, f"main_explain exited with code {e.code}"

        capturado = capsys.readouterr()
        assert "Update #2" in capturado.out

    def test_update_inexistente_exibe_erro(self, capsys, monkeypatch):
        """main_explain --update 99 → imprime erro; sys.exit(1)"""
        monkeypatch.setattr(sys, "argv", ["explain", "--update", "99"])

        try:
            main_explain()
            assert False, "main_explain deveria ter feito sys.exit(1)"
        except SystemExit as e:
            assert e.code == 1

        capturado = capsys.readouterr()
        assert "Erro" in capturado.out or "não encontrado" in capturado.out

    def test_argumento_invalido_exibe_uso(self, capsys, monkeypatch):
        """main_explain sem --update → imprime mensagem de uso; sys.exit(1)"""
        monkeypatch.setattr(sys, "argv", ["explain"])

        try:
            main_explain()
            assert False, "main_explain deveria ter feito sys.exit(1)"
        except SystemExit as e:
            assert e.code == 1

        capturado = capsys.readouterr()
        assert "Uso:" in capturado.out
