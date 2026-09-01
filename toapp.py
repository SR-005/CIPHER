import cv2
from flask import Flask, Response

app=Flask(__name__)
camera=cv2.VideoCapture(0)

#read frames from camera, resizes them, and encodes to MJPEG
def generateframes():
    while True:
        success,frame=camera.read()
        if not success:
            break

        frame=cv2.resize(frame,(640,480))   #resizing to mimic ESP32-CAM
        ret,buffer=cv2.imencode('.jpg',frame)
        framebytes=buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + framebytes + b'\r\n')


@app.route('/')
def videofeed():                    
    return Response(generateframes(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    print("CIPHER Camera Simulator running...")
    app.run(debug=False)