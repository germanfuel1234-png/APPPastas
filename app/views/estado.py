"""Vista: Consulta del estado del ticket (GET /api/ordenes/{id})."""
import asyncio

import flet as ft

from app.api import ApiError, consultar_orden, marcar_entregada
from app.helpers import aviso, estado_ui, fmt
from app.theme import COLOR_PRICE

# Segundos entre reconsultas automáticas mientras el ticket sigue PENDIENTE
# (el usuario no tiene que tocar "Recargar estado" a mano para enterarse
# de que el webhook de MP ya aprobó el pago).
_POLL_SEGUNDOS = 5

# Orden de las etapas para el stepper visual del ticket. RECHAZADO es una
# rama terminal aparte, no un paso más de esta secuencia.
_ETAPAS = ["PENDIENTE", "APROBADO", "ENTREGADO"]


def build_estado_view(page: ft.Page, cart, navigation_bar: ft.NavigationBar) -> ft.View:
    campo = ft.TextField(
        label="Nº de ticket (ID de orden)",
        hint_text="Ej: 12",
        keyboard_type=ft.KeyboardType.NUMBER,
    )
    btn_consultar = ft.FilledButton(
        "Consultar estado",
        icon=ft.Icons.SEARCH,
        expand=True,
    )
    resultado = ft.Column(controls=[], expand=True, spacing=10)

    def consultar(e) -> None:
        valor = campo.value.strip()
        if not valor.isdigit():
            aviso(page, "Ingresá el número de ticket.")
            return

        resultado.controls.clear()
        resultado.controls.append(
            ft.Row(
                controls=[ft.ProgressRing(height=22, width=22), ft.Text("Consultando estado…")],
                spacing=8,
            )
        )
        page.update()

        try:
            data = consultar_orden(int(valor))
        except ApiError as exc:
            resultado.controls.clear()
            resultado.controls.append(_tarjeta_errores(str(exc)))
            page.update()
            return

        resultado.controls.clear()
        resultado.controls.append(_tarjeta_ticket(data, page, consultar))
        page.update()

        if data["orden"].get("estado") == "PENDIENTE":
            page.run_task(_poll_ticket, page, int(valor), resultado, consultar)

    btn_consultar.on_click = consultar
    campo.on_submit = consultar

    return ft.View(
        route="/estado",
        controls=[
            ft.AppBar(
                title=ft.Text("Estado de mi ticket", weight=ft.FontWeight.BOLD),
                center_title=True,
                bgcolor=ft.Colors.WHITE,
            ),
            ft.Container(
                content=ft.Row(
                    controls=[campo, ft.IconButton(ft.Icons.ARROW_FORWARD, on_click=consultar)]
                ),
                padding=16,
            ),
            resultado,
        ],
        navigation_bar=navigation_bar,
    )


def _tarjeta_errores(mensaje: str) -> ft.Container:
    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Icon(ft.Icons.ERROR_OUTLINE, color=ft.Colors.RED_400, size=48),
                ft.Text("No se encontró el ticket", weight=ft.FontWeight.BOLD),
                ft.Text(
                    mensaje,
                    size=12,
                    color=ft.Colors.GREY_700,
                    text_align=ft.TextAlign.CENTER,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=6,
        ),
        padding=24,
    )


def _badge(estado: str) -> ft.Container:
    color, icono = estado_ui(estado)
    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(icono, size=16, color=ft.Colors.WHITE),
                ft.Text(estado, size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
            ],
            spacing=4,
        ),
        bgcolor=color,
        border_radius=20,
        padding=6,
    )


