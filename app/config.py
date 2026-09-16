"""Configuración del cliente Flet (carga el .env de la raíz del proyecto).

Deliberadamente NO se lee acá ``ADMIN_TOKEN``: si el cliente lo cargara desde
el .env quedaría embebido en el paquete distribuido de la app, y cualquiera
podría extraerlo para marcar pedidos como entregados sin pagar. El personal
lo tipea a mano cuando lo necesita (ver ``app/views/estado.py``).
"""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
# Fallback para builds empaquetados (APK/web): el .env de la raíz del repo
# queda afuera del paquete que arma `flet build`, así que si existe un .env
# junto a este archivo (empaquetado dentro de app/) también se lee. No pisa
# valores ya cargados desde el .env de la raíz (load_dotenv no sobreescribe
# por default), así que en desarrollo local sigue mandando el de la raíz.
load_dotenv(Path(__file__).resolve().parent / ".env")

# URL base del backend FastAPI.
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")

# Divisas usada al formatear precios.
DIVISA = os.getenv("APP_DIVISA", "$")