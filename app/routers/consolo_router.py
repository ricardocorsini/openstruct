from fastapi import APIRouter, Body, HTTPException, status
from pydantic import BaseModel, Field
from app.services.dimensionamento.consolo.consolo_curto import ConsoloCurto

router = APIRouter(tags=["Dimensionamento - Consolos de Concreto Armado"])


class ConsoloCurtoInput(BaseModel):
    nome: str = Field(..., description="Identificação do consolo")
    bw: float = Field(..., description="Largura do consolo (cm)")
    h: float = Field(..., description="Altura total do consolo (cm)")
    d_linha: float = Field(..., description="Distância da armadura à face comprimida, d' (cm)")
    dist_a: float = Field(..., description="Distância a (cm)")
    vk: float = Field(..., description="Carga vertical característica Vk (kN)")
    hk: float = Field(..., description="Carga horizontal característica Hk (kN)")
    fck: float = Field(..., description="Resistência característica do concreto (MPa)")
    fywk: float = Field(..., description="Resistência característica do aço (MPa)")
    gama_c: float = Field(1.4, description="Fator parcial do concreto")
    gama_s: float = Field(1.15, description="Fator parcial do aço")
    gama_f: float = Field(1.4, description="Fator de majoração das ações")


class ConsoloCurtoResult(BaseModel):
    identificacao: str
    entradas: dict
    propriedades_calculo: dict
    geometria_biela: dict
    armaduras: dict
    verificacoes_finais: dict


class ErrorResponse(BaseModel):
    detail: str = Field(..., description="Descrição do erro ocorrido.")


@router.post(
    "/consolos/curto",
    summary="Dimensionamento de consolo curto (NBR 6118)",
    description=(
        "Executa o dimensionamento de consolo curto em concreto armado, "
        "retornando propriedades de cálculo, geometria da biela, armaduras "
        "e verificações finais.\n\n"
        "**Unidades de entrada:**\n"
        "- bw, h, d_linha, dist_a em cm\n"
        "- vk, hk em kN\n"
        "- fck, fywk em MPa"
    ),
    response_model=ConsoloCurtoResult,
    responses={
        400: {"model": ErrorResponse, "description": "Erro de validação ou parâmetros inconsistentes."},
        422: {"model": ErrorResponse, "description": "Erro de validação dos dados de entrada."},
        500: {"model": ErrorResponse, "description": "Erro interno durante o processamento."},
    },
)
def dimensionar_consolo_curto(
    data: ConsoloCurtoInput = Body(
        ...,
        example={
            "nome": "C1",
            "bw": 40,
            "h": 65,
            "d_linha": 5,
            "dist_a": 30,
            "vk": 571.42,
            "hk": 92.85,
            "fck": 40,
            "fywk": 500,
            "gama_c": 1.4,
            "gama_s": 1.15,
            "gama_f": 1.4,
        },
    )
):
    try:
        if any(v <= 0 for v in [data.bw, data.h, data.d_linha, data.dist_a, data.vk, data.fck, data.fywk]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Todos os parâmetros geométricos e resistentes devem ser positivos."
            )

        if data.h <= data.d_linha:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A altura total h deve ser maior que d_linha."
            )

        if any(v <= 0 for v in [data.gama_c, data.gama_s, data.gama_f]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Os coeficientes gama devem ser positivos."
            )

        consolo = ConsoloCurto(
            nome=data.nome,
            bw=data.bw,
            h=data.h,
            d_linha=data.d_linha,
            dist_a=data.dist_a,
            vk=data.vk,
            hk=data.hk,
            fck=data.fck,
            fywk=data.fywk,
            gama_c=data.gama_c,
            gama_s=data.gama_s,
            gama_f=data.gama_f,
        )

        return consolo.gerar_resultado()

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro inesperado ao executar o cálculo do consolo curto: {e}"
        )