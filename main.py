import customtkinter as ctk
from PIL import Image, ImageTk, ImageDraw
import cv2
import math
import speech_recognition as sr
import threading
import subprocess
import serial
import sounddevice as sd
import queue
import sys
import json
from vosk import Model, KaldiRecognizer



audio_detection_active = False
recognition_thread = None
SERIAL_PORT = "/dev/ttyTHS0"
BAUD_RATE = 115200
MODEL_PATH = "/home/elian/Downloads/vosk-model-small-en-us-0.15"
q = queue.Queue()

try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.01)
    print("Conexión establecida con ESP32")
except serial.SerialException:
    print("No se pudo abrir el puerto serie")

def read_sensors():
    try:
        while ser.in_waiting > 0:
            line = ser.readline().decode('utf-8').strip()
        values = line.split(",")
        if len(values) == 2:
            gas_value = int(values[0])
            mag_analog = int(values[1])
            return gas_value, mag_analog
    except Exception as e:
        print(f"Error al leer los sensores: {e}")
    return None, None


def read_magnetometer():
    _, mag_analog = read_sensors()
    if mag_analog is not None:
        scaled_value = (mag_analog - 1800) / 1800 * 550  # 2048 *450
        return int(scaled_value)
    return 0


def read_mq7_sensor():
    gas_value, _ = read_sensors()
    if gas_value is not None:
        ppm = gas_value
        return int(ppm - 100)  # quitar el -100 este no iba
    return 0


def run_script(script_name):
    try:
        subprocess.run(["python3", script_name], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error al ejecutar {script_name}: {e}")


def execute_script(script_name):
    thread = threading.Thread(target=run_script, args=(script_name,), daemon=True)
    thread.start()


def draw_tachometer_background(tacho_canvas):
    tacho_canvas.create_arc(50, 50, 250, 250, start=0, extent=180, style="arc", outline="white", width=2)
    tacho_canvas.create_oval(140, 140, 160, 160, fill="white", outline="white")
    center_x, center_y = 150, 150
    r = 115
    for polarity in range(-250, 251, 25):
        angle = 90 - (polarity * 90 / 250)
        rad = math.radians(angle)
        x = center_x + r * math.cos(rad)
        y = center_y - r * math.sin(rad)
        tacho_canvas.create_text(x, y, text=str(polarity), fill="white", font=("Arial", 8), tag="tick")


def update_tachometer(tacho_canvas):
    microteslas = read_magnetometer()
    min_polarity, max_polarity = -250, 250
    polarity = microteslas
    angle = 90 - (polarity * 90 / 250)
    center_x, center_y = 150, 150
    needle_length = 80
    rad = math.radians(angle)
    end_x = center_x + needle_length * math.cos(rad)
    end_y = center_y - needle_length * math.sin(rad)

    tacho_canvas.delete("needle")
    tacho_canvas.delete("value")
    tacho_canvas.create_line(center_x, center_y, end_x, end_y, fill="#4BEFFF", width=6, capstyle="round", tag="needle")
    tacho_canvas.create_text(center_x, 260, text=f"Polaridad: {polarity}", fill="white", font=("Arial", 16, "bold"),
                             tag="value")
    tacho_canvas.after(500, update_tachometer, tacho_canvas)


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

def callback(indata, frames, time, status):
    if status:
        print("⚠", status)
    q.put(bytes(indata))

def update_video(index, cap, camera_label):
    ret, frame = cap.read()
    if ret:
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_image = Image.fromarray(frame_rgb)
        frame_photo = ImageTk.PhotoImage(frame_image)
        camera_label.configure(image=frame_photo)
        camera_label.image = frame_photo
    camera_label.after(30, update_video, index, cap, camera_label)

def start_offline_speech_recognition(speech_label):
    global audio_detection_active
    try:
        model = Model(MODEL_PATH)
        rec = KaldiRecognizer(model, 16000)
        rec.SetWords(True)

        with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype='int16',
                               channels=1, callback=callback):
            print("🎤 Reconocimiento activado")
            while audio_detection_active:
                data = q.get()
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    text = result.get("text", "")
                    print("Texto:", text)
                    speech_label.configure(text=f".:| {text}")
                else:
                    partial = json.loads(rec.PartialResult())
                    partial_text = partial.get("partial", "")
                    print("→", partial_text, end='\r')
                    speech_label.configure(text=f"🗣 SpchTxt: {partial_text}")

    except Exception as e:
        print(f"Error en reconocimiento de voz: {e}")
        speech_label.configure(text="Error en reconocimiento")

def toggle_audio_detection(speech_label):
    global audio_detection_active, recognition_thread

    if audio_detection_active:
        audio_detection_active = False
        speech_label.configure(text="🔇 Detección de audio desactivada")
        print("🔇 Reconocimiento desactivado")
    else:
        audio_detection_active = True
        speech_label.configure(text=".:| Detección de audio activada...")
        recognition_thread = threading.Thread(
            target=start_offline_speech_recognition,
            args=(speech_label,),
            daemon=True
        )
        recognition_thread.start()

