import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, HTTPException, status
from pydantic import BaseModel, Field

from app.services.dimensionamento.vigas_concreto.dim_cis import Beam
from app.services.dimensionamento.vigas_concreto.dim_flexao import (
    FlexureDesignError,
    dimensionar_viga_retangular_flexao,
)


logger = logging.getLogger(__name__)
router = APIRouter(tags=["Dimensionamento - Vigas de Concreto Armado"])


# ==========================================================
# MODELOS DE ENTRADA E SAÍDA - CISALHAMENTO
# ==========================================================
class BeamInput(BaseModel):
    """Modelo de entrada para dimensionamento ao cisalhamento."""

    name: str = Field(..., description="Identificação da viga")
    bw: float = Field(..., description="Largura da viga (cm)")
    h: float = Field(..., description="Altura total da viga (cm)")
    Vk: float = Field(..., description="Esforço cortante característico (kN)")
    gama_c: float = Field(1.4, description="Fator de minoração do fck")
    gama_c2: float = Field(1.4, description="Fator de majoração do Vk")
    fywk: float = Field(..., description="Resistência característica do aço (MPa)")
    gama_s: float = Field(1.15, description="Fator de minoração do aço")
    fck: float = Field(..., description="Resistência característica do concreto (MPa)")
    stirrup_leg: int = Field(
        ...,
        alias="stirrupLeg",
        description="Número de ramos do estribo (2, 4 etc.)",
    )
    considerar_flexocompressao: bool = Field(
        False,
        alias="considerarFlexocompressao",
        description=(
            "Quando verdadeiro, corrige a contribuição do concreto Vc para "
            "flexocompressão conforme Vc = Vc0(1 + M0/MSd,max), limitado a 2Vc0."
        ),
    )
    N0: Optional[float] = Field(
        None,
        ge=0,
        description=(
            "Força normal de compressão concomitante com VSd, em kN, usada para "
            "determinar M0 com gamma_f = 1,0. Informar como módulo positivo."
        ),
    )
    MSd_max: Optional[float] = Field(
        None,
        gt=0,
        alias="MSdMax",
        description=(
            "Valor absoluto do momento fletor de cálculo máximo no trecho analisado, em kN.m."
        ),
    )

    class Config:
        allow_population_by_field_name = True


class BeamResult(BaseModel):
    """Resposta do dimensionamento ao cisalhamento."""

    viga: str = Field(..., description="Identificação da viga analisada.")
    entrada: Dict[str, Any] = Field(..., description="Dados de entrada utilizados.")
    resultados: Dict[str, Any] = Field(..., description="Resultados do dimensionamento.")


# ==========================================================
# MODELOS DE ENTRADA E SAÍDA - FLEXÃO
# ==========================================================
class BeamFlexureInput(BaseModel):
    """Entrada para uma seção retangular sob flexão simples no ELU."""

    name: str = Field(..., min_length=1, description="Identificação da viga.")
    bw_cm: float = Field(..., gt=0, description="Largura da seção retangular, em cm.")
    h_cm: float = Field(..., gt=0, description="Altura total da seção, em cm.")
    momento_sd_kn_m: float = Field(
        ...,
        gt=0,
        description=(
            "Valor absoluto do momento fletor de cálculo Msd, já majorado, em kN.m."
        ),
    )
    fck_mpa: float = Field(
        ...,
        ge=20,
        le=90,
        description="Resistência característica à compressão do concreto, em MPa.",
    )
    fyk_mpa: float = Field(
        500.0,
        gt=0,
        description="Resistência característica ao escoamento do aço, em MPa.",
    )
    gamma_c: float = Field(1.4, gt=0, description="Coeficiente parcial do concreto.")
    gamma_s: float = Field(1.15, gt=0, description="Coeficiente parcial do aço.")
    es_mpa: float = Field(
        210000.0,
        gt=0,
        description="Módulo de elasticidade do aço, em MPa.",
    )
    beta_redistribuicao: float = Field(
        1.0,
        ge=0.75,
        le=1.0,
        description="Coeficiente de redistribuição de momentos; use 1,0 quando não houver.",
    )
    cobrimento_cm: float = Field(
        3.0,
        gt=0,
        description="Cobrimento nominal, em cm, usado para estimar d e d'.",
    )
    diametro_estribo_mm: float = Field(
        5.0,
        gt=0,
        description="Diâmetro do estribo, em mm.",
    )
    diametro_barra_tracao_mm: float = Field(
        16.0,
        gt=0,
        description="Diâmetro estimado das barras tracionadas, em mm.",
    )
    diametro_barra_compressao_mm: Optional[float] = Field(
        None,
        gt=0,
        description=(
            "Diâmetro estimado das barras comprimidas, em mm; quando omitido, "
            "usa o diâmetro das barras tracionadas."
        ),
    )
    d_cm: Optional[float] = Field(
        None,
        gt=0,
        description="Altura útil real, em cm. Quando informada, substitui a estimativa.",
    )
    d_linha_cm: Optional[float] = Field(
        None,
        gt=0,
        description=(
            "Distância da borda comprimida ao centro da armadura comprimida, em cm. "
            "Quando informada, substitui a estimativa."
        ),
    )
    considerar_armadura_minima: bool = Field(
        True,
        description="Se verdadeiro, a armadura tracionada adotada respeita a mínima.",
    )

    class Config:
        schema_extra = {
            "example": {
                "name": "V1",
                "bw_cm": 20.0,
                "h_cm": 50.0,
                "momento_sd_kn_m": 120.0,
                "fck_mpa": 30.0,
                "fyk_mpa": 500.0,
                "gamma_c": 1.4,
                "gamma_s": 1.15,
                "beta_redistribuicao": 1.0,
                "cobrimento_cm": 3.0,
                "diametro_estribo_mm": 5.0,
                "diametro_barra_tracao_mm": 16.0,
                "considerar_armadura_minima": True,
            }
        }


