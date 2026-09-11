from fastapi import FastAPI, HTTPException
from fatec import generate, create_db

app = FastAPI(
    title="API de Estoque",
    description="API para consulta do estoque utilizando linguagem natural.",
    version="1.0.0",
)


@app.on_event("startup")
def startup():
    create_db()


@app.get("/")
def home():
    return {"mensagem": "API de Estoque funcionando!"}


@app.get("/estoque")
def consultar_estoque(pergunta: str):

    try:
        resultado = generate(pergunta)

        return {"pergunta": pergunta, "resultado": resultado}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
