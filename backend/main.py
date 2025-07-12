import os
import shutil
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

UPLOAD_DIR = "uploads"

# 🔁 Reset uploads/ folder on server start
if os.path.exists(UPLOAD_DIR):
    shutil.rmtree(UPLOAD_DIR)
os.makedirs(UPLOAD_DIR)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/upload")
async def upload_pdfs(files: list[UploadFile] = File(...)):
    saved_files = []

    for file in files:
        file_path = os.path.join(UPLOAD_DIR, file.filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        saved_files.append(file.filename)

    print("Saved files:", saved_files)
    return {"message": f"Saved {len(saved_files)} file(s)", "files": saved_files}
