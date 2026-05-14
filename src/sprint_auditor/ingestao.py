from sprint_auditor.modelos import Artefato, ResultadoIngestao


def ingerir_artefatos(artefatos: list[Artefato]) -> ResultadoIngestao:
    """Valida e normaliza artefatos.

    Para cada artefato:
    - Conteúdo vazio ou só whitespace → valido=False, erro_ingestao preenchido
    - Conteúdo válido → cópia com conteudo.strip()

    Nunca levanta exceção — erros são registrados no próprio Artefato.
    O input não é mutado.
    """
    artefatos_validos = []
    artefatos_invalidos = []

    for artefato in artefatos:
        if not artefato.conteudo or not artefato.conteudo.strip():
            artefatos_invalidos.append(
                artefato.model_copy(
                    update={
                        "valido": False,
                        "erro_ingestao": "Conteúdo vazio ou ausente",
                    }
                )
            )
        else:
            artefatos_validos.append(
                artefato.model_copy(
                    update={"conteudo": artefato.conteudo.strip()}
                )
            )

    return ResultadoIngestao.model_construct(
        artefatos_validos=artefatos_validos,
        artefatos_invalidos=artefatos_invalidos,
    )
