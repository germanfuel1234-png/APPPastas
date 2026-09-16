"""Vista: Carrito de compras (resumen antes de pagar)."""
import flet as ft

from app.helpers import fmt, producto_thumbnail
from app.theme import COLOR_PRICE, COLOR_PRIMARY_LIGHT


def build_carrito_view(page: ft.Page, cart, navigation_bar: ft.NavigationBar) -> ft.View:
    cuerpo = ft.Column(controls=[], expand=True, spacing=10)

    def render() -> None:
        cuerpo.controls.clear()
        items = cart.items

        if not items:
            cuerpo.controls.append(
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Icon(ft.Icons.SHOPPING_CART, size=56, color=ft.Colors.GREY_400),
                            ft.Text("Tu carrito está vacío", size=18, weight=ft.FontWeight.BOLD),
                            ft.Text(
                                "Sumá cajas de pasta desde el catálogo.",
                                size=13,
                                color=ft.Colors.GREY_700,
                            ),
                            ft.Button(
                                "Ver catálogo",
                                icon=ft.Icons.MENU_BOOK,
                                on_click=lambda _: page.navigate("/"),
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=8,
                    ),
                    padding=30,
                )
            )
        else:
            filas = [_fila_item(item, cart, render) for item in items]
            cuerpo.controls.append(
                ft.ListView(controls=filas, spacing=10, padding=16, expand=True)
            )
            cuerpo.controls.append(
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Text("Total", size=16, weight=ft.FontWeight.W_600),
                                    ft.Text(
                                        fmt(cart.total),
                                        size=22,
                                        weight=ft.FontWeight.BOLD,
                                        color=COLOR_PRICE,
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            ft.FilledButton(
                                "Continuar al pago",
                                icon=ft.Icons.PAYMENTS,
                                on_click=lambda _: page.navigate("/checkout"),
                                expand=True,
                            ),
                            ft.OutlinedButton(
                                "Vaciar carrito",
                                on_click=lambda _: (cart.clear(), render()),
                            ),
                        ],
                        spacing=10,
                    ),
                    padding=16,
                )
            )
        page.update()

    view = ft.View(
        route="/carrito",
        controls=[
            ft.AppBar(
                title=ft.Text("Tu carrito", weight=ft.FontWeight.BOLD),
                center_title=True,
                bgcolor=ft.Colors.WHITE,
            ),
            cuerpo,
        ],
        navigation_bar=navigation_bar,
    )
    render()
    return view


def _fila_item(item, cart, recargar) -> ft.Card:
    def on_add(e) -> None:
        cart.add(item.producto_id, item.nombre, item.precio_caja, item.imagen_url, 1)
        recargar()

    def on_sub(e) -> None:
        cart.set_cantidad(item.producto_id, item.cantidad - 1)
        recargar()

    def on_delete(e) -> None:
        cart.remove(item.producto_id)
        recargar()

    return ft.Card(
        content=ft.Container(
            content=ft.Row(
                controls=[
                    producto_thumbnail(item.imagen_url, 32),
                    ft.Column(
                        controls=[
                            ft.Text(item.nombre, weight=ft.FontWeight.W_600, size=14),
                            ft.Text(
                                f"{item.cantidad} caja(s) x {fmt(item.precio_caja)}",
                                size=12,
                                color=ft.Colors.GREY_700,
                            ),
                            ft.Text(
                                fmt(item.subtotal),
                                weight=ft.FontWeight.BOLD,
                                size=14,
                                color=COLOR_PRICE,
                            ),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                    ft.Column(
                        controls=[
                            ft.IconButton(
                                ft.Icons.ADD_CIRCLE_OUTLINE,
                                icon_color=COLOR_PRIMARY_LIGHT,
                                icon_size=22,
                                tooltip="Agregar caja",
                                on_click=on_add,
                            ),
                            ft.IconButton(
                                ft.Icons.REMOVE_CIRCLE_OUTLINE,
                                icon_color=ft.Colors.GREY_700,
                                icon_size=22,
                                tooltip="Quitar caja",
                                on_click=on_sub,
                            ),
                            ft.IconButton(
                                ft.Icons.DELETE_OUTLINE,
                                icon_color=ft.Colors.RED_400,
                                icon_size=22,
                                tooltip="Eliminar producto",
                                on_click=on_delete,
                            ),
                        ],
                        spacing=0,
                    ),
                ],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=10,
        ),
    )