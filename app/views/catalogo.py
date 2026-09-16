"""Vista: Catálogo de pastas por caja (consume GET /api/productos)."""
import asyncio

import flet as ft

from ..api import ApiError, fetch_productos
from ..helpers import fmt, producto_thumbnail
from ..theme import COLOR_PRICE, COLOR_PRIMARY_BG, COLOR_PRIMARY_LIGHT, COLOR_PRIMARY_TEXT


def build_catalogo_view(page: ft.Page, cart, navigation_bar: ft.NavigationBar) -> ft.View:
    banner = ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(ft.Icons.STORE, color=COLOR_PRIMARY_TEXT),
                ft.Text(
                    "Pedidos de cajas con retiro en el local · Pagá con Mercado Pago",
                    size=12,
                    color=COLOR_PRIMARY_TEXT,
                    expand=True,
                ),
            ]
        ),
        bgcolor=COLOR_PRIMARY_BG,
        padding=8,
    )

    # El GET /api/productos se resuelve en segundo plano (page.run_task) para no
    # congelar la pantalla: se muestra un spinner y se reemplaza cuando llega la
    # respuesta (o el error).
    contenido = ft.Column(controls=[_placeholder_cargando()], expand=True)

    async def cargar() -> None:
        try:
            productos = (await asyncio.to_thread(fetch_productos) or {}).get("productos", [])
        except ApiError as exc:
            contenido.controls = [_placeholder_error(str(exc), page)]
            page.update()
            return

        if not productos:
            contenido.controls = [_placeholder_vacio()]
        else:
            cards = [_product_card(p, page, cart) for p in productos]
            contenido.controls = [ft.ListView(controls=cards, spacing=14, padding=16, expand=True)]
        page.update()

    page.run_task(cargar)

    return ft.View(
        route="/",
        controls=[ft.AppBar(
            title=ft.Text("Fábrica de Pastas", weight=ft.FontWeight.BOLD),
            center_title=True,
            bgcolor=ft.Colors.WHITE,
        ), banner, contenido],
        navigation_bar=navigation_bar,
    )


def _placeholder_cargando() -> ft.Container:
    return ft.Container(
        content=ft.Column(
            controls=[ft.ProgressRing(), ft.Text("Cargando catálogo…", color=ft.Colors.GREY_700)],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10,
        ),
        padding=40,
        alignment=ft.Alignment.CENTER,
    )


def _placeholder_error(mensaje: str, page: ft.Page) -> ft.Container:
    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(
                    "No se pudo cargar el catálogo",
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.RED_700,
                ),
                ft.Text(mensaje, size=12, color=ft.Colors.GREY_700),
                ft.Button(
                    "Reintentar",
                    on_click=lambda _: page.navigate("/"),
                ),
            ],
            spacing=8,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=24,
    )


def _placeholder_vacio() -> ft.Container:
    return ft.Container(
        content=ft.Text(
            "El catálogo está vacío. Ejecutá el seed del backend "
            "(.venv\\Scripts\\python.exe -m backend.seed).",
            text_align=ft.TextAlign.CENTER,
        ),
        padding=24,
    )


def _product_card(producto: dict, page: ft.Page, cart) -> ft.Card:
    pid = int(producto["id"])
    nombre = producto["nombre"]
    precio = float(producto["precio_caja"])
    descripcion = producto.get("descripcion") or ""
    imagen = producto.get("imagen_url") or ""

    qty_text = ft.Text(_cantidad_label(cart.cantidad_de(pid)), size=13, color=ft.Colors.GREY_700)

    def refresh() -> None:
        cant = cart.cantidad_de(pid)
        qty_text.value = _cantidad_label(cant)
        page.update()

    def on_add(e) -> None:
        cart.add(pid, nombre, precio, imagen, 1)
        refresh()

    def on_sub(e) -> None:
        cart.set_cantidad(pid, cart.cantidad_de(pid) - 1)
        refresh()

    return ft.Card(
        content=ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            producto_thumbnail(imagen, 40),
                            ft.Column(
                                controls=[
                                    ft.Text(nombre, weight=ft.FontWeight.W_600, size=15),
                                    ft.Text(
                                        descripcion,
                                        size=12,
                                        color=ft.Colors.GREY_700,
                                        max_lines=2,
                                        overflow=ft.TextOverflow.ELLIPSIS,
                                    ),
                                ],
                                spacing=2,
                                expand=True,
                            ),
                        ],
                        spacing=12,
                    ),
                    ft.Divider(height=1),
                    ft.Row(
                        controls=[
                            ft.Text(
                                f"{fmt(precio)} / caja",
                                weight=ft.FontWeight.BOLD,
                                color=COLOR_PRICE,
                            ),
                            ft.Row(
                                controls=[
                                    ft.IconButton(
                                        ft.Icons.REMOVE,
                                        icon_color=ft.Colors.GREY_700,
                                        tooltip="Quitar caja",
                                        on_click=on_sub,
                                    ),
                                    qty_text,
                                    ft.IconButton(
                                        ft.Icons.ADD,
                                        icon_color=COLOR_PRIMARY_LIGHT,
                                        tooltip="Agregar caja",
                                        on_click=on_add,
                                    ),
                                ],
                                spacing=4,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                ],
                spacing=8,
            ),
            padding=12,
        ),
    )


def _cantidad_label(cant: int) -> str:
    if cant <= 0:
        return "0 cajas"
    return f"{cant} caja" + ("s" if cant != 1 else "")