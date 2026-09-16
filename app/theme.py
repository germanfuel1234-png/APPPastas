"""Identidad visual centralizada de la app.

Antes cada vista repetía colores sueltos de Material (``ft.Colors.GREEN_800``,
``AMBER_100``, ``ORANGE_700``...). Quedan acá como constantes con nombre para
que un cambio de paleta no implique tocar los cuatro archivos de vistas.
"""
import flet as ft

# Color de marca (identifica precios, acentos de "retiro en el local", etc.)
COLOR_PRIMARY = ft.Colors.GREEN_800
COLOR_PRIMARY_LIGHT = ft.Colors.GREEN_700
COLOR_PRIMARY_BG = ft.Colors.AMBER_100
COLOR_PRIMARY_TEXT = ft.Colors.GREEN_900

# Acento (ícono de producto, botones secundarios).
COLOR_ACCENT = ft.Colors.ORANGE_700

# Precio destacado (catálogo, carrito, checkout, ticket).
COLOR_PRICE = COLOR_PRIMARY


def build_theme() -> ft.Theme:
    """Tema Material generado a partir del color de marca."""
    return ft.Theme(color_scheme_seed=COLOR_PRIMARY)
