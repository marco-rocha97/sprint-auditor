from sprint_auditor.alert_engine import (
    _detectar_bloqueio_linguistico,
    _detectar_desvio_limiar,
    _detectar_deterioracao_consistente,
    analisar_alertas,
)
from sprint_auditor.ingestao import ingerir_artefatos
from sprint_auditor.modelos import (
    Artefato,
    CategoriaAlerta,
    DeliveryScore,
    NivelConfianca,
    TipoArtefato,
    Update,
)
from sprint_auditor.score_engine import calcular_delivery_score
from sprint_auditor.seed import carregar_projeto_seed


class TestAnalisarAlertas:
    """Testes de integração do ponto de entrada analisar_alertas"""

    def test_silencio_quando_no_trilho(self):
        """Update com score=100 e sem bloqueio deve retornar lista vazia"""
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
        )

        alertas = analisar_alertas(update, [])

        assert alertas == []

    def test_desvio_limiar_unico(self):
        """Update com score abaixo do limiar deve gerar alerta DESVIO_LIMIAR"""
        update = Update(
            id="upd-test",
            numero=1,
            dia_projeto=3,
            artefatos=[
                Artefato(
                    id="art-test",
                    tipo=TipoArtefato.BOARD,
                    conteudo="[✗] Task 1, [✗] Task 2",
                    dia_projeto=3,
                )
            ],
            score=DeliveryScore(dados_suficientes=True, valor=0),
        )

        alertas = analisar_alertas(update, [])

        assert len(alertas) == 1
        assert alertas[0].categoria == CategoriaAlerta.DESVIO_LIMIAR

    def test_bloqueio_linguistico_unico(self):
        """Update com score acima do limiar mas com bloqueio deve gerar BLOQUEIO_LINGUISTICO"""
        update = Update(
            id="upd-test",
            numero=1,
            dia_projeto=3,
            artefatos=[
                Artefato(
                    id="art-test",
                    tipo=TipoArtefato.TRANSCRICAO,
                    conteudo="Aguardando aprovação do departamento",
                    dia_projeto=3,
                )
            ],
            score=DeliveryScore(dados_suficientes=True, valor=80),
        )

        alertas = analisar_alertas(update, [])

        assert len(alertas) == 1
        assert alertas[0].categoria == CategoriaAlerta.BLOQUEIO_LINGUISTICO

    def test_multi_alerta_desvio_e_bloqueio(self):
        """Update com score baixo E bloqueio deve retornar 2 alertas"""
        update = Update(
            id="upd-test",
            numero=1,
            dia_projeto=3,
            artefatos=[
                Artefato(
                    id="art-board",
                    tipo=TipoArtefato.BOARD,
                    conteudo="[✗] Task 1",
                    dia_projeto=3,
                ),
                Artefato(
                    id="art-trans",
                    tipo=TipoArtefato.TRANSCRICAO,
                    conteudo="Bloqueado por falta de acesso",
                    dia_projeto=3,
                ),
            ],
            score=DeliveryScore(dados_suficientes=True, valor=0),
        )

        alertas = analisar_alertas(update, [])

        assert len(alertas) == 2
        categorias = {a.categoria for a in alertas}
        assert categorias == {CategoriaAlerta.DESVIO_LIMIAR, CategoriaAlerta.BLOQUEIO_LINGUISTICO}

    def test_dados_insuficientes_sem_bloqueio(self):
        """Update com dados_suficientes=False e sem bloqueio → lista vazia"""
        update = Update(
            id="upd-test",
            numero=1,
            dia_projeto=3,
            artefatos=[
                Artefato(
                    id="art-test",
                    tipo=TipoArtefato.BOARD,
                    conteudo="",
                    dia_projeto=3,
                    valido=False,
                )
            ],
            score=DeliveryScore(dados_suficientes=False, valor=None),
        )

        alertas = analisar_alertas(update, [])

        assert alertas == []

    def test_dados_insuficientes_com_bloqueio(self):
        """Update com dados_suficientes=False mas com bloqueio → gera BLOQUEIO_LINGUISTICO"""
        update = Update(
            id="upd-test",
            numero=1,
            dia_projeto=3,
            artefatos=[
                Artefato(
                    id="art-test",
                    tipo=TipoArtefato.TRANSCRICAO,
                    conteudo="Completamente bloqueado",
                    dia_projeto=3,
                )
            ],
            score=DeliveryScore(dados_suficientes=False, valor=None),
        )

        alertas = analisar_alertas(update, [])

        assert len(alertas) == 1
        assert alertas[0].categoria == CategoriaAlerta.BLOQUEIO_LINGUISTICO


