"""Catálogo inicial de pastas por caja.

Uso:  .venv\\Scripts\\python.exe -m backend.seed
"""
from .database import execute, fetch_one

PRODUCTOS = [
    ("Ravioles de ricota (caja 0,5 kg)",
     "Ravioles artesanales con relleno de ricota y nuez moscada.", 3500.00, ""),
    ("Tallarines al huevo (caja 0,5 kg)",
     "Fideos frescos al huevo, corte fino.", 3000.00, ""),
    ("Sorrentinos de jamón y queso (caja 0,5 kg)",
     "Pasta rellena con jamón cocido y queso crema.", 4200.00, ""),
    ("Ñoquis de papa (caja 0,5 kg)",
     "Ñoquis clásicos hechos con papa y harina.", 3200.00, ""),
    ("Ravioles de verdura (caja 0,5 kg)",
     "Relleno de acelga, espinaca y ricota.", 3700.00, ""),
    ("Fetuccine al huevo (caja 0,5 kg)",
     "Fideos frescos de cinta ancha con huevo.", 3300.00, ""),
]


def main() -> None:
    insertados = 0
    omitidos = 0
    for nombre, descripcion, precio, imagen in PRODUCTOS:
        if fetch_one("SELECT id FROM productos WHERE nombre = %s", (nombre,)):
            omitidos += 1
            print(f"[omito, ya existe] {nombre}")
            continue
        execute(
            "INSERT INTO productos (nombre, descripcion, precio_caja, imagen_url) "
            "VALUES (%s, %s, %s, %s)",
            (nombre, descripcion, precio, imagen or None),
        )
        insertados += 1
        print(f"[insertado] {nombre} — ${precio:,.2f} / caja")

    print(f"\nListo. Insertados: {insertados} | Omitidos: {omitidos}")


if __name__ == "__main__":
    main()