"""Integración con Mercado Pago (Checkout Pro) usando el SDK oficial.

- ``crear_preferencia``: crea la preferencia de pago y devuelve (preference_id, init_point).
- ``obtener_pago``: consulta el detalle de un pago para verificar webhooks.
- ``estado_mp_a_db``: mapea el status de Mercado Pago al enum de la tabla ``ordenes``.
- ``verificar_firma_webhook``: valida el header ``x-signature`` de las notificaciones.
"""
import hashlib
import hmac

from .config import settings


class MercadoPagoError(Exception):
    """Error de comunicación / configuración con Mercado Pago."""


def get_sdk():
    """Devuelve una instancia del SDK con el access token configurado."""
    if not settings.MP_ACCESS_TOKEN:
        raise MercadoPagoError(
            "MP_ACCESS_TOKEN no está configurado. Revisá el archivo .env"
        )
    import mercadopago

    return mercadopago.SDK(settings.MP_ACCESS_TOKEN)


def _status_code(result) -> int:
    code = result.get("status") or result.get("status_code") or 200
    if not isinstance(code, int):
        return 400  # forma de error del SDK
    return code


def crear_preferencia(items: list[dict], orden_id: int,
                      cliente_nombre: str, cliente_apellido: str,
                      cliente_telefono: str) -> tuple[str, str]:
    """Crea una preferencia de pago y devuelve ``(preference_id, init_point)``.

    ``items`` es una lista de dicts con las claves: producto_id, nombre,
    descripcion, precio_caja y cantidad_cajas.
    """
    sdk = get_sdk()

    mp_items = []
    for it in items:
        mp_items.append(
            {
                "id": str(it["producto_id"]),
                "title": f"{it['nombre']} (caja)",
                "description": it.get("descripcion") or it["nombre"],
                "quantity": int(it["cantidad_cajas"]),
                "unit_price": float(it["precio_caja"]),
                "currency_id": "ARS",
            }
        )

    back_urls = {}
    if settings.MP_BACK_URL_SUCCESS:
        back_urls["success"] = settings.MP_BACK_URL_SUCCESS
    if settings.MP_BACK_URL_PENDING:
        back_urls["pending"] = settings.MP_BACK_URL_PENDING
    if settings.MP_BACK_URL_FAILURE:
        back_urls["failure"] = settings.MP_BACK_URL_FAILURE

    preference_data = {
        "items": mp_items,
        "payer": {
            "name": cliente_nombre,
            "surname": cliente_apellido or None,
            "phone": {"area_code": "", "number": cliente_telefono},
            "email": settings.MP_PAYER_EMAIL,
        },
        # Referencia que luego permite asociar el pago/webhook a la orden local.
        "external_reference": str(orden_id),
        "statement_descriptor": "FABRICA DE PASTAS",
    }
    if settings.MP_NOTIFICATION_URL:
        preference_data["notification_url"] = settings.MP_NOTIFICATION_URL
    if back_urls:
        preference_data["back_urls"] = back_urls
        preference_data["auto_return"] = "approved"

    result = sdk.preference().create(preference_data)
    if _status_code(result) >= 400:
        raise MercadoPagoError(f"MP no pudo crear la preferencia: {result.get('response')}")

    response = result.get("response") or {}
    preference_id = response.get("id")
    init_point = response.get("init_point")
    if not preference_id or not init_point:
        raise MercadoPagoError("MP no devolvió id/init_point para la preferencia.")
    return preference_id, init_point


def obtener_pago(payment_id) -> dict:
    """Consulta el detalle de un pago realizado en Mercado Pago."""
    sdk = get_sdk()
    result = sdk.payment().get(str(payment_id))
    return result.get("response") or {}


def estado_mp_a_db(status: str) -> str:
    """Mapea el ``status`` de Mercado Pago al enum de la tabla ``ordenes``."""
    return {
        "approved": "APROBADO",
        "rejected": "RECHAZADO",
        "refunded": "RECHAZADO",
        "cancelled": "RECHAZADO",
        "charged_back": "RECHAZADO",
    }.get(status, "PENDIENTE")


def verificar_firma_webhook(x_signature: str, x_request_id: str, data_id: str) -> bool:
    """Valida el header ``x-signature`` de un webhook de Mercado Pago.

    Sigue el algoritmo oficial de MP: el header trae pares ``clave=valor``
    separados por coma (``ts=...,v1=...``). Se arma el "manifest"
    ``id:{data_id};request-id:{x_request_id};ts:{ts};`` y se compara su HMAC-SHA256
    (con ``MP_WEBHOOK_SECRET``) contra el ``v1`` recibido.
    Devuelve ``True`` si coincide. No se llama si no hay secreto configurado
    (ver ``routers/webhooks.py``).
    """
    partes = dict(
        p.split("=", 1) for p in x_signature.split(",") if "=" in p
    )
    ts = partes.get("ts", "")
    v1_recibido = partes.get("v1", "")
    if not ts or not v1_recibido:
        return False

    manifest = f"id:{data_id};request-id:{x_request_id};ts:{ts};"
    firma_calculada = hmac.new(
        settings.MP_WEBHOOK_SECRET.encode(), manifest.encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(firma_calculada, v1_recibido)