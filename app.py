import os
import face_recognition
import re
import subprocess
import sqlite3
import cv2
from dotenv import load_dotenv

load_dotenv()
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from database import guardar_votante, iniciar_base_datos, buscar_votante
from functools import wraps

def requiere_admin(f):
    @wraps(f)
    def decorada(*args, **kwargs):
        if not session.get("admin_logueado"):
            return redirect(url_for("loginadmin"))
        return f(*args, **kwargs)
    return decorada

app= Flask(__name__)

detector_rostros = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

USUARIO_ADMIN = os.environ.get("ADMIN_USUARIO", "amaia")
CONTRASENA_ADMIN = os.environ.get("ADMIN_PASSWORD", "votaid2026")
app.secret_key = os.environ.get("SECRET_KEY", "votaid.2026")

iniciar_base_datos()

@app.route('/')
def inicio():
    return render_template('index.html')

@app.route("/registro")
def registro():
    # Limpiar cualquier sesión anterior de votación
    session.pop("dni", None)
    session.pop("nombre", None)
    session.pop("rostro_verificado", None)

    return render_template("registro.html")

@app.route("/registrar", methods=["POST"])
def registrar():
        # --- Revisar el estado de la jornada ---
    estado = obtener_estado_jornada()

    if estado == "no_iniciada":
        return render_template(
            "registro.html",
            error="La jornada electoral todavía no ha comenzado."
        )

    if estado == "cerrada":
        return render_template(
            "registro.html",
            error="La jornada electoral está cerrada. Ya no se puede votar."
        )
    dni = request.form.get("dni")

    if not dni:
        return render_template("registro.html", error="Ingresá tu DNI.")

    votante = buscar_votante(dni)

    if not votante:
        return render_template(
            "registro.html",
            error="El DNI no corresponde a un votante registrado."
        )

    # --- revisar si ya votó ---
    if votante[4] == 1:
        return render_template(
            "registro.html",
            error="Ya registramos tu voto. No podés votar dos veces."
        )

    # Guardamos el DNI en la sesión para usarlo después
    session["dni"] = dni
    session["nombre"] = votante[1]  # votante[1] es el nombre

    return redirect(url_for("reconocimiento"))

@app.route("/reconocimiento")
def reconocimiento():
    dni = session.get("dni")

    if not dni:
        # Si alguien entra directo sin pasar por /registro
        return redirect(url_for("registro"))

    return render_template("reconocimiento.html", dni=dni)

@app.route("/loginadmin", methods=["GET", "POST"])
def loginadmin():
    if request.method == "POST":
        usuario = request.form.get("usuario")
        contrasena = request.form.get("contrasena")

        if usuario == USUARIO_ADMIN and contrasena == CONTRASENA_ADMIN:
            session["admin_logueado"] = True
            return redirect(url_for("panel_admin"))
        return render_template("admin/loginadmin.html", error="Usuario o contraseña incorrectos")
    return render_template("admin/loginadmin.html")

def validar_nombre(nombre):
    if nombre is None:
        return False
    nombre = nombre.strip()
    return bool(re.fullmatch(r"[A-Za-zÁÉÍÓÚáéíóúÜüÑñ\s]+", nombre))

@app.route("/admin/panel")
@requiere_admin
def panel_admin():
    return render_template("admin/paneladmin.html")

@app.route("/admin/logout")
@requiere_admin
def admin_logout():
    session.pop("admin_logueado", None)
    return redirect(url_for("inicio"))


@app.route("/admin/registrarvotante", methods=["GET", "POST"])
@requiere_admin
def registrarvotante():
    if request.method == "POST":

        nombre = request.form.get("nombre")
        dni = request.form.get("dni")
        foto = request.files.get("foto")

        if not nombre or not dni:
            return render_template("admin/registrarvotante.html", error="Completa nombre y DNI."), 400

        nombre = nombre.strip()
        dni = dni.strip()

        if not validar_nombre(nombre):
            return render_template("admin/registrarvotante.html", error="El nombre solo puede contener letras, espacios y acentos."), 400

        if not re.fullmatch(r"\d{8}", dni):
            return render_template("admin/registrarvotante.html", error="El DNI debe tener solo números, sin puntos ni letras."), 400

        if not foto or foto.filename == "":
            return render_template("admin/registrarvotante.html", error="Debe seleccionar una foto antes de registrar."), 400

        print("Nombre:", nombre)
        print("DNI:", dni)
        print("Foto", foto.filename)

        carpeta = os.path.join(app.static_folder, "usuarios")
        os.makedirs(carpeta, exist_ok=True)

        nombre_archivo = dni + ".jpg"
        ruta_foto = os.path.join(carpeta, nombre_archivo)

        foto.save(ruta_foto)
        guardar_votante(nombre, dni, nombre_archivo)
        return render_template("admin/registrarvotante.html", mensaje="Votante registrado correctamente.")

    return render_template("admin/registrarvotante.html")

