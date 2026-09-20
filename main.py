import cv2
import asyncio
import threading
import time
from fastapi.responses import FileResponse
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from ultralytics import YOLO

app=FastAPI(title="CIPHER")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

cameraurl="http://127.0.0.1:5000/"      #url of the live stream. code from camsimulation.py
currentframebytes=None

model=YOLO("yolov8n.pt")    #initializing model

#contiously pulls frames from the stream
def capturestreamthread():
    global currentframebytes
    capture=cv2.VideoCapture(cameraurl)             #getting the live feed

    if not capture.isOpened():                      #if no video feed is available
        print("The Camera is not Connected")      
        return

    while True:                                     #if camera feed is available
        success,frame=capture.read()
        if success:
            #YOLO Proccessing here
            result=model(frame,classes=[0], verbose=False)      #classes=[0] targets persons only, verbose=False suppresses thinking logs
            labelledframe=result[0].plot()


            #compressing video frames to JPEG Images
            _,buffer=cv2.imencode('.jpg',labelledframe)
            currentframebytes=buffer.tobytes()

        else:
            print("Didn't get the Frame")
            time.sleep(1)
            capture=cv2.VideoCapture(cameraurl)         #retry


@app.on_event("startup")
async def startupevent():
    #Start the camera capture loop
    thread=threading.Thread(target=capturestreamthread, daemon=True)
    thread.start()
    print("Thread has started!")


#this endpoint will be used by frontend to stream video
@app.websocket("/ws/video")
async def videowebsocket(websocket: WebSocket):         
    await websocket.accept()
    print("Client connected to WebSocket")

    try:
        while True:
            if currentframebytes:
                await websocket.send_bytes(currentframebytes)   #send bytes to software
                await asyncio.sleep(0.033)          #30FPS

    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")

@app.get("/")
async def get_test_page():
    """Serves a basic HTML page to test the WebSocket stream."""
    return FileResponse("stream.html")

#for laptop only
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app,port=8000)

#cross platform- use ipcongif IPv4 Addess as host
'''if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app,host="0.0.0.0" ,port=8000)'''

