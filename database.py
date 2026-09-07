import os
import sqlite3


RUTA_BASE_DATOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Votaid.db")


def iniciar_base_datos():
    conexion = sqlite3.connect(RUTA_BASE_DATOS)
    cursor = conexion.cursor()

    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS usuarios (
                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                       nombre TEXT NOT NULL,
                       dni TEXT NOT NULL,
                       foto_nombre TEXT NOT NULL,
                       ya_voto INTEGER DEFAULT 0,
                       fecha_hora_voto TEXT
                   )
                   """)

    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS partidos(
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   nombre TEXT NOT NULL,
                   votos INTEGER DEFAULT 0
                   )
                   """)

    conexion.commit()
    conexion.close()


def guardar_votante(nombre, dni, foto_nombre):
    conexion = sqlite3.connect(RUTA_BASE_DATOS)
    cursor = conexion.cursor()

    cursor.execute(
        "INSERT INTO usuarios (nombre, dni, foto_nombre) VALUES (?, ?, ?)",
        (nombre, dni, foto_nombre)
    )

    conexion.commit()
    conexion.close()
    
def buscar_votante(dni):
    conexion = sqlite3.connect(RUTA_BASE_DATOS)
    cursor = conexion.cursor()

    cursor.execute(
        "SELECT * FROM usuarios WHERE dni = ?",
        (dni,)
    )

    votante = cursor.fetchone()

    conexion.close()

    return votante