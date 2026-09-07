import os
import re
import subprocess
import sqlite3
import cv2

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from database import guardar_votante, iniciar_base_datos, buscar_votante

app= Flask(__name__)

detector_rostros = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

app.secret_key = "votaid.2026"

USUARIO_ADMIN = "amaia"

CONTRASENA_ADMIN = "votaid2026"

iniciar_base_datos()

@app.route('/')
def inicio():
    return render_template('index.html')

@app.route("/registro")
def registro():

    return render_template("registro.html")

@app.route("/registrar", methods=["POST"])
def registrar():

    dni = request.form.get("dni")

    votante = buscar_votante(dni)

    if not votante:
        return render_template(
            "registro.html",
            error="El DNI no corresponde a un votante registrado."
        )

    return render_template(
        "reconocimiento.html",
        votante=votante
    )

@app.route("/reconocimiento")
def reconocimiento():

    return render_template("reconocimiento.html")


@app.route("/loginadmin", methods=["GET", "POST"])
def loginadmin():
    if request.method == "POST":
        usuario = request.form.get("usuario")
        contrasena = request.form.get("contrasena")

        if usuario == USUARIO_ADMIN and contrasena == CONTRASENA_ADMIN:
            return render_template("admin/paneladmin.html")
        return render_template("admin/loginadmin.html", error="Usuario o contraseña incorrectos")
    return render_template("admin/loginadmin.html")

def validar_nombre(nombre):
    if nombre is None:
        return False
    nombre = nombre.strip()
    return bool(re.fullmatch(r"[A-Za-zÁÉÍÓÚáéíóúÜüÑñ\s]+", nombre))


@app.route("/admin/registrarvotante", methods=["GET", "POST"])
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
def captura():

    return render_template("admin/captura.html")

@app.route("/capturar")
def capturar():

    subprocess.run(["python", "camara.py"])

    return redirect(url_for("registrarvotante"))

@app.route('/admin/administrarlista')
def administrarlista():
    return render_template('admin/administrarlista.html')

@app.route('/admin/administrarlista/votantes')
def administrar_votantes():
    conexion = sqlite3.connect("Votaid.db")
    cursor = conexion.cursor()
    cursor.execute("SELECT * FROM usuarios")
    usuarios = cursor.fetchall()
    datos_usuarios = usuarios
    conexion.close()
    return render_template('admin/administrarvotantes.html', usuarios=datos_usuarios)

@app.route('/admin/administrarlista/candidatos')
def administrar_candidatos():
    return render_template('admin/administrarcandidatos.html')

@app.route('/admin/resultados')
def resultados():
    return render_template('admin/resultados.html')

@app.route('/admin/estadojornada')
def estado_jornada():
    return render_template('admin/estadojornada.html')

@app.route("/votacion")
def votacion():

    return render_template("votacion.html")
    
@app.route("/verificar_rostro", methods=["POST"])
def verificar_rostro():

    foto = request.files.get("foto")

    if not foto:
        return jsonify({
            "rostro": False,
            "mensaje": "No se recibió ninguna foto."
        }), 400

    # Guardamos temporalmente la imagen
    ruta = "captura.jpg"
    foto.save(ruta)

    # Abrimos la imagen con OpenCV
    imagen = cv2.imread(ruta)

    if imagen is None:
        return jsonify({
            "rostro": False,
            "mensaje": "No se pudo leer la imagen."
        }), 400

    # Convertimos la imagen a escala de grises
    gris = cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY)

    # Buscamos rostros
    rostros = detector_rostros.detectMultiScale(
        gris,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(100, 100)
    )

    # Si no encontró ningún rostro
    if len(rostros) == 0:
        return jsonify({
            "rostro": False,
            "mensaje": "No se detectó ningún rostro."
        })

    # Si encontró un rostro
    return jsonify({
        "rostro": True,
        "mensaje": "Rostro detectado correctamente."
    })

if __name__ == '__main__':
    app.run(debug=True)