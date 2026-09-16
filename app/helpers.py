"""Utilidades compartidas para las vistas de la app Flet."""
import flet as ft

from .config import DIVISA
from .theme import COLOR_ACCENT


def fmt(precio) -> str:
    """Formatea un precio con la divisa configurada. Ej: $3.500,00"""
    return f"{DIVISA}{float(precio):,.2f}"


def aviso(page: ft.Page, mensaje: str) -> None:
    """Muestra un SnackBar con un mensaje breve."""
    page.show_dialog(ft.SnackBar(ft.Text(mensaje)))


def producto_thumbnail(imagen_url: str, size: int) -> ft.Control:
    """Foto del producto si hay ``imagen_url``, si no el ícono genérico de antes."""
    if imagen_url:
        return ft.Image(
            src=imagen_url,
            width=size,
            height=size,
            fit=ft.BoxFit.COVER,
            border_radius=8,
        )
    return ft.Icon(ft.Icons.RESTAURANT, size=size, color=COLOR_ACCENT)


def estado_ui(estado: str):
    """Devuelve (color, icono) para el badge de un estado de orden."""
    mapping = {
        "PENDIENTE": (ft.Colors.AMBER_700, ft.Icons.HOURGLASS_TOP),
        "APROBADO": (ft.Colors.GREEN_700, ft.Icons.CHECK_CIRCLE),
        "RECHAZADO": (ft.Colors.RED_700, ft.Icons.CANCEL),
        "ENTREGADO": (ft.Colors.BLUE_700, ft.Icons.STORE),
    }
    return mapping.get(estado, (ft.Colors.GREY_600, ft.Icons.HELP_OUTLINE))