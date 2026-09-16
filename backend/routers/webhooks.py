"""Webhook de Mercado Pago.

Mercado Pago notifica automáticamente los cambios de estado de los pagos a
``POST /api/webhooks/mercadopago``. Acá se verifica el pago contra la API de MP
(con el ``payment_id`` recibido) y se actualiza la orden correspondiente en
MySQL (APROBADO / RECHAZADO), dejando el historial de estados.

Si ``MP_WEBHOOK_SECRET`` está configurado, además se valida la firma
``x-signature`` para rechazar notificaciones que no vengan de Mercado Pago
(evita que cualquiera dispare relecturas de pago spameando el endpoint).
"""
import logging

from fastapi import APIRouter, HTTPException, Request

from ..config import settings
from ..database import get_connection, historizar
from ..mercadopago_service import estado_mp_a_db, obtener_pago, verificar_firma_webhook

logger = logging.getLogger("fabricapastas.webhook")
router = APIRouter(prefix="/api", tags=["Webhooks"])


@router.post("/webhooks/mercadopago")
async def webhook_mercadopago(request: Request, payload: dict):
    """Recibe la notificación de pago y actualiza el estado de la orden."""
    tipo = payload.get("type") or payload.get("topic")
    data = payload.get("data") or {}
    payment_id = data.get("id")

    if tipo != "payment" or not payment_id:
        # No es una notificación de pago o no trae id: se ignora.
        logger.info("Webhook ignorado: type=%s data=%s", tipo, data)
        return {"received": True, "ignored": True}

    if settings.MP_WEBHOOK_SECRET:
        x_signature = request.headers.get("x-signature", "")
        x_request_id = request.headers.get("x-request-id", "")
        if not verificar_firma_webhook(x_signature, x_request_id, str(payment_id)):
            logger.warning("Webhook con firma inválida: payment=%s", payment_id)
            raise HTTPException(status_code=403, detail="Firma de webhook inválida.")
    else:
        logger.warning(
            "MP_WEBHOOK_SECRET no configurado: la firma del webhook no se valida."
        )

    payment = obtener_pago(payment_id) or {}
    preference_id = payment.get("preference_id") or ""
    external_ref = payment.get("external_reference") or ""
    mp_status = payment.get("status") or ""
    nuevo_estado = estado_mp_a_db(mp_status)

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # 1) buscar la orden por preference_id (preferido)
            orden = None
            if preference_id:
                cur.execute(
                    "SELECT id, estado FROM ordenes WHERE mp_preference_id = %s LIMIT 1",
                    (preference_id,),
                )
                orden = cur.fetchone()
            # 2) fallback por external_reference (que es el id local de la orden)
            if orden is None and external_ref.isdigit():
                cur.execute(
                    "SELECT id, estado FROM ordenes WHERE id = %s LIMIT 1",
                    (int(external_ref),),
                )
                orden = cur.fetchone()

            if orden is None:
                logger.warning(
                    "Webhook sin orden asociada: payment=%s preferencia=%s",
                    payment_id, preference_id,
                )
                return {"received": True, "ignored": True}

            orden_id = orden["id"]
            estado_anterior = orden["estado"]

            # No sobrescribir órdenes ya cerradas (aprobadas o entregadas).
            if nuevo_estado != "PENDIENTE" and estado_anterior not in ("APROBADO", "ENTREGADO"):
                cur.execute(
                    "UPDATE ordenes SET estado = %s, mp_payment_id = %s WHERE id = %s",
                    (nuevo_estado, str(payment_id), orden_id),
                )
                historizar(
                    conn, orden_id, nuevo_estado,
                    detalle=f"Webhook MP: payment {payment_id} status '{mp_status or '?'}'",
                )

        conn.commit()
        return {
            "received": True,
            "orden_id": orden_id,
            "payment_id": str(payment_id),
            "estado": nuevo_estado,
        }
    except Exception:  # noqa: BLE001
        conn.rollback()
        raise
    finally:
        conn.close()