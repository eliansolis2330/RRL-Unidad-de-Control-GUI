import subprocess


def ejecutar_comando():
    screen_width = 1280
    screen_height = 480
    window_width = 1280
    window_height = 480

    window_x = (1920 - window_width) // 2
    window_y = (1080 - window_height) // 2

    comando = (
        f"gst-launch-1.0 \
        nvarguscamerasrc sensor_id=0 ! 'video/x-raw(memory:NVMM), width=1920, height=1080, format=(string)NV12' ! nvvidconv ! queue ! mix.sink_0 \
        nvarguscamerasrc sensor_id=1 ! 'video/x-raw(memory:NVMM), width=1920, height=1080, format=(string)NV12' ! nvvidconv ! queue ! mix.sink_1 \
        nvcompositor name=mix sink_0::xpos=0 sink_0::ypos=0 sink_0::width=640 sink_0::height=480 \
        sink_1::xpos=640 sink_1::ypos=0 sink_1::width=640 sink_1::height=480 \
        mix. ! nvegltransform ! nveglglessink window-width={window_width} window-height={window_height} window-x={window_x} window-y={window_y}"
    )

    subprocess.run(comando, shell=True)


if __name__ == "__main__":
    ejecutar_comando()