@app.route("/admin/captura")
@requiere_admin
def captura():

    return render_template("admin/captura.html")

@app.route("/capturar")
def capturar():

    subprocess.run(["python", "camara.py"])

    return redirect(url_for("registrarvotante"))

@app.route('/admin/administrarlista')
@requiere_admin
def administrarlista():
    return render_template('admin/administrarlista.html')

@app.route('/admin/administrarlista/votantes')
@requiere_admin
def administrar_votantes():
    buscar = request.args.get("buscar", "").strip()

    con = sqlite3.connect("Votaid.db")
    cur = con.cursor()

    # --- Contadores ---
    cur.execute("SELECT COUNT(*) FROM usuarios")
    total = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM usuarios WHERE ya_voto = 1")
    ya_votaron = cur.fetchone()[0]

    no_votaron = total - ya_votaron

    # --- Lista de votantes ---
    if buscar:
        cur.execute(
            "SELECT * FROM usuarios WHERE nombre LIKE ? OR dni LIKE ?",
            (f"%{buscar}%", f"%{buscar}%")
        )
    else:
        cur.execute("SELECT * FROM usuarios")

    usuarios = cur.fetchall()
    con.close()

    return render_template(
        'admin/administrarvotantes.html',
        usuarios=usuarios,
        total=total,
        ya_votaron=ya_votaron,
        no_votaron=no_votaron,
        buscar=buscar
    )

@app.route('/admin/administrarlista/candidatos')
@requiere_admin
def administrar_candidatos():
    con = sqlite3.connect("Votaid.db")
    cur = con.cursor()

    # 1. Traer TODOS los partidos
    cur.execute("SELECT id, nombre, numero_lista FROM partidos ORDER BY numero_lista")
    partidos_filas = cur.fetchall()

    # 2. Traer TODOS los candidatos
    cur.execute("SELECT id, partido_id, categoria, nombre, foto_nombre FROM candidatos")
    candidatos_filas = cur.fetchall()

    con.close()

    # 3. Armar la estructura: cada partido con su senador y diputado
    partidos = []
    for pid, pnombre, pnumero in partidos_filas:
        partido = {
            "id": pid,
            "nombre": pnombre,
            "numero_lista": pnumero,
            "senador": None,
            "diputado": None
        }

        # Buscar los candidatos de este partido
        for cid, cpid, categoria, cnombre, cfoto in candidatos_filas:
            if cpid == pid:
                if categoria == "senador":
                    partido["senador"] = {"id": cid, "nombre": cnombre, "foto": cfoto}
                elif categoria == "diputado":
                    partido["diputado"] = {"id": cid, "nombre": cnombre, "foto": cfoto}

        partidos.append(partido)

    return render_template(
        'admin/administrarcandidatos.html',
        partidos=partidos
    )

