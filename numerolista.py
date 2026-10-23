import sqlite3

con = sqlite3.connect("Votaid.db")
cur = con.cursor()

try:
    cur.execute("ALTER TABLE usuarios ADD COLUMN sexo INTEGER")
    print("Columna sexo agregada")
except sqlite3.OperationalError as e:
    print(f"La columna ya existe: {e}")

con.commit()
con.close()
print("Números de lista cargados")
