import customtkinter as ctk
from PIL import Image, ImageTk, ImageDraw
import cv2
import random
import math
import speech_recognition as sr
import threading
import subprocess


def read_magnetometer():
    return random.uniform(0, 360)


def read_mq7_sensor():
    return random.randint(200, 800)


def run_script(script_name):
    try:
        subprocess.run(["python3", script_name], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error al ejecutar {script_name}: {e}")


def execute_script(script_name):
    thread = threading.Thread(target=run_script, args=(script_name,), daemon=True)
    thread.start()


# ============================================================
# Funciones para el tacómetro de polaridad (rango: -250 a 250)
# ============================================================

def draw_tachometer_background(tacho_canvas):
    """
    Dibuja el fondo del tacómetro: un arco semicircular, ticks de valores cada 25,
    y un círculo central que simula el pivote.
    """
    # Dibuja el arco semicircular en la parte superior (de 0 a 180 grados)
    tacho_canvas.create_arc(50, 50, 250, 250, start=0, extent=180, style="arc", outline="white", width=2)
    # Dibuja el círculo central (pivote de la aguja)
    tacho_canvas.create_oval(140, 140, 160, 160, fill="white", outline="white")

    # Agrega etiquetas cada 25 unidades
    center_x, center_y = 150, 150
    # Usaremos un radio ligeramente mayor para las etiquetas (por ejemplo, 115)
    r = 115
    for polarity in range(-250, 251, 25):
        # Mapea la polaridad al ángulo (linealmente de 180° a 0°)
        angle = 90 - (polarity * 90 / 250)
        rad = math.radians(angle)
        x = center_x + r * math.cos(rad)
        y = center_y - r * math.sin(rad)
        # Dibuja el valor; se usa una fuente pequeña para no saturar
        tacho_canvas.create_text(x, y, text=str(polarity), fill="white", font=("Arial", 8), tag="tick")


def update_tachometer(tacho_canvas):
    """
    Actualiza el tacómetro generando un valor aleatorio de polaridad, calcula el ángulo
    correspondiente y redibuja la aguja (más gruesa y con extremos redondeados) y el valor.
    """
    # Genera un valor aleatorio entre -250 y 250
    polarity = random.randint(-250, 250)
    # Mapea la polaridad a un ángulo:
    # Para polarity = -250 → ángulo = 180° (aguja a la izquierda)
    # Para polarity =  250 → ángulo = 0°   (aguja a la derecha)
    # Para polarity =    0 → ángulo = 90°  (aguja hacia arriba)
    angle = 90 - (polarity * 90 / 250)
    center_x, center_y = 150, 150
    needle_length = 80
    rad = math.radians(angle)
    end_x = center_x + needle_length * math.cos(rad)
    end_y = center_y - needle_length * math.sin(rad)

    # Elimina la aguja y el valor numérico anterior (pero no los ticks)
    tacho_canvas.delete("needle")
    tacho_canvas.delete("value")
    # Dibuja la aguja (línea roja, más gruesa y con extremos redondeados)
    tacho_canvas.create_line(center_x, center_y, end_x, end_y, fill="red", width=6, capstyle="round", tag="needle")
    # Muestra el valor numérico de la polaridad debajo del tacómetro
    tacho_canvas.create_text(center_x, 260, text=f"Polaridad: {polarity}", fill="white", font=("Arial", 16, "bold"),
                             tag="value")
    # Programa la próxima actualización en 500 milisegundos
    tacho_canvas.after(500, update_tachometer, tacho_canvas)


# ============================================================
# Otras funciones (cámaras, reconocimiento de voz, etc.)
# ============================================================

def update_air_quality(air_quality_label):
    ppm = read_mq7_sensor()
    air_quality_label.configure(text=f"CO: {ppm} PPM")
    air_quality_label.after(1000, update_air_quality, air_quality_label)


def setup_cameras(indices, camera_frames):
    caps = []
    for i, idx in enumerate(indices):
        cap = cv2.VideoCapture(idx)
        if cap.isOpened():
            caps.append(cap)
            update_video(i, cap, camera_frames[i])
        else:
            print(f"Error al abrir la cámara con índice {idx}")
    return caps


def update_video(index, cap, camera_label):
    ret, frame = cap.read()
    if ret:
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_image = Image.fromarray(frame_rgb)
        frame_photo = ImageTk.PhotoImage(frame_image)
        camera_label.configure(image=frame_photo)
        camera_label.image = frame_photo
    camera_label.after(30, update_video, index, cap, camera_label)


def update_speech_to_text(speech_label):
    recognizer = sr.Recognizer()
    mic = sr.Microphone()
    global audio_detection_active

    def listen():
        while audio_detection_active:
            try:
                with mic as source:
                    recognizer.adjust_for_ambient_noise(source)
                    audio = recognizer.listen(source)
                text = recognizer.recognize_google(audio, language="es-ES")
                speech_label.configure(text=f"Reconocido: {text}")
            except sr.UnknownValueError:
                speech_label.configure(text="No se pudo reconocer el audio")
            except sr.RequestError:
                speech_label.configure(text="Error en el servicio de reconocimiento")

    thread = threading.Thread(target=listen)
    thread.daemon = True
    thread.start()


def toggle_audio_detection(speech_label):
    global audio_detection_active
    if audio_detection_active:
        audio_detection_active = False
        speech_label.configure(text="Detección de audio desactivada")
    else:
        audio_detection_active = True
        update_speech_to_text(speech_label)


def create_gui():
    global audio_detection_active
    audio_detection_active = False

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    root = ctk.CTk()
    root.title("Unidad de Control del Robot de Rescate")
    root.attributes("-fullscreen", True)

    # --------------------------
    # Header: Título y logo
    # --------------------------
    header_frame = ctk.CTkFrame(root, height=200, fg_color="black")
    header_frame.pack(fill="x")

    header_label = ctk.CTkLabel(header_frame, text="Unidad de Control", font=("Arial", 45, "bold"), text_color="white")
    header_label.pack(side="left", padx=20)

    logo_image = Image.open("nixlogo.png")  # Asegúrate de que "nixlogo.png" esté en la ruta correcta
    logo_image = logo_image.resize((120, 120), Image.Resampling.LANCZOS)
    logo_photo = ImageTk.PhotoImage(logo_image)
    logo_label = ctk.CTkLabel(header_frame, image=logo_photo, text="")
    logo_label.image = logo_photo
    logo_label.pack(side="right", padx=20)

    # --------------------------
    # Botones de acciones
    # --------------------------
    button_frame = ctk.CTkFrame(root, height=50, fg_color="black")
    button_frame.pack(fill="x")

    extra_buttons = [
        ('Detectar Movimiento', lambda: execute_script("movementDetection.py")),
        ('Detección QR', lambda: execute_script("qrDetector.py")),
        ('Speech to Text', lambda: toggle_audio_detection(speech_label)),
        ("Cámara Térmica", lambda: execute_script("thermalCamera.py")),
        ("YOLOv10", lambda: execute_script("runyolov10.py")),
        ("MQ y Magentómetro", None),
        ("SLAM 2D", None),
        ("Save SLAM", None),
    ]

    for text, command in extra_buttons:
        button = ctk.CTkButton(button_frame, text=text, width=210, height=40, font=("Arial", 18, "bold"),
                               text_color="black", fg_color="white", hover_color="#cccccc", command=command)
        button.pack(side="left", padx=20, pady=10)

    # --------------------------
    # Configuración de Cámaras
    # --------------------------
    camera_indices = []

    def save_indices():
        indices = camera_input.get()
        camera_indices.clear()
        camera_indices.extend(map(int, indices.split(",")))
        setup_cameras(camera_indices, camera_labels)

    camera_input = ctk.CTkEntry(header_frame, width=300, placeholder_text="Índices de cámaras (ej: 1,2)",
                                font=("Arial", 14), fg_color="white", text_color="black")
    camera_input.pack(side="right", padx=10)

    save_button = ctk.CTkButton(header_frame, text="Configurar Cámaras", font=("Arial", 14, "bold"),
                                text_color="white", fg_color="red", hover_color="#cccccc", command=save_indices)
    save_button.pack(side="right", padx=10)

    # --------------------------
    # Área Principal: Cámaras y Widgets
    # --------------------------
    main_frame = ctk.CTkFrame(root, fg_color="black")
    main_frame.pack(expand=True, fill="both")
    main_frame.grid_rowconfigure(1, weight=1)
    main_frame.grid_columnconfigure((0, 1, 2), weight=1)

    # Sección de cámaras
    camera_labels = []
    for i in range(4):
        frame = ctk.CTkFrame(main_frame, fg_color="#1e1e1e", corner_radius=10)
        frame.grid(row=i // 2, column=i % 2, padx=10, pady=10, sticky="nsew")
        label = ctk.CTkLabel(frame, text=f"Cámara {i + 1}", font=("Arial", 18, "bold"), text_color="white")
        label.pack(expand=True, fill="both")
        camera_labels.append(label)

    # Widget Frame para los elementos adicionales
    widget_frame = ctk.CTkFrame(main_frame, fg_color="black", corner_radius=10)
    widget_frame.grid(row=0, column=2, rowspan=2, padx=10, pady=10, sticky="nsew")

    # --------------------------
    # Nuevo Tacómetro de Polaridad
    # --------------------------
    tachometer_frame = ctk.CTkFrame(widget_frame, fg_color="#1e1e1e", corner_radius=10)
    tachometer_frame.pack(pady=10, fill="x", expand=True)

    tachometer_label = ctk.CTkLabel(tachometer_frame, text="Tacómetro de Polaridad", font=("Arial", 18, "bold"),
                                    text_color="white")
    tachometer_label.pack()

    tacho_canvas = ctk.CTkCanvas(tachometer_frame, width=300, height=300, bg="#1e1e1e", highlightthickness=0)
    tacho_canvas.pack()

    draw_tachometer_background(tacho_canvas)
    update_tachometer(tacho_canvas)

    # --------------------------
    # Calidad del Aire
    # --------------------------
    air_quality_frame = ctk.CTkFrame(widget_frame, fg_color="#1e1e1e", corner_radius=10)
    air_quality_frame.pack(pady=10, fill="x", expand=True)

    air_quality_label = ctk.CTkLabel(air_quality_frame, text="CO: -- PPM", font=("Arial", 18, "bold"),
                                     text_color="white")
    air_quality_label.pack()
    update_air_quality(air_quality_label)

    # --------------------------
    # Reconocimiento de Voz
    # --------------------------
    speech_frame = ctk.CTkFrame(widget_frame, fg_color="#1e1e1e", corner_radius=10)
    speech_frame.pack(pady=10, fill="x", expand=True)

    speech_label = ctk.CTkLabel(speech_frame, text="Audio: No detectado", font=("Arial", 18, "bold"),
                                text_color="white")
    speech_label.pack()

    root.mainloop()


if __name__ == "__main__":
    create_gui()