@app.route("/admin/candidatos/agregar_lista", methods=["GET", "POST"])
@requiere_admin
def agregar_lista():
    if request.method == "POST":
        # --- Leer los datos del formulario ---
        nombre_partido = request.form.get("nombre_partido", "").strip()
        numero_lista = request.form.get("numero_lista", "").strip()
        nombre_senador = request.form.get("nombre_senador", "").strip()
        foto_senador = request.form.get("foto_senador", "").strip()
        nombre_diputado = request.form.get("nombre_diputado", "").strip()
        foto_diputado = request.form.get("foto_diputado", "").strip()

        # --- Validar que estén todos los campos ---
        if not all([nombre_partido, numero_lista, nombre_senador, foto_senador, nombre_diputado, foto_diputado]):
            return render_template(
                "admin/agregarlista.html",
                error="Todos los campos son obligatorios."
            )

        # --- Validar que el número de lista sea numérico ---
        if not numero_lista.isdigit():
            return render_template(
                "admin/agregarlista.html",
                error="El número de lista debe ser numérico."
            )

        con = sqlite3.connect("Votaid.db")
        cur = con.cursor()

        # --- Verificar que no exista ya ese número de lista ---
        cur.execute("SELECT id FROM partidos WHERE numero_lista = ?", (numero_lista,))
        existe = cur.fetchone()
        if existe:
            con.close()
            return render_template(
                "admin/agregarlista.html",
                error=f"Ya existe una lista con el número {numero_lista}."
            )

        # --- Verificar que las fotos existan ---
        ruta_senador = os.path.join(app.static_folder, "img", foto_senador)
        ruta_diputado = os.path.join(app.static_folder, "img", foto_diputado)

        if not os.path.exists(ruta_senador):
            con.close()
            return render_template(
                "admin/agregarlista.html",
                error=f"No se encontró la foto '{foto_senador}' en static/img/."
            )

        if not os.path.exists(ruta_diputado):
            con.close()
            return render_template(
                "admin/agregarlista.html",
                error=f"No se encontró la foto '{foto_diputado}' en static/img/."
            )

        # --- Insertar el partido ---
        cur.execute(
            "INSERT INTO partidos (nombre, numero_lista, votos) VALUES (?, ?, 0)",
            (nombre_partido, int(numero_lista))
        )
        partido_id = cur.lastrowid

        # --- Insertar los candidatos ---
        cur.execute(
            "INSERT INTO candidatos (partido_id, categoria, nombre, foto_nombre) VALUES (?, 'senador', ?, ?)",
            (partido_id, nombre_senador, foto_senador)
        )
        cur.execute(
            "INSERT INTO candidatos (partido_id, categoria, nombre, foto_nombre) VALUES (?, 'diputado', ?, ?)",
            (partido_id, nombre_diputado, foto_diputado)
        )

        # --- Crear los contadores en la tabla resultados ---
        cur.execute(
            "INSERT INTO resultados (partido_id, categoria, votos) VALUES (?, 'senador', 0)",
            (partido_id,)
        )
        cur.execute(
            "INSERT INTO resultados (partido_id, categoria, votos) VALUES (?, 'diputado', 0)",
            (partido_id,)
        )

        con.commit()
        con.close()

        return redirect(url_for("administrar_candidatos"))

    # GET: mostrar el formulario
    return render_template("admin/agregarlista.html")

@app.route("/admin/candidatos/eliminar_lista/<int:partido_id>")
@requiere_admin
def eliminar_lista(partido_id):
    con = sqlite3.connect("Votaid.db")
    cur = con.cursor()

    # Verificar que el partido exista
    cur.execute("SELECT id FROM partidos WHERE id = ?", (partido_id,))
    if not cur.fetchone():
        con.close()
        return redirect(url_for("administrar_candidatos"))

    # Eliminar los candidatos del partido
    cur.execute("DELETE FROM candidatos WHERE partido_id = ?", (partido_id,))

    # Eliminar los contadores en resultados
    cur.execute("DELETE FROM resultados WHERE partido_id = ?", (partido_id,))

    # Eliminar el partido
    cur.execute("DELETE FROM partidos WHERE id = ?", (partido_id,))

    con.commit()
    con.close()

    return redirect(url_for("administrar_candidatos"))
