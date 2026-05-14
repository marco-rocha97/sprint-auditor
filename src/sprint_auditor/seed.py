from datetime import datetime, timezone

from sprint_auditor.modelos import (
    Artefato,
    Projeto,
    TipoArtefato,
    Update,
)


def carregar_projeto_seed() -> Projeto:
    """Retorna o projeto sintético 'Alpha Corp' com 4 updates: desvio, bloqueio e recovery parcial."""

    artefato_u1_board = Artefato(
        id="art-u1-board",
        tipo=TipoArtefato.BOARD,
        conteudo=(
            "Discovery: [✓] Kickoff realizado, [✓] Escopo definido, "
            "[~] Validação SAP em progresso"
        ),
        dia_projeto=3,
    )

    artefato_u1_transcricao = Artefato(
        id="art-u1-transcricao",
        tipo=TipoArtefato.TRANSCRICAO,
        conteudo=(
            "Equipe concluiu o kickoff com sucesso. Escopo está alinhado. "
            "Temos um pequeno atraso na validação SAP mas está dentro da "
            "tolerância para o cronograma."
        ),
        dia_projeto=3,
    )

    update_1 = Update(
        id="upd-1",
        numero=1,
        dia_projeto=3,
        artefatos=[artefato_u1_board, artefato_u1_transcricao],
    )

    artefato_u2_board = Artefato(
        id="art-u2-board",
        tipo=TipoArtefato.BOARD,
        conteudo=(
            "Configuração: [✗] Acesso ao ambiente SAP, [✗] Setup do agente "
            "IA, [✗] Integração com CRM"
        ),
        dia_projeto=6,
    )

    artefato_u2_transcricao = Artefato(
        id="art-u2-transcricao",
        tipo=TipoArtefato.TRANSCRICAO,
        conteudo=(
            "Ainda não temos acesso ao SAP, aguardando aprovação do "
            "departamento de TI da Alpha Corp. Isso está segurando tudo. "
            "O setup do agente não pode avançar sem o ambiente configurado."
        ),
        dia_projeto=6,
    )

    update_2 = Update(
        id="upd-2",
        numero=2,
        dia_projeto=6,
        artefatos=[artefato_u2_board, artefato_u2_transcricao],
    )

    artefato_u3_board = Artefato(
        id="art-u3-board",
        tipo=TipoArtefato.BOARD,
        conteudo=(
            "Desenvolvimento: [✗] Agente IA bloqueado, [✗] Testes SAP "
            "falhos, [✗] Deploy pausado"
        ),
        dia_projeto=9,
    )

    artefato_u3_transcricao = Artefato(
        id="art-u3-transcricao",
        tipo=TipoArtefato.TRANSCRICAO,
        conteudo=(
            "Desenvolvimento está completamente bloqueado. O ambiente SAP "
            "tem falhas de conectividade. Sem acesso, não conseguimos testar "
            "a integração."
        ),
        dia_projeto=9,
    )

    update_3 = Update(
        id="upd-3",
        numero=3,
        dia_projeto=9,
        artefatos=[artefato_u3_board, artefato_u3_transcricao],
    )

    artefato_u4_board = Artefato(
        id="art-u4-board",
        tipo=TipoArtefato.BOARD,
        conteudo=(
            "Desenvolvimento: [✓] Acesso ao ambiente SAP liberado, "
            "[~] Setup do agente IA em progresso, [✗] Integração com CRM bloqueada"
        ),
        dia_projeto=12,
    )

    artefato_u4_transcricao = Artefato(
        id="art-u4-transcricao",
        tipo=TipoArtefato.TRANSCRICAO,
        conteudo=(
            "O acesso SAP foi liberado na quarta-feira. O agente IA está sendo "
            "configurado mas com atraso em relação ao cronograma original. "
            "A integração com CRM ainda está pendente — estamos correndo contra o prazo."
        ),
        dia_projeto=12,
    )

    update_4 = Update(
        id="upd-4",
        numero=4,
        dia_projeto=12,
        artefatos=[artefato_u4_board, artefato_u4_transcricao],
    )

    projeto = Projeto(
        id="proj-alpha-001",
        nome="Onboarding Alpha Corp",
        data_kickoff=datetime(2026, 4, 28, 9, 0, 0, tzinfo=timezone.utc),
        updates=[update_1, update_2, update_3, update_4],
    )

    return projeto
