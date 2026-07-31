"""Rotas para análises de interação solo-estrutura."""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, HTTPException, status
from pydantic import BaseModel, Field

from app.services.interacao_solo_estrutura.estaca_pynite import (
    AnaliseEstacaPyNite,
    CargasTopo,
    DependenciaPyNiteAusente,
    ErroModeloEstaca,
    FalhaAnaliseEstaca,
    PropriedadesSecao,
)


router = APIRouter(tags=["Interação Solo-Estrutura - Estacas"])

EXEMPLO_REQUISICAO = {
    "comprimento_m": 6.0,
    "molas_horizontais_tf_m": [500.0, 750.0, 1000.0, 1250.0, 1500.0],
    "material": {
        "modulo_elasticidade_tf_m2": 3000000.0,
        "coeficiente_poisson": 0.20,
    },
    "secao": {"diametro_m": 0.40},
    "cargas_topo": {
        "horizontal_x_tf": 10.0,
        "momento_z_tf_m": 5.0,
        "axial_compressao_tf": 100.0,
    },
    "pontos_por_elemento": 6,
}


class MaterialEstacaInput(BaseModel):
    modulo_elasticidade_tf_m2: float = Field(
        ...,
        gt=0,
        description="Módulo de elasticidade longitudinal E (tf/m²).",
    )
    coeficiente_poisson: float = Field(
        0.20,
        gt=-1,
        lt=0.5,
        description="Coeficiente de Poisson.",
    )
    modulo_cisalhamento_tf_m2: Optional[float] = Field(
        None,
        gt=0,
        description=(
            "Módulo de cisalhamento G (tf/m²). Se omitido, será calculado "
            "por G = E/[2(1+nu)]."
        ),
    )


class SecaoEstacaInput(BaseModel):
    diametro_m: Optional[float] = Field(
        None,
        gt=0,
        description=(
            "Diâmetro de uma seção circular maciça (m). Use este campo sozinho "
            "ou informe as quatro propriedades geométricas diretamente."
        ),
    )
    area_m2: Optional[float] = Field(None, gt=0, description="Área A (m²).")
    inercia_y_m4: Optional[float] = Field(
        None, gt=0, description="Momento de inércia Iy (m⁴)."
    )
    inercia_z_m4: Optional[float] = Field(
        None, gt=0, description="Momento de inércia Iz (m⁴)."
    )
    constante_torcao_m4: Optional[float] = Field(
        None, gt=0, description="Constante de torção J (m⁴)."
    )


class CargasTopoInput(BaseModel):
    horizontal_x_tf: float = Field(
        0.0,
        description="Carga horizontal no topo; positiva no sentido global +X (tf).",
    )
    momento_z_tf_m: float = Field(
        0.0,
        description=(
            "Momento no topo; positivo em +MZ pela regra da mão direita (tf.m)."
        ),
    )
    axial_compressao_tf: float = Field(
        0.0,
        description=(
            "Carga axial no topo; valor positivo representa compressão e é "
            "aplicado no sentido global -Y (tf)."
        ),
    )


class AnaliseEstacaInput(BaseModel):
    comprimento_m: float = Field(..., gt=0, description="Comprimento da estaca (m).")
    molas_horizontais_tf_m: List[float] = Field(
        ...,
        description=(
            "Rigidezes das molas em DX, em tf/m, nas profundidades 1 m, 2 m, "
            "3 m etc. Não informe mola no topo nem na ponta rígida."
        ),
    )
    material: MaterialEstacaInput
    secao: SecaoEstacaInput
    cargas_topo: CargasTopoInput
    pontos_por_elemento: int = Field(
        6,
        ge=2,
        le=50,
        description="Quantidade de pontos retornados por trecho da estaca.",
    )


class PontoDiagramaResult(BaseModel):
    profundidade_m: float
    elemento: str
    x_local_m: float
    lado: str
    valor: float


class NoEstacaResult(BaseModel):
    no: str
    profundidade_m: float
    tipo: str
    rigidez_mola_x_tf_m: Optional[float]
    deslocamento_x_m: float
    deslocamento_y_m: float
    rotacao_z_rad: float
    reacao_x_tf: float
    reacao_y_tf: float
    momento_reacao_z_tf_m: float
    reacao_mola_x_tf: Optional[float]