@app.route("/admin/candidatos/agregar", methods=["GET", "POST"])
@requiere_admin
def agregar_candidato():
    con = sqlite3.connect("Votaid.db")
    cur = con.cursor()

    # Traer los partidos para el <select> del formulario
    cur.execute("SELECT id, nombre FROM partidos ORDER BY id")
    partidos = cur.fetchall()

    if request.method == "POST":
        partido_id = request.form.get("partido_id")
        categoria = request.form.get("categoria")
        nombre = request.form.get("nombre", "").strip()
        foto_nombre = request.form.get("foto_nombre", "").strip()

        # --- Validaciones ---
        if not partido_id or not categoria or not nombre or not foto_nombre:
            con.close()
            return render_template(
                "admin/agregarcandidatos.html",
                partidos=partidos,
                error="Todos los campos son obligatorios."
            )

        if categoria not in ("senador", "diputado"):
            con.close()
            return render_template(
                "admin/agregarcandidatos.html",
                partidos=partidos,
                error="Categoría inválida."
            )

        # --- Verificar que no exista ya un candidato de esa categoría en ese partido ---
        cur.execute(
            "SELECT id FROM candidatos WHERE partido_id = ? AND categoria = ?",
            (partido_id, categoria)
        )
        existe = cur.fetchone()

        if existe:
            con.close()
            return render_template(
                "admin/agregarcandidatos.html",
                partidos=partidos,
                error="Ya hay un candidato de esa categoría para este partido."
            )

        # --- Verificar que la foto exista en la carpeta ---
        ruta_foto = os.path.join(app.static_folder, "img", "partidos", foto_nombre)
        if not os.path.exists(ruta_foto):
            con.close()
            return render_template(
                "admin/agregarcandidatos.html",
                partidos=partidos,
                error=f"No se encontró la foto '{foto_nombre}' en la carpeta de imágenes."
            )

        # --- Guardar ---
        cur.execute(
            "INSERT INTO candidatos (partido_id, categoria, nombre, foto_nombre) VALUES (?, ?, ?, ?)",
            (partido_id, categoria, nombre, foto_nombre)
        )
        con.commit()
        con.close()

        return redirect(url_for("administrarcandidatos"))

    con.close()
    return render_template(
        "admin/agregarcandidatos.html",
        partidos=partidos
    )
@app.route('/admin/resultados')
@requiere_admin
def resultados():
    con = sqlite3.connect("Votaid.db")
    cur = con.cursor()

    # Votos por partido, separados por categoría
    cur.execute("""
        SELECT p.id, p.nombre, p.numero_lista, r.categoria, r.votos
        FROM resultados r
        JOIN partidos p ON p.id = r.partido_id
        ORDER BY r.categoria, r.votos DESC, p.numero_lista ASC
    """)
    filas = cur.fetchall()

    # Separar en dos listas
    senadores = []
    diputados = []

    for pid, nombre, numero_lista, categoria, votos in filas:
        item = {
            "id": pid,
            "nombre": nombre,
            "numero_lista": numero_lista,
            "votos": votos
        }
        if categoria == "senador":
            senadores.append(item)
        else:
            diputados.append(item)

    # Totales por categoría (para calcular %)
    total_senadores = sum(p["votos"] for p in senadores)
    total_diputados = sum(p["votos"] for p in diputados)

    # Calcular porcentajes
    for p in senadores:
        p["porcentaje"] = round((p["votos"] / total_senadores) * 100, 1) if total_senadores > 0 else 0

    for p in diputados:
        p["porcentaje"] = round((p["votos"] / total_diputados) * 100, 1) if total_diputados > 0 else 0

    # Participación
    cur.execute("SELECT COUNT(*) FROM usuarios WHERE ya_voto = 1")
    votaron = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM usuarios")
    total = cur.fetchone()[0]

    con.close()

    porcentaje_participacion = round((votaron / total) * 100, 1) if total > 0 else 0

    return render_template(
        "admin/resultados.html",
        senadores=senadores,
        diputados=diputados,
        votaron=votaron,
        total=total,
        porcentaje_participacion=porcentaje_participacion
    )

@app.route("/admin/cerrar_jornada", methods=["POST"])
@requiere_admin
def cerrar_jornada():
    con = sqlite3.connect("Votaid.db")
    cur = con.cursor()
    cur.execute("UPDATE jornada SET cerrada = 1 WHERE id = 1")
    con.commit()
    con.close()

    return redirect(url_for("resultados"))

from datetime import datetime

