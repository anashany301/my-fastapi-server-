from fastapi import FastAPI
from pydantic import BaseModel
import asyncio
import os
import uuid

app = FastAPI()

class CodePayload(BaseModel):
    code: str
    filename: str

@app.get("/")
async def home():
    return {"status": "Async Server Running"}

@app.post("/run")
async def run_code(payload: CodePayload):
    ext = os.path.splitext(payload.filename)[1].lower()
    unique_id = str(uuid.uuid4())[:8]
    temp_file = f"/tmp/temp_{unique_id}{ext}"

    with open(temp_file, "w", encoding="utf-8") as f:
        f.write(payload.code)

    try:
        if ext == ".py":
            cmd = ["python3", temp_file]
        elif ext == ".js":
            cmd = ["node", temp_file]
        elif ext == ".sh":
            cmd = ["bash", temp_file]
        else:
            if os.path.exists(temp_file): os.remove(temp_file)
            return {"output": f"Unsupported extension: {ext}"}

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=10.0)
            output = stdout.decode() if stdout else stderr.decode()
        except asyncio.TimeoutError:
            process.kill()
            output = "Error: Timeout (10s limit)"

        if os.path.exists(temp_file):
            os.remove(temp_file)

        return {"output": output if output.strip() else "[No Output]"}

    except Exception as e:
        if os.path.exists(temp_file):
            os.remove(temp_file)
        return {"output": f"Server Error: {str(e)}"}
