from fastapi import FastAPI, HTTPException
from fatec import generate, create_db, warm_up

app = FastAPI(
    title="API de Estoque",
    description="API para consulta do estoque utilizando linguagem natural.",
    version="1.0.0",
)


@app.on_event("startup")
def startup():
    create_db()
    try:
        # Evita que a primeira pergunta pague o carregamento do modelo.
        warm_up()
    except Exception as erro:
        print(f"Aquecimento do LLM falhou: {erro}")


@app.get("/")
def home():
    return {"mensagem": "API de Estoque funcionando!"}


@app.get("/estoque")
def consultar_estoque(pergunta: str):
    try:
        return generate(pergunta)

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )
