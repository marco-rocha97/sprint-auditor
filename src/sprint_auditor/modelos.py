from enum import Enum
from typing import Optional

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


class Fase(str, Enum):
    DISCOVERY = "discovery"
    CONFIGURACAO = "configuracao"
    DESENVOLVIMENTO = "desenvolvimento"
    REVIEW = "review"


class TipoArtefato(str, Enum):
    TRANSCRICAO = "transcricao"
    BOARD = "board"


class NivelConfianca(str, Enum):
    ALTO = "alto"
    MEDIO = "medio"
    BAIXO = "baixo"


class CategoriaAlerta(str, Enum):
    DESVIO_LIMIAR = "desvio_limiar"
    DETERIORACAO_CONSISTENTE = "deterioracao_consistente"
    BLOQUEIO_LINGUISTICO = "bloqueio_linguistico"


class Artefato(BaseModel):
    id: str
    tipo: TipoArtefato
    conteudo: str
    dia_projeto: int = Field(ge=1, le=15)
    valido: bool = True
    erro_ingestao: Optional[str] = None


class DeliveryScore(BaseModel):
    dados_suficientes: bool
    valor: Optional[int] = Field(None, ge=0, le=100)
    scores_por_fase: dict[Fase, Optional[int]] = Field(default_factory=dict)

    @model_validator(mode='after')
    def validar_consistencia_dados(self) -> 'DeliveryScore':
        if self.dados_suficientes and self.valor is None:
            raise ValueError("dados_suficientes=True requer valor not None")
        if not self.dados_suficientes and self.valor is not None:
            raise ValueError("dados_suficientes=False requer valor=None")
        return self


class Alerta(BaseModel):
    categoria: CategoriaAlerta
    fase: Fase
    dia_projeto: int = Field(ge=1, le=15)
    gap_pp: Optional[float] = None
    causa_provavel: str
    nivel_confianca: NivelConfianca
    acao_sugerida: str
    artefato_fonte_id: str
    trecho_fonte: str


class Update(BaseModel):
    id: str
    numero: int = Field(ge=1)
    dia_projeto: int = Field(ge=1, le=15)
    artefatos: list[Artefato] = Field(default_factory=list)
    score: Optional[DeliveryScore] = None
    alertas: list[Alerta] = Field(default_factory=list)


class ResultadoIngestao(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, from_attributes=True)

    artefatos_validos: list[Artefato] = Field(default_factory=list)
    artefatos_invalidos: list[Artefato] = Field(default_factory=list)

    @property
    def tem_artefatos(self) -> bool:
        return len(self.artefatos_validos) > 0


class Projeto(BaseModel):
    id: str
    nome: str
    data_kickoff: AwareDatetime
    updates: list[Update] = Field(default_factory=list)
