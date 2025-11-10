from fastapi import APIRouter, Body, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import List
import os
from app.services.desenho.estacas.desenho_service import estacas_cargas

router = APIRouter(tags=["Desenho"])

class Estaca(BaseModel):
    coord_X: float = Field(..., description="Coordenada X da estaca (m)")
    coord_Y: float = Field(..., description="Coordenada Y da estaca (m)")
    diametro: float = Field(..., description="Diâmetro da estaca (m)")
    texto: str = Field(..., description="Nome e carga (ex: 'E1\n350 kN')")


@router.post(
    "/estacas/cargas",
    summary="Desenho de estacas com cargas",
    description=(
        "Este endpoint cria automaticamente um arquivo DXF contendo a planta de estacas, "
        "com representação gráfica (círculo + cruz central) e o texto com nome e carga acima de cada estaca (conforme exemplo).\n\n"
        "**Unidades:** todas as dimensões devem ser informadas em **metros (m)**.\n\n"
        "**Textos adicionais:** é permitido incluir mais informações além da carga. "
        "Basta separar por '\\n' para que cada linha apareça em uma nova linha no desenho.\n\n"
        "Exemplo de campo `texto`:\n"
        "```\n"
        "E1\\n350 kN\\nCA -2.00\n"
        "```\n"
        "Resultado: 3 linhas empilhadas sobre a estaca."
    ),
    response_description="Arquivo DXF gerado e baixado automaticamente.",
)
def desenho_estacas_cargas(
    background_tasks: BackgroundTasks,
    estacas: List[Estaca] = Body(
        ...,
        example=[
            {"coord_X": -1, "coord_Y": 1, "diametro": 0.8, "texto": "E1\n350 kN"},
            {"coord_X": 1, "coord_Y": 1, "diametro": 0.8, "texto": "E2\n450 kN"},
            {"coord_X": -1, "coord_Y": -1, "diametro": 0.8, "texto": "E3\n250 kN"},
            {"coord_X": 1, "coord_Y": -1, "diametro": 0.8, "texto": "E4\n456 kN"},
        ],
    ),
):
    caminho_arquivo = estacas_cargas([e.dict() for e in estacas])

    # Apagar o arquivo após o envio. 
    background_tasks.add_task(os.remove, caminho_arquivo)

    return FileResponse(
        caminho_arquivo,
        filename=os.path.basename(caminho_arquivo),
        media_type="application/dxf",
    )
