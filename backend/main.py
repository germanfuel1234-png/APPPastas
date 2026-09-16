"""API REST de la Fábrica de Pastas (FastAPI + MySQL + Mercado Pago)."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import fetch_one
from .routers import ordenes, productos, webhooks

app = FastAPI(
    title="Fábrica de Pastas API",
    description=(
        "Backend para la app de pedidos con retiro en local "
        "y pago mediante Mercado Pago (Checkout Pro + Webhooks)."
    ),
    version="1.0.0",
)

# La API no usa cookies (el único secreto es el header X-Admin-Token), por lo
# que no hace falta allow_credentials=True: combinarlo con allow_origins=["*"]
# es una configuración inválida según la spec de CORS. Los orígenes permitidos
# se restringen vía CORS_ORIGINS en .env para despliegues productivos.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(productos.router)
app.include_router(ordenes.router)
app.include_router(webhooks.router)


@app.get("/")
def root():
    return {"app": "Fábrica de Pastas API", "docs": "/docs", "health": "/health"}


@app.get("/health")
def health():
    """Check de estado del servicio y de la conexión a MySQL."""
    try:
        ok = fetch_one("SELECT 1 AS ok") is not None
    except Exception:
        ok = False
    return {"status": "ok", "database": ok}