class BeamFlexureResult(BaseModel):
    """Resposta consolidada do dimensionamento à flexão."""

    viga: str = Field(..., description="Identificação da viga analisada.")
    entrada: Dict[str, Any] = Field(..., description="Dados de entrada efetivamente recebidos.")
    resultados: Dict[str, Any] = Field(
        ...,
        description=(
            "Materiais, geometria, linha neutra, armaduras, deformações, "
            "verificações e avisos."
        ),
    )


class ErrorResponse(BaseModel):
    """Modelo de resposta para erros."""

    detail: str = Field(..., description="Descrição do erro ocorrido.")


# ==========================================================
# ENDPOINT - CISALHAMENTO
# ==========================================================
@router.post(
    "/vigas/cisalhamento",
    summary="Dimensionamento ao esforço cortante - Modelo I",
    description=(
        "Executa o dimensionamento de elementos retangulares de concreto armado ao "
        "esforço cortante pelo Modelo I. Por padrão, utiliza Vc = Vc0. Opcionalmente, "
        "pode considerar flexocompressão, calculando M0 = N0.h/6 para a seção retangular "
        "e Vc = Vc0(1 + M0/MSd,max), limitado a 2Vc0.\n\n"
        "**Unidades:** bw e h em cm; Vk e N0 em kN; MSd,max em kN.m; "
        "fck e fywk em MPa. Para N0, a tensão normal deve ser avaliada com gamma_f = 1,0."
    ),
    response_model=BeamResult,
    responses={
        400: {"model": ErrorResponse, "description": "Parâmetros inconsistentes."},
        422: {"model": ErrorResponse, "description": "Erro de validação do JSON."},
        500: {"model": ErrorResponse, "description": "Erro interno."},
    },
)
def dimensionar_viga_cisalhamento(
    data: BeamInput = Body(
        ...,
        example={
            "name": "V1",
            "bw": 14,
            "h": 45,
            "Vk": 120,
            "gama_c": 1.4,
            "gama_c2": 1.4,
            "fywk": 500,
            "gama_s": 1.15,
            "fck": 30,
            "stirrupLeg": 2,
            "considerarFlexocompressao": False,
        },
    ),
):
    """Realiza o cálculo de cisalhamento para vigas de concreto armado."""

    try:
        if any(v <= 0 for v in [data.bw, data.h, data.Vk, data.fck, data.fywk]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Todos os parâmetros geométricos e resistentes devem ser positivos.",
            )

        if data.considerar_flexocompressao:
            if data.N0 is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Para considerar flexocompressão, informe N0 em kN "
                        "(força normal concomitante com VSd, com gamma_f = 1,0)."
                    ),
                )

            if data.MSd_max is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Para considerar flexocompressão, informe MSdMax em kN.m.",
                )

        beam = Beam(
            name=data.name,
            bw=data.bw,
            h=data.h,
            Vk=data.Vk,
            gama_c=data.gama_c,
            gama_c2=data.gama_c2,
            fywk=data.fywk,
            gama_s=data.gama_s,
            fck=data.fck,
            stirrup_leg=data.stirrup_leg,
            considerar_flexocompressao=data.considerar_flexocompressao,
            N0=data.N0,
            MSd_max=data.MSd_max,
        )
        return {
            "viga": data.name,
            "entrada": data.dict(),
            "resultados": beam.results_dim_cis(),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Erro inesperado no dimensionamento ao cisalhamento")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro inesperado ao executar o cálculo de cisalhamento.",
        ) from exc


# ==========================================================
# ENDPOINT - FLEXÃO
# ==========================================================
@router.post(
    "/vigas/flexao",
    summary="Dimensionamento à flexão de viga retangular",
    description=(
        "Dimensiona, no ELU, uma seção retangular de concreto armado submetida à "
        "flexão simples. O momento de entrada é **Msd**, já majorado. A rotina "
        "calcula armadura simples ou dupla, armadura mínima, posição da linha neutra, "
        "deformações e tensões no aço.\n\n"
        "**Unidades:** geometria em cm; bitolas em mm; resistências em MPa; "
        "momento em kN.m.\n\n"
        "**Referência indicada:** ABNT NBR 6118:2026. O resultado não substitui a "
        "verificação e o detalhamento pelo engenheiro responsável."
    ),
    response_model=BeamFlexureResult,
    response_model_exclude_none=True,
    responses={
        400: {
            "model": ErrorResponse,
            "description": "Geometria inválida ou seção inviável para as hipóteses adotadas.",
        },
        422: {
            "model": ErrorResponse,
            "description": "Erro de validação do corpo da requisição.",
        },
        500: {"model": ErrorResponse, "description": "Erro interno não previsto."},
    },
)
def dimensionar_viga_flexao(data: BeamFlexureInput):
    """Dimensiona uma viga retangular à flexão simples."""

    try:
        entrada = data.dict()
        resultados = dimensionar_viga_retangular_flexao(**entrada)
        return {"viga": data.name, "entrada": entrada, "resultados": resultados}
    except FlexureDesignError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Erro inesperado no dimensionamento à flexão")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro inesperado ao executar o dimensionamento à flexão.",
        ) from exc
