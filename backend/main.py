from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Allow frontend on localhost to talk to this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/upload")
async def upload_pdfs(files: list[UploadFile] = File(...)):
    file_names = [file.filename for file in files]
    print("Received files:", file_names)
    return {"message": f"Received {len(files)} PDF(s)", "files": file_names}
