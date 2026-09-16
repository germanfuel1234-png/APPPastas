# 🍝 Fábrica de Pastas — App de pedidos con pago por Mercado Pago

Implementación completa de la [especificación](especificacion_contexto_fabrica_pastas.md):
app móvil **Python + Flet** + backend **FastAPI + MySQL** con integración **Mercado Pago**
(Checkout Pro y Webhooks).

## Funcionalidades

| Módulo | Qué hace |
|---|---|
| **Catálogo (Flet)** | Lista las pastas por caja, precios, alta de cantidades y carrito. |
| **Carrito / Checkout** | Datos del invitado (Nombre, Apellido, Teléfono), resumen y total; modalidad fija **Retiro en el local**. |
| **Pago** | `POST /api/ordenes` crea la orden `PENDIENTE` y una preferencia de pago en Mercado Pago; la app abre el `init_point`. |
| **Webhook** | `POST /api/webhooks/mercadopago` verifica el pago contra la API de MP y actualiza la orden a `APROBADO` / `RECHAZADO`. |
| **Ticket** | Pantalla para consultar el estado por número de orden (con historial); el staff puede marcar `ENTREGADO`. |

## Arquitectura

```
App móvil (Flet)  --HTTP/REST-->  Backend FastAPI  -->  MySQL
        ^                                  ^
        |  init_point / webhook            | Webhook (notificación)
        +-------------------------- Mercado Pago API
```

## Estructura del proyecto

```
.
├── database/schema.sql          # Esquema MySQL (tablas + historial)
├── backend/                     # FastAPI + PyMySQL + SDK Mercado Pago
│   ├── main.py                  # App FastAPI (CORS, routers, /health)
│   ├── config.py                # Lee .env (DB, MP, servidor)
│   ├── database.py              # Conexión PyMySQL + helpers
│   ├── schemas.py               # Modelos Pydantic
│   ├── mercadopago_service.py   # Preferencia + verificación de pago
│   ├── seed.py                  # Catálogo inicial (6 productos)
│   └── routers/
│       ├── productos.py         # GET /api/productos
│       ├── ordenes.py           # POST /api/ordenes, GET /api/ordenes/{id},
│       │                        # POST /api/ordenes/{id}/entregar
│       └── webhooks.py          # POST /api/webhooks/mercadopago
├── app/                         # Cliente Flet (5 vistas)
│   ├── main.py                  # Entrada y navegación
│   ├── config.py / api.py / state.py
│   └── views/                   # catálogo, carrito, checkout, estado
├── tests/                       # test_api.py y test_flet.py (sin MySQL ni MP real)
├── .vscode/                     # extensiones, settings, tareas y debug listos
├── docker-compose.yml           # MySQL 8 opcional (docker compose up -d)
├── run_backend.bat              # Inicia el backend (uvicorn)
├── run_app.bat                  # Inicia la app Flet
├── requirements.txt
└── .env / .env.example          # Configuración (no subir .env!)
```

## Requisitos