def obtener_estado_jornada():
    """
    Devuelve el estado actual de la jornada:
    - "no_iniciada": todavía no llegó la fecha de inicio
    - "activa": entre inicio y cierre
    - "cerrada": pasó la fecha de cierre o se cerró manualmente
    """
    con = sqlite3.connect("Votaid.db")
    cur = con.cursor()
    cur.execute("SELECT cerrada, fecha_inicio, fecha_cierre FROM jornada WHERE id = 1")
    fila = cur.fetchone()

    if not fila:
        con.close()
        return "activa"  # Si no hay fila, por defecto activa

    cerrada_manual = fila[0] == 1
    fecha_inicio_str = fila[1]
    fecha_cierre_str = fila[2]

    # Si está cerrada manualmente, listo
    if cerrada_manual:
        con.close()
        return "cerrada"

    ahora = datetime.now()

    # Chequear fecha de inicio
    if fecha_inicio_str:
        try:
            inicio = datetime.fromisoformat(fecha_inicio_str)
            if ahora < inicio:
                con.close()
                return "no_iniciada"
        except ValueError:
            pass

    # Chequear fecha de cierre (auto-cierre)
    if fecha_cierre_str:
        try:
            cierre = datetime.fromisoformat(fecha_cierre_str)
            if ahora >= cierre:
                cur.execute("UPDATE jornada SET cerrada = 1 WHERE id = 1")
                con.commit()
                con.close()
                return "cerrada"
        except ValueError:
            pass

    con.close()
    return "activa"

@app.route('/admin/estadojornada')
@requiere_admin
def estado_jornada():
    con = sqlite3.connect("Votaid.db")
    cur = con.cursor()
    cur.execute("SELECT fecha_inicio, fecha_cierre FROM jornada WHERE id = 1")
    fila = cur.fetchone()
    con.close()

    fecha_inicio = fila[0] if fila else None
    fecha_cierre = fila[1] if fila else None

    estado = obtener_estado_jornada()

    return render_template(
        'admin/estadojornada.html',
        estado=estado,
        fecha_inicio=fecha_inicio,
        fecha_cierre=fecha_cierre
    )

@app.route("/votacion")
def votacion():
    dni = session.get("dni")
    rostro_ok = session.get("rostro_verificado")

    if not dni or not rostro_ok:
        return redirect(url_for("registro"))

    con = sqlite3.connect("Votaid.db")
    cur = con.cursor()

    # Traer todos los partidos ordenados por número de lista
    cur.execute("SELECT id, nombre, numero_lista FROM partidos ORDER BY numero_lista")
    partidos_filas = cur.fetchall()

    # Traer todos los candidatos
    cur.execute("SELECT id, partido_id, categoria, nombre, foto_nombre FROM candidatos")
    candidatos_filas = cur.fetchall()

    con.close()

    # Armar la estructura
    partidos = []
    for pid, pnombre, pnumero in partidos_filas:
        partido = {
            "id": pid,
            "nombre": pnombre,
            "numero_lista": pnumero,
            "senador": None,
            "diputado": None
        }

        for cid, cpid, categoria, cnombre, cfoto in candidatos_filas:
            if cpid == pid:
                if categoria == "senador":
                    partido["senador"] = {"id": cid, "nombre": cnombre, "foto": cfoto}
                elif categoria == "diputado":
                    partido["diputado"] = {"id": cid, "nombre": cnombre, "foto": cfoto}

        partidos.append(partido)

    return render_template("votacion.html", partidos=partidos)
    
