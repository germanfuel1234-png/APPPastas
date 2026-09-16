"""Gestión de órdenes/tickets.

- ``POST /api/ordenes``: recibe el carrito del invitado, registra la orden en
  MySQL como ``PENDIENTE`` y genera la preferencia en Mercado Pago (el total se
  calcula SIEMPRE del lado del servidor).
- ``GET /api/ordenes/{id}``: consulta el estado del ticket + historial.
- ``POST /api/ordenes/{id}/entregar``: el personal marca la orden como
  ``ENTREGADO`` al retirar (requiere token de administración).
"""
from fastapi import APIRouter, Header, HTTPException

from ..config import settings
from ..database import fetch_all, fetch_one, historizar, transaction
from ..mercadopago_service import MercadoPagoError, crear_preferencia
from ..schemas import CrearOrdenRequest

router = APIRouter(prefix="/api", tags=["Órdenes"])


@router.post("/ordenes", status_code=201)
def crear_orden(req: CrearOrdenRequest):
    """Crea la orden (PENDIENTE) y devuelve el link de pago de Mercado Pago."""
    nombre = req.cliente_nombre.strip()
    apellido = req.cliente_apellido.strip()
    telefono = req.cliente_telefono.strip()
    ids = [it.producto_id for it in req.items]
    placeholders = ",".join(["%s"] * len(ids))

    try:
        with transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, nombre, descripcion, precio_caja FROM productos "
                    f"WHERE activo = TRUE AND id IN ({placeholders})",
                    tuple(ids),
                )
                productos_db = {p["id"]: p for p in cur.fetchall()}

            faltantes = [i for i in ids if i not in productos_db]
            if faltantes:
                raise HTTPException(
                    status_code=400,
                    detail=f"Productos inexistentes o inactivos: {faltantes}",
                )

            lineas = []
            total = 0.0
            for it in req.items:
                p = productos_db[it.producto_id]
                lineas.append(
                    {
                        "producto_id": p["id"],
                        "nombre": p["nombre"],
                        "descripcion": p["descripcion"],
                        "precio_caja": p["precio_caja"],
                        "cantidad_cajas": it.cantidad_cajas,
                    }
                )
                total += float(p["precio_caja"]) * it.cantidad_cajas
            total = round(total, 2)

            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO ordenes (cliente_nombre, cliente_telefono, "
                    "tipo_entrega, total) VALUES (%s, %s, %s, %s)",
                    (nombre, telefono, req.tipo_entrega, total),
                )
                orden_id = cur.lastrowid
                for linea in lineas:
                    cur.execute(
                        "INSERT INTO detalle_orden (orden_id, producto_id, "
                        "cantidad_cajas, precio_unitario) VALUES (%s, %s, %s, %s)",
                        (orden_id, linea["producto_id"], linea["cantidad_cajas"],
                         linea["precio_caja"]),
                    )

            historizar(conn, orden_id, "PENDIENTE", detalle="Orden creada - esperando pago")

            # Preferencia de pago en Mercado Pago (si falla se revierte todo).
            try:
                preference_id, init_point = crear_preferencia(
                    items=lineas,
                    orden_id=orden_id,
                    cliente_nombre=nombre,
                    cliente_apellido=apellido,
                    cliente_telefono=telefono,
                )
            except MercadoPagoError as exc:
                raise HTTPException(status_code=502, detail=str(exc)) from exc

            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE ordenes SET mp_preference_id = %s, mp_init_point = %s WHERE id = %s",
                    (preference_id, init_point, orden_id),
                )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Error interno: {exc}") from exc

    return {
        "id_orden": orden_id,
        "estado": "PENDIENTE",
        "total": total,
        "mp_preference_id": preference_id,
        "init_point": init_point,
    }


@router.get("/ordenes/{orden_id}")
def consultar_orden(orden_id: int):
    """Consulta el ticket: estado actual, items e historial de estados."""
    orden = fetch_one("SELECT * FROM ordenes WHERE id = %s", (orden_id,))
    if orden is None:
        raise HTTPException(status_code=404, detail="Orden no encontrada")

    items = fetch_all(
        "SELECT d.producto_id, p.nombre, d.cantidad_cajas, d.precio_unitario, "
        "(d.cantidad_cajas * d.precio_unitario) AS subtotal "
        "FROM detalle_orden d JOIN productos p ON p.id = d.producto_id "
        "WHERE d.orden_id = %s ORDER BY d.id",
        (orden_id,),
    )
    historial = fetch_all(
        "SELECT id, estado, detalle, fecha FROM orden_historial "
        "WHERE orden_id = %s ORDER BY id",
        (orden_id,),
    )
    return {"orden": orden, "items": items, "historial": historial}


@router.post("/ordenes/{orden_id}/entregar")
def marcar_entregada(
    orden_id: int,
    x_admin_token: str = Header(default=""),
):
    """Marca una orden APROBADA como ENTREGADO (verificación en el local)."""
    if x_admin_token != settings.ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Token de administración inválido.")

    orden = fetch_one("SELECT id, estado FROM ordenes WHERE id = %s", (orden_id,))
    if orden is None:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    if orden["estado"] != "APROBADO":
        raise HTTPException(
            status_code=409,
            detail="Solo se puede marcar como ENTREGADA una orden APROBADA.",
        )

    with transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE ordenes SET estado = 'ENTREGADO' WHERE id = %s", (orden_id,)
            )
        historizar(conn, orden_id, "ENTREGADO", detalle="Retirada en el local")

    return {"orden": fetch_one("SELECT * FROM ordenes WHERE id = %s", (orden_id,))}