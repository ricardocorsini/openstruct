from fastapi import APIRouter, Body, HTTPException, status
from pydantic import BaseModel, Field
from app.services.dimensionamento.vigas_concreto.dim_cis import Beam

router = APIRouter(tags=["Dimensionamento - Vigas de Concreto Armado"])

# ==========================================================
# MODELOS DE ENTRADA E SAÍDA
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
    stirrup_leg: int = Field(..., alias="stirrupLeg", description="Número de ramos do estribo (2, 4, etc.)")

    class Config:
        allow_population_by_field_name = True


class BeamResult(BaseModel):
    """Modelo de resposta bem-sucedida."""
    viga: str = Field(..., description="Identificação da viga analisada.")
    entrada: dict = Field(..., description="Dados de entrada utilizados no cálculo.")
    resultados: dict = Field(..., description="Resultados completos do dimensionamento.")


class ErrorResponse(BaseModel):
    """Modelo de resposta para erros."""
    detail: str = Field(..., description="Descrição do erro ocorrido.")


# ==========================================================
# ENDPOINT PRINCIPAL
# ==========================================================
@router.post(
    "/vigas/cisalhamento",
    summary="Dimensionamento ao esforço cortante (cisalhamento) - Modelo I (NBR 6118)",
    description=(
        "Autor: Ricardo Corsini | corsini.eng@gmail.com | github.com/ricardocorsini\n\n"
        "Testado por: S/N\n\n"
        "Melhorias adicionadas por: versão inicial.\n\n"
        "Executa o dimensionamento de vigas de concreto armado ao esforço cortante (cisalhamento), "
        "com base na NBR 6118/2024 (Modelo I).\n\n"
        "**Unidades de entrada:**\n"
        "- bw, h em cm\n"
        "- Vk em kN\n"
        "- fck, fywk em MPa"
    ),
    response_model=BeamResult,
    responses={
        400: {"model": ErrorResponse, "description": "Erro de validação ou parâmetros inconsistentes."},
        422: {"model": ErrorResponse, "description": "Erro de validação dos dados de entrada (Pydantic)."},
        500: {"model": ErrorResponse, "description": "Erro interno durante o processamento."},
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
        },
    ),
):
    """Realiza o cálculo completo de cisalhamento para vigas de concreto armado (Modelo I)."""

    try:

        # Validação dos parâmetros de entrada

        if any(v <= 0 for v in [data.bw, data.h, data.Vk, data.fck, data.fywk]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Todos os parâmetros geométricos e resistentes devem ser positivos."
            )

        # Aqui podem ser inseridas mais verificações, como por exemplo o intervalo aceitável para fck. 

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
        )

        results = beam.results_dim_cis()
        return {"viga": data.name, "entrada": data.dict(), "resultados": results}

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro inesperado ao executar o cálculo de cisalhamento: {e}"
        )