@app.route("/verificar_rostro", methods=["POST"])
def verificar_rostro():
        # --- Revisar el estado de la jornada ---
    estado = obtener_estado_jornada()

    if estado == "no_iniciada":
        return jsonify({
            "coincide": False,
            "mensaje": "La jornada todavía no ha comenzado."
        })

    if estado == "cerrada":
        return jsonify({
            "coincide": False,
            "mensaje": "La jornada está cerrada. No se puede votar."
        })
    # -----------------------------------------------------------
    # El DNI ya fue validado en la pantalla 1
    # -----------------------------------------------------------
    foto = request.files.get("foto")
    dni = request.form.get("dni")

    # --- Guarda por si algo llegó mal desde el frontend ---
    if not foto:
        return jsonify({
            "coincide": False,
            "mensaje": "No se recibió la imagen desde la cámara. Intentá de nuevo."
        }), 400

    if not dni:
        return jsonify({
            "coincide": False,
            "mensaje": "Faltó el DNI. Volvé a la pantalla anterior."
        }), 400

    # -----------------------------------------------------------
    # Buscar al usuario en la BD
    # -----------------------------------------------------------
    con = sqlite3.connect("Votaid.db")
    cur = con.cursor()
    cur.execute(
        "SELECT id, nombre, foto_nombre, ya_voto FROM usuarios WHERE dni = ?",
        (dni,)
    )
    usuario = cur.fetchone()
    con.close()

    if not usuario:
        return jsonify({
            "coincide": False,
            "mensaje": "El DNI no figura en el padrón. Volvé a la pantalla anterior."
        })

    usuario_id, nombre, foto_nombre, ya_voto = usuario

  #bloqueooooooooooo
    # -----------------------------------------------------------
    # Cargar la foto del padrón (la que corresponde al DNI)
    # -----------------------------------------------------------
    ruta_foto_guardada = os.path.join("static", "usuarios", foto_nombre)

    if not os.path.exists(ruta_foto_guardada):
        return jsonify({
            "coincide": False,
            "mensaje": "Hubo un problema con tu foto del padrón. Avisá a las autoridades."
        })

    # -----------------------------------------------------------
    # Guardar la foto capturada temporalmente
    # -----------------------------------------------------------
    ruta_captura = "captura.jpg"
    foto.save(ruta_captura)

    # -----------------------------------------------------------
    # Cargar ambas imágenes
    # -----------------------------------------------------------
    try:
        img_guardada = face_recognition.load_image_file(ruta_foto_guardada)
        img_capturada = face_recognition.load_image_file(ruta_captura)
    except Exception:
        return jsonify({
            "coincide": False,
            "mensaje": "Hubo un error al procesar las imágenes. Avisá a las autoridades."
        }), 500

    # --- Obtener vectores faciales ---
    enc_guardada = face_recognition.face_encodings(img_guardada)
    enc_capturada = face_recognition.face_encodings(img_capturada)

    # --- Casos especiales ---
    if len(enc_guardada) == 0:
        return jsonify({
            "coincide": False,
            "mensaje": "Tu foto del padrón no es válida. Avisá a las autoridades."
        })

    if len(enc_capturada) == 0:
        return jsonify({
            "coincide": False,
            "mensaje": "No te pudimos ver bien. Acercate a la cámara e intentá de nuevo."
        })

    # -----------------------------------------------------------
    # LA VALIDACIÓN CLAVE: ¿coincide la cara con la del DNI?
    # -----------------------------------------------------------
    resultado = face_recognition.compare_faces(
        [enc_guardada[0]],
        enc_capturada[0],
        tolerance=0.5
    )

    if not resultado[0]:
        return jsonify({
            "coincide": False,
            "mensaje": "Tu rostro no coincide con el DNI ingresado"
        })

      # --- Bloqueo de doble voto ---
    if ya_voto == 1:
        return jsonify({
            "coincide": False,
            "ya_voto": True,
            "mensaje": f"{nombre}, ya registramos tu voto. No podés votar dos veces."
        })

    # -----------------------------------------------------------
    # Todo OK
    # -----------------------------------------------------------
    session["rostro_verificado"] = True
    session["dni"] = dni  # por lasdudaaas
    return jsonify({
        "coincide": True,
        "usuario_id": usuario_id,
        "nombre": nombre,
        "mensaje": "Rostro verificado correctamente."
    })

