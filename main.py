import os
from fastapi import FastAPI, HTTPException,Request
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(description="Audio Streaming Server")

app.mount("/static", StaticFiles(directory="static", html=True), name="static")


@app.get("/health")
async def healthCheck():
    return "I am Healthy!"

@app.post("/stream")
async def stream_audio(request: Request):
    data = await request.json()
    song_name = data.get("song_name")  # ✅ Correct dictionary access

    if not song_name:
        raise HTTPException(status_code=400, detail="song_name is required")

    file_path = f"songs/{song_name}"
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="Song not found")

    def iter_audio():
        with open(file_path, "rb") as file:
            while chunk := file.read(1024):
                yield chunk

    return StreamingResponse(iter_audio(), media_type="audio/mpeg")