class AnaliseEstacaResult(BaseModel):
    sistema_unidades: Dict[str, str]
    modelo: Dict[str, Any]
    propriedades: Dict[str, float]
    cargas_aplicadas: Dict[str, float]
    nos: List[NoEstacaResult]
    diagramas: Dict[str, List[PontoDiagramaResult]]
    resumo: Dict[str, Any]
    equilibrio: Dict[str, float]
    avisos: List[str]


class ErrorResponse(BaseModel):
    detail: str = Field(..., description="Descrição do erro ocorrido.")


def _resolver_secao(secao: SecaoEstacaInput) -> PropriedadesSecao:
    propriedades_diretas = (
        secao.area_m2,
        secao.inercia_y_m4,
        secao.inercia_z_m4,
        secao.constante_torcao_m4,
    )
    informou_alguma_direta = any(valor is not None for valor in propriedades_diretas)
    informou_todas_diretas = all(valor is not None for valor in propriedades_diretas)

    if secao.diametro_m is not None and informou_alguma_direta:
        raise ErroModeloEstaca(
            "Informe somente diametro_m ou as quatro propriedades geométricas "
            "diretas; não use as duas formas ao mesmo tempo."
        )

    if secao.diametro_m is not None:
        diametro = secao.diametro_m
        area = math.pi * diametro**2 / 4
        inercia = math.pi * diametro**4 / 64
        constante_torcao = math.pi * diametro**4 / 32
        return PropriedadesSecao(
            area_m2=area,
            inercia_y_m4=inercia,
            inercia_z_m4=inercia,
            constante_torcao_m4=constante_torcao,
        )

    if not informou_todas_diretas:
        raise ErroModeloEstaca(
            "Informe diametro_m para uma seção circular maciça ou informe "
            "area_m2, inercia_y_m4, inercia_z_m4 e constante_torcao_m4."
        )

    return PropriedadesSecao(
        area_m2=secao.area_m2,
        inercia_y_m4=secao.inercia_y_m4,
        inercia_z_m4=secao.inercia_z_m4,
        constante_torcao_m4=secao.constante_torcao_m4,
    )


@router.post(
    "/estacas/analise-linear",
    summary="Análise linear ISE de uma estaca sobre molas horizontais",
    description=(
        "Monta e resolve no PyNite uma estaca no plano XY, discretizada a cada "
        "metro. O topo é livre e recebe FX, MZ e força axial de compressão. "
        "As molas atuam em DX nos nós internos e a ponta possui translações X "
        "e Y impedidas, com rotação Z livre. Retorna esforços, deslocamentos, "
        "reações e pontos prontos para os diagramas do frontend.\\n\\n"
        "**Unidades:** m, tf, tf.m, tf/m e tf/m²."
    ),
    response_model=AnaliseEstacaResult,
    responses={
        400: {
            "model": ErrorResponse,
            "description": "Parâmetros incompatíveis com o modelo.",
        },
        422: {
            "model": ErrorResponse,
            "description": "Erro de validação dos dados ou falha da análise.",
        },
        503: {
            "model": ErrorResponse,
            "description": "Dependência PyNiteFEA não instalada.",
        },
        500: {
            "model": ErrorResponse,
            "description": "Erro interno durante o processamento.",
        },
    },
)
def analisar_estaca_ise(
    data: AnaliseEstacaInput = Body(..., examples=[EXEMPLO_REQUISICAO]),
) -> Dict[str, Any]:
    try:
        secao = _resolver_secao(data.secao)
        servico = AnaliseEstacaPyNite(
            comprimento_m=data.comprimento_m,
            molas_horizontais_tf_m=data.molas_horizontais_tf_m,
            cargas=CargasTopo(
                horizontal_x_tf=data.cargas_topo.horizontal_x_tf,
                momento_z_tf_m=data.cargas_topo.momento_z_tf_m,
                axial_compressao_tf=data.cargas_topo.axial_compressao_tf,
            ),
            modulo_elasticidade_tf_m2=(
                data.material.modulo_elasticidade_tf_m2
            ),
            coeficiente_poisson=data.material.coeficiente_poisson,
            modulo_cisalhamento_tf_m2=(
                data.material.modulo_cisalhamento_tf_m2
            ),
            secao=secao,
            pontos_por_elemento=data.pontos_por_elemento,
        )
        return servico.analisar()
    except ErroModeloEstaca as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except DependenciaPyNiteAusente as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except FalhaAnaliseEstaca as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro inesperado ao analisar a estaca: {exc}",
        ) from exc
