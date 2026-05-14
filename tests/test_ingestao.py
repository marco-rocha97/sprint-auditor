import pytest

from src.sprint_auditor.ingestao import ingerir_artefatos
from src.sprint_auditor.modelos import Artefato, TipoArtefato


class TestIngestaoHappyPath:
    def test_transcricao_valida_unica(self):
        artefato = Artefato(
            id="art-001",
            tipo=TipoArtefato.TRANSCRICAO,
            conteudo="texto qualquer",
            dia_projeto=1,
        )
        resultado = ingerir_artefatos([artefato])

        assert resultado.tem_artefatos is True
        assert len(resultado.artefatos_validos) == 1
        assert len(resultado.artefatos_invalidos) == 0
        assert resultado.artefatos_validos[0].valido is True

    def test_dois_tipos_validos(self):
        board = Artefato(
            id="board-001",
            tipo=TipoArtefato.BOARD,
            conteudo="dados do board",
            dia_projeto=1,
        )
        transcricao = Artefato(
            id="trans-001",
            tipo=TipoArtefato.TRANSCRICAO,
            conteudo="transcrição da call",
            dia_projeto=1,
        )
        resultado = ingerir_artefatos([board, transcricao])

        assert resultado.tem_artefatos is True
        assert len(resultado.artefatos_validos) == 2
        assert len(resultado.artefatos_invalidos) == 0


class TestIngestaoArtefatosInvalidos:
    def test_conteudo_vazio(self):
        artefato = Artefato(
            id="art-002",
            tipo=TipoArtefato.TRANSCRICAO,
            conteudo="",
            dia_projeto=1,
        )
        resultado = ingerir_artefatos([artefato])

        assert len(resultado.artefatos_invalidos) == 1
        assert resultado.artefatos_invalidos[0].valido is False
        assert resultado.artefatos_invalidos[0].erro_ingestao is not None
        assert resultado.tem_artefatos is False

    def test_conteudo_so_whitespace(self):
        artefato = Artefato(
            id="art-003",
            tipo=TipoArtefato.TRANSCRICAO,
            conteudo="\n\t  ",
            dia_projeto=1,
        )
        resultado = ingerir_artefatos([artefato])

        assert len(resultado.artefatos_invalidos) == 1
        assert resultado.artefatos_invalidos[0].valido is False
        assert resultado.artefatos_invalidos[0].erro_ingestao is not None

    def test_mistura_valido_invalido(self):
        valido = Artefato(
            id="art-004",
            tipo=TipoArtefato.TRANSCRICAO,
            conteudo="conteúdo válido",
            dia_projeto=1,
        )
        invalido = Artefato(
            id="art-005",
            tipo=TipoArtefato.TRANSCRICAO,
            conteudo="",
            dia_projeto=1,
        )
        resultado = ingerir_artefatos([valido, invalido])

        assert len(resultado.artefatos_validos) == 1
        assert len(resultado.artefatos_invalidos) == 1
        assert resultado.tem_artefatos is True


class TestIngestaoSemArtefatos:
    def test_lista_entrada_vazia(self):
        resultado = ingerir_artefatos([])

        assert resultado.tem_artefatos is False
        assert len(resultado.artefatos_validos) == 0
        assert len(resultado.artefatos_invalidos) == 0

    def test_todos_invalidos(self):
        art1 = Artefato(
            id="art-006",
            tipo=TipoArtefato.TRANSCRICAO,
            conteudo="",
            dia_projeto=1,
        )
        art2 = Artefato(
            id="art-007",
            tipo=TipoArtefato.BOARD,
            conteudo="",
            dia_projeto=1,
        )
        resultado = ingerir_artefatos([art1, art2])

        assert resultado.tem_artefatos is False
        assert len(resultado.artefatos_validos) == 0
        assert len(resultado.artefatos_invalidos) == 2


class TestNormalizacao:
    def test_strip_aplicado_no_valido(self):
        artefato = Artefato(
            id="art-008",
            tipo=TipoArtefato.TRANSCRICAO,
            conteudo="  texto com bordas  ",
            dia_projeto=1,
        )
        resultado = ingerir_artefatos([artefato])

        assert len(resultado.artefatos_validos) == 1
        assert resultado.artefatos_validos[0].conteudo == "texto com bordas"


class TestGarantias:
    def test_sem_mutacao_do_input(self):
        artefato = Artefato(
            id="art-009",
            tipo=TipoArtefato.TRANSCRICAO,
            conteudo="",
            dia_projeto=1,
        )
        conteudo_original = artefato.conteudo
        valido_original = artefato.valido

        ingerir_artefatos([artefato])

        assert artefato.conteudo == conteudo_original
        assert artefato.valido == valido_original

    def test_rastreabilidade_do_erro(self):
        artefato = Artefato(
            id="art-010",
            tipo=TipoArtefato.TRANSCRICAO,
            conteudo="",
            dia_projeto=5,
        )
        resultado = ingerir_artefatos([artefato])

        assert len(resultado.artefatos_invalidos) == 1
        assert resultado.artefatos_invalidos[0].id == "art-010"
        assert resultado.artefatos_invalidos[0].dia_projeto == 5