class TestDetectarDesvioLimiar:
    """Testes do detector DESVIO_LIMIAR"""

    def test_score_69_abaixo_limiar(self):
        """Score=69 está abaixo do limiar 70 → Alerta"""
        update = Update(
            id="upd-test",
            numero=1,
            dia_projeto=3,
            artefatos=[
                Artefato(
                    id="art-board",
                    tipo=TipoArtefato.BOARD,
                    conteudo="[✓] Task 1, [~] Task 2",
                    dia_projeto=3,
                )
            ],
            score=DeliveryScore(dados_suficientes=True, valor=69),
        )

        alerta = _detectar_desvio_limiar(update)

        assert alerta is not None
        assert alerta.categoria == CategoriaAlerta.DESVIO_LIMIAR
        assert alerta.nivel_confianca == NivelConfianca.ALTO
        assert alerta.artefato_fonte_id == "art-board"
        assert alerta.gap_pp is not None

    def test_score_70_boundary_nao_dispara(self):
        """Score=70 (exatamente no limiar) NÃO dispara — limiar é exclusivo (<, não <=)"""
        update = Update(
            id="upd-test",
            numero=1,
            dia_projeto=3,
            artefatos=[
                Artefato(
                    id="art-board",
                    tipo=TipoArtefato.BOARD,
                    conteudo="[✓] Task 1",
                    dia_projeto=3,
                )
            ],
            score=DeliveryScore(dados_suficientes=True, valor=70),
        )

        alerta = _detectar_desvio_limiar(update)

        assert alerta is None

    def test_score_71_acima_limiar_nao_dispara(self):
        """Score=71 está acima do limiar → Nenhum Alerta"""
        update = Update(
            id="upd-test",
            numero=1,
            dia_projeto=3,
            artefatos=[
                Artefato(
                    id="art-board",
                    tipo=TipoArtefato.BOARD,
                    conteudo="[✓] Task 1",
                    dia_projeto=3,
                )
            ],
            score=DeliveryScore(dados_suficientes=True, valor=71),
        )

        alerta = _detectar_desvio_limiar(update)

        assert alerta is None

    def test_gap_pp_criterio_spec(self):
        """gap_pp para score=63, dia=6 deve ser ~22.2 (criterio SPEC)"""
        update = Update(
            id="upd-test",
            numero=1,
            dia_projeto=6,
            artefatos=[
                Artefato(
                    id="art-board",
                    tipo=TipoArtefato.BOARD,
                    conteudo="[✓] Task 1",
                    dia_projeto=6,
                )
            ],
            score=DeliveryScore(dados_suficientes=True, valor=63),
        )

        alerta = _detectar_desvio_limiar(update)

        assert alerta is not None
        expected_gap = 60.0 * (1 - 63 / 100)
        assert abs(alerta.gap_pp - expected_gap) < 0.1

    def test_score_none_retorna_none(self):
        """Score=None → Nenhum Alerta"""
        update = Update(
            id="upd-test",
            numero=1,
            dia_projeto=3,
            artefatos=[],
            score=None,
        )

        alerta = _detectar_desvio_limiar(update)

        assert alerta is None

    def test_dados_insuficientes_retorna_none(self):
        """dados_suficientes=False → Nenhum Alerta"""
        update = Update(
            id="upd-test",
            numero=1,
            dia_projeto=3,
            artefatos=[],
            score=DeliveryScore(dados_suficientes=False, valor=None),
        )

        alerta = _detectar_desvio_limiar(update)

        assert alerta is None

    def test_sem_artefatos_validos_retorna_none(self):
        """Update com dados_suficientes=True mas sem artefatos válidos → Nenhum Alerta"""
        update = Update(
            id="upd-test",
            numero=1,
            dia_projeto=3,
            artefatos=[
                Artefato(
                    id="art-bad",
                    tipo=TipoArtefato.BOARD,
                    conteudo="",
                    dia_projeto=3,
                    valido=False,
                )
            ],
            score=DeliveryScore(dados_suficientes=True, valor=50),
        )

        alerta = _detectar_desvio_limiar(update)

        assert alerta is None


