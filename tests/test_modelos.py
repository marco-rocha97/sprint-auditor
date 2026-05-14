from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from src.sprint_auditor.modelos import (
    Artefato,
    DeliveryScore,
    Projeto,
    TipoArtefato,
    Update,
)


class TestDeliveryScore:
    def test_score_com_dados_happy_path(self):
        score = DeliveryScore(dados_suficientes=True, valor=75)
        assert score.dados_suficientes is True
        assert score.valor == 75

    def test_score_sem_dados_happy_path(self):
        score = DeliveryScore(dados_suficientes=False, valor=None)
        assert score.dados_suficientes is False
        assert score.valor is None

    def test_score_inconsistencia_dados_true_valor_none(self):
        with pytest.raises(ValidationError):
            DeliveryScore(dados_suficientes=True, valor=None)

    def test_score_inconsistencia_dados_false_valor_not_none(self):
        with pytest.raises(ValidationError):
            DeliveryScore(dados_suficientes=False, valor=50)

    def test_score_valor_zero_valido(self):
        score = DeliveryScore(dados_suficientes=True, valor=0)
        assert score.valor == 0

    def test_score_valor_cem_valido(self):
        score = DeliveryScore(dados_suficientes=True, valor=100)
        assert score.valor == 100


class TestArtefato:
    def test_artefato_dia_zero_invalido(self):
        with pytest.raises(ValidationError):
            Artefato(
                id="art-1",
                tipo=TipoArtefato.TRANSCRICAO,
                conteudo="teste",
                dia_projeto=0,
            )

    def test_artefato_dia_dezesseis_invalido(self):
        with pytest.raises(ValidationError):
            Artefato(
                id="art-1",
                tipo=TipoArtefato.TRANSCRICAO,
                conteudo="teste",
                dia_projeto=16,
            )


class TestUpdate:
    def test_update_sem_score_valido(self):
        update = Update(
            id="upd-1",
            numero=1,
            dia_projeto=3,
            artefatos=[],
            score=None,
        )
        assert update.score is None

    def test_update_score_none_distinto_de_dados_insuficientes(self):
        update_sem_score = Update(
            id="upd-1",
            numero=1,
            dia_projeto=3,
            score=None,
        )
        score_insuficiente = DeliveryScore(dados_suficientes=False, valor=None)
        assert update_sem_score.score is None
        assert isinstance(score_insuficiente, DeliveryScore)
        assert update_sem_score.score != score_insuficiente


class TestProjeto:
    def test_projeto_com_data_utc(self):
        data_utc = datetime(2026, 4, 28, 9, 0, 0, tzinfo=timezone.utc)
        projeto = Projeto(
            id="proj-1",
            nome="Teste",
            data_kickoff=data_utc,
        )
        assert projeto.data_kickoff.tzinfo is not None
