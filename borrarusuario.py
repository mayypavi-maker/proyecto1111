import sqlite3
conexion=sqlite3.connect("Votaid.db")
cursor=conexion.cursor()
cursor.execute("DELETE FROM usuarios WHERE dni = ?", ("12345678",))
conexion.commit()
conexion.close()