class TestDetectarDeterioracaoConsistente:
    """Testes do detector DETERIORACAO_CONSISTENTE"""

    def test_dois_drops_consecutivos_sem_cruzar_limiar(self):
        """Scores [90, 80, 75] → 2 drops sem cruzar limiar → Alerta"""
        update_1 = Update(
            id="upd-1",
            numero=1,
            dia_projeto=1,
            artefatos=[
                Artefato(id="art-1", tipo=TipoArtefato.BOARD, conteudo="[✓]", dia_projeto=1)
            ],
            score=DeliveryScore(dados_suficientes=True, valor=90),
        )

        update_2 = Update(
            id="upd-2",
            numero=2,
            dia_projeto=5,
            artefatos=[
                Artefato(id="art-2", tipo=TipoArtefato.BOARD, conteudo="[✓]", dia_projeto=5)
            ],
            score=DeliveryScore(dados_suficientes=True, valor=80),
        )

        update_3 = Update(
            id="upd-3",
            numero=3,
            dia_projeto=9,
            artefatos=[
                Artefato(id="art-3", tipo=TipoArtefato.BOARD, conteudo="[~]", dia_projeto=9)
            ],
            score=DeliveryScore(dados_suficientes=True, valor=75),
        )

        alerta = _detectar_deterioracao_consistente(update_3, [update_1, update_2])

        assert alerta is not None
        assert alerta.categoria == CategoriaAlerta.DETERIORACAO_CONSISTENTE
        assert alerta.nivel_confianca == NivelConfianca.MEDIO
        assert alerta.gap_pp is None

    def test_apenas_um_drop_nao_dispara(self):
        """Apenas 1 anterior com score → Nenhum Alerta"""
        update_1 = Update(
            id="upd-1",
            numero=1,
            dia_projeto=1,
            artefatos=[
                Artefato(id="art-1", tipo=TipoArtefato.BOARD, conteudo="[✓]", dia_projeto=1)
            ],
            score=DeliveryScore(dados_suficientes=True, valor=90),
        )

        update_2 = Update(
            id="upd-2",
            numero=2,
            dia_projeto=5,
            artefatos=[
                Artefato(id="art-2", tipo=TipoArtefato.BOARD, conteudo="[~]", dia_projeto=5)
            ],
            score=DeliveryScore(dados_suficientes=True, valor=80),
        )

        alerta = _detectar_deterioracao_consistente(update_2, [update_1])

        assert alerta is None

    def test_drops_mas_um_cruza_limiar_nao_dispara(self):
        """Scores [90, 80, 60] — score final cruza limiar → _detectar_desvio_limiar toma conta"""
        update_1 = Update(
            id="upd-1",
            numero=1,
            dia_projeto=1,
            artefatos=[
                Artefato(id="art-1", tipo=TipoArtefato.BOARD, conteudo="[✓]", dia_projeto=1)
            ],
            score=DeliveryScore(dados_suficientes=True, valor=90),
        )

        update_2 = Update(
            id="upd-2",
            numero=2,
            dia_projeto=5,
            artefatos=[
                Artefato(id="art-2", tipo=TipoArtefato.BOARD, conteudo="[~]", dia_projeto=5)
            ],
            score=DeliveryScore(dados_suficientes=True, valor=80),
        )

        update_3 = Update(
            id="upd-3",
            numero=3,
            dia_projeto=9,
            artefatos=[
                Artefato(id="art-3", tipo=TipoArtefato.BOARD, conteudo="[✗]", dia_projeto=9)
            ],
            score=DeliveryScore(dados_suficientes=True, valor=60),
        )

        alerta = _detectar_deterioracao_consistente(update_3, [update_1, update_2])

        assert alerta is None

    def test_menos_de_dois_anteriores_com_score_nao_dispara(self):
        """Lista vazia de anteriores → Nenhum Alerta"""
        update = Update(
            id="upd-test",
            numero=1,
            dia_projeto=3,
            artefatos=[
                Artefato(id="art-test", tipo=TipoArtefato.BOARD, conteudo="[~]", dia_projeto=3)
            ],
            score=DeliveryScore(dados_suficientes=True, valor=75),
        )

        alerta = _detectar_deterioracao_consistente(update, [])

        assert alerta is None


