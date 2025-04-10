import cv2
#pip install nanocamera
import nanocamera as nano

if __name__ == __main__():
    Camera = nano.Camera(flip = 2, width= 640, height= 480, fps = 60)

    print('Csi camera ready? - ', camera.isReady())

    while(camera.isReady()):
        try:
            #read camera image
            frame = camera.read()
            #display the frame
            cv2.imshow('Video Frame', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        except KeyboardInterrupt:
            break
    #close the camera instance
    camera.release()
    #remove camera object
    del camera