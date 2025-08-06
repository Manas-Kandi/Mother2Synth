import time
import fitz
from llm import gemini_model

LLM_PROMPT_NORMALIZER = """You are a senior UX research assistant.

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
Return only the cleaned, speaker-separated transcript."""

def run_llm_normalizer(raw_text: str) -> str:
    """Use Gemini to clean and structure raw transcript text."""
    if len(raw_text) > 50000:
        print(f"\u26A0\uFE0F Text very long ({len(raw_text)} chars), truncating to 50k")
        raw_text = raw_text[:50000] + "\n\n[... text truncated due to length ...]"
    prompt = LLM_PROMPT_NORMALIZER.replace("{raw_text}", raw_text)
    for attempt in range(2):
        try:
            print(f"\U0001F9E0 Normalizing attempt {attempt + 1}")
            response = gemini_model.generate_content(prompt)
            result = response.text.strip()
            if result and len(result) > 10:
                print(f"\u2705 Normalization successful ({len(result)} chars)")
                return result
            raise ValueError("Normalizer returned empty or very short result")
        except Exception as e:
            print(f"\u274C Normalization error (attempt {attempt + 1}): {e}")
            if attempt < 1:
                time.sleep(1)
                continue
    print("\U0001F6AB Normalization failed, returning raw text")
    return f"[Normalization failed - returning raw text]\n\n{raw_text}"

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from a PDF using PyMuPDF."""
    doc = fitz.open(pdf_path)
    full_text = ""
    for page in doc:
        full_text += page.get_text() + "\n"
    return full_text
