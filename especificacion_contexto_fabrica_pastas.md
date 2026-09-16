# Especificación Técnica y Arquitectura: App Móvil "Fábrica de Pastas"

## 1. Visión General del Proyecto
Aplicación móvil desarrollada en **Python con Flet** orientada a la venta de pastas artesanales por caja. Permite a usuarios realizar pedidos en modalidad **invitado** con retiro en el local, generando cupones/links de pago mediante **Mercado Pago**. El servidor (**FastAPI/Flask + MySQL**) gestiona las órdenes, sincroniza los estados de pago mediante Webhooks y permite la verificación posterior.

---

## 2. Arquitectura del Sistema

```
+------------------------------+             +------------------------------+
|   App Móvil (Flet Client)    |             |   Servidor Backend (Python)  |
| - Catálogo por caja          |  HTTP / REST| - API REST (FastAPI / Flask) |
| - Carrito de compras         | ----------> | - Integración Mercado Pago   |
| - Datos de contacto          |             | - Base de Datos MySQL        |
+------------------------------+             +------------------------------+
               |                                            ^
               | Redirección Pago                           | Webhook (Notificación)
               v                                            |
+---------------------------------------------------------------------------+
|                           Mercado Pago API                                |
+---------------------------------------------------------------------------+
```

---

## 3. Requerimientos Funcionales

### 3.1 App Móvil (Flet)
1. **Catálogo de Productos:**
   - Visualización de pastas (Ravioles, Fideos, Sorrentinos, Ñoquis, etc.).
   - Precios unitarios expresados por **caja**.
   - Selección de cantidades e incorporación al carrito.
2. **Carrito de Compras y Checkout:**
   - Resumen del pedido con cálculo del total.
   - Formulario de contacto mínimo para invitados (Nombre, Apellido, Teléfono/WhatsApp).
   - Confirmación de modalidad: *Retiro en el local*.
3. **Generación de Pago:**
   - Solicitud de creación de orden al backend.
   - Recepción de URL / Cupón de pago de Mercado Pago.
   - Apertura del checkout de Mercado Pago en la app/navegador.
4. **Consulta de Estado del Ticket:**
   - Pantalla de confirmación con el código/ID de orden.
   - Consulta del estado de la orden (*Pendiente*, *Aprobado*, *Rechazado*).

### 3.2 Backend / Servidor (Python)
1. **Gestión de Catálogo y Pedidos:**
   - Endpoints para listar productos.
   - Endpoint para recibir la orden y registrarla en MySQL como `PENDIENTE`.
2. **Integración con Mercado Pago:**
   - Creación de preferencia de pago (Preference ID) enviando los items y datos del cliente.
   - Configuración de `notification_url` para recibir Webhooks de Mercado Pago.
3. **Manejo de Webhooks:**
   - Endpoint `/webhook/mercadopago` para recibir alertas automáticas en tiempo real.
   - Verificación de la transacción en la API de Mercado Pago y actualización del estado en MySQL (`APROBADO`, `RECHAZADO`).
4. **Verificación e Inspección (Panel / Endpoint):**
   - Endpoint `/ordenes/{id_orden}` para consultar el estado actual del ticket y su historial.

---

## 4. Modelo de Base de Datos (MySQL)

```sql
CREATE DATABASE IF NOT EXISTS fabrica_pastas;
USE fabrica_pastas;

-- Tabla de Productos
CREATE TABLE productos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT,
    precio_caja DECIMAL(10, 2) NOT NULL,
    imagen_url VARCHAR(255),
    activo BOOLEAN DEFAULT TRUE
);

-- Tabla de Órdenes / Tickets
CREATE TABLE ordenes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cliente_nombre VARCHAR(100) NOT NULL,
    cliente_telefono VARCHAR(50) NOT NULL,
    tipo_entrega ENUM('RETIRO_LOCAL') DEFAULT 'RETIRO_LOCAL',
    total DECIMAL(10, 2) NOT NULL,
    estado ENUM('PENDIENTE', 'APROBADO', 'RECHAZADO', 'ENTREGADO') DEFAULT 'PENDIENTE',
    mp_preference_id VARCHAR(255),
    mp_payment_id VARCHAR(255),
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Detalle de la Orden
CREATE TABLE detalle_orden (
    id INT AUTO_INCREMENT PRIMARY KEY,
    orden_id INT NOT NULL,
    producto_id INT NOT NULL,
    cantidad_cajas INT NOT NULL,
    precio_unitario DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (orden_id) REFERENCES ordenes(id) ON DELETE CASCADE,
    FOREIGN KEY (producto_id) REFERENCES productos(id)
);
```

---

## 5. Especificación de Endpoints API (REST)

| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/api/productos` | Obtiene el catálogo de pastas por caja. |
| `POST` | `/api/ordenes` | Recibe el carrito, crea la orden en DB y genera la preferencia en Mercado Pago. |
| `GET` | `/api/ordenes/{id}` | Consulta el estado actual del ticket/orden. |
| `POST` | `/api/webhooks/mercadopago` | Recibe la notificación de pago desde Mercado Pago y actualiza la BD. |

---

## 6. Flujo de Trabajo (Paso a Paso)

1. **Cliente en la App Mobile:**
   - Navega por el menú de pastas y agrega cajas de ravioles/fideos al carrito.
   - Toca "Finalizar Compra", ingresa su Nombre y Teléfono.
2. **Procesamiento de la Orden:**
   - Flet envía un `POST /api/ordenes` con los items e información del comprador.
   - El Servidor inserta la orden en MySQL con estado `PENDIENTE`.
   - El Servidor llama a la SDK de Mercado Pago para crear la preferencia y obtiene el enlace de pago (`init_point`).
3. **Pago:**
   - La app abre la pasarela de Mercado Pago. El cliente paga (dinero en cuenta, tarjeta, débito, etc.).
4. **Actualización Automática (Webhook):**
   - Mercado Pago notifica al Servidor vía `POST /api/webhooks/mercadopago`.
   - El Servidor consulta a Mercado Pago el estado del `payment_id`.
   - Si el pago fue exitoso, actualiza el estado de la orden en MySQL a `APROBADO`.
5. **Retiro y Verificación:**
   - El cliente se presenta en el local con su número de ticket/orden.
   - El personal del local consulta el sistema para verificar que la orden figura como `APROBADO` antes de entregar las cajas de pasta.