- Python 3.10+ (probado con 3.11)
- MySQL 8.x corriendo localmente
- Cuenta de desarrollador de [Mercado Pago](https://www.mercadopago.com.ar/developers)
  (para desarrollo se usan credenciales de prueba `TEST-...`)

## Puesta en marcha (Windows)

### 1. Entorno virtual + dependencias

```bat
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2. Base de datos MySQL

**Opción A) Con Docker (lo más rápido).** Con Docker Desktop instalado, en la raíz
del proyecto:

```bat
docker compose up -d
```

Crea el contenedor `fabrica_pastas_mysql` (MySQL 8, root/root) y carga el esquema
automáticamente.

**Opción B) Con un MySQL instalado.** En un cliente MySQL (root u otro usuario), ejecutá:

```sql
SOURCE C:/Users/.../database/schema.sql;
```

> El esquema crea la base `fabrica_pastas`, las tablas `productos`, `ordenes`,
> `detalle_orden` y `orden_historial`.

### 3. Configuración `.env`

Copiá `.env.example` a `.env` y completá como mínimo:

```
DB_USER=root
DB_PASSWORD=tu_password
MP_ACCESS_TOKEN=TEST-xxxx-...          # credenciales de prueba de MP
MP_NOTIFICATION_URL=https://xxxx.ngrok-free.app/api/webhooks/mercadopago   # opcional
MP_WEBHOOK_SECRET=                     # opcional: firma del webhook (ver sección Seguridad)
CORS_ORIGINS=*                         # opcional: restringir a orígenes reales en producción
ADMIN_TOKEN=cambiar-me                 # token de staff, exclusivo del backend
API_BASE_URL=http://127.0.0.1:8000
```

### 4. Catálogo inicial

```bat
.venv\Scripts\python.exe -m backend.seed
```

### 5. Correr

```bat
run_backend.bat        # o: .venv\Scripts\python.exe -m uvicorn backend.main:app --reload
run_app.bat            # o: .venv\Scripts\flet.exe run app\main.py
```

- API y documentación interactiva: http://127.0.0.1:8000/docs
- Estado del servicio: http://127.0.0.1:8000/health

## Trabajar en VS Code

### Extensiones recomendadas

El proyecto incluye `.vscode/extensions.json`. Al abrir la carpeta, VS Code ofrece
instalarlas (pestaña *Extensions* → *Recommended*). Las principales:

| Extensión | ID | Para qué |
|---|---|---|
| **Python** | `ms-python.python` | IntelliSense, entorno virtual, depuración. |
| **Pylance** | `ms-python.vscode-pylance` | Análisis de tipos. |
| **debugpy** | `ms-python.debugpy` | Depurador (F5). |
| **Database Client** | `cweijan.vscode-database-client2` | Ver y editar la base MySQL dentro de VS Code. |

### Ver la base de datos en VS Code (Database Client)

1. Instalá la extensión **Database Client** (ver arriba).
2. Con MySQL corriendo (paso 2 de la puesta en marcha), abrí el panel **DATABASE**
   en la barra lateral izquierda.
3. Clic en el botón **`+`** (nueva conexión) → elegí **MySQL**.
4. Completá (coinciden con `.env` local):

   | Campo | Valor |
   |---|---|
   | Host | `localhost` |
   | Port | `3306` |
   | User | `root` |
   | Password | la de tu `.env` (`DB_PASSWORD`) |
   | Database | `fabrica_pastas` |

5. **Connect** y listo: vas a ver `productos`, `ordenes`, `detalle_orden` y
   `orden_historial`. Hacé doble clic en una tabla para ver y editar sus filas,
   o abrí un editor SQL con *Open Query* para escribir consultas.

> La conexión no se guarda en el repositorio (se almacena en tu VS Code).
> Si Docker fue el método usado para MySQL, usuario/contraseña son `root` / `root`.

### Tareas y depuración integradas

El proyecto trae `.vscode/tasks.json` y `.vscode/launch.json`:

- **Terminal → Run Task…** → *Iniciar backend (FastAPI)*, *Iniciar app Flet*,
  *Cargar catálogo (seed)*, *Ejecutar pruebas de la API/app Flet*.
- **Run and Debug (F5)** → *Backend (uvicorn)*, *App Flet (cliente)*,
  *Seed del catálogo* con breakpoints.
- `settings.json` apunta el intérprete de Python al `.venv` del proyecto
  automáticamente.

## Endpoints

| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/api/productos` | Catálogo de pastas por caja. |
| `POST` | `/api/ordenes` | Crea la orden (`PENDIENTE`) + preferencia MP. Devuelve `init_point`. |
| `GET` | `/api/ordenes/{id}` | Estado del ticket + items + historial. |
| `POST` | `/api/webhooks/mercadopago` | Webhook de MP que actualiza el estado del pago. |
| `POST` | `/api/ordenes/{id}/entregar` | Staff marca la orden `ENTREGADO` (header `X-Admin-Token`). |

## Probar pagos de punta a punta (webhooks)

1. Levantá el backend y exponela públicamente con un túnel, p. ej. ngrok:
   `ngrok http 8000`.
2. Configurá `MP_NOTIFICATION_URL` en `.env` con
   `https://<tu-tunel>/api/webhooks/mercadopago` y reiniciá el backend.
3. Hacé un pedido en la app y pagá con las **tarjetas de prueba** de Mercado Pago
   (ver documentación de MP para los números de prueba).
4. Mercado Pago notificará automáticamente y el webhook actualizará la orden a
   `APROBADO`. Verificalo con `GET /api/ordenes/{id}` o en la pestaña "Mi ticket".

> Sin `MP_NOTIFICATION_URL`, igual se puede usar el link de pago; recibirás la
> actualización via webhook solo cuando el backend sea accesible desde internet.

## Pruebas automáticas

Las pruebas no requieren MySQL ni Mercado Pago real (usan almacenamiento en memoria
y mockean el SDK):

```bat
.venv\Scripts\python.exe tests\test_api.py    :: flujo completo de la API + webhooks
.venv\Scripts\python.exe tests\test_flet.py   :: construcción de vistas y flujo de checkout
```

## Seguridad

- Los totales SIEMPRE se calculan en el servidor (el precio unitario se lee de la
  tabla `productos`), evitando manipulación del precio desde la app.
- `ADMIN_TOKEN` es exclusivo del backend: la app Flet **no** lo lee de `.env`. Cuando
  el personal toca "Marcar como entregada" en la pantalla de ticket, se le pide el
  token en un diálogo y viaja solo en ese request — así no queda embebido en el
  paquete distribuido de la app.
- El webhook de Mercado Pago valida la firma `x-signature` si configurás
  `MP_WEBHOOK_SECRET` (panel de la app en MP → Webhooks → "Firma secreta"). Sin ese
  secreto, el webhook sigue funcionando pero no puede verificar que la notificación
  venga realmente de Mercado Pago (aceptable en desarrollo, no en producción).
- CORS no usa `allow_credentials=True` (la API no usa cookies) y los orígenes se
  restringen con `CORS_ORIGINS` en `.env`.

## Notas

- La preferencia de MP usa `external_reference = id_orden` como respaldo para
  asociar el webhook a la orden.
- Modo invitado: No se piden cuentas; solo contacto y retiro en el local.
- El carrito se guarda en disco (`app/state.py`, `cart.json` en el directorio de
  datos de Flet) para sobrevivir a un cierre accidental de la app.