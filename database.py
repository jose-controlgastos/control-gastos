import sqlite3
import hashlib

def conectar_db():
    return sqlite3.connect("control_obras_PRO.db")

def inicializar_sistema():
    conexion = conectar_db()
    cursor = conexion.cursor()
    
    # 1. Tabla de Usuarios
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        usuario TEXT PRIMARY KEY,
        contrasena TEXT NOT NULL,
        nombre TEXT NOT NULL
    )
    """)
    
    # 2. Tabla de Proveedores y Trabajadores (Suministros y Mano de Obra)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS contactos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL UNIQUE,
        tipo TEXT NOT NULL, -- 'Trabajador' o 'Proveedor'
        telefono TEXT
    )
    """)
    
    # 3. Tabla de Gastos mejorada
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS gastos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT NOT NULL,
        categoria TEXT NOT NULL,
        contacto_id INTEGER,
        concepto TEXT NOT NULL,
        importe REAL NOT NULL,
        usuario_registro TEXT,
        FOREIGN KEY(contacto_id) REFERENCES contactos(id),
        FOREIGN KEY(usuario_registro) REFERENCES usuarios(usuario)
    )
    """)
    
    # Crear un usuario administrador de prueba si no existe (Usuario: admin, Clave: 1234)
    password_hasheada = hashlib.sha256("1234".encode()).hexdigest()
    cursor.execute("INSERT OR IGNORE INTO usuarios VALUES (?, ?, ?)", ("admin", password_hasheada, "Encargado General"))
    
    conexion.commit()
    conexion.close()

if __name__ == "__main__":
    inicializar_sistema()
    print("Base de datos profesional inicializada correctamente.")
