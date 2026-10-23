import sqlite3

con = sqlite3.connect("Votaid.db")
cur = con.cursor()

# Cambiá esta línea según lo que quieras probar:
cur.execute("""
    UPDATE jornada
    SET cerrada = 0,
        fecha_inicio = '2026-08-09T20:00',
        fecha_cierre = '2026-08-20T16:00'
    WHERE id = 1
""")

con.commit()
con.close()

print("Estado actualizado")