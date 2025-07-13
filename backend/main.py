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
You are a senior UX research assistant.

You will be given raw transcript text extracted from a PDF. This text may include:
- Page numbers, headers/footers, and other formatting artifacts
- Broken sentences or poor line breaks
- Missing or inconsistent speaker labels
- Boilerplate content unrelated to the conversation

Your task is to return a cleaned and structured transcript that is ready for downstream synthesis.

Instructions:
1. Remove noise such as page numbers, headers/footers, and irrelevant boilerplate.
2. Repair formatting issues like broken lines or mid-sentence splits.
3. Preserve speaker turns clearly. If speaker labels are inconsistent or missing:
   - **Use conversational context to separate distinct speakers.**
   - **Assign clearly differentiated pseudonyms**, like "Speaker 1", "Speaker 2", etc.
   - If a real name is obvious (e.g. mentioned multiple times as self-introduction), use it instead.
4. If a speaker is guessed, annotate with `[inferred]`.
5. If part of the text is unreadable, mark it as `[unintelligible]`.
6. **Do not hallucinate content** — your job is to clean and segment, not create new ideas.

Format:
- Output as plain text
- Each paragraph should start with a speaker label, like:

ERIC: I grew up in Pittsburgh. I loved fishing with my dad.
AJENA [inferred]: That sounds peaceful. My family used to hike a lot.

Here is the raw transcript:
---
{raw_text}
---
Return only the cleaned, speaker-separated transcript.
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
    prompt = (
        "You are an \"Idea Atomiser\" working with cleaned UX research transcripts.\n\n"
        "Your job is to break the transcript into discrete **idea units**, or \"atoms\".\n\n"
        "Each atom must:\n"
        "- Be 1–3 sentences long\n"
        "- Be self-contained (understandable without additional context)\n"
        "- Include only one coherent thought or idea\n"
        "- Include the **speaker label**, preserved as given (e.g., 'AJENA', 'ERIC', or 'SPEAKER 1')\n\n"
        "Guidelines:\n"
        "- Do not combine ideas from different speakers into one atom\n"
        "- If a speaker shifts topics, split that into multiple atoms\n"
        "- Retain any emotional tone or opinion expressed — it may be useful later\n"
        "- Avoid splitting mid-sentence unless absolutely necessary\n\n"
        "Output format: valid JSON list\n"
        "Each atom must be a JSON object like:\n"
        "{\n  \"speaker\": \"AJENA\",\n  \"text\": \"I grew up in Roanoke and loved spending time outdoors with my brothers.\"\n}\n\n"
        "Here is the cleaned transcript:\n---\n"
        f"{clean_text}\n---\n"
        "Return only a valid JSON list of atoms."
    )

    try:
        response = gemini_model.generate_content(prompt)
        raw = response.text.strip()

        # Remove Markdown-style code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1].strip()

        atoms = json.loads(raw)
        return atoms
    except Exception as e:
        print("Failed to parse LLM response:", e)
        print("Raw response was:\n", response.text)
        return []

def extract_text_from_pdf(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    full_text = ""
    for page in doc:
        full_text += page.get_text() + "\n"
    return full_text

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
        full_text = extract_text_from_pdf(pdf_path)
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
        full_text = extract_text_from_pdf(pdf_path)
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
