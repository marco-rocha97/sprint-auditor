import pytest

from sprint_auditor.modelos import Fase
from sprint_auditor.template_fases import fase_do_dia, progresso_esperado


class TestProgressoEsperado:
    def test_criterio_spec_configuracao_dia_6(self):
        assert progresso_esperado(Fase.CONFIGURACAO, 6) == 60

    def test_fim_de_cada_fase_eh_cem(self):
        assert progresso_esperado(Fase.DISCOVERY, 3) == 100
        assert progresso_esperado(Fase.CONFIGURACAO, 7) == 100
        assert progresso_esperado(Fase.DESENVOLVIMENTO, 12) == 100
        assert progresso_esperado(Fase.REVIEW, 15) == 100

    def test_inicio_de_cada_fase(self):
        assert progresso_esperado(Fase.DISCOVERY, 1) == 30
        assert progresso_esperado(Fase.CONFIGURACAO, 4) == 10
        assert progresso_esperado(Fase.DESENVOLVIMENTO, 8) == 10
        assert progresso_esperado(Fase.REVIEW, 13) == 30

    def test_combinacao_invalida_raises_keyerror(self):
        with pytest.raises(KeyError):
            progresso_esperado(Fase.DISCOVERY, 5)


class TestFaseDodia:
    def test_fases_por_dia_limites(self):
        assert fase_do_dia(1) == Fase.DISCOVERY
        assert fase_do_dia(3) == Fase.DISCOVERY
        assert fase_do_dia(4) == Fase.CONFIGURACAO
        assert fase_do_dia(7) == Fase.CONFIGURACAO
        assert fase_do_dia(8) == Fase.DESENVOLVIMENTO
        assert fase_do_dia(12) == Fase.DESENVOLVIMENTO
        assert fase_do_dia(13) == Fase.REVIEW
        assert fase_do_dia(15) == Fase.REVIEW

    def test_dia_fora_do_range_raises_valueerror(self):
        with pytest.raises(ValueError):
            fase_do_dia(0)
        with pytest.raises(ValueError):
            fase_do_dia(16)
