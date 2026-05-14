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
        """Update #1 com score=83 → output contém NO TRILHO"""
        projeto = carregar_projeto_seed()
        update_1 = projeto.updates[0]

        resultado_ingestao = ingerir_artefatos(update_1.artefatos)
        score = calcular_delivery_score(resultado_ingestao, dia=update_1.dia_projeto)
        update_1.score = score

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
