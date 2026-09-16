"""Capa de acceso a MySQL usando PyMySQL (esquema de la especificación)."""
from contextlib import contextmanager

import pymysql

from .config import settings


def get_connection() -> pymysql.connections.Connection:
    """Crea una conexión a la base ``fabrica_pastas``."""
    return pymysql.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        database=settings.DB_NAME,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )


@contextmanager
def transaction():
    """Contexto que entrega una conexión y hace commit/rollback automáticamente."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def fetch_all(sql: str, params: tuple = ()) -> list[dict]:
    with transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return list(cur.fetchall())


def fetch_one(sql: str, params: tuple = ()) -> dict | None:
    rows = fetch_all(sql, params)
    return rows[0] if rows else None


def execute(sql: str, params: tuple = ()) -> int:
    """Ejecuta un INSERT/UPDATE/DELETE y devuelve el último id insertado."""
    with transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.lastrowid


def historizar(conn, orden_id: int, estado: str, detalle: str = "") -> None:
    """Registra un cambio de estado en ``orden_historial``."""
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO orden_historial (orden_id, estado, detalle) VALUES (%s, %s, %s)",
            (orden_id, estado, detalle),
        )