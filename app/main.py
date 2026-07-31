from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import (
    consolo_router,
    desenho_router,
    dimensionamento_estaca_router,
    dim_conc_router,
    interacao_solo_estrutura_router,
    utilidades_fund_router,
)


app = FastAPI(
    title="openStruct",
    description=(
        "A API aberta da Engenharia Estrutural Brasileira. "
        "Contribua com o projeto no GitHub.\n\n"
        "Projeto mantido pela comunidade.\n"
    ),
    version="1.0.0",
    contact={
        "name": "openStruct",
        "url": "https://github.com/ricardocorsini/openstruct",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
)

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(desenho_router.router, prefix="/desenho")
app.include_router(dim_conc_router.router, prefix="/dimensionamento")
app.include_router(utilidades_fund_router.router, prefix="/utilidades")
app.include_router(consolo_router.router, prefix="/dimensionamento")
app.include_router(dimensionamento_estaca_router.router, prefix="/dimensionamento")
app.include_router(interacao_solo_estrutura_router.router, prefix="/ise")


@app.get("/", tags=["Início"])
def home():
    return {
        "projeto": "openStruct",
        "descricao": (
            "A API aberta da Engenharia Estrutural Brasileira. "
            "Contribua com o projeto no GitHub.\n\n"
            "Projeto mantido pela comunidade.\n"
        ),
        "links": {
            "documentação": "/docs",
            "repositório": "https://github.com/ricardocorsini/openstruct",
        },
        "proximos_passos": [
            "Use /ping para testar a conexão.",
            "Explore /docs para conhecer os endpoints.",
            "Contribua via Pull Request no GitHub.",
        ],
    }


@app.get("/ping", tags=["Utilitários"])
def ping():
    return {
        "status": "ok",
        "mensagem": "API openStruct está online! 🚀",
        "hora_servidor": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