def create_gui():
    global audio_detection_active
    audio_detection_active = False

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    root = ctk.CTk()
    root.title("Unidad de Control del Robot de Rescate")
    root.attributes("-fullscreen", True)

    icon_path = "/home/elian/PycharmProjects/PythonProject1/.venv/elbueno.ico"
    try:
        icon_image = Image.open(icon_path)
        icon_photo = ImageTk.PhotoImage(icon_image)
        root.tk.call('wm', 'iconphoto', root._w, icon_photo)
    except Exception as e:
        print(f"Error al cargar el ícono: {e}")

    header_frame = ctk.CTkFrame(root, height=200, fg_color="black")
    header_frame.pack(fill="x")

    header_label = ctk.CTkLabel(header_frame, text="Unidad de Control", font=("Arial", 45, "bold"), text_color="white")
    header_label.pack(side="left", padx=20)

    logo_image = Image.open("/home/elian/PycharmProjects/PythonProject1/.venv/nixlogo.png")
    logo_image = logo_image.resize((120, 120), Image.Resampling.LANCZOS)
    logo_photo = ImageTk.PhotoImage(logo_image)
    logo_label = ctk.CTkLabel(header_frame, image=logo_photo, text="")
    logo_label.image = logo_photo
    logo_label.pack(side="right", padx=20)

    button_frame = ctk.CTkFrame(root, height=50, fg_color="black")
    button_frame.pack(fill="x")

    buttons = [
        ('Detectar Movimiento', lambda: execute_script("movementDetection.py")),
        ('Detección QR', lambda: execute_script("qrDetector.py")),
        ('Speech to Text', lambda: toggle_audio_detection(speech_label)),
        ("Cámara Térmica", lambda: execute_script("thermalCamera.py")),
        ("YOLOv10", lambda: execute_script("runyolov10.py")),
        ("Cams CSI", lambda: execute_script("csiCameras.py")),
        ("SLAM", lambda: execute_script("slam.py")),
    ]

    for text, command in buttons:
        button = ctk.CTkButton(button_frame, text=text, width=210, height=40, font=("Arial", 18, "bold"),
                               text_color="black", fg_color="white", hover_color="#cccccc", command=command, border_width=4, border_color="#4BEFFF", corner_radius=17)
        button.pack(side="left", padx=20, pady=10)

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
                                text_color="black", fg_color="#4BEFFF", hover_color="#cccccc", command=save_indices, corner_radius=15)
    save_button.pack(side="right", padx=10)

    main_frame = ctk.CTkFrame(root, fg_color="black")
    main_frame.pack(expand=True, fill="both")
    main_frame.grid_rowconfigure(1, weight=1)
    main_frame.grid_columnconfigure((0, 1, 2), weight=1)

    camera_labels = []
    for i in range(2):
        frame = ctk.CTkFrame(main_frame, fg_color="#1e1e1e", corner_radius=17)
        frame.grid(row=i // 2, column=i % 2, padx=10, pady=10, sticky="nsew")
        label = ctk.CTkLabel(frame, text=f"Cámara {i + 1}", font=("Arial", 18, "bold"), text_color="white")
        label.pack(expand=True, fill="both")
        camera_labels.append(label)
    widget_frame = ctk.CTkFrame(main_frame, fg_color="black", corner_radius=17)
    widget_frame.grid(row=0, column=2, rowspan=2, padx=10, pady=10, sticky="nsew")

    tachometer_frame = ctk.CTkFrame(widget_frame, fg_color="#1e1e1e", corner_radius=17, border_width=2, border_color="#4BEFFF",)
    tachometer_frame.pack(pady=10, fill="x", expand=True)

    tachometer_label = ctk.CTkLabel(tachometer_frame, text="Tacómetro de Polaridad", font=("Arial", 18, "bold"),
                                    text_color="white")
    tachometer_label.pack()

    tacho_canvas = ctk.CTkCanvas(tachometer_frame, width=300, height=300, bg="#1e1e1e", highlightthickness=0)
    tacho_canvas.pack()

    draw_tachometer_background(tacho_canvas)
    update_tachometer(tacho_canvas)

    air_quality_frame = ctk.CTkFrame(widget_frame, fg_color="#1e1e1e", corner_radius=17, border_width=2, border_color="#4BEFFF",)
    air_quality_frame.pack(pady=10, fill="x", expand=True)

    air_quality_label = ctk.CTkLabel(air_quality_frame, text="CO: -- PPM", font=("Arial", 18, "bold"),
                                     text_color="white")
    air_quality_label.pack()
    update_air_quality(air_quality_label)

    speech_frame = ctk.CTkFrame(widget_frame, fg_color="#1e1e1e", corner_radius=17, border_width=2, border_color="#4BEFFF",)
    speech_frame.pack(pady=10, fill="x", expand=True)

    speech_label = ctk.CTkLabel(speech_frame, text="Audio: No detectado", font=("Arial", 18, "bold"),
                                text_color="white")
    speech_label.pack()
    root.mainloop()

if __name__ == "__main__":
    create_gui()