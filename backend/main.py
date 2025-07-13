import google.generativeai as genai
genai.configure(api_key="AIzaSyBLv7dA4tI0bZGo6DXGAQA1_-fKRqnieYc")  # ⬅️ Replace this with your real key

gemini_model = genai.GenerativeModel(model_name="models/gemini-2.5-flash")

import os
import shutil
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import fitz  # PyMuPDF
import json

UPLOAD_DIR = "uploads"

LLM_PROMPT = """
You are a transcript normalizer.

You will be given a raw UX research transcript that may include broken formatting, inconsistent speaker labels, and noisy boilerplate text (e.g., headers or page numbers).

Your job is to return a clean, readable transcript. Keep speaker labels clear. If you need to infer a speaker label, include “[inferred]” after it.

If anything is unreadable, mark it with “[unintelligible]”. Do not hallucinate.

Here is the raw transcript:
---
{raw_text}
---
Return only the cleaned transcript.
"""

def run_llm_normalizer(raw_text: str) -> str:
    prompt = LLM_PROMPT.replace("{raw_text}", raw_text)
    try:
        response = gemini_model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Error from Gemini: {e}")
        return "[LLM error]"

def run_llm_atomiser(clean_text: str) -> list[dict]:
    prompt = f"""
You are an "Idea Atomiser".

Your job is to break a cleaned UX research transcript into discrete idea units.

Each unit should:
- Be 1–3 sentences long.
- Be self-contained.
- Preserve the speaker label.

Respond in JSON format only — no explanation, no markdown, no backticks. Just the raw list.

Here is the cleaned transcript:
---
{clean_text}
---
Return only valid JSON like this:

[
  {{ "speaker": "User", "text": "I had trouble using the app on my phone." }},
  {{ "speaker": "Moderator", "text": "What did you expect to happen?" }}
]
"""

    try:
        response = gemini_model.generate_content(prompt)
        raw = response.text.strip()

        # Try parsing JSON safely
        atoms = json.loads(raw)
        return atoms
    except Exception as e:
        print("Failed to parse LLM response:", e)
        print("Raw response was:\n", response.text)
        return []

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

        cleaned = clean_transcript(full_text)
        cleaned_text = run_llm_normalizer(cleaned)
        print(f"---\nNormalized output for {filename}:\n{cleaned_text}\n---")
        normalized_output[filename] = cleaned_text

    return normalized_output


@app.get("/atomise")
async def atomise_files():
    upload_dir = "uploads"
    atomised_output = {}

    for filename in os.listdir(upload_dir):
        if not filename.lower().endswith(".pdf"):
            continue

        pdf_path = os.path.join(upload_dir, filename)
        doc = fitz.open(pdf_path)
        full_text = ""

        for page in doc:
            full_text += page.get_text() + "\n"

        # Step 1: Normalize the text
        clean_text = run_llm_normalizer(full_text)

        # Step 2: Atomise the clean text
        atoms = run_llm_atomiser(clean_text)

        atomised_output[filename] = atoms

    return atomised_output


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
