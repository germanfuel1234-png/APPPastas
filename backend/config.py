"""Configuración central del backend (base de datos, Mercado Pago y servidor).

Los valores se leen desde el archivo ``.env`` ubicado en la raíz del proyecto.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent  # raíz del repo
load_dotenv(BASE_DIR / ".env")


class Settings:
    # ---- Base de datos MySQL ----
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
    DB_USER: str = os.getenv("DB_USER", "root")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_NAME: str = os.getenv("DB_NAME", "fabrica_pastas")

    # ---- Mercado Pago (Checkout Pro) ----
    MP_ACCESS_TOKEN: str = os.getenv("MP_ACCESS_TOKEN", "")
    # URL pública que recibe los webhooks (ej: https://xxxx.ngrok-free.app/api/webhooks/mercadopago)
    MP_NOTIFICATION_URL: str = os.getenv("MP_NOTIFICATION_URL", "")
    # Email del pagador invitado (Mercado Pago requiere un mail en la preferencia).
    MP_PAYER_EMAIL: str = os.getenv("MP_PAYER_EMAIL", "invitado@fabrica-pastas.local")
    MP_BACK_URL_SUCCESS: str = os.getenv("MP_BACK_URL_SUCCESS", "")
    MP_BACK_URL_PENDING: str = os.getenv("MP_BACK_URL_PENDING", "")
    MP_BACK_URL_FAILURE: str = os.getenv("MP_BACK_URL_FAILURE", "")

    # ---- Servidor backend (FastAPI) ----
    BACKEND_HOST: str = os.getenv("BACKEND_HOST", "0.0.0.0")
    BACKEND_PORT: int = int(os.getenv("BACKEND_PORT", "8000"))

    # Orígenes permitidos por CORS (coma-separado). "*" = cualquiera (default,
    # apto para desarrollo o cuando el único consumidor es la app nativa).
    CORS_ORIGINS: list[str] = [
        o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()
    ] or ["*"]

    # Secreto de verificación de firma del webhook de Mercado Pago
    # (panel de la app en Mercado Pago > Webhooks > "Firma secreta").
    # Si queda vacío, el webhook no valida firma (solo recomendado en desarrollo).
    MP_WEBHOOK_SECRET: str = os.getenv("MP_WEBHOOK_SECRET", "")

    # ---- Staff (verificación en el local, NO se distribuye con el cliente) ----
    ADMIN_TOKEN: str = os.getenv("ADMIN_TOKEN", "cambiar-me")


settings = Settings()