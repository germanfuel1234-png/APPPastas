"""Cliente HTTP para consumir la API del backend (FastAPI)."""
import requests

from .config import API_BASE_URL


class ApiError(Exception):
    """Error de conexión o respuesta HTTP inválida del backend."""


def _request(method: str, path: str, timeout: int = 15, **kwargs):
    try:
        resp = requests.request(method, f"{API_BASE_URL}{path}", timeout=timeout, **kwargs)
    except requests.RequestException as exc:
        raise ApiError(
            f"No se pudo conectar con el servidor ({API_BASE_URL}). "
            f"¿Está corriendo el backend? Detalle: {exc}"
        ) from exc

    try:
        data = resp.json()
    except ValueError:
        data = {}

    if not resp.ok:
        detail = ""
        if isinstance(data, dict):
            detail = data.get("detail") or data.get("message") or ""
        raise ApiError(detail or f"El servidor respondió con error {resp.status_code}.")

    return data


def fetch_productos():
    """GET /api/productos -> {'productos': [...]}"""
    return _request("GET", "/api/productos")


def crear_orden(payload: dict):
    """POST /api/ordenes -> {'id_orden', 'estado', 'total', 'init_point', ...}"""
    return _request("POST", "/api/ordenes", json=payload)


def consultar_orden(orden_id):
    """GET /api/ordenes/{id} -> {'orden', 'items', 'historial'}"""
    return _request("GET", f"/api/ordenes/{int(orden_id)}")


def marcar_entregada(orden_id, token: str):
    """POST /api/ordenes/{id}/entregar (staff del local)."""
    return _request(
        "POST",
        f"/api/ordenes/{int(orden_id)}/entregar",
        headers={"X-Admin-Token": token},
    )