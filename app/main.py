from fastapi import FastAPI
from app.api.produtos_routes import router as produtos_router
from app.api.consulta_routes import router as consulta_router

app = FastAPI(title="Estoque Text2SQL")

app.include_router(produtos_router)
app.include_router(consulta_router)