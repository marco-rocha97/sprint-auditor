from datetime import timedelta

from src.sprint_auditor.modelos import TipoArtefato
from src.sprint_auditor.seed import carregar_projeto_seed


class TestCarregarProjetoSeed:
    def test_estrutura_minima(self):
        projeto = carregar_projeto_seed()
        assert isinstance(projeto.updates, list)
        assert len(projeto.updates) >= 3

    def test_diversidade_de_tipos(self):
        projeto = carregar_projeto_seed()
        tipos = set()
        for update in projeto.updates:
            for artefato in update.artefatos:
                tipos.add(artefato.tipo)
        assert TipoArtefato.TRANSCRICAO in tipos
        assert TipoArtefato.BOARD in tipos

    def test_dia_de_desvio_presente(self):
        projeto = carregar_projeto_seed()
        dias = [update.dia_projeto for update in projeto.updates]
        assert 6 in dias

    def test_cronologia_updates(self):
        projeto = carregar_projeto_seed()
        dias = [update.dia_projeto for update in projeto.updates]
        assert dias == sorted(dias)

    def test_ancora_de_bloqueio_sap(self):
        projeto = carregar_projeto_seed()
        encontrou_bloqueio = False
        for update in projeto.updates:
            if update.dia_projeto == 6:
                for artefato in update.artefatos:
                    if artefato.tipo == TipoArtefato.TRANSCRICAO:
                        if "SAP" in artefato.conteudo:
                            encontrou_bloqueio = True
        assert encontrou_bloqueio is True

    def test_timezone_utc(self):
        projeto = carregar_projeto_seed()
        assert projeto.data_kickoff.tzinfo is not None
        assert projeto.data_kickoff.utcoffset() == timedelta(0)
