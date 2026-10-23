import sqlite3

con = sqlite3.connect("Votaid.db")
cur = con.cursor()

cur.execute("""
    CREATE TABLE IF NOT EXISTS candidatos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        partido_id INTEGER NOT NULL,
        categoria TEXT NOT NULL,
        nombre TEXT NOT NULL,
        foto_nombre TEXT NOT NULL,
        FOREIGN KEY (partido_id) REFERENCES partidos(id)
    )
""")

con.commit()
con.close()

print("Tabla candidatos creada")
