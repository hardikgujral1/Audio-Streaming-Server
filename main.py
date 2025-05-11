import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException

from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
import boto3
from botocore.exceptions import NoCredentialsError
from datetime import datetime, timedelta
import os
import time
import json


connections = []

app = FastAPI(description="Audio Streaming Server")

app.mount("/static", StaticFiles(directory="static", html=True), name="static")
s3 = boto3.client('s3', endpoint_url="https://s3.ap-south-1.amazonaws.com",region_name = "ap-south-1",aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"))






@app.get("/health")
async def healthCheck():
    return "I am Healthy!"




@app.get("/stream/{song_name:path}")
async def stream_audio(song_name : str):
    print(song_name)
    bucket = "vibexlabs"
    signed_url = generate_presigned_url(bucket, song_name)
    print(signed_url)    
    if not signed_url:
        raise HTTPException(status_code=400, detail="Failed to generate presigned URL")

    return {"stream_url": signed_url}



@app.get("/songs" )
async def get_songs():
    try:
        # List objects in the S3 bucket
        response = s3.list_objects_v2(Bucket="vibexlabs")
        
        if 'Contents' not in response:
            raise HTTPException(status_code=404, detail="No songs found")

        songs = [item['Key'] for item in response['Contents'] if item['Key'].endswith('.mp3')]
        return songs
    
    except NoCredentialsError:
        raise HTTPException(status_code=403, detail="AWS credentials are missing or invalid")
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))


def generate_presigned_url(bucket,key):


    url = s3.generate_presigned_url(
        ClientMethod='get_object',
        Params={
            'Bucket': f'{bucket}',
            'Key': f'{key}'
        },
        ExpiresIn=30 # one hour in seconds, increase if needed
    )
    return url


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connections.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            data = json.loads(data)
            event = data.get("event")

            if event == "play":
                # Send sync signal to all clients
                sync_time = int(time.time() * 1000)  # Reference time in milliseconds
                broadcast_data = {
                    "event": "sync",
                    "sync_time": sync_time  # Reference time to sync playback
                }
                for conn in connections:
                    await conn.send_text(json.dumps(broadcast_data))

            elif event == "load":
                song = data.get("song")
                broadcast_data = {
                    "event": "load",
                    "song": song
                }
                for conn in connections:
                    await conn.send_text(json.dumps(broadcast_data))

    except WebSocketDisconnect:
        connections.remove(websocket)

@app.get("/time")
def get_server_time():
    return {"server_time": int(datetime.utcnow().timestamp() * 1000)}  # in ms