import os
import shutil
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import fitz  # PyMuPDF

UPLOAD_DIR = "uploads"

# 🔁 Reset uploads/ folder on server start
#if os.path.exists(UPLOAD_DIR):
#    shutil.rmtree(UPLOAD_DIR)
os.makedirs(UPLOAD_DIR, exist_ok=True)

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

@app.get("/normalize")
async def normalize_files():
    upload_dir = "uploads"
    normalized_output = {}

    for filename in os.listdir(upload_dir):
        if not filename.lower().endswith(".pdf"):
            continue

        pdf_path = os.path.join(upload_dir, filename)
        doc = fitz.open(pdf_path)
        full_text = ""

        for page in doc:
            page_text = page.get_text()
            full_text += page_text + "\n"

        cleaned_text = clean_transcript(full_text)
        normalized_output[filename] = cleaned_text.strip()

    return normalized_output


def clean_transcript(raw_text: str) -> str:
    lines = raw_text.splitlines()
    cleaned = []

    for line in lines:
        line = line.strip()
        if (
            not line
            or "page" in line.lower()
            or "confidential" in line.lower()
            or line.isupper()
        ):
            continue
        cleaned.append(line)

    return "\n".join(cleaned)
