from fastapi import FastAPI
from datetime import datetime
from app.routers import desenho_router, dim_conc_router

# ==========================================================
# Configuração inicial da API
# ==========================================================
app = FastAPI(
    title="openStruct",
    description=(
        "A API aberta da Engenharia Estrutural Brasileira. Contribua com o projeto no GitHub.\n\n"
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

# ==========================================================
# Registro dos routers
# ==========================================================
app.include_router(desenho_router.router, prefix="/desenho")
app.include_router(dim_conc_router.router, prefix="/dimensionamento")



# ==========================================================
# Rota principal
# ==========================================================
@app.get("/", tags=["Início"])
def home():
    """
    Rota raiz da API openStruct.
    Apresenta mensagem de boas-vindas e instruções básicas.
    """
    return {
        "projeto": "openStruct",
        "descricao": (
            "A API aberta da Engenharia Estrutural Brasileira. Contribua com o projeto no GitHub.\n\n"
            "Projeto mantido pela comunidade.\n"
        ),
        "links": {
            "documentação": "/docs",
            "repositório": "https://github.com/ricardocorsini/openstruct",
        },
        "proximos_passos": [
            "Use /ping para testar a conexão.",
            "Explore /docs para conhecer os endpoints.",
            "Contribua via Pull Request no GitHub."
        ],
    }


# ==========================================================
# Endpoint de vitalidade
# ==========================================================
@app.get("/ping", tags=["Utilitários"])
def ping():
    """
    Retorna mensagem de status e horário atual do servidor.
    """
    return {
        "status": "ok",
        "mensagem": "API openStruct está online! 🚀",
        "hora_servidor": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    }


# ==========================================================
# Execução direta (modo local) - Aconselhado rodar com Docker, mesmo no local; 
# ==========================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