def _stepper(estado: str) -> ft.Control:
    """Progreso PENDIENTE -> APROBADO -> ENTREGADO. RECHAZADO es una rama aparte."""
    if estado == "RECHAZADO":
        color, icono = estado_ui("RECHAZADO")
        return ft.Row(
            controls=[
                ft.Icon(icono, color=color, size=20),
                ft.Text("Pago rechazado", color=color, weight=ft.FontWeight.BOLD, size=13),
            ],
            spacing=6,
        )

    idx_actual = _ETAPAS.index(estado) if estado in _ETAPAS else 0
    nodos: list[ft.Control] = []
    for i, etapa in enumerate(_ETAPAS):
        color, icono = estado_ui(etapa)
        activo = i <= idx_actual
        nodos.append(
            ft.Column(
                controls=[
                    ft.Icon(icono, size=20, color=color if activo else ft.Colors.GREY_300),
                    ft.Text(
                        etapa.capitalize(),
                        size=10,
                        color=color if activo else ft.Colors.GREY_400,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=2,
            )
        )
        if i < len(_ETAPAS) - 1:
            nodos.append(
                ft.Container(
                    height=2,
                    expand=True,
                    bgcolor=color if i < idx_actual else ft.Colors.GREY_300,
                    margin=ft.Margin.only(top=10),
                )
            )
    return ft.Row(controls=nodos, alignment=ft.MainAxisAlignment.CENTER)


async def _poll_ticket(page: ft.Page, orden_id: int, resultado: ft.Column, consultar) -> None:
    """Reconsulta el ticket cada pocos segundos mientras siga PENDIENTE.

    Se corta solo si el usuario navega fuera de /estado o si el estado deja
    de ser PENDIENTE (ahí se refresca la tarjeta una última vez).
    """
    while page.route == "/estado":
        await asyncio.sleep(_POLL_SEGUNDOS)
        if page.route != "/estado":
            return
        try:
            data = consultar_orden(orden_id)
        except ApiError:
            return
        if data["orden"].get("estado") != "PENDIENTE":
            resultado.controls.clear()
            resultado.controls.append(_tarjeta_ticket(data, page, consultar))
            page.update()
            return


def _tarjeta_ticket(data: dict, page: ft.Page, consultar) -> ft.ListView:
    orden = data["orden"]
    items = data["items"] or []
    historial = data["historial"] or []
    estado = orden.get("estado", "PENDIENTE")

    filas_items = [
        ft.Row(
            controls=[
                ft.Column(
                    controls=[
                        ft.Text(item["nombre"], size=13, weight=ft.FontWeight.W_600),
                        ft.Text(
                            f"{item['cantidad_cajas']} caja(s) x {fmt(item['precio_unitario'])}",
                            size=11,
                            color=ft.Colors.GREY_700,
                        ),
                    ],
                    spacing=1,
                    expand=True,
                ),
                ft.Text(fmt(item["subtotal"]), size=13, weight=ft.FontWeight.BOLD),
            ],
            spacing=8,
        )
        for item in items
    ]

    filas_historial = [
        ft.Row(
            controls=[
                ft.Icon(ft.Icons.CIRCLE, size=10, color=estado_ui(h["estado"])[0]),
                ft.Text(
                    f"{h['estado']}  ·  {h.get('detalle') or ''}",
                    size=12,
                    color=ft.Colors.GREY_800,
                    expand=True,
                ),
                ft.Text(str(h["fecha"])[:19], size=11, color=ft.Colors.GREY_600),
            ],
            spacing=8,
        )
        for h in historial
    ]

    def marcar_entregada_click(e) -> None:
        _pedir_token_y_marcar(page, orden["id"], lambda: consultar(None))

    controles: list[ft.Control] = [
        ft.Card(
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Row(controls=[_badge(estado)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        _stepper(estado),
                        ft.Text(f"Ticket #{orden['id']}", size=18, weight=ft.FontWeight.BOLD),
                        ft.Text(
                            f"Cliente: {orden['cliente_nombre']} · {orden['cliente_telefono']}",
                            size=13,
                            color=ft.Colors.GREY_800,
                        ),
                        ft.Text(f"Modalidad: {orden['tipo_entrega']}", size=13, color=ft.Colors.GREY_800),
                        ft.Text(f"Creado: {str(orden['fecha_creacion'])[:19]}", size=12, color=ft.Colors.GREY_600),
                    ],
                    spacing=6,
                ),
                padding=12,
            )
        ),
        ft.Card(
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text("Detalle del pedido", size=15, weight=ft.FontWeight.BOLD),
                        *filas_items,
                        ft.Divider(height=1),
                        ft.Row(
                            controls=[
                                ft.Text("Total", weight=ft.FontWeight.BOLD),
                                ft.Text(
                                    fmt(orden["total"]),
                                    size=16,
                                    weight=ft.FontWeight.BOLD,
                                    color=COLOR_PRICE,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                    ],
                    spacing=6,
                ),
                padding=12,
            )
        ),
    ]

    if historial:
        controles.append(
            ft.Card(
                content=ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text("Historial de estados", size=15, weight=ft.FontWeight.BOLD),
                            *filas_historial,
                        ],
                        spacing=6,
                    ),
                    padding=12,
                )
            )
        )

    if estado == "PENDIENTE" and orden.get("mp_init_point"):
        controles.append(
            ft.Button(
                "Continuar con el pago",
                icon=ft.Icons.PAYMENTS,
                bgcolor=ft.Colors.BLUE_700,
                color=ft.Colors.WHITE,
                action=ft.OpenUrl(orden["mp_init_point"], target=ft.UrlTarget.BLANK),
                expand=True,
            )
        )

    if estado == "APROBADO":
        controles.append(
            ft.FilledTonalButton(
                "Marcar como entregada (staff del local)",
                icon=ft.Icons.STORE,
                on_click=marcar_entregada_click,
                expand=True,
            )
        )

    controles.append(
        ft.OutlinedButton(
            "Recargar estado",
            icon=ft.Icons.REFRESH,
            on_click=lambda _: consultar(None),
            expand=True,
        )
    )

    return ft.ListView(controls=controles, spacing=12, padding=16, expand=True)


def _pedir_token_y_marcar(page: ft.Page, orden_id: int, al_confirmar) -> None:
    """Pide el token de staff en un diálogo y recién ahí llama a la API.

    El token NO se guarda en ningún lado del cliente (ni en config, ni en
    disco): se tipea en el momento y solo viaja en ese único request. Antes
    la app lo leía de app/config.py, lo que lo dejaba embebido en el paquete
    distribuido — cualquiera podía extraerlo y marcar pedidos como
    entregados sin haber pagado.
    """
    campo_token = ft.TextField(
        label="Token de administración",
        password=True,
        can_reveal_password=True,
        autofocus=True,
    )

    def cerrar(e=None) -> None:
        page.pop_dialog()

    def confirmar(e) -> None:
        token = campo_token.value.strip()
        cerrar()
        if not token:
            return
        try:
            marcar_entregada(orden_id, token)
        except ApiError as exc:
            aviso(page, str(exc))
            return
        aviso(page, "Orden marcada como ENTREGADA ✓")
        al_confirmar()

    dialogo = ft.AlertDialog(
        title=ft.Text("Verificación de personal"),
        content=ft.Column(
            controls=[
                ft.Text(
                    "Ingresá el token de administración para confirmar la entrega.",
                    size=12,
                    color=ft.Colors.GREY_700,
                ),
                campo_token,
            ],
            tight=True,
            spacing=10,
        ),
        actions=[
            ft.TextButton("Cancelar", on_click=cerrar),
            ft.FilledButton("Confirmar entrega", on_click=confirmar),
        ],
    )
    page.show_dialog(dialogo)