@app.route("/votar", methods=["POST"])
def votar():
        # --- Verificar que haya alguien en sesión con rostro verificado ---
    dni = session.get("dni")
    rostro_ok = session.get("rostro_verificado")

    if not dni or not rostro_ok:
        return redirect(url_for("registro"))

    # --- Verificar que el votante exista y no haya votado ---
    con = sqlite3.connect("Votaid.db")
    cur = con.cursor()
    cur.execute("SELECT id, nombre, ya_voto FROM usuarios WHERE dni = ?", (dni,))
    usuario = cur.fetchone()

    if not usuario:
        con.close()
        return redirect(url_for("registro"))

    usuario_id, nombre, ya_voto = usuario

    if ya_voto == 1:
        con.close()
        return render_template("votacion.html", error="Ya registramos tu voto. No podés votar dos veces.")

    senador_lista = request.form.get("senador")
    diputado_lista = request.form.get("diputado")

    if not senador_lista or not diputado_lista:
        con.close()
        return render_template("votacion.html", error="Tenés que elegir senador y diputado.")

    # Extraer el número de lista (ej: "lista101" → "101")
    def extraer_numero(valor_lista):
        if valor_lista and valor_lista.startswith("lista"):
            return valor_lista[5:]  # "lista101" → "101"
        return None

    numero_senador = extraer_numero(senador_lista)
    numero_diputado = extraer_numero(diputado_lista)

    if not numero_senador or not numero_diputado:
        con.close()
        return render_template("votacion.html", error="Hubo un error con tu elección. Intentá de nuevo.")

    # Buscar el partido por su numero_lista
    cur.execute("SELECT id FROM partidos WHERE numero_lista = ?", (numero_senador,))
    fila_senador = cur.fetchone()
    senador_id = fila_senador[0] if fila_senador else None

    cur.execute("SELECT id FROM partidos WHERE numero_lista = ?", (numero_diputado,))
    fila_diputado = cur.fetchone()
    diputado_id = fila_diputado[0] if fila_diputado else None

    if not senador_id or not diputado_id:
        con.close()
        return render_template("votacion.html", error="Hubo un error con tu elección. Intentá de nuevo.")
    
    # --- Guardar los votos y marcar al usuario ---
    try:
        cur.execute(
            "UPDATE resultados SET votos = votos + 1 WHERE partido_id = ? AND categoria = 'senador'",
            (senador_id,)
        )
        cur.execute(
            "UPDATE resultados SET votos = votos + 1 WHERE partido_id = ? AND categoria = 'diputado'",
            (diputado_id,)
        )
        cur.execute(
            "UPDATE usuarios SET ya_voto = 1 WHERE id = ?",
            (usuario_id,)
        )
        con.commit()
    except Exception as e:
        con.rollback()
        con.close()
        return render_template("votacion.html", error=f"Hubo un error al guardar tu voto: {e}")

    con.close()

    # --- Limpiar la sesión ---
    session.pop("dni", None)
    session.pop("nombre", None)
    session.pop("rostro_verificado", None)

       # --- Redirigir a pantalla de agradecimiento ---
    return redirect(url_for("voto_confirmado", nombre=nombre))

@app.route("/voto_confirmado")
def voto_confirmado():
    nombre = request.args.get("nombre", "")
    return render_template("voto_confirmado.html", nombre=nombre)

@app.route("/admin/guardar_fechas", methods=["POST"])
@requiere_admin
def guardar_fechas():
    fecha_inicio = request.form.get("fecha_inicio")
    fecha_cierre = request.form.get("fecha_cierre")

    if not fecha_inicio or not fecha_cierre:
        return redirect(url_for("estado_jornada"))

    # Verificar que la fecha de cierre sea posterior a la de inicio
    try:
        inicio_dt = datetime.fromisoformat(fecha_inicio)
        cierre_dt = datetime.fromisoformat(fecha_cierre)
        if cierre_dt <= inicio_dt:
            return redirect(url_for("estado_jornada"))
    except ValueError:
        return redirect(url_for("estado_jornada"))

    con = sqlite3.connect("Votaid.db")
    cur = con.cursor()
    cur.execute(
        "UPDATE jornada SET fecha_inicio = ?, fecha_cierre = ?, cerrada = 0 WHERE id = 1",
        (fecha_inicio, fecha_cierre)
    )
    con.commit()
    con.close()

    return redirect(url_for("estado_jornada"))

@app.route("/admin/reabrir_jornada", methods=["POST"])
@requiere_admin
def reabrir_jornada():
    fecha_inicio = request.form.get("fecha_inicio")
    fecha_cierre = request.form.get("fecha_cierre")

    if not fecha_inicio or not fecha_cierre:
        return redirect(url_for("estado_jornada"))

    # Verificar que la fecha de cierre sea posterior a la de inicio
    try:
        inicio_dt = datetime.fromisoformat(fecha_inicio)
        cierre_dt = datetime.fromisoformat(fecha_cierre)
        if cierre_dt <= inicio_dt:
            return redirect(url_for("estado_jornada"))
    except ValueError:
        return redirect(url_for("estado_jornada"))

    con = sqlite3.connect("Votaid.db")
    cur = con.cursor()
    cur.execute(
        "UPDATE jornada SET fecha_inicio = ?, fecha_cierre = ?, cerrada = 0 WHERE id = 1",
        (fecha_inicio, fecha_cierre)
    )
    con.commit()
    con.close()

    return redirect(url_for("estado_jornada"))

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)