"""Modelos Pydantic para los request/response de la API."""
import re
from typing import List

from pydantic import BaseModel, Field, field_validator

# Sin espacios/guiones/paréntesis, solo dígitos (+ opcional "+" inicial),
# 8 a 15 dígitos (rango E.164). Mismo criterio que app/views/checkout.py.
_TELEFONO_RE = re.compile(r"^\+?\d{8,15}$")


class ItemOrden(BaseModel):
    """Línea de pedido: un producto y su cantidad de cajas."""

    producto_id: int
    cantidad_cajas: int = Field(default=1, ge=1, le=1000)


class CrearOrdenRequest(BaseModel):
    """Body del POST /api/ordenes (datos mínimos del invitado + carrito)."""

    cliente_nombre: str = Field(min_length=2, max_length=100)
    cliente_apellido: str = Field(default="", max_length=100)
    cliente_telefono: str = Field(min_length=4, max_length=50)
    tipo_entrega: str = Field(default="RETIRO_LOCAL", pattern="RETIRO_LOCAL")
    items: List[ItemOrden] = Field(min_length=1)

    @field_validator("cliente_telefono")
    @classmethod
    def _validar_telefono(cls, v: str) -> str:
        normalizado = re.sub(r"[\s\-()]", "", v)
        if not _TELEFONO_RE.match(normalizado):
            raise ValueError(
                "Teléfono inválido: usá solo dígitos (8 a 15), con '+' opcional al inicio."
            )
        return v