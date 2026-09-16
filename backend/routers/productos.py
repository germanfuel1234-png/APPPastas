"""Catálogo de productos."""
from fastapi import APIRouter, HTTPException

from ..database import fetch_all

router = APIRouter(prefix="/api", tags=["Catálogo"])


@router.get("/productos")
def listar_productos():
    """GET /api/productos — devuelve el catálogo de pastas por caja."""
    try:
        rows = fetch_all(
            "SELECT id, nombre, descripcion, precio_caja, imagen_url "
            "FROM productos WHERE activo = TRUE ORDER BY id"
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=503,
            detail=f"Base de datos no disponible. Verificá MySQL y el .env. ({exc})",
        ) from exc
    return {"productos": rows}