"""Smoke test del cliente Flet: construye las 4 vistas con un Page simulado."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Salida UTF-8 aunque la consola de Windows use otra página de códigos.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


class MockWindow:
    def __init__(self):
        self.width = 430
        self.height = 780
        self.min_width = 380
        self.min_height = 600


class _Servicios:
    def __init__(self):
        self.servicios = []

    def register_service(self, service):
        self.servicios.append(service)

    def unregister_service(self, service):
        try:
            self.servicios.remove(service)
        except ValueError:
            pass


class MockPage:
    """Mínimo sustituto de ft.Page para 'build_*_view'."""

    def __init__(self):
        self.views = []
        self.route = "/"
        self.window = MockWindow()
        self.title = ""
        self.padding = 0
        self.spacing = 0
        self._services = _Servicios()

    def update(self, *_args, **_kwargs):
        pass

    def navigate(self, route, **_kwargs):
        self.route = route
        self.views.clear()

    def show_dialog(self, _dialog):
        pass

    def pop_dialog(self):
        pass

    def add(self, *_args):
        pass

    def run_task(self, handler, *args, **kwargs):
        """Sustituto síncrono de Page.run_task: corre la corrutina hasta el final.

        Alcanza para el smoke test (no hay un loop real de Flet corriendo);
        catalogo.py y estado.py usan page.run_task para cargas/polling en
        segundo plano.
        """
        return asyncio.run(handler(*args, **kwargs))


if __name__ == "__main__":
    import flet as ft
    from app.state import CartState
    from app.views.carrito import build_carrito_view
    from app.views.catalogo import build_catalogo_view
    from app.views.checkout import build_checkout_view
    from app.views.estado import build_estado_view

    def fake_nav(selected_index=0):
        return ft.NavigationBar(
            selected_index=selected_index,
            destinations=[
                ft.NavigationBarDestination(icon=ft.Icons.MENU_BOOK, label="Catálogo"),
                ft.NavigationBarDestination(icon=ft.Icons.SHOPPING_CART, label="Carrito"),
            ],
        )

    page = MockPage()
    cart = CartState()

    # 1) Catálogo (sin backend -> muestra el estado de error, no debe romper)
    view = build_catalogo_view(page, cart, fake_nav())
    assert isinstance(view, ft.View), "catálogo no devolvió un ft.View"
    assert view.route == "/"
    print("OK view catálogo (con/sin backend)")

    # 2) Carrito vacío
    view = build_carrito_view(page, cart, fake_nav())
    assert isinstance(view, ft.View) and view.route == "/carrito"
    print("OK view carrito vacío")

    # 3) Checkout con carrito vacío
    view = build_checkout_view(page, cart, fake_nav())
    assert isinstance(view, ft.View) and view.route == "/checkout"
    print("OK view checkout (carrito vacío)")

    # 4) Agregar items y reconstruir carrito + checkout con contenido
    cart.add(1, "Ravioles ricota", 3500.0, "", 2)
    cart.add(2, "Tallarines", 3000.0, "", 1)
    assert cart.total == 10000.0
    view = build_carrito_view(page, cart, fake_nav())
    assert isinstance(view, ft.View)
    view = build_checkout_view(page, cart, fake_nav())
    assert isinstance(view, ft.View)
    print("OK view carrito y checkout con items (total $10.000,00)")

    # 5) Estado del ticket
    view = build_estado_view(page, cart, fake_nav())
    assert isinstance(view, ft.View) and view.route == "/estado"
    print("OK view estado del ticket")

    # 6) Navegación del main (route_change con MockPage)
    import app.main as entry

    entry.main(page)
    assert len(page.views) == 1
    assert page.views[0].route == "/"
    print("OK entry.main() construyó la vista inicial '/'")

    print("\n✅ SMOKE TEST DEL CLIENTE FLET PASÓ")

# ---------------------------------------------------------------------------
# Prueba 2: flujo de checkout (monkeypatch de app.api.crear_orden)
# ---------------------------------------------------------------------------
import app.api as api_module  # noqa: E402
import app.views.checkout as checkout_mod  # noqa: E402

_real_crear_orden = checkout_mod.crear_orden


def _walk(control, out):
    if control is None:
        return
    out.append(control)
    children = []
    if isinstance(getattr(control, "controls", None), list):
        children = control.controls
    elif getattr(control, "content", None) is not None and not isinstance(
        control.content, str
    ):
        children = [control.content]
    for child in children:
        _walk(child, out)


def _find(view, tipos, label=None):
    found = []
    _walk(view, found)
    return [
        c
        for c in found
        if isinstance(c, tipos)
        and (label is None or getattr(c, "content", None) == label)
    ]


page2 = MockPage()
cart2 = CartState()
cart2.add(1, "Ravioles ricota", 3500.0, "", 2)

# ft.OpenUrl se registra contra la página actual del contexto de Flet;
# en la app real esto ocurre dentro de un callback. Acá lo simulamos:
import flet.controls.context as _fctx  # noqa: E402

_fctx._context_page.set(page2)

view2 = build_checkout_view(page2, cart2, fake_nav())

campos = {tf.label: tf for tf in _find(view2, ft.TextField)}
campos["Nombre *"].value = "Juan"
campos["Teléfono / WhatsApp *"].value = "+54 9 11 5555-5555"

llamadas = {}


def fake_crear_orden(payload):
    llamadas["payload"] = payload
    return {
        "id_orden": 77,
        "estado": "PENDIENTE",
        "total": 7000.0,
        "mp_preference_id": "PREF_77",
        "init_point": "https://www.mercadopago.com.ar/checkout/v1/redirect?pref_id=PREF_77",
    }


api_module.crear_orden = fake_crear_orden
checkout_mod.crear_orden = fake_crear_orden
try:
    btn = _find(view2, ft.FilledButton, "Confirmar pedido y pagar")[0]
    btn.on_click(None)  # simula el tap del usuario
finally:
    api_module.crear_orden = _real_crear_orden
    checkout_mod.crear_orden = _real_crear_orden

assert llamadas["payload"]["items"][0] == {"producto_id": 1, "cantidad_cajas": 2}, llamadas
assert llamadas["payload"]["cliente_nombre"] == "Juan"
assert len(cart2) == 0, "el carrito debería vaciarse tras generar la orden"

pagar = _find(view2, ft.Button, "Pagar ahora con Mercado Pago")
assert pagar, "no se encontró el botón de pago en la confirmación"
assert pagar[0].action is not None, "el botón de pago debe abrir el init_point"
print("OK flujo checkout: formulario -> orden generada -> panel de confirmación con link de pago")