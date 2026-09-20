import cv2
import asyncio
import threading
import time
import datetime
from collections import deque
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

preeventframes=90
posteventframes=90
framebuffer=deque(maxlen=preeventframes)
isrecording=False
posteventcounter=0
videowriter=None

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

            framebuffer.append(labelledframe)           #continuosly push the frame into the frame buffer

            boxes=result[0].boxes                   #check if there is any event happening

            #if any event is happening and if its not already recording then, save pre event clips
            if len(boxes)>0  and not isrecording:
                print("Violence Detected!!")
                isrecording=True
                posteventcounter=0

                timestamp=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")         #set timestamp in the video recording
                filename=f"incident_{timestamp}.mp4"
                fourcc=cv2.VideoWriter_fourcc(*'mpv4')          #fourcc is an indentifier which tells the system which compression algorithm to apply
                height,width,_=labelledframe.shape              #set video height and width same as labelled video height and width
                videowriter=cv2.VideoWriter(filename,fourcc,30.0,(width,height))

                #dump already recorded frames into filename as pre-event footage
                for bufferedframe in framebuffer:
                    videowriter.write(bufferedframe)
                print("Pre Event Frames are saved!")

            #for post event clip saving
            if isrecording:
                videowriter.write(labelledframe)
                posteventcounter+=1

                if posteventcounter>=posteventframes:   #when the post event queue is full, stop the recording
                    videowriter.release()
                    isrecording=False
                    framebuffer.clear()
                    print("Post Event Recording Compelete")

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

