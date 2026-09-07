import cv2
import asyncio
import threading
import time
from fastapi.responses import HTMLResponse
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

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


#contiously pulls frames from the stream
def capturestreamthread():
    global currentframebytes

    #getting the live feed
    capture=cv2.VideoCapture(cameraurl)         

    #if no video feed is available
    if not capture.isOpened():                  
        print("The Camera is not Connected")      
        return

    #if camera feed is available
    while True:
        success,frame=capture.read()
        if success:
            #YOLO Model to be added

            #compressing video frames to JPEG Images
            _,buffer=cv2.imencode('.jpg',frame)
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
    html_content = """
    <!DOCTYPE html>
    <html>
        <head>
            <title>CIPHER Test Stream</title>
        </head>
        <body style="background-color: #111; color: #0f0; text-align: center; font-family: monospace;">
            <h2>Project CIPHER: Gateway Test</h2>
            <!-- This is where the video frames will appear -->
            <img id="videostream" style="border: 2px solid #0f0; border-radius: 8px; max-width: 100%;" />
            
            <script>
                // 1. Connect to the FastAPI WebSocket
                var ws = new WebSocket(`ws://${location.host}/ws/video`);
                var img = document.getElementById("videostream");
                
                // 2. Every time a message (frame) arrives, update the image
                ws.onmessage = function(event) {
                    // Create a blob from the raw JPEG bytes sent by Python
                    var blob = new Blob([event.data], {type: "image/jpeg"});
                    // Create a local URL for the blob and set it as the image source
                    img.src = URL.createObjectURL(blob);
                };
                
                ws.onopen = function() {
                    console.log("Connected to CIPHER video stream!");
                };
            </script>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, port=8000)

