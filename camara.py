import cv2

# Abrir la cámara
camara = cv2.VideoCapture(0)

while True:

    ret, frame = camara.read()

    if not ret:
        print("Error al abrir la cámara.")
        break

    # Obtener tamaño de la imagen
    alto, ancho = frame.shape[:2]

    # Coordenadas del recuadro guía
    x1 = ancho // 2 - 150
    y1 = alto // 2 - 170

    x2 = ancho // 2 + 150
    y2 = alto // 2 + 170

    # Dibujar el recuadro
    cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 255), 2)

    # Título
    cv2.putText(
        frame,
        "Ubique su rostro dentro del recuadro",
        (40, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 255),
        2
    )

    cv2.putText(
        frame,
        "ENTER = Capturar     ESC = Cancelar",
        (40, alto - 25),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (0, 255, 0),
        2
    )

    cv2.imshow("VotaID - Captura de rostro", frame)

    tecla = cv2.waitKey(1)

    # ENTER
    if tecla == 13:

        cv2.imwrite("capturas/temporales/captura_actual.jpg", frame)

        cv2.putText(
            frame,
            "Foto capturada correctamente",
            (60, alto // 2),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            3
        )

        cv2.imshow("VotaID - Captura de rostro", frame)

        cv2.waitKey(1000)

        break

    # ESC
    elif tecla == 27:

        print("Captura cancelada.")

        break

camara.release()
cv2.destroyAllWindows()