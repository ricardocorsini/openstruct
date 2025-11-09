from fastapi import APIRouter, Body
from pydantic import BaseModel, Field
from typing import List
from app.services.desenho.desenho_service import gerar_desenho_estacas

router = APIRouter(tags=["Desenho"])


# ===============================
# Modelo de dados
# ===============================
class Estaca(BaseModel):
    coord_X: float = Field(..., description="Coordenada X da estaca (m)")
    coord_Y: float = Field(..., description="Coordenada Y da estaca (m)")
    diametro: float = Field(..., description="Diâmetro da estaca (m)")
    texto: str = Field(..., description="Nome e carga (ex: 'E1\\n350 kN')")


# ===============================
# Endpoint com exemplo completo
# ===============================
@router.post(
    "/estacas/cargas",
    summary="Gerar desenho DXF com estacas e cargas",
    description=(
        "Gera um arquivo DXF contendo a planta de estacas com as respectivas cargas. "
        "O desenho inclui círculos, eixos, textos e legenda padronizada."
    ),
    response_description="Mensagem de sucesso e nome do arquivo DXF gerado",
)
def desenho_estacas_cargas(
    estacas: List[Estaca] = Body(
        ...,
        example=[
            {"coord_X": -1, "coord_Y": 1, "diametro": 0.8, "texto": "E1\\n350 kN"},
            {"coord_X": 1, "coord_Y": 1, "diametro": 0.8, "texto": "E2\\n450 kN"},
            {"coord_X": -1, "coord_Y": -1, "diametro": 0.8, "texto": "E3\\n250 kN"},
            {"coord_X": 1, "coord_Y": -1, "diametro": 0.8, "texto": "E4\\n456 kN"},
        ],
    ),
):
    """
    Gera e salva um arquivo DXF com base nas estacas enviadas.
    """
    nome_arquivo = gerar_desenho_estacas([e.dict() for e in estacas])
    return {
        "status": "ok",
        "mensagem": f"Desenho gerado com sucesso: {nome_arquivo}"
    }
