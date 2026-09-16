"""Prueba end-to-end de la API sin MySQL.

Reemplaza la capa de base de datos (backend.database) por un almacén en
memoria y mockea al SDK de Mercado Pago, para ejercitar el flujo completo:
catálogo -> orden -> preferencia -> webhook -> actualización de estado.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Salida UTF-8 aunque la consola de Windows use otra página de códigos.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Almacén en memoria
# ---------------------------------------------------------------------------
PRODUCTOS = [
    {"id": 1, "nombre": "Ravioles ricota", "descripcion": "x500g", "precio_caja": 3500.0, "imagen_url": None},
    {"id": 2, "nombre": "Tallarines al huevo", "descripcion": "x500g", "precio_caja": 3000.0, "imagen_url": None},
]
ORDENES = {}
DETALLE = {}    # orden_id -> [lineas]
HISTORIAL = {}  # orden_id -> [filas]
NEXT_ORDEN = {"n": 1}
PREFERENCIAS = {"PREF_1": "https://www.mercadopago.com.ar/checkout/v1/redirect?pref_id=PREF_1"}
PAYMENTS = {}


class FakeCursor:
    def __init__(self, conn):
        self.conn = conn
        self.lastrowid = None
        self._result = []
        self._sql = ""
        self._params = ()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=()):
        self._sql = sql.lower()
        self._params = params or ()
        self._result = []
        self.lastrowid = None
        sqlu = sql.upper()

        if "SELECT 1 AS OK" in sqlu:
            self._result = [{"ok": 1}]
        elif "FROM PRODUCTOS" in sqlu:
            ids = self._params if self._params else None
            pool = [dict(p) for p in PRODUCTOS]
            if ids:
                pool = [p for p in pool if p["id"] in ids]
            self._result = pool
        elif "FROM ORDENES" in sqlu:
            if "MP_PREFERENCE_ID" in sqlu:
                pref = self._params[0]
                self._result = [o for o in ORDENES.values() if o.get("mp_preference_id") == pref]
            elif "WHERE ID = %S" in sqlu:
                oid = int(self._params[0])
                self._result = [ORDENES[oid]] if oid in ORDENES else []
            else:
                self._result = list(ORDENES.values())
        elif "FROM DETALLE_ORDEN" in sqlu:
            oid = int(self._params[0])
            self._result = [
                {**l,
                 "nombre": next(p["nombre"] for p in PRODUCTOS if p["id"] == l["producto_id"]),
                 "subtotal": l["cantidad_cajas"] * l["precio_unitario"]}
                for l in DETALLE.get(oid, [])
            ]
        elif "FROM ORDEN_HISTORIAL" in sqlu:
            oid = int(self._params[0])
            self._result = list(HISTORIAL.get(oid, []))
        elif "INSERT INTO ORDENES" in sqlu:
            nombre, telefono, tipo, total = self._params
            oid = NEXT_ORDEN["n"]
            NEXT_ORDEN["n"] += 1
            ORDENES[oid] = {
                "id": oid, "cliente_nombre": nombre, "cliente_telefono": telefono,
                "tipo_entrega": tipo, "total": total, "estado": "PENDIENTE",
                "mp_preference_id": None, "mp_payment_id": None,
                "fecha_creacion": "2026-09-15 10:00:00",
                "fecha_actualizacion": "2026-09-15 10:00:00",
            }
            self.lastrowid = oid
        elif "INSERT INTO DETALLE_ORDEN" in sqlu:
            oid, pid, cant, precio = self._params
            DETALLE.setdefault(oid, []).append(
                {"producto_id": pid, "cantidad_cajas": cant, "precio_unitario": precio}
            )
        elif "INSERT INTO ORDEN_HISTORIAL" in sqlu:
            oid, estado, detalle = self._params
            HISTORIAL.setdefault(oid, []).append(
                {"id": len(HISTORIAL.get(oid, [])) + 1, "orden_id": oid,
                 "estado": estado, "detalle": detalle, "fecha": "2026-09-15 10:00:00"}
            )
        elif "UPDATE ORDENES" in sqlu:
            oid = int(self._params[-1])
            if "MP_PREFERENCE_ID" in sqlu:
                ORDENES[oid]["mp_preference_id"] = self._params[0]
            elif "MP_PAYMENT_ID" in sqlu:
                ORDENES[oid]["estado"] = self._params[0]
                ORDENES[oid]["mp_payment_id"] = self._params[1]
            elif "'ENTREGADO'" in sqlu:
                ORDENES[oid]["estado"] = "ENTREGADO"

    def fetchall(self):
        return self._result

    def fetchone(self):
        return self._result[0] if self._result else None


class FakeConn:
    def __init__(self):
        self._pending = []

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


# ---------------------------------------------------------------------------
# Monkeypatch de la capa de BD y de Mercado Pago
# ---------------------------------------------------------------------------
import backend.database as db
import backend.routers.ordenes as ordenes_mod
import backend.routers.productos as productos_mod
import backend.routers.webhooks as webhooks_mod
from backend.main import app


def fake_connection():
    return FakeConn()


def fake_transaction():
    return FakeConn()


def fake_fetch_all(sql, params=()):
    with FakeConn().cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def fake_fetch_one(sql, params=()):
    with FakeConn().cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def fake_historizar(conn, orden_id, estado, detalle=""):
    with conn.cursor() as cur:
        cur.execute("INSERT INTO orden_historial VALUES (0, %s, %s, %s, 0)",
                    (orden_id, estado, detalle))


def fake_crear_preferencia(items, orden_id, cliente_nombre, cliente_apellido, cliente_telefono):
    pid = f"PREF_{orden_id}"
    PREFERENCIAS[pid] = f"https://www.mercadopago.com.ar/checkout/v1/redirect?pref_id={pid}"
    return pid, PREFERENCIAS[pid]


def fake_obtener_pago(payment_id):
    return PAYMENTS.get(str(payment_id), {})


for mod in (db, productos_mod, ordenes_mod, webhooks_mod):
    mod.fetch_all = fake_fetch_all
    mod.fetch_one = fake_fetch_one
db.get_connection = fake_connection
db.transaction = fake_transaction
db.historizar = fake_historizar
ordenes_mod.transaction = fake_transaction
ordenes_mod.historizar = fake_historizar
ordenes_mod.crear_preferencia = fake_crear_preferencia
webhooks_mod.get_connection = fake_connection
webhooks_mod.historizar = fake_historizar
webhooks_mod.obtener_pago = fake_obtener_pago
webhooks_mod.fetch_one = fake_fetch_one


if __name__ == "__main__":
    from fastapi.testclient import TestClient

    client = TestClient(app)

    # --- health ---
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok", r.text

    # --- catálogo ---
    r = client.get("/api/productos")
    assert r.status_code == 200, r.text
    assert len(r.json()["productos"]) == 2, r.text

    # --- orden con carrito ---
    r = client.post("/api/ordenes", json={
        "cliente_nombre": "Juan",
        "cliente_apellido": "Pérez",
        "cliente_telefono": "+54 9 11 5555-5555",
        "tipo_entrega": "RETIRO_LOCAL",
        "items": [
            {"producto_id": 1, "cantidad_cajas": 2},
            {"producto_id": 2, "cantidad_cajas": 1},
        ],
    })
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["id_orden"] == 1
    assert data["estado"] == "PENDIENTE"
    assert data["total"] == 10000.0, data  # 2*3500 + 1*3000
    assert data["init_point"].startswith("https://"), data
    print("OK POST /api/ordenes ->", data)

    # --- validación: producto inexistente ---
    r = client.post("/api/ordenes", json={
        "cliente_nombre": "Ana", "cliente_telefono": "42123456",
        "items": [{"producto_id": 999, "cantidad_cajas": 1}],
    })
    assert r.status_code == 400, r.text

    # --- consulta del ticket (PENDIENTE + historial) ---
    r = client.get("/api/ordenes/1")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["orden"]["estado"] == "PENDIENTE"
    assert len(body["items"]) == 2
    assert len(body["historial"]) == 1
    print("OK GET /api/ordenes/1")

    # --- webhook: pago aprobado ---
    PAYMENTS["9001"] = {"preference_id": "PREF_1", "external_reference": "1", "status": "approved"}
    r = client.post("/api/webhooks/mercadopago", json={"type": "payment", "data": {"id": "9001"}})
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "APROBADO", r.text

    r = client.get("/api/ordenes/1")
    assert r.json()["orden"]["estado"] == "APROBADO"
    assert r.json()["orden"]["mp_payment_id"] == "9001"
    assert len(r.json()["historial"]) == 2
    print("OK webhook aprobado -> estado APROBADO")

    # --- webhook posterior con estado rechazado no pisa la orden aprobada ---
    PAYMENTS["9002"] = {"preference_id": "PREF_1", "status": "rejected"}
    r = client.post("/api/webhooks/mercadopago", json={"type": "payment", "data": {"id": "9002"}})
    assert r.json()["estado"] == "RECHAZADO", r.text  # el webhook responde estado nuevo
    r = client.get("/api/ordenes/1")
    assert r.json()["orden"]["estado"] == "APROBADO", r.text  # pero no se pisa
    print("OK webhook posterior no sobrescribe una orden APROBADA")

    # --- staff: marcar entregada (con y sin token) ---
    r = client.post("/api/ordenes/1/entregar", headers={"X-Admin-Token": "token-incorrecto"})
    assert r.status_code == 403, r.text
    r = client.post("/api/ordenes/1/entregar")
    assert r.status_code == 403, r.text
    r = client.post("/api/ordenes/1/entregar", headers={"X-Admin-Token": "cambiar-me"})
    assert r.status_code == 200, r.text
    assert r.json()["orden"]["estado"] == "ENTREGADO", r.text
    print("OK /api/ordenes/1/entregar -> ENTREGADO (token)")

    # --- webhook de un pago SIN orden asociada ---
    PAYMENTS["9999"] = {"preference_id": "PREF_INEXISTENTE", "status": "approved"}
    r = client.post("/api/webhooks/mercadopago", json={"type": "payment", "data": {"id": "9999"}})
    assert r.json() == {"received": True, "ignored": True}, r.text

    # --- webhook con type que no es payment ---
    r = client.post("/api/webhooks/mercadopago", json={"type": "merchant_order", "data": {"id": "1"}})
    assert r.json() == {"received": True, "ignored": True}, r.text

    # --- validación pydantic (items vacíos) ---
    r = client.post("/api/ordenes", json={
        "cliente_nombre": "Ana", "cliente_telefono": "555", "items": []
    })
    assert r.status_code == 422, r.text

    print("\n✅ TODAS LAS PRUEBAS DE LA API PASARON")