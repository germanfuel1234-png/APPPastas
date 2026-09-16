"""Estado del carrito de compras (persistido en disco, local a esta instalación).

Antes vivía solo en memoria del proceso: cerrar la app o que se reinicie
perdía el carrito. Se guarda como JSON en el directorio de datos que Flet
expone de forma síncrona vía ``FLET_APP_STORAGE_DATA`` (durante `flet run`
apunta a ``app/.flet/storage/data/``; en una app empaquetada, al directorio
de datos persistente del dispositivo). No requiere el servicio async
``SharedPreferences`` de Flet, evitando esa complejidad para un caso de uso
de un solo usuario/dispositivo.
"""
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

_CART_FILENAME = "cart.json"


def _cart_file_path() -> Path:
    storage_dir = os.environ.get("FLET_APP_STORAGE_DATA") or os.getcwd()
    return Path(storage_dir) / _CART_FILENAME


@dataclass
class CartItem:
    producto_id: int
    nombre: str
    precio_caja: float
    imagen_url: str = ""
    cantidad: int = 1

    @property
    def subtotal(self) -> float:
        return self.precio_caja * self.cantidad


class CartState:
    def __init__(self):
        self._items: dict[int, CartItem] = {}

    def add(self, producto_id: int, nombre: str, precio_caja: float,
            imagen_url: str = "", cantidad: int = 1) -> int:
        """Agrega cajas de un producto al carrito y devuelve la cantidad total."""
        item = self._items.get(producto_id)
        if item:
            item.cantidad += cantidad
        else:
            self._items[producto_id] = CartItem(
                producto_id, nombre, float(precio_caja), imagen_url, cantidad
            )
        self.save()
        return self._items[producto_id].cantidad

    def set_cantidad(self, producto_id: int, cantidad: int) -> None:
        """Fija la cantidad de un producto (si llega a 0 lo elimina)."""
        if cantidad <= 0:
            self.remove(producto_id)
            return
        item = self._items.get(producto_id)
        if item:
            item.cantidad = cantidad
            self.save()

    def remove(self, producto_id: int) -> None:
        self._items.pop(producto_id, None)
        self.save()

    def clear(self) -> None:
        self._items.clear()
        self.save()

    def cantidad_de(self, producto_id: int) -> int:
        item = self._items.get(producto_id)
        return item.cantidad if item else 0

    @property
    def items(self) -> list[CartItem]:
        return list(self._items.values())

    @property
    def count(self) -> int:
        return sum(i.cantidad for i in self._items.values())

    @property
    def total(self) -> float:
        return round(sum(i.subtotal for i in self._items.values()), 2)

    def __len__(self):
        return len(self._items)

    def save(self) -> None:
        """Vuelca el carrito a disco. Falla en silencio (no es crítico para operar)."""
        try:
            data = [asdict(item) for item in self._items.values()]
            _cart_file_path().write_text(json.dumps(data), encoding="utf-8")
        except OSError:
            pass

    def load(self) -> None:
        """Restaura el carrito guardado, si existe. No pisa un carrito ya cargado en error."""
        path = _cart_file_path()
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        self._items = {
            int(d["producto_id"]): CartItem(**d) for d in data
        }