class TestDetectarBloqueioLinguistico:
    """Testes do detector BLOQUEIO_LINGUISTICO"""

    def test_aguardando_aprovacao_match(self):
        """Padrão 'aguardando aprovação' deve casar"""
        update = Update(
            id="upd-test",
            numero=1,
            dia_projeto=3,
            artefatos=[
                Artefato(
                    id="art-trans",
                    tipo=TipoArtefato.TRANSCRICAO,
                    conteudo="Ainda aguardando aprovação do departamento",
                    dia_projeto=3,
                )
            ],
        )

        alerta = _detectar_bloqueio_linguistico(update)

        assert alerta is not None
        assert alerta.categoria == CategoriaAlerta.BLOQUEIO_LINGUISTICO
        assert "aguardando aprovação" in alerta.trecho_fonte.lower()

    def test_bloqueado_match(self):
        """Padrão 'bloqueado' deve casar"""
        update = Update(
            id="upd-test",
            numero=1,
            dia_projeto=3,
            artefatos=[
                Artefato(
                    id="art-trans",
                    tipo=TipoArtefato.TRANSCRICAO,
                    conteudo="Desenvolvimento está completamente bloqueado",
                    dia_projeto=3,
                )
            ],
        )

        alerta = _detectar_bloqueio_linguistico(update)

        assert alerta is not None
        assert alerta.categoria == CategoriaAlerta.BLOQUEIO_LINGUISTICO
        assert "bloqueado" in alerta.trecho_fonte.lower()

    def test_sem_sinal_bloqueio_retorna_none(self):
        """Transcrição sem nenhum padrão → Nenhum Alerta"""
        update = Update(
            id="upd-test",
            numero=1,
            dia_projeto=3,
            artefatos=[
                Artefato(
                    id="art-trans",
                    tipo=TipoArtefato.TRANSCRICAO,
                    conteudo="Tudo está progredindo normalmente",
                    dia_projeto=3,
                )
            ],
        )

        alerta = _detectar_bloqueio_linguistico(update)

        assert alerta is None

    def test_somente_board_sem_transcricao_nao_dispara(self):
        """Board com bloqueio mas sem TRANSCRICAO → Nenhum Alerta"""
        update = Update(
            id="upd-test",
            numero=1,
            dia_projeto=3,
            artefatos=[
                Artefato(
                    id="art-board",
                    tipo=TipoArtefato.BOARD,
                    conteudo="[✗] Bloqueado aguardando aprovação",
                    dia_projeto=3,
                )
            ],
        )

        alerta = _detectar_bloqueio_linguistico(update)

        assert alerta is None

    def test_case_insensitive_match(self):
        """Padrões devem casar independente de maiúsculas/minúsculas"""
        update = Update(
            id="upd-test",
            numero=1,
            dia_projeto=3,
            artefatos=[
                Artefato(
                    id="art-trans",
                    tipo=TipoArtefato.TRANSCRICAO,
                    conteudo="Não temos ACESSO ao sistema",
                    dia_projeto=3,
                )
            ],
        )

        alerta = _detectar_bloqueio_linguistico(update)

        assert alerta is not None

    def test_nao_pode_avancar_match(self):
        """Padrão 'não pode avançar' deve casar"""
        update = Update(
            id="upd-test",
            numero=1,
            dia_projeto=3,
            artefatos=[
                Artefato(
                    id="art-trans",
                    tipo=TipoArtefato.TRANSCRICAO,
                    conteudo="Sem o acesso não pode avançar com o desenvolvimento",
                    dia_projeto=3,
                )
            ],
        )

        alerta = _detectar_bloqueio_linguistico(update)

        assert alerta is not None
        assert "não pode avançar" in alerta.trecho_fonte.lower()


class TestSeedRastreabilidade:
    """Testes usando o seed para verificar rastreabilidade conforme critério SPEC"""

    def test_seed_u2_desvio_limiar_rastreavel(self):
        """Seed U2 deve gerar alerta DESVIO_LIMIAR rastreável ao artefato de board"""
        projeto = carregar_projeto_seed()
        update_1 = projeto.updates[0]
        update_2 = projeto.updates[1]

        resultado_u1 = ingerir_artefatos(update_1.artefatos)
        score_u1 = calcular_delivery_score(resultado_u1, dia=update_1.dia_projeto)
        update_1.score = score_u1

        resultado_u2 = ingerir_artefatos(update_2.artefatos)
        score_u2 = calcular_delivery_score(resultado_u2, dia=update_2.dia_projeto)
        update_2.score = score_u2

        alerta_desvio_esperado = None
        alertas = analisar_alertas(update_2, [update_1])
        for alerta in alertas:
            if alerta.categoria == CategoriaAlerta.DESVIO_LIMIAR:
                alerta_desvio_esperado = alerta
                break

        assert alerta_desvio_esperado is not None
        assert alerta_desvio_esperado.artefato_fonte_id == "art-u2-board"

    def test_seed_u2_bloqueio_rastreavel(self):
        """Seed U2 deve gerar alerta BLOQUEIO_LINGUISTICO com trecho 'aguardando' rastreável"""
        projeto = carregar_projeto_seed()
        update_1 = projeto.updates[0]
        update_2 = projeto.updates[1]

        resultado_u1 = ingerir_artefatos(update_1.artefatos)
        score_u1 = calcular_delivery_score(resultado_u1, dia=update_1.dia_projeto)
        update_1.score = score_u1

        resultado_u2 = ingerir_artefatos(update_2.artefatos)
        score_u2 = calcular_delivery_score(resultado_u2, dia=update_2.dia_projeto)
        update_2.score = score_u2

        alerta_bloqueio_esperado = None
        alertas = analisar_alertas(update_2, [update_1])
        for alerta in alertas:
            if alerta.categoria == CategoriaAlerta.BLOQUEIO_LINGUISTICO:
                alerta_bloqueio_esperado = alerta
                break

        assert alerta_bloqueio_esperado is not None
        assert alerta_bloqueio_esperado.artefato_fonte_id == "art-u2-transcricao"
        assert "aguardando" in alerta_bloqueio_esperado.trecho_fonte.lower()
