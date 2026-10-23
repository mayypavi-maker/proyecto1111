let estado = "apagada";
const video = document.getElementById("video");
const canvas = document.getElementById("fotoCapturada");
const boton = document.getElementById("abrirCamara");
const camara = document.getElementById("camara");
const fotoBase64 = document.getElementById("fotoBase64");
const formulario = document.getElementById("formularioVotante");
const nombreInput = document.getElementById("nombre");
const dniInput = document.getElementById("dni");
const mensajeFormulario = document.querySelector(".alert");

let streamActual = null;
let contextoCanvas = null;
let fotoBlob = null;

function mostrarMensaje(texto, tipo = "error") {
    let mensaje = mensajeFormulario;

    if (!mensaje) {
        mensaje = document.createElement("div");
        mensaje.className = "alert";
        formulario.before(mensaje);
    }

    mensaje.textContent = texto;
    mensaje.className = `alert alert-${tipo}`;
    mensaje.style.display = "block";
}

formulario.addEventListener("submit", async (event) => {
    event.preventDefault();

    const nombre = nombreInput.value.trim();
    const dni = dniInput.value.trim();

    const nombreRegex = /^[A-Za-zÁÉÍÓÚáéíóúÜüÑñ\s]+$/;
    const dniRegex = /^\d{7,8}$/;

    if (!nombreRegex.test(nombre)) {
        mostrarMensaje("El nombre solo puede contener letras y espacios.", "error");
        return;
    }

    if (!dniRegex.test(dni)) {
        mostrarMensaje("El DNI debe tener solo números, sin puntos ni letras.", "error");
        return;
    }

    if (!fotoBlob) {
        mostrarMensaje("Debe capturar una foto antes de registrar.", "error");
        return;
    }

    const datos = new FormData(formulario);
    datos.append("foto", fotoBlob, "rostro.jpg");

    try {
        const respuesta = await fetch(formulario.action, {
            method: "POST",
            body: datos
        });

        const texto = await respuesta.text();

        if (respuesta.ok) {
            mostrarMensaje("Votante registrado correctamente.", "success");
            formulario.reset();
            fotoBlob = null;
            if (video && streamActual) {
                video.classList.remove("mostrando");
                canvas.classList.remove("mostrando");
                camara.style.display = "none";
                estado = "apagada";
                boton.textContent = "📷 Abrir cámara";
            }
        } else {
            mostrarMensaje(texto || "Ocurrió un error al registrar.", "error");
        }
    } catch (error) {
        console.error("Error al enviar:", error);
        mostrarMensaje("No se pudo registrar el votante. Intenta nuevamente.", "error");
    }
});

if (canvas) {
    contextoCanvas = canvas.getContext("2d");
}

boton.addEventListener("click", async () => {
    if (estado === "apagada") {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                video: true
            });

            streamActual = stream;
            camara.style.display = "block";
            video.srcObject = stream;
            video.classList.add("mostrando");
            canvas.classList.remove("mostrando");
            await video.play();
            estado = "encendida";
            boton.textContent = "📸 Capturar foto";
        } catch (error) {
            console.error("No se pudo abrir la cámara:", error);
            boton.textContent = "⚠️ No se pudo abrir la cámara";
        }
    } else if (estado === "encendida") {
        if (contextoCanvas) {
            contextoCanvas.drawImage(video, 0, 0, canvas.width, canvas.height);
        }

        if (streamActual) {
            streamActual.getTracks().forEach(track => track.stop());
            streamActual = null;
        }
        video.pause();
        video.srcObject = null;

        canvas.toBlob((blob) => {
                console.log("Foto preparada:", blob);
                fotoBlob = blob;
        }, "image/jpeg", 0.8);

        video.classList.remove("mostrando");
        canvas.classList.add("mostrando");
        estado = "capturada";
        boton.textContent = "🔁 Tomar nuevamente";
    } else {
        if (streamActual) {
            streamActual.getTracks().forEach(track => track.stop());
            streamActual = null;
        }

        fotoBlob = null;
        fotoBase64.value = "";
        contextoCanvas.clearRect(0, 0, canvas.width, canvas.height);
        video.srcObject = null;
        video.classList.remove("mostrando");
        canvas.classList.remove("mostrando");
        camara.style.display = "none";
        estado = "apagada";

        boton.click();
    }
});