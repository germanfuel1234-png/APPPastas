"""Punto de entrada de la app móvil "Fábrica de Pastas" (cliente Flet).

Ejecutar desde la raíz del proyecto:
    .venv\\Scripts\\python.exe app\\main.py
o con el CLI oficial:
    .venv\\Scripts\\flet.exe run app\\main.py
"""
import sys
from pathlib import Path

# Garantiza que la raíz del proyecto esté en sys.path aunque el CLI de Flet
# cambie el directorio de trabajo.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import flet as ft  # noqa: E402

from app.state import CartState  # noqa: E402
from app.theme import build_theme  # noqa: E402
from app.views.carrito import build_carrito_view  # noqa: E402
from app.views.catalogo import build_catalogo_view  # noqa: E402
from app.views.checkout import build_checkout_view  # noqa: E402
from app.views.estado import build_estado_view  # noqa: E402

# (route, etiqueta, icono) para la NavigationBar inferior.
NAV = [
    ("/", "Catálogo", ft.Icons.MENU_BOOK),
    ("/carrito", "Carrito", ft.Icons.SHOPPING_CART),
    ("/checkout", "Checkout", ft.Icons.PAYMENTS),
    ("/estado", "Mi ticket", ft.Icons.RECEIPT_LONG),
]


def main(page: ft.Page) -> None:
    page.title = "Fábrica de Pastas · Pedidos con retiro"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = build_theme()
    page.padding = 0
    page.spacing = 0

    # Tamaño tipo "móvil" para la ventana de escritorio.
    try:
        page.window.width = 430
        page.window.height = 780
        page.window.min_width = 380
        page.window.min_height = 600
    except Exception:  # noqa: BLE001  (la ventana puede no ser editable en web)
        pass

    cart = CartState()
    cart.load()  # restaura el carrito guardado en la sesión anterior, si hay

    def nav_bar(selected_index: int) -> ft.NavigationBar:
        def on_change(e) -> None:
            route = NAV[e.control.selected_index][0]
            page.navigate(route)

        return ft.NavigationBar(
            selected_index=selected_index,
            bgcolor=ft.Colors.SURFACE,
            destinations=[
                ft.NavigationBarDestination(icon=icon, label=label)
                for _, label, icon in NAV
            ],
            on_change=on_change,
        )

    def route_change(e=None) -> None:
        route = (e.route if e is not None else page.route) or "/"
        page.views.clear()

        index = next((i for i, (r, _, _) in enumerate(NAV) if r == route), 0)
        builder = {
            "/": build_catalogo_view,
            "/carrito": build_carrito_view,
            "/checkout": build_checkout_view,
            "/estado": build_estado_view,
        }.get(route, build_catalogo_view)

        view = builder(page, cart, nav_bar(index))
        page.views.append(view)
        page.update()

    page.on_route_change = route_change
    route_change(None)


if __name__ == "__main__":
    ft.run(main, view=ft.AppView.FLET_APP)