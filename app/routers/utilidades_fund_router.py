import os
import base64
import uuid
from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import List
from app.services.utilidades.fundacoes.calc_molas_estaca import SoilAnalysisSystemAPI

router = APIRouter()
soil = SoilAnalysisSystemAPI()

# ---------------------------
# MODELOS
# ---------------------------

class ApoioEntrada(BaseModel):
    apoio: int
    prof: float
    diametro: float
    tipo_solo: str
    spt: int

    model_config = {
        "json_schema_extra": {
            "example": {
                "apoio": 1,
                "prof": 1.0,
                "diametro": 0.40,
                "tipo_solo": "Argila",
                "spt": 2
            }
        }
    }


class ApoiosRequest(BaseModel):
    apoios: List[ApoioEntrada]
    exportar_txt: bool = False

    model_config = {
        "json_schema_extra": {
            "example": {
                "exportar_txt": True,
                "apoios": [
                    {"apoio": 1, "prof": 1.0, "diametro": 0.40, "tipo_solo": "Argila", "spt": 2},
                    {"apoio": 2, "prof": 1.0, "diametro": 0.40, "tipo_solo": "Areia", "spt": 6},
                    {"apoio": 3, "prof": 2.0, "diametro": 0.40, "tipo_solo": "Areia", "spt": 9},
                    {"apoio": 4, "prof": 3.0, "diametro": 0.40, "tipo_solo": "Areia", "spt": 9}
                ]
            }
        }
    }


# ---------------------------
# EXEMPLOS DE RESPOSTAS
# ---------------------------

response_json_example = {
    "dados": [
        {
            "apoio": 1,
            "tipo_solo": "Argila",
            "spt": 2,
            "prof": 1.0,
            "area": 0.40,
            "m": 112.50,
            "kmola": 45.00
        }
    ],
    "txt_incluido": False
}

response_error_example = {
    "erro": "SPT 99 não encontrado para o solo 'Areia'"
}


# ---------------------------
# ROTA PRINCIPAL
# ---------------------------

@router.post(
    "/fundacoes/molas-estaca",
    tags=["Utilidades"],
    summary="Calcula kmola (tf/m) para apoios horizontais de estacas e gera relatório opcional em TXT",
    description="""
Esta rota calcula o coeficiente de mola horizontal (**kmola**) (tf/m) para cada apoio.

Você pode escolher:

### ✔ Retornar só JSON ("exportar_txt": false)
### ✔ Retornar só o arquivo TXT para download ("exportar_txt": true)

""",
    responses={
        200: {
            "description": "Cálculo realizado com sucesso",
            "content": {"application/json": {"example": response_json_example}}
        },
        400: {
            "description": "Erro de validação",
            "content": {"application/json": {"example": response_error_example}}
        },
    }
)
def gerar_txt(req: ApoiosRequest, background_tasks: BackgroundTasks):

    novos = []

    # ---------------------------
    # PROCESSA CÁLCULOS
    # ---------------------------
    for a in req.apoios:
        calc = soil.calcular(a.tipo_solo, a.spt, a.prof, a.diametro)

        if "erro" in calc:
            return JSONResponse(status_code=400, content={"erro": calc["erro"]})

        novos.append({
            "apoio": a.apoio,
            "tipo_solo": a.tipo_solo,
            "spt": a.spt,
            "prof": a.prof,
            "area": calc["area"],
            "m": calc["m"],
            "kmola": calc["kmola"],
        })

    # ---------------------------
    # SE NÃO FOR PARA EXPORTAR TXT → RETORNA JSON
    # ---------------------------
    if not req.exportar_txt:
        return {
            "dados": novos,
            "txt_incluido": False
        }

    # ---------------------------
    # SE EXPORTAR TXT → GERAR ARQUIVO TEMPORÁRIO
    # ---------------------------
    conteudo = soil.gerar_relatorio_txt(novos)

    tmp_dir = "app/tmp"
    os.makedirs(tmp_dir, exist_ok=True)

    filename = f"relatorio_solo_{uuid.uuid4().hex}.txt"
    filepath = os.path.join(tmp_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(conteudo)

    # Adiciona tarefa para deletar o arquivo após a resposta
    background_tasks.add_task(os.remove, filepath)

    # Retorna o arquivo para download (NÃO JSON)
    return FileResponse(
        filepath,
        media_type="text/plain",
        filename="relatorio_solo.txt",
        background=background_tasks
    )
