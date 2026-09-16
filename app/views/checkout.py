"""Vista: Checkout — datos de contacto, resumen, generación de pago."""
import re

import flet as ft

from app.api import ApiError, crear_orden
from app.helpers import aviso, fmt
from app.theme import COLOR_PRICE, COLOR_PRIMARY_TEXT

# Igual criterio que backend/schemas.py: sin espacios/guiones/paréntesis,
# queda solo dígitos (+ opcional "+" inicial), 8 a 15 dígitos (rango E.164).
_TELEFONO_RE = re.compile(r"^\+?\d{8,15}$")


def _telefono_valido(telefono: str) -> bool:
    normalizado = re.sub(r"[\s\-()]", "", telefono)
    return bool(_TELEFONO_RE.match(normalizado))


def build_checkout_view(page: ft.Page, cart, navigation_bar: ft.NavigationBar) -> ft.View:
    cuerpo = ft.Column(controls=[], expand=True, spacing=10)
    resultado = {"data": None}

    campo_nombre = ft.TextField(
        label="Nombre *",
        hint_text="Ej: Juan",
        keyboard_type=ft.KeyboardType.NAME,
    )
    campo_apellido = ft.TextField(
        label="Apellido",
        hint_text="Ej: Pérez",
        keyboard_type=ft.KeyboardType.NAME,
    )
    campo_telefono = ft.TextField(
        label="Teléfono / WhatsApp *",
        hint_text="Ej: +54 9 11 2345-6789",
        keyboard_type=ft.KeyboardType.PHONE,
    )
    btn_enviar = ft.FilledButton(
        "Confirmar pedido y pagar",
        icon=ft.Icons.CREDIT_CARD,
        expand=True,
    )

    def enviar(e) -> None:
        nombre = campo_nombre.value.strip()
        telefono = campo_telefono.value.strip()
        if len(nombre) < 2:
            aviso(page, "Ingresá tu nombre.")
            return
        if not _telefono_valido(telefono):
            aviso(page, "Ingresá un teléfono válido (solo números, 8 a 15 dígitos).")
            return

        btn_enviar.content = ft.Row(
            controls=[
                ft.ProgressRing(width=16, height=16, stroke_width=2, color=ft.Colors.WHITE),
                ft.Text("Generando pago…", color=ft.Colors.WHITE),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=8,
        )
        btn_enviar.disabled = True
        page.update()

        try:
            resp = crear_orden(
                {
                    "cliente_nombre": nombre,
                    "cliente_apellido": campo_apellido.value.strip(),
                    "cliente_telefono": telefono,
                    "tipo_entrega": "RETIRO_LOCAL",
                    "items": [
                        {"producto_id": it.producto_id, "cantidad_cajas": it.cantidad}
                        for it in cart.items
                    ],
                }
            )
        except ApiError as exc:
            btn_enviar.content = "Confirmar pedido y pagar"
            btn_enviar.disabled = False
            aviso(page, str(exc))
            page.update()
            return

        resultado["data"] = resp
        cart.clear()
        render()

    def build_formulario() -> ft.Control:
        if not cart.items:
            return ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Icon(ft.Icons.PAYMENTS, size=52, color=ft.Colors.GREY_400),
                        ft.Text("No hay productos en el carrito", size=16, weight=ft.FontWeight.BOLD),
                        ft.Button(
                            "Ir al catálogo",
                            on_click=lambda _: page.navigate("/"),
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=8,
                ),
                padding=30,
            )

        filas = []
        for it in cart.items:
            filas.append(
                ft.Row(
                    controls=[
                        ft.Text(it.nombre, expand=True, size=13),
                        ft.Text(f"{it.cantidad} x {fmt(it.precio_caja)}", size=12, color=ft.Colors.GREY_700),
                        ft.Text(fmt(it.subtotal), size=13, weight=ft.FontWeight.BOLD),
                    ],
                    spacing=8,
                )
            )

        return ft.ListView(
            controls=[
                ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Text("Datos de contacto", size=16, weight=ft.FontWeight.BOLD),
                                campo_nombre,
                                campo_apellido,
                                campo_telefono,
                                ft.Row(
                                    controls=[
                                        ft.Icon(ft.Icons.STORE, size=16, color=COLOR_PRIMARY_TEXT),
                                        ft.Text("Modalidad: Retiro en el local", size=13, color=ft.Colors.GREY_800),
                                    ],
                                    spacing=6,
                                ),
                            ],
                            spacing=10,
                        ),
                        padding=12,
                    )
                ),
                ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Text("Resumen del pedido", size=16, weight=ft.FontWeight.BOLD),
                                *filas,
                                ft.Divider(height=1),
                                ft.Row(
                                    controls=[
                                        ft.Text("Total", size=15, weight=ft.FontWeight.BOLD),
                                        ft.Text(fmt(cart.total), size=17, weight=ft.FontWeight.BOLD, color=COLOR_PRICE),
                                    ],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                ),
                            ],
                            spacing=8,
                        ),
                        padding=12,
                    )
                ),
                btn_enviar,
                ft.Text(
                    "Al confirmar se generará el link de pago de Mercado Pago. "
                    "Podés pagar con dinero en cuenta, tarjeta o débito.",
                    size=11,
                    color=ft.Colors.GREY_600,
                ),
            ],
            spacing=12,
            padding=16,
            expand=True,
        )

    def build_confirmacion() -> ft.Control:
        data = resultado["data"]
        return ft.ListView(
            controls=[
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN_700, size=64),
                            ft.Text("¡Pedido generado!", size=22, weight=ft.FontWeight.BOLD),
                            ft.Text(
                                f"Tu número de ticket: #{data['id_orden']}",
                                size=16,
                                weight=ft.FontWeight.W_600,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=6,
                    ),
                    padding=24,
                ),
                ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Row(
                                    controls=[
                                        ft.Text("Estado actual", size=13, color=ft.Colors.GREY_700),
                                        ft.Text("PENDIENTE", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER_800),
                                    ],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                ),
                                ft.Text(f"Total a pagar: {fmt(data['total'])}", size=17, weight=ft.FontWeight.BOLD),
                                ft.TextField(
                                    value=data["init_point"],
                                    label="Link / cupón de pago (copialo si querés)",
                                    read_only=True,
                                    multiline=True,
                                    min_lines=2,
                                    max_lines=4,
                                    text_size=12,
                                ),
                            ],
                            spacing=10,
                        ),
                        padding=12,
                    )
                ),
                ft.Button(
                    "Pagar ahora con Mercado Pago",
                    icon=ft.Icons.PAYMENTS,
                    bgcolor=ft.Colors.BLUE_700,
                    color=ft.Colors.WHITE,
                    action=ft.OpenUrl(data["init_point"], target=ft.UrlTarget.BLANK),
                    on_click=lambda _: aviso(page, "Completá el pago y luego consultá tu ticket."),
                    expand=True,
                ),
                ft.Button(
                    "Ya pagué · consultar mi ticket",
                    icon=ft.Icons.RECEIPT_LONG,
                    on_click=lambda _: page.navigate("/estado"),
                    expand=True,
                ),
                ft.OutlinedButton(
                    "Volver al catálogo",
                    on_click=lambda _: page.navigate("/"),
                ),
            ],
            spacing=12,
            padding=16,
            expand=True,
        )

    def render() -> None:
        cuerpo.controls.clear()
        if resultado["data"] is None:
            cuerpo.controls.append(build_formulario())
        else:
            cuerpo.controls.append(build_confirmacion())
        page.update()

    btn_enviar.on_click = enviar

    view = ft.View(
        route="/checkout",
        controls=[
            ft.AppBar(
                title=ft.Text("Checkout", weight=ft.FontWeight.BOLD),
                center_title=True,
                bgcolor=ft.Colors.WHITE,
            ),
            cuerpo,
        ],
        navigation_bar=navigation_bar,
    )
    render()
    return view