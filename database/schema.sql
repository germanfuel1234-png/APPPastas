-- ============================================================
-- Esquema de base de datos: Fábrica de Pastas (MySQL)
-- Basado en la especificación_contexto_fabrica_pastas.md
-- ============================================================

CREATE DATABASE IF NOT EXISTS fabrica_pastas;
USE fabrica_pastas;

-- Tabla de Productos
CREATE TABLE IF NOT EXISTS productos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT,
    precio_caja DECIMAL(10, 2) NOT NULL,
    imagen_url VARCHAR(255),
    activo BOOLEAN DEFAULT TRUE
);

-- Tabla de Órdenes / Tickets
CREATE TABLE IF NOT EXISTS ordenes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cliente_nombre VARCHAR(100) NOT NULL,
    cliente_telefono VARCHAR(50) NOT NULL,
    tipo_entrega ENUM('RETIRO_LOCAL') DEFAULT 'RETIRO_LOCAL',
    total DECIMAL(10, 2) NOT NULL,
    estado ENUM('PENDIENTE', 'APROBADO', 'RECHAZADO', 'ENTREGADO') DEFAULT 'PENDIENTE',
    mp_preference_id VARCHAR(255),
    mp_payment_id VARCHAR(255),
    mp_init_point VARCHAR(500),
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Detalle de la Orden
CREATE TABLE IF NOT EXISTS detalle_orden (
    id INT AUTO_INCREMENT PRIMARY KEY,
    orden_id INT NOT NULL,
    producto_id INT NOT NULL,
    cantidad_cajas INT NOT NULL,
    precio_unitario DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (orden_id) REFERENCES ordenes(id) ON DELETE CASCADE,
    FOREIGN KEY (producto_id) REFERENCES productos(id)
);

-- Historial de estados de cada orden (PENDIENTE -> APROBADO / RECHAZADO / ENTREGADO)
CREATE TABLE IF NOT EXISTS orden_historial (
    id INT AUTO_INCREMENT PRIMARY KEY,
    orden_id INT NOT NULL,
    estado ENUM('PENDIENTE', 'APROBADO', 'RECHAZADO', 'ENTREGADO') NOT NULL,
    detalle VARCHAR(255) DEFAULT '',
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (orden_id) REFERENCES ordenes(id) ON DELETE CASCADE
);

-- Índices para búsquedas frecuentes
CREATE INDEX IF NOT EXISTS idx_ordenes_estado ON ordenes(estado);
CREATE INDEX IF NOT EXISTS idx_ordenes_preference ON ordenes(mp_preference_id);
CREATE INDEX IF NOT EXISTS idx_detalle_orden ON detalle_orden(orden_id);
CREATE INDEX IF NOT EXISTS idx_historial_orden ON orden_historial(orden_id);