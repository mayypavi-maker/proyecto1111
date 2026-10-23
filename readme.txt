comandos importantes.
//para limpiar la bd
python -c "import sqlite3; con = sqlite3.connect('Votaid.db'); cur = con.cursor(); cur.execute('UPDATE usuarios SET ya_voto = 0'); cur.execute('UPDATE resultados SET votos = 0'); con.commit(); print('Reseteado'); con.close()"

//para abrir el servidor 
/activar entorno
.venv\Scripts\activate
/verificar que este funcionando facercognition
python -c "import face_recognition; print('OK')"
/para abrir el host
python app.python


resetttttt
python -c "import sqlite3; con = sqlite3.connect('Votaid.db'); cur = con.cursor(); cur.execute('UPDATE usuarios SET ya_voto = 0'); cur.execute('UPDATE resultados SET votos = 0'); con.commit(); print('Reset'); con.